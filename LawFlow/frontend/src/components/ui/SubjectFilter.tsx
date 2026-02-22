interface SubjectOption {
  value: string;
  label: string;
}

interface MasteryInfo {
  subject: string;
  mastery_score: number;
}

interface SubjectFilterProps {
  subjects: readonly SubjectOption[];
  selected: string;
  onSelect: (value: string) => void;
  masteryData?: MasteryInfo[];
}

export default function SubjectFilter({
  subjects,
  selected,
  onSelect,
  masteryData,
}: SubjectFilterProps) {
  return (
    <div className="flex flex-wrap gap-2">
      {subjects.map((s) => {
        const isActive = selected === s.value;
        const mastery = masteryData?.find((m) => m.subject === s.value);
        return (
          <button
            key={s.value}
            onClick={() => onSelect(s.value)}
            className="px-3 py-1.5 rounded-lg text-xs font-medium transition-all"
            style={{
              backgroundColor: isActive ? "var(--accent-muted)" : "var(--bg-card)",
              color: isActive ? "var(--accent-text)" : "var(--text-secondary)",
              border: `1px solid ${isActive ? "var(--accent)" : "var(--border)"}`,
            }}
          >
            {s.label}
            {mastery && (
              <span className="ml-1.5 opacity-60">
                {mastery.mastery_score.toFixed(0)}%
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
}
