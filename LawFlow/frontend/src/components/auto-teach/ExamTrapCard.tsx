import { AlertTriangle } from "lucide-react";

interface ExamTrapCardProps {
  trap: string;
  detail: string;
}

export default function ExamTrapCard({ trap, detail }: ExamTrapCardProps) {
  return (
    <article
      className="flex items-start gap-3 rounded-2xl border-2 border-b-4 p-4"
      style={{
        backgroundColor: "var(--orange-bg)",
        borderColor: "var(--orange)",
        borderBottomColor: "var(--orange-dark)",
      }}
    >
      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-white" style={{ backgroundColor: "var(--orange)" }}>
        <AlertTriangle size={16} />
      </div>
      <div>
        <h4 className="mb-1 text-base" style={{ fontWeight: 800, color: "var(--orange-dark)" }}>{trap}</h4>
        <p className="text-base leading-7" style={{ color: "var(--text-primary)" }}>{detail}</p>
      </div>
    </article>
  );
}
