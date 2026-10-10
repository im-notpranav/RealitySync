import { Play, Zap } from "lucide-react";
import { useId, useState } from "react";
import { useNavigate } from "react-router-dom";

import { RoleGate } from "../../components/RoleGate";
import {
  Button,
  Card,
  DataTable,
  Field,
  Input,
  PageHeader,
  Pill,
  ProgressBar,
  SectionHeader,
  Select,
  Slider,
  toast,
} from "../../components/ui";
import { useSimulationRuns } from "../../lib/api/queries";
import { formatNumber, formatPercent, relativeTime } from "../../lib/format";

export function Component() {
  const runs = useSimulationRuns();
  const navigate = useNavigate();
  const ids = { seed: useId(), customers: useId(), outage: useId() };
  const [seed, setSeed] = useState("42");
  const [customers, setCustomers] = useState("500");
  const [anomalyRate, setAnomalyRate] = useState(0.08);
  const [speed, setSpeed] = useState(25);
  const [historyDays, setHistoryDays] = useState(365);
  const [scenarioRate, setScenarioRate] = useState(0.05);
  const [outage, setOutage] = useState("none");

  return (
    <RoleGate min="admin" title="Simulation">
      <PageHeader
        title="Simulation"
        subtitle="Generate synthetic CRM, Billing and Support data with labelled issues and investigation scenarios"
        actions={
          <Button onClick={() => toast({ title: "Drift injected", description: "5 new issues are on their way." })}>
            <Zap size={16} aria-hidden="true" />
            Simulate drift
          </Button>
        }
      />
      <div className="grid gap-4 lg:grid-cols-12">
        <Card className="lg:col-span-5">
          <h2 className="mb-4 text-h3 text-ink-950">New run</h2>
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="Seed" htmlFor={ids.seed}>
              <Input id={ids.seed} inputMode="numeric" value={seed} onChange={(e) => setSeed(e.target.value)} />
            </Field>
            <Field label="Customers" htmlFor={ids.customers} hint="10–5,000">
              <Input id={ids.customers} inputMode="numeric" value={customers} onChange={(e) => setCustomers(e.target.value)} />
            </Field>
          </div>
          <div className="mt-4 flex flex-col gap-4">
            <div>
              <p className="mb-1.5 text-small font-medium text-ink-700">Anomaly rate</p>
              <Slider label="Anomaly rate" value={anomalyRate} min={0} max={0.5} step={0.01} onValueChange={setAnomalyRate} format={(v) => formatPercent(v)} />
            </div>
            <div>
              <p className="mb-1.5 text-small font-medium text-ink-700">Events per second</p>
              <Slider label="Events per second" value={speed} min={1} max={200} step={1} onValueChange={setSpeed} format={(v) => `${v}/s`} />
            </div>
            <div>
              <p className="mb-1.5 text-small font-medium text-ink-700">History</p>
              <Slider label="History in days" value={historyDays} min={30} max={730} step={5} onValueChange={setHistoryDays} format={(v) => `${v} d`} />
            </div>
            <div>
              <p className="mb-1.5 text-small font-medium text-ink-700">Investigation scenarios</p>
              <Slider label="Scenario rate" value={scenarioRate} min={0} max={0.2} step={0.01} onValueChange={setScenarioRate} format={(v) => formatPercent(v)} />
            </div>
            <Field label="Feed outage" htmlFor={ids.outage} hint="One system goes silent for the last 40 days, to test “cannot assess”.">
              <Select
                id={ids.outage}
                label="Feed outage"
                value={outage}
                onValueChange={setOutage}
                options={[
                  { value: "none", label: "No outage" },
                  { value: "crm", label: "CRM" },
                  { value: "billing", label: "Billing" },
                  { value: "support", label: "Support" },
                ]}
              />
            </Field>
          </div>
          <Button
            variant="primary"
            className="mt-6 w-full"
            onClick={() => toast({ title: "Simulation started", description: `${formatNumber(Number(customers) || 0)} customers, seed ${seed}.` })}
          >
            <Play size={16} aria-hidden="true" />
            Start simulation
          </Button>
        </Card>

        <div className="lg:col-span-7">
          <SectionHeader title="Runs" />
          <Card className="overflow-hidden p-0">
            <DataTable
              caption="Simulation runs"
              rows={runs.data}
              loading={runs.isLoading}
              rowKey={(r) => r.id}
              rowLabel={(r) => `Open evaluation for run ${r.id}`}
              onRowClick={(r) => navigate(`/simulation/${r.id}/evaluation`)}
              columns={[
                {
                  key: "run",
                  header: "Run",
                  cell: (r) => (
                    <div>
                      <p className="font-medium text-ink-950">Seed {r.seed}</p>
                      <p className="text-small text-ink-500">
                        {formatNumber(r.customers)} customers · {r.injected_issues} issues
                      </p>
                    </div>
                  ),
                },
                {
                  key: "progress",
                  header: "Progress",
                  cell: (r) => (
                    <div className="flex w-40 flex-col gap-1">
                      <span className="text-caption font-normal tabular text-ink-500">
                        {formatNumber(r.progress.events_sent)} / {formatNumber(r.progress.events_total)} events
                      </span>
                      <ProgressBar value={r.progress.events_sent / r.progress.events_total} label="Run progress" />
                    </div>
                  ),
                },
                {
                  key: "status",
                  header: "Status",
                  cell: (r) => <Pill tone={r.status === "completed" ? "moss" : r.status === "running" ? "sky" : "neutral"}>{r.status}</Pill>,
                },
                {
                  key: "started",
                  header: "Started",
                  hideBelow: "lg",
                  cell: (r) => <span className="text-small text-ink-500">{relativeTime(r.started_at)}</span>,
                },
              ]}
            />
          </Card>
        </div>
      </div>
    </RoleGate>
  );
}
