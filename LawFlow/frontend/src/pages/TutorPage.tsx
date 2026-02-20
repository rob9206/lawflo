import { useState, useRef, useEffect, useCallback } from "react";
import { useQuery } from "@tanstack/react-query";
import { useParams } from "react-router-dom";
import ReactMarkdown from "react-markdown";
import { createSession, getSession, sendMessageStream, getModes } from "@/api/tutor";
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

const SUBJECTS = [
  { value: "", label: "Any subject" },
  { value: "con_law", label: "Con Law" },
  { value: "contracts", label: "Contracts" },
  { value: "torts", label: "Torts" },
  { value: "crim_law", label: "Crim Law" },
  { value: "civ_pro", label: "Civ Pro" },
  { value: "property", label: "Property" },
  { value: "evidence", label: "Evidence" },
  { value: "prof_responsibility", label: "Prof. Resp." },
];

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

  // Load existing session
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

  // Auto-scroll
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
          // Clean performance tags from display
          const clean = accumulated.replace(/<performance>[\s\S]*?<\/performance>/g, "").trim();
          const assistantMsg: SessionMessage = {
            id: crypto.randomUUID(),
            session_id: sessionId,
            role: "assistant",
            content: clean,
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

  // Session setup screen
  if (!sessionId) {
    return (
      <div>
        <h2 className="text-2xl font-bold mb-6">AI Tutor</h2>

        <div className="max-w-2xl">
          {/* Mode selection */}
          <h3 className="text-sm font-medium text-zinc-400 mb-3">Study Mode</h3>
          <div className="grid grid-cols-3 gap-2 mb-6">
            {modes &&
              Object.entries(modes).map(([key, mode]) => (
                <button
                  key={key}
                  onClick={() => setSelectedMode(key)}
                  className={`flex items-center gap-2 px-3 py-2.5 rounded-lg text-sm text-left transition-colors ${
                    selectedMode === key
                      ? "bg-indigo-500/15 border-indigo-500 text-indigo-400 border"
                      : "bg-zinc-900 border-zinc-800 text-zinc-300 border hover:border-zinc-700"
                  }`}
                >
                  {MODE_ICONS[key] || <GraduationCap size={16} />}
                  <div>
                    <p className="font-medium">{mode.name}</p>
                    <p className="text-xs text-zinc-500 mt-0.5 line-clamp-2">{mode.description}</p>
                  </div>
                </button>
              ))}
          </div>

          {/* Subject */}
          <h3 className="text-sm font-medium text-zinc-400 mb-2">Subject Focus</h3>
          <div className="flex flex-wrap gap-2 mb-6">
            {SUBJECTS.map((s) => (
              <button
                key={s.value}
                onClick={() => setSelectedSubject(s.value)}
                className={`px-3 py-1.5 rounded-lg text-sm transition-colors ${
                  selectedSubject === s.value
                    ? "bg-indigo-500/15 text-indigo-400 border border-indigo-500"
                    : "bg-zinc-900 text-zinc-400 border border-zinc-800 hover:border-zinc-700"
                }`}
              >
                {s.label}
              </button>
            ))}
          </div>

          {/* Start button */}
          <button
            onClick={startSession}
            className="w-full bg-indigo-600 hover:bg-indigo-500 text-white font-medium py-3 px-6 rounded-xl transition-colors"
          >
            Start Study Session
          </button>
        </div>
      </div>
    );
  }

  // Chat interface
  return (
    <div className="flex flex-col h-[calc(100vh-3rem)]">
      {/* Header */}
      <div className="flex items-center gap-3 pb-4 border-b border-zinc-800">
        <GraduationCap size={20} className="text-indigo-400" />
        <div>
          <h2 className="font-semibold">AI Tutor Session</h2>
          <p className="text-xs text-zinc-500">
            {selectedMode} · {selectedSubject || "all subjects"}
          </p>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto py-4 space-y-4">
        {messages.length === 0 && !streaming && (
          <div className="text-center text-zinc-500 py-12">
            <GraduationCap size={40} className="mx-auto mb-3 text-zinc-700" />
            <p>Start by asking a question or describing what you want to study.</p>
            <p className="text-xs mt-1">
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
              className={`max-w-[80%] rounded-2xl px-4 py-3 text-sm ${
                msg.role === "user"
                  ? "bg-indigo-600 text-white"
                  : "bg-zinc-900 border border-zinc-800 text-zinc-200"
              }`}
            >
              {msg.role === "assistant" ? (
                <div className="prose-tutor">
                  <ReactMarkdown>{msg.content}</ReactMarkdown>
                </div>
              ) : (
                <p className="whitespace-pre-wrap">{msg.content}</p>
              )}
            </div>
          </div>
        ))}

        {/* Streaming response */}
        {streaming && streamingText && (
          <div className="flex justify-start">
            <div className="max-w-[80%] bg-zinc-900 border border-zinc-800 rounded-2xl px-4 py-3 text-sm text-zinc-200">
              <div className="prose-tutor">
                <ReactMarkdown>
                  {streamingText.replace(/<performance>[\s\S]*?<\/performance>/g, "")}
                </ReactMarkdown>
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

      {/* Input */}
      <div className="pt-4 border-t border-zinc-800">
        <div className="flex gap-2">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask a question, answer a prompt, or describe what to study..."
            rows={2}
            className="flex-1 bg-zinc-900 border border-zinc-700 rounded-xl px-4 py-3 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500"
          />
          <button
            onClick={sendMessage}
            disabled={!input.trim() || streaming}
            className="self-end bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 disabled:cursor-not-allowed text-white p-3 rounded-xl transition-colors"
          >
            <Send size={18} />
          </button>
        </div>
      </div>
    </div>
  );
}
