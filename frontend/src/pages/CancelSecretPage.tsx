import { useState, type FormEvent } from "react";
import { ApiError, cancelSecret } from "../lib/api";
import { extractSecretIdForCancellation } from "../lib/cancel-link";
import { copy, Language } from "../lib/i18n";

export default function CancelSecretPage() {
  const [language, setLanguage] = useState<Language>("ar");
  const [reference, setReference] = useState("");
  const [cancelCode, setCancelCode] = useState("");
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isCancelled, setIsCancelled] = useState(false);
  const text = copy[language];
  const direction = language === "ar" ? "rtl" : "ltr";

  function handleLanguageChange(nextLanguage: Language) {
    setLanguage(nextLanguage);
    setError("");
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const secretId = extractSecretIdForCancellation(reference);
    const normalizedCancelCode = cancelCode.trim();

    if (!secretId) {
      setError(text.cancelReferenceError);
      return;
    }
    if (normalizedCancelCode.length < 32) {
      setError(text.cancelCodeRequired);
      return;
    }

    setError("");
    setIsSubmitting(true);
    try {
      await cancelSecret(secretId, normalizedCancelCode);
      setCancelCode("");
      setIsCancelled(true);
    } catch (error: unknown) {
      setError(error instanceof ApiError && error.status === 429 ? text.cancelThrottled : text.cancelUnavailable);
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <main dir={direction} className="flex min-h-[100dvh] flex-col bg-[#f5f7fb] text-slate-800">
      <header className="mx-auto flex w-full max-w-5xl items-center justify-between px-5 py-5 sm:px-8 sm:py-7">
        <a href="/" className="text-xl font-extrabold tracking-tight text-slate-900 no-underline">OneSecret</a>
        <label className="sr-only" htmlFor="language-select">{text.language}</label>
        <select
          id="language-select"
          aria-label={text.language}
          value={language}
          onChange={(event) => handleLanguageChange(event.target.value as Language)}
          className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-700 outline-none transition focus:border-slate-500 focus:ring-4 focus:ring-slate-200"
        >
          <option value="ar">{text.arabic}</option>
          <option value="en">{text.english}</option>
        </select>
      </header>

      <div className="mx-auto flex w-full max-w-5xl flex-1 items-center px-5 pb-12 pt-4 sm:px-8 sm:py-10">
        <section className="mx-auto w-full max-w-xl">
          <div className="mb-8 text-center sm:mb-10">
            <h1 className="text-3xl font-black leading-tight tracking-tight text-slate-950 sm:text-5xl">{text.cancelTitle}</h1>
            <p className="mx-auto mt-4 max-w-md text-base font-medium leading-7 text-slate-500 sm:text-lg">{text.cancelDescription}</p>
          </div>

          <div className="rounded-3xl border border-slate-200 bg-white p-5 shadow-[0_18px_50px_-28px_rgba(15,23,42,0.28)] sm:p-8">
            {isCancelled ? (
              <div className="rounded-2xl border border-emerald-200 bg-emerald-50 p-5 text-center" aria-live="polite">
                <h2 className="text-lg font-bold text-emerald-900">{text.cancelSuccessTitle}</h2>
                <p className="mt-2 text-sm leading-6 text-emerald-800">{text.cancelSuccessDescription}</p>
                <a href="/" className="mt-5 inline-flex rounded-xl border border-emerald-800 bg-emerald-800 px-4 py-3 text-sm font-bold text-white no-underline transition hover:bg-emerald-900 active:scale-[0.99]">{text.cancelBackToCreate}</a>
              </div>
            ) : (
              <form className="space-y-6" onSubmit={handleSubmit} noValidate>
                <div className="space-y-2">
                  <label className="block text-base font-bold text-slate-800" htmlFor="cancel-reference">{text.cancelReferenceLabel}</label>
                  <p className="text-xs leading-5 text-slate-500">{text.cancelReferenceDescription}</p>
                  <input
                    id="cancel-reference"
                    type="text"
                    autoComplete="off"
                    value={reference}
                    onChange={(event) => {
                      setReference(event.target.value);
                      setError("");
                    }}
                    placeholder={text.cancelReferencePlaceholder}
                    className="w-full rounded-xl border border-slate-200 bg-white px-4 py-3 text-left text-base font-medium text-slate-900 outline-none placeholder:text-slate-400 transition focus:border-slate-500 focus:ring-4 focus:ring-slate-100"
                    dir="ltr"
                  />
                </div>

                <div className="space-y-2">
                  <label className="block text-base font-bold text-slate-800" htmlFor="cancel-code">{text.cancelCodeLabel}</label>
                  <p className="text-xs leading-5 text-slate-500">{text.cancelCodeDescription}</p>
                  <input
                    id="cancel-code"
                    type="password"
                    autoComplete="off"
                    minLength={32}
                    maxLength={64}
                    value={cancelCode}
                    onChange={(event) => {
                      setCancelCode(event.target.value);
                      setError("");
                    }}
                    placeholder={text.cancelCodePlaceholder}
                    className="w-full rounded-xl border border-slate-200 bg-white px-4 py-3 text-left text-base font-medium text-slate-900 outline-none placeholder:text-slate-400 transition focus:border-slate-500 focus:ring-4 focus:ring-slate-100"
                    dir="ltr"
                  />
                </div>

                {error && <p role="alert" className="rounded-2xl bg-rose-50 px-4 py-3 text-sm font-medium text-rose-700">{error}</p>}

                <button type="submit" disabled={isSubmitting} className="w-full rounded-2xl border border-rose-950 bg-[linear-gradient(135deg,#641b2a_0%,#3d0f1b_55%,#280812_100%)] px-5 py-4 text-base font-bold text-white shadow-[0_10px_22px_-14px_rgba(61,15,27,0.85)] transition duration-150 hover:brightness-110 active:scale-[0.99] disabled:cursor-not-allowed disabled:opacity-60">
                  {isSubmitting ? text.cancelling : text.cancelAction}
                </button>
              </form>
            )}
          </div>
        </section>
      </div>

      <footer className="px-5 py-6 text-center text-sm text-slate-400">{text.footer}</footer>
    </main>
  );
}
