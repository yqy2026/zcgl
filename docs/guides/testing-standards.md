# Testing Standards
# Land Property Asset Management System

**Version**: 2.0
**Date**: 2026-01-15
**Status**: Active

---

## Table of Contents

1. [Overview](#overview)
2. [Test File Naming Conventions](#test-file-naming-conventions)
3. [Test Directory Structure](#test-directory-structure)
4. [Backend Testing Standards (pytest)](#backend-testing-standards-pytest)
5. [Frontend Testing Standards (Vitest/React Testing Library)](#frontend-testing-standards-vitestreact-testing-library)
6. [Coverage Targets](#coverage-targets)
7. [Test Execution Standards](#test-execution-standards)
8. [CI/CD Integration](#cicd-integration)

---

## Overview

This document defines the testing standards and best practices for the Land Property Asset Management System (土地物业资产管理系统). All team members must follow these guidelines when writing, organizing, and maintaining tests.

### Goals

- **Comprehensive Coverage**: Ensure all critical business logic is tested
- **Clear Organization**: Tests organized by type and purpose
- **Maintainability**: Tests that are easy to understand and modify
- **Fast Feedback**: Tests that run quickly and provide clear results

---

## Test File Naming Conventions

### Backend (Python/pytest)

| Test Type | Naming Pattern | Example | Location |
|-----------|---------------|---------|----------|
| Unit Tests | `test_<module>_<component>.py` | `test_asset_model.py` | `tests/unit/models/` |
| Integration Tests | `test_<module>_api.py` | `test_asset_api.py` | `tests/integration/api/` |
| E2E Tests | `test_<workflow>_lifecycle.py` | `test_asset_lifecycle.py` | `tests/e2e/` |
| Security Tests | `test_<security_feature>.py` | `test_rbac_core.py` | `tests/security/` |
| Performance Tests | `test_<component>_performance.py` | `test_api_performance.py` | `tests/performance/` |

### Frontend (Vitest/React)

| Test Type | Naming Pattern | Example | Location |
|-----------|---------------|---------|----------|
| Component Tests | `<Component>.test.tsx` | `AssetForm.test.tsx` | `<component-dir>/__tests__/` |
| Hook Tests | `use<hook-name>.test.ts` | `useAssets.test.ts` | `hooks/__tests__/` |
| Service Tests | `<service-name>.test.ts` | `assetService.test.ts` | `services/__tests__/` |
| Utils Tests | `<util-name>.test.ts` | `dataConversion.test.ts` | `utils/__tests__/` |
| Page Tests | `<PageName>.test.tsx` | `AssetListPage.test.tsx` | `pages/__tests__/` |

---

## Test Directory Structure

### Backend Structure

```
backend/tests/
├── conftest.py                      # Enhanced fixtures (keep existing)
├── conftest_performance.py          # Performance fixtures (keep existing)
│
├── unit/                            # Unit Tests - Fast, isolated
│   ├── models/                      # Model layer tests
│   │   ├── test_asset_model.py      # Asset model validation
│   │   ├── test_rent_contract_model.py
│   │   └── test_user_model.py
│   │
│   ├── services/                    # Service layer tests
│   │   ├── permission/
│   │   │   └── test_rbac_service.py # RBAC service tests
│   │   ├── document/
│   │   │   ├── test_pdf_import_service.py
│   │   │   └── test_pdf_processing_service.py
│   │   └── test_analytics_service.py
│   │
│   ├── crud/                        # CRUD layer tests
│   │   ├── test_asset_crud.py
│   │   └── test_rent_contract_crud.py
│   │
│   └── utils/                       # Utility tests
│       ├── test_validation.py
│       └── test_enums.py
│
├── integration/                     # Integration Tests - Module collaboration
│   ├── api/                         # API endpoint tests
│   │   ├── test_asset_api.py
│   │   ├── test_rent_api.py
│   │   └── test_auth_api.py
│   │
│   ├── database/                    # Database integration tests
│   │   ├── test_asset_repository.py
│   │   └── test_database_migrations.py
│   │
│   └── pdf/                         # PDF processing integration
│       └── test_pdf_workflow.py
│
├── e2e/                             # End-to-End Tests - Complete workflows
│   ├── test_asset_lifecycle.py      # Create → Read → Update → Delete
│   ├── test_contract_workflow.py    # Upload → Process → Approve
│   └── test_user_permissions.py     # Login → Access → Logout
│
├── security/                        # Security Tests - Critical
│   ├── test_rbac_core.py
│   ├── test_rbac_critical_security.py
│   └── test_authentication.py
│
├── performance/                     # Performance Tests - Separate, slower
│   ├── test_api_performance.py
│   └── test_pdf_performance.py
```

### Frontend Structure

```
frontend/src/
├── __tests__/                      # Root test configuration
│   ├── setup.ts                    # Global test setup
│   └── test-utils.tsx              # Custom test utilities
│
├── components/
│   ├── Asset/
│   │   └── __tests__/
│   │       ├── AssetForm.test.tsx
│   │       ├── AssetList.test.tsx
│   │       └── AssetCard.test.tsx
│   │
│   ├── Forms/                      # Unified form tests
│   │   └── __tests__/
│   │       ├── AssetForm.test.tsx
│   │       ├── OwnershipForm.test.tsx
│   │       └── RentContractForm.test.tsx
│   │
│   └── Router/
│       └── __tests__/
│           ├── DynamicRouteLoader.test.tsx
│           └── RouteBuilder.test.tsx
│
├── services/
│   └── __tests__/
│       ├── apiClient.test.ts
│       └── assetService.test.ts
│
├── hooks/
│   └── __tests__/
│       ├── useAssets.test.ts
│       └── useAuth.test.ts
│
├── pages/
│   └── __tests__/
│       ├── AssetListPage.test.tsx
│       └── DashboardPage.test.tsx
│
└── utils/
    └── __tests__/
        └── dataConversion.test.ts
```

---

## Backend Testing Standards (pytest)

### Test Structure Template

```python
"""
Asset CRUD operations tests
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.asset import Asset
from src.schemas.asset import AssetCreate
from src.crud.asset import asset_crud


class TestAssetCRUD:
    """Test Asset CRUD operations"""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_create_asset_success(self, db_session: AsyncSession) -> None:
        """Test successful asset creation with valid data"""
        # Arrange
        asset_data = AssetCreate(
            ownership_id="ownership-001",
            property_name="测试物业",
            address="测试地址123号",
            actual_property_area=1000.0,
            ownership_status="已确权",
        )

        # Act
        result = await asset_crud.create_async(db_session, obj_in=asset_data)

        # Assert
        assert result is not None
        assert result.ownership_id == "ownership-001"
        assert result.property_name == "测试物业"
        assert result.id is not None

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_create_asset_duplicate_fails(self, db_session: AsyncSession) -> None:
        """Test that duplicate assets are rejected"""
        # Arrange
        asset_data = AssetCreate(
            ownership_id="ownership-001",
            property_name="唯一物业",
            address="测试地址",
        )

        # Act - Create first asset
        await asset_crud.create_async(db_session, obj_in=asset_data)

        # Assert - Attempting to create duplicate should raise error
        with pytest.raises(ValueError, match="already exists"):
            await asset_crud.create_async(db_session, obj_in=asset_data)

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_get_asset_by_id_from_db(self, db_session: AsyncSession) -> None:
        """Test retrieving asset from database by ID"""
        # Arrange
        asset_data = AssetCreate(
            ownership_id="ownership-001",
            property_name="测试物业",
            address="测试地址",
        )
        created = await asset_crud.create_async(db_session, obj_in=asset_data)

        # Act
        retrieved = await asset_crud.get_async(db_session, created.id)

        # Assert
        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.property_name == "测试物业"
```

### Fixture Usage

```python
# conftest.py
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from src.models.asset import Asset
from src.factories.asset_factory import AssetFactory


@pytest.fixture(scope="function")
async def db_session() -> AsyncSession:
    """Real database session for integration tests (async)"""
    from src.database import get_async_db
    async for session in get_async_db():
        yield session
        await session.rollback()


@pytest.fixture(scope="function")
async def authenticated_client(db_session: AsyncSession):
    """API client with authentication cookies"""
    from httpx import ASGITransport, AsyncClient
    from src.main import app

    # 创建测试用户并通过 /auth/login 获取 cookie
    auth_cookies = await create_test_user_and_get_auth_cookies(db_session)

    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://127.0.0.1",
        cookies=auth_cookies,
    ) as client:
        yield client


@pytest.fixture(scope="session")
def sample_asset_data():
    """Sample asset data for testing"""
    return {
        "ownership_id": "ownership-001",
        "management_entity": "测试管理人",
        "property_name": "测试物业",
        "address": "测试地址123号",
        "actual_property_area": 1000.0,
        "rentable_area": 800.0,
        "ownership_status": "已确权",
    }
```

### Test Markers

```python
# Run specific test types
pytest -m unit                    # Only unit tests
pytest -m integration             # Only integration tests
pytest -m slow                    # Only slow tests
pytest -m "not slow"              # Exclude slow tests

# Combined markers
pytest -m "integration and database"  # Integration tests that use database
pytest -m "unit and not slow"         # Fast unit tests only
```

### Async Tests

```python
import pytest


@pytest.mark.asyncio
async def test_async_pdf_processing():
    """Test async PDF processing"""
    from src.services.document.pdf_processing_service import PDFProcessingService

    service = PDFProcessingService()
    result = await service.process_pdf_async("test.pdf")

    assert result.status == "completed"
    assert result.extracted_text is not None
```

---

## Frontend Testing Standards (Vitest/React Testing Library)

### Component Test Template

```typescript
/**
 * AssetForm component tests
 */

import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { AssetForm } from './AssetForm'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { describe, it, expect, vi, beforeEach } from 'vitest'

// Mock dependencies
vi.mock('@/api/client', () => ({
  apiClient: {
    post: vi.fn(),
  },
}))

const mockOnSubmit = vi.fn()

const renderWithQueryClient = (component: React.ReactElement) => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  })

  return render(
    <QueryClientProvider client={queryClient}>
      {component}
    </QueryClientProvider>
  )
}

describe('AssetForm', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders all required fields correctly', () => {
    renderWithQueryClient(
      <AssetForm mode="create" onSubmit={mockOnSubmit} />
    )

    expect(screen.getByLabelText(/权属单位/)).toBeInTheDocument()
    expect(screen.getByLabelText(/物业名称/)).toBeInTheDocument()
    expect(screen.getByLabelText(/地址/)).toBeInTheDocument()
  })

  it('submits form with valid data', async () => {
    const user = userEvent.setup()

    renderWithQueryClient(
      <AssetForm mode="create" onSubmit={mockOnSubmit} />
    )

    // Fill in form fields
    await user.type(screen.getByLabelText(/权属单位/), 'ownership-001')
    await user.type(screen.getByLabelText(/物业名称/), '测试物业')
    await user.type(screen.getByLabelText(/地址/), '测试地址123号')
    await user.type(screen.getByLabelText(/建筑面积/), '1000')

    // Submit form
    await user.click(screen.getByRole('button', { name: /提交/ }))

    // Verify submission
    await waitFor(() => {
      expect(mockOnSubmit).toHaveBeenCalledWith(
        expect.objectContaining({
          ownership_id: 'ownership-001',
          property_name: '测试物业',
          address: '测试地址123号',
          actual_property_area: 1000,
        })
      )
    })
  })

  it('shows validation errors for required fields', async () => {
    const user = userEvent.setup()

    renderWithQueryClient(
      <AssetForm mode="create" onSubmit={mockOnSubmit} />
    )

    // Submit without filling required fields
    await user.click(screen.getByRole('button', { name: /提交/ }))

    // Verify error messages
    await waitFor(() => {
      expect(screen.getByText(/权属单位是必填项/)).toBeInTheDocument()
      expect(screen.getByText(/物业名称是必填项/)).toBeInTheDocument()
    })

    // Verify form was not submitted
    expect(mockOnSubmit).not.toHaveBeenCalled()
  })

  it('displays loading state during submission', async () => {
    const user = userEvent.setup()
    mockOnSubmit.mockImplementation(() => new Promise(resolve => setTimeout(resolve, 1000)))

    renderWithQueryClient(
      <AssetForm mode="create" onSubmit={mockOnSubmit} />
    )

    // Fill and submit
    await user.type(screen.getByLabelText(/权属单位/), 'ownership-001')
    await user.click(screen.getByRole('button', { name: /提交/ }))

    // Verify loading state
    expect(screen.getByRole('button', { name: /提交中/ })).toBeDisabled()
  })
})
```

### Hook Test Template

```typescript
/**
 * useAssets hook tests
 */

import { renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useAssets } from './useAssets'
import { describe, it, expect, vi } from 'vitest'

const wrapper = ({ children }: { children: React.ReactNode }) => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  })
  return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
}

describe('useAssets', () => {
  it('fetches assets successfully', async () => {
    const { result } = renderHook(() => useAssets(), { wrapper })

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false)
    })

    expect(result.current.data).toBeDefined()
    expect(result.current.data.length).toBeGreaterThan(0)
  })

  it('handles error state correctly', async () => {
    // Mock error response
    vi.mock('@/api/client', () => ({
      apiClient: {
        get: vi.fn().mockRejectedValue(new Error('API Error')),
      },
    }))

    const { result } = renderHook(() => useAssets(), { wrapper })

    await waitFor(() => {
      expect(result.current.isError).toBe(true)
    })

    expect(result.current.error).toBeDefined()
  })
})
```

### Service Test Template

```typescript
/**
 * Asset service tests
 */

import { apiClient } from '@/api/client'
import { assetService } from './assetService'
import { describe, it, expect, vi, beforeEach } from 'vitest'

// Mock the API client
vi.mock('@/api/client', () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  },
}))

describe('assetService', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('getAssets', () => {
    it('fetches assets with default parameters', async () => {
      const mockAssets = [
        { id: '1', property_name: '测试物业1' },
        { id: '2', property_name: '测试物业2' },
      ]
      vi.mocked(apiClient.get).mockResolvedValue({ data: mockAssets })

      const result = await assetService.getAssets()

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/assets', {
        params: { page: 1, pageSize: 20 },
      })
      expect(result).toEqual(mockAssets)
    })

    it('handles API errors gracefully', async () => {
      vi.mocked(apiClient.get).mockRejectedValue(new Error('Network Error'))

      await expect(assetService.getAssets()).rejects.toThrow('Network Error')
    })
  })

  describe('createAsset', () => {
    it('creates a new asset successfully', async () => {
      const newAsset = {
        ownership_id: 'ownership-001',
        property_name: '新物业',
        address: '测试地址',
      }
      const createdAsset = { id: '123', ...newAsset }
      vi.mocked(apiClient.post).mockResolvedValue({ data: createdAsset })

      const result = await assetService.createAsset(newAsset)

      expect(apiClient.post).toHaveBeenCalledWith(
        '/api/v1/assets',
        newAsset
      )
      expect(result).toEqual(createdAsset)
    })
  })
})
```

---

## Coverage Targets

### Current CI Gates (Baseline)

#### Backend (pytest)

| Category | Minimum | Notes |
|----------|---------|-------|
| **Overall** | 70% | Enforced by `--cov-fail-under=70` |

#### Frontend (Vitest)

| Category | Minimum | Notes |
|----------|---------|-------|
| **Lines / Functions / Statements** | 50% | Enforced by Vitest thresholds |
| **Branches** | 45% | Enforced by Vitest thresholds |

### Target Coverage (Roadmap)

#### Backend Coverage Goals

| Category | Target | Notes |
|----------|--------|-------|
| **Overall** | 85% | Project-wide coverage |
| **Unit Tests** | 95% | Isolated functions and classes |
| **Integration Tests** | 80% | API and database integration |
| **Critical Paths** | 95%+ | Authentication, authorization, payment processing |
| **Utility Functions** | 90% | Helper functions and validators |

#### Frontend Coverage Goals

| Category | Target | Notes |
|----------|--------|-------|
| **Overall** | 75% | Project-wide coverage |
| **Components** | 80% | UI components |
| **Hooks** | 85% | Custom React hooks |
| **Services** | 80% | API service layer |
| **Utils** | 90% | Helper functions |
| **Critical Paths** | 90%+ | Authentication, asset creation, form validation |

---

## Test Execution Standards

### Backend Test Execution

```bash
# Run all tests
cd backend
pytest

# Run with coverage(auto-generated xml/html)
pytest --cov=src

# Run specific test types
pytest -m unit                    # Fast unit tests only
pytest -m integration             # Integration tests
pytest -m e2e                     # End-to-end workflow tests
pytest -m "not slow"              # Exclude slow tests

# Run specific file
pytest tests/unit/models/test_asset_model.py
pytest tests/e2e/test_auth_flow_e2e.py -m e2e

# Run with verbose output
pytest -v --tb=short

# Run failed tests only
pytest --lf

# Recommended E2E command (disable coverage gate for workflow tests)
pytest tests/e2e -m e2e --no-cov
```

### Frontend Test Execution

```bash
# Run all tests
cd frontend
pnpm test

# Run Playwright E2E tests
pnpm e2e

# Run E2E in CI mode
pnpm e2e:ci

# Show Playwright HTML report
pnpm e2e:report

# Run with coverage
pnpm test:coverage

# Run in watch mode
pnpm test:watch

# Run specific test file
pnpm test AssetForm.test.tsx

# Run tests matching pattern
pnpm test -t "AssetForm"

# Run tests for specific directory
pnpm test components/Asset

# Update snapshots
pnpm test -u
```

### Test Execution Time Targets

| Test Type | Maximum Time | Notes |
|-----------|--------------|-------|
| Unit Tests | < 1 minute | Fast, isolated tests |
| Integration Tests | < 5 minutes | Database/API integration |
| E2E Tests | < 15 minutes | Playwright + backend workflow checks |
| Full Suite | < 20 minutes | All tests combined |

---

## CI/CD Integration

### Backend CI Pipeline

```yaml
name: Backend Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        test-type: [unit, integration, security]
        python-version: ['3.12']

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
          cache: 'pip'

      - name: Install dependencies
        run: |
          pip install -e ".[dev]"

      - name: Run ${{ matrix.test-type }} tests
        run: |
          pytest -m ${{ matrix.test-type }} --cov=src --cov-report=xml

      - name: Upload coverage
        uses: codecov/codecov-action@v4
```

### Frontend CI Pipeline

```yaml
name: Frontend Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - name: Install pnpm
        uses: pnpm/action-setup@v3
        with:
          version: 9

      - name: Set up Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'pnpm'
          cache-dependency-path: frontend/pnpm-lock.yaml

      - name: Install dependencies
        run: cd frontend && pnpm install --frozen-lockfile

      - name: Run tests
        run: cd frontend && pnpm test:ci

      - name: Type check (tsgo)
        run: cd frontend && pnpm type-check

      - name: Lint (oxlint)
        run: cd frontend && pnpm lint
```

### E2E CI Pipeline (Blocking)

```yaml
jobs:
  backend-e2e:
    runs-on: ubuntu-latest
    steps:
      - run: cd backend && pytest tests/e2e -m e2e --no-cov

  frontend-e2e:
    runs-on: ubuntu-latest
    steps:
      - run: cd frontend && pnpm e2e:ci
```

**Notes**
- E2E jobs are configured as **blocking gates** for pull requests.
- Frontend E2E uses Playwright `tests/e2e` with role-specific `storageState`.
- Backend E2E requires PostgreSQL and should run with `E2E_TEST_DATABASE_URL`.

---

## Best Practices

### DO's ✅

1. **Write descriptive test names** that clearly state what is being tested
2. **Follow Arrange-Act-Assert pattern** for clear test structure
3. **Use fixtures** for common test data and setup
4. **Test behavior, not implementation** - focus on what the code does, not how
5. **Keep tests independent** - each test should be able to run in isolation
6. **Mock external dependencies** - databases, APIs, file systems
7. **Use appropriate assertions** - most specific to least specific
8. **Clean up resources** - use `finally` blocks or fixture teardown
9. **Use `vi.mock` for Vitest** mocking standard

### DON'Ts ❌

1. **Don't test third-party libraries** - trust that they work
2. **Don't write tests that depend on execution order**
3. **Don't use random data in tests** - use deterministic fixtures or seeded random
4. **Don't ignore test failures** - fix them immediately
5. **Don't test trivial code** - getters/setters, simple pass-through functions
6. **Don't hardcode values** that should come from configuration
7. **Don't catch all exceptions** - catch only expected exceptions
8. **Don't sleep in tests** - use proper async/await or mocks

---

**Document Owner**: Development Team
**Last Updated**: 2026-01-15
**Next Review**: 2026-07-15
