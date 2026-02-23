interface EmptyStateProps {
  icon: React.ReactNode;
  message: string;
  sub?: string;
  action?: React.ReactNode;
}

export default function EmptyState({ icon, message, sub, action }: EmptyStateProps) {
  return (
    <div
      className="mx-auto text-center"
      style={{ maxWidth: "360px", padding: "48px 24px" }}
    >
      <div className="mb-4 flex justify-center" style={{ color: "var(--text-muted)" }}>
        {icon}
      </div>
      <p style={{ fontSize: "20px", fontWeight: 800, color: "var(--text-primary)", marginBottom: "8px" }}>
        {message}
      </p>
      {sub && (
        <p style={{ fontSize: "15px", fontWeight: 500, color: "var(--text-secondary)" }}>
          {sub}
        </p>
      )}
      {action && <div style={{ marginTop: "20px" }}>{action}</div>}
    </div>
  );
}
