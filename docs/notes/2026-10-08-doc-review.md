# Doc review — 2026-10-08

**Reviewer:** `claude-review-1` · **Scope:** `AGENTS.md`, `docs/00`–`09` · **Result:** 31 fixes (sections A–B), missing pieces added (C), task plan rebuilt (D).
Decisions are recorded as D-013…D-029 in `08_PROGRESS_HANDOFF.md §6`. This note explains *why* each change was made, so later agents don't undo them.

## A. Bugs — the docs contradicted themselves or could not work

| # | Problem | Fix | Where |
|---|---------|-----|-------|
| A1 | The confidence formula gives **0.829** for the R004 example (0.97 × 0.95 × 0.9 × 1.0), but the PRD, API and alert examples said 0.93 / priority 2.79. An agent writing tests from the examples would "fix" the formula. | Examples corrected to 0.829 / 2.487. Added a worked example that doubles as a unit test. | 03 §M5, 04 §7–8, 00 §6.1 |
| A2 | **R012 (duplicates) could never fire.** Blocking only looked at *other* systems, so a second CRM account for the same person never joined the entity. | Blocking now includes the record's own system. Primary-account order is defined; extra accounts go into `extra_accounts`. | 01 FR-ENT-002, 03 §M3/M4 |
| A3 | **Evaluation could not be computed.** Nothing stored which source record belongs to which ground-truth customer. | New table `simulation_ground_truth`, written by the runner and never sent through ingest. | 05 §2.17.1, 03 §M9 |
| A4 | Suggested authority: "if the top two differ by < 0.15 → undetermined" ran before "tie → most recent", so the tie rule could never apply. | 3-step rule: authority gap ≥ 0.15 → recency ≥ 24 h → undetermined. | 03 §M5 |
| A5 | `UNIQUE (input_hash, prompt_version, model)` on explanations made **Regenerate** fail with a unique violation. Fallbacks were also cached forever, so a finding hit by a Gemini outage never got a real explanation. | Non-unique cache index that ignores fallback rows. Regenerate always inserts. A sweeper retries failure fallbacks. | 05 §2.13, 03 §M8 |
| A6 | Evidence hash included `crm.updated_at`, so any unrelated CRM edit counted as a "material change". That re-opened false positives and spent Gemini budget. | Hash = `{rule_key, fields, compared timestamps}`. Rules put only the timestamps they compare into `timestamps`. | 03 §M4/M5 |
| A7 | A user-resolved finding whose data wasn't fixed would re-open on the next detection run (any event on the entity). The ASCII state diagram was also ambiguous (resolved → false_positive?). | Authoritative transition table. User-resolved findings re-open only when the evidence hash changes (`resolved_evidence_hash`). | 03 §M6, 05 §2.11, 01 FR-FND-003 |
| A8 | Consistency score used "total linked entities", which was undefined. Single-record orphan entities with findings made the formula inconsistent with `entities.health`. | Score = consistent ÷ (consistent + inconsistent) from `entities.health`; `null` when empty. | 01 FR-DSH-002, 05 §5.3 |
| A9 | `normalize_status` listed a vocabulary (`trial`, `closed`, …) that didn't match the per-record-type canonical statuses (`trialing`, `inactive`, …). | Function takes `record_type` and returns that type's vocabulary; unknown → `None`. | 03 §M2 |
| A10 | The "orphan child → R013 may fire" note was wrong: R013 is about a billing **account** without CRM. Children arriving before their parent were never re-attached. | Orphan children wait unlinked and are attached when the parent links. | 03 §M3, 01 FR-ENT-005 |
| A11 | FR-NRM-004 said naive timestamps are "rejected or assumed UTC per source config", but no such config exists. 04 said they're rejected. | Rejected (422). | 01, 04 §1.5 |
| A12 | `extra="forbid"` everywhere would reject real-world ingest payloads with extra fields. | `payload` keeps unknown keys raw; normalization ignores them. | 04 §1.5 |
| A13 | Idempotency key used `record_hash` (normalized), which would force normalization in the API layer, and it ignored `event_type`. | Uses the raw `payload_hash` and includes `event_type`. | 03 §M1 |
| A14 | `GET /findings/export.csv` would be captured by `/findings/{id}` (422) if registered later. | Route-order note. | 04 §1.5 |
| A15 | Schema doc formatting: `record_versions` numbered 2.5.1 after 2.6; the relationship table had 4 headers but 3 cells; ER diagram missed `rejected_pairs`, `api_keys` → users. | Fixed. | 05 |
| A16 | Heartbeat/pong messages were not in the envelope format, which breaks client de-dup and parsing. | `system.ping` / `system.pong` envelopes on a `system` topic. | 04 §14 |
| A17 | T-028 used `source_systems.py` while 02 listed `systems.py`. Several services named in tasks were missing from the tree. Health/WS paths were ambiguous (`/api/v1/health` vs `/health`). | Tree updated; `/health*` and `/ws` at the server root. | 02 §7, 04 |

## B. Design gaps — would have caused data loss, races or wrong numbers

| # | Gap | Fix |
|---|-----|-----|
| B1 | 500 ms in-memory debounce between "record changed" and "run detection": a worker crash lost detection for good. | Durable `entities.detection_requested_at` + a detection loop (`SKIP LOCKED`). This also coalesces bursts and drives rule-change re-evaluation (ADR-09). |
| B2 | Two workers handling events for the same record, or two records of the same new customer, could interleave → non-deterministic state or duplicate entities. | Per-record advisory lock with a deterministic tie-break, plus sorted blocking-key advisory locks (ADR-11). |
| B3 | `WORKER_MODE=separate` silently broke real-time, because an in-memory EventBus can't reach another process. | `EVENT_BUS=pg_notify` (`PgNotifyEventBus`); config validation enforces it (ADR-10). |
| B4 | Simulator noise ("typos", "missing fields", "timestamp skew") could trigger real rules, which then count as false positives and sink precision. | Explicit noise limits, plus FR-SIM-008: an anomaly-free run must give zero findings. |
| B5 | Only 11 anomaly types for 15 rules: R003, R005, R010 and R011 were never measured. Legitimate side-effect findings (e.g. R011 after a status conflict) counted as FPs. | 15 types (one per rule) with `acceptable_rule_keys` ("ignored" in metrics). |
| B6 | G2 (matching ≥ 95%) had no measurement. | Matching metrics in the evaluation (auto-match precision, auto+review recall). The generator only sets cross-reference ids on 30% of Billing accounts, so matching isn't trivial. |
| B7 | G4 "95% explained within 10 s" is impossible during a simulation burst at concurrency 2. | Goal restated as p50 at steady state; queue ordered by priority. |
| B8 | Which link statuses count for detection was unspecified. | `auto_matched`, `confirmed`, `needs_review` (confidence lowered); never `rejected`. |
| B9 | Plan prices for R014 and the generator were undefined, so the two could disagree. | Plan catalog (INR) in `domain/normalize/plans.py`. |
| B10 | Field-authority JSON keys were free-form ("ticket fields", "invoice dates"). | Fixed key list. |
| B11 | Rules had no `version`/config schema, yet evidence has `rule.version` and the UI builds forms "from the rule config schema". | `Rule.version`, `Rule.config_model`; `GET /rules` returns `config_schema`; startup registry→table sync defined. |
| B12 | `make seed` vs "seed on first start" was ambiguous. | Bootstrap (systems, rules, admin) runs on startup, idempotent; `make seed` = demo data only. |
| B13 | The "Secure cookie in production" rule needed an environment flag that didn't exist; `DATABASE_URL_TEST` was used but undocumented. | `APP_ENV`, `DATABASE_URL_TEST`, `EVENT_BUS` added to 02 §8. |
| B14 | The default Gemini model `gemini-2.5-flash` is now limited to users who already used it (ai.google.dev, checked 2026-10-08). | Default `gemini-3.5-flash-lite`; T-029 re-verifies. |

## C. Missing pieces the UI or tasks referenced

- **Approved dependency list** (02 §2.1). The rules said "only approved deps", but there was no list. The JWT library, ULID, Faker and the font package were all missing.
- **Frontend routes table** (02 §3.1). The **Link review** page had no nav entry, and **Settings** had no content.
- **Components** used by pages but not in the style guide: `Switch` (rules), `Slider` (systems), `Dialog` (reset, one-time API key), `ErrorState` (used in 07 snippet). The Tailwind excerpt now exposes all tokens.
- **Change own password** (FR-AUT-007, `POST /auth/change-password`). Users had no way to do it.
- **Dashboard summary** lacked the data for three widgets (spotlight, explained-by-AI, resolution progress).
- **Failed ingest events UI** (FR-ING-009 retry had an endpoint but no screen) → Systems page.
- **Audit log UI** → Settings.
- **Contract tests** (02 §11) and the **retention job** (NFR-DAT-002) had no task.

## D. Task plan changes (09)

- **Splits** (the original tasks were over the 1-day limit): T-005 → T-005 + **T-043** (data-viz components); T-011 → T-011 + **T-044** (worker loop); T-025 → **T-045** (alerts) + T-025; T-027 → T-027 + **T-046** (dashboard endpoints); T-037 → T-037 + **T-049** (settings).
- **New:** **T-047** retention job (P2), **T-048** API contract tests, **T-050** PgNotify bus / separate worker (P2).
- **Dependency fixes:**
  - T-039 now needs all rule tasks (T-021/22/23), because its precision/recall gate needs every rule.
  - T-030 needs T-027, because it edits `findings.py`, which T-027 creates.
  - T-013 needs T-010 (plan catalog).
  - T-031 needs T-032 (live dashboard).
  - T-042 needs every backend endpoint task.
- **Computed:** waves (14), critical path, a "Blocks" line on every task, milestone mapping, and requirement → task traceability. Every ID is checked by a script, so no requirement is left without an owner.
