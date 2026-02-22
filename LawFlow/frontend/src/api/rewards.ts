import api from "@/lib/api";
import type { RewardsSummary, Achievement, RewardsLedger } from "@/types";

export async function getRewardsSummary(): Promise<RewardsSummary> {
  const { data } = await api.get("/rewards/summary");
  return data;
}

export async function getAchievements(): Promise<Achievement[]> {
  const { data } = await api.get("/rewards/achievements");
  return data;
}

export async function getRewardsLedger(params?: {
  limit?: number;
  offset?: number;
  type?: string;
}): Promise<RewardsLedger> {
  const { data } = await api.get("/rewards/ledger", { params });
  return data;
}
