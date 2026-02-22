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
        {icon && <span className="text-accent-label">{icon}</span>}
        <div>
          <h2 className="text-2xl font-bold text-ui-primary">{title}</h2>
          {subtitle && (
            <p className="text-sm mt-0.5 text-ui-muted">{subtitle}</p>
          )}
        </div>
      </div>
      {action}
    </div>
  );
}
