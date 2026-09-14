"""Tests for the educational DES image API and temporary image sharing flow."""

import base64
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.database import Base, build_engine, build_session_factory
from app.des_image_api import DesImageShare, MAX_IMAGE_BYTES, router

app = FastAPI()
app.include_router(router)
client = TestClient(app)


@pytest.fixture()
def share_client(tmp_path: Path):
    engine = build_engine(f"sqlite:///{tmp_path / 'des-share.db'}")
    Base.metadata.create_all(engine)
    factory = build_session_factory(engine)
    share_app = FastAPI()
    share_app.state.session_factory = factory
    share_app.include_router(router)
    with TestClient(share_app) as configured_client:
        yield configured_client, factory


@pytest.mark.parametrize(
    ("filename", "content_type", "image_bytes"),
    [
        ("image.png", "image/png", b"\x89PNG\r\n\x1a\nOneSecret"),
        ("image.jpg", "image/jpeg", b"\xff\xd8\xffOneSecret\xff\xd9"),
    ],
)
def test_encrypt_accepts_png_and_jpeg_and_returns_valid_package(filename, content_type, image_bytes):
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


@pytest.mark.parametrize(
    ("filename", "content_type", "fake_bytes"),
    [
        ("fake.png", "image/png", b"this-is-not-a-png"),
        ("fake.jpg", "image/jpeg", b"this-is-not-a-jpeg"),
    ],
)
def test_encrypt_rejects_spoofed_image_content_type(filename, content_type, fake_bytes):
    response = client.post(
        "/api/des-image/encrypt",
        files={"file": (filename, fake_bytes, content_type)},
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
    assert base64.b64decode(decrypted.json()["data_b64"], validate=True) == original_bytes


@pytest.mark.parametrize("field", ["key_b64", "iv_b64", "ciphertext_b64"])
def test_decrypt_rejects_malformed_base64_strictly(field: str):
    encrypted = client.post(
        "/api/des-image/encrypt",
        files={"file": ("test.png", b"\x89PNG\r\n\x1a\ncontent", "image/png")},
    ).json()
    encrypted[field] = "not-valid-base64!!!"
    response = client.post("/api/des-image/decrypt", json=encrypted)
    assert response.status_code == 400


def test_decrypt_rejects_invalid_mime_type():
    encrypted = client.post(
        "/api/des-image/encrypt",
        files={"file": ("test.png", b"\x89PNG\r\n\x1a\ncontent", "image/png")},
    ).json()
    encrypted["content_type"] = "text/html"
    assert client.post("/api/des-image/decrypt", json=encrypted).status_code == 400


def test_share_creates_link_package_without_storing_key(share_client):
    configured, factory = share_client
    original = b"\x89PNG\r\n\x1a\nshared-image-content"
    created = configured.post(
        "/api/des-image/share",
        files={"file": ("photo.png", original, "image/png")},
        data={"expires_minutes": "15"},
    )
    assert created.status_code == 201
    body = created.json()
    assert body["filename"] == "photo.png"
    assert body["key_fragment"]

    with factory() as session:
        row = session.get(DesImageShare, body["id"])
        assert row is not None
        assert row.ciphertext is not None
        assert row.iv is not None
        assert not hasattr(row, "key")

    info = configured.get(f"/api/des-image/share/{body['id']}")
    assert info.status_code == 200
    assert "ciphertext" not in info.json()
    assert "key" not in info.json()


def test_share_rejects_spoofed_jpeg_before_encryption(share_client):
    configured, _ = share_client
    response = configured.post(
        "/api/des-image/share",
        files={"file": ("fake.jpg", b"plain-text-disguised-as-jpeg", "image/jpeg")},
        data={"expires_minutes": "15"},
    )
    assert response.status_code == 400


def test_share_wrong_key_does_not_consume_then_correct_key_is_one_time(share_client):
    configured, factory = share_client
    original = b"\xff\xd8\xffshared-jpeg-content\xff\xd9"
    created = configured.post(
        "/api/des-image/share",
        files={"file": ("photo.jpg", original, "image/jpeg")},
        data={"expires_minutes": "15"},
    ).json()
    share_id = created["id"]

    wrong_key = base64.urlsafe_b64encode(b"7bytes!").decode("ascii").rstrip("=")
    wrong = configured.post(
        f"/api/des-image/share/{share_id}/reveal",
        json={"key_fragment": wrong_key},
    )
    assert wrong.status_code == 400
    assert configured.get(f"/api/des-image/share/{share_id}").status_code == 200

    revealed = configured.post(
        f"/api/des-image/share/{share_id}/reveal",
        json={"key_fragment": created["key_fragment"]},
    )
    assert revealed.status_code == 200
    assert base64.b64decode(revealed.json()["data_b64"], validate=True) == original
    assert configured.get(f"/api/des-image/share/{share_id}").status_code == 410

    with factory() as session:
        row = session.get(DesImageShare, share_id)
        assert row is not None
        assert row.used_at is not None
        assert row.ciphertext is None
        assert row.iv is None
