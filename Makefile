# Backend targets expect the backend virtualenv to be active (see README: Local setup).
.PHONY: dev test test-backend test-frontend lint lint-backend lint-frontend \
	types types-backend types-frontend check check-backend migrate migration seed api-types audit

dev:
	docker compose up --build

test: test-backend test-frontend

test-backend:
	cd backend && pytest

test-frontend:
	cd frontend && npm run test

lint: lint-backend lint-frontend

lint-backend:
	cd backend && ruff check . && ruff format --check . && lint-imports

lint-frontend:
	cd frontend && npm run lint

types: types-backend types-frontend

types-backend:
	cd backend && mypy --strict app

types-frontend:
	cd frontend && npm run typecheck

check: lint types test

check-backend: lint-backend types-backend test-backend

migrate:
	docker compose run --rm backend alembic upgrade head

migration:
	@if [ -z "$(m)" ]; then echo "Usage: make migration m=message"; exit 1; fi
	docker compose run --rm backend alembic revision --autogenerate -m "$(m)"

seed:
	@echo "not yet implemented (T-041)"

api-types:
	cd frontend && npm run api-types

audit:
	cd backend && pip-audit
	cd frontend && npm audit
