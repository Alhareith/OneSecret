import { FormEvent, useState } from "react";
import { createSecret } from "../lib/api";
import { copy, Language } from "../lib/i18n";

const durationOptions = [1, 5, 15, 60, 1440] as const;

function createSecretId(): string {
  const randomBytes = new Uint8Array(24);
  window.crypto.getRandomValues(randomBytes);
  return Array.from(randomBytes, (byte) => byte.toString(16).padStart(2, "0")).join("");
}

function getShortShareUrl(shareUrl: string): string {
  const secretId = shareUrl.split("/s/")[1] ?? "";
  return `…/s/${secretId.slice(0, 8)}…${secretId.slice(-6)}`;
}

export default function CreateSecretPage() {
  const [language, setLanguage] = useState<Language>("ar");
  const [message, setMessage] = useState("");
  const [minutes, setMinutes] = useState<(typeof durationOptions)[number]>(15);
  const [secretCode, setSecretCode] = useState("");
  const [destroyOnOpen, setDestroyOnOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [shareUrl, setShareUrl] = useState("");
  const [copyNotice, setCopyNotice] = useState("");

  const text = copy[language];
  const direction = language === "ar" ? "rtl" : "ltr";

  function handleLanguageChange(nextLanguage: Language) {
    setLanguage(nextLanguage);
    setError("");
    setCopyNotice("");
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const plaintext = message.trim();
    const normalizedSecretCode = secretCode.trim();

    if (!plaintext) {
      setError(text.emptyMessage);
      return;
    }
    if (normalizedSecretCode && normalizedSecretCode.length < 8) {
      setError(text.secretCodeTooShort);
      return;
    }

    setError("");
    setCopyNotice("");
    setIsSubmitting(true);

    try {
      const expiresAt = new Date(Date.now() + minutes * 60_000).toISOString();
      const result = await createSecret({
        secret_id: createSecretId(),
        plaintext,
        expires_at: expiresAt,
        destroy_on_open: destroyOnOpen,
        ...(normalizedSecretCode ? { secret_code: normalizedSecretCode } : {}),
      });
      setShareUrl(`${window.location.origin}/s/${result.id}`);
      setMessage("");
      setSecretCode("");
      setDestroyOnOpen(false);
    } catch {
      setError(text.generalError);
    } finally {
      setIsSubmitting(false);
    }
  }

  async function copyShareUrl() {
    try {
      await navigator.clipboard.writeText(shareUrl);
      setCopyNotice(text.copied);
    } catch {
      setCopyNotice(text.copyFailed);
    }
  }

  async function shareSecret() {
    const shareData = {
      title: text.appName,
      text: text.appName,
      url: shareUrl,
    };

    if (typeof navigator.share !== "function" || (typeof navigator.canShare === "function" && !navigator.canShare(shareData))) {
      setCopyNotice(text.nativeShareUnavailable);
      return;
    }

    try {
      await navigator.share(shareData);
    } catch (error) {
      if (error instanceof DOMException && error.name === "AbortError") return;
      setCopyNotice(text.nativeShareUnavailable);
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
            <h1 className="text-3xl font-black leading-tight tracking-tight text-slate-950 sm:text-5xl">{text.createTitle}</h1>
            <p className="mx-auto mt-4 max-w-md text-base font-medium leading-7 text-slate-500 sm:text-lg">{text.createDescription}</p>
          </div>

          <div className="rounded-3xl border border-slate-200 bg-white p-5 shadow-[0_18px_50px_-28px_rgba(15,23,42,0.28)] sm:p-8">
            <form className="space-y-6" onSubmit={handleSubmit} noValidate>
              <div className="space-y-2">
                <label className="block text-base font-bold text-slate-800" htmlFor="secret-message">{text.messageLabel}</label>
                <textarea
                  id="secret-message"
                  maxLength={10_000}
                  rows={7}
                  value={message}
                  onChange={(event) => {
                    const nextMessage = event.target.value;
                    setMessage(nextMessage);
                    if (nextMessage.trim()) setError("");
                  }}
                  placeholder={text.messagePlaceholder}
                  className="w-full resize-y rounded-2xl border border-slate-200 bg-white px-4 py-4 text-base font-medium leading-7 text-slate-900 outline-none placeholder:text-slate-400 transition focus:border-slate-500 focus:ring-4 focus:ring-slate-100"
                />
              </div>

              <div className="space-y-2">
                <label className="block text-base font-bold text-slate-800" htmlFor="expires-at">{text.expiresLabel}</label>
                <select
                  id="expires-at"
                  value={minutes}
                  onChange={(event) => setMinutes(Number(event.target.value) as (typeof durationOptions)[number])}
                  className="w-full rounded-2xl border border-slate-200 bg-white px-4 py-3.5 text-base text-slate-800 outline-none transition focus:border-slate-500 focus:ring-4 focus:ring-slate-100"
                >
                  {durationOptions.map((duration) => <option key={duration} value={duration}>{text.duration[String(duration) as keyof typeof text.duration]}</option>)}
                </select>
              </div>

              <details className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3">
                <summary className="cursor-pointer text-sm font-bold text-slate-700">{text.advancedOptions}</summary>
                <div className="mt-4 space-y-5">
                  <div className="space-y-2">
                    <label className="block text-sm font-bold text-slate-800" htmlFor="secret-code">{text.secretCodeLabel}</label>
                    <p className="text-xs leading-5 text-slate-500">{text.secretCodeDescription}</p>
                    <input
                      id="secret-code"
                      type="password"
                      autoComplete="off"
                      minLength={8}
                      maxLength={128}
                      value={secretCode}
                      onChange={(event) => {
                        setSecretCode(event.target.value);
                        if (event.target.value.trim().length >= 8) setError("");
                      }}
                      placeholder={text.secretCodePlaceholder}
                      className="w-full rounded-xl border border-slate-200 bg-white px-4 py-3 text-base font-medium text-slate-900 outline-none placeholder:text-slate-400 transition focus:border-slate-500 focus:ring-4 focus:ring-slate-100"
                    />
                  </div>
                  <label className="flex cursor-pointer items-start gap-3 rounded-xl border border-slate-200 bg-white p-3">
                    <input
                      type="checkbox"
                      checked={destroyOnOpen}
                      onChange={(event) => setDestroyOnOpen(event.target.checked)}
                      className="mt-1 h-4 w-4 accent-slate-900"
                    />
                    <span>
                      <span className="block text-sm font-bold text-slate-800">{text.destroyOnOpenLabel}</span>
                      <span className="mt-1 block text-xs leading-5 text-slate-500">{text.destroyOnOpenDescription}</span>
                    </span>
                  </label>
                </div>
              </details>

              {error && <p role="alert" className="rounded-2xl bg-rose-50 px-4 py-3 text-sm font-medium text-rose-700">{error}</p>}

              <button
                type="submit"
                disabled={isSubmitting}
                className="w-full rounded-2xl border border-[#0d1c2f] bg-[linear-gradient(135deg,#334960_0%,#172b44_48%,#0f2035_100%)] px-5 py-4 text-base font-bold text-white shadow-[0_10px_22px_-14px_rgba(15,32,53,0.85)] transition duration-150 hover:brightness-110 active:scale-[0.99] disabled:cursor-not-allowed disabled:opacity-60"
              >
                {isSubmitting ? text.creating : text.create}
              </button>
            </form>

            {shareUrl && (
              <div className="mt-6 rounded-2xl border border-slate-200 bg-slate-50 p-4 sm:p-5" aria-live="polite">
                <h2 className="text-base font-bold text-slate-900">{text.successTitle}</h2>
                <p className="mt-1 text-sm text-slate-500">{text.successDescription}</p>
                <p dir="ltr" aria-label={text.shareLinkLabel} className="mt-4 overflow-hidden text-ellipsis whitespace-nowrap rounded-xl border border-slate-200 bg-white px-3 py-3 text-left text-sm font-semibold tracking-wide text-slate-600">{getShortShareUrl(shareUrl)}</p>
                <div className="mt-3 grid grid-cols-2 gap-3">
                  <button type="button" onClick={copyShareUrl} className="rounded-xl border border-slate-300 bg-white px-4 py-3 text-sm font-bold text-slate-700 transition hover:border-slate-500 hover:text-slate-900 active:scale-[0.99]">{text.copy}</button>
                  <button type="button" onClick={shareSecret} className="rounded-xl border border-slate-900 bg-slate-900 px-4 py-3 text-sm font-bold text-white transition hover:bg-slate-800 active:scale-[0.99]">{text.share}</button>
                </div>
                {copyNotice && <p className="mt-3 text-center text-sm font-medium text-slate-600">{copyNotice}</p>}
              </div>
            )}
          </div>
        </section>
      </div>

      <footer className="px-5 py-6 text-center text-sm text-slate-400">{text.footer}</footer>
    </main>
  );
}
