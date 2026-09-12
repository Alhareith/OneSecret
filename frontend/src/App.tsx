import { lazy, Suspense } from "react";
import CreateSecretPage from "./pages/CreateSecretPage";

const RevealSecretPage = lazy(() => import("./pages/RevealSecretPage"));
const CancelSecretPage = lazy(() => import("./pages/CancelSecretPage"));
const RsaFilePage = lazy(() => import("./pages/RsaFilePage"));
const RsaFileReceivePage = lazy(() => import("./pages/RsaFileReceivePage"));
const DesImagePage = lazy(() => import("./pages/DesImagePage"));

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

  if (window.location.pathname === "/des-image") {
    return (
      <Suspense fallback={<main className="min-h-[100dvh] bg-[#f5f7fb]" />}>
        <DesImagePage />
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
      <div className="fixed bottom-5 right-5 z-50 flex flex-col gap-2 sm:bottom-7 sm:right-7">
        <a
          href="/des-image"
          aria-label="إرسال الصور"
          className="rounded-2xl border border-emerald-800 bg-[linear-gradient(135deg,#166534_0%,#14532d_55%,#052e16_100%)] px-5 py-3 text-center text-sm font-bold text-white no-underline shadow-[0_12px_30px_-16px_rgba(20,83,45,0.9)] transition hover:brightness-110 active:scale-[0.98]"
        >
          إرسال الصور
        </a>
        <a
          href="/rsa-file"
          aria-label="إرسال الملفات"
          className="rounded-2xl border border-[#0d1c2f] bg-[linear-gradient(135deg,#334960_0%,#172b44_48%,#0f2035_100%)] px-5 py-3 text-center text-sm font-bold text-white no-underline shadow-[0_12px_30px_-16px_rgba(15,32,53,0.9)] transition hover:brightness-110 active:scale-[0.98]"
        >
          إرسال الملفات
        </a>
      </div>
    </>
  );
}
