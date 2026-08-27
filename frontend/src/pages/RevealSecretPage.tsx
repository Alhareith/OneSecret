import { useEffect, useRef, useState } from "react";
import type { FormEvent } from "react";
import { ApiError, revealSecret } from "../lib/api";
import { copy, Language } from "../lib/i18n";
import { createRevealRequestCache } from "../lib/reveal-request-cache";

type RevealView = "opening" | "code" | "throttled" | "unavailable" | "revealed";

export default function RevealSecretPage({ secretId }: { secretId: string }) {
  const [language, setLanguage] = useState<Language>("ar");
  const [view, setView] = useState<RevealView>("opening");
  const [plaintext, setPlaintext] = useState("");
  const [secretCode, setSecretCode] = useState("");
  const [codeError, setCodeError] = useState("");
  const [isUnlocking, setIsUnlocking] = useState(false);
  const revealRequestCacheRef = useRef(createRevealRequestCache(revealSecret));
  const text = copy[language];
  const direction = language === "ar" ? "rtl" : "ltr";

  useEffect(() => {
    let cancelled = false;
    setView("opening");
    setPlaintext("");

    revealRequestCacheRef.current.get(secretId)
      .then((result) => {
        if (!cancelled) {
          setPlaintext(result.plaintext);
          setView("revealed");
        }
      })
      .catch((error: unknown) => {
        if (cancelled) return;
        if (error instanceof ApiError && error.status === 401) {
          setView("code");
        } else if (error instanceof ApiError && error.status === 429) {
          setView("throttled");
        } else {
          setView("unavailable");
        }
      });

    return () => {
      cancelled = true;
    };
  }, [secretId]);

  async function handleCodeSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const normalizedCode = secretCode.trim();
    if (!normalizedCode) {
      setCodeError(text.secretCodeRequired);
      return;
    }

    setCodeError("");
    setIsUnlocking(true);
    try {
      const result = await revealSecret(secretId, normalizedCode);
      setPlaintext(result.plaintext);
      setSecretCode("");
      setView("revealed");
    } catch (error: unknown) {
      setCodeError(error instanceof ApiError && error.status === 429 ? text.secretCodeThrottled : text.secretCodeInvalid);
    } finally {
      setIsUnlocking(false);
    }
  }

  return (
    <main dir={direction} className="flex min-h-[100dvh] flex-col bg-[#f5f7fb] text-slate-800">
      <header className="mx-auto flex w-full max-w-3xl items-center justify-between px-5 py-5 sm:px-8 sm:py-7">
        <a href="/" className="text-xl font-extrabold tracking-tight text-slate-900 no-underline">OneSecret</a>
        <label className="sr-only" htmlFor="language-select">{text.language}</label>
        <select
          id="language-select"
          aria-label={text.language}
          value={language}
          onChange={(event) => setLanguage(event.target.value as Language)}
          className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-700 outline-none transition focus:border-slate-500 focus:ring-4 focus:ring-slate-200"
        >
          <option value="ar">{text.arabic}</option>
          <option value="en">{text.english}</option>
        </select>
      </header>

      <div className="mx-auto flex w-full max-w-3xl flex-1 items-center px-5 pb-12 pt-4 sm:px-8 sm:py-10">
        <section className="mx-auto w-full max-w-2xl">
          {view === "opening" && (
            <div className="rounded-3xl border border-slate-200 bg-white px-6 py-16 text-center shadow-[0_18px_50px_-28px_rgba(15,23,42,0.28)] sm:px-10">
              <span aria-hidden="true" className="mx-auto block h-8 w-8 animate-spin rounded-full border-[3px] border-slate-200 border-t-[#172b44]" />
              <p className="mt-5 text-lg font-bold text-slate-800">{text.revealChecking}</p>
            </div>
          )}

          {view === "revealed" && (
            <div className="rounded-3xl border border-slate-200 bg-white p-5 shadow-[0_18px_50px_-28px_rgba(15,23,42,0.28)] sm:p-9">
              <div className="text-center">
                <h1 className="text-2xl font-black tracking-tight text-slate-950 sm:text-3xl">{text.revealTitle}</h1>
                <p className="mt-2 text-base font-medium text-slate-500">{text.revealDescription}</p>
              </div>
              <div role="status" aria-live="polite" className="mt-7 rounded-2xl bg-[#f7f5f2] px-5 py-6 sm:px-8 sm:py-8">
                <p className="whitespace-pre-wrap break-words text-xl font-semibold leading-10 text-slate-950 sm:text-2xl sm:leading-[2.8rem]">{plaintext}</p>
              </div>
              <div className="mt-7 border-t border-slate-100 pt-6 text-center">
                <p className="text-xs font-medium text-slate-400">{text.sentWith}</p>
                <a href="/" className="mt-4 inline-flex flex-col items-center gap-1 text-sm no-underline transition hover:opacity-80">
                  <span className="font-semibold text-slate-700">{text.sendOwnTitle}</span>
                  <span className="font-extrabold text-slate-950">{text.sendOwnAction} <span aria-hidden="true">→</span></span>
                </a>
              </div>
            </div>
          )}

          {view === "code" && (
            <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-[0_18px_50px_-28px_rgba(15,23,42,0.28)] sm:p-9">
              <div className="text-center">
                <h1 className="text-2xl font-black tracking-tight text-slate-950 sm:text-3xl">{text.secretCodePromptTitle}</h1>
                <p className="mx-auto mt-2 max-w-md text-base font-medium leading-7 text-slate-500">{text.secretCodePromptDescription}</p>
              </div>
              <form className="mt-7 space-y-4" onSubmit={handleCodeSubmit} noValidate>
                <label className="sr-only" htmlFor="reveal-secret-code">{text.secretCodePromptTitle}</label>
                <input
                  id="reveal-secret-code"
                  type="password"
                  autoComplete="off"
                  minLength={8}
                  maxLength={128}
                  value={secretCode}
                  onChange={(event) => {
                    setSecretCode(event.target.value);
                    if (event.target.value.trim()) setCodeError("");
                  }}
                  placeholder={text.secretCodePlaceholder}
                  className="w-full rounded-2xl border border-slate-200 bg-white px-4 py-4 text-base font-medium text-slate-900 outline-none placeholder:text-slate-400 transition focus:border-slate-500 focus:ring-4 focus:ring-slate-100"
                />
                {codeError && <p role="alert" className="rounded-2xl bg-rose-50 px-4 py-3 text-sm font-medium text-rose-700">{codeError}</p>}
                <button type="submit" disabled={isUnlocking} className="w-full rounded-2xl border border-[#0d1c2f] bg-[linear-gradient(135deg,#334960_0%,#172b44_48%,#0f2035_100%)] px-5 py-4 text-base font-bold text-white shadow-[0_10px_22px_-14px_rgba(15,32,53,0.85)] transition duration-150 hover:brightness-110 active:scale-[0.99] disabled:cursor-not-allowed disabled:opacity-60">
                  {isUnlocking ? text.unlocking : text.unlock}
                </button>
              </form>
            </div>
          )}

          {view === "unavailable" && (
            <div className="rounded-3xl border border-slate-200 bg-white px-6 py-14 text-center shadow-[0_18px_50px_-28px_rgba(15,23,42,0.28)] sm:px-10">
              <h1 className="text-2xl font-extrabold tracking-tight text-slate-900 sm:text-3xl">{text.unavailableTitle}</h1>
              <p className="mx-auto mt-3 max-w-md text-base leading-7 text-slate-500">{text.unavailableDescription}</p>
            </div>
          )}

          {view === "throttled" && (
            <div className="rounded-3xl border border-slate-200 bg-white px-6 py-14 text-center shadow-[0_18px_50px_-28px_rgba(15,23,42,0.28)] sm:px-10">
              <h1 className="text-2xl font-extrabold tracking-tight text-slate-900 sm:text-3xl">{text.rateLimitedTitle}</h1>
              <p className="mx-auto mt-3 max-w-md text-base leading-7 text-slate-500">{text.rateLimitedDescription}</p>
            </div>
          )}
        </section>
      </div>

      <footer className="px-5 py-6 text-center text-sm text-slate-400">{text.footer}</footer>
    </main>
  );
}
