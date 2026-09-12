import { ApiError } from "./api";

export type ClientTextCreateInput = {
  secret_id: string;
  ciphertext_b64: string;
  nonce_b64: string;
  expires_at: string;
  destroy_on_open: boolean;
  secret_code?: string;
};

export type ClientTextCreateOutput = {
  id: string;
  expires_at: string;
  status: "active";
  cancel_code: string;
};

export type ClientTextRevealOutput = {
  id: string;
  ciphertext_b64: string;
  nonce_b64: string;
  crypto: "AES-256-GCM/WebCrypto";
};

export type ClientFileShare = {
  id: string;
  filename: string;
  content_type: string;
  expires_at: string;
};

export type ClientFileEnvelope = {
  id: string;
  filename: string;
  content_type: string;
  encrypted_key_b64: string;
  nonce_b64: string;
  ciphertext_b64: string;
  crypto: "AES-256-GCM+RSA-OAEP-SHA256/WebCrypto";
};

export async function createClientTextShare(input: ClientTextCreateInput): Promise<ClientTextCreateOutput> {
  const response = await fetch("/api/client-crypto/text", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  if (!response.ok) throw new ApiError(response.status, "CREATE_CLIENT_TEXT_FAILED");
  return response.json() as Promise<ClientTextCreateOutput>;
}

export async function revealClientTextShare(secretId: string, secretCode?: string): Promise<ClientTextRevealOutput> {
  const response = await fetch(`/api/client-crypto/text/${encodeURIComponent(secretId)}/reveal`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(secretCode ? { secret_code: secretCode } : {}),
  });
  if (!response.ok) throw new ApiError(response.status, "REVEAL_CLIENT_TEXT_FAILED");
  return response.json() as Promise<ClientTextRevealOutput>;
}

export async function cancelClientTextShare(secretId: string, cancelCode: string): Promise<void> {
  const response = await fetch(`/api/client-crypto/text/${encodeURIComponent(secretId)}/cancel`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ cancel_code: cancelCode }),
  });
  if (!response.ok) throw new ApiError(response.status, "CANCEL_CLIENT_TEXT_FAILED");
}

export async function createClientFileShare(input: {
  filename: string;
  content_type: string;
  encrypted_key_b64: string;
  nonce_b64: string;
  ciphertext_b64: string;
  claim_token: string;
  expires_minutes: number;
}): Promise<ClientFileShare> {
  const response = await fetch("/api/client-crypto/file", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  if (!response.ok) throw new ApiError(response.status, "CREATE_CLIENT_FILE_FAILED");
  return response.json() as Promise<ClientFileShare>;
}

export async function getClientFileShare(shareId: string): Promise<ClientFileShare> {
  const response = await fetch(`/api/client-crypto/file/${encodeURIComponent(shareId)}`);
  if (!response.ok) throw new ApiError(response.status, "GET_CLIENT_FILE_FAILED");
  return response.json() as Promise<ClientFileShare>;
}

export async function getClientFileEnvelope(shareId: string, claimToken: string): Promise<ClientFileEnvelope> {
  const response = await fetch(`/api/client-crypto/file/${encodeURIComponent(shareId)}/envelope`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ claim_token: claimToken }),
  });
  if (!response.ok) throw new ApiError(response.status, "GET_CLIENT_FILE_ENVELOPE_FAILED");
  return response.json() as Promise<ClientFileEnvelope>;
}

export async function consumeClientFileShare(shareId: string, claimToken: string): Promise<void> {
  const response = await fetch(`/api/client-crypto/file/${encodeURIComponent(shareId)}/consume`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ claim_token: claimToken }),
  });
  if (!response.ok) throw new ApiError(response.status, "CONSUME_CLIENT_FILE_FAILED");
}
