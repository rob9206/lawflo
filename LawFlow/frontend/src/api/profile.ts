import api from "@/lib/api";

export interface ProfileStats {
  total_subjects: number;
  total_topics: number;
  overall_mastery: number;
  total_study_hours: number;
  total_sessions: number;
  total_assessments: number;
  total_documents: number;
  total_flashcards: number;
}

export interface ApiKeyStatus {
  anthropic: {
    configured: boolean;
    masked: string;
    model: string;
  };
}

export async function getProfileStats(): Promise<ProfileStats> {
  const { data } = await api.get("/profile/stats");
  return data;
}

export async function getApiKeys(): Promise<ApiKeyStatus> {
  const { data } = await api.get("/profile/api-keys");
  return data;
}

export async function saveApiKeys(
  payload: { anthropic_key?: string; model?: string }
): Promise<{ status: string; updated: string[] }> {
  const { data } = await api.post("/profile/api-keys", payload);
  return data;
}

export async function resetProgress(): Promise<{ status: string }> {
  const { data } = await api.post("/profile/reset-progress");
  return data;
}

export async function resetAll(): Promise<{ status: string }> {
  const { data } = await api.post("/profile/reset-all");
  return data;
}

export async function exportData(): Promise<void> {
  const response = await api.get("/profile/export", { responseType: "blob" });
  const url = URL.createObjectURL(response.data);
  const a = document.createElement("a");
  a.href = url;
  const disposition: string = response.headers["content-disposition"] ?? "";
  const match = disposition.match(/filename="?([^"]+)"?/);
  a.download = match ? match[1] : "lawflow_backup.json";
  a.click();
  URL.revokeObjectURL(url);
}

export async function importData(
  file: File
): Promise<{ status: string; imported: Record<string, number> }> {
  const form = new FormData();
  form.append("file", file);
  const { data } = await api.post("/profile/import", form, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
}