.PHONY: help setup setup-backend setup-frontend dev dev-backend dev-frontend \
	lint lint-backend lint-frontend scan-frontend scan-frontend-report type-check type-check-e2e \
	test test-backend test-frontend test-frontend-ci test-e2e test-e2e-backend test-e2e-frontend \
	test-e2e-import test-e2e-import-backend test-e2e-import-frontend \
	test-integration test-coverage \
	build-frontend backend-import check ci-gate \
	backend-org-cov secrets migrate check-migration-naming docs-lint check-field-drift

ROOT_DIR := $(CURDIR)
BACKEND_VENV ?= $(ROOT_DIR)/backend/.venv
PYTHON ?= $(shell if [ -x "$(BACKEND_VENV)/Scripts/python.exe" ]; then echo "$(BACKEND_VENV)/Scripts/python.exe"; elif [ -x "$(BACKEND_VENV)/bin/python" ]; then echo "$(BACKEND_VENV)/bin/python"; elif command -v python >/dev/null 2>&1; then echo python; else echo python3; fi)
BACKEND_IMPORT_FALLBACK_SECRET_KEY ?= ZcglBackendImportSmoke2026StrongKey!42

help:
	@echo "Targets:"
	@echo "  setup             Install backend + frontend dependencies"
	@echo "  setup-backend     Sync backend dependencies with uv (dev extras)"
	@echo "  setup-frontend    Install frontend dependencies with pnpm"
	@echo "  dev               Run backend and frontend dev servers"
	@echo "  dev-backend       Run backend dev server"
	@echo "  dev-frontend      Run frontend dev server"
	@echo "  lint-backend      Run Ruff for backend"
	@echo "  check-migration-naming Validate Alembic migration filename convention"
	@echo "  lint-frontend     Run Oxlint for frontend"
	@echo "  scan-frontend     Run frontend px/token guard checks"
	@echo "  scan-frontend-report Export frontend px/token guard reports"
	@echo "  type-check        Run frontend Tsgo checks (app + e2e)"
	@echo "  type-check-e2e    Run frontend Tsgo E2E check"
	@echo "  test-backend      Run backend unit tests"
	@echo "  test-frontend     Run frontend tests"
	@echo "  test-frontend-ci  Run frontend tests with CI profile"
	@echo "  test-integration  Run backend integration tests with coverage"
	@echo "  test-coverage     Run all tests with coverage reports"
	@echo "  test-e2e-backend  Run backend E2E tests"
	@echo "  test-e2e-frontend Run frontend E2E tests"
	@echo "  test-e2e          Run backend and frontend E2E tests"
	@echo "  test-e2e-import   Run import-focused backend+frontend E2E regression"
	@echo "  test-e2e-import-backend  Run backend import-focused E2E tests"
	@echo "  test-e2e-import-frontend Run frontend import-focused E2E tests"
	@echo "  build-frontend    Build frontend"
	@echo "  backend-import    Import backend app to validate runtime"
	@echo "  check             Run lint, tests, build, and import checks"
	@echo "  ci-gate           Run CI gate (ruff + tsgo + unit tests)"
	@echo "  docs-lint         Run all docs checks (authority + code-evidence + plans + field drift)"
	@echo "  check-field-drift Run field spec vs ORM drift report"
	@echo "  backend-org-cov   Run org CRUD coverage test"
	@echo "  secrets           Generate SECRET_KEY and DATA_ENCRYPTION_KEY"
	@echo "  migrate           Run alembic upgrade head"

setup:
	@$(MAKE) -j2 setup-backend setup-frontend

setup-backend:
	cd backend && uv sync --frozen --extra dev

setup-frontend:
	cd frontend && pnpm install --frozen-lockfile

dev:
	@$(MAKE) -j2 dev-backend dev-frontend

dev-backend:
	cd backend && $(PYTHON) run_dev.py

dev-frontend:
	cd frontend && pnpm dev

lint: lint-backend lint-frontend

lint-backend:
	cd backend && uv run --extra dev python -m ruff check . && uv run python scripts/migration/check_migration_naming.py

check-migration-naming:
	cd backend && $(PYTHON) scripts/migration/check_migration_naming.py

lint-frontend:
	cd frontend && pnpm lint

scan-frontend:
	cd frontend && corepack pnpm guard:ui

scan-frontend-report:
	mkdir -p reports/frontend
	cd frontend && corepack pnpm guard:ui:ci

type-check:
	cd frontend && pnpm type-check && pnpm type-check:e2e

type-check-e2e:
	cd frontend && pnpm type-check:e2e

test: test-backend test-frontend

test-backend:
	cd backend && $(PYTHON) -m pytest -m unit

test-frontend:
	cd frontend && pnpm test

test-frontend-ci:
	cd frontend && CI=true pnpm test

test-e2e: test-e2e-backend test-e2e-frontend

test-e2e-backend:
	cd backend && E2E_TEST_DATABASE_URL="$${E2E_TEST_DATABASE_URL:-$${TEST_DATABASE_URL:-}}" $(PYTHON) -m pytest tests/e2e -m e2e --no-cov

test-e2e-frontend:
	cd frontend && pnpm e2e

test-e2e-import:
	bash scripts/dev/run_import_e2e.sh

test-e2e-import-backend:
	cd backend && E2E_TEST_DATABASE_URL="$${E2E_TEST_DATABASE_URL:-$${TEST_DATABASE_URL:-}}" $(PYTHON) -m pytest \
		tests/e2e/test_pdf_import_e2e.py tests/e2e/test_property_certificate_import_e2e.py -m e2e --no-cov

test-e2e-import-frontend:
	@curl -fsS http://127.0.0.1:8002/docs >/dev/null || (echo "[ERROR] Backend API is required at http://127.0.0.1:8002"; exit 2)
	cd frontend && pnpm e2e tests/e2e/user/import-guardrails.spec.ts tests/e2e/rental/import-success.spec.ts tests/e2e/user/property-certificate-import-success.spec.ts --project=chromium

build-frontend:
	cd frontend && pnpm build

backend-import:
	@cd backend && \
		RESOLVED_DATABASE_URL="$${DATABASE_URL:-$${TEST_DATABASE_URL:-$${INTEGRATION_TEST_DATABASE_URL:-}}}"; \
		RESOLVED_SECRET_KEY="$${SECRET_KEY:-}"; \
		if [ -z "$$RESOLVED_DATABASE_URL" ] && [ -f .env ]; then \
			RESOLVED_DATABASE_URL="$$(awk -F= '/^DATABASE_URL=/{print substr($$0, index($$0, "=") + 1)}' .env | tail -n 1)"; \
		fi; \
		if [ -z "$$RESOLVED_SECRET_KEY" ] && [ -f .env ]; then \
			RESOLVED_SECRET_KEY="$$(awk -F= '/^SECRET_KEY=/{print substr($$0, index($$0, "=") + 1)}' .env | tail -n 1)"; \
		fi; \
		if [ -z "$$RESOLVED_DATABASE_URL" ]; then \
			echo "[ERROR] backend-import requires DATABASE_URL."; \
			echo "Set one of: DATABASE_URL / TEST_DATABASE_URL / INTEGRATION_TEST_DATABASE_URL."; \
			echo "Example: DATABASE_URL=postgresql+psycopg://user:pass@localhost:5432/zcgl make backend-import"; \
			exit 2; \
		fi; \
		if [ -z "$$RESOLVED_SECRET_KEY" ]; then \
			RESOLVED_SECRET_KEY="$(BACKEND_IMPORT_FALLBACK_SECRET_KEY)"; \
		fi; \
		SECRET_KEY="$$RESOLVED_SECRET_KEY" DATABASE_URL="$$RESOLVED_DATABASE_URL" $(PYTHON) -c "from src.main import app; print('import ok')"

check: lint-backend lint-frontend scan-frontend type-check test-backend test-frontend build-frontend backend-import docs-lint

ci-gate: lint-backend type-check test-backend test-frontend-ci

backend-org-cov:
	cd backend && \
		ENVIRONMENT=testing \
		DEBUG=False \
		PYDANTIC_SETTINGS_IGNORE_DOT_ENV=1 \
		SECRET_KEY=local-test-secret \
		DATABASE_URL="$${TEST_DATABASE_URL:-postgresql+psycopg://user:pass@localhost:5432/zcgl_test}" \
		$(PYTHON) -m pytest tests/unit/crud/test_organization.py \
			--cov=src.crud.organization --cov-report=term-missing -v

secrets:
	@$(PYTHON) -c "import secrets; print('SECRET_KEY=\"%s\"' % secrets.token_urlsafe(32))"
	@cd backend && $(PYTHON) -m src.core.encryption

migrate:
	cd backend && $(PYTHON) -m alembic upgrade head

docs-lint:
	$(PYTHON) scripts/check_requirements_authority.py
	$(PYTHON) scripts/check_field_drift.py

check-field-drift:
	$(PYTHON) scripts/check_field_drift.py

# 运行集成测试
test-integration:
	cd backend && $(PYTHON) -m pytest -m integration --cov=src --cov-report=html --cov-report=term-missing

# 生成覆盖率报告
test-coverage:
	@echo "=== Backend Coverage ==="
	cd backend && $(PYTHON) -m pytest --cov=src --cov-report=html --cov-report=term-missing
	@echo "=== Frontend Coverage ==="
	cd frontend && pnpm test:coverage
	@echo "Coverage reports generated at:"
	@echo "  Backend:  test-results/backend/coverage/html/index.html"
	@echo "  Frontend: test-results/frontend/coverage/index.html"
