# GEMINI.md

This file provides project context for Gemini, following 2026 best practices. For detailed documentation, please refer to the `docs/` directory.

**Last Updated**: 2026-02-18

---

## Project Overview

**Real Estate Asset Management & Operations System** - A full-stack asset management platform supporting RBAC permission management, contract lifecycle management, and intelligent document extraction with multi-provider LLM integration.

### Core Features
- **Asset Management**: 58-field comprehensive asset tracking.
- **Contract Management**: PDF parsing & data extraction.
- **RBAC**: Fine-grained permission control.
- **Document AI**: Intelligent extraction using GLM-4V/Qwen-VL.
- **Analytics**: Visualized dashboards and reports.

| Layer | Tech Stack |
|---|-------|
| **Frontend** | React 19.2 + TypeScript 5.9 + Vite 6 + Ant Design 6 + pnpm |
| **Backend** | FastAPI 0.104+ + Python 3.12 + SQLAlchemy 2.0 + Pydantic v2 |
| **Database** | PostgreSQL 18.2+ (Prod/Dev/Test) |
| **Cache** | Redis 8.6+ |
| **LLM** | GLM-4V, Qwen-VL-Max, DeepSeek-VL, Hunyuan-Vision |

**Project Scale**: 774 Python files | 597 TypeScript files | 22 DB models | 70% test coverage

---

## Quick Commands

```bash
# Development
cd frontend && pnpm dev          # Frontend :5173
cd backend && python run_dev.py  # Backend :8002 (or :8003 if occupied)

# Robust Dev (Monitored)
pwsh -File scripts/dev_watch.ps1

# Testing
cd frontend && pnpm test
cd backend && pytest -m unit     # Unit tests
cd backend && pytest -m "not slow" # Fast tests

# Code Quality
cd frontend && pnpm lint && pnpm type-check
cd backend && ruff check . && mypy src

# Database Migrations
cd backend && alembic upgrade head
```

---

## Core Architecture

### Backend Layered Architecture

```
Request → api/v1/ → services/ → crud/ → models/ → PostgreSQL
              ↑           ↑
         Business Logic  Data Access
```

**Key Rules**:
- **Services Layer**: Business logic **MUST** reside here, NOT in API endpoints.
- **CRUD Layer**: Pure data access; do not bypass CRUD to access DB.
- **API Registration**: Use `route_registry.register_router()` for new APIs.
- **PII Encryption**: Use `SensitiveDataHandler` for fields like Phone/ID Card.

### Frontend State Management

| State Type | Library | Purpose |
|---|---|---|
| **Global UI** | Zustand | Theme, Sidebar, User Preferences (`useAppStore`) |
| **Asset UI** | Zustand | Selection, Filters, View Modes (`useAssetStore`) |
| **Server Data** | React Query | API Caching, Synchronization |
| **Forms** | React Hook Form | Validation, Submission |
| **Auth** | Context | User Session (`AuthContext`) |

---

## Directory Navigation

### Backend Structure (`backend/src/`)

```
src/
├── api/v1/            # API Endpoints (Versioned)
├── services/          # Business Logic (Core Rules)
├── crud/              # Data Access Layer
├── models/            # SQLAlchemy ORM Models
├── schemas/           # Pydantic Schemas
├── core/              # Config, Security, Events
├── security/          # Auth, Encryption (JWT/AES)
├── monitor/           # Performance & Resource Monitoring
└── utils/             # Utility Functions
```

### Frontend Structure (`frontend/src/`)

```
src/
├── api/               # API Client & Endpoints
├── components/        # Reusable Components
│   ├── Forms/         # Standardized Forms
│   ├── Asset/         # Asset Domain Components
│   └── Analytics/     # Charts & Dashboards
├── pages/             # Route Pages
├── hooks/             # Custom Hooks
├── store/             # Zustand Stores
├── types/             # TypeScript Definitions
└── utils/             # Helper Functions
```

---

## Development Guidelines

### Backend Development

1.  **Pydantic v2**:
    *   Use `model_validate()` / `model_dump()`.
    *   Config: `model_config = ConfigDict(from_attributes=True)`.

2.  **SQLAlchemy 2.0**:
    *   Prefer ORM + QueryBuilder.
    *   Use `selectinload` for collections to avoid N+1 issues.

3.  **Security (Critical)**:
    *   **Encryption**: `SensitiveDataHandler` enforces AES-256 for PII.
    *   **Keys**: `DATA_ENCRYPTION_KEY` is required. Missing key = plaintext fallback (Warn).

4.  **New Feature Flow**:
    *   Schema (`schemas/`) -> Model (`models/`) -> CRUD (`crud/`) -> Service (`services/`) -> API (`api/v1/`).

### Frontend Development

1.  **Strict Boolean Expressions**:
    *   Avoid implicit casting. Use explicit checks.
    *   ✅ `if (val !== null)` | ❌ `if (val)`
    *   ✅ `if (arr?.length > 0)` | ❌ `if (arr.length)`
    *   ✅ `value ?? default` | ❌ `value || default`

2.  **Imports**:
    *   Use `@/` alias (e.g., `import { X } from '@/components'`).
    *   Avoid relative paths like `../../../`.

3.  **API Data**:
    *   Use **React Query** for all server state.
    *   Do NOT use `useState` + `useEffect` for fetching data.

---

## Environment Configuration

### Files & Setup

| File | Purpose | Action |
|---|---|---|
| `backend/.env` | Runtime Config | Copy from `.env.example`, set `SECRET_KEY` |
| `frontend/.env` | Build Config | Copy from `.env.example` |

### Key Variables

**Backend**:
```bash
SECRET_KEY="<32+ chars random string>"      # REQUIRED
DATA_ENCRYPTION_KEY="<base64 key>"          # Generate via module
DATABASE_URL="postgresql+psycopg://..."     # PostgreSQL required
LLM_PROVIDER="hunyuan"                      # AI Provider
```

**Generate Keys**:
```bash
# Secret Key
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Encryption Key
cd backend && python -m src.core.encryption
```

---

## Troubleshooting

| Issue | Solution |
|---|---|
| **Backend Import Error** | `cd backend && pip install -e .` |
| **DB Migration Fail** | `alembic stamp head && alembic upgrade head` |
| **Frontend Port Busy** | Check `vite.config.ts` or kill process on :5173 |
| **Search Encrypted Data** | Ensure Deterministic Encryption is enabled in Handler |
| **Test Memory High** | Use `pytest --no-cov` or run single file |
| **CORS Error** | Check backend `CORS_ORIGINS` in `.env` |

---

## Git Workflow

*   **Branches**: `main` (Prod) ← `develop` (Dev) ← `feature/*`
*   **Commits**: `type(scope): description` (e.g., `feat(asset): add valuation field`)
*   **Conflict Resolution**:
    *   Do NOT blindly use "Accept Theirs/Ours".
    *   Manually verify `models/` and `crud/` for lost changes.
    *   Run tests after merge: `pytest -m unit`.

---

## ⚠️ Critical Warnings

> [!DANGER]
> **Production Security**:
> *   `SECRET_KEY` must be strong & random.
> *   Never commit `.env` files.
> *   Change default DB passwords.

> [!WARNING]
> **Data Integrity**:
> *   Always run migrations (`alembic upgrade head`) after pulling.
> *   Verify RBAC permissions if API returns 403 unexpectedly (`init_rbac_data.py`).
