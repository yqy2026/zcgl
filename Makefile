.PHONY: help dev dev-backend dev-frontend \
	lint lint-backend lint-frontend type-check \
	test test-backend test-frontend \
	build-frontend backend-import check \
	backend-org-cov secrets migrate

help:
	@echo "Targets:"
	@echo "  dev               Run backend and frontend dev servers"
	@echo "  dev-backend       Run backend dev server"
	@echo "  dev-frontend      Run frontend dev server"
	@echo "  lint-backend      Run Ruff for backend"
	@echo "  lint-frontend     Run ESLint for frontend"
	@echo "  type-check        Run TypeScript type check"
	@echo "  test-backend      Run backend unit tests"
	@echo "  test-frontend     Run frontend tests"
	@echo "  build-frontend    Build frontend"
	@echo "  backend-import    Import backend app to validate runtime"
	@echo "  check             Run lint, tests, build, and import checks"
	@echo "  backend-org-cov   Run org CRUD coverage test"
	@echo "  secrets           Generate SECRET_KEY and DATA_ENCRYPTION_KEY"
	@echo "  migrate           Run alembic upgrade head"

dev:
	@$(MAKE) -j2 dev-backend dev-frontend

dev-backend:
	cd backend && python run_dev.py

dev-frontend:
	cd frontend && pnpm dev

lint: lint-backend lint-frontend

lint-backend:
	cd backend && ruff check .

lint-frontend:
	cd frontend && pnpm lint

type-check:
	cd frontend && pnpm type-check

test: test-backend test-frontend

test-backend:
	cd backend && pytest -m unit

test-frontend:
	cd frontend && pnpm test

build-frontend:
	cd frontend && pnpm build

backend-import:
	cd backend && python -c "from src.main import app; print('import ok')"

check: lint-backend lint-frontend type-check test-backend test-frontend build-frontend backend-import

backend-org-cov:
	cd backend && \
		ENVIRONMENT=testing \
		DEBUG=False \
		PYDANTIC_SETTINGS_IGNORE_DOT_ENV=1 \
		SECRET_KEY=local-test-secret \
		DATABASE_URL="$${TEST_DATABASE_URL:-postgresql+psycopg://user:pass@localhost:5432/zcgl_test}" \
		python -m pytest tests/unit/crud/test_organization.py \
			--cov=src.crud.organization --cov-report=term-missing -v

secrets:
	@python -c "import secrets; print('SECRET_KEY=\"%s\"' % secrets.token_urlsafe(32))"
	@cd backend && python -m src.core.encryption

migrate:
	cd backend && alembic upgrade head
