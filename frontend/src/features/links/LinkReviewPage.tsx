import { Check, GitCompareArrows, X } from "lucide-react";
import { useEffect, useState } from "react";

import { RoleGate } from "../../components/RoleGate";
import { Button, Card, EmptyState, PageHeader, Pill, Skeleton, SystemChip, toast } from "../../components/ui";
import { useDecideLink, useLinkQueue } from "../../lib/api/queries";
import type { LinkReviewItem } from "../../lib/api/types";
import { cn } from "../../lib/cn";
import { formatPercent, humanize, relativeTime } from "../../lib/format";

function Compare({ item }: { item: LinkReviewItem }) {
  const keys = Array.from(
    new Set([...Object.keys(item.left.normalized), ...Object.keys(item.right.normalized)]),
  );
  return (
    <div className="grid gap-4 md:grid-cols-2">
      {[item.left, item.right].map((record) => (
        <div key={record.id} className="rounded-control border border-ink-200 p-4">
          <div className="mb-2 flex items-center justify-between gap-2">
            <SystemChip system={record.system} />
            <span className="text-caption font-normal tabular text-ink-500">
              {record.external_id} · {relativeTime(record.source_updated_at)}
            </span>
          </div>
          <dl className="divide-y divide-ink-100">
            {keys.map((key) => {
              const same =
                item.left.normalized[key] && item.left.normalized[key] === item.right.normalized[key];
              return (
                <div key={key} className="flex items-baseline justify-between gap-3 py-2">
                  <dt className="text-small text-ink-500">{humanize(key)}</dt>
                  <dd
                    className={cn(
                      "flex items-center gap-1.5 text-small font-medium",
                      same ? "text-ink-950" : "text-peach-fg",
                    )}
                  >
                    {record.normalized[key] ?? <span className="font-normal text-ink-400">—</span>}
                    {same ? <Check size={14} className="text-moss-fg" aria-label="matches" /> : null}
                  </dd>
                </div>
              );
            })}
          </dl>
        </div>
      ))}
    </div>
  );
}

/** Link review (06 §7.4). Keyboard: Y confirm, N reject, J/K move — never animated. */
export function Component() {
  const { data, isLoading } = useLinkQueue();
  const decide = useDecideLink();
  const [index, setIndex] = useState(0);
  const item = data?.[Math.min(index, (data?.length ?? 1) - 1)];

  function act(decision: "confirm" | "reject") {
    if (!item) return;
    decide.mutate(
      { id: item.id, decision },
      {
        onSuccess: () =>
          toast({ title: decision === "confirm" ? "Match confirmed" : "Match rejected", tone: "success" }),
      },
    );
  }

  useEffect(() => {
    function onKey(event: KeyboardEvent) {
      if (event.target instanceof HTMLInputElement || event.target instanceof HTMLTextAreaElement) return;
      const key = event.key.toLowerCase();
      if (key === "y") act("confirm");
      else if (key === "n") act("reject");
      else if (key === "j") setIndex((i) => Math.min(i + 1, (data?.length ?? 1) - 1));
      else if (key === "k") setIndex((i) => Math.max(i - 1, 0));
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  });

  return (
    <RoleGate min="analyst" title="Link review">
      <PageHeader
        title="Link review"
        subtitle={
          <>
            Confirm or reject uncertain customer matches · <kbd className="font-sans">Y</kbd> same,{" "}
            <kbd className="font-sans">N</kbd> different, <kbd className="font-sans">J</kbd>/
            <kbd className="font-sans">K</kbd> move
          </>
        }
      />
      {isLoading ? <Skeleton className="h-80 w-full" /> : null}
      {data && data.length === 0 ? (
        <Card>
          <EmptyState
            icon={GitCompareArrows}
            title="The review queue is clear"
            description="New uncertain matches appear here as data arrives."
          />
        </Card>
      ) : null}
      {data && item ? (
        <div className="grid gap-4 lg:grid-cols-12">
          <Card className="p-2 lg:col-span-4">
            <ul aria-label="Review queue" className="flex flex-col gap-1">
              {data.map((link, i) => (
                <li key={link.id}>
                  <button
                    type="button"
                    onClick={() => setIndex(i)}
                    aria-current={link.id === item.id}
                    className={cn(
                      "flex w-full items-center gap-3 rounded-control px-3 py-3 text-left transition-colors duration-fast",
                      link.id === item.id ? "bg-ink-100" : "pointer:hover:bg-ink-100",
                    )}
                  >
                    <span className="min-w-0 flex-1">
                      <span className="block truncate text-small font-medium capitalize text-ink-950">
                        {link.left.normalized.name}
                      </span>
                      <span className="block truncate text-caption font-normal text-ink-500">
                        {link.left.external_id} ↔ {link.right.external_id}
                      </span>
                    </span>
                    <Pill tone={link.score >= 0.75 ? "neutral" : "amber"}>{formatPercent(link.score)}</Pill>
                  </button>
                </li>
              ))}
            </ul>
          </Card>
          <Card className="lg:col-span-8">
            <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
              <h2 className="text-h3 text-ink-950">Same customer?</h2>
              <Pill tone="amber">Match score {formatPercent(item.score)}</Pill>
            </div>
            <Compare item={item} />
            <div className="mt-4 flex flex-wrap gap-2 text-caption font-normal text-ink-500">
              {Object.entries(item.features).map(([feature, value]) => (
                <span key={feature} className="rounded-pill bg-ink-100 px-2.5 py-1 tabular">
                  {humanize(feature)} {value.toFixed(2)}
                </span>
              ))}
            </div>
            <div className="mt-6 flex justify-end gap-2">
              <Button surface="paper" onClick={() => act("reject")} disabled={decide.isPending}>
                <X size={16} aria-hidden="true" /> Not the same
              </Button>
              <Button variant="primary" onClick={() => act("confirm")} disabled={decide.isPending}>
                <Check size={16} aria-hidden="true" /> Same customer
              </Button>
            </div>
          </Card>
        </div>
      ) : null}
    </RoleGate>
  );
}
