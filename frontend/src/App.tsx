import { lazy, Suspense } from "react";
import CreateSecretPage from "./pages/CreateSecretPage";

const RevealSecretPage = lazy(() => import("./pages/RevealSecretPage"));
const CancelSecretPage = lazy(() => import("./pages/CancelSecretPage"));

export default function App() {
  if (window.location.pathname === "/cancel") {
    return (
      <Suspense fallback={<main className="min-h-[100dvh] bg-[#f5f7fb]" />}>
        <CancelSecretPage />
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

  return <CreateSecretPage />;
}
