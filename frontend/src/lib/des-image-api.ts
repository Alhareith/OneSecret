// العقد النهائي لاتصال واجهة ملاطف بمسار صور DES.
// هذا الملف لا يحتوي React ولا منطق DES؛ فقط أنواع البيانات وطلبات fetch.

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

export async function encryptDesImage(file: File): Promise<DesImageEncrypted> {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch("/api/des-image/encrypt", {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    throw new Error("Failed to encrypt image. Please check the file and try again.");
  }

  return response.json();
}

export async function decryptDesImage(payload: DesImageEncrypted): Promise<DesImageDecrypted> {
  const response = await fetch("/api/des-image/decrypt", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw new Error("Failed to decrypt image. Invalid data or key.");
  }

  return response.json();
}

// عقد التنفيذ:
// encryptDesImage: FormData بحقل file -> POST /api/des-image/encrypt.
// decryptDesImage: JSON من DesImageEncrypted -> POST /api/des-image/decrypt.
// عند !response.ok ارمِ خطأ عامًا فقط؛ لا تفسر تفاصيل تشفير حساسة هنا.
