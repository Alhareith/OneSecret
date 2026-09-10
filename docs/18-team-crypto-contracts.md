# عقود العمل المتوازي: DES للصور وRSA للملفات

هذه الوثيقة هي المرجع التنفيذي لمساحتي العمل الجديدتين قبل الدمج في الواجهة الرئيسية. الهدف أن يعمل ملاطف وأيمن في الوقت نفسه من دون تعديل الملفات نفسها أو تغيير AES الحالي.

## 1. قاعدة العمل العامة

- AES الحالي يبقى كما هو في `backend/app/crypto.py` ومسار الرسائل الحالي لا يُعدّل أثناء تنفيذ المهمتين.
- ملاطف يعمل فقط على ملفات DES والصور المحددة أدناه.
- أيمن يعمل فقط على ملفات RSA والملفات المحددة أدناه.
- لا تستخدم أي من الميزتين قاعدة البيانات في هذه المرحلة؛ كل المعالجة مؤقتة وفي الذاكرة.
- لا تحفظ الصور أو الملفات أو المفاتيح أو ciphertext في ملفات مؤقتة أو logs أو قاعدة البيانات.
- `main.py` و`App.tsx` ملفات ربط مشتركة، لذلك لا يعدلهما أي من الشخصين أثناء العمل المتوازي.
- الربط النهائي للـrouters والصفحات يتم بعد نجاح المهمتين منفصلتين.

## 2. الملفات المشتركة الجاهزة قبل بدء العمل

تم تجهيز الاعتماديات المشتركة داخل `backend/requirements.txt` مسبقًا:

- `cryptography`: موجودة أصلًا وتستخدمها AES وRSA/AES-GCM.
- `pycryptodome`: لاستخدام Single DES.
- `python-multipart`: لاستقبال `UploadFile/FormData` في FastAPI.

لا يحتاج ملاطف أو أيمن إلى تعديل `requirements.txt` من أجل المهمتين المعتمدتين.

---

# ملاطف — DES للصور

## 3. `backend/app/crypto_des.py`

### دوره
منطق DES الخام فقط. لا يعرف أن البيانات صورة.

### يدخل إليه
- `plaintext: bytes`
- `key: bytes` بطول 8
- `iv: bytes` بطول 8

### يخرج منه
- `encrypt_bytes` -> `ciphertext: bytes`
- `decrypt_bytes` -> نفس `plaintext: bytes` الأصلية تمامًا

### الدوال المعتمدة
- `generate_key() -> bytes`
- `validate_key(key: bytes) -> bytes`
- `generate_iv() -> bytes`
- `validate_iv(iv: bytes) -> bytes`
- `encrypt_bytes(plaintext: bytes, key: bytes, iv: bytes) -> bytes`
- `decrypt_bytes(ciphertext: bytes, key: bytes, iv: bytes) -> bytes`

### القرار التقني
- Single DES.
- CBC mode.
- PKCS#7 padding.
- مفتاح 8 bytes.
- IV جديد 8 bytes لكل تشفير.

### ممنوع داخل الملف
FastAPI، Base64، أسماء الصور، MIME types، React، قاعدة البيانات، RSA.

## 4. `backend/app/des_image_api.py`

### دوره
تحويل الصورة بين HTTP و`crypto_des` فقط.

### الملفات المقبولة
- `image/png`
- `image/jpeg`
- غير فارغة.
- بحد أقصى 5 MiB.

لا تعاد معالجة الصورة أو تغيير المقاس أو الجودة أو الصيغة؛ تقرأ bytes كما هي.

### Endpoint 1
`POST /api/des-image/encrypt`

**المدخل:** multipart/form-data، حقل `file`.

**المخرج:**
```json
{
  "filename": "photo.png",
  "content_type": "image/png",
  "key_b64": "...",
  "iv_b64": "...",
  "ciphertext_b64": "..."
}
```

### Endpoint 2
`POST /api/des-image/decrypt`

**المدخل:** نفس حقول الحزمة المشفرة السابقة بصيغة JSON.

**المخرج:**
```json
{
  "filename": "photo.png",
  "content_type": "image/png",
  "data_b64": "..."
}
```

`data_b64` بعد فك Base64 يجب أن يساوي bytes الصورة الأصلية byte-for-byte.

### الأخطاء
- ملف غير صالح/فارغ/كبير -> 400 أو 413 برسالة عامة.
- Base64 أو مفتاح أو IV غير صالح -> 400 برسالة عامة.
- لا traceback ولا تفاصيل داخلية في الرد.

## 5. `backend/tests/test_crypto_des.py`

يختبر `crypto_des.py` فقط دون FastAPI أو صور.

المطلوب إثباته: طول المفتاح والـIV، العشوائية، رفض القيم الخاطئة، round-trip للـbytes، اختلاف ciphertext عند تغيير IV، وفشل فك بيانات غير صحيحة.

## 6. `backend/tests/test_des_image_api.py`

يختبر router مستقلًا دون تعديل `main.py`. ينشئ تطبيق FastAPI داخل الاختبار ثم `include_router(router)`.

المطلوب: قبول PNG/JPEG، رفض الأنواع الأخرى والحجم الزائد والملف الفارغ، صحة الحزمة، واسترجاع نفس bytes الصورة.

## 7. `frontend/src/lib/des-image-api.ts`

### دوره
طلبات الشبكة فقط، بلا JSX وبلا منطق DES.

### الأنواع المعتمدة
- `DesImageEncrypted`
- `DesImageDecrypted`

### الدوال المعتمدة
- `encryptDesImage(file: File): Promise<DesImageEncrypted>`
- `decryptDesImage(payload: DesImageEncrypted): Promise<DesImageDecrypted>`

الأولى تستخدم `FormData`; الثانية تستخدم JSON.

## 8. `frontend/src/pages/DesImagePage.tsx`

### دورة الصفحة
1. يختار المستخدم PNG/JPG.
2. تتحقق الواجهة من النوع والحجم.
3. Encrypt -> `encryptDesImage`.
4. تحفظ الحزمة في React state فقط.
5. Decrypt -> `decryptDesImage`.
6. تحول `data_b64` إلى Blob بنفس `content_type`.
7. تعرض أو توفر الصورة المسترجعة باسمها الأصلي.
8. تنظف Object URL عند تغييره أو مغادرة الصفحة.

### ممنوع
- `localStorage` أو `sessionStorage` للمفاتيح أو الحزمة.
- طباعة المفتاح في console.
- تعديل `App.tsx` أو صفحات الرسائل الحالية.

---

# أيمن — RSA للملفات

## 9. `backend/app/crypto_rsa.py`

### دوره
كل المنطق التشفيري الخاص بمهمة RSA، بما فيه التشفير الهجين للملف.

### القرار التقني
- RSA 2048 bit على الأقل.
- public exponent = 65537.
- RSA-OAEP مع SHA-256 وMGF1(SHA-256).
- الملف نفسه لا يشفر مباشرة بـRSA.
- ينشأ مفتاح AES-256 عشوائي للملف.
- AES-GCM nonce = 12 bytes.
- RSA يشفر مفتاح AES فقط.

### الدوال المعتمدة
- `generate_key_pair()`
- `private_key_to_pem(private_key)`
- `public_key_to_pem(public_key)`
- `load_private_key(pem: bytes)`
- `load_public_key(pem: bytes)`
- `encrypt_small_data(plaintext: bytes, public_key)`
- `decrypt_small_data(ciphertext: bytes, private_key)`
- `encrypt_file_bytes(plaintext: bytes, public_key) -> RsaFileEnvelope`
- `decrypt_file_bytes(envelope: RsaFileEnvelope, private_key) -> bytes`

### `RsaFileEnvelope`
يحمل فقط:
- `encrypted_key: bytes`
- `nonce: bytes`
- `ciphertext: bytes`

### ممنوع داخل الملف
FastAPI، أسماء الملفات، MIME types، قاعدة البيانات، React، DES.

## 10. `backend/app/rsa_file_api.py`

### دوره
HTTP والتحقق من الملفات والتحويل Base64/PEM فقط، ثم استدعاء `crypto_rsa`.

### الملفات المقبولة
- أي ملف غير صورة `image/*`.
- غير فارغ.
- بحد أقصى 5 MiB.

الصور محجوزة لمسار ملاطف لتجنب تداخل المسؤوليات.

### Endpoint 1
`POST /api/rsa-file/generate-keypair`

**المخرج:**
```json
{
  "public_key_pem": "...",
  "private_key_pem": "..."
}
```

هذه مفاتيح تجربة تعليمية لا تحفظ في الخادم أو قاعدة البيانات.

### Endpoint 2
`POST /api/rsa-file/encrypt`

**المدخل:** multipart/form-data:
- `file`
- `public_key_pem`

**المخرج:**
```json
{
  "filename": "document.pdf",
  "content_type": "application/pdf",
  "encrypted_key_b64": "...",
  "nonce_b64": "...",
  "ciphertext_b64": "..."
}
```

### Endpoint 3
`POST /api/rsa-file/decrypt`

**المدخل:**
```json
{
  "filename": "document.pdf",
  "content_type": "application/pdf",
  "private_key_pem": "...",
  "encrypted_key_b64": "...",
  "nonce_b64": "...",
  "ciphertext_b64": "..."
}
```

**المخرج:**
```json
{
  "filename": "document.pdf",
  "content_type": "application/pdf",
  "data_b64": "..."
}
```

بعد Base64، `data_b64` يجب أن يعيد bytes الملف الأصلية byte-for-byte.

## 11. `backend/tests/test_crypto_rsa.py`

يختبر منطق RSA والهجين فقط دون FastAPI.

المطلوب: صحة حجم المفتاح و65537، PEM round-trip، RSA مباشر لرسالة قصيرة، رفض مفتاح خاطئ، hybrid round-trip لبيانات نصية وثنائية، اختلاف الحزم مع التشفير المتكرر، وفشل ciphertext معدل.

## 12. `backend/tests/test_rsa_file_api.py`

يختبر router مستقلًا بتطبيق FastAPI صغير داخل الاختبار دون تعديل `main.py`.

المطلوب: توليد المفاتيح، ملف text/plain وملف PDF/ثنائي، رفض image/*، الحجم والفراغ، صحة الحزمة، الاسترجاع byte-for-byte، وفشل PEM/Base64/ciphertext الخاطئ برسالة عامة.

## 13. `frontend/src/lib/rsa-file-api.ts`

### الأنواع المعتمدة
- `RsaKeyPair`
- `RsaFileEncrypted`
- `RsaFileDecrypted`

### الدوال المعتمدة
- `generateRsaKeyPair(): Promise<RsaKeyPair>`
- `encryptRsaFile(file, publicKeyPem): Promise<RsaFileEncrypted>`
- `decryptRsaFile(payload, privateKeyPem): Promise<RsaFileDecrypted>`

## 14. `frontend/src/pages/RsaFilePage.tsx`

### دورة الصفحة
1. Generate Keys -> يحتفظ بالمفتاحين في React state فقط.
2. يختار المستخدم ملفًا غير صورة، بحد أقصى 5 MiB.
3. Encrypt يستخدم المفتاح العام فقط.
4. تحفظ الحزمة المشفرة في state.
5. Decrypt يستخدم المفتاح الخاص والحزمة.
6. `data_b64` يتحول إلى Blob بنفس MIME type.
7. يسمح بتنزيل الملف المسترجع بالاسم الأصلي.
8. تغيير الملف أو توليد مفاتيح جديدة يمسح النتائج القديمة.
9. تنظف Object URLs عند الاستبدال/الخروج.

### ممنوع
- تخزين المفتاح الخاص في localStorage/sessionStorage.
- طباعته في console.
- تعديل `App.tsx` أو صفحات الرسائل الحالية.

---

# 15. الملفات المحجوزة أثناء العمل المتوازي

لا يعدلها ملاطف ولا أيمن ضمن المهمتين:

- `backend/app/crypto.py`
- `backend/app/main.py`
- `backend/app/secrets_service.py`
- `backend/app/schemas.py`
- `backend/app/models.py`
- `backend/app/config.py`
- `frontend/src/App.tsx`
- `frontend/src/lib/api.ts`
- `frontend/src/lib/i18n.ts`
- `frontend/src/pages/CreateSecretPage.tsx`
- `frontend/src/pages/RevealSecretPage.tsx`
- `.github/workflows/quality.yml`
- `backend/requirements.txt` بعد دمج هذه التهيئة

إذا ظهرت حاجة حقيقية لتعديل ملف محجوز، لا ينفذها الشخص داخل فرعه؛ يسجل الحاجة في وصف الـPull Request لتنفذ مرة واحدة في مرحلة الربط.

# 16. نقاط الربط المؤجلة بعد اكتمال العمل

بعد نجاح كل ميزة منفردة فقط، يحتاج المشروع إلى تغييرات مشتركة صغيرة:

1. `backend/app/main.py`
   - استيراد `des_image_api.router` و`rsa_file_api.router`.
   - `app.include_router(...)` لكل واحد.

2. `frontend/src/App.tsx`
   - إضافة مسار لصفحة DES.
   - إضافة مسار لصفحة RSA.

3. `frontend/src/lib/i18n.ts`
   - فقط إذا تقرر تعريب/ترجمة الصفحتين ضمن نفس نظام النصوص الحالي.

هذه الخطوات لا تنفذ بالتوازي من الشخصين.

# 17. شرط اعتبار أي مهمة جاهزة للرفع

لا تعتبر مهمة DES أو RSA مكتملة ما لم:

- تعمل اختبارات الملف التشفيري الجديد.
- تعمل اختبارات API الجديدة.
- `pytest -q` ينجح كاملًا.
- `pnpm check` ينجح.
- `pnpm build` ينجح.
- AES ومسار الرسائل الحاليان لم يتغيرا ولم تنكسر اختباراتهما.
- لا يوجد تعديل خارج الملفات المملوكة للمهمة.
- لا توجد مفاتيح أو بيانات اختبار حساسة داخل commit.

بهذه الحدود يستطيع ملاطف وأيمن العمل بالتوازي لأن ملفات التنفيذ والاختبار والواجهة لكل منهما منفصلة، وأي تعديل مشترك مؤجل إلى مرحلة الربط بعد اكتمال الـPull Requests.
