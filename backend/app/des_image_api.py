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

from fastapi import APIRouter
from pydantic import BaseModel

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
