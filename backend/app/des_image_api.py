"""HTTP API لمسار صور DES التعليمي.

يقبل PNG/JPEG حتى 5 MiB، يقرأ bytes كما هي دون إعادة ترميز، ويستدعي
``crypto_des`` فقط لتنفيذ DES-CBC. لا يستخدم قاعدة البيانات أو ملفات مؤقتة.
"""

import base64
import binascii

from fastapi import APIRouter, File, HTTPException, UploadFile, status
from pydantic import BaseModel

from app.crypto_des import decrypt_bytes, encrypt_bytes, generate_iv, generate_key

MAX_IMAGE_BYTES = 5 * 1024 * 1024
ALLOWED_IMAGE_TYPES = frozenset({"image/png", "image/jpeg"})

router = APIRouter(prefix="/api/des-image", tags=["DES Images"])


class DesImageEncrypted(BaseModel):
    filename: str
    content_type: str
    key_b64: str
    iv_b64: str
    ciphertext_b64: str


class DesImageDecryptRequest(BaseModel):
    filename: str
    content_type: str
    key_b64: str
    iv_b64: str
    ciphertext_b64: str


class DesImageDecrypted(BaseModel):
    filename: str
    content_type: str
    data_b64: str


def _decode_base64(value: str) -> bytes:
    """يفك Base64 الصارم ويرفض الأحرف أو الـpadding غير الصالح."""
    return base64.b64decode(value, validate=True)


@router.post("/encrypt", response_model=DesImageEncrypted)
async def encrypt_image(file: UploadFile = File(...)) -> DesImageEncrypted:
    """يشفر PNG/JPEG كـbytes باستخدام DES-CBC."""
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PNG and JPEG images are allowed.",
        )

    # نقرأ بايتًا واحدًا فوق الحد فقط حتى لا نحمل ملفًا ضخمًا كاملًا في الذاكرة.
    file_bytes = await file.read(MAX_IMAGE_BYTES + 1)
    if not file_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File is empty.",
        )
    if len(file_bytes) > MAX_IMAGE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File size exceeds the 5 MiB limit.",
        )

    key = generate_key()
    iv = generate_iv()
    ciphertext = encrypt_bytes(file_bytes, key, iv)

    return DesImageEncrypted(
        filename=file.filename or "image",
        content_type=file.content_type,
        key_b64=base64.b64encode(key).decode("ascii"),
        iv_b64=base64.b64encode(iv).decode("ascii"),
        ciphertext_b64=base64.b64encode(ciphertext).decode("ascii"),
    )


@router.post("/decrypt", response_model=DesImageDecrypted)
async def decrypt_image(request: DesImageDecryptRequest) -> DesImageDecrypted:
    """يفك حزمة DES ويعيد bytes الصورة الأصلية بترميز Base64."""
    if request.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Decryption failed. Invalid data.",
        )

    try:
        key = _decode_base64(request.key_b64)
        iv = _decode_base64(request.iv_b64)
        ciphertext = _decode_base64(request.ciphertext_b64)
        plaintext = decrypt_bytes(ciphertext, key, iv)
    except (ValueError, binascii.Error):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Decryption failed. Invalid key, IV, or corrupted data.",
        ) from None

    return DesImageDecrypted(
        filename=request.filename,
        content_type=request.content_type,
        data_b64=base64.b64encode(plaintext).decode("ascii"),
    )
