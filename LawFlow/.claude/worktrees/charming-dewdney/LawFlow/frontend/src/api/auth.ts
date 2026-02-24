import api from "@/lib/api";
import type { AuthUser } from "@/lib/authStorage";

export interface AuthTokensResponse {
  user: AuthUser;
  access_token: string;
  refresh_token: string;
  token_type: "Bearer";
  expires_in_seconds: number;
}

export async function register(params: {
  email: string;
  password: string;
  display_name?: string;
}): Promise<AuthTokensResponse> {
  const { data } = await api.post("/auth/register", params);
  return data;
}

export async function login(params: {
  email: string;
  password: string;
}): Promise<AuthTokensResponse> {
  const { data } = await api.post("/auth/login", params);
  return data;
}

export async function refresh(refreshToken: string): Promise<AuthTokensResponse> {
  const { data } = await api.post("/auth/refresh", { refresh_token: refreshToken });
  return data;
}

export async function getMe(): Promise<AuthUser> {
  const { data } = await api.get("/auth/me");
  return data;
}

export async function updateProfile(payload: {
  display_name?: string;
  avatar_url?: string;
}): Promise<AuthUser> {
  const { data } = await api.put("/auth/update-profile", payload);
  return data;
}

export async function changePassword(payload: {
  current_password: string;
  new_password: string;
}): Promise<{ status: string }> {
  const { data } = await api.post("/auth/change-password", payload);
  return data;
}
