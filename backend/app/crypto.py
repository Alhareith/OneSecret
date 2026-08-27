"""دوال التشفير في OneSecret، مبنية خطوة بخطوة لأغراض التعلم والاختبار."""

import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


AES_256_KEY_BYTES = 32
GCM_NONCE_BYTES = 12


def generate_key() -> bytes:
    """ينشئ مفتاح AES-256 عشوائيًا بطول 32 بايت.

    هذه هي دالة التحضير المكافئة تعليميًا لفكرة MakeKey في مختبر Vigenère،
    لكن المفتاح هنا عشوائي بايتات وليس كلمة من حروف A-Z.
    """

    return AESGCM.generate_key(bit_length=256)


def validate_key(key: bytes) -> bytes:
    """يتحقق أن المفتاح يصلح لاستخدام AES-256 قبل أي عملية تشفير."""

    if not isinstance(key, (bytes, bytearray)):
        raise TypeError("AES-256 key must be bytes")

    normalized_key = bytes(key)
    if len(normalized_key) != AES_256_KEY_BYTES:
        raise ValueError("AES-256 key must be exactly 32 bytes")

    return normalized_key


def generate_nonce() -> bytes:
    """ينشئ Nonce عشوائيًا جديدًا بطول 12 بايت لكل عملية AES-GCM."""

    return os.urandom(GCM_NONCE_BYTES)


def validate_nonce(nonce: bytes) -> bytes:
    """يتحقق من Nonce القياسي الذي نعتمده قبل التشفير أو فك التشفير."""

    if not isinstance(nonce, (bytes, bytearray)):
        raise TypeError("AES-GCM nonce must be bytes")

    normalized_nonce = bytes(nonce)
    if len(normalized_nonce) != GCM_NONCE_BYTES:
        raise ValueError("AES-GCM nonce must be exactly 12 bytes")

    return normalized_nonce


def encrypt_text(plaintext: str, key: bytes, nonce: bytes) -> bytes:
    """يحوّل النص إلى UTF-8 ثم يشفّره باستخدام AES-256-GCM.

    الناتج يتضمن ciphertext ووسم السلامة الذي تستعمله المكتبة عند فك التشفير.
    """

    if not isinstance(plaintext, str):
        raise TypeError("Plaintext must be a string")

    aesgcm = AESGCM(validate_key(key))
    return aesgcm.encrypt(validate_nonce(nonce), plaintext.encode("utf-8"), None)


def decrypt_text(ciphertext: bytes, key: bytes, nonce: bytes) -> str:
    """يفك AES-GCM ويعيد النص الأصلي فقط عندما تمر سلامة البيانات بنجاح.

    تترك الدالة خطأ InvalidTag من المكتبة يمر إلى طبقة API لاحقًا، حيث تعرض
    الواجهة رسالة عامة لا تكشف هل كان المفتاح أو Nonce أو البيانات هو الخطأ.
    """

    if not isinstance(ciphertext, (bytes, bytearray)):
        raise TypeError("Ciphertext must be bytes")

    aesgcm = AESGCM(validate_key(key))
    plaintext_bytes = aesgcm.decrypt(validate_nonce(nonce), bytes(ciphertext), None)

    try:
        return plaintext_bytes.decode("utf-8")
    except UnicodeDecodeError as error:
        raise ValueError("Decrypted data is not valid UTF-8") from error
