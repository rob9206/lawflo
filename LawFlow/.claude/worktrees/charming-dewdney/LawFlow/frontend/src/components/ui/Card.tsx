import { cn } from "@/lib/utils";

interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  hover?: boolean;
  padding?: "none" | "sm" | "md" | "lg";
}

const paddingMap = {
  none: "",
  sm: "p-3",
  md: "p-4",
  lg: "p-5",
};

export default function Card({
  hover = false,
  padding = "md",
  className,
  children,
  ...props
}: CardProps) {
  return (
    <div
      className={cn(
        "duo-card",
        hover && "transition-transform duration-150 hover:-translate-y-0.5",
        paddingMap[padding],
        className
      )}
      {...props}
    >
      {children}
    </div>
  );
}
