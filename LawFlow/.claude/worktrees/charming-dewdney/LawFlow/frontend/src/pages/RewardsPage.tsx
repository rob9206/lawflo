import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { getRewardsSummary, getAchievements } from "@/api/rewards";
import { formatDate } from "@/lib/utils";
import type { Achievement, AchievementRarity, RewardsSummary, RewardTransaction } from "@/types";
import Card from "@/components/ui/Card";
import StatCard from "@/components/ui/StatCard";
import PageHeader from "@/components/ui/PageHeader";
import MasteryBar from "@/components/ui/MasteryBar";
import EmptyState from "@/components/ui/EmptyState";
import {
  Trophy,
  Star,
  Flame,
  TrendingUp,
  Zap,
  Award,
} from "lucide-react";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

// ── Rarity config ──────────────────────────────────────────────

const RARITY_CONFIG: Record<AchievementRarity, {
  color: string;
  badgeClass: string;
  label: string;
}> = {
  common: {
    color: "var(--text-muted)",
    badgeClass: "duo-badge",
    label: "Common",
  },
  uncommon: {
    color: "var(--green)",
    badgeClass: "duo-badge duo-badge-green",
    label: "Uncommon",
  },
  rare: {
    color: "var(--blue)",
    badgeClass: "duo-badge duo-badge-blue",
    label: "Rare",
  },
  legendary: {
    color: "var(--gold)",
    badgeClass: "duo-badge duo-badge-gold",
    label: "Legendary",
  },
};

// ── Activity type labels ───────────────────────────────────────

const ACTIVITY_LABELS: Record<string, string> = {
  exam_complete: "Exam",
  tutor_session: "Tutor",
  flashcard_session: "Flashcards",
  past_test_upload: "Upload",
  streak_bonus: "Streak",
  random_bonus: "Bonus",
  achievement_unlock: "Achievement",
};

// ── Chart tooltip style ────────────────────────────────────────

const chartTooltipStyle: React.CSSProperties = {
  backgroundColor: "var(--card-bg)",
  border: "2px solid var(--border)",
  borderBottom: "4px solid var(--border-dark)",
  borderRadius: "var(--radius-lg)",
  color: "var(--text-primary)",
  fontSize: "13px",
  fontWeight: 700,
  fontFamily: "'Nunito', sans-serif",
};

// ── Main page ──────────────────────────────────────────────────

export default function RewardsPage() {
  const [filter, setFilter] = useState<"all" | "unlocked" | "locked">("all");

  const { data: summary, isLoading: summaryLoading } = useQuery({
    queryKey: ["rewards-summary"],
    queryFn: getRewardsSummary,
    staleTime: 60_000,
  });

  const { data: achievements = [], isLoading: achievementsLoading } = useQuery({
    queryKey: ["achievements"],
    queryFn: getAchievements,
  });

  const isLoading = summaryLoading || achievementsLoading;

  if (isLoading) {
    return (
      <div className="space-y-4 animate-pulse">
        <div className="h-8 rounded-lg w-48" style={{ backgroundColor: "var(--surface-bg)" }} />
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="h-24 duo-card" />
          ))}
        </div>
        <div className="h-48 duo-card" />
      </div>
    );
  }

  if (!summary) {
    return (
      <EmptyState
        icon={<Trophy size={32} />}
        message="No rewards data yet."
        sub="Complete study sessions to start earning XP."
      />
    );
  }

  const filteredAchievements = achievements.filter((a) => {
    if (filter === "unlocked") return a.unlocked;
    if (filter === "locked") return !a.unlocked;
    return true;
  });

  const unlockedCount = achievements.filter((a) => a.unlocked).length;
  const levelPct = Math.round(summary.level_progress * 100);

  return (
    <div className="space-y-6">
      <PageHeader
        icon={<Trophy size={20} />}
        title="Rewards"
        subtitle="Track your XP, achievements, and study streaks"
      />

      {/* ── Stats row ──────────────────────────────────── */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <StatCard
          icon={<Zap size={18} />}
          label="Total XP"
          value={summary.balance.toLocaleString()}
          sub="lifetime earned"
          color="var(--purple)"
        />
        <StatCard
          icon={<Star size={18} />}
          label="Level"
          value={String(summary.level)}
          sub={summary.active_title}
          color="var(--gold)"
          bar
          barValue={levelPct}
        />
        <StatCard
          icon={<Flame size={18} />}
          label="Streak"
          value={`${summary.current_streak}d`}
          sub={`Best: ${summary.longest_streak}d`}
          color="var(--orange)"
        />
        <StatCard
          icon={<Award size={18} />}
          label="Achievements"
          value={`${unlockedCount}/${achievements.length}`}
          sub="unlocked"
          color="var(--green)"
        />
      </div>

      {/* ── Level progress card ────────────────────────── */}
      <LevelProgressCard summary={summary} />

      {/* ── Main 2-column layout ───────────────────────── */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[1fr_320px]">

        {/* Left — Achievement grid */}
        <div>
          <div className="flex items-center justify-between mb-3">
            <h3 style={{ fontSize: "20px", fontWeight: 800, color: "var(--text-primary)" }}>
              Achievements
            </h3>
            <div className="flex gap-1">
              {(["all", "unlocked", "locked"] as const).map((tab) => (
                <button
                  key={tab}
                  onClick={() => setFilter(tab)}
                  className={filter === tab ? "duo-btn duo-btn-blue" : "duo-btn duo-btn-ghost"}
                  style={{ padding: "4px 12px", fontSize: "13px" }}
                >
                  {tab.charAt(0).toUpperCase() + tab.slice(1)}
                </button>
              ))}
            </div>
          </div>

          {filteredAchievements.length === 0 ? (
            <EmptyState
              icon={<Award size={32} />}
              message={filter === "unlocked" ? "No achievements unlocked yet." : "No locked achievements."}
              sub="Keep studying to unlock badges!"
            />
          ) : (
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
              {filteredAchievements.map((ach) => (
                <AchievementCard key={ach.achievement_key} achievement={ach} />
              ))}
            </div>
          )}
        </div>

        {/* Right — Sidebar */}
        <div className="space-y-4">
          <XpHistoryChart transactions={summary.recent_transactions} />
          <RecentTransactionsCard transactions={summary.recent_transactions} />
        </div>
      </div>
    </div>
  );
}

// ── Sub-components ─────────────────────────────────────────────

function LevelProgressCard({ summary }: { summary: RewardsSummary }) {
  const pct = Math.round(summary.level_progress * 100);
  return (
    <Card>
      <div className="flex items-center justify-between mb-2">
        <div>
          <p style={{ fontSize: "12px", fontWeight: 600, color: "var(--text-muted)" }}>
            Level {summary.level}
          </p>
          <p style={{ fontSize: "15px", fontWeight: 800, color: "var(--text-primary)" }}>
            {summary.active_title}
          </p>
        </div>
        <span style={{ fontSize: "13px", fontWeight: 800, textTransform: "uppercase", letterSpacing: "0.06em", color: "var(--blue)" }}>
          {summary.total_earned.toLocaleString()} XP
        </span>
      </div>
      <MasteryBar score={pct} />
      {summary.next_level_at && (
        <p style={{ fontSize: "11px", fontWeight: 600, marginTop: "6px", color: "var(--text-muted)" }}>
          {summary.total_earned.toLocaleString()} / {summary.next_level_at.toLocaleString()} XP to Level {summary.level + 1}
        </p>
      )}
    </Card>
  );
}

function AchievementCard({ achievement }: { achievement: Achievement }) {
  const rarity = RARITY_CONFIG[achievement.rarity];
  const pct = Math.round(achievement.progress * 100);

  return (
    <div
      className="duo-card p-4 flex flex-col gap-2 relative overflow-hidden transition-all"
      style={{
        borderTopColor: rarity.color,
        opacity: achievement.unlocked ? 1 : 0.6,
      }}
    >
      <div
        className="absolute top-0 left-0 right-0"
        style={{ height: "3px", backgroundColor: rarity.color }}
      />

      <div className="flex items-start justify-between">
        <span style={{ fontSize: "24px" }}>
          {achievement.unlocked ? "\u2728" : "\u{1F512}"}
        </span>
        <span className={rarity.badgeClass}>
          {rarity.label}
        </span>
      </div>

      <div>
        <p style={{ fontSize: "15px", fontWeight: 800, color: "var(--text-primary)" }}>
          {achievement.title}
        </p>
        <p style={{ fontSize: "13px", fontWeight: 500, marginTop: "2px", color: "var(--text-muted)" }}>
          {achievement.description}
        </p>
      </div>

      {achievement.unlocked ? (
        <p style={{ fontSize: "11px", fontWeight: 600, color: "var(--text-muted)", marginTop: "auto" }}>
          Unlocked {formatDate(achievement.unlocked_at)}
        </p>
      ) : (
        <div style={{ marginTop: "auto" }}>
          <div className="flex justify-between" style={{ fontSize: "11px", fontWeight: 600, color: "var(--text-muted)", marginBottom: "4px" }}>
            <span>{achievement.current_value} / {achievement.target_value}</span>
            <span>{pct}%</span>
          </div>
          <MasteryBar score={pct} size="sm" />
        </div>
      )}
    </div>
  );
}

function XpHistoryChart({ transactions }: { transactions: RewardTransaction[] }) {
  if (transactions.length === 0) return null;

  const chartData = [...transactions].reverse().map((t) => ({
    label: new Date(t.created_at).toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
    }),
    xp: t.amount,
  }));

  return (
    <Card>
      <div className="flex items-center gap-2 mb-4">
        <TrendingUp size={14} style={{ color: "var(--text-muted)" }} />
        <h3 style={{ fontSize: "17px", fontWeight: 800, color: "var(--text-primary)" }}>
          Recent XP
        </h3>
      </div>
      <ResponsiveContainer width="100%" height={160}>
        <AreaChart data={chartData} margin={{ top: 4, right: 4, left: -28, bottom: 0 }}>
          <defs>
            <linearGradient id="xpGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="var(--green)" stopOpacity={0.3} />
              <stop offset="95%" stopColor="var(--green)" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
          <XAxis
            dataKey="label"
            tick={{ fill: "var(--text-muted)", fontSize: 9 }}
            axisLine={false}
            tickLine={false}
          />
          <YAxis
            tick={{ fill: "var(--text-muted)", fontSize: 9 }}
            axisLine={false}
            tickLine={false}
          />
          <Tooltip
            contentStyle={chartTooltipStyle}
            formatter={(v: number) => [v, "XP"]}
          />
          <Area
            type="monotone"
            dataKey="xp"
            stroke="var(--green)"
            strokeWidth={2}
            fill="url(#xpGradient)"
          />
        </AreaChart>
      </ResponsiveContainer>
    </Card>
  );
}

function RecentTransactionsCard({ transactions }: { transactions: RewardTransaction[] }) {
  if (transactions.length === 0) return null;

  return (
    <Card>
      <h3 style={{ fontSize: "17px", fontWeight: 800, color: "var(--text-primary)", marginBottom: "12px" }}>
        Recent Activity
      </h3>
      <div className="space-y-2">
        {transactions.map((t) => (
          <div
            key={t.id}
            className="flex items-center justify-between"
            style={{
              borderRadius: "var(--radius-sm)",
              padding: "8px 12px",
              backgroundColor: "var(--surface-bg)",
            }}
          >
            <div>
              <p style={{ fontSize: "13px", fontWeight: 700, color: "var(--text-primary)" }}>
                {t.description}
              </p>
              <p style={{ fontSize: "11px", fontWeight: 600, color: "var(--text-muted)" }}>
                {ACTIVITY_LABELS[t.activity_type] ?? t.activity_type}
              </p>
            </div>
            <span style={{ fontSize: "13px", fontWeight: 800, color: "var(--green)" }}>
              +{t.amount}
            </span>
          </div>
        ))}
      </div>
    </Card>
  );
}
