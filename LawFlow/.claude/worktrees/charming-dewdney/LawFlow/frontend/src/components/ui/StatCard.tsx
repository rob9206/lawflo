import Card from "./Card";
import MasteryBar from "./MasteryBar";

interface StatCardProps {
  icon: React.ReactNode;
  label: string;
  value: string;
  sub?: string;
  color?: string;
  bar?: boolean;
  barValue?: number;
}

export default function StatCard({
  icon,
  label,
  value,
  sub,
  color,
  bar,
  barValue,
}: StatCardProps) {
  return (
    <Card>
      <div className="flex items-center gap-2 mb-2">
        <span style={{ color: color || "var(--text-secondary)" }}>{icon}</span>
        <span style={{ fontSize: "13px", fontWeight: 800, textTransform: "uppercase", letterSpacing: "0.06em", color: "var(--text-secondary)" }}>
          {label}
        </span>
      </div>
      <p style={{ fontSize: "28px", fontWeight: 900, color: "var(--text-primary)" }}>{value}</p>
      {bar && barValue !== undefined && (
        <div className="my-1.5">
          <MasteryBar score={barValue} size="sm" />
        </div>
      )}
      {sub && <p style={{ fontSize: "13px", fontWeight: 600, marginTop: "4px", color: "var(--text-secondary)" }}>{sub}</p>}
    </Card>
  );
}
