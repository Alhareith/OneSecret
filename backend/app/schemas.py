"""محجوز لتعريف نماذج الطلبات والردود في مرحلة API."""
"""عقود البيانات بين الواجهة وFastAPI لمرحلة دورة حياة السر."""

from datetime import datetime, timedelta, timezone
from typing import Literal

from pydantic import BaseModel, Field, field_validator


SecretState = Literal["active", "used", "expired", "missing"]
SECRET_ID_PATTERN = r"^[a-f0-9]{48}$"
MAX_SECRET_LIFETIME = timedelta(hours=24)


class CreateSecretRequest(BaseModel):
    """بيانات إنشاء سر. plaintext لا يُعاد في رد الإنشاء."""

    secret_id: str = Field(min_length=48, max_length=48, pattern=SECRET_ID_PATTERN)
    plaintext: str = Field(min_length=1, max_length=10_000)
    expires_at: datetime
    destroy_on_open: bool = False
    secret_code: str | None = Field(default=None, min_length=8, max_length=128)

    @field_validator("expires_at")
    @classmethod
    def require_timezone_and_limit_lifetime(cls, value: datetime) -> datetime:
        """يرفض وقتًا بلا منطقة زمنية أو مدة تتجاوز خيارات المنتج."""

        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Expiration time must include a timezone")

        if value > datetime.now(timezone.utc) + MAX_SECRET_LIFETIME:
            raise ValueError("Expiration time exceeds the allowed lifetime")

        return value


class CreateSecretResponse(BaseModel):
    id: str
    expires_at: datetime
    status: Literal["active"] = "active"
    cancel_code: str = Field(min_length=32, max_length=64)


class SecretStatusResponse(BaseModel):
    id: str
    status: SecretState
    expires_at: datetime | None = None


class RevealSecretResponse(BaseModel):
    id: str
    plaintext: str


class RevealSecretRequest(BaseModel):
    secret_code: str | None = Field(default=None, min_length=8, max_length=128)


class CancelSecretRequest(BaseModel):
    cancel_code: str = Field(min_length=32, max_length=64)


class CancelSecretResponse(BaseModel):
    id: str
    status: Literal["cancelled"] = "cancelled"
