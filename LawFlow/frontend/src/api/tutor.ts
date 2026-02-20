import api from "@/lib/api";
import type { TutorSession, TutorMode } from "@/types";

export async function getModes(): Promise<Record<string, TutorMode>> {
  const { data } = await api.get("/tutor/modes");
  return data;
}

export async function createSession(params: {
  mode: string;
  subject?: string;
  topics?: string[];
}): Promise<TutorSession> {
  const { data } = await api.post("/tutor/session", params);
  return data;
}

export async function getSession(sessionId: string): Promise<TutorSession> {
  const { data } = await api.get(`/tutor/session/${sessionId}`);
  return data;
}

export async function endSession(sessionId: string): Promise<TutorSession> {
  const { data } = await api.post(`/tutor/session/${sessionId}/end`);
  return data;
}

export async function sendMessageStream(
  sessionId: string,
  content: string,
  onChunk: (text: string) => void,
  onDone: () => void
): Promise<void> {
  const response = await fetch("/api/tutor/message", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId, content }),
  });

  if (!response.ok) {
    throw new Error(`Tutor API error: ${response.status}`);
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
        const text = line.slice(6);
        if (text === "[DONE]") {
          onDone();
          return;
        }
        if (text.startsWith("[ERROR]")) {
          throw new Error(text);
        }
        onChunk(text);
      }
    }
  }
  onDone();
}
