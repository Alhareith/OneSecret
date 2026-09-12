import { ApiError } from "./api";

export type RsaKeyPair = {
  public_key_pem: string;
  private_key_pem: string;
};

export type RsaFileEncrypted = {
  filename: string;
  content_type: string;
  encrypted_key_b64: string;
  nonce_b64: string;
  ciphertext_b64: string;
};

export type RsaFileDecrypted = {
  filename: string;
  content_type: string;
  data_b64: string;
};

export type RsaFileShare = {
  id: string;
  filename: string;
  content_type: string;
  expires_at: string;
};

export async function generateRsaKeyPair(): Promise<RsaKeyPair> {
  const response = await fetch("/api/rsa-file/generate-keypair", {
    method: "POST",
  });
  if (!response.ok) {
    throw new ApiError(response.status, "GENERATE_KEYPAIR_FAILED");
  }

  return response.json() as Promise<RsaKeyPair>;
}

export async function encryptRsaFile(file: File, publicKeyPem: string): Promise<RsaFileEncrypted> {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("public_key_pem", publicKeyPem);

  const response = await fetch("/api/rsa-file/encrypt", {
    method: "POST",
    body: formData,
  });
  if (!response.ok) {
    throw new ApiError(response.status, "ENCRYPT_FILE_FAILED");
  }

  return response.json() as Promise<RsaFileEncrypted>;
}

export async function decryptRsaFile(
  payload: RsaFileEncrypted,
  privateKeyPem: string,
): Promise<RsaFileDecrypted> {
  const response = await fetch("/api/rsa-file/decrypt", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ...payload, private_key_pem: privateKeyPem }),
  });
  if (!response.ok) {
    throw new ApiError(response.status, "DECRYPT_FILE_FAILED");
  }

  return response.json() as Promise<RsaFileDecrypted>;
}

export async function createRsaFileShare(
  file: File,
  publicKeyPem: string,
  expiresMinutes: number,
): Promise<RsaFileShare> {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("public_key_pem", publicKeyPem);
  formData.append("expires_minutes", String(expiresMinutes));

  const response = await fetch("/api/rsa-file/share", {
    method: "POST",
    body: formData,
  });
  if (!response.ok) {
    throw new ApiError(response.status, "CREATE_FILE_SHARE_FAILED");
  }

  return response.json() as Promise<RsaFileShare>;
}

export async function getRsaFileShare(shareId: string): Promise<RsaFileShare> {
  const response = await fetch(`/api/rsa-file/share/${encodeURIComponent(shareId)}`);
  if (!response.ok) {
    throw new ApiError(response.status, "GET_FILE_SHARE_FAILED");
  }

  return response.json() as Promise<RsaFileShare>;
}

export async function revealRsaFileShare(
  shareId: string,
  privateKeyPem: string,
): Promise<RsaFileDecrypted> {
  const response = await fetch(`/api/rsa-file/share/${encodeURIComponent(shareId)}/reveal`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ private_key_pem: privateKeyPem }),
  });
  if (!response.ok) {
    throw new ApiError(response.status, "REVEAL_FILE_SHARE_FAILED");
  }

  return response.json() as Promise<RsaFileDecrypted>;
}
