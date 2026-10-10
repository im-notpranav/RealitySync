import { ArrowLeft, Clock, History, Rewind, Unlink } from "lucide-react";
import { useEffect, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";

import {
  Button,
  ButtonLink,
  Card,
  EmptyState,
  ErrorState,
  PageHeader,
  Pill,
  RiskBadge,
  SeverityBadge,
  SignalBars,
  Skeleton,
  Slider,
  SystemChip,
  TrailView,
} from "../../components/ui";
import { useAsOf, useEntity, useEntityTimeline } from "../../lib/api/queries";
import type { Expectation, LinkStatus, RiskAssessment, SourceRecord, SystemKey } from "../../lib/api/types";
import { cn } from "../../lib/cn";
import { formatDate, formatDateTime, formatPercent, humanize, relativeTime, systemNames } from "../../lib/format";
import { hasRole, useSession } from "../../store/session";
import { healthPill } from "./CustomersPage";

const DAY = 86_400_000;
const RANGE_DAYS = 120;

const linkPill: Record<LinkStatus, { label: string; tone: "neutral" | "amber" | "moss" | "rose" }> = {
  auto_matched: { label: "Matched", tone: "neutral" },
  needs_review: { label: "Needs review", tone: "amber" },
  confirmed: { label: "Confirmed", tone: "moss" },
  rejected: { label: "Rejected", tone: "rose" },
};

interface RecordCard {
  record: SourceRecord;
  status: LinkStatus;
  confidence: number;
}

function SystemRecordCard({
  card,
  others,
  live,
}: {
  card: RecordCard;
  others: RecordCard[];
  /** In as-of mode: today's values, to mark what changed since. */
  live?: Record<string, string | null>;
}) {
  const { record } = card;
  return (
    <Card className="flex flex-col gap-3">
      <div className="flex items-center justify-between gap-2">
        <SystemChip system={record.system} />
        <Pill tone={linkPill[card.status].tone}>
          {linkPill[card.status].label} {card.status !== "needs_review" ? formatPercent(card.confidence) : ""}
        </Pill>
      </div>
      <p className="text-caption font-normal tabular text-ink-500">
        {record.external_id} · v{record.version} · recorded {relativeTime(record.source_updated_at)}
      </p>
      <dl className="flex flex-col divide-y divide-ink-100">
        {Object.entries(record.normalized).map(([key, value]) => {
          const differs = others.some((o) => key in o.record.normalized && o.record.normalized[key] && value && o.record.normalized[key] !== value);
          const changed = live && live[key] !== undefined && live[key] !== value;
          return (
            <div
              key={key}
              className={cn("flex items-baseline justify-between gap-3 py-2", differs && "-mx-2 rounded-[8px] bg-peach-bg px-2")}
            >
              <dt className="text-small text-ink-500">{humanize(key)}</dt>
              <dd className="flex items-center gap-1.5 truncate text-right text-small font-medium text-ink-950">
                {value ?? <span className="font-normal text-ink-400">—</span>}
                {changed ? <Pill tone="sky">changed since</Pill> : null}
              </dd>
            </div>
          );
        })}
      </dl>
    </Card>
  );
}

function RiskCard({ risk }: { risk: RiskAssessment | null }) {
  const [showTrail, setShowTrail] = useState(false);
  return (
    <Card>
      <div className="flex items-center justify-between gap-2">
        <h2 className="text-h3 text-ink-950">Risk</h2>
        {risk ? <RiskBadge level={risk.level} confidence={risk.confidence} /> : null}
      </div>
      {risk ? (
        <>
          <p className="mt-3 text-kpi tabular text-ink-950">{risk.score.toFixed(3)}</p>
          <p className="text-small text-ink-500">
            Score and confidence are separate: confidence {formatPercent(risk.confidence)} reflects how much of the
            evidence was available and fresh.
          </p>
          <div className="mt-5">
            <SignalBars risk={risk} />
          </div>
          <Button variant="ghost" size="sm" className="-ml-3 mt-4" onClick={() => setShowTrail((v) => !v)} aria-expanded={showTrail}>
            {showTrail ? "Hide evidence trail" : "Show evidence trail"}
          </Button>
          {showTrail ? (
            <div className="mt-3">
              <TrailView trail={risk.trail} />
            </div>
          ) : null}
        </>
      ) : (
        <p className="mt-3 text-small text-ink-500">Risk is assessed after the first detection run.</p>
      )}
    </Card>
  );
}

function ExpectationsCard({ expectations }: { expectations: Expectation[] }) {
  return (
    <Card>
      <h2 className="text-h3 text-ink-950">Waiting for evidence</h2>
      {expectations.length === 0 ? (
        <p className="mt-2 text-small text-ink-500">Nothing outstanding — every expected record has arrived.</p>
      ) : (
        <ul className="mt-3 flex flex-col gap-3">
          {expectations.map((e) => (
            <li key={`${e.rule_key}-${e.trigger_record_id}`} className="flex flex-col gap-1.5">
              <div className="flex flex-wrap items-center gap-2">
                <SystemChip system={e.system} />
                {e.outcome === "pending" ? (
                  <Pill tone="amber" icon={<Clock size={11} aria-hidden="true" />}>
                    Waiting until {formatDate(e.deadline)}
                  </Pill>
                ) : (
                  <Pill tone="neutral">Cannot assess</Pill>
                )}
              </div>
              <p className="text-small text-ink-700">
                Expected {humanize(e.expected.replace(".", " "))}
                {e.outcome === "cannot_assess"
                  ? ` — no ${systemNames[e.system]} data recorded since ${e.feed_watermark ? formatDate(e.feed_watermark) : "the start"}.`
                  : "."}
              </p>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}

/** Customer detail (06 §7.3) with the Time Machine as-of mode (06 §7.8). */
export function Component() {
  const { id = "" } = useParams();
  const [params, setParams] = useSearchParams();
  const at = params.get("at");
  const user = useSession((state) => state.user);
  const live = useEntity(id);
  const timeline = useEntityTimeline(id);
  const asOf = useAsOf(id, at);

  const daysFromAt = at ? Math.max(0, Math.round((Date.now() - new Date(at).getTime()) / DAY)) : 30;
  const [daysBack, setDaysBack] = useState(daysFromAt);
  useEffect(() => setDaysBack(daysFromAt), [daysFromAt]);

  function goTo(days: number) {
    setDaysBack(days);
    setParams({ at: new Date(Date.now() - days * DAY).toISOString() }, { replace: true });
  }

  if (live.isError) return <ErrorState onRetry={() => void live.refetch()} />;
  if (live.isLoading)
    return (
      <div className="flex flex-col gap-4 pt-3">
        <Skeleton className="h-12 w-72" />
        <Skeleton className="h-64 w-full" />
      </div>
    );
  const d = live.data;
  if (!d)
    return (
      <Card className="mt-6">
        <EmptyState title="Customer not found" action={<ButtonLink to="/entities" surface="paper">Back to customers</ButtonLink>} />
      </Card>
    );

  const view = at ? asOf.data : null;
  const cards: RecordCard[] = view
    ? view.records.map((r) => ({ record: r.record, status: r.link.status, confidence: r.link.match_confidence }))
    : d.records.map((r) => ({ record: r.record, status: r.link_status, confidence: r.match_confidence }));
  const liveBySystem = Object.fromEntries(d.records.map((r) => [r.record.system, r.record.normalized])) as Partial<
    Record<SystemKey, Record<string, string | null>>
  >;
  const risk = view ? view.risk : d.risk;
  const findings = view ? view.findings.map((f) => ({ id: f.live_finding_id ?? f.fingerprint, ...f })) : d.open_findings;

  return (
    <>
      <Link
        to="/entities"
        className="mt-1 inline-flex items-center gap-1 text-small text-ink-500 transition-colors duration-fast pointer:hover:text-ink-950"
      >
        <ArrowLeft size={14} aria-hidden="true" /> Customers
      </Link>
      <PageHeader
        title={d.canonical_name}
        subtitle={
          <span className="flex flex-wrap items-center gap-2">
            {d.canonical_email}
            <Pill tone={healthPill[d.health].tone}>{healthPill[d.health].label}</Pill>
            {d.risk ? <RiskBadge level={d.risk.level} confidence={d.risk.confidence} /> : null}
          </span>
        }
        actions={
          <>
            {at ? (
              <Button onClick={() => setParams({}, { replace: true })}>Back to now</Button>
            ) : (
              <Button onClick={() => goTo(30)}>
                <Rewind size={16} aria-hidden="true" />
                Open Time Machine
              </Button>
            )}
            {hasRole(user, "analyst") ? (
              <ButtonLink to={`/investigations?new=1&entity=${d.id}`} variant="primary">
                <History size={16} aria-hidden="true" />
                Investigate
              </ButtonLink>
            ) : null}
          </>
        }
      />

      {at ? (
        <section aria-label="Time Machine" className="on-dark glass-dark mb-6 rounded-card p-5 text-on-dark shadow-raised">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <p className="flex items-center gap-2 text-body font-medium">
              <Rewind size={16} aria-hidden="true" />
              Viewing as of {formatDateTime(new Date(Date.now() - daysBack * DAY).toISOString())} — data recorded by then,
              today's rules
            </p>
            <Pill tone="neutral" className="bg-white/10 text-on-dark">
              Rule set {view?.rule_set.hash ?? "…"}
            </Pill>
          </div>
          <div className="mt-4 [&_[role=slider]]:ring-white/40">
            <Slider
              label="Days back in time"
              value={RANGE_DAYS - daysBack}
              min={0}
              max={RANGE_DAYS}
              step={1}
              onValueChange={(v) => goTo(RANGE_DAYS - v)}
              format={(v) => (v === RANGE_DAYS ? "Today" : `${RANGE_DAYS - v} d ago`)}
            />
          </div>
          <p className="mt-3 text-caption font-normal text-on-dark-muted">{view?.caveat}</p>
        </section>
      ) : null}

      <div className="grid gap-4 lg:grid-cols-12">
        <div className="flex min-w-0 flex-col gap-4 lg:col-span-8">
          <div className={cn("grid gap-4 md:grid-cols-2 2xl:grid-cols-3", asOf.isFetching && "opacity-70 transition-opacity duration-fast")}>
            {cards.map((card) => (
              <SystemRecordCard
                key={card.record.id}
                card={card}
                others={cards.filter((c) => c !== card)}
                live={view ? liveBySystem[card.record.system] : undefined}
              />
            ))}
          </div>

          {view && view.not_yet_linkable.length > 0 ? (
            <Card className="bg-ink-100 shadow-none">
              <h2 className="flex items-center gap-2 text-h3 text-ink-950">
                <Unlink size={16} aria-hidden="true" /> Not yet linkable at this time
              </h2>
              <ul className="mt-2 flex flex-wrap gap-2">
                {view.not_yet_linkable.map((r) => (
                  <li key={r.record_id} className="flex items-center gap-2 text-small text-ink-700">
                    <SystemChip system={r.system} /> {r.external_id}
                  </li>
                ))}
              </ul>
              <p className="mt-2 text-caption font-normal text-ink-500">
                These records existed but did not yet match this customer with the data recorded by then.
              </p>
            </Card>
          ) : null}

          {!view ? (
            <Card>
              <h2 className="mb-3 text-h3 text-ink-950">Timeline</h2>
              <ol className="relative flex flex-col gap-4 border-l border-ink-200 pl-5">
                {(timeline.data ?? []).map((item) => (
                  <li key={`${item.at}-${item.external_id}`} className="relative">
                    <span aria-hidden="true" className="absolute -left-[25px] top-1.5 size-2.5 rounded-pill border-2 border-paper bg-ink-950" />
                    <div className="flex flex-wrap items-center gap-2">
                      <SystemChip system={item.system} />
                      <span className="text-small text-ink-950">{item.summary}</span>
                      {item.out_of_order ? <Pill tone="amber">Arrived out of order</Pill> : null}
                    </div>
                    <p className="mt-0.5 text-caption font-normal tabular text-ink-500">
                      {item.external_id} · {relativeTime(item.at)}
                    </p>
                  </li>
                ))}
              </ol>
            </Card>
          ) : null}
        </div>

        <div className="flex min-w-0 flex-col gap-4 lg:col-span-4">
          <RiskCard risk={risk ?? null} />
          <Card>
            <h2 className="text-h3 text-ink-950">{view ? "Findings at that time" : "Open findings"}</h2>
            {findings.length === 0 ? (
              <p className="mt-2 text-small text-ink-500">No findings.</p>
            ) : (
              <ul className="mt-3 flex flex-col divide-y divide-ink-100">
                {findings.map((f) => (
                  <li key={f.id}>
                    <Link
                      to={`/findings?finding=${f.id}`}
                      className="-mx-2 flex items-center gap-2 rounded-[8px] px-2 py-2.5 transition-colors duration-fast pointer:hover:bg-ink-100"
                    >
                      <SeverityBadge severity={f.severity} />
                      <span className="min-w-0 flex-1 truncate text-small text-ink-950">{f.title}</span>
                      <span className="text-caption tabular text-ink-500">{f.rule_key}</span>
                    </Link>
                  </li>
                ))}
              </ul>
            )}
          </Card>
          <ExpectationsCard expectations={view ? view.expectations : d.expectations} />
        </div>
      </div>
    </>
  );
}
