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
        <span className={color}>{icon}</span>
        <span className="text-xs text-ui-muted">{label}</span>
      </div>
      <p className="text-2xl font-bold text-ui-primary">{value}</p>
      {bar && barValue !== undefined && (
        <div className="my-1.5">
          <MasteryBar score={barValue} size="sm" />
        </div>
      )}
      {sub && <p className="text-xs mt-0.5 text-ui-secondary">{sub}</p>}
    </Card>
  );
}
