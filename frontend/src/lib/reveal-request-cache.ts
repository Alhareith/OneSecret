export function createRevealRequestCache<T>(requestReveal: (secretId: string) => Promise<T>) {
  let current: { secretId: string; request: Promise<T> } | null = null;

  return {
    get(secretId: string): Promise<T> {
      if (current?.secretId !== secretId) {
        current = { secretId, request: requestReveal(secretId) };
      }
      return current.request;
    },
  };
}
