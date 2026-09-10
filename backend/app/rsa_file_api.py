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

from fastapi import APIRouter
from pydantic import BaseModel

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


# أيمن يضيف هنا فقط endpoints الثلاثة حسب العقد أعلاه.
