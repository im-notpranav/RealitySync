// Response shapes from 04_API_SPEC.md. Replaced by generated types (`make api-types`) once the backend serves them.

export type Severity = "low" | "medium" | "high" | "critical";
export type FindingStatus = "open" | "acknowledged" | "resolved" | "false_positive" | "auto_resolved";
export type SystemKey = "crm" | "billing" | "support";
export type RiskLevel = "low" | "watch" | "warning" | "critical";
export type Health = "consistent" | "inconsistent" | "unknown";
export type LinkStatus = "auto_matched" | "needs_review" | "confirmed" | "rejected";
export type RuleCategory = "field_conflict" | "logic" | "temporal" | "structural" | "missing_evidence";
export type AlertType =
  | "finding_created"
  | "finding_escalated"
  | "finding_resolved"
  | "link_needs_review"
  | "risk_threshold_crossed";
export type UserRole = "admin" | "analyst" | "viewer";

export interface ConfidenceBreakdown {
  link: number;
  rule: number;
  evidence: number;
  recency: number;
}

export interface FindingListItem {
  id: string;
  entity_id: string;
  entity_name: string;
  rule_key: string;
  title: string;
  severity: Severity;
  status: FindingStatus;
  confidence: number;
  priority_score: number;
  systems: SystemKey[];
  first_detected_at: string;
  last_detected_at: string;
  reopen_count: number;
  sla_breached: boolean;
  has_explanation: boolean;
}

/** 03 §M5 trail. */
export interface TrailFact {
  id: string;
  kind: "record_field" | "absence";
  system: SystemKey;
  record_id?: string;
  external_id?: string;
  record_type?: string;
  version?: number;
  field?: string;
  value?: string;
  recorded_at?: string;
  expected?: string;
  deadline?: string;
  checked_until?: string;
  feed_watermark?: string | null;
}

export interface TrailInference {
  id: string;
  kind: "rule" | "authority" | "risk_signal" | "risk_level";
  uses: string[];
  statement: string;
  rule_key?: string;
}

export interface Trail {
  facts: TrailFact[];
  inferences: TrailInference[];
  conclusion: {
    kind: "finding" | "risk";
    rule_key?: string;
    risk: string;
    confidence: number;
    score?: number;
    uses: string[];
  };
}

export interface Explanation {
  id: string;
  summary: string;
  root_cause: string;
  likely_correct_system: SystemKey | "undetermined";
  suggested_actions: string[];
  caveats: string;
  cited_fact_ids: string[];
  model: string;
  is_fallback: boolean;
  created_at: string;
}

export interface FindingDetail extends FindingListItem {
  rule: { key: string; name: string; category: RuleCategory };
  confidence_breakdown: ConfidenceBreakdown;
  evidence: {
    fields: { field: string; values: Partial<Record<SystemKey, string>> }[];
    timestamps: Record<string, string>;
    suggested_authority?: { field: string; likely_correct: SystemKey | null; reason: string };
    trail: Trail;
  };
  explanation: Explanation | null;
  history: { at: string; action: string; by?: string; note?: string }[];
  resolved_at: string | null;
}

export type RiskSignalName = "payment_delay" | "complaint_trend" | "commercial_decline" | "open_inconsistencies";

export interface RiskAssessment {
  score: number;
  level: RiskLevel;
  confidence: number;
  model_version: number;
  assessed_at: string;
  signals: Record<RiskSignalName, { value: number; available: boolean; weight: number }>;
  trail: Trail;
}

export interface RiskSummary {
  score: number;
  level: RiskLevel;
  confidence: number;
}

export interface EntityListItem {
  id: string;
  canonical_name: string;
  canonical_email: string | null;
  health: Health;
  open_findings_count: number;
  highest_severity: Severity | null;
  risk: RiskSummary | null;
  systems: SystemKey[];
  updated_at: string;
}

export interface SourceRecord {
  id: string;
  system: SystemKey;
  type: "account" | "subscription" | "invoice" | "ticket";
  external_id: string;
  normalized: Record<string, string | null>;
  source_updated_at: string;
  version: number;
}

export interface EntityRecordLink {
  link_id: string;
  link_status: LinkStatus;
  match_confidence: number;
  match_features: Record<string, number>;
  record: SourceRecord;
}

export interface Expectation {
  rule_key: string;
  outcome: "pending" | "cannot_assess";
  trigger_record_id: string;
  expected: string;
  system: SystemKey;
  deadline: string;
  feed_watermark: string | null;
}

export interface EntityDetail {
  id: string;
  canonical_name: string;
  canonical_email: string | null;
  health: Health;
  records: EntityRecordLink[];
  children: { subscriptions: SourceRecord[]; invoices: SourceRecord[]; tickets: SourceRecord[] };
  open_findings: Pick<FindingListItem, "id" | "rule_key" | "severity" | "confidence" | "status" | "title">[];
  risk: RiskAssessment | null;
  expectations: Expectation[];
}

export interface TimelineItem {
  at: string;
  system: SystemKey;
  record_type: string;
  external_id: string;
  changed_fields: string[];
  summary: string;
  out_of_order: boolean;
}

export interface AsOfView {
  entity_id: string;
  at: string;
  records: { link: { status: LinkStatus; match_confidence: number }; record: SourceRecord & { recorded_at: string } }[];
  not_yet_linkable: { record_id: string; system: SystemKey; external_id: string }[];
  findings: (Pick<FindingListItem, "rule_key" | "title" | "severity" | "confidence"> & {
    fingerprint: string;
    live_finding_id: string | null;
  })[];
  expectations: Expectation[];
  risk: RiskAssessment;
  feed_watermarks: Record<SystemKey, string | null>;
  rule_set: { hash: string; risk_model_version: number };
  caveat: string;
}

export interface Alert {
  id: string;
  type: AlertType;
  severity: Severity;
  title: string;
  body: string;
  finding_id: string | null;
  entity_id: string | null;
  link_id: string | null;
  created_at: string;
  is_read: boolean;
}

export interface DashboardSummary {
  entities: number;
  systems: number;
  open_findings: number;
  needs_review_links: number;
  consistency_score: number | null;
  by_severity: Record<Severity, number>;
  by_status: Record<FindingStatus, number>;
  by_system: Record<SystemKey, number>;
  by_rule: { rule_key: string; count: number }[];
  explained_share: number;
  new_today: number;
  consistency_delta: number;
  at_risk: { total: number; critical: number; avg_confidence: number };
  ingest: { events_per_sec: number; pending: number; detection_pending: number; avg_detect_ms: number };
  generated_at: string;
}

export interface TrendPoint {
  date: string;
  created: number;
  resolved: number;
  open_end_of_day: number;
}

export interface SystemHealth {
  key: SystemKey;
  name: string;
  open_issues: number;
  last_event_at: string | null;
  records: number;
}

export interface LinkReviewItem {
  id: string;
  score: number;
  features: Record<string, number>;
  left: SourceRecord;
  right: SourceRecord;
  entity_id: string;
  created_at: string;
}

export interface Investigation {
  id: string;
  entity_id: string;
  entity_name: string;
  incident: { kind: "churn" | "finding"; finding_id: string | null; at: string };
  lookback_days: number;
  warning_threshold: number;
  status: "queued" | "running" | "completed" | "failed";
  progress: { checkpoints_done: number; checkpoints_total: number };
  outcome: "crossed" | "never_crossed" | null;
  first_detectable_at: string | null;
  lead_time_hours: number | null;
  caveat: string | null;
  rule_set_hash: string;
  requested_by: string;
  created_at: string;
  completed_at: string | null;
  at_crossing: { risk: RiskAssessment } | null;
}

export interface Checkpoint {
  at: string;
  risk_score: number;
  risk_level: RiskLevel;
  risk_confidence: number;
  finding_count: number;
}

export interface Rule {
  id: string;
  key: string;
  name: string;
  category: RuleCategory;
  description: string;
  severity: Severity;
  default_severity: Severity;
  is_enabled: boolean;
  certainty: number;
  version: number;
  open_findings: number;
}

export interface SourceSystem {
  id: string;
  key: SystemKey;
  name: string;
  is_active: boolean;
  reliability_weight: number;
  field_authority: Record<string, number>;
  record_counts: Record<string, number>;
  last_event_at: string | null;
}

export interface FailedEvent {
  id: string;
  source: SystemKey;
  record_type: string;
  external_id: string;
  attempts: number;
  error: string;
  received_at: string;
}

export interface Evaluation {
  precision: number;
  recall: number;
  f1: number;
  true_positives: number;
  false_positives: number;
  false_negatives: number;
  ignored: number;
  matching: { auto_precision: number; recall_auto_or_review: number; true_pairs: number };
  by_type: { issue_type: string; injected: number; detected: number; recall: number }[];
  investigation: {
    lead_time_mae_hours: number;
    lead_time_within_1d_rate: number;
    detection_rate: number;
    no_false_hindsight_rate: number;
    signals_without_churn_detection_rate: number;
    outage_missing_evidence_findings: number;
    lookahead_violations: number;
  };
}

export interface SimulationRun {
  id: string;
  status: "running" | "completed" | "stopped" | "failed";
  seed: number;
  customers: number;
  progress: { events_sent: number; events_total: number };
  injected_issues: number;
  started_at: string;
  ended_at: string | null;
}

export interface UserItem {
  id: string;
  email: string;
  full_name: string;
  role: UserRole;
  is_active: boolean;
  last_login_at: string | null;
}

export interface AuditItem {
  id: string;
  actor: string;
  action: string;
  target_type: string;
  target_id: string | null;
  created_at: string;
}
