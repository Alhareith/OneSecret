export const CANCEL_CODE_PATTERN = /^[A-HJ-NP-Z2-9]{5}$/;

export function normalizeCancelCode(value: string): string {
  return value.trim().toUpperCase();
}

export function isValidCancelCode(value: string): boolean {
  return CANCEL_CODE_PATTERN.test(normalizeCancelCode(value));
}
