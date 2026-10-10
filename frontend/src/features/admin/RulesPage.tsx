import { useEffect, useState } from "react";

import { RoleGate } from "../../components/RoleGate";
import { Card, DataTable, ErrorState, PageHeader, Pill, Select, Switch, toast, type Tone } from "../../components/ui";
import { useRules } from "../../lib/api/queries";
import type { Rule, RuleCategory, Severity } from "../../lib/api/types";
import { humanize } from "../../lib/format";

const categoryTone: Record<RuleCategory, Tone> = {
  field_conflict: "sky",
  logic: "indigo",
  temporal: "peach",
  structural: "neutral",
  missing_evidence: "amber",
};

const severityOptions = (["low", "medium", "high", "critical"] as Severity[]).map((s) => ({ value: s, label: humanize(s) }));

export function Component() {
  const { data, isLoading, isError, refetch } = useRules();
  const [rules, setRules] = useState<Rule[] | undefined>(undefined);
  useEffect(() => setRules(data), [data]);

  function update(key: string, patch: Partial<Rule>, message: string) {
    setRules((current) => current?.map((r) => (r.key === key ? { ...r, ...patch } : r)));
    toast({ title: message, description: "Affected customers are queued for re-evaluation." });
  }

  return (
    <RoleGate min="admin" title="Rules">
      <PageHeader title="Rules" subtitle="18 deterministic checks. The AI explains findings; it never decides them." />
      <Card className="overflow-hidden p-0">
        {isError ? (
          <ErrorState onRetry={() => void refetch()} />
        ) : (
          <DataTable
            caption="Detection rules"
            rows={rules}
            loading={isLoading}
            rowKey={(r) => r.key}
            columns={[
              {
                key: "rule",
                header: "Rule",
                sortValue: (r) => r.key,
                cell: (r) => (
                  <div className="min-w-0">
                    <p className="truncate font-medium text-ink-950">
                      <span className="tabular text-ink-500">{r.key}</span> {r.name}
                    </p>
                    <p className="truncate text-small text-ink-500">Certainty {r.certainty.toFixed(2)} · version {r.version}</p>
                  </div>
                ),
              },
              {
                key: "category",
                header: "Category",
                hideBelow: "md",
                cell: (r) => <Pill tone={categoryTone[r.category]}>{humanize(r.category)}</Pill>,
              },
              {
                key: "severity",
                header: "Severity",
                cell: (r) => (
                  <Select
                    label={`Severity for ${r.key}`}
                    value={r.severity}
                    onValueChange={(v) => update(r.key, { severity: v as Severity }, `${r.key} severity set to ${v}`)}
                    options={severityOptions}
                    className="h-9 w-32"
                  />
                ),
              },
              {
                key: "open",
                header: "Open findings",
                sortValue: (r) => r.open_findings,
                hideBelow: "lg",
                cell: (r) => <span className="tabular">{r.open_findings}</span>,
              },
              {
                key: "enabled",
                header: "Enabled",
                cell: (r) => (
                  <Switch
                    label={`${r.key} enabled`}
                    hideLabel
                    checked={r.is_enabled}
                    onCheckedChange={(checked) => update(r.key, { is_enabled: checked }, `${r.key} ${checked ? "enabled" : "disabled"}`)}
                  />
                ),
              },
            ]}
          />
        )}
      </Card>
    </RoleGate>
  );
}
