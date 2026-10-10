import { ArrowLeft, Download, Info, Rewind } from "lucide-react";
import { Link, useParams } from "react-router-dom";

import {
  Button,
  ButtonLink,
  Card,
  EmptyState,
  ErrorState,
  PageHeader,
  ProgressBar,
  ReplayChart,
  RiskBadge,
  SignalBars,
  Skeleton,
  toast,
  TrailView,
} from "../../components/ui";
import { useCheckpoints, useInvestigation } from "../../lib/api/queries";
import { formatDate, formatDuration, formatNumber, formatShortDate } from "../../lib/format";
import { useFirstVisit } from "../../lib/motion";

function Stat({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <Card>
      <p className="text-small text-ink-500">{label}</p>
      <p className="mt-3 text-kpi tabular text-ink-950">{value}</p>
      {sub ? <p className="mt-1 text-small text-ink-500">{sub}</p> : null}
    </Card>
  );
}

/** Investigation result (06 §7.8): outcome sentence, non-dismissible caveat, replay chart, the crossing. */
export function Component() {
  const { id = "" } = useParams();
  const investigation = useInvestigation(id);
  const checkpoints = useCheckpoints(id);
  const animate = useFirstVisit(`investigation-${id}`);

  if (investigation.isError) return <ErrorState onRetry={() => void investigation.refetch()} />;
  if (investigation.isLoading)
    return (
      <div className="flex flex-col gap-4 pt-3">
        <Skeleton className="h-12 w-80" />
        <Skeleton className="h-72 w-full" />
      </div>
    );
  const inv = investigation.data;
  if (!inv)
    return (
      <Card className="mt-6">
        <EmptyState
          title="Investigation not found"
          action={
            <ButtonLink to="/investigations" surface="paper">
              All investigations
            </ButtonLink>
          }
        />
      </Card>
    );

  const kind = inv.incident.kind === "churn" ? "churn" : "finding";
  const back = (
    <Link
      to="/investigations"
      className="mt-1 inline-flex items-center gap-1 text-small text-ink-500 transition-colors duration-fast pointer:hover:text-ink-950"
    >
      <ArrowLeft size={14} aria-hidden="true" /> Investigations
    </Link>
  );

  if (inv.status === "running" || inv.status === "queued") {
    const { checkpoints_done: done, checkpoints_total: total } = inv.progress;
    return (
      <>
        {back}
        <PageHeader
          title={`${inv.entity_name} — ${kind}`}
          subtitle="Replaying what RealitySync could have known…"
        />
        <Card className="flex flex-col gap-4">
          <p className="flex items-center gap-2 text-body text-ink-950">
            <span aria-hidden="true" className="live-dot size-2 rounded-pill bg-moss-500" />
            Checkpoint {formatNumber(done)} of {formatNumber(total)}
          </p>
          <ProgressBar value={done / total} label="Replay progress" animate />
          <p className="text-small text-ink-500">
            Each checkpoint rebuilds the customer from data recorded by then and runs today's rules. This page
            updates when the replay finishes.
          </p>
        </Card>
      </>
    );
  }

  const crossed = inv.outcome === "crossed";
  const outcome = crossed
    ? `RealitySync could have flagged this ${formatDuration(inv.lead_time_hours ?? 0)} before the incident`
    : "With the data recorded before the incident, RealitySync would not have flagged this";

  return (
    <>
      {back}
      <PageHeader
        title={`${inv.entity_name} — ${kind}`}
        subtitle={outcome}
        actions={
          <>
            <Button
              onClick={() =>
                toast({ title: "Export started", description: "The export always includes the caveat." })
              }
            >
              <Download size={16} aria-hidden="true" />
              Export
            </Button>
            {crossed && inv.first_detectable_at ? (
              <ButtonLink
                to={`/entities/${inv.entity_id}?at=${encodeURIComponent(inv.first_detectable_at)}`}
                variant="primary"
              >
                <Rewind size={16} aria-hidden="true" />
                Open at the crossing
              </ButtonLink>
            ) : null}
          </>
        }
      />

      {/* The caveat is always shown, unedited and not collapsible (FR-INV-005). */}
      <Card className="mb-6 flex gap-3 shadow-[inset_3px_0_0_var(--amber-fg),var(--shadow-card)]">
        <Info size={18} aria-hidden="true" className="mt-0.5 shrink-0 text-amber-fg" />
        <p className="max-w-[80ch] text-small text-ink-700">{inv.caveat}</p>
      </Card>

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <Stat
          label="Lead time"
          value={inv.lead_time_hours !== null ? formatDuration(inv.lead_time_hours) : "—"}
          sub={crossed ? "before the incident" : "threshold not reached"}
        />
        <Stat
          label="First detectable"
          value={inv.first_detectable_at ? formatShortDate(inv.first_detectable_at) : "—"}
          sub={
            inv.first_detectable_at
              ? `${new Date(inv.first_detectable_at).getFullYear()} · risk ≥ ${inv.warning_threshold.toFixed(2)}`
              : "threshold not reached"
          }
        />
        <Stat
          label="Incident"
          value={formatShortDate(inv.incident.at)}
          sub={`${new Date(inv.incident.at).getFullYear()} · ${kind === "churn" ? "first recorded churn" : "finding noticed"}`}
        />
        <Stat
          label="Checkpoints replayed"
          value={formatNumber(inv.progress.checkpoints_total)}
          sub={`Look back ${inv.lookback_days} days · rule set ${inv.rule_set_hash}`}
        />
      </div>

      <Card className="mt-4">
        <div className="mb-2 flex flex-wrap items-center justify-between gap-3">
          <h2 className="text-h3 text-ink-950">Risk over time</h2>
          <p className="text-caption font-normal text-ink-500">
            Each point is the customer as recorded on that day, scored with today's rules
          </p>
        </div>
        {checkpoints.data ? (
          <ReplayChart
            checkpoints={checkpoints.data}
            threshold={inv.warning_threshold}
            crossingAt={inv.first_detectable_at}
            animate={animate}
          />
        ) : (
          <Skeleton className="h-[260px] w-full" />
        )}
      </Card>

      {crossed && inv.at_crossing ? (
        <div className="mt-4 grid gap-4 lg:grid-cols-12">
          <Card className="lg:col-span-5">
            <div className="flex items-center justify-between gap-2">
              <h2 className="text-h3 text-ink-950">At the crossing</h2>
              <RiskBadge level={inv.at_crossing.risk.level} confidence={inv.at_crossing.risk.confidence} />
            </div>
            <p className="mt-3 text-kpi tabular text-ink-950">{inv.at_crossing.risk.score.toFixed(3)}</p>
            <p className="mb-5 text-small text-ink-500">
              Risk score on {inv.first_detectable_at ? formatDate(inv.first_detectable_at) : "—"}
            </p>
            <SignalBars risk={inv.at_crossing.risk} />
          </Card>
          <Card className="lg:col-span-7">
            <h2 className="mb-4 text-h3 text-ink-950">Why — the evidence trail</h2>
            <TrailView trail={inv.at_crossing.risk.trail} />
          </Card>
        </div>
      ) : null}
    </>
  );
}
