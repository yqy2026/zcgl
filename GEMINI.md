# GEMINI.md - Project Context & Instructions

## Project Overview

**Project Name:** 土地物业资产管理系统 (Land Property Asset Management System)
**Description:** A comprehensive full-stack web application designed for managing real estate assets, rental contracts, and property operations. It features bilingual support (Chinese/English), RBAC permission systems, and advanced features like PDF OCR for contract processing, Dynamic Enum Management, and Contract Life Cycle Management V2.
**Last Updated:** 2026-01-08

## Tech Stack

### Backend
*   **Language:** Python 3.12+
*   **Framework:** FastAPI
*   **Database:** SQLAlchemy 2.0 (ORM), SQLite (Dev), PostgreSQL (Prod)
*   **Validation:** Pydantic v2
*   **Task Queue/Cache:** Redis
*   **Specialized:** PaddleOCR (Chinese text recognition), PyMuPDF (PDF processing)
*   **Package Manager:** uv

### Frontend
*   **Language:** TypeScript
*   **Framework:** React 18
*   **Build Tool:** Vite
*   **UI Library:** Ant Design 5
*   **State Management:** Zustand (Global), React Query (Server), React Hook Form (Forms)
*   **Testing:** Vitest, React Testing Library
*   **Package Manager:** npm

### Infrastructure
*   **Containerization:** Docker, Docker Compose
*   **Reverse Proxy:** Nginx

## Directory Structure & Key Files

```
D:\code\zcgl\
├── backend/                # Python/FastAPI Backend
│   ├── src/
│   │   ├── api/v1/         # API Endpoints (37 endpoint files)
│   │   ├── core/           # Core config, security, router registry, environment
│   │   ├── crud/           # Database operations (18 files)
│   │   ├── models/         # SQLAlchemy ORM models (14 files)
│   │   ├── schemas/        # Pydantic models (18 files)
│   │   ├── services/       # Business logic (19 subdirectories)
│   │   ├── middleware/     # Auth, CORS, request processing
│   │   └── main.py         # Application entry point
│   ├── tests/              # Pytest suite
│   ├── alembic/            # Database migrations
│   ├── pyproject.toml      # Backend dependencies & tools config
│   └── uv.lock             # Dependency lock file
├── frontend/               # React/TypeScript Frontend
│   ├── src/
│   │   ├── api/            # API client & configuration
│   │   ├── components/     # Reusable UI components (114+ TSX files)
│   │   ├── pages/          # Application pages/routes (40 files)
│   │   ├── services/       # API services (35 files)
│   │   ├── hooks/          # Custom React hooks (13 files)
│   │   ├── store/          # Zustand stores
│   │   ├── types/          # TypeScript definitions (15 files)
│   │   └── utils/          # Utility functions (15 files)
│   ├── package.json        # Frontend dependencies & scripts
│   └── vite.config.ts      # Vite configuration
├── docs/                   # Comprehensive documentation
├── docker-compose.yml      # Service orchestration
├── CLAUDE.md               # AI assistant guide (Claude)
└── GEMINI.md               # AI assistant guide (Gemini)
```

## Setup & Development Commands

### Backend (`backend/`)

*   **Install Dependencies:** `uv sync` (use `uv sync --all-extras` for full dev environment)
*   **Add Dependency:** `uv add <package>` (or `uv add --group dev <package>` for dev dependencies)
*   **Start Dev Server:** `python run_dev.py` or `uvicorn src.main:app --reload --port 8002`
*   **Run Tests:** `pytest` (Supports markers: `-m unit`, `-m api`, etc.)
*   **Lint/Format:** `ruff check .`, `ruff format .`
*   **Type Check:** `mypy src`
*   **Database Migrations:** `alembic upgrade head`

### Frontend (`frontend/`)

*   **Install Dependencies:** `npm install`
*   **Start Dev Server:** `npm run dev` (Port 5173)
*   **Build:** `npm run build`
*   **Run Tests:** `npm test`
*   **Lint:** `npm run lint`

### Infrastructure (Root)

*   **Start All Services:** `docker-compose up -d`
*   **Stop All Services:** `docker-compose down`

## Development Conventions

1.  **API Versioning:** All endpoints must be registered under `/api/v1/*`. Use the `router_registry` in `backend/src/core/router_registry.py` for registering new routes.
2.  **Safe Imports:** The backend uses a custom `safe_import` mechanism in `backend/src/core/import_utils.py` to handle optional dependencies (like OCR libraries) gracefully. Adhere to this pattern for heavy dependencies.
3.  **Strict Typing:** Both backend (Mypy strict mode) and frontend (TypeScript) enforce strict typing. Ensure all functions have type hints and interfaces are defined.
4.  **Testing Standards:** Maintain high coverage (>95%). Use `pytest` markers for backend tests and `vitest` for frontend.
5.  **State Management:** Use `Zustand` for global client state and `React Query` for server data. Avoid prop drilling.
6.  **Environment:** Configuration is managed via `.env` files. Respect `backend/src/core/environment.py` logic for environment detection (Prod/Dev/Test).
