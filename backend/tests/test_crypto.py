import pytest
from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.crypto import (
    AES_256_KEY_BYTES,
    GCM_NONCE_BYTES,
    decrypt_text,
    encrypt_text,
    generate_key,
    generate_nonce,
    validate_key,
    validate_nonce,
)


def test_generate_key_returns_a_32_byte_aes_256_key() -> None:
    key = generate_key()

    assert isinstance(key, bytes)
    assert len(key) == AES_256_KEY_BYTES
    assert validate_key(key) == key


def test_generate_key_produces_new_random_keys() -> None:
    first_key = generate_key()
    second_key = generate_key()

    assert first_key != second_key


@pytest.mark.parametrize("invalid_key", [b"", b"short", b"x" * 31, b"x" * 33])
def test_validate_key_rejects_invalid_key_lengths(invalid_key: bytes) -> None:
    with pytest.raises(ValueError, match="exactly 32 bytes"):
        validate_key(invalid_key)


def test_validate_key_rejects_non_bytes_value() -> None:
    with pytest.raises(TypeError, match="must be bytes"):
        validate_key("not-bytes")  # type: ignore[arg-type]


def test_generate_nonce_returns_a_12_byte_value() -> None:
    nonce = generate_nonce()

    assert isinstance(nonce, bytes)
    assert len(nonce) == GCM_NONCE_BYTES
    assert validate_nonce(nonce) == nonce


def test_generate_nonce_produces_unique_samples() -> None:
    nonces = {generate_nonce() for _ in range(20)}

    assert len(nonces) == 20


@pytest.mark.parametrize("invalid_nonce", [b"", b"short", b"x" * 11, b"x" * 13])
def test_validate_nonce_rejects_invalid_nonce_lengths(invalid_nonce: bytes) -> None:
    with pytest.raises(ValueError, match="exactly 12 bytes"):
        validate_nonce(invalid_nonce)


def test_validate_nonce_rejects_non_bytes_value() -> None:
    with pytest.raises(TypeError, match="must be bytes"):
        validate_nonce("not-bytes")  # type: ignore[arg-type]


def test_encrypt_text_returns_encrypted_bytes_for_arabic_and_english_text() -> None:
    plaintext = "رسالة سرية: OneSecret 123"
    ciphertext = encrypt_text(plaintext, generate_key(), generate_nonce())

    assert isinstance(ciphertext, bytes)
    assert ciphertext
    assert ciphertext != plaintext.encode("utf-8")


def test_encrypt_text_changes_output_when_nonce_changes() -> None:
    plaintext = "same message"
    key = generate_key()

    first_ciphertext = encrypt_text(plaintext, key, generate_nonce())
    second_ciphertext = encrypt_text(plaintext, key, generate_nonce())

    assert first_ciphertext != second_ciphertext


def test_encrypt_text_rejects_non_string_plaintext() -> None:
    with pytest.raises(TypeError, match="Plaintext must be a string"):
        encrypt_text(b"not-text", generate_key(), generate_nonce())  # type: ignore[arg-type]


def test_encrypt_text_rejects_invalid_key_or_nonce() -> None:
    with pytest.raises(ValueError, match="exactly 32 bytes"):
        encrypt_text("message", b"short", generate_nonce())

    with pytest.raises(ValueError, match="exactly 12 bytes"):
        encrypt_text("message", generate_key(), b"short")


@pytest.mark.parametrize("plaintext", ["رسالة سرية", "OneSecret 123", "عربي + English", ""])
def test_decrypt_text_recovers_the_original_plaintext(plaintext: str) -> None:
    key = generate_key()
    nonce = generate_nonce()
    ciphertext = encrypt_text(plaintext, key, nonce)

    assert decrypt_text(ciphertext, key, nonce) == plaintext


def test_decrypt_text_rejects_a_wrong_key() -> None:
    nonce = generate_nonce()
    ciphertext = encrypt_text("message", generate_key(), nonce)

    with pytest.raises(InvalidTag):
        decrypt_text(ciphertext, generate_key(), nonce)


def test_decrypt_text_rejects_a_wrong_nonce() -> None:
    key = generate_key()
    ciphertext = encrypt_text("message", key, generate_nonce())

    with pytest.raises(InvalidTag):
        decrypt_text(ciphertext, key, generate_nonce())


def test_decrypt_text_rejects_tampered_ciphertext() -> None:
    key = generate_key()
    nonce = generate_nonce()
    ciphertext = encrypt_text("message", key, nonce)
    tampered_ciphertext = ciphertext[:-1] + bytes([ciphertext[-1] ^ 1])

    with pytest.raises(InvalidTag):
        decrypt_text(tampered_ciphertext, key, nonce)


def test_decrypt_text_rejects_non_bytes_ciphertext() -> None:
    with pytest.raises(TypeError, match="Ciphertext must be bytes"):
        decrypt_text("not-bytes", generate_key(), generate_nonce())  # type: ignore[arg-type]


def test_decrypt_text_rejects_validly_encrypted_non_utf8_payload() -> None:
    key = generate_key()
    nonce = generate_nonce()
    ciphertext = AESGCM(key).encrypt(nonce, b"\xff", None)

    with pytest.raises(ValueError, match="not valid UTF-8"):
        decrypt_text(ciphertext, key, nonce)
