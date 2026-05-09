# ─────────────────────────────────────────────
# Book Manager — Docker workflow
# Requires: Docker Desktop (or docker + docker compose plugin)
# No other local dependencies needed.
# ─────────────────────────────────────────────

.PHONY: help setup up down logs shell-backend shell-frontend \
        migrate makemigration test test-watch lint

# Default target
help:
	@echo ""
	@echo "  make setup          Copy .env.example → .env (fill in credentials after)"
	@echo "  make up             Build and start all services (db + backend + frontend)"
	@echo "  make down           Stop and remove containers"
	@echo "  make logs           Tail logs from all services"
	@echo "  make migrate        Run pending Alembic migrations"
	@echo "  make makemigration  Auto-generate a new migration (MSG=your_message)"
	@echo "  make test           Run pytest inside Docker (isolated test-db)"
	@echo "  make shell-backend  Open a bash shell in the running backend container"
	@echo "  make shell-frontend Open a sh shell in the running frontend container"
	@echo ""

# ── Bootstrap ──────────────────────────────────────────────────────────────

setup:
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo "✅  .env created from .env.example — open it and fill in your credentials."; \
	else \
		echo "ℹ️   .env already exists, skipping."; \
	fi

# ── Dev environment ─────────────────────────────────────────────────────────

up: setup
	docker compose up --build

down:
	docker compose down

logs:
	docker compose logs -f

# ── Database ────────────────────────────────────────────────────────────────

migrate:
	docker compose run --rm migrate

# Usage: make makemigration MSG="add user bio column"
makemigration:
	@if [ -z "$(MSG)" ]; then echo "Usage: make makemigration MSG=\"describe your change\""; exit 1; fi
	docker compose run --rm --no-deps \
		-e DATABASE_URL=postgresql+asyncpg://postgres:postgres@db:5432/bookmanager \
		backend alembic revision --autogenerate -m "$(MSG)"

# ── Tests ───────────────────────────────────────────────────────────────────

test:
	docker compose -f docker-compose.test.yml up --build --abort-on-container-exit --exit-code-from test
	docker compose -f docker-compose.test.yml down -v

# ── Shells ──────────────────────────────────────────────────────────────────

shell-backend:
	docker compose exec backend bash

shell-frontend:
	docker compose exec frontend sh
