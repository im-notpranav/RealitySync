import { Search } from "lucide-react";
import { useState } from "react";
import { useNavigate } from "react-router-dom";

import {
  Avatar,
  Card,
  DataTable,
  EmptyState,
  ErrorState,
  Input,
  PageHeader,
  Pill,
  RiskBadge,
  SeverityBadge,
  SystemChip,
} from "../../components/ui";
import { useEntities } from "../../lib/api/queries";
import type { Health } from "../../lib/api/types";
import { relativeTime } from "../../lib/format";

export const healthPill: Record<Health, { label: string; tone: "moss" | "peach" | "neutral" }> = {
  consistent: { label: "Consistent", tone: "moss" },
  inconsistent: { label: "Inconsistent", tone: "peach" },
  unknown: { label: "Unknown", tone: "neutral" },
};

const riskRank = { low: 0, watch: 1, warning: 2, critical: 3 } as const;

export function Component() {
  const [q, setQ] = useState("");
  const navigate = useNavigate();
  const { data, isLoading, isError, refetch } = useEntities(q);

  return (
    <>
      <PageHeader title="Customers" subtitle="Every customer as CRM, Billing and Support describe them" />
      <div className="mb-4 flex items-center gap-2">
        <div className="relative w-full sm:w-80">
          <Search size={16} aria-hidden="true" className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-ink-500" />
          <Input
            surface="glass"
            type="search"
            aria-label="Search customers"
            placeholder="Name or email"
            value={q}
            onChange={(event) => setQ(event.target.value)}
            className="pl-9"
          />
        </div>
        <p className="ml-auto text-small tabular text-ink-500" aria-live="polite">
          {data ? `${data.length} customers` : ""}
        </p>
      </div>
      <Card className="overflow-hidden p-0">
        {isError ? (
          <ErrorState title="Couldn't load customers. Check your connection and retry." onRetry={() => void refetch()} />
        ) : (
          <DataTable
            caption="Customers"
            rows={data}
            loading={isLoading}
            rowKey={(e) => e.id}
            rowLabel={(e) => `Open customer ${e.canonical_name}`}
            onRowClick={(e) => navigate(`/entities/${e.id}`)}
            defaultSort={{ key: "risk", dir: "desc" }}
            empty={<EmptyState title="No customers match" description="Try a different name or email." />}
            columns={[
              {
                key: "name",
                header: "Customer",
                sortValue: (e) => e.canonical_name,
                cell: (e) => (
                  <div className="flex min-w-0 items-center gap-3">
                    <Avatar name={e.canonical_name} size="sm" />
                    <div className="min-w-0">
                      <p className="truncate font-medium text-ink-950">{e.canonical_name}</p>
                      <p className="truncate text-small text-ink-500">{e.canonical_email}</p>
                    </div>
                  </div>
                ),
              },
              {
                key: "health",
                header: "Health",
                cell: (e) => <Pill tone={healthPill[e.health].tone}>{healthPill[e.health].label}</Pill>,
                hideBelow: "md",
              },
              {
                key: "risk",
                header: "Risk",
                sortValue: (e) => (e.risk ? riskRank[e.risk.level] * 10 + e.risk.score : -1),
                cell: (e) => (e.risk ? <RiskBadge level={e.risk.level} confidence={e.risk.confidence} /> : <Pill>Not assessed</Pill>),
              },
              {
                key: "findings",
                header: "Open findings",
                sortValue: (e) => e.open_findings_count,
                cell: (e) => (
                  <span className="inline-flex items-center gap-2">
                    <span className="tabular font-medium">{e.open_findings_count}</span>
                    {e.highest_severity ? <SeverityBadge severity={e.highest_severity} /> : null}
                  </span>
                ),
              },
              {
                key: "systems",
                header: "Systems",
                hideBelow: "xl",
                cell: (e) => (
                  <div className="flex gap-1">
                    {e.systems.map((s) => (
                      <SystemChip key={s} system={s} />
                    ))}
                  </div>
                ),
              },
              {
                key: "updated",
                header: "Updated",
                hideBelow: "lg",
                sortValue: (e) => new Date(e.updated_at).getTime(),
                cell: (e) => <span className="text-small tabular text-ink-500">{relativeTime(e.updated_at)}</span>,
              },
            ]}
          />
        )}
      </Card>
    </>
  );
}
