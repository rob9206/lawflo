import { useQuery } from "@tanstack/react-query";
import { getDashboard } from "@/api/progress";
import { masteryColor, masteryBg } from "@/lib/utils";
import {
  BookOpen,
  Brain,
  Clock,
  Layers,
} from "lucide-react";

export default function DashboardPage() {
  const { data, isLoading } = useQuery({
    queryKey: ["dashboard"],
    queryFn: getDashboard,
  });

  if (isLoading) {
    return <div className="animate-pulse text-zinc-500">Loading dashboard...</div>;
  }

  const stats = data?.stats;
  const subjects = data?.subjects || [];

  return (
    <div>
      <h2 className="text-2xl font-bold mb-6">Dashboard</h2>

      {/* Stats row */}
      <div className="grid grid-cols-4 gap-4 mb-8">
        <StatCard
          icon={<Brain size={20} />}
          label="Overall Mastery"
          value={`${(stats?.overall_mastery ?? 0).toFixed(0)}%`}
        />
        <StatCard
          icon={<Layers size={20} />}
          label="Knowledge Chunks"
          value={String(stats?.total_knowledge_chunks ?? 0)}
        />
        <StatCard
          icon={<BookOpen size={20} />}
          label="Study Sessions"
          value={String(stats?.total_sessions ?? 0)}
        />
        <StatCard
          icon={<Clock size={20} />}
          label="Study Time"
          value={`${stats?.total_study_minutes ?? 0}m`}
        />
      </div>

      {/* Subject mastery grid */}
      <h3 className="text-lg font-semibold mb-4">Subject Mastery</h3>
      {subjects.length === 0 ? (
        <div className="text-zinc-500 bg-zinc-900 rounded-xl p-8 text-center">
          <p className="mb-2">No subjects tracked yet.</p>
          <p className="text-sm">
            Upload documents and start a tutoring session to begin tracking your progress.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-2 gap-4">
          {subjects.map((s) => (
            <div
              key={s.subject}
              className="bg-zinc-900 border border-zinc-800 rounded-xl p-4"
            >
              <div className="flex items-center justify-between mb-3">
                <h4 className="font-semibold">{s.display_name}</h4>
                <span className={`text-lg font-bold ${masteryColor(s.mastery_score)}`}>
                  {s.mastery_score.toFixed(0)}%
                </span>
              </div>

              {/* Mastery bar */}
              <div className="h-2 bg-zinc-800 rounded-full overflow-hidden mb-3">
                <div
                  className={`h-full rounded-full transition-all ${masteryBg(s.mastery_score)}`}
                  style={{
                    width: `${s.mastery_score}%`,
                    backgroundColor:
                      s.mastery_score >= 80 ? "#22c55e" :
                      s.mastery_score >= 60 ? "#10b981" :
                      s.mastery_score >= 40 ? "#f59e0b" :
                      s.mastery_score >= 20 ? "#f97316" : "#ef4444",
                  }}
                />
              </div>

              <div className="flex justify-between text-xs text-zinc-500">
                <span>{s.topic_count ?? 0} topics</span>
                <span>{s.sessions_count} sessions</span>
              </div>

              {/* Weak topics */}
              {s.topics && s.topics.length > 0 && (
                <div className="mt-3 pt-3 border-t border-zinc-800">
                  <p className="text-xs text-zinc-500 mb-2">Weakest topics:</p>
                  <div className="flex flex-wrap gap-1.5">
                    {s.topics
                      .sort((a, b) => a.mastery_score - b.mastery_score)
                      .slice(0, 3)
                      .map((t) => (
                        <span
                          key={t.topic}
                          className={`text-xs px-2 py-0.5 rounded-full ${masteryBg(t.mastery_score)} ${masteryColor(t.mastery_score)}`}
                        >
                          {t.display_name} ({t.mastery_score.toFixed(0)}%)
                        </span>
                      ))}
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function StatCard({
  icon,
  label,
  value,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
}) {
  return (
    <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-4">
      <div className="flex items-center gap-2 text-zinc-400 mb-1">
        {icon}
        <span className="text-xs">{label}</span>
      </div>
      <p className="text-2xl font-bold">{value}</p>
    </div>
  );
}
