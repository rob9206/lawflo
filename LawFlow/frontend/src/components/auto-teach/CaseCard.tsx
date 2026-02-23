import type { CaseExample } from "@/types/auto-teach";

interface CaseCardProps {
  caseExample: CaseExample;
}

export default function CaseCard({ caseExample }: CaseCardProps) {
  return (
    <section
      className="rounded-2xl border-b-4 p-6 text-white"
      style={{ backgroundColor: "var(--navy)", borderBottomColor: "var(--navy-dark)" }}
    >
      <div className="mb-3 text-[12px] uppercase tracking-[0.1em] text-white/50" style={{ fontWeight: 800 }}>
        Case Example
      </div>
      <h3 className="text-xl" style={{ fontWeight: 900 }}>{caseExample.name}</h3>
      {caseExample.court && <p className="mb-4 text-[13px] text-white/45" style={{ fontWeight: 600 }}>{caseExample.court}</p>}

      <div className="mb-3">
        <div className="mb-1 text-[11px] uppercase tracking-[0.1em]" style={{ fontWeight: 800, color: "var(--gold)" }}>
          Facts
        </div>
        <p className="text-base leading-7 text-white/85">{caseExample.facts}</p>
      </div>

      <div className={caseExample.significance ? "mb-3" : ""}>
        <div className="mb-1 text-[11px] uppercase tracking-[0.1em]" style={{ fontWeight: 800, color: "var(--gold)" }}>
          Holding
        </div>
        <p className="text-base leading-7 text-white" style={{ fontWeight: 700 }}>{caseExample.holding}</p>
      </div>

      {caseExample.significance && (
        <p className="border-t border-white/12 pt-3 text-sm italic text-white/55">💡 {caseExample.significance}</p>
      )}
    </section>
  );
}
