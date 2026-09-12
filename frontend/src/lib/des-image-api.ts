export class DesImageApiError extends Error {
  constructor(public readonly status: number, message: string) {
    super(message);
  }
}

export type DesImageEncrypted = {
  filename: string;
  content_type: string;
  key_b64: string;
  iv_b64: string;
  ciphertext_b64: string;
};

export type DesImageDecrypted = {
  filename: string;
  content_type: string;
  data_b64: string;
};

export type DesImageShareCreated = {
  id: string;
  filename: string;
  content_type: string;
  expires_at: string;
  key_fragment: string;
};

export type DesImageShareInfo = {
  id: string;
  filename: string;
  content_type: string;
  expires_at: string;
};

export type DesImageRevealResponse = {
  id: string;
  filename: string;
  content_type: string;
  data_b64: string;
};

async function requireOk(response: Response, message: string): Promise<Response> {
  if (!response.ok) throw new DesImageApiError(response.status, message);
  return response;
}

export async function encryptDesImage(file: File): Promise<DesImageEncrypted> {
  const formData = new FormData();
  formData.append("file", file);
  const response = await fetch("/api/des-image/encrypt", { method: "POST", body: formData });
  await requireOk(response, "فشل تشفير الصورة.");
  return response.json() as Promise<DesImageEncrypted>;
}

export async function decryptDesImage(payload: DesImageEncrypted): Promise<DesImageDecrypted> {
  const response = await fetch("/api/des-image/decrypt", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  await requireOk(response, "فشل فك تشفير الصورة.");
  return response.json() as Promise<DesImageDecrypted>;
}

export async function createDesImageShare(file: File, expiresMinutes: number): Promise<DesImageShareCreated> {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("expires_minutes", String(expiresMinutes));
  const response = await fetch("/api/des-image/share", { method: "POST", body: formData });
  await requireOk(response, "تعذر تشفير الصورة وإنشاء رابط المشاركة.");
  return response.json() as Promise<DesImageShareCreated>;
}

export async function getDesImageShare(shareId: string): Promise<DesImageShareInfo> {
  const response = await fetch(`/api/des-image/share/${encodeURIComponent(shareId)}`);
  await requireOk(response, "تعذر الوصول إلى الصورة المشفرة.");
  return response.json() as Promise<DesImageShareInfo>;
}

export async function revealDesImageShare(shareId: string, keyFragment: string): Promise<DesImageRevealResponse> {
  const response = await fetch(`/api/des-image/share/${encodeURIComponent(shareId)}/reveal`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ key_fragment: keyFragment }),
  });
  await requireOk(response, "تعذر فك تشفير الصورة.");
  return response.json() as Promise<DesImageRevealResponse>;
}
