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

export function masteryBarColor(score: number): string {
  if (score >= 80) return "#22c55e";
  if (score >= 60) return "#10b981";
  if (score >= 40) return "#f59e0b";
  if (score >= 20) return "#f97316";
  return "#ef4444";
}

export function masteryLabel(score: number): string {
  if (score >= 80) return "Mastered";
  if (score >= 60) return "Advanced";
  if (score >= 40) return "Proficient";
  if (score >= 20) return "Developing";
  return "Beginning";
}

export function scoreColor(score: number): string {
  if (score >= 80) return "#22c55e";
  if (score >= 60) return "#10b981";
  if (score >= 40) return "#f59e0b";
  if (score >= 20) return "#f97316";
  return "#ef4444";
}

export function scoreLabel(score: number): string {
  if (score >= 90) return "Excellent";
  if (score >= 80) return "Strong";
  if (score >= 70) return "Good";
  if (score >= 60) return "Adequate";
  if (score >= 50) return "Needs Work";
  if (score >= 35) return "Weak";
  return "Critical Gap";
}

export function priorityLevel(score: number): "high" | "medium" | "low" {
  if (score < 30) return "high";
  if (score < 55) return "medium";
  return "low";
}

/**
 * Clean up markdown formatting issues in AI-generated content.
 * Fixes concatenated words, unclosed tags, missing spaces, etc.
 */
export function cleanMarkdown(text: string): string {
  if (!text) return text;

  // Strip complete performance blocks.
  text = text.replace(/<performance>[\s\S]*?<\/performance>/g, "").trim();
  // Strip incomplete performance blocks that can appear while streaming.
  text = text.replace(/<performance>[\s\S]*$/g, "").trim();

  // Fix concatenated words (lowercase followed by uppercase)
  text = text.replace(/([a-z])([A-Z])/g, "$1 $2");

  // Fix missing spaces after punctuation (but preserve URLs and decimals)
  text = text.replace(/([.!?])([A-Za-z])/g, "$1 $2");
  text = text.replace(/([,;:])([A-Za-z])/g, "$1 $2");

  // Fix markdown headers missing spaces (e.g., "##Header" -> "## Header")
  text = text.replace(/(#{1,6})([A-Za-z])/g, "$1 $2");

  // Fix unclosed bold tags - ensure ** is always paired
  const boldCount = (text.match(/\*\*/g) || []).length;
  if (boldCount % 2 === 1) {
    // Odd number means unclosed tag, add closing at end
    text = text + "**";
  }

  // Fix broken markdown patterns
  // Remove extra whitespace but preserve intentional blank lines
  const lines = text.split("\n");
  const cleanedLines: string[] = [];
  let prevEmpty = false;
  
  for (const line of lines) {
    const stripped = line.trim();
    if (!stripped) {
      if (!prevEmpty) {
        cleanedLines.push("");
        prevEmpty = true;
      }
    } else {
      cleanedLines.push(stripped);
      prevEmpty = false;
    }
  }

  return cleanedLines.join("\n");
}
