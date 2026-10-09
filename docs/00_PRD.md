# 00 — Product Requirements Document (PRD)

**Product:** RealitySync — Organizational Reality Intelligence
**Version:** 1.2 (MVP — investigation features added 2026-10-10, T-052; design rationale in `docs/notes/2026-10-09-investigation-features-plan.md`)
**Status:** Approved for implementation
**Doc owner:** Pranav
**Related docs:** 01_REQUIREMENTS · 02_ARCHITECTURE · 03_MODULES · 04_API_SPEC · 05_DATABASE_SCHEMA · 06_UI_STYLE_GUIDE · 07_AGENT_RULES · 08_PROGRESS_HANDOFF · 09_TASKS

---

## 1. Summary

RealitySync is an AI-assisted data-consistency monitor for enterprise systems. It continuously compares what **CRM**, **Billing**, and **Support** systems say about the same customer, detects where they disagree, scores how sure it is, explains the problem in plain language, and alerts people in real time.

> One-line pitch: *"Your systems disagree about reality. RealitySync finds where, proves it, and tells you why."*

**Positioning (USP):** RealitySync reconstructs organizational events across disconnected systems and investigates when a problem first became detectable from the evidence available at the time, with traceable explanations for every finding.

Beyond "where do our systems disagree right now?", RealitySync answers **"at what point could we have detected this, using only the evidence available then?"** Four signature capabilities support that question:

| Capability | What it does |
|------------|--------------|
| **Organizational Time Machine** | Shows what the evidence showed — and what RealitySync would have concluded — at any past moment, using only data recorded by then |
| **"Could We Have Known?" investigation** | For an incident (e.g. a churn), finds the first moment a configured warning threshold was crossed and reports the lead time, with a mandatory retrospective caveat |
| **Evidence-to-Conclusion Trail** | Every conclusion is a chain of **facts** (what a source record states) → **inferences** (what RealitySync concludes) → conclusion; each fact links to the exact source record version |
| **Missing-Evidence Detector** | Reports expected evidence that is **unconfirmed** after a deadline, and says "cannot assess" when the source system's feed is silent — never claiming an action did not happen |

Engineering principles: time-aware analysis (no lookahead), fact vs inference separation, evidence provenance, and **risk ≠ confidence** (risk = how concerning; confidence = how well the evidence supports it).

## 2. Problem

Enterprises run many systems that each store a version of the same customer. Over time these versions drift:

- CRM shows a customer as **Active**; Billing shows the subscription **Cancelled** (revenue and forecasting errors).
- A support ticket is opened **before** the account exists (integration or data-entry bug).
- An invoice is issued **after** cancellation (customer-facing billing error).
- The same person exists twice with slightly different names/emails (duplicate/fragmented records).

Today these issues are found late — by angry customers, finance audits, or manual spreadsheet reconciliation. Teams lack a single tool that matches entities across systems, detects contradictions, and shows evidence.

## 3. Vision and goals

### Goals (MVP)
| ID | Goal | Measure |
|----|------|---------|
| G1 | Detect cross-system inconsistencies automatically | ≥ 90% precision and ≥ 85% recall on the synthetic benchmark |
| G2 | Match records of the same customer across systems despite messy data | ≥ 95% of ground-truth links found (auto-matched **or** needs-review) at default thresholds, and auto-match precision ≥ 0.99 (measured by the evaluation service, 03 §M9) |
| G3 | Give every finding evidence and a confidence score | 100% of findings have an evidence object and confidence ∈ [0,1] |
| G4 | Explain findings with AI in plain language | 100% of findings get an explanation (AI or fallback) eventually; p50 time-to-explanation < 10 s at steady state (≤ 1 new finding/s). Bursts are queued highest-priority first. |
| G5 | Real-time experience | Ingest → UI alert p95 < 2 s (excluding AI explanation) |
| G6 | Be a strong portfolio/resume artifact | Reproducible demo, measurable metrics, clean docs, README with GIF |
| G7 | Reconstruct when a problem first became detectable | On the synthetic benchmark: ≥ 90% of detectable churns get `first_detectable_at` within 1 day of the ground-truth crossing; ≥ 95% of undetectable churns correctly report "never crossed" (no false hindsight); the no-lookahead check passes on every evaluation |
| G8 | Find missing evidence without false accusations | Missing-evidence rules (R016–R018) meet G1's precision/recall, and a simulated feed outage produces zero missing-evidence findings ("cannot assess" instead) |

### Non-goals (MVP)
- Automatically **fixing** data in source systems (write-back). RealitySync only detects, explains, and suggests.
- Connecting to real production systems (Salesforce, Stripe, Zendesk). The architecture allows it; MVP uses a simulator.
- Multi-tenancy, SSO/SAML, billing for RealitySync itself.
- Machine-learned matching models (rule-weighted fuzzy matching is used; ML is a Phase 2 idea).
- Mobile native apps (responsive web only).
- A generic AI chatbot. AI only explains structured evidence; it never decides, detects or picks dates.
- Predicting the future (forecasting churn). Investigations are **retrospective**: they report when evidence crossed a configured threshold, not what will happen.

## 4. Users and personas

| Persona | Role | Needs | Key screens |
|---------|------|-------|-------------|
| **Riya — RevOps Analyst** (primary) | Reconciles CRM vs Billing | Prioritized list of conflicts, evidence, which system is probably right | Findings, Entity detail |
| **Arjun — Support/Ops Manager** | Watches data quality health | Live alerts, trend of issues, SLA on open findings | Dashboard, Alerts |
| **Meera — Platform Admin** | Configures the system | Manage rules, thresholds, source reliability, users, run simulations | Rules, Systems, Simulation, Users |

Roles in the product: `admin`, `analyst`, `viewer` (see 01_REQUIREMENTS §Security).

## 5. Core user stories

1. As an analyst, I see a live feed of new inconsistencies so I can react immediately.
2. As an analyst, I open a finding and see the exact records, fields, timestamps and rule that triggered it.
3. As an analyst, I read a plain-language explanation and a suggested next step for each finding.
4. As an analyst, I confirm or reject uncertain entity matches so the system learns what is the same customer.
5. As an analyst, I acknowledge, resolve, or mark findings as false positives with a note.
6. As a manager, I see an overall consistency score and trends by system and severity.
7. As an admin, I enable/disable rules, tune severity and thresholds, and set how much I trust each system per field.
8. As an admin, I run a simulation with injected issues and see precision/recall of detection.
9. As any user, I get toast/bell notifications without refreshing the page.
10. As an analyst, I travel back to a past date for a customer and see exactly which records existed then, what they said, and what RealitySync would have concluded — without any knowledge from later.
11. As an analyst, I click **Investigate this incident** on a churned customer and see when the configured warning threshold was first crossed, how many days before the churn, and which facts caused it.
12. As an analyst, I click any factor in a conclusion and see its source system, record, version and recorded time, clearly separated from RealitySync's inferences.
13. As an analyst, I see which expected evidence (a payment, a support response, an invoice) is unconfirmed after its deadline, and which cannot be assessed because a system's feed is silent.
14. As a manager, I see a customer's risk and RealitySync's confidence in that assessment as two separate numbers.

## 6. Feature list and priority (MoSCoW)

### Must have
- Ingestion of records/events from CRM, Billing, Support (simulator + REST ingest API)
- Normalization (names, emails, phones, timestamps, statuses)
- Entity matching with confidence, thresholds, and manual review queue
- Rule-based contradiction detection (field, status, temporal/logic checks) — 15 rules at launch (R001–R015)
- Missing-evidence detection (R016–R018) with `pending` / `unconfirmed` / `cannot_assess` outcomes
- Evidence + confidence scoring per finding, with an Evidence-to-Conclusion Trail (facts → inferences → conclusion)
- Organizational Time Machine (as-of view of any entity at any past moment, no lookahead)
- Deterministic risk signals per entity (risk score + separate risk confidence)
- "Could We Have Known?" investigations (first detectable moment, lead time, crossing trail, caveat)
- Finding lifecycle (open → acknowledged → resolved / false positive; auto-resolve)
- Alerts + WebSocket real-time updates
- AI explanations via Gemini with deterministic fallback
- Dashboard, Entities, Findings, Alerts, Rules, Systems, Simulation pages
- JWT auth with roles
- Synthetic data generator + anomaly injector + evaluation metrics

### Should have
- Entity timeline (history of record changes across systems)
- Bulk finding actions
- Audit log
- Per-field source authority ("which system is likely right")
- CSV export of findings

### Could have (Phase 2)
- Redis-backed event bus for multi-instance scaling
- Slack/email notification channels
- Real connectors (Stripe, Salesforce, Zendesk)
- ML-assisted matching and anomaly detection
- Write-back "fix it" suggestions as pull-requests/tickets
- Employee offboarding domain (HR termination → IT access revocation): new systems, record types and entity type (Q-006)
- Replay with the rule configuration that was active at the time (configuration history; MVP replays with today's configuration, recorded in every result — Q-009)
- AI narrative summary of an investigation (grounded in cited fact ids)
- "Knowledge time" replay axis (RealitySync receive time) for real integrations

### Won't have (MVP)
- Multi-tenancy, SSO, mobile apps, auto-remediation

## 6.1 Demo scenario (acceptance story)

1. Admin starts a simulation: 500 customers, 8% anomaly rate, seed 42 (includes churn scenarios with early warning signals).
2. Records stream into the three systems; dashboard fills live.
3. Findings appear in the live feed; a critical one triggers a toast.
4. Analyst opens "CRM active, billing cancelled" → sees the Evidence-to-Conclusion Trail (facts from CRM and Billing, the R004 inference), confidence ≈ 0.83 (worked example in 03 §M5), and an AI explanation that cites fact ids.
5. **Signature moment:** analyst opens a churned customer and clicks **Investigate this incident**. RealitySync replays the evidence: payment delayed (Billing) → complaints increased (Support) → warning threshold crossed → customer cancelled (CRM). Result: *"The configured warning threshold was first crossed 20 days earlier, based on the evidence available by that date"* — with the retrospective caveat always visible.
6. Analyst drags the Time Machine to the crossing date and sees exactly which records existed then; later records are absent.
7. A "Payment unconfirmed" missing-evidence finding shows the absence as a fact and the Billing feed watermark; for a system with a silent feed the UI says "cannot assess".
8. Admin clicks **Simulate drift** → new conflicts appear within seconds.
9. Evaluation page shows precision/recall vs injected ground truth, plus investigation lead-time accuracy and missing-evidence metrics.

## 7. Scope boundaries

| In scope | Out of scope |
|----------|--------------|
| Three source systems, four record types (account, subscription, invoice, ticket) | More than three systems at launch (architecture supports it) |
| Synthetic data only | Real PII or production data |
| English UI | Localization |
| Desktop + tablet + mobile-responsive web | Native apps |
| Gemini API for explanations | Self-hosted LLMs |

## 8. Success metrics

| Metric | Target |
|--------|--------|
| Detection precision / recall (synthetic) | ≥ 0.90 / ≥ 0.85 |
| Matching recall at auto threshold | ≥ 0.95 |
| Ingest→alert latency p95 | < 2 s |
| Dashboard initial load (10k entities) | < 2 s |
| Investigation lead-time accuracy (synthetic) | ≥ 90% within 1 day of ground truth (G7) |
| No false hindsight (undetectable churns reported "never crossed") | ≥ 95% (G7) |
| Missing-evidence findings during a simulated feed outage | 0 (G8) |
| As-of view for one entity, p95 | < 500 ms |
| Backend unit-test coverage of `domain/` | ≥ 85% |
| One-command local start | `make dev` works on a clean machine |

## 9. Assumptions

- Source systems expose records with an external id and `created_at`/`updated_at` timestamps.
- Email and phone are the strongest identity signals; names are noisy.
- Gemini API access is available with an API key; free-tier rate limits apply.
- Development uses **multiple AI coding agents** working in parallel; therefore all work is contract-first and tracked in `09_TASKS.md` / `08_PROGRESS_HANDOFF.md`.

## 10. Risks and mitigations

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Too many false positives | Users ignore alerts | Confidence thresholds, false-positive suppression, evaluation page for tuning |
| LLM hallucination | Wrong explanations | Send structured evidence only; JSON schema output; show evidence beside text; fallback templates |
| Gemini rate limits / outages | Missing explanations | Cache by input hash, concurrency cap, fallback explanation, retry with backoff |
| Agents conflict or drift from contracts | Rework | `07_AGENT_RULES`, task `Touches` lists, contract-change procedure, handoff file |
| Scope creep | Missed demo | MoSCoW list above; Could-haves frozen until Must-haves are done |
| Real-time bugs (duplicate/out-of-order events) | Wrong UI state | Idempotent events with ids, versioned envelopes, client de-duplication |

## 11. Milestones (ordered; no fixed dates — the product owner removed the timeline constraint on 2026-10-09)

| Milestone | Content |
|-----------|---------|
| M0 Foundation | Repo, tooling, auth, DB, UI shell |
| M1 Data pipeline | Simulator, ingest, normalization, matching |
| M2 Detection | Rule engine, scoring + trail, findings, alerts, missing-evidence rules |
| M3 Real-time + AI | WebSockets, Gemini explanations (fact citations), dashboard live |
| M5 Investigation | Time Machine (as-of), risk signals, "Could We Have Known?" investigations and their UI |
| M4 Polish | Evaluation (incl. investigation metrics), hardening, README, demo video |

The core investigation workflow must work end to end before real-time polish (WebSocket niceties, PgNotify) gets attention.

The exact task list for each milestone is in `09_TASKS.md` → "Milestone mapping".

## 12. Glossary

| Term | Meaning |
|------|---------|
| Source system | CRM, Billing, or Support — an upstream system of record |
| Source record | A record as stored in one source system |
| Entity | The canonical customer RealitySync believes several source records represent |
| Link | Association between a source record and an entity, with match confidence |
| Rule | A deterministic check that can produce a finding |
| Finding | A detected inconsistency with evidence, severity, and confidence |
| Evidence | Structured proof: records, fields, values, timestamps, rule |
| Alert | A notification derived from a finding event |
| Authority | How much a system is trusted for a given field |
| Ground truth | The simulator's record of which source records belong to which real customer, and which anomalies were injected |
| Decoy | A harmless variation (nickname, formatting) the simulator adds on purpose; it must **not** produce a finding |
| Detection queue | The durable list of entities waiting for their rules to be re-run (`entities.detection_requested_at`) |
| Recorded time | When a source system recorded a version of a record (`record_versions.source_updated_at`). The Time Machine's only time axis. |
| Effective time | When a business event happened according to the record (`paid_at`, `cancelled_at`, …). Never used to decide what was known. |
| As-of view | An entity reconstructed from the versions recorded at or before a moment T, evaluated with `now = T` |
| Fact | What a source record states (or, for an `absence` fact, what our data does not contain up to a time) — with system, record, version and recorded time |
| Inference | What RealitySync concludes from facts (a rule result, a risk signal, a suggested authority) |
| Trail | Facts → inferences → conclusion, stored with every finding and risk assessment |
| Expectation | Evidence a missing-evidence rule expects by a deadline; outcome `pending`, `unconfirmed` or `cannot_assess` |
| Feed watermark | The latest recorded time received from a source system; evidence can only be called missing when the watermark is past the deadline |
| Risk / Risk confidence | Risk = how concerning a situation is (0–1, level); risk confidence = how much of the evidence the assessment needs is available and fresh. Always shown separately. |
| Investigation | A deterministic replay of an entity's history that finds the first checkpoint where risk crossed the warning threshold (`first_detectable_at`) and the lead time before an incident |

## 13. Open questions

| # | Question | Owner | Default until answered |
|---|----------|-------|------------------------|
| Q1 | Exact Gemini model name to use | Pranav | Configurable via `GEMINI_MODEL`; default `gemini-3.5-flash-lite`. As of 2026-10-08, Google limits Gemini 2.5 models to users who already used them. The T-029 agent re-verifies this against the docs. |
| Q2 | Available time budget | Pranav | Answered 2026-10-09: no timeline constraint |
| Q3 | Deploy publicly (demo URL)? | Pranav | Docker Compose local only |
