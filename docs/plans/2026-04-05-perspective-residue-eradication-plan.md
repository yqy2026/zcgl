# Perspective Residue Eradication Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Remove the remaining perspective-oriented naming, routes, fixtures, and docs that still conflict with the data-scope model, while only preserving explicitly approved protocol compatibility surfaces.

**Architecture:** Treat the cleanup as a layered rename plus residue sweep, not a single global search-and-replace. Request-level runtime state should move to `scope` terminology, owner/manager binding semantics should move to `binding` terminology, and only the explicitly preserved compatibility surfaces (`X-Perspective` request header and `capabilities[].perspectives` response field) may keep the old word. Each batch must follow TDD: add or update a failing regression first, run it red, implement the minimal rename/cleanup, then run the focused verification before moving on.

**Tech Stack:** FastAPI, Pydantic v2, SQLAlchemy 2.0, React 19, TypeScript 5, React Query, Vitest, pytest, Ruff, Oxlint, docs-lint

---

## 0. Scope Boundary

### In Scope

- Backend request/runtime naming such as `PerspectiveContext`, `PerspectiveContextChecker`, `perspective` parameters that really mean scope mode, and helper names like `build_party_filter_from_perspective_context()`.
- Backend service-layer naming that really means binding type or scope mode, including customer-profile, search, and contract-group internals.
- Frontend runtime/config/test residue that still depends on perspective-prefixed route paths or `perspective:*` query-scope tokens.
- User-visible and requirement-doc wording that still says "当前视角" where the real meaning is data scope or binding type.

### Explicitly Preserved Compatibility Surfaces

- `X-Perspective` request header stays as-is for now.
- `capabilities[].perspectives` stays as-is for now.

Reason: these are still active full-stack protocol surfaces. They can be retired later, but not inside this cleanup unless a separate breaking-contract decision is made.

### Naming Target

- `owner | manager` as user-binding semantics: `BindingType`
- `owner | manager | all` as request narrowing semantics: `ScopeMode`
- Request context object: `DataScopeContext`
- Context dependency/helper names: `require_data_scope_context`, `build_party_filter_from_scope_context`

---

### Task 1: Rename Backend Scope Primitives

**Files:**
- Modify: `backend/src/schemas/authz.py`
- Modify: `backend/src/middleware/auth.py`
- Modify: `backend/src/services/party_scope.py`
- Test: `backend/tests/unit/middleware/test_perspective_context.py`
- Test: `backend/tests/unit/middleware/test_perspective_context_optional.py`
- Test: `backend/tests/unit/services/test_party_scope.py`

**Step 1: Write the failing tests**

Update the middleware and party-scope tests so they import and assert the new names first.

```python
from src.middleware.auth import DataScopeContext, require_data_scope_context
from src.services.party_scope import build_party_filter_from_scope_context

def test_scope_context_symbols_exist():
    assert DataScopeContext is not None
    assert callable(require_data_scope_context)
    assert callable(build_party_filter_from_scope_context)
```

**Step 2: Run test to verify it fails**

Run: `cd backend && uv run python -m pytest --no-cov tests/unit/middleware/test_perspective_context.py tests/unit/middleware/test_perspective_context_optional.py tests/unit/services/test_party_scope.py -q`

Expected: import or symbol errors because the new scope names do not exist yet.

**Step 3: Write minimal implementation**

- In `backend/src/schemas/authz.py`, rename internal type aliases to `BindingType` and `ScopeMode`, while keeping the capability response field name `perspectives` unchanged.
- In `backend/src/middleware/auth.py`, rename `PerspectiveContext` to `DataScopeContext`, `PerspectiveContextChecker` to `DataScopeContextChecker`, and `require_perspective_context()` to `require_data_scope_context()`.
- Rename context fields so request-scope semantics no longer use the ambiguous word `perspective`.

```python
BindingType = Literal["owner", "manager"]
ScopeMode = Literal["owner", "manager", "all"]

@dataclass(frozen=True)
class DataScopeContext:
    scope_mode: ScopeMode
    allowed_binding_types: list[BindingType]
    owner_party_ids: list[str]
    manager_party_ids: list[str]
    effective_party_ids: list[str]
    source: Literal["header", "auto"]
```

- In `backend/src/services/party_scope.py`, rename `build_party_filter_from_perspective_context()` to `build_party_filter_from_scope_context()` and switch its internal branches to `scope_mode`.

**Step 4: Run test to verify it passes**

Run: `cd backend && uv run python -m pytest --no-cov tests/unit/middleware/test_perspective_context.py tests/unit/middleware/test_perspective_context_optional.py tests/unit/services/test_party_scope.py -q`

Expected: PASS.

**Step 5: Commit**

```bash
git add backend/src/schemas/authz.py backend/src/middleware/auth.py backend/src/services/party_scope.py backend/tests/unit/middleware/test_perspective_context.py backend/tests/unit/middleware/test_perspective_context_optional.py backend/tests/unit/services/test_party_scope.py
git commit -m "refactor(scope): rename request scope primitives"
```

---

### Task 2: Rename Backend Service-Layer Semantics

**Files:**
- Modify: `backend/src/services/party/service.py`
- Modify: `backend/src/services/search/service.py`
- Modify: `backend/src/services/contract/contract_group_service.py`
- Modify: `backend/src/api/v1/party.py`
- Modify: `backend/src/api/v1/search.py`
- Test: `backend/tests/unit/services/test_party_service.py`
- Test: `backend/tests/unit/services/search/test_search_service.py`
- Test: `backend/tests/unit/api/v1/test_party_api.py`
- Test: `backend/tests/unit/api/v1/test_search_api.py`
- Test: `backend/tests/unit/services/contract/test_contract_group_service.py`

**Step 1: Write the failing tests**

Update service and API tests so internal calls use the new argument names.

```python
profile = await service.get_customer_profile(
    db=session,
    party_id="party-1",
    binding_type="manager",
    effective_party_ids=["mgr-1"],
)

result = await search_service.search_global(
    db=session,
    query="测试",
    scope_mode="manager",
    effective_party_ids=["mgr-1"],
)
```

**Step 2: Run test to verify it fails**

Run: `cd backend && uv run python -m pytest --no-cov tests/unit/services/test_party_service.py tests/unit/services/search/test_search_service.py tests/unit/api/v1/test_party_api.py tests/unit/api/v1/test_search_api.py tests/unit/services/contract/test_contract_group_service.py -q`

Expected: failures due to renamed keyword arguments and symbol references.

**Step 3: Write minimal implementation**

- In `backend/src/services/party/service.py`, rename customer-profile parameters and helper arguments from `perspective` to `binding_type` where they mean owner/manager binding semantics.
- In `backend/src/services/search/service.py`, rename internal parameters from `perspective` to `scope_mode` where they mean request narrowing mode.
- In `backend/src/services/contract/contract_group_service.py`, rename the service-only `perspective` parameter to `binding_type` or `scope_mode` based on the actual branch semantics, then update all callers.
- Update API-layer wiring in `backend/src/api/v1/party.py` and `backend/src/api/v1/search.py` so they read the new `DataScopeContext` fields.

**Step 4: Run test to verify it passes**

Run: `cd backend && uv run python -m pytest --no-cov tests/unit/services/test_party_service.py tests/unit/services/search/test_search_service.py tests/unit/api/v1/test_party_api.py tests/unit/api/v1/test_search_api.py tests/unit/services/contract/test_contract_group_service.py -q`

Expected: PASS, except for environment-driven DB skips already accepted by the fixtures.

**Step 5: Commit**

```bash
git add backend/src/services/party/service.py backend/src/services/search/service.py backend/src/services/contract/contract_group_service.py backend/src/api/v1/party.py backend/src/api/v1/search.py backend/tests/unit/services/test_party_service.py backend/tests/unit/services/search/test_search_service.py backend/tests/unit/api/v1/test_party_api.py backend/tests/unit/api/v1/test_search_api.py backend/tests/unit/services/contract/test_contract_group_service.py
git commit -m "refactor(scope): rename backend service semantics"
```

---

### Task 3: Remove Frontend Runtime Residue From Flat-Route Code Paths

**Files:**
- Modify: `frontend/src/hooks/useSmartPreload.tsx`
- Modify: `frontend/src/routes/AppRoutes.tsx`
- Modify: `frontend/src/config/menuConfig.tsx`
- Modify: `frontend/src/components/Layout/AppBreadcrumb.tsx`
- Modify: `frontend/src/components/Layout/AppHeader.tsx`
- Test: `frontend/src/hooks/__tests__/useSmartPreload.test.tsx`
- Test: `frontend/src/config/__tests__/menuConfig.perspective-grouping.test.tsx`
- Test: `frontend/src/components/Layout/__tests__/AppBreadcrumb.test.tsx`
- Test: `frontend/src/components/Layout/__tests__/AppHeader.test.tsx`
- Test: `frontend/src/routes/__tests__/AppRoutes.legacy-rental-retired.test.tsx`

**Step 1: Write the failing tests**

Update route and preload tests so they assert canonical flat routes instead of perspective-prefixed ones.

```ts
expect(source).toContain("'/assets/list'")
expect(getSelectedKeys('/assets/asset-1')).toEqual(['/assets/list'])
expect(navigateMock).toHaveBeenCalledWith('/search')
```

**Step 2: Run test to verify it fails**

Run: `cd frontend && pnpm exec vitest run src/hooks/__tests__/useSmartPreload.test.tsx src/config/__tests__/menuConfig.perspective-grouping.test.tsx src/components/Layout/__tests__/AppBreadcrumb.test.tsx src/components/Layout/__tests__/AppHeader.test.tsx src/routes/__tests__/AppRoutes.legacy-rental-retired.test.tsx --reporter=dot`

Expected: failures because runtime and tests still refer to `/owner/*` and `/manager/*`.

**Step 3: Write minimal implementation**

- In `frontend/src/hooks/useSmartPreload.tsx`, replace hard-coded `/owner/assets` predictions with canonical flat routes.
- In `frontend/src/config/menuConfig.tsx`, remove any perspective-grouping assumptions and keep only flat-route selection/open-key behavior.
- In `frontend/src/routes/AppRoutes.tsx`, keep only the legacy redirects that are still intentionally supported; delete redundant compatibility entries that no longer add value after test rewrites.
- Update header/breadcrumb tests and wiring to assert canonical flat-route navigation.

**Step 4: Run test to verify it passes**

Run: `cd frontend && pnpm exec vitest run src/hooks/__tests__/useSmartPreload.test.tsx src/config/__tests__/menuConfig.perspective-grouping.test.tsx src/components/Layout/__tests__/AppBreadcrumb.test.tsx src/components/Layout/__tests__/AppHeader.test.tsx src/routes/__tests__/AppRoutes.legacy-rental-retired.test.tsx --reporter=dot`

Expected: PASS.

**Step 5: Commit**

```bash
git add frontend/src/hooks/useSmartPreload.tsx frontend/src/routes/AppRoutes.tsx frontend/src/config/menuConfig.tsx frontend/src/components/Layout/AppBreadcrumb.tsx frontend/src/components/Layout/AppHeader.tsx frontend/src/hooks/__tests__/useSmartPreload.test.tsx frontend/src/config/__tests__/menuConfig.perspective-grouping.test.tsx frontend/src/components/Layout/__tests__/AppBreadcrumb.test.tsx frontend/src/components/Layout/__tests__/AppHeader.test.tsx frontend/src/routes/__tests__/AppRoutes.legacy-rental-retired.test.tsx
git commit -m "refactor(scope): remove frontend runtime perspective residue"
```

---

### Task 4: Normalize Frontend Test Fixtures And Scoped Query Tokens

**Files:**
- Modify: `frontend/src/hooks/__tests__/useAnalytics.test.ts`
- Modify: `frontend/src/hooks/__tests__/useAssets.test.ts`
- Modify: `frontend/src/hooks/__tests__/useProject.test.ts`
- Modify: `frontend/src/pages/Assets/__tests__/AssetAnalyticsPage.export.test.tsx`
- Modify: `frontend/src/pages/Assets/__tests__/AssetCreatePage.test.tsx`
- Modify: `frontend/src/pages/Assets/__tests__/AssetDetailPage.test.tsx`
- Modify: `frontend/src/pages/Assets/__tests__/AssetListPage.test.tsx`
- Modify: `frontend/src/pages/Customer/__tests__/CustomerDetailPage.test.tsx`
- Modify: `frontend/src/pages/Search/__tests__/GlobalSearchPage.test.tsx`
- Modify: `frontend/src/services/__tests__/searchService.test.ts`
- Modify: `frontend/src/components/Project/__tests__/ProjectList.test.tsx`

**Step 1: Write the failing tests**

Rewrite the fixture values to the current scope model first.

```ts
vi.mock('@/utils/queryScope', () => ({
  buildQueryScopeKey: () => 'user:user-1|scope:owner,manager',
}))

renderWithProviders(<AssetListPage />, { route: '/assets/list' })
```

**Step 2: Run test to verify it fails**

Run: `cd frontend && pnpm exec vitest run src/hooks/__tests__/useAnalytics.test.ts src/hooks/__tests__/useAssets.test.ts src/hooks/__tests__/useProject.test.ts src/pages/Assets/__tests__/AssetAnalyticsPage.export.test.tsx src/pages/Assets/__tests__/AssetCreatePage.test.tsx src/pages/Assets/__tests__/AssetDetailPage.test.tsx src/pages/Assets/__tests__/AssetListPage.test.tsx src/pages/Customer/__tests__/CustomerDetailPage.test.tsx src/pages/Search/__tests__/GlobalSearchPage.test.tsx src/services/__tests__/searchService.test.ts src/components/Project/__tests__/ProjectList.test.tsx --reporter=dot`

Expected: failures because old fixture routes and query-scope tokens are still in place.

**Step 3: Write minimal implementation**

- Replace `perspective:*` query-scope fixture tokens with `scope:*` tokens.
- Replace `/owner/*` and `/manager/*` test entries with canonical routes, except for the small number of explicit legacy-redirect tests that intentionally verify redirect behavior.
- Remove any no-longer-meaningful test names that still say "当前视角" when they really assert scope-driven caching.

**Step 4: Run test to verify it passes**

Run: `cd frontend && pnpm exec vitest run src/hooks/__tests__/useAnalytics.test.ts src/hooks/__tests__/useAssets.test.ts src/hooks/__tests__/useProject.test.ts src/pages/Assets/__tests__/AssetAnalyticsPage.export.test.tsx src/pages/Assets/__tests__/AssetCreatePage.test.tsx src/pages/Assets/__tests__/AssetDetailPage.test.tsx src/pages/Assets/__tests__/AssetListPage.test.tsx src/pages/Customer/__tests__/CustomerDetailPage.test.tsx src/pages/Search/__tests__/GlobalSearchPage.test.tsx src/services/__tests__/searchService.test.ts src/components/Project/__tests__/ProjectList.test.tsx --reporter=dot`

Expected: PASS.

**Step 5: Commit**

```bash
git add frontend/src/hooks/__tests__/useAnalytics.test.ts frontend/src/hooks/__tests__/useAssets.test.ts frontend/src/hooks/__tests__/useProject.test.ts frontend/src/pages/Assets/__tests__/AssetAnalyticsPage.export.test.tsx frontend/src/pages/Assets/__tests__/AssetCreatePage.test.tsx frontend/src/pages/Assets/__tests__/AssetDetailPage.test.tsx frontend/src/pages/Assets/__tests__/AssetListPage.test.tsx frontend/src/pages/Customer/__tests__/CustomerDetailPage.test.tsx frontend/src/pages/Search/__tests__/GlobalSearchPage.test.tsx frontend/src/services/__tests__/searchService.test.ts frontend/src/components/Project/__tests__/ProjectList.test.tsx
git commit -m "test(scope): align frontend fixtures with data scope"
```

---

### Task 5: Rewrite Docs, Mark Completion, And Run Final Verification

**Files:**
- Modify: `docs/requirements-specification.md`
- Modify: `docs/features/requirements-appendix-fields.md`
- Modify: `docs/plans/README.md`
- Modify: `CHANGELOG.md`
- Modify: `docs/archive/backend-plans/2026-04-05-perspective-residue-cleanup.md`
- Modify: `docs/plans/2026-04-05-perspective-residue-eradication-plan.md`

**Step 1: Write the failing documentation checks**

Before editing docs, grep for old wording so the implementation has a fixed target.

```bash
grep -R "当前视角\|强制 X-Perspective\|perspective_type" docs
```

Expected: remaining matches that should be removed or reworded, excluding archived historical context that is intentionally preserved.

**Step 2: Update docs minimally**

- Rewrite requirement wording so `REQ-AUTH-002` and `REQ-SCH-003` match the new scope terminology.
- Update the fields appendix where customer-profile or contract-role descriptions still mention perspective.
- Update the archived cleanup plan and this active implementation plan with the actual outcome.
- Add a concise `CHANGELOG.md` entry that records the internal rename and the verification evidence.

**Step 3: Run focused verification**

Run:

```bash
cd backend && uv run python -m pytest --no-cov tests/unit/middleware/test_perspective_context.py tests/unit/middleware/test_perspective_context_optional.py tests/unit/services/test_party_scope.py tests/unit/services/test_party_service.py tests/unit/services/search/test_search_service.py tests/unit/api/v1/test_party_api.py tests/unit/api/v1/test_search_api.py tests/unit/services/contract/test_contract_group_service.py -q
cd backend && uv run python -m ruff check src tests/unit
cd frontend && pnpm exec vitest run src/hooks/__tests__/useSmartPreload.test.tsx src/config/__tests__/menuConfig.perspective-grouping.test.tsx src/components/Layout/__tests__/AppBreadcrumb.test.tsx src/components/Layout/__tests__/AppHeader.test.tsx src/hooks/__tests__/useAnalytics.test.ts src/hooks/__tests__/useAssets.test.ts src/hooks/__tests__/useProject.test.ts src/pages/Assets/__tests__/AssetAnalyticsPage.export.test.tsx src/pages/Assets/__tests__/AssetCreatePage.test.tsx src/pages/Assets/__tests__/AssetDetailPage.test.tsx src/pages/Assets/__tests__/AssetListPage.test.tsx src/pages/Customer/__tests__/CustomerDetailPage.test.tsx src/pages/Search/__tests__/GlobalSearchPage.test.tsx src/services/__tests__/searchService.test.ts src/components/Project/__tests__/ProjectList.test.tsx --reporter=dot
cd frontend && pnpm type-check
cd frontend && pnpm exec oxlint --config .oxlintrc.json --deny-warnings --max-warnings=0 --disable-unicorn-plugin --react-plugin --import-plugin --jsx-a11y-plugin src/hooks/__tests__/useSmartPreload.test.tsx src/config/__tests__/menuConfig.perspective-grouping.test.tsx src/components/Layout/__tests__/AppBreadcrumb.test.tsx src/components/Layout/__tests__/AppHeader.test.tsx src/hooks/__tests__/useAnalytics.test.ts src/hooks/__tests__/useAssets.test.ts src/hooks/__tests__/useProject.test.ts src/pages/Assets/__tests__/AssetAnalyticsPage.export.test.tsx src/pages/Assets/__tests__/AssetCreatePage.test.tsx src/pages/Assets/__tests__/AssetDetailPage.test.tsx src/pages/Assets/__tests__/AssetListPage.test.tsx src/pages/Customer/__tests__/CustomerDetailPage.test.tsx src/pages/Search/__tests__/GlobalSearchPage.test.tsx src/services/__tests__/searchService.test.ts src/components/Project/__tests__/ProjectList.test.tsx
cd /mnt/d/ccode/zcgl && make docs-lint
```

Expected: all targeted checks pass; any DB-driven skips must be called out explicitly rather than treated as a clean pass.

**Step 4: Commit**

```bash
git add docs/requirements-specification.md docs/features/requirements-appendix-fields.md docs/plans/README.md CHANGELOG.md docs/archive/backend-plans/2026-04-05-perspective-residue-cleanup.md docs/plans/2026-04-05-perspective-residue-eradication-plan.md
git commit -m "docs(scope): close perspective residue eradication"
```

---

## Execution Notes

- Do not reintroduce compatibility aliases like `PerspectiveContext = DataScopeContext` unless a concrete import path still needs them.
- Keep changes minimal inside each task; do not mix runtime renames with unrelated refactors.
- If a batch expands beyond its listed files, stop and update this plan before continuing.
- If a route or capability field is preserved only for compatibility, add a short comment or doc note explaining that preservation boundary.

## Expected Outcome

- Internal runtime code consistently distinguishes binding semantics from request scope semantics.
- Frontend runtime/config no longer depends on perspective-prefixed canonical routes.
- Test fixtures no longer encode obsolete perspective-based query-scope tokens.
- Docs describe data scope as the primary concept, with perspective retained only where it is an explicit compatibility surface.
