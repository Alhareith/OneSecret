// مساحة أيمن في الواجهة — RSA للملفات فقط.
// لا تضف هنا أي منطق DES، ولا تعدل App.tsx أثناء التطوير المتوازي.
// الربط النهائي للمسار يتم لاحقًا بعد اكتمال الميزة.

export default function RsaFilePage() {
  return (
    <main className="min-h-[100dvh] bg-[#f5f7fb] p-6 text-slate-800">
      <section className="mx-auto max-w-2xl">
        <h1 className="text-2xl font-black text-slate-950">RSA - Files</h1>
        <p className="mt-3 text-sm leading-7 text-slate-600">
          مساحة توليد مفاتيح RSA، رفع ملف، تشفيره بالطريقة الهجينة، ثم فكّه واستعادته.
        </p>
      </section>
    </main>
  );
}

/*
العقد النهائي للصفحة:
1. زر Generate Keys يستدعي generateRsaKeyPair ويحفظ المفتاحين في state فقط.
2. لا localStorage ولا sessionStorage ولا console للمفتاح الخاص.
3. اختيار ملف واحد غير image/*، غير فارغ، وبحد أقصى 5 MiB.
4. لا يسمح Encrypt قبل وجود public_key_pem وملف صالح.
5. Encrypt يستدعي encryptRsaFile(file, publicKeyPem) ويحفظ RsaFileEncrypted في state فقط.
6. لا يسمح Decrypt قبل وجود الحزمة المشفرة وprivate_key_pem المطابق.
7. Decrypt يستدعي decryptRsaFile ثم يحول data_b64 إلى Blob بنفس content_type.
8. ينشأ Object URL لتنزيل الملف بالاسم الأصلي، ثم يتم تنظيفه عبر URL.revokeObjectURL.
9. تغيير الملف أو توليد مفاتيح جديدة يمسح نتيجة التشفير/الفك السابقة حتى لا تختلط المفاتيح بالحزم.
10. اعرض رسائل خطأ عامة ومفهومة، ولا تعرض traceback أو PEM كامل ضمن رسالة خطأ.
11. لا تعدل CreateSecretPage أو RevealSecretPage أو App.tsx ضمن مهمة أيمن.
*/
