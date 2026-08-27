from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import inspect

from app.database import Base, build_engine, build_session_factory, normalize_database_url, prepare_database_connection
from app.models import Secret


def test_secret_table_stores_only_encrypted_payload(tmp_path) -> None:
    database_path = tmp_path / "onesecret-test.db"
    engine = build_engine(f"sqlite:///{database_path}")
    Base.metadata.create_all(engine)

    try:
        columns = {column["name"] for column in inspect(engine).get_columns("secrets")}
        indexes = {index["name"] for index in inspect(engine).get_indexes("secrets")}

        assert {"id", "ciphertext", "nonce", "created_at", "expires_at", "used_at"} <= columns
        assert "ix_secrets_expires_at" in indexes
        assert "plaintext" not in columns
        assert "encryption_key" not in columns

        now = datetime.now(timezone.utc)
        session_factory = build_session_factory(engine)

        with session_factory() as session:
            session.add(
                Secret(
                    id="test-secret-id",
                    ciphertext="encrypted-example-payload",
                    nonce="nonce-example",
                    created_at=now,
                    expires_at=now + timedelta(minutes=15),
                    used_at=None,
                )
            )
            session.commit()

            stored_secret = session.get(Secret, "test-secret-id")

        assert stored_secret is not None
        assert stored_secret.ciphertext == "encrypted-example-payload"
        assert stored_secret.used_at is None
    finally:
        engine.dispose()


def test_normalize_database_url_uses_pymysql_for_platform_mysql_urls() -> None:
    source = "mysql://user:password@example.test:3306/onesecret"

    assert normalize_database_url(source) == "mysql+pymysql://user:password@example.test:3306/onesecret"
    assert normalize_database_url("mysql+pymysql://user:password@example.test/onesecret") == (
        "mysql+pymysql://user:password@example.test/onesecret"
    )
    assert normalize_database_url("sqlite:///local.db") == "sqlite:///local.db"

    engine = build_engine(source)
    try:
        assert engine.url.drivername == "mysql+pymysql"
    finally:
        engine.dispose()


def test_prepare_database_connection_moves_platform_ssl_json_to_pymysql_connect_args() -> None:
    source = (
        "mysql://user:password@example.test:3306/onesecret?"
        'ssl={"rejectUnauthorized":true}&charset=utf8mb4'
    )

    prepared_url, connect_args = prepare_database_connection(source)

    assert str(prepared_url).startswith("mysql+pymysql://")
    assert "ssl=" not in str(prepared_url)
    assert "charset=utf8mb4" in str(prepared_url)
    assert connect_args == {"ssl": {"rejectUnauthorized": True}}


def test_prepare_database_connection_rejects_non_json_ssl_configuration() -> None:
    with pytest.raises(ValueError, match="SSL configuration is invalid"):
        prepare_database_connection("mysql://user:password@example.test/onesecret?ssl=required")
