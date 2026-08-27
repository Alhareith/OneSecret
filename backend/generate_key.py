"""توليد مفتاح AES-256 واحد بصيغة Base64 لاستخدامه في إعدادات OneSecret.

شغّل: python3 generate_key.py
ثم انسخ السطر الناتج إلى حقل ONESECRET_ENCRYPTION_KEY الآمن فقط.
"""

import base64
import secrets


def generate_base64_aes_256_key() -> str:
    """ينشئ 32 بايت عشوائية ويعيدها كنص Base64."""

    return base64.b64encode(secrets.token_bytes(32)).decode("ascii")


if __name__ == "__main__":
    print(generate_base64_aes_256_key())
