# Investigation features plan — Time Machine, Evidence Trail, Missing Evidence, "Could We Have Known?"

- **Date:** 2026-10-09 · **Author:** `claude-code-1` · **Status:** proposal (not a contract)
- **Source:** product owner direction, 2026-10-09 (new signature features; the 2–3 week timeline in that direction was explicitly excluded).
- **Becomes contract through:** task **T-052** (contract update, docs 00–06), after the open questions in §8 are answered.

---

## 1. New positioning

**RealitySync — Organizational Reality Intelligence.**

> RealitySync reconstructs organizational events across disconnected systems and investigates when a problem first became detectable from the evidence available at the time, with traceable explanations for every finding.

The question the product answers changes from *"where do our systems disagree right now?"* to also *"at what point could we have detected this, using only the evidence available then?"*

The existing contradiction detector (R001–R015) stays. It becomes one source of evidence for investigations.

| Signature feature | Priority | One-line definition |
|---|---|---|
| Organizational Time Machine | 1 | Show what the evidence showed, and what RealitySync would have concluded, at any past moment |
| "Could We Have Known?" investigation | 1 (demo centrepiece) | For an incident, find the first moment a configured warning threshold was crossed using only evidence recorded by then |
| Evidence-to-Conclusion Trail | 2 | Every conclusion is a chain of facts → inferences → conclusion, each fact clickable to its source record version |
| Missing-Evidence Detector | 3 | Report expected evidence that is **unconfirmed** after a deadline, never claiming it "did not happen" |

Four engineering principles from the same direction become invariants (§6): time-aware analysis (no lookahead), fact vs inference separation, evidence provenance, risk ≠ confidence.

---

## 2. Why this fits the existing architecture

The planned design already contains the three properties time travel needs:

1. **Rules are pure functions of an `EntityContext` that includes `now`** (03 §M4; `domain/` cannot read the clock). Re-running them with `now = T` and the data known at `T` is a replay, not a new engine.
2. **Every record keeps its full version history** (`record_versions`, 05 §2.6.1) with `source_updated_at` and an index on `(source_record_id, source_updated_at DESC)`. "The latest version recorded at or before T" is one indexed query.
3. **Detection is deterministic** (D-009). The same inputs always produce the same findings, so a past conclusion can be reconstructed exactly and tested.

So the new work is mostly **an as-of context builder plus new consumers of it**, not a rewrite.

One conflict must be resolved: **T-047 (retention prune) deletes non-current record versions**, which would destroy the history the Time Machine reads. See Q-008.

---

## 3. Feature designs

### 3.1 Two time axes (foundation for everything below)

| Axis | Meaning | Where it lives |
|---|---|---|
| **Recorded time** | When the source system recorded this version of the record | `record_versions.source_updated_at` (already exists) |
| **Effective time** | When the business event happened, per the record | Payload dates: `paid_at`, `cancelled_at`, `opened_at`, … |

**As-of T** always filters on **recorded time ≤ T**. A version recorded on Oct 12 with `paid_at = Oct 5` (a backdated entry) is **not** visible at Oct 10, even though its effective date is earlier. That is the whole point: it reflects what the organization's systems actually held on Oct 10.

RealitySync's own receive time (`ingest_events.received_at`) is not used for replay, because the simulator compresses months of business time into minutes. For real integrations later, a "knowledge time" option can switch the filter to `received_at`.

### 3.2 Organizational Time Machine

- **Snapshot builder** (`services/snapshot_service.py`, new): `build_context_as_of(entity_id, T) -> EntityContext`
  - For every record ever linked to the entity, take the latest version with `source_updated_at ≤ T`. Records with no version by T don't exist yet; versions with `is_deleted` are excluded.
  - **No identity lookahead:** re-score the entity's account links using the as-of versions with the pure matcher (`domain/matching`). Accounts that were not yet linkable at T (score < `MATCH_REVIEW`) are excluded and listed as `not_yet_linkable`. Without this, a link discovered from an email added later would leak future knowledge.
  - `ctx.now = T`.
- **Run current rules and risk signals** on that context. The output records the `rule_set` used (keys, versions, config hash) because replay uses **today's** configuration (Q-009).
- **Nothing is written to `findings`.** As-of results are computed views; only investigations persist them (§3.5).
- **API (proposed):** `GET /entities/{id}/as-of?at=<ISO8601>` → records (with version used), facts, findings-as-of, risk-as-of, `not_yet_linkable`, `rule_set`.

### 3.3 Evidence-to-Conclusion Trail

The evidence object (03 §M5) gains a `trail`, built **deterministically by rules**; the LLM never adds facts:

```json
"trail": {
  "facts": [
    {"id": "f1", "kind": "record_field", "system": "billing", "record_id": "…", "external_id": "B-5521",
     "record_type": "invoice", "version": 3, "field": "paid_at", "value": null,
     "recorded_at": "2026-10-03T09:00:00Z"},
    {"id": "f2", "kind": "absence", "system": "billing", "expected": "invoice payment",
     "checked_until": "2026-10-10T00:00:00Z", "feed_watermark": "2026-10-11T08:00:00Z"}
  ],
  "inferences": [
    {"id": "i1", "rule_key": "R016", "rule_version": 1, "uses": ["f1", "f2"],
     "statement": "Payment unconfirmed 7 days after due date", "config_used": {"grace_days": 7}}
  ],
  "conclusion": {"uses": ["i1"], "risk": "high", "confidence": 0.82}
}
```

- **Facts** are what a source record states (or, for `absence`, what our data does *not* contain up to a time). **Inferences** are what RealitySync concludes. The UI renders them differently and never mixes them.
- **Provenance:** every `record_field` fact points to an exact record version (`GET /records/{id}` already returns versions).
- **`evidence_hash` is unchanged** (`{rule_key, fields, timestamps}`); the trail is excluded, so adding it causes no reopen churn (D-018 still holds).
- **AI explanations cite facts:** the response schema gains `cited_fact_ids`, validated as a subset of the trail's ids; an invalid citation falls back to the template. `suggested_authority` is relabelled as an inference.

### 3.4 Missing-Evidence Detector

A new rule category **`missing_evidence`** runs in the existing rule engine (same registry, lifecycle, alerts and auto-resolve).

Three outcomes per expectation:

| Outcome | Condition | Result |
|---|---|---|
| `pending` | Trigger seen; deadline not passed | Nothing (visible in the as-of view only) |
| `unconfirmed` | Deadline passed, expected evidence absent, **and the expected system's feed has data recorded after the deadline** | Finding, titled "… unconfirmed …" |
| `cannot_assess` | Deadline passed but the expected system has sent nothing recorded after the deadline (feed gap) | **No finding**; shown on system health as "cannot assess" |

The `cannot_assess` state is what separates "a record is missing" from "the action never happened". It needs a per-system watermark, `source_systems.last_recorded_at` (max `source_updated_at` received; maintained by ingest).

When the evidence arrives, the finding auto-resolves through the existing `auto_resolved` transition, and the trail shows when it arrived.

**Proposed rules (customer domain, existing record types):**

| Key | Name | Trigger → expected evidence | Deadline (config) | Needs |
|---|---|---|---|---|
| R016 | Payment unconfirmed | Invoice `issued` → `paid_at` recorded | `due_at` + `grace_days` (7) | New optional invoice field `due_at`; fallback `issued_at + payment_terms_days` (15) |
| R017 | Support response unconfirmed | Ticket with `priority ∈ {high, urgent}` opened → `first_response_at` recorded | `response_sla_hours` (24) | New optional ticket field `first_response_at` |
| R018 | Invoice unconfirmed for active subscription | Subscription `active` → an invoice issued in each billing period | `invoice_gap_days` (35) | — |

Also proposed: give R004/R005 an optional `propagation_grace_days` (default 0, so behaviour is unchanged) so a cancellation still propagating between systems can be treated as pending rather than a contradiction.

Employee offboarding (HR termination → IT access revocation, the example in the direction) needs new systems (`hr`, `it`), new record types and a second entity type. That is proposed as a later expansion (Q-006).

### 3.5 "Could We Have Known?" investigation

- **Input:** `POST /investigations {entity_id, incident: {kind: "churn" | "finding", at?, record_id?, finding_id?}, warning_threshold?, lookback_days?}`. Default incident = the churn: the first recorded CRM `churned` or Billing subscription `cancelled`.
- **Algorithm (deterministic, bounded):**
  1. Checkpoints = sorted distinct recorded times of the entity's versions in `[incident − lookback, incident)`, **plus** deadline-crossing times (e.g. `due_at + grace`) computed from facts known at the time, because risk can change with the passage of time alone.
  2. At each checkpoint `T`: `build_context_as_of(entity, T)` → findings-as-of + risk-as-of.
  3. `first_detectable_at` = the earliest `T` with `risk_score ≥ warning_threshold` (or, for `kind = finding`, the earliest `T` where that finding's fingerprint appears). `lead_time = incident_at − first_detectable_at`.
- **Output:** a timeline of checkpoints (facts added at each step, risk score, crossing marker), the trail at the crossing point, the `rule_set` used, and a **mandatory caveat**: *"Retrospective finding: the evidence available on <date> crossed the configured threshold. This is not proof that the outcome was inevitable or that anyone knew."*
- **No result** is a valid, honest outcome: "The threshold was never crossed before the incident with the evidence available at the time."
- **Persistence:** `investigations` (inputs, status, result, `inputs_hash`, created_by) and `investigation_checkpoints` (as_of, risk_score, risk_level, findings snapshot, facts added). Same inputs give an identical result; this is tested.
- **AI:** an optional narrative summary of the investigation, grounded in cited fact ids. It never chooses dates or thresholds.

### 3.6 Risk vs confidence, and the churn-risk model (new module M12)

- **Risk** = how concerning the situation is. **Confidence** = how well the available evidence supports the assessment. They are shown as two separate values everywhere; `priority_score` stays only as a sort key.
- For contradiction findings, risk = the existing severity; confidence = the existing formula (03 §M5).
- **M12 Risk Signals** (`domain/risk/`, pure, deterministic; consistent with D-009, no ML):

| Signal | From | Normalized 0..1 |
|---|---|---|
| `payment_delay` | invoices: days past `due_at`, late payments in the last 90 days | capped linear in days overdue |
| `complaint_trend` | tickets: last 30 days vs the previous 60-day baseline; high-priority count | ratio above baseline, capped |
| `commercial_decline` | subscriptions/invoices: plan downgrade, quantity decrease, invoice amount drop in 90 days | stand-in for "orders declined" (Q-007) |
| `open_inconsistencies` | open high/critical findings on the entity | count-based, capped |

  `risk_score = Σ weight × signal` (weights in config). Levels: `watch ≥ 0.40`, `warning ≥ 0.60`, `critical ≥ 0.80`. **Risk confidence** = data coverage: the share of signal inputs present and fresh (e.g. no Support data → lower confidence).
- **Live:** recomputed in the detection loop; current value stored per entity; a new alert type `risk_threshold_crossed` fires when the level rises.

### 3.7 Simulation & evaluation

The synthetic benchmark must measure the new features, as it already does for rules (FR-SIM-004/008).

- **Generator:** month-scale histories with realistic recorded times; invoices get `due_at`; tickets get `priority` and `first_response_at`.
- **New scenario types (ground truth in `injected_issues`):**

| Scenario | Ground truth | Measures |
|---|---|---|
| `churn_with_early_signals` | Signals begin X days before churn; expected crossing date | Lead-time accuracy |
| `churn_without_signals` | Undetectable by design | Investigation must not claim early detection |
| `signals_without_churn` | Warning crossed, no churn | False early-warning rate |
| `payment_never_recorded` | R016 expected | Missing-evidence precision/recall |
| `support_response_missing` | R017 expected | 〃 |
| `invoice_feed_gap` | R018 expected | 〃 |
| Decoy: `late_within_grace` | Evidence arrives before the deadline | Must not fire |
| Decoy: `system_feed_outage` | Whole system silent | Must give `cannot_assess`, not findings |

- **New metrics:** lead-time absolute error, detectable-churn detection rate, false early-warning rate, missing-evidence precision/recall, and a **no-lookahead check** (§6, invariant 9) run on every evaluation.

---

## 4. Contract changes (to be made in T-052)

| Doc | Change |
|---|---|
| 00 PRD | New positioning and USP; goals G7 (investigation lead-time accuracy) and G8 (missing-evidence precision/recall); demo scenario rewritten around "Investigate this incident"; non-goals add "generic chatbot" |
| 01 Requirements | New FR groups: `FR-TMX` (as-of), `FR-TRL` (trail), `FR-MEV` (missing evidence), `FR-INV` (investigation), `FR-RSK` (risk); NFR-DAT-002 changed per Q-008; FR-SIM additions |
| 02 Architecture | `snapshot_service`, `investigation_service`, `domain/risk/`; data-flow diagram; ADR: "replay through pure rules, recorded-time axis" |
| 03 Modules | M12 Risk Signals; M13 Investigation; M4 category `missing_evidence` + R016–R018; M5 trail + `cited_fact_ids`; M9 scenarios/metrics; invariants 9–11 |
| 04 API | `GET /entities/{id}/as-of`, `POST/GET /investigations`, `GET /investigations/{id}`; evidence schema `trail`; explanation `cited_fact_ids`; WS `investigation.progress`/`completed`, `risk.changed`; alert type `risk_threshold_crossed`; optional ingest fields `invoice.due_at`, `ticket.first_response_at` |
| 05 Database | `investigations`, `investigation_checkpoints`, `entity_risk` (current) + `risk_events`; `rules.category` CHECK adds `missing_evidence`; `source_systems.last_recorded_at`; `injected_issues` scenario types |
| 06 UI | Time Machine scrubber, investigation timeline, trail view (fact vs inference styling), risk vs confidence display. **Held until the product owner's frontend changes are in** (see §7) |

---

## 5. Changes to existing tasks (made in T-052)

| Task | Change |
|---|---|
| T-013 / T-014 | Month-scale histories, `due_at`, `first_response_at`; new scenario types (or split into T-057) |
| T-019 | Context builder exposes a seam for as-of loading (same `EntityContext` type) |
| T-024 | Evidence `trail` (facts / inferences / conclusion) built from `FindingCandidate` |
| T-029 / T-030 | `cited_fact_ids` in the schema, validated; fallback on invalid citations |
| T-033 | Drawer shows the trail with fact/inference distinction (UI held, §7) |
| T-039 | Adds the investigation and missing-evidence metrics (or via T-058) |
| T-041 | Demo seed includes a completed "Could we have known?" investigation |
| T-047 | Prunes only processed ingest events; record versions kept (Q-008) |
| T-031 | Dashboard charts that do not support an investigation are de-scoped or replaced (part of the frontend review) |

---

## 6. New invariants (tests must assert)

9. **No lookahead:** the as-of result for time T is byte-identical whether computed before or after any data recorded after T is ingested (property test: ingest history up to T → compute; ingest the rest → recompute as-of T → equal).
10. **Fact/inference separation:** every inference cites at least one fact; every AI-cited fact id exists in the trail; facts never contain RealitySync conclusions.
11. **Missing ≠ never happened:** a missing-evidence rule never fires while the expected system's watermark is before the deadline (gives `cannot_assess` instead).

---

## 7. Sequencing

1. **T-051** foundation repair (in review).
2. **T-052** contract update: blocked on the decisions in §8.
3. The core pipeline continues as planned (ingest → matching → rules → scoring), now with the trail and as-of seam built in from the start.
4. New backend tasks: T-053 as-of snapshot → T-054 missing-evidence rules → T-055 risk signals → T-056 investigation engine; simulation scenarios (T-057) and evaluation (T-058) alongside.
5. **Frontend (T-004 onward, and T-059 investigation UI) waits for the product owner's frontend changes.** No frontend implementation starts before that conversation.

Lower priority, in line with the direction ("don't build complicated real-time infrastructure before the core works"): T-050 stays P2; WebSocket work stays, but the investigation flow must work without it.

---

## 8. Decisions needed from the product owner

| ID | Question | Recommendation |
|---|---|---|
| Q-006 | Missing-evidence scope: customer domain only (R016–R018), or also HR/IT employee offboarding (new systems, record types, entity type)? | Customer domain now; offboarding as a later expansion |
| Q-007 | "Orders declined" signal: there is no order data. Use subscription downgrade / quantity / invoice-amount decline as a proxy, or add an `order` record type? | Proxy (no new record type) |
| Q-008 | Retention: stop pruning record versions (the Time Machine needs them), or keep a configurable history horizon? | Keep all versions; prune only processed ingest events |
| Q-009 | Replay with **today's** rule configuration (recorded in each result), or keep a configuration history and replay with **then-current** config? | Today's config, recorded; config history later |
| Q-010 | Investigation incident types for the first version: churn only, or also "first appearance of any finding"? | Both (the second is nearly free) |
| Q-011 | Adopt "RealitySync — Organizational Reality Intelligence" and the USP above in the PRD? | Yes |
