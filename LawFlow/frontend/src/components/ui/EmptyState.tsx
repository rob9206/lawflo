import Card from "./Card";

interface EmptyStateProps {
  icon: React.ReactNode;
  message: string;
  sub?: string;
  action?: React.ReactNode;
}

export default function EmptyState({ icon, message, sub, action }: EmptyStateProps) {
  return (
    <Card padding="none" className="p-12 text-center">
      <div className="text-ui-muted mb-3 flex justify-center">{icon}</div>
      <p className="text-ui-secondary">{message}</p>
      {sub && <p className="text-xs mt-1 text-ui-muted">{sub}</p>}
      {action && <div className="mt-6">{action}</div>}
    </Card>
  );
}
