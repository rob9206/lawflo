import api from "@/lib/api";
import { getStoredApiKey } from "@/lib/apiKey";
import { getAccessToken } from "@/lib/authStorage";

export interface TeachingTarget {
  subject: string;
  topic: string;
  display_name: string;
  priority_score: number;
  mastery: number;
  exam_weight: number;
  recommended_mode: string;
  mode_reason: string;
  knowledge_chunks_available: number;
  time_estimate_minutes: number;
}

export interface TeachingPlan {
  subject: string;
  subject_display: string;
  has_exam_data: boolean;
  teaching_plan: TeachingTarget[];
  total_estimated_minutes: number;
  /** Shown when teaching_plan is empty (e.g. "No topics found. Run the seed script first.") */
  message?: string;
  auto_session: {
    mode: string;
    subject: string;
    topics: string[];
    opening_message: string;
  } | null;
}

export interface ExamBlueprint {
  id: string;
  document_id: string;
  subject: string;
  exam_title: string | null;
  exam_format: string | null;
  total_questions: number | null;
  time_limit_minutes: number | null;
  professor_patterns: string | null;
  high_yield_summary: string | null;
  topics_tested: {
    topic: string;
    weight: number;
    question_format: string | null;
    difficulty: number;
    notes: string | null;
  }[];
}

export async function getTeachingPlan(
  subject: string,
  params?: { max_topics?: number; available_minutes?: number }
): Promise<TeachingPlan> {
  const { data } = await api.get(`/auto-teach/plan/${subject}`, { params });
  return data;
}

/** Run subject/topic seed so AutoTeach has topics. Safe to call multiple times. */
export async function runSeed(): Promise<{ status: string; message: string }> {
  const { data } = await api.post("/seed");
  return data;
}

export async function getNextTopic(subject: string): Promise<TeachingTarget | null> {
  const { data } = await api.get(`/auto-teach/next/${subject}`);
  return data;
}

export async function startAutoSession(
  subject: string,
  topic?: string,
  onChunk?: (text: string) => void,
  onDone?: (sessionId: string, mode: string, topic: string) => void,
  availableMinutes?: number,
): Promise<void> {
  const key = getStoredApiKey();
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (key) {
    headers["X-Anthropic-Api-Key"] = key;
  }
  const accessToken = getAccessToken();
  if (accessToken) {
    headers.Authorization = `Bearer ${accessToken}`;
  }

  const response = await fetch("/api/auto-teach/start", {
    method: "POST",
    headers,
    body: JSON.stringify({ subject, topic, available_minutes: availableMinutes }),
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`Auto-teach error: ${response.status} - ${errorText}`);
  }

  const sessionId = response.headers.get("X-Session-Id") || "";
  const mode = response.headers.get("X-Tutor-Mode") || "";
  const resolvedTopic = response.headers.get("X-Topic") || "";
  if (!sessionId.trim()) {
    throw new Error("Auto-teach session did not return a valid session id");
  }

  const reader = response.body?.getReader();
  if (!reader) throw new Error("No response body");

  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() || "";

    for (const line of lines) {
      if (line.startsWith("data: ")) {
        const raw = line.slice(6);
        if (raw === "[DONE]") {
          onDone?.(sessionId, mode, resolvedTopic);
          return;
        }
        if (raw.startsWith("[ERROR]")) {
          throw new Error(raw.slice(7).trim() || "Auto-teach session error");
        }
        try {
          onChunk?.(JSON.parse(raw));
        } catch {
          onChunk?.(raw);
        }
      }
    }
  }
  onDone?.(sessionId, mode, resolvedTopic);
}

export async function analyzeExam(documentId: string): Promise<ExamBlueprint> {
  const { data } = await api.post(`/auto-teach/exam/analyze/${documentId}`);
  return data;
}

export async function getExamBlueprints(subject?: string): Promise<ExamBlueprint[]> {
  const { data } = await api.get("/auto-teach/exam/blueprints", {
    params: subject ? { subject } : undefined,
  });
  return data;
}
