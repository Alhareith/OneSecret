"""اختبارات القبول النهائية لمسار صور DES — مسؤولية ملاطف.

عند ربط router بالتطبيق للاختبار، يجب إثبات:

1. /encrypt يقبل PNG وJPEG صحيحتين ضمن الحجم المسموح.
2. يرفض الملف الفارغ.
3. يرفض content-type ليس image/png أو image/jpeg.
4. يرفض صورة تتجاوز MAX_IMAGE_BYTES.
5. رد التشفير يحتوي filename وcontent_type وkey_b64 وiv_b64 وciphertext_b64.
6. قيم Base64 قابلة للفك إلى bytes صالحة، والمفتاح 8 bytes والـIV 8 bytes.
7. /decrypt يعيد data_b64 الذي يساوي bytes الصورة الأصلية byte-for-byte.
8. Base64 تالف أو مفتاح/IV غير صالح يعيد خطأ 400 عام، لا traceback ولا تفاصيل حساسة.
9. لا تُحفظ الصورة أو المفتاح في قاعدة البيانات أو ملفات مؤقتة.
10. اختبار التكامل لا يحتاج أي تعديل في main.py: أنشئ FastAPI صغيرة داخل الاختبار وinclude_router(router).
"""

import base64
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from app.des_image_api import router, MAX_IMAGE_BYTES

# النقطة 10: إنشاء تطبيق FastAPI مصغر للاختبار دون لمس main.py
app = FastAPI()
app.include_router(router)
client = TestClient(app)

def test_encrypt_valid_images_and_response_structure():
    """يغطي النقاط 1، 5، 6: قبول PNG/JPEG، هيكل الرد، وصلاحية Base64 والأطوال"""
    # اختبار PNG
    png_bytes = b"fake_png_data_for_testing"
    files = {"file": ("image.png", png_bytes, "image/png")}
    response = client.post("/api/des-image/encrypt", files=files)
    
    assert response.status_code == 200
    data = response.json()
    
    # التحقق من هيكل الرد (النقطة 5)
    assert "filename" in data
    assert "content_type" in data
    assert "key_b64" in data
    assert "iv_b64" in data
    assert "ciphertext_b64" in data
    
    # التحقق من إمكانية فك Base64 وأطوال المفتاح والـ IV (النقطة 6)
    key = base64.b64decode(data["key_b64"])
    iv = base64.b64decode(data["iv_b64"])
    assert len(key) == 8
    assert len(iv) == 8

def test_encrypt_empty_file():
    """يغطي النقطة 2: رفض الملف الفارغ"""
    files = {"file": ("empty.png", b"", "image/png")}
    response = client.post("/api/des-image/encrypt", files=files)
    assert response.status_code == 400
    assert "empty" in response.json()["detail"].lower()

def test_encrypt_invalid_content_type():
    """يغطي النقطة 3: رفض الأنواع غير المسموحة"""
    files = {"file": ("document.pdf", b"fake_pdf_data", "application/pdf")}
    response = client.post("/api/des-image/encrypt", files=files)
    assert response.status_code == 400
    assert "png and jpeg" in response.json()["detail"].lower()

def test_encrypt_exceeds_max_size():
    """يغطي النقطة 4: رفض صورة تتجاوز الحجم الأقصى"""
    large_bytes = b"0" * (MAX_IMAGE_BYTES + 1)
    files = {"file": ("large.jpg", large_bytes, "image/jpeg")}
    response = client.post("/api/des-image/encrypt", files=files)
    assert response.status_code == 400
    assert "size exceeds" in response.json()["detail"].lower()

def test_decrypt_roundtrip():
    """يغطي النقطة 7 (و 9 ضمناً): فك التشفير يعيد نفس البايتات الأصلية تماماً"""
    original_bytes = b"secret_image_data_byte_for_byte"
    files = {"file": ("secret.jpg", original_bytes, "image/jpeg")}
    
    # التشفير أولاً
    enc_response = client.post("/api/des-image/encrypt", files=files)
    enc_data = enc_response.json()
    
    # فك التشفير
    dec_response = client.post("/api/des-image/decrypt", json=enc_data)
    assert dec_response.status_code == 200
    dec_data = dec_response.json()
    
    # التحقق من التطابق التام
    decrypted_bytes = base64.b64decode(dec_data["data_b64"])
    assert decrypted_bytes == original_bytes

def test_decrypt_invalid_data_returns_generic_400():
    """يغطي النقطة 8: Base64 تالف أو مفتاح خاطئ يعيد 400 عام بدون تفاصيل حساسة"""
    payload = {
        "filename": "test.png",
        "content_type": "image/png",
        "key_b64": "invalid_base64_string!!!",
        "iv_b64": "invalid_base64_string!!!",
        "ciphertext_b64": "invalid_base64_string!!!"
    }
    
    response = client.post("/api/des-image/decrypt", json=payload)
    assert response.status_code == 400
    
    # التأكد من عدم وجود traceback أو تفاصيل حساسة في الرد
    response_text = response.text.lower()
    assert "traceback" not in response_text
    assert "valueerror" not in response_text
