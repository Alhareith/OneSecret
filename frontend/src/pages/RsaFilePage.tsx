import { useState } from "react";
import { createRsaFileShare, generateRsaKeyPair } from "../lib/rsa-file-api";

const MAX_FILE_BYTES = 5 * 1024 * 1024;
const durationOptions = [1, 5, 15, 60, 1440] as const;

function encodePemForFragment(pem: string): string {
  const bytes = new TextEncoder().encode(pem);
  let binary = "";
  for (const byte of bytes) binary += String.fromCharCode(byte);
  return btoa(binary).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/g, "");
}

function shortShareUrl(shareUrl: string): string {
  const url = new URL(shareUrl);
  return `${url.origin}${url.pathname}#k=••••••`;
}

export default function RsaFilePage() {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [expiresMinutes, setExpiresMinutes] = useState<(typeof durationOptions)[number]>(15);
  const [shareUrl, setShareUrl] = useState("");
  const [expiresAt, setExpiresAt] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState("");
  const [isBusy, setIsBusy] = useState(false);

  function handleFileSelect(event: React.ChangeEvent<HTMLInputElement>) {
    setError(null);
    setNotice("");
    setShareUrl("");
    setExpiresAt("");
    const file = event.target.files?.[0] ?? null;

    if (!file) {
      setSelectedFile(null);
      return;
    }
    if (file.type.startsWith("image/")) {
      setSelectedFile(null);
      setError("الصور لها مسار مستقل في OneSecret؛ اختر ملفًا غير صورة.");
      event.target.value = "";
      return;
    }
    if (file.size === 0) {
      setSelectedFile(null);
      setError("لا يمكن إرسال ملف فارغ.");
      event.target.value = "";
      return;
    }
    if (file.size > MAX_FILE_BYTES) {
      setSelectedFile(null);
      setError("الحد الأقصى لحجم الملف هو 5 ميجابايت.");
      event.target.value = "";
      return;
    }

    setSelectedFile(file);
  }

  async function handleCreateShare() {
    if (!selectedFile) return;

    setError(null);
    setNotice("");
    setIsBusy(true);
    try {
      const keyPair = await generateRsaKeyPair();
      const share = await createRsaFileShare(selectedFile, keyPair.public_key_pem, expiresMinutes);
      const keyFragment = encodePemForFragment(keyPair.private_key_pem);
      setShareUrl(`${window.location.origin}/f/${encodeURIComponent(share.id)}#k=${keyFragment}`);
      setExpiresAt(share.expires_at);
    } catch {
      setError("تعذّر تشفير الملف وإنشاء رابط الإرسال. حاول مرة أخرى.");
    } finally {
      setIsBusy(false);
    }
  }

  async function copyShareUrl() {
    try {
      await navigator.clipboard.writeText(shareUrl);
      setNotice("تم نسخ رابط الملف.");
    } catch {
      setNotice("تعذّر النسخ تلقائيًا.");
    }
  }

  async function shareFileLink() {
    if (typeof navigator.share !== "function") {
      await copyShareUrl();
      return;
    }

    try {
      await navigator.share({
        title: "OneSecret",
        text: "ملف مشفّر عبر OneSecret",
        url: shareUrl,
      });
    } catch (shareError) {
      if (shareError instanceof DOMException && shareError.name === "AbortError") return;
      setNotice("تعذّرت المشاركة المباشرة؛ يمكنك نسخ الرابط بدلًا منها.");
    }
  }

  return (
    <main dir="rtl" className="min-h-[100dvh] bg-[#f5f7fb] px-5 py-7 text-slate-800 sm:px-8">
      <section className="mx-auto max-w-2xl">
        <div className="mb-7 flex items-center justify-between gap-4">
          <div>
            <p className="text-sm font-bold text-slate-500">OneSecret</p>
            <h1 className="mt-1 text-3xl font-black tracking-tight text-slate-950">إرسال ملف مشفّر</h1>
          </div>
          <a href="/" className="rounded-xl border border-slate-200 bg-white px-4 py-2 text-sm font-bold text-slate-700 no-underline">الرئيسية</a>
        </div>

        <div className="rounded-3xl border border-slate-200 bg-white p-5 shadow-[0_18px_50px_-28px_rgba(15,23,42,0.28)] sm:p-8">
          <p className="text-sm leading-7 text-slate-600">
            يُشفّر الملف أولًا باستخدام AES-256-GCM، ثم يُحمى مفتاح AES باستخدام RSA. الخادم يحتفظ بالحزمة المشفّرة فقط، بينما مفتاح الاستلام يبقى داخل رابط المشاركة.
          </p>

          {error && <p role="alert" className="mt-5 rounded-2xl bg-rose-50 px-4 py-3 text-sm font-semibold text-rose-700">{error}</p>}

          <div className="mt-7 space-y-6">
            <div>
              <label className="block text-base font-black text-slate-900" htmlFor="rsa-file">1. اختر الملف</label>
              <p className="mt-1 text-xs leading-5 text-slate-500">ملف غير صورة، وبحجم أقصى 5 MiB.</p>
              <input
                id="rsa-file"
                type="file"
                onChange={handleFileSelect}
                disabled={isBusy}
                className="mt-3 block w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm"
              />
              {selectedFile && (
                <div className="mt-3 rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-900">
                  <span className="font-bold">{selectedFile.name}</span>
                  <span className="mx-2 text-emerald-500">•</span>
                  {(selectedFile.size / 1024).toFixed(1)} KB
                </div>
              )}
            </div>

            <div>
              <label className="block text-base font-black text-slate-900" htmlFor="file-expiry">2. مدة صلاحية الرابط</label>
              <select
                id="file-expiry"
                value={expiresMinutes}
                onChange={(event) => {
                  setExpiresMinutes(Number(event.target.value) as (typeof durationOptions)[number]);
                  setShareUrl("");
                  setExpiresAt("");
                }}
                disabled={isBusy}
                className="mt-3 w-full rounded-2xl border border-slate-200 bg-white px-4 py-3.5 text-base outline-none"
              >
                <option value={1}>دقيقة واحدة</option>
                <option value={5}>5 دقائق</option>
                <option value={15}>15 دقيقة</option>
                <option value={60}>ساعة واحدة</option>
                <option value={1440}>24 ساعة</option>
              </select>
            </div>

            <button
              type="button"
              onClick={handleCreateShare}
              disabled={isBusy || !selectedFile}
              className="w-full rounded-2xl border border-[#0d1c2f] bg-[linear-gradient(135deg,#334960_0%,#172b44_48%,#0f2035_100%)] px-5 py-4 text-base font-black text-white shadow-[0_10px_22px_-14px_rgba(15,32,53,0.85)] transition hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {isBusy ? "جاري التشفير..." : "3. تشفير وإنشاء رابط الإرسال"}
            </button>
          </div>

          {shareUrl && (
            <section className="mt-7 rounded-2xl border border-sky-200 bg-sky-50 p-5" aria-live="polite">
              <h2 className="text-lg font-black text-slate-950">الرابط جاهز للإرسال</h2>
              <p className="mt-2 text-sm leading-6 text-slate-600">
                أرسل هذا الرابط للمستقبل. الرابط نفسه يحتوي مفتاح فك التشفير، لذلك لا تنشره في مكان عام.
              </p>
              <p dir="ltr" className="mt-4 overflow-hidden text-ellipsis whitespace-nowrap rounded-xl border border-sky-200 bg-white px-3 py-3 text-left text-xs font-semibold text-slate-600">
                {shortShareUrl(shareUrl)}
              </p>
              {expiresAt && (
                <p className="mt-3 text-xs font-semibold text-slate-500">
                  ينتهي: {new Date(expiresAt).toLocaleString("ar")}
                </p>
              )}
              <div className="mt-4 grid grid-cols-2 gap-3">
                <button type="button" onClick={copyShareUrl} className="rounded-xl border border-slate-300 bg-white px-4 py-3 text-sm font-black text-slate-800">نسخ الرابط</button>
                <button type="button" onClick={shareFileLink} className="rounded-xl bg-slate-900 px-4 py-3 text-sm font-black text-white">إرسال الرابط</button>
              </div>
              <p className="mt-4 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-xs leading-6 text-amber-900">
                الرابط للاستخدام مرة واحدة: بعد أن يستلم المستقبل الملف بنجاح تُمسح الحزمة المشفّرة من الخادم.
              </p>
              {notice && <p className="mt-3 text-center text-sm font-bold text-slate-600">{notice}</p>}
            </section>
          )}
        </div>
      </section>
    </main>
  );
}
