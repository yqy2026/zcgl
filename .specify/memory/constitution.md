<!--
Sync Impact Report:
==================
Version Change: Initial → 1.0.0
Modified Principles: N/A (initial creation)
Added Sections: All sections (initial creation)
Removed Sections: N/A
Templates Requiring Updates:
  ✅ plan-template.md - Constitution Check section aligns with principles
  ✅ spec-template.md - Requirements structure aligned
  ✅ tasks-template.md - Task categorization reflects principles
Follow-up TODOs: None
-->

# 土地物业资产管理系统 Constitution
<!-- Land Property Asset Management System Constitution -->

## Core Principles

### I. Service Layer Architecture (NON-NEGOTIABLE)

All business logic MUST reside in the Service layer, not in API endpoints or CRUD operations.

- **Location**: `backend/src/services/` organized by domain (e.g., `asset/`, `analytics/`, `document/`)
- **Rule**: API endpoints (`api/v1/`) MUST only handle HTTP concerns (routing, parsing, response formatting)
- **Rule**: CRUD operations (`crud/`) MUST only handle database operations (queries, transactions)
- **Rule**: All business rules, validation, transformations, and orchestration MUST be in service classes
- **Rationale**: Separation of concerns enables testing, reusability, and maintainability. Business logic should be testable without HTTP fixtures.

### II. Test-First Quality Standards

Code quality is enforced through comprehensive testing with strict coverage requirements.

- **Backend Coverage**: Minimum 95% for unit tests, 85% overall (see `docs/TESTING_STANDARDS.md`)
- **Frontend Coverage**: Minimum 80% for components, 85% for hooks and services
- **Test Organization**: Tests organized by type (unit, integration, api, security, performance)
- **Critical Paths**: Authentication, authorization, payment processing require 95%+ coverage
- **Rationale**: High coverage ensures reliability, enables refactoring, and prevents regressions in a financial/business-critical system.

### III. Modular Service Organization

Services are organized by domain boundaries with clear responsibilities.

- **Structure**: Each service directory contains related services (e.g., `services/asset/` for asset-related operations)
- **Batch Operations**: Use dedicated batch services with transaction management (`batch_service.py`)
- **Validation**: Data validators co-located with services (`validators.py`)
- **No Shared State**: Services must be stateless and thread-safe
- **Rationale**: Domain-driven organization improves discoverability, reduces coupling, and enables parallel development.

### IV. API Design Consistency

All API endpoints must follow consistent patterns for predictable client interactions.

- **Import Path**: Frontend MUST use `@/api/client` (not deprecated `@/services`)
- **Routing**: Register via `route_registry.register_router()` with proper versioning (`/api/v1/`)
- **Error Handling**: Consistent error response format across all endpoints
- **Validation**: Use Pydantic v2 schemas for request/response validation
- **Rationale**: Consistency reduces cognitive load, enables code generation, and improves developer experience.

### V. Database Migration Discipline

Database schema changes must be handled through versioned migrations, never manual modifications.

- **Tool**: Alembic for all schema changes
- **Workflow**: `alembic revision --autogenerate -m "description"` → review → `alembic upgrade head`
- **Recovery**: If migration fails, use `alembic stamp head` to reset state
- **Rule**: Never modify database schema directly in production
- **Rationale**: Versioned migrations ensure reproducibility, enable rollbacks, and support multiple environments.

### VI. Type Safety & Validation

Strong typing and validation are enforced at multiple layers to prevent data corruption.

- **Backend**: Python type hints required on all functions, `mypy` type checking enforced
- **Frontend**: TypeScript strict mode enabled, no `any` types without justification
- **Schemas**: Pydantic v2 for backend validation, PropTypes/zod for frontend validation
- **Rationale**: Type safety catches errors at compile time, validates data contracts, and improves IDE support.

### VII. Environment Configuration Management

Configuration must be environment-aware and explicitly managed.

- **Environments**: `development`, `production`, `testing`, `staging` defined in `backend/.env`
- **Dependency Policy**: `strict` (all required), `graceful` (optional but warn), or `optional` (silent failure)
- **Secrets**: JWT secret must be 32+ characters in production (enforced at startup)
- **Rationale**: Explicit environment configuration prevents runtime surprises and enables safe deployments.

## Additional Constraints

### Security Requirements

- **Authentication**: JWT-based authentication with secure token storage
- **Authorization**: Role-based access control (RBAC) enforced at service layer
- **Data Validation**: All user inputs validated via Pydantic schemas before processing
- **Secrets Management**: No hardcoded credentials, use environment variables
- **OCR Security**: PaddleOCR document processing requires explicit opt-in via `--extra pdf-ocr`

### Performance Standards

- **API Response Time**: Target <200ms p95 for standard CRUD operations
- **Database Queries**: Use indexes for frequently queried fields, avoid N+1 queries
- **Frontend Rendering**: Optimize component re-renders, use React Query caching
- **File Upload**: Maximum file size limits enforced, virus scanning for documents

### Technology Constraints

- **Python Version**: 3.12 required (type checking, performance improvements)
- **Node Version**: 20+ required for frontend tooling
- **Database**: SQLite for development, PostgreSQL for production
- **Frontend Framework**: React 18 with TypeScript, Vite for build tooling
- **UI Library**: Ant Design 5 for consistent component library

## Development Workflow

### Code Review Requirements

- **Approval**: At least one reviewer required for all PRs
- **Testing**: All tests must pass (unit, integration, type checks)
- **Documentation**: Update relevant docs for API changes or new features
- **Compliance**: Verify constitution compliance (service layer, testing, type safety)

### Quality Gates

- **Pre-commit**: Linting and formatting checks (`ruff`, `eslint`)
- **Pre-push**: Type checking (`mypy`, `tsc`) and test coverage validation
- **CI/CD**: Full test suite execution with coverage reporting
- **Deployment**: Manual approval required for production deployments

### Branch Protection

- **main**: Production branch, protected, require PR approval
- **develop**: Integration branch, require CI checks
- **feature/***: Feature branches from `develop`, merge back via PR
- **hotfix/***: Emergency fixes from `main`, merge to both `main` and `develop`

## Governance

### Amendment Process

1. **Proposal**: Document proposed change with rationale in GitHub issue
2. **Review**: Technical lead review for alignment with project goals
3. **Approval**: Team consensus required for principle changes
4. **Update**: Increment version number, update all dependent templates
5. **Communication**: Announce changes via team meeting or documentation

### Versioning Policy

- **MAJOR**: Backward-incompatible changes (e.g., removing a principle, requiring new technology)
- **MINOR**: New principle added or significant guidance expansion
- **PATCH**: Clarifications, wording improvements, non-semantic changes

### Compliance Review

- **Frequency**: Review constitution compliance monthly during sprint retros
- **Scope**: Recent PRs, test coverage reports, architecture decisions
- **Action**: Address violations immediately, update documentation as needed
- **Escalation**: Persistent violations require technical lead intervention

### Runtime Guidance

- **Development Standards**: See `CLAUDE.md` for quick reference and command patterns
- **Testing Standards**: See `docs/TESTING_STANDARDS.md` for detailed test organization
- **API Documentation**: See `docs/integrations/api-overview.md` for API patterns
- **Environment Setup**: See `docs/guides/environment-setup.md` for local development

---

**Version**: 1.0.0 | **Ratified**: 2026-01-08 | **Last Amended**: 2026-01-08
