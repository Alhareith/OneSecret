# OneSecret — سجل التنفيذ الحالي

هذا الملف يحتوي فقط الأعمال المفتوحة المرتبطة بتثبيت V2. السجل التاريخي الطويل الموجود سابقًا في `todo.md` يعبّر عن مراحل قديمة وقد يتعارض مع المعمارية الحالية، لذلك لا يُستخدم بعد الآن كمرجع معماري.

## مكتمل في مرحلة توحيد الحقيقة التقنية

- [x] تحديث README ليصف Text/File/Image ومسار كل خوارزمية بدقة.
- [x] تحديث SECURITY بحدود الثقة المختلفة لكل نوع بيانات.
- [x] تحديث CONTRIBUTING ليتوافق مع Client-side Web Crypto الحالي.
- [x] تحديث PROJECT_PLAN إلى خطة تثبيت V2 بدل خطة V1 القديمة.
- [x] تحديث فهرس docs لتمييز الوثائق التاريخية عن المرجع الحالي.
- [x] إضافة `docs/19-v2-finalization.md` كمرجع للحالة الحالية وبوابات الإصدار.
- [x] إزالة وصف “preview branch” القديم من router المجمع بدون تغيير السلوك.

## مكتمل في مرحلة Security parity + DES validation

- [x] إعادة حماية محاولات Secret Code الخاطئة في Client Text API.
- [x] إعادة حماية محاولات Cancel Code الخاطئة في Client Text API، بما فيها bucket عام داخل نسخة الخادم.
- [x] إضافة اختبارات Rate Limit للمسارات الجديدة.
- [x] التحقق من Magic Bytes لصور PNG/JPEG قبل DES encryption.
- [x] إضافة اختبارات لرفض MIME مزيف أو signature غير صحيحة.
- [x] تشغيل بوابة الجودة: `142 passed` في pytest، مع نجاح TypeScript check وVite production build على الفرع.
- [x] تحديث `SECURITY.md` ليصف الحماية الحالية بدل اعتبارها عملاً مستقبليًا.

## المرحلة التالية المقترحة — Legacy inventory + isolation

- [ ] جرد كل Legacy API ومسار قديم وتحديد المستهلك الفعلي له.
- [ ] فصل المسارات الحالية عن Server-side AES/RSA compatibility code بوضوح.
- [ ] تحديد ما إذا كانت روابط V1 القديمة مطلوبة للتوافق قبل حذف أي كود.
- [ ] عزل أو تعطيل Demo endpoints غير المستخدمة في التشغيل الفعلي.
- [ ] تقييم إزالة اعتماد النظام الحالي على `ONESECRET_ENCRYPTION_KEY` إذا أصبح خاصًا بالـLegacy فقط.
- [ ] إضافة اختبارات تثبت أن عزل Legacy لا يكسر Text/File/Image الحالية.
- [ ] تشغيل pytest وTypeScript check وVite build وGitHub Actions قبل الدمج.

## مراحل لاحقة — لا تبدأ قبل اعتماد المرحلة السابقة

- [ ] إضافة اختبارات Frontend Web Crypto.
- [ ] تنظيف dependencies وتثبيت إصدارات البيئة المدعومة.
- [ ] مراجعة migrations وتنظيف البيانات المنتهية.
- [ ] توحيد واجهة Text/File/Image.
- [ ] إصدار `v2.0.0` بعد نجاح جميع البوابات فقط.
