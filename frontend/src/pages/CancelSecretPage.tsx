import { useState, type FormEvent } from "react";
import CancelSecretForm from "../components/CancelSecretForm";
import { copy, Language } from "../lib/i18n";

export default function CancelSecretPage() {
  const [language, setLanguage] = useState<Language>("ar");
  const text = copy[language];
  const direction = language === "ar" ? "rtl" : "ltr";

  function handleLanguageChange(nextLanguage: Language) {
    setLanguage(nextLanguage);
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
            <CancelSecretForm language={language} />
          </div>
        </section>
      </div>

      <footer className="px-5 py-6 text-center text-sm text-slate-400">{text.footer}</footer>
    </main>
  );
}
