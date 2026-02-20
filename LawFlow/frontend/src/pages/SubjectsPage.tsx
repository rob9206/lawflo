import { useQuery } from "@tanstack/react-query";
import { useNavigate, useParams } from "react-router-dom";
import { getMastery, getSubjectMastery } from "@/api/progress";
import { masteryColor } from "@/lib/utils";
import {
  BookOpen,
  Zap,
  ChevronRight,
  TrendingUp,
  TrendingDown,
  Clock,
  BarChart2,
} from "lucide-react";
import type { TopicMastery } from "@/types";

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

function masteryLabel(score: number) {
  if (score >= 80) return "Mastered";
  if (score >= 60) return "Advanced";
  if (score >= 40) return "Proficient";
  if (score >= 20) return "Developing";
  return "Beginning";
}

function masteryBarColor(score: number) {
  if (score >= 80) return "#22c55e";
  if (score >= 60) return "#10b981";
  if (score >= 40) return "#f59e0b";
  if (score >= 20) return "#f97316";
  return "#ef4444";
}

function confidenceFromTopics(topics: TopicMastery[]): number {
  const total = topics.reduce((s, t) => s + t.correct_count + t.incorrect_count, 0);
  if (total === 0) return 0;
  const correct = topics.reduce((s, t) => s + t.correct_count, 0);
  return Math.round((correct / total) * 100);
}

/* ── Subject list grid ──────────────────────────────────────────────────── */
export function SubjectsListPage() {
  const navigate = useNavigate();
  const { data: subjects = [], isLoading } = useQuery({
    queryKey: ["mastery"],
    queryFn: getMastery,
  });

  if (isLoading) {
    return (
      <div className="grid grid-cols-2 gap-4">
        {[...Array(4)].map((_, i) => (
          <div
            key={i}
            className="h-52 rounded-xl animate-pulse"
            style={{ backgroundColor: "var(--bg-card)" }}
          />
        ))}
      </div>
    );
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-2xl font-bold" style={{ color: "var(--text-primary)" }}>
            Subjects
          </h2>
          <p className="text-sm mt-0.5" style={{ color: "var(--text-muted)" }}>
            Track your mastery across law school courses
          </p>
        </div>
      </div>

      {subjects.length === 0 ? (
        <div
          className="rounded-xl p-12 text-center"
          style={{ backgroundColor: "var(--bg-card)", border: "1px solid var(--border)" }}
        >
          <BookOpen size={40} className="mx-auto mb-3" style={{ color: "var(--text-muted)" }} />
          <p style={{ color: "var(--text-secondary)" }}>No subjects tracked yet.</p>
          <p className="text-xs mt-1" style={{ color: "var(--text-muted)" }}>
            Upload documents and start studying to see subject cards here.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
          {subjects.map((s) => (
            <SubjectCard
              key={s.subject}
              subject={s.subject}
              displayName={s.display_name}
              masteryScore={s.mastery_score}
              studyMinutes={s.total_study_time_minutes}
              onClick={() => navigate(`/subjects/${s.subject}`)}
            />
          ))}
        </div>
      )}
    </div>
  );
}

function SubjectCard({
  subject,
  displayName,
  masteryScore,
  studyMinutes,
  onClick,
}: {
  subject: string;
  displayName: string;
  masteryScore: number;
  studyMinutes: number;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className="group text-left rounded-xl p-5 transition-all"
      style={{
        backgroundColor: "var(--bg-card)",
        border: "1px solid var(--border)",
        boxShadow: "var(--shadow-card)",
      }}
    >
      {/* Header */}
      <div className="flex items-start justify-between mb-3">
        <div
          className="w-10 h-10 rounded-xl flex items-center justify-center"
          style={{ backgroundColor: "var(--accent-muted)" }}
        >
          <BookOpen size={18} style={{ color: "var(--accent-text)" }} />
        </div>
        <span
          className="text-[10px] font-semibold px-2 py-0.5 rounded-full"
          style={{ backgroundColor: "var(--bg-muted)", color: "var(--text-muted)" }}
        >
          Core Courses
        </span>
      </div>

      <h3 className="font-semibold text-sm mb-0.5" style={{ color: "var(--text-primary)" }}>
        {displayName}
      </h3>
      <p className="text-xs mb-3 line-clamp-2" style={{ color: "var(--text-muted)" }}>
        {subject === "con_law" && "Foundational principles of the U.S. Constitution."}
        {subject === "contracts" && "Formation, enforcement, and remedies for breach of contract."}
        {subject === "torts" && "Civil wrongs including negligence, intentional torts, and strict liability."}
        {subject === "crim_law" && "Principles of criminal liability, defenses, and specific crimes."}
        {subject === "civ_pro" && "Rules governing civil litigation including jurisdiction and discovery."}
        {subject === "property" && "Real and personal property rights, transfers, and land use."}
        {subject === "evidence" && "Rules governing admissibility of evidence at trial."}
        {subject === "prof_responsibility" && "Professional duties, ethics, and responsibilities of attorneys."}
        {!SUBJECT_LABELS[subject] && "Legal concepts and principles for this subject."}
      </p>

      {/* Progress bar */}
      <div className="mb-2">
        <div className="flex items-center justify-between mb-1">
          <span className="text-[10px]" style={{ color: "var(--text-muted)" }}>
            Knowledge
          </span>
          <span
            className={`text-xs font-bold ${masteryColor(masteryScore)}`}
          >
            {masteryScore.toFixed(0)}% · {masteryLabel(masteryScore)}
          </span>
        </div>
        <div
          className="h-1.5 rounded-full overflow-hidden"
          style={{ backgroundColor: "var(--bg-muted)" }}
        >
          <div
            className="h-full rounded-full transition-all"
            style={{
              width: `${masteryScore}%`,
              backgroundColor: masteryBarColor(masteryScore),
            }}
          />
        </div>
      </div>

      <div className="flex items-center justify-between mt-3 pt-3" style={{ borderTop: "1px solid var(--border)" }}>
        <span className="text-[10px]" style={{ color: "var(--text-muted)" }}>
          {Math.round(studyMinutes / 60)}h studied
        </span>
        <span
          className="flex items-center gap-1 text-[10px] font-medium group-hover:underline"
          style={{ color: "var(--accent-text)" }}
        >
          Study This Subject
          <ChevronRight size={12} />
        </span>
      </div>
    </button>
  );
}

/* ── Subject detail page ────────────────────────────────────────────────── */
export function SubjectDetailPage() {
  const { subject } = useParams<{ subject: string }>();
  const navigate = useNavigate();

  const { data, isLoading } = useQuery({
    queryKey: ["subject-mastery", subject],
    queryFn: () => getSubjectMastery(subject!),
    enabled: !!subject,
  });

  if (isLoading || !data) {
    return (
      <div className="animate-pulse space-y-4">
        <div className="h-8 w-48 rounded" style={{ backgroundColor: "var(--bg-muted)" }} />
        <div className="h-48 rounded-xl" style={{ backgroundColor: "var(--bg-card)" }} />
      </div>
    );
  }

  const topics = data.topics || [];
  const confidence = confidenceFromTopics(topics);

  const strongTopics = topics
    .filter((t) => t.mastery_score >= 60)
    .sort((a, b) => b.mastery_score - a.mastery_score)
    .slice(0, 3);

  const weakTopics = topics
    .filter((t) => t.mastery_score < 60)
    .sort((a, b) => a.mastery_score - b.mastery_score)
    .slice(0, 3);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <button
            onClick={() => navigate("/subjects")}
            className="text-xs mb-2 flex items-center gap-1 transition-colors"
            style={{ color: "var(--text-muted)" }}
          >
            ← Back to Subjects
          </button>
          <h2 className="text-2xl font-bold" style={{ color: "var(--text-primary)" }}>
            {data.display_name}
          </h2>
          <span
            className="inline-block text-xs mt-1 px-2 py-0.5 rounded-full"
            style={{ backgroundColor: "var(--bg-muted)", color: "var(--text-muted)" }}
          >
            Core Courses
          </span>
        </div>
        <button
          onClick={() => navigate(`/auto-teach?subject=${subject}`)}
          className="flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-semibold text-white"
          style={{ backgroundColor: "var(--accent)" }}
        >
          <Zap size={16} />
          Study This Subject
        </button>
      </div>

      {/* Top metrics */}
      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        {/* Knowledge mastery */}
        <MetricCard
          label="Knowledge"
          value={`${(data.mastery_score / 10).toFixed(1)}/10`}
          sub={masteryLabel(data.mastery_score)}
          bar
          barValue={data.mastery_score}
          icon={<BarChart2 size={16} />}
        />
        {/* Confidence */}
        <MetricCard
          label="Confidence"
          value={`${(confidence / 10).toFixed(1)}/10`}
          sub="from Q&A accuracy"
          bar
          barValue={confidence}
          icon={<TrendingUp size={16} />}
        />
        {/* Study time */}
        <MetricCard
          label="Study Time"
          value={`${Math.round(data.total_study_time_minutes / 60)}h`}
          sub={`${data.sessions_count} sessions`}
          icon={<Clock size={16} />}
        />
        {/* Topics */}
        <MetricCard
          label="Topics"
          value={String(topics.length)}
          sub={`${topics.filter((t) => t.mastery_score >= 80).length} mastered`}
          icon={<BookOpen size={16} />}
        />
      </div>

      {/* Strong / Weak topics */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <div
          className="rounded-xl p-4"
          style={{
            backgroundColor: "var(--bg-card)",
            border: "1px solid var(--border)",
            boxShadow: "var(--shadow-card)",
          }}
        >
          <div className="flex items-center gap-2 mb-3">
            <TrendingUp size={15} className="text-emerald-400" />
            <h4 className="text-sm font-semibold" style={{ color: "var(--text-primary)" }}>
              Strong Topics
            </h4>
          </div>
          {strongTopics.length === 0 ? (
            <p className="text-xs" style={{ color: "var(--text-muted)" }}>
              No strong topics yet — keep studying!
            </p>
          ) : (
            <div className="space-y-2">
              {strongTopics.map((t) => (
                <TopicRow key={t.id} topic={t} />
              ))}
            </div>
          )}
        </div>

        <div
          className="rounded-xl p-4"
          style={{
            backgroundColor: "var(--bg-card)",
            border: "1px solid var(--border)",
            boxShadow: "var(--shadow-card)",
          }}
        >
          <div className="flex items-center gap-2 mb-3">
            <TrendingDown size={15} className="text-red-400" />
            <h4 className="text-sm font-semibold" style={{ color: "var(--text-primary)" }}>
              Needs Attention
            </h4>
          </div>
          {weakTopics.length === 0 ? (
            <p className="text-xs" style={{ color: "var(--text-muted)" }}>
              All topics look good!
            </p>
          ) : (
            <div className="space-y-2">
              {weakTopics.map((t) => (
                <TopicRow key={t.id} topic={t} />
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Full topic breakdown */}
      <div
        className="rounded-xl p-4"
        style={{
          backgroundColor: "var(--bg-card)",
          border: "1px solid var(--border)",
          boxShadow: "var(--shadow-card)",
        }}
      >
        <h4 className="text-sm font-semibold mb-4" style={{ color: "var(--text-primary)" }}>
          All Topics
        </h4>
        {topics.length === 0 ? (
          <p className="text-xs" style={{ color: "var(--text-muted)" }}>
            No topics yet. Start a tutoring session to begin tracking.
          </p>
        ) : (
          <div className="space-y-3">
            {topics
              .sort((a, b) => a.mastery_score - b.mastery_score)
              .map((topic) => (
                <div key={topic.id}>
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs font-medium" style={{ color: "var(--text-primary)" }}>
                      {topic.display_name}
                    </span>
                    <div className="flex items-center gap-3">
                      <span className="text-[10px]" style={{ color: "var(--text-muted)" }}>
                        {topic.exposure_count} sessions
                      </span>
                      <span className={`text-xs font-semibold ${masteryColor(topic.mastery_score)}`}>
                        {topic.mastery_score.toFixed(0)}%
                      </span>
                    </div>
                  </div>
                  <div
                    className="h-1.5 rounded-full overflow-hidden"
                    style={{ backgroundColor: "var(--bg-muted)" }}
                  >
                    <div
                      className="h-full rounded-full transition-all"
                      style={{
                        width: `${topic.mastery_score}%`,
                        backgroundColor: masteryBarColor(topic.mastery_score),
                      }}
                    />
                  </div>
                </div>
              ))}
          </div>
        )}
      </div>
    </div>
  );
}

function MetricCard({
  label,
  value,
  sub,
  bar,
  barValue,
  icon,
}: {
  label: string;
  value: string;
  sub: string;
  bar?: boolean;
  barValue?: number;
  icon: React.ReactNode;
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
      <div className="flex items-center gap-1.5 mb-2" style={{ color: "var(--text-muted)" }}>
        {icon}
        <span className="text-xs">{label}</span>
      </div>
      <p className="text-xl font-bold" style={{ color: "var(--text-primary)" }}>
        {value}
      </p>
      {bar && barValue !== undefined && (
        <div className="my-1.5 h-1.5 rounded-full overflow-hidden" style={{ backgroundColor: "var(--bg-muted)" }}>
          <div
            className="h-full rounded-full"
            style={{
              width: `${barValue}%`,
              backgroundColor: masteryBarColor(barValue),
            }}
          />
        </div>
      )}
      <p className="text-[10px] mt-0.5" style={{ color: "var(--text-secondary)" }}>
        {sub}
      </p>
    </div>
  );
}

function TopicRow({ topic }: { topic: TopicMastery }) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-xs" style={{ color: "var(--text-secondary)" }}>
        {topic.display_name}
      </span>
      <span className={`text-xs font-semibold ${masteryColor(topic.mastery_score)}`}>
        {topic.mastery_score.toFixed(0)}%
      </span>
    </div>
  );
}
