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
  void file;
  throw new Error("DES_IMAGE_ENCRYPT_NOT_IMPLEMENTED");
}

export async function decryptDesImage(payload: DesImageEncrypted): Promise<DesImageDecrypted> {
  void payload;
  throw new Error("DES_IMAGE_DECRYPT_NOT_IMPLEMENTED");
}

// عقد التنفيذ:
// encryptDesImage: FormData بحقل file -> POST /api/des-image/encrypt.
// decryptDesImage: JSON من DesImageEncrypted -> POST /api/des-image/decrypt.
// عند !response.ok ارمِ خطأ عامًا فقط؛ لا تفسر تفاصيل تشفير حساسة هنا.
