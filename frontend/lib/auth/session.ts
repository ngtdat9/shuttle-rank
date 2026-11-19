const DEV_TOKEN_KEY = "shuttle-rank.dev-admin-token";

export function readDevToken(): string | null {
  if (typeof window === "undefined") return null;
  const value = sessionStorage.getItem(DEV_TOKEN_KEY);
  if (!value) return null;
  const trimmed = value.trim();
  return trimmed.length > 0 ? trimmed : null;
}

export function writeDevToken(token: string): void {
  sessionStorage.setItem(DEV_TOKEN_KEY, token);
}

export function clearDevToken(): void {
  if (typeof window === "undefined") return;
  sessionStorage.removeItem(DEV_TOKEN_KEY);
}
