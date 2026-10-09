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
