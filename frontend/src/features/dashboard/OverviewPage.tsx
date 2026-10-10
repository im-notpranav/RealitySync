import { Download, FlaskConical, GitCompareArrows, History, Plus, Rewind, Sparkles } from "lucide-react";
import { motion } from "motion/react";
import { useSearchParams } from "react-router-dom";

import {
  ActionList,
  Button,
  ButtonLink,
  Card,
  DataTable,
  EmptyState,
  ErrorState,
  KpiCard,
  LiveFeed,
  PageHeader,
  Pill,
  SectionHeader,
  Skeleton,
  SystemChip,
  toast,
  TrendChart,
  type ActionItem,
} from "../../components/ui";
import { useAlerts, useDashboardSummary, useFindings, useSystemHealth, useTrends } from "../../lib/api/queries";
import { env } from "../../lib/env";
import { formatNumber, relativeTime, todayLabel } from "../../lib/format";
import { rise, stagger, useFirstVisit } from "../../lib/motion";
import { hasRole, useSession } from "../../store/session";
import { FindingDrawer } from "../findings/FindingDrawer";
import { findingColumns } from "../findings/findingColumns";
import { useDemoLiveAlerts } from "./useDemoLiveAlerts";

function freshness(lastEventAt: string | null) {
  if (!lastEventAt) return <Pill tone="neutral">No data yet</Pill>;
  const age = Date.now() - new Date(lastEventAt).getTime();
  if (age < 60 * 60_000) return <Pill tone="moss" dot>Fresh</Pill>;
  if (age < 24 * 60 * 60_000) return <Pill tone="amber">Quiet</Pill>;
  return <Pill tone="amber">No data for {relativeTime(lastEventAt).replace(" ago", "")}</Pill>;
}

// The overview card is narrower than the Findings page: systems are shown in the drawer instead.
const overviewColumns = findingColumns.filter((column) => column.key !== "systems");

const thirtyDaysAgo = () => new Date(Date.now() - 30 * 86_400_000).toISOString();

/** Overview (06 §7.1): the reference layout mapped to consistency content. */
export function Component() {
  const animate = useFirstVisit("overview");
  const user = useSession((state) => state.user);
  const [params, setParams] = useSearchParams();
  const summary = useDashboardSummary();
  const trends = useTrends();
  const health = useSystemHealth();
  const findings = useFindings({ status: "active" });
  const alerts = useAlerts();
  const newAlertIds = useDemoLiveAlerts();

  const s = summary.data;
  const actions: ActionItem[] = [
    {
      title: "Start an investigation",
      description: "Could we have known about a churn earlier?",
      to: "/investigations?new=1",
      icon: History,
    },
    {
      title: "Open the Time Machine",
      description: "See a customer as the data stood on any day",
      to: `/entities/e-02?at=${encodeURIComponent(thirtyDaysAgo())}`,
      icon: Rewind,
    },
    ...(hasRole(user, "analyst")
      ? [
          {
            title: "Review links",
            description: "Confirm or reject uncertain customer matches",
            to: "/review",
            icon: GitCompareArrows,
            badge: s ? <Pill tone="neutral">{s.needs_review_links} waiting</Pill> : undefined,
          },
        ]
      : []),
    ...(hasRole(user, "admin")
      ? [{ title: "Run a simulation", description: "Generate synthetic data with labelled issues", to: "/simulation", icon: FlaskConical }]
      : []),
  ];

  return (
    <motion.div variants={stagger} initial={animate ? "hidden" : false} animate="show">
      <motion.div variants={rise}>
        <PageHeader
          title="Overview"
          subtitle={
            <>
              Live consistency — {todayLabel()}
              {s && s.new_today > 0 ? <span className="text-ink-700"> · {s.new_today} new findings today</span> : null}
            </>
          }
          actions={
            hasRole(user, "analyst") ? (
              <>
                <Button
                  onClick={() =>
                    toast({ title: "Export started", description: "The findings CSV downloads when the API is connected." })
                  }
                >
                  <Download size={16} aria-hidden="true" />
                  Export report
                </Button>
                <ButtonLink to="/investigations?new=1" variant="primary">
                  <Plus size={16} aria-hidden="true" />
                  New investigation
                </ButtonLink>
              </>
            ) : null
          }
        />
      </motion.div>

      {summary.isError ? (
        <Card>
          <ErrorState title="Couldn't load the overview. Check your connection and retry." onRetry={() => void summary.refetch()} />
        </Card>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <motion.div variants={rise}>
            <KpiCard
              label="Open findings"
              value={s?.open_findings}
              loading={summary.isLoading}
              animate={animate}
              chip={s ? <Pill tone="indigo">+{s.new_today} today</Pill> : null}
              sub={s ? `${s.by_severity.high + s.by_severity.critical} high or critical` : null}
            />
          </motion.div>
          <motion.div variants={rise}>
            <KpiCard
              label="Consistency score"
              value={s?.consistency_score}
              format={(v) => `${v.toFixed(1)}%`}
              loading={summary.isLoading}
              animate={animate}
              chip={s ? <Pill tone="moss">▲ {s.consistency_delta.toFixed(1)} pts</Pill> : null}
              progress={s?.consistency_score ? { value: s.consistency_score / 100, label: "Consistency score" } : undefined}
            />
          </motion.div>
          <motion.div variants={rise}>
            <KpiCard
              label="Customers at risk"
              value={s?.at_risk.total}
              loading={summary.isLoading}
              animate={animate}
              chip={s ? <Pill tone="rose">{s.at_risk.critical} critical</Pill> : null}
              sub={s ? `Warning or critical · avg. confidence ${Math.round(s.at_risk.avg_confidence * 100)}%` : null}
            />
          </motion.div>
          <motion.div variants={rise}>
            <KpiCard
              label="Explained by AI"
              value={s ? s.explained_share * 100 : undefined}
              format={(v) => `${Math.round(v)}%`}
              loading={summary.isLoading}
              animate={animate}
              chip={
                <Pill tone="indigo" icon={<Sparkles size={11} aria-hidden="true" />}>
                  Gemini
                </Pill>
              }
              sub={s ? `of ${formatNumber(s.open_findings)} active findings` : null}
            />
          </motion.div>
        </div>
      )}

      <div className="mt-8 grid gap-x-4 gap-y-8 lg:grid-cols-12">
        <motion.section variants={rise} className="min-w-0 lg:col-span-8" aria-labelledby="live-findings">
          <SectionHeader
            id="live-findings"
            title="Live findings"
            action={
              <ButtonLink to="/findings" size="sm">
                View all
              </ButtonLink>
            }
          />
          <Card className="overflow-hidden p-0">
            <DataTable
              caption="Active findings by priority"
              rows={findings.data?.slice(0, 7)}
              loading={findings.isLoading}
              columns={overviewColumns}
              rowKey={(f) => f.id}
              rowLabel={(f) => `Open finding: ${f.title}, ${f.entity_name}`}
              onRowClick={(f) => setParams({ finding: f.id })}
              selectedKey={params.get("finding")}
              empty={<EmptyState title="No active findings" description="Every system agrees right now." />}
            />
          </Card>
        </motion.section>

        <motion.aside variants={rise} className="flex min-w-0 flex-col gap-4 lg:col-span-4" aria-labelledby="quick-actions">
          <div>
            <SectionHeader id="quick-actions" title="Quick actions" />
            <ActionList items={actions} label="Quick actions" />
          </div>
          <LiveFeed alerts={alerts.data} loading={alerts.isLoading} newIds={newAlertIds} connected={env.demoData} limit={5} />
        </motion.aside>
      </div>

      <div className="mt-8 grid gap-4 lg:grid-cols-12">
        <motion.section variants={rise} className="lg:col-span-7" aria-labelledby="this-week">
          <Card>
            <div className="mb-2 flex items-center justify-between gap-3">
              <h2 id="this-week" className="text-h3 text-ink-950">
                Findings this week
              </h2>
              <div className="flex items-center gap-3 text-caption text-ink-500">
                <span className="inline-flex items-center gap-1.5">
                  <span aria-hidden="true" className="size-2 rounded-pill bg-ink-950" /> Created
                </span>
                <span className="inline-flex items-center gap-1.5">
                  <span aria-hidden="true" className="size-2 rounded-pill bg-moss-500" /> Resolved
                </span>
              </div>
            </div>
            {trends.data ? <TrendChart points={trends.data} animate={animate} /> : <Skeleton className="h-[220px] w-full" />}
          </Card>
        </motion.section>

        <motion.section variants={rise} className="lg:col-span-5" aria-labelledby="system-health">
          <Card className="h-full">
            <h2 id="system-health" className="mb-3 text-h3 text-ink-950">
              System health
            </h2>
            <ul className="divide-y divide-ink-100">
              {(health.data ?? []).map((system) => (
                <li key={system.key} className="flex items-center gap-3 py-3">
                  <SystemChip system={system.key} />
                  <div className="min-w-0 flex-1">
                    <p className="text-small text-ink-950">
                      <span className="font-medium tabular">{system.open_issues}</span> open issues
                    </p>
                    <p className="text-caption font-normal text-ink-500">
                      {formatNumber(system.records)} records · last data{" "}
                      {system.last_event_at ? relativeTime(system.last_event_at) : "never"}
                    </p>
                  </div>
                  {freshness(system.last_event_at)}
                </li>
              ))}
              {health.isLoading
                ? Array.from({ length: 3 }, (_, i) => (
                    <li key={i} className="py-3">
                      <Skeleton className="h-9 w-full" />
                    </li>
                  ))
                : null}
            </ul>
            <p className="mt-3 text-caption font-normal text-ink-500">
              When a system goes quiet, missing-evidence checks report “cannot assess” instead of raising findings.
            </p>
          </Card>
        </motion.section>
      </div>

      <FindingDrawer id={params.get("finding")} onClose={() => setParams({})} />
    </motion.div>
  );
}
