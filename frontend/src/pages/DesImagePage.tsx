import { useEffect, useState } from "react";
import {
  decryptDesImage,
  encryptDesImage,
  type DesImageEncrypted,
} from "../lib/des-image-api";

const MAX_FILE_SIZE = 5 * 1024 * 1024;
const ALLOWED_TYPES = new Set(["image/png", "image/jpeg"]);

function errorMessage(error: unknown, fallback: string): string {
  return error instanceof Error && error.message ? error.message : fallback;
}

export default function DesImagePage() {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [encryptedPackage, setEncryptedPackage] = useState<DesImageEncrypted | null>(null);
  const [decryptedImageUrl, setDecryptedImageUrl] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    return () => {
      if (decryptedImageUrl) URL.revokeObjectURL(decryptedImageUrl);
    };
  }, [decryptedImageUrl]);

  const clearDecryptedImage = () => {
    setDecryptedImageUrl((currentUrl) => {
      if (currentUrl) URL.revokeObjectURL(currentUrl);
      return null;
    });
  };

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0] ?? null;

    setSelectedFile(null);
    setEncryptedPackage(null);
    clearDecryptedImage();
    setError(null);

    if (!file) return;
    if (!ALLOWED_TYPES.has(file.type)) {
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
    setEncryptedPackage(null);
    clearDecryptedImage();

    try {
      setEncryptedPackage(await encryptDesImage(selectedFile));
    } catch (caughtError: unknown) {
      setError(errorMessage(caughtError, "حدث خطأ أثناء التشفير."));
    } finally {
      setIsLoading(false);
    }
  };

  const handleDecrypt = async () => {
    if (!encryptedPackage) return;

    setIsLoading(true);
    setError(null);
    clearDecryptedImage();

    try {
      const result = await decryptDesImage(encryptedPackage);
      const binary = atob(result.data_b64);
      const bytes = Uint8Array.from(binary, (character) => character.charCodeAt(0));
      const blob = new Blob([bytes], { type: result.content_type });
      setDecryptedImageUrl(URL.createObjectURL(blob));
    } catch (caughtError: unknown) {
      setError(errorMessage(caughtError, "حدث خطأ أثناء فك التشفير."));
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <main className="min-h-[100dvh] bg-[#f5f7fb] p-6 text-slate-800">
      <section className="mx-auto max-w-2xl">
        <div className="mb-5 flex items-center justify-between gap-3">
          <div>
            <h1 className="text-2xl font-black text-slate-950">DES - Images</h1>
            <p className="mt-2 text-sm leading-7 text-slate-600">
              تشفير صورة PNG/JPEG تعليميًا باستخدام DES-CBC ثم استعادتها byte-for-byte.
            </p>
          </div>
          <a href="/" className="text-sm font-semibold text-slate-600 hover:text-slate-950">
            الرئيسية
          </a>
        </div>

        <div className="space-y-6 rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
          <div>
            <label className="mb-2 block text-sm font-semibold">اختر صورة (PNG/JPG):</label>
            <input
              type="file"
              accept="image/png,image/jpeg"
              onChange={handleFileChange}
              className="block w-full text-sm text-slate-500 file:mr-4 file:rounded-md file:border-0 file:bg-blue-50 file:px-4 file:py-2 file:text-sm file:font-semibold file:text-blue-700 hover:file:bg-blue-100"
            />
            {selectedFile && (
              <p className="mt-2 text-xs text-slate-500">{selectedFile.name}</p>
            )}
            {error && <p className="mt-2 text-sm font-medium text-red-600">{error}</p>}
          </div>

          <button
            type="button"
            onClick={handleEncrypt}
            disabled={!selectedFile || isLoading}
            className="rounded-md bg-slate-900 px-6 py-2 text-sm font-semibold text-white transition-colors hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {isLoading && !encryptedPackage ? "جاري التشفير..." : "تشفير الصورة (Encrypt)"}
          </button>

          {encryptedPackage && (
            <div className="rounded-md border border-green-200 bg-green-50 p-4">
              <p className="text-sm font-semibold text-green-800">تم تشفير الصورة بنجاح.</p>
              <p className="mt-1 text-xs text-green-700">الملف: {encryptedPackage.filename}</p>
              <button
                type="button"
                onClick={handleDecrypt}
                disabled={isLoading}
                className="mt-4 rounded-md bg-green-700 px-6 py-2 text-sm font-semibold text-white transition-colors hover:bg-green-800 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {isLoading ? "جاري فك التشفير..." : "فك التشفير (Decrypt)"}
              </button>
            </div>
          )}

          {decryptedImageUrl && encryptedPackage && (
            <div className="border-t pt-6">
              <h2 className="mb-3 text-sm font-semibold">الصورة المسترجعة:</h2>
              <img
                src={decryptedImageUrl}
                alt="Decrypted"
                className="h-auto max-w-full rounded-md border border-slate-200 shadow-sm"
              />
              <a
                href={decryptedImageUrl}
                download={encryptedPackage.filename}
                className="mt-3 inline-block text-sm font-medium text-blue-600 hover:underline"
              >
                تحميل الصورة بالاسم الأصلي
              </a>
            </div>
          )}
        </div>
      </section>
    </main>
  );
}
