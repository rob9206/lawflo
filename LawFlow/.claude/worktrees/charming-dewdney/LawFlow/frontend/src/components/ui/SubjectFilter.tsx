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
            className="transition-all"
            style={{
              padding: "8px 16px",
              borderRadius: "var(--radius-full)",
              fontSize: "13px",
              fontWeight: isActive ? 800 : 700,
              backgroundColor: isActive ? "var(--blue-bg)" : "var(--card-bg)",
              color: isActive ? "var(--blue-dark)" : "var(--text-secondary)",
              border: `2px solid ${isActive ? "var(--blue)" : "var(--border)"}`,
              borderBottom: `4px solid ${isActive ? "var(--blue-dark)" : "var(--border-dark)"}`,
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
