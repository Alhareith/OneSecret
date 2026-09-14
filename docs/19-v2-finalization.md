# OneSecret V2 Finalization Snapshot

هذه الوثيقة هي اللقطة التقنية المرجعية قبل بدء تغييرات التثبيت السلوكية. هدفها منع خلط المعمارية الحالية بالتصاميم التاريخية الموجودة في `docs/01-18`.

## 1. الحالة الحالية

الفرع `main` يدعم ثلاثة مسارات تشغيل فعلية:

```text
TEXT
Browser
AES-256-GCM
32-byte key
12-byte nonce
key in #k=
server stores ciphertext + nonce + metadata

FILE
Browser
AES-256-GCM + RSA-OAEP/SHA-256
RSA-2048
AES encrypts file bytes
RSA encrypts AES key
private RSA key + claim token in URL fragment
server stores encrypted envelope

IMAGE
Backend
Single DES-CBC + PKCS#7
8-byte DES key
8-byte IV
server receives original image bytes
server stores encrypted payload, not DES key
```

## 2. Trust Boundary Matrix

| السؤال | Text | File | Image |
|---|---|---|---|
| أين يوجد plaintext قبل التشفير؟ | Browser | Browser | Browser ثم Backend request |
| أين يحدث التشفير؟ | Browser | Browser | Backend |
| هل Backend يرى plaintext؟ | لا في المسار الحالي | لا في المسار الحالي | نعم أثناء التشفير |
| هل مفتاح فك المحتوى مخزن في DB؟ | لا | لا | لا |
| هل يستخدم URL Fragment؟ | AES key | RSA private key + claim token | DES key |
| هل الخوارزمية Authenticated Encryption؟ | نعم — GCM | نعم لمحتوى الملف — GCM | لا — DES-CBC |

## 3. الملفات المرجعية الحالية

### Frontend

- `frontend/src/lib/browser-crypto.ts`
  - AES-256-GCM للنص.
  - AES-256-GCM لمحتوى الملف.
  - RSA-OAEP/SHA-256 لحماية مفتاح AES.
  - توليد claim token.
- `frontend/src/lib/client-crypto-api.ts`
  - إرسال واستلام الحزم المشفرة.
- `frontend/src/lib/api.ts`
  - ربط واجهة النص بالمسار Client-side مع fallback Legacy.
- `frontend/src/pages/CreateSecretPage.tsx`
- `frontend/src/pages/RevealSecretPage.tsx`
- `frontend/src/pages/RsaFilePage.tsx`
- `frontend/src/pages/RsaFileReceivePage.tsx`
- `frontend/src/pages/DesImagePage.tsx`
- `frontend/src/pages/DesImageReceivePage.tsx`

### Backend

- `backend/app/client_crypto_core.py`
  - نماذج التخزين والتحقق المشتركة لـText/File.
- `backend/app/client_crypto_text_api.py`
  - إنشاء/Reveal/Cancel للحزم النصية المشفرة في Browser.
- `backend/app/client_crypto_file_api.py`
  - إنشاء/envelope/consume للملفات المشفرة.
- `backend/app/des_image_api.py`
  - تشفير DES ومشاركة الصور وفكها.
- `backend/app/crypto_des.py`
  - Single DES-CBC الخام.
- `backend/app/main.py`
  - نقطة تشغيل التطبيق، وتشمل أيضًا Compatibility APIs قديمة.

## 4. ما لا نعتبره المعمارية الأساسية الجديدة

ما زالت توجد ملفات Server-side أقدم مثل:

- `backend/app/crypto.py`
- `backend/app/crypto_rsa.py`
- أجزاء من `backend/app/main.py` لمسارات `/api/secrets` القديمة.
- `backend/app/rsa_file_api.py` لمسار RSA تعليمي/قديم.

لا نحذفها في مرحلة التوثيق. مصيرها يحدد في مرحلة Legacy Isolation بعد البحث عن كل caller واختبار backward compatibility.

## 5. ملاحظات أمنية يجب إغلاقها قبل V2

### 5.1 Secret Code / Cancel Code rate limits

المسار القديم يملك سياسات متخصصة لمحاولات الرموز الخاطئة. يجب التأكد أن Client Text API الجديد يملك المستوى نفسه من الحماية وعدم الاعتماد فقط على limit عام للـReveal/Cancel.

### 5.2 DES upload validation

التحقق الحالي يقبل PNG/JPEG حسب MIME ويملك دالة signature check عند Reveal. قبل V2 يجب تطبيق signature check كذلك على الصورة الأصلية قبل التشفير حتى لا يكفي `Content-Type` مزيف.

### 5.3 Legacy exposure

وجود API قديم وجديد في التطبيق نفسه يزيد سطح الهجوم ويعقد الشرح. يجب أن يكون كل endpoint مفعّلًا لسبب واضح أو يزال/يعزل.

### 5.4 Browser crypto tests

GitHub Actions تفحص TypeScript وVite، بينما التشفير الجديد الفعلي موجود في Browser. يلزم suite اختبارات مباشرة لـAES/RSA/fragment behavior قبل الإصدار النهائي.

### 5.5 One-time semantics

File وImage flows تمسح payload عند الاستهلاك/Reveal، لكن يجب اختبار وتوثيق السلوك تحت concurrency قبل إعطاء ضمان أقوى من الذي يثبته الكود.

## 6. قواعد العرض والمناقشة

الصياغات الصحيحة:

- **Text:** “النص يُشفّر داخل المتصفح بـAES-256-GCM قبل وصوله إلى الخادم.”
- **File:** “AES يشفر الملف، وRSA يحمي مفتاح AES.”
- **Image:** “الصورة تصل إلى Backend وتُشفّر تعليميًا باستخدام Single DES-CBC؛ مفتاح DES لا يُخزن في قاعدة البيانات.”
- **Nonce:** “قيمة فريدة/عشوائية بطول 12 بايت في AES-GCM، وليست مفتاحًا سريًا.”
- **IV في DES:** “قيمة بطول 8 بايت تستخدم مع CBC، ومفتاح DES نفسه 8 بايت.”

الصياغات الممنوعة لأنها غير دقيقة:

- “كل التشفير يحدث في Backend.”
- “كل البيانات تُشفّر قبل أن تصل إلى Backend.”
- “RSA يشفر الملف كاملًا.”
- “DES آمن كنظام حديث.”
- “OneSecret كله Zero Knowledge.”

## 7. بوابات الإصدار

لا يعتمد `v2.0.0` إلا بعد تحقق كل الآتي:

- [x] توحيد README وSECURITY وخطة المشروع مع الواقع الحالي.
- [ ] Security parity لمسار Client Text.
- [ ] Magic-byte validation لمسار DES upload.
- [ ] قرار موثق لكل Legacy endpoint.
- [ ] Frontend Web Crypto automated tests.
- [ ] تنظيف requirements وإصدار Python المدعوم.
- [ ] مراجعة schema/migrations ودورة cleanup.
- [ ] توحيد واجهة اختيار Text/File/Image.
- [ ] نجاح CI النهائي.
- [ ] تحديث CHANGELOG/version/tag/release.

## 8. المرحلة التالية بعد اكتمال هذه الوثيقة

المرحلة التالية المقترحة هي **Security parity + DES validation** فقط، لأنها مجموعة مترابطة وصغيرة نسبيًا ويمكن اختبارها دون خلطها مع حذف Legacy أو إعادة تصميم الواجهة.
