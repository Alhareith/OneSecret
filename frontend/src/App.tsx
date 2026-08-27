import { lazy, Suspense } from "react";
import CreateSecretPage from "./pages/CreateSecretPage";

const RevealSecretPage = lazy(() => import("./pages/RevealSecretPage"));

export default function App() {
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
