"""نماذج SQLAlchemy الخاصة بقاعدة بيانات OneSecret."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Secret(Base):
    """سجل سر مشفّر. لا يحتوي على النص الأصلي أو مفتاح التشفير."""

    __tablename__ = "secrets"
    __table_args__ = (Index("ix_secrets_expires_at", "expires_at"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    ciphertext: Mapped[str | None] = mapped_column(Text, nullable=True)
    nonce: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    destroy_on_open: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    secret_code_salt: Mapped[str | None] = mapped_column(String(64), nullable=True)
    secret_code_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    cancel_code_salt: Mapped[str | None] = mapped_column(String(64), nullable=True)
    cancel_code_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
