import { useCallback, useMemo, useState } from "react";
import { CheckCircle2, XCircle } from "lucide-react";
import { cn } from "@/lib/utils";
import type { PracticeQuestion } from "@/types/auto-teach";

interface PracticeTabProps {
  questions: PracticeQuestion[];
  onReviewLesson?: () => void;
  onNextTopic?: () => void;
  onComplete?: () => void;
}

export default function PracticeTab({ questions, onReviewLesson, onNextTopic, onComplete }: PracticeTabProps) {
  const [qIndex, setQIndex] = useState(0);
  const [selected, setSelected] = useState<string | null>(null);
  const [revealed, setRevealed] = useState(false);
  const [score, setScore] = useState({ correct: 0, total: 0 });

  const question = questions[qIndex] ?? questions[0];
  const isLast = qIndex >= questions.length - 1;
  const isCorrect = selected === question.correct;
  const canReveal = Boolean(selected) && !revealed;

  const advanceToNext = useCallback(() => {
    setSelected(null);
    setRevealed(false);
    setQIndex((i) => i + 1);
  }, []);

  const handleReveal = useCallback(() => {
    setRevealed(true);
    const nowCorrect = selected === question.correct;
    setScore((s) => ({
      correct: s.correct + (nowCorrect ? 1 : 0),
      total: s.total + 1,
    }));
    if (isLast) {
      onComplete?.();
    }
  }, [selected, question.correct, isLast, onComplete]);

  const choiceStyles = useMemo(() => {
    return question.choices.reduce<Record<string, { bg: string; border: string; text: string }>>(
      (acc, choice) => {
        if (!revealed) {
          if (selected === choice.id) {
            acc[choice.id] = {
              bg: "var(--blue-bg)",
              border: "var(--blue)",
              text: "var(--blue-dark)",
            };
          } else {
            acc[choice.id] = {
              bg: "var(--card-bg)",
              border: "var(--border)",
              text: "var(--text-muted)",
            };
          }
          return acc;
        }

        if (choice.id === question.correct) {
          acc[choice.id] = {
            bg: "var(--green-bg)",
            border: "var(--green)",
            text: "var(--green-dark)",
          };
          return acc;
        }

        if (choice.id === selected) {
          acc[choice.id] = {
            bg: "var(--red-bg)",
            border: "var(--red)",
            text: "var(--red-dark)",
          };
          return acc;
        }

        acc[choice.id] = {
          bg: "var(--card-bg)",
          border: "var(--border)",
          text: "var(--text-muted)",
        };
        return acc;
      },
      {}
    );
  }, [question.choices, question.correct, revealed, selected]);

  return (
    <section className="duo-card animate-fade-up rounded-2xl p-6">
      <div className="mb-4 flex items-center justify-between">
        <span className="text-sm" style={{ fontWeight: 700, color: "var(--text-muted)" }}>
          Question {qIndex + 1} of {questions.length}
        </span>
        {score.total > 0 && (
          <span className="text-sm" style={{ fontWeight: 700, color: "var(--green-dark)" }}>
            {score.correct}/{score.total} correct
          </span>
        )}
      </div>

      <p className="mb-5 text-lg leading-8" style={{ fontWeight: 600, color: "var(--text-primary)" }}>
        {question.stem}
      </p>

      <div className="mb-5 space-y-3">
        {question.choices.map((choice) => {
          const style = choiceStyles[choice.id];
          return (
            <button
              key={choice.id}
              type="button"
              disabled={revealed}
              onClick={() => setSelected(choice.id)}
              className={cn(
                "flex w-full items-start gap-3 rounded-2xl border-2 border-b-4 p-4 text-left transition-all",
                {
                  "opacity-40": revealed && choice.id !== selected && choice.id !== question.correct,
                }
              )}
              style={{
                backgroundColor: style.bg,
                borderColor: style.border,
                borderBottomColor: style.border,
              }}
            >
              <span
                className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border-2 text-sm"
                style={{
                  fontWeight: 900,
                  color: style.text,
                  borderColor: style.border,
                  backgroundColor:
                    revealed && choice.id === question.correct ? "var(--green-bg)" : "transparent",
                }}
              >
                {choice.id}
              </span>
              <span className="pt-1 text-base leading-7" style={{ color: "var(--text-primary)" }}>
                {choice.text}
              </span>
            </button>
          );
        })}
      </div>

      {!revealed && (
        <button
          type="button"
          onClick={handleReveal}
          disabled={!canReveal}
          className={cn(
            "w-full rounded-2xl border-none border-b-4 px-6 py-3 text-base uppercase tracking-[0.03em]",
            canReveal ? "duo-btn duo-btn-green" : "cursor-not-allowed"
          )}
          style={
            canReveal
              ? {}
              : {
                  backgroundColor: "var(--border)",
                  color: "var(--text-muted)",
                  borderBottomColor: "var(--text-muted)",
                }
          }
        >
          Check Answer
        </button>
      )}

      {revealed && (
        <div
          className="animate-fade-up mt-4 rounded-2xl border-2 p-5"
          style={{
            backgroundColor: isCorrect ? "var(--green-bg)" : "var(--red-bg)",
            borderColor: isCorrect ? "var(--green)" : "var(--red)",
          }}
        >
          <div className="mb-2 flex items-center gap-2">
            {isCorrect ? (
              <CheckCircle2 size={22} style={{ color: "var(--green)" }} />
            ) : (
              <XCircle size={22} style={{ color: "var(--red)" }} />
            )}
            <span
              className="text-lg"
              style={{ fontWeight: 800, color: isCorrect ? "var(--green-dark)" : "var(--red-dark)" }}
            >
              {isCorrect ? "Great job!" : `Correct answer: ${question.correct}`}
            </span>
          </div>

          <p className="text-base leading-7" style={{ color: "var(--text-primary)" }}>
            {question.explanation}
          </p>

          <div className="mt-4 flex flex-wrap gap-2">
            {!isLast ? (
              <button type="button" onClick={advanceToNext} className="duo-btn duo-btn-green">
                Next Question
              </button>
            ) : (
              <>
                <button
                  type="button"
                  onClick={() => onReviewLesson?.()}
                  className="duo-btn duo-btn-outline"
                >
                  Review Lesson
                </button>
                <button
                  type="button"
                  onClick={() => onNextTopic?.()}
                  className="duo-btn duo-btn-green"
                >
                  Next Topic
                </button>
              </>
            )}
          </div>
        </div>
      )}
    </section>
  );
}
