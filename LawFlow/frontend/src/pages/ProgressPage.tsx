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
import { masteryColor } from "@/lib/utils";
import { Flame, Calendar, Clock, TrendingUp, BarChart2, BookOpen } from "lucide-react";

function masteryBarColor(score: number) {
  if (score >= 80) return "#22c55e";
  if (score >= 60) return "#10b981";
  if (score >= 40) return "#f59e0b";
  if (score >= 20) return "#f97316";
  return "#ef4444";
}

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

  // Recent 14 days for the area chart label abbreviations
  const recentHistory = history.slice(-14).map((d) => ({
    ...d,
    label: d.date.slice(5), // "MM-DD"
  }));

  // Subject comparison data
  const subjectChartData = subjects.map((s) => ({
    name: s.display_name.split(" ")[0], // first word for brevity
    mastery: Math.round(s.mastery_score),
    fill: masteryBarColor(s.mastery_score),
  }));

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-2xl font-bold" style={{ color: "var(--text-primary)" }}>
          Progress
        </h2>
        <p className="text-sm mt-0.5" style={{ color: "var(--text-muted)" }}>
          Your learning analytics over the past 30 days
        </p>
      </div>

      {/* Streak stats */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <StreakCard
          icon={<Flame size={20} className="text-orange-400" />}
          label="Current Streak"
          value={`${streaks?.current_streak ?? 0}`}
          sub="days in a row"
        />
        <StreakCard
          icon={<TrendingUp size={20} className="text-emerald-400" />}
          label="Longest Streak"
          value={`${streaks?.longest_streak ?? 0}`}
          sub="days record"
        />
        <StreakCard
          icon={<Calendar size={20} className="text-blue-400" />}
          label="Total Study Days"
          value={`${streaks?.total_days ?? 0}`}
          sub="since joining"
        />
        <StreakCard
          icon={<Clock size={20} className="text-indigo-400" />}
          label="Total Hours"
          value={`${Math.round((dashboard?.stats.total_study_minutes ?? 0) / 60)}`}
          sub="hours studied"
        />
      </div>

      {/* Charts row */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">

        {/* Study time bar chart */}
        <div
          className="rounded-xl p-5"
          style={{
            backgroundColor: "var(--bg-card)",
            border: "1px solid var(--border)",
            boxShadow: "var(--shadow-card)",
          }}
        >
          <div className="flex items-center gap-2 mb-4">
            <BarChart2 size={16} style={{ color: "var(--text-muted)" }} />
            <h3 className="text-sm font-semibold" style={{ color: "var(--text-primary)" }}>
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
        </div>

        {/* Sessions area chart */}
        <div
          className="rounded-xl p-5"
          style={{
            backgroundColor: "var(--bg-card)",
            border: "1px solid var(--border)",
            boxShadow: "var(--shadow-card)",
          }}
        >
          <div className="flex items-center gap-2 mb-4">
            <TrendingUp size={16} style={{ color: "var(--text-muted)" }} />
            <h3 className="text-sm font-semibold" style={{ color: "var(--text-primary)" }}>
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
        </div>

      </div>

      {/* Subject comparison */}
      {subjectChartData.length > 0 && (
        <div
          className="rounded-xl p-5"
          style={{
            backgroundColor: "var(--bg-card)",
            border: "1px solid var(--border)",
            boxShadow: "var(--shadow-card)",
          }}
        >
          <div className="flex items-center gap-2 mb-4">
            <BookOpen size={16} style={{ color: "var(--text-muted)" }} />
            <h3 className="text-sm font-semibold" style={{ color: "var(--text-primary)" }}>
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
        </div>
      )}

      {/* Mastery distribution + Topic heatmap */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[280px_1fr]">

        {/* Distribution */}
        <div
          className="rounded-xl p-5"
          style={{
            backgroundColor: "var(--bg-card)",
            border: "1px solid var(--border)",
            boxShadow: "var(--shadow-card)",
          }}
        >
          <h3 className="text-sm font-semibold mb-4" style={{ color: "var(--text-primary)" }}>
            Mastery Distribution
          </h3>
          {allTopics.length === 0 ? (
            <p className="text-xs" style={{ color: "var(--text-muted)" }}>No topics yet.</p>
          ) : (
            <div className="space-y-3">
              {distribution.map(({ label, count, color }) => (
                <div key={label}>
                  <div className="flex justify-between mb-1">
                    <span className="text-xs" style={{ color: "var(--text-secondary)" }}>
                      {label}
                    </span>
                    <span className="text-xs font-semibold" style={{ color }}>
                      {count}
                    </span>
                  </div>
                  <div
                    className="h-2 rounded-full overflow-hidden"
                    style={{ backgroundColor: "var(--bg-muted)" }}
                  >
                    <div
                      className="h-full rounded-full"
                      style={{
                        width: allTopics.length > 0 ? `${(count / allTopics.length) * 100}%` : "0%",
                        backgroundColor: color,
                      }}
                    />
                  </div>
                </div>
              ))}
              <p className="text-[10px] pt-1" style={{ color: "var(--text-muted)" }}>
                {allTopics.length} total topics tracked
              </p>
            </div>
          )}
        </div>

        {/* Topic table */}
        <div
          className="rounded-xl p-5"
          style={{
            backgroundColor: "var(--bg-card)",
            border: "1px solid var(--border)",
            boxShadow: "var(--shadow-card)",
          }}
        >
          <h3 className="text-sm font-semibold mb-4" style={{ color: "var(--text-primary)" }}>
            All Topics
          </h3>
          {allTopics.length === 0 ? (
            <p className="text-xs" style={{ color: "var(--text-muted)" }}>No topics yet.</p>
          ) : (
            <div className="overflow-auto max-h-80">
              <table className="w-full text-xs">
                <thead>
                  <tr style={{ borderBottom: "1px solid var(--border)" }}>
                    {["Topic", "Subject", "Mastery", "Sessions", "Accuracy"].map((h) => (
                      <th
                        key={h}
                        className="text-left pb-2 pr-4 font-medium"
                        style={{ color: "var(--text-muted)" }}
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
                          <td className="py-2 pr-4 font-medium" style={{ color: "var(--text-primary)" }}>
                            {topic.display_name}
                          </td>
                          <td className="py-2 pr-4" style={{ color: "var(--text-muted)" }}>
                            {topic.subject}
                          </td>
                          <td className="py-2 pr-4">
                            <div className="flex items-center gap-2">
                              <div
                                className="h-1.5 w-16 rounded-full overflow-hidden"
                                style={{ backgroundColor: "var(--bg-muted)" }}
                              >
                                <div
                                  className="h-full rounded-full"
                                  style={{
                                    width: `${topic.mastery_score}%`,
                                    backgroundColor: masteryBarColor(topic.mastery_score),
                                  }}
                                />
                              </div>
                              <span className={masteryColor(topic.mastery_score)}>
                                {topic.mastery_score.toFixed(0)}%
                              </span>
                            </div>
                          </td>
                          <td className="py-2 pr-4" style={{ color: "var(--text-muted)" }}>
                            {topic.exposure_count}
                          </td>
                          <td className="py-2" style={{ color: "var(--text-muted)" }}>
                            {accuracy !== null ? `${accuracy}%` : "—"}
                          </td>
                        </tr>
                      );
                    })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function StreakCard({
  icon,
  label,
  value,
  sub,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
  sub: string;
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
        {icon}
        <span className="text-xs" style={{ color: "var(--text-muted)" }}>
          {label}
        </span>
      </div>
      <p className="text-3xl font-bold" style={{ color: "var(--text-primary)" }}>
        {value}
      </p>
      <p className="text-xs mt-0.5" style={{ color: "var(--text-secondary)" }}>
        {sub}
      </p>
    </div>
  );
}

function EmptyChart() {
  return (
    <div
      className="h-[180px] rounded-xl flex items-center justify-center"
      style={{ backgroundColor: "var(--bg-muted)" }}
    >
      <p className="text-xs" style={{ color: "var(--text-muted)" }}>
        No data yet — start studying!
      </p>
    </div>
  );
}
