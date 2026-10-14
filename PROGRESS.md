# RealitySync — Progress

_Last updated: 2026-10-15._ Plain-language summary. The detailed, agent-facing record is in
[`docs/08_PROGRESS_HANDOFF.md`](docs/08_PROGRESS_HANDOFF.md) and the full task list is in
[`docs/09_TASKS.md`](docs/09_TASKS.md).

## At a glance

| | Tasks |
|---|---:|
| Done | 15 |
| In progress | 1 (T-011) |
| To do | 45 |
| **Total** | **61** |

**What works today:** the frontend (every screen designed, running on synthetic demo data), the
backend foundation (FastAPI, PostgreSQL, migrations, health checks, CI), and real sign-in on the
backend (users, roles, tokens, audit log). The business features (detecting disagreements between
CRM, Billing and Support) are not built yet.

---

## Done

| Task | What it delivered |
|------|-------------------|
| T-001 | Repo layout, Makefile, Docker Compose, CI, pre-commit |
| T-002 | Backend app: settings, logging without personal data, error format, `/health` |
| T-003 | Database foundation: async SQLAlchemy, Alembic, Postgres test container |
| T-051 | Repairs to the foundation (backend, infra, CI) |
| T-052 | Specs for the investigation features (Time Machine, Evidence Trail, Missing Evidence, "Could We Have Known?") |
| T-060 | New visual direction ("Capsule" glass style) written into the UI style guide |
| T-004 | Frontend app: React, Vite, Tailwind, routing, app shell |
| T-005 | Design system: buttons, forms, cards, tables, dialogs, toasts |
| T-043 | Charts, KPI cards, evidence trail and diff views |
| T-061 | Every screen designed against demo data |
| T-006 | Database tables for users, login tokens and the audit log |
| T-007 | Backend sign-in: login, token refresh with theft detection, logout, change password, roles (viewer / analyst / admin), rate limits, user management, first-admin setup |
| T-008 | Frontend sign-in: login page, silent refresh, role-based page access, account menu, demo-data mode |
| T-009 | Every remaining database table, plus CRM, Billing and Support created on startup |
| T-010 | Cleaning up names, emails, phones, statuses, plans, times and amounts so systems can be compared |

## In progress — T-011 Ingest API and API keys

Branch `agent/T-011-ingest-api` (pushed, **not merged**). The endpoint that CRM, Billing and
Support (or the simulator) send record events to.

Done:
- `POST /ingest/events`: checks every event on its own, so one bad event does not block the
  rest; refuses batches over 500 events; spots replays and counts them as duplicates; stores
  events as "pending" and wakes the worker.
- API keys for machines (`/api-keys`): created once with the secret shown one time, stored
  only as a hash, can be tied to one system, limited to 60 requests a minute, can be revoked.
- Admin list of received events with filters, and a retry button for failed ones.
- Lint and type checks pass.

Left to do:
1. Run the new tests (`test_ingest.py`, `test_api_keys.py`, `test_ingest_notify.py`) and fix
   anything that fails.
2. Run `make check`, record the decisions in `docs/08`, then merge.

---

## What should be done next (in order)

**1. Data in** — get CRM, Billing and Support records into the database
- T-011 Ingest API and API keys (in progress) · T-012 Record versioning · T-044 Ingest worker

**2. Test data** — a built-in simulator so there is something to detect
- T-013 Synthetic customers · T-014 Injected problems with answer keys · T-015 Simulation runner

**3. Matching** — work out which records are the same customer
- T-016 Matching logic · T-017 Entity resolution · T-018 Link review endpoints

**4. Detection** — find the disagreements
- T-019 Rule engine · T-020…T-023 Rules R001–R015 · T-024 Scoring and finding lifecycle
- T-025 Detection pipeline · T-045 Alerts

**5. Live updates and APIs**
- T-026 WebSockets · T-027 Read/write APIs · T-028 Rules and systems endpoints · T-046 Dashboard endpoints

**6. AI explanations** (Gemini only explains; it never decides)
- T-029 Gemini client · T-030 Explanation service

**7. Connect the screens to real data** (replace the demo data, screen by screen)
- T-031 Dashboard · T-032 Live feed · T-033 Findings · T-034 Customers · T-035 Alerts
- T-036 Simulation · T-037 Rules and systems · T-038 Link review · T-049 Settings

**8. Signature features**
- T-053 Time Machine · T-054 Missing-evidence rules · T-055 Risk signals
- T-056 "Could We Have Known?" investigations · T-057 Scenario data · T-058 Their evaluation
- T-059 Time Machine and investigation screens

**9. Quality and launch**
- T-039 Evaluation · T-040 End-to-end tests · T-048 API contract tests
- T-041 Demo seed and README · T-042 Security review · T-047 Data retention · T-050 Multi-process mode

The longest chain of dependent work runs through ingest, rules, scoring, the Time Machine, risk
and investigations (T-009 → T-011 → T-012 → T-019 → T-024 → T-053 → T-055 → T-056).

---

## Decisions waiting for the product owner

- **Q-012** — Should the last active admin be protected from demotion or deactivation? (Currently yes.)
- **Q-003 / Q-004 / Q-005** — Public demo deployment? Project licence? Currency and plan prices for synthetic data?
- Replace the `claude-code-1` agent label used in `docs/08` and `docs/09` with a neutral one?
- Delete the local-only `backup/pre-rebase` branch?

## Try it locally

```bash
cp .env.example .env    # set JWT_SECRET (32+ characters), ADMIN_EMAIL and ADMIN_PASSWORD
make dev                # database, backend on :8000, frontend on :5173
make migrate            # then restart the backend once so the first admin is created
```

Without a backend, use **Explore with demo data** on the sign-in page.
