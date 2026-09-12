"""DES image encryption and temporary sharing API.

PNG/JPEG images are encrypted with the educational Single-DES CBC implementation.
The encrypted image is stored temporarily for link sharing; the DES key itself is
not stored in the database and is carried in the URL fragment by the frontend.
"""

from __future__ import annotations

import base64
import binascii
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import PurePath
from typing import Iterator

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from pydantic import BaseModel, Field
from sqlalchemy import DateTime, LargeBinary, String, update
from sqlalchemy.dialects.mysql import MEDIUMBLOB
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Mapped, Session, mapped_column, sessionmaker

from app.crypto_des import decrypt_bytes, encrypt_bytes, generate_iv, generate_key
from app.database import Base

MAX_IMAGE_BYTES = 5 * 1024 * 1024
MAX_SHARE_MINUTES = 24 * 60
ALLOWED_IMAGE_TYPES = frozenset({"image/png", "image/jpeg"})

router = APIRouter(prefix="/api/des-image", tags=["DES Images"])


class DesImageShare(Base):
    """Temporary DES-encrypted image. The DES key is intentionally not persisted."""

    __tablename__ = "des_image_shares"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(64), nullable=False)
    iv: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    ciphertext: Mapped[bytes | None] = mapped_column(
        LargeBinary().with_variant(MEDIUMBLOB(), "mysql"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class DesImageEncrypted(BaseModel):
    filename: str
    content_type: str
    key_b64: str
    iv_b64: str
    ciphertext_b64: str


class DesImageDecryptRequest(BaseModel):
    filename: str
    content_type: str
    key_b64: str
    iv_b64: str
    ciphertext_b64: str


class DesImageDecrypted(BaseModel):
    filename: str
    content_type: str
    data_b64: str


class DesImageShareCreated(BaseModel):
    id: str
    filename: str
    content_type: str
    expires_at: datetime
    key_fragment: str


class DesImageShareInfo(BaseModel):
    id: str
    filename: str
    content_type: str
    expires_at: datetime


class DesImageRevealRequest(BaseModel):
    key_fragment: str = Field(min_length=8, max_length=128)


class DesImageRevealResponse(BaseModel):
    id: str
    filename: str
    content_type: str
    data_b64: str


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _decode_base64(value: str) -> bytes:
    """Strict Base64 decoder for the original encrypt/decrypt demo endpoints."""
    return base64.b64decode(value, validate=True)


def _encode_base64url(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _decode_base64url(value: str) -> bytes:
    try:
        normalized = value.encode("ascii")
        normalized += b"=" * ((4 - len(normalized) % 4) % 4)
        return base64.b64decode(normalized, altchars=b"-_", validate=True)
    except (UnicodeEncodeError, binascii.Error, ValueError) as exc:
        raise ValueError("Invalid key fragment") from exc


def _get_session(request: Request) -> Iterator[Session]:
    factory: sessionmaker[Session] | None = getattr(request.app.state, "session_factory", None)
    if factory is None:
        raise HTTPException(status_code=503, detail="Service is unavailable")
    session = factory()
    try:
        yield session
    finally:
        session.close()


async def _read_valid_image(file: UploadFile) -> bytes:
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PNG and JPEG images are allowed.",
        )

    file_bytes = await file.read(MAX_IMAGE_BYTES + 1)
    if not file_bytes:
        raise HTTPException(status_code=400, detail="File is empty.")
    if len(file_bytes) > MAX_IMAGE_BYTES:
        raise HTTPException(status_code=400, detail="File size exceeds the 5 MiB limit.")
    return file_bytes


def _has_expected_signature(data: bytes, content_type: str) -> bool:
    if content_type == "image/png":
        return data.startswith(b"\x89PNG\r\n\x1a\n")
    if content_type == "image/jpeg":
        return data.startswith(b"\xff\xd8\xff")
    return False


def _get_active_share(session: Session, share_id: str) -> DesImageShare:
    share = session.get(DesImageShare, share_id)
    if share is None or share.used_at is not None:
        raise HTTPException(status_code=410, detail="Image is unavailable")

    if share.expires_at <= _utc_now():
        if share.iv is not None or share.ciphertext is not None:
            session.execute(
                update(DesImageShare)
                .where(DesImageShare.id == share_id)
                .values(iv=None, ciphertext=None)
            )
            session.commit()
        raise HTTPException(status_code=410, detail="Image is unavailable")

    if share.iv is None or share.ciphertext is None:
        raise HTTPException(status_code=410, detail="Image is unavailable")
    return share


@router.post("/encrypt", response_model=DesImageEncrypted)
async def encrypt_image(file: UploadFile = File(...)) -> DesImageEncrypted:
    """Original educational encrypt endpoint kept for compatibility/tests."""
    file_bytes = await _read_valid_image(file)
    key = generate_key()
    iv = generate_iv()
    ciphertext = encrypt_bytes(file_bytes, key, iv)

    return DesImageEncrypted(
        filename=PurePath(file.filename or "image").name,
        content_type=file.content_type or "image/png",
        key_b64=base64.b64encode(key).decode("ascii"),
        iv_b64=base64.b64encode(iv).decode("ascii"),
        ciphertext_b64=base64.b64encode(ciphertext).decode("ascii"),
    )


@router.post("/decrypt", response_model=DesImageDecrypted)
async def decrypt_image(request: DesImageDecryptRequest) -> DesImageDecrypted:
    """Original educational decrypt endpoint kept for compatibility/tests."""
    if request.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=400, detail="Decryption failed. Invalid data.")

    try:
        key = _decode_base64(request.key_b64)
        iv = _decode_base64(request.iv_b64)
        ciphertext = _decode_base64(request.ciphertext_b64)
        plaintext = decrypt_bytes(ciphertext, key, iv)
    except (ValueError, binascii.Error):
        raise HTTPException(
            status_code=400,
            detail="Decryption failed. Invalid key, IV, or corrupted data.",
        ) from None

    return DesImageDecrypted(
        filename=request.filename,
        content_type=request.content_type,
        data_b64=base64.b64encode(plaintext).decode("ascii"),
    )


@router.post("/share", response_model=DesImageShareCreated, status_code=201)
async def create_des_image_share(
    file: UploadFile = File(...),
    expires_minutes: int = Form(15),
    session: Session = Depends(_get_session),
) -> DesImageShareCreated:
    """Encrypt an image with DES-CBC, store only the encrypted package, and return a share key."""
    if expires_minutes < 1 or expires_minutes > MAX_SHARE_MINUTES:
        raise HTTPException(status_code=400, detail="Invalid expiration")

    file_bytes = await _read_valid_image(file)
    key = generate_key()
    iv = generate_iv()
    ciphertext = encrypt_bytes(file_bytes, key, iv)
    current = _utc_now()
    expires_at = current + timedelta(minutes=expires_minutes)
    safe_filename = PurePath(file.filename or "image").name
    content_type = file.content_type or "image/png"

    for _ in range(3):
        share = DesImageShare(
            id=secrets.token_urlsafe(24),
            filename=safe_filename,
            content_type=content_type,
            iv=iv,
            ciphertext=ciphertext,
            created_at=current,
            expires_at=expires_at,
            used_at=None,
        )
        try:
            session.add(share)
            session.commit()
            return DesImageShareCreated(
                id=share.id,
                filename=share.filename,
                content_type=share.content_type,
                expires_at=share.expires_at,
                key_fragment=_encode_base64url(key),
            )
        except IntegrityError:
            session.rollback()

    raise HTTPException(status_code=503, detail="Unable to create image share")


@router.get("/share/{share_id}", response_model=DesImageShareInfo)
def get_des_image_share(
    share_id: str,
    session: Session = Depends(_get_session),
) -> DesImageShareInfo:
    share = _get_active_share(session, share_id)
    return DesImageShareInfo(
        id=share.id,
        filename=share.filename,
        content_type=share.content_type,
        expires_at=share.expires_at,
    )


@router.post("/share/{share_id}/reveal", response_model=DesImageRevealResponse)
def reveal_des_image_share(
    share_id: str,
    payload: DesImageRevealRequest,
    session: Session = Depends(_get_session),
) -> DesImageRevealResponse:
    """Decrypt once with the key from the URL fragment, then erase the encrypted payload."""
    share = _get_active_share(session, share_id)
    try:
        key = _decode_base64url(payload.key_fragment)
        plaintext = decrypt_bytes(bytes(share.ciphertext or b""), key, bytes(share.iv or b""))
    except (ValueError, binascii.Error):
        raise HTTPException(status_code=400, detail="Invalid image key or corrupted data") from None

    if not _has_expected_signature(plaintext, share.content_type):
        raise HTTPException(status_code=400, detail="Invalid image key or corrupted data")

    current = _utc_now()
    result = session.execute(
        update(DesImageShare)
        .where(
            DesImageShare.id == share_id,
            DesImageShare.used_at.is_(None),
            DesImageShare.expires_at > current,
        )
        .values(used_at=current, iv=None, ciphertext=None)
    )
    if result.rowcount != 1:
        session.rollback()
        raise HTTPException(status_code=410, detail="Image is unavailable")
    session.commit()

    return DesImageRevealResponse(
        id=share.id,
        filename=share.filename,
        content_type=share.content_type,
        data_b64=base64.b64encode(plaintext).decode("ascii"),
    )
