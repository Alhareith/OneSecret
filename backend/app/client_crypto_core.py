"""Shared storage and validation helpers for browser-encrypted OneSecret shares."""

from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from typing import Iterator

from fastapi import HTTPException, Request, status
from sqlalchemy import Boolean, DateTime, Index, LargeBinary, String, update
from sqlalchemy.dialects.mysql import MEDIUMBLOB
from sqlalchemy.orm import Mapped, Session, mapped_column, sessionmaker

from app.database import Base
from app.rate_limit import RequestRateLimiter, RateLimit

TEXT_ID_PATTERN = r"^[a-f0-9]{48}$"
CANCEL_CODE_PATTERN = r"^[A-HJ-NP-Z2-9]{5}$"
CANCEL_CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
CANCEL_CODE_LENGTH = 5
MAX_SECRET_LIFETIME = timedelta(hours=24)
MAX_TEXT_CIPHERTEXT_BYTES = 50_016
MAX_FILE_BYTES = 5 * 1024 * 1024
AES_GCM_NONCE_BYTES = 12
AES_GCM_TAG_BYTES = 16
RSA_2048_CIPHERTEXT_BYTES = 256
MAX_SHARE_MINUTES = 24 * 60


class ClientTextShare(Base):
    """A text share encrypted entirely in the browser."""

    __tablename__ = "client_text_shares"
    __table_args__ = (Index("ix_client_text_shares_expires_at", "expires_at"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    ciphertext: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    nonce: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    destroy_on_open: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    secret_code_salt: Mapped[str | None] = mapped_column(String(64), nullable=True)
    secret_code_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    cancel_code_salt: Mapped[str | None] = mapped_column(String(64), nullable=True)
    cancel_code_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)


class ClientFileShare(Base):
    """A hybrid-encrypted file envelope produced entirely in the browser."""

    __tablename__ = "client_file_shares"
    __table_args__ = (Index("ix_client_file_shares_expires_at", "expires_at"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(255), nullable=False)
    encrypted_key: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    nonce: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    ciphertext: Mapped[bytes | None] = mapped_column(
        LargeBinary().with_variant(MEDIUMBLOB(), "mysql"), nullable=True
    )
    claim_token_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def normalize_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Expiration time must include timezone")
    return value.astimezone(timezone.utc).replace(tzinfo=None)


def generate_cancel_code() -> str:
    return "".join(secrets.choice(CANCEL_CODE_ALPHABET) for _ in range(CANCEL_CODE_LENGTH))


def strict_b64decode(value: str, *, field: str) -> bytes:
    try:
        return base64.b64decode(value.encode("ascii"), validate=True)
    except (UnicodeEncodeError, binascii.Error, ValueError) as exc:
        raise HTTPException(status_code=400, detail=f"Invalid {field}") from exc


def b64encode(value: bytes) -> str:
    return base64.b64encode(value).decode("ascii")


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def valid_claim_token(expected_hash: str, submitted: str) -> bool:
    return hmac.compare_digest(expected_hash, token_hash(submitted))


def enforce_rate_limit(
    request: Request,
    *,
    scope: str,
    policy: RateLimit,
    consume: bool = True,
    source: str | None = None,
) -> None:
    """Apply a rate-limit bucket, optionally checking it without consuming an event."""

    limiter: RequestRateLimiter | None = getattr(request.app.state, "rate_limiter", None)
    if limiter is None:
        return
    bucket_source = source if source is not None else (
        request.client.host if request.client is not None else "unknown"
    )
    retry_after = (
        limiter.consume(scope=scope, source=bucket_source, policy=policy)
        if consume
        else limiter.retry_after(scope=scope, source=bucket_source, policy=policy)
    )
    if retry_after is not None:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests. Try again later.",
            headers={"Retry-After": str(retry_after)},
        )


def get_session(request: Request) -> Iterator[Session]:
    factory: sessionmaker[Session] | None = getattr(request.app.state, "session_factory", None)
    if factory is None:
        raise HTTPException(status_code=503, detail="Service is unavailable")
    session = factory()
    try:
        yield session
    finally:
        session.close()


def get_active_text(session: Session, share_id: str, *, now: datetime | None = None) -> ClientTextShare:
    current = now or utc_now()
    share = session.get(ClientTextShare, share_id)
    if share is None or share.cancelled_at is not None or share.used_at is not None:
        raise HTTPException(status_code=410, detail="Secret is unavailable")
    if share.expires_at <= current:
        if share.ciphertext is not None or share.nonce is not None:
            session.execute(
                update(ClientTextShare)
                .where(ClientTextShare.id == share.id)
                .values(ciphertext=None, nonce=None)
            )
            session.commit()
        raise HTTPException(status_code=410, detail="Secret is unavailable")
    if share.ciphertext is None or share.nonce is None:
        raise HTTPException(status_code=410, detail="Secret is unavailable")
    return share


def get_active_file(session: Session, share_id: str, *, now: datetime | None = None) -> ClientFileShare:
    current = now or utc_now()
    share = session.get(ClientFileShare, share_id)
    if share is None or share.used_at is not None:
        raise HTTPException(status_code=410, detail="File is unavailable")
    if share.expires_at <= current:
        if share.encrypted_key is not None or share.nonce is not None or share.ciphertext is not None:
            session.execute(
                update(ClientFileShare)
                .where(ClientFileShare.id == share.id)
                .values(encrypted_key=None, nonce=None, ciphertext=None)
            )
            session.commit()
        raise HTTPException(status_code=410, detail="File is unavailable")
    if share.encrypted_key is None or share.nonce is None or share.ciphertext is None:
        raise HTTPException(status_code=410, detail="File is unavailable")
    return share
