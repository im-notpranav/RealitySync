import { RotateCcw } from "lucide-react";
import { useState } from "react";

import { RoleGate } from "../../components/RoleGate";
import {
  Button,
  Card,
  DataTable,
  EmptyState,
  PageHeader,
  Pill,
  SectionHeader,
  Skeleton,
  Slider,
  SystemChip,
  toast,
} from "../../components/ui";
import { useFailedEvents, useSourceSystems } from "../../lib/api/queries";
import type { SourceSystem } from "../../lib/api/types";
import { formatNumber, humanize, relativeTime } from "../../lib/format";

function SystemCard({ system }: { system: SourceSystem }) {
  const [reliability, setReliability] = useState(system.reliability_weight);
  const quiet = system.last_event_at && Date.now() - new Date(system.last_event_at).getTime() > 86_400_000;
  return (
    <Card className="flex flex-col gap-4">
      <div className="flex items-center justify-between gap-2">
        <SystemChip system={system.key} />
        {quiet ? (
          <Pill tone="amber">No data for {relativeTime(system.last_event_at!).replace(" ago", "")}</Pill>
        ) : (
          <Pill tone="moss" dot>
            Receiving data
          </Pill>
        )}
      </div>
      <p className="text-small text-ink-500">
        {Object.entries(system.record_counts)
          .map(([type, count]) => `${formatNumber(count)} ${type}s`)
          .join(" · ")}
      </p>
      <div>
        <p className="mb-1.5 text-small font-medium text-ink-700">Reliability</p>
        <Slider label={`${system.name} reliability`} value={reliability} onValueChange={setReliability} />
      </div>
      <div>
        <p className="mb-2 text-small font-medium text-ink-700">Field authority</p>
        <ul className="flex flex-col gap-2">
          {Object.entries(system.field_authority).map(([field, value]) => (
            <li key={field} className="grid grid-cols-[96px_1fr_36px] items-center gap-3">
              <span className="text-small text-ink-500">{humanize(field)}</span>
              <span className="h-1.5 overflow-hidden rounded-pill bg-ink-200">
                <span className="block h-full rounded-pill bg-ink-950" style={{ width: `${value * 100}%` }} />
              </span>
              <span className="text-right text-small tabular text-ink-900">{value.toFixed(2)}</span>
            </li>
          ))}
        </ul>
      </div>
    </Card>
  );
}

export function Component() {
  const systems = useSourceSystems();
  const failed = useFailedEvents();
  return (
    <RoleGate min="admin" title="Systems">
      <PageHeader
        title="Systems"
        subtitle="Source systems, how much each is trusted per field, and events that failed to process"
      />
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {systems.isLoading
          ? Array.from({ length: 3 }, (_, i) => <Skeleton key={i} className="h-80" />)
          : null}
        {systems.data?.map((system) => (
          <SystemCard key={system.key} system={system} />
        ))}
      </div>
      <div className="mt-8">
        <SectionHeader title="Failed events" />
        <Card className="overflow-hidden p-0">
          <DataTable
            caption="Failed ingest events"
            rows={failed.data}
            loading={failed.isLoading}
            rowKey={(e) => e.id}
            empty={<EmptyState title="No failed events" description="Every event was processed." />}
            columns={[
              { key: "source", header: "System", cell: (e) => <SystemChip system={e.source} /> },
              {
                key: "record",
                header: "Record",
                cell: (e) => (
                  <span className="text-small text-ink-900">
                    {humanize(e.record_type)} <span className="tabular text-ink-500">{e.external_id}</span>
                  </span>
                ),
              },
              {
                key: "error",
                header: "Error",
                cell: (e) => <span className="text-small text-rose-fg">{e.error}</span>,
              },
              {
                key: "attempts",
                header: "Attempts",
                hideBelow: "md",
                cell: (e) => <span className="tabular">{e.attempts}</span>,
              },
              {
                key: "retry",
                header: "",
                cell: (e) => (
                  <Button
                    size="sm"
                    surface="paper"
                    onClick={() => toast({ title: "Event queued again", description: e.external_id })}
                  >
                    <RotateCcw size={14} aria-hidden="true" /> Retry
                  </Button>
                ),
              },
            ]}
          />
        </Card>
      </div>
    </RoleGate>
  );
}
