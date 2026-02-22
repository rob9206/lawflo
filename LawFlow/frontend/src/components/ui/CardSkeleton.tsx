import { cn } from "@/lib/utils";

interface CardSkeletonProps {
  className?: string;
  lines?: number;
}

export default function CardSkeleton({ className, lines = 3 }: CardSkeletonProps) {
  return (
    <div className={cn("card p-4 animate-pulse", className)}>
      <div className="h-3 w-1/3 rounded bg-muted-ui mb-3" />
      {Array.from({ length: lines }).map((_, i) => (
        <div
          key={i}
          className="h-2.5 rounded bg-muted-ui mb-2"
          style={{ width: `${85 - i * 15}%` }}
        />
      ))}
    </div>
  );
}
