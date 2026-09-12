"""العقد النهائي لمسار صور DES الخاص بملاطف.

المسؤولية:

- استقبال صورة PNG/JPEG فقط.
- التحقق من النوع والحجم وعدم كون الملف فارغًا.
- قراءة الصورة كـ bytes كما هي دون إعادة ترميزها أو تغيير أبعادها.
- استدعاء crypto_des فقط لتنفيذ التشفير وفك التشفير.
- تحويل القيم الثنائية إلى Base64 عند نقلها داخل JSON فقط.

حدود الملف:

- لا يحتوي تنفيذ DES نفسه.
- لا يستخدم قاعدة البيانات.
- لا يعدل main.py أو schemas.py أو models.py.
- لا يتعامل مع RSA أو الملفات العامة.

العقد الخارجي عند الربط لاحقًا:
POST /api/des-image/encrypt
  input: multipart file باسم file
  output: DesImageEncrypted

POST /api/des-image/decrypt
  input: DesImageDecryptRequest JSON
  output: DesImageDecrypted

الحجم الأقصى المعتمد لهذه الميزة التعليمية: 5 MiB.
"""

import base64
from fastapi import APIRouter, UploadFile, File, HTTPException, status
from pydantic import BaseModel
from app.crypto_des import generate_key, generate_iv, encrypt_bytes, decrypt_bytes

MAX_IMAGE_BYTES = 5 * 1024 * 1024
ALLOWED_IMAGE_TYPES = frozenset({"image/png", "image/jpeg"})

router = APIRouter(prefix="/api/des-image", tags=["DES Images"])


class DesImageEncrypted(BaseModel):
    """الحزمة التي تحتاجها الواجهة لفك الصورة لاحقًا."""

    filename: str
    content_type: str
    key_b64: str
    iv_b64: str
    ciphertext_b64: str


class DesImageDecryptRequest(BaseModel):
    """كل ما يلزم لفك صورة سبق تشفيرها في هذه الصفحة."""

    filename: str
    content_type: str
    key_b64: str
    iv_b64: str
    ciphertext_b64: str


class DesImageDecrypted(BaseModel):
    """الصورة بعد فكها؛ data_b64 يجب أن يمثل bytes الأصلية تمامًا."""

    filename: str
    content_type: str
    data_b64: str


# ملاطف يضيف هنا فقط نقطتي النهاية encrypt وdecrypt حسب العقد أعلاه.

@router.post("/encrypt", response_model=DesImageEncrypted)
async def encrypt_image(file: UploadFile = File(...)):
    """يستقبل صورة، يتحقق منها، يشفرها، ويعيد الحزمة المشفرة بترميز Base64."""
    
    # 1. التحقق من نوع الملف
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PNG and JPEG images are allowed."
        )
    
    # 2. قراءة الملف والتحقق من الحجم والفراغ
    file_bytes = await file.read()
    
    if len(file_bytes) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File is empty."
        )
        
    if len(file_bytes) > MAX_IMAGE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File size exceeds the 5 MiB limit."
        )
        
    # 3. التشفير باستخدام crypto_des
    key = generate_key()
    iv = generate_iv()
    ciphertext = encrypt_bytes(file_bytes, key, iv)
    
    # 4. تحويل القيم الثنائية إلى Base64
    key_b64 = base64.b64encode(key).decode('utf-8')
    iv_b64 = base64.b64encode(iv).decode('utf-8')
    ciphertext_b64 = base64.b64encode(ciphertext).decode('utf-8')
    
    return DesImageEncrypted(
        filename=file.filename or "image",
        content_type=file.content_type,
        key_b64=key_b64,
        iv_b64=iv_b64,
        ciphertext_b64=ciphertext_b64
    )


@router.post("/decrypt", response_model=DesImageDecrypted)
async def decrypt_image(request: DesImageDecryptRequest):
    """يستقبل الحزمة المشفرة، يفك تشفيرها، ويعيد الصورة الأصلية بترميز Base64."""
    
    try:
        # 1. فك ترميز Base64 إلى قيم ثنائية (bytes)
        key = base64.b64decode(request.key_b64)
        iv = base64.b64decode(request.iv_b64)
        ciphertext = base64.b64decode(request.ciphertext_b64)
        
        # 2. فك التشفير باستخدام crypto_des
        plaintext = decrypt_bytes(ciphertext, key, iv)
        
        # 3. تحويل الصورة الأصلية إلى Base64 لإرسالها للواجهة
        data_b64 = base64.b64encode(plaintext).decode('utf-8')
        
        return DesImageDecrypted(
            filename=request.filename,
            content_type=request.content_type,
            data_b64=data_b64
        )
        
    except (ValueError, base64.binascii.Error) as e:
        # التقاط أخطاء فك التشفير (مثل مفتاح خاطئ أو بيانات تالفة) أو أخطاء Base64
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Decryption failed. Invalid key, IV, or corrupted data."
        )
