import { Clock } from "lucide-react";

import { ConfidenceMeter, Pill, SeverityBadge, StatusPill, SystemChip, type Column } from "../../components/ui";
import type { FindingListItem } from "../../lib/api/types";
import { relativeTime } from "../../lib/format";

const severityRank = { low: 1, medium: 2, high: 3, critical: 4 } as const;

export const findingColumns: Column<FindingListItem>[] = [
  {
    key: "severity",
    header: "Severity",
    cell: (f) => <SeverityBadge severity={f.severity} />,
    sortValue: (f) => severityRank[f.severity],
    className: "w-[120px]",
  },
  {
    key: "title",
    header: "Finding",
    cell: (f) => (
      <div className="min-w-0">
        <p className="truncate font-medium text-ink-950">{f.title}</p>
        <p className="truncate text-small text-ink-500">
          {f.rule_key} · {f.entity_name}
        </p>
      </div>
    ),
  },
  {
    key: "systems",
    header: "Systems",
    cell: (f) => (
      <div className="flex gap-1">
        {f.systems.map((s) => (
          <SystemChip key={s} system={s} />
        ))}
      </div>
    ),
    hideBelow: "xl",
  },
  {
    key: "confidence",
    header: "Confidence",
    cell: (f) => <ConfidenceMeter value={f.confidence} />,
    sortValue: (f) => f.confidence,
    hideBelow: "md",
  },
  {
    key: "detected",
    header: "Detected",
    cell: (f) => (
      <span className="inline-flex items-center gap-1.5 text-small tabular text-ink-500">
        {relativeTime(f.first_detected_at)}
        {f.sla_breached ? (
          <Pill tone="rose" icon={<Clock size={11} aria-hidden="true" />} title="SLA breached">
            SLA
          </Pill>
        ) : null}
      </span>
    ),
    sortValue: (f) => new Date(f.first_detected_at).getTime(),
    hideBelow: "lg",
  },
  { key: "status", header: "Status", cell: (f) => <StatusPill status={f.status} /> },
];
