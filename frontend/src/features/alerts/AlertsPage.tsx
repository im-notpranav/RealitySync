import { BellOff } from "lucide-react";
import { useMemo, useState } from "react";
import { Link } from "react-router-dom";

import { Button, Card, EmptyState, ErrorState, PageHeader, Select, SeverityBadge, Skeleton } from "../../components/ui";
import { useAlerts } from "../../lib/api/queries";
import type { Alert } from "../../lib/api/types";
import { cn } from "../../lib/cn";
import { formatDate, humanize, relativeTime } from "../../lib/format";

function dayLabel(iso: string): string {
  const date = new Date(iso);
  const today = new Date();
  const yesterday = new Date(Date.now() - 86_400_000);
  if (date.toDateString() === today.toDateString()) return "Today";
  if (date.toDateString() === yesterday.toDateString()) return "Yesterday";
  return formatDate(iso);
}

function href(alert: Alert) {
  if (alert.finding_id) return `/findings?finding=${alert.finding_id}`;
  if (alert.link_id) return "/review";
  return alert.entity_id ? `/entities/${alert.entity_id}` : "/alerts";
}

export function Component() {
  const { data, isLoading, isError, refetch } = useAlerts();
  const [type, setType] = useState("all");
  const [read, setRead] = useState<ReadonlySet<string>>(new Set());

  const groups = useMemo(() => {
    const filtered = (data ?? []).filter((a) => type === "all" || a.type === type);
    const map = new Map<string, Alert[]>();
    for (const alert of filtered) {
      const label = dayLabel(alert.created_at);
      map.set(label, [...(map.get(label) ?? []), alert]);
    }
    return [...map.entries()];
  }, [data, type]);

  return (
    <>
      <PageHeader
        title="Alerts"
        subtitle="Everything RealitySync flagged, newest first"
        actions={<Button onClick={() => setRead(new Set((data ?? []).map((a) => a.id)))}>Mark all as read</Button>}
      />
      <div className="mb-4">
        <Select
          surface="glass"
          label="Alert type"
          value={type}
          onValueChange={setType}
          className="w-56"
          options={[
            { value: "all", label: "All alerts" },
            { value: "finding_created", label: "New findings" },
            { value: "risk_threshold_crossed", label: "Risk changes" },
            { value: "link_needs_review", label: "Links to review" },
            { value: "finding_resolved", label: "Resolved" },
          ]}
        />
      </div>
      {isError ? <ErrorState onRetry={() => void refetch()} /> : null}
      {isLoading ? <Skeleton className="h-72 w-full" /> : null}
      {data && groups.length === 0 ? (
        <Card>
          <EmptyState icon={BellOff} title="No alerts" description="You're all caught up." />
        </Card>
      ) : null}
      <div className="flex flex-col gap-6">
        {groups.map(([label, alerts]) => (
          <section key={label} aria-label={label}>
            <h2 className="mb-2 text-small font-medium text-ink-500">{label}</h2>
            <Card className="p-0">
              <ul className="divide-y divide-ink-100">
                {alerts.map((alert) => {
                  const unread = !alert.is_read && !read.has(alert.id);
                  return (
                    <li key={alert.id}>
                      <Link
                        to={href(alert)}
                        className="flex items-center gap-4 px-5 py-4 transition-colors duration-fast first:rounded-t-card last:rounded-b-card pointer:hover:bg-ink-100"
                      >
                        <span
                          aria-label={unread ? "Unread" : undefined}
                          className={cn("size-2 shrink-0 rounded-pill", unread ? "bg-moss-500" : "bg-transparent")}
                        />
                        <SeverityBadge severity={alert.severity} />
                        <span className="min-w-0 flex-1">
                          <span className={cn("block truncate text-body text-ink-950", unread && "font-semibold")}>{alert.title}</span>
                          <span className="block truncate text-small text-ink-500">
                            {humanize(alert.type)} · {alert.body}
                          </span>
                        </span>
                        <span className="shrink-0 text-small tabular text-ink-500">{relativeTime(alert.created_at)}</span>
                      </Link>
                    </li>
                  );
                })}
              </ul>
            </Card>
          </section>
        ))}
      </div>
    </>
  );
}
