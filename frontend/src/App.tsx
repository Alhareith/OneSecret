import { lazy, Suspense } from "react";
import CreateSecretPage from "./pages/CreateSecretPage";

const RevealSecretPage = lazy(() => import("./pages/RevealSecretPage"));
const CancelSecretPage = lazy(() => import("./pages/CancelSecretPage"));
const RsaFilePage = lazy(() => import("./pages/RsaFilePage"));
const RsaFileReceivePage = lazy(() => import("./pages/RsaFileReceivePage"));

export default function App() {
  if (window.location.pathname === "/cancel") {
    return (
      <Suspense fallback={<main className="min-h-[100dvh] bg-[#f5f7fb]" />}>
        <CancelSecretPage />
      </Suspense>
    );
  }

  if (window.location.pathname === "/rsa-file") {
    return (
      <Suspense fallback={<main className="min-h-[100dvh] bg-[#f5f7fb]" />}>
        <RsaFilePage />
      </Suspense>
    );
  }

  const fileShareMatch = window.location.pathname.match(/^\/f\/([^/]+)$/);
  if (fileShareMatch?.[1]) {
    return (
      <Suspense fallback={<main className="min-h-[100dvh] bg-[#f5f7fb]" />}>
        <RsaFileReceivePage shareId={decodeURIComponent(fileShareMatch[1])} />
      </Suspense>
    );
  }

  const secretMatch = window.location.pathname.match(/^\/s\/([^/]+)$/);
  if (secretMatch?.[1]) {
    return (
      <Suspense fallback={<main className="min-h-[100dvh] bg-[#fbfaf8]" />}>
        <RevealSecretPage secretId={secretMatch[1]} />
      </Suspense>
    );
  }

  return (
    <>
      <CreateSecretPage />
      <a
        href="/rsa-file"
        aria-label="إرسال الملفات"
        className="fixed bottom-5 right-5 z-50 rounded-2xl border border-[#0d1c2f] bg-[linear-gradient(135deg,#334960_0%,#172b44_48%,#0f2035_100%)] px-5 py-3 text-sm font-bold text-white no-underline shadow-[0_12px_30px_-16px_rgba(15,32,53,0.9)] transition hover:brightness-110 active:scale-[0.98] sm:bottom-7 sm:right-7"
      >
        إرسال الملفات
      </a>
    </>
  );
}
