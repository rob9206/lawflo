import { useState, useRef, useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import ReactMarkdown from "react-markdown";
import { getTeachingPlan, startAutoSession, type TeachingPlan, type TeachingTarget } from "@/api/autoTeach";
import { getMastery } from "@/api/progress";
import { sendMessageStream } from "@/api/tutor";
import { masteryColor, masteryBg } from "@/lib/utils";
import {
  Zap,
  Target,
  ChevronRight,
  Clock,
  Send,
  ArrowRight,
  BarChart3,
  BookOpen,
} from "lucide-react";

const SUBJECTS = [
  { value: "con_law", label: "Constitutional Law" },
  { value: "contracts", label: "Contracts" },
  { value: "torts", label: "Torts" },
  { value: "crim_law", label: "Criminal Law" },
  { value: "civ_pro", label: "Civil Procedure" },
  { value: "property", label: "Property" },
  { value: "evidence", label: "Evidence" },
  { value: "prof_responsibility", label: "Prof. Responsibility" },
];

const MODE_LABELS: Record<string, string> = {
  explain: "Learn",
  socratic: "Question",
  hypo: "Hypo Drill",
  issue_spot: "Issue Spot",
  irac: "IRAC",
  exam_strategy: "Exam Prep",
};

export default function AutoTeachPage() {
  const [selectedSubject, setSelectedSubject] = useState<string | null>(null);
  const [availableMinutes, setAvailableMinutes] = useState<number>(60);

  // Active session state
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [sessionMode, setSessionMode] = useState("");
  const [sessionTopic, setSessionTopic] = useState("");
  const [messages, setMessages] = useState<{ role: string; content: string }[]>([]);
  const [streaming, setStreaming] = useState(false);
  const [streamingText, setStreamingText] = useState("");
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

  // Start an auto-teach session for a topic
  const startSession = async (topic?: string) => {
    if (!selectedSubject) return;
    setStreaming(true);
    setStreamingText("");
    setMessages([]);

    let accumulated = "";

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
  };

  // Send a follow-up message
  const sendMessage = async () => {
    if (!input.trim() || !sessionId || streaming) return;

    const userContent = input.trim();
    setMessages((prev) => [...prev, { role: "user", content: userContent }]);
    setInput("");
    setStreaming(true);
    setStreamingText("");

    let accumulated = "";

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
  };

  // ── If in an active session, show the chat ──
  if (sessionId) {
    return (
      <div className="flex flex-col h-[calc(100vh-3rem)]">
        <div className="flex items-center justify-between pb-4 border-b border-zinc-800">
          <div className="flex items-center gap-3">
            <Zap size={20} className="text-amber-400" />
            <div>
              <h2 className="font-semibold">AutoTeach Session</h2>
              <p className="text-xs text-zinc-500">
                {MODE_LABELS[sessionMode] || sessionMode} · {sessionTopic}
              </p>
            </div>
          </div>
          <button
            onClick={() => {
              setSessionId(null);
              setMessages([]);
            }}
            className="text-xs text-zinc-500 hover:text-zinc-300 px-3 py-1 border border-zinc-700 rounded-lg"
          >
            Back to Plan
          </button>
        </div>

        <div className="flex-1 overflow-y-auto py-4 space-y-4">
          {messages.map((msg, i) => (
            <div key={i} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
              <div className={`max-w-[80%] rounded-2xl px-4 py-3 text-sm ${
                msg.role === "user"
                  ? "bg-indigo-600 text-white"
                  : "bg-zinc-900 border border-zinc-800 text-zinc-200"
              }`}>
                {msg.role === "assistant" ? (
                  <div className="prose-tutor"><ReactMarkdown>{msg.content}</ReactMarkdown></div>
                ) : (
                  <p className="whitespace-pre-wrap">{msg.content}</p>
                )}
              </div>
            </div>
          ))}
          {streaming && streamingText && (
            <div className="flex justify-start">
              <div className="max-w-[80%] bg-zinc-900 border border-zinc-800 rounded-2xl px-4 py-3 text-sm">
                <div className="prose-tutor">
                  <ReactMarkdown>{streamingText.replace(/<performance>[\s\S]*?<\/performance>/g, "")}</ReactMarkdown>
                </div>
              </div>
            </div>
          )}
          {streaming && !streamingText && (
            <div className="flex justify-start">
              <div className="bg-zinc-900 border border-zinc-800 rounded-2xl px-4 py-3">
                <div className="flex gap-1">
                  <span className="w-2 h-2 bg-zinc-600 rounded-full animate-bounce" />
                  <span className="w-2 h-2 bg-zinc-600 rounded-full animate-bounce [animation-delay:150ms]" />
                  <span className="w-2 h-2 bg-zinc-600 rounded-full animate-bounce [animation-delay:300ms]" />
                </div>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        <div className="pt-4 border-t border-zinc-800">
          <div className="flex gap-2">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendMessage(); } }}
              placeholder="Ask a follow-up, answer a question, or say 'next topic'..."
              rows={2}
              className="flex-1 bg-zinc-900 border border-zinc-700 rounded-xl px-4 py-3 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-indigo-500/50"
            />
            <button
              onClick={sendMessage}
              disabled={!input.trim() || streaming}
              className="self-end bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 text-white p-3 rounded-xl"
            >
              <Send size={18} />
            </button>
          </div>
        </div>
      </div>
    );
  }

  // ── Subject selection + teaching plan ──
  return (
    <div>
      <div className="flex items-center gap-3 mb-6">
        <Zap size={24} className="text-amber-400" />
        <div>
          <h2 className="text-2xl font-bold">AutoTeach</h2>
          <p className="text-sm text-zinc-500">AI-optimized study sessions that teach you exactly what you need</p>
        </div>
      </div>

      {/* Subject picker */}
      <div className="grid grid-cols-4 gap-2 mb-6">
        {SUBJECTS.map((s) => {
          const m = masteryData?.find((x) => x.subject === s.value);
          return (
            <button
              key={s.value}
              onClick={() => setSelectedSubject(s.value)}
              className={`text-left px-4 py-3 rounded-xl border transition-colors ${
                selectedSubject === s.value
                  ? "bg-amber-500/10 border-amber-500 text-amber-400"
                  : "bg-zinc-900 border-zinc-800 hover:border-zinc-700"
              }`}
            >
              <p className="text-sm font-medium">{s.label}</p>
              <p className={`text-xs mt-0.5 ${m ? masteryColor(m.mastery_score) : "text-zinc-500"}`}>
                {m ? `${m.mastery_score.toFixed(0)}% mastery` : "Not started"}
              </p>
            </button>
          );
        })}
      </div>

      {/* Time budget */}
      {selectedSubject && (
        <div className="flex items-center gap-4 mb-6 p-4 bg-zinc-900 border border-zinc-800 rounded-xl">
          <Clock size={18} className="text-zinc-400" />
          <span className="text-sm text-zinc-400">I have</span>
          <div className="flex gap-2">
            {[30, 60, 90, 120].map((mins) => (
              <button
                key={mins}
                onClick={() => setAvailableMinutes(mins)}
                className={`px-3 py-1 rounded-lg text-sm transition-colors ${
                  availableMinutes === mins
                    ? "bg-amber-500/15 text-amber-400 border border-amber-500"
                    : "bg-zinc-800 text-zinc-400 border border-zinc-700"
                }`}
              >
                {mins}m
              </button>
            ))}
          </div>
          <span className="text-sm text-zinc-400">to study</span>
        </div>
      )}

      {/* Teaching plan */}
      {planLoading && <div className="text-zinc-500 animate-pulse">Computing optimal study plan...</div>}

      {plan && (
        <div>
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold">
              Study Plan — {plan.subject_display}
            </h3>
            <div className="flex items-center gap-4 text-sm text-zinc-500">
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

          {/* Big "Start Studying" button */}
          {plan.auto_session && (
            <button
              onClick={() => startSession()}
              disabled={streaming}
              className="w-full mb-6 bg-gradient-to-r from-amber-600 to-orange-600 hover:from-amber-500 hover:to-orange-500 text-white font-semibold py-4 px-6 rounded-xl flex items-center justify-center gap-3 transition-all shadow-lg shadow-amber-900/20"
            >
              <Zap size={20} />
              Start Studying — {plan.teaching_plan[0]?.display_name}
              <ArrowRight size={18} />
            </button>
          )}

          {/* Topic list */}
          <div className="space-y-2">
            {plan.teaching_plan.map((target, i) => (
              <TopicRow
                key={target.topic}
                target={target}
                rank={i + 1}
                hasExamData={plan.has_exam_data}
                onStart={() => startSession(target.topic)}
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
}: {
  target: TeachingTarget;
  rank: number;
  hasExamData: boolean;
  onStart: () => void;
}) {
  return (
    <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-4 flex items-center gap-4">
      {/* Rank */}
      <div className="w-8 h-8 rounded-full bg-zinc-800 flex items-center justify-center text-sm font-bold text-zinc-400">
        {rank}
      </div>

      {/* Info */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <p className="font-medium">{target.display_name}</p>
          <span className={`text-xs px-2 py-0.5 rounded-full ${masteryBg(target.mastery)} ${masteryColor(target.mastery)}`}>
            {target.mastery.toFixed(0)}%
          </span>
          <span className="text-xs bg-zinc-800 text-zinc-500 px-2 py-0.5 rounded-full">
            {MODE_LABELS[target.recommended_mode] || target.recommended_mode}
          </span>
        </div>
        <p className="text-xs text-zinc-500 mt-0.5">
          {target.mode_reason}
          {hasExamData && ` · ${(target.exam_weight * 100).toFixed(0)}% of exam`}
        </p>
      </div>

      {/* Metadata */}
      <div className="text-right text-xs text-zinc-500 shrink-0">
        <p>{target.time_estimate_minutes}m</p>
        {target.knowledge_chunks_available > 0 && (
          <p className="flex items-center gap-1 justify-end">
            <BookOpen size={10} />
            {target.knowledge_chunks_available} chunks
          </p>
        )}
      </div>

      {/* Start button */}
      <button
        onClick={onStart}
        className="shrink-0 p-2 bg-zinc-800 hover:bg-indigo-600 rounded-lg text-zinc-400 hover:text-white transition-colors"
      >
        <ChevronRight size={18} />
      </button>
    </div>
  );
}
