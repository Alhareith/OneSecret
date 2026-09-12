"""اختبارات منطق DES الخام دون FastAPI أو صور."""

import os

import pytest

from app.crypto_des import (
    decrypt_bytes,
    encrypt_bytes,
    generate_iv,
    generate_key,
    validate_iv,
    validate_key,
)


def test_generate_key_requirements():
    key1 = generate_key()
    key2 = generate_key()
    assert isinstance(key1, bytes)
    assert len(key1) == 8
    assert key1 != key2


def test_validate_key_failures():
    with pytest.raises(ValueError):
        validate_key(b"short")
    with pytest.raises(ValueError):
        validate_key(b"toolongkey")
    with pytest.raises(ValueError):
        validate_key("string_not_bytes")  # type: ignore[arg-type]


def test_generate_and_validate_iv_requirements():
    iv1 = generate_iv()
    iv2 = generate_iv()
    assert isinstance(iv1, bytes)
    assert len(iv1) == 8
    assert iv1 != iv2

    with pytest.raises(ValueError):
        validate_iv(b"1234567")
    with pytest.raises(ValueError):
        validate_iv(12345678)  # type: ignore[arg-type]


def test_encrypt_decrypt_roundtrip():
    key = generate_key()
    iv = generate_iv()

    for plaintext in (b"Hello OneSecret", b"", os.urandom(100)):
        ciphertext = encrypt_bytes(plaintext, key, iv)
        assert ciphertext != plaintext
        assert decrypt_bytes(ciphertext, key, iv) == plaintext


def test_iv_changes_ciphertext():
    key = generate_key()
    plaintext = b"Consistent Data"
    assert encrypt_bytes(plaintext, key, generate_iv()) != encrypt_bytes(
        plaintext, key, generate_iv()
    )


def test_wrong_key_never_claims_authentication():
    """DES-CBC غير موثّق؛ المفتاح الخاطئ قد يفشل padding أو يعيد garbage."""
    key = generate_key()
    wrong_key = generate_key()
    iv = generate_iv()
    plaintext = b"Secret Message"
    ciphertext = encrypt_bytes(plaintext, key, iv)

    try:
        wrong_plaintext = decrypt_bytes(ciphertext, wrong_key, iv)
    except ValueError:
        return

    assert wrong_plaintext != plaintext


def test_corrupted_padding_fails_deterministically():
    """نقلب بتًا في C1 لتغيير آخر padding byte في P2 من 0x02 بشكل حتمي."""
    key = generate_key()
    iv = generate_iv()
    plaintext = b"Secret Message"  # 14 bytes -> PKCS#7 padding = 0x02 0x02
    ciphertext = bytearray(encrypt_bytes(plaintext, key, iv))

    assert len(ciphertext) == 16
    ciphertext[7] ^= 0x01

    with pytest.raises(ValueError):
        decrypt_bytes(bytes(ciphertext), key, iv)
