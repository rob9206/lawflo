import { useCallback, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ArrowLeft, Zap, ChevronDown } from "lucide-react";
import type { AutoTeachLesson } from "@/types/auto-teach";
import AutoTeachHeader from "@/components/auto-teach/AutoTeachHeader";
import LessonContent from "@/components/auto-teach/LessonContent";
import CaseCard from "@/components/auto-teach/CaseCard";
import ExamTrapCard from "@/components/auto-teach/ExamTrapCard";
import PracticeTab from "@/components/auto-teach/PracticeTab";

interface AutoTeachCardProps {
  lesson: AutoTeachLesson;
  onBack?: () => void;
}

export default function AutoTeachCard({ lesson, onBack }: AutoTeachCardProps) {
  const navigate = useNavigate();
  const quizRef = useRef<HTMLDivElement>(null);
  const [quizDone, setQuizDone] = useState(false);

  const scrollToQuiz = useCallback(() => {
    quizRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  }, []);

  const goBack = () => (onBack ? onBack() : navigate(-1));

  const hasTraps = lesson.examTraps && lesson.examTraps.length > 0;
  const hasPattern = Boolean(lesson.recognitionPattern);
  const hasNotes = lesson.additionalNotes && lesson.additionalNotes.length > 0;

  return (
    <div
      className="autoteach-card min-h-screen pb-28"
      style={{ backgroundColor: "var(--page-bg)", color: "var(--text-primary)" }}
    >
      {/* ── Sticky top bar ─────────────────────────────── */}
      <div
        className="sticky top-0 z-10 flex items-center justify-center border-b-2 px-4 py-3"
        style={{ borderColor: "var(--border)", backgroundColor: "var(--card-bg)" }}
      >
        <button
          type="button"
          onClick={goBack}
          aria-label="Go back"
          className="absolute left-4 border-none bg-transparent p-1"
          style={{ color: "var(--text-muted)" }}
        >
          <ArrowLeft size={22} />
        </button>

        <span
          className="text-[15px] uppercase tracking-[0.06em]"
          style={{ fontWeight: 800, color: "var(--text-primary)" }}
        >
          AutoTeach
        </span>

        <div className="absolute right-4 flex items-center gap-1">
          <Zap size={16} style={{ color: "var(--gold)" }} />
          <span className="text-sm" style={{ fontWeight: 800, color: "var(--gold)" }}>+25</span>
        </div>
      </div>

      {/* ── Main scrollable content ───────────────────── */}
      <div className="mx-auto w-full max-w-[680px]">
        <AutoTeachHeader lesson={lesson} />

        <div className="mt-5 space-y-6 px-4">
          {/* Definition + Key Elements */}
          <LessonContent lesson={lesson} />

          {/* Case Example (only if AI extracted a real case) */}
          {lesson.caseExample && <CaseCard caseExample={lesson.caseExample} />}

          {/* Exam Traps (only if AI extracted traps) */}
          {hasTraps && (
            <section>
              <h3
                className="mb-3 px-1 text-[12px] uppercase tracking-[0.1em]"
                style={{ fontWeight: 800, color: "var(--orange-dark)" }}
              >
                Exam Traps
              </h3>
              <div className="space-y-3">
                {lesson.examTraps!.map((trap, index) => (
                  <ExamTrapCard key={`${trap.trap}-${index}`} trap={trap.trap} detail={trap.detail} />
                ))}
              </div>
            </section>
          )}

          {/* Recognition Pattern (only if AI extracted one) */}
          {hasPattern && lesson.recognitionPattern && (
            <section
              className="rounded-2xl border-2 border-b-4 p-6"
              style={{
                backgroundColor: "var(--blue-bg)",
                borderColor: "var(--blue)",
                borderBottomColor: "var(--blue-dark)",
              }}
            >
              <h3
                className="mb-2 text-[12px] uppercase tracking-[0.1em]"
                style={{ fontWeight: 800, color: "var(--blue-dark)" }}
              >
                Recognition Pattern
              </h3>
              <p className="mb-2 text-sm" style={{ fontWeight: 700, color: "var(--text-secondary)" }}>
                If you see on the exam:
              </p>
              <p
                className="mb-3 text-[17px] italic leading-7"
                style={{ fontWeight: 700, color: "var(--blue-dark)" }}
              >
                &ldquo;{lesson.recognitionPattern.trigger}&rdquo;
              </p>
              <div
                className="flex items-center gap-2 rounded-xl border-2 px-4 py-3"
                style={{ borderColor: "var(--border)", backgroundColor: "var(--card-bg)" }}
              >
                <span className="text-xl" style={{ fontWeight: 700, color: "var(--green)" }}>
                  &rarr;
                </span>
                <span className="text-base" style={{ fontWeight: 800, color: "var(--text-primary)" }}>
                  {lesson.recognitionPattern.response}
                </span>
              </div>
            </section>
          )}

          {/* Additional Notes (generic, topic-adaptive sections) */}
          {hasNotes &&
            lesson.additionalNotes!.map((note, ni) => (
              <section key={`note-${ni}`} className="duo-card rounded-2xl p-6">
                <h3
                  className="mb-3 text-[12px] uppercase tracking-[0.1em]"
                  style={{ fontWeight: 800, color: "var(--text-secondary)" }}
                >
                  {note.heading}
                </h3>
                <div className="space-y-3">
                  {note.items.map((item, ii) => (
                    <div key={`${note.heading}-${ii}`} className="flex items-center gap-3">
                      <span
                        className="flex h-[30px] w-[30px] shrink-0 items-center justify-center rounded-lg border-2 text-[13px]"
                        style={{
                          fontWeight: 800,
                          borderColor: "var(--border)",
                          backgroundColor: "var(--page-bg)",
                          color: "var(--text-muted)",
                        }}
                      >
                        {ii + 1}
                      </span>
                      <p>
                        <span className="text-base" style={{ fontWeight: 700, color: "var(--text-primary)" }}>
                          {item.label}
                        </span>
                        <span className="ml-1 text-[15px]" style={{ color: "var(--text-secondary)" }}>
                          - {item.detail}
                        </span>
                      </p>
                    </div>
                  ))}
                </div>
              </section>
            ))}

          {/* Practice Quiz */}
          <div ref={quizRef}>
            <h3
              className="mb-3 px-1 text-[12px] uppercase tracking-[0.1em]"
              style={{ fontWeight: 800, color: "var(--blue-dark)" }}
            >
              Test Yourself
            </h3>
            <PracticeTab
              questions={lesson.practiceQuestions}
              onReviewLesson={() => window.scrollTo({ top: 0, behavior: "smooth" })}
              onNextTopic={() => (onBack ? onBack() : navigate("/auto-teach"))}
              onComplete={() => setQuizDone(true)}
            />
          </div>
        </div>
      </div>

      {/* ── Sticky bottom bar ────────────────────────── */}
      <div
        className="fixed bottom-0 left-0 right-0 z-10 border-t-2 px-4 py-3"
        style={{ borderColor: "var(--border)", backgroundColor: "var(--card-bg)" }}
      >
        <div className="mx-auto flex max-w-[680px] items-center justify-between">
          <div className="flex items-center gap-2">
            <Zap size={16} style={{ color: "var(--green)" }} />
            <span className="text-sm" style={{ fontWeight: 700, color: "var(--text-primary)" }}>
              {lesson.title}
            </span>
            <span className="text-xs" style={{ fontWeight: 600, color: "var(--text-muted)" }}>
              {lesson.category}
            </span>
          </div>

          {!quizDone ? (
            <button
              type="button"
              onClick={scrollToQuiz}
              className="duo-btn duo-btn-green flex items-center gap-2"
              style={{ padding: "8px 20px", fontSize: "14px" }}
            >
              Test Yourself
              <ChevronDown size={16} />
            </button>
          ) : (
            <button
              type="button"
              onClick={() => (onBack ? onBack() : navigate("/auto-teach"))}
              className="duo-btn duo-btn-green flex items-center gap-2"
              style={{ padding: "8px 20px", fontSize: "14px" }}
            >
              Next Topic
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
