"""نماذج SQLAlchemy الخاصة بقاعدة بيانات OneSecret."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Index, LargeBinary, String, Text
from sqlalchemy.dialects.mysql import MEDIUMBLOB
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


class RsaFileShare(Base):
    """حزمة ملف RSA مشفّرة مؤقتًا؛ لا تحفظ المفتاح الخاص أو bytes الملف الأصلية."""

    __tablename__ = "rsa_file_shares"
    __table_args__ = (Index("ix_rsa_file_shares_expires_at", "expires_at"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(255), nullable=False)
    encrypted_key: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    nonce: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    ciphertext: Mapped[bytes | None] = mapped_column(
        LargeBinary().with_variant(MEDIUMBLOB, "mysql"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
