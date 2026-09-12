import { useEffect, useState } from "react";
import { ApiError } from "../lib/api";
import { getRsaFileShare, revealRsaFileShare, type RsaFileShare } from "../lib/rsa-file-api";

function decodePemFromFragment(encoded: string): string {
  const normalized = encoded.replace(/-/g, "+").replace(/_/g, "/");
  const padded = normalized + "=".repeat((4 - (normalized.length % 4)) % 4);
  const binary = atob(padded);
  const bytes = new Uint8Array(binary.length);
  for (let index = 0; index < binary.length; index += 1) bytes[index] = binary.charCodeAt(index);
  return new TextDecoder().decode(bytes);
}

function dataUrlFromBase64(dataB64: string, contentType: string): string {
  const byteString = atob(dataB64);
  const bytes = new Uint8Array(byteString.length);
  for (let index = 0; index < byteString.length; index += 1) bytes[index] = byteString.charCodeAt(index);
  return URL.createObjectURL(new Blob([bytes], { type: contentType }));
}

export default function RsaFileReceivePage({ shareId }: { shareId: string }) {
  const [share, setShare] = useState<RsaFileShare | null>(null);
  const [privateKeyPem] = useState<string | null>(() => {
    try {
      const encoded = new URLSearchParams(window.location.hash.slice(1)).get("k");
      return encoded ? decodePemFromFragment(encoded) : null;
    } catch {
      return null;
    }
  });
  const [downloadUrl, setDownloadUrl] = useState<string | null>(null);
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [isRevealing, setIsRevealing] = useState(false);

  useEffect(() => {
    let cancelled = false;

    async function loadShare() {
      if (!privateKeyPem) {
        setError("رابط الاستلام غير مكتمل أو فقد مفتاح فك التشفير.");
        setIsLoading(false);
        return;
      }

      try {
        const result = await getRsaFileShare(shareId);
        if (!cancelled) setShare(result);
      } catch (loadError) {
        if (!cancelled) {
          setError(loadError instanceof ApiError && loadError.status === 410
            ? "هذا الملف غير متاح؛ قد يكون تم استلامه مسبقًا أو انتهت صلاحية الرابط."
            : "تعذّر الوصول إلى الملف المشفّر.");
        }
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    }

    void loadShare();
    return () => {
      cancelled = true;
    };
  }, [privateKeyPem, shareId]);

  useEffect(() => {
    return () => {
      if (downloadUrl) URL.revokeObjectURL(downloadUrl);
    };
  }, [downloadUrl]);

  async function handleReveal() {
    if (!share || !privateKeyPem) return;

    setError("");
    setIsRevealing(true);
    try {
      const result = await revealRsaFileShare(shareId, privateKeyPem);
      if (downloadUrl) URL.revokeObjectURL(downloadUrl);
      setDownloadUrl(dataUrlFromBase64(result.data_b64, result.content_type));
      window.history.replaceState(null, "", window.location.pathname);
    } catch (revealError) {
      setError(revealError instanceof ApiError && revealError.status === 410
        ? "هذا الملف لم يعد متاحًا للاستلام."
        : "تعذّر فك تشفير الملف. تأكد من أن رابط المشاركة كامل وصحيح.");
    } finally {
      setIsRevealing(false);
    }
  }

  return (
    <main dir="rtl" className="min-h-[100dvh] bg-[#f5f7fb] px-5 py-8 text-slate-800 sm:px-8">
      <section className="mx-auto max-w-xl">
        <div className="mb-7 text-center">
          <p className="text-sm font-black text-slate-500">OneSecret</p>
          <h1 className="mt-2 text-3xl font-black tracking-tight text-slate-950">استلام ملف مشفّر</h1>
          <p className="mt-3 text-sm leading-7 text-slate-500">الملف لا يُفك إلا باستخدام المفتاح الموجود داخل رابط المشاركة.</p>
        </div>

        <div className="rounded-3xl border border-slate-200 bg-white p-5 shadow-[0_18px_50px_-28px_rgba(15,23,42,0.28)] sm:p-8">
          {isLoading && <p className="text-center text-sm font-bold text-slate-500">جاري التحقق من الرابط...</p>}

          {!isLoading && error && !share && (
            <div className="rounded-2xl bg-rose-50 px-4 py-4 text-sm font-semibold leading-6 text-rose-700">{error}</div>
          )}

          {share && (
            <>
              <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                <p className="text-xs font-bold text-slate-500">الملف المرسل</p>
                <p className="mt-2 break-all text-lg font-black text-slate-950">{share.filename}</p>
                <p dir="ltr" className="mt-1 text-left text-xs font-semibold text-slate-500">{share.content_type}</p>
                <p className="mt-3 text-xs font-semibold text-slate-500">تنتهي الصلاحية: {new Date(share.expires_at).toLocaleString("ar")}</p>
              </div>

              {!downloadUrl && (
                <button
                  type="button"
                  onClick={handleReveal}
                  disabled={isRevealing}
                  className="mt-5 w-full rounded-2xl border border-[#0d1c2f] bg-[linear-gradient(135deg,#334960_0%,#172b44_48%,#0f2035_100%)] px-5 py-4 text-base font-black text-white shadow-[0_10px_22px_-14px_rgba(15,32,53,0.85)] transition hover:brightness-110 disabled:opacity-50"
                >
                  {isRevealing ? "جاري فك التشفير..." : "استلام الملف وفك التشفير"}
                </button>
              )}

              {error && <p role="alert" className="mt-4 rounded-2xl bg-rose-50 px-4 py-3 text-sm font-semibold text-rose-700">{error}</p>}

              {downloadUrl && (
                <div className="mt-5 rounded-2xl border border-emerald-200 bg-emerald-50 p-5">
                  <h2 className="text-lg font-black text-emerald-950">تم استلام الملف بنجاح</h2>
                  <p className="mt-2 text-sm leading-6 text-emerald-800">تم فك التشفير محليًا في هذه الجلسة، وتم حذف الحزمة المشفّرة من الخادم.</p>
                  <div className="mt-4 grid grid-cols-2 gap-3">
                    <a
                      href={downloadUrl}
                      target="_blank"
                      rel="noreferrer"
                      className="rounded-xl border border-emerald-300 bg-white px-4 py-3 text-center text-sm font-black text-emerald-950 no-underline"
                    >
                      فتح الملف
                    </a>
                    <a
                      href={downloadUrl}
                      download={share.filename}
                      className="rounded-xl bg-emerald-900 px-4 py-3 text-center text-sm font-black text-white no-underline"
                    >
                      تنزيل الملف
                    </a>
                  </div>
                </div>
              )}
            </>
          )}

          <a href="/" className="mt-6 block text-center text-sm font-bold text-slate-500 no-underline">العودة إلى OneSecret</a>
        </div>
      </section>
    </main>
  );
}
