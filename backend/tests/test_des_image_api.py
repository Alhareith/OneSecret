"""اختبارات API صور DES مستقلًا عن التطبيق الرئيسي."""

import base64

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.des_image_api import MAX_IMAGE_BYTES, router

app = FastAPI()
app.include_router(router)
client = TestClient(app)


@pytest.mark.parametrize(
    ("filename", "content_type", "image_bytes"),
    [
        ("image.png", "image/png", b"\x89PNG\r\n\x1a\nOneSecret"),
        ("image.jpg", "image/jpeg", b"\xff\xd8\xffOneSecret\xff\xd9"),
    ],
)
def test_encrypt_accepts_png_and_jpeg_and_returns_valid_package(
    filename: str,
    content_type: str,
    image_bytes: bytes,
):
    response = client.post(
        "/api/des-image/encrypt",
        files={"file": (filename, image_bytes, content_type)},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["filename"] == filename
    assert data["content_type"] == content_type
    assert len(base64.b64decode(data["key_b64"], validate=True)) == 8
    assert len(base64.b64decode(data["iv_b64"], validate=True)) == 8
    assert base64.b64decode(data["ciphertext_b64"], validate=True)


def test_encrypt_rejects_empty_file():
    response = client.post(
        "/api/des-image/encrypt",
        files={"file": ("empty.png", b"", "image/png")},
    )
    assert response.status_code == 400


def test_encrypt_rejects_invalid_content_type():
    response = client.post(
        "/api/des-image/encrypt",
        files={"file": ("document.pdf", b"data", "application/pdf")},
    )
    assert response.status_code == 400


def test_encrypt_rejects_file_over_limit():
    response = client.post(
        "/api/des-image/encrypt",
        files={"file": ("large.jpg", b"0" * (MAX_IMAGE_BYTES + 1), "image/jpeg")},
    )
    assert response.status_code == 400


def test_decrypt_roundtrip_is_byte_for_byte():
    original_bytes = b"\x89PNG\r\n\x1a\nsecret_image_data_byte_for_byte"
    encrypted = client.post(
        "/api/des-image/encrypt",
        files={"file": ("secret.png", original_bytes, "image/png")},
    )
    assert encrypted.status_code == 200

    decrypted = client.post("/api/des-image/decrypt", json=encrypted.json())
    assert decrypted.status_code == 200
    payload = decrypted.json()
    assert payload["filename"] == "secret.png"
    assert payload["content_type"] == "image/png"
    assert base64.b64decode(payload["data_b64"], validate=True) == original_bytes


@pytest.mark.parametrize(
    "field",
    ["key_b64", "iv_b64", "ciphertext_b64"],
)
def test_decrypt_rejects_malformed_base64_strictly(field: str):
    encrypted = client.post(
        "/api/des-image/encrypt",
        files={"file": ("test.png", b"\x89PNG\r\n\x1a\ncontent", "image/png")},
    ).json()
    encrypted[field] = "not-valid-base64!!!"

    response = client.post("/api/des-image/decrypt", json=encrypted)
    assert response.status_code == 400
    response_text = response.text.lower()
    assert "traceback" not in response_text
    assert "valueerror" not in response_text


def test_decrypt_rejects_invalid_mime_type():
    encrypted = client.post(
        "/api/des-image/encrypt",
        files={"file": ("test.png", b"\x89PNG\r\n\x1a\ncontent", "image/png")},
    ).json()
    encrypted["content_type"] = "text/html"

    response = client.post("/api/des-image/decrypt", json=encrypted)
    assert response.status_code == 400
