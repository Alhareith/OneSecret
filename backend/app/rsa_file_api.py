"""مساحة API الخاصة بملفات RSA لأيمن.

تستقبل الملف وبياناته، تستدعي دوال crypto_rsa، ثم تعيد الاستجابة المناسبة.
تبقى جميع مسارات RSA هنا حتى لا يضطر هذا العمل إلى تعديل main.py أثناء التطوير.
"""

from fastapi import APIRouter

router = APIRouter(prefix="/api/rsa-file", tags=["RSA Files"])

# تضاف نقاط النهاية الخاصة برفع الملف وتشفيره وفكّه هنا.
