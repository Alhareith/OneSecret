"""اختبارات القبول النهائية لمسار ملفات RSA — مسؤولية أيمن.

عند ربط router بالتطبيق داخل الاختبار فقط، يجب إثبات:
1. /generate-keypair يعيد public_key_pem وprivate_key_pem صالحين.
2. /encrypt يقبل ملفًا غير فارغ ضمن 5 MiB مع public_key_pem صحيح.
3. /encrypt يرفض image/* حتى تبقى الصور ضمن مهمة DES.
4. /encrypt يرفض الملف الفارغ والملف الأكبر من MAX_FILE_BYTES.
5. رد التشفير يحتوي filename وcontent_type وencrypted_key_b64 وnonce_b64 وciphertext_b64.
6. /decrypt مع المفتاح الخاص المطابق يعيد data_b64 مطابقًا للملف الأصلي byte-for-byte.
7. مفتاح خاص غير مطابق يفشل برد 400 عام.
8. Base64 تالف أو PEM تالف أو ciphertext معدل يفشل برد 400 عام من دون traceback أو تفاصيل حساسة.
9. لا تُحفظ الملفات أو المفتاح الخاص في قاعدة البيانات أو ملفات مؤقتة.
10. اختبار التكامل لا يحتاج تعديل main.py: أنشئ FastAPI صغيرة داخل الاختبار وinclude_router(router).
11. اختبر نوعين على الأقل من الملفات غير الصورية، مثل text/plain وapplication/pdf أو octet-stream.
"""

# أضف اختبارات API هنا بعد تنفيذ endpoints في app.rsa_file_api.
