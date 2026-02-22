import { useState, useEffect, useCallback, useRef } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  generateExam,
  submitAnswer,
  completeExam,
  getExamHistory,
  type ExamAssessment,
  type ExamQuestion,
  type IracGrading,
} from "@/api/exam";
import { getMastery } from "@/api/progress";
import { useRewardToast } from "@/hooks/useRewardToast";
import type { RewardsSummary } from "@/types";
import { cleanMarkdown, scoreColor, scoreLabel } from "@/lib/utils";
import { SUBJECTS_REQUIRED, EXAM_FORMATS } from "@/lib/constants";
import ReactMarkdown from "react-markdown";
import PageHeader from "@/components/ui/PageHeader";
import Card from "@/components/ui/Card";
import Badge from "@/components/ui/Badge";
import MasteryBar from "@/components/ui/MasteryBar";
import {
  FileQuestion,
  Clock,
  ChevronLeft,
  ChevronRight,
  CheckCircle,
  XCircle,
  Loader2,
  BarChart2,
  Trophy,
  AlertTriangle,
  BookOpen,
  Target,
  Zap,
  RotateCcw,
  Send,
  History,
} from "lucide-react";

type Phase = "setup" | "exam" | "grading" | "results";

// ── Timer Hook ─────────────────────────────────────────────────────────────

function useTimer(totalSeconds: number, onExpire: () => void) {
  const [remaining, setRemaining] = useState(totalSeconds);
  const [running, setRunning] = useState(false);
  const expireRef = useRef(onExpire);
  expireRef.current = onExpire;

  useEffect(() => {
    if (!running || remaining <= 0) return;
    const interval = setInterval(() => {
      setRemaining((prev) => {
        if (prev <= 1) {
          setRunning(false);
          expireRef.current();
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
    return () => clearInterval(interval);
  }, [running, remaining]);

  const start = useCallback(() => setRunning(true), []);
  const stop = useCallback(() => setRunning(false), []);

  const minutes = Math.floor(remaining / 60);
  const seconds = remaining % 60;
  const display = `${minutes}:${seconds.toString().padStart(2, "0")}`;
  const pct = (remaining / totalSeconds) * 100;
  const urgent = remaining < totalSeconds * 0.1;

  return { display, pct, urgent, remaining, start, stop, running };
}

// ── Main Component ─────────────────────────────────────────────────────────

export default function ExamSimulatorPage() {
  const queryClient = useQueryClient();
  const fireRewardToast = useRewardToast();
  const [phase, setPhase] = useState<Phase>("setup");
  const [exam, setExam] = useState<ExamAssessment | null>(null);
  const [results, setResults] = useState<ExamAssessment | null>(null);
  const [currentQ, setCurrentQ] = useState(0);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [gradingProgress, setGradingProgress] = useState(0);

  // Setup state
  const [subject, setSubject] = useState("");
  const [format, setFormat] = useState("mixed");
  const [numQuestions, setNumQuestions] = useState(5);
  const [timeMinutes, setTimeMinutes] = useState(60);

  const { data: masteryData = [] } = useQuery({
    queryKey: ["mastery"],
    queryFn: getMastery,
  });

  const { data: history = [] } = useQuery({
    queryKey: ["exam-history", subject],
    queryFn: () => getExamHistory(subject || undefined, 5),
  });

  // Generate exam mutation
  const generateMutation = useMutation({
    mutationFn: () => generateExam(subject, format, numQuestions, timeMinutes),
    onSuccess: (data) => {
      setExam(data);
      setCurrentQ(0);
      setAnswers({});
      setPhase("exam");
    },
  });

  // Timer
  const timer = useTimer(timeMinutes * 60, () => {
    handleSubmitExam();
  });

  // Start timer when exam begins
  useEffect(() => {
    if (phase === "exam" && exam && !timer.running) {
      timer.start();
    }
  }, [phase, exam]);

  const currentQuestion = exam?.questions?.[currentQ];
  const totalQuestions = exam?.questions?.length ?? 0;

  const setAnswer = (questionId: string, answer: string) => {
    setAnswers((prev) => ({ ...prev, [questionId]: answer }));
  };

  // Submit all answers and grade
  const handleSubmitExam = async () => {
    if (!exam?.questions) return;

    timer.stop();
    setPhase("grading");
    setGradingProgress(0);

    const questions = exam.questions;
    let graded = 0;

    // Grade each answer
    for (const q of questions) {
      const answer = answers[q.id] || "";
      try {
        await submitAnswer(q.id, answer);
      } catch (e) {
        console.error(`Failed to grade question ${q.id}:`, e);
      }
      graded++;
      setGradingProgress(Math.round((graded / questions.length) * 100));
    }

    // Complete the exam
    try {
      // Snapshot rewards cache BEFORE the XP-awarding API call
      const rewardsSnapshot = queryClient.getQueryData<RewardsSummary>(["rewards-summary"]);
      const finalResults = await completeExam(exam.id);
      setResults(finalResults);
      setPhase("results");
      queryClient.invalidateQueries({ queryKey: ["mastery"] });
      queryClient.invalidateQueries({ queryKey: ["exam-history"] });
      // Fire reward toast with pre-captured snapshot
      void fireRewardToast(rewardsSnapshot).catch(() => {});
    } catch (e) {
      console.error("Failed to complete exam:", e);
    }
  };

  const resetExam = () => {
    setPhase("setup");
    setExam(null);
    setResults(null);
    setCurrentQ(0);
    setAnswers({});
    setGradingProgress(0);
  };

  // ── SETUP PHASE ──────────────────────────────────────────────────────────
  if (phase === "setup") {
    return (
      <div className="space-y-6">
        <PageHeader
          icon={<FileQuestion size={24} />}
          title="Exam Simulator"
          subtitle="Timed practice exams weighted by your professor's patterns"
        />

        {/* Subject selection */}
        <div>
          <label className="block text-sm font-semibold mb-2 text-ui-primary">
            Subject
          </label>
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
            {SUBJECTS_REQUIRED.map((s) => {
              const mastery = masteryData.find((m) => m.subject === s.value);
              return (
                <button
                  key={s.value}
                  onClick={() => setSubject(s.value)}
                  className="text-left rounded-xl p-3 transition-all"
                  style={{
                    backgroundColor:
                      subject === s.value ? "var(--accent-muted)" : "var(--bg-card)",
                    border: `1px solid ${
                      subject === s.value ? "var(--accent)" : "var(--border)"
                    }`,
                    color:
                      subject === s.value
                        ? "var(--accent-text)"
                        : "var(--text-primary)",
                  }}
                >
                  <span className="text-sm font-medium">{s.label}</span>
                  {mastery && (
                    <span className="block text-xs mt-0.5 text-ui-muted">
                      {mastery.mastery_score.toFixed(0)}% mastery
                    </span>
                  )}
                </button>
              );
            })}
          </div>
        </div>

        {/* Format selection */}
        <div>
          <label className="block text-sm font-semibold mb-2 text-ui-primary">
            Exam Format
          </label>
          <div className="grid grid-cols-2 gap-2">
            {EXAM_FORMATS.map((f) => (
              <button
                key={f.value}
                onClick={() => setFormat(f.value)}
                className="text-left rounded-xl p-3 transition-all"
                style={{
                  backgroundColor:
                    format === f.value ? "var(--accent-muted)" : "var(--bg-card)",
                  border: `1px solid ${
                    format === f.value ? "var(--accent)" : "var(--border)"
                  }`,
                }}
              >
                <span
                  className="text-sm font-medium"
                  style={{
                    color:
                      format === f.value
                        ? "var(--accent-text)"
                        : "var(--text-primary)",
                  }}
                >
                  {f.label}
                </span>
                <span className="block text-xs mt-0.5 text-ui-muted">
                  {f.desc}
                </span>
              </button>
            ))}
          </div>
        </div>

        {/* Configuration */}
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-semibold mb-2 text-ui-primary">
              Questions: {numQuestions}
            </label>
            <input
              type="range"
              min={1}
              max={15}
              value={numQuestions}
              onChange={(e) => setNumQuestions(Number(e.target.value))}
              className="w-full accent-indigo-500"
              title="Number of questions"
            />
            <div className="flex justify-between text-xs mt-1 text-ui-muted">
              <span>1 (quick)</span>
              <span>15 (full exam)</span>
            </div>
          </div>
          <div>
            <label className="block text-sm font-semibold mb-2 text-ui-primary">
              Time Limit: {timeMinutes} min
            </label>
            <input
              type="range"
              min={10}
              max={180}
              step={5}
              value={timeMinutes}
              onChange={(e) => setTimeMinutes(Number(e.target.value))}
              className="w-full accent-indigo-500"
              title="Time limit in minutes"
            />
            <div className="flex justify-between text-xs mt-1 text-ui-muted">
              <span>10 min</span>
              <span>3 hours</span>
            </div>
          </div>
        </div>

        {/* Start button */}
        <button
          onClick={() => generateMutation.mutate()}
          disabled={!subject || generateMutation.isPending}
          className="btn-primary w-full py-4 text-lg flex items-center justify-center gap-3"
        >
          {generateMutation.isPending ? (
            <>
              <Loader2 size={20} className="animate-spin" />
              Generating Exam...
            </>
          ) : (
            <>
              <Zap size={20} />
              Start Exam
            </>
          )}
        </button>

        {generateMutation.isError && (
          <div
            className="rounded-xl p-4 flex items-start gap-3"
            style={{
              backgroundColor: "rgba(239,68,68,0.1)",
              border: "1px solid rgba(239,68,68,0.3)",
            }}
          >
            <AlertTriangle size={18} className="text-red-400 shrink-0 mt-0.5" />
            <div>
              <p className="text-sm font-medium text-red-400">
                Failed to generate exam
              </p>
              <p className="text-xs mt-1 text-ui-muted">
                {(generateMutation.error as Error)?.message ||
                  "Make sure you have uploaded documents for this subject."}
              </p>
            </div>
          </div>
        )}

        {/* Past exam history */}
        {history.length > 0 && (
          <div>
            <div className="flex items-center gap-2 mb-3">
              <History size={16} className="text-ui-muted" />
              <h3 className="text-sm font-semibold text-ui-primary">
                Recent Exams
              </h3>
            </div>
            <div className="space-y-2">
              {history.map((h) => (
                <Card key={h.id} padding="sm" className="flex items-center justify-between">
                  <div>
                    <span className="text-sm font-medium text-ui-primary">
                      {SUBJECTS_REQUIRED.find((s) => s.value === h.subject)?.label || h.subject}
                    </span>
                    <span className="text-xs ml-2 text-ui-muted">
                      {h.total_questions}Q · {h.assessment_type} ·{" "}
                      {h.completed_at
                        ? new Date(h.completed_at).toLocaleDateString()
                        : "Incomplete"}
                    </span>
                  </div>
                  {h.score != null && (
                    <span
                      className="text-lg font-bold"
                      style={{ color: scoreColor(h.score) }}
                    >
                      {h.score.toFixed(0)}%
                    </span>
                  )}
                </Card>
              ))}
            </div>
          </div>
        )}
      </div>
    );
  }

  // ── EXAM PHASE ───────────────────────────────────────────────────────────
  if (phase === "exam" && exam && currentQuestion) {
    const answeredCount = Object.keys(answers).filter(
      (id) => answers[id]?.trim()
    ).length;

    return (
      <div className="space-y-4">
        {/* Top bar: timer + progress */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <FileQuestion size={20} className="text-accent-label" />
            <span className="text-sm font-semibold text-ui-primary">
              {SUBJECTS_REQUIRED.find((s) => s.value === exam.subject)?.label}
            </span>
          </div>

          {/* Timer */}
          <div
            className={`flex items-center gap-2 px-4 py-1.5 rounded-full text-sm font-mono font-bold ${
              timer.urgent ? "animate-pulse" : ""
            }`}
            style={{
              backgroundColor: timer.urgent
                ? "rgba(239,68,68,0.15)"
                : "var(--bg-card)",
              color: timer.urgent ? "#ef4444" : "var(--text-primary)",
              border: `1px solid ${
                timer.urgent ? "rgba(239,68,68,0.4)" : "var(--border)"
              }`,
            }}
          >
            <Clock size={14} />
            {timer.display}
          </div>
        </div>

        {/* Progress bar */}
        <div>
          <div className="flex justify-between text-xs mb-1 text-ui-muted">
            <span>
              Question {currentQ + 1} of {totalQuestions}
            </span>
            <span>{answeredCount} answered</span>
          </div>
          <div className="progress-track">
            <div
              className="progress-fill"
              style={{
                width: `${((currentQ + 1) / totalQuestions) * 100}%`,
                backgroundColor: "var(--accent)",
              }}
            />
          </div>
        </div>

        {/* Question navigator dots */}
        <div className="flex gap-1.5 flex-wrap">
          {exam.questions?.map((q, i) => {
            const answered = !!answers[q.id]?.trim();
            const isCurrent = i === currentQ;
            return (
              <button
                key={q.id}
                onClick={() => setCurrentQ(i)}
                className="w-7 h-7 rounded-lg text-xs font-medium transition-all"
                style={{
                  backgroundColor: isCurrent
                    ? "var(--accent)"
                    : answered
                    ? "rgba(34,197,94,0.2)"
                    : "var(--bg-card)",
                  color: isCurrent
                    ? "white"
                    : answered
                    ? "#22c55e"
                    : "var(--text-muted)",
                  border: `1px solid ${
                    isCurrent
                      ? "var(--accent)"
                      : answered
                      ? "rgba(34,197,94,0.3)"
                      : "var(--border)"
                  }`,
                }}
              >
                {i + 1}
              </button>
            );
          })}
        </div>

        {/* Question card */}
        <Card padding="lg" className="rounded-2xl">
          {/* Question metadata */}
          <div className="flex items-center gap-2 mb-4">
            <Badge variant="accent">
              {currentQuestion.question_type === "mc"
                ? "Multiple Choice"
                : currentQuestion.question_type === "essay"
                ? "Essay"
                : "Issue Spotting"}
            </Badge>
            {currentQuestion.topic && (
              <Badge variant="muted">{currentQuestion.topic}</Badge>
            )}
          </div>

          {/* Question text */}
          <div className="prose-tutor mb-6">
            <ReactMarkdown>
              {cleanMarkdown(currentQuestion.question_text)}
            </ReactMarkdown>
          </div>

          {/* Answer input */}
          {currentQuestion.question_type === "mc" &&
          currentQuestion.options ? (
            <div className="space-y-2">
              {currentQuestion.options.map((option, i) => {
                const letter = String.fromCharCode(65 + i);
                const selected = answers[currentQuestion.id] === letter;
                return (
                  <button
                    key={i}
                    onClick={() => setAnswer(currentQuestion.id, letter)}
                    className="w-full text-left rounded-xl p-3 transition-all flex items-start gap-3"
                    style={{
                      backgroundColor: selected
                        ? "var(--accent-muted)"
                        : "var(--bg-muted)",
                      border: `1px solid ${
                        selected ? "var(--accent)" : "var(--border)"
                      }`,
                    }}
                  >
                    <span
                      className="shrink-0 w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold"
                      style={{
                        backgroundColor: selected
                          ? "var(--accent)"
                          : "var(--bg-card)",
                        color: selected ? "white" : "var(--text-muted)",
                      }}
                    >
                      {letter}
                    </span>
                    <span
                      className="text-sm"
                      style={{
                        color: selected
                          ? "var(--accent-text)"
                          : "var(--text-primary)",
                      }}
                    >
                      {option.replace(/^[A-D]\)\s*/, "")}
                    </span>
                  </button>
                );
              })}
            </div>
          ) : (
            <textarea
              value={answers[currentQuestion.id] || ""}
              onChange={(e) => setAnswer(currentQuestion.id, e.target.value)}
              placeholder={
                currentQuestion.question_type === "essay"
                  ? "Write your IRAC analysis here...\n\nIssue: ...\nRule: ...\nApplication: ...\nConclusion: ..."
                  : "List all legal issues you can identify..."
              }
              rows={12}
              className="input-base w-full rounded-xl p-4 text-sm resize-none"
            />
          )}
        </Card>

        {/* Navigation */}
        <div className="flex items-center justify-between">
          <button
            onClick={() => setCurrentQ((i) => Math.max(0, i - 1))}
            disabled={currentQ === 0}
            className="btn-secondary flex items-center gap-2 disabled:opacity-30"
          >
            <ChevronLeft size={16} /> Previous
          </button>

          {currentQ < totalQuestions - 1 ? (
            <button
              onClick={() => setCurrentQ((i) => Math.min(totalQuestions - 1, i + 1))}
              className="flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium transition-all"
              style={{
                backgroundColor: "var(--accent-muted)",
                color: "var(--accent-text)",
                border: "1px solid var(--accent)",
              }}
            >
              Next <ChevronRight size={16} />
            </button>
          ) : (
            <button
              onClick={handleSubmitExam}
              className="btn-primary flex items-center gap-2"
            >
              <Send size={16} /> Submit Exam
            </button>
          )}
        </div>
      </div>
    );
  }

  // ── GRADING PHASE ────────────────────────────────────────────────────────
  if (phase === "grading") {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          <Loader2
            size={48}
            className="mx-auto animate-spin mb-6 text-accent-label"
          />
          <h2 className="text-xl font-bold mb-2 text-ui-primary">
            Grading Your Exam...
          </h2>
          <p className="text-sm mb-4 text-ui-muted">
            AI is evaluating your answers with IRAC rubric analysis
          </p>
          <div className="progress-track w-64 mx-auto">
            <div
              className="progress-fill"
              style={{
                width: `${gradingProgress}%`,
                backgroundColor: "var(--accent)",
              }}
            />
          </div>
          <p className="text-xs mt-2 text-ui-muted">
            {gradingProgress}% complete
          </p>
        </div>
      </div>
    );
  }

  // ── RESULTS PHASE ────────────────────────────────────────────────────────
  if (phase === "results" && results) {
    const score = results.score ?? 0;
    const irac = results.irac_breakdown;
    const topicBreakdown = results.topic_breakdown || {};

    return (
      <div className="space-y-6">
        {/* Score header */}
        <div className="text-center">
          <Trophy
            size={48}
            className="mx-auto mb-4"
            style={{ color: scoreColor(score) }}
          />
          <p
            className="text-6xl font-bold"
            style={{ color: scoreColor(score) }}
          >
            {score.toFixed(0)}
          </p>
          <p className="text-lg font-medium mt-1 text-ui-primary">
            {scoreLabel(score)}
          </p>
          <p className="text-sm mt-1 text-ui-muted">
            {results.total_questions} questions ·{" "}
            {results.time_taken_minutes?.toFixed(0) ?? "?"} min ·{" "}
            {results.assessment_type}
          </p>
        </div>

        {/* IRAC breakdown (for essays) */}
        {irac && Object.values(irac).some((v) => v !== null) && (
          <Card padding="lg">
            <h3 className="text-sm font-semibold mb-4 flex items-center gap-2 text-ui-primary">
              <Target size={16} className="text-accent-label" />
              IRAC Component Breakdown
            </h3>
            <div className="space-y-3">
              {[
                { key: "issue_spotting", label: "Issue Spotting", weight: "30%" },
                { key: "rule_accuracy", label: "Rule Accuracy", weight: "20%" },
                {
                  key: "application_depth",
                  label: "Application Depth",
                  weight: "35%",
                },
                {
                  key: "conclusion_support",
                  label: "Conclusion Support",
                  weight: "15%",
                },
              ].map(({ key, label, weight }) => {
                const val = irac[key as keyof typeof irac];
                if (val == null) return null;
                return (
                  <div key={key}>
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-xs font-medium text-ui-primary">
                        {label}{" "}
                        <span className="text-ui-muted">({weight})</span>
                      </span>
                      <span
                        className="text-sm font-bold"
                        style={{ color: scoreColor(val) }}
                      >
                        {val.toFixed(0)}
                      </span>
                    </div>
                    <MasteryBar score={val} size="sm" />
                  </div>
                );
              })}
            </div>
          </Card>
        )}

        {/* Topic breakdown */}
        {Object.keys(topicBreakdown).length > 0 && (
          <Card padding="lg">
            <h3 className="text-sm font-semibold mb-4 flex items-center gap-2 text-ui-primary">
              <BarChart2 size={16} className="text-accent-label" />
              Topic Performance
            </h3>
            <div className="space-y-2">
              {Object.entries(topicBreakdown)
                .sort(([, a], [, b]) => a - b)
                .map(([topic, topicScore]) => (
                  <div key={topic} className="flex items-center gap-3">
                    <span className="text-xs w-32 truncate text-ui-secondary">
                      {topic}
                    </span>
                    <div className="flex-1">
                      <MasteryBar score={topicScore} size="sm" />
                    </div>
                    <span
                      className="text-xs font-bold w-10 text-right"
                      style={{ color: scoreColor(topicScore) }}
                    >
                      {topicScore.toFixed(0)}
                    </span>
                  </div>
                ))}
            </div>
          </Card>
        )}

        {/* Per-question feedback */}
        <div>
          <h3 className="text-sm font-semibold mb-3 flex items-center gap-2 text-ui-primary">
            <BookOpen size={16} className="text-accent-label" />
            Question-by-Question Review
          </h3>
          <div className="space-y-3">
            {results.questions?.map((q, i) => (
              <QuestionReview key={q.id} question={q} index={i} />
            ))}
          </div>
        </div>

        {/* Actions */}
        <div className="flex gap-3">
          <button
            onClick={resetExam}
            className="btn-secondary flex-1 flex items-center justify-center gap-2 py-3"
          >
            <RotateCcw size={16} />
            New Exam
          </button>
          <button
            onClick={() => {
              resetExam();
              setSubject(results.subject);
            }}
            className="btn-primary flex-1 flex items-center justify-center gap-2 py-3"
          >
            <Zap size={16} />
            Retake Same Subject
          </button>
        </div>
      </div>
    );
  }

  // Fallback
  return null;
}

// ── Question Review Component ──────────────────────────────────────────────

function QuestionReview({
  question,
  index,
}: {
  question: ExamQuestion;
  index: number;
}) {
  const [expanded, setExpanded] = useState(false);
  const qScore = question.score ?? 0;

  let grading: IracGrading | null = null;
  if (question.feedback) {
    try {
      grading = JSON.parse(question.feedback);
    } catch {
      // Not JSON feedback
    }
  }

  return (
    <Card padding="none" className="overflow-hidden">
      {/* Header */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full text-left p-4 flex items-center gap-3 transition-colors text-ui-primary"
      >
        {qScore >= 60 ? (
          <CheckCircle size={18} className="text-emerald-400 shrink-0" />
        ) : (
          <XCircle size={18} className="text-red-400 shrink-0" />
        )}
        <span className="text-sm font-medium flex-1 truncate">
          Q{index + 1}: {question.question_text.slice(0, 80)}...
        </span>
        <span
          className="text-sm font-bold shrink-0"
          style={{ color: scoreColor(qScore) }}
        >
          {qScore.toFixed(0)}
        </span>
        <ChevronRight
          size={16}
          className={`shrink-0 transition-transform text-ui-muted ${
            expanded ? "rotate-90" : ""
          }`}
        />
      </button>

      {/* Expanded details */}
      {expanded && (
        <div className="px-4 pb-4 space-y-3" style={{ borderTop: "1px solid var(--border)" }}>
          <div className="pt-3">
            <p className="text-xs font-semibold uppercase mb-1 text-ui-muted">
              Your Answer
            </p>
            <div
              className="text-sm rounded-lg p-3"
              style={{
                backgroundColor: "var(--bg-muted)",
                color: "var(--text-primary)",
              }}
            >
              {question.student_answer || (
                <span className="text-ui-muted">(No answer provided)</span>
              )}
            </div>
          </div>

          {/* IRAC breakdown for essays */}
          {grading && question.question_type === "essay" && (
            <div className="space-y-2">
              {grading.strengths && (
                <div className="flex items-start gap-2">
                  <CheckCircle
                    size={14}
                    className="text-emerald-400 shrink-0 mt-0.5"
                  />
                  <p className="text-xs text-ui-secondary">
                    <strong>Strengths:</strong> {grading.strengths}
                  </p>
                </div>
              )}
              {grading.weaknesses && (
                <div className="flex items-start gap-2">
                  <AlertTriangle
                    size={14}
                    className="text-amber-400 shrink-0 mt-0.5"
                  />
                  <p className="text-xs text-ui-secondary">
                    <strong>Needs work:</strong> {grading.weaknesses}
                  </p>
                </div>
              )}
              {grading.issues_missed && grading.issues_missed.length > 0 && (
                <div className="flex items-start gap-2">
                  <XCircle
                    size={14}
                    className="text-red-400 shrink-0 mt-0.5"
                  />
                  <p className="text-xs text-ui-secondary">
                    <strong>Issues missed:</strong>{" "}
                    {grading.issues_missed.join(", ")}
                  </p>
                </div>
              )}
            </div>
          )}

          {/* Textual feedback */}
          {grading?.feedback ? (
            <div>
              <p className="text-xs font-semibold uppercase mb-1 text-ui-muted">
                Feedback
              </p>
              <div className="prose-tutor text-xs">
                <ReactMarkdown>
                  {cleanMarkdown(grading.feedback)}
                </ReactMarkdown>
              </div>
            </div>
          ) : question.feedback && !grading ? (
            <div>
              <p className="text-xs font-semibold uppercase mb-1 text-ui-muted">
                Feedback
              </p>
              <div className="prose-tutor text-xs">
                <ReactMarkdown>
                  {cleanMarkdown(question.feedback)}
                </ReactMarkdown>
              </div>
            </div>
          ) : null}
        </div>
      )}
    </Card>
  );
}
