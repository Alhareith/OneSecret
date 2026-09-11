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