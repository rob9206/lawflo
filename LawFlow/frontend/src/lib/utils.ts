import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatDate(iso: string | null): string {
  if (!iso) return "Never";
  return new Date(iso).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

export function masteryColor(score: number): string {
  if (score >= 80) return "text-green-400";
  if (score >= 60) return "text-emerald-400";
  if (score >= 40) return "text-yellow-400";
  if (score >= 20) return "text-orange-400";
  return "text-red-400";
}

export function masteryBg(score: number): string {
  if (score >= 80) return "bg-green-500/20";
  if (score >= 60) return "bg-emerald-500/20";
  if (score >= 40) return "bg-yellow-500/20";
  if (score >= 20) return "bg-orange-500/20";
  return "bg-red-500/20";
}
