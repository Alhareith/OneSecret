import base64

import pytest

from app.config import load_encryption_key
from app.main import app, configure_runtime_from_environment


def test_load_encryption_key_decodes_a_valid_aes_256_base64_value(monkeypatch) -> None:
    expected_key = b"k" * 32
    monkeypatch.setenv("ONESECRET_ENCRYPTION_KEY", base64.b64encode(expected_key).decode("ascii"))

    assert load_encryption_key() == expected_key


def test_load_encryption_key_rejects_missing_value(monkeypatch) -> None:
    monkeypatch.delenv("ONESECRET_ENCRYPTION_KEY", raising=False)

    with pytest.raises(RuntimeError, match="not configured"):
        load_encryption_key()


@pytest.mark.parametrize("invalid_value", ["not-base64", base64.b64encode(b"short").decode("ascii")])
def test_load_encryption_key_rejects_invalid_values(monkeypatch, invalid_value: str) -> None:
    monkeypatch.setenv("ONESECRET_ENCRYPTION_KEY", invalid_value)

    with pytest.raises(RuntimeError, match="key is invalid"):
        load_encryption_key()


def test_fastapi_runtime_uses_the_valid_key_from_environment(monkeypatch, tmp_path) -> None:
    expected_key = b"r" * 32
    monkeypatch.setenv("ONESECRET_DATABASE_URL", f"sqlite:///{tmp_path / 'runtime.db'}")
    monkeypatch.setenv("ONESECRET_ENCRYPTION_KEY", base64.b64encode(expected_key).decode("ascii"))

    configure_runtime_from_environment()

    assert app.state.encryption_key == expected_key


def test_fastapi_runtime_rejects_missing_or_invalid_environment_key(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("ONESECRET_DATABASE_URL", f"sqlite:///{tmp_path / 'runtime-invalid.db'}")
    monkeypatch.delenv("ONESECRET_ENCRYPTION_KEY", raising=False)

    with pytest.raises(RuntimeError, match="not configured"):
        configure_runtime_from_environment()
