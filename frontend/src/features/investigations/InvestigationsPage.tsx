import { Plus } from "lucide-react";
import { useNavigate, useSearchParams } from "react-router-dom";

import {
  Button,
  Card,
  DataTable,
  EmptyState,
  ErrorState,
  PageHeader,
  Pill,
  ProgressBar,
} from "../../components/ui";
import { useInvestigations } from "../../lib/api/queries";
import type { Investigation } from "../../lib/api/types";
import { formatDate, formatDuration, relativeTime } from "../../lib/format";
import { hasRole, useSession } from "../../store/session";
import { NewInvestigationDialog } from "./NewInvestigationDialog";

export function OutcomePill({ investigation }: { investigation: Investigation }) {
  if (investigation.status === "running" || investigation.status === "queued") {
    const { checkpoints_done: done, checkpoints_total: total } = investigation.progress;
    return (
      <span className="flex w-36 flex-col gap-1">
        <span className="text-caption font-normal tabular text-ink-500">
          Replaying {done} of {total}
        </span>
        <ProgressBar value={done / total} label="Replay progress" />
      </span>
    );
  }
  if (investigation.status === "failed") return <Pill tone="rose">Failed</Pill>;
  return investigation.outcome === "crossed" ? (
    <Pill tone="peach" dot>
      Could have flagged
    </Pill>
  ) : (
    <Pill tone="neutral">Would not have flagged</Pill>
  );
}

export function Component() {
  const [params, setParams] = useSearchParams();
  const navigate = useNavigate();
  const user = useSession((state) => state.user);
  const { data, isLoading, isError, refetch } = useInvestigations();
  const dialogOpen = params.get("new") === "1" && hasRole(user, "analyst");

  return (
    <>
      <PageHeader
        title="Investigations"
        subtitle="Could RealitySync have known earlier? Replays of what was knowable before each incident."
        actions={
          hasRole(user, "analyst") ? (
            <Button variant="primary" onClick={() => setParams({ new: "1" })}>
              <Plus size={16} aria-hidden="true" />
              New investigation
            </Button>
          ) : null
        }
      />
      <Card className="overflow-hidden p-0">
        {isError ? (
          <ErrorState onRetry={() => void refetch()} />
        ) : (
          <DataTable
            caption="Investigations"
            rows={data}
            loading={isLoading}
            rowKey={(i) => i.id}
            rowLabel={(i) => `Open investigation for ${i.entity_name}`}
            onRowClick={(i) => navigate(`/investigations/${i.id}`)}
            empty={<EmptyState title="No investigations yet" description="Start one from a customer or with the button above." />}
            columns={[
              {
                key: "customer",
                header: "Customer",
                sortValue: (i) => i.entity_name,
                cell: (i) => <span className="font-medium text-ink-950">{i.entity_name}</span>,
              },
              {
                key: "incident",
                header: "Incident",
                cell: (i) => (
                  <span className="text-small text-ink-700">
                    {i.incident.kind === "churn" ? "Churn" : "Finding"} · {formatDate(i.incident.at)}
                  </span>
                ),
              },
              { key: "outcome", header: "Outcome", cell: (i) => <OutcomePill investigation={i} /> },
              {
                key: "lead",
                header: "Lead time",
                sortValue: (i) => i.lead_time_hours ?? -1,
                cell: (i) => (
                  <span className="tabular font-medium text-ink-950">
                    {i.lead_time_hours !== null ? formatDuration(i.lead_time_hours) : "—"}
                  </span>
                ),
              },
              {
                key: "started",
                header: "Started",
                hideBelow: "lg",
                sortValue: (i) => new Date(i.created_at).getTime(),
                cell: (i) => (
                  <span className="text-small text-ink-500">
                    {relativeTime(i.created_at)} by {i.requested_by}
                  </span>
                ),
              },
            ]}
          />
        )}
      </Card>
      <NewInvestigationDialog
        open={dialogOpen}
        onOpenChange={(open) => !open && setParams({}, { replace: true })}
        defaultEntityId={params.get("entity")}
      />
    </>
  );
}
