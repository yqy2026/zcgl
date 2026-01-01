# Contributing Guidelines

Thank you for your interest in contributing to the 土地物业资产管理系统 (Land Property Asset Management System)!

This document provides guidelines and standards for contributing to the project.

---

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Workflow](#development-workflow)
- [File Naming Conventions](#file-naming-conventions)
- [Code Style Guidelines](#code-style-guidelines)
- [Commit Message Format](#commit-message-format)
- [Pull Request Process](#pull-request-process)
- [Testing Requirements](#testing-requirements)

---

## Code of Conduct

- Be respectful and inclusive
- Provide constructive feedback
- Focus on what is best for the community
- Show empathy towards other community members

---

## Getting Started

### Prerequisites

- **Frontend**: Node.js 18+, npm or yarn
- **Backend**: Python 3.12+, pip
- **Database**: SQLite (dev) or PostgreSQL (prod)
- **Optional**: Docker, Redis

### Setup

1. Fork the repository
2. Clone your fork:
   ```bash
   git clone https://github.com/your-username/zcgl.git
   cd zcgl
   ```

3. Install dependencies:
   ```bash
   # Frontend
   cd frontend
   npm install

   # Backend
   cd ../backend
   pip install -e .
   ```

4. Configure environment (see `docs/guides/environment-setup.md`)

5. Run development servers:
   ```bash
   # Frontend (port 5173)
   npm run dev

   # Backend (port 8002)
   python run_dev.py
   ```

---

## Development Workflow

1. **Create a branch** from `develop`:
   ```bash
   git checkout develop
   git pull origin develop
   git checkout -b feature/your-feature-name
   ```

2. **Make changes** following the conventions in this document

3. **Test your changes**:
   ```bash
   # Frontend
   npm run lint
   npm run type-check
   npm test

   # Backend
   ruff check backend/
   ruff format backend/
   mypy backend/src
   pytest
   ```

4. **Commit your changes** using the [Commit Message Format](#commit-message-format)

5. **Push to your fork**:
   ```bash
   git push origin feature/your-feature-name
   ```

6. **Create a Pull Request** to `develop`

---

## File Naming Conventions

### Frontend (React + TypeScript)

#### Component Files
- **Pattern**: PascalCase
- **Format**: `{ComponentName}.tsx`
- **Examples**:
  - ✅ `AssetForm.tsx`, `AssetList.tsx`, `DashboardPage.tsx`
  - ✅ `ErrorBoundary.tsx`, `LoadingSpinner.tsx`, `ConfirmDialog.tsx`
  - ❌ `assetForm.tsx`, `asset_list.tsx`, `dashboard-page.tsx`

#### Test Files
- **Pattern**: Same name as source with `.test.` suffix
- **Location**: Co-located in `__tests__/` subdirectory
- **Format**: `{ComponentName}.test.tsx` or `{fileName}.test.ts`
- **Examples**:
  - ✅ `components/Asset/__tests__/AssetList.test.tsx`
  - ✅ `hooks/__tests__/useAuth.test.ts`
  - ❌ `AssetList.spec.tsx`, `AssetList.test.tsx` (not in `__tests__/`)

#### Service Files
- **Pattern**: camelCase
- **Format**: `{featureName}Service.ts` or `{description}.ts`
- **Examples**:
  - ✅ `authService.ts`, `assetService.ts`, `analyticsService.ts`
  - ✅ `cacheManager.ts`, `errorHandler.ts`, `responseExtractor.ts`
  - ❌ `auth_service.ts`, `AuthService.ts`

#### Custom Hook Files
- **Pattern**: camelCase with `use` prefix
- **Format**: `use{FeatureName}.ts`
- **Examples**:
  - ✅ `useAuth.ts`, `useAssets.ts`, `useAnalytics.ts`
  - ✅ `useErrorHandler.ts`, `useSearchHistory.ts`
  - ❌ `UseAuth.ts`, `useAuthHook.ts`, `auth.ts`

#### Store Files (Zustand)
- **Pattern**: camelCase with `use` prefix
- **Format**: `use{StoreName}.ts`
- **Examples**:
  - ✅ `useAppStore.ts`, `useAssetStore.ts`, `useAuthStore.ts`
  - ❌ `appStore.ts`, `appStore.ts` (without `use` prefix)

#### Page Files
- **Pattern**: PascalCase with `Page` suffix
- **Format**: `{FeatureName}Page.tsx`
- **Examples**:
  - ✅ `AssetListPage.tsx`, `DashboardPage.tsx`, `UserManagementPage.tsx`
  - ✅ `AssetDetailPage.tsx`, `ContractListPage.tsx`
  - ❌ `AssetList.tsx` (use Page suffix for pages), `asset-list-page.tsx`

#### Utility Files
- **Pattern**: camelCase
- **Format**: `{utilityName}.ts` or `{description}.ts`
- **Examples**:
  - ✅ `format.ts`, `validationRules.ts`, `dataConversion.ts`
  - ✅ `dateUtils.ts`, `numberUtils.ts`, `stringHelpers.ts`
  - ❌ `utils.ts` (too generic), `format_helper.ts`

#### API Files
- **Pattern**: camelCase
- **Format**: `{description}.ts`
- **Examples**:
  - ✅ `api/client.ts`, `api/config.ts`, `api/index.ts`
  - ✅ `services/asset.ts` (asset API service)
  - ❌ `assetApi.ts` (redundant "Api" suffix)

#### Type Definition Files
- **Pattern**: camelCase with `.d.ts` extension
- **Format**: `{name}.d.ts`
- **Examples**:
  - ✅ `global.d.ts`, `vite-env.d.ts`
  - ❌ `types.ts` (use `.d.ts` for declarations)

#### Configuration Files
- **Pattern**: kebab-case or dot-prefixed
- **Examples**:
  - ✅ `vite.config.ts`, `tsconfig.json`, `.eslintrc.cjs`
  - ✅ `tailwind.config.js`, `postcss.config.js`

### Backend (FastAPI + Python)

#### API Route Files
- **Pattern**: snake_case
- **Format**: `{resource_name}.py`
- **Examples**:
  - ✅ `assets.py`, `auth.py`, `rent_contract.py`
  - ✅ `organization.py`, `ownership.py`, `project.py`
  - ❌ `Assets.py`, `assets_routes.py`, `assetRoutes.py`

#### CRUD Files
- **Pattern**: snake_case
- **Format**: `{resource_name}.py` or `{resource}_crud.py`
- **Examples**:
  - ✅ `asset.py`, `auth.py`, `rent_contract.py`
  - ✅ `base.py` (base CRUD class)
  - ❌ `asset_crud.py` (redundant when in crud/ directory)

#### Model Files
- **Pattern**: snake_case
- **Format**: `{resource_name}.py`
- **Examples**:
  - ✅ `asset.py`, `auth.py`, `rent_contract.py`
  - ✅ `operation_log.py`, `pdf_import_session.py`
  - ❌ `Asset.py`, `AssetModel.py`

#### Schema Files
- **Pattern**: snake_case
- **Format**: `{resource_name}.py` or `{category}.py`
- **Examples**:
  - ✅ `asset.py`, `auth.py`, `common.py`
  - ✅ `excel.py`, `backup.py`, `statistics.py`
  - ❌ `AssetSchema.py`, `asset_schemas.py`

#### Service Files
- **Pattern**: snake_case with `_service.py` suffix
- **Format**: `{feature}_service.py` or `{description}.py`
- **Examples**:
  - ✅ `auth_service.py`, `caching_ocr_service.py`
  - ✅ `occupancy_calculator.py`, `asset_calculator.py`
  - ❌ `auth.py` (ambiguous - use _service suffix for services)

#### Middleware Files
- **Pattern**: snake_case
- **Format**: `{description}_middleware.py` or `{feature}.py`
- **Examples**:
  - ✅ `security_middleware.py`, `performance_monitoring.py`
  - ✅ `auth.py` (in middleware/ directory), `request_logging.py`
  - ❌ `SecurityMiddleware.py`, `authMiddleware.py`

#### Core Utility Files
- **Pattern**: snake_case
- **Format**: `{description}.py`
- **Examples**:
  - ✅ `config.py`, `security.py`, `dependency_injection.py`
  - ✅ `error_handler.py`, `router_registry.py`, `environment.py`
  - ❌ `Config.py`, `configUtils.py`

#### Test Files
- **Pattern**: snake_case with `_test.py` suffix or `test_*.py` prefix
- **Location**: Mirrors source structure in `tests/` directory
- **Format**: `{module_name}_test.py` or `test_{feature}.py`
- **Examples**:
  - ✅ `tests/unit/core/blacklist_test.py`
  - ✅ `tests/integration/services/test_auth_service.py`
  - ❌ `test_auth.py` (at root), `authTests.py`

#### Configuration Files
- **Pattern**: snake_case or UPPER_SNAKE_CASE
- **Examples**:
  - ✅ `settings.py`, `alembic.ini`, `pytest.ini`
  - ✅ `.env.example`, `.flake8`

### Directory Naming

#### Frontend Directories
- **Pattern**: PascalCase for features, camelCase for utilities
- **Examples**:
  - ✅ `components/Asset/`, `components/Contract/`, `components/Dashboard/`
  - ✅ `pages/`, `services/`, `hooks/`, `store/`, `utils/`
  - ❌ `components/asset/`, `components/contract/`

#### Backend Directories
- **Pattern**: snake_case
- **Examples**:
  - ✅ `api/v1/`, `crud/`, `models/`, `schemas/`, `services/`
  - ✅ `core/`, `middleware/`, `tests/unit/`
  - ❌ `Api/`, `Crud/`, `Models/`

### Index Files

#### Frontend
- **Pattern**: `index.ts` for clean exports
- **Usage**: Re-export from feature directories
- **Examples**:
  ```typescript
  // components/Forms/index.ts
  export { AssetForm } from './AssetForm';
  export { OwnershipForm } from './OwnershipForm';
  export { ProjectForm } from './ProjectForm';
  ```

#### Backend
- **Pattern**: `__init__.py` in all directories
- **Usage**: Expose public API of modules
- **Examples**:
  ```python
  # models/__init__.py
  from .asset import Asset
  from .auth import User, Role
  ```

### File Naming Best Practices

1. **Be Descriptive**: Use names that clearly describe the file's purpose
   - ✅ `occupancyRateChart.tsx`
   - ❌ `Chart.tsx`

2. **Avoid Redundancy**: Don't repeat directory name in filename
   - ✅ `services/auth.ts` (not `authService.ts`)
   - ✅ `components/Asset/AssetForm.tsx` (not `components/Asset/assetFormComponent.tsx`)

3. **Keep it Short**: Prefer shorter names when clear
   - ✅ `format.ts`
   - ❌ `stringFormattingUtilities.ts`

4. **Use Consistent Patterns**: Follow the established patterns in each codebase

5. **Group Related Files**: Use subdirectories for organization
   - ✅ `services/asset/assetCoreService.ts`, `services/asset/assetCalculations.ts`
   - ❌ `assetCoreService.ts`, `assetCalculations.ts` (in services/ root)

---

## Code Style Guidelines

### Frontend (TypeScript + React)

- **Line length**: 100 characters
- **Indentation**: 2 spaces
- **Quotes**: Single quotes
- **Semicolons**: Required
- **Components**: Functional components with hooks
- **Naming**:
  - Components: PascalCase (`AssetForm`)
  - Functions/Variables: camelCase (`getUserProfile`)
  - Constants: UPPER_SNAKE_CASE (`MAX_FILE_SIZE`)
  - Types/Interfaces: PascalCase (`UserProps`)

### Backend (Python)

- **Line length**: 88 characters (Black default)
- **Indentation**: 4 spaces
- **Quotes**: Double quotes
- **Naming**:
  - Functions/Variables: snake_case (`get_user_profile`)
  - Classes: PascalCase (`UserService`)
  - Constants: UPPER_SNAKE_CASE (`MAX_FILE_SIZE`)

For detailed style guides, see:
- `docs/guides/frontend.md`
- `docs/guides/backend.md`

---

## Commit Message Format

Follow the Conventional Commits specification:

```
type(scope): subject

body (optional)

footer (optional)
```

### Types

- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, no logic change)
- `refactor`: Code refactoring
- `perf`: Performance improvements
- `test`: Adding or updating tests
- `chore`: Maintenance tasks
- `ci`: CI/CD changes

### Examples

```bash
feat(auth): add JWT refresh token support

Implement automatic token refresh mechanism to improve
user experience and security.

Closes #123
```

```bash
fix(asset): correct calculation of occupancy rate

Fix division by zero error when calculating occupancy rate
for properties with zero total area.

Fixes #456
```

```bash
docs(contributing): add file naming conventions

Add comprehensive file naming guidelines for frontend
and backend code.
```

---

## Pull Request Process

1. **Update Documentation**: If your changes affect functionality, update relevant docs

2. **Ensure Tests Pass**:
   ```bash
   # Frontend
   npm test
   npm run lint

   # Backend
   pytest
   ruff check backend/
   ```

3. **Update Changelog**: Add an entry to `CHANGELOG.md` (if applicable)

4. **Create PR**:
   - Fill out the PR template
   - Link related issues
   - Request review from maintainers

5. **Address Feedback**: Respond to review comments and make necessary changes

6. **Approval & Merge**: Wait for approval before merging

### PR Title Format

Use the same format as commit messages:
```
feat(scope): brief description
fix(scope): brief description
```

---

## Testing Requirements

### Coverage Targets

- **Frontend**: 95%+ coverage
- **Backend**: 95%+ coverage

### Test Types

- **Unit Tests**: Test individual functions/components
- **Integration Tests**: Test module interactions
- **E2E Tests**: Test complete workflows
- **API Tests**: Test backend endpoints

### Running Tests

```bash
# Frontend
npm test                           # All tests
npm run test:coverage              # Coverage report
npm run test:ui                    # UI mode

# Backend
pytest                             # All tests
pytest -m unit                     # Unit tests only
pytest -m integration              # Integration tests only
pytest --cov=src --cov-report=html # Coverage report
```

For detailed testing guidelines, see `docs/TESTING_STANDARDS.md`

---

## Questions or Need Help?

- Check existing documentation in `docs/`
- Open an issue for bugs or feature requests
- Start a discussion for questions

---

**Thank you for contributing!** 🎉
