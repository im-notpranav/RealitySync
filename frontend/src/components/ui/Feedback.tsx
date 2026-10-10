import { AlertCircle, Inbox, type LucideIcon } from "lucide-react";
import type { ReactNode } from "react";

import { cn } from "../../lib/cn";
import { Button } from "./Button";

export function Skeleton({ className }: { className?: string }) {
  return <div aria-hidden="true" className={cn("skeleton rounded-[10px]", className)} />;
}

export interface EmptyStateProps {
  icon?: LucideIcon;
  title: string;
  description?: string;
  action?: ReactNode;
  className?: string;
}

/** Icon circle + one sentence + one action (06 §6, §9). */
export function EmptyState({ icon: Icon = Inbox, title, description, action, className }: EmptyStateProps) {
  return (
    <div className={cn("flex flex-col items-center gap-3 px-6 py-12 text-center", className)}>
      <span className="grid size-12 place-items-center rounded-pill bg-neutral-bg text-neutral-fg">
        <Icon size={20} strokeWidth={1.75} aria-hidden="true" />
      </span>
      <p className="text-h3 text-ink-950">{title}</p>
      {description ? <p className="max-w-sm text-small text-ink-500">{description}</p> : null}
      {action}
    </div>
  );
}

export function ErrorState({
  title = "Couldn't load this. Check your connection and retry.",
  onRetry,
  className,
}: {
  title?: string;
  onRetry?: () => void;
  className?: string;
}) {
  return (
    <div role="alert" className={cn("flex flex-col items-center gap-3 px-6 py-12 text-center", className)}>
      <span className="grid size-12 place-items-center rounded-pill bg-rose-bg text-rose-fg">
        <AlertCircle size={20} strokeWidth={1.75} aria-hidden="true" />
      </span>
      <p className="max-w-sm text-body text-ink-900">{title}</p>
      {onRetry ? (
        <Button surface="paper" size="sm" onClick={onRetry}>
          Retry
        </Button>
      ) : null}
    </div>
  );
}
