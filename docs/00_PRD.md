# 00 — Product Requirements Document (PRD)

**Product:** RealitySync
**Version:** 1.1 (MVP — revised after doc review 2026-10-08)
**Status:** Approved for implementation
**Doc owner:** Pranav
**Related docs:** 01_REQUIREMENTS · 02_ARCHITECTURE · 03_MODULES · 04_API_SPEC · 05_DATABASE_SCHEMA · 06_UI_STYLE_GUIDE · 07_AGENT_RULES · 08_PROGRESS_HANDOFF · 09_TASKS

---

## 1. Summary

RealitySync is an AI-assisted data-consistency monitor for enterprise systems. It continuously compares what **CRM**, **Billing**, and **Support** systems say about the same customer, detects where they disagree, scores how sure it is, explains the problem in plain language, and alerts people in real time.

> One-line pitch: *"Your systems disagree about reality. RealitySync finds where, proves it, and tells you why."*

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

### Non-goals (MVP)
- Automatically **fixing** data in source systems (write-back). RealitySync only detects, explains, and suggests.
- Connecting to real production systems (Salesforce, Stripe, Zendesk). The architecture allows it; MVP uses a simulator.
- Multi-tenancy, SSO/SAML, billing for RealitySync itself.
- Machine-learned matching models (rule-weighted fuzzy matching is used; ML is a Phase 2 idea).
- Mobile native apps (responsive web only).

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

## 6. Feature list and priority (MoSCoW)

### Must have
- Ingestion of records/events from CRM, Billing, Support (simulator + REST ingest API)
- Normalization (names, emails, phones, timestamps, statuses)
- Entity matching with confidence, thresholds, and manual review queue
- Rule-based contradiction detection (field, status, temporal/logic checks) — 15 rules at launch
- Evidence + confidence scoring per finding
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

### Won't have (MVP)
- Multi-tenancy, SSO, mobile apps, auto-remediation

## 6.1 Demo scenario (acceptance story)

1. Admin starts a simulation: 500 customers, 8% anomaly rate, seed 42.
2. Records stream into the three systems; dashboard fills live.
3. Findings appear in the live feed; a critical one triggers a toast.
4. Analyst opens "CRM active, billing cancelled" → sees side-by-side evidence, confidence ≈ 0.83 (worked example in 03 §M5), AI explanation.
5. Admin clicks **Simulate drift** → new conflicts appear within seconds.
6. Evaluation page shows precision/recall vs injected ground truth.

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

## 11. Milestones (suggested, adjust to available time)

| Milestone | Content | Target |
|-----------|---------|--------|
| M0 Foundation | Repo, tooling, auth, DB, UI shell | Week 1 |
| M1 Data pipeline | Simulator, ingest, normalization, matching | Week 2 |
| M2 Detection | Rule engine, scoring, findings, alerts | Week 3 |
| M3 Real-time + AI | WebSockets, Gemini explanations, dashboard live | Week 4 |
| M4 Polish | Evaluation page, hardening, README, demo video | Week 5 |

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

## 13. Open questions

| # | Question | Owner | Default until answered |
|---|----------|-------|------------------------|
| Q1 | Exact Gemini model name to use | Pranav | Configurable via `GEMINI_MODEL`; default `gemini-3.5-flash-lite`. As of 2026-10-08, Google limits Gemini 2.5 models to users who already used them. The T-029 agent re-verifies this against the docs. |
| Q2 | Available time budget | Pranav | Plan assumes ~5 weeks, flexible |
| Q3 | Deploy publicly (demo URL)? | Pranav | Docker Compose local only |
