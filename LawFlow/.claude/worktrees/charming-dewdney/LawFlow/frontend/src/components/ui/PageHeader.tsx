interface PageHeaderProps {
  icon?: React.ReactNode;
  title: string;
  subtitle?: string;
  action?: React.ReactNode;
}

export default function PageHeader({ icon, title, subtitle, action }: PageHeaderProps) {
  return (
    <div className="flex items-start justify-between">
      <div className="flex items-center gap-3">
        {icon && <span style={{ color: "var(--blue)" }}>{icon}</span>}
        <div>
          <h2 style={{ fontSize: "30px", fontWeight: 900, color: "var(--text-primary)" }}>
            {title}
          </h2>
          {subtitle && (
            <p style={{ fontSize: "15px", fontWeight: 500, marginTop: "4px", color: "var(--text-secondary)" }}>
              {subtitle}
            </p>
          )}
        </div>
      </div>
      {action}
    </div>
  );
}
