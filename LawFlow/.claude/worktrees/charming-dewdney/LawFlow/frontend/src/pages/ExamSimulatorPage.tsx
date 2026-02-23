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

export default function ExamSimulatorPage() {
  const queryClient = useQueryClient();
  const fireRewardToast = useRewardToast();
  const [phase, setPhase] = useState<Phase>("setup");
  const [exam, setExam] = useState<ExamAssessment | null>(null);
  const [results, setResults] = useState<ExamAssessment | null>(null);
  const [currentQ, setCurrentQ] = useState(0);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [gradingProgress, setGradingProgress] = useState(0);

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

  const generateMutation = useMutation({
    mutationFn: () => generateExam(subject, format, numQuestions, timeMinutes),
    onSuccess: (data) => {
      setExam(data);
      setCurrentQ(0);
      setAnswers({});
      setPhase("exam");
    },
  });

  const timer = useTimer(timeMinutes * 60, () => {
    handleSubmitExam();
  });

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

  const handleSubmitExam = async () => {
    if (!exam?.questions) return;

    timer.stop();
    setPhase("grading");
    setGradingProgress(0);

    const questions = exam.questions;
    let graded = 0;

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

    try {
      const rewardsSnapshot = queryClient.getQueryData<RewardsSummary>(["rewards-summary"]);
      const finalResults = await completeExam(exam.id);
      setResults(finalResults);
      setPhase("results");
      queryClient.invalidateQueries({ queryKey: ["mastery"] });
      queryClient.invalidateQueries({ queryKey: ["exam-history"] });
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

  // ── SETUP PHASE ──
  if (phase === "setup") {
    return (
      <div className="space-y-6">
        <PageHeader
          icon={<FileQuestion size={24} />}
          title="Exam Simulator"
          subtitle="Timed practice exams weighted by your professor's patterns"
        />

        <div>
          <label className="duo-label">Subject</label>
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
            {SUBJECTS_REQUIRED.map((s) => {
              const mastery = masteryData.find((m) => m.subject === s.value);
              return (
                <button
                  key={s.value}
                  onClick={() => setSubject(s.value)}
                  className="duo-card text-left p-3 transition-all"
                  style={{
                    backgroundColor: subject === s.value ? "var(--blue-bg)" : "var(--card-bg)",
                    borderColor: subject === s.value ? "var(--blue)" : undefined,
                    borderBottomColor: subject === s.value ? "var(--blue-dark)" : undefined,
                  }}
                >
                  <span style={{
                    fontSize: "14px",
                    fontWeight: 700,
                    color: subject === s.value ? "var(--blue-dark)" : "var(--text-primary)",
                  }}>
                    {s.label}
                  </span>
                  {mastery && (
                    <span style={{ display: "block", fontSize: "12px", fontWeight: 600, marginTop: "4px", color: "var(--text-muted)" }}>
                      {mastery.mastery_score.toFixed(0)}% mastery
                    </span>
                  )}
                </button>
              );
            })}
          </div>
        </div>

        <div>
          <label className="duo-label">Exam Format</label>
          <div className="grid grid-cols-2 gap-2">
            {EXAM_FORMATS.map((f) => (
              <button
                key={f.value}
                onClick={() => setFormat(f.value)}
                className="duo-card text-left p-3 transition-all"
                style={{
                  backgroundColor: format === f.value ? "var(--blue-bg)" : "var(--card-bg)",
                  borderColor: format === f.value ? "var(--blue)" : undefined,
                  borderBottomColor: format === f.value ? "var(--blue-dark)" : undefined,
                }}
              >
                <span style={{
                  fontSize: "14px",
                  fontWeight: 700,
                  color: format === f.value ? "var(--blue-dark)" : "var(--text-primary)",
                }}>
                  {f.label}
                </span>
                <span style={{ display: "block", fontSize: "12px", fontWeight: 600, marginTop: "4px", color: "var(--text-muted)" }}>
                  {f.desc}
                </span>
              </button>
            ))}
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="duo-label">Questions: {numQuestions}</label>
            <input
              type="range"
              min={1}
              max={15}
              value={numQuestions}
              onChange={(e) => setNumQuestions(Number(e.target.value))}
              className="w-full"
              style={{ accentColor: "var(--green)" }}
              title="Number of questions"
            />
            <div className="flex justify-between mt-1" style={{ fontSize: "12px", fontWeight: 600, color: "var(--text-muted)" }}>
              <span>1 (quick)</span>
              <span>15 (full exam)</span>
            </div>
          </div>
          <div>
            <label className="duo-label">Time Limit: {timeMinutes} min</label>
            <input
              type="range"
              min={10}
              max={180}
              step={5}
              value={timeMinutes}
              onChange={(e) => setTimeMinutes(Number(e.target.value))}
              className="w-full"
              style={{ accentColor: "var(--green)" }}
              title="Time limit in minutes"
            />
            <div className="flex justify-between mt-1" style={{ fontSize: "12px", fontWeight: 600, color: "var(--text-muted)" }}>
              <span>10 min</span>
              <span>3 hours</span>
            </div>
          </div>
        </div>

        <button
          onClick={() => generateMutation.mutate()}
          disabled={!subject || generateMutation.isPending}
          className="duo-btn duo-btn-green w-full py-4 flex items-center justify-center gap-3"
          style={{ fontSize: "16px" }}
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
            className="p-4 flex items-start gap-3"
            style={{
              backgroundColor: "var(--red-bg)",
              border: "2px solid var(--red)",
              borderBottom: "4px solid var(--red-dark)",
              borderRadius: "var(--radius-lg)",
            }}
          >
            <AlertTriangle size={18} style={{ color: "var(--red-dark)" }} className="shrink-0 mt-0.5" />
            <div>
              <p style={{ fontSize: "14px", fontWeight: 800, color: "var(--red-dark)" }}>
                Failed to generate exam
              </p>
              <p style={{ fontSize: "13px", fontWeight: 500, marginTop: "4px", color: "var(--text-secondary)" }}>
                {(generateMutation.error as { response?: { data?: { error?: string } } })?.response?.data?.error ||
                  (generateMutation.error as Error)?.message ||
                  "Make sure you have uploaded documents for this subject."}
              </p>
              <p style={{ fontSize: "13px", fontWeight: 500, marginTop: "4px", color: "var(--text-secondary)" }}>
                If the message says no topics were found, go to AutoTeach and click &quot;Seed database&quot; first.
              </p>
            </div>
          </div>
        )}

        {history.length > 0 && (
          <div>
            <div className="flex items-center gap-2 mb-3">
              <History size={16} style={{ color: "var(--text-muted)" }} />
              <h3 style={{ fontSize: "13px", fontWeight: 800, textTransform: "uppercase", letterSpacing: "0.06em", color: "var(--text-secondary)" }}>
                Recent Exams
              </h3>
            </div>
            <div className="space-y-2">
              {history.map((h) => (
                <Card key={h.id} padding="sm" className="flex items-center justify-between">
                  <div>
                    <span style={{ fontSize: "14px", fontWeight: 700, color: "var(--text-primary)" }}>
                      {SUBJECTS_REQUIRED.find((s) => s.value === h.subject)?.label || h.subject}
                    </span>
                    <span style={{ fontSize: "12px", fontWeight: 600, marginLeft: "8px", color: "var(--text-muted)" }}>
                      {h.total_questions}Q · {h.assessment_type} ·{" "}
                      {h.completed_at
                        ? new Date(h.completed_at).toLocaleDateString()
                        : "Incomplete"}
                    </span>
                  </div>
                  {h.score != null && (
                    <span
                      style={{ fontSize: "18px", fontWeight: 900, color: scoreColor(h.score) }}
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

  // ── EXAM PHASE ──
  if (phase === "exam" && exam && currentQuestion) {
    const answeredCount = Object.keys(answers).filter(
      (id) => answers[id]?.trim()
    ).length;

    return (
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <FileQuestion size={20} style={{ color: "var(--blue)" }} />
            <span style={{ fontSize: "14px", fontWeight: 800, color: "var(--text-primary)" }}>
              {SUBJECTS_REQUIRED.find((s) => s.value === exam.subject)?.label}
            </span>
          </div>

          <div
            className={`flex items-center gap-2 px-4 py-1.5 text-sm font-mono ${
              timer.urgent ? "animate-pulse" : ""
            }`}
            style={{
              borderRadius: "var(--radius-full)",
              backgroundColor: timer.urgent ? "var(--red-bg)" : "var(--card-bg)",
              color: timer.urgent ? "var(--red)" : "var(--text-primary)",
              border: `2px solid ${timer.urgent ? "var(--red)" : "var(--border)"}`,
              fontWeight: 800,
            }}
          >
            <Clock size={14} />
            {timer.display}
          </div>
        </div>

        <div>
          <div className="flex justify-between mb-1" style={{ fontSize: "12px", fontWeight: 700, color: "var(--text-muted)" }}>
            <span>Question {currentQ + 1} of {totalQuestions}</span>
            <span>{answeredCount} answered</span>
          </div>
          <div className="duo-progress-track">
            <div
              className="duo-progress-fill"
              style={{
                width: `${((currentQ + 1) / totalQuestions) * 100}%`,
                backgroundColor: "var(--blue)",
              }}
            />
          </div>
        </div>

        <div className="flex gap-1.5 flex-wrap">
          {exam.questions?.map((q, i) => {
            const answered = !!answers[q.id]?.trim();
            const isCurrent = i === currentQ;
            return (
              <button
                key={q.id}
                onClick={() => setCurrentQ(i)}
                className="w-7 h-7 text-xs transition-all"
                style={{
                  borderRadius: "var(--radius-sm)",
                  backgroundColor: isCurrent
                    ? "var(--blue)"
                    : answered
                    ? "var(--green-bg)"
                    : "var(--card-bg)",
                  color: isCurrent
                    ? "white"
                    : answered
                    ? "var(--green-dark)"
                    : "var(--text-muted)",
                  border: `2px solid ${
                    isCurrent
                      ? "var(--blue)"
                      : answered
                      ? "var(--green)"
                      : "var(--border)"
                  }`,
                  fontWeight: 800,
                }}
              >
                {i + 1}
              </button>
            );
          })}
        </div>

        <Card padding="lg" style={{ borderRadius: "var(--radius-xl)" }}>
          <div className="flex items-center gap-2 mb-4">
            <Badge variant="navy">
              {currentQuestion.question_type === "mc"
                ? "Multiple Choice"
                : currentQuestion.question_type === "essay"
                ? "Essay"
                : "Issue Spotting"}
            </Badge>
            {currentQuestion.topic && (
              <Badge>{currentQuestion.topic}</Badge>
            )}
          </div>

          <div className="prose-tutor mb-6">
            <ReactMarkdown>
              {cleanMarkdown(currentQuestion.question_text)}
            </ReactMarkdown>
          </div>

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
                    className="duo-card w-full text-left p-3 transition-all flex items-start gap-3"
                    style={{
                      backgroundColor: selected ? "var(--blue-bg)" : "var(--card-bg)",
                      borderColor: selected ? "var(--blue)" : undefined,
                      borderBottomColor: selected ? "var(--blue-dark)" : undefined,
                    }}
                  >
                    <span
                      className="shrink-0 w-6 h-6 rounded-full flex items-center justify-center"
                      style={{
                        fontSize: "12px",
                        fontWeight: 800,
                        backgroundColor: selected ? "var(--blue)" : "var(--surface-bg)",
                        color: selected ? "white" : "var(--text-muted)",
                      }}
                    >
                      {letter}
                    </span>
                    <span style={{
                      fontSize: "14px",
                      fontWeight: 600,
                      color: selected ? "var(--blue-dark)" : "var(--text-primary)",
                    }}>
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
              className="duo-input w-full resize-none"
              style={{ fontSize: "14px" }}
            />
          )}
        </Card>

        <div className="flex items-center justify-between">
          <button
            onClick={() => setCurrentQ((i) => Math.max(0, i - 1))}
            disabled={currentQ === 0}
            className="duo-btn duo-btn-outline flex items-center gap-2 disabled:opacity-30"
          >
            <ChevronLeft size={16} /> Previous
          </button>

          {currentQ < totalQuestions - 1 ? (
            <button
              onClick={() => setCurrentQ((i) => Math.min(totalQuestions - 1, i + 1))}
              className="duo-btn duo-btn-blue flex items-center gap-2"
            >
              Next <ChevronRight size={16} />
            </button>
          ) : (
            <button
              onClick={handleSubmitExam}
              className="duo-btn duo-btn-green flex items-center gap-2"
            >
              <Send size={16} /> Submit Exam
            </button>
          )}
        </div>
      </div>
    );
  }

  // ── GRADING PHASE ──
  if (phase === "grading") {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          <Loader2
            size={48}
            className="mx-auto animate-spin mb-6"
            style={{ color: "var(--blue)" }}
          />
          <h2 style={{ fontSize: "22px", fontWeight: 900, color: "var(--text-primary)", marginBottom: "8px" }}>
            Grading Your Exam...
          </h2>
          <p style={{ fontSize: "15px", fontWeight: 500, color: "var(--text-muted)", marginBottom: "16px" }}>
            AI is evaluating your answers with IRAC rubric analysis
          </p>
          <div className="duo-progress-track w-64 mx-auto">
            <div
              className="duo-progress-fill"
              style={{
                width: `${gradingProgress}%`,
                backgroundColor: "var(--blue)",
              }}
            />
          </div>
          <p style={{ fontSize: "13px", fontWeight: 600, color: "var(--text-muted)", marginTop: "8px" }}>
            {gradingProgress}% complete
          </p>
        </div>
      </div>
    );
  }

  // ── RESULTS PHASE ──
  if (phase === "results" && results) {
    const score = results.score ?? 0;
    const irac = results.irac_breakdown;
    const topicBreakdown = results.topic_breakdown || {};

    return (
      <div className="space-y-6">
        <div className="text-center">
          <Trophy
            size={48}
            className="mx-auto mb-4"
            style={{ color: scoreColor(score) }}
          />
          <p style={{ fontSize: "64px", fontWeight: 900, color: scoreColor(score) }}>
            {score.toFixed(0)}
          </p>
          <p style={{ fontSize: "18px", fontWeight: 800, marginTop: "4px", color: "var(--text-primary)" }}>
            {scoreLabel(score)}
          </p>
          <p style={{ fontSize: "14px", fontWeight: 600, marginTop: "4px", color: "var(--text-muted)" }}>
            {results.total_questions} questions ·{" "}
            {results.time_taken_minutes?.toFixed(0) ?? "?"} min ·{" "}
            {results.assessment_type}
          </p>
        </div>

        {irac && Object.values(irac).some((v) => v !== null) && (
          <Card padding="lg">
            <h3 className="flex items-center gap-2 mb-4" style={{ fontSize: "14px", fontWeight: 800, color: "var(--text-primary)" }}>
              <Target size={16} style={{ color: "var(--blue)" }} />
              IRAC Component Breakdown
            </h3>
            <div className="space-y-3">
              {[
                { key: "issue_spotting", label: "Issue Spotting", weight: "30%" },
                { key: "rule_accuracy", label: "Rule Accuracy", weight: "20%" },
                { key: "application_depth", label: "Application Depth", weight: "35%" },
                { key: "conclusion_support", label: "Conclusion Support", weight: "15%" },
              ].map(({ key, label, weight }) => {
                const val = irac[key as keyof typeof irac];
                if (val == null) return null;
                return (
                  <div key={key}>
                    <div className="flex items-center justify-between mb-1">
                      <span style={{ fontSize: "13px", fontWeight: 700, color: "var(--text-primary)" }}>
                        {label}{" "}
                        <span style={{ color: "var(--text-muted)" }}>({weight})</span>
                      </span>
                      <span style={{ fontSize: "14px", fontWeight: 900, color: scoreColor(val) }}>
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

        {Object.keys(topicBreakdown).length > 0 && (
          <Card padding="lg">
            <h3 className="flex items-center gap-2 mb-4" style={{ fontSize: "14px", fontWeight: 800, color: "var(--text-primary)" }}>
              <BarChart2 size={16} style={{ color: "var(--blue)" }} />
              Topic Performance
            </h3>
            <div className="space-y-2">
              {Object.entries(topicBreakdown)
                .sort(([, a], [, b]) => a - b)
                .map(([topic, topicScore]) => (
                  <div key={topic} className="flex items-center gap-3">
                    <span style={{ fontSize: "13px", fontWeight: 600, color: "var(--text-secondary)" }} className="w-32 truncate">
                      {topic}
                    </span>
                    <div className="flex-1">
                      <MasteryBar score={topicScore} size="sm" />
                    </div>
                    <span style={{ fontSize: "13px", fontWeight: 900, color: scoreColor(topicScore) }} className="w-10 text-right">
                      {topicScore.toFixed(0)}
                    </span>
                  </div>
                ))}
            </div>
          </Card>
        )}

        <div>
          <h3 className="flex items-center gap-2 mb-3" style={{ fontSize: "14px", fontWeight: 800, color: "var(--text-primary)" }}>
            <BookOpen size={16} style={{ color: "var(--blue)" }} />
            Question-by-Question Review
          </h3>
          <div className="space-y-3">
            {results.questions?.map((q, i) => (
              <QuestionReview key={q.id} question={q} index={i} />
            ))}
          </div>
        </div>

        <div className="flex gap-3">
          <button
            onClick={resetExam}
            className="duo-btn duo-btn-outline flex-1 flex items-center justify-center gap-2 py-3"
          >
            <RotateCcw size={16} />
            New Exam
          </button>
          <button
            onClick={() => {
              resetExam();
              setSubject(results.subject);
            }}
            className="duo-btn duo-btn-green flex-1 flex items-center justify-center gap-2 py-3"
          >
            <Zap size={16} />
            Retake Same Subject
          </button>
        </div>
      </div>
    );
  }

  return null;
}

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
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full text-left p-4 flex items-center gap-3 transition-colors"
        style={{ color: "var(--text-primary)" }}
      >
        {qScore >= 60 ? (
          <CheckCircle size={18} style={{ color: "var(--green)" }} className="shrink-0" />
        ) : (
          <XCircle size={18} style={{ color: "var(--red)" }} className="shrink-0" />
        )}
        <span style={{ fontSize: "14px", fontWeight: 700 }} className="flex-1 truncate">
          Q{index + 1}: {question.question_text.slice(0, 80)}...
        </span>
        <span style={{ fontSize: "14px", fontWeight: 900, color: scoreColor(qScore) }} className="shrink-0">
          {qScore.toFixed(0)}
        </span>
        <ChevronRight
          size={16}
          className={`shrink-0 transition-transform ${expanded ? "rotate-90" : ""}`}
          style={{ color: "var(--text-muted)" }}
        />
      </button>

      {expanded && (
        <div className="px-4 pb-4 space-y-3" style={{ borderTop: "1px solid var(--border)" }}>
          <div className="pt-3">
            <p className="duo-label" style={{ marginBottom: "4px" }}>Your Answer</p>
            <div
              className="rounded-lg p-3"
              style={{
                fontSize: "14px",
                fontWeight: 600,
                backgroundColor: "var(--surface-bg)",
                color: "var(--text-primary)",
              }}
            >
              {question.student_answer || (
                <span style={{ color: "var(--text-muted)" }}>(No answer provided)</span>
              )}
            </div>
          </div>

          {grading && question.question_type === "essay" && (
            <div className="space-y-2">
              {grading.strengths && (
                <div className="flex items-start gap-2">
                  <CheckCircle size={14} style={{ color: "var(--green)" }} className="shrink-0 mt-0.5" />
                  <p style={{ fontSize: "13px", fontWeight: 600, color: "var(--text-secondary)" }}>
                    <strong>Strengths:</strong> {grading.strengths}
                  </p>
                </div>
              )}
              {grading.weaknesses && (
                <div className="flex items-start gap-2">
                  <AlertTriangle size={14} style={{ color: "var(--orange)" }} className="shrink-0 mt-0.5" />
                  <p style={{ fontSize: "13px", fontWeight: 600, color: "var(--text-secondary)" }}>
                    <strong>Needs work:</strong> {grading.weaknesses}
                  </p>
                </div>
              )}
              {grading.issues_missed && grading.issues_missed.length > 0 && (
                <div className="flex items-start gap-2">
                  <XCircle size={14} style={{ color: "var(--red)" }} className="shrink-0 mt-0.5" />
                  <p style={{ fontSize: "13px", fontWeight: 600, color: "var(--text-secondary)" }}>
                    <strong>Issues missed:</strong>{" "}
                    {grading.issues_missed.join(", ")}
                  </p>
                </div>
              )}
            </div>
          )}

          {grading?.feedback ? (
            <div>
              <p className="duo-label" style={{ marginBottom: "4px" }}>Feedback</p>
              <div className="prose-tutor" style={{ fontSize: "13px" }}>
                <ReactMarkdown>{cleanMarkdown(grading.feedback)}</ReactMarkdown>
              </div>
            </div>
          ) : question.feedback && !grading ? (
            <div>
              <p className="duo-label" style={{ marginBottom: "4px" }}>Feedback</p>
              <div className="prose-tutor" style={{ fontSize: "13px" }}>
                <ReactMarkdown>{cleanMarkdown(question.feedback)}</ReactMarkdown>
              </div>
            </div>
          ) : null}
        </div>
      )}
    </Card>
  );
}
