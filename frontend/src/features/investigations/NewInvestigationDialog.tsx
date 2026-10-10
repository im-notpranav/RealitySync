import { useEffect, useId, useState } from "react";
import { useNavigate } from "react-router-dom";

import { Button, Dialog, Field, Select, Slider, toast } from "../../components/ui";
import { useEntities } from "../../lib/api/queries";

/** POST /investigations (04 §17.3) — analyst+. */
export function NewInvestigationDialog({
  open,
  onOpenChange,
  defaultEntityId,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  defaultEntityId?: string | null;
}) {
  const navigate = useNavigate();
  const entities = useEntities();
  const ids = { entity: useId(), kind: useId() };
  const [entityId, setEntityId] = useState(defaultEntityId ?? "e-02");
  const [kind, setKind] = useState<"churn" | "finding">("churn");
  const [lookback, setLookback] = useState(180);
  const [threshold, setThreshold] = useState(0.6);

  useEffect(() => {
    if (defaultEntityId) setEntityId(defaultEntityId);
  }, [defaultEntityId]);

  const customer = entities.data?.find((e) => e.id === entityId);

  return (
    <Dialog
      open={open}
      onOpenChange={onOpenChange}
      title="New investigation"
      description="Replays the customer's history day by day with today's rules to find the first moment RealitySync could have flagged the incident."
      footer={
        <>
          <Button surface="paper" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            variant="primary"
            onClick={() => {
              onOpenChange(false);
              toast({
                title: "Investigation started",
                description: `Replaying ${lookback} days for ${customer?.canonical_name ?? "the customer"}.`,
              });
              navigate("/investigations/i-503");
            }}
          >
            Start investigation
          </Button>
        </>
      }
    >
      <div className="flex flex-col gap-4">
        <Field label="Customer" htmlFor={ids.entity}>
          <Select
            id={ids.entity}
            label="Customer"
            value={entityId}
            onValueChange={setEntityId}
            options={(entities.data ?? []).map((e) => ({ value: e.id, label: e.canonical_name }))}
          />
        </Field>
        <Field
          label="Incident"
          htmlFor={ids.kind}
          hint={kind === "churn" ? "Uses the first recorded churn or cancellation." : "Uses the moment the finding was noticed."}
        >
          <Select
            id={ids.kind}
            label="Incident"
            value={kind}
            onValueChange={(v) => setKind(v as "churn" | "finding")}
            options={[
              { value: "churn", label: "Churn" },
              { value: "finding", label: "A finding" },
            ]}
          />
        </Field>
        <div className="flex flex-col gap-1.5">
          <span className="text-small font-medium text-ink-700">Look back</span>
          <Slider label="Look back in days" value={lookback} min={30} max={365} step={15} onValueChange={setLookback} format={(v) => `${v} d`} />
        </div>
        <div className="flex flex-col gap-1.5">
          <span className="text-small font-medium text-ink-700">Warning threshold</span>
          <Slider label="Warning threshold" value={threshold} min={0.4} max={0.9} step={0.05} onValueChange={setThreshold} />
        </div>
      </div>
    </Dialog>
  );
}
