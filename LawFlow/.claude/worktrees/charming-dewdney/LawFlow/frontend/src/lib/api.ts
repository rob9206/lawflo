import axios from "axios";
import { getStoredApiKey } from "@/lib/apiKey";
import {
  clearAuthSession,
  getAccessToken,
  getRefreshToken,
  getStoredUser,
  saveAuthSession,
} from "@/lib/authStorage";

const api = axios.create({
  baseURL: "/api",
  timeout: 120_000,
});

let refreshPromise: Promise<string> | null = null;

interface RetryableConfig {
  _retry?: boolean;
  headers?: Record<string, string>;
  url?: string;
}

async function refreshAccessToken(): Promise<string> {
  const refreshToken = getRefreshToken();
  if (!refreshToken) {
    throw new Error("No refresh token available");
  }

  if (!refreshPromise) {
    refreshPromise = axios
      .post("/api/auth/refresh", { refresh_token: refreshToken })
      .then((resp) => {
        const data = resp.data as {
          access_token: string;
          refresh_token: string;
          user: {
            id: string;
            email: string;
            display_name: string;
            avatar_url: string | null;
            tier: "free" | "pro";
            subscription_status: string;
          };
        };
        saveAuthSession({
          accessToken: data.access_token,
          refreshToken: data.refresh_token,
          user: data.user,
        });
        return data.access_token;
      })
      .finally(() => {
        refreshPromise = null;
      });
  }

  return refreshPromise;
}

api.interceptors.request.use((config) => {
  const key = getStoredApiKey();
  if (key) {
    config.headers = config.headers ?? {};
    (config.headers as Record<string, string>)["X-Anthropic-Api-Key"] = key;
  }

  const accessToken = getAccessToken();
  if (accessToken) {
    config.headers = config.headers ?? {};
    (config.headers as Record<string, string>).Authorization = `Bearer ${accessToken}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const status = error?.response?.status as number | undefined;
    const message = error?.response?.data?.error as string | undefined;
    const original = (error.config ?? {}) as RetryableConfig;

    if (status === 403 && message && message.toLowerCase().includes("free tier limit")) {
      const { toast } = await import("sonner");
      toast.error(message, {
        action: {
          label: "Upgrade",
          onClick: () => {
            window.location.href = "/pricing";
          },
        },
      });
    }

    const isAuthRoute = (original.url ?? "").includes("/auth/");
    if (status === 401 && !original._retry && !isAuthRoute) {
      try {
        original._retry = true;
        const freshToken = await refreshAccessToken();
        original.headers = original.headers ?? {};
        original.headers.Authorization = `Bearer ${freshToken}`;
        return api(original as any);
      } catch {
        clearAuthSession();
        if (window.location.pathname !== "/login") {
          const next = encodeURIComponent(window.location.pathname + window.location.search);
          window.location.href = `/login?next=${next}`;
        }
      }
    }

    if (status === 401 && isAuthRoute) {
      const user = getStoredUser();
      if (user) {
        clearAuthSession();
      }
    }

    return Promise.reject(error);
  }
);

export default api;
