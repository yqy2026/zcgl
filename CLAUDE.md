# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## Project Overview

**土地物业资产管理系统** (Land Property Asset Management System) - A full-stack web application for managing real estate assets, rental contracts, and property operations with Chinese/English bilingual support.

**Tech Stack**:
- **Frontend**: React 18 + TypeScript + Vite + Ant Design 5
- **Backend**: FastAPI + Python 3.12 + SQLAlchemy 2.0 + Pydantic v2
- **Database**: SQLite (dev) / PostgreSQL (prod)
- **Special**: PaddleOCR for Chinese PDF processing, Redis caching

---
### Login{"username": "admin", "password": "Admin123!@#"}


## Development Commands

### Frontend (in `frontend/` directory)

```bash
npm run dev           # Start dev server on port 5173
npm run build         # Production build
npm run type-check    # TypeScript type checking
npm run lint          # ESLint check
npm run lint:fix      # Auto-fix ESLint issues
npm test              # Run tests (Vitest)
npm run test:coverage # Coverage report
npm run test:ui       # UI mode for tests
```

### Backend (in `backend/` directory)

```bash
# Development
python run_dev.py               # Start dev server on port 8002
uvicorn src.main:app --reload --port 8002  # Alternative start

# Testing
pytest                          # Run all tests
pytest -m unit                  # Unit tests only
pytest -m integration           # Integration tests only
pytest -m api                   # API endpoint tests
pytest --cov=src --cov-report=html  # Coverage report

# Code Quality
ruff check backend/             # Linting
ruff format backend/            # Formatting
mypy backend/src                # Type checking
pre-commit run --all-files      # Run all pre-commit hooks

# Database
alembic upgrade head            # Apply migrations
alembic revision --autogenerate -m "message"  # Create migration
```

### Docker Deployment

```bash
docker-compose up -d            # Start all services
docker-compose down             # Stop all services
docker-compose logs -f [service] # View logs
```

---

## Architecture

### High-Level Structure

```
zcgl/
├── frontend/           # React 18 + TypeScript frontend
│   └── src/
│       ├── api/        # Centralized API layer (2025-12-24 reorganized)
│       │   ├── client.ts     # EnhancedApiClient with retry logic
│       │   ├── config.ts     # API configuration constants
│       │   └── index.ts      # Clean exports
│       ├── components/ # 70+ React components
│       │   ├── Forms/        # Unified form components (AssetForm, etc.)
│       │   ├── Router/       # Dynamic routing + performance monitoring
│       │   ├── Asset/        # Asset management components
│       │   └── Layout/       # Layout components
│       ├── pages/      # Page components (15 pages)
│       ├── services/   # API services (re-exports from api/)
│       ├── store/      # Zustand global state
│       └── routes/     # Route configuration
├── backend/            # FastAPI + Python backend
│   └── src/
│       ├── api/v1/     # API endpoints (versioned: /api/v1/*)
│       ├── core/       # Config, security, router_registry.py
│       ├── crud/       # Database operations (base CRUD classes)
│       ├── models/     # SQLAlchemy ORM models
│       ├── schemas/    # Pydantic request/response models
│       ├── services/   # Business logic layer
│       └── middleware/ # Auth, CORS, request processing
├── database/           # Database schemas and migrations
├── openspec/           # Spec-driven development framework
└── docs/               # Comprehensive documentation
```

### Key Architectural Patterns

**Backend - Router Registry System**:
- All APIs use centralized route registration via `core/router_registry.py`
- Unified versioned architecture: `/api/v1/*`
- Automatic route registration and dependency injection

**Backend - Layered Architecture**:
```
api/v1/          → Endpoint definitions
services/        → Business logic
crud/            → Database operations
models/          → SQLAlchemy ORM
schemas/         → Pydantic validation
middleware/      → Request/response processing
core/            → Configuration and utilities
```

**Frontend - State Management**:
- **Zustand**: Global UI state (user, theme, permissions)
- **React Query**: Server state (API data caching)
- **React Hook Form**: Form state
- **Local state**: Component-specific UI interactions

**Frontend - API Client** (2025-12-24 reorganized):
- Import from `@/api/client` for EnhancedApiClient
- Import from `@/api/config` for API configuration
- Import from `@/api` for unified exports

---

## OpenSpec Workflow

This project uses OpenSpec for spec-driven development. Before implementing features:

1. **Review existing work**: `openspec list`, `openspec list --specs`
2. **Create proposals for**: New features, breaking changes, architecture changes
3. **Skip proposals for**: Bug fixes, typos, non-breaking dependency updates
4. **Validate**: `openspec validate <change-id> --strict`
5. **Archive after deployment**: `openspec archive <change-id> --yes`

See `openspec/AGENTS.md` for complete workflow details.

---

## Testing

### Backend Test Categories (pytest markers)

```bash
pytest -m unit          # Unit tests (fast, isolated)
pytest -m integration   # Integration tests (database, services)
pytest -m api           # API endpoint tests
pytest -m e2e           # End-to-end workflow tests
pytest -m slow          # Slow tests (PDF processing, OCR)
pytest -m database      # Database-specific tests
pytest -m performance   # Performance tests
```

**Coverage Requirements**: 95%+ for both frontend and backend

### Frontend Testing

```bash
npm test                # Run tests with Vitest
npm run test:coverage   # Coverage report
npm run test:ui         # UI mode
npm run test:watch      # Watch mode
```

---

## Import Conventions

### Frontend (2025-12-24 Updated)

```typescript
// API client - recommended new paths
import { enhancedApiClient } from '@/api/client';
import { API_CONFIG } from '@/api/config';
import { enhancedApiClient, API_CONFIG } from '@/api';  // unified

// Form components - recommended new path
import { AssetForm } from '@/components/Forms';
import { OwnershipForm, ProjectForm } from '@/components/Forms';

// Backward compatible - still works
import { enhancedApiClient } from '@/services';  // re-exported
import { AssetForm } from '@/components/Asset';  // re-exported
```

### Backend

```python
# Standard imports
from src.api.v1 import assets
from src.core.config import settings
from src.models.asset import Asset
from src.schemas.asset import AssetCreate, AssetUpdate
from src.services.asset_service import AssetService
from src.crud.asset import asset_crud
```

---

## Code Style

### Frontend (TypeScript)
- **Components**: PascalCase (`AssetForm.tsx`)
- **Variables/Functions**: camelCase (`getUserProfile`)
- **Constants**: UPPER_SNAKE_CASE (`API_BASE_URL`)
- **Line length**: 100 characters
- **Indentation**: 2 spaces

### Backend (Python)
- **Files/Functions/Variables**: snake_case (`asset_service.py`)
- **Classes**: PascalCase (`AssetService`)
- **Constants**: UPPER_SNAKE_CASE (`MAX_FILE_SIZE`)
- **Line length**: 88 characters
- **Indentation**: 4 spaces

---

## Service Ports

- Frontend (dev): 5173
- Frontend (prod): 3000 (via Nginx)
- Backend API: 8002
- Redis: 6379
- Nginx: 80/443

---

## Key Features & Special Notes

- **Asset Model**: 58-field asset information management
- **PDF Processing**: PaddleOCR for Chinese text recognition (can be disabled)
- **Route Performance Monitoring**: Dynamic route loading with FCP, LCP, FID, CLS tracking
- **RBAC**: Role-based access control with resource-level permissions
- **Multi-tenancy**: Organization-based data isolation
- **Bilingual**: Chinese/English interface support

---

## Documentation

See `docs/` for detailed guides:
- `docs/guides/environment-setup.md` - Environment configuration
- `docs/guides/database.md` - Database setup and migrations
- `docs/guides/frontend.md` - React development guide
- `docs/guides/backend.md` - FastAPI development guide
- `docs/guides/deployment.md` - Docker deployment
- `docs/integrations/api-overview.md` - API architecture
- `docs/integrations/auth-api.md` - Authentication endpoints

---

## Common Issues

### Frontend
- **Port 5173 in use**: Change port in `vite.config.ts`
- **API request failures**: Check backend is running on port 8002
- **TypeScript errors**: Run `npm run type-check` to see full report

### Backend
- **Database connection fails**: Ensure `database/data/` directory exists
- **Import errors**: Run `pip install -e .` in backend directory
- **Alembic migration fails**: Run `alembic stamp head` then `alembic upgrade head`

---

## Git Workflow

- **main**: Production branch
- **develop**: Integration branch
- **feature/***: Feature branches
- **hotfix/***: Critical fixes

**Commit format**: `type(scope): description` (e.g., `feat(auth): add JWT refresh`)
