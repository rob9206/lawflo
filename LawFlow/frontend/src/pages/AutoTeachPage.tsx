import { useState, useRef, useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import ReactMarkdown from "react-markdown";
import { getTeachingPlan, startAutoSession, type TeachingTarget } from "@/api/autoTeach";
import { getMastery } from "@/api/progress";
import { sendMessageStream } from "@/api/tutor";
import { useRewardToast } from "@/hooks/useRewardToast";
import { masteryColor, cleanMarkdown, cn } from "@/lib/utils";
import { SUBJECTS_REQUIRED, AUTOTEACH_MODE_LABELS } from "@/lib/constants";
import Card from "@/components/ui/Card";
import PageHeader from "@/components/ui/PageHeader";
import Badge from "@/components/ui/Badge";
import {
  Zap,
  ChevronRight,
  Clock,
  Send,
  ArrowRight,
  BarChart3,
  BookOpen,
} from "lucide-react";

export default function AutoTeachPage() {
  const fireRewardToast = useRewardToast();
  const [selectedSubject, setSelectedSubject] = useState<string | null>(null);
  const [availableMinutes, setAvailableMinutes] = useState<number>(60);

  const [sessionId, setSessionId] = useState<string | null>(null);
  const [sessionMode, setSessionMode] = useState("");
  const [sessionTopic, setSessionTopic] = useState("");
  const [messages, setMessages] = useState<{ role: string; content: string }[]>([]);
  const [streaming, setStreaming] = useState(false);
  const [streamingText, setStreamingText] = useState("");
  const [sessionError, setSessionError] = useState<string | null>(null);
  const [input, setInput] = useState("");
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const { data: masteryData } = useQuery({
    queryKey: ["mastery"],
    queryFn: getMastery,
  });

  const { data: plan, isLoading: planLoading } = useQuery({
    queryKey: ["teaching-plan", selectedSubject, availableMinutes],
    queryFn: () => getTeachingPlan(selectedSubject!, { available_minutes: availableMinutes }),
    enabled: !!selectedSubject,
  });

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streamingText]);

  const startSession = async (topic?: string) => {
    if (!selectedSubject) return;
    setStreaming(true);
    setStreamingText("");
    setMessages([]);
    setSessionError(null);

    let accumulated = "";

    try {
      await startAutoSession(
        selectedSubject,
        topic,
        (chunk) => {
          accumulated += chunk;
          setStreamingText(accumulated);
        },
        (sid, mode, resolvedTopic) => {
          const clean = accumulated.replace(/<performance>[\s\S]*?<\/performance>/g, "").trim();
          setSessionId(sid);
          setSessionMode(mode);
          setSessionTopic(resolvedTopic);
          setMessages([{ role: "assistant", content: clean }]);
          setStreamingText("");
          setStreaming(false);
        }
      );
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Failed to start session";
      setSessionError(msg);
      setStreaming(false);
      setStreamingText("");
    }
  };

  const sendMessage = async () => {
    if (!input.trim() || !sessionId || streaming) return;

    const userContent = input.trim();
    setMessages((prev) => [...prev, { role: "user", content: userContent }]);
    setInput("");
    setStreaming(true);
    setStreamingText("");

    let accumulated = "";

    try {
      await sendMessageStream(
        sessionId,
        userContent,
        (chunk) => {
          accumulated += chunk;
          setStreamingText(accumulated);
        },
        () => {
          const clean = accumulated.replace(/<performance>[\s\S]*?<\/performance>/g, "").trim();
          setMessages((prev) => [...prev, { role: "assistant", content: clean }]);
          setStreamingText("");
          setStreaming(false);
        }
      );
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: "Something went wrong. Please try again." },
      ]);
      setStreamingText("");
      setStreaming(false);
    }
  };

  // Active session
  if (sessionId) {
    return (
      <div className="flex flex-col h-[calc(100vh-3rem)]">
        <div className="flex items-center justify-between pb-4 border-b border-[var(--border)]">
          <div className="flex items-center gap-3">
            <Zap size={20} className="text-amber-400" />
            <div>
              <h2 className="font-semibold text-ui-primary">AutoTeach Session</h2>
              <p className="text-xs text-ui-muted">
                {AUTOTEACH_MODE_LABELS[sessionMode] || sessionMode} · {sessionTopic}
              </p>
            </div>
          </div>
          <button
            onClick={() => {
              setSessionId(null);
              setMessages([]);
              // Check if XP was earned during this session
              void fireRewardToast().catch(() => {});
            }}
            className="btn-secondary text-xs px-3 py-1 rounded-lg"
          >
            Back to Plan
          </button>
        </div>

        <div className="flex-1 overflow-y-auto py-4 space-y-4">
          {messages.map((msg, i) => (
            <div key={i} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
              <div
                className="max-w-[90%] rounded-2xl px-4 py-3 text-sm"
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
                  <div className="prose-tutor leading-relaxed">
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
                className="max-w-[90%] rounded-2xl px-4 py-3 text-sm"
                style={{
                  backgroundColor: "var(--bg-card)",
                  border: "1px solid var(--border)",
                  color: "var(--text-primary)",
                }}
              >
                <div className="prose-tutor leading-relaxed">
                  <ReactMarkdown>
                    {cleanMarkdown(streamingText.replace(/<performance>[\s\S]*?<\/performance>/g, ""))}
                  </ReactMarkdown>
                </div>
              </div>
            </div>
          )}

          {streaming && !streamingText && (
            <div className="flex justify-start">
              <div
                className="rounded-2xl px-4 py-3"
                style={{
                  backgroundColor: "var(--bg-card)",
                  border: "1px solid var(--border)",
                }}
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

        <div className="pt-4" style={{ borderTop: "1px solid var(--border)" }}>
          <div className="flex gap-2">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendMessage(); }
              }}
              placeholder="Ask a follow-up, answer a question, or say 'next topic'..."
              rows={2}
              className="flex-1 rounded-xl px-4 py-3 text-sm resize-none focus:outline-none focus:ring-2"
              style={{
                backgroundColor: "var(--bg-input)",
                border: "1px solid var(--border)",
                color: "var(--text-primary)",
              }}
            />
            <button
              onClick={sendMessage}
              disabled={!input.trim() || streaming}
              className="self-end p-3 rounded-xl text-white disabled:opacity-40"
              style={{ backgroundColor: "var(--accent)" }}
            >
              <Send size={18} />
            </button>
          </div>
        </div>
      </div>
    );
  }

  // Subject selection + teaching plan
  return (
    <div>
      <div className="mb-6">
        <PageHeader
          icon={<Zap size={24} />}
          title="AutoTeach"
          subtitle="AI-optimized study sessions that teach you exactly what you need"
        />
      </div>

      {/* Subject picker */}
      <div className="grid grid-cols-4 gap-2 mb-6">
        {SUBJECTS_REQUIRED.map((s) => {
          const m = masteryData?.find((x) => x.subject === s.value);
          const active = selectedSubject === s.value;
          return (
            <Card
              key={s.value}
              hover
              padding="none"
              className={cn(
                "text-left px-4 py-3 cursor-pointer transition-all",
                active && "!border-amber-500 !bg-amber-500/10"
              )}
              onClick={() => setSelectedSubject(s.value)}
            >
              <p className={cn("text-sm font-medium", active ? "text-amber-300" : "text-ui-primary")}>
                {s.label}
              </p>
              <p className={cn("text-xs mt-0.5", m ? masteryColor(m.mastery_score) : "text-ui-muted")}>
                {m ? `${m.mastery_score.toFixed(0)}% mastery` : "Not started"}
              </p>
            </Card>
          );
        })}
      </div>

      {/* Time budget */}
      {selectedSubject && (
        <Card className="flex items-center gap-4 mb-6">
          <Clock size={18} className="text-ui-muted" />
          <span className="text-sm text-ui-secondary">I have</span>
          <div className="flex gap-2">
            {[30, 60, 90, 120].map((mins) => (
              <button
                key={mins}
                onClick={() => setAvailableMinutes(mins)}
                className={cn(
                  "px-3 py-1 rounded-lg text-sm transition-all border",
                  availableMinutes === mins
                    ? "bg-amber-500/15 text-amber-300 border-amber-500"
                    : "bg-[var(--bg-muted)] text-ui-secondary border-[var(--border)]"
                )}
              >
                {mins}m
              </button>
            ))}
          </div>
          <span className="text-sm text-ui-secondary">to study</span>
        </Card>
      )}

      {planLoading && (
        <div className="animate-pulse text-ui-muted">Computing optimal study plan...</div>
      )}

      {plan && plan.teaching_plan.length === 0 && (
        <Card className="text-center py-8 text-ui-muted text-sm">
          No study topics found for this subject. The database may still be initializing — try refreshing in a moment.
        </Card>
      )}

      {plan && plan.teaching_plan.length > 0 && (
        <div>
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-ui-primary">
              Study Plan — {plan.subject_display}
            </h3>
            <div className="flex items-center gap-4 text-sm text-ui-muted">
              <span className="flex items-center gap-1">
                <Clock size={14} />
                {plan.total_estimated_minutes}m total
              </span>
              {plan.has_exam_data && (
                <span className="flex items-center gap-1 text-amber-400">
                  <BarChart3 size={14} />
                  Exam-optimized
                </span>
              )}
            </div>
          </div>

          {sessionError && (
            <Card className="mb-4 !bg-red-500/10 !border-red-500/35 text-red-400 text-sm">
              {sessionError}
            </Card>
          )}

          {plan.auto_session && (
            <button
              onClick={() => startSession()}
              disabled={streaming}
              className="w-full mb-6 bg-gradient-to-r from-amber-600 to-orange-600 hover:from-amber-500 hover:to-orange-500 text-white font-semibold py-4 px-6 rounded-xl flex items-center justify-center gap-3 transition-all shadow-lg shadow-amber-900/20 disabled:opacity-60 disabled:cursor-not-allowed"
            >
              <Zap size={20} />
              Start Studying — {plan.teaching_plan[0]?.display_name}
              <ArrowRight size={18} />
            </button>
          )}

          <div className="space-y-2">
            {plan.teaching_plan.map((target, i) => (
              <TopicRow
                key={target.topic}
                target={target}
                rank={i + 1}
                hasExamData={plan.has_exam_data}
                onStart={() => startSession(target.topic)}
                disabled={streaming}
              />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function TopicRow({
  target,
  rank,
  hasExamData,
  onStart,
  disabled,
}: {
  target: TeachingTarget;
  rank: number;
  hasExamData: boolean;
  onStart: () => void;
  disabled?: boolean;
}) {
  return (
    <Card className="flex items-center gap-4">
      <div className="w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold bg-[var(--bg-muted)] text-ui-muted">
        {rank}
      </div>

      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <p className="font-medium text-ui-primary">{target.display_name}</p>
          <Badge className={masteryColor(target.mastery)}>
            {target.mastery.toFixed(0)}%
          </Badge>
          <Badge>
            {AUTOTEACH_MODE_LABELS[target.recommended_mode] || target.recommended_mode}
          </Badge>
        </div>
        <p className="text-xs mt-0.5 text-ui-muted">
          {target.mode_reason}
          {hasExamData && ` · ${(target.exam_weight * 100).toFixed(0)}% of exam`}
        </p>
      </div>

      <div className="text-right text-xs shrink-0 text-ui-muted">
        <p>{target.time_estimate_minutes}m</p>
        {target.knowledge_chunks_available > 0 && (
          <p className="flex items-center gap-1 justify-end">
            <BookOpen size={10} />
            {target.knowledge_chunks_available} chunks
          </p>
        )}
      </div>

      <button
        onClick={onStart}
        disabled={disabled}
        className="shrink-0 p-2 rounded-lg transition-colors bg-[var(--bg-muted)] text-ui-muted disabled:opacity-40 disabled:cursor-not-allowed"
      >
        <ChevronRight size={18} />
      </button>
    </Card>
  );
}
