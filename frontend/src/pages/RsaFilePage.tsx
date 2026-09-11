import { useState, useEffect } from "react";
import {
  generateRsaKeyPair,
  encryptRsaFile,
  decryptRsaFile,
  type RsaKeyPair,
  type RsaFileEncrypted,
} from "../lib/rsa-file-api";

const MAX_FILE_BYTES = 5 * 1024 * 1024;

export default function RsaFilePage() {
  const [keyPair, setKeyPair] = useState<RsaKeyPair | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [encrypted, setEncrypted] = useState<RsaFileEncrypted | null>(null);
  const [downloadUrl, setDownloadUrl] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isBusy, setIsBusy] = useState(false);

  useEffect(() => {
    return () => {
      if (downloadUrl) {
        URL.revokeObjectURL(downloadUrl);
      }
    };
  }, [downloadUrl]);

  async function handleGenerateKeys() {
    setError(null);
    setIsBusy(true);
    try {
      const pair = await generateRsaKeyPair();
      setKeyPair(pair);
      setSelectedFile(null);
      setEncrypted(null);
      setDownloadUrl(null);
    } catch {
      setError("تعذّر توليد المفاتيح. حاول مرة أخرى.");
    } finally {
      setIsBusy(false);
    }
  }

  function handleFileSelect(event: React.ChangeEvent<HTMLInputElement>) {
    setError(null);
    const file = event.target.files?.[0] ?? null;

    if (!file) {
      setSelectedFile(null);
      return;
    }

    if (file.type.startsWith("image/")) {
      setError("الصور غير مقبولة هنا؛ هذا المسار مخصص للملفات غير الصور فقط.");
      event.target.value = "";
      return;
    }

    if (file.size === 0) {
      setError("الملف فارغ.");
      event.target.value = "";
      return;
    }

    if (file.size > MAX_FILE_BYTES) {
      setError("حجم الملف يتجاوز 5 ميجابايت.");
      event.target.value = "";
      return;
    }

    setSelectedFile(file);
    setEncrypted(null);
    setDownloadUrl(null);
  }

  async function handleEncrypt() {
    if (!keyPair || !selectedFile) return;

    setError(null);
    setIsBusy(true);
    try {
      const result = await encryptRsaFile(selectedFile, keyPair.public_key_pem);
      setEncrypted(result);
      setDownloadUrl(null);
    } catch {
      setError("فشل التشفير. تأكد من صحة الملف والمفتاح العام.");
    } finally {
      setIsBusy(false);
    }
  }

  async function handleDecrypt() {
    if (!keyPair || !encrypted) return;

    setError(null);
    setIsBusy(true);
    try {
      const result = await decryptRsaFile(encrypted, keyPair.private_key_pem);
      const byteString = atob(result.data_b64);
      const bytes = new Uint8Array(byteString.length);
      for (let i = 0; i < byteString.length; i++) {
        bytes[i] = byteString.charCodeAt(i);
      }
      const blob = new Blob([bytes], { type: result.content_type });
      const url = URL.createObjectURL(blob);
      setDownloadUrl(url);
    } catch {
      setError("فشل فك التشفير. تأكد من صحة المفتاح الخاص وسلامة الحزمة.");
    } finally {
      setIsBusy(false);
    }
  }

  return (
    <main className="min-h-[100dvh] bg-[#f5f7fb] p-6 text-slate-800">
      <section className="mx-auto max-w-2xl space-y-6">
        <div>
          <h1 className="text-2xl font-black text-slate-950">RSA - Files</h1>
          <p className="mt-3 text-sm leading-7 text-slate-600">
            مساحة توليد مفاتيح RSA، رفع ملف، تشفيره بالطريقة الهجينة، ثم فكّه واستعادته.
          </p>
        </div>

        {error && (
          <div className="rounded-md border border-red-300 bg-red-50 p-3 text-sm text-red-700">
            {error}
          </div>
        )}

        <div className="rounded-md border border-slate-200 bg-white p-4">
          <h2 className="font-bold">1. المفاتيح</h2>
          <button
            type="button"
            onClick={handleGenerateKeys}
            disabled={isBusy}
            className="mt-2 rounded-md bg-slate-900 px-4 py-2 text-sm font-semibold text-white disabled:opacity-50"
          >
            توليد مفاتيح جديدة
          </button>
          {keyPair && (
            <p className="mt-2 text-xs text-slate-500">تم توليد زوج مفاتيح جديد.</p>
          )}
        </div>

        <div className="rounded-md border border-slate-200 bg-white p-4">
          <h2 className="font-bold">2. الملف</h2>
          <input
            type="file"
            onChange={handleFileSelect}
            disabled={isBusy || !keyPair}
            className="mt-2 text-sm"
          />
          {selectedFile && (
            <p className="mt-2 text-xs text-slate-500">
              {selectedFile.name} ({selectedFile.size} bytes)
            </p>
          )}
        </div>

        <div className="rounded-md border border-slate-200 bg-white p-4">
          <h2 className="font-bold">3. التشفير</h2>
          <button
            type="button"
            onClick={handleEncrypt}
            disabled={isBusy || !keyPair || !selectedFile}
            className="mt-2 rounded-md bg-slate-900 px-4 py-2 text-sm font-semibold text-white disabled:opacity-50"
          >
            تشفير الملف
          </button>
          {encrypted && (
            <p className="mt-2 text-xs text-slate-500">
              تم التشفير: {encrypted.filename} ({encrypted.content_type})
            </p>
          )}
        </div>

        <div className="rounded-md border border-slate-200 bg-white p-4">
          <h2 className="font-bold">4. فك التشفير</h2>
          <button
            type="button"
            onClick={handleDecrypt}
            disabled={isBusy || !keyPair || !encrypted}
            className="mt-2 rounded-md bg-slate-900 px-4 py-2 text-sm font-semibold text-white disabled:opacity-50"
          >
            فك التشفير
          </button>
          {downloadUrl && encrypted && (
            <a
              href={downloadUrl}
              download={encrypted.filename}
              className="mt-3 block w-fit rounded-md border border-slate-900 px-4 py-2 text-sm font-semibold text-slate-900"
            >
              تنزيل الملف المسترجع
            </a>
          )}
        </div>
      </section>
    </main>
  );
}
