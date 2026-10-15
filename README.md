# RealitySync

An AI system that detects when enterprise systems disagree about the same customer.

Planning and contracts live in [`docs/`](docs/); agents start at [`AGENTS.md`](AGENTS.md).

## Run with Docker

```bash
cp .env.example .env      # then set JWT_SECRET to a long random value
make dev                  # db + backend on http://localhost:8000
make migrate              # apply database migrations (inside Docker)
```

The frontend service is not wired up yet (T-004); `make dev` currently starts the database and the API.

## Local development (backend)

Requires Python 3.12 and Docker (tests start a throwaway Postgres container unless `DATABASE_URL_TEST` is set).

```bash
py -3.12 -m venv backend/.venv          # Windows; on macOS/Linux: python3.12 -m venv backend/.venv
source backend/.venv/Scripts/activate   # Windows Git Bash; on macOS/Linux: source backend/.venv/bin/activate
pip install -e "backend[dev]"
make check-backend                      # ruff, import-linter, mypy, pytest
```

`make check` runs the backend and frontend checks together (frontend: `cd frontend && npm ci` first).

## Deploy the public demo (Vercel)

The public demo is the frontend on built-in synthetic CRM, Billing and Support data; it needs no
backend, database or secrets (D-071). `vercel.json` builds `frontend/` with `VITE_DEMO_DATA=on`, so
the login page offers "Explore with demo data" (signs in as Demo Admin, every screen visible).

- **From GitHub:** in Vercel, *Add New → Project*, import this repository, keep the root directory
  as the repository root, and deploy. Settings come from `vercel.json`; no environment variables.
- **From the CLI:** `npx vercel` (first run links the project), then `npx vercel --prod`.

Check the build locally first: `cd frontend && VITE_DEMO_DATA=on npm run build && npm run preview`.
