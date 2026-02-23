import type { AutoTeachLesson } from "@/types/auto-teach";
import RequirementPill from "@/components/auto-teach/RequirementPill";

interface LessonContentProps {
  lesson: AutoTeachLesson;
}

export default function LessonContent({ lesson }: LessonContentProps) {
  return (
    <div className="space-y-5">
      <section className="duo-card rounded-2xl p-6">
        <h3
          className="mb-2 text-[12px] uppercase tracking-[0.1em]"
          style={{ fontWeight: 800, color: "var(--text-secondary)" }}
        >
          Definition
        </h3>
        <p
          className="text-lg leading-8"
          style={{ fontWeight: 500, color: "var(--text-primary)", whiteSpace: "pre-line" }}
        >
          {lesson.definition}
        </p>
      </section>

      {lesson.requirements.length > 0 && (
        <section>
          <h3
            className="mb-3 px-1 text-[12px] uppercase tracking-[0.1em]"
            style={{ fontWeight: 800, color: "var(--text-secondary)" }}
          >
            Key Elements{" "}
            <span className="normal-case tracking-normal" style={{ color: "var(--text-muted)" }}>
              - tap to expand
            </span>
          </h3>
          <div className="space-y-3">
            {lesson.requirements.map((requirement, index) => (
              <RequirementPill
                key={requirement.label}
                index={index}
                label={requirement.label}
                detail={requirement.detail}
              />
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
