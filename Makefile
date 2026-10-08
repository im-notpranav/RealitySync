.PHONY: dev test lint types check migrate seed api-types audit migration

dev:
	docker-compose up

test:
	cd backend && pytest
	cd frontend && npm run test

lint:
	cd backend && ruff check . && ruff format --check .
	cd frontend && npm run lint

types:
	cd backend && mypy --strict app
	cd frontend && npm run typecheck

check: lint types test

migrate:
	cd backend && alembic upgrade head

migration:
	@if [ -z "$(m)" ]; then echo "Usage: make migration m=message"; exit 1; fi
	cd backend && alembic revision --autogenerate -m "$(m)"

seed:
	@echo "not yet implemented"

api-types:
	@echo "not yet implemented"

audit:
	cd backend && pip-audit
	cd frontend && npm audit
