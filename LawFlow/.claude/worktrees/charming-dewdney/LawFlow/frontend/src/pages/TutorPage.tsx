import { useState, useRef, useEffect, useCallback } from "react";
import { useQuery } from "@tanstack/react-query";
import { useParams } from "react-router-dom";
import ReactMarkdown from "react-markdown";
import { createSession, getSession, sendMessageStream, getModes } from "@/api/tutor";
import { cleanMarkdown, cn } from "@/lib/utils";
import { SUBJECTS_SHORT, MODE_LABELS } from "@/lib/constants";
import Card from "@/components/ui/Card";
import PageHeader from "@/components/ui/PageHeader";
import SubjectFilter from "@/components/ui/SubjectFilter";
import {
  Send,
  GraduationCap,
  MessageSquare,
  BookOpen,
  Target,
  Lightbulb,
  Swords,
  ClipboardCheck,
} from "lucide-react";
import type { SessionMessage } from "@/types";

const MODE_ICONS: Record<string, React.ReactNode> = {
  socratic: <MessageSquare size={16} />,
  irac: <ClipboardCheck size={16} />,
  issue_spot: <Target size={16} />,
  hypo: <Swords size={16} />,
  explain: <Lightbulb size={16} />,
  exam_strategy: <BookOpen size={16} />,
};

export default function TutorPage() {
  const { sessionId: paramSessionId } = useParams();
  const [sessionId, setSessionId] = useState<string | null>(paramSessionId ?? null);
  const [selectedMode, setSelectedMode] = useState("explain");
  const [selectedSubject, setSelectedSubject] = useState("");
  const [messages, setMessages] = useState<SessionMessage[]>([]);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [streamingText, setStreamingText] = useState("");
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const { data: modes } = useQuery({
    queryKey: ["tutor-modes"],
    queryFn: getModes,
  });

  useEffect(() => {
    if (paramSessionId) {
      getSession(paramSessionId).then((s) => {
        if (s) {
          setSessionId(s.id);
          setMessages(s.messages || []);
        }
      });
    }
  }, [paramSessionId]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streamingText]);

  const startSession = useCallback(async () => {
    const session = await createSession({
      mode: selectedMode,
      subject: selectedSubject || undefined,
    });
    setSessionId(session.id);
    setMessages([]);
  }, [selectedMode, selectedSubject]);

  const sendMessage = useCallback(async () => {
    if (!input.trim() || !sessionId || streaming) return;

    const userMsg: SessionMessage = {
      id: crypto.randomUUID(),
      session_id: sessionId,
      role: "user",
      content: input.trim(),
      message_index: messages.length,
      created_at: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setStreaming(true);
    setStreamingText("");

    let accumulated = "";

    try {
      await sendMessageStream(
        sessionId,
        userMsg.content,
        (chunk) => {
          accumulated += chunk;
          setStreamingText(accumulated);
        },
        () => {
          const assistantMsg: SessionMessage = {
            id: crypto.randomUUID(),
            session_id: sessionId,
            role: "assistant",
            content: accumulated.trim(),
            message_index: messages.length + 1,
            created_at: new Date().toISOString(),
          };
          setMessages((prev) => [...prev, assistantMsg]);
          setStreamingText("");
          setStreaming(false);
        }
      );
    } catch (err) {
      setStreaming(false);
      setStreamingText("");
      console.error("Tutor error:", err);
    }
  }, [input, sessionId, streaming, messages.length]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  /* ── Session setup screen ─────────────────────────────────────────────── */
  if (!sessionId) {
    return (
      <div>
        <PageHeader icon={<GraduationCap size={24} />} title="AI Tutor" />

        <div className="max-w-2xl mt-6">
          <h3 style={{ fontSize: "13px", fontWeight: 800, textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: "12px", color: "var(--text-secondary)" }}>
            Study Mode
          </h3>
          <div className="grid grid-cols-3 gap-2 mb-6">
            {modes &&
              Object.entries(modes).map(([key, mode]) => (
                <Card
                  key={key}
                  padding="none"
                  className={cn(
                    "flex items-center gap-2 px-3 py-2.5 text-left cursor-pointer transition-all",
                    selectedMode === key
                      ? "!border-[var(--blue)] !bg-[var(--blue-bg)]"
                      : ""
                  )}
                  onClick={() => setSelectedMode(key)}
                >
                  <span style={{ color: selectedMode === key ? "var(--blue-dark)" : "var(--text-secondary)" }}>
                    {MODE_ICONS[key] || <GraduationCap size={16} />}
                  </span>
                  <div>
                    <p style={{
                      fontSize: "14px",
                      fontWeight: 700,
                      color: selectedMode === key ? "var(--blue-dark)" : "var(--text-primary)",
                    }}>
                      {mode.name}
                    </p>
                    <p className="line-clamp-2" style={{ fontSize: "12px", marginTop: "2px", color: "var(--text-muted)" }}>
                      {mode.description}
                    </p>
                  </div>
                </Card>
              ))}
          </div>

          <h3 style={{ fontSize: "13px", fontWeight: 800, textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: "8px", color: "var(--text-secondary)" }}>
            Subject Focus
          </h3>
          <div className="mb-6">
            <SubjectFilter
              subjects={SUBJECTS_SHORT}
              selected={selectedSubject}
              onSelect={setSelectedSubject}
            />
          </div>

          <button onClick={startSession} className="duo-btn duo-btn-green w-full" style={{ padding: "14px" }}>
            Start Study Session
          </button>
        </div>
      </div>
    );
  }

  /* ── Chat session ─────────────────────────────────────────────────────── */
  return (
    <div className="flex flex-col h-[calc(100vh-3rem)]">
      {/* Session header */}
      <div
        className="flex items-center gap-3 pb-4"
        style={{ borderBottom: "2px solid var(--border)" }}
      >
        <GraduationCap size={20} style={{ color: "var(--blue-dark)" }} />
        <div>
          <h2 style={{ fontWeight: 800, fontSize: "17px", color: "var(--text-primary)" }}>AI Tutor Session</h2>
          <p style={{ fontSize: "12px", color: "var(--text-muted)" }}>
            {MODE_LABELS[selectedMode] ?? selectedMode} · {selectedSubject || "all subjects"}
          </p>
        </div>
      </div>

      {/* Messages area */}
      <div className="flex-1 overflow-y-auto py-4 space-y-4">
        {messages.length === 0 && !streaming && (
          <div className="text-center py-12">
            <GraduationCap size={40} className="mx-auto mb-3" style={{ color: "var(--text-muted)" }} />
            <p style={{ color: "var(--text-muted)", fontWeight: 600 }}>
              Start by asking a question or describing what you want to study.
            </p>
            <p style={{ fontSize: "13px", marginTop: "4px", color: "var(--text-muted)" }}>
              Try: "Teach me consideration in contracts" or "Quiz me on negligence elements"
            </p>
          </div>
        )}

        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
          >
            {msg.role === "user" ? (
              <div
                className="rounded-2xl px-4 py-3"
                style={{
                  maxWidth: "85%",
                  fontSize: "15px",
                  fontWeight: 600,
                  backgroundColor: "var(--green)",
                  color: "white",
                }}
              >
                <p className="whitespace-pre-wrap">{msg.content}</p>
              </div>
            ) : (
              <div
                className="duo-card rounded-2xl px-4 py-3"
                style={{
                  maxWidth: "85%",
                  fontSize: "15px",
                  backgroundColor: "var(--blue-bg-subtle, var(--blue-bg))",
                  color: "var(--text-primary)",
                }}
              >
                <div className="prose-tutor">
                  <ReactMarkdown>{cleanMarkdown(msg.content)}</ReactMarkdown>
                </div>
              </div>
            )}
          </div>
        ))}

        {streaming && streamingText && (
          <div className="flex justify-start">
            <div
              className="duo-card rounded-2xl px-4 py-3"
              style={{
                maxWidth: "85%",
                fontSize: "15px",
                backgroundColor: "var(--blue-bg-subtle, var(--blue-bg))",
                color: "var(--text-primary)",
              }}
            >
              <div className="prose-tutor">
                <ReactMarkdown>
                  {cleanMarkdown(streamingText)}
                </ReactMarkdown>
              </div>
            </div>
          </div>
        )}

        {streaming && !streamingText && (
          <div className="flex justify-start">
            <div
              className="duo-card rounded-2xl px-4 py-3"
              style={{ backgroundColor: "var(--blue-bg-subtle, var(--blue-bg))" }}
            >
              <div className="flex gap-1">
                <span className="w-2 h-2 rounded-full animate-bounce" style={{ backgroundColor: "var(--text-muted)" }} />
                <span className="w-2 h-2 rounded-full animate-bounce [animation-delay:150ms]" style={{ backgroundColor: "var(--text-muted)" }} />
                <span className="w-2 h-2 rounded-full animate-bounce [animation-delay:300ms]" style={{ backgroundColor: "var(--text-muted)" }} />
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input bar — sticky bottom */}
      <div
        style={{
          borderTop: "2px solid var(--border)",
          backgroundColor: "var(--card-bg)",
          padding: "16px 0 0",
        }}
      >
        <div className="flex gap-2">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask a question, answer a prompt, or describe what to study..."
            rows={2}
            className="duo-input flex-1 rounded-xl px-4 py-3 resize-none"
            style={{ fontSize: "15px" }}
          />
          <button
            onClick={sendMessage}
            disabled={!input.trim() || streaming}
            className="duo-btn duo-btn-green self-end disabled:opacity-40 disabled:cursor-not-allowed"
            style={{
              padding: "12px",
              borderRadius: "50%",
              width: "48px",
              height: "48px",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
            title="Send message"
          >
            <Send size={18} />
          </button>
        </div>
      </div>
    </div>
  );
}
