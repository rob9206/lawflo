import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import ReactMarkdown from "react-markdown";
import { cleanMarkdown } from "@/lib/utils";
import {
  getDueCards,
  getCardStats,
  answerCard,
  generateCardsForSubject,
  type FlashCard,
  type CardStats,
} from "@/api/review";
import { masteryColor } from "@/lib/utils";
import {
  Layers,
  RotateCcw,
  ChevronRight,
  Sparkles,
  CheckCircle2,
  XCircle,
  Brain,
  Zap,
  Clock,
  Trophy,
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

const QUALITY_BUTTONS = [
  {
    quality: 0,
    label: "Blackout",
    sublabel: "No clue",
    color: "bg-red-600 hover:bg-red-500",
    icon: XCircle,
  },
  {
    quality: 2,
    label: "Hard",
    sublabel: "Wrong / close",
    color: "bg-orange-600 hover:bg-orange-500",
    icon: Brain,
  },
  {
    quality: 3,
    label: "Good",
    sublabel: "Got it, took effort",
    color: "bg-emerald-600 hover:bg-emerald-500",
    icon: CheckCircle2,
  },
  {
    quality: 5,
    label: "Easy",
    sublabel: "Instant recall",
    color: "bg-green-600 hover:bg-green-500",
    icon: Zap,
  },
];

// Predict next interval for display
function predictInterval(card: FlashCard, quality: number): string {
  let ef = card.ease_factor + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02));
  ef = Math.max(1.3, ef);
  let interval: number;

  if (quality < 3) {
    interval = 1;
  } else if (card.repetitions === 0) {
    interval = 1;
  } else if (card.repetitions === 1) {
    interval = 3;
  } else {
    interval = Math.round(card.interval_days * ef);
  }

  if (interval === 1) return "1 day";
  if (interval < 30) return `${interval} days`;
  if (interval < 365) return `${Math.round(interval / 30)} mo`;
  return `${(interval / 365).toFixed(1)} yr`;
}

const CARD_TYPE_LABELS: Record<string, string> = {
  concept: "Concept",
  rule: "Rule / Test",
  case_holding: "Case Holding",
  element_list: "Elements",
};

export default function ReviewPage() {
  const queryClient = useQueryClient();
  const [selectedSubject, setSelectedSubject] = useState<string | null>(null);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [flipped, setFlipped] = useState(false);
  const [sessionComplete, setSessionComplete] = useState(false);
  const [sessionResults, setSessionResults] = useState<
    { quality: number; card: FlashCard }[]
  >([]);

  const { data: stats } = useQuery({
    queryKey: ["card-stats", selectedSubject],
    queryFn: () => getCardStats(selectedSubject || undefined),
  });

  const {
    data: dueCards,
    isLoading: cardsLoading,
    refetch: refetchDue,
  } = useQuery({
    queryKey: ["due-cards", selectedSubject],
    queryFn: () => getDueCards(selectedSubject || undefined),
    enabled: true,
  });

  const answerMutation = useMutation({
    mutationFn: ({ cardId, quality }: { cardId: string; quality: number }) =>
      answerCard(cardId, quality),
    onSuccess: (_, vars) => {
      const card = dueCards?.[currentIndex];
      if (card) {
        setSessionResults((prev) => [
          ...prev,
          { quality: vars.quality, card },
        ]);
      }

      setFlipped(false);
      if (dueCards && currentIndex + 1 < dueCards.length) {
        setCurrentIndex((i) => i + 1);
      } else {
        setSessionComplete(true);
      }

      queryClient.invalidateQueries({ queryKey: ["card-stats"] });
    },
  });

  const generateMutation = useMutation({
    mutationFn: (subject: string) => generateCardsForSubject(subject),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["due-cards"] });
      queryClient.invalidateQueries({ queryKey: ["card-stats"] });
    },
  });

  const currentCard = dueCards?.[currentIndex];
  const hasDue = (dueCards?.length ?? 0) > 0;

  // ── Session complete screen ──
  if (sessionComplete && sessionResults.length > 0) {
    const correct = sessionResults.filter((r) => r.quality >= 3).length;
    const total = sessionResults.length;
    const pct = Math.round((correct / total) * 100);

    return (
      <div className="max-w-2xl mx-auto">
        <div className="text-center mb-8">
          <Trophy size={48} className="mx-auto text-amber-400 mb-4" />
          <h2 className="text-2xl font-bold mb-2">Session Complete!</h2>
          <p className="text-zinc-400">
            You reviewed {total} card{total > 1 ? "s" : ""}
          </p>
        </div>

        <div className="grid grid-cols-3 gap-4 mb-8">
          <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-4 text-center">
            <p className="text-3xl font-bold text-green-400">{correct}</p>
            <p className="text-xs text-zinc-500 mt-1">Correct</p>
          </div>
          <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-4 text-center">
            <p className="text-3xl font-bold text-red-400">
              {total - correct}
            </p>
            <p className="text-xs text-zinc-500 mt-1">Needs Review</p>
          </div>
          <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-4 text-center">
            <p
              className={`text-3xl font-bold ${
                pct >= 80
                  ? "text-green-400"
                  : pct >= 60
                  ? "text-yellow-400"
                  : "text-red-400"
              }`}
            >
              {pct}%
            </p>
            <p className="text-xs text-zinc-500 mt-1">Accuracy</p>
          </div>
        </div>

        <div className="space-y-2 mb-8">
          {sessionResults.map((r, i) => (
            <div
              key={i}
              className="bg-zinc-900 border border-zinc-800 rounded-lg p-3 flex items-center gap-3"
            >
              {r.quality >= 3 ? (
                <CheckCircle2 size={16} className="text-green-400 shrink-0" />
              ) : (
                <XCircle size={16} className="text-red-400 shrink-0" />
              )}
              <p className="text-sm truncate flex-1">{r.card.front}</p>
              <span className="text-xs text-zinc-500 shrink-0">
                {QUALITY_BUTTONS.find((b) => b.quality === r.quality)?.label ||
                  `Q${r.quality}`}
              </span>
            </div>
          ))}
        </div>

        <button
          onClick={() => {
            setSessionComplete(false);
            setSessionResults([]);
            setCurrentIndex(0);
            setFlipped(false);
            refetchDue();
          }}
          className="w-full bg-indigo-600 hover:bg-indigo-500 text-white font-medium py-3 rounded-xl"
        >
          Start New Session
        </button>
      </div>
    );
  }

  // ── Active review session ──
  if (currentCard && !sessionComplete) {
    return (
      <div className="max-w-2xl mx-auto">
        {/* Progress bar */}
        <div className="flex items-center gap-3 mb-6">
          <Layers size={20} className="text-violet-400" />
          <h2 className="font-semibold">Flash Cards</h2>
          <div className="flex-1" />
          <span className="text-sm text-zinc-500">
            {currentIndex + 1} / {dueCards?.length ?? 0}
          </span>
          <button
            onClick={() => {
              if (sessionResults.length > 0) {
                setSessionComplete(true);
              } else {
                setCurrentIndex(0);
                setFlipped(false);
              }
            }}
            className="text-xs text-zinc-500 hover:text-zinc-300 px-3 py-1 border border-zinc-700 rounded-lg"
          >
            End Session
          </button>
        </div>

        <div className="w-full h-1 bg-zinc-800 rounded-full mb-6">
          <div
            className="h-full bg-violet-500 rounded-full transition-all"
            style={{
              width: `${((currentIndex + 1) / (dueCards?.length ?? 1)) * 100}%`,
            }}
          />
        </div>

        {/* Card metadata */}
        <div className="flex items-center gap-2 mb-4">
          <span className="text-xs bg-zinc-800 text-zinc-400 px-2 py-0.5 rounded-full">
            {SUBJECTS.find((s) => s.value === currentCard.subject)?.label ||
              currentCard.subject}
          </span>
          {currentCard.topic && (
            <span className="text-xs bg-zinc-800 text-zinc-500 px-2 py-0.5 rounded-full">
              {currentCard.topic}
            </span>
          )}
          <span className="text-xs bg-violet-500/20 text-violet-400 px-2 py-0.5 rounded-full">
            {CARD_TYPE_LABELS[currentCard.card_type] || currentCard.card_type}
          </span>
        </div>

        {/* The card */}
        <div
          onClick={() => !flipped && setFlipped(true)}
          className={`min-h-[280px] bg-zinc-900 border rounded-2xl p-8 mb-6 transition-all ${
            flipped
              ? "border-violet-500/30"
              : "border-zinc-700 cursor-pointer hover:border-zinc-600"
          }`}
        >
          {!flipped ? (
            <div className="flex flex-col h-full">
              <p className="text-xs text-zinc-500 uppercase tracking-wider mb-4">
                Question
              </p>
              <div className="flex-1 flex items-center">
                <p className="text-lg font-medium leading-relaxed">
                  {currentCard.front}
                </p>
              </div>
              <p className="text-xs text-zinc-600 text-center mt-6">
                Click to reveal answer
              </p>
            </div>
          ) : (
            <div className="flex flex-col h-full">
              <p className="text-xs text-violet-400 uppercase tracking-wider mb-4">
                Answer
              </p>
              <div className="flex-1 prose-tutor text-sm leading-relaxed">
                <ReactMarkdown>{cleanMarkdown(currentCard.back)}</ReactMarkdown>
              </div>
            </div>
          )}
        </div>

        {/* Quality rating buttons — only visible when flipped */}
        {flipped && (
          <div>
            <p className="text-xs text-zinc-500 text-center mb-3">
              How well did you know this?
            </p>
            <div className="grid grid-cols-4 gap-2">
              {QUALITY_BUTTONS.map((btn) => {
                const Icon = btn.icon;
                return (
                  <button
                    key={btn.quality}
                    onClick={() =>
                      answerMutation.mutate({
                        cardId: currentCard.id,
                        quality: btn.quality,
                      })
                    }
                    disabled={answerMutation.isPending}
                    className={`${btn.color} text-white rounded-xl py-3 px-2 flex flex-col items-center gap-1 transition-colors disabled:opacity-40`}
                  >
                    <Icon size={18} />
                    <span className="text-sm font-medium">{btn.label}</span>
                    <span className="text-[10px] opacity-70">
                      {btn.sublabel}
                    </span>
                    <span className="text-[10px] opacity-50 mt-0.5">
                      <Clock size={8} className="inline mr-0.5" />
                      {predictInterval(currentCard, btn.quality)}
                    </span>
                  </button>
                );
              })}
            </div>
          </div>
        )}
      </div>
    );
  }

  // ── Dashboard / Subject picker ──
  return (
    <div>
      <div className="flex items-center gap-3 mb-6">
        <Layers size={24} className="text-violet-400" />
        <div>
          <h2 className="text-2xl font-bold">Flash Cards</h2>
          <p className="text-sm text-zinc-500">
            Spaced repetition for long-term retention
          </p>
        </div>
      </div>

      {/* Global stats */}
      {stats && (
        <div className="grid grid-cols-5 gap-3 mb-6">
          {[
            { label: "Total Cards", value: stats.total, color: "text-zinc-300" },
            { label: "Due Now", value: stats.due, color: "text-amber-400" },
            { label: "New", value: stats.new, color: "text-blue-400" },
            { label: "Learning", value: stats.learning, color: "text-violet-400" },
            { label: "Mature", value: stats.mature, color: "text-green-400" },
          ].map((s) => (
            <div
              key={s.label}
              className="bg-zinc-900 border border-zinc-800 rounded-xl p-3 text-center"
            >
              <p className={`text-2xl font-bold ${s.color}`}>{s.value}</p>
              <p className="text-xs text-zinc-500 mt-0.5">{s.label}</p>
            </div>
          ))}
        </div>
      )}

      {/* Start review or generate cards */}
      {hasDue ? (
        <button
          onClick={() => {
            setCurrentIndex(0);
            setFlipped(false);
            setSessionComplete(false);
            setSessionResults([]);
          }}
          className="w-full mb-6 bg-gradient-to-r from-violet-600 to-purple-600 hover:from-violet-500 hover:to-purple-500 text-white font-semibold py-4 px-6 rounded-xl flex items-center justify-center gap-3 transition-all shadow-lg shadow-violet-900/20"
        >
          <RotateCcw size={20} />
          Start Review — {dueCards?.length} card{(dueCards?.length ?? 0) > 1 ? "s" : ""} due
          <ChevronRight size={18} />
        </button>
      ) : (
        <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-6 mb-6 text-center">
          <CheckCircle2 size={32} className="mx-auto text-green-400 mb-3" />
          <p className="font-medium mb-1">
            {stats?.total
              ? "All caught up!"
              : "No flash cards yet"}
          </p>
          <p className="text-sm text-zinc-500">
            {stats?.total
              ? "No cards due for review right now. Come back later or generate more cards."
              : "Upload documents first, then generate flash cards from your study material."}
          </p>
        </div>
      )}

      {/* Subject cards — for generating new cards */}
      <h3 className="text-sm font-semibold text-zinc-400 uppercase tracking-wider mb-3">
        Generate Cards by Subject
      </h3>
      <div className="grid grid-cols-2 gap-3">
        {SUBJECTS.map((s) => (
          <div
            key={s.value}
            className="bg-zinc-900 border border-zinc-800 rounded-xl p-4 flex items-center justify-between"
          >
            <div>
              <p className="font-medium">{s.label}</p>
              <p className="text-xs text-zinc-500 mt-0.5">
                Generate flashcards from uploaded material
              </p>
            </div>
            <button
              onClick={() => generateMutation.mutate(s.value)}
              disabled={generateMutation.isPending}
              className="shrink-0 bg-violet-600 hover:bg-violet-500 disabled:opacity-40 text-white px-4 py-2 rounded-lg text-sm flex items-center gap-2"
            >
              <Sparkles size={14} />
              {generateMutation.isPending &&
              generateMutation.variables === s.value
                ? "Generating..."
                : "Generate"}
            </button>
          </div>
        ))}
      </div>

      {cardsLoading && (
        <div className="text-zinc-500 animate-pulse mt-6 text-center">
          Loading flash cards...
        </div>
      )}
    </div>
  );
}
