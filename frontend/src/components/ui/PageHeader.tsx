import type { ReactNode } from "react";

export interface PageHeaderProps {
  title: string;
  subtitle?: ReactNode;
  /** Secondary buttons first, then at most one primary button (06 §1.4). */
  actions?: ReactNode;
}

export function PageHeader({ title, subtitle, actions }: PageHeaderProps) {
  return (
    <header className="flex flex-wrap items-end justify-between gap-x-6 gap-y-4 pb-6 pt-3">
      <div className="min-w-0">
        <h1 className="text-display text-ink-950 max-sm:text-[32px] max-sm:leading-[36px]">{title}</h1>
        {subtitle ? <p className="mt-1.5 text-small text-ink-500">{subtitle}</p> : null}
      </div>
      {actions ? <div className="flex flex-wrap items-center gap-2">{actions}</div> : null}
    </header>
  );
}
