// مساحة عميل API الخاصة بملفات RSA لأيمن.
// توضع هنا فقط أنواع البيانات ودوال الاتصال بمسارات /api/rsa-file.

export type RsaFileResult = {
  filename: string;
  contentType: string;
  data: string;
};

// تضاف دوال رفع الملف والتشفير وفك التشفير هنا.
