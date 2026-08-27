"""اشتقاق والتحقق من Secret Code من دون حفظ الكود نفسه."""

import base64
import hashlib
import hmac
import secrets


SALT_BYTES = 16
DERIVED_KEY_BYTES = 32
SCRYPT_N = 2**14
SCRYPT_R = 8
SCRYPT_P = 1


def _derive(secret_code: str, salt: bytes) -> bytes:
    return hashlib.scrypt(
        secret_code.encode("utf-8"),
        salt=salt,
        n=SCRYPT_N,
        r=SCRYPT_R,
        p=SCRYPT_P,
        dklen=DERIVED_KEY_BYTES,
        maxmem=64 * 1024 * 1024,
    )


def create_secret_code_material(secret_code: str) -> tuple[str, str]:
    """يعيد salt واشتقاق scrypt بصيغة قابلة للتخزين، ولا يعيد الكود."""

    salt = secrets.token_bytes(SALT_BYTES)
    derived_key = _derive(secret_code, salt)
    return (
        base64.urlsafe_b64encode(salt).decode("ascii"),
        base64.urlsafe_b64encode(derived_key).decode("ascii"),
    )


def verify_secret_code(secret_code: str, *, salt: str, expected_hash: str) -> bool:
    """يتحقق بمقارنة ثابتة الزمن بعد اشتقاق قيمة الكود المقدمة."""

    try:
        salt_bytes = base64.urlsafe_b64decode(salt.encode("ascii"))
        expected_bytes = base64.urlsafe_b64decode(expected_hash.encode("ascii"))
    except (ValueError, UnicodeEncodeError):
        return False

    return hmac.compare_digest(_derive(secret_code, salt_bytes), expected_bytes)
