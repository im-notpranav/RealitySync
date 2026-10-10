import { Download, Search } from "lucide-react";
import { useSearchParams } from "react-router-dom";

import { Button, Card, DataTable, EmptyState, ErrorState, Input, PageHeader, Select, toast } from "../../components/ui";
import { useFindings, type FindingFilters } from "../../lib/api/queries";
import { hasRole, useSession } from "../../store/session";
import { FindingDrawer } from "./FindingDrawer";
import { findingColumns } from "./findingColumns";

const statusOptions = [
  { value: "active", label: "Active" },
  { value: "open", label: "Open" },
  { value: "acknowledged", label: "Acknowledged" },
  { value: "resolved", label: "Resolved" },
  { value: "false_positive", label: "False positive" },
  { value: "all", label: "All statuses" },
];
const severityOptions = [
  { value: "all", label: "All severities" },
  { value: "critical", label: "Critical" },
  { value: "high", label: "High" },
  { value: "medium", label: "Medium" },
  { value: "low", label: "Low" },
];
const systemOptions = [
  { value: "all", label: "All systems" },
  { value: "crm", label: "CRM" },
  { value: "billing", label: "Billing" },
  { value: "support", label: "Support" },
];

/** Findings (06 §7.2): filters and the open drawer live in the URL. Filtering swaps content instantly. */
export function Component() {
  const [params, setParams] = useSearchParams();
  const user = useSession((state) => state.user);
  const filters: FindingFilters = {
    q: params.get("q") ?? "",
    status: (params.get("status") as FindingFilters["status"]) ?? "active",
    severity: params.get("severity") ?? "all",
    system: params.get("system") ?? "all",
  };
  const { data, isLoading, isError, refetch } = useFindings(filters);

  function setParam(key: string, value: string | null) {
    const next = new URLSearchParams(params);
    if (value === null || value === "" || value === "all" || (key === "status" && value === "active")) next.delete(key);
    else next.set(key, value);
    setParams(next, { replace: true });
  }

  return (
    <>
      <PageHeader
        title="Findings"
        subtitle="Contradictions between your systems, ranked by priority"
        actions={
          hasRole(user, "analyst") ? (
            <Button onClick={() => toast({ title: "Export started", description: "The CSV uses the current filters." })}>
              <Download size={16} aria-hidden="true" />
              Export CSV
            </Button>
          ) : null
        }
      />

      <div className="mb-4 flex flex-wrap items-center gap-2">
        <div className="relative w-full sm:w-72">
          <Search
            size={16}
            aria-hidden="true"
            className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-ink-500"
          />
          <Input
            surface="glass"
            type="search"
            aria-label="Search findings"
            placeholder="Title, customer or rule"
            value={filters.q}
            onChange={(event) => setParam("q", event.target.value)}
            className="pl-9"
          />
        </div>
        <Select
          surface="glass"
          label="Status"
          value={filters.status ?? "active"}
          onValueChange={(v) => setParam("status", v)}
          options={statusOptions}
          className="w-40"
        />
        <Select
          surface="glass"
          label="Severity"
          value={filters.severity ?? "all"}
          onValueChange={(v) => setParam("severity", v)}
          options={severityOptions}
          className="w-40"
        />
        <Select
          surface="glass"
          label="System"
          value={filters.system ?? "all"}
          onValueChange={(v) => setParam("system", v)}
          options={systemOptions}
          className="w-36"
        />
        <p className="ml-auto text-small tabular text-ink-500" aria-live="polite">
          {data ? `${data.length} ${data.length === 1 ? "finding" : "findings"}` : ""}
        </p>
      </div>

      <Card className="overflow-hidden p-0">
        {isError ? (
          <ErrorState title="Couldn't load findings. Check your connection and retry." onRetry={() => void refetch()} />
        ) : (
          <DataTable
            caption="Findings"
            rows={data}
            loading={isLoading}
            columns={[
              ...findingColumns.slice(0, 2),
              {
                key: "customer",
                header: "Customer",
                cell: (f) => <span className="text-small text-ink-700">{f.entity_name}</span>,
                sortValue: (f) => f.entity_name,
                hideBelow: "lg",
              },
              ...findingColumns.slice(2),
            ]}
            rowKey={(f) => f.id}
            rowLabel={(f) => `Open finding: ${f.title}, ${f.entity_name}`}
            onRowClick={(f) => setParam("finding", f.id)}
            selectedKey={params.get("finding")}
            defaultSort={{ key: "severity", dir: "desc" }}
            empty={<EmptyState title="No findings match these filters" description="Try another status or clear the search." />}
          />
        )}
      </Card>

      <FindingDrawer id={params.get("finding")} onClose={() => setParam("finding", null)} />
    </>
  );
}
