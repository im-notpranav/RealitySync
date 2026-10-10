import { ChevronRight, type LucideIcon } from "lucide-react";
import { animate, motion, useReducedMotion } from "motion/react";
import { useEffect, useState, type ReactNode } from "react";
import { Link } from "react-router-dom";

import { cn } from "../../lib/cn";
import { EASE_OUT } from "../../lib/motion";
import { Card } from "./Card";
import { Skeleton } from "./Feedback";

// ------------------------------------------------------------------ count-up

/** Counts up once on the first load (700 ms ease-out); later changes and reduced motion show the value directly. */
export function CountUp({
  value,
  format = (v) => Math.round(v).toString(),
  animate: shouldAnimate = false,
}: {
  value: number;
  format?: (value: number) => string;
  animate?: boolean;
}) {
  const reduce = useReducedMotion();
  const [display, setDisplay] = useState(() => (shouldAnimate && !reduce ? 0 : value));

  useEffect(() => {
    if (!shouldAnimate || reduce) {
      setDisplay(value);
      return;
    }
    const controls = animate(0, value, { duration: 0.7, ease: EASE_OUT, onUpdate: setDisplay });
    return () => controls.stop();
    // Count up only once, for the first value we were given.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [shouldAnimate, reduce]);

  useEffect(() => {
    if (!shouldAnimate) setDisplay(value);
  }, [value, shouldAnimate]);

  return (
    <>
      <span aria-hidden="true">{format(display)}</span>
      <span className="sr-only">{format(value)}</span>
    </>
  );
}

// ------------------------------------------------------------------ progress

/** Moss fill; grows from the left on first view via clip-path so the rounded end keeps its shape. */
export function ProgressBar({
  value,
  label,
  animate: shouldAnimate = false,
  className,
}: {
  value: number;
  label: string;
  animate?: boolean;
  className?: string;
}) {
  const clamped = Math.max(0, Math.min(1, value));
  const visible = `inset(0 ${100 - clamped * 100}% 0 0 round 999px)`;
  return (
    <div
      role="progressbar"
      aria-label={label}
      aria-valuemin={0}
      aria-valuemax={100}
      aria-valuenow={Math.round(clamped * 100)}
      className={cn("h-2 w-full overflow-hidden rounded-pill bg-ink-200", className)}
    >
      <motion.div
        className="h-full w-full rounded-pill bg-moss-500"
        initial={shouldAnimate ? { clipPath: "inset(0 100% 0 0 round 999px)" } : false}
        animate={{ clipPath: visible }}
        transition={{ duration: 0.7, ease: EASE_OUT }}
      />
    </div>
  );
}

// ------------------------------------------------------------------ KPI card

export interface KpiCardProps {
  label: string;
  value: number | null | undefined;
  format?: (value: number) => string;
  chip?: ReactNode;
  sub?: ReactNode;
  progress?: { value: number; label: string };
  animate?: boolean;
  loading?: boolean;
}

/** One big number, a label, one context line, at most one chip (06 §1.3). */
export function KpiCard({
  label,
  value,
  format,
  chip,
  sub,
  progress,
  animate: shouldAnimate,
  loading,
}: KpiCardProps) {
  return (
    <Card className="flex min-h-[148px] flex-col">
      <div className="flex items-start justify-between gap-3">
        <p className="text-small text-ink-500">{label}</p>
        {!loading ? chip : null}
      </div>
      {loading || value === undefined ? (
        <>
          <Skeleton className="mt-4 h-9 w-28" />
          <Skeleton className="mt-3 h-3.5 w-36" />
        </>
      ) : (
        <>
          <p className="mt-3 text-kpi tabular text-ink-950">
            {value === null ? "—" : <CountUp value={value} format={format} animate={shouldAnimate} />}
          </p>
          {sub ? <p className="mt-1 text-small text-ink-500">{sub}</p> : null}
          {progress ? (
            <ProgressBar
              value={progress.value}
              label={progress.label}
              animate={shouldAnimate}
              className="mt-auto"
            />
          ) : null}
        </>
      )}
    </Card>
  );
}

// ------------------------------------------------------------------ section header

export function SectionHeader({ title, action, id }: { title: string; action?: ReactNode; id?: string }) {
  return (
    <div className="mb-3 flex min-h-10 items-center justify-between gap-3">
      <h2 id={id} className="text-h2 text-ink-950">
        {title}
      </h2>
      {action}
    </div>
  );
}

// ------------------------------------------------------------------ action list

export interface ActionItem {
  title: string;
  description: string;
  to: string;
  icon?: LucideIcon;
  badge?: ReactNode;
}

/** "Quick actions" list (06 §6): rows wash on hover; the chevron nudges right. */
export function ActionList({ items, label }: { items: ActionItem[]; label: string }) {
  return (
    <Card className="p-0">
      <ul aria-label={label} className="divide-y divide-ink-100">
        {items.map((item) => {
          const Icon = item.icon;
          return (
            <li key={item.title}>
              <Link
                to={item.to}
                className="group flex items-center gap-3 px-5 py-4 transition-colors duration-fast first:rounded-t-card last:rounded-b-card pointer:hover:bg-ink-100"
              >
                {Icon ? (
                  <span className="grid size-9 shrink-0 place-items-center rounded-pill bg-ink-100 text-ink-700 transition-colors duration-fast group-hover:bg-paper">
                    <Icon size={16} strokeWidth={1.75} aria-hidden="true" />
                  </span>
                ) : null}
                <span className="min-w-0 flex-1">
                  <span className="flex items-center gap-2 text-h3 text-ink-950">
                    {item.title}
                    {item.badge}
                  </span>
                  <span className="block truncate text-small text-ink-500">{item.description}</span>
                </span>
                <ChevronRight
                  size={16}
                  aria-hidden="true"
                  className="shrink-0 text-ink-500 transition-transform duration-fast ease-out motion-safe:group-hover:translate-x-0.5"
                />
              </Link>
            </li>
          );
        })}
      </ul>
    </Card>
  );
}
