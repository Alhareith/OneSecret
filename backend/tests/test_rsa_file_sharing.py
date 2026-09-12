import base64
from datetime import timedelta

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.database import Base, build_engine, build_session_factory
from app.models import RsaFileShare
from app.rsa_file_api import router, utc_now


@pytest.fixture
def share_client(tmp_path):
    database_path = tmp_path / "rsa-file-sharing.db"
    engine = build_engine(f"sqlite:///{database_path}")
    Base.metadata.create_all(engine)
    session_factory = build_session_factory(engine)

    app = FastAPI()
    app.state.session_factory = session_factory
    app.include_router(router)

    try:
        yield TestClient(app), session_factory
    finally:
        engine.dispose()


def generate_keys(client: TestClient) -> tuple[str, str]:
    response = client.post("/api/rsa-file/generate-keypair")
    assert response.status_code == 200
    body = response.json()
    return body["public_key_pem"], body["private_key_pem"]


def create_share(client: TestClient, public_key_pem: str, data: bytes = b"shared file content") -> dict:
    response = client.post(
        "/api/rsa-file/share",
        files={"file": ("document.txt", data, "text/plain")},
        data={"public_key_pem": public_key_pem, "expires_minutes": "15"},
    )
    assert response.status_code == 201
    return response.json()


def test_file_share_can_be_received_once_and_encrypted_payload_is_erased(share_client):
    client, session_factory = share_client
    public_key_pem, private_key_pem = generate_keys(client)
    original = b"OneSecret RSA file sharing round trip\x00\x01"

    created = create_share(client, public_key_pem, original)
    share_id = created["id"]

    info_response = client.get(f"/api/rsa-file/share/{share_id}")
    assert info_response.status_code == 200
    assert set(info_response.json()) == {"id", "filename", "content_type", "expires_at"}

    with session_factory() as session:
        stored = session.get(RsaFileShare, share_id)
        assert stored is not None
        assert stored.ciphertext is not None
        assert original not in stored.ciphertext
        assert not hasattr(stored, "private_key_pem")

    reveal_response = client.post(
        f"/api/rsa-file/share/{share_id}/reveal",
        json={"private_key_pem": private_key_pem},
    )
    assert reveal_response.status_code == 200
    assert base64.b64decode(reveal_response.json()["data_b64"]) == original

    assert client.get(f"/api/rsa-file/share/{share_id}").status_code == 410
    assert client.post(
        f"/api/rsa-file/share/{share_id}/reveal",
        json={"private_key_pem": private_key_pem},
    ).status_code == 410

    with session_factory() as session:
        consumed = session.get(RsaFileShare, share_id)
        assert consumed is not None
        assert consumed.used_at is not None
        assert consumed.encrypted_key is None
        assert consumed.nonce is None
        assert consumed.ciphertext is None


def test_wrong_private_key_does_not_consume_share(share_client):
    client, _ = share_client
    public_key_pem, private_key_pem = generate_keys(client)
    _, wrong_private_key_pem = generate_keys(client)
    created = create_share(client, public_key_pem)
    share_id = created["id"]

    wrong_response = client.post(
        f"/api/rsa-file/share/{share_id}/reveal",
        json={"private_key_pem": wrong_private_key_pem},
    )
    assert wrong_response.status_code == 400
    assert client.get(f"/api/rsa-file/share/{share_id}").status_code == 200

    correct_response = client.post(
        f"/api/rsa-file/share/{share_id}/reveal",
        json={"private_key_pem": private_key_pem},
    )
    assert correct_response.status_code == 200


def test_file_share_rejects_images_and_invalid_expiration(share_client):
    client, _ = share_client
    public_key_pem, _ = generate_keys(client)

    image_response = client.post(
        "/api/rsa-file/share",
        files={"file": ("photo.png", b"fake image", "image/png")},
        data={"public_key_pem": public_key_pem, "expires_minutes": "15"},
    )
    assert image_response.status_code == 400

    for invalid_minutes in (0, 1441):
        response = client.post(
            "/api/rsa-file/share",
            files={"file": ("document.txt", b"hello", "text/plain")},
            data={"public_key_pem": public_key_pem, "expires_minutes": str(invalid_minutes)},
        )
        assert response.status_code == 400


def test_expired_share_is_unavailable_and_payload_is_erased(share_client):
    client, session_factory = share_client
    public_key_pem, _ = generate_keys(client)
    created = create_share(client, public_key_pem)
    share_id = created["id"]

    with session_factory() as session:
        stored = session.get(RsaFileShare, share_id)
        assert stored is not None
        stored.expires_at = utc_now() - timedelta(seconds=1)
        session.commit()

    assert client.get(f"/api/rsa-file/share/{share_id}").status_code == 410

    with session_factory() as session:
        expired = session.get(RsaFileShare, share_id)
        assert expired is not None
        assert expired.encrypted_key is None
        assert expired.nonce is None
        assert expired.ciphertext is None
