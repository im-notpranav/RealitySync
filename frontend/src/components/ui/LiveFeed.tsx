import { AlertTriangle, CheckCircle2, Gauge, GitCompareArrows, TrendingUp } from "lucide-react";
import { AnimatePresence, motion } from "motion/react";
import { Link } from "react-router-dom";

import type { Alert } from "../../lib/api/types";
import { cn } from "../../lib/cn";
import { relativeTime } from "../../lib/format";
import { EASE_OUT } from "../../lib/motion";
import { severityTone, type Tone } from "./Badges";
import { Card } from "./Card";
import { Skeleton } from "./Feedback";

const typeIcon = {
  finding_created: AlertTriangle,
  finding_escalated: TrendingUp,
  finding_resolved: CheckCircle2,
  link_needs_review: GitCompareArrows,
  risk_threshold_crossed: Gauge,
} as const;

const toneCircle: Record<Tone, string> = {
  peach: "bg-peach-bg text-peach-fg",
  rose: "bg-rose-bg text-rose-fg",
  amber: "bg-amber-bg text-amber-fg",
  indigo: "bg-indigo-bg text-indigo-fg",
  sky: "bg-sky-bg text-sky-fg",
  moss: "bg-moss-bg text-moss-fg",
  neutral: "bg-neutral-bg text-neutral-fg",
};

function alertHref(alert: Alert): string {
  if (alert.finding_id) return `/findings?finding=${alert.finding_id}`;
  if (alert.link_id) return "/review";
  if (alert.entity_id) return `/entities/${alert.entity_id}`;
  return "/alerts";
}

export function LiveFeed({
  alerts,
  newIds,
  connected,
  loading,
  limit = 6,
}: {
  alerts: Alert[] | undefined;
  newIds: ReadonlySet<string>;
  connected: boolean;
  loading?: boolean;
  limit?: number;
}) {
  const unread = alerts?.filter((a) => !a.is_read).length ?? 0;
  return (
    <Card className="p-0">
      <div className="flex items-center justify-between gap-3 px-5 pb-2 pt-4">
        <h2 className="flex items-center gap-2 text-h3 text-ink-950">
          <span
            aria-hidden="true"
            className={cn("size-2 rounded-pill", connected ? "live-dot bg-moss-500" : "bg-ink-400")}
          />
          Live feed
        </h2>
        <span className="text-caption text-ink-500">{unread} unread</span>
      </div>
      <ul aria-live="polite" aria-label="Live alerts" className="px-2 pb-2">
        {loading || !alerts
          ? Array.from({ length: 4 }, (_, i) => (
              <li key={i} className="flex items-center gap-3 px-3 py-2.5">
                <Skeleton className="size-8 rounded-pill" />
                <Skeleton className="h-4 flex-1" />
              </li>
            ))
          : null}
        <AnimatePresence initial={false}>
          {alerts?.slice(0, limit).map((alert) => {
            const Icon = typeIcon[alert.type];
            const tone = alert.type === "finding_resolved" ? "moss" : severityTone[alert.severity];
            return (
              <motion.li
                key={alert.id}
                layout="position"
                initial={{ opacity: 0, transform: "translateY(-6px)" }}
                animate={{
                  opacity: 1,
                  transform: "translateY(0px)",
                  transition: { duration: 0.24, ease: EASE_OUT },
                }}
                exit={{ opacity: 0, transition: { duration: 0.15 } }}
              >
                <Link
                  to={alertHref(alert)}
                  className={cn(
                    "flex items-center gap-3 rounded-control px-3 py-2.5 transition-colors duration-fast pointer:hover:bg-ink-100",
                    newIds.has(alert.id) && "row-flash",
                  )}
                >
                  <span
                    className={cn("grid size-8 shrink-0 place-items-center rounded-pill", toneCircle[tone])}
                  >
                    <Icon size={15} strokeWidth={1.9} aria-hidden="true" />
                  </span>
                  <span className="min-w-0 flex-1">
                    <span
                      className={cn(
                        "block truncate text-small text-ink-950",
                        !alert.is_read && "font-semibold",
                      )}
                    >
                      {alert.title}
                    </span>
                    <span className="block truncate text-caption font-normal text-ink-500">{alert.body}</span>
                  </span>
                  <span className="shrink-0 text-caption font-normal tabular text-ink-500">
                    {relativeTime(alert.created_at)}
                  </span>
                </Link>
              </motion.li>
            );
          })}
        </AnimatePresence>
      </ul>
    </Card>
  );
}
