import { cn } from "@/lib/utils";

type BadgeVariant = "accent" | "muted" | "success" | "warning" | "danger";

interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: BadgeVariant;
}

export default function Badge({ variant = "muted", className, children, ...props }: BadgeProps) {
  return (
    <span className={cn("badge", `badge-${variant}`, className)} {...props}>
      {children}
    </span>
  );
}
