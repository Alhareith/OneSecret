"""Client-side crypto API aggregator.

The browser encrypts text/files before any payload reaches the server. This module
only combines the storage APIs; it never receives a plaintext content field or a
decryption key.
"""

from fastapi import APIRouter

from app.client_crypto_core import ClientFileShare, ClientTextShare
from app.client_crypto_file_api import router as file_router
from app.client_crypto_text_api import router as text_router

router = APIRouter(prefix="/api/client-crypto", tags=["Client-side Crypto"])
router.include_router(text_router)
router.include_router(file_router)

__all__ = ["ClientFileShare", "ClientTextShare", "router"]
