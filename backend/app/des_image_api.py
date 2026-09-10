"""مساحة API الخاصة بصور DES لملاطف.

تستقبل الصورة وبياناتها، تستدعي دوال crypto_des، ثم تعيد الاستجابة المناسبة.
تبقى جميع مسارات DES هنا حتى لا يضطر هذا العمل إلى تعديل main.py أثناء التطوير.
"""

from fastapi import APIRouter

router = APIRouter(prefix="/api/des-image", tags=["DES Images"])

# تضاف نقاط النهاية الخاصة برفع الصورة وتشفيرها وفكها هنا.
