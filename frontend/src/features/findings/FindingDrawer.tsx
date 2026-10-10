import { ArrowUpRight, Clock, RefreshCw, Sparkles } from "lucide-react";
import { useState, type ReactNode } from "react";
import { Link } from "react-router-dom";

import {
  Button,
  ConfidenceMeter,
  Dialog,
  DiffTable,
  Drawer,
  ErrorState,
  Pill,
  SeverityBadge,
  Skeleton,
  StatusPill,
  SystemChip,
  toast,
  TrailView,
} from "../../components/ui";
import { useFinding, useUpdateFindingStatus } from "../../lib/api/queries";
import type { FindingStatus } from "../../lib/api/types";
import { humanize, relativeTime, systemNames } from "../../lib/format";
import { hasRole, useSession } from "../../store/session";

const doneToast: Partial<Record<FindingStatus, string>> = {
  acknowledged: "Finding acknowledged",
  resolved: "Finding resolved",
  false_positive: "Marked as false positive",
  open: "Finding reopened",
};

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="flex flex-col gap-3">
      <h3 className="text-h3 text-ink-950">{title}</h3>
      {children}
    </section>
  );
}

/** Finding detail (06 §7.2): evidence → trail → AI explanation → history, actions in a sticky bar. */
export function FindingDrawer({ id, onClose }: { id: string | null; onClose: () => void }) {
  const { data, isLoading, isError, refetch } = useFinding(id);
  const update = useUpdateFindingStatus();
  const user = useSession((state) => state.user);
  const [noteOpen, setNoteOpen] = useState(false);
  const [note, setNote] = useState("");

  const canAct = hasRole(user, "analyst") && data && (data.status === "open" || data.status === "acknowledged");

  function transition(status: FindingStatus, withNote?: string) {
    if (!data) return;
    update.mutate(
      { id: data.id, status, note: withNote },
      { onSuccess: () => toast({ title: doneToast[status] ?? "Finding updated", tone: "success" }) },
    );
  }

  return (
    <>
      <Drawer
        open={Boolean(id)}
        onOpenChange={(open) => !open && onClose()}
        label={data?.title ?? "Finding"}
        title={data?.title ?? (isLoading ? <Skeleton className="h-7 w-64" /> : "Finding")}
        header={
          data ? (
            <div className="flex flex-wrap items-center gap-2">
              <SeverityBadge severity={data.severity} />
              <StatusPill status={data.status} />
              <ConfidenceMeter value={data.confidence} breakdown={data.confidence_breakdown} />
              <Pill tone="neutral">{data.rule.key}</Pill>
              {data.sla_breached ? (
                <Pill tone="rose" icon={<Clock size={11} aria-hidden="true" />}>
                  SLA breached
                </Pill>
              ) : null}
            </div>
          ) : null
        }
        footer={
          canAct ? (
            <>
              <Button variant="ghost" onClick={() => setNoteOpen(true)} className="mr-auto">
                Mark as false positive
              </Button>
              {data.status === "open" ? (
                <Button surface="paper" onClick={() => transition("acknowledged")} disabled={update.isPending}>
                  Acknowledge
                </Button>
              ) : null}
              <Button variant="primary" onClick={() => transition("resolved")} disabled={update.isPending}>
                Resolve finding
              </Button>
            </>
          ) : undefined
        }
      >
        {isError ? <ErrorState onRetry={() => void refetch()} /> : null}
        {isLoading ? (
          <div className="flex flex-col gap-3">
            <Skeleton className="h-24 w-full" />
            <Skeleton className="h-40 w-full" />
          </div>
        ) : null}
        {data ? (
          <div className="flex flex-col gap-7">
            <div className="flex flex-wrap items-center justify-between gap-2 text-small text-ink-500">
              <Link
                to={`/entities/${data.entity_id}`}
                className="inline-flex items-center gap-1 font-medium text-ink-950 underline-offset-4 pointer:hover:underline"
              >
                {data.entity_name}
                <ArrowUpRight size={14} aria-hidden="true" />
              </Link>
              <span>
                Detected {relativeTime(data.first_detected_at)} · {data.systems.map((s) => systemNames[s]).join(", ")}
              </span>
            </div>

            <Section title="Evidence">
              <DiffTable fields={data.evidence.fields} />
              {Object.keys(data.evidence.timestamps).length > 0 ? (
                <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 text-small">
                  {Object.entries(data.evidence.timestamps).map(([key, value]) => (
                    <div key={key} className="contents">
                      <dt className="text-ink-500">{humanize(key.split(".").slice(-1)[0] ?? key)}</dt>
                      <dd className="tabular text-ink-900">{relativeTime(value)}</dd>
                    </div>
                  ))}
                </dl>
              ) : null}
              {data.evidence.suggested_authority ? (
                <p className="flex flex-wrap items-center gap-2 text-small text-ink-700">
                  Likely correct:
                  {data.evidence.suggested_authority.likely_correct ? (
                    <SystemChip system={data.evidence.suggested_authority.likely_correct} />
                  ) : (
                    <Pill>Undetermined</Pill>
                  )}
                  <span className="text-ink-500">{data.evidence.suggested_authority.reason}</span>
                </p>
              ) : null}
            </Section>

            <Section title="Explanation">
              {data.explanation ? (
                <div className="rounded-control bg-ink-100 p-4">
                  <div className="mb-3 flex items-center justify-between gap-2">
                    {data.explanation.is_fallback ? (
                      <Pill tone="neutral">Template</Pill>
                    ) : (
                      <Pill tone="indigo" icon={<Sparkles size={11} aria-hidden="true" />}>
                        AI-generated
                      </Pill>
                    )}
                    {hasRole(user, "analyst") ? (
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() =>
                          toast({ title: "Regeneration queued", description: "The new explanation arrives in a few seconds." })
                        }
                      >
                        <RefreshCw size={14} aria-hidden="true" />
                        Regenerate
                      </Button>
                    ) : null}
                  </div>
                  <p className="max-w-[70ch] text-body text-ink-950">{data.explanation.summary}</p>
                  <p className="mt-3 text-small text-ink-700">
                    <span className="font-medium">Likely cause:</span> {data.explanation.root_cause}
                  </p>
                  <ul className="mt-3 flex list-disc flex-col gap-1 pl-5 text-small text-ink-700">
                    {data.explanation.suggested_actions.map((action) => (
                      <li key={action}>{action}</li>
                    ))}
                  </ul>
                  <p className="mt-3 text-small text-ink-500">{data.explanation.caveats}</p>
                  <p className="mt-3 text-caption font-normal text-ink-500">
                    Relies on facts {data.explanation.cited_fact_ids.join(", ")} in the trail below
                  </p>
                </div>
              ) : (
                <div className="flex flex-col gap-2 rounded-control bg-ink-100 p-4" aria-busy="true">
                  <p className="text-small text-ink-500">The explanation is being written. The evidence below is complete.</p>
                  <Skeleton className="h-4 w-11/12" />
                  <Skeleton className="h-4 w-3/4" />
                </div>
              )}
            </Section>

            <Section title="Evidence trail">
              <TrailView trail={data.evidence.trail} citedFactIds={data.explanation?.cited_fact_ids} />
            </Section>

            <Section title="History">
              <ol className="relative flex flex-col gap-4 border-l border-ink-200 pl-5">
                {data.history.map((event, index) => (
                  <li key={`${event.at}-${index}`} className="relative">
                    <span
                      aria-hidden="true"
                      className="absolute -left-[25px] top-1.5 size-2.5 rounded-pill border-2 border-paper bg-ink-950"
                    />
                    <p className="text-small text-ink-950">
                      {humanize(event.action)}
                      {event.by ? <span className="text-ink-500"> by {event.by}</span> : null}
                    </p>
                    {event.note ? <p className="text-small text-ink-700">“{event.note}”</p> : null}
                    <p className="text-caption font-normal text-ink-500">{relativeTime(event.at)}</p>
                  </li>
                ))}
              </ol>
            </Section>
          </div>
        ) : null}
      </Drawer>

      <Dialog
        open={noteOpen}
        onOpenChange={setNoteOpen}
        title="Mark as false positive"
        description="Say why this is not a real problem. The note is kept in the finding's history."
        footer={
          <>
            <Button surface="paper" onClick={() => setNoteOpen(false)}>
              Cancel
            </Button>
            <Button
              variant="primary"
              disabled={note.trim().length === 0}
              onClick={() => {
                transition("false_positive", note.trim());
                setNoteOpen(false);
                setNote("");
              }}
            >
              Mark as false positive
            </Button>
          </>
        }
      >
        <label htmlFor="fp-note" className="sr-only">
          Note
        </label>
        <textarea
          id="fp-note"
          value={note}
          onChange={(event) => setNote(event.target.value)}
          rows={4}
          maxLength={1000}
          placeholder="For example: the customer uses two phone numbers."
          className="w-full rounded-control border border-ink-200 bg-paper p-3 text-body text-ink-900 placeholder:text-ink-400"
        />
      </Dialog>
    </>
  );
}
