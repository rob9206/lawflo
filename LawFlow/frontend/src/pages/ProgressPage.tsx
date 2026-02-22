import { useQuery } from "@tanstack/react-query";
import {
  BarChart,
  Bar,
  Cell,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
  AreaChart,
  Area,
} from "recharts";
import { getDashboard, getStudyHistory, getStreaks } from "@/api/progress";
import { masteryColor, masteryBarColor } from "@/lib/utils";
import { Flame, Calendar, Clock, TrendingUp, BarChart2, BookOpen } from "lucide-react";
import Card from "@/components/ui/Card";
import StatCard from "@/components/ui/StatCard";
import PageHeader from "@/components/ui/PageHeader";
import MasteryBar from "@/components/ui/MasteryBar";

const chartTooltipStyle = {
  backgroundColor: "var(--bg-card)",
  border: "1px solid var(--border)",
  borderRadius: "8px",
  color: "var(--text-primary)",
  fontSize: "12px",
};

export default function ProgressPage() {
  const { data: dashboard } = useQuery({
    queryKey: ["dashboard"],
    queryFn: getDashboard,
  });

  const { data: history = [] } = useQuery({
    queryKey: ["study-history"],
    queryFn: () => getStudyHistory(30),
  });

  const { data: streaks } = useQuery({
    queryKey: ["streaks"],
    queryFn: getStreaks,
  });

  const subjects = dashboard?.subjects ?? [];
  const allTopics = subjects.flatMap((s) => s.topics ?? []);

  // Mastery distribution buckets
  const distribution = [
    { label: "Mastered", count: allTopics.filter((t) => t.mastery_score >= 80).length, color: "#22c55e" },
    { label: "Advanced", count: allTopics.filter((t) => t.mastery_score >= 60 && t.mastery_score < 80).length, color: "#10b981" },
    { label: "Proficient", count: allTopics.filter((t) => t.mastery_score >= 40 && t.mastery_score < 60).length, color: "#f59e0b" },
    { label: "Developing", count: allTopics.filter((t) => t.mastery_score >= 20 && t.mastery_score < 40).length, color: "#f97316" },
    { label: "Beginning", count: allTopics.filter((t) => t.mastery_score < 20).length, color: "#ef4444" },
  ];

  const recentHistory = history.slice(-14).map((d) => ({
    ...d,
    label: d.date.slice(5),
  }));

  const subjectChartData = subjects.map((s) => ({
    name: s.display_name.split(" ")[0],
    mastery: Math.round(s.mastery_score),
    fill: masteryBarColor(s.mastery_score),
  }));

  return (
    <div className="space-y-6">
      <PageHeader
        title="Progress"
        subtitle="Your learning analytics over the past 30 days"
      />

      {/* Streak stats */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <StatCard
          icon={<Flame size={20} />}
          color="text-orange-400"
          label="Current Streak"
          value={`${streaks?.current_streak ?? 0}`}
          sub="days in a row"
        />
        <StatCard
          icon={<TrendingUp size={20} />}
          color="text-emerald-400"
          label="Longest Streak"
          value={`${streaks?.longest_streak ?? 0}`}
          sub="days record"
        />
        <StatCard
          icon={<Calendar size={20} />}
          color="text-blue-400"
          label="Total Study Days"
          value={`${streaks?.total_days ?? 0}`}
          sub="since joining"
        />
        <StatCard
          icon={<Clock size={20} />}
          color="text-indigo-400"
          label="Total Hours"
          value={`${Math.round((dashboard?.stats.total_study_minutes ?? 0) / 60)}`}
          sub="hours studied"
        />
      </div>

      {/* Charts row */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Study time bar chart */}
        <Card padding="lg">
          <div className="flex items-center gap-2 mb-4">
            <BarChart2 size={16} className="text-ui-muted" />
            <h3 className="text-sm font-semibold text-ui-primary">
              Daily Study Time (last 14 days)
            </h3>
          </div>
          {history.length === 0 ? (
            <EmptyChart />
          ) : (
            <ResponsiveContainer width="100%" height={180}>
              <BarChart data={recentHistory} margin={{ top: 4, right: 4, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
                <XAxis
                  dataKey="label"
                  tick={{ fill: "var(--text-muted)", fontSize: 10 }}
                  axisLine={false}
                  tickLine={false}
                />
                <YAxis
                  tick={{ fill: "var(--text-muted)", fontSize: 10 }}
                  axisLine={false}
                  tickLine={false}
                />
                <Tooltip
                  contentStyle={chartTooltipStyle}
                  formatter={(value: number) => [`${Math.round(value)}m`, "Study time"]}
                  labelStyle={{ color: "var(--text-muted)" }}
                />
                <Bar dataKey="minutes" fill="var(--accent)" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </Card>

        {/* Sessions area chart */}
        <Card padding="lg">
          <div className="flex items-center gap-2 mb-4">
            <TrendingUp size={16} className="text-ui-muted" />
            <h3 className="text-sm font-semibold text-ui-primary">
              Study Sessions (last 14 days)
            </h3>
          </div>
          {history.length === 0 ? (
            <EmptyChart />
          ) : (
            <ResponsiveContainer width="100%" height={180}>
              <AreaChart data={recentHistory} margin={{ top: 4, right: 4, left: -20, bottom: 0 }}>
                <defs>
                  <linearGradient id="sessionGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="var(--accent)" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="var(--accent)" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
                <XAxis
                  dataKey="label"
                  tick={{ fill: "var(--text-muted)", fontSize: 10 }}
                  axisLine={false}
                  tickLine={false}
                />
                <YAxis
                  allowDecimals={false}
                  tick={{ fill: "var(--text-muted)", fontSize: 10 }}
                  axisLine={false}
                  tickLine={false}
                />
                <Tooltip
                  contentStyle={chartTooltipStyle}
                  formatter={(value: number) => [value, "Sessions"]}
                  labelStyle={{ color: "var(--text-muted)" }}
                />
                <Area
                  type="monotone"
                  dataKey="sessions"
                  stroke="var(--accent)"
                  strokeWidth={2}
                  fill="url(#sessionGradient)"
                />
              </AreaChart>
            </ResponsiveContainer>
          )}
        </Card>
      </div>

      {/* Subject comparison */}
      {subjectChartData.length > 0 && (
        <Card padding="lg">
          <div className="flex items-center gap-2 mb-4">
            <BookOpen size={16} className="text-ui-muted" />
            <h3 className="text-sm font-semibold text-ui-primary">
              Subject Mastery Comparison
            </h3>
          </div>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart
              data={subjectChartData}
              layout="vertical"
              margin={{ top: 4, right: 40, left: 40, bottom: 0 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" horizontal={false} />
              <XAxis
                type="number"
                domain={[0, 100]}
                tick={{ fill: "var(--text-muted)", fontSize: 10 }}
                axisLine={false}
                tickLine={false}
                tickFormatter={(v) => `${v}%`}
              />
              <YAxis
                type="category"
                dataKey="name"
                tick={{ fill: "var(--text-secondary)", fontSize: 11 }}
                axisLine={false}
                tickLine={false}
                width={72}
              />
              <Tooltip
                contentStyle={chartTooltipStyle}
                formatter={(value: number) => [`${value}%`, "Mastery"]}
                labelStyle={{ color: "var(--text-muted)" }}
              />
              <Bar dataKey="mastery" radius={[0, 4, 4, 0]}>
                {subjectChartData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.fill} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </Card>
      )}

      {/* Mastery distribution + Topic heatmap */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[280px_1fr]">
        {/* Distribution */}
        <Card padding="lg">
          <h3 className="text-sm font-semibold mb-4 text-ui-primary">
            Mastery Distribution
          </h3>
          {allTopics.length === 0 ? (
            <p className="text-xs text-ui-muted">No topics yet.</p>
          ) : (
            <div className="space-y-3">
              {distribution.map(({ label, count, color }) => (
                <div key={label}>
                  <div className="flex justify-between mb-1">
                    <span className="text-xs text-ui-secondary">{label}</span>
                    <span className="text-xs font-semibold" style={{ color }}>
                      {count}
                    </span>
                  </div>
                  <div className="progress-track">
                    <div
                      className="progress-fill"
                      style={{
                        width: allTopics.length > 0 ? `${(count / allTopics.length) * 100}%` : "0%",
                        backgroundColor: color,
                      }}
                    />
                  </div>
                </div>
              ))}
              <p className="text-[10px] pt-1 text-ui-muted">
                {allTopics.length} total topics tracked
              </p>
            </div>
          )}
        </Card>

        {/* Topic table */}
        <Card padding="lg">
          <h3 className="text-sm font-semibold mb-4 text-ui-primary">
            All Topics
          </h3>
          {allTopics.length === 0 ? (
            <p className="text-xs text-ui-muted">No topics yet.</p>
          ) : (
            <div className="overflow-auto max-h-80">
              <table className="w-full text-xs">
                <thead>
                  <tr style={{ borderBottom: "1px solid var(--border)" }}>
                    {["Topic", "Subject", "Mastery", "Sessions", "Accuracy"].map((h) => (
                      <th
                        key={h}
                        className="text-left pb-2 pr-4 font-medium text-ui-muted"
                      >
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {allTopics
                    .sort((a, b) => a.mastery_score - b.mastery_score)
                    .map((topic) => {
                      const total = topic.correct_count + topic.incorrect_count;
                      const accuracy = total > 0 ? Math.round((topic.correct_count / total) * 100) : null;
                      return (
                        <tr
                          key={topic.id}
                          style={{ borderBottom: "1px solid var(--border)" }}
                        >
                          <td className="py-2 pr-4 font-medium text-ui-primary">
                            {topic.display_name}
                          </td>
                          <td className="py-2 pr-4 text-ui-muted">
                            {topic.subject}
                          </td>
                          <td className="py-2 pr-4">
                            <div className="flex items-center gap-2">
                              <div className="w-16">
                                <MasteryBar score={topic.mastery_score} size="sm" />
                              </div>
                              <span className={masteryColor(topic.mastery_score)}>
                                {topic.mastery_score.toFixed(0)}%
                              </span>
                            </div>
                          </td>
                          <td className="py-2 pr-4 text-ui-muted">
                            {topic.exposure_count}
                          </td>
                          <td className="py-2 text-ui-muted">
                            {accuracy !== null ? `${accuracy}%` : "—"}
                          </td>
                        </tr>
                      );
                    })}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}

function EmptyChart() {
  return (
    <Card padding="none" className="h-[180px] flex items-center justify-center bg-[var(--bg-muted)]">
      <p className="text-xs text-ui-muted">
        No data yet — start studying!
      </p>
    </Card>
  );
}
