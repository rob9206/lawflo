import { useState, useCallback, useRef } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  getDueCards,
  getCardStats,
  answerCard,
  generateCardsForSubject,
  completeFlashcardSession,
  type FlashCard,
} from "@/api/review";
import { getMastery } from "@/api/progress";
import { useRewardToast } from "@/hooks/useRewardToast";
import type { RewardsSummary } from "@/types";
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
import { SUBJECTS_FULL, CARD_TYPE_LABELS, QUALITY_BUTTONS } from "@/lib/constants";
import Card from "@/components/ui/Card";
import StatCard from "@/components/ui/StatCard";
import PageHeader from "@/components/ui/PageHeader";
import Badge from "@/components/ui/Badge";
import EmptyState from "@/components/ui/EmptyState";
import SubjectFilter from "@/components/ui/SubjectFilter";

export default function FlashcardPage() {
  const queryClient = useQueryClient();
  const fireRewardToast = useRewardToast();
  const [selectedSubject, setSelectedSubject] = useState("");
  const [currentIndex, setCurrentIndex] = useState(0);
  const [isFlipped, setIsFlipped] = useState(false);
  const [reviewedCount, setReviewedCount] = useState(0);
  const [sessionDone, setSessionDone] = useState(false);
  const [generating, setGenerating] = useState(false);
  const qualitySum = useRef(0);

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
    onSuccess: (_data, variables) => {
      qualitySum.current += variables.quality;
      const next = currentIndex + 1;
      const newCount = reviewedCount + 1;
      setReviewedCount(newCount);
      setIsFlipped(false);

      if (next >= dueCards.length) {
        setSessionDone(true);
        // Snapshot rewards cache BEFORE the XP-awarding API call
        const rewardsSnapshot = queryClient.getQueryData<RewardsSummary>(["rewards-summary"]);
        const avgQuality = qualitySum.current / newCount;
        void completeFlashcardSession(newCount, avgQuality)
          .then(() => fireRewardToast(rewardsSnapshot))
          .catch(() => {});
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
      qualitySum.current = 0;
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
    qualitySum.current = 0;
    await refetchCards();
  }, [refetchCards]);

  const handleSubjectSelect = useCallback((value: string) => {
    setSelectedSubject(value);
    setCurrentIndex(0);
    setIsFlipped(false);
    setSessionDone(false);
    setReviewedCount(0);
    qualitySum.current = 0;
  }, []);

  const currentCard: FlashCard | undefined = dueCards[currentIndex];

  const generateButton = selectedSubject ? (
    <button
      onClick={handleGenerate}
      disabled={generating}
      className="btn-primary flex items-center gap-2"
    >
      {generating ? (
        <Loader2 size={16} className="animate-spin" />
      ) : (
        <Sparkles size={16} />
      )}
      {generating ? "Generating…" : "Generate Cards"}
    </button>
  ) : undefined;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Flashcards"
        subtitle="Spaced repetition review — SM-2 algorithm"
        action={generateButton}
      />

      {/* Stats row */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <StatCard icon={<CreditCard size={16} />} label="Total Cards" value={String(stats?.total ?? 0)} color="text-indigo-400" />
        <StatCard icon={<Zap size={16} />} label="Due Today" value={String(stats?.due ?? 0)} color="text-amber-400" />
        <StatCard icon={<Brain size={16} />} label="Learning" value={String(stats?.learning ?? 0)} color="text-blue-400" />
        <StatCard icon={<Star size={16} />} label="Mature" value={String(stats?.mature ?? 0)} color="text-emerald-400" />
      </div>

      <SubjectFilter
        subjects={SUBJECTS_FULL}
        selected={selectedSubject}
        onSelect={handleSubjectSelect}
        masteryData={masteryData}
      />

      {/* Card area */}
      {cardsLoading ? (
        <div className="flex items-center justify-center h-64">
          <Loader2 size={24} className="animate-spin text-ui-muted" />
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
          icon={<BookOpen size={40} />}
          message="No cards due for review"
          sub={
            selectedSubject
              ? "Great work! Generate more cards from your knowledge base."
              : "Select a subject and generate cards from your uploaded documents."
          }
          action={
            selectedSubject ? (
              <button
                onClick={handleGenerate}
                disabled={generating}
                className="btn-primary flex items-center gap-2 mx-auto"
              >
                {generating ? <Loader2 size={16} className="animate-spin" /> : <Sparkles size={16} />}
                {generating ? "Generating…" : "Generate Flashcards"}
              </button>
            ) : undefined
          }
        />
      ) : (
        currentCard && (
          <div className="space-y-4">
            {/* Progress */}
            <div className="flex items-center justify-between text-xs text-ui-muted">
              <span>{currentIndex + 1} / {dueCards.length} cards</span>
              <span>{reviewedCount} reviewed this session</span>
            </div>
            <div className="progress-track h-1">
              <div
                className="progress-fill h-full"
                style={{ width: `${((currentIndex) / dueCards.length) * 100}%` }}
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
                <Card padding="none" className="flip-card-front rounded-2xl flex flex-col p-8 cursor-pointer select-none">
                  <div className="flex items-center gap-2 mb-4">
                    <Badge variant="accent">{currentCard.subject}</Badge>
                    {currentCard.topic && (
                      <Badge variant="muted">{currentCard.topic}</Badge>
                    )}
                    <Badge variant="muted" className="ml-auto">
                      {CARD_TYPE_LABELS[currentCard.card_type] ?? currentCard.card_type}
                    </Badge>
                  </div>

                  <div className="flex-1 flex items-center justify-center">
                    <p className="text-center text-lg font-medium leading-relaxed text-ui-primary">
                      {currentCard.front}
                    </p>
                  </div>

                  <p className="text-center text-xs mt-4 text-ui-muted">
                    Tap to reveal answer
                  </p>
                </Card>

                {/* Back */}
                <Card padding="none" className="flip-card-back rounded-2xl flex flex-col p-8">
                  <div className="flex items-center gap-2 mb-4">
                    <Badge variant="success">Answer</Badge>
                  </div>

                  <div className="flex-1 overflow-auto">
                    <p className="text-sm leading-relaxed whitespace-pre-wrap text-ui-primary">
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
                </Card>
              </div>
            </div>

            {!isFlipped && (
              <button
                onClick={() => setIsFlipped(true)}
                className="btn-secondary w-full"
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
    <Card padding="none" className="p-12 text-center">
      <CheckCircle size={48} className="mx-auto mb-4 text-emerald-400" />
      <h3 className="text-xl font-bold mb-1 text-ui-primary">
        Session Complete!
      </h3>
      <p className="text-sm mb-6 text-ui-muted">
        You reviewed {reviewedCount} card{reviewedCount !== 1 ? "s" : ""} this session.
      </p>
      <div className="flex items-center justify-center gap-3">
        <button onClick={onReset} className="btn-secondary flex items-center gap-2">
          <RotateCcw size={16} />
          Review Again
        </button>
        {onGenerate && (
          <button
            onClick={onGenerate}
            disabled={generating}
            className="btn-primary flex items-center gap-2"
          >
            {generating ? <Loader2 size={16} className="animate-spin" /> : <Sparkles size={16} />}
            More Cards
          </button>
        )}
      </div>
    </Card>
  );
}
