"""اختبارات القبول النهائية لمسار ملفات RSA — مسؤولية أيمن.

عند ربط router بالتطبيق داخل الاختبار فقط، يجب إثبات:
1. /generate-keypair يعيد public_key_pem وprivate_key_pem صالحين.
2. /encrypt يقبل ملفًا غير فارغ ضمن 5 MiB مع public_key_pem صحيح.
3. /encrypt يرفض image/* حتى تبقى الصور ضمن مهمة DES.
4. /encrypt يرفض الملف الفارغ والملف الأكبر من MAX_FILE_BYTES.
5. رد التشفير يحتوي filename وcontent_type وencrypted_key_b64 وnonce_b64 وciphertext_b64.
6. /decrypt مع المفتاح الخاص المطابق يعيد data_b64 مطابقًا للملف الأصلي byte-for-byte.
7. مفتاح خاص غير مطابق يفشل برد 400 عام.
8. Base64 تالف أو PEM تالف أو ciphertext معدل يفشل برد 400 عام من دون traceback أو تفاصيل حساسة.
9. لا تُحفظ الملفات أو المفتاح الخاص في قاعدة البيانات أو ملفات مؤقتة.
10. اختبار التكامل لا يحتاج تعديل main.py: أنشئ FastAPI صغيرة داخل الاختبار وinclude_router(router).
11. اختبر نوعين على الأقل من الملفات غير الصورية، مثل text/plain وapplication/pdf أو octet-stream.
"""
"""اختبارات HTTP لمسار RSA للملفات، بمعزل تام عن main.py.

نبني تطبيق FastAPI صغير مؤقت داخل هذا الملف فقط ونربط فيه الـ router،
دون أي تعديل على main.py الحقيقي.
"""

import base64

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.rsa_file_api import router


@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


@pytest.fixture
def key_pair_pems(client):
    """يولّد زوج مفاتيح عبر الـ endpoint نفسه، فيستخدم في باقي الاختبارات."""
    response = client.post("/api/rsa-file/generate-keypair")
    assert response.status_code == 200
    body = response.json()
    return body["public_key_pem"], body["private_key_pem"]


# 1. توليد المفاتيح -----------------------------------------------------------


def test_generate_keypair_returns_pem_strings(client):
    response = client.post("/api/rsa-file/generate-keypair")

    assert response.status_code == 200
    body = response.json()
    assert "PRIVATE KEY" in body["private_key_pem"]
    assert "PUBLIC KEY" in body["public_key_pem"]


# 2. ملف text/plain وملف PDF/ثنائي --------------------------------------------


def test_encrypt_decrypt_round_trip_text_file(client, key_pair_pems):
    public_pem, private_pem = key_pair_pems
    original_bytes = "محتوى نصي تجريبي - test content 123".encode("utf-8")

    encrypt_response = client.post(
        "/api/rsa-file/encrypt",
        files={"file": ("note.txt", original_bytes, "text/plain")},
        data={"public_key_pem": public_pem},
    )
    assert encrypt_response.status_code == 200
    encrypted = encrypt_response.json()

    decrypt_response = client.post(
        "/api/rsa-file/decrypt",
        json={
            "filename": encrypted["filename"],
            "content_type": encrypted["content_type"],
            "private_key_pem": private_pem,
            "encrypted_key_b64": encrypted["encrypted_key_b64"],
            "nonce_b64": encrypted["nonce_b64"],
            "ciphertext_b64": encrypted["ciphertext_b64"],
        },
    )
    assert decrypt_response.status_code == 200
    decrypted = decrypt_response.json()

    recovered_bytes = base64.b64decode(decrypted["data_b64"])
    assert recovered_bytes == original_bytes


def test_encrypt_decrypt_round_trip_binary_pdf_like_file(client, key_pair_pems):
    public_pem, private_pem = key_pair_pems
    # محتوى ثنائي عشوائي يحاكي ملف PDF حقيقي (مو نص قابل للقراءة)
    original_bytes = bytes(range(256)) * 100

    encrypt_response = client.post(
        "/api/rsa-file/encrypt",
        files={"file": ("document.pdf", original_bytes, "application/pdf")},
        data={"public_key_pem": public_pem},
    )
    assert encrypt_response.status_code == 200
    encrypted = encrypt_response.json()
    assert encrypted["content_type"] == "application/pdf"

    decrypt_response = client.post(
        "/api/rsa-file/decrypt",
        json={
            "filename": encrypted["filename"],
            "content_type": encrypted["content_type"],
            "private_key_pem": private_pem,
            "encrypted_key_b64": encrypted["encrypted_key_b64"],
            "nonce_b64": encrypted["nonce_b64"],
            "ciphertext_b64": encrypted["ciphertext_b64"],
        },
    )
    assert decrypt_response.status_code == 200
    recovered_bytes = base64.b64decode(decrypt_response.json()["data_b64"])
    assert recovered_bytes == original_bytes


# 3. رفض image/* -------------------------------------------------------------


def test_encrypt_rejects_image_content_type(client, key_pair_pems):
    public_pem, _ = key_pair_pems

    response = client.post(
        "/api/rsa-file/encrypt",
        files={"file": ("photo.png", b"fake png bytes", "image/png")},
        data={"public_key_pem": public_pem},
    )

    assert response.status_code == 400


# 4. رفض الحجم الزايد والفراغ -------------------------------------------------


def test_encrypt_rejects_empty_file(client, key_pair_pems):
    public_pem, _ = key_pair_pems

    response = client.post(
        "/api/rsa-file/encrypt",
        files={"file": ("empty.txt", b"", "text/plain")},
        data={"public_key_pem": public_pem},
    )

    assert response.status_code == 400


def test_encrypt_rejects_file_over_5mib(client, key_pair_pems):
    public_pem, _ = key_pair_pems
    too_large = b"a" * (5 * 1024 * 1024 + 1)

    response = client.post(
        "/api/rsa-file/encrypt",
        files={"file": ("big.bin", too_large, "application/octet-stream")},
        data={"public_key_pem": public_pem},
    )

    assert response.status_code == 400


# 5. صحة الحزمة (نتحقق من الشكل قبل الفك) -------------------------------------


def test_encrypt_response_contains_expected_fields(client, key_pair_pems):
    public_pem, _ = key_pair_pems

    response = client.post(
        "/api/rsa-file/encrypt",
        files={"file": ("note.txt", b"hello", "text/plain")},
        data={"public_key_pem": public_pem},
    )

    body = response.json()
    assert set(body.keys()) == {
        "filename",
        "content_type",
        "encrypted_key_b64",
        "nonce_b64",
        "ciphertext_b64",
    }
    # تأكيد أن القيم فعلاً Base64 صالحة، لا نص خام
    base64.b64decode(body["encrypted_key_b64"])
    base64.b64decode(body["nonce_b64"])
    base64.b64decode(body["ciphertext_b64"])


# 6. فشل PEM/Base64/ciphertext الخاطئ برسالة عامة -----------------------------


def test_encrypt_rejects_invalid_public_key_pem(client):
    response = client.post(
        "/api/rsa-file/encrypt",
        files={"file": ("note.txt", b"hello", "text/plain")},
        data={"public_key_pem": "not a real pem"},
    )

    assert response.status_code == 400


def test_decrypt_rejects_invalid_private_key_pem(client, key_pair_pems):
    public_pem, _ = key_pair_pems

    encrypt_response = client.post(
        "/api/rsa-file/encrypt",
        files={"file": ("note.txt", b"hello", "text/plain")},
        data={"public_key_pem": public_pem},
    )
    encrypted = encrypt_response.json()

    response = client.post(
        "/api/rsa-file/decrypt",
        json={
            "filename": encrypted["filename"],
            "content_type": encrypted["content_type"],
            "private_key_pem": "not a real pem",
            "encrypted_key_b64": encrypted["encrypted_key_b64"],
            "nonce_b64": encrypted["nonce_b64"],
            "ciphertext_b64": encrypted["ciphertext_b64"],
        },
    )

    assert response.status_code == 400


def test_decrypt_rejects_invalid_base64(client, key_pair_pems):
    _, private_pem = key_pair_pems

    response = client.post(
        "/api/rsa-file/decrypt",
        json={
            "filename": "note.txt",
            "content_type": "text/plain",
            "private_key_pem": private_pem,
            "encrypted_key_b64": "not-valid-base64!!!",
            "nonce_b64": "not-valid-base64!!!",
            "ciphertext_b64": "not-valid-base64!!!",
        },
    )

    assert response.status_code == 400


def test_decrypt_rejects_tampered_ciphertext(client, key_pair_pems):
    public_pem, private_pem = key_pair_pems

    encrypt_response = client.post(
        "/api/rsa-file/encrypt",
        files={"file": ("note.txt", b"do not tamper", "text/plain")},
        data={"public_key_pem": public_pem},
    )
    encrypted = encrypt_response.json()

    tampered_ciphertext = bytearray(base64.b64decode(encrypted["ciphertext_b64"]))
    tampered_ciphertext[0] ^= 0xFF
    tampered_b64 = base64.b64encode(bytes(tampered_ciphertext)).decode("ascii")

    response = client.post(
        "/api/rsa-file/decrypt",
        json={
            "filename": encrypted["filename"],
            "content_type": encrypted["content_type"],
            "private_key_pem": private_pem,
            "encrypted_key_b64": encrypted["encrypted_key_b64"],
            "nonce_b64": encrypted["nonce_b64"],
            "ciphertext_b64": tampered_b64,
        },
    )

    assert response.status_code == 400
