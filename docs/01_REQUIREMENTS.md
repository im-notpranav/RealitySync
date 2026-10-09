# 01 — Requirements Document

Keywords **MUST**, **SHOULD**, **MAY** follow RFC 2119. Every requirement has an ID. Tasks in `09_TASKS.md` and tests reference these IDs.

---

## 1. Functional requirements

### 1.1 Source systems and ingestion (ING)
| ID | Requirement | Priority |
|----|-------------|----------|
| FR-ING-001 | The system MUST support three source systems at launch: `crm`, `billing`, `support`, seeded on first start. | Must |
| FR-ING-002 | The system MUST accept record events through `POST /api/v1/ingest/events` (batch up to 500). | Must |
| FR-ING-003 | Supported record types: `account`, `subscription`, `invoice`, `ticket`. | Must |
| FR-ING-004 | Each event MUST carry: source key, record type, external id, event type (`upsert`/`delete`), payload, and source timestamp. | Must |
| FR-ING-005 | Ingestion MUST be idempotent: replaying the same event MUST NOT create duplicate records or findings. | Must |
| FR-ING-006 | Ingest MUST persist the event durably before acknowledging (HTTP 202) and process it asynchronously. | Must |
| FR-ING-007 | The system MUST keep a version history of each record (`record_versions`) including changed fields. | Must |
| FR-ING-008 | Out-of-order events (older `source_updated_at` than stored) MUST be stored as history but MUST NOT overwrite current state. Events for the same record MUST be applied one at a time (per-record lock); on equal `source_updated_at` the later-received event wins (`received_at`, then `id`). | Must |
| FR-ING-009 | Failed events MUST be marked `failed` with an error message and be retryable by admins. | Should |
| FR-ING-010 | Ingest MUST authenticate with an API key (`X-API-Key`) or an admin JWT. | Must |
| FR-ING-011 | Optional payload fields `invoice.due_at` and `ticket.first_response_at` MUST be accepted and normalized (04 §5.1); ticket `priority` is normalized to `low`, `normal`, `high`, `urgent` (unknown → `null`). | Must |

### 1.2 Normalization (NRM)
| ID | Requirement |
|----|-------------|
| FR-NRM-001 | Names MUST be normalized: trim, Unicode NFKC, case-fold, remove punctuation/titles/suffixes, collapse spaces, token sort for comparison. |
| FR-NRM-002 | Emails MUST be lower-cased and validated; Gmail-style dots and `+tag` MUST be ignored for matching but preserved for display. |
| FR-NRM-003 | Phones MUST be parsed to E.164 using a default region (`IN`, configurable). Unparseable values are kept raw and flagged. |
| FR-NRM-004 | Timestamps MUST be stored as UTC `timestamptz`. Naive inputs (no timezone) MUST be rejected at ingest with `VALIDATION_ERROR` (04 §1.5). Epoch seconds are accepted as UTC. |
| FR-NRM-005 | Statuses MUST be mapped to canonical vocabulary via per-system mapping (e.g., CRM `Customer`→`active`, Billing `canceled`→`cancelled`). |
| FR-NRM-006 | Normalization MUST be pure and deterministic (no I/O) and fully unit-tested. |

### 1.3 Entity resolution (ENT)
| ID | Requirement | Priority |
|----|-------------|----------|
| FR-ENT-001 | The system MUST link `account` records across systems into canonical **entities**. | Must |
| FR-ENT-002 | Candidate generation MUST use blocking keys (normalized email, E.164 phone, phonetic last name + first initial) across **all** systems, including the record's own system (needed to detect duplicates, R012). | Must |
| FR-ENT-003 | Match score MUST be a weighted combination of feature similarities (see 03_MODULES §M3) in [0,1]. | Must |
| FR-ENT-004 | Thresholds: score ≥ `MATCH_AUTO` (0.85) → auto-link; `MATCH_REVIEW` (0.60) ≤ score < 0.85 → `needs_review`; < 0.60 → no link. Both configurable. | Must |
| FR-ENT-005 | Child records (`subscription`, `invoice`, `ticket`) MUST attach to the entity of their parent account via `parent_external_id`. Children that arrive before their parent are held unlinked and MUST be attached when the parent account is linked. | Must |
| FR-ENT-006 | Analysts MUST be able to confirm or reject uncertain links; a rejected link MUST NOT be re-proposed. | Must |
| FR-ENT-007 | When identity fields change, links MUST be re-evaluated. | Should |
| FR-ENT-008 | Duplicate entity candidates inside one system MUST be flagged (rule R012). | Should |
| FR-ENT-009 | Each link MUST store its feature breakdown (`match_features`) for explainability. | Must |

### 1.4 Detection (DET)
| ID | Requirement | Priority |
|----|-------------|----------|
| FR-DET-001 | The system MUST run a registry of rules against an entity's linked records (rule catalog in 03_MODULES §M4). | Must |
| FR-DET-002 | Launch rule set: R001–R015 (contradictions) and R016–R018 (missing evidence, §1.14). | Must |
| FR-DET-003 | Rules MUST be pure functions: `(EntityContext, RuleConfig) → list[FindingCandidate]`. | Must |
| FR-DET-004 | Detection MUST be incremental: only the affected entity is re-evaluated after an event. The request to re-evaluate MUST be stored durably (in the same transaction as the record change) so a worker crash cannot lose it. | Must |
| FR-DET-005 | Each finding MUST have a deterministic `fingerprint` so repeated detection updates rather than duplicates. | Must |
| FR-DET-006 | If a previously detected condition no longer holds, the finding MUST be auto-resolved (`auto_resolved`). | Must |
| FR-DET-007 | Admins MUST be able to enable/disable rules and override severity and config. | Must |
| FR-DET-008 | Findings tied to a link with confidence below `MATCH_AUTO` MUST have their confidence reduced accordingly. | Must |

### 1.5 Evidence and confidence (EVD)
| ID | Requirement |
|----|-------------|
| FR-EVD-001 | Every finding MUST include an `evidence` JSON: involved records (system, id, version), conflicting fields with values, relevant timestamps, rule key, and match links used. |
| FR-EVD-002 | Every finding MUST include `confidence` ∈ [0,1] and a `confidence_breakdown` (link, rule certainty, evidence strength, recency). |
| FR-EVD-003 | Findings MUST include a `suggested_authority` (which system is likely correct) when per-field authority is configured. |
| FR-EVD-004 | A `priority_score` = severity weight × confidence MUST be computed for sorting. |
| FR-EVD-005 | Every finding's evidence MUST include a `trail` (facts → inferences → conclusion, §1.13). |

### 1.6 Finding lifecycle (FND)
| ID | Requirement |
|----|-------------|
| FR-FND-001 | States: `open`, `acknowledged`, `resolved`, `false_positive`, `auto_resolved`. Allowed transitions per 03_MODULES §M6. |
| FR-FND-002 | Manual transitions MUST record the actor and optional note, and write an audit log entry. |
| FR-FND-003 | An `auto_resolved` finding MUST reopen when its condition is detected again. A user-`resolved` finding MUST reopen only if the condition is detected with a different `evidence_hash` than at resolution time (so an unfixed-but-resolved finding does not bounce back on every unrelated update). Each reopen increments `reopen_count`. |
| FR-FND-004 | False-positive findings MUST be suppressed unless evidence materially changes (evidence hash changes) and rule config allows reopening. |
| FR-FND-005 | List endpoints MUST support filtering (status, severity, rule, system, entity, date range, min confidence), sorting, and pagination. |
| FR-FND-006 | Bulk status update of up to 100 findings MUST be supported. |

### 1.7 Alerts and real time (ALR / RTM)
| ID | Requirement |
|----|-------------|
| FR-ALR-001 | An alert MUST be created for: finding created, finding escalated (severity/confidence increased past a threshold), finding resolved (optional), link needs review, entity risk level rising to `warning` or `critical` (`risk_threshold_crossed`). |
| FR-ALR-002 | Alerts MUST be de-duplicated: the same fingerprint MUST NOT alert more than once per 10 minutes unless severity increases. |
| FR-ALR-003 | Users MUST be able to mark alerts read (individually and all); unread count MUST be available. |
| FR-RTM-001 | The server MUST push events over WebSocket (`/ws`) for finding, alert, entity (incl. risk), ingest-stats, simulation, and investigation changes. |
| FR-RTM-002 | WebSocket auth MUST use a single-use short-lived ticket obtained via REST. |
| FR-RTM-003 | Events MUST use the versioned envelope in 04_API_SPEC §WebSocket and include unique ids so clients can de-duplicate. |
| FR-RTM-004 | The client MUST auto-reconnect with exponential backoff and refetch missed data via REST after reconnect. |
| FR-RTM-005 | The server MUST send a heartbeat every 25 s; clients treat 60 s silence as disconnected. |

### 1.8 AI explanations (AIX)
| ID | Requirement |
|----|-------------|
| FR-AIX-001 | For each new or materially changed finding, the system MUST request an explanation from Gemini asynchronously. |
| FR-AIX-002 | The prompt MUST contain only the structured evidence (never free-form record text as instructions) and MUST request JSON output matching a schema: `summary`, `root_cause`, `likely_correct_system`, `suggested_actions[]`, `caveats`, `cited_fact_ids[]`. |
| FR-AIX-003 | Output MUST be validated against the schema; on failure retry once, then use the deterministic fallback template (`is_fallback = true`). |
| FR-AIX-004 | Explanations MUST be cached by `input_hash`; identical evidence MUST NOT trigger another API call. |
| FR-AIX-005 | PII redaction (mask emails/phones) MUST be on by default (`LLM_REDACT_PII=true`). |
| FR-AIX-006 | Concurrency to Gemini MUST be capped (`GEMINI_MAX_CONCURRENCY`, default 2) with exponential backoff on 429/5xx. |
| FR-AIX-007 | A user with `analyst` or `admin` role MUST be able to regenerate an explanation. |
| FR-AIX-008 | The UI MUST visibly label AI-generated text and show the evidence next to it. |
| FR-AIX-009 | `cited_fact_ids` MUST be a non-empty subset of the finding's trail fact ids; any other value counts as invalid output (retry once, then fallback). The fallback cites every fact. |

### 1.9 Simulation and evaluation (SIM)
| ID | Requirement |
|----|-------------|
| FR-SIM-001 | Admins MUST be able to start a seeded simulation: `seed`, `customers`, `anomaly_rate`, `events_per_second`, `anomaly_types[]`. |
| FR-SIM-002 | Same seed + same config MUST produce identical ground truth and injected issues. |
| FR-SIM-003 | The generator MUST create ground-truth customers and derive CRM/Billing/Support views with realistic noise (typos, nicknames, formatting, case, phone formats). |
| FR-SIM-004 | The injector MUST support these anomaly types — one per rule, so every rule is measured (mapping in 03 §M9): `email_mismatch`, `name_mismatch`, `phone_mismatch`, `status_conflict`, `billing_active_crm_churned`, `plan_mismatch`, `ticket_before_account`, `invoice_after_cancel`, `paid_before_issued`, `updated_before_created`, `open_ticket_closed_account`, `duplicate_record`, `orphan_billing`, `amount_mismatch`, `stale_sync`, `payment_never_recorded`, `support_response_missing`, `invoice_feed_gap`. |
| FR-SIM-005 | Every injected anomaly MUST be stored as a labeled `injected_issues` row. Every simulated source record MUST be mapped to its ground-truth customer in `simulation_ground_truth` (needed to score findings and matching). |
| FR-SIM-006 | "Simulate drift" MUST inject N new live anomalies into an existing run. |
| FR-SIM-007 | The evaluation service MUST compute detection precision, recall, F1 (overall and per type) by matching findings to injected issues, and matching quality (auto-match precision, auto+review recall) against ground truth. |
| FR-SIM-008 | With `anomaly_rate = 0` and decoys on, a run MUST produce zero findings (noise alone must never trigger a rule, R001–R018) and no entity risk level ≥ `warning`. |
| FR-SIM-009 | The simulator MUST generate month-scale histories with realistic recorded times and these **scenarios** (03 §M9): `churn_with_early_signals`, `churn_without_signals`, `signals_without_churn`. Ground truth stores the incident time and, for scenarios with signals, `expected_crossing_at` computed by the reference risk model on the noise-free history. |
| FR-SIM-010 | Decoys MUST include `late_within_grace` (expected evidence arrives just before its deadline → no finding) and `system_feed_outage` (one system silent for the last 40 days of the run → `cannot_assess`, no missing-evidence findings). |
| FR-SIM-011 | Evaluation MUST also report: lead-time absolute error and within-1-day rate, detectable-churn detection rate, no-false-hindsight rate, risk precision, missing-evidence findings during outages, and the result of the no-lookahead check (FR-TMX-006). |

### 1.10 Dashboard and analytics (DSH)
| ID | Requirement |
|----|-------------|
| FR-DSH-001 | Dashboard MUST show: entity count, system count, open findings, needs-review count, consistency score, findings by severity, trend (7/30 days), per-system issue counts, live feed. |
| FR-DSH-002 | **Consistency score** = 100 × `consistent` ÷ (`consistent` + `inconsistent`), using `entities.health` (05 §5.3). Entities with health `unknown` (a single record and no findings) are excluded. If the denominator is 0, the score is `null` and the UI shows "—". |
| FR-DSH-003 | Dashboard values MUST update live via WebSocket without full reload. |

### 1.11 Authentication and administration (AUT)
| ID | Requirement |
|----|-------------|
| FR-AUT-001 | Users authenticate with email + password; passwords hashed with Argon2id. |
| FR-AUT-002 | Access token (JWT, 15 min) + refresh token (opaque, 7 days, rotating, httpOnly cookie). |
| FR-AUT-003 | Roles: `admin` (everything), `analyst` (read all, act on findings/links, regenerate explanations), `viewer` (read only). |
| FR-AUT-004 | A first admin MUST be seeded from environment variables on first start. |
| FR-AUT-005 | Admins MUST be able to create/deactivate users and manage API keys. |
| FR-AUT-006 | All state-changing actions MUST write to `audit_logs`. |
| FR-AUT-007 | Any signed-in user MUST be able to change their own password (current password required); doing so revokes their other refresh tokens. |

### 1.12 Organizational Time Machine (TMX)
| ID | Requirement | Priority |
|----|-------------|----------|
| FR-TMX-001 | The system MUST reconstruct any entity **as of** a time T using only record versions whose **recorded time** (`record_versions.source_updated_at`) is ≤ T. Per record, the version with the greatest recorded time ≤ T wins; ties go to the higher `version`. Effective dates inside payloads never decide visibility. | Must |
| FR-TMX-002 | A record with no version recorded by T, or whose winning version is a deletion, MUST be absent from the as-of view. | Must |
| FR-TMX-003 | **No identity lookahead:** which account records belong to the entity as of T MUST be recomputed with the matcher (03 §M3) from the as-of versions. Link confirmations and rejections count only if decided at or before T. Accounts not linkable at T are reported as `not_yet_linkable`. | Must |
| FR-TMX-004 | Rules and risk signals MUST be evaluated on the as-of context with `now = T`, using **today's** rule configuration; every as-of result MUST record the `rule_set` used (rule keys, versions, config hash). | Must |
| FR-TMX-005 | As-of evaluation MUST NOT write findings, alerts or entity state. | Must |
| FR-TMX-006 | **No-lookahead invariant:** the as-of result for T MUST be identical whether computed before or after any data recorded after T is ingested. | Must |
| FR-TMX-007 | Record versions MUST NOT be pruned (they are the Time Machine's history; NFR-DAT-002). | Must |

### 1.13 Evidence-to-Conclusion Trail (TRL)
| ID | Requirement | Priority |
|----|-------------|----------|
| FR-TRL-001 | Every finding and every risk assessment MUST carry a `trail` with `facts`, `inferences` and a `conclusion` (schema in 03 §M5). | Must |
| FR-TRL-002 | Every `record_field` fact MUST reference a record id and version present in the evaluated context, with its system and recorded time. Every inference MUST cite at least one fact; the conclusion MUST cite at least one inference. | Must |
| FR-TRL-003 | Facts MUST contain only values stated by source records, or `absence` observations (what our data does not contain up to a time, with the feed watermark). Anything RealitySync computes — deadlines, scores, suggested authority — is an inference. | Must |
| FR-TRL-004 | The trail MUST be built deterministically by rules and scoring (never by the LLM) and MUST NOT be part of `evidence_hash`. | Must |

### 1.14 Missing-Evidence Detector (MEV)
| ID | Requirement | Priority |
|----|-------------|----------|
| FR-MEV-001 | Rules in category `missing_evidence` (R016–R018, 03 §M4) MUST evaluate **expectations**: a trigger fact, the evidence expected, and a deadline. Scope is the customer domain (Q-006); employee offboarding is Phase 2. | Must |
| FR-MEV-002 | Each expectation MUST have exactly one outcome: `pending` (deadline not passed), `unconfirmed` (deadline passed, evidence absent, and the expected system's feed watermark is later than the deadline), or `cannot_assess` (deadline passed but the watermark is at or before the deadline). Only `unconfirmed` produces a finding. | Must |
| FR-MEV-003 | The **feed watermark** of a system at time `now` MUST be the greatest recorded time among that system's record versions with recorded time ≤ `now`. | Must |
| FR-MEV-004 | Titles, fallback explanations and UI copy MUST say "unconfirmed" or "cannot assess"; they MUST NOT claim that an action did not happen. | Must |
| FR-MEV-005 | When the expected evidence is later recorded, the finding MUST auto-resolve (FR-DET-006). | Must |
| FR-MEV-006 | `pending` and `cannot_assess` expectations MUST be visible in the entity detail and the as-of view. | Should |

### 1.15 Risk signals (RSK)
| ID | Requirement | Priority |
|----|-------------|----------|
| FR-RSK-001 | The system MUST compute deterministic risk signals per entity — `payment_delay`, `complaint_trend`, `commercial_decline`, `open_inconsistencies` — with the formulas in 03 §M12. No ML. | Must |
| FR-RSK-002 | Each assessment MUST have `risk_score` ∈ [0,1], a `risk_level` (`low`, `watch`, `warning`, `critical`) and a separately computed `risk_confidence` ∈ [0,1] (evidence coverage and freshness). Score and confidence MUST always be returned together and MUST NOT be combined into one number. | Must |
| FR-RSK-003 | Live risk MUST be recomputed whenever the entity is re-detected; the current assessment and every level change MUST be stored. | Must |
| FR-RSK-004 | "Orders declined" is represented by the `commercial_decline` proxy (plan downgrade, quantity decrease, invoice amount drop); there is no order record type (Q-007). | Must |

### 1.16 "Could We Have Known?" investigations (INV)
| ID | Requirement | Priority |
|----|-------------|----------|
| FR-INV-001 | Analysts MUST be able to start an investigation for an entity and an incident of kind `churn` or `finding` (Q-010). | Must |
| FR-INV-002 | A `churn` incident is the earliest recorded CRM account version with status `churned` or Billing subscription version with status `cancelled`; if none exists → 422. A `finding` incident names a finding and requires `incident.at` (when the problem was noticed). | Must |
| FR-INV-003 | Checkpoints MUST be the recorded times of the entity's versions in `[incident_at − lookback, incident_at)` plus every 00:00 UTC day boundary in that window (time alone changes deadlines and risk windows). `lookback_days` default 180, max 365; more than 1,000 checkpoints → 422. | Must |
| FR-INV-004 | At each checkpoint the system MUST compute the as-of findings and risk. `first_detectable_at` = the first checkpoint where `risk_score ≥ warning_threshold` (default 0.60) for `churn`, or where the finding's fingerprint is present for `finding`. `lead_time = incident_at − first_detectable_at`. | Must |
| FR-INV-005 | The result MUST include outcome (`crossed` or `never_crossed`), `first_detectable_at`, lead time, the trail and risk at the crossing, the `rule_set`, and the retrospective caveat text (04 §17) — always, including in exports. | Must |
| FR-INV-006 | Investigations MUST be deterministic: identical inputs (`inputs_hash`) MUST give an identical result; a repeated identical request returns the existing completed investigation. | Must |
| FR-INV-007 | Investigations and their checkpoints MUST be persisted; progress and completion MUST be published over WebSocket. | Must |

---

## 2. Non-functional requirements

### 2.1 Performance
| ID | Requirement |
|----|-------------|
| NFR-PERF-001 | Ingest endpoint sustains ≥ 200 events/s on a developer laptop (4 cores) with Postgres local. |
| NFR-PERF-002 | Event → finding persisted → WebSocket push p95 < 2 s (AI excluded). |
| NFR-PERF-003 | List endpoints respond p95 < 300 ms for 10k entities / 50k findings with proper indexes. |
| NFR-PERF-004 | Entity detection for one entity (≤ 20 records, 15 rules) < 50 ms CPU. |
| NFR-PERF-005 | Dashboard summary p95 < 400 ms. |
| NFR-PERF-006 | As-of view of one entity (≤ 50 records, ≤ 500 versions) p95 < 500 ms. |
| NFR-PERF-007 | An investigation with ≤ 1,000 checkpoints completes in < 30 s; at most 2 run concurrently per process. |

### 2.2 Reliability and data integrity
| ID | Requirement |
|----|-------------|
| NFR-REL-001 | No ingested event is lost: persisted before ack; processing is at-least-once and idempotent. |
| NFR-REL-002 | Worker crash MUST NOT lose events; `processing` events older than 5 min are re-queued. |
| NFR-REL-003 | DB changes happen only through Alembic migrations. |
| NFR-REL-004 | LLM failure MUST NOT block detection or alerting. |

### 2.3 Security
| ID | Requirement |
|----|-------------|
| NFR-SEC-001 | All secrets come from environment variables; none in git. |
| NFR-SEC-002 | All inputs validated by Pydantic; SQL only via ORM/parameterized queries. |
| NFR-SEC-003 | Auth endpoints rate-limited (5 failed logins/min/IP+email). |
| NFR-SEC-004 | CORS allow-list from env (credentials allowed only for listed origins); cookies `HttpOnly`, `SameSite=Lax`, `Secure` when `APP_ENV=production`. |
| NFR-SEC-005 | PII (emails, phones) never appears in application logs; tokens never logged. |
| NFR-SEC-006 | Record payloads are untrusted data: never interpreted as prompts/instructions; escaped when rendered in UI. |
| NFR-SEC-007 | Gemini API key is server-side only; never exposed to the browser. |
| NFR-SEC-008 | Dependencies pinned; `pip-audit` / `npm audit` run in CI. |

### 2.4 Observability
| ID | Requirement |
|----|-------------|
| NFR-OBS-001 | Structured JSON logs with `request_id`, `user_id` (if any), `event_id`, `entity_id` where relevant. |
| NFR-OBS-002 | `GET /health` (liveness) and `GET /health/ready` (DB + worker check). The worker counts as healthy if no `pending` ingest event and no requested detection is older than 60 s. Both paths are at the server root, not under `/api/v1`. |
| NFR-OBS-003 | Ingest and detection timings recorded and exposed on the Dashboard's ingest stats. |

### 2.5 Usability and accessibility
| ID | Requirement |
|----|-------------|
| NFR-UX-001 | UI follows 06_UI_STYLE_GUIDE; components come from the shared design system. |
| NFR-UX-002 | WCAG 2.1 AA: contrast ≥ 4.5:1, full keyboard navigation, visible focus, ARIA labels, `prefers-reduced-motion` respected. |
| NFR-UX-003 | Responsive: usable from 360 px to 1920 px. |
| NFR-UX-004 | Every list has loading (skeleton), empty, and error states. |
| NFR-UX-005 | Real-time updates never steal focus or shift content under the cursor (new rows animate in without layout jump when user is scrolled). |

### 2.6 Maintainability and quality
| ID | Requirement |
|----|-------------|
| NFR-MNT-001 | Backend: Python 3.12, type hints everywhere, `ruff` + `mypy` clean. |
| NFR-MNT-002 | Frontend: TypeScript `strict`, ESLint + Prettier clean, no `any`. |
| NFR-MNT-003 | `domain/` coverage ≥ 85%; API integration tests for every endpoint's happy path and main error path. |
| NFR-MNT-004 | CI (lint, type-check, tests) MUST pass before merge. |
| NFR-MNT-005 | OpenAPI schema is generated from code; frontend types are generated from it. |

### 2.7 Portability and operations
| ID | Requirement |
|----|-------------|
| NFR-OPS-001 | `make dev` starts Postgres, backend, and frontend via Docker Compose; `make seed` loads a demo run. |
| NFR-OPS-002 | Configuration via env vars documented in `.env.example`. |
| NFR-OPS-003 | Runs on Linux/macOS/Windows (WSL2) with Docker. |

### 2.8 Data and compliance
| ID | Requirement |
|----|-------------|
| NFR-DAT-001 | Only synthetic data is used; generator uses `Faker` with a fixed seed and non-routable domains (e.g., `example.com`). |
| NFR-DAT-002 | Retention: `processed` ingest events older than 90 days MAY be pruned by an admin job. Record versions MUST NOT be pruned (FR-TMX-007; Q-008, 2026-10-10). |

---

## 3. Constraints
- Stack fixed by 02_ARCHITECTURE (Python/FastAPI, React/TypeScript, PostgreSQL, Gemini).
- No dependency outside the approved list in 02 §2.1 without a Decision entry in `08_PROGRESS_HANDOFF.md`.
- Contracts (04_API_SPEC, 05_DATABASE_SCHEMA) are the source of truth; code conforms to docs, not vice versa, until a contract change is approved.

## 4. Traceability
Each task in `09_TASKS.md` lists the requirement IDs it satisfies in its acceptance criteria. `09_TASKS.md` → "Requirement traceability" maps every requirement ID to the task(s) that own it. A requirement is "done" only when its tests pass.
