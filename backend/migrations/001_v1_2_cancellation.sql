-- OneSecret V1.2: مواد رمز الإلغاء المشتقة ووقت الإلغاء.
-- ينفذ هذا الترحيل مرة واحدة فقط عبر أداة ترحيل قاعدة البيانات المعتمدة.
-- لا ينشئ رمز إلغاء للرسائل السابقة؛ تظل قابلة للعمل حتى انتهاء صلاحيتها.

ALTER TABLE secrets
    MODIFY COLUMN ciphertext TEXT NULL,
    MODIFY COLUMN nonce VARCHAR(64) NULL,
    ADD COLUMN cancelled_at DATETIME(6) NULL AFTER used_at,
    ADD COLUMN cancel_code_salt VARCHAR(64) NULL,
    ADD COLUMN cancel_code_hash VARCHAR(128) NULL;
