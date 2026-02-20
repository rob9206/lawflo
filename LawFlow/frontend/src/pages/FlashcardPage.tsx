import { useState, useCallback } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  getDueCards,
  getCardStats,
  answerCard,
  generateCardsForSubject,
  type FlashCard,
} from "@/api/review";
import { getMastery } from "@/api/progress";
import {
  CreditCard,
  Zap,
  CheckCircle,
  RotateCcw,
  Sparkles,
  Loader2,
  Brain,
  Star,
  BookOpen,
} from "lucide-react";

const SUBJECTS = [
  { value: "", label: "All Subjects" },
  { value: "con_law", label: "Constitutional Law" },
  { value: "contracts", label: "Contracts" },
  { value: "torts", label: "Torts" },
  { value: "crim_law", label: "Criminal Law" },
  { value: "civ_pro", label: "Civil Procedure" },
  { value: "property", label: "Property" },
  { value: "evidence", label: "Evidence" },
  { value: "prof_responsibility", label: "Prof. Responsibility" },
];

const CARD_TYPE_LABELS: Record<string, string> = {
  concept: "Concept",
  rule: "Rule",
  case_holding: "Case Holding",
  element_list: "Elements",
};

const QUALITY_BUTTONS = [
  { label: "Again", quality: 1, color: "#ef4444", bg: "rgba(239,68,68,0.15)" },
  { label: "Hard", quality: 2, color: "#f97316", bg: "rgba(249,115,22,0.15)" },
  { label: "Good", quality: 4, color: "#10b981", bg: "rgba(16,185,129,0.15)" },
  { label: "Easy", quality: 5, color: "#6366f1", bg: "rgba(99,102,241,0.15)" },
];

export default function FlashcardPage() {
  const queryClient = useQueryClient();
  const [selectedSubject, setSelectedSubject] = useState("");
  const [currentIndex, setCurrentIndex] = useState(0);
  const [isFlipped, setIsFlipped] = useState(false);
  const [reviewedCount, setReviewedCount] = useState(0);
  const [sessionDone, setSessionDone] = useState(false);
  const [generating, setGenerating] = useState(false);

  const { data: stats } = useQuery({
    queryKey: ["card-stats", selectedSubject],
    queryFn: () => getCardStats(selectedSubject || undefined),
    refetchInterval: 30_000,
  });

  const { data: dueCards = [], isLoading: cardsLoading, refetch: refetchCards } = useQuery({
    queryKey: ["due-cards", selectedSubject],
    queryFn: () => getDueCards(selectedSubject || undefined, 20),
  });

  const { data: masteryData = [] } = useQuery({
    queryKey: ["mastery"],
    queryFn: getMastery,
  });

  const answerMutation = useMutation({
    mutationFn: ({ cardId, quality }: { cardId: string; quality: number }) =>
      answerCard(cardId, quality),
    onSuccess: () => {
      const next = currentIndex + 1;
      setReviewedCount((c) => c + 1);
      setIsFlipped(false);

      if (next >= dueCards.length) {
        setSessionDone(true);
      } else {
        setCurrentIndex(next);
      }

      queryClient.invalidateQueries({ queryKey: ["card-stats"] });
    },
  });

  const handleGenerate = useCallback(async () => {
    if (!selectedSubject) return;
    setGenerating(true);
    try {
      await generateCardsForSubject(selectedSubject, 5);
      await refetchCards();
      setCurrentIndex(0);
      setSessionDone(false);
      setIsFlipped(false);
      setReviewedCount(0);
      queryClient.invalidateQueries({ queryKey: ["card-stats"] });
    } finally {
      setGenerating(false);
    }
  }, [selectedSubject, refetchCards, queryClient]);

  const resetSession = useCallback(async () => {
    setCurrentIndex(0);
    setIsFlipped(false);
    setReviewedCount(0);
    setSessionDone(false);
    await refetchCards();
  }, [refetchCards]);

  const currentCard: FlashCard | undefined = dueCards[currentIndex];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h2 className="text-2xl font-bold" style={{ color: "var(--text-primary)" }}>
            Flashcards
          </h2>
          <p className="text-sm mt-0.5" style={{ color: "var(--text-muted)" }}>
            Spaced repetition review — SM-2 algorithm
          </p>
        </div>

        {/* Generate button */}
        {selectedSubject && (
          <button
            onClick={handleGenerate}
            disabled={generating}
            className="flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-semibold text-white transition-all disabled:opacity-60"
            style={{ backgroundColor: "var(--accent)" }}
          >
            {generating ? (
              <Loader2 size={16} className="animate-spin" />
            ) : (
              <Sparkles size={16} />
            )}
            {generating ? "Generating…" : "Generate Cards"}
          </button>
        )}
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <MiniStat icon={<CreditCard size={16} />} label="Total Cards" value={String(stats?.total ?? 0)} color="text-indigo-400" />
        <MiniStat icon={<Zap size={16} />} label="Due Today" value={String(stats?.due ?? 0)} color="text-amber-400" />
        <MiniStat icon={<Brain size={16} />} label="Learning" value={String(stats?.learning ?? 0)} color="text-blue-400" />
        <MiniStat icon={<Star size={16} />} label="Mature" value={String(stats?.mature ?? 0)} color="text-emerald-400" />
      </div>

      {/* Subject filter */}
      <div className="flex flex-wrap gap-2">
        {SUBJECTS.map((s) => {
          const mastery = masteryData.find((m) => m.subject === s.value);
          return (
            <button
              key={s.value}
              onClick={() => {
                setSelectedSubject(s.value);
                setCurrentIndex(0);
                setIsFlipped(false);
                setSessionDone(false);
                setReviewedCount(0);
              }}
              className="px-3 py-1.5 rounded-lg text-xs font-medium transition-all"
              style={{
                backgroundColor:
                  selectedSubject === s.value ? "var(--accent-muted)" : "var(--bg-card)",
                color:
                  selectedSubject === s.value ? "var(--accent-text)" : "var(--text-secondary)",
                border: `1px solid ${selectedSubject === s.value ? "var(--accent)" : "var(--border)"}`,
              }}
            >
              {s.label}
              {mastery && (
                <span className="ml-1.5 opacity-60">{mastery.mastery_score.toFixed(0)}%</span>
              )}
            </button>
          );
        })}
      </div>

      {/* Card area */}
      {cardsLoading ? (
        <div className="flex items-center justify-center h-64">
          <Loader2 size={24} className="animate-spin" style={{ color: "var(--text-muted)" }} />
        </div>
      ) : sessionDone ? (
        <SessionComplete
          reviewedCount={reviewedCount}
          onReset={resetSession}
          onGenerate={selectedSubject ? handleGenerate : undefined}
          generating={generating}
        />
      ) : dueCards.length === 0 ? (
        <EmptyState
          hasSubject={!!selectedSubject}
          onGenerate={selectedSubject ? handleGenerate : undefined}
          generating={generating}
        />
      ) : (
        currentCard && (
          <div className="space-y-4">
            {/* Progress */}
            <div className="flex items-center justify-between text-xs" style={{ color: "var(--text-muted)" }}>
              <span>{currentIndex + 1} / {dueCards.length} cards</span>
              <span>{reviewedCount} reviewed this session</span>
            </div>
            <div className="h-1 rounded-full overflow-hidden" style={{ backgroundColor: "var(--bg-muted)" }}>
              <div
                className="h-full rounded-full transition-all"
                style={{
                  width: `${((currentIndex) / dueCards.length) * 100}%`,
                  backgroundColor: "var(--accent)",
                }}
              />
            </div>

            {/* Flip card */}
            <div
              className="flip-card w-full"
              style={{ height: "320px" }}
              onClick={() => !isFlipped && setIsFlipped(true)}
            >
              <div className={`flip-card-inner ${isFlipped ? "flipped" : ""}`}>
                {/* Front */}
                <div
                  className="flip-card-front rounded-2xl flex flex-col p-8 cursor-pointer select-none"
                  style={{
                    backgroundColor: "var(--bg-card)",
                    border: "1px solid var(--border)",
                    boxShadow: "var(--shadow-card)",
                  }}
                >
                  <div className="flex items-center gap-2 mb-4">
                    <span
                      className="text-[10px] font-semibold px-2 py-0.5 rounded-full"
                      style={{ backgroundColor: "var(--accent-muted)", color: "var(--accent-text)" }}
                    >
                      {currentCard.subject}
                    </span>
                    {currentCard.topic && (
                      <span
                        className="text-[10px] px-2 py-0.5 rounded-full"
                        style={{ backgroundColor: "var(--bg-muted)", color: "var(--text-muted)" }}
                      >
                        {currentCard.topic}
                      </span>
                    )}
                    <span
                      className="text-[10px] px-2 py-0.5 rounded-full ml-auto"
                      style={{ backgroundColor: "var(--bg-muted)", color: "var(--text-muted)" }}
                    >
                      {CARD_TYPE_LABELS[currentCard.card_type] ?? currentCard.card_type}
                    </span>
                  </div>

                  <div className="flex-1 flex items-center justify-center">
                    <p
                      className="text-center text-lg font-medium leading-relaxed"
                      style={{ color: "var(--text-primary)" }}
                    >
                      {currentCard.front}
                    </p>
                  </div>

                  <p
                    className="text-center text-xs mt-4"
                    style={{ color: "var(--text-muted)" }}
                  >
                    Tap to reveal answer
                  </p>
                </div>

                {/* Back */}
                <div
                  className="flip-card-back rounded-2xl flex flex-col p-8"
                  style={{
                    backgroundColor: "var(--bg-card)",
                    border: "1px solid var(--border)",
                    boxShadow: "var(--shadow-card)",
                  }}
                >
                  <div className="flex items-center gap-2 mb-4">
                    <span
                      className="text-[10px] font-semibold px-2 py-0.5 rounded-full"
                      style={{ backgroundColor: "rgba(34,197,94,0.15)", color: "#4ade80" }}
                    >
                      Answer
                    </span>
                  </div>

                  <div className="flex-1 overflow-auto">
                    <p
                      className="text-sm leading-relaxed whitespace-pre-wrap"
                      style={{ color: "var(--text-primary)" }}
                    >
                      {currentCard.back}
                    </p>
                  </div>

                  {/* Quality buttons */}
                  <div className="mt-4 grid grid-cols-4 gap-2">
                    {QUALITY_BUTTONS.map(({ label, quality, color, bg }) => (
                      <button
                        key={label}
                        onClick={(e) => {
                          e.stopPropagation();
                          answerMutation.mutate({ cardId: currentCard.id, quality });
                        }}
                        disabled={answerMutation.isPending}
                        className="py-2 rounded-xl text-xs font-semibold transition-all disabled:opacity-60"
                        style={{ backgroundColor: bg, color }}
                      >
                        {label}
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            </div>

            {!isFlipped && (
              <button
                onClick={() => setIsFlipped(true)}
                className="w-full py-3 rounded-xl text-sm font-semibold transition-all"
                style={{
                  backgroundColor: "var(--accent-muted)",
                  color: "var(--accent-text)",
                  border: "1px solid var(--accent)",
                }}
              >
                Show Answer
              </button>
            )}
          </div>
        )
      )}
    </div>
  );
}

function MiniStat({
  icon,
  label,
  value,
  color,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
  color: string;
}) {
  return (
    <div
      className="rounded-xl p-4"
      style={{
        backgroundColor: "var(--bg-card)",
        border: "1px solid var(--border)",
        boxShadow: "var(--shadow-card)",
      }}
    >
      <div className="flex items-center gap-2 mb-1">
        <span className={color}>{icon}</span>
        <span className="text-xs" style={{ color: "var(--text-muted)" }}>
          {label}
        </span>
      </div>
      <p className="text-2xl font-bold" style={{ color: "var(--text-primary)" }}>
        {value}
      </p>
    </div>
  );
}

function EmptyState({
  hasSubject,
  onGenerate,
  generating,
}: {
  hasSubject: boolean;
  onGenerate?: () => void;
  generating: boolean;
}) {
  return (
    <div
      className="rounded-2xl p-12 text-center"
      style={{
        backgroundColor: "var(--bg-card)",
        border: "1px solid var(--border)",
      }}
    >
      <BookOpen size={40} className="mx-auto mb-4" style={{ color: "var(--text-muted)" }} />
      <p className="font-semibold mb-1" style={{ color: "var(--text-primary)" }}>
        No cards due for review
      </p>
      <p className="text-sm mb-6" style={{ color: "var(--text-muted)" }}>
        {hasSubject
          ? "Great work! Generate more cards from your knowledge base."
          : "Select a subject and generate cards from your uploaded documents."}
      </p>
      {onGenerate && (
        <button
          onClick={onGenerate}
          disabled={generating}
          className="flex items-center gap-2 mx-auto px-5 py-2.5 rounded-xl text-sm font-semibold text-white disabled:opacity-60"
          style={{ backgroundColor: "var(--accent)" }}
        >
          {generating ? <Loader2 size={16} className="animate-spin" /> : <Sparkles size={16} />}
          {generating ? "Generating…" : "Generate Flashcards"}
        </button>
      )}
    </div>
  );
}

function SessionComplete({
  reviewedCount,
  onReset,
  onGenerate,
  generating,
}: {
  reviewedCount: number;
  onReset: () => void;
  onGenerate?: () => void;
  generating: boolean;
}) {
  return (
    <div
      className="rounded-2xl p-12 text-center"
      style={{
        backgroundColor: "var(--bg-card)",
        border: "1px solid var(--border)",
      }}
    >
      <CheckCircle size={48} className="mx-auto mb-4 text-emerald-400" />
      <h3 className="text-xl font-bold mb-1" style={{ color: "var(--text-primary)" }}>
        Session Complete!
      </h3>
      <p className="text-sm mb-6" style={{ color: "var(--text-muted)" }}>
        You reviewed {reviewedCount} card{reviewedCount !== 1 ? "s" : ""} this session.
      </p>
      <div className="flex items-center justify-center gap-3">
        <button
          onClick={onReset}
          className="flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-semibold transition-all"
          style={{
            backgroundColor: "var(--bg-muted)",
            color: "var(--text-primary)",
            border: "1px solid var(--border)",
          }}
        >
          <RotateCcw size={16} />
          Review Again
        </button>
        {onGenerate && (
          <button
            onClick={onGenerate}
            disabled={generating}
            className="flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-semibold text-white disabled:opacity-60"
            style={{ backgroundColor: "var(--accent)" }}
          >
            {generating ? <Loader2 size={16} className="animate-spin" /> : <Sparkles size={16} />}
            More Cards
          </button>
        )}
      </div>
    </div>
  );
}
