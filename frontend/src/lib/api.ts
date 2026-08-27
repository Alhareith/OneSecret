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

export class ApiError extends Error {
  constructor(public readonly status: number, code: string) {
    super(code);
  }
}

export async function createSecret(input: CreateSecretInput): Promise<CreateSecretOutput> {
  const response = await fetch("/api/secrets", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });

  if (!response.ok) {
    throw new ApiError(response.status, "CREATE_SECRET_FAILED");
  }

  return response.json() as Promise<CreateSecretOutput>;
}

export async function getSecretStatus(secretId: string): Promise<SecretStatusOutput> {
  const response = await fetch(`/api/secrets/${encodeURIComponent(secretId)}/status`);
  if (!response.ok) throw new Error("STATUS_SECRET_FAILED");

  return response.json() as Promise<SecretStatusOutput>;
}

export async function revealSecret(secretId: string, secretCode?: string): Promise<RevealSecretOutput> {
  const response = await fetch(`/api/secrets/${encodeURIComponent(secretId)}/reveal`, {
    method: "POST",
    ...(secretCode ? { headers: { "Content-Type": "application/json" }, body: JSON.stringify({ secret_code: secretCode }) } : {}),
  });
  if (!response.ok) throw new ApiError(response.status, "REVEAL_SECRET_FAILED");

  return response.json() as Promise<RevealSecretOutput>;
}
