from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.crypto import generate_key
from app.main import app, configure_runtime
from app.models import Secret


@pytest.fixture
def client(tmp_path) -> TestClient:
    configure_runtime(
        database_url=f"sqlite:///{tmp_path / 'api-test.db'}",
        encryption_key=generate_key(),
    )
    return TestClient(app)


def create_payload(secret_id: str, plaintext: str = "رسالة من API", **options: object) -> dict[str, object]:
    return {
        "secret_id": secret_id,
        "plaintext": plaintext,
        "expires_at": (datetime.now(timezone.utc) + timedelta(minutes=15)).isoformat(),
        **options,
    }


def secret_id(number: int) -> str:
    return f"{number:048x}"


def test_default_secret_reveals_repeatedly_until_expiry(client: TestClient) -> None:
    identifier = secret_id(1)
    create_response = client.post("/api/secrets", json=create_payload(identifier))
    assert create_response.status_code == 201
    assert create_response.json()["id"] == identifier
    assert "plaintext" not in create_response.json()
    assert "ciphertext" not in create_response.json()

    first = client.post(f"/api/secrets/{identifier}/reveal")
    second = client.post(f"/api/secrets/{identifier}/reveal")
    status_response = client.get(f"/api/secrets/{identifier}/status")

    assert first.json() == {"id": identifier, "plaintext": "رسالة من API"}
    assert second.json() == {"id": identifier, "plaintext": "رسالة من API"}
    assert status_response.json()["status"] == "active"


def test_destroy_on_open_is_explicit_and_consumes_once(client: TestClient) -> None:
    identifier = secret_id(2)
    assert client.post("/api/secrets", json=create_payload(identifier, destroy_on_open=True)).status_code == 201

    assert client.post(f"/api/secrets/{identifier}/reveal").status_code == 200
    second = client.post(f"/api/secrets/{identifier}/reveal")
    assert second.status_code == 410
    assert second.json() == {"detail": "Secret is unavailable"}


def test_secret_code_is_required_without_being_exposed_or_consumed(client: TestClient) -> None:
    identifier = secret_id(3)
    code = "correct-secret-code-2026"
    assert client.post("/api/secrets", json=create_payload(identifier, secret_code=code)).status_code == 201

    required = client.post(f"/api/secrets/{identifier}/reveal")
    wrong = client.post(f"/api/secrets/{identifier}/reveal", json={"secret_code": "wrong-secret-code-2026"})
    correct = client.post(f"/api/secrets/{identifier}/reveal", json={"secret_code": code})
    repeat = client.post(f"/api/secrets/{identifier}/reveal", json={"secret_code": code})

    assert required.status_code == 401
    assert wrong.status_code == 401
    assert required.json() == {"detail": "Secret code is required or invalid"}
    assert code not in required.text
    assert correct.status_code == 200
    assert repeat.status_code == 200

    session = app.state.session_factory()
    try:
        secret = session.get(Secret, identifier)
        assert secret is not None
        assert code not in secret.secret_code_hash
        assert code not in secret.secret_code_salt
        assert secret.used_at is None
    finally:
        session.close()


def test_status_for_missing_secret_does_not_reveal_sensitive_data(client: TestClient) -> None:
    response = client.get(f"/api/secrets/{secret_id(4)}/status")
    assert response.status_code == 200
    assert response.json()["status"] == "missing"
    assert "ciphertext" not in response.json()
    assert "plaintext" not in response.json()


def test_create_endpoint_rejects_invalid_input_and_expired_time(client: TestClient) -> None:
    assert client.post("/api/secrets", json=create_payload(secret_id(5), plaintext="")).status_code == 422
    expired_response = client.post(
        "/api/secrets",
        json={
            "secret_id": secret_id(6),
            "plaintext": "message",
            "expires_at": (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat(),
        },
    )
    assert expired_response.status_code == 400
    assert expired_response.json()["detail"] == "Secret cannot be created"


def test_validation_errors_do_not_reflect_plaintext_or_secret_code(client: TestClient) -> None:
    marker = "SENSITIVE-MARKER-DO-NOT-ECHO"
    response = client.post(
        "/api/secrets",
        json=create_payload(secret_id(7), plaintext=marker + ("x" * 10_000), secret_code="code-" + marker),
    )
    assert response.status_code == 422
    assert response.json() == {"detail": "Invalid request"}
    assert marker not in response.text
    assert '"input"' not in response.text


def test_api_rejects_invalid_identifier_and_expiry_format(client: TestClient) -> None:
    assert client.post("/api/secrets", json=create_payload("invalid-identifier")).status_code == 422
    assert client.get("/api/secrets/invalid-identifier/status").status_code == 422
    assert client.post(
        "/api/secrets",
        json={"secret_id": secret_id(8), "plaintext": "message", "expires_at": (datetime.now() + timedelta(minutes=15)).isoformat()},
    ).status_code == 422


@pytest.mark.parametrize("corrupted_field", ["ciphertext", "nonce"])
def test_corrupted_payload_returns_generic_error_and_is_invalidated(client: TestClient, corrupted_field: str) -> None:
    identifier = secret_id(9 if corrupted_field == "ciphertext" else 10)
    assert client.post("/api/secrets", json=create_payload(identifier)).status_code == 201
    session = app.state.session_factory()
    try:
        secret = session.get(Secret, identifier)
        assert secret is not None
        setattr(secret, corrupted_field, "broken")
        session.commit()
    finally:
        session.close()

    response = client.post(f"/api/secrets/{identifier}/reveal")
    assert response.status_code == 410
    assert response.json() == {"detail": "Secret is unavailable"}
    assert client.get(f"/api/secrets/{identifier}/status").json()["status"] == "used"


def test_expired_secret_cannot_be_revealed_after_expiry(client: TestClient) -> None:
    identifier = secret_id(11)
    assert client.post("/api/secrets", json=create_payload(identifier)).status_code == 201
    session = app.state.session_factory()
    try:
        secret = session.get(Secret, identifier)
        assert secret is not None
        secret.expires_at = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(seconds=1)
        session.commit()
    finally:
        session.close()

    response = client.post(f"/api/secrets/{identifier}/reveal")
    assert response.status_code == 410
    assert response.json() == {"detail": "Secret is unavailable"}


def test_concurrent_default_reveals_succeed_before_expiry(client: TestClient) -> None:
    identifier = secret_id(12)
    assert client.post("/api/secrets", json=create_payload(identifier, plaintext="shared before expiry")).status_code == 201

    with ThreadPoolExecutor(max_workers=5) as executor:
        responses = list(executor.map(lambda _: client.post(f"/api/secrets/{identifier}/reveal"), range(5)))

    assert [response.status_code for response in responses].count(200) == 5


def test_concurrent_destroy_on_open_allows_one_reveal(client: TestClient) -> None:
    identifier = secret_id(13)
    assert client.post("/api/secrets", json=create_payload(identifier, destroy_on_open=True)).status_code == 201

    with ThreadPoolExecutor(max_workers=5) as executor:
        responses = list(executor.map(lambda _: client.post(f"/api/secrets/{identifier}/reveal"), range(5)))

    assert [response.status_code for response in responses].count(200) == 1
    assert [response.status_code for response in responses].count(410) == 4
