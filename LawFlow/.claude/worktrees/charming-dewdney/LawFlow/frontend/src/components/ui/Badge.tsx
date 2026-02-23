import { cn } from "@/lib/utils";

type BadgeVariant = "default" | "green" | "blue" | "orange" | "red" | "gold" | "navy" | "purple";

interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: BadgeVariant;
}

export default function Badge({ variant = "default", className, children, ...props }: BadgeProps) {
  return (
    <span className={cn("duo-badge", variant !== "default" && `duo-badge-${variant}`, className)} {...props}>
      {children}
    </span>
  );
}
