import base64
import binascii
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

import pytest
from cryptography.exceptions import InvalidTag

from app.crypto import generate_key
from app.database import Base, build_engine, build_session_factory
from app.secrets_service import (
    CANCEL_CODE_ALPHABET,
    CANCEL_CODE_LENGTH,
    DuplicateSecretIdError,
    SecretState,
    cancel_secret,
    create_secret,
    get_secret_state,
    generate_cancel_code,
    reveal_secret,
)


@pytest.fixture
def session(tmp_path):
    engine = build_engine(f"sqlite:///{tmp_path / 'secret-service.db'}")
    Base.metadata.create_all(engine)
    session_factory = build_session_factory(engine)
    session = session_factory()

    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def test_create_secret_stores_only_encrypted_payload_and_is_active(session) -> None:
    now = datetime(2026, 8, 25, 10, 0, 0)
    secret = create_secret(
        session,
        secret_id="secure-secret-identifier-01",
        plaintext="رسالة لا تحفظ كنص واضح",
        expires_at=datetime(2026, 8, 25, 10, 15, tzinfo=timezone.utc),
        encryption_key=generate_key(),
        now=now,
    )

    state, stored_secret = get_secret_state(session, secret.id, now=now)

    assert state == SecretState.ACTIVE
    assert stored_secret is not None
    assert stored_secret.ciphertext != "رسالة لا تحفظ كنص واضح"
    assert stored_secret.nonce
    assert stored_secret.used_at is None
    assert stored_secret.cancelled_at is None
    assert stored_secret.destroy_on_open is False
    assert stored_secret.cancel_code_salt
    assert stored_secret.cancel_code_hash


def test_create_secret_rejects_expiration_in_the_past(session) -> None:
    with pytest.raises(ValueError, match="must be in the future"):
        create_secret(
            session,
            secret_id="expired-secret-identifier-01",
            plaintext="message",
            expires_at=datetime(2026, 8, 25, 9, 59, tzinfo=timezone.utc),
            encryption_key=generate_key(),
            now=datetime(2026, 8, 25, 10, 0, 0),
        )


def test_create_secret_rejects_duplicate_identifier(session) -> None:
    now = datetime(2026, 8, 25, 10, 0, 0)
    values = {
        "secret_id": "duplicate-secret-identifier-01",
        "plaintext": "message",
        "expires_at": (now + timedelta(minutes=10)).replace(tzinfo=timezone.utc),
        "encryption_key": generate_key(),
        "now": now,
    }
    create_secret(session, **values)

    with pytest.raises(DuplicateSecretIdError):
        create_secret(session, **values)


def test_get_secret_state_returns_missing_and_expired(session) -> None:
    now = datetime(2026, 8, 25, 10, 0, 0)
    missing_state, missing_secret = get_secret_state(session, "missing-secret-identifier-01", now=now)
    assert missing_state == SecretState.MISSING
    assert missing_secret is None

    secret = create_secret(
        session,
        secret_id="expiring-secret-identifier-01",
        plaintext="message",
        expires_at=(now + timedelta(minutes=1)).replace(tzinfo=timezone.utc),
        encryption_key=generate_key(),
        now=now,
    )
    expired_state, _ = get_secret_state(session, secret.id, now=now + timedelta(minutes=2))
    assert expired_state == SecretState.EXPIRED


def test_default_secret_can_be_revealed_multiple_times_until_expiry(session) -> None:
    now = datetime(2026, 8, 25, 10, 0, 0)
    key = generate_key()
    secret = create_secret(
        session,
        secret_id="repeatable-secret-identifier-01",
        plaintext="رسالة قابلة للقراءة حتى الانتهاء",
        expires_at=(now + timedelta(minutes=5)).replace(tzinfo=timezone.utc),
        encryption_key=key,
        now=now,
    )

    first = reveal_secret(session, secret.id, encryption_key=key, now=now)
    second = reveal_secret(session, secret.id, encryption_key=key, now=now + timedelta(minutes=2))
    expired = reveal_secret(session, secret.id, encryption_key=key, now=now + timedelta(minutes=6))
    _, stored_secret = get_secret_state(session, secret.id, now=now + timedelta(minutes=2))

    assert first.plaintext == "رسالة قابلة للقراءة حتى الانتهاء"
    assert second.plaintext == "رسالة قابلة للقراءة حتى الانتهاء"
    assert expired.state == SecretState.EXPIRED
    assert stored_secret is not None
    assert stored_secret.used_at is None


def test_destroy_on_open_allows_only_one_successful_reveal(session) -> None:
    now = datetime(2026, 8, 25, 10, 0, 0)
    key = generate_key()
    secret = create_secret(
        session,
        secret_id="destroy-secret-identifier-01",
        plaintext="مرة واحدة عند اختيار المرسل",
        expires_at=(now + timedelta(minutes=5)).replace(tzinfo=timezone.utc),
        encryption_key=key,
        destroy_on_open=True,
        now=now,
    )

    first = reveal_secret(session, secret.id, encryption_key=key, now=now)
    second = reveal_secret(session, secret.id, encryption_key=key, now=now)

    assert first.plaintext == "مرة واحدة عند اختيار المرسل"
    assert second.state == SecretState.USED


def test_secret_code_is_derived_and_required_without_consuming_repeatable_secret(session) -> None:
    now = datetime(2026, 8, 25, 10, 0, 0)
    key = generate_key()
    code = "correct-code-2026"
    secret = create_secret(
        session,
        secret_id="code-secret-identifier-01",
        plaintext="رسالة محمية بكود",
        expires_at=(now + timedelta(minutes=5)).replace(tzinfo=timezone.utc),
        encryption_key=key,
        secret_code=code,
        now=now,
    )

    missing = reveal_secret(session, secret.id, encryption_key=key, now=now)
    wrong = reveal_secret(session, secret.id, encryption_key=key, secret_code="wrong-code-2026", now=now)
    first = reveal_secret(session, secret.id, encryption_key=key, secret_code=code, now=now)
    second = reveal_secret(session, secret.id, encryption_key=key, secret_code=code, now=now + timedelta(minutes=2))
    expired = reveal_secret(session, secret.id, encryption_key=key, secret_code=code, now=now + timedelta(minutes=6))

    assert secret.secret_code_salt
    assert secret.secret_code_hash
    assert code not in secret.secret_code_salt
    assert code not in secret.secret_code_hash
    assert missing.state == SecretState.CODE_REQUIRED
    assert wrong.state == SecretState.CODE_REQUIRED
    assert first.plaintext == "رسالة محمية بكود"
    assert second.plaintext == "رسالة محمية بكود"
    assert expired.state == SecretState.EXPIRED
    assert expired.plaintext is None
    assert secret.used_at is None


def test_generated_cancel_code_uses_five_unambiguous_symbols() -> None:
    cancel_code = generate_cancel_code()

    assert len(cancel_code) == CANCEL_CODE_LENGTH == 5
    assert all(symbol in CANCEL_CODE_ALPHABET for symbol in cancel_code)


def test_cancel_secret_requires_derived_sender_code_and_clears_sensitive_material(session) -> None:
    now = datetime(2026, 8, 25, 10, 0, 0)
    key = generate_key()
    cancel_code = "v1-cancel-code-visible-to-sender-only-2026"
    secret = create_secret(
        session,
        secret_id="cancel-secret-identifier-01",
        plaintext="رسالة يجب ألا تبقى بعد الإلغاء",
        expires_at=(now + timedelta(minutes=5)).replace(tzinfo=timezone.utc),
        encryption_key=key,
        secret_code="secret-code-2026",
        cancel_code=cancel_code,
        now=now,
    )

    result = cancel_secret(session, secret.id, cancel_code=cancel_code, now=now)
    state, stored_secret = get_secret_state(session, secret.id, now=now)

    assert result.cancelled is True
    assert state is SecretState.CANCELLED
    assert stored_secret is not None
    assert stored_secret.cancelled_at == now
    assert stored_secret.ciphertext is None
    assert stored_secret.nonce is None
    assert stored_secret.secret_code_salt is None
    assert stored_secret.secret_code_hash is None
    assert stored_secret.cancel_code_salt is None
    assert stored_secret.cancel_code_hash is None
    assert reveal_secret(session, secret.id, encryption_key=key, now=now).state is SecretState.CANCELLED


def test_cancel_secret_rejects_wrong_code_without_changing_active_secret(session) -> None:
    now = datetime(2026, 8, 25, 10, 0, 0)
    key = generate_key()
    secret = create_secret(
        session,
        secret_id="wrong-cancel-secret-identifier-01",
        plaintext="الرسالة تبقى متاحة قبل الإلغاء الصحيح",
        expires_at=(now + timedelta(minutes=5)).replace(tzinfo=timezone.utc),
        encryption_key=key,
        cancel_code="correct-cancel-code-for-v1-2-2026",
        now=now,
    )

    result = cancel_secret(session, secret.id, cancel_code="wrong-cancel-code-for-v1-2-2026", now=now)
    state, stored_secret = get_secret_state(session, secret.id, now=now)

    assert result.cancelled is False
    assert state is SecretState.ACTIVE
    assert stored_secret is not None
    assert stored_secret.cancelled_at is None
    assert reveal_secret(session, secret.id, encryption_key=key, now=now).plaintext == "الرسالة تبقى متاحة قبل الإلغاء الصحيح"


def test_cancel_secret_allows_only_one_concurrent_success(tmp_path) -> None:
    engine = build_engine(f"sqlite:///{tmp_path / 'concurrent-cancel.db'}")
    Base.metadata.create_all(engine)
    session_factory = build_session_factory(engine)
    key = generate_key()
    now = datetime(2026, 8, 25, 10, 0, 0)
    cancel_code = "concurrent-cancel-code-for-v1-2-2026"

    try:
        with session_factory() as setup_session:
            secret = create_secret(
                setup_session,
                secret_id="concurrent-cancel-identifier-01",
                plaintext="cancel only once",
                expires_at=(now + timedelta(minutes=5)).replace(tzinfo=timezone.utc),
                encryption_key=key,
                cancel_code=cancel_code,
                now=now,
            )
            secret_id = secret.id

        def cancel():
            with session_factory() as worker_session:
                return cancel_secret(worker_session, secret_id, cancel_code=cancel_code, now=now)

        with ThreadPoolExecutor(max_workers=5) as executor:
            results = list(executor.map(lambda _: cancel(), range(5)))

        assert sum(result.cancelled for result in results) == 1
    finally:
        engine.dispose()


def test_reveal_rejects_expired_or_missing_secret(session) -> None:
    now = datetime(2026, 8, 25, 10, 0, 0)
    key = generate_key()
    secret = create_secret(
        session,
        secret_id="expired-reveal-identifier-01",
        plaintext="message",
        expires_at=(now + timedelta(minutes=1)).replace(tzinfo=timezone.utc),
        encryption_key=key,
        now=now,
    )

    assert reveal_secret(session, secret.id, encryption_key=key, now=now + timedelta(minutes=2)).state == SecretState.EXPIRED
    assert reveal_secret(session, "missing-reveal-identifier-01", encryption_key=key, now=now).state == SecretState.MISSING


@pytest.mark.parametrize(
    ("corrupted_field", "corrupted_value"),
    [("ciphertext", "broken"), ("nonce", "broken"), ("ciphertext", None), ("nonce", None)],
)
def test_corrupted_payload_is_invalidated_after_a_failed_reveal(session, corrupted_field: str, corrupted_value: str | None) -> None:
    now = datetime(2026, 8, 25, 10, 0, 0)
    key = generate_key()
    secret = create_secret(
        session,
        secret_id=f"corrupted-{corrupted_field}-identifier-01",
        plaintext="message",
        expires_at=(now + timedelta(minutes=5)).replace(tzinfo=timezone.utc),
        encryption_key=key,
        now=now,
    )
    setattr(secret, corrupted_field, corrupted_value)
    session.commit()

    with pytest.raises((binascii.Error, InvalidTag, ValueError)):
        reveal_secret(session, secret.id, encryption_key=key, now=now)

    state, stored_secret = get_secret_state(session, secret.id, now=now)
    assert state == SecretState.USED
    assert stored_secret is not None
    assert stored_secret.used_at == now


def test_default_secret_allows_concurrent_reveals_until_expiry(tmp_path) -> None:
    engine = build_engine(f"sqlite:///{tmp_path / 'concurrent-repeatable.db'}")
    Base.metadata.create_all(engine)
    session_factory = build_session_factory(engine)
    key = generate_key()
    now = datetime(2026, 8, 25, 10, 0, 0)

    try:
        with session_factory() as setup_session:
            secret = create_secret(
                setup_session,
                secret_id="concurrent-repeatable-identifier-01",
                plaintext="all readers before expiry",
                expires_at=(now + timedelta(minutes=5)).replace(tzinfo=timezone.utc),
                encryption_key=key,
                now=now,
            )
            secret_id = secret.id

        def reveal():
            with session_factory() as worker_session:
                return reveal_secret(worker_session, secret_id, encryption_key=key, now=now)

        with ThreadPoolExecutor(max_workers=5) as executor:
            results = list(executor.map(lambda _: reveal(), range(5)))

        assert [result.plaintext for result in results] == ["all readers before expiry"] * 5
    finally:
        engine.dispose()


def test_destroy_on_open_allows_only_one_concurrent_reveal(tmp_path) -> None:
    engine = build_engine(f"sqlite:///{tmp_path / 'concurrent-destroy.db'}")
    Base.metadata.create_all(engine)
    session_factory = build_session_factory(engine)
    key = generate_key()
    now = datetime(2026, 8, 25, 10, 0, 0)

    try:
        with session_factory() as setup_session:
            secret = create_secret(
                setup_session,
                secret_id="concurrent-destroy-identifier-01",
                plaintext="one reader only",
                expires_at=(now + timedelta(minutes=5)).replace(tzinfo=timezone.utc),
                encryption_key=key,
                destroy_on_open=True,
                now=now,
            )
            secret_id = secret.id

        def reveal():
            with session_factory() as worker_session:
                return reveal_secret(worker_session, secret_id, encryption_key=key, now=now)

        with ThreadPoolExecutor(max_workers=5) as executor:
            results = list(executor.map(lambda _: reveal(), range(5)))

        assert sum(result.plaintext == "one reader only" for result in results) == 1
        assert sum(result.state == SecretState.USED for result in results) == 4
    finally:
        engine.dispose()
