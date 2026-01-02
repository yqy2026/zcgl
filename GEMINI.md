# GEMINI.md - Project Context & Instructions

## Project Overview

**Project Name:** 土地物业资产管理系统 (Land Property Asset Management System)
**Description:** A comprehensive full-stack web application designed for managing real estate assets, rental contracts, and property operations. It features bilingual support (Chinese/English), RBAC permission systems, and advanced features like PDF OCR for contract processing.

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
D:\ccode\zcgl\
├── backend/                # Python/FastAPI Backend
│   ├── src/
│   │   ├── api/v1/         # API Endpoints (Versioned)
│   │   ├── core/           # Core config, security, router registry
│   │   ├── crud/           # Database operations
│   │   ├── models/         # SQLAlchemy ORM models
│   │   ├── schemas/        # Pydantic models
│   │   ├── services/       # Business logic (OCR, Assets, etc.)
│   │   └── main.py         # Application entry point
│   ├── tests/              # Pytest suite
│   ├── alembic/            # Database migrations
│   ├── pyproject.toml      # Backend dependencies & tools config
│   └── uv.lock             # Dependency lock file
├── frontend/               # React/TypeScript Frontend
│   ├── src/
│   │   ├── api/            # API client & configuration
│   │   ├── components/     # Reusable UI components
│   │   ├── pages/          # Application pages/routes
│   │   ├── store/          # Zustand stores
│   │   └── types/          # TypeScript definitions
│   ├── package.json        # Frontend dependencies & scripts
│   └── vite.config.ts      # Vite configuration
├── docs/                   # Comprehensive documentation
├── docker-compose.yml      # Service orchestration
└── CLAUDE.md               # Existing AI assistant guide (Reference)
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
