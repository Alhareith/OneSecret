"""اختبارات القبول النهائية لـ crypto_des — مسؤولية ملاطف.

يجب أن يضيف ملاطف اختبارات مستقلة تثبت على الأقل:

1. generate_key يعيد bytes بطول 8.
2. مفتاحان مولدان ليسا متطابقين في عينة الاختبار.
3. validate_key يرفض النوع الخاطئ والأطوال غير 8.
4. generate_iv يعيد bytes بطول 8 وقيمًا جديدة.
5. validate_iv يرفض النوع/الطول الخاطئ.
6. encrypt_bytes يعيد bytes غير مساوية للمدخل.
7. encrypt ثم decrypt يعيدان نفس bytes الأصلية، بما فيها بيانات فارغة وبيانات ثنائية.
8. تغيير IV يغيّر ciphertext لنفس plaintext والمفتاح.
9. مفتاح خاطئ أو Padding تالف يؤدي إلى فشل واضح عند فك التشفير.
10. لا تعتمد هذه الاختبارات على FastAPI أو صور حقيقية؛ هذا الملف يختبر التشفير الخام فقط.

قاعدة القبول: لا تُحذف اختبارات AES الحالية ولا تُعدّل لإجبارها على المرور.
"""

import os
import pytest
from app.crypto_des import (
    generate_key,
    validate_key,
    generate_iv,
    validate_iv,
    encrypt_bytes,
    decrypt_bytes
)

def test_generate_key_requirements():
    """يغطي النقطة 1 و 2: طول المفتاح 8، ومفتاحان ليسا متطابقين"""
    key1 = generate_key()
    key2 = generate_key()
    
    assert isinstance(key1, bytes)
    assert len(key1) == 8
    assert key1 != key2

def test_validate_key_failures():
    """يغطي النقطة 3: رفض النوع الخاطئ والأطوال غير 8"""
    with pytest.raises(ValueError):
        validate_key(b"short")  # أقل من 8
    with pytest.raises(ValueError):
        validate_key(b"toolongkey")  # أكثر من 8
    with pytest.raises(ValueError):
        validate_key("string_not_bytes")  # نوع خاطئ

def test_generate_and_validate_iv_requirements():
    """يغطي النقطة 4 و 5: طول IV 8، قيم جديدة، ورفض الخاطئ"""
    iv1 = generate_iv()
    iv2 = generate_iv()
    
    assert isinstance(iv1, bytes)
    assert len(iv1) == 8
    assert iv1 != iv2
    
    with pytest.raises(ValueError):
        validate_iv(b"1234567")
    with pytest.raises(ValueError):
        validate_iv(12345678)

def test_encrypt_decrypt_roundtrip():
    """يغطي النقطة 6 و 7: التشفير يغير البيانات، والفك يعيدها (فارغة وثنائية)"""
    key = generate_key()
    iv = generate_iv()
    
    # بيانات نصية عادية
    plaintext1 = b"Hello OneSecret"
    ciphertext1 = encrypt_bytes(plaintext1, key, iv)
    assert ciphertext1 != plaintext1
    assert decrypt_bytes(ciphertext1, key, iv) == plaintext1
    
    # بيانات فارغة
    plaintext2 = b""
    ciphertext2 = encrypt_bytes(plaintext2, key, iv)
    assert ciphertext2 != plaintext2
    assert decrypt_bytes(ciphertext2, key, iv) == plaintext2
    
    # بيانات ثنائية عشوائية
    plaintext3 = os.urandom(100)
    ciphertext3 = encrypt_bytes(plaintext3, key, iv)
    assert ciphertext3 != plaintext3
    assert decrypt_bytes(ciphertext3, key, iv) == plaintext3

def test_iv_changes_ciphertext():
    """يغطي النقطة 8: تغيير IV يغير ciphertext"""
    key = generate_key()
    iv1 = generate_iv()
    iv2 = generate_iv()
    plaintext = b"Consistent Data"
    
    cipher1 = encrypt_bytes(plaintext, key, iv1)
    cipher2 = encrypt_bytes(plaintext, key, iv2)
    
    assert cipher1 != cipher2

def test_decryption_failures():
    """يغطي النقطة 9: مفتاح خاطئ أو Padding تالف يؤدي لفشل"""
    key = generate_key()
    wrong_key = generate_key()
    iv = generate_iv()
    plaintext = b"Secret Message"
    
    ciphertext = encrypt_bytes(plaintext, key, iv)
    
    # مفتاح خاطئ (سيؤدي غالباً لفشل في فك الـ Padding)
    with pytest.raises(ValueError):
        decrypt_bytes(ciphertext, wrong_key, iv)
        
    # Padding تالف (تغيير آخر بايت في الـ ciphertext)
    corrupted_ciphertext = bytearray(ciphertext)
    corrupted_ciphertext[-1] ^= 0xFF
    with pytest.raises(ValueError):
        decrypt_bytes(bytes(corrupted_ciphertext), key, iv)
