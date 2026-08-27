"""نقطة تشغيل FastAPI. لا تحتوي هذه المرحلة على مسارات للرسائل."""

import binascii
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path as FilePath
from typing import Annotated

from cryptography.exceptions import InvalidTag
from fastapi import Depends, FastAPI, HTTPException, Path, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings, load_encryption_key
from app.database import Base, build_engine, build_session_factory
from app.rate_limit import CREATE_SECRET_LIMIT, FAILED_CODE_LIMIT, REVEAL_LIMIT, RequestRateLimiter, RateLimit
from app.schemas import (
    CreateSecretRequest,
    CreateSecretResponse,
    RevealSecretRequest,
    RevealSecretResponse,
    SECRET_ID_PATTERN,
    SecretStatusResponse,
)
from app.secrets_service import (
    DuplicateSecretIdError,
    SecretState,
    create_secret,
    get_secret_state,
    reveal_secret,
)

SecretIdPath = Annotated[
    str,
    Path(min_length=48, max_length=48, pattern=SECRET_ID_PATTERN),
]
PROJECT_ROOT = FilePath(__file__).resolve().parents[2]
FRONTEND_DIST_DIR = PROJECT_ROOT / "frontend" / "dist"
SECURITY_LOGGER = logging.getLogger("onesecret.security")


def configure_runtime(*, database_url: str, encryption_key: bytes) -> None:
    """يجهز قاعدة البيانات والمفتاح داخل ذاكرة التطبيق.

    تستدعيه الاختبارات الآن. في مرحلة التشغيل النهائية سنقرأ القيم من البيئة.
    """

    engine = build_engine(database_url)
    Base.metadata.create_all(engine)
    app.state.session_factory = build_session_factory(engine)
    app.state.encryption_key = encryption_key
    app.state.rate_limiter = RequestRateLimiter()


def configure_runtime_from_environment() -> None:
    """يهيئ FastAPI من إعدادات البيئة في التشغيل الفعلي من دون كشف المفتاح."""

    settings = get_settings()
    if not settings.database_url:
        raise RuntimeError("OneSecret database is not configured")

    configure_runtime(
        database_url=settings.database_url,
        encryption_key=load_encryption_key(),
    )


@asynccontextmanager
async def lifespan(_: FastAPI):
    """يهيئ الإنتاج من البيئة، ويترك الاختبارات تضبط التطبيق يدويًا."""

    settings = get_settings()
    requires_configuration = os.getenv("ONESECRET_REQUIRE_CONFIGURATION") == "true"
    if requires_configuration or settings.database_url:
        configure_runtime_from_environment()
    yield


app = FastAPI(title="OneSecret API", version="1.1.0", lifespan=lifespan)


@app.middleware("http")
async def apply_security_headers(request: Request, call_next):
    """يضيف رؤوس متصفح آمنة من دون حجب Web Share على الهاتف."""

    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    response.headers.setdefault("Content-Security-Policy", "frame-ancestors 'none'; base-uri 'self'")
    response.headers.setdefault("Permissions-Policy", "camera=(), geolocation=(), microphone=(), payment=(), usb=(), web-share=(self)")

    path = request.url.path
    if path.startswith("/api/secrets/") or path.startswith("/s/"):
        response.headers["Cache-Control"] = "no-store"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"

    return response


@app.exception_handler(RequestValidationError)
async def validation_error_response(_: Request, __: RequestValidationError) -> JSONResponse:
    """لا يعيد تفاصيل Pydantic لأن `input` قد يحتوي النص السري المرفوض."""

    return JSONResponse(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, content={"detail": "Invalid request"})

if FRONTEND_DIST_DIR.exists():
    frontend_assets_dir = FRONTEND_DIST_DIR / "assets"
    if frontend_assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=frontend_assets_dir), name="frontend-assets")


def get_session(request: Request):
    session_factory: sessionmaker[Session] | None = getattr(request.app.state, "session_factory", None)
    if session_factory is None:
        raise RuntimeError("OneSecret API is not configured")

    session = session_factory()
    try:
        yield session
    finally:
        session.close()


def get_encryption_key(request: Request) -> bytes:
    encryption_key: bytes | None = getattr(request.app.state, "encryption_key", None)
    if encryption_key is None:
        raise RuntimeError("OneSecret API is not configured")

    return encryption_key


def get_client_source(request: Request) -> str:
    """يعيد مصدر الاتصال كما يراه الخادم، من دون الثقة برؤوس عميل قابلة للتزوير."""

    return request.client.host if request.client is not None else "unknown"


def get_rate_limiter(request: Request) -> RequestRateLimiter:
    limiter: RequestRateLimiter | None = getattr(request.app.state, "rate_limiter", None)
    if limiter is None:
        raise RuntimeError("OneSecret API is not configured")

    return limiter


def reject_when_rate_limited(
    request: Request,
    *,
    scope: str,
    policy: RateLimit,
    consume: bool,
) -> None:
    """يفرض حدًا ويرسل سجلًا مجردًا من أي بيانات سرية عند الحجب."""

    limiter = get_rate_limiter(request)
    source = get_client_source(request)
    retry_after = (
        limiter.consume(scope=scope, source=source, policy=policy)
        if consume
        else limiter.retry_after(scope=scope, source=source, policy=policy)
    )
    if retry_after is None:
        return

    SECURITY_LOGGER.warning("security_event operation=%s outcome=rate_limited", scope.split(":", maxsplit=1)[0])
    raise HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail="Too many requests. Try again later.",
        headers={"Retry-After": str(retry_after)},
    )


@app.get("/api/health", include_in_schema=False)
def health_check(request: Request) -> dict[str, str]:
    """يعيد حالة عامة فقط بعد نجاح تهيئة قاعدة البيانات ومفتاح التشفير."""

    if getattr(request.app.state, "session_factory", None) is None or getattr(request.app.state, "encryption_key", None) is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Service is unavailable")

    return {"status": "ok"}


@app.post("/api/secrets", response_model=CreateSecretResponse, status_code=status.HTTP_201_CREATED)
def create_secret_endpoint(
    request: Request,
    payload: CreateSecretRequest,
    session: Session = Depends(get_session),
    encryption_key: bytes = Depends(get_encryption_key),
) -> CreateSecretResponse:
    reject_when_rate_limited(request, scope="create", policy=CREATE_SECRET_LIMIT, consume=True)
    try:
        secret = create_secret(
            session,
            secret_id=payload.secret_id,
            plaintext=payload.plaintext,
            expires_at=payload.expires_at,
            encryption_key=encryption_key,
            destroy_on_open=payload.destroy_on_open,
            secret_code=payload.secret_code,
        )
    except DuplicateSecretIdError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Secret identifier is unavailable") from error
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Secret cannot be created") from error

    return CreateSecretResponse(id=secret.id, expires_at=secret.expires_at)


@app.get("/api/secrets/{secret_id}/status", response_model=SecretStatusResponse)
def get_secret_status_endpoint(
    secret_id: SecretIdPath,
    session: Session = Depends(get_session),
) -> SecretStatusResponse:
    state, secret = get_secret_state(session, secret_id)
    return SecretStatusResponse(
        id=secret_id,
        status=state,
        expires_at=secret.expires_at if secret else None,
    )


@app.post("/api/secrets/{secret_id}/reveal", response_model=RevealSecretResponse)
def reveal_secret_endpoint(
    request: Request,
    secret_id: SecretIdPath,
    payload: RevealSecretRequest | None = None,
    session: Session = Depends(get_session),
    encryption_key: bytes = Depends(get_encryption_key),
) -> RevealSecretResponse:
    reject_when_rate_limited(request, scope="reveal", policy=REVEAL_LIMIT, consume=True)
    submitted_code = payload.secret_code if payload else None
    if submitted_code is not None:
        reject_when_rate_limited(
            request,
            scope=f"secret-code:{secret_id}",
            policy=FAILED_CODE_LIMIT,
            consume=False,
        )

    try:
        result = reveal_secret(
            session,
            secret_id,
            encryption_key=encryption_key,
            secret_code=payload.secret_code if payload else None,
        )
    except (InvalidTag, UnicodeDecodeError, ValueError, binascii.Error) as error:
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="Secret is unavailable") from error

    if result.state is SecretState.CODE_REQUIRED:
        if submitted_code is not None:
            reject_when_rate_limited(
                request,
                scope=f"secret-code:{secret_id}",
                policy=FAILED_CODE_LIMIT,
                consume=True,
            )
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Secret code is required or invalid")

    if result.state is not SecretState.ACTIVE or result.plaintext is None:
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="Secret is unavailable")

    return RevealSecretResponse(id=secret_id, plaintext=result.plaintext)


if FRONTEND_DIST_DIR.exists():
    @app.get("/{client_path:path}", include_in_schema=False)
    def serve_frontend(client_path: str) -> FileResponse:
        """يعيد React نفسه لمسارات SPA، مثل /s/{id}، بعد إتمام مسارات API."""

        if client_path == "api" or client_path.startswith("api/"):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not Found")

        return FileResponse(FRONTEND_DIST_DIR / "index.html")
