import { ArrowLeft } from "lucide-react";
import { Link, useParams } from "react-router-dom";

import { RoleGate } from "../../components/RoleGate";
import { Card, KpiCard, PageHeader, Pill, ProgressBar, SectionHeader, Skeleton } from "../../components/ui";
import { useEvaluation } from "../../lib/api/queries";
import { formatPercent, humanize } from "../../lib/format";
import { useFirstVisit } from "../../lib/motion";

function Target({ ok, label }: { ok: boolean; label: string }) {
  return <Pill tone={ok ? "moss" : "rose"}>{ok ? `Meets ${label}` : `Below ${label}`}</Pill>;
}

export function Component() {
  const { runId = "" } = useParams();
  const { data, isLoading } = useEvaluation(runId);
  const animate = useFirstVisit(`evaluation-${runId}`);
  const pct = (v: number) => `${(v * 100).toFixed(1)}%`;

  return (
    <RoleGate min="admin" title="Evaluation">
      <Link
        to="/simulation"
        className="mt-1 inline-flex items-center gap-1 text-small text-ink-500 transition-colors duration-fast pointer:hover:text-ink-950"
      >
        <ArrowLeft size={14} aria-hidden="true" /> Simulation
      </Link>
      <PageHeader
        title="Evaluation"
        subtitle={`How well RealitySync found what was injected in run ${runId}`}
      />
      {isLoading || !data ? (
        <Skeleton className="h-64 w-full" />
      ) : (
        <>
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <KpiCard
              label="Precision"
              value={data.precision}
              format={pct}
              animate={animate}
              chip={<Target ok={data.precision >= 0.9} label="0.90" />}
              sub={`${data.true_positives} true · ${data.false_positives} false positives`}
            />
            <KpiCard
              label="Recall"
              value={data.recall}
              format={pct}
              animate={animate}
              chip={<Target ok={data.recall >= 0.85} label="0.85" />}
              sub={`${data.false_negatives} missed · ${data.ignored} ignored`}
            />
            <KpiCard
              label="F1"
              value={data.f1}
              format={(v) => v.toFixed(3)}
              animate={animate}
              sub="Harmonic mean of precision and recall"
            />
            <KpiCard
              label="Matching precision"
              value={data.matching.auto_precision}
              format={pct}
              animate={animate}
              sub={`Recall ${pct(data.matching.recall_auto_or_review)} over ${data.matching.true_pairs} true pairs`}
            />
          </div>

          <div className="mt-8 grid gap-4 lg:grid-cols-12">
            <section className="lg:col-span-7">
              <SectionHeader title="Investigations" />
              <Card className="grid gap-x-6 gap-y-4 sm:grid-cols-2">
                {[
                  ["Detected early (churn with signals)", data.investigation.detection_rate],
                  ["No false hindsight", data.investigation.no_false_hindsight_rate],
                  ["Lead time within a day", data.investigation.lead_time_within_1d_rate],
                  ["Signals without churn flagged", data.investigation.signals_without_churn_detection_rate],
                ].map(([label, value]) => (
                  <div key={label as string}>
                    <div className="mb-1.5 flex items-center justify-between gap-2">
                      <span className="text-small text-ink-700">{label}</span>
                      <span className="text-small font-medium tabular text-ink-950">
                        {formatPercent(value as number)}
                      </span>
                    </div>
                    <ProgressBar value={value as number} label={label as string} animate={animate} />
                  </div>
                ))}
                <div className="flex flex-wrap gap-2 sm:col-span-2">
                  <Pill tone="neutral">
                    Lead-time error {data.investigation.lead_time_mae_hours.toFixed(1)} h
                  </Pill>
                  <Pill tone={data.investigation.outage_missing_evidence_findings === 0 ? "moss" : "rose"}>
                    {data.investigation.outage_missing_evidence_findings} missing-evidence findings during
                    outage
                  </Pill>
                  <Pill tone={data.investigation.lookahead_violations === 0 ? "moss" : "rose"}>
                    {data.investigation.lookahead_violations} lookahead violations
                  </Pill>
                </div>
              </Card>
            </section>
            <section className="lg:col-span-5">
              <SectionHeader title="By issue type" />
              <Card>
                <ul className="flex flex-col gap-3">
                  {data.by_type.map((t) => (
                    <li key={t.issue_type}>
                      <div className="mb-1 flex items-center justify-between gap-2 text-small">
                        <span className="text-ink-700">{humanize(t.issue_type)}</span>
                        <span className="tabular text-ink-500">
                          {t.detected}/{t.injected}
                        </span>
                      </div>
                      <ProgressBar
                        value={t.recall}
                        label={`${humanize(t.issue_type)} recall`}
                        animate={animate}
                      />
                    </li>
                  ))}
                </ul>
              </Card>
            </section>
          </div>
        </>
      )}
    </RoleGate>
  );
}
