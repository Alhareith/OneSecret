import { decryptTextInBrowser, encryptTextInBrowser } from "./browser-crypto";
import { createClientTextShare, revealClientTextShare } from "./client-crypto-api";

export type CreateSecretInput = {
  secret_id: string;
  plaintext: string;
  expires_at: string;
  destroy_on_open: boolean;
  secret_code?: string;
};

export type CreateSecretOutput = {
  id: string;
  expires_at: string;
  status: "active";
  cancel_code: string;
};

export type SecretStatus = "active" | "used" | "expired" | "missing";

export type SecretStatusOutput = {
  id: string;
  status: SecretStatus;
  expires_at: string | null;
};

export type RevealSecretOutput = {
  id: string;
  plaintext: string;
};

export type CancelSecretOutput = {
  id: string;
  status: "cancelled";
};

export class ApiError extends Error {
  constructor(public readonly status: number, code: string) {
    super(code);
  }
}

function keyFromCurrentFragment(): string | null {
  try {
    return new URLSearchParams(window.location.hash.slice(1)).get("k");
  } catch {
    return null;
  }
}

export async function createSecret(input: CreateSecretInput): Promise<CreateSecretOutput> {
  // Encrypt before the first request leaves the browser. The backend receives only ciphertext + nonce.
  const encrypted = await encryptTextInBrowser(input.plaintext);
  const result = await createClientTextShare({
    secret_id: input.secret_id,
    ciphertext_b64: encrypted.ciphertext_b64,
    nonce_b64: encrypted.nonce_b64,
    expires_at: input.expires_at,
    destroy_on_open: input.destroy_on_open,
    ...(input.secret_code ? { secret_code: input.secret_code } : {}),
  });

  // Existing UI builds /s/${result.id}; appending the fragment here preserves that UI unchanged.
  return { ...result, id: `${result.id}#k=${encrypted.key_fragment}` };
}

export async function getSecretStatus(secretId: string): Promise<SecretStatusOutput> {
  // Kept for legacy links and existing callers. Client-encrypted reveal does not need a status preflight.
  const response = await fetch(`/api/secrets/${encodeURIComponent(secretId)}/status`);
  if (!response.ok) throw new Error("STATUS_SECRET_FAILED");
  return response.json() as Promise<SecretStatusOutput>;
}

export async function revealSecret(secretId: string, secretCode?: string): Promise<RevealSecretOutput> {
  const keyFragment = keyFromCurrentFragment();
  if (keyFragment) {
    const envelope = await revealClientTextShare(secretId, secretCode);
    try {
      const plaintext = await decryptTextInBrowser(
        envelope.ciphertext_b64,
        envelope.nonce_b64,
        keyFragment,
      );
      window.history.replaceState(null, "", window.location.pathname);
      return { id: secretId, plaintext };
    } catch {
      throw new ApiError(410, "CLIENT_DECRYPT_FAILED");
    }
  }

  // Backward compatibility for links created before client-side encryption was enabled.
  const response = await fetch(`/api/secrets/${encodeURIComponent(secretId)}/reveal`, {
    method: "POST",
    ...(secretCode
      ? { headers: { "Content-Type": "application/json" }, body: JSON.stringify({ secret_code: secretCode }) }
      : {}),
  });
  if (!response.ok) throw new ApiError(response.status, "REVEAL_SECRET_FAILED");
  return response.json() as Promise<RevealSecretOutput>;
}

export async function cancelSecret(secretId: string, cancelCode: string): Promise<CancelSecretOutput> {
  const clientResponse = await fetch(`/api/client-crypto/text/${encodeURIComponent(secretId)}/cancel`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ cancel_code: cancelCode }),
  });
  if (clientResponse.ok) return clientResponse.json() as Promise<CancelSecretOutput>;
  if (clientResponse.status !== 404 && clientResponse.status !== 410) {
    throw new ApiError(clientResponse.status, "CANCEL_SECRET_FAILED");
  }

  // Backward compatibility for older server-encrypted links.
  const response = await fetch(`/api/secrets/${encodeURIComponent(secretId)}/cancel`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ cancel_code: cancelCode }),
  });
  if (!response.ok) throw new ApiError(response.status, "CANCEL_SECRET_FAILED");
  return response.json() as Promise<CancelSecretOutput>;
}
