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
    label: "Again",
    sublabel: "No clue",
    btnClass: "duo-btn duo-btn-red",
    icon: XCircle,
  },
  {
    quality: 2,
    label: "Hard",
    sublabel: "Wrong / close",
    btnClass: "duo-btn duo-btn-orange",
    icon: Brain,
  },
  {
    quality: 3,
    label: "Good",
    sublabel: "Got it, took effort",
    btnClass: "duo-btn duo-btn-blue",
    icon: CheckCircle2,
  },
  {
    quality: 5,
    label: "Easy",
    sublabel: "Instant recall",
    btnClass: "duo-btn duo-btn-green",
    icon: Zap,
  },
];

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

  if (sessionComplete && sessionResults.length > 0) {
    const correct = sessionResults.filter((r) => r.quality >= 3).length;
    const total = sessionResults.length;
    const pct = Math.round((correct / total) * 100);

    return (
      <div className="max-w-2xl mx-auto">
        <div
          className="text-center mb-8 p-8"
          style={{
            background: "var(--gold-bg)",
            borderRadius: "var(--radius-xl)",
            border: "2px solid var(--gold)",
            borderBottom: "4px solid var(--gold-dark)",
          }}
        >
          <Trophy size={48} className="mx-auto mb-4" style={{ color: "var(--gold)" }} />
          <h2 style={{ fontSize: "22px", fontWeight: 900, color: "var(--text-primary)", marginBottom: "8px" }}>
            Session Complete!
          </h2>
          <p style={{ fontSize: "15px", fontWeight: 500, color: "var(--text-secondary)" }}>
            You reviewed {total} card{total > 1 ? "s" : ""}
          </p>
        </div>

        <div className="grid grid-cols-3 gap-4 mb-8">
          <div className="duo-card p-4 text-center">
            <p style={{ fontSize: "30px", fontWeight: 900, color: "var(--green)" }}>{correct}</p>
            <p style={{ fontSize: "13px", fontWeight: 700, color: "var(--text-secondary)", marginTop: "4px" }}>Correct</p>
          </div>
          <div className="duo-card p-4 text-center">
            <p style={{ fontSize: "30px", fontWeight: 900, color: "var(--red)" }}>
              {total - correct}
            </p>
            <p style={{ fontSize: "13px", fontWeight: 700, color: "var(--text-secondary)", marginTop: "4px" }}>Needs Review</p>
          </div>
          <div className="duo-card p-4 text-center">
            <p style={{
              fontSize: "30px",
              fontWeight: 900,
              color: pct >= 80 ? "var(--green)" : pct >= 60 ? "var(--orange)" : "var(--red)",
            }}>
              {pct}%
            </p>
            <p style={{ fontSize: "13px", fontWeight: 700, color: "var(--text-secondary)", marginTop: "4px" }}>Accuracy</p>
          </div>
        </div>

        <div className="space-y-2 mb-8">
          {sessionResults.map((r, i) => (
            <div
              key={i}
              className="duo-card p-3 flex items-center gap-3"
            >
              {r.quality >= 3 ? (
                <CheckCircle2 size={16} style={{ color: "var(--green)" }} className="shrink-0" />
              ) : (
                <XCircle size={16} style={{ color: "var(--red)" }} className="shrink-0" />
              )}
              <p style={{ fontSize: "14px", fontWeight: 600, color: "var(--text-primary)" }} className="truncate flex-1">
                {r.card.front}
              </p>
              <span style={{ fontSize: "13px", fontWeight: 700, color: "var(--text-secondary)" }} className="shrink-0">
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
          className="duo-btn duo-btn-green w-full py-3"
        >
          Start New Session
        </button>
      </div>
    );
  }

  if (currentCard && !sessionComplete) {
    return (
      <div className="max-w-2xl mx-auto">
        <div className="flex items-center gap-3 mb-6">
          <Layers size={20} style={{ color: "var(--blue)" }} />
          <h2 style={{ fontSize: "18px", fontWeight: 800, color: "var(--text-primary)" }}>Flash Cards</h2>
          <div className="flex-1" />
          <span style={{ fontSize: "14px", fontWeight: 600, color: "var(--text-secondary)" }}>
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
            className="duo-btn duo-btn-outline"
            style={{ padding: "6px 12px", fontSize: "13px", textTransform: "none" }}
          >
            End Session
          </button>
        </div>

        <div className="duo-progress-track mb-6">
          <div
            className="duo-progress-fill"
            style={{
              width: `${((currentIndex + 1) / (dueCards?.length ?? 1)) * 100}%`,
              backgroundColor: "var(--blue)",
            }}
          />
        </div>

        <div className="flex items-center gap-2 mb-4">
          <span className="duo-badge" style={{ fontSize: "12px", padding: "4px 10px" }}>
            {SUBJECTS.find((s) => s.value === currentCard.subject)?.label ||
              currentCard.subject}
          </span>
          {currentCard.topic && (
            <span className="duo-badge" style={{ fontSize: "12px", padding: "4px 10px" }}>
              {currentCard.topic}
            </span>
          )}
          <span className="duo-badge duo-badge-navy" style={{ fontSize: "12px", padding: "4px 10px" }}>
            {CARD_TYPE_LABELS[currentCard.card_type] || currentCard.card_type}
          </span>
        </div>

        <div
          onClick={() => !flipped && setFlipped(true)}
          className="duo-card mb-6 transition-all"
          style={{
            minHeight: "280px",
            padding: "32px",
            cursor: flipped ? "default" : "pointer",
            borderColor: flipped ? "var(--blue)" : undefined,
            borderBottomColor: flipped ? "var(--blue-dark)" : undefined,
          }}
        >
          {!flipped ? (
            <div className="flex flex-col h-full">
              <p style={{
                fontSize: "11px",
                fontWeight: 800,
                textTransform: "uppercase",
                letterSpacing: "0.08em",
                color: "var(--text-muted)",
                marginBottom: "16px",
              }}>
                Question
              </p>
              <div className="flex-1 flex items-center">
                <p style={{ fontSize: "18px", fontWeight: 700, lineHeight: 1.6, color: "var(--text-primary)" }}>
                  {currentCard.front}
                </p>
              </div>
              <p style={{ fontSize: "13px", fontWeight: 600, color: "var(--text-muted)", textAlign: "center", marginTop: "24px" }}>
                Click to reveal answer
              </p>
            </div>
          ) : (
            <div className="flex flex-col h-full">
              <p style={{
                fontSize: "11px",
                fontWeight: 800,
                textTransform: "uppercase",
                letterSpacing: "0.08em",
                color: "var(--blue)",
                marginBottom: "16px",
              }}>
                Answer
              </p>
              <div className="flex-1 prose-tutor leading-relaxed">
                <ReactMarkdown>{cleanMarkdown(currentCard.back)}</ReactMarkdown>
              </div>
            </div>
          )}
        </div>

        {flipped && (
          <div>
            <p style={{ fontSize: "13px", fontWeight: 700, color: "var(--text-secondary)", textAlign: "center", marginBottom: "12px" }}>
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
                    className={`${btn.btnClass} flex flex-col items-center gap-1 py-3 px-2`}
                    style={{ textTransform: "none", letterSpacing: "normal" }}
                  >
                    <Icon size={18} />
                    <span style={{ fontSize: "14px", fontWeight: 800 }}>{btn.label}</span>
                    <span style={{ fontSize: "10px", fontWeight: 600, opacity: 0.8 }}>
                      {btn.sublabel}
                    </span>
                    <span style={{ fontSize: "10px", fontWeight: 600, opacity: 0.6, marginTop: "2px" }}>
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

  return (
    <div>
      <div className="flex items-center gap-3 mb-6">
        <Layers size={24} style={{ color: "var(--blue)" }} />
        <div>
          <h2 style={{ fontSize: "30px", fontWeight: 900, color: "var(--text-primary)" }}>Flash Cards</h2>
          <p style={{ fontSize: "15px", fontWeight: 500, color: "var(--text-secondary)" }}>
            Spaced repetition for long-term retention
          </p>
        </div>
      </div>

      {stats && (
        <div className="grid grid-cols-5 gap-3 mb-6">
          {[
            { label: "Total Cards", value: stats.total, color: "var(--text-primary)" },
            { label: "Due Now", value: stats.due, color: "var(--orange)" },
            { label: "New", value: stats.new, color: "var(--blue)" },
            { label: "Learning", value: stats.learning, color: "var(--purple)" },
            { label: "Mature", value: stats.mature, color: "var(--green)" },
          ].map((s) => (
            <div key={s.label} className="duo-card p-3 text-center">
              <p style={{ fontSize: "28px", fontWeight: 900, color: s.color }}>{s.value}</p>
              <p style={{ fontSize: "13px", fontWeight: 700, color: "var(--text-secondary)", marginTop: "4px" }}>{s.label}</p>
            </div>
          ))}
        </div>
      )}

      {hasDue ? (
        <button
          onClick={() => {
            setCurrentIndex(0);
            setFlipped(false);
            setSessionComplete(false);
            setSessionResults([]);
          }}
          className="duo-btn duo-btn-green w-full mb-6 py-4 flex items-center justify-center gap-3"
          style={{ fontSize: "16px" }}
        >
          <RotateCcw size={20} />
          Start Review — {dueCards?.length} card{(dueCards?.length ?? 0) > 1 ? "s" : ""} due
          <ChevronRight size={18} />
        </button>
      ) : (
        <div className="duo-card p-6 mb-6 text-center">
          <CheckCircle2 size={32} className="mx-auto mb-3" style={{ color: "var(--green)" }} />
          <p style={{ fontSize: "17px", fontWeight: 800, color: "var(--text-primary)", marginBottom: "4px" }}>
            {stats?.total ? "All caught up!" : "No flash cards yet"}
          </p>
          <p style={{ fontSize: "15px", fontWeight: 500, color: "var(--text-secondary)" }}>
            {stats?.total
              ? "No cards due for review right now. Come back later or generate more cards."
              : "Upload documents first, then generate flash cards from your study material."}
          </p>
        </div>
      )}

      <h3 style={{
        fontSize: "13px",
        fontWeight: 800,
        textTransform: "uppercase",
        letterSpacing: "0.06em",
        color: "var(--text-secondary)",
        marginBottom: "12px",
      }}>
        Generate Cards by Subject
      </h3>
      <div className="grid grid-cols-2 gap-3">
        {SUBJECTS.map((s) => (
          <div key={s.value} className="duo-card p-4 flex items-center justify-between">
            <div>
              <p style={{ fontSize: "15px", fontWeight: 700, color: "var(--text-primary)" }}>{s.label}</p>
              <p style={{ fontSize: "13px", fontWeight: 500, color: "var(--text-secondary)", marginTop: "4px" }}>
                Generate flashcards from uploaded material
              </p>
            </div>
            <button
              onClick={() => generateMutation.mutate(s.value)}
              disabled={generateMutation.isPending}
              className="duo-btn duo-btn-blue shrink-0"
              style={{ padding: "8px 16px", fontSize: "13px" }}
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
        <div className="animate-pulse mt-6 text-center" style={{ color: "var(--text-muted)" }}>
          Loading flash cards...
        </div>
      )}
    </div>
  );
}
