import axios from "axios";
import { getStoredApiKey } from "@/lib/apiKey";

const api = axios.create({
  baseURL: "/api",
  timeout: 120_000,
});

api.interceptors.request.use((config) => {
  const key = getStoredApiKey();
  if (key) {
    config.headers = config.headers ?? {};
    (config.headers as Record<string, string>)["X-Anthropic-Api-Key"] = key;
  }
  return config;
});

export default api;
