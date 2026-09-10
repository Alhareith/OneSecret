"""اختبارات القبول النهائية لمسار صور DES — مسؤولية ملاطف.

عند ربط router بالتطبيق للاختبار، يجب إثبات:
1. /encrypt يقبل PNG وJPEG صحيحتين ضمن الحجم المسموح.
2. يرفض الملف الفارغ.
3. يرفض content-type ليس image/png أو image/jpeg.
4. يرفض صورة تتجاوز MAX_IMAGE_BYTES.
5. رد التشفير يحتوي filename وcontent_type وkey_b64 وiv_b64 وciphertext_b64.
6. قيم Base64 قابلة للفك إلى bytes صالحة، والمفتاح 8 bytes والـIV 8 bytes.
7. /decrypt يعيد data_b64 الذي يساوي bytes الصورة الأصلية byte-for-byte.
8. Base64 تالف أو مفتاح/IV غير صالح يعيد خطأ 400 عام، لا traceback ولا تفاصيل حساسة.
9. لا تُحفظ الصورة أو المفتاح في قاعدة البيانات أو ملفات مؤقتة.
10. اختبار التكامل لا يحتاج أي تعديل في main.py: أنشئ FastAPI صغيرة داخل الاختبار وinclude_router(router).
"""

# أضف اختبارات API هنا بعد تنفيذ endpoints في app.des_image_api.
