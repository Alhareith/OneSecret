"""العقد النهائي لمسار ملفات RSA الخاص بأيمن.

المسؤولية:
- توليد زوج مفاتيح RSA للتجربة التعليمية المحلية.
- استقبال ملف عام غير صورة، والتحقق من الحجم وعدم كونه فارغًا.
- تمرير bytes الملف إلى crypto_rsa لتنفيذ التشفير الهجين.
- إعادة/استقبال الحزمة المشفرة بصيغة Base64 داخل JSON.
- فك الحزمة بالمفتاح الخاص وإعادة نفس bytes الأصلية.

حدود الملف:
- لا يحتوي تنفيذ RSA أو AES-GCM نفسه.
- لا يستخدم قاعدة البيانات.
- لا يعدل main.py أو schemas.py أو models.py.
- لا يعالج image/* حتى لا يتداخل مع مهمة DES للصور.

العقد الخارجي عند الربط لاحقًا:
POST /api/rsa-file/generate-keypair
  input: لا شيء
  output: RsaKeyPairResponse

POST /api/rsa-file/encrypt
  input: multipart file باسم file + public_key_pem نص
  output: RsaFileEncrypted

POST /api/rsa-file/decrypt
  input: RsaFileDecryptRequest JSON
  output: RsaFileDecrypted

الحجم الأقصى المعتمد لهذه الميزة التعليمية: 5 MiB.
"""

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

import base64
from app.crypto_rsa import (
    RsaFileEnvelope,
    decrypt_file_bytes,
    encrypt_file_bytes,
    generate_key_pair,
    load_private_key,
    load_public_key,
    private_key_to_pem,
    public_key_to_pem,
)

MAX_FILE_BYTES = 5 * 1024 * 1024

router = APIRouter(prefix="/api/rsa-file", tags=["RSA Files"])


class RsaKeyPairResponse(BaseModel):
    public_key_pem: str
    private_key_pem: str


class RsaFileEncrypted(BaseModel):
    filename: str
    content_type: str
    encrypted_key_b64: str
    nonce_b64: str
    ciphertext_b64: str


class RsaFileDecryptRequest(BaseModel):
    filename: str
    content_type: str
    private_key_pem: str
    encrypted_key_b64: str
    nonce_b64: str
    ciphertext_b64: str


class RsaFileDecrypted(BaseModel):
    filename: str
    content_type: str
    data_b64: str


@router.post("/generate-keypair", response_model=RsaKeyPairResponse)
def generate_keypair() -> RsaKeyPairResponse:
    private_key, public_key = generate_key_pair()

    return RsaKeyPairResponse(
        public_key_pem=public_key_to_pem(public_key).decode("utf-8"),
        private_key_pem=private_key_to_pem(private_key).decode("utf-8"),
    )


@router.post("/encrypt", response_model=RsaFileEncrypted)
async def encrypt_file(
    file: UploadFile = File(...),
    public_key_pem: str = Form(...),
) -> RsaFileEncrypted:
    if file.content_type and file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Image files are not accepted here")

    file_bytes = await file.read()

    if len(file_bytes) == 0:
        raise HTTPException(status_code=400, detail="File is empty")

    if len(file_bytes) > MAX_FILE_BYTES:
        raise HTTPException(status_code=400, detail="File exceeds 5 MiB limit")

    try:
        public_key = load_public_key(public_key_pem.encode("utf-8"))
        envelope = encrypt_file_bytes(file_bytes, public_key)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid public key")

    return RsaFileEncrypted(
        filename=file.filename or "file",
        content_type=file.content_type or "application/octet-stream",
        encrypted_key_b64=base64.b64encode(envelope.encrypted_key).decode("ascii"),
        nonce_b64=base64.b64encode(envelope.nonce).decode("ascii"),
        ciphertext_b64=base64.b64encode(envelope.ciphertext).decode("ascii"),
    )


@router.post("/decrypt", response_model=RsaFileDecrypted)
def decrypt_file(payload: RsaFileDecryptRequest) -> RsaFileDecrypted:
    try:
        private_key = load_private_key(payload.private_key_pem.encode("utf-8"))
        envelope = RsaFileEnvelope(
            encrypted_key=base64.b64decode(payload.encrypted_key_b64),
            nonce=base64.b64decode(payload.nonce_b64),
            ciphertext=base64.b64decode(payload.ciphertext_b64),
        )
        plaintext = decrypt_file_bytes(envelope, private_key)
    except ValueError:
        raise HTTPException(status_code=400, detail="Decryption failed")

    return RsaFileDecrypted(
        filename=payload.filename,
        content_type=payload.content_type,
        data_b64=base64.b64encode(plaintext).decode("ascii"),
    )
