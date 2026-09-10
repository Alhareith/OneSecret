// مساحة عميل API الخاصة بصور DES لملاطف.
// توضع هنا فقط أنواع البيانات ودوال الاتصال بمسارات /api/des-image.

export type DesImageResult = {
  filename: string;
  contentType: string;
  data: string;
};

// تضاف دوال رفع الصورة والتشفير وفك التشفير هنا.
