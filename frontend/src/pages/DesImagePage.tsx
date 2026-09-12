// مساحة ملاطف في الواجهة — DES للصور فقط.
// لا تضف هنا أي منطق RSA، ولا تعدل App.tsx أثناء التطوير المتوازي.
// الربط النهائي للمسار يتم لاحقًا بعد اكتمال الميزة.

import { useState, useEffect } from "react";
import {
  encryptDesImage,
  decryptDesImage,
  DesImageEncrypted,
} from "../lib/des-image-api";

const MAX_FILE_SIZE = 5 * 1024 * 1024; // 5 MiB

export default function DesImagePage() {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [encryptedPackage, setEncryptedPackage] = useState<DesImageEncrypted | null>(null);
  const [decryptedImageUrl, setDecryptedImageUrl] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);

  // تنظيف Object URL عند تغييره أو عند مغادرة الصفحة (النقطة 8)
  useEffect(() => {
    return () => {
      if (decryptedImageUrl) {
        URL.revokeObjectURL(decryptedImageUrl);
      }
    };
  }, [decryptedImageUrl]);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    
    // تصفير النتائج القديمة عند اختيار صورة جديدة (النقطة 9)
    setSelectedFile(null);
    setEncryptedPackage(null);
    if (decryptedImageUrl) {
      URL.revokeObjectURL(decryptedImageUrl);
      setDecryptedImageUrl(null);
    }
    setError(null);

    if (!file) return;

    // التحقق من النوع والحجم (النقطة 1 و 2)
    if (file.type !== "image/png" && file.type !== "image/jpeg") {
      setError("يُسمح فقط بصور PNG أو JPEG.");
      return;
    }

    if (file.size === 0) {
      setError("الملف فارغ.");
      return;
    }

    if (file.size > MAX_FILE_SIZE) {
      setError("حجم الصورة يتجاوز الحد الأقصى المسموح به (5 MiB).");
      return;
    }

    setSelectedFile(file);
  };

  const handleEncrypt = async () => {
    if (!selectedFile) return;

    setIsLoading(true);
    setError(null);

    try {
      // استدعاء دالة التشفير (النقطة 3)
      const result = await encryptDesImage(selectedFile);
      setEncryptedPackage(result); // الحفظ في state فقط (النقطة 4)
    } catch (err: any) {
      setError(err.message || "حدث خطأ أثناء التشفير.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleDecrypt = async () => {
    if (!encryptedPackage) return;

    setIsLoading(true);
    setError(null);

    try {
      // استدعاء دالة فك التشفير (النقطة 6)
      const result = await decryptDesImage(encryptedPackage);

      // تحويل Base64 إلى Blob (النقطة 7)
      const byteCharacters = atob(result.data_b64);
      const byteNumbers = new Array(byteCharacters.length);
      for (let i = 0; i < byteCharacters.length; i++) {
        byteNumbers[i] = byteCharacters.charCodeAt(i);
      }
      const byteArray = new Uint8Array(byteNumbers);
      const blob = new Blob([byteArray], { type: result.content_type });

      // إنشاء Object URL لعرض الصورة
      const url = URL.createObjectURL(blob);
      setDecryptedImageUrl(url);
    } catch (err: any) {
      setError(err.message || "حدث خطأ أثناء فك التشفير.");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <main className="min-h-[100dvh] bg-[#f5f7fb] p-6 text-slate-800">
      <section className="mx-auto max-w-2xl">
        <h1 className="text-2xl font-black text-slate-950">DES - Images</h1>
        <p className="mt-3 text-sm leading-7 text-slate-600">
          مساحة رفع صورة PNG/JPG، تشفيرها، ثم فكها واستعادة نفس الصورة.
        </p>

        <div className="mt-8 space-y-6 bg-white p-6 rounded-xl shadow-sm border border-slate-200">
          
          {/* قسم اختيار الملف */}
          <div>
            <label className="block text-sm font-semibold mb-2">اختر صورة (PNG/JPG):</label>
            <input
              type="file"
              accept="image/png, image/jpeg"
              onChange={handleFileChange}
              className="block w-full text-sm text-slate-500 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
            />
            {error && <p className="mt-2 text-sm text-red-600 font-medium">{error}</p>}
          </div>

          {/* قسم التشفير */}
          <div>
            <button
              onClick={handleEncrypt}
              disabled={!selectedFile || isLoading}
              className="bg-slate-900 text-white px-6 py-2 rounded-md text-sm font-semibold disabled:opacity-50 disabled:cursor-not-allowed hover:bg-slate-800 transition-colors"
            >
              {isLoading && !encryptedPackage ? "جاري التشفير..." : "تشفير الصورة (Encrypt)"}
            </button>
          </div>

          {/* عرض حالة التشفير (النقطة 5) */}
          {encryptedPackage && (
            <div className="p-4 bg-green-50 border border-green-200 rounded-md">
              <p className="text-sm text-green-800 font-semibold">
                ✅ تم تشفير الصورة بنجاح!
              </p>
              <p className="text-xs text-green-700 mt-1">
                الملف: {encryptedPackage.filename}
              </p>
              
              {/* قسم فك التشفير */}
              <div className="mt-4">
                <button
                  onClick={handleDecrypt}
                  disabled={isLoading}
                  className="bg-green-700 text-white px-6 py-2 rounded-md text-sm font-semibold disabled:opacity-50 disabled:cursor-not-allowed hover:bg-green-800 transition-colors"
                >
                  {isLoading && encryptedPackage ? "جاري فك التشفير..." : "فك التشفير (Decrypt)"}
                </button>
              </div>
            </div>
          )}

          {/* عرض الصورة المسترجعة */}
          {decryptedImageUrl && (
            <div className="mt-6 border-t pt-6">
              <h3 className="text-sm font-semibold mb-3">الصورة المسترجعة:</h3>
              <img
                src={decryptedImageUrl}
                alt="Decrypted"
                className="max-w-full h-auto rounded-md border border-slate-200 shadow-sm"
              />
              <a
                href={decryptedImageUrl}
                download={`decrypted_${selectedFile?.name || "image.png"}`}
                className="inline-block mt-3 text-sm text-blue-600 hover:underline font-medium"
              >
                تحميل الصورة
              </a>
            </div>
          )}

        </div>
      </section>
    </main>
  );
}
