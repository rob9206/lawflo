import { cn } from "@/lib/utils";

interface CardSkeletonProps {
  className?: string;
  lines?: number;
}

export default function CardSkeleton({ className, lines = 3 }: CardSkeletonProps) {
  return (
    <div className={cn("duo-card p-4 animate-pulse", className)}>
      <div className="h-3 w-1/3 rounded mb-3" style={{ background: "var(--surface-bg)" }} />
      {Array.from({ length: lines }).map((_, i) => (
        <div
          key={i}
          className="h-2.5 rounded mb-2"
          style={{ width: `${85 - i * 15}%`, background: "var(--surface-bg)" }}
        />
      ))}
    </div>
  );
}
