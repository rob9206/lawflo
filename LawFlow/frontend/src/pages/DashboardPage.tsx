import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { getDashboard, getWeaknesses } from "@/api/progress";
import { getRecentSessions } from "@/api/tutor";
import { masteryColor } from "@/lib/utils";
import {
  Brain,
  Clock,
  Layers,
  BookOpen,
  AlertTriangle,
  Zap,
  GraduationCap,
  Upload,
  CreditCard,
  ChevronRight,
  Target,
  Activity,
} from "lucide-react";

const SUBJECT_LABELS: Record<string, string> = {
  con_law: "Constitutional Law",
  contracts: "Contracts",
  torts: "Torts",
  crim_law: "Criminal Law",
  civ_pro: "Civil Procedure",
  property: "Property",
  evidence: "Evidence",
  prof_responsibility: "Professional Responsibility",
};

const MODE_LABELS: Record<string, string> = {
  explain: "Explain",
  socratic: "Socratic",
  hypo: "Hypo Drill",
  issue_spot: "Issue Spot",
  irac: "IRAC",
  exam_strategy: "Exam Strategy",
};

function masteryLabel(score: number) {
  if (score >= 80) return "Mastered";
  if (score >= 60) return "Advanced";
  if (score >= 40) return "Proficient";
  if (score >= 20) return "Developing";
  return "Beginning";
}

function priorityLevel(score: number): "high" | "medium" | "low" {
  if (score < 30) return "high";
  if (score < 55) return "medium";
  return "low";
}

export default function DashboardPage() {
  const navigate = useNavigate();

  const { data: dashboard, isLoading } = useQuery({
    queryKey: ["dashboard"],
    queryFn: getDashboard,
  });

  const { data: weakTopics = [] } = useQuery({
    queryKey: ["weaknesses", 5],
    queryFn: () => getWeaknesses(5),
  });

  const { data: recentSessions = [] } = useQuery({
    queryKey: ["recent-sessions"],
    queryFn: () => getRecentSessions(5),
  });

  if (isLoading) {
    return (
      <div className="space-y-4 animate-pulse">
        <div className="h-8 rounded-lg w-64" style={{ backgroundColor: "var(--bg-muted)" }} />
        <div className="grid grid-cols-4 gap-4">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="h-24 rounded-xl" style={{ backgroundColor: "var(--bg-card)" }} />
          ))}
        </div>
      </div>
    );
  }

  const stats = dashboard?.stats;
  const subjects = dashboard?.subjects || [];
  const overallMastery = (stats?.overall_mastery ?? 0).toFixed(0);
  const priorityCount = weakTopics.filter((t) => t.mastery_score < 40).length;

  return (
    <div className="space-y-6">
      {/* ── Welcome header ─────────────────────────────────────────── */}
      <div className="flex items-start justify-between">
        <div>
          <h2 className="text-2xl font-bold" style={{ color: "var(--text-primary)" }}>
            Welcome back, Law Student
          </h2>
          <p className="text-sm mt-1" style={{ color: "var(--text-secondary)" }}>
            {subjects.length > 0
              ? `You're studying ${subjects.length} subject${subjects.length !== 1 ? "s" : ""}. Keep pushing!`
              : "Upload your first document to get started."}
          </p>
        </div>
        <button
          onClick={() => navigate("/auto-teach")}
          className="flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-semibold text-white transition-all"
          style={{ backgroundColor: "var(--accent)" }}
        >
          <Zap size={16} />
          Start Study Session
        </button>
      </div>

      {/* ── Stats row ──────────────────────────────────────────────── */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <StatCard
          icon={<Brain size={18} />}
          label="Avg. Mastery"
          value={`${overallMastery}%`}
          sub={masteryLabel(Number(overallMastery))}
          color="text-indigo-400"
        />
        <StatCard
          icon={<BookOpen size={18} />}
          label="Subjects"
          value={String(stats?.total_subjects ?? 0)}
          sub="active courses"
          color="text-blue-400"
        />
        <StatCard
          icon={<Clock size={18} />}
          label="Study Hours"
          value={`${Math.round((stats?.total_study_minutes ?? 0) / 60)}`}
          sub="total hours"
          color="text-emerald-400"
        />
        <StatCard
          icon={<Target size={18} />}
          label="Priority Tasks"
          value={String(priorityCount)}
          sub={`${priorityCount} high priority`}
          color="text-amber-400"
        />
      </div>

      {/* ── Main 2-column layout ───────────────────────────────────── */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[1fr_320px]">

        {/* Left — Today's Study Plan */}
        <div>
          <div className="flex items-center justify-between mb-3">
            <div>
              <h3 className="text-base font-semibold" style={{ color: "var(--text-primary)" }}>
                Today's Study Plan
              </h3>
              <p className="text-xs" style={{ color: "var(--text-muted)" }}>
                Prioritized topics based on your knowledge gaps
              </p>
            </div>
          </div>

          {weakTopics.length === 0 ? (
            <div
              className="rounded-xl p-8 text-center"
              style={{ backgroundColor: "var(--bg-card)", border: "1px solid var(--border)" }}
            >
              <Layers size={32} className="mx-auto mb-3" style={{ color: "var(--text-muted)" }} />
              <p style={{ color: "var(--text-secondary)" }}>No study data yet.</p>
              <p className="text-xs mt-1" style={{ color: "var(--text-muted)" }}>
                Upload documents and start a tutoring session to build your plan.
              </p>
            </div>
          ) : (
            <div className="space-y-2">
              {weakTopics.map((topic) => {
                const priority = priorityLevel(topic.mastery_score);
                return (
                  <div
                    key={topic.id}
                    className="rounded-xl p-4 transition-all"
                    style={{
                      backgroundColor: "var(--bg-card)",
                      border: "1px solid var(--border)",
                      boxShadow: "var(--shadow-card)",
                    }}
                  >
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          <span
                            className="text-[10px] font-bold uppercase tracking-wide px-2 py-0.5 rounded-full"
                            style={{
                              backgroundColor:
                                priority === "high"
                                  ? "rgba(239,68,68,0.15)"
                                  : priority === "medium"
                                  ? "rgba(245,158,11,0.15)"
                                  : "rgba(34,197,94,0.15)",
                              color:
                                priority === "high"
                                  ? "#f87171"
                                  : priority === "medium"
                                  ? "#fbbf24"
                                  : "#4ade80",
                            }}
                          >
                            {priority}
                          </span>
                          <span
                            className="text-[10px] px-2 py-0.5 rounded-full font-medium"
                            style={{
                              backgroundColor: "var(--accent-muted)",
                              color: "var(--accent-text)",
                            }}
                          >
                            {SUBJECT_LABELS[topic.subject] ?? topic.subject}
                          </span>
                        </div>
                        <p
                          className="font-semibold text-sm truncate"
                          style={{ color: "var(--text-primary)" }}
                        >
                          {topic.display_name}
                        </p>
                        <div className="flex items-center gap-3 mt-1 text-xs" style={{ color: "var(--text-muted)" }}>
                          <span className={masteryColor(topic.mastery_score)}>
                            Current: {topic.mastery_score.toFixed(0)}%
                          </span>
                          <span>·</span>
                          <span>{topic.exposure_count} sessions</span>
                        </div>
                      </div>
                      <button
                        onClick={() =>
                          navigate(
                            `/auto-teach?subject=${topic.subject}&topic=${topic.topic}`
                          )
                        }
                        className="shrink-0 px-3 py-1.5 text-xs font-semibold rounded-lg text-white transition-all"
                        style={{ backgroundColor: "var(--accent)" }}
                      >
                        Start
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Right column */}
        <div className="space-y-4">

          {/* Subject Overview */}
          <div
            className="rounded-xl p-4"
            style={{
              backgroundColor: "var(--bg-card)",
              border: "1px solid var(--border)",
              boxShadow: "var(--shadow-card)",
            }}
          >
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-semibold" style={{ color: "var(--text-primary)" }}>
                Subject Overview
              </h3>
              <button
                onClick={() => navigate("/subjects")}
                className="text-xs transition-colors"
                style={{ color: "var(--accent-text)" }}
              >
                View All
              </button>
            </div>
            <p className="text-xs mb-3" style={{ color: "var(--text-muted)" }}>
              Your progress across all subjects
            </p>
            {subjects.length === 0 ? (
              <p className="text-xs" style={{ color: "var(--text-muted)" }}>No subjects yet.</p>
            ) : (
              <div className="space-y-3">
                {subjects.slice(0, 5).map((s) => {
                  const masteredCount =
                    s.topics?.filter((t) => t.mastery_score >= 80).length ?? 0;
                  const totalTopics = s.topic_count ?? 0;
                  return (
                    <button
                      key={s.subject}
                      onClick={() => navigate(`/subjects/${s.subject}`)}
                      className="w-full text-left group"
                    >
                      <div className="flex items-center justify-between mb-1">
                        <span
                          className="text-xs font-medium group-hover:underline"
                          style={{ color: "var(--text-primary)" }}
                        >
                          {s.display_name}
                        </span>
                        <span className={`text-xs font-bold ${masteryColor(s.mastery_score)}`}>
                          {s.mastery_score.toFixed(0)}%
                        </span>
                      </div>
                      <div
                        className="h-1.5 rounded-full overflow-hidden mb-0.5"
                        style={{ backgroundColor: "var(--bg-muted)" }}
                      >
                        <div
                          className="h-full rounded-full transition-all"
                          style={{
                            width: `${s.mastery_score}%`,
                            backgroundColor:
                              s.mastery_score >= 80
                                ? "#22c55e"
                                : s.mastery_score >= 60
                                ? "#10b981"
                                : s.mastery_score >= 40
                                ? "#f59e0b"
                                : s.mastery_score >= 20
                                ? "#f97316"
                                : "#ef4444",
                          }}
                        />
                      </div>
                      <p className="text-[10px]" style={{ color: "var(--text-muted)" }}>
                        {masteredCount}/{totalTopics} topics mastered
                      </p>
                    </button>
                  );
                })}
              </div>
            )}
          </div>

          {/* Recent Sessions */}
          <div
            className="rounded-xl p-4"
            style={{
              backgroundColor: "var(--bg-card)",
              border: "1px solid var(--border)",
              boxShadow: "var(--shadow-card)",
            }}
          >
            <div className="flex items-center gap-2 mb-3">
              <Activity size={14} style={{ color: "var(--text-muted)" }} />
              <h3 className="text-sm font-semibold" style={{ color: "var(--text-primary)" }}>
                Recent Sessions
              </h3>
            </div>
            {recentSessions.length === 0 ? (
              <p className="text-xs" style={{ color: "var(--text-muted)" }}>
                No sessions yet.
              </p>
            ) : (
              <div className="space-y-2">
                {recentSessions.map((session) => (
                  <button
                    key={session.id}
                    onClick={() => navigate(`/tutor/${session.id}`)}
                    className="w-full flex items-center justify-between rounded-lg px-3 py-2 text-left transition-colors"
                    style={{ backgroundColor: "var(--bg-surface)" }}
                  >
                    <div>
                      <p className="text-xs font-medium" style={{ color: "var(--text-primary)" }}>
                        {MODE_LABELS[session.tutor_mode ?? ""] ?? "Study session"}{" "}
                        {session.subject ? `· ${SUBJECT_LABELS[session.subject] ?? session.subject}` : ""}
                      </p>
                      <p className="text-[10px]" style={{ color: "var(--text-muted)" }}>
                        {SUBJECT_LABELS[session.subject ?? ""] ?? (session.subject || "General")}
                      </p>
                    </div>
                    <span
                      className="text-[10px] font-semibold px-2 py-0.5 rounded-full"
                      style={{
                        backgroundColor: session.ended_at
                          ? "rgba(34,197,94,0.15)"
                          : "rgba(59,130,246,0.15)",
                        color: session.ended_at ? "#4ade80" : "#60a5fa",
                      }}
                    >
                      {session.ended_at ? "done" : "active"}
                    </span>
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Quick Actions */}
          <div
            className="rounded-xl p-4"
            style={{
              backgroundColor: "var(--bg-card)",
              border: "1px solid var(--border)",
              boxShadow: "var(--shadow-card)",
            }}
          >
            <h3 className="text-sm font-semibold mb-3" style={{ color: "var(--text-primary)" }}>
              Quick Actions
            </h3>
            <div className="space-y-1">
              {[
                { icon: GraduationCap, label: "AI Study Session", to: "/tutor" },
                { icon: Upload, label: "Upload Materials", to: "/documents" },
                { icon: CreditCard, label: "Review Flashcards", to: "/flashcards" },
              ].map(({ icon: Icon, label, to }) => (
                <button
                  key={to}
                  onClick={() => navigate(to)}
                  className="w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm text-left transition-colors"
                  style={{
                    backgroundColor: "var(--bg-surface)",
                    color: "var(--text-secondary)",
                  }}
                >
                  <Icon size={15} style={{ color: "var(--text-muted)" }} />
                  {label}
                  <ChevronRight size={14} className="ml-auto" style={{ color: "var(--text-muted)" }} />
                </button>
              ))}
            </div>
          </div>

        </div>
      </div>
    </div>
  );
}

function StatCard({
  icon,
  label,
  value,
  sub,
  color,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
  sub: string;
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
      <div className="flex items-center gap-2 mb-2">
        <span className={color}>{icon}</span>
        <span className="text-xs" style={{ color: "var(--text-muted)" }}>
          {label}
        </span>
      </div>
      <p className="text-2xl font-bold" style={{ color: "var(--text-primary)" }}>
        {value}
      </p>
      <p className="text-xs mt-0.5" style={{ color: "var(--text-secondary)" }}>
        {sub}
      </p>
    </div>
  );
}
