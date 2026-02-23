import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { getDashboard, getWeaknesses } from "@/api/progress";
import { getRecentSessions } from "@/api/tutor";
import { getRewardsSummary } from "@/api/rewards";
import { masteryColor, masteryLabel, priorityLevel } from "@/lib/utils";
import { SUBJECT_LABELS, MODE_LABELS } from "@/lib/constants";
import Card from "@/components/ui/Card";
import StatCard from "@/components/ui/StatCard";
import PageHeader from "@/components/ui/PageHeader";
import Badge from "@/components/ui/Badge";
import EmptyState from "@/components/ui/EmptyState";
import MasteryBar from "@/components/ui/MasteryBar";
import {
  Brain,
  Clock,
  Layers,
  BookOpen,
  Zap,
  GraduationCap,
  Upload,
  CreditCard,
  ChevronRight,
  Target,
  Activity,
  Trophy,
  Flame,
  Star,
} from "lucide-react";

const PRIORITY_BADGE = {
  high: "red",
  medium: "orange",
  low: "green",
} as const;

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

  const { data: rewardsSummary } = useQuery({
    queryKey: ["rewards-summary"],
    queryFn: getRewardsSummary,
    staleTime: 60_000,
  });

  if (isLoading) {
    return (
      <div className="space-y-4 animate-pulse">
        <div
          className="rounded-lg"
          style={{ height: "32px", width: "256px", background: "var(--surface-bg)" }}
        />
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          {[...Array(4)].map((_, i) => (
            <div
              key={i}
              className="duo-card"
              style={{ height: "96px", borderRadius: "var(--radius-lg)" }}
            />
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
      <PageHeader
        title="Welcome back, Law Student"
        subtitle={
          subjects.length > 0
            ? `You're studying ${subjects.length} subject${subjects.length !== 1 ? "s" : ""}. Keep pushing!`
            : "Upload your first document to get started."
        }
        action={
          <button
            onClick={() => navigate("/auto-teach")}
            className="duo-btn duo-btn-green flex items-center gap-2"
          >
            <Zap size={16} />
            Start Study Session
          </button>
        }
      />

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <StatCard
          icon={<Brain size={18} />}
          label="Avg. Mastery"
          value={`${overallMastery}%`}
          sub={masteryLabel(Number(overallMastery))}
          color="var(--purple)"
        />
        <StatCard
          icon={<BookOpen size={18} />}
          label="Subjects"
          value={String(stats?.total_subjects ?? 0)}
          sub="active courses"
          color="var(--blue)"
        />
        <StatCard
          icon={<Clock size={18} />}
          label="Study Hours"
          value={`${Math.round((stats?.total_study_minutes ?? 0) / 60)}`}
          sub="total hours"
          color="var(--green)"
        />
        <StatCard
          icon={<Target size={18} />}
          label="Priority Tasks"
          value={String(priorityCount)}
          sub={`${priorityCount} high priority`}
          color="var(--orange)"
        />
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[1fr_320px]">

        {/* Left — Today's Study Plan */}
        <div>
          <div className="flex items-center justify-between mb-3">
            <div>
              <h3 style={{ fontSize: "20px", fontWeight: 800, color: "var(--text-primary)" }}>
                Today's Study Plan
              </h3>
              <p style={{ fontSize: "13px", fontWeight: 500, color: "var(--text-muted)" }}>
                Prioritized topics based on your knowledge gaps
              </p>
            </div>
          </div>

          {weakTopics.length === 0 ? (
            <EmptyState
              icon={<Layers size={32} />}
              message="No study data yet."
              sub="Upload documents and start a tutoring session to build your plan."
            />
          ) : (
            <div className="space-y-2">
              {weakTopics.map((topic) => {
                const priority = priorityLevel(topic.mastery_score);
                return (
                  <Card key={topic.id} hover>
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          <Badge variant={PRIORITY_BADGE[priority]}>
                            {priority}
                          </Badge>
                          <Badge variant="blue">
                            {SUBJECT_LABELS[topic.subject] ?? topic.subject}
                          </Badge>
                        </div>
                        <p style={{ fontSize: "15px", fontWeight: 700, color: "var(--text-primary)" }} className="truncate">
                          {topic.display_name}
                        </p>
                        <div className="flex items-center gap-3 mt-1" style={{ fontSize: "13px", color: "var(--text-muted)" }}>
                          <span style={{ color: masteryColor(topic.mastery_score) }}>
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
                        className="duo-btn duo-btn-green shrink-0"
                        style={{ padding: "8px 16px", fontSize: "13px" }}
                      >
                        Start
                      </button>
                    </div>
                  </Card>
                );
              })}
            </div>
          )}
        </div>

        {/* Right column */}
        <div className="space-y-4">

          {/* Rewards widget */}
          {rewardsSummary && (
            <Card
              hover
              className="cursor-pointer"
              onClick={() => navigate("/rewards")}
            >
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <Trophy size={16} style={{ color: "var(--gold)" }} />
                  <h3 style={{ fontSize: "15px", fontWeight: 800, color: "var(--text-primary)" }}>
                    Lv.{rewardsSummary.level}{" "}
                    <span style={{ fontWeight: 600, color: "var(--text-secondary)" }}>
                      {rewardsSummary.active_title}
                    </span>
                  </h3>
                </div>
                <ChevronRight size={14} style={{ color: "var(--text-muted)" }} />
              </div>
              <MasteryBar
                score={Math.round(rewardsSummary.level_progress * 100)}
                size="sm"
              />
              <div className="flex items-center gap-4 mt-2" style={{ fontSize: "13px", color: "var(--text-muted)" }}>
                <span className="flex items-center gap-1">
                  <Star size={12} style={{ color: "var(--purple)" }} />
                  {rewardsSummary.balance.toLocaleString()} XP
                </span>
                <span className="flex items-center gap-1">
                  <Flame size={12} style={{ color: "var(--orange)" }} />
                  {rewardsSummary.current_streak}d streak
                </span>
              </div>
            </Card>
          )}

          {/* Subject Overview */}
          <Card>
            <div className="flex items-center justify-between mb-3">
              <h3 style={{ fontSize: "15px", fontWeight: 800, color: "var(--text-primary)" }}>
                Subject Overview
              </h3>
              <button
                onClick={() => navigate("/subjects")}
                style={{ fontSize: "13px", fontWeight: 800, color: "var(--blue-dark)" }}
                className="transition-colors"
              >
                View All
              </button>
            </div>
            <p style={{ fontSize: "13px", fontWeight: 500, color: "var(--text-muted)", marginBottom: "12px" }}>
              Your progress across all subjects
            </p>
            {subjects.length === 0 ? (
              <p style={{ fontSize: "13px", color: "var(--text-muted)" }}>No subjects yet.</p>
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
                        <span style={{ fontSize: "13px", fontWeight: 700, color: "var(--text-primary)" }} className="group-hover:underline">
                          {s.display_name}
                        </span>
                        <span style={{ fontSize: "13px", fontWeight: 800, color: masteryColor(s.mastery_score) }}>
                          {s.mastery_score.toFixed(0)}%
                        </span>
                      </div>
                      <MasteryBar score={s.mastery_score} size="sm" />
                      <p style={{ fontSize: "11px", fontWeight: 500, marginTop: "2px", color: "var(--text-muted)" }}>
                        {masteredCount}/{totalTopics} topics mastered
                      </p>
                    </button>
                  );
                })}
              </div>
            )}
          </Card>

          {/* Recent Sessions */}
          <Card>
            <div className="flex items-center gap-2 mb-3">
              <Activity size={14} style={{ color: "var(--text-muted)" }} />
              <h3 style={{ fontSize: "15px", fontWeight: 800, color: "var(--text-primary)" }}>
                Recent Sessions
              </h3>
            </div>
            {recentSessions.length === 0 ? (
              <p style={{ fontSize: "13px", color: "var(--text-muted)" }}>
                No sessions yet.
              </p>
            ) : (
              <div className="space-y-2">
                {recentSessions.map((session) => (
                  <button
                    key={session.id}
                    onClick={() => navigate(`/tutor/${session.id}`)}
                    className="w-full flex items-center justify-between text-left transition-colors"
                    style={{
                      padding: "8px 12px",
                      borderRadius: "var(--radius-md)",
                      background: "var(--surface-bg)",
                    }}
                  >
                    <div>
                      <p style={{ fontSize: "13px", fontWeight: 700, color: "var(--text-primary)" }}>
                        {MODE_LABELS[session.tutor_mode ?? ""] ?? "Study session"}{" "}
                        {session.subject ? `· ${SUBJECT_LABELS[session.subject] ?? session.subject}` : ""}
                      </p>
                      <p style={{ fontSize: "11px", color: "var(--text-muted)" }}>
                        {SUBJECT_LABELS[session.subject ?? ""] ?? (session.subject || "General")}
                      </p>
                    </div>
                    <Badge variant={session.ended_at ? "green" : "blue"}>
                      {session.ended_at ? "done" : "active"}
                    </Badge>
                  </button>
                ))}
              </div>
            )}
          </Card>

          {/* Quick Actions */}
          <Card>
            <h3 style={{ fontSize: "15px", fontWeight: 800, color: "var(--text-primary)", marginBottom: "12px" }}>
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
                  className="w-full flex items-center gap-3 text-left transition-colors"
                  style={{
                    padding: "8px 12px",
                    borderRadius: "var(--radius-md)",
                    fontSize: "15px",
                    fontWeight: 600,
                    color: "var(--text-secondary)",
                    background: "var(--surface-bg)",
                  }}
                >
                  <Icon size={15} style={{ color: "var(--text-muted)" }} />
                  {label}
                  <ChevronRight size={14} className="ml-auto" style={{ color: "var(--text-muted)" }} />
                </button>
              ))}
            </div>
          </Card>

        </div>
      </div>
    </div>
  );
}
