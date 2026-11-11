import type { ReactNode } from "react";

interface PageHeaderProps {
  title: string;
  subtitle?: ReactNode;
  actions?: ReactNode;
}

export default function PageHeader({
  title,
  subtitle,
  actions,
}: PageHeaderProps) {
  return (
    <header className="bg-header border-hair flex min-h-16 flex-wrap items-center justify-between gap-x-6 gap-y-3 border-b px-10 py-3.5">
      <div className="flex min-w-0 items-baseline gap-2.5">
        <h1 className="m-0 text-xl font-semibold">{title}</h1>
        {subtitle && <span className="text-ink-3 text-sm">{subtitle}</span>}
      </div>
      {actions && <div className="flex flex-wrap gap-2.5">{actions}</div>}
    </header>
  );
}
