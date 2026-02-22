import { cn, masteryBarColor } from "@/lib/utils";

interface MasteryBarProps {
  score: number;
  size?: "sm" | "md";
}

export default function MasteryBar({ score, size = "md" }: MasteryBarProps) {
  return (
    <div className={cn("progress-track", size === "sm" && "progress-track-sm")}>
      <div
        className="progress-fill"
        style={{
          width: `${Math.min(score, 100)}%`,
          backgroundColor: masteryBarColor(score),
        }}
      />
    </div>
  );
}
