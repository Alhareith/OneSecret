import { FormEvent, useState } from "react";

import { ApiError, cancelSecret } from "../lib/api";
import { isValidCancelCode, normalizeCancelCode } from "../lib/cancel-code";
import { extractSecretIdForCancellation } from "../lib/cancel-link";
import { copy, Language } from "../lib/i18n";

type CancelSecretFormProps = {
  language: Language;
  compact?: boolean;
};

export default function CancelSecretForm({ language, compact = false }: CancelSecretFormProps) {
  const [reference, setReference] = useState("");
  const [cancelCode, setCancelCode] = useState("");
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isCancelled, setIsCancelled] = useState(false);
  const text = copy[language];

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const secretId = extractSecretIdForCancellation(reference);
    const normalizedCancelCode = normalizeCancelCode(cancelCode);

    if (!secretId) {
      setError(text.cancelReferenceError);
      return;
    }
    if (!isValidCancelCode(normalizedCancelCode)) {
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

  if (isCancelled) {
    return (
      <div className="rounded-2xl border border-emerald-200 bg-emerald-50 p-5 text-center" aria-live="polite">
        <h3 className="text-lg font-bold text-emerald-900">{text.cancelSuccessTitle}</h3>
        <p className="mt-2 text-sm leading-6 text-emerald-800">{text.cancelSuccessDescription}</p>
        {!compact && <a href="/" className="mt-5 inline-flex rounded-xl border border-emerald-800 bg-emerald-800 px-4 py-3 text-sm font-bold text-white no-underline transition hover:bg-emerald-900 active:scale-[0.99]">{text.cancelBackToCreate}</a>}
      </div>
    );
  }

  return (
    <form className={compact ? "mt-5 space-y-4" : "space-y-6"} onSubmit={handleSubmit} noValidate>
      <div className="space-y-2">
        <label className="block text-base font-bold text-slate-800" htmlFor={compact ? "inline-cancel-reference" : "cancel-reference"}>{text.cancelReferenceLabel}</label>
        {!compact && <p className="text-xs leading-5 text-slate-500">{text.cancelReferenceDescription}</p>}
        <input
          id={compact ? "inline-cancel-reference" : "cancel-reference"}
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
        <label className="block text-base font-bold text-slate-800" htmlFor={compact ? "inline-cancel-code" : "cancel-code"}>{text.cancelCodeLabel}</label>
        <p className="text-xs leading-5 text-slate-500">{text.cancelCodeDescription}</p>
        <input
          id={compact ? "inline-cancel-code" : "cancel-code"}
          type="password"
          autoComplete="off"
          autoCapitalize="characters"
          inputMode="text"
          minLength={5}
          maxLength={5}
          value={cancelCode}
          onChange={(event) => {
            setCancelCode(normalizeCancelCode(event.target.value));
            setError("");
          }}
          placeholder={text.cancelCodePlaceholder}
          className="w-full rounded-xl border border-slate-200 bg-white px-4 py-3 text-left font-mono text-lg font-bold tracking-[0.24em] text-slate-900 outline-none placeholder:font-sans placeholder:text-base placeholder:font-medium placeholder:tracking-normal placeholder:text-slate-400 transition focus:border-slate-500 focus:ring-4 focus:ring-slate-100"
          dir="ltr"
        />
      </div>

      {error && <p role="alert" className="rounded-2xl bg-rose-50 px-4 py-3 text-sm font-medium text-rose-700">{error}</p>}

      <button type="submit" disabled={isSubmitting} className="w-full rounded-2xl border border-rose-950 bg-[linear-gradient(135deg,#641b2a_0%,#3d0f1b_55%,#280812_100%)] px-5 py-4 text-base font-bold text-white shadow-[0_10px_22px_-14px_rgba(61,15,27,0.85)] transition duration-150 hover:brightness-110 active:scale-[0.99] disabled:cursor-not-allowed disabled:opacity-60">
        {isSubmitting ? text.cancelling : text.cancelAction}
      </button>
    </form>
  );
}
