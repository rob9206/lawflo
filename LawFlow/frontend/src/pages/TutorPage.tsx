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

  if (!sessionId) {
    return (
      <div>
        <PageHeader icon={<GraduationCap size={24} />} title="AI Tutor" />

        <div className="max-w-2xl mt-6">
          <h3 className="text-sm font-medium mb-3 text-ui-secondary">Study Mode</h3>
          <div className="grid grid-cols-3 gap-2 mb-6">
            {modes &&
              Object.entries(modes).map(([key, mode]) => (
                <Card
                  key={key}
                  padding="none"
                  className={cn(
                    "flex items-center gap-2 px-3 py-2.5 text-sm text-left cursor-pointer transition-all",
                    selectedMode === key
                      ? "ring-1 ring-[var(--accent)] bg-[var(--accent-muted)] text-accent-label"
                      : "text-ui-secondary"
                  )}
                  onClick={() => setSelectedMode(key)}
                >
                  {MODE_ICONS[key] || <GraduationCap size={16} />}
                  <div>
                    <p className="font-medium">{mode.name}</p>
                    <p className="text-xs mt-0.5 line-clamp-2 text-ui-muted">
                      {mode.description}
                    </p>
                  </div>
                </Card>
              ))}
          </div>

          <h3 className="text-sm font-medium mb-2 text-ui-secondary">Subject Focus</h3>
          <div className="mb-6">
            <SubjectFilter
              subjects={SUBJECTS_SHORT}
              selected={selectedSubject}
              onSelect={setSelectedSubject}
            />
          </div>

          <button onClick={startSession} className="btn-primary w-full py-3">
            Start Study Session
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-[calc(100vh-3rem)]">
      <div className="flex items-center gap-3 pb-4 border-b border-[var(--border)]">
        <GraduationCap size={20} className="text-accent-label" />
        <div>
          <h2 className="font-semibold text-ui-primary">AI Tutor Session</h2>
          <p className="text-xs text-ui-muted">
            {MODE_LABELS[selectedMode] ?? selectedMode} · {selectedSubject || "all subjects"}
          </p>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto py-4 space-y-4">
        {messages.length === 0 && !streaming && (
          <div className="text-center py-12">
            <GraduationCap size={40} className="mx-auto mb-3 text-ui-muted" />
            <p className="text-ui-muted">
              Start by asking a question or describing what you want to study.
            </p>
            <p className="text-xs mt-1 text-ui-muted">
              Try: "Teach me consideration in contracts" or "Quiz me on negligence elements"
            </p>
          </div>
        )}

        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
          >
            <div
              className="max-w-[80%] rounded-2xl px-4 py-3 text-sm"
              style={
                msg.role === "user"
                  ? { backgroundColor: "var(--accent)", color: "#fff" }
                  : {
                      backgroundColor: "var(--bg-card)",
                      border: "1px solid var(--border)",
                      color: "var(--text-primary)",
                    }
              }
            >
              {msg.role === "assistant" ? (
                <div className="prose-tutor">
                  <ReactMarkdown>{cleanMarkdown(msg.content)}</ReactMarkdown>
                </div>
              ) : (
                <p className="whitespace-pre-wrap">{msg.content}</p>
              )}
            </div>
          </div>
        ))}

        {streaming && streamingText && (
          <div className="flex justify-start">
            <div
              className="max-w-[80%] rounded-2xl px-4 py-3 text-sm"
              style={{
                backgroundColor: "var(--bg-card)",
                border: "1px solid var(--border)",
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
            <Card padding="none" className="rounded-2xl px-4 py-3">
              <div className="flex gap-1">
                <span className="w-2 h-2 rounded-full animate-bounce bg-[var(--text-muted)]" />
                <span className="w-2 h-2 rounded-full animate-bounce [animation-delay:150ms] bg-[var(--text-muted)]" />
                <span className="w-2 h-2 rounded-full animate-bounce [animation-delay:300ms] bg-[var(--text-muted)]" />
              </div>
            </Card>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      <div className="pt-4 border-t border-[var(--border)]">
        <div className="flex gap-2">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask a question, answer a prompt, or describe what to study..."
            rows={2}
            className="input-base flex-1 rounded-xl px-4 py-3 text-sm resize-none"
          />
          <button
            onClick={sendMessage}
            disabled={!input.trim() || streaming}
            className="btn-primary self-end p-3 rounded-xl disabled:opacity-40 disabled:cursor-not-allowed"
            title="Send message"
          >
            <Send size={18} />
          </button>
        </div>
      </div>
    </div>
  );
}
