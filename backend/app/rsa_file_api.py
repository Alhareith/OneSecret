"""HTTP API for RSA file encryption and temporary encrypted file sharing.

The original educational RSA endpoints remain available. The sharing layer stores
only the encrypted envelope and file metadata; the RSA private key is never
stored in the database.
"""

import base64
import secrets
from datetime import datetime, timedelta, timezone
from typing import Iterator

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from pydantic import BaseModel
from sqlalchemy import and_, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.crypto_rsa import (
    RsaFileEnvelope,
    decrypt_file_bytes,
    encrypt_file_bytes,
    generate_key_pair,
    load_private_key,
    load_public_key,
    private_key_to_pem,
    public_key_to_pem,
)
from app.models import RsaFileShare

MAX_FILE_BYTES = 5 * 1024 * 1024
MAX_SHARE_MINUTES = 24 * 60

router = APIRouter(prefix="/api/rsa-file", tags=["RSA Files"])


class RsaKeyPairResponse(BaseModel):
    public_key_pem: str
    private_key_pem: str


class RsaFileEncrypted(BaseModel):
    filename: str
    content_type: str
    encrypted_key_b64: str
    nonce_b64: str
    ciphertext_b64: str


class RsaFileDecryptRequest(BaseModel):
    filename: str
    content_type: str
    private_key_pem: str
    encrypted_key_b64: str
    nonce_b64: str
    ciphertext_b64: str


class RsaFileDecrypted(BaseModel):
    filename: str
    content_type: str
    data_b64: str


class RsaFileShareCreated(BaseModel):
    id: str
    filename: str
    content_type: str
    expires_at: datetime


class RsaFileShareInfo(BaseModel):
    id: str
    filename: str
    content_type: str
    expires_at: datetime


class RsaFileShareRevealRequest(BaseModel):
    private_key_pem: str


def utc_now() -> datetime:
    """Return naive UTC to match the SQLite behavior used by this project."""

    return datetime.now(timezone.utc).replace(tzinfo=None)


def get_share_session(request: Request) -> Iterator[Session]:
    """Open a database session from the runtime configured by the main app."""

    session_factory: sessionmaker[Session] | None = getattr(request.app.state, "session_factory", None)
    if session_factory is None:
        raise HTTPException(status_code=503, detail="Service is unavailable")

    session = session_factory()
    try:
        yield session
    finally:
        session.close()


async def read_valid_file(file: UploadFile) -> bytes:
    """Validate the shared RSA file contract and return the raw bytes."""

    if file.content_type and file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Image files are not accepted here")

    file_bytes = await file.read()
    if len(file_bytes) == 0:
        raise HTTPException(status_code=400, detail="File is empty")
    if len(file_bytes) > MAX_FILE_BYTES:
        raise HTTPException(status_code=400, detail="File exceeds 5 MiB limit")

    return file_bytes


def get_active_share(session: Session, share_id: str, *, now: datetime | None = None) -> RsaFileShare:
    """Return an active share or the same generic unavailable response for all dead states."""

    current_time = now or utc_now()
    share = session.get(RsaFileShare, share_id)
    if share is None:
        raise HTTPException(status_code=410, detail="File is unavailable")

    if share.used_at is not None:
        raise HTTPException(status_code=410, detail="File is unavailable")

    if share.expires_at <= current_time:
        if share.encrypted_key is not None or share.nonce is not None or share.ciphertext is not None:
            session.execute(
                update(RsaFileShare)
                .where(RsaFileShare.id == share_id)
                .values(encrypted_key=None, nonce=None, ciphertext=None)
            )
            session.commit()
        raise HTTPException(status_code=410, detail="File is unavailable")

    if share.encrypted_key is None or share.nonce is None or share.ciphertext is None:
        raise HTTPException(status_code=410, detail="File is unavailable")

    return share


@router.post("/generate-keypair", response_model=RsaKeyPairResponse)
def generate_keypair() -> RsaKeyPairResponse:
    private_key, public_key = generate_key_pair()

    return RsaKeyPairResponse(
        public_key_pem=public_key_to_pem(public_key).decode("utf-8"),
        private_key_pem=private_key_to_pem(private_key).decode("utf-8"),
    )


@router.post("/encrypt", response_model=RsaFileEncrypted)
async def encrypt_file(
    file: UploadFile = File(...),
    public_key_pem: str = Form(...),
) -> RsaFileEncrypted:
    file_bytes = await read_valid_file(file)

    try:
        public_key = load_public_key(public_key_pem.encode("utf-8"))
        envelope = encrypt_file_bytes(file_bytes, public_key)
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="Invalid public key")

    return RsaFileEncrypted(
        filename=file.filename or "file",
        content_type=file.content_type or "application/octet-stream",
        encrypted_key_b64=base64.b64encode(envelope.encrypted_key).decode("ascii"),
        nonce_b64=base64.b64encode(envelope.nonce).decode("ascii"),
        ciphertext_b64=base64.b64encode(envelope.ciphertext).decode("ascii"),
    )


@router.post("/decrypt", response_model=RsaFileDecrypted)
def decrypt_file(payload: RsaFileDecryptRequest) -> RsaFileDecrypted:
    try:
        private_key = load_private_key(payload.private_key_pem.encode("utf-8"))
        envelope = RsaFileEnvelope(
            encrypted_key=base64.b64decode(payload.encrypted_key_b64),
            nonce=base64.b64decode(payload.nonce_b64),
            ciphertext=base64.b64decode(payload.ciphertext_b64),
        )
        plaintext = decrypt_file_bytes(envelope, private_key)
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="Decryption failed")

    return RsaFileDecrypted(
        filename=payload.filename,
        content_type=payload.content_type,
        data_b64=base64.b64encode(plaintext).decode("ascii"),
    )


@router.post("/share", response_model=RsaFileShareCreated, status_code=201)
async def create_file_share(
    file: UploadFile = File(...),
    public_key_pem: str = Form(...),
    expires_minutes: int = Form(15),
    session: Session = Depends(get_share_session),
) -> RsaFileShareCreated:
    """Encrypt a file and store only its encrypted envelope for temporary sharing."""

    if expires_minutes < 1 or expires_minutes > MAX_SHARE_MINUTES:
        raise HTTPException(status_code=400, detail="Invalid expiration")

    file_bytes = await read_valid_file(file)
    try:
        public_key = load_public_key(public_key_pem.encode("utf-8"))
        envelope = encrypt_file_bytes(file_bytes, public_key)
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="Invalid public key")

    current_time = utc_now()
    expires_at = current_time + timedelta(minutes=expires_minutes)
    filename = file.filename or "file"
    content_type = file.content_type or "application/octet-stream"

    for _ in range(3):
        share_id = secrets.token_urlsafe(24)
        share = RsaFileShare(
            id=share_id,
            filename=filename,
            content_type=content_type,
            encrypted_key=envelope.encrypted_key,
            nonce=envelope.nonce,
            ciphertext=envelope.ciphertext,
            created_at=current_time,
            expires_at=expires_at,
            used_at=None,
        )
        try:
            session.add(share)
            session.commit()
            return RsaFileShareCreated(
                id=share.id,
                filename=share.filename,
                content_type=share.content_type,
                expires_at=share.expires_at,
            )
        except IntegrityError:
            session.rollback()

    raise HTTPException(status_code=503, detail="Unable to create file share")


@router.get("/share/{share_id}", response_model=RsaFileShareInfo)
def get_file_share_info(
    share_id: str,
    session: Session = Depends(get_share_session),
) -> RsaFileShareInfo:
    """Return safe metadata only; encrypted bytes and keys are never exposed here."""

    share = get_active_share(session, share_id)
    return RsaFileShareInfo(
        id=share.id,
        filename=share.filename,
        content_type=share.content_type,
        expires_at=share.expires_at,
    )


@router.post("/share/{share_id}/reveal", response_model=RsaFileDecrypted)
def reveal_file_share(
    share_id: str,
    payload: RsaFileShareRevealRequest,
    session: Session = Depends(get_share_session),
) -> RsaFileDecrypted:
    """Decrypt once with the private key supplied by the recipient, then erase the stored envelope."""

    current_time = utc_now()
    share = get_active_share(session, share_id, now=current_time)
    filename = share.filename
    content_type = share.content_type

    try:
        private_key = load_private_key(payload.private_key_pem.encode("utf-8"))
        envelope = RsaFileEnvelope(
            encrypted_key=bytes(share.encrypted_key or b""),
            nonce=bytes(share.nonce or b""),
            ciphertext=bytes(share.ciphertext or b""),
        )
        plaintext = decrypt_file_bytes(envelope, private_key)
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="Decryption failed")

    consume_result = session.execute(
        update(RsaFileShare)
        .where(
            and_(
                RsaFileShare.id == share_id,
                RsaFileShare.used_at.is_(None),
                RsaFileShare.expires_at > current_time,
                RsaFileShare.encrypted_key.is_not(None),
                RsaFileShare.nonce.is_not(None),
                RsaFileShare.ciphertext.is_not(None),
            )
        )
        .values(
            used_at=current_time,
            encrypted_key=None,
            nonce=None,
            ciphertext=None,
        )
    )
    if consume_result.rowcount != 1:
        session.rollback()
        raise HTTPException(status_code=410, detail="File is unavailable")

    session.commit()
    return RsaFileDecrypted(
        filename=filename,
        content_type=content_type,
        data_b64=base64.b64encode(plaintext).decode("ascii"),
    )
