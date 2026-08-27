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


def assert_sensitive_response_headers(response) -> None:
    assert response.headers["Cache-Control"] == "no-store"
    assert response.headers["Pragma"] == "no-cache"
    assert response.headers["Expires"] == "0"
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "no-referrer"
    assert "frame-ancestors 'none'" in response.headers["Content-Security-Policy"]
    assert "web-share=(self)" in response.headers["Permissions-Policy"]


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
    assert_sensitive_response_headers(required)
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
    assert_sensitive_response_headers(response)


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
    assert_sensitive_response_headers(response)


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


def test_create_requests_are_rate_limited_without_reflecting_plaintext(client: TestClient, caplog: pytest.LogCaptureFixture) -> None:
    marker = "CREATE-SECRET-MUST-NOT-APPEAR"
    for number in range(20, 26):
        response = client.post("/api/secrets", json=create_payload(secret_id(number), plaintext=f"{marker}-{number}"))
        assert response.status_code == 201

    blocked = client.post("/api/secrets", json=create_payload(secret_id(26), plaintext=marker))
    assert blocked.status_code == 429
    assert blocked.json() == {"detail": "Too many requests. Try again later."}
    assert int(blocked.headers["Retry-After"]) > 0
    assert marker not in blocked.text
    assert marker not in caplog.text


def test_reveal_requests_are_rate_limited_without_exposing_secret(client: TestClient, caplog: pytest.LogCaptureFixture) -> None:
    identifier = secret_id(27)
    marker = "REVEAL-SECRET-MUST-NOT-APPEAR"
    assert client.post("/api/secrets", json=create_payload(identifier, plaintext=marker)).status_code == 201

    for _ in range(60):
        response = client.post(f"/api/secrets/{identifier}/reveal")
        assert response.status_code == 200

    blocked = client.post(f"/api/secrets/{identifier}/reveal")
    assert blocked.status_code == 429
    assert int(blocked.headers["Retry-After"]) > 0
    assert_sensitive_response_headers(blocked)
    assert marker not in blocked.text
    assert marker not in caplog.text


def test_failed_secret_code_attempts_are_limited_per_secret_without_blocking_valid_use(client: TestClient, caplog: pytest.LogCaptureFixture) -> None:
    protected_id = secret_id(28)
    other_id = secret_id(29)
    code = "correct-secret-code-2026"
    marker = "CODE-MUST-NOT-APPEAR-IN-LOGS"
    assert client.post("/api/secrets", json=create_payload(protected_id, secret_code=code)).status_code == 201
    assert client.post("/api/secrets", json=create_payload(other_id, secret_code=code)).status_code == 201

    for _ in range(5):
        wrong = client.post(f"/api/secrets/{protected_id}/reveal", json={"secret_code": marker})
        assert wrong.status_code == 401

    blocked = client.post(f"/api/secrets/{protected_id}/reveal", json={"secret_code": code})
    assert blocked.status_code == 429
    assert int(blocked.headers["Retry-After"]) > 0
    assert_sensitive_response_headers(blocked)
    assert marker not in caplog.text
    assert code not in caplog.text

    other_secret = client.post(f"/api/secrets/{other_id}/reveal", json={"secret_code": code})
    assert other_secret.status_code == 200


def test_reveal_response_has_no_store_and_browser_protection_headers(client: TestClient) -> None:
    identifier = secret_id(30)
    assert client.post("/api/secrets", json=create_payload(identifier)).status_code == 201

    response = client.post(f"/api/secrets/{identifier}/reveal")
    assert response.status_code == 200
    assert_sensitive_response_headers(response)


def test_create_returns_cancel_code_once_and_stores_only_derived_material(client: TestClient) -> None:
    identifier = secret_id(31)
    response = client.post("/api/secrets", json=create_payload(identifier))

    assert response.status_code == 201
    assert_sensitive_response_headers(response)
    body = response.json()
    cancel_code = body["cancel_code"]
    assert len(cancel_code) == 5
    assert set(cancel_code) <= set("ABCDEFGHJKLMNPQRSTUVWXYZ23456789")
    assert "plaintext" not in body
    assert "secret_code" not in body

    session = app.state.session_factory()
    try:
        secret = session.get(Secret, identifier)
        assert secret is not None
        assert secret.cancel_code_salt
        assert secret.cancel_code_hash
        assert cancel_code not in secret.cancel_code_salt
        assert cancel_code not in secret.cancel_code_hash
    finally:
        session.close()


def test_correct_cancel_code_disables_secret_and_hides_cancelled_state(client: TestClient) -> None:
    identifier = secret_id(32)
    created = client.post("/api/secrets", json=create_payload(identifier, plaintext="CANCELLED-SECRET-MARKER"))
    cancel_code = created.json()["cancel_code"]

    cancelled = client.post(f"/api/secrets/{identifier}/cancel", json={"cancel_code": cancel_code.lower()})
    reveal = client.post(f"/api/secrets/{identifier}/reveal")
    status_response = client.get(f"/api/secrets/{identifier}/status")

    assert cancelled.status_code == 200
    assert cancelled.json() == {"id": identifier, "status": "cancelled"}
    assert_sensitive_response_headers(cancelled)
    assert "CANCELLED-SECRET-MARKER" not in cancelled.text
    assert reveal.status_code == 410
    assert reveal.json() == {"detail": "Secret is unavailable"}
    assert_sensitive_response_headers(reveal)
    assert status_response.json() == {"id": identifier, "status": "missing", "expires_at": None}
    assert_sensitive_response_headers(status_response)

    session = app.state.session_factory()
    try:
        secret = session.get(Secret, identifier)
        assert secret is not None
        assert secret.cancelled_at is not None
        assert secret.ciphertext is None
        assert secret.nonce is None
        assert secret.cancel_code_salt is None
        assert secret.cancel_code_hash is None
    finally:
        session.close()


def test_wrong_cancel_code_is_generic_and_does_not_disable_secret(client: TestClient) -> None:
    identifier = secret_id(33)
    created = client.post("/api/secrets", json=create_payload(identifier, plaintext="available before valid cancellation"))
    valid_code = created.json()["cancel_code"]
    wrong_code = "ZZZZZ"

    wrong = client.post(f"/api/secrets/{identifier}/cancel", json={"cancel_code": wrong_code})
    reveal = client.post(f"/api/secrets/{identifier}/reveal")
    correct = client.post(f"/api/secrets/{identifier}/cancel", json={"cancel_code": valid_code})

    assert wrong.status_code == 410
    assert wrong.json() == {"detail": "Secret is unavailable"}
    assert_sensitive_response_headers(wrong)
    assert wrong_code not in wrong.text
    assert reveal.status_code == 200
    assert reveal.json()["plaintext"] == "available before valid cancellation"
    assert correct.status_code == 200


def test_cancel_rejects_missing_expired_and_invalid_code_without_reflection(client: TestClient) -> None:
    identifier = secret_id(34)
    marker = "ZZZZZ"

    missing = client.post(f"/api/secrets/{identifier}/cancel", json={"cancel_code": marker})
    assert missing.status_code == 410
    assert missing.json() == {"detail": "Secret is unavailable"}
    assert marker not in missing.text

    created = client.post("/api/secrets", json=create_payload(identifier))
    session = app.state.session_factory()
    try:
        secret = session.get(Secret, identifier)
        assert secret is not None
        secret.expires_at = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(seconds=1)
        session.commit()
    finally:
        session.close()

    expired = client.post(f"/api/secrets/{identifier}/cancel", json={"cancel_code": created.json()["cancel_code"]})
    invalid = client.post(f"/api/secrets/{secret_id(35)}/cancel", json={"cancel_code": marker + ("x" * 100)})
    assert expired.status_code == 410
    assert_sensitive_response_headers(expired)
    assert invalid.status_code == 422
    assert invalid.json() == {"detail": "Invalid request"}
    assert marker not in invalid.text


def test_failed_cancel_code_attempts_are_limited_per_secret_without_logging_codes(client: TestClient, caplog: pytest.LogCaptureFixture) -> None:
    protected_id = secret_id(36)
    other_id = secret_id(37)
    marker = "ZZZZZ"
    protected = client.post("/api/secrets", json=create_payload(protected_id))
    other = client.post("/api/secrets", json=create_payload(other_id))

    for _ in range(3):
        wrong = client.post(f"/api/secrets/{protected_id}/cancel", json={"cancel_code": marker})
        assert wrong.status_code == 410

    blocked = client.post(f"/api/secrets/{protected_id}/cancel", json={"cancel_code": protected.json()["cancel_code"]})
    other_cancel = client.post(f"/api/secrets/{other_id}/cancel", json={"cancel_code": other.json()["cancel_code"]})

    assert blocked.status_code == 429
    assert int(blocked.headers["Retry-After"]) > 0
    assert_sensitive_response_headers(blocked)
    assert marker not in caplog.text
    assert protected.json()["cancel_code"] not in caplog.text
    assert other_cancel.status_code == 200


def test_short_cancel_code_global_limit_cannot_be_bypassed_by_another_source(client: TestClient) -> None:
    identifier = secret_id(38)
    created = client.post("/api/secrets", json=create_payload(identifier))
    cancel_code = created.json()["cancel_code"]

    for _ in range(3):
        assert client.post(f"/api/secrets/{identifier}/cancel", json={"cancel_code": "ZZZZZ"}).status_code == 410

    second_source = TestClient(app, client=("198.51.100.37", 50000))
    for _ in range(2):
        assert second_source.post(f"/api/secrets/{identifier}/cancel", json={"cancel_code": "ZZZZZ"}).status_code == 410

    blocked = second_source.post(f"/api/secrets/{identifier}/cancel", json={"cancel_code": cancel_code})
    assert blocked.status_code == 429
    assert int(blocked.headers["Retry-After"]) > 0
    assert_sensitive_response_headers(blocked)
