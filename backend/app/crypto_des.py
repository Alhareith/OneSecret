"""عقد منطق DES الخاص بملاطف.

المسؤولية الوحيدة لهذا الملف:
- إنشاء/التحقق من مفتاح DES.
- إنشاء/التحقق من IV.
- تشفير bytes وفكها باستخدام Single DES في وضع CBC مع PKCS#7 padding.

حدود الملف:
- لا يعرف شيئًا عن PNG/JPG أو أسماء الملفات.
- لا يحتوي FastAPI أو Base64 أو واجهة مستخدم.
- لا يستورد أي ملف من مساحة RSA ولا يعدل AES الحالي.

العقد الثابت:
- DES key: 8 bytes.
- IV: 8 bytes جديد لكل عملية تشفير.
- encrypt_bytes: bytes -> bytes مشفرة.
- decrypt_bytes: bytes مشفرة -> نفس bytes الأصلية تمامًا.
"""
"""عقد منطق DES الخاص بملاطف.

المسؤولية الوحيدة لهذا الملف:

- إنشاء/التحقق من مفتاح DES.
- إنشاء/التحقق من IV.
- تشفير bytes وفكها باستخدام Single DES في وضع CBC مع PKCS#7 padding.

حدود الملف:

- لا يعرف شيئًا عن PNG/JPG أو أسماء الملفات.
- لا يحتوي FastAPI أو Base64 أو واجهة مستخدم.
- لا يستورد أي ملف من مساحة RSA ولا يعدل AES الحالي.

العقد الثابت:

- DES key: 8 bytes.
- IV: 8 bytes جديد لكل عملية تشفير.
- encrypt_bytes: bytes -> bytes مشفرة.
- decrypt_bytes: bytes مشفرة -> نفس bytes الأصلية تمامًا.
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
    """يعيد المفتاح بعد التحقق من النوع والطول، ويرفض أي قيمة غير صالحة."""
    if not isinstance(key, bytes) or len(key) != DES_KEY_BYTES:
        raise ValueError(f"Key must be exactly {DES_KEY_BYTES} bytes.")
    return key


def generate_iv() -> bytes:
    """يعيد IV عشوائيًا جديدًا بطول 8 bytes."""
    return os.urandom(DES_IV_BYTES)


def validate_iv(iv: bytes) -> bytes:
    """يعيد IV بعد التحقق من النوع والطول."""
    if not isinstance(iv, bytes) or len(iv) != DES_IV_BYTES:
        raise ValueError(f"IV must be exactly {DES_IV_BYTES} bytes.")
    return iv


def encrypt_bytes(plaintext: bytes, key: bytes, iv: bytes) -> bytes:
    """يشفر bytes باستخدام DES-CBC وPadding صحيح ويعيد ciphertext فقط."""
    valid_key = validate_key(key)
    valid_iv = validate_iv(iv)
    
    cipher = DES.new(valid_key, DES.MODE_CBC, valid_iv)
    padded_data = pad(plaintext, DES.block_size)
    return cipher.encrypt(padded_data)


def decrypt_bytes(ciphertext: bytes, key: bytes, iv: bytes) -> bytes:
    """يفك ciphertext ويزيل Padding ويعيد bytes الأصلية دون تعديل."""
    valid_key = validate_key(key)
    valid_iv = validate_iv(iv)
    
    cipher = DES.new(valid_key, DES.MODE_CBC, valid_iv)
    decrypted_padded_data = cipher.decrypt(ciphertext)
    return unpad(decrypted_padded_data, DES.block_size)
