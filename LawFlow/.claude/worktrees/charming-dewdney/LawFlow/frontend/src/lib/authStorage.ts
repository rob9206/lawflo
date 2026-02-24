export interface AuthUser {
  id: string;
  email: string;
  display_name: string;
  avatar_url: string | null;
  tier: "free" | "pro";
  subscription_status: string;
}

const ACCESS_TOKEN_KEY = "lawflow.auth.accessToken";
const REFRESH_TOKEN_KEY = "lawflow.auth.refreshToken";
const USER_KEY = "lawflow.auth.user";

export function getAccessToken(): string {
  return localStorage.getItem(ACCESS_TOKEN_KEY) ?? "";
}

export function getRefreshToken(): string {
  return localStorage.getItem(REFRESH_TOKEN_KEY) ?? "";
}

export function getStoredUser(): AuthUser | null {
  const raw = localStorage.getItem(USER_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as AuthUser;
  } catch {
    return null;
  }
}

export function saveAuthSession(payload: {
  accessToken: string;
  refreshToken: string;
  user: AuthUser;
}): void {
  localStorage.setItem(ACCESS_TOKEN_KEY, payload.accessToken);
  localStorage.setItem(REFRESH_TOKEN_KEY, payload.refreshToken);
  localStorage.setItem(USER_KEY, JSON.stringify(payload.user));
}

export function updateStoredUser(user: AuthUser): void {
  localStorage.setItem(USER_KEY, JSON.stringify(user));
}

export function clearAuthSession(): void {
  localStorage.removeItem(ACCESS_TOKEN_KEY);
  localStorage.removeItem(REFRESH_TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
}
