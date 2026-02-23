import { cn, masteryBarColor } from "@/lib/utils";

interface MasteryBarProps {
  score: number;
  size?: "sm" | "md";
}

export default function MasteryBar({ score, size = "md" }: MasteryBarProps) {
  return (
    <div
      className={cn("duo-progress-track", size === "sm" && "!h-2")}
    >
      <div
        className="duo-progress-fill"
        style={{
          width: `${Math.min(score, 100)}%`,
          backgroundColor: masteryBarColor(score),
        }}
      />
    </div>
  );
}
