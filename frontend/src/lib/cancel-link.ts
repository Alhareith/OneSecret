const SECRET_ID_PATTERN = /^[a-f0-9]{48}$/;

/** يستخرج معرّف OneSecret من معرّف خام أو من رابط مشاركة، محليًا فقط. */
export function extractSecretIdForCancellation(value: string): string | null {
  const trimmedValue = value.trim();
  if (SECRET_ID_PATTERN.test(trimmedValue)) return trimmedValue;

  try {
    const url = new URL(trimmedValue);
    const match = url.pathname.match(/^\/s\/([a-f0-9]{48})$/);
    return match?.[1] ?? null;
  } catch {
    return null;
  }
}
