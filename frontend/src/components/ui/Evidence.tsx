import { FileSearch, Sparkles } from "lucide-react";
import { useState } from "react";

import type { SystemKey, Trail, TrailFact } from "../../lib/api/types";
import { cn } from "../../lib/cn";
import { formatDateTime, formatPercent, humanize, systemNames } from "../../lib/format";
import { Pill, RiskBadge, SeverityBadge, SystemChip } from "./Badges";

const SYSTEMS: SystemKey[] = ["crm", "billing", "support"];

// ------------------------------------------------------------------ diff table

/** field · CRM · Billing · Support; differing cells are tinted (06 §6 DiffRow). */
export function DiffTable({
  fields,
}: {
  fields: { field: string; values: Partial<Record<SystemKey, string>> }[];
}) {
  const systems = SYSTEMS.filter((s) => fields.some((f) => f.values[s] !== undefined));
  return (
    <div className="overflow-hidden rounded-control border border-ink-200">
      <table className="w-full border-collapse text-left">
        <caption className="sr-only">Values per system</caption>
        <thead className="bg-ink-100">
          <tr>
            <th scope="col" className="h-9 px-3 text-caption font-medium text-ink-500">
              Field
            </th>
            {systems.map((system) => (
              <th key={system} scope="col" className="h-9 px-3 text-caption font-medium text-ink-500">
                {systemNames[system]}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {fields.map((row) => {
            const distinct = new Set(Object.values(row.values).filter((v) => v && v !== "—"));
            const differs = distinct.size > 1 || systems.some((s) => row.values[s] === "—");
            return (
              <tr key={row.field} className="border-t border-ink-100">
                <th scope="row" className="px-3 py-2.5 text-small font-medium text-ink-700">
                  {humanize(row.field)}
                </th>
                {systems.map((system) => (
                  <td
                    key={system}
                    className={cn(
                      "px-3 py-2.5 text-small text-ink-900",
                      differs &&
                        row.values[system] !== undefined &&
                        "bg-peach-bg shadow-[inset_2px_0_0_var(--peach-fg)]",
                    )}
                  >
                    {row.values[system] ?? <span className="text-ink-400">—</span>}
                  </td>
                ))}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

// ------------------------------------------------------------------ trail

const inferenceLabel = {
  rule: "Rule",
  authority: "Authority",
  risk_signal: "Risk signal",
  risk_level: "Risk level",
} as const;

function FactBody({ fact }: { fact: TrailFact }) {
  if (fact.kind === "absence") {
    return (
      <>
        <span className="block text-small font-medium text-ink-950">Not recorded: {fact.expected}</span>
        <span className="block mt-0.5 text-caption font-normal text-ink-500">
          Expected by {fact.deadline ? formatDateTime(fact.deadline) : "—"} · {systemNames[fact.system]} data
          recorded until {fact.feed_watermark ? formatDateTime(fact.feed_watermark) : "never"}
        </span>
      </>
    );
  }
  return (
    <>
      <span className="block text-small text-ink-950">
        <span className="font-medium">{humanize(fact.field ?? "value")}</span> = {fact.value}
      </span>
      <span className="block mt-0.5 text-caption font-normal tabular text-ink-500">
        {fact.external_id} · {fact.record_type} v{fact.version} · recorded{" "}
        {fact.recorded_at ? formatDateTime(fact.recorded_at) : "—"}
      </span>
    </>
  );
}

/**
 * Evidence-to-Conclusion Trail (06 §7.8): facts, inferences and the conclusion are separate groups;
 * hovering a fact highlights the inferences that use it and vice versa.
 */
export function TrailView({ trail, citedFactIds = [] }: { trail: Trail; citedFactIds?: string[] }) {
  const [hovered, setHovered] = useState<string | null>(null);
  const [pinned, setPinned] = useState<string | null>(null);
  const active = hovered ?? pinned;
  const linked = new Set<string>();
  if (active) {
    linked.add(active);
    for (const inference of trail.inferences) {
      if (inference.id === active) inference.uses.forEach((id) => linked.add(id));
      if (inference.uses.includes(active)) linked.add(inference.id);
    }
  }
  // Click (or Enter) pins the highlight so keyboard users can explore the links too.
  const tileProps = (id: string) => ({
    type: "button" as const,
    "aria-pressed": pinned === id,
    onClick: () => setPinned((current) => (current === id ? null : id)),
    onMouseEnter: () => setHovered(id),
    onMouseLeave: () => setHovered(null),
  });
  const tile = (id: string) =>
    cn(
      "block w-full rounded-control border p-3 text-left transition-[background-color,border-color] duration-fast",
      linked.has(id) ? "border-ink-950 bg-ink-100" : "border-ink-200 bg-paper",
    );

  return (
    <div className="flex flex-col gap-5">
      <section aria-labelledby="trail-facts">
        <h3 id="trail-facts" className="mb-2 flex items-center gap-2 text-caption text-ink-500">
          <FileSearch size={14} aria-hidden="true" /> Facts (from source systems)
        </h3>
        <ul className="flex flex-col gap-2">
          {trail.facts.map((fact) => (
            <li key={fact.id}>
              <button {...tileProps(fact.id)} className={tile(fact.id)}>
                <span className="mb-1.5 flex flex-wrap items-center gap-1.5">
                  <span className="rounded-[6px] bg-ink-100 px-1.5 text-caption tabular text-ink-700">
                    {fact.id}
                  </span>
                  <SystemChip system={fact.system} />
                  {fact.kind === "absence" ? <Pill tone="amber">Absence</Pill> : null}
                  {citedFactIds.includes(fact.id) ? (
                    <Pill tone="indigo" icon={<Sparkles size={11} aria-hidden="true" />}>
                      Cited by AI
                    </Pill>
                  ) : null}
                </span>
                <FactBody fact={fact} />
              </button>
            </li>
          ))}
        </ul>
      </section>

      <section aria-labelledby="trail-inferences">
        <h3 id="trail-inferences" className="mb-2 text-caption text-ink-500">
          What RealitySync inferred
        </h3>
        <ul className="flex flex-col gap-2">
          {trail.inferences.map((inference) => (
            <li key={inference.id}>
              <button {...tileProps(inference.id)} className={tile(inference.id)}>
                <span className="mb-1 flex items-center gap-1.5">
                  <span className="rounded-[6px] bg-ink-100 px-1.5 text-caption tabular text-ink-700">
                    {inference.id}
                  </span>
                  <span className="text-caption text-ink-500">{inferenceLabel[inference.kind]}</span>
                  <span className="ml-auto text-caption font-normal text-ink-500">
                    uses {inference.uses.join(", ")}
                  </span>
                </span>
                <span className="block text-small text-ink-900">{inference.statement}</span>
              </button>
            </li>
          ))}
        </ul>
      </section>

      <section aria-labelledby="trail-conclusion">
        <h3 id="trail-conclusion" className="mb-2 text-caption text-ink-500">
          Conclusion
        </h3>
        <div className="flex flex-wrap items-center gap-2 rounded-control bg-ink-950 p-3 text-on-dark">
          {trail.conclusion.kind === "risk" ? (
            <RiskBadge level={trail.conclusion.risk as "low"} confidence={trail.conclusion.confidence} />
          ) : (
            <SeverityBadge severity={trail.conclusion.risk as "low"} />
          )}
          <span className="text-small">
            Confidence {formatPercent(trail.conclusion.confidence)}
            {trail.conclusion.score !== undefined ? ` · score ${trail.conclusion.score.toFixed(3)}` : ""}
          </span>
          <span className="ml-auto text-caption font-normal text-on-dark-muted">
            from {trail.conclusion.uses.join(", ")}
          </span>
        </div>
      </section>
    </div>
  );
}
