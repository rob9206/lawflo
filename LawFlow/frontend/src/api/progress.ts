import api from "@/lib/api";
import type { DashboardData, SubjectMastery, TopicMastery } from "@/types";

export async function getDashboard(): Promise<DashboardData> {
  const { data } = await api.get("/progress/dashboard");
  return data;
}

export async function getMastery(): Promise<SubjectMastery[]> {
  const { data } = await api.get("/progress/mastery");
  return data;
}

export async function getSubjectMastery(
  subject: string
): Promise<SubjectMastery & { topics: TopicMastery[] }> {
  const { data } = await api.get(`/progress/mastery/${subject}`);
  return data;
}

export async function getWeaknesses(limit?: number): Promise<TopicMastery[]> {
  const { data } = await api.get("/progress/weaknesses", {
    params: { limit },
  });
  return data;
}
