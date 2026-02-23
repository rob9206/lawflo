import type { AutoTeachLesson } from "@/types/auto-teach";

interface AutoTeachHeaderProps {
  lesson: AutoTeachLesson;
}

export default function AutoTeachHeader({ lesson }: AutoTeachHeaderProps) {
  return (
    <header
      className="w-full rounded-b-[20px] border-b-4 px-7 pb-7 pt-8 text-center text-white"
      style={{ backgroundColor: "var(--navy)", borderBottomColor: "var(--navy-dark)" }}
    >
      <div className="mb-4 inline-block rounded-[10px] bg-white/15 px-3 py-1 text-xs uppercase tracking-[0.1em] text-white/80" style={{ fontWeight: 800 }}>
        {lesson.category} · {lesson.level}
      </div>

      <h1 className="mb-1 text-4xl leading-none" style={{ fontWeight: 900 }}>{lesson.title}</h1>
      <p className="mb-5 text-lg text-white/70" style={{ fontWeight: 600 }}>{lesson.subtitle}</p>

      <div className="inline-flex items-center gap-2 rounded-[14px] border-2 border-white/25 bg-white/12 px-5 py-2">
        <span className="text-[22px] tracking-[0.08em]" style={{ fontWeight: 900, color: "var(--gold)" }}>
          {lesson.mnemonic.acronym}
        </span>
        <span className="h-1 w-1 rounded-full bg-white/40" />
        <span className="text-[15px] text-white/85" style={{ fontWeight: 700 }}>{lesson.mnemonic.expansion}</span>
      </div>
    </header>
  );
}
