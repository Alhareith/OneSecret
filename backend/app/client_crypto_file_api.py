"""File sharing endpoints for hybrid ciphertext produced by Web Crypto."""

import secrets
from datetime import datetime, timedelta
from pathlib import PurePath
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.client_crypto_core import (
    AES_GCM_NONCE_BYTES,
    AES_GCM_TAG_BYTES,
    MAX_FILE_BYTES,
    MAX_SHARE_MINUTES,
    RSA_2048_CIPHERTEXT_BYTES,
    ClientFileShare,
    b64encode,
    enforce_rate_limit,
    get_active_file,
    get_session,
    strict_b64decode,
    token_hash,
    utc_now,
    valid_claim_token,
)
from app.rate_limit import CREATE_SECRET_LIMIT, REVEAL_LIMIT

router = APIRouter()


class ClientFileCreateRequest(BaseModel):
    filename: str = Field(min_length=1, max_length=255)
    content_type: str = Field(min_length=1, max_length=255)
    encrypted_key_b64: str = Field(min_length=1, max_length=1024)
    nonce_b64: str = Field(min_length=1, max_length=128)
    ciphertext_b64: str = Field(min_length=1, max_length=8_000_000)
    claim_token: str = Field(min_length=20, max_length=256)
    expires_minutes: int = Field(default=15, ge=1, le=MAX_SHARE_MINUTES)


class ClientFileShareInfo(BaseModel):
    id: str
    filename: str
    content_type: str
    expires_at: datetime


class ClientFileClaimRequest(BaseModel):
    claim_token: str = Field(min_length=20, max_length=256)


class ClientFileEnvelopeResponse(BaseModel):
    id: str
    filename: str
    content_type: str
    encrypted_key_b64: str
    nonce_b64: str
    ciphertext_b64: str
    crypto: Literal["AES-256-GCM+RSA-OAEP-SHA256/WebCrypto"] = (
        "AES-256-GCM+RSA-OAEP-SHA256/WebCrypto"
    )


class ClientFileConsumeResponse(BaseModel):
    id: str
    status: Literal["consumed"] = "consumed"


@router.post("/file", response_model=ClientFileShareInfo, status_code=201)
def create_client_file(
    request: Request,
    payload: ClientFileCreateRequest,
    session: Session = Depends(get_session),
) -> ClientFileShareInfo:
    enforce_rate_limit(request, scope="client-file-create", policy=CREATE_SECRET_LIMIT)
    if payload.content_type.lower().startswith("image/"):
        raise HTTPException(status_code=400, detail="Image files use a separate path")

    encrypted_key = strict_b64decode(payload.encrypted_key_b64, field="encrypted key")
    nonce = strict_b64decode(payload.nonce_b64, field="nonce")
    ciphertext = strict_b64decode(payload.ciphertext_b64, field="ciphertext")
    if len(encrypted_key) != RSA_2048_CIPHERTEXT_BYTES:
        raise HTTPException(status_code=400, detail="Invalid encrypted key")
    if len(nonce) != AES_GCM_NONCE_BYTES:
        raise HTTPException(status_code=400, detail="Invalid nonce")
    if len(ciphertext) <= AES_GCM_TAG_BYTES or len(ciphertext) > MAX_FILE_BYTES + AES_GCM_TAG_BYTES:
        raise HTTPException(status_code=400, detail="Invalid ciphertext size")

    safe_filename = PurePath(payload.filename).name or "file"
    current = utc_now()
    expires_at = current + timedelta(minutes=payload.expires_minutes)
    for _ in range(3):
        share = ClientFileShare(
            id=secrets.token_urlsafe(24),
            filename=safe_filename,
            content_type=payload.content_type,
            encrypted_key=encrypted_key,
            nonce=nonce,
            ciphertext=ciphertext,
            claim_token_hash=token_hash(payload.claim_token),
            created_at=current,
            expires_at=expires_at,
            used_at=None,
        )
        try:
            session.add(share)
            session.commit()
            return ClientFileShareInfo(
                id=share.id,
                filename=share.filename,
                content_type=share.content_type,
                expires_at=share.expires_at,
            )
        except IntegrityError:
            session.rollback()
    raise HTTPException(status_code=503, detail="Unable to create file share")


@router.get("/file/{share_id}", response_model=ClientFileShareInfo)
def get_client_file_info(
    share_id: str,
    session: Session = Depends(get_session),
) -> ClientFileShareInfo:
    share = get_active_file(session, share_id)
    return ClientFileShareInfo(
        id=share.id,
        filename=share.filename,
        content_type=share.content_type,
        expires_at=share.expires_at,
    )


@router.post("/file/{share_id}/envelope", response_model=ClientFileEnvelopeResponse)
def get_client_file_envelope(
    request: Request,
    share_id: str,
    payload: ClientFileClaimRequest,
    session: Session = Depends(get_session),
) -> ClientFileEnvelopeResponse:
    enforce_rate_limit(request, scope="client-file-envelope", policy=REVEAL_LIMIT)
    share = get_active_file(session, share_id)
    if not valid_claim_token(share.claim_token_hash, payload.claim_token):
        raise HTTPException(status_code=401, detail="File is unavailable")
    return ClientFileEnvelopeResponse(
        id=share.id,
        filename=share.filename,
        content_type=share.content_type,
        encrypted_key_b64=b64encode(bytes(share.encrypted_key or b"")),
        nonce_b64=b64encode(bytes(share.nonce or b"")),
        ciphertext_b64=b64encode(bytes(share.ciphertext or b"")),
    )


@router.post("/file/{share_id}/consume", response_model=ClientFileConsumeResponse)
def consume_client_file(
    request: Request,
    share_id: str,
    payload: ClientFileClaimRequest,
    session: Session = Depends(get_session),
) -> ClientFileConsumeResponse:
    enforce_rate_limit(request, scope="client-file-consume", policy=REVEAL_LIMIT)
    share = get_active_file(session, share_id)
    if not valid_claim_token(share.claim_token_hash, payload.claim_token):
        raise HTTPException(status_code=401, detail="File is unavailable")

    current = utc_now()
    result = session.execute(
        update(ClientFileShare)
        .where(
            ClientFileShare.id == share_id,
            ClientFileShare.used_at.is_(None),
            ClientFileShare.expires_at > current,
        )
        .values(used_at=current, encrypted_key=None, nonce=None, ciphertext=None)
    )
    if result.rowcount != 1:
        session.rollback()
        raise HTTPException(status_code=410, detail="File is unavailable")
    session.commit()
    return ClientFileConsumeResponse(id=share_id)
