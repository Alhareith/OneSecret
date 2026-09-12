"""Text sharing endpoints for AES-256-GCM ciphertext produced by Web Crypto."""

from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.client_crypto_core import (
    AES_GCM_NONCE_BYTES,
    AES_GCM_TAG_BYTES,
    CANCEL_CODE_PATTERN,
    MAX_SECRET_LIFETIME,
    MAX_TEXT_CIPHERTEXT_BYTES,
    TEXT_ID_PATTERN,
    ClientTextShare,
    b64encode,
    enforce_rate_limit,
    generate_cancel_code,
    get_active_text,
    get_session,
    normalize_utc,
    strict_b64decode,
    utc_now,
)
from app.rate_limit import CANCEL_LIMIT, CREATE_SECRET_LIMIT, REVEAL_LIMIT
from app.secret_code import create_secret_code_material, verify_secret_code

router = APIRouter()


class ClientTextCreateRequest(BaseModel):
    secret_id: str = Field(min_length=48, max_length=48, pattern=TEXT_ID_PATTERN)
    ciphertext_b64: str = Field(min_length=1, max_length=100_000)
    nonce_b64: str = Field(min_length=1, max_length=128)
    expires_at: datetime
    destroy_on_open: bool = False
    secret_code: str | None = Field(default=None, min_length=8, max_length=128)

    @field_validator("expires_at")
    @classmethod
    def validate_expiry(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Expiration time must include timezone")
        if value > datetime.now(timezone.utc) + MAX_SECRET_LIFETIME:
            raise ValueError("Expiration exceeds limit")
        return value


class ClientTextCreateResponse(BaseModel):
    id: str
    expires_at: datetime
    status: Literal["active"] = "active"
    cancel_code: str = Field(min_length=5, max_length=5, pattern=CANCEL_CODE_PATTERN)


class ClientTextRevealRequest(BaseModel):
    secret_code: str | None = Field(default=None, min_length=8, max_length=128)


class ClientTextRevealResponse(BaseModel):
    id: str
    ciphertext_b64: str
    nonce_b64: str
    crypto: Literal["AES-256-GCM/WebCrypto"] = "AES-256-GCM/WebCrypto"


class ClientTextCancelRequest(BaseModel):
    cancel_code: str = Field(min_length=5, max_length=5, pattern=CANCEL_CODE_PATTERN)

    @field_validator("cancel_code", mode="before")
    @classmethod
    def normalize_code(cls, value: object) -> object:
        return value.strip().upper() if isinstance(value, str) else value


class ClientTextCancelResponse(BaseModel):
    id: str
    status: Literal["cancelled"] = "cancelled"


@router.post("/text", response_model=ClientTextCreateResponse, status_code=201)
def create_client_text(
    request: Request,
    payload: ClientTextCreateRequest,
    session: Session = Depends(get_session),
) -> ClientTextCreateResponse:
    enforce_rate_limit(request, scope="client-text-create", policy=CREATE_SECRET_LIMIT)
    ciphertext = strict_b64decode(payload.ciphertext_b64, field="ciphertext")
    nonce = strict_b64decode(payload.nonce_b64, field="nonce")
    if len(nonce) != AES_GCM_NONCE_BYTES:
        raise HTTPException(status_code=400, detail="Invalid nonce")
    if len(ciphertext) < AES_GCM_TAG_BYTES or len(ciphertext) > MAX_TEXT_CIPHERTEXT_BYTES:
        raise HTTPException(status_code=400, detail="Invalid ciphertext")

    expires_at = normalize_utc(payload.expires_at)
    current = utc_now()
    if expires_at <= current:
        raise HTTPException(status_code=400, detail="Expiration must be in the future")

    secret_salt, secret_hash = (
        create_secret_code_material(payload.secret_code) if payload.secret_code else (None, None)
    )
    cancel_code = generate_cancel_code()
    cancel_salt, cancel_hash = create_secret_code_material(cancel_code)
    share = ClientTextShare(
        id=payload.secret_id,
        ciphertext=ciphertext,
        nonce=nonce,
        created_at=current,
        expires_at=expires_at,
        used_at=None,
        cancelled_at=None,
        destroy_on_open=payload.destroy_on_open,
        secret_code_salt=secret_salt,
        secret_code_hash=secret_hash,
        cancel_code_salt=cancel_salt,
        cancel_code_hash=cancel_hash,
    )
    try:
        session.add(share)
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(status_code=409, detail="Secret identifier is unavailable") from exc
    return ClientTextCreateResponse(id=share.id, expires_at=share.expires_at, cancel_code=cancel_code)


@router.post("/text/{share_id}/reveal", response_model=ClientTextRevealResponse)
def reveal_client_text(
    request: Request,
    share_id: str,
    payload: ClientTextRevealRequest | None = None,
    session: Session = Depends(get_session),
) -> ClientTextRevealResponse:
    enforce_rate_limit(request, scope="client-text-reveal", policy=REVEAL_LIMIT)
    share = get_active_text(session, share_id)
    submitted = payload.secret_code if payload else None
    if share.secret_code_hash is not None:
        if submitted is None or share.secret_code_salt is None or not verify_secret_code(
            submitted, salt=share.secret_code_salt, expected_hash=share.secret_code_hash
        ):
            raise HTTPException(status_code=401, detail="Secret code is required or invalid")

    ciphertext = bytes(share.ciphertext or b"")
    nonce = bytes(share.nonce or b"")
    if share.destroy_on_open:
        current = utc_now()
        result = session.execute(
            update(ClientTextShare)
            .where(
                ClientTextShare.id == share_id,
                ClientTextShare.used_at.is_(None),
                ClientTextShare.expires_at > current,
            )
            .values(used_at=current, ciphertext=None, nonce=None)
        )
        if result.rowcount != 1:
            session.rollback()
            raise HTTPException(status_code=410, detail="Secret is unavailable")
        session.commit()

    return ClientTextRevealResponse(
        id=share_id, ciphertext_b64=b64encode(ciphertext), nonce_b64=b64encode(nonce)
    )


@router.post("/text/{share_id}/cancel", response_model=ClientTextCancelResponse)
def cancel_client_text(
    request: Request,
    share_id: str,
    payload: ClientTextCancelRequest,
    session: Session = Depends(get_session),
) -> ClientTextCancelResponse:
    enforce_rate_limit(request, scope="client-text-cancel", policy=CANCEL_LIMIT)
    share = session.get(ClientTextShare, share_id)
    if share is None:
        raise HTTPException(status_code=404, detail="Secret not found")
    if (
        share.used_at is not None
        or share.cancelled_at is not None
        or share.expires_at <= utc_now()
        or share.cancel_code_salt is None
        or share.cancel_code_hash is None
        or not verify_secret_code(
            payload.cancel_code,
            salt=share.cancel_code_salt,
            expected_hash=share.cancel_code_hash,
        )
    ):
        raise HTTPException(status_code=410, detail="Secret is unavailable")

    current = utc_now()
    result = session.execute(
        update(ClientTextShare)
        .where(
            ClientTextShare.id == share_id,
            ClientTextShare.used_at.is_(None),
            ClientTextShare.cancelled_at.is_(None),
            ClientTextShare.expires_at > current,
        )
        .values(
            cancelled_at=current,
            ciphertext=None,
            nonce=None,
            secret_code_salt=None,
            secret_code_hash=None,
            cancel_code_salt=None,
            cancel_code_hash=None,
        )
    )
    if result.rowcount != 1:
        session.rollback()
        raise HTTPException(status_code=410, detail="Secret is unavailable")
    session.commit()
    return ClientTextCancelResponse(id=share_id)
