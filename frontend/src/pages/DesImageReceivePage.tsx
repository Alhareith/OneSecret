import { useEffect, useMemo, useState } from "react";
import { DesImageApiError, getDesImageShare, revealDesImageShare, type DesImageShareInfo } from "../lib/des-image-api";

function readKeyFragment(): string | null {
  try {
    return new URLSearchParams(window.location.hash.slice(1)).get("k");
  } catch {
    return null;
  }
}

export default function DesImageReceivePage({ shareId }: { shareId: string }) {
  const keyFragment = useMemo(readKeyFragment, []);
  const [share, setShare] = useState<DesImageShareInfo | null>(null);
  const [imageUrl, setImageUrl] = useState<string | null>(null);
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [isRevealing, setIsRevealing] = useState(false);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      if (!keyFragment) {
        setError("رابط الصورة غير مكتمل أو فقد مفتاح فك التشفير.");
        setIsLoading(false);
        return;
      }
      try {
        const result = await getDesImageShare(shareId);
        if (!cancelled) setShare(result);
      } catch (caught) {
        if (!cancelled) {
          setError(caught instanceof DesImageApiError && caught.status === 410
            ? "هذه الصورة غير متاحة؛ قد تكون استُلمت مسبقًا أو انتهت صلاحية الرابط."
            : "تعذر الوصول إلى الصورة المشفرة.");
        }
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    }
    void load();
    return () => { cancelled = true; };
  }, [keyFragment, shareId]);

  useEffect(() => () => { if (imageUrl) URL.revokeObjectURL(imageUrl); }, [imageUrl]);

  async function handleReveal() {
    if (!share || !keyFragment) return;
    setError("");
    setIsRevealing(true);
    try {
      const result = await revealDesImageShare(shareId, keyFragment);
      const binary = atob(result.data_b64);
      const bytes = Uint8Array.from(binary, (character) => character.charCodeAt(0));
      const blob = new Blob([bytes], { type: result.content_type });
      if (imageUrl) URL.revokeObjectURL(imageUrl);
      setImageUrl(URL.createObjectURL(blob));
      window.history.replaceState(null, "", window.location.pathname);
    } catch (caught) {
      setError(caught instanceof DesImageApiError && caught.status === 410
        ? "هذه الصورة لم تعد متاحة للاستلام."
        : "تعذر فك تشفير الصورة. تأكد من أن رابط المشاركة كامل وصحيح.");
    } finally {
      setIsRevealing(false);
    }
  }

  return (
    <main dir="rtl" className="min-h-[100dvh] bg-[#f5f7fb] px-5 py-8 text-slate-800 sm:px-8">
      <section className="mx-auto max-w-xl">
        <div className="mb-7 text-center">
          <p className="text-sm font-black text-slate-500">OneSecret</p>
          <h1 className="mt-2 text-3xl font-black tracking-tight text-slate-950">استلام صورة مشفّرة</h1>
          <p className="mt-3 text-sm leading-7 text-slate-500">الصورة مخزنة كحزمة DES-CBC مشفرة وتُفك مرة واحدة عند الاستلام.</p>
        </div>

        <div className="rounded-3xl border border-slate-200 bg-white p-5 shadow-[0_18px_50px_-28px_rgba(15,23,42,0.28)] sm:p-8">
          {isLoading && <p className="text-center text-sm font-bold text-slate-500">جاري التحقق من الرابط...</p>}
          {!isLoading && error && !share && <div className="rounded-2xl bg-rose-50 px-4 py-4 text-sm font-semibold leading-6 text-rose-700">{error}</div>}

          {share && (
            <>
              <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                <p className="text-xs font-bold text-slate-500">الصورة المرسلة</p>
                <p className="mt-2 break-all text-lg font-black text-slate-950">{share.filename}</p>
                <p className="mt-3 text-xs font-semibold text-slate-500">تنتهي الصلاحية: {new Date(share.expires_at).toLocaleString("ar")}</p>
              </div>

              {!imageUrl && <button type="button" onClick={handleReveal} disabled={isRevealing} className="mt-5 w-full rounded-2xl border border-emerald-800 bg-[linear-gradient(135deg,#166534_0%,#14532d_55%,#052e16_100%)] px-5 py-4 text-base font-black text-white transition hover:brightness-110 disabled:opacity-50">{isRevealing ? "جاري فك التشفير..." : "استلام الصورة وفك التشفير"}</button>}
              {error && <p role="alert" className="mt-4 rounded-2xl bg-rose-50 px-4 py-3 text-sm font-semibold text-rose-700">{error}</p>}

              {imageUrl && (
                <div className="mt-5 rounded-2xl border border-emerald-200 bg-emerald-50 p-5">
                  <h2 className="text-lg font-black text-emerald-950">تم استلام الصورة بنجاح</h2>
                  <img src={imageUrl} alt={share.filename} className="mt-4 h-auto max-w-full rounded-xl border border-emerald-200 bg-white" />
                  <a href={imageUrl} download={share.filename} className="mt-4 block rounded-xl bg-emerald-900 px-4 py-3 text-center text-sm font-black text-white no-underline">تنزيل الصورة</a>
                  <p className="mt-3 text-xs leading-6 text-emerald-800">بعد نجاح فك التشفير تم استهلاك الرابط وحذف الحزمة المشفرة من الخادم.</p>
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
