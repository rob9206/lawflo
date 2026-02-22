import { useQuery } from "@tanstack/react-query";
import { useNavigate, useParams } from "react-router-dom";
import { getMastery, getSubjectMastery } from "@/api/progress";
import { masteryColor, masteryLabel, masteryBarColor } from "@/lib/utils";
import { SUBJECT_LABELS, SUBJECT_DESCRIPTIONS } from "@/lib/constants";
import Card from "@/components/ui/Card";
import StatCard from "@/components/ui/StatCard";
import PageHeader from "@/components/ui/PageHeader";
import Badge from "@/components/ui/Badge";
import EmptyState from "@/components/ui/EmptyState";
import MasteryBar from "@/components/ui/MasteryBar";
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
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
        {[...Array(4)].map((_, i) => (
          <div key={i} className="h-52 rounded-xl animate-pulse card" />
        ))}
      </div>
    );
  }

  return (
    <div>
      <PageHeader
        title="Subjects"
        subtitle="Track your mastery across law school courses"
      />

      <div className="mt-6">
        {subjects.length === 0 ? (
          <EmptyState
            icon={<BookOpen size={40} />}
            message="No subjects tracked yet."
            sub="Upload documents and start studying to see subject cards here."
          />
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
  const description =
    SUBJECT_DESCRIPTIONS[subject] ?? "Legal concepts and principles for this subject.";

  return (
    <Card hover padding="lg" className="cursor-pointer group" onClick={onClick}>
      <div className="flex items-start justify-between mb-3">
        <div
          className="w-10 h-10 rounded-xl flex items-center justify-center"
          style={{ backgroundColor: "var(--accent-muted)" }}
        >
          <BookOpen size={18} className="text-accent-label" />
        </div>
        <Badge>Core Courses</Badge>
      </div>

      <h3 className="font-semibold text-sm mb-0.5 text-ui-primary">
        {displayName}
      </h3>
      <p className="text-xs mb-3 line-clamp-2 text-ui-muted">
        {description}
      </p>

      <div className="mb-2">
        <div className="flex items-center justify-between mb-1">
          <span className="text-[10px] text-ui-muted">Knowledge</span>
          <span className={`text-xs font-bold ${masteryColor(masteryScore)}`}>
            {masteryScore.toFixed(0)}% · {masteryLabel(masteryScore)}
          </span>
        </div>
        <MasteryBar score={masteryScore} size="sm" />
      </div>

      <div
        className="flex items-center justify-between mt-3 pt-3"
        style={{ borderTop: "1px solid var(--border)" }}
      >
        <span className="text-[10px] text-ui-muted">
          {Math.round(studyMinutes / 60)}h studied
        </span>
        <span className="flex items-center gap-1 text-[10px] font-medium text-accent-label group-hover:underline">
          Study This Subject
          <ChevronRight size={12} />
        </span>
      </div>
    </Card>
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
        <div className="h-8 w-48 rounded bg-muted-ui" />
        <div className="h-48 rounded-xl card" />
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
      <PageHeader
        title={data.display_name}
        subtitle=""
        action={
          <button
            onClick={() => navigate(`/auto-teach?subject=${subject}`)}
            className="btn-primary flex items-center gap-2"
          >
            <Zap size={16} />
            Study This Subject
          </button>
        }
      />
      <div className="-mt-4">
        <button
          onClick={() => navigate("/subjects")}
          className="text-xs mb-2 flex items-center gap-1 transition-colors text-ui-muted"
        >
          ← Back to Subjects
        </button>
        <Badge>Core Courses</Badge>
      </div>

      {/* Top metrics */}
      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        <StatCard
          label="Knowledge"
          value={`${(data.mastery_score / 10).toFixed(1)}/10`}
          sub={masteryLabel(data.mastery_score)}
          bar
          barValue={data.mastery_score}
          icon={<BarChart2 size={16} />}
        />
        <StatCard
          label="Confidence"
          value={`${(confidence / 10).toFixed(1)}/10`}
          sub="from Q&A accuracy"
          bar
          barValue={confidence}
          icon={<TrendingUp size={16} />}
        />
        <StatCard
          label="Study Time"
          value={`${Math.round(data.total_study_time_minutes / 60)}h`}
          sub={`${data.sessions_count} sessions`}
          icon={<Clock size={16} />}
        />
        <StatCard
          label="Topics"
          value={String(topics.length)}
          sub={`${topics.filter((t) => t.mastery_score >= 80).length} mastered`}
          icon={<BookOpen size={16} />}
        />
      </div>

      {/* Strong / Weak topics */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <Card>
          <div className="flex items-center gap-2 mb-3">
            <TrendingUp size={15} className="text-emerald-400" />
            <h4 className="text-sm font-semibold text-ui-primary">Strong Topics</h4>
          </div>
          {strongTopics.length === 0 ? (
            <p className="text-xs text-ui-muted">No strong topics yet — keep studying!</p>
          ) : (
            <div className="space-y-2">
              {strongTopics.map((t) => (
                <TopicRow key={t.id} topic={t} />
              ))}
            </div>
          )}
        </Card>

        <Card>
          <div className="flex items-center gap-2 mb-3">
            <TrendingDown size={15} className="text-red-400" />
            <h4 className="text-sm font-semibold text-ui-primary">Needs Attention</h4>
          </div>
          {weakTopics.length === 0 ? (
            <p className="text-xs text-ui-muted">All topics look good!</p>
          ) : (
            <div className="space-y-2">
              {weakTopics.map((t) => (
                <TopicRow key={t.id} topic={t} />
              ))}
            </div>
          )}
        </Card>
      </div>

      {/* Full topic breakdown */}
      <Card>
        <h4 className="text-sm font-semibold mb-4 text-ui-primary">All Topics</h4>
        {topics.length === 0 ? (
          <p className="text-xs text-ui-muted">
            No topics yet. Start a tutoring session to begin tracking.
          </p>
        ) : (
          <div className="space-y-3">
            {topics
              .sort((a, b) => a.mastery_score - b.mastery_score)
              .map((topic) => (
                <div key={topic.id}>
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs font-medium text-ui-primary">
                      {topic.display_name}
                    </span>
                    <div className="flex items-center gap-3">
                      <span className="text-[10px] text-ui-muted">
                        {topic.exposure_count} sessions
                      </span>
                      <span className={`text-xs font-semibold ${masteryColor(topic.mastery_score)}`}>
                        {topic.mastery_score.toFixed(0)}%
                      </span>
                    </div>
                  </div>
                  <MasteryBar score={topic.mastery_score} size="sm" />
                </div>
              ))}
          </div>
        )}
      </Card>
    </div>
  );
}

function TopicRow({ topic }: { topic: TopicMastery }) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-xs text-ui-secondary">{topic.display_name}</span>
      <span className={`text-xs font-semibold ${masteryColor(topic.mastery_score)}`}>
        {topic.mastery_score.toFixed(0)}%
      </span>
    </div>
  );
}
