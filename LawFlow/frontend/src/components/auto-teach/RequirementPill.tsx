import { useState } from "react";
import { ChevronDown } from "lucide-react";
import { cn } from "@/lib/utils";

interface RequirementPillProps {
  label: string;
  detail: string;
  index: number;
}

export default function RequirementPill({ label, detail, index }: RequirementPillProps) {
  const [open, setOpen] = useState(false);

  return (
    <button
      type="button"
      onClick={() => setOpen((current) => !current)}
      className="w-full rounded-2xl border-2 border-b-4 px-4 py-3 text-left transition-all"
      style={{
        backgroundColor: "var(--card-bg)",
        borderColor: open ? "var(--green)" : "var(--border)",
        borderBottomColor: open ? "var(--green-dark)" : "var(--border)",
      }}
    >
      <div className="flex items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <span
            className="flex h-8 w-8 items-center justify-center rounded-[10px] border-2 text-sm"
            style={{
              fontWeight: 900,
              borderColor: open ? "var(--green)" : "var(--border)",
              backgroundColor: open ? "var(--green-bg)" : "var(--page-bg)",
              color: open ? "var(--green-dark)" : "var(--text-muted)",
            }}
          >
            {index + 1}
          </span>
          <span className="text-[17px]" style={{ fontWeight: 800, color: "var(--text-primary)" }}>{label}</span>
        </div>

        <ChevronDown
          size={20}
          className={cn(
            "shrink-0 transition-transform",
            open ? "rotate-180" : "-rotate-90"
          )}
          style={{ color: open ? "var(--green)" : "var(--text-muted)" }}
        />
      </div>

      {open && (
        <p className="animate-fade-up ml-11 mt-3 text-base leading-7" style={{ color: "var(--text-primary)" }}>{detail}</p>
      )}
    </button>
  );
}
