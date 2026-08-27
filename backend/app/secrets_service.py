"""دورة حياة السر: إنشاء السجل وفحص حالته ثم كشفه بصورة ذرية لاحقًا."""

import base64
from datetime import datetime, timezone
from dataclasses import dataclass
from enum import StrEnum
import secrets

from sqlalchemy import and_, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.crypto import decrypt_text, encrypt_text, generate_nonce
from app.models import Secret
from app.secret_code import create_secret_code_material, verify_secret_code


class SecretState(StrEnum):
    ACTIVE = "active"
    USED = "used"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
    MISSING = "missing"
    CODE_REQUIRED = "code_required"


class DuplicateSecretIdError(ValueError):
    """يشير إلى محاولة إعادة استخدام معرّف رابط موجود مسبقًا."""


@dataclass(frozen=True)
class RevealResult:
    """نتيجة محاولة Reveal؛ النص يظهر فقط في الحالة النشطة الناجحة."""

    state: SecretState
    plaintext: str | None = None


@dataclass(frozen=True)
class CancelResult:
    """نتيجة داخلية لا تكشف سبب فشل إلغاء الرابط."""

    cancelled: bool


def utc_now() -> datetime:
    """يعيد الوقت الحالي بتوقيت UTC من دون معلومات منطقة لأن SQLite تختبره بهذه الصورة."""

    return datetime.now(timezone.utc).replace(tzinfo=None)


def normalize_utc(value: datetime) -> datetime:
    """يحوّل وقتًا واعيًا بالمنطقة إلى UTC قابل للحفظ والمقارنة."""

    if value.tzinfo is None:
        raise ValueError("Expiration time must include a timezone")

    return value.astimezone(timezone.utc).replace(tzinfo=None)


def generate_cancel_code() -> str:
    """ينشئ رمز إلغاء عشوائيًا عالي العشوائية للمرسل فقط."""

    return secrets.token_urlsafe(32)


def create_secret(
    session: Session,
    *,
    secret_id: str,
    plaintext: str,
    expires_at: datetime,
    encryption_key: bytes,
    destroy_on_open: bool = False,
    secret_code: str | None = None,
    cancel_code: str | None = None,
    now: datetime | None = None,
) -> Secret:
    """يشفّر النص ثم يحفظ ciphertext وnonce فقط في جدول الأسرار."""

    current_time = now or utc_now()
    normalized_expiry = normalize_utc(expires_at)

    if normalized_expiry <= current_time:
        raise ValueError("Expiration time must be in the future")

    nonce = generate_nonce()
    ciphertext = encrypt_text(plaintext, encryption_key, nonce)
    code_salt, code_hash = create_secret_code_material(secret_code) if secret_code else (None, None)
    cancellation_value = cancel_code or generate_cancel_code()
    cancel_salt, cancel_hash = create_secret_code_material(cancellation_value)
    secret = Secret(
        id=secret_id,
        ciphertext=base64.urlsafe_b64encode(ciphertext).decode("ascii"),
        nonce=base64.urlsafe_b64encode(nonce).decode("ascii"),
        created_at=current_time,
        expires_at=normalized_expiry,
        used_at=None,
        cancelled_at=None,
        destroy_on_open=destroy_on_open,
        secret_code_salt=code_salt,
        secret_code_hash=code_hash,
        cancel_code_salt=cancel_salt,
        cancel_code_hash=cancel_hash,
    )

    try:
        session.add(secret)
        session.commit()
    except IntegrityError as error:
        session.rollback()
        raise DuplicateSecretIdError("Secret identifier already exists") from error

    return secret


def get_secret_state(
    session: Session,
    secret_id: str,
    *,
    now: datetime | None = None,
) -> tuple[SecretState, Secret | None]:
    """يعيد حالة عامة للسر، من دون قراءة أو كشف ciphertext للمستخدم."""

    secret = session.get(Secret, secret_id)
    if secret is None:
        return SecretState.MISSING, None

    if secret.cancelled_at is not None:
        return SecretState.CANCELLED, secret

    if secret.used_at is not None:
        return SecretState.USED, secret

    if secret.expires_at <= (now or utc_now()):
        return SecretState.EXPIRED, secret

    return SecretState.ACTIVE, secret


def reveal_secret(
    session: Session,
    secret_id: str,
    *,
    encryption_key: bytes,
    secret_code: str | None = None,
    now: datetime | None = None,
) -> RevealResult:
    """يكشف السر حتى انتهاء الصلاحية، أو يستهلكه ذريًا إذا اختير الإتلاف."""

    current_time = now or utc_now()
    current_state, secret = get_secret_state(session, secret_id, now=current_time)
    if current_state is not SecretState.ACTIVE or secret is None:
        return RevealResult(state=current_state)

    if secret.secret_code_hash is not None:
        if secret_code is None or secret.secret_code_salt is None:
            return RevealResult(state=SecretState.CODE_REQUIRED)
        if not verify_secret_code(secret_code, salt=secret.secret_code_salt, expected_hash=secret.secret_code_hash):
            return RevealResult(state=SecretState.CODE_REQUIRED)

    if secret.destroy_on_open:
        update_result = session.execute(
            update(Secret)
            .where(
                and_(
                    Secret.id == secret_id,
                    Secret.used_at.is_(None),
                    Secret.expires_at > current_time,
                    Secret.destroy_on_open.is_(True),
                )
            )
            .values(used_at=current_time)
        )
        if update_result.rowcount != 1:
            session.rollback()
            state, _ = get_secret_state(session, secret_id, now=current_time)
            return RevealResult(state=state)
        session.commit()

    try:
        if secret.ciphertext is None or secret.nonce is None:
            raise ValueError("Encrypted secret payload is unavailable")
        ciphertext = base64.urlsafe_b64decode(secret.ciphertext.encode("ascii"))
        nonce = base64.urlsafe_b64decode(secret.nonce.encode("ascii"))
        plaintext = decrypt_text(ciphertext, encryption_key, nonce)
    except Exception:
        if not secret.destroy_on_open:
            session.execute(
                update(Secret)
                .where(and_(Secret.id == secret_id, Secret.used_at.is_(None)))
                .values(used_at=current_time)
            )
            session.commit()
        raise

    return RevealResult(state=SecretState.ACTIVE, plaintext=plaintext)


def cancel_secret(
    session: Session,
    secret_id: str,
    *,
    cancel_code: str,
    now: datetime | None = None,
) -> CancelResult:
    """يعطل رابطًا نشطًا ذريًا بعد التحقق من رمز الإلغاء المشتق."""

    current_time = now or utc_now()
    current_state, secret = get_secret_state(session, secret_id, now=current_time)
    if (
        current_state is not SecretState.ACTIVE
        or secret is None
        or secret.cancel_code_salt is None
        or secret.cancel_code_hash is None
    ):
        return CancelResult(cancelled=False)

    if not verify_secret_code(cancel_code, salt=secret.cancel_code_salt, expected_hash=secret.cancel_code_hash):
        return CancelResult(cancelled=False)

    update_result = session.execute(
        update(Secret)
        .where(
            and_(
                Secret.id == secret_id,
                Secret.used_at.is_(None),
                Secret.cancelled_at.is_(None),
                Secret.expires_at > current_time,
            )
        )
        .values(
            cancelled_at=current_time,
            ciphertext=None,
            nonce=None,
            secret_code_salt=None,
            secret_code_hash=None,
            cancel_code_salt=None,
            cancel_code_hash=None,
        )
    )
    if update_result.rowcount != 1:
        session.rollback()
        return CancelResult(cancelled=False)

    session.commit()
    return CancelResult(cancelled=True)
