import { useState } from "react";
import { createDesImageShare } from "../lib/des-image-api";

const MAX_FILE_SIZE = 5 * 1024 * 1024;
const ALLOWED_TYPES = new Set(["image/png", "image/jpeg"]);
const durationOptions = [1, 5, 15, 60, 1440] as const;

function shortShareUrl(shareUrl: string): string {
  const url = new URL(shareUrl);
  return `${url.origin}${url.pathname}#k=••••••`;
}

export default function DesImagePage() {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [expiresMinutes, setExpiresMinutes] = useState<(typeof durationOptions)[number]>(15);
  const [shareUrl, setShareUrl] = useState("");
  const [expiresAt, setExpiresAt] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState("");
  const [isBusy, setIsBusy] = useState(false);

  function handleFileChange(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0] ?? null;
    setSelectedFile(null);
    setShareUrl("");
    setExpiresAt("");
    setError(null);
    setNotice("");

    if (!file) return;
    if (!ALLOWED_TYPES.has(file.type)) {
      setError("يُسمح فقط بصور PNG أو JPEG.");
      event.target.value = "";
      return;
    }
    if (file.size === 0) {
      setError("لا يمكن إرسال صورة فارغة.");
      event.target.value = "";
      return;
    }
    if (file.size > MAX_FILE_SIZE) {
      setError("الحد الأقصى لحجم الصورة هو 5 MiB.");
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
      const share = await createDesImageShare(selectedFile, expiresMinutes);
      setShareUrl(`${window.location.origin}/i/${encodeURIComponent(share.id)}#k=${share.key_fragment}`);
      setExpiresAt(share.expires_at);
    } catch {
      setError("تعذّر تشفير الصورة وإنشاء رابط المشاركة. حاول مرة أخرى.");
    } finally {
      setIsBusy(false);
    }
  }

  async function copyShareUrl() {
    try {
      await navigator.clipboard.writeText(shareUrl);
      setNotice("تم نسخ رابط الصورة.");
    } catch {
      setNotice("تعذّر النسخ تلقائيًا؛ انسخ الرابط يدويًا.");
    }
  }

  async function shareImageLink() {
    if (typeof navigator.share !== "function") {
      await copyShareUrl();
      return;
    }
    try {
      await navigator.share({ title: "OneSecret", text: "صورة مشفّرة عبر OneSecret", url: shareUrl });
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
            <h1 className="mt-1 text-3xl font-black tracking-tight text-slate-950">إرسال صورة مشفّرة بـ DES</h1>
          </div>
          <a href="/" className="rounded-xl border border-slate-200 bg-white px-4 py-2 text-sm font-bold text-slate-700 no-underline">الرئيسية</a>
        </div>

        <div className="rounded-3xl border border-slate-200 bg-white p-5 shadow-[0_18px_50px_-28px_rgba(15,23,42,0.28)] sm:p-8">
          <p className="rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm font-semibold leading-7 text-amber-950">
            يتم تشفير الصورة تعليميًا باستخدام Single DES في وضع CBC مع PKCS#7. تُحفظ الحزمة المشفرة مؤقتًا، بينما مفتاح DES يكون داخل رابط المشاركة.
          </p>

          {error && <p role="alert" className="mt-5 rounded-2xl bg-rose-50 px-4 py-3 text-sm font-semibold text-rose-700">{error}</p>}

          <div className="mt-7 space-y-6">
            <div>
              <label htmlFor="des-image" className="block text-base font-black text-slate-900">1. اختر الصورة</label>
              <p className="mt-1 text-xs leading-5 text-slate-500">PNG أو JPEG وبحجم أقصى 5 MiB.</p>
              <input id="des-image" type="file" accept="image/png,image/jpeg" onChange={handleFileChange} disabled={isBusy} className="mt-3 block w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm" />
              {selectedFile && <div className="mt-3 rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-900"><span className="font-bold">{selectedFile.name}</span><span className="mx-2 text-emerald-500">•</span>{(selectedFile.size / 1024).toFixed(1)} KB</div>}
            </div>

            <div>
              <label htmlFor="image-expiry" className="block text-base font-black text-slate-900">2. مدة صلاحية الرابط</label>
              <select id="image-expiry" value={expiresMinutes} onChange={(event) => { setExpiresMinutes(Number(event.target.value) as (typeof durationOptions)[number]); setShareUrl(""); setExpiresAt(""); }} disabled={isBusy} className="mt-3 w-full rounded-2xl border border-slate-200 bg-white px-4 py-3.5 text-base outline-none">
                <option value={1}>دقيقة واحدة</option>
                <option value={5}>5 دقائق</option>
                <option value={15}>15 دقيقة</option>
                <option value={60}>ساعة واحدة</option>
                <option value={1440}>24 ساعة</option>
              </select>
            </div>

            <button type="button" onClick={handleCreateShare} disabled={isBusy || !selectedFile} className="w-full rounded-2xl border border-emerald-800 bg-[linear-gradient(135deg,#166534_0%,#14532d_55%,#052e16_100%)] px-5 py-4 text-base font-black text-white shadow-[0_10px_22px_-14px_rgba(20,83,45,0.8)] transition hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-50">
              {isBusy ? "جاري تشفير الصورة..." : "3. تشفير الصورة وإنشاء رابط الإرسال"}
            </button>
          </div>

          {shareUrl && (
            <section className="mt-7 rounded-2xl border border-emerald-200 bg-emerald-50 p-5" aria-live="polite">
              <h2 className="text-lg font-black text-slate-950">رابط الصورة جاهز</h2>
              <p className="mt-2 text-sm leading-6 text-slate-600">أرسل الرابط كاملًا للمستقبل. المفتاح موجود بعد # داخل الرابط ولا يُخزن في قاعدة البيانات.</p>
              <p dir="ltr" className="mt-4 overflow-hidden text-ellipsis whitespace-nowrap rounded-xl border border-emerald-200 bg-white px-3 py-3 text-left text-xs font-semibold text-slate-600">{shortShareUrl(shareUrl)}</p>
              {expiresAt && <p className="mt-3 text-xs font-semibold text-slate-500">ينتهي: {new Date(expiresAt).toLocaleString("ar")}</p>}
              <div className="mt-4 grid grid-cols-2 gap-3">
                <button type="button" onClick={copyShareUrl} className="rounded-xl border border-slate-300 bg-white px-4 py-3 text-sm font-black text-slate-800">نسخ الرابط</button>
                <button type="button" onClick={shareImageLink} className="rounded-xl bg-emerald-900 px-4 py-3 text-sm font-black text-white">إرسال الرابط</button>
              </div>
              <p className="mt-4 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-xs leading-6 text-amber-900">الرابط للاستخدام مرة واحدة؛ بعد نجاح فك الصورة تُحذف الحزمة المشفرة من الخادم.</p>
              {notice && <p className="mt-3 text-center text-sm font-bold text-slate-600">{notice}</p>}
            </section>
          )}
        </div>
      </section>
    </main>
  );
}
