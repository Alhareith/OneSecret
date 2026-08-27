import base64

import pytest
from fastapi.testclient import TestClient

from app.main import app


def test_fastapi_environment_is_available() -> None:
    assert app.title == "OneSecret API"


def test_lifespan_configures_runtime_from_complete_environment(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("ONESECRET_DATABASE_URL", f"sqlite:///{tmp_path / 'lifespan.db'}")
    monkeypatch.setenv("ONESECRET_ENCRYPTION_KEY", base64.b64encode(b"l" * 32).decode("ascii"))
    monkeypatch.setenv("ONESECRET_REQUIRE_CONFIGURATION", "true")

    with TestClient(app) as client:
        response = client.get(f"/api/secrets/{'a' * 48}/status")

    assert response.status_code == 200
    assert response.json()["status"] == "missing"


def test_lifespan_fails_closed_when_configuration_is_required(monkeypatch) -> None:
    monkeypatch.setenv("ONESECRET_REQUIRE_CONFIGURATION", "true")
    monkeypatch.delenv("ONESECRET_DATABASE_URL", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("ONESECRET_ENCRYPTION_KEY", raising=False)

    with pytest.raises(RuntimeError, match="database is not configured"):
        with TestClient(app):
            pass


def test_unknown_api_route_does_not_use_the_react_fallback() -> None:
    client = TestClient(app)

    response = client.get("/api/not-a-route")

    assert response.status_code == 404
    assert response.json() == {"detail": "Not Found"}
