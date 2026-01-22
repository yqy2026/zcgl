# GEMINI.md

This file provides project context for Gemini, following 2026 best practices. For detailed documentation, please refer to the `docs/` directory.

**Last Updated**: 2026-01-22

---

## Project Overview

**Land Property Asset Management System** - A full-stack asset management platform supporting RBAC permission management, contract lifecycle management, and intelligent document extraction with multi-provider LLM integration.

| Layer | Tech Stack |
|---|-------|
| **Frontend** | React 19 + TypeScript + Vite 6 + Ant Design 6 + pnpm |
| **Backend** | FastAPI + Python 3.12 + SQLAlchemy 2.0 + Pydantic v2 |
| **Database** | SQLite (dev) / PostgreSQL (prod) |
| **Cache** | Redis |
| **LLM** | GLM-4V, Qwen-VL-Max, DeepSeek-VL, Hunyuan-Vision |

**Project Scale**: 274 Python files | 374 TypeScript files | 17 DB models | 70% test coverage

---

## Quick Commands

```bash
# Development
cd frontend && pnpm dev          # Frontend :5173
cd backend && python run_dev.py  # Backend :8002

# Testing
cd frontend && pnpm test
cd backend && pytest -m unit     # Optional: integration, api, e2e

# Code Quality
cd frontend && pnpm lint && pnpm type-check
cd backend && ruff check . && mypy src

# Database Migrations
cd backend && alembic upgrade head
```

---

## Core Architecture

```
React UI → EnhancedApiClient → FastAPI (/api/v1/*) → Service → CRUD → SQLAlchemy
```

**Key Rules**:
- Business logic **MUST** reflect in the `services/` layer, NOT in `api/v1/` endpoints.
- Register new APIs using `route_registry.register_router()`.
- Frontend imports: use `@/api/client` and `@/components/Forms`.

---

## Directory Navigation

> Progressive Disclosure: View specific directories only when needed.

| Requirement | Location |
|-----|---------|
| API Endpoints | `backend/src/api/v1/` |
| Business Logic | `backend/src/services/` |
| DB Models | `backend/src/models/` |
| UI Components | `frontend/src/components/` |
| Pages/Routes | `frontend/src/pages/` |
| Types | `frontend/src/types/` |

---

## ⚠️ Critical Warnings

> [!WARNING]
> **JWT Secret**: Must be 32+ characters in production.

> [!WARNING]
> **Alembic Failures**: Run `alembic stamp head` then `alembic upgrade head` if migrations fail.

---

## Development Cheat Sheet

### Adding New API Endpoints

```python
# backend/src/api/v1/my_feature.py
from src.core.router_registry import route_registry

router = APIRouter(prefix="/my-feature", tags=["My Feature"])

@router.get("/items")
async def get_items(): ...

route_registry.register_router(router, prefix="/api/v1", tags=["My Feature"], version="v1")
```

### Service Layer Pattern

```python
# ✅ CORRECT - Logic in Service
class AssetService:
    def process(self, data): ...

# ❌ WRONG - Logic in API
@router.post("/process")
async def process(data):
    # Do NOT put business logic here!
```

### Frontend State Management

| State Type | Library |
|---------|------|
| Global UI | Zustand (`store/`) |
| Server Data | React Query |
| Forms | React Hook Form |

---

## Environment Configuration

### 📁 Configuration Files

| File | Purpose | Example |
|------|---------|---------|
| `backend/.env` | Backend environment variables | `backend/.env.example` |
| `frontend/.env` | Frontend environment variables | `frontend/.env.example` |

### 🚀 First-Time Setup

```bash
# 1. Backend - Copy and configure
cp backend/.env.example backend/.env
# Edit backend/.env and set SECRET_KEY (32+ characters required)

# 2. Frontend - Copy and configure (optional, uses defaults)
cp frontend/.env.example frontend/.env
# Edit if needed, defaults work for local development

# 3. Generate secure SECRET_KEY
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### ⚙️ Key Configuration Variables

**Backend (`backend/.env`)**:
```bash
# Essential
SECRET_KEY=<32+_character_random_string>  # REQUIRED
DATABASE_URL=sqlite:///./database/data/land_property.db

# LLM Provider (choose one)
LLM_PROVIDER="glm-4v"                    # or "qwen-vl-max", "deepseek-vl"
ZHIPU_API_KEY="your-api-key"             # for GLM-4V

# Environment
ENVIRONMENT=development                   # production, testing, staging
DEBUG=true                               # false in production
```

**Frontend (`frontend/.env`)**:
```bash
VITE_API_BASE_URL=http://127.0.0.1:8002/api/v1
VITE_APP_TITLE=经营性资产管理系统
```

> [!WARNING]
> **Production**: Set `SECRET_KEY` to a strong random value. Never commit `.env` files to git.

See `backend/src/core/environment.py` for environment detection logic.

---

## Git Workflow

- **Branches**: main (prod) ← develop ← feature/* / hotfix/*
- **Commit Format**: `type(scope): description` (e.g., `feat(auth): add JWT refresh`)
