# 09 — Tasks

The implementation plan, split into discrete tasks that individual agents can claim. **Claiming protocol:** `07_AGENT_RULES §2`. When you change a task's status, also update the board in `08_PROGRESS_HANDOFF §10`.

> **Revised 2026-10-08 (doc review):** 8 tasks added (T-043…T-050, mostly splits of over-sized tasks), dependencies corrected, waves recomputed, requirement traceability and milestone mapping added. Details: `docs/notes/2026-10-08-doc-review.md`.

## Legend
- **Status:** `todo` · `in_progress` · `review` · `blocked` · `done`
- **Priority:** `P0` critical path · `P1` needed for MVP · `P2` polish / post-MVP
- **Size:** `S` ≤ 2 h · `M` ≤ half day · `L` ≤ 1 day (split if bigger)
- **Depends:** all must be `done` before starting (you may read ahead, not build on unmerged work)
- **Blocks:** tasks waiting on this one (for information; `Depends` is authoritative)
- **Touches:** files/folders the task may modify. Anything else is out of scope (`07 §5.3`).
- **Agent:** your agent id (e.g., `claude-code-1`) or `unassigned`
- Every acceptance criterion needs a test or a documented manual check. All tasks also require: `make check` green, handoff updated.

## Parallel waves (computed from `Depends`; a task can start once every earlier wave it depends on is done)
| Wave | Tasks |
|------|-------|
| 0 | T-001 |
| 1 | T-002, T-004 |
| 2 | T-003, T-005, T-010, T-029 |
| 3 | T-006, T-013, T-016, T-043 |
| 4 | T-007, T-009, T-014 |
| 5 | T-008, T-011, T-026, T-044 |
| 6 | T-012, T-015, T-032 |
| 7 | T-017, T-019, T-047 |
| 8 | T-018, T-020, T-021, T-022, T-023, T-024 |
| 9 | T-027, T-038, T-045, T-046 |
| 10 | T-025, T-031, T-033, T-034, T-035, T-049 |
| 11 | T-028, T-030, T-039, T-050 |
| 12 | T-036, T-037, T-042, T-048 |
| 13 | T-040, T-041 |

**Critical path** (longest chain by size, ≈ 78 h of sequential work): T-001 → T-002 → T-003 → T-006 → T-009 → T-011 → T-012 → T-019 → T-024 → T-045 → T-025 → T-039 → T-036 → T-041. Keep these staffed first.

## Summary table
| ID | Title | Epic | Pri | Size | Depends | Wave | Status |
|----|-------|------|-----|------|---------|------|--------|
| T-001 | Repo scaffolding & tooling | E0 | P0 | L | — | 0 | done |
| T-002 | Backend skeleton | E0 | P0 | M | T-001 | 1 | done |
| T-003 | Database foundation | E0 | P0 | M | T-002 | 2 | done |
| T-004 | Frontend skeleton | E0 | P0 | M | T-001 | 1 | todo |
| T-005 | Design system — core primitives | E0 | P0 | L | T-004 | 2 | todo |
| T-006 | Auth data model | E1 | P0 | S | T-003 | 3 | todo |
| T-007 | Auth & users backend | E1 | P0 | L | T-006 | 4 | todo |
| T-008 | Frontend auth | E1 | P0 | M | T-005, T-007 | 5 | todo |
| T-009 | Core schema migration & models | E2 | P0 | L | T-003, T-006 | 4 | todo |
| T-010 | Normalization library | E2 | P0 | M | T-002 | 2 | todo |
| T-011 | Ingest API & API keys | E2 | P0 | L | T-007, T-009, T-010 | 5 | todo |
| T-012 | Record upsert & versioning | E2 | P0 | M | T-010, T-011, T-044 | 6 | todo |
| T-013 | Synthetic data generator | E3 | P0 | L | T-002, T-010 | 3 | todo |
| T-014 | Anomaly injector & labels | E3 | P0 | L | T-013 | 4 | todo |
| T-015 | Simulation runner & endpoints | E3 | P1 | L | T-011, T-014, T-026 | 6 | todo |
| T-016 | Matching domain logic | E4 | P0 | L | T-010 | 3 | todo |
| T-017 | Entity resolution service | E4 | P0 | L | T-009, T-012, T-016 | 7 | todo |
| T-018 | Link review endpoints | E4 | P1 | M | T-017 | 8 | todo |
| T-019 | Rule engine framework | E5 | P0 | L | T-009, T-012 | 7 | todo |
| T-020 | Rules R001–R003 (field conflicts) | E5 | P0 | M | T-019 | 8 | todo |
| T-021 | Rules R004–R006, R014 (status, plan, amount) | E5 | P0 | M | T-019 | 8 | todo |
| T-022 | Rules R007–R010 (temporal) | E5 | P0 | M | T-019 | 8 | todo |
| T-023 | Rules R011–R013, R015 (structural/logic) | E5 | P1 | M | T-019 | 8 | todo |
| T-024 | Scoring & finding lifecycle | E5 | P0 | L | T-019 | 8 | todo |
| T-025 | Detection loop & pipeline wiring | E5 | P0 | L | T-017, T-020, T-024, T-026, T-045 | 10 | todo |
| T-026 | EventBus & WebSocket server | E6 | P0 | L | T-007 | 5 | todo |
| T-027 | Read/write REST APIs | E6 | P0 | L | T-017, T-024 | 9 | todo |
| T-028 | Rules & systems endpoints | E6 | P1 | M | T-019, T-025 | 11 | todo |
| T-029 | Gemini client wrapper | E7 | P0 | L | T-002 | 2 | todo |
| T-030 | Explanation service & endpoint | E7 | P0 | M | T-025, T-027, T-029 | 11 | todo |
| T-031 | Dashboard page | E8 | P0 | L | T-008, T-032, T-043, T-046 | 10 | todo |
| T-032 | WebSocket client, live feed, toasts | E8 | P0 | L | T-008, T-026, T-043 | 6 | todo |
| T-033 | Findings list & drawer | E8 | P0 | L | T-027, T-032, T-043 | 10 | todo |
| T-034 | Entities list & detail | E8 | P1 | L | T-008, T-027, T-043 | 10 | todo |
| T-035 | Alerts page & bell | E8 | P1 | M | T-027, T-032 | 10 | todo |
| T-036 | Simulation & evaluation pages | E8 | P1 | M | T-015, T-039, T-043 | 12 | todo |
| T-037 | Rules & systems pages | E8 | P1 | M | T-008, T-011, T-028 | 12 | todo |
| T-038 | Link review UI | E8 | P1 | M | T-008, T-018, T-043 | 9 | todo |
| T-039 | Evaluation service & endpoints | E9 | P1 | M | T-015, T-021, T-022, T-023, T-025 | 11 | todo |
| T-040 | End-to-end tests | E9 | P1 | M | T-031, T-033, T-036 | 13 | todo |
| T-041 | Demo seed, README, performance check | E9 | P1 | M | T-030, T-036, T-039 | 13 | todo |
| T-042 | Hardening & security review | E9 | P1 | M | T-011, T-015, T-018, T-027, T-028, T-030, T-039, T-046 | 12 | todo |
| T-043 | Design system — data-viz & composite components | E0 | P0 | M | T-005 | 3 | todo |
| T-044 | Ingest worker loop | E2 | P0 | M | T-009 | 5 | todo |
| T-045 | Alert service & policy | E5 | P0 | M | T-024 | 9 | todo |
| T-046 | Dashboard endpoints | E6 | P0 | M | T-017, T-024, T-026 | 9 | todo |
| T-047 | Retention prune job | E2 | P2 | S | T-012 | 7 | todo |
| T-048 | API contract tests | E9 | P1 | M | T-011, T-015, T-018, T-027, T-028, T-030, T-039, T-046 | 12 | todo |
| T-049 | Settings page (profile, users, API keys, audit) | E8 | P1 | M | T-008, T-011, T-027 | 10 | todo |
| T-050 | PgNotify EventBus & separate worker mode | E6 | P2 | M | T-025 | 11 | todo |

## Milestone mapping (PRD §11)
| Milestone | Tasks |
|-----------|-------|
| M0 Foundation | T-001, T-002, T-003, T-004, T-005, T-043, T-006, T-007, T-008 |
| M1 Data pipeline | T-009, T-010, T-011, T-044, T-012, T-013, T-014, T-016, T-017, T-018 |
| M2 Detection | T-019, T-020, T-021, T-022, T-023, T-024, T-045, T-025, T-027, T-046, T-028 |
| M3 Real-time + AI | T-026, T-015, T-029, T-030, T-031, T-032, T-033, T-034, T-035, T-037, T-038, T-049 |
| M4 Polish | T-039, T-036, T-040, T-041, T-042, T-048, T-047, T-050 |

## Requirement traceability (every requirement ID → owning task(s))
| Requirement(s) | Task(s) |
|----------------|---------|
| FR-ING-001 | T-009, T-011 |
| FR-ING-002 | T-011 |
| FR-ING-003 | T-011 |
| FR-ING-004 | T-011 |
| FR-ING-005 | T-011, T-012 |
| FR-ING-006 | T-011, T-044 |
| FR-ING-007 | T-012 |
| FR-ING-008 | T-012 |
| FR-ING-009 | T-011, T-044, T-037 |
| FR-ING-010 | T-011 |
| FR-NRM-001…006 | T-010 |
| FR-ENT-001 | T-017, T-034 |
| FR-ENT-002 | T-016 |
| FR-ENT-003 | T-016 |
| FR-ENT-004 | T-017 |
| FR-ENT-005 | T-017 |
| FR-ENT-006 | T-018, T-038 |
| FR-ENT-007 | T-017 |
| FR-ENT-008 | T-017, T-023 |
| FR-ENT-009 | T-016, T-034 |
| FR-DET-001…003 | T-019 |
| FR-DET-002 (R001–R015) | T-020, T-021, T-022, T-023 |
| FR-DET-004 | T-017, T-025 |
| FR-DET-005/006/008 | T-024 |
| FR-DET-007 | T-019, T-028, T-037 |
| FR-EVD-001…004 | T-024 |
| FR-FND-001…004 | T-024 |
| FR-FND-005/006 | T-027, T-033 |
| FR-ALR-001/002 | T-045 |
| FR-ALR-003 | T-027, T-035 |
| FR-RTM-001…003, 005 | T-026 |
| FR-RTM-004 | T-032 |
| FR-AIX-001/003/004/007 | T-030 |
| FR-AIX-002/005/006 | T-029 |
| FR-AIX-008 | T-033 |
| FR-SIM-001/006 | T-015, T-036 |
| FR-SIM-002/003 | T-013 |
| FR-SIM-004 | T-014 |
| FR-SIM-005 | T-014, T-015 |
| FR-SIM-007 | T-039, T-036 |
| FR-SIM-008 | T-013, T-039 |
| FR-DSH-001/002 | T-046, T-031 |
| FR-DSH-003 | T-031, T-032 |
| FR-AUT-001…004 | T-006, T-007, T-008 |
| FR-AUT-005 | T-007, T-011, T-049 |
| FR-AUT-006 | T-007, T-027, T-049 |
| FR-AUT-007 | T-007, T-049 |
| NFR-PERF-001…005 | T-025, T-046, T-041 |
| NFR-REL-001/002 | T-011, T-044 |
| NFR-REL-003 | T-003 |
| NFR-REL-004 | T-025, T-030 |
| NFR-SEC-001…008 | T-001, T-002, T-007, T-042 |
| NFR-OBS-001/002 | T-002, T-003 |
| NFR-OBS-003 | T-025, T-046 |
| NFR-UX-001…005 | T-004, T-005, T-043, T-031, T-032 |
| NFR-MNT-001…004 | T-001 |
| NFR-MNT-005 | T-027, T-048 |
| NFR-OPS-001…003 | T-001, T-041 |
| NFR-DAT-001 | T-013 |
| NFR-DAT-002 | T-047 |

---

# E0 — Foundation

### T-001 — Repo scaffolding & tooling
- Status: done | Priority: P0 | Size: L | Depends: — | Wave: 0 | Agent: gemini-1 | Claimed: 2026-10-08
- Blocks: T-002, T-004
- Touches: repo root, `.github/`, `backend/` (empty package + `pyproject.toml`), `frontend/` (`package.json` only), `docker-compose.yml`, `Makefile`, `.env.example`, `.gitignore`, `.pre-commit-config.yaml`, `.secrets.baseline`, `README.md` (stub), `LICENSE`
- Requirements: NFR-OPS-001/002/003, NFR-MNT-001/002/004, NFR-SEC-001/008
- Acceptance:
  - If no git repository exists yet: `git init -b main`; first commit contains `AGENTS.md` and `docs/` unchanged.
  - Monorepo layout per `02 §7`; `docs/` untouched.
  - `docker-compose.yml` with `db` (postgres:16), `backend`, `frontend`; healthchecks (backend → `GET /health`); named volume.
  - `Makefile` targets from `07 §15` exist (targets that need later code may print "not yet implemented" but must not fail `make check` on an empty project).
  - `.env.example` lists **every** variable in `02 §8` (incl. `APP_ENV`, `DATABASE_URL_TEST`, `EVENT_BUS`) with placeholders only.
  - CI workflow runs lint, types, tests (backend + frontend) on PR with a Postgres service; caches dependencies.
  - Pre-commit: ruff, ruff-format, eslint/prettier, detect-secrets (baseline committed).
  - `import-linter` contract: `app.domain` may not import `app.api`, `app.services`, `app.models`, `app.db`, `app.ai`, `app.realtime`, `app.workers`, `app.simulation`, `sqlalchemy`, `fastapi`, `httpx`, `asyncpg`, `google.genai`.
  - Only dependencies from `02 §2.1`, pinned.
  - `LICENSE` = MIT (default of Q-004).

### T-002 — Backend skeleton
- Status: done | Priority: P0 | Size: M | Depends: T-001 | Wave: 1 | Agent: gemini-2 | Claimed: 2026-10-09
- Blocks: T-003, T-010, T-013, T-029
- Touches: `backend/app/main.py`, `backend/app/core/*`, `backend/app/api/health.py`, `backend/app/api/v1/router.py`, `backend/tests/`
- Requirements: NFR-OBS-001/002, NFR-SEC-001/004/005
- Acceptance:
  - App factory + lifespan; REST routers under `/api/v1`; `/health`, `/health/ready`, `/openapi.json`, `/docs` at the server root (`/docs` hidden when `APP_ENV=production`).
  - `core/config.py` (pydantic-settings) exposing all env vars from `02 §8` with defaults/validation; startup fails if `WORKER_MODE=separate` and `EVENT_BUS≠pg_notify`.
  - `core/clock.py`: `Clock` protocol, `SystemClock`, `FixedClock` (tests). No `datetime.now()` elsewhere.
  - `structlog` JSON logging with `request_id` middleware and a PII scrubber processor (emails/phones masked) — unit tested.
  - Error classes (`NotFoundError`, `ConflictError`, `ValidationFailed`, `PermissionDenied`, `RateLimited`) + global handler producing the envelope in `04 §1.3` (including 422 from Pydantic).
  - `GET /health` and `GET /health/ready` (ready returns db `"unknown"` until T-003).
  - CORS from env with credentials only for listed origins. pytest + httpx async client fixture; tests for health and error envelope.

### T-003 — Database foundation
- Status: done | Priority: P0 | Size: M | Depends: T-002 | Wave: 2 | Agent: gemini-3 | Claimed: 2026-10-09
- Blocks: T-006, T-009
- Touches: `backend/app/db/*`, `backend/alembic*`, `backend/tests/conftest.py`, `backend/app/api/health.py` (ready check only)
- Requirements: NFR-REL-003
- Acceptance:
  - Async engine/session factory, `Base` with naming convention, `get_session` dependency.
  - Alembic configured for async; first migration enables `pgcrypto`, `citext`, `pg_trgm`.
  - Test fixtures: `DATABASE_URL_TEST` if set, else a Postgres test container; migrations applied once per session; per-test transaction rollback or truncate.
  - `/health/ready` checks DB connectivity (503 if down).
  - `make migrate` works in Docker; CI runs `alembic upgrade head` on an empty DB and `alembic check`.
  - **Holds the migration lock until merged.**

### T-004 — Frontend skeleton
- Status: todo | Priority: P0 | Size: M | Depends: T-001 | Wave: 1 | Agent: unassigned | Claimed: —
- Blocks: T-005
- Touches: `frontend/**` (excluding `components/ui/*` internals beyond what the shell needs)
- Requirements: NFR-UX-001/003, NFR-MNT-002
- Acceptance:
  - Vite + React 18 + TS strict; Tailwind configured with the tokens from `06 §11`; `styles/tokens.css`; Inter variable font self-hosted.
  - React Router with **every route in `02 §3.1`** as a lazy-loaded placeholder; `/styleguide` only when `APP_ENV=development`.
  - App shell: logo pill, PillNav (items per `06 §5`, incl. Review), settings pill, bell, avatar button — matches the reference at ≥ 1280 px and collapses at < 768 px.
  - TanStack Query provider, Zustand setup, `lib/api` fetch wrapper (base URL from env, error-envelope parsing, `credentials: "include"` on `/auth/*`), `make api-types` script using `openapi-typescript`.
  - ESLint (incl. jsx-a11y), Prettier, Vitest, Testing Library configured; one smoke test.

### T-005 — Design system — core primitives
- Status: todo | Priority: P0 | Size: L | Depends: T-004 | Wave: 2 | Agent: unassigned | Claimed: —
- Blocks: T-008, T-043
- Touches: `frontend/src/components/ui/**`, `frontend/src/app/styleguide/**`
- Requirements: NFR-UX-001/002/004
- Acceptance:
  - Components from `06 §6`: GlassCard, DarkCard, Button (primary, accent, secondary, ghost, danger), IconButton, PillNav/NavItem, Avatar, SeverityBadge, SystemChip, Input/Select/Search, Switch, Slider, Tabs, Table, Drawer, Dialog, Toast, Tooltip, Skeleton, EmptyState, ErrorState.
  - Radix primitives for Drawer/Dialog, Tabs, Tooltip, Select, Toast, Switch, Slider; keyboard + ARIA verified.
  - `/styleguide` dev-only route showing every component and state.
  - Only tokens used (lint rule or grep test forbids raw hex in `components/`).
  - Unit tests: SeverityBadge shape + label per severity; Button variants; Dialog Esc/focus trap.

### T-043 — Design system — data-viz & composite components
- Status: todo | Priority: P0 | Size: M | Depends: T-005 | Wave: 3 | Agent: unassigned | Claimed: —
- Blocks: T-031, T-032, T-033, T-034, T-036, T-038
- Touches: `frontend/src/components/ui/**` (new files + exports only), `frontend/src/app/styleguide/**`
- Requirements: NFR-UX-001/002
- Note: Split from the original T-005 (too large for one day).
- Acceptance:
  - Components from `06 §6`: StatNumber, PillMeter (incl. hatched unknown state), ColumnBars, RingGauge, AccordionRow (Radix Accordion), TimelineGrid, LiveFeedItem, ConfidenceMeter, DiffRow.
  - All shown on `/styleguide`; respect `prefers-reduced-motion`.
  - Unit tests: ConfidenceMeter colour ramp (< 0.6 / 0.6–0.85 / ≥ 0.85) and breakdown tooltip; DiffRow highlights only differing cells; ColumnBars highlighted bar + tooltip chip.
  - Visual comparison against `reference-dashboard.png` in the PR (screenshots).

---

# E1 — Authentication

### T-006 — Auth data model
- Status: todo | Priority: P0 | Size: S | Depends: T-003 | Wave: 3 | Agent: unassigned | Claimed: —
- Blocks: T-007, T-009
- Touches: `backend/app/models/{user,refresh_token,audit_log}.py`, new migration
- Requirements: FR-AUT-001/002/006
- Acceptance:
  - Tables `users`, `refresh_tokens`, `audit_logs` exactly per `05 §2.1, 2.2, 2.19` incl. constraints and indexes.
  - Migration reversible (upgrade/downgrade tested); model tests.
  - **Migration lock.**

### T-007 — Auth & users backend
- Status: todo | Priority: P0 | Size: L | Depends: T-006 | Wave: 4 | Agent: unassigned | Claimed: —
- Blocks: T-008, T-011, T-026
- Touches: `backend/app/core/{security,deps,rate_limit}.py`, `backend/app/api/v1/{auth,users}.py`, `backend/app/services/{auth_service,user_service,audit_service}.py`, `backend/app/schemas/{auth,user}.py`, `backend/app/main.py` (one bootstrap line)
- Requirements: FR-AUT-001…007, NFR-SEC-003/004
- Acceptance:
  - Endpoints in `04 §2` (incl. `POST /auth/change-password`) and `§3` users (API keys come in T-011) with exact schemas/errors.
  - Argon2id hashing; JWT HS256 15 min; refresh rotation with reuse detection (reuse revokes the family); refresh cookie httpOnly / SameSite=Lax / path `/api/v1/auth` / `Secure` when `APP_ENV=production`; refresh requires `X-Requested-With`.
  - `require_role` dependency; viewer < analyst < admin; tests for every role on a sample protected route.
  - Rate limits: login 5 failures/min/IP+email and change-password 5 failures/min/user → 429 with `Retry-After`.
  - Bootstrap: first admin from `ADMIN_EMAIL`/`ADMIN_PASSWORD` on startup if `users` is empty (idempotent).
  - WS ticket issue/consume helper (single use, 60 s TTL, in-memory) — consumed in T-026.
  - Audit entries: login, user create/update, password change.

### T-008 — Frontend auth
- Status: todo | Priority: P0 | Size: M | Depends: T-005, T-007 | Wave: 5 | Agent: unassigned | Claimed: —
- Blocks: T-031, T-032, T-034, T-037, T-038, T-049
- Touches: `frontend/src/features/auth/**`, `frontend/src/lib/api/**`, `frontend/src/store/auth.ts`, `frontend/src/app/router.tsx` (guards), app shell nav (role filtering)
- Requirements: FR-AUT-003, NFR-SEC-001
- Acceptance:
  - Login page in glass style; access token in memory only.
  - Silent refresh on app load and on 401 (single in-flight refresh).
  - Route guards by role per the table in `02 §3.1`; nav hides items the role cannot use.
  - Logout clears state; user menu (profile, users for admin, sign out).
  - Tests for refresh and guard logic (mock API).

---

# E2 — Data model & ingest

### T-009 — Core schema migration & models
- Status: todo | Priority: P0 | Size: L | Depends: T-003, T-006 | Wave: 4 | Agent: unassigned | Claimed: —
- Blocks: T-011, T-017, T-019, T-044
- Touches: `backend/app/models/**` (remaining tables), new migration(s), `backend/app/db/seed.py`, `backend/app/main.py` (one bootstrap line)
- Requirements: All of `05`; FR-ING-001
- Acceptance:
  - All tables in `05 §2.3–2.18` incl. **§2.17.1 `simulation_ground_truth`** and the new columns (`entities.detection_requested_at`, `findings.resolved_evidence_hash` / `explained_evidence_hash`, `injected_issues.acceptable_rule_keys`, `evaluation_runs.ignored` / `matching`) with CHECK, partial/unique constraints and indexes as specified.
  - Bootstrap (startup, idempotent): three `source_systems` with default field authority (keys exactly as `03 §M1`) and status mappings (`03 §M2`); admin edits are never overwritten. (Rules are synced in T-019.)
  - Migration upgrade/downgrade tested; constraint tests (e.g. a record cannot have two non-rejected links; `rejected_pairs` ordering CHECK).
  - **Migration lock.**

### T-010 — Normalization library
- Status: todo | Priority: P0 | Size: M | Depends: T-002 | Wave: 2 | Agent: unassigned | Claimed: —
- Blocks: T-011, T-012, T-013, T-016
- Touches: `backend/app/domain/normalize/**`, `backend/tests/unit/domain/normalize/**`
- Requirements: FR-NRM-001…006
- Acceptance:
  - Functions in `03 §M2` with the examples given; nickname table; gmail canonicalization; phone E.164 via `phonenumbers` with default region; amounts to `Decimal`.
  - `normalize_status(system, record_type, s)` returns only the canonical vocabulary for that record type; unknown → `None` + `status_unmapped`.
  - `plans.py`: plan catalog + `normalize_plan` (aliases per `03 §M2`).
  - `normalize_ts` rejects naive datetimes; accepts ISO 8601 with offset and epoch seconds.
  - `name_block` helper (metaphone of last token + first initial) for blocking.
  - Edge cases tested (empty, None, emoji, RTL, 2-digit years rejected); pure (import-linter passes); ≥ 90% coverage.

### T-011 — Ingest API & API keys
- Status: todo | Priority: P0 | Size: L | Depends: T-007, T-009, T-010 | Wave: 5 | Agent: unassigned | Claimed: —
- Blocks: T-012, T-015, T-037, T-042, T-048, T-049
- Touches: `backend/app/api/v1/{ingest,api_keys}.py`, `backend/app/services/ingest_service.py`, `backend/app/schemas/{ingest,api_key}.py`, `backend/app/api/v1/router.py` (include lines)
- Requirements: FR-ING-001…006, 009 (retry endpoint), 010, FR-AUT-005 (API keys), NFR-REL-001
- Acceptance:
  - `POST /ingest/events`, `GET /ingest/events`, `POST /ingest/events/{id}/retry`, and `/api-keys` endpoints exactly per `04 §3, §5` (partial rejection, 413, per-record-type validation, unknown payload keys kept raw).
  - Idempotency key per `03 §M1` (raw `payload_hash`, includes `event_type`); duplicates counted, not re-queued.
  - API-key auth (hashed, prefix shown, bound-to-source check) or admin JWT; rate limit 60/min/key.
  - `NOTIFY ingest_pending` after commit; 202 returned before any processing.
  - Audit entries for API key create/revoke and event retry.

### T-012 — Record upsert & versioning
- Status: todo | Priority: P0 | Size: M | Depends: T-010, T-011, T-044 | Wave: 6 | Agent: unassigned | Claimed: —
- Blocks: T-017, T-019, T-047
- Touches: `backend/app/services/record_service.py`, `backend/app/workers/pipeline.py` (hook only), tests
- Requirements: FR-ING-007, FR-ING-008, FR-NRM-*
- Acceptance:
  - New/update/delete/out-of-order semantics per `03 §M1`; `record_hash` equality skips the version bump; `changed_fields` computed on normalized fields; soft delete.
  - Per-record advisory lock; equal-timestamp tie-break by `received_at`, then `id` (`02 §3.3`).
  - Returns a `RecordChanged` result to the pipeline (consumed by T-017).
  - Invariant 1: replay-twice yields identical DB state; concurrent same-record events end in a deterministic state (test).

### T-044 — Ingest worker loop
- Status: todo | Priority: P0 | Size: M | Depends: T-009 | Wave: 5 | Agent: unassigned | Claimed: —
- Blocks: T-012
- Touches: `backend/app/workers/{queue,run,pipeline}.py`, `backend/app/main.py` (one lifespan line), tests
- Requirements: FR-ING-006, FR-ING-009, NFR-REL-001/002
- Note: Split from the original T-011 (worker loop was a separate day of work).
- Acceptance:
  - Claim batches with `FOR UPDATE SKIP LOCKED` (`pending → processing`); `LISTEN ingest_pending` wake-up with a 1 s polling fallback.
  - Stuck `processing` rows older than 5 min re-queued; `attempts` incremented; after 5 attempts stays `failed` with a PII-free error.
  - `WORKER_MODE=inline` (asyncio task started in lifespan) and `separate` (`python -m app.workers.run`).
  - `pipeline.process_event(session, event)` hook; a stub that marks the event processed until T-012.
  - Tests: two concurrent workers never double-process; crash recovery (kill mid-batch → re-queued); failure path.

### T-047 — Retention prune job
- Status: todo | Priority: P2 | Size: S | Depends: T-012 | Wave: 7 | Agent: unassigned | Claimed: —
- Blocks: —
- Touches: `backend/app/services/retention_service.py`, `Makefile` (one `prune` target), `docs/07_AGENT_RULES.md` §15 (one line), tests
- Requirements: NFR-DAT-002
- Acceptance:
  - `make prune days=90` deletes `processed` ingest events and non-current `record_versions` older than N days, in batches of 1,000.
  - Never deletes the current version of a record or anything referenced by an active finding's evidence.
  - Admin-only audit entry with counts; dry-run flag; test.

---

# E3 — Simulation

### T-013 — Synthetic data generator
- Status: todo | Priority: P0 | Size: L | Depends: T-002, T-010 | Wave: 3 | Agent: unassigned | Claimed: —
- Blocks: T-014
- Touches: `backend/app/simulation/{generator,noise,catalog}.py`, tests
- Requirements: FR-SIM-002, FR-SIM-003, NFR-DAT-001
- Acceptance:
  - Deterministic for `(seed, config)`; ground-truth customers with lifecycle, subscriptions (plan catalog prices), invoices, tickets.
  - CRM/Billing/Support event streams with noise **within the limits in `03 §M9`** (noise never triggers a rule).
  - Distinct but linkable identifiers per system (e.g. `C-1042`, `B-5521`, `Z-9013`); `external_refs` on only `external_ref_rate` of Billing accounts.
  - Emits ground-truth mapping rows (`system_key, record_type, external_id → ground_truth_key`); ground-truth keys never appear in payloads.
  - Only `example.com`-style data and reserved phone ranges; with noise disabled output equals ground truth (test); no DB access.

### T-014 — Anomaly injector & labels
- Status: todo | Priority: P0 | Size: L | Depends: T-013 | Wave: 4 | Agent: unassigned | Claimed: —
- Blocks: T-015
- Touches: `backend/app/simulation/{injector,catalog}.py`, tests
- Requirements: FR-SIM-004, FR-SIM-005
- Acceptance:
  - All 15 anomaly types from the mapping table in `03 §M9`, each with `expected_rule_key` and `acceptable_rule_keys`.
  - Label objects (`issue_type`, `ground_truth_key`, `expected_rule_key`, `acceptable_rule_keys`, `system_key`, `details`, `is_decoy`); decoys included.
  - Reproducible by seed; each mutation changes exactly one system view and only the intended fields (property test).

### T-015 — Simulation runner & endpoints
- Status: todo | Priority: P1 | Size: L | Depends: T-011, T-014, T-026 | Wave: 6 | Agent: unassigned | Claimed: —
- Blocks: T-036, T-039, T-042, T-048
- Touches: `backend/app/simulation/runner.py`, `backend/app/api/v1/simulation.py`, `backend/app/services/simulation_service.py`, `backend/app/schemas/simulation.py`, `backend/app/api/v1/router.py` (include line)
- Requirements: FR-SIM-001, FR-SIM-005, FR-SIM-006
- Acceptance:
  - Endpoints `POST/GET /simulation/runs`, `GET /{id}`, `POST /{id}/drift`, `POST /{id}/stop`, `POST /simulation/reset` per `04 §11` (incl. `external_ref_rate`).
  - Writes `simulation_ground_truth` rows **before** emitting a record's first event; persists `simulation_runs` and `injected_issues`.
  - Emits events through the ingest service (no direct record writes) at the configured rate; publishes `simulation.progress` every second.
  - Only one active run (409); reset stops the run and deletes exactly the tables listed in `04 §11`; requires `"confirm":"RESET"`; admin only; audit entries.

---

# E4 — Entity resolution

### T-016 — Matching domain logic
- Status: todo | Priority: P0 | Size: L | Depends: T-010 | Wave: 3 | Agent: unassigned | Claimed: —
- Blocks: T-017
- Touches: `backend/app/domain/matching/**`, tests
- Requirements: FR-ENT-002, FR-ENT-003, FR-ENT-009
- Acceptance:
  - Blocking keys across all systems incl. the record's own; feature functions and scorer per `03 §M3` (weights, available-weight renormalization, thin-evidence cap 0.59, external-ref shortcut).
  - Returns score + feature breakdown; threshold decision helper; `primary.py` implements the primary-account order from `03 §M3` step 4.
  - Pure; labeled pair fixture set (≥ 60 pairs incl. nicknames, typos, shared phone, different people with the same name, same-system duplicates): recall ≥ 0.95 (auto + review) and no false auto-match.

### T-017 — Entity resolution service
- Status: todo | Priority: P0 | Size: L | Depends: T-009, T-012, T-016 | Wave: 7 | Agent: unassigned | Claimed: —
- Blocks: T-018, T-025, T-027, T-046
- Touches: `backend/app/services/resolution_service.py`, `backend/app/workers/pipeline.py` (hook line), tests
- Requirements: FR-ENT-001, 004…008, FR-DET-004
- Acceptance:
  - On account changes: candidate retrieval via expression indexes, scoring, link/join/create-entity per `03 §M3`; same-system extras linked for R012.
  - Advisory locks on sorted blocking keys prevent duplicate entity creation (concurrency test with two workers).
  - Children attach via parent (`match_method=parent`); waiting orphan children attached when their parent links.
  - Re-evaluation on identity-field change; rejected pairs honoured; never auto-merges two entities; canonical name/email from highest authority.
  - Sets `entities.detection_requested_at` for every touched entity in the same transaction; returns new `needs_review` links for alerting.
  - Idempotent (replay test).

### T-018 — Link review endpoints
- Status: todo | Priority: P1 | Size: M | Depends: T-017 | Wave: 8 | Agent: unassigned | Claimed: —
- Blocks: T-038, T-042, T-048
- Touches: `backend/app/api/v1/links.py`, `backend/app/services/link_service.py`, `backend/app/schemas/link.py`, router include line, tests
- Requirements: FR-ENT-006
- Acceptance:
  - `GET /links`, `POST /links/{id}/confirm`, `POST /links/{id}/reject` per `04 §6`; analyst role.
  - Confirm → `link_certainty = 1.0` in scoring and a detection request for the entity.
  - Reject → `rejected_pairs` row(s), record re-resolved, detection requested for old and new entity.
  - Audit entries; 409 when already decided; tests.

---

# E5 — Detection

### T-019 — Rule engine framework
- Status: todo | Priority: P0 | Size: L | Depends: T-009, T-012 | Wave: 7 | Agent: unassigned | Claimed: —
- Blocks: T-020, T-021, T-022, T-023, T-024, T-028
- Touches: `backend/app/domain/rules/{base,registry}.py`, `backend/app/services/{context_builder,rule_runner}.py`, `backend/app/main.py` (one bootstrap line), tests
- Requirements: FR-DET-001…003, 007
- Acceptance:
  - `Rule` protocol (incl. `version`, `config_model`), `FindingCandidate`, `EntityContext` per `03 §M4`; `@register_rule` with auto-discovery of `domain/rules/` modules.
  - Context builder: primary accounts (order from `03 §M3`), `extra_accounts`, children, and links with status `auto_matched`, `confirmed`, `needs_review`; no N+1 (query count asserted).
  - Runner: enabled rules only, per-rule try/except, config + severity overrides from `rules`.
  - Registry → table sync on startup per `03 §M4` (keeps admin overrides, adds new config keys, version change requests re-detection).
  - Tests with a fake rule.

### T-020 — Rules R001–R003 (field conflicts)
- Status: todo | Priority: P0 | Size: M | Depends: T-019 | Wave: 8 | Agent: unassigned | Claimed: —
- Blocks: T-025
- Touches: `backend/app/domain/rules/field_rules.py`, tests
- Requirements: FR-DET-002
- Acceptance:
  - R001 email, R002 name (threshold from config; nickname/formatting variants must **not** fire), R003 phone.
  - Candidates carry fields, values, involved records and only compared timestamps.
  - Table-driven tests incl. decoys and missing-data cases.

### T-021 — Rules R004–R006, R014 (status, plan, amount)
- Status: todo | Priority: P0 | Size: M | Depends: T-019 | Wave: 8 | Agent: unassigned | Claimed: —
- Blocks: T-039
- Touches: `backend/app/domain/rules/status_rules.py`, tests
- Requirements: FR-DET-002
- Acceptance:
  - R004, R005, R006 (via `normalize_plan`), R014 (default price table = plan catalog, `tolerance`).
  - Status equivalence per `03 §M2`; another active subscription suppresses R004; tests per rule incl. multi-subscription edge cases.

### T-022 — Rules R007–R010 (temporal)
- Status: todo | Priority: P0 | Size: M | Depends: T-019 | Wave: 8 | Agent: unassigned | Claimed: —
- Blocks: T-039
- Touches: `backend/app/domain/rules/temporal_rules.py`, tests
- Requirements: FR-DET-002
- Acceptance:
  - R007 (tolerance config), R008 (grace days), R009, R010; timezone-aware comparisons.
  - Boundary tests (exactly at tolerance); uses `ctx.now`, never the system clock.

### T-023 — Rules R011–R013, R015 (structural/logic)
- Status: todo | Priority: P1 | Size: M | Depends: T-019 | Wave: 8 | Agent: unassigned | Claimed: —
- Blocks: T-039
- Touches: `backend/app/domain/rules/structural_rules.py`, tests
- Requirements: FR-DET-002, FR-ENT-008
- Acceptance:
  - R011, R012 (fires on `extra_accounts`), R013 (orphan billing account), R015 (concrete definition in `03 §M4`).
  - Config thresholds; tests incl. false-positive guards.

### T-024 — Scoring & finding lifecycle
- Status: todo | Priority: P0 | Size: L | Depends: T-019 | Wave: 8 | Agent: unassigned | Claimed: —
- Blocks: T-025, T-027, T-045, T-046
- Touches: `backend/app/domain/scoring/**`, `backend/app/services/finding_service.py`, `backend/app/models/finding*.py` (behaviour only), tests
- Requirements: FR-DET-005/006/008, FR-EVD-001…004, FR-FND-001…004
- Acceptance:
  - Pure functions per `03 §M5`: `confidence`, `priority`, `escalate_severity`, `fingerprint`, `evidence_hash` (`{rule_key, fields, timestamps}` only), `suggested_authority` (3-step rule).
  - The worked example in `03 §M5` (0.829 / 2.487) is a unit test.
  - Upsert algorithm per `03 §M6` in one transaction: create/update/auto-resolve and the system reopen rules (incl. `resolved_evidence_hash`); writes `finding_events`; updates entity counters and health per `05 §5.3`.
  - State machine = the transition table in `03 §M6`; illegal → `ConflictError` with the allowed list.
  - Invariants 2, 3, 5 from `03 §Cross-module invariants` tested.

### T-025 — Detection loop & pipeline wiring
- Status: todo | Priority: P0 | Size: L | Depends: T-017, T-020, T-024, T-026, T-045 | Wave: 10 | Agent: unassigned | Claimed: —
- Blocks: T-028, T-030, T-039, T-050
- Touches: `backend/app/workers/{pipeline,detection_loop}.py`, `backend/app/services/detection_service.py`, `backend/app/main.py` (one lifespan line), tests
- Requirements: FR-DET-004, NFR-PERF-002, NFR-REL-004, NFR-OBS-003
- Acceptance:
  - Ingest pipeline wired: record upsert → resolution → detection request (one transaction).
  - Detection loop per `02 §3.3`: claims entities with `detection_requested_at ≤ now − 500 ms` (`SKIP LOCKED`), runs context → rules → scoring → findings → alerts in one transaction, clears the request only if unchanged since claim.
  - Publishes after commit: `finding.*`, `alert.created`, `entity.updated`, `link.needs_review`, `dashboard.counters`; `ingest.stats` every 2 s (incl. `detection_pending`).
  - Explanation hook (enqueue function; no-op until T-030).
  - End-to-end test: ingest status-conflict pair → finding + alert + WS event; invariant 2 (re-run → nothing new); invariant 8 (kill between transactions → detection still happens); latency p95 < 2 s for 200 events.

### T-045 — Alert service & policy
- Status: todo | Priority: P0 | Size: M | Depends: T-024 | Wave: 9 | Agent: unassigned | Claimed: —
- Blocks: T-025
- Touches: `backend/app/services/alert_service.py`, tests
- Requirements: FR-ALR-001, FR-ALR-002
- Note: Split from the original T-025.
- Acceptance:
  - Alert creation policy table in `03 §M7` as a pure function of the finding change.
  - `dedup_key` formats and the 10-minute window (bypassed when severity increases); link alerts once per link.
  - Writes `alerts`; returns created alerts for publishing; tests for every policy row and dedup edge.

---

# E6 — Real-time & API

### T-026 — EventBus & WebSocket server
- Status: todo | Priority: P0 | Size: L | Depends: T-007 | Wave: 5 | Agent: unassigned | Claimed: —
- Blocks: T-015, T-025, T-032, T-046
- Touches: `backend/app/realtime/{bus,ws_manager,events}.py`, `backend/app/api/ws.py`, tests
- Requirements: FR-RTM-001…003, 005
- Acceptance:
  - `EventBus` interface + `InMemoryEventBus`; ULID event ids; envelope per `04 §14.1` for every server message (incl. `system.ping` / `system.pong`).
  - `WSManager`: topics, topic permissions per `04 §14`, bounded per-connection queue (100; slow client dropped), heartbeat 25 s.
  - `/ws?ticket=` at the server root; close `4401` on bad/used/expired ticket; subscribe/unsubscribe/ping.
  - Tests with the Starlette test client: multi-client broadcast, auth failure, topic filtering, admin-only `simulation` topic.

### T-027 — Read/write REST APIs
- Status: todo | Priority: P0 | Size: L | Depends: T-017, T-024 | Wave: 9 | Agent: unassigned | Claimed: —
- Blocks: T-030, T-033, T-034, T-035, T-042, T-048, T-049
- Touches: `backend/app/api/v1/{entities,records,findings,alerts,audit}.py`, query services, schemas, router include lines, tests
- Requirements: FR-FND-002/005/006, FR-ALR-003, FR-AUT-006
- Acceptance:
  - All endpoints in `04 §6` (entities, timeline, records), `§7` (except explain), `§8`, `§12` with filters, sorting, pagination, error codes, role checks.
  - Static routes (`/findings/export.csv`, `/findings/bulk`) registered before `/findings/{id}`; CSV export streams (max 10,000 rows).
  - PATCH/bulk transitions go through `finding_service` (T-024) and write audit entries.
  - Findings list uses the designed indexes (EXPLAIN checked in a test); OpenAPI matches the spec; authorization tests; `make api-types` produces frontend types.

### T-028 — Rules & systems endpoints
- Status: todo | Priority: P1 | Size: M | Depends: T-019, T-025 | Wave: 11 | Agent: unassigned | Claimed: —
- Blocks: T-037, T-042, T-048
- Touches: `backend/app/api/v1/{rules,source_systems}.py`, services, schemas, router include lines, tests
- Requirements: FR-DET-007
- Acceptance:
  - Endpoints in `04 §4, §9`; `GET /rules` includes `version` and `config_schema`.
  - Rule config validated against the rule's `config_model`; changes set `detection_requested_at` in batches per `04 §9` and return `reevaluation: queued`.
  - Field authority PATCH accepts only the keys listed in `03 §M1`; values in [0,1].
  - Audit entries; changing authority/reliability changes subsequent confidence/authority results (test).

### T-046 — Dashboard endpoints
- Status: todo | Priority: P0 | Size: M | Depends: T-017, T-024, T-026 | Wave: 9 | Agent: unassigned | Claimed: —
- Blocks: T-031, T-042, T-048
- Touches: `backend/app/api/v1/dashboard.py`, `backend/app/services/dashboard_service.py`, `backend/app/schemas/dashboard.py`, router include line, tests
- Requirements: FR-DSH-001, FR-DSH-002, NFR-PERF-005
- Note: Split from the original T-027.
- Acceptance:
  - `GET /dashboard/summary` with every field in `04 §10` (`by_status`, `explained_share`, `spotlight`, nullable `consistency_score`, ingest stats from the latest `ingest.stats` event).
  - `GET /dashboard/trends?range=7d|30d`.
  - Consistency score per FR-DSH-002 (unit-tested incl. the empty case); 5 s in-memory cache.
  - p95 < 400 ms on 10k entities / 50k findings (perf test with generated rows).

### T-050 — PgNotify EventBus & separate worker mode
- Status: todo | Priority: P2 | Size: M | Depends: T-025 | Wave: 11 | Agent: unassigned | Claimed: —
- Blocks: —
- Touches: `backend/app/realtime/pg_bus.py`, `backend/app/workers/run.py` (bus selection), `docker-compose.yml` (optional `worker` profile), tests
- Requirements: FR-RTM-001 (multi-process), NFR-REL-002
- Note: Needed only for the scalability story; MVP demo runs inline.
- Acceptance:
  - `PgNotifyEventBus` per `02 §3.4` (`NOTIFY rs_events`; envelopes > 7 KB sent by reference and re-read).
  - `EVENT_BUS=pg_notify` + `WORKER_MODE=separate` works end-to-end: worker in another process, WS client still receives `finding.created` (integration test).
  - Compose profile `worker` runs `python -m app.workers.run`.

---

# E7 — AI explanations

### T-029 — Gemini client wrapper
- Status: todo | Priority: P0 | Size: L | Depends: T-002 | Wave: 2 | Agent: unassigned | Claimed: —
- Blocks: T-030
- Touches: `backend/app/ai/**`, tests
- Requirements: FR-AIX-002…006
- Acceptance:
  - **First:** re-verify the model name (default `gemini-3.5-flash-lite`), free-tier limits, structured-output support and `google-genai` usage in the official docs; record the result under Q-001 in `08`.
  - `GeminiClient.explain(evidence) → ExplanationResult` with JSON-schema structured output, temperature ≤ 0.3, 15 s timeout.
  - Prompt `prompts/explain_v1.md` treats evidence as untrusted data; redaction (emails → `j***@domain`, phones → last 2 digits) on by default.
  - Pydantic validation; one retry on invalid output; deterministic fallback renderer for all 15 rule keys.
  - Semaphore (`GEMINI_MAX_CONCURRENCY`), exponential backoff with jitter on 429/5xx, daily budget, circuit breaker (5 failures → 60 s).
  - `input_hash` helper per `03 §M8`; `FakeGeminiClient` for tests; no network in tests; missing key → fallback with one log line.

### T-030 — Explanation service & endpoint
- Status: todo | Priority: P0 | Size: M | Depends: T-025, T-027, T-029 | Wave: 11 | Agent: unassigned | Claimed: —
- Blocks: T-041, T-042, T-048
- Touches: `backend/app/services/explanation_service.py`, `backend/app/workers/explain_worker.py`, `backend/app/api/v1/findings.py` (explain endpoint only), tests
- Requirements: FR-AIX-001, 003, 004, 007, NFR-REL-004
- Acceptance:
  - Priority queue (highest `priority_score` first) + 30 s sweeper based on `explained_evidence_hash` (`03 §M8`); failure fallbacks retried at most every 10 min within budget.
  - Cache hits only on non-fallback rows; regenerate always inserts a new row; saves `finding_explanations`; sets `explained_evidence_hash`; publishes `finding.explanation_ready`.
  - `POST /findings/{id}/explain` (analyst, 10/min/user, 429 on exhausted budget).
  - Invariant 6: LLM failures never change finding state; tests with the fake client.

---

# E8 — Frontend features

### T-031 — Dashboard page
- Status: todo | Priority: P0 | Size: L | Depends: T-008, T-032, T-043, T-046 | Wave: 10 | Agent: unassigned | Claimed: —
- Blocks: T-040
- Touches: `frontend/src/features/dashboard/**`
- Requirements: FR-DSH-001…003, NFR-UX-*
- Acceptance:
  - Layout and component mapping per `06 §7.1` (greeting, PillMeters, big numbers, Spotlight, Findings this week, Ingest ring, Resolution progress, System health accordion, Recent activity, Live feed).
  - Live counters from `dashboard.counters` / `ingest.stats`; 60 s safety refetch.
  - Skeleton/empty/error states; one orchestrated load animation; responsive; screenshots vs reference in the PR; data via generated types.

### T-032 — WebSocket client, live feed, toasts
- Status: todo | Priority: P0 | Size: L | Depends: T-008, T-026, T-043 | Wave: 6 | Agent: unassigned | Claimed: —
- Blocks: T-031, T-033, T-035
- Touches: `frontend/src/lib/ws/**`, `frontend/src/store/live.ts`, `frontend/src/features/alerts/LiveFeed*`, app providers
- Requirements: FR-RTM-004/005, NFR-UX-005
- Acceptance:
  - Ticket → connect → subscribe; reconnect with backoff 1→30 s; 60 s silence (no `system.ping`) = disconnected.
  - De-duplication by event id; updates TanStack Query caches and the live-feed store (cap 200); refetch key queries on reconnect.
  - Connection indicator; toasts per severity policy (`03 §M7`); "N new" pill instead of layout shift when scrolled; `aria-live` regions.
  - Tests with a mock WebSocket (reconnect, de-dup, ordering, heartbeat timeout).

### T-033 — Findings list & drawer
- Status: todo | Priority: P0 | Size: L | Depends: T-027, T-032, T-043 | Wave: 10 | Agent: unassigned | Claimed: —
- Blocks: T-040
- Touches: `frontend/src/features/findings/**`
- Requirements: FR-FND-005/006, FR-AIX-008
- Acceptance:
  - Table + filters + sort + pagination per `06 §7.2`; filters and the open drawer (`?finding=<id>`) synced to the URL.
  - Drawer: evidence (`DiffRow`), confidence breakdown tooltip, AI explanation card (AI/Template badge, pending state, regenerate), history, sticky action bar (ack / resolve / false positive with required note).
  - Bulk actions; "Export CSV" with current filters (analyst+).
  - Live updates without losing scroll/selection; tests for filters and the transition UI (illegal transitions disabled).

### T-034 — Entities list & detail
- Status: todo | Priority: P1 | Size: L | Depends: T-008, T-027, T-043 | Wave: 10 | Agent: unassigned | Claimed: —
- Blocks: —
- Touches: `frontend/src/features/entities/**`
- Requirements: FR-ENT-001/009, FR-DSH-001
- Acceptance:
  - Searchable list with health chips; detail page per `06 §7.3` (system columns with differing fields highlighted, children, links with feature breakdown, findings, timeline).
  - Loading/empty/error states; live `entity.updated` handling.

### T-035 — Alerts page & bell
- Status: todo | Priority: P1 | Size: M | Depends: T-027, T-032 | Wave: 10 | Agent: unassigned | Claimed: —
- Blocks: —
- Touches: `frontend/src/features/alerts/**`, app shell bell component
- Requirements: FR-ALR-003
- Acceptance:
  - Bell dropdown with unread count and latest 5; full page grouped by day with filters; mark read / read-all.
  - Counts stay in sync with WS events; keyboard accessible.

### T-036 — Simulation & evaluation pages
- Status: todo | Priority: P1 | Size: M | Depends: T-015, T-039, T-043 | Wave: 12 | Agent: unassigned | Claimed: —
- Blocks: T-040, T-041
- Touches: `frontend/src/features/simulation/**`
- Requirements: FR-SIM-001/006/007
- Acceptance:
  - Run form with validation matching `04 §11` (incl. anomaly types and `external_ref_rate`); run status ring with live progress; "Simulate drift" accent button; stop; reset via `Dialog` with typed confirmation.
  - Evaluation view: precision/recall/F1 (`display-xl`), matching metrics, per-type bars, misses/false positives; admin only.

### T-037 — Rules & systems pages
- Status: todo | Priority: P1 | Size: M | Depends: T-008, T-011, T-028 | Wave: 12 | Agent: unassigned | Claimed: —
- Blocks: —
- Touches: `frontend/src/features/{rules,systems}/**`
- Requirements: FR-DET-007, FR-ING-009
- Acceptance:
  - Rules table (Switch, severity Select, config Drawer generated from `config_schema`).
  - Systems cards (reliability Slider, authority editor limited to the documented keys) + "Failed events" table with Retry.
  - Admin only; optimistic updates with rollback on error.

### T-038 — Link review UI
- Status: todo | Priority: P1 | Size: M | Depends: T-008, T-018, T-043 | Wave: 9 | Agent: unassigned | Claimed: —
- Blocks: —
- Touches: `frontend/src/features/links/**`
- Requirements: FR-ENT-006
- Acceptance:
  - Route `/review`: queue + side-by-side comparison per `06 §7.4`; confirm/reject with optional note.
  - Keyboard shortcuts (`Y`, `N`, `J`, `K`); live `link.needs_review` additions; nav count chip; empty state when the queue is clear.

### T-049 — Settings page (profile, users, API keys, audit)
- Status: todo | Priority: P1 | Size: M | Depends: T-008, T-011, T-027 | Wave: 10 | Agent: unassigned | Claimed: —
- Blocks: —
- Touches: `frontend/src/features/settings/**`
- Requirements: FR-AUT-005, FR-AUT-006, FR-AUT-007
- Note: Split out of the original T-037.
- Acceptance:
  - Tabs per `06 §7.7`: Profile (incl. change password), Users (admin create/deactivate/role), API keys (admin; secret shown once in a `Dialog`), Audit log (admin, filterable).
  - Loading/empty/error states; role-gated tabs; tests for the one-time secret and password form validation.

---

# E9 — Quality & polish

### T-039 — Evaluation service & endpoints
- Status: todo | Priority: P1 | Size: M | Depends: T-015, T-021, T-022, T-023, T-025 | Wave: 11 | Agent: unassigned | Claimed: —
- Blocks: T-036, T-041, T-042, T-048
- Touches: `backend/app/services/evaluation_service.py`, `backend/app/api/v1/simulation.py` (evaluation endpoints only), `backend/tests/evaluation/**`
- Requirements: FR-SIM-007, FR-SIM-008, G1, G2
- Acceptance:
  - Scoring per `03 §M9`: TP / ignored / FP via `simulation_ground_truth` and `acceptable_rule_keys`; precision/recall/F1 overall and per type; misses and FP lists; matching metrics.
  - Persisted `evaluation_runs`; `GET/POST …/evaluation`.
  - Regression tests: seed 42, 300 customers, all anomaly types → precision ≥ 0.90, recall ≥ 0.85, matching recall ≥ 0.95; F1 drop > 3 points vs `backend/tests/evaluation/baseline.json` fails CI.
  - Invariant 7: `anomaly_rate = 0` with decoys → zero findings.

### T-040 — End-to-end tests
- Status: todo | Priority: P1 | Size: M | Depends: T-031, T-033, T-036 | Wave: 13 | Agent: unassigned | Claimed: —
- Blocks: —
- Touches: `frontend/e2e/**`, CI workflow (e2e job)
- Requirements: PRD §6.1 demo scenario
- Acceptance:
  - Playwright: login → start simulation → live finding on dashboard → open finding drawer → acknowledge → drift injects a new finding live.
  - Runs in CI with docker compose; traces/screenshots on failure.

### T-041 — Demo seed, README, performance check
- Status: todo | Priority: P1 | Size: M | Depends: T-030, T-036, T-039 | Wave: 13 | Agent: unassigned | Claimed: —
- Blocks: —
- Touches: `README.md`, `Makefile` (seed target), `scripts/**`, `docs/assets/**`
- Requirements: G6, NFR-PERF-001…005, NFR-OPS-001
- Acceptance:
  - `make seed` creates a ready demo (completed run with evaluation and explanations).
  - README: problem, architecture diagram, setup in ≤ 5 commands, screenshots/GIF, measured metrics table (precision/recall/latency), tech stack, how agents were used.
  - Load script verifies NFR-PERF-001/002/003 and records results in the README.

### T-042 — Hardening & security review
- Status: todo | Priority: P1 | Size: M | Depends: T-011, T-015, T-018, T-027, T-028, T-030, T-039, T-046 | Wave: 12 | Agent: unassigned | Claimed: —
- Blocks: —
- Touches: any file, **only to fix findings from the review**; `docs/notes/security-review.md`
- Requirements: NFR-SEC-001…008
- Acceptance:
  - Authorization matrix test (every endpoint × role) matches `03 §M11`.
  - PII-in-logs test; security headers; cookie flags with `APP_ENV=production`; CORS tests.
  - `pip-audit` and `npm audit` clean or documented; detect-secrets baseline clean.
  - LLM prompt-injection test (payload containing instructions does not alter output schema or behaviour).
  - Written review with residual risks.

### T-048 — API contract tests
- Status: todo | Priority: P1 | Size: M | Depends: T-011, T-015, T-018, T-027, T-028, T-030, T-039, T-046 | Wave: 12 | Agent: unassigned | Claimed: —
- Blocks: —
- Touches: `backend/tests/contract/**`, CI workflow (one job)
- Requirements: NFR-MNT-005, 04 §16
- Note: 02 §11 asked for contract tests but no task owned them.
- Acceptance:
  - A test lists every method + path from `04_API_SPEC` and asserts each exists in `/openapi.json` (no missing, no undocumented).
  - Schemathesis run against the app (authenticated as admin) with no 5xx and envelope-shaped errors.
  - Generated frontend types are up to date (`make api-types` produces no diff) in CI.

---
