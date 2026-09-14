import base64
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.client_crypto_api import ClientFileShare, ClientTextShare, router
from app.database import Base, build_engine, build_session_factory
from app.rate_limit import FAILED_CANCEL_CODE_GLOBAL_LIMIT, RequestRateLimiter


@pytest.fixture()
def configured(tmp_path: Path):
    engine = build_engine(f"sqlite:///{tmp_path / 'client-crypto.db'}")
    Base.metadata.create_all(engine)
    factory = build_session_factory(engine)
    app = FastAPI()
    app.state.session_factory = factory
    app.state.rate_limiter = RequestRateLimiter()
    app.include_router(router)
    with TestClient(app) as client:
        yield client, factory


def b64(value: bytes) -> str:
    return base64.b64encode(value).decode("ascii")


def text_payload(*, secret_id="a" * 48, destroy=False, code=None):
    # Looks exactly like AES-GCM output to the storage layer: ciphertext includes 16-byte tag.
    payload = {
        "secret_id": secret_id,
        "ciphertext_b64": b64(os.urandom(64) + os.urandom(16)),
        "nonce_b64": b64(os.urandom(12)),
        "expires_at": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
        "destroy_on_open": destroy,
    }
    if code:
        payload["secret_code"] = code
    return payload


def file_payload(*, token="T" * 43, content_type="application/pdf"):
    return {
        "filename": "report.pdf",
        "content_type": content_type,
        "encrypted_key_b64": b64(os.urandom(256)),
        "nonce_b64": b64(os.urandom(12)),
        "ciphertext_b64": b64(os.urandom(1024) + os.urandom(16)),
        "claim_token": token,
        "expires_minutes": 15,
    }


def test_text_share_stores_only_ciphertext_and_returns_envelope(configured):
    client, factory = configured
    payload = text_payload()
    response = client.post("/api/client-crypto/text", json=payload)
    assert response.status_code == 201
    body = response.json()
    assert body["id"] == "a" * 48
    assert len(body["cancel_code"]) == 5

    with factory() as session:
        row = session.get(ClientTextShare, "a" * 48)
        assert row is not None
        assert row.ciphertext == base64.b64decode(payload["ciphertext_b64"])
        assert row.nonce == base64.b64decode(payload["nonce_b64"])
        assert not hasattr(row, "plaintext")

    revealed = client.post(f"/api/client-crypto/text/{'a'*48}/reveal", json={})
    assert revealed.status_code == 200
    assert revealed.json()["ciphertext_b64"] == payload["ciphertext_b64"]
    assert revealed.json()["nonce_b64"] == payload["nonce_b64"]
    assert "plaintext" not in revealed.json()


def test_text_secret_code_and_destroy_on_open(configured):
    client, _ = configured
    payload = text_payload(secret_id="b" * 48, destroy=True, code="correct-pass")
    assert client.post("/api/client-crypto/text", json=payload).status_code == 201
    assert client.post(f"/api/client-crypto/text/{'b'*48}/reveal", json={}).status_code == 401
    assert client.post(f"/api/client-crypto/text/{'b'*48}/reveal", json={"secret_code": "wrong-pass"}).status_code == 401
    ok = client.post(f"/api/client-crypto/text/{'b'*48}/reveal", json={"secret_code": "correct-pass"})
    assert ok.status_code == 200
    assert client.post(f"/api/client-crypto/text/{'b'*48}/reveal", json={"secret_code": "correct-pass"}).status_code == 410


def test_text_secret_code_failed_attempts_are_rate_limited(configured):
    client, _ = configured
    secret_id = "e" * 48
    payload = text_payload(secret_id=secret_id, code="correct-password")
    assert client.post("/api/client-crypto/text", json=payload).status_code == 201

    for _ in range(5):
        wrong = client.post(
            f"/api/client-crypto/text/{secret_id}/reveal",
            json={"secret_code": "wrong-password"},
        )
        assert wrong.status_code == 401

    blocked = client.post(
        f"/api/client-crypto/text/{secret_id}/reveal",
        json={"secret_code": "correct-password"},
    )
    assert blocked.status_code == 429
    assert int(blocked.headers["Retry-After"]) >= 1


def test_text_cancel_clears_envelope(configured):
    client, factory = configured
    payload = text_payload(secret_id="c" * 48)
    created = client.post("/api/client-crypto/text", json=payload).json()
    cancelled = client.post(
        f"/api/client-crypto/text/{'c'*48}/cancel",
        json={"cancel_code": created["cancel_code"]},
    )
    assert cancelled.status_code == 200
    with factory() as session:
        row = session.get(ClientTextShare, "c" * 48)
        assert row is not None
        assert row.ciphertext is None
        assert row.nonce is None


def test_text_cancel_code_failed_attempts_are_rate_limited_per_source(configured):
    client, _ = configured
    secret_id = "f" * 48
    created = client.post("/api/client-crypto/text", json=text_payload(secret_id=secret_id)).json()
    wrong_code = "AAAAA" if created["cancel_code"] != "AAAAA" else "BBBBB"

    for _ in range(3):
        wrong = client.post(
            f"/api/client-crypto/text/{secret_id}/cancel",
            json={"cancel_code": wrong_code},
        )
        assert wrong.status_code == 410

    blocked = client.post(
        f"/api/client-crypto/text/{secret_id}/cancel",
        json={"cancel_code": created["cancel_code"]},
    )
    assert blocked.status_code == 429
    assert int(blocked.headers["Retry-After"]) >= 1


def test_text_cancel_code_global_bucket_blocks_even_before_source_limit(configured):
    client, _ = configured
    secret_id = "9" * 48
    created = client.post("/api/client-crypto/text", json=text_payload(secret_id=secret_id)).json()
    wrong_code = "CCCCC" if created["cancel_code"] != "CCCCC" else "DDDDD"

    for _ in range(2):
        wrong = client.post(
            f"/api/client-crypto/text/{secret_id}/cancel",
            json={"cancel_code": wrong_code},
        )
        assert wrong.status_code == 410

    limiter = client.app.state.rate_limiter
    for _ in range(3):
        assert limiter.consume(
            scope=f"client-text-cancel-code-global:{secret_id}",
            source="all-sources",
            policy=FAILED_CANCEL_CODE_GLOBAL_LIMIT,
        ) is None

    blocked = client.post(
        f"/api/client-crypto/text/{secret_id}/cancel",
        json={"cancel_code": created["cancel_code"]},
    )
    assert blocked.status_code == 429


def test_text_rejects_bad_nonce(configured):
    client, _ = configured
    payload = text_payload(secret_id="d" * 48)
    payload["nonce_b64"] = b64(b"too-short")
    assert client.post("/api/client-crypto/text", json=payload).status_code == 400


def test_file_share_server_receives_only_encrypted_envelope(configured):
    client, factory = configured
    token = "X" * 43
    payload = file_payload(token=token)
    created = client.post("/api/client-crypto/file", json=payload)
    assert created.status_code == 201
    share_id = created.json()["id"]

    with factory() as session:
        row = session.get(ClientFileShare, share_id)
        assert row is not None
        assert row.ciphertext == base64.b64decode(payload["ciphertext_b64"])
        assert row.encrypted_key == base64.b64decode(payload["encrypted_key_b64"])
        assert not hasattr(row, "private_key")
        assert not hasattr(row, "plaintext")
        assert row.claim_token_hash != token

    info = client.get(f"/api/client-crypto/file/{share_id}")
    assert info.status_code == 200
    assert "ciphertext_b64" not in info.json()

    wrong = client.post(f"/api/client-crypto/file/{share_id}/envelope", json={"claim_token": "Y" * 43})
    assert wrong.status_code == 401

    envelope = client.post(f"/api/client-crypto/file/{share_id}/envelope", json={"claim_token": token})
    assert envelope.status_code == 200
    assert envelope.json()["ciphertext_b64"] == payload["ciphertext_b64"]
    assert envelope.json()["encrypted_key_b64"] == payload["encrypted_key_b64"]
    assert "private_key" not in envelope.json()

    consumed = client.post(f"/api/client-crypto/file/{share_id}/consume", json={"claim_token": token})
    assert consumed.status_code == 200
    assert client.get(f"/api/client-crypto/file/{share_id}").status_code == 410


def test_file_wrong_token_does_not_consume(configured):
    client, _ = configured
    token = "A" * 43
    share_id = client.post("/api/client-crypto/file", json=file_payload(token=token)).json()["id"]
    assert client.post(f"/api/client-crypto/file/{share_id}/consume", json={"claim_token": "B" * 43}).status_code == 401
    assert client.get(f"/api/client-crypto/file/{share_id}").status_code == 200


def test_file_rejects_images_and_invalid_envelope(configured):
    client, _ = configured
    assert client.post("/api/client-crypto/file", json=file_payload(content_type="image/png")).status_code == 400
    payload = file_payload()
    payload["encrypted_key_b64"] = b64(os.urandom(128))
    assert client.post("/api/client-crypto/file", json=payload).status_code == 400
