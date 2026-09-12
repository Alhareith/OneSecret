export const AES_KEY_BYTES = 32;
export const AES_GCM_NONCE_BYTES = 12;
export const RSA_MODULUS_BITS = 2048;

export type BrowserTextEnvelope = {
  ciphertext_b64: string;
  nonce_b64: string;
  key_fragment: string;
};

export type BrowserFileEnvelope = {
  encrypted_key_b64: string;
  nonce_b64: string;
  ciphertext_b64: string;
  private_key_fragment: string;
};

function requireWebCrypto(): SubtleCrypto {
  if (!globalThis.crypto?.subtle) {
    throw new Error("WEB_CRYPTO_UNAVAILABLE");
  }
  return globalThis.crypto.subtle;
}

function randomBytes(length: number): Uint8Array {
  const bytes = new Uint8Array(length);
  globalThis.crypto.getRandomValues(bytes);
  return bytes;
}

function toArrayBuffer(bytes: Uint8Array): ArrayBuffer {
  return bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength) as ArrayBuffer;
}

export function bytesToBase64(bytes: Uint8Array): string {
  let binary = "";
  const chunkSize = 0x8000;
  for (let offset = 0; offset < bytes.length; offset += chunkSize) {
    const chunk = bytes.subarray(offset, Math.min(offset + chunkSize, bytes.length));
    binary += String.fromCharCode(...chunk);
  }
  return btoa(binary);
}

export function base64ToBytes(value: string): Uint8Array {
  const binary = atob(value);
  const bytes = new Uint8Array(binary.length);
  for (let index = 0; index < binary.length; index += 1) bytes[index] = binary.charCodeAt(index);
  return bytes;
}

export function bytesToBase64Url(bytes: Uint8Array): string {
  return bytesToBase64(bytes).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/g, "");
}

export function base64UrlToBytes(value: string): Uint8Array {
  const normalized = value.replace(/-/g, "+").replace(/_/g, "/");
  const padded = normalized + "=".repeat((4 - (normalized.length % 4)) % 4);
  return base64ToBytes(padded);
}

async function importAesKey(rawKey: Uint8Array, usages: KeyUsage[]): Promise<CryptoKey> {
  if (rawKey.byteLength !== AES_KEY_BYTES) throw new Error("INVALID_AES_KEY");
  return requireWebCrypto().importKey(
    "raw",
    toArrayBuffer(rawKey),
    { name: "AES-GCM", length: 256 },
    false,
    usages,
  );
}

export async function encryptTextInBrowser(plaintext: string): Promise<BrowserTextEnvelope> {
  const subtle = requireWebCrypto();
  const keyBytes = randomBytes(AES_KEY_BYTES);
  const nonce = randomBytes(AES_GCM_NONCE_BYTES);
  const key = await importAesKey(keyBytes, ["encrypt"]);
  const plaintextBytes = new TextEncoder().encode(plaintext);
  const ciphertext = await subtle.encrypt(
    { name: "AES-GCM", iv: toArrayBuffer(nonce), tagLength: 128 },
    key,
    toArrayBuffer(plaintextBytes),
  );

  return {
    ciphertext_b64: bytesToBase64(new Uint8Array(ciphertext)),
    nonce_b64: bytesToBase64(nonce),
    key_fragment: bytesToBase64Url(keyBytes),
  };
}

export async function decryptTextInBrowser(
  ciphertextB64: string,
  nonceB64: string,
  keyFragment: string,
): Promise<string> {
  const subtle = requireWebCrypto();
  const keyBytes = base64UrlToBytes(keyFragment);
  const nonce = base64ToBytes(nonceB64);
  const ciphertext = base64ToBytes(ciphertextB64);
  if (nonce.byteLength !== AES_GCM_NONCE_BYTES) throw new Error("INVALID_NONCE");

  const key = await importAesKey(keyBytes, ["decrypt"]);
  const plaintext = await subtle.decrypt(
    { name: "AES-GCM", iv: toArrayBuffer(nonce), tagLength: 128 },
    key,
    toArrayBuffer(ciphertext),
  );
  return new TextDecoder().decode(plaintext);
}

export async function encryptFileInBrowser(file: File): Promise<BrowserFileEnvelope> {
  const subtle = requireWebCrypto();
  const rsaPair = await subtle.generateKey(
    {
      name: "RSA-OAEP",
      modulusLength: RSA_MODULUS_BITS,
      publicExponent: new Uint8Array([1, 0, 1]),
      hash: "SHA-256",
    },
    true,
    ["encrypt", "decrypt"],
  ) as CryptoKeyPair;

  const aesKeyBytes = randomBytes(AES_KEY_BYTES);
  const nonce = randomBytes(AES_GCM_NONCE_BYTES);
  const aesKey = await importAesKey(aesKeyBytes, ["encrypt"]);
  const fileBytes = new Uint8Array(await file.arrayBuffer());

  const ciphertext = await subtle.encrypt(
    { name: "AES-GCM", iv: toArrayBuffer(nonce), tagLength: 128 },
    aesKey,
    toArrayBuffer(fileBytes),
  );
  const encryptedKey = await subtle.encrypt(
    { name: "RSA-OAEP" },
    rsaPair.publicKey,
    toArrayBuffer(aesKeyBytes),
  );
  const privateKeyPkcs8 = await subtle.exportKey("pkcs8", rsaPair.privateKey);

  return {
    encrypted_key_b64: bytesToBase64(new Uint8Array(encryptedKey)),
    nonce_b64: bytesToBase64(nonce),
    ciphertext_b64: bytesToBase64(new Uint8Array(ciphertext)),
    private_key_fragment: bytesToBase64Url(new Uint8Array(privateKeyPkcs8)),
  };
}

export async function decryptFileInBrowser(
  envelope: Pick<BrowserFileEnvelope, "encrypted_key_b64" | "nonce_b64" | "ciphertext_b64">,
  privateKeyFragment: string,
  contentType: string,
): Promise<Blob> {
  const subtle = requireWebCrypto();
  const privateKeyBytes = base64UrlToBytes(privateKeyFragment);
  const privateKey = await subtle.importKey(
    "pkcs8",
    toArrayBuffer(privateKeyBytes),
    { name: "RSA-OAEP", hash: "SHA-256" },
    false,
    ["decrypt"],
  );

  const encryptedKey = base64ToBytes(envelope.encrypted_key_b64);
  const rawAesKey = await subtle.decrypt(
    { name: "RSA-OAEP" },
    privateKey,
    toArrayBuffer(encryptedKey),
  );
  const aesKey = await importAesKey(new Uint8Array(rawAesKey), ["decrypt"]);
  const nonce = base64ToBytes(envelope.nonce_b64);
  const ciphertext = base64ToBytes(envelope.ciphertext_b64);
  if (nonce.byteLength !== AES_GCM_NONCE_BYTES) throw new Error("INVALID_NONCE");

  const plaintext = await subtle.decrypt(
    { name: "AES-GCM", iv: toArrayBuffer(nonce), tagLength: 128 },
    aesKey,
    toArrayBuffer(ciphertext),
  );
  return new Blob([plaintext], { type: contentType || "application/octet-stream" });
}

export function generateClaimToken(): string {
  return bytesToBase64Url(randomBytes(32));
}
