// العقد النهائي لاتصال واجهة أيمن بمسار ملفات RSA.
// هذا الملف لا يحتوي React ولا منطق RSA/AES؛ فقط أنواع البيانات وطلبات fetch.

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
  throw new Error("RSA_KEYPAIR_NOT_IMPLEMENTED");
}

export async function encryptRsaFile(file: File, publicKeyPem: string): Promise<RsaFileEncrypted> {
  void file;
  void publicKeyPem;
  throw new Error("RSA_FILE_ENCRYPT_NOT_IMPLEMENTED");
}

export async function decryptRsaFile(
  payload: RsaFileEncrypted,
  privateKeyPem: string,
): Promise<RsaFileDecrypted> {
  void payload;
  void privateKeyPem;
  throw new Error("RSA_FILE_DECRYPT_NOT_IMPLEMENTED");
}

// عقد التنفيذ:
// generateRsaKeyPair: POST /api/rsa-file/generate-keypair.
// encryptRsaFile: FormData بحقل file وحقل public_key_pem -> POST /api/rsa-file/encrypt.
// decryptRsaFile: JSON يجمع الحزمة المشفرة مع private_key_pem -> POST /api/rsa-file/decrypt.
// عند !response.ok ارمِ خطأ عامًا فقط، ولا تطبع PEM أو ciphertext في console.
