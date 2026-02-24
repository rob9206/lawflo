import api from "@/lib/api";

export interface BillingStatus {
  tier: "free" | "pro";
  subscription_status: string;
  usage: Record<string, number>;
  limits: Record<string, number>;
}

export async function getBillingStatus(): Promise<BillingStatus> {
  const { data } = await api.get("/billing/status");
  return data;
}

export async function createCheckout(): Promise<{ url: string; session_id: string }> {
  const { data } = await api.post("/billing/create-checkout");
  return data;
}

export async function createPortal(): Promise<{ url: string }> {
  const { data } = await api.post("/billing/create-portal");
  return data;
}
