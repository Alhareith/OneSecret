// مساحة ملاطف في الواجهة — DES للصور فقط.
// لا تضف هنا أي منطق RSA، ولا تعدل App.tsx أثناء التطوير المتوازي.
// الربط النهائي للمسار يتم لاحقًا بعد اكتمال الميزة.

export default function DesImagePage() {
  return (
    <main className="min-h-[100dvh] bg-[#f5f7fb] p-6 text-slate-800">
      <section className="mx-auto max-w-2xl">
        <h1 className="text-2xl font-black text-slate-950">DES - Images</h1>
        <p className="mt-3 text-sm leading-7 text-slate-600">
          مساحة رفع صورة PNG/JPG، تشفيرها، ثم فكها واستعادة نفس الصورة.
        </p>
      </section>
    </main>
  );
}

/*
العقد النهائي للصفحة:
1. اختيار ملف واحد فقط من image/png أو image/jpeg.
2. رفض الملف الفارغ أو الأكبر من 5 MiB قبل الإرسال قدر الإمكان.
3. زر Encrypt يستدعي encryptDesImage(file).
4. بعد النجاح تُحفظ حزمة DesImageEncrypted في state فقط؛ لا localStorage ولا sessionStorage.
5. تعرض الصفحة اسم الصورة وحالة نجاح واضحة، ولا تعرض المفتاح في console.
6. زر Decrypt يستدعي decryptDesImage(encryptedPackage).
7. data_b64 الناتج يتحول إلى Blob بنفس content_type ثم Object URL لعرض/تنزيل الصورة المسترجعة.
8. يجب تنظيف Object URL عند استبداله أو مغادرة الصفحة باستخدام URL.revokeObjectURL.
9. تغيير الصورة يمسح أي نتيجة قديمة حتى لا تختلط حزمة صورة بصورة أخرى.
10. لا تعدل CreateSecretPage أو RevealSecretPage أو App.tsx ضمن مهمة ملاطف.
*/
