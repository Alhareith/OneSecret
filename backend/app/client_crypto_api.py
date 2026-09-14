"""Aggregate the current OneSecret sharing routers.

Text and general-file payloads are encrypted in the browser before reaching the
server. DES images remain a separate educational backend-side DES-CBC path, so
the server receives the original image bytes for that path before encryption.
"""

from fastapi import APIRouter

from app.client_crypto_core import ClientFileShare, ClientTextShare
from app.client_crypto_file_api import router as file_router
from app.client_crypto_text_api import router as text_router
from app.des_image_api import router as des_image_router

router = APIRouter()
router.include_router(text_router, prefix="/api/client-crypto", tags=["Client-side Crypto"])
router.include_router(file_router, prefix="/api/client-crypto", tags=["Client-side Crypto"])
router.include_router(des_image_router)

__all__ = ["ClientFileShare", "ClientTextShare", "router"]
