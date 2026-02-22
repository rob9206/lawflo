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
  high: "danger",
  medium: "warning",
  low: "success",
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
        <div className="h-8 rounded-lg w-64 bg-muted-ui" />
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="h-24 rounded-xl card" />
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
            className="btn-primary flex items-center gap-2"
          >
            <Zap size={16} />
            Start Study Session
          </button>
        }
      />

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
              <h3 className="text-base font-semibold text-ui-primary">
                Today's Study Plan
              </h3>
              <p className="text-xs text-ui-muted">
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
                          <Badge variant="accent">
                            {SUBJECT_LABELS[topic.subject] ?? topic.subject}
                          </Badge>
                        </div>
                        <p className="font-semibold text-sm truncate text-ui-primary">
                          {topic.display_name}
                        </p>
                        <div className="flex items-center gap-3 mt-1 text-xs text-ui-muted">
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
                        className="btn-primary shrink-0 text-xs"
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
                  <Trophy size={16} className="text-amber-400" />
                  <h3 className="text-sm font-semibold text-ui-primary">
                    Lv.{rewardsSummary.level}{" "}
                    <span className="font-normal text-accent-label">
                      {rewardsSummary.active_title}
                    </span>
                  </h3>
                </div>
                <ChevronRight size={14} className="text-ui-muted" />
              </div>
              <MasteryBar
                score={Math.round(rewardsSummary.level_progress * 100)}
                size="sm"
              />
              <div className="flex items-center gap-4 mt-2 text-xs text-ui-muted">
                <span className="flex items-center gap-1">
                  <Star size={12} className="text-indigo-400" />
                  {rewardsSummary.balance.toLocaleString()} XP
                </span>
                <span className="flex items-center gap-1">
                  <Flame size={12} className="text-orange-400" />
                  {rewardsSummary.current_streak}d streak
                </span>
              </div>
            </Card>
          )}

          {/* Subject Overview */}
          <Card>
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-semibold text-ui-primary">
                Subject Overview
              </h3>
              <button
                onClick={() => navigate("/subjects")}
                className="text-xs text-accent-label transition-colors"
              >
                View All
              </button>
            </div>
            <p className="text-xs mb-3 text-ui-muted">
              Your progress across all subjects
            </p>
            {subjects.length === 0 ? (
              <p className="text-xs text-ui-muted">No subjects yet.</p>
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
                        <span className="text-xs font-medium text-ui-primary group-hover:underline">
                          {s.display_name}
                        </span>
                        <span className={`text-xs font-bold ${masteryColor(s.mastery_score)}`}>
                          {s.mastery_score.toFixed(0)}%
                        </span>
                      </div>
                      <MasteryBar score={s.mastery_score} size="sm" />
                      <p className="text-[10px] mt-0.5 text-ui-muted">
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
              <Activity size={14} className="text-ui-muted" />
              <h3 className="text-sm font-semibold text-ui-primary">
                Recent Sessions
              </h3>
            </div>
            {recentSessions.length === 0 ? (
              <p className="text-xs text-ui-muted">
                No sessions yet.
              </p>
            ) : (
              <div className="space-y-2">
                {recentSessions.map((session) => (
                  <button
                    key={session.id}
                    onClick={() => navigate(`/tutor/${session.id}`)}
                    className="w-full flex items-center justify-between rounded-lg px-3 py-2 text-left transition-colors bg-surface"
                  >
                    <div>
                      <p className="text-xs font-medium text-ui-primary">
                        {MODE_LABELS[session.tutor_mode ?? ""] ?? "Study session"}{" "}
                        {session.subject ? `· ${SUBJECT_LABELS[session.subject] ?? session.subject}` : ""}
                      </p>
                      <p className="text-[10px] text-ui-muted">
                        {SUBJECT_LABELS[session.subject ?? ""] ?? (session.subject || "General")}
                      </p>
                    </div>
                    <Badge variant={session.ended_at ? "success" : "accent"}>
                      {session.ended_at ? "done" : "active"}
                    </Badge>
                  </button>
                ))}
              </div>
            )}
          </Card>

          {/* Quick Actions */}
          <Card>
            <h3 className="text-sm font-semibold mb-3 text-ui-primary">
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
                  className="w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm text-left text-ui-secondary transition-colors bg-surface"
                >
                  <Icon size={15} className="text-ui-muted" />
                  {label}
                  <ChevronRight size={14} className="ml-auto text-ui-muted" />
                </button>
              ))}
            </div>
          </Card>

        </div>
      </div>
    </div>
  );
}
