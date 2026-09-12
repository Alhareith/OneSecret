"""منطق DES التعليمي الخاص بمسار الصور.

- Single DES في وضع CBC.
- مفتاح DES بطول 8 bytes.
- IV عشوائي بطول 8 bytes لكل عملية تشفير.
- PKCS#7 padding.
- هذا الملف يتعامل مع bytes فقط ولا يعرف شيئًا عن HTTP أو الصور أو Base64.
"""

import os

from Crypto.Cipher import DES
from Crypto.Util.Padding import pad, unpad

DES_KEY_BYTES = 8
DES_IV_BYTES = 8


def generate_key() -> bytes:
    """يعيد مفتاح DES عشوائيًا بطول 8 bytes."""
    return os.urandom(DES_KEY_BYTES)


def validate_key(key: bytes) -> bytes:
    """يتحقق من أن المفتاح bytes بطول 8 بالضبط."""
    if not isinstance(key, bytes) or len(key) != DES_KEY_BYTES:
        raise ValueError(f"Key must be exactly {DES_KEY_BYTES} bytes.")
    return key


def generate_iv() -> bytes:
    """يعيد IV عشوائيًا جديدًا بطول 8 bytes."""
    return os.urandom(DES_IV_BYTES)


def validate_iv(iv: bytes) -> bytes:
    """يتحقق من أن IV عبارة عن bytes بطول 8 بالضبط."""
    if not isinstance(iv, bytes) or len(iv) != DES_IV_BYTES:
        raise ValueError(f"IV must be exactly {DES_IV_BYTES} bytes.")
    return iv


def encrypt_bytes(plaintext: bytes, key: bytes, iv: bytes) -> bytes:
    """يشفر bytes باستخدام DES-CBC ويعيد ciphertext فقط."""
    valid_key = validate_key(key)
    valid_iv = validate_iv(iv)
    cipher = DES.new(valid_key, DES.MODE_CBC, valid_iv)
    return cipher.encrypt(pad(plaintext, DES.block_size))


def decrypt_bytes(ciphertext: bytes, key: bytes, iv: bytes) -> bytes:
    """يفك DES-CBC ويزيل PKCS#7 padding ويعيد bytes الأصلية."""
    valid_key = validate_key(key)
    valid_iv = validate_iv(iv)
    cipher = DES.new(valid_key, DES.MODE_CBC, valid_iv)
    return unpad(cipher.decrypt(ciphertext), DES.block_size)
