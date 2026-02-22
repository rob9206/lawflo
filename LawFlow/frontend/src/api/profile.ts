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

export async function getProfileStats(): Promise<ProfileStats> {
  const { data } = await api.get("/profile/stats");
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