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
  rarityClass: string;
  badgeClass: string;
  label: string;
}> = {
  common: {
    rarityClass: "rarity-common",
    badgeClass: "badge badge-muted",
    label: "Common",
  },
  uncommon: {
    rarityClass: "rarity-uncommon",
    badgeClass: "badge badge-success",
    label: "Uncommon",
  },
  rare: {
    rarityClass: "rarity-rare",
    badgeClass: "badge badge-info",
    label: "Rare",
  },
  legendary: {
    rarityClass: "rarity-legendary",
    badgeClass: "badge badge-warning",
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

const chartTooltipStyle = {
  backgroundColor: "var(--bg-card)",
  border: "1px solid var(--border)",
  borderRadius: "8px",
  color: "var(--text-primary)",
  fontSize: "12px",
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
        <div className="h-8 rounded-lg w-48 bg-muted-ui" />
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="h-24 rounded-xl card" />
          ))}
        </div>
        <div className="h-48 rounded-xl card" />
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
          color="text-indigo-400"
        />
        <StatCard
          icon={<Star size={18} />}
          label="Level"
          value={String(summary.level)}
          sub={summary.active_title}
          color="text-amber-400"
          bar
          barValue={levelPct}
        />
        <StatCard
          icon={<Flame size={18} />}
          label="Streak"
          value={`${summary.current_streak}d`}
          sub={`Best: ${summary.longest_streak}d`}
          color="text-orange-400"
        />
        <StatCard
          icon={<Award size={18} />}
          label="Achievements"
          value={`${unlockedCount}/${achievements.length}`}
          sub="unlocked"
          color="text-emerald-400"
        />
      </div>

      {/* ── Level progress card ────────────────────────── */}
      <LevelProgressCard summary={summary} />

      {/* ── Main 2-column layout ───────────────────────── */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[1fr_320px]">

        {/* Left — Achievement grid */}
        <div>
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-base font-semibold text-ui-primary">
              Achievements
            </h3>
            <div className="flex gap-1">
              {(["all", "unlocked", "locked"] as const).map((tab) => (
                <button
                  key={tab}
                  onClick={() => setFilter(tab)}
                  className={`px-3 py-1 rounded-lg text-xs font-medium transition-colors ${
                    filter === tab
                      ? "bg-accent-muted text-accent-label"
                      : "text-ui-muted hover:text-ui-secondary"
                  }`}
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
          <p className="text-xs text-ui-muted">Level {summary.level}</p>
          <p className="text-sm font-semibold text-ui-primary">
            {summary.active_title}
          </p>
        </div>
        <span className="text-xs font-semibold text-accent-label">
          {summary.total_earned.toLocaleString()} XP
        </span>
      </div>
      <MasteryBar score={pct} />
      {summary.next_level_at && (
        <p className="text-[10px] mt-1.5 text-ui-muted">
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
      className={`card p-4 flex flex-col gap-2 relative overflow-hidden transition-all ${rarity.rarityClass} ${
        achievement.unlocked ? "" : "opacity-60"
      }`}
    >
      {/* Rarity accent line — inherits --rarity-color from the parent .rarity-* class */}
      <div className="absolute top-0 left-0 right-0 h-[2px] rarity-accent" />

      <div className="flex items-start justify-between">
        <span className="text-2xl">
          {achievement.unlocked ? "\u2728" : "\u{1F512}"}
        </span>
        <span className={rarity.badgeClass}>
          {rarity.label}
        </span>
      </div>

      <div>
        <p className="text-sm font-semibold text-ui-primary">{achievement.title}</p>
        <p className="text-xs text-ui-muted mt-0.5">{achievement.description}</p>
      </div>

      {achievement.unlocked ? (
        <p className="text-[10px] text-ui-muted mt-auto">
          Unlocked {formatDate(achievement.unlocked_at)}
        </p>
      ) : (
        <div className="mt-auto">
          <div className="flex justify-between text-[10px] text-ui-muted mb-1">
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

  // Plot each transaction individually (not cumulative) since we only
  // have a partial slice of the full ledger — cumulative from zero
  // would misrepresent the user's actual XP growth.
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
        <TrendingUp size={14} className="text-ui-muted" />
        <h3 className="text-sm font-semibold text-ui-primary">Recent XP</h3>
      </div>
      <ResponsiveContainer width="100%" height={160}>
        <AreaChart data={chartData} margin={{ top: 4, right: 4, left: -28, bottom: 0 }}>
          <defs>
            <linearGradient id="xpGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="var(--accent)" stopOpacity={0.3} />
              <stop offset="95%" stopColor="var(--accent)" stopOpacity={0} />
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
            stroke="var(--accent)"
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
      <h3 className="text-sm font-semibold mb-3 text-ui-primary">
        Recent Activity
      </h3>
      <div className="space-y-2">
        {transactions.map((t) => (
          <div
            key={t.id}
            className="flex items-center justify-between rounded-lg px-3 py-2 bg-surface"
          >
            <div>
              <p className="text-xs font-medium text-ui-primary">
                {t.description}
              </p>
              <p className="text-[10px] text-ui-muted">
                {ACTIVITY_LABELS[t.activity_type] ?? t.activity_type}
              </p>
            </div>
            <span className="text-xs font-bold text-emerald-400">
              +{t.amount}
            </span>
          </div>
        ))}
      </div>
    </Card>
  );
}
