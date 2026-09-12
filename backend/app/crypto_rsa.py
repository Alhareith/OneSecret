"""عقد منطق RSA الخاص بأيمن.

المسؤولية الوحيدة لهذا الملف:
- توليد زوج مفاتيح RSA.
- تحميل/تسلسل المفاتيح بصيغة PEM.
- تشفير وفك بيانات قصيرة مباشرة بـ RSA-OAEP للتجربة والاختبار.
- تشفير الملفات بطريقة هجينة صحيحة: AES-256-GCM للمحتوى وRSA-OAEP لمفتاح AES.

حدود الملف:
- لا يعرف أسماء الملفات أو MIME type أو FastAPI.
- لا يستخدم قاعدة البيانات.
- لا يتعامل مع DES ولا يعدل AES الحالي.

العقد الثابت:
- RSA key size = 2048 bit على الأقل.
- public exponent = 65537.
- OAEP يستخدم SHA-256 وMGF1(SHA-256).
- مفتاح المحتوى المؤقت = 32 bytes لـ AES-256-GCM.
- nonce للمحتوى = 12 bytes.
"""

from dataclasses import dataclass
from typing import Any

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import hashes

import os
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.exceptions import InvalidTag

RSA_KEY_SIZE = 2048
RSA_PUBLIC_EXPONENT = 65537
CONTENT_KEY_BYTES = 32
CONTENT_NONCE_BYTES = 12


@dataclass(frozen=True)
class RsaFileEnvelope:
    """القيم الثنائية اللازمة لفك ملف مشفر بالطريقة الهجينة."""

    encrypted_key: bytes
    nonce: bytes
    ciphertext: bytes


def generate_key_pair() -> tuple[Any, Any]:
    """يعيد (private_key, public_key)."""
    private_key = rsa.generate_private_key(
        public_exponent=RSA_PUBLIC_EXPONENT,
        key_size=RSA_KEY_SIZE,
    )
    public_key = private_key.public_key()
    return private_key, public_key


def private_key_to_pem(private_key: Any) -> bytes:
    """يعيد المفتاح الخاص PEM غير مشفر للاستخدام التعليمي المحلي فقط."""
    return private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )


def public_key_to_pem(public_key: Any) -> bytes:
    """يعيد المفتاح العام بصيغة PEM."""
    return public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )


def load_private_key(pem: bytes) -> Any:
    """يحمّل PEM ويتأكد أنه مفتاح RSA خاص صالح."""
    private_key = serialization.load_pem_private_key(pem, password=None)
    if not isinstance(private_key, rsa.RSAPrivateKey):
        raise ValueError("PEM does not contain an RSA private key")
    return private_key


def load_public_key(pem: bytes) -> Any:
    """يحمّل PEM ويتأكد أنه مفتاح RSA عام صالح."""
    public_key = serialization.load_pem_public_key(pem)
    if not isinstance(public_key, rsa.RSAPublicKey):
        raise ValueError("PEM does not contain an RSA public key")
    return public_key


def encrypt_small_data(plaintext: bytes, public_key: Any) -> bytes:
    """يشفر bytes قصيرة مباشرة باستخدام RSA-OAEP/SHA-256."""
    return public_key.encrypt(
        plaintext,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None,
        ),
    )


def decrypt_small_data(ciphertext: bytes, private_key: Any) -> bytes:
    """يفك بيانات قصيرة سبق تشفيرها مباشرة بـ RSA-OAEP."""
    return private_key.decrypt(
        ciphertext,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None,
        ),
    )


def encrypt_file_bytes(plaintext: bytes, public_key: Any) -> RsaFileEnvelope:
    """يشفر المحتوى بـ AES-GCM ويغلف مفتاح AES بالمفتاح العام RSA."""
    content_key = os.urandom(CONTENT_KEY_BYTES)
    nonce = os.urandom(CONTENT_NONCE_BYTES)

    aesgcm = AESGCM(content_key)
    ciphertext = aesgcm.encrypt(nonce, plaintext, None)

    encrypted_key = encrypt_small_data(content_key, public_key)

    return RsaFileEnvelope(
        encrypted_key=encrypted_key,
        nonce=nonce,
        ciphertext=ciphertext,
    )


def decrypt_file_bytes(envelope: RsaFileEnvelope, private_key: Any) -> bytes:
    """يفك مفتاح المحتوى بـ RSA ثم يعيد bytes الملف الأصلية عبر AES-GCM."""
    content_key = decrypt_small_data(envelope.encrypted_key, private_key)

    aesgcm = AESGCM(content_key)
    try:
        return aesgcm.decrypt(envelope.nonce, envelope.ciphertext, None)
    except InvalidTag as exc:
        raise ValueError("AES-GCM authentication failed: ciphertext or key mismatch") from exc
