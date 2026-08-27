"""إعدادات الخادم. لا توجد أسرار فعلية داخل هذا الملف."""

import base64
import binascii
from dataclasses import dataclass
import os


@dataclass(frozen=True)
class Settings:
    """قيم الإعدادات التي يحتاجها الخادم في المراحل اللاحقة."""

    database_url: str | None
    encryption_key: str | None


def get_settings() -> Settings:
    """يقرأ الأسماء من البيئة؛ لا يضع القيم الحساسة في الكود."""

    return Settings(
        database_url=os.getenv("ONESECRET_DATABASE_URL") or os.getenv("DATABASE_URL"),
        encryption_key=os.getenv("ONESECRET_ENCRYPTION_KEY"),
    )


def load_encryption_key() -> bytes:
    """يقرأ مفتاح AES-256 من البيئة ويتحقق من Base64 وطول 32 بايت.

    لا تسجل هذه الدالة المفتاح أو تعيده في رسائل الأخطاء.
    """

    encoded_key = get_settings().encryption_key
    if not encoded_key:
        raise RuntimeError("OneSecret encryption key is not configured")

    try:
        key = base64.b64decode(encoded_key, validate=True)
    except (ValueError, binascii.Error) as error:
        raise RuntimeError("OneSecret encryption key is invalid") from error

    if len(key) != 32:
        raise RuntimeError("OneSecret encryption key is invalid")

    return key
