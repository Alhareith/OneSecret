"""نقطة تشغيل FastAPI. لا تحتوي هذه المرحلة على مسارات للرسائل."""

import binascii
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


def configure_runtime(*, database_url: str, encryption_key: bytes) -> None:
    """يجهز قاعدة البيانات والمفتاح داخل ذاكرة التطبيق.

    تستدعيه الاختبارات الآن. في مرحلة التشغيل النهائية سنقرأ القيم من البيئة.
    """

    engine = build_engine(database_url)
    Base.metadata.create_all(engine)
    app.state.session_factory = build_session_factory(engine)
    app.state.encryption_key = encryption_key


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


app = FastAPI(title="OneSecret API", version="0.0.1", lifespan=lifespan)


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


@app.get("/api/health", include_in_schema=False)
def health_check(request: Request) -> dict[str, str]:
    """يعيد حالة عامة فقط بعد نجاح تهيئة قاعدة البيانات ومفتاح التشفير."""

    if getattr(request.app.state, "session_factory", None) is None or getattr(request.app.state, "encryption_key", None) is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Service is unavailable")

    return {"status": "ok"}


@app.post("/api/secrets", response_model=CreateSecretResponse, status_code=status.HTTP_201_CREATED)
def create_secret_endpoint(
    payload: CreateSecretRequest,
    session: Session = Depends(get_session),
    encryption_key: bytes = Depends(get_encryption_key),
) -> CreateSecretResponse:
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
    secret_id: SecretIdPath,
    payload: RevealSecretRequest | None = None,
    session: Session = Depends(get_session),
    encryption_key: bytes = Depends(get_encryption_key),
) -> RevealSecretResponse:
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
