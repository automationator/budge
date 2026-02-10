.PHONY: help build up down logs db-upgrade db-downgrade db-revision clean restart fresh db-wait lint format test test-file web-install web-dev web-build web-lint web-test web-test-watch web-test-coverage web-test-e2e web-test-e2e-ui web-test-all update-deps outdated prod-build prod-up prod-down prod-logs prod-backup prod-restore setup-hooks

help:
	@echo "Available commands:"
	@echo "  make build         - Build Docker images"
	@echo "  make up            - Start all services (db, api, web)"
	@echo "  make down          - Stop all services"
	@echo "  make logs          - View logs from all services"
	@echo "  make db-wait       - Wait for database to be ready"
	@echo "  make db-revision   - Create new Alembic migration"
	@echo "  make db-upgrade    - Apply Alembic migrations to database"
	@echo "  make db-downgrade  - Rollback last Alembic migration"
	@echo "  make clean         - Remove containers, volumes, and images"
	@echo "  make restart       - Restart all services"
	@echo "  make fresh         - Rebuild the entire application"
	@echo "  make lint          - Run ruff linter"
	@echo "  make format        - Run ruff linter and fix issues"
	@echo "  make test          - Run tests"
	@echo "  make test-file FILE=path - Run specific test file"
	@echo "  make setup-hooks   - Configure git to use project hooks"
	@echo ""
	@echo "Frontend commands:"
	@echo "  make web-install   - Install frontend dependencies"
	@echo "  make web-dev       - Start frontend dev server"
	@echo "  make web-build     - Build frontend for production"
	@echo "  make web-lint      - Lint frontend code"
	@echo "  make web-test      - Run frontend unit tests once"
	@echo "  make web-test-watch - Run frontend unit tests in watch mode"
	@echo "  make web-test-coverage - Run frontend tests with coverage"
	@echo "  make web-test-e2e [FILE=path] - Run frontend E2E tests (optionally specific file)"
	@echo "  make web-test-e2e-ui - Run frontend E2E tests with UI"
	@echo "  make web-test-all  - Run all frontend tests (unit + E2E)"
	@echo ""
	@echo "Dependency management:"
	@echo "  make update-deps   - Update all dependency lock files (backend + frontend)"
	@echo "  make outdated      - Show available dependency updates"
	@echo ""
	@echo "Production commands:"
	@echo "  make prod-build    - Build production Docker images"
	@echo "  make prod-up       - Start production stack"
	@echo "  make prod-down     - Stop production stack"
	@echo "  make prod-logs     - View production logs"
	@echo "  make prod-backup   - Create database backup"
	@echo "  make prod-restore  - Restore database backup"

build:
	docker compose build

up:
	docker compose up -d

down:
	docker compose down

logs:
	docker compose logs -f

clean:
	docker compose down -v --remove-orphans

fresh: clean build up db-upgrade

# make db-revision MESSAGE="blah"
db-revision:
	docker compose run --rm api uv run alembic revision --autogenerate -m "$(MESSAGE)"

db-wait:
	@echo "Waiting for database..."
	@until docker compose exec db pg_isready -U "$$POSTGRES_USER" -d "$$POSTGRES_DB" > /dev/null 2>&1; do \
		sleep 1; \
	done
	@echo "Database is ready"

db-upgrade: db-wait
	docker compose run --rm api uv run alembic upgrade head

db-downgrade:
	docker compose run --rm api uv run alembic downgrade -1

restart: down up

lint:
	cd backend && uv run ruff check .

format:
	cd backend && uv run ruff check --fix .
	cd backend && uv run ruff format .

test: db-wait
	cd backend && uv run pytest -vv

# make test-file FILE=tests/teams/test_team_security.py
test-file: db-wait
	cd backend && uv run pytest -vv $(FILE)

# Frontend commands
web-install:
	cd frontend && npm install

web-dev:
	cd frontend && npm run dev

web-build:
	cd frontend && npm run build

web-lint:
	cd frontend && npm run lint

web-test:
	cd frontend && npm run test:run

web-test-watch:
	cd frontend && npm run test

web-test-coverage:
	cd frontend && npm run test:coverage

# make web-test-e2e FILE=tests/e2e/tests/nav-drawer.spec.ts
web-test-e2e:
	docker compose -f docker-compose.yml -f docker-compose.e2e.yml up -d
	cd frontend && npx playwright test $(FILE); \
	EXIT_CODE=$$?; \
	docker compose up -d; \
	exit $$EXIT_CODE

web-test-e2e-ui:
	docker compose -f docker-compose.yml -f docker-compose.e2e.yml up -d
	cd frontend && npm run test:e2e:ui; \
	EXIT_CODE=$$?; \
	docker compose up -d; \
	exit $$EXIT_CODE

web-test-all: web-test web-test-e2e

# Dependency management
update-deps:
	cd backend && uv lock --upgrade && uv sync
	cd frontend && npm update

outdated:
	@echo "=== Backend ==="
	@cd backend && uv pip list --outdated || true
	@echo ""
	@echo "=== Frontend ==="
	@cd frontend && npm outdated || true

setup-hooks:
	git config core.hooksPath .githooks
	@echo "Git hooks configured. Pre-commit hook will now run on each commit."

# Production commands
prod-build:
	docker compose -f docker-compose.prod.yml --env-file .env.prod build

prod-up: prod-build
	docker compose -f docker-compose.prod.yml --env-file .env.prod up -d
	@echo ""
	@echo "Budge is running at http://localhost:$${HTTP_PORT:-80}

prod-down:
	docker compose -f docker-compose.prod.yml --env-file .env.prod down

prod-logs:
	docker compose -f docker-compose.prod.yml --env-file .env.prod logs -f

prod-backup:
	./scripts/backup.sh

prod-restore:
ifndef FILE
	@echo "Usage: make prod-restore FILE=<backup_file>"
	@echo ""
	@echo "Example:"
	@echo "  make prod-restore FILE=./backups/budge_backup_20240115_120000.dump.gz"
else
	./scripts/restore.sh $(FILE)
endif
