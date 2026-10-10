/**
 * Synthetic demo data shaped exactly like 04_API_SPEC responses. Used in development until the backend
 * endpoints exist (D-049). Every person, email and id here is invented (example.com).
 */
import type {
  Alert,
  AsOfView,
  AuditItem,
  Checkpoint,
  DashboardSummary,
  EntityDetail,
  EntityListItem,
  Evaluation,
  FailedEvent,
  FindingDetail,
  FindingListItem,
  Investigation,
  LinkReviewItem,
  RiskAssessment,
  Rule,
  SimulationRun,
  SourceSystem,
  SystemHealth,
  SystemKey,
  TimelineItem,
  Trail,
  TrendPoint,
  UserItem,
} from "../api/types";

const NOW = Date.now();
const MIN = 60_000;
const HOUR = 60 * MIN;
const DAY = 24 * HOUR;
const ago = (ms: number) => new Date(NOW - ms).toISOString();
const dayStart = (daysAgo: number) => {
  const d = new Date(NOW - daysAgo * DAY);
  d.setUTCHours(0, 0, 0, 0);
  return d.toISOString();
};

// ---------------------------------------------------------------- customers

interface Person {
  id: string;
  name: string;
  email: string;
  systems: SystemKey[];
}

const people: Person[] = [
  { id: "e-01", name: "Jonathan Smith", email: "jon.smith@example.com", systems: ["crm", "billing", "support"] },
  { id: "e-02", name: "Priya Raman", email: "priya.raman@example.com", systems: ["crm", "billing", "support"] },
  { id: "e-03", name: "Arjun Mehta", email: "arjun.mehta@example.com", systems: ["crm", "billing"] },
  { id: "e-04", name: "Sara Lindqvist", email: "sara.lindqvist@example.com", systems: ["crm", "billing", "support"] },
  { id: "e-05", name: "Kenji Watanabe", email: "kenji.w@example.com", systems: ["crm", "billing", "support"] },
  { id: "e-06", name: "Maria Gonzalez", email: "maria.gonzalez@example.com", systems: ["crm", "billing"] },
  { id: "e-07", name: "Omar Haddad", email: "omar.haddad@example.com", systems: ["billing", "support"] },
  { id: "e-08", name: "Lena Fischer", email: "lena.fischer@example.com", systems: ["crm", "billing", "support"] },
  { id: "e-09", name: "Rahul Verma", email: "rahul.verma@example.com", systems: ["crm", "billing", "support"] },
  { id: "e-10", name: "Chloe Martin", email: "chloe.martin@example.com", systems: ["crm", "support"] },
  { id: "e-11", name: "Daniel Okafor", email: "daniel.okafor@example.com", systems: ["crm", "billing", "support"] },
  { id: "e-12", name: "Aisha Khan", email: "aisha.khan@example.com", systems: ["crm", "billing"] },
];

const personById = new Map(people.map((p) => [p.id, p]));

// ---------------------------------------------------------------- trails

function contradictionTrail(
  ruleKey: string,
  severity: string,
  confidence: number,
  field: string,
  a: { system: SystemKey; ext: string; type: string; value: string; at: string; version: number },
  b: { system: SystemKey; ext: string; type: string; value: string; at: string; version: number },
  statement: string,
  authority?: string,
): Trail {
  return {
    facts: [
      { id: "f1", kind: "record_field", system: a.system, record_id: `${a.ext}-r`, external_id: a.ext, record_type: a.type, version: a.version, field, value: a.value, recorded_at: a.at },
      { id: "f2", kind: "record_field", system: b.system, record_id: `${b.ext}-r`, external_id: b.ext, record_type: b.type, version: b.version, field, value: b.value, recorded_at: b.at },
    ],
    inferences: [
      { id: "i1", kind: "rule", rule_key: ruleKey, uses: ["f1", "f2"], statement },
      ...(authority ? [{ id: "i2", kind: "authority" as const, uses: ["f1", "f2"], statement: authority }] : []),
    ],
    conclusion: { kind: "finding", rule_key: ruleKey, risk: severity, confidence, uses: authority ? ["i1", "i2"] : ["i1"] },
  };
}

function absenceTrail(
  ruleKey: string,
  confidence: number,
  trigger: { system: SystemKey; ext: string; type: string; field: string; value: string; at: string },
  expected: string,
  deadline: string,
  watermark: string,
  statement: string,
): Trail {
  return {
    facts: [
      { id: "f1", kind: "record_field", system: trigger.system, record_id: `${trigger.ext}-r`, external_id: trigger.ext, record_type: trigger.type, version: 2, field: trigger.field, value: trigger.value, recorded_at: trigger.at },
      { id: "f2", kind: "absence", system: trigger.system, expected, deadline, checked_until: ago(0), feed_watermark: watermark },
    ],
    inferences: [{ id: "i1", kind: "rule", rule_key: ruleKey, uses: ["f1", "f2"], statement }],
    conclusion: { kind: "finding", rule_key: ruleKey, risk: "medium", confidence, uses: ["i1"] },
  };
}

// ---------------------------------------------------------------- findings

interface FindingSeed {
  id: string;
  entity: string;
  rule: string;
  ruleName: string;
  category: FindingDetail["rule"]["category"];
  title: string;
  severity: FindingListItem["severity"];
  status: FindingListItem["status"];
  confidence: number;
  breakdown: FindingDetail["confidence_breakdown"];
  systems: SystemKey[];
  detectedAgo: number;
  fields: FindingDetail["evidence"]["fields"];
  timestamps: Record<string, string>;
  authority?: FindingDetail["evidence"]["suggested_authority"];
  trail: Trail;
  explanation?: Omit<NonNullable<FindingDetail["explanation"]>, "id" | "created_at" | "model">;
  slaBreached?: boolean;
}

const severityWeight = { low: 1, medium: 2, high: 3, critical: 4 } as const;

const seeds: FindingSeed[] = [
  {
    id: "f-1001",
    entity: "e-01",
    rule: "R004",
    ruleName: "CRM active, billing cancelled",
    category: "logic",
    title: "CRM active, billing cancelled",
    severity: "high",
    status: "open",
    confidence: 0.829,
    breakdown: { link: 0.97, rule: 0.95, evidence: 0.5, recency: 1 },
    systems: ["crm", "billing"],
    detectedAgo: 12 * MIN,
    fields: [{ field: "status", values: { crm: "active", billing: "cancelled" } }],
    timestamps: { "billing.cancelled_at": ago(3 * DAY) },
    authority: { field: "status", likely_correct: "billing", reason: "billing authority 0.95 vs crm 0.50" },
    trail: contradictionTrail(
      "R004", "high", 0.829, "status",
      { system: "crm", ext: "C-1042", type: "account", value: "active", at: ago(40 * DAY), version: 3 },
      { system: "billing", ext: "SUB-7781", type: "subscription", value: "cancelled", at: ago(3 * DAY), version: 5 },
      "CRM still shows the account active although Billing cancelled its only subscription",
      "Billing is likely correct for status (authority 0.95 vs 0.50)",
    ),
    explanation: {
      summary: "Billing shows this subscription was cancelled 3 days ago, but the CRM still lists the customer as active.",
      root_cause: "The cancellation was most likely not synced back to the CRM.",
      likely_correct_system: "billing",
      suggested_actions: ["Confirm the cancellation with the account owner.", "Update the CRM status to churned."],
      caveats: "If the customer re-subscribed through another channel, billing data may be incomplete.",
      cited_fact_ids: ["f1", "f2"],
      is_fallback: false,
    },
  },
  {
    id: "f-1002",
    entity: "e-02",
    rule: "R016",
    ruleName: "Payment unconfirmed",
    category: "missing_evidence",
    title: "Payment unconfirmed after due date",
    severity: "medium",
    status: "open",
    confidence: 0.765,
    breakdown: { link: 1, rule: 0.85, evidence: 0.5, recency: 1 },
    systems: ["billing"],
    detectedAgo: 34 * MIN,
    fields: [{ field: "invoice.status", values: { billing: "issued" } }],
    timestamps: { "billing.invoice.issued_at": ago(31 * DAY), deadline: ago(9 * DAY) },
    trail: absenceTrail(
      "R016", 0.765,
      { system: "billing", ext: "INV-30551", type: "invoice", field: "status", value: "issued", at: ago(31 * DAY) },
      "invoice.paid_at", ago(9 * DAY), ago(4 * MIN),
      "No payment is recorded for INV-30551 nine days after its due date plus grace; Billing data is current",
    ),
    explanation: {
      summary: "Invoice INV-30551 has no recorded payment nine days after its due date and grace period.",
      root_cause: "Payment is unconfirmed: it may be late, or recorded somewhere Billing does not see.",
      likely_correct_system: "undetermined",
      suggested_actions: ["Check the payment provider for this invoice.", "Contact the customer if no payment exists."],
      caveats: "This is missing evidence, not proof that the customer did not pay.",
      cited_fact_ids: ["f1", "f2"],
      is_fallback: false,
    },
  },
  {
    id: "f-1003",
    entity: "e-03",
    rule: "R001",
    ruleName: "Email mismatch",
    category: "field_conflict",
    title: "Email differs between CRM and Billing",
    severity: "medium",
    status: "acknowledged",
    confidence: 0.912,
    breakdown: { link: 0.98, rule: 0.95, evidence: 0.75, recency: 1 },
    systems: ["crm", "billing"],
    detectedAgo: 2 * HOUR,
    fields: [{ field: "email", values: { crm: "arjun.mehta@example.com", billing: "a.mehta@example.com" } }],
    timestamps: {},
    authority: { field: "email", likely_correct: "crm", reason: "crm authority 0.90 vs billing 0.60" },
    trail: contradictionTrail(
      "R001", "medium", 0.912, "email",
      { system: "crm", ext: "C-2210", type: "account", value: "arjun.mehta@example.com", at: ago(5 * DAY), version: 4 },
      { system: "billing", ext: "B-4410", type: "account", value: "a.mehta@example.com", at: ago(62 * DAY), version: 2 },
      "Linked accounts have different canonical emails",
      "CRM is likely correct for email (authority 0.90 vs 0.60)",
    ),
  },
  {
    id: "f-1004",
    entity: "e-04",
    rule: "R008",
    ruleName: "Invoice after cancellation",
    category: "temporal",
    title: "Invoice issued after cancellation",
    severity: "critical",
    status: "open",
    confidence: 0.884,
    breakdown: { link: 0.99, rule: 0.95, evidence: 0.75, recency: 1 },
    systems: ["billing"],
    detectedAgo: 45 * MIN,
    fields: [{ field: "invoice.issued_at", values: { billing: "14 days after cancelled_at" } }],
    timestamps: { "billing.cancelled_at": ago(20 * DAY), "billing.invoice.issued_at": ago(6 * DAY) },
    trail: contradictionTrail(
      "R008", "critical", 0.884, "issued_at",
      { system: "billing", ext: "SUB-5530", type: "subscription", value: "cancelled", at: ago(20 * DAY), version: 6 },
      { system: "billing", ext: "INV-30890", type: "invoice", value: "issued", at: ago(6 * DAY), version: 1 },
      "An invoice was issued 14 days after the subscription was cancelled (grace 3 days)",
    ),
    explanation: {
      summary: "An invoice was issued 14 days after this subscription was cancelled.",
      root_cause: "Billing kept a recurring schedule active after the cancellation.",
      likely_correct_system: "billing",
      suggested_actions: ["Void invoice INV-30890.", "Check the recurring schedule for this subscription."],
      caveats: "If the customer was billed for usage before cancelling, the invoice may be legitimate.",
      cited_fact_ids: ["f1", "f2"],
      is_fallback: true,
    },
  },
  {
    id: "f-1005",
    entity: "e-05",
    rule: "R017",
    ruleName: "Support response unconfirmed",
    category: "missing_evidence",
    title: "No response recorded for an urgent ticket",
    severity: "medium",
    status: "open",
    confidence: 0.722,
    breakdown: { link: 0.94, rule: 0.85, evidence: 0.5, recency: 1 },
    systems: ["support"],
    detectedAgo: 3 * HOUR,
    fields: [{ field: "ticket.priority", values: { support: "urgent" } }],
    timestamps: { "support.ticket.opened_at": ago(2 * DAY) },
    trail: absenceTrail(
      "R017", 0.722,
      { system: "support", ext: "Z-9013", type: "ticket", field: "priority", value: "urgent", at: ago(2 * DAY) },
      "ticket.first_response_at", ago(DAY), ago(9 * MIN),
      "No first response is recorded within 24 h for an urgent open ticket; Support data is current",
    ),
  },
  {
    id: "f-1006",
    entity: "e-06",
    rule: "R006",
    ruleName: "Plan mismatch",
    category: "field_conflict",
    title: "Plan differs between CRM and Billing",
    severity: "medium",
    status: "open",
    confidence: 0.803,
    breakdown: { link: 0.94, rule: 0.95, evidence: 0.5, recency: 1 },
    systems: ["crm", "billing"],
    detectedAgo: 5 * HOUR,
    fields: [{ field: "plan", values: { crm: "enterprise", billing: "pro" } }],
    timestamps: {},
    authority: { field: "plan", likely_correct: "billing", reason: "billing authority 0.95 vs crm 0.50" },
    trail: contradictionTrail(
      "R006", "medium", 0.803, "plan",
      { system: "crm", ext: "C-3301", type: "account", value: "enterprise", at: ago(15 * DAY), version: 7 },
      { system: "billing", ext: "SUB-6612", type: "subscription", value: "pro", at: ago(16 * DAY), version: 3 },
      "CRM plan does not match the active subscription plan",
      "Billing is likely correct for plan (authority 0.95 vs 0.50)",
    ),
  },
  {
    id: "f-1007",
    entity: "e-08",
    rule: "R005",
    ruleName: "Billing active, CRM churned",
    category: "logic",
    title: "Billing active, CRM churned",
    severity: "high",
    status: "open",
    confidence: 0.857,
    breakdown: { link: 1, rule: 0.95, evidence: 0.5, recency: 1 },
    systems: ["crm", "billing"],
    detectedAgo: 8 * HOUR,
    fields: [{ field: "status", values: { crm: "churned", billing: "active" } }],
    timestamps: {},
    authority: { field: "status", likely_correct: "billing", reason: "billing authority 0.95 vs crm 0.50" },
    trail: contradictionTrail(
      "R005", "high", 0.857, "status",
      { system: "crm", ext: "C-5120", type: "account", value: "churned", at: ago(9 * DAY), version: 8 },
      { system: "billing", ext: "SUB-8120", type: "subscription", value: "active", at: ago(2 * DAY), version: 11 },
      "The subscription is still active although the CRM marks the customer churned",
      "Billing is likely correct for status (authority 0.95 vs 0.50)",
    ),
    slaBreached: true,
  },
  {
    id: "f-1008",
    entity: "e-09",
    rule: "R014",
    ruleName: "Invoice amount mismatch",
    category: "field_conflict",
    title: "Invoice amount differs from the plan price",
    severity: "medium",
    status: "resolved",
    confidence: 0.93,
    breakdown: { link: 1, rule: 0.95, evidence: 0.75, recency: 1 },
    systems: ["billing"],
    detectedAgo: 2 * DAY,
    fields: [{ field: "amount", values: { billing: "₹1,099.00 (expected ₹1,299.00)" } }],
    timestamps: {},
    trail: contradictionTrail(
      "R014", "medium", 0.93, "amount",
      { system: "billing", ext: "SUB-2290", type: "subscription", value: "pro × 1", at: ago(90 * DAY), version: 2 },
      { system: "billing", ext: "INV-29011", type: "invoice", value: "1099.00 INR", at: ago(3 * DAY), version: 1 },
      "Invoice amount is 15% below plan price × quantity (tolerance 1%)",
    ),
  },
  {
    id: "f-1009",
    entity: "e-10",
    rule: "R013",
    ruleName: "Orphan billing customer",
    category: "structural",
    title: "Billing customer without a CRM account",
    severity: "high",
    status: "open",
    confidence: 0.79,
    breakdown: { link: 0.83, rule: 0.95, evidence: 0.5, recency: 1 },
    systems: ["billing"],
    detectedAgo: 26 * HOUR,
    fields: [{ field: "crm account", values: { billing: "B-7712 active", crm: "—" } }],
    timestamps: {},
    trail: contradictionTrail(
      "R013", "high", 0.79, "account",
      { system: "billing", ext: "B-7712", type: "account", value: "active subscription", at: ago(4 * DAY), version: 2 },
      { system: "billing", ext: "SUB-7713", type: "subscription", value: "active", at: ago(4 * DAY), version: 1 },
      "A Billing account with an active subscription has no linked CRM account",
    ),
  },
  {
    id: "f-1010",
    entity: "e-11",
    rule: "R002",
    ruleName: "Name mismatch",
    category: "field_conflict",
    title: "Name differs between CRM and Support",
    severity: "low",
    status: "open",
    confidence: 0.668,
    breakdown: { link: 0.82, rule: 0.8, evidence: 0.5, recency: 0.95 },
    systems: ["crm", "support"],
    detectedAgo: 30 * HOUR,
    fields: [{ field: "name", values: { crm: "Daniel Okafor", support: "Dan Okafo" } }],
    timestamps: {},
    trail: contradictionTrail(
      "R002", "low", 0.668, "name",
      { system: "crm", ext: "C-6610", type: "account", value: "Daniel Okafor", at: ago(70 * DAY), version: 2 },
      { system: "support", ext: "Z-4410", type: "account", value: "Dan Okafo", at: ago(12 * DAY), version: 3 },
      "Name similarity 0.71 is below the 0.80 threshold",
    ),
  },
  {
    id: "f-1011",
    entity: "e-12",
    rule: "R018",
    ruleName: "Invoice unconfirmed for active subscription",
    category: "missing_evidence",
    title: "No invoice recorded for an active subscription",
    severity: "high",
    status: "open",
    confidence: 0.79,
    breakdown: { link: 0.97, rule: 0.85, evidence: 0.5, recency: 1 },
    systems: ["billing"],
    detectedAgo: 50 * MIN,
    fields: [{ field: "last invoice", values: { billing: "52 days ago" } }],
    timestamps: { "billing.last_billed": ago(52 * DAY) },
    trail: absenceTrail(
      "R018", 0.79,
      { system: "billing", ext: "SUB-9902", type: "subscription", field: "status", value: "active", at: ago(80 * DAY) },
      "invoice for SUB-9902", ago(17 * DAY), ago(4 * MIN),
      "No invoice is recorded for 52 days for an active subscription (expected every 35 days)",
    ),
  },
  {
    id: "f-1012",
    entity: "e-05",
    rule: "R003",
    ruleName: "Phone mismatch",
    category: "field_conflict",
    title: "Phone differs between CRM and Billing",
    severity: "low",
    status: "false_positive",
    confidence: 0.701,
    breakdown: { link: 0.94, rule: 0.95, evidence: 0.5, recency: 0.87 },
    systems: ["crm", "billing"],
    detectedAgo: 4 * DAY,
    fields: [{ field: "phone", values: { crm: "+91 98••• ••210", billing: "+91 98••• ••877" } }],
    timestamps: {},
    trail: contradictionTrail(
      "R003", "low", 0.701, "phone",
      { system: "crm", ext: "C-4401", type: "account", value: "••210", at: ago(30 * DAY), version: 3 },
      { system: "billing", ext: "B-4402", type: "account", value: "••877", at: ago(44 * DAY), version: 2 },
      "Both records have a valid phone and the numbers differ",
    ),
  },
];

function toListItem(seed: FindingSeed): FindingListItem {
  const person = personById.get(seed.entity)!;
  return {
    id: seed.id,
    entity_id: seed.entity,
    entity_name: person.name,
    rule_key: seed.rule,
    title: seed.title,
    severity: seed.severity,
    status: seed.status,
    confidence: seed.confidence,
    priority_score: Number((severityWeight[seed.severity] * seed.confidence).toFixed(3)),
    systems: seed.systems,
    first_detected_at: ago(seed.detectedAgo),
    last_detected_at: ago(Math.max(0, seed.detectedAgo - 5 * MIN)),
    reopen_count: 0,
    sla_breached: seed.slaBreached ?? false,
    has_explanation: Boolean(seed.explanation),
  };
}

export const findings: FindingListItem[] = seeds.map(toListItem);

export const findingDetails: Record<string, FindingDetail> = Object.fromEntries(
  seeds.map((seed) => [
    seed.id,
    {
      ...toListItem(seed),
      rule: { key: seed.rule, name: seed.ruleName, category: seed.category },
      confidence_breakdown: seed.breakdown,
      evidence: { fields: seed.fields, timestamps: seed.timestamps, suggested_authority: seed.authority, trail: seed.trail },
      explanation: seed.explanation
        ? {
            ...seed.explanation,
            id: `x-${seed.id}`,
            model: seed.explanation.is_fallback ? "template" : "gemini-3.5-flash-lite",
            created_at: ago(Math.max(0, seed.detectedAgo - 2 * MIN)),
          }
        : null,
      history: [
        { at: ago(seed.detectedAgo), action: "created" },
        ...(seed.status === "acknowledged"
          ? [{ at: ago(seed.detectedAgo - 30 * MIN), action: "acknowledged", by: "Riya Sharma", note: "Checking with the account owner" }]
          : []),
        ...(seed.status === "resolved" ? [{ at: ago(DAY), action: "resolved", by: "Riya Sharma", note: "Invoice corrected in Billing" }] : []),
        ...(seed.status === "false_positive"
          ? [{ at: ago(3 * DAY), action: "false_positive", by: "Riya Sharma", note: "Customer uses two numbers" }]
          : []),
      ],
      resolved_at: seed.status === "resolved" ? ago(DAY) : null,
    } satisfies FindingDetail,
  ]),
);

// ---------------------------------------------------------------- risk

function risk(
  score: number,
  level: RiskAssessment["level"],
  confidence: number,
  values: [number, number, number, number],
  available: [boolean, boolean, boolean, boolean] = [true, true, true, true],
): RiskAssessment {
  const [p, c, d, o] = values;
  return {
    score,
    level,
    confidence,
    model_version: 1,
    assessed_at: ago(5 * MIN),
    signals: {
      payment_delay: { value: p, available: available[0], weight: 0.4 },
      complaint_trend: { value: c, available: available[1], weight: 0.3 },
      commercial_decline: { value: d, available: available[2], weight: 0.2 },
      open_inconsistencies: { value: o, available: available[3], weight: 0.1 },
    },
    trail: {
      facts: [
        { id: "f1", kind: "record_field", system: "billing", external_id: "INV-30120", record_type: "invoice", version: 2, field: "paid_at", value: "21 days late", recorded_at: ago(40 * DAY) },
        { id: "f2", kind: "record_field", system: "billing", external_id: "INV-30551", record_type: "invoice", version: 1, field: "status", value: "issued, 9 days late", recorded_at: ago(31 * DAY) },
        { id: "f3", kind: "record_field", system: "support", external_id: "Z-9071", record_type: "ticket", version: 1, field: "priority", value: "high", recorded_at: ago(6 * DAY) },
        { id: "f4", kind: "record_field", system: "billing", external_id: "SUB-7790", record_type: "subscription", version: 4, field: "plan", value: "pro → starter", recorded_at: ago(58 * DAY) },
      ],
      inferences: [
        { id: "i1", kind: "risk_signal", uses: ["f1", "f2"], statement: `Payment delay ${p.toFixed(2)}: two invoices late by up to 21 days in the last 90 days` },
        { id: "i2", kind: "risk_signal", uses: ["f3"], statement: `Complaint trend ${c.toFixed(2)}: 4 tickets in 30 days vs 2 in the 60 before, 1 high priority` },
        { id: "i3", kind: "risk_signal", uses: ["f4"], statement: `Commercial decline ${d.toFixed(2)}: plan downgraded from pro to starter` },
        { id: "i4", kind: "risk_level", uses: ["f1", "f2", "f3", "f4"], statement: `Weighted score ${score.toFixed(3)} → ${level}` },
      ],
      conclusion: { kind: "risk", risk: level, score, confidence, uses: ["i1", "i2", "i3", "i4"] },
    },
  };
}

const riskByEntity: Record<string, RiskAssessment> = {
  "e-02": risk(0.696, "warning", 1, [0.69, 1, 0.6, 0]),
  "e-04": risk(0.84, "critical", 0.9, [0.9, 0.8, 0.6, 1]),
  "e-07": risk(0.64, "warning", 0.6, [0.85, 0.7, 0.4, 0.5]),
  "e-08": risk(0.81, "critical", 1, [0.8, 1, 0.6, 0.5]),
  "e-12": risk(0.47, "watch", 0.7, [0.5, 0, 0.6, 0.5], [true, false, true, true]),
  "e-05": risk(0.42, "watch", 1, [0.2, 0.75, 0.4, 0]),
  "e-01": risk(0.38, "low", 1, [0.1, 0.5, 0.6, 0.5]),
};

// ---------------------------------------------------------------- entities

export const entities: EntityListItem[] = people.map((person) => {
  const open = findings.filter((f) => f.entity_id === person.id && (f.status === "open" || f.status === "acknowledged"));
  const highest = open.reduce<FindingListItem["severity"] | null>(
    (acc, f) => (!acc || severityWeight[f.severity] > severityWeight[acc] ? f.severity : acc),
    null,
  );
  const r = riskByEntity[person.id];
  return {
    id: person.id,
    canonical_name: person.name,
    canonical_email: person.email,
    health: open.some((f) => f.severity !== "low") ? "inconsistent" : person.systems.length > 1 ? "consistent" : "unknown",
    open_findings_count: open.length,
    highest_severity: highest,
    risk: r ? { score: r.score, level: r.level, confidence: r.confidence } : { score: 0.08, level: "low", confidence: 1 },
    systems: person.systems,
    updated_at: ago(Number(person.id.slice(2)) * 47 * MIN),
  };
});

function accountRecord(system: SystemKey, ext: string, person: Person, extra: Record<string, string | null>, updatedAgo: number, version: number) {
  return {
    id: `${ext}-r`,
    system,
    type: "account" as const,
    external_id: ext,
    normalized: { name: person.name.toLowerCase(), email: person.email, ...extra },
    source_updated_at: ago(updatedAgo),
    version,
  };
}

export function entityDetail(id: string): EntityDetail | null {
  const person = personById.get(id);
  if (!person) return null;
  const base = Number(id.slice(2));
  const records = person.systems.map((system, index) => ({
    link_id: `l-${id}-${system}`,
    link_status: (index === 2 && base % 3 === 0 ? "needs_review" : "auto_matched") as EntityDetail["records"][number]["link_status"],
    match_confidence: index === 0 ? 1 : 0.97 - index * 0.04,
    match_features: { email_exact: 1, phone_exact: index === 2 ? 0 : 1, name_sim: 0.92 - index * 0.05 },
    record: accountRecord(
      system,
      `${system === "crm" ? "C" : system === "billing" ? "B" : "Z"}-${1000 + base * 37}`,
      person,
      system === "crm"
        ? { status: id === "e-08" ? "churned" : "active", plan: id === "e-06" ? "enterprise" : "pro", phone: "+91 98••• ••210" }
        : system === "billing"
          ? { status: id === "e-01" ? "cancelled" : "active", plan: "pro", phone: "+91 98••• ••210" }
          : { phone: null, tickets_open: "2" },
      (index + 1) * 3 * DAY,
      3 + index,
    ),
  }));
  const r = riskByEntity[id] ?? null;
  return {
    id,
    canonical_name: person.name,
    canonical_email: person.email,
    health: entities.find((e) => e.id === id)!.health,
    records,
    children: {
      subscriptions: person.systems.includes("billing")
        ? [{ id: `sub-${id}`, system: "billing", type: "subscription", external_id: `SUB-${7700 + base}`, normalized: { plan: "pro", status: id === "e-01" ? "cancelled" : "active", quantity: "1" }, source_updated_at: ago(3 * DAY), version: 5 }]
        : [],
      invoices: person.systems.includes("billing")
        ? [0, 1, 2].map((n) => ({ id: `inv-${id}-${n}`, system: "billing" as const, type: "invoice" as const, external_id: `INV-${30500 + base * 10 + n}`, normalized: { amount: "1299.00 INR", status: n === 0 && id === "e-02" ? "issued" : "paid" }, source_updated_at: ago((n * 30 + 2) * DAY), version: 2 }))
        : [],
      tickets: person.systems.includes("support")
        ? [{ id: `t-${id}`, system: "support", type: "ticket", external_id: `Z-${9000 + base}`, normalized: { subject: "Invoice question", priority: "high", status: "open" }, source_updated_at: ago(2 * DAY), version: 2 }]
        : [],
    },
    open_findings: findings
      .filter((f) => f.entity_id === id && (f.status === "open" || f.status === "acknowledged"))
      .map(({ id: fid, rule_key, severity, confidence, status, title }) => ({ id: fid, rule_key, severity, confidence, status, title })),
    risk: r,
    expectations:
      id === "e-02"
        ? [{ rule_key: "R016", outcome: "pending", trigger_record_id: "inv-e-02-1", expected: "invoice.paid_at", system: "billing", deadline: ago(-6 * DAY), feed_watermark: ago(4 * MIN) }]
        : id === "e-05"
          ? [{ rule_key: "R017", outcome: "cannot_assess", trigger_record_id: "t-e-05", expected: "ticket.first_response_at", system: "support", deadline: ago(2 * DAY), feed_watermark: ago(3 * DAY) }]
          : [],
  };
}

export function entityTimeline(id: string): TimelineItem[] {
  if (!personById.has(id)) return [];
  return [
    { at: ago(3 * DAY), system: "billing", record_type: "subscription", external_id: "SUB-7781", changed_fields: ["status"], summary: "status: active → cancelled", out_of_order: false },
    { at: ago(6 * DAY), system: "support", record_type: "ticket", external_id: "Z-9071", changed_fields: ["priority"], summary: "New high-priority ticket: Invoice question", out_of_order: false },
    { at: ago(31 * DAY), system: "billing", record_type: "invoice", external_id: "INV-30551", changed_fields: ["status"], summary: "Invoice issued: ₹1,299.00", out_of_order: false },
    { at: ago(40 * DAY), system: "crm", record_type: "account", external_id: "C-1042", changed_fields: ["phone"], summary: "phone updated", out_of_order: true },
    { at: ago(58 * DAY), system: "billing", record_type: "subscription", external_id: "SUB-7790", changed_fields: ["plan"], summary: "plan: pro → starter", out_of_order: false },
  ];
}

/** Time Machine (04 §17.1): risk rises as history accumulates. */
export function asOfView(id: string, at: string): AsOfView | null {
  const detail = entityDetail(id);
  if (!detail) return null;
  const daysBack = Math.max(0, (NOW - new Date(at).getTime()) / DAY);
  const progress = Math.max(0, Math.min(1, 1 - daysBack / 90));
  const score = Number((0.12 + 0.6 * progress).toFixed(3));
  const level = score >= 0.8 ? "critical" : score >= 0.6 ? "warning" : score >= 0.4 ? "watch" : "low";
  const base = riskByEntity[id] ?? risk(score, level, 1, [0.4, 0.5, 0.3, 0]);
  const third = detail.records[2];
  return {
    entity_id: id,
    at,
    records: detail.records
      .filter((_, index) => !(index === 2 && daysBack > 45))
      .map((link) => ({
        link: { status: link.link_status, match_confidence: link.match_confidence },
        record: {
          ...link.record,
          recorded_at: link.record.source_updated_at,
          normalized:
            link.record.system === "billing" && daysBack > 3 && id === "e-01"
              ? { ...link.record.normalized, status: "active" }
              : link.record.normalized,
        },
      })),
    not_yet_linkable:
      daysBack > 45 && third
        ? [{ record_id: third.record.id, system: third.record.system, external_id: third.record.external_id }]
        : [],
    findings: findings
      .filter((f) => f.entity_id === id && new Date(f.first_detected_at).getTime() <= new Date(at).getTime())
      .map((f) => ({ rule_key: f.rule_key, title: f.title, severity: f.severity, confidence: f.confidence, fingerprint: `fp-${f.id}`, live_finding_id: f.id })),
    expectations: detail.expectations,
    risk: { ...base, score, level, assessed_at: at },
    feed_watermarks: { crm: at, billing: at, support: daysBack < 40 ? ago(40 * DAY) : at },
    rule_set: { hash: "3f9c2a7d", risk_model_version: 1 },
    caveat: "Reconstructed from data recorded by then, evaluated with today's rules (rule set 3f9c2a7d). Membership is reconstructed from current links.",
  };
}

// ---------------------------------------------------------------- dashboard

export const dashboardSummary: DashboardSummary = {
  entities: 500,
  systems: 3,
  open_findings: 62,
  needs_review_links: 9,
  consistency_score: 91.4,
  by_severity: { low: 20, medium: 25, high: 15, critical: 2 },
  by_status: { open: 50, acknowledged: 12, resolved: 31, false_positive: 4, auto_resolved: 18 },
  by_system: { crm: 40, billing: 48, support: 12 },
  by_rule: [
    { rule_key: "R004", count: 14 },
    { rule_key: "R016", count: 9 },
    { rule_key: "R001", count: 8 },
  ],
  explained_share: 0.96,
  new_today: 8,
  consistency_delta: 1.2,
  at_risk: { total: 7, critical: 3, avg_confidence: 0.92 },
  ingest: { events_per_sec: 12.4, pending: 3, detection_pending: 1, avg_detect_ms: 18 },
  generated_at: ago(0),
};

export const trends: TrendPoint[] = Array.from({ length: 7 }, (_, i) => {
  const created = [9, 14, 11, 7, 16, 12, 8][i]!;
  const resolved = [6, 9, 12, 8, 10, 13, 5][i]!;
  return { date: dayStart(6 - i), created, resolved, open_end_of_day: 50 + i * 2 };
});

export const systemHealth: SystemHealth[] = [
  { key: "crm", name: "CRM", open_issues: 40, last_event_at: ago(40 * 1000), records: 500 },
  { key: "billing", name: "Billing", open_issues: 48, last_event_at: ago(12 * 1000), records: 6100 },
  { key: "support", name: "Support", open_issues: 12, last_event_at: ago(3 * DAY), records: 1840 },
];

// ---------------------------------------------------------------- alerts

export const alerts: Alert[] = [
  { id: "a-1", type: "finding_created", severity: "high", title: "CRM active, billing cancelled", body: "Jonathan Smith — confidence 83%", finding_id: "f-1001", entity_id: "e-01", link_id: null, created_at: ago(12 * MIN), is_read: false },
  { id: "a-2", type: "risk_threshold_crossed", severity: "high", title: "Risk rose to warning", body: "Priya Raman — risk 0.70, confidence 100%", finding_id: null, entity_id: "e-02", link_id: null, created_at: ago(30 * MIN), is_read: false },
  { id: "a-3", type: "finding_created", severity: "critical", title: "Invoice issued after cancellation", body: "Sara Lindqvist — confidence 88%", finding_id: "f-1004", entity_id: "e-04", link_id: null, created_at: ago(45 * MIN), is_read: false },
  { id: "a-4", type: "finding_created", severity: "high", title: "No invoice recorded for an active subscription", body: "Aisha Khan — confidence 79%", finding_id: "f-1011", entity_id: "e-12", link_id: null, created_at: ago(50 * MIN), is_read: true },
  { id: "a-5", type: "link_needs_review", severity: "medium", title: "Possible match needs review", body: "Omar Haddad — match score 0.78", finding_id: null, entity_id: "e-07", link_id: "lr-1", created_at: ago(2 * HOUR), is_read: true },
  { id: "a-6", type: "risk_threshold_crossed", severity: "critical", title: "Risk rose to critical", body: "Lena Fischer — risk 0.81, confidence 100%", finding_id: null, entity_id: "e-08", link_id: null, created_at: ago(7 * HOUR), is_read: true },
  { id: "a-7", type: "finding_resolved", severity: "medium", title: "Invoice amount mismatch resolved", body: "Rahul Verma", finding_id: "f-1008", entity_id: "e-09", link_id: null, created_at: ago(DAY + 2 * HOUR), is_read: true },
];

/** Items the demo "live" feed streams in, one at a time (06 §8 live row). */
export const liveQueue: Omit<Alert, "id" | "created_at">[] = [
  { type: "finding_created", severity: "medium", title: "Email differs between CRM and Billing", body: "Chloe Martin — confidence 91%", finding_id: "f-1003", entity_id: "e-10", link_id: null, is_read: false },
  { type: "risk_threshold_crossed", severity: "high", title: "Risk rose to warning", body: "Omar Haddad — risk 0.64, confidence 60%", finding_id: null, entity_id: "e-07", link_id: null, is_read: false },
  { type: "finding_created", severity: "low", title: "Name differs between CRM and Support", body: "Daniel Okafor — confidence 67%", finding_id: "f-1010", entity_id: "e-11", link_id: null, is_read: false },
];

// ---------------------------------------------------------------- link review

export const linkQueue: LinkReviewItem[] = [
  {
    id: "lr-1", score: 0.78, entity_id: "e-07", created_at: ago(2 * HOUR),
    features: { email_exact: 0, email_local_sim: 0.86, phone_exact: 1, name_sim: 0.91, company_sim: 0.8 },
    left: { id: "B-5521-r", system: "billing", type: "account", external_id: "B-5521", normalized: { name: "omar haddad", email: "omar.haddad@example.com", phone: "+91 98••• ••455", company: "Haddad Traders" }, source_updated_at: ago(5 * DAY), version: 3 },
    right: { id: "Z-7710-r", system: "support", type: "account", external_id: "Z-7710", normalized: { name: "omar hadad", email: "o.haddad@example.com", phone: "+91 98••• ••455", company: "Haddad Traders Pvt" }, source_updated_at: ago(2 * DAY), version: 1 },
  },
  {
    id: "lr-2", score: 0.72, entity_id: "e-11", created_at: ago(5 * HOUR),
    features: { email_exact: 0, phone_exact: 0, name_sim: 0.88, company_sim: 1 },
    left: { id: "C-6610-r", system: "crm", type: "account", external_id: "C-6610", normalized: { name: "daniel okafor", email: "daniel.okafor@example.com", phone: "+91 97••• ••120", company: "Okafor Labs" }, source_updated_at: ago(70 * DAY), version: 2 },
    right: { id: "Z-4410-r", system: "support", type: "account", external_id: "Z-4410", normalized: { name: "dan okafo", email: "dan@example.com", phone: null, company: "Okafor Labs" }, source_updated_at: ago(12 * DAY), version: 3 },
  },
  {
    id: "lr-3", score: 0.66, entity_id: "e-06", created_at: ago(DAY),
    features: { email_exact: 0, phone_exact: 1, name_sim: 0.7 },
    left: { id: "C-3301-r", system: "crm", type: "account", external_id: "C-3301", normalized: { name: "maria gonzalez", email: "maria.gonzalez@example.com", phone: "+91 99••• ••301", company: null }, source_updated_at: ago(15 * DAY), version: 7 },
    right: { id: "B-3390-r", system: "billing", type: "account", external_id: "B-3390", normalized: { name: "m gonzales", email: "billing@example.com", phone: "+91 99••• ••301", company: "MG Design" }, source_updated_at: ago(16 * DAY), version: 2 },
  },
];

// ---------------------------------------------------------------- investigations

const crossingRisk = riskByEntity["e-02"]!;

export const investigations: Investigation[] = [
  {
    id: "i-501", entity_id: "e-02", entity_name: "Priya Raman",
    incident: { kind: "churn", finding_id: null, at: ago(10 * DAY) },
    lookback_days: 180, warning_threshold: 0.6, status: "completed",
    progress: { checkpoints_done: 412, checkpoints_total: 412 },
    outcome: "crossed", first_detectable_at: dayStart(53), lead_time_hours: 43 * 24 + 9,
    caveat: "Retrospective analysis using today's rules (rule set 3f9c2a7d) on data as it was recorded at each moment. It shows when RealitySync could have flagged this, not that anyone should have acted. Membership is reconstructed from current links.",
    rule_set_hash: "3f9c2a7d", requested_by: "Riya Sharma", created_at: ago(2 * HOUR), completed_at: ago(2 * HOUR - 21_000),
    at_crossing: { risk: crossingRisk },
  },
  {
    id: "i-502", entity_id: "e-03", entity_name: "Arjun Mehta",
    incident: { kind: "churn", finding_id: null, at: ago(22 * DAY) },
    lookback_days: 180, warning_threshold: 0.6, status: "completed",
    progress: { checkpoints_done: 288, checkpoints_total: 288 },
    outcome: "never_crossed", first_detectable_at: null, lead_time_hours: null,
    caveat: "Retrospective analysis using today's rules (rule set 3f9c2a7d). With the data recorded before the incident, RealitySync would not have reached the threshold (0.60). This does not mean no warning signs existed outside the connected systems. Membership is reconstructed from current links.",
    rule_set_hash: "3f9c2a7d", requested_by: "Riya Sharma", created_at: ago(DAY), completed_at: ago(DAY - 14_000),
    at_crossing: null,
  },
  {
    id: "i-503", entity_id: "e-08", entity_name: "Lena Fischer",
    incident: { kind: "finding", finding_id: "f-1007", at: ago(6 * HOUR) },
    lookback_days: 90, warning_threshold: 0.6, status: "running",
    progress: { checkpoints_done: 150, checkpoints_total: 240 },
    outcome: null, first_detectable_at: null, lead_time_hours: null, caveat: null,
    rule_set_hash: "3f9c2a7d", requested_by: "Demo Admin", created_at: ago(4 * MIN), completed_at: null,
    at_crossing: null,
  },
];

export function checkpoints(id: string): Checkpoint[] {
  const inv = investigations.find((i) => i.id === id);
  if (!inv) return [];
  const days = Math.min(inv.lookback_days, 120);
  const incident = new Date(inv.incident.at).getTime();
  return Array.from({ length: days }, (_, i) => {
    const t = i / (days - 1);
    const at = new Date(incident - (days - i) * DAY).toISOString();
    const wobble = Math.sin(i * 0.9) * 0.025 + Math.sin(i * 0.31) * 0.02;
    const score =
      inv.outcome === "crossed"
        ? Math.min(0.92, 0.1 + 0.78 * Math.pow(t, 1.6) + wobble)
        : Math.min(0.52, 0.12 + 0.3 * t + wobble);
    const s = Math.max(0.04, Number(score.toFixed(3)));
    return {
      at,
      risk_score: s,
      risk_level: s >= 0.8 ? "critical" : s >= 0.6 ? "warning" : s >= 0.4 ? "watch" : "low",
      risk_confidence: t < 0.2 ? 0.7 : 1,
      finding_count: s > 0.5 ? 2 : s > 0.3 ? 1 : 0,
    } satisfies Checkpoint;
  });
}

// ---------------------------------------------------------------- admin

const ruleSeeds: [string, string, Rule["category"], Rule["severity"], number, number][] = [
  ["R001", "Email mismatch", "field_conflict", "medium", 0.95, 14],
  ["R002", "Name mismatch", "field_conflict", "low", 0.8, 3],
  ["R003", "Phone mismatch", "field_conflict", "low", 0.95, 2],
  ["R004", "CRM active, billing cancelled", "logic", "high", 0.95, 14],
  ["R005", "Billing active, CRM churned", "logic", "high", 0.95, 6],
  ["R006", "Plan mismatch", "field_conflict", "medium", 0.95, 5],
  ["R007", "Ticket before account", "temporal", "medium", 0.95, 1],
  ["R008", "Invoice after cancellation", "temporal", "high", 0.95, 4],
  ["R009", "Paid before issued", "temporal", "high", 0.95, 0],
  ["R010", "Updated before created", "temporal", "low", 0.95, 0],
  ["R011", "Open ticket, account closed", "logic", "medium", 0.95, 2],
  ["R012", "Duplicate record in system", "structural", "medium", 0.8, 3],
  ["R013", "Orphan billing customer", "structural", "high", 0.95, 2],
  ["R014", "Invoice amount mismatch", "field_conflict", "medium", 0.95, 4],
  ["R015", "Stale sync", "temporal", "low", 0.7, 1],
  ["R016", "Payment unconfirmed", "missing_evidence", "medium", 0.85, 9],
  ["R017", "Support response unconfirmed", "missing_evidence", "medium", 0.85, 4],
  ["R018", "Invoice unconfirmed for active subscription", "missing_evidence", "high", 0.85, 3],
];

export const rules: Rule[] = ruleSeeds.map(([key, name, category, severity, certainty, open]) => ({
  id: `rule-${key}`,
  key,
  name,
  category,
  description: `Deterministic check ${key} (03 §M4).`,
  severity,
  default_severity: severity,
  is_enabled: key !== "R010",
  certainty,
  version: 1,
  open_findings: open,
}));

export const sourceSystems: SourceSystem[] = [
  { id: "s-crm", key: "crm", name: "CRM", is_active: true, reliability_weight: 0.8, field_authority: { name: 0.9, email: 0.9, phone: 0.9, company: 0.9, status: 0.5, plan: 0.5 }, record_counts: { account: 500 }, last_event_at: ago(40_000) },
  { id: "s-billing", key: "billing", name: "Billing", is_active: true, reliability_weight: 0.9, field_authority: { name: 0.6, email: 0.6, status: 0.95, plan: 0.95, amount: 1, invoice_dates: 1 }, record_counts: { account: 480, subscription: 480, invoice: 5120 }, last_event_at: ago(12_000) },
  { id: "s-support", key: "support", name: "Support", is_active: true, reliability_weight: 0.7, field_authority: { name: 0.4, email: 0.4, ticket: 1 }, record_counts: { account: 420, ticket: 1420 }, last_event_at: ago(3 * DAY) },
];

export const failedEvents: FailedEvent[] = [
  { id: "ev-1", source: "support", record_type: "ticket", external_id: "Z-9120", attempts: 5, error: "payload.opened_at has no timezone", received_at: ago(3 * HOUR) },
  { id: "ev-2", source: "billing", record_type: "invoice", external_id: "INV-31002", attempts: 5, error: "unknown currency code", received_at: ago(9 * HOUR) },
];

export const simulationRuns: SimulationRun[] = [
  { id: "r-12", status: "completed", seed: 42, customers: 500, progress: { events_sent: 5400, events_total: 5400 }, injected_issues: 40, started_at: ago(26 * HOUR), ended_at: ago(25 * HOUR) },
  { id: "r-11", status: "stopped", seed: 7, customers: 200, progress: { events_sent: 1200, events_total: 2200 }, injected_issues: 16, started_at: ago(3 * DAY), ended_at: ago(3 * DAY - HOUR) },
];

const byTypeSeeds: [string, number, number][] = [
  ["status_conflict", 8, 8],
  ["email_mismatch", 6, 6],
  ["invoice_after_cancel", 4, 4],
  ["plan_mismatch", 4, 3],
  ["payment_never_recorded", 5, 5],
  ["support_response_missing", 3, 3],
  ["stale_sync", 4, 2],
  ["duplicate_record", 3, 2],
];

export const evaluation: Evaluation = {
  precision: 0.93,
  recall: 0.88,
  f1: 0.904,
  true_positives: 35,
  false_positives: 3,
  false_negatives: 5,
  ignored: 4,
  matching: { auto_precision: 0.995, recall_auto_or_review: 0.97, true_pairs: 1000 },
  by_type: byTypeSeeds.map(([issue_type, injected, detected]) => ({ issue_type, injected, detected, recall: detected / injected })),
  investigation: {
    lead_time_mae_hours: 9.6,
    lead_time_within_1d_rate: 0.9,
    detection_rate: 1,
    no_false_hindsight_rate: 1,
    signals_without_churn_detection_rate: 0.857,
    outage_missing_evidence_findings: 0,
    lookahead_violations: 0,
  },
};

export const users: UserItem[] = [
  { id: "u-1", email: "admin@example.com", full_name: "Demo Admin", role: "admin", is_active: true, last_login_at: ago(5 * MIN) },
  { id: "u-2", email: "riya.sharma@example.com", full_name: "Riya Sharma", role: "analyst", is_active: true, last_login_at: ago(2 * HOUR) },
  { id: "u-3", email: "viewer@example.com", full_name: "Sam Viewer", role: "viewer", is_active: false, last_login_at: ago(20 * DAY) },
];

export const auditLog: AuditItem[] = [
  { id: "au-1", actor: "Riya Sharma", action: "investigation.start", target_type: "entity", target_id: "e-02", created_at: ago(2 * HOUR) },
  { id: "au-2", actor: "Riya Sharma", action: "finding.transition", target_type: "finding", target_id: "f-1003", created_at: ago(90 * MIN) },
  { id: "au-3", actor: "Demo Admin", action: "rule.update", target_type: "rule", target_id: "R010", created_at: ago(DAY) },
  { id: "au-4", actor: "Demo Admin", action: "simulation.start", target_type: "simulation_run", target_id: "r-12", created_at: ago(26 * HOUR) },
];

// First detectable = first checkpoint at or above the threshold (03 §M14), derived so the demo stays consistent.
for (const inv of investigations) {
  if (inv.outcome !== "crossed") continue;
  const first = checkpoints(inv.id).find((c) => c.risk_score >= inv.warning_threshold);
  if (!first) continue;
  inv.first_detectable_at = first.at;
  inv.lead_time_hours = Math.round((new Date(inv.incident.at).getTime() - new Date(first.at).getTime()) / HOUR);
}
