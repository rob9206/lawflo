const API_KEY_STORAGE_KEY = "lawflow.anthropicApiKey";
const QUOTE_CHARS = new Set(["\"", "'", "`"]);

function normalizeApiKey(raw: string): string {
  let key = raw.trim();
  if (!key) return "";

  if (key.toLowerCase().startsWith("bearer ")) {
    key = key.slice(7).trim();
  }

  while (key.length >= 2 && QUOTE_CHARS.has(key[0]) && QUOTE_CHARS.has(key[key.length - 1])) {
    key = key.slice(1, -1).trim();
  }

  return key;
}

export function getStoredApiKey(): string {
  if (typeof window === "undefined") return "";
  const raw = window.localStorage.getItem(API_KEY_STORAGE_KEY) ?? "";
  return normalizeApiKey(raw);
}

export function saveApiKey(raw: string): string {
  const normalized = normalizeApiKey(raw);
  if (typeof window !== "undefined") {
    if (normalized) {
      window.localStorage.setItem(API_KEY_STORAGE_KEY, normalized);
    } else {
      window.localStorage.removeItem(API_KEY_STORAGE_KEY);
    }
  }
  return normalized;
}

export function clearApiKey(): void {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(API_KEY_STORAGE_KEY);
}

export function maskApiKey(key: string): string {
  if (!key) return "Not set";
  if (key.length <= 14) return key;
  return `${key.slice(0, 10)}...${key.slice(-4)}`;
}

export function looksLikeAnthropicKey(key: string): boolean {
  return key.startsWith("sk-ant-") && key.length >= 40;
}
