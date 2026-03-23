# Frontend Perspective Simplification V2 Follow-up Implementation Plan

> **状态**：✅ 已完成，2026-03-23 归档。route-derived perspective core、ViewProvider 运行时退役以及 canonical active-path follow-up 均已并入 `develop`。

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Finish converting the merged owner/manager route shell into the canonical frontend perspective model, so perspective is derived from the route instead of persisted manual view selection.

**Architecture:** Keep backend authz and data scope unchanged. On the frontend, treat route prefix (`/owner/*`, `/manager/*`) as the only perspective signal, replace `ViewContext`/`viewSelectionStorage` with route-derived helpers, and move internal navigation to canonical active paths. Keep legacy redirects only as a short-lived migration shim until internal callers and tests are fully switched.

**Tech Stack:** React 19, React Router 6, React Query 5, Vitest, Playwright, GitHub Actions

---

## Scope

In scope:
- route-derived perspective helper and query-scope keys
- removal of manual view-selection storage/provider plumbing
- canonical owner/manager internal navigation and tests
- frontend unit/E2E coverage updates

Out of scope:
- backend authz rule redesign
- capability package schema changes
- party binding model changes
- broad owner/manager data-scope semantics changes on the API side

## Current Baseline

- `OWNER_ROUTES` / `MANAGER_ROUTES` and `LegacyRouteRedirect` already exist.
- `PartySelector` already infers default filter mode from `/owner/*` and `/manager/*`.
- `ViewContext` still gates most assets/projects/analytics queries through `currentView`, `selectionRequired`, and `isViewReady`.
- `queryScope.ts` still includes `viewSelectionStorage`, even though the selected view only affects frontend cache keys and loading gates.
- Many page tests still mock `@/contexts/ViewContext`, which keeps the old mental model alive.

## File Map

### Create

- `frontend/src/routes/perspective.ts`
- `frontend/src/routes/__tests__/perspective.test.ts`

### Modify

- `frontend/src/App.tsx`
- `frontend/src/constants/routes.ts`
- `frontend/src/routes/AppRoutes.tsx`
- `frontend/src/routes/LegacyRouteRedirect.tsx`
- `frontend/src/utils/queryScope.ts`
- `frontend/src/components/Common/PartySelector.tsx`
- `frontend/src/components/Layout/AppBreadcrumb.tsx`
- `frontend/src/components/Layout/AppSidebar.tsx`
- `frontend/src/components/Layout/MobileMenu.tsx`
- `frontend/src/components/Project/ProjectList.tsx`
- `frontend/src/components/System/CurrentViewBanner.tsx`
- `frontend/src/hooks/useAnalytics.ts`
- `frontend/src/hooks/useAssetAnalytics.ts`
- `frontend/src/hooks/useAssets.ts`
- `frontend/src/hooks/useProject.ts`
- `frontend/src/pages/Assets/AssetListPage.tsx`
- `frontend/src/pages/Assets/AssetDetailPage.tsx`
- `frontend/src/pages/Assets/AssetCreatePage.tsx`
- `frontend/src/pages/Assets/AssetAnalyticsPage.tsx`
- `frontend/src/pages/Project/ProjectDetailPage.tsx`
- `frontend/src/pages/PropertyCertificate/PropertyCertificateDetailPage.tsx`
- `frontend/src/pages/PropertyCertificate/PropertyCertificateImport.tsx`
- `frontend/src/__tests__/app-view-provider.test.ts`
- `frontend/src/components/Common/__tests__/PartySelector.test.tsx`
- `frontend/src/components/Layout/__tests__/AppBreadcrumb.test.tsx`
- `frontend/src/components/Layout/__tests__/AppSidebar.test.tsx`
- `frontend/src/config/__tests__/menuConfig.perspective-grouping.test.tsx`
- `frontend/src/config/__tests__/rental-retired-navigation.test.ts`
- `frontend/src/hooks/__tests__/useAnalytics.test.ts`
- `frontend/src/hooks/__tests__/useAssetAnalytics.test.ts`
- `frontend/src/hooks/__tests__/useAssets.test.ts`
- `frontend/src/hooks/__tests__/useProject.test.ts`
- `frontend/src/pages/Assets/__tests__/AssetListPage.test.tsx`
- `frontend/src/pages/Assets/__tests__/AssetDetailPage.test.tsx`
- `frontend/src/pages/Assets/__tests__/AssetCreatePage.test.tsx`
- `frontend/src/pages/Assets/__tests__/AssetAnalyticsPage.test.tsx`
- `frontend/src/pages/Project/__tests__/ProjectDetailPage.test.tsx`
- `frontend/src/components/Project/__tests__/ProjectList.test.tsx`
- `frontend/tests/e2e/asset-flow.spec.ts`
- `frontend/tests/e2e/user/user-usability.spec.ts`
- `frontend/tests/e2e/user/import-guardrails.spec.ts`
- `frontend/tests/e2e/user/property-certificate-import-success.spec.ts`
- `CHANGELOG.md`

### Delete

- `frontend/src/contexts/ViewContext.tsx`
- `frontend/src/utils/viewSelectionStorage.ts`
- `frontend/src/types/viewSelection.ts`

## Chunk 1: Route-Derived Perspective Core

### Task 1: Introduce a single route perspective resolver

**Files:**
- Create: `frontend/src/routes/perspective.ts`
- Test: `frontend/src/routes/__tests__/perspective.test.ts`

- [ ] **Step 1: Write the failing test**

```ts
import { describe, expect, it } from 'vitest';
import { getRoutePerspective, isPerspectiveRoute } from '../perspective';

describe('route perspective resolution', () => {
  it('maps owner-prefixed paths to owner', () => {
    expect(getRoutePerspective('/owner/assets')).toBe('owner');
    expect(getRoutePerspective('/owner/property-certificates/cert-1')).toBe('owner');
  });

  it('maps manager-prefixed paths to manager', () => {
    expect(getRoutePerspective('/manager/projects')).toBe('manager');
    expect(getRoutePerspective('/manager/contract-groups/group-1')).toBe('manager');
  });

  it('returns null for shared and legacy paths', () => {
    expect(getRoutePerspective('/dashboard')).toBeNull();
    expect(getRoutePerspective('/assets/list')).toBeNull();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && pnpm vitest run src/routes/__tests__/perspective.test.ts`
Expected: FAIL because `perspective.ts` does not exist yet.

- [ ] **Step 3: Write minimal implementation**

```ts
export type RoutePerspective = 'owner' | 'manager' | null;

export const getRoutePerspective = (pathname: string): RoutePerspective => {
  if (pathname.startsWith('/owner/')) return 'owner';
  if (pathname.startsWith('/manager/')) return 'manager';
  return null;
};

export const isPerspectiveRoute = (pathname: string): boolean =>
  getRoutePerspective(pathname) != null;
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && pnpm vitest run src/routes/__tests__/perspective.test.ts`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/routes/perspective.ts frontend/src/routes/__tests__/perspective.test.ts
git commit -m "test(frontend-perspective): add route perspective resolver"
```

### Task 2: Collapse query scope to user + route perspective

**Files:**
- Modify: `frontend/src/utils/queryScope.ts`
- Delete: `frontend/src/utils/viewSelectionStorage.ts`
- Delete: `frontend/src/types/viewSelection.ts`
- Test: `frontend/src/hooks/__tests__/useAssets.test.ts`
- Test: `frontend/src/hooks/__tests__/useProject.test.ts`

- [ ] **Step 1: Write the failing tests**

Add assertions that query keys depend on route perspective, not stored view keys:

```ts
expect(result.current.queryKey).toEqual([
  'assets-list',
  'user:test-user|perspective:owner',
  params,
]);
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd frontend && pnpm vitest run src/hooks/__tests__/useAssets.test.ts src/hooks/__tests__/useProject.test.ts`
Expected: FAIL because `queryScope.ts` still emits `view:<stored-key>`.

- [ ] **Step 3: Write minimal implementation**

```ts
export type QueryScopePerspective = 'owner' | 'manager' | null;

export const buildQueryScopeKey = (perspective: QueryScopePerspective): string => {
  const currentUser = AuthStorage.getCurrentUser();
  const normalizedPerspective = perspective == null ? 'perspective:none' : `perspective:${perspective}`;
  return `${normalizeUserScope(currentUser?.id)}|${normalizedPerspective}`;
};
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd frontend && pnpm vitest run src/hooks/__tests__/useAssets.test.ts src/hooks/__tests__/useProject.test.ts`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/utils/queryScope.ts frontend/src/hooks/__tests__/useAssets.test.ts frontend/src/hooks/__tests__/useProject.test.ts
git rm frontend/src/utils/viewSelectionStorage.ts frontend/src/types/viewSelection.ts
git commit -m "refactor(frontend-perspective): drop stored view cache scope"
```

## Chunk 2: Remove ViewProvider Runtime Dependency

### Task 3: Replace `useView()` consumers with route-derived state

**Files:**
- Modify: `frontend/src/hooks/useAnalytics.ts`
- Modify: `frontend/src/hooks/useAssetAnalytics.ts`
- Modify: `frontend/src/hooks/useAssets.ts`
- Modify: `frontend/src/hooks/useProject.ts`
- Modify: `frontend/src/pages/Assets/AssetListPage.tsx`
- Modify: `frontend/src/pages/Assets/AssetDetailPage.tsx`
- Modify: `frontend/src/pages/Assets/AssetCreatePage.tsx`
- Modify: `frontend/src/pages/Assets/AssetAnalyticsPage.tsx`
- Modify: `frontend/src/components/Project/ProjectList.tsx`
- Modify: `frontend/src/pages/Project/ProjectDetailPage.tsx`
- Test: `frontend/src/hooks/__tests__/useAnalytics.test.ts`
- Test: `frontend/src/hooks/__tests__/useAssetAnalytics.test.ts`
- Test: `frontend/src/pages/Assets/__tests__/AssetListPage.test.tsx`
- Test: `frontend/src/pages/Assets/__tests__/AssetDetailPage.test.tsx`
- Test: `frontend/src/pages/Assets/__tests__/AssetCreatePage.test.tsx`
- Test: `frontend/src/pages/Assets/__tests__/AssetAnalyticsPage.test.tsx`
- Test: `frontend/src/components/Project/__tests__/ProjectList.test.tsx`
- Test: `frontend/src/pages/Project/__tests__/ProjectDetailPage.test.tsx`

- [ ] **Step 1: Write the failing tests**

Change tests to stop mocking `@/contexts/ViewContext` and instead mount inside a `MemoryRouter` with owner/manager paths. Assert:
- owner route queries use `perspective:owner`
- manager route queries use `perspective:manager`
- shared routes stay queryable without manual selector blocking

- [ ] **Step 2: Run tests to verify they fail**

Run:
`cd frontend && pnpm vitest run src/hooks/__tests__/useAnalytics.test.ts src/hooks/__tests__/useAssetAnalytics.test.ts src/pages/Assets/__tests__/AssetListPage.test.tsx src/pages/Assets/__tests__/AssetDetailPage.test.tsx src/pages/Assets/__tests__/AssetCreatePage.test.tsx src/pages/Assets/__tests__/AssetAnalyticsPage.test.tsx src/components/Project/__tests__/ProjectList.test.tsx src/pages/Project/__tests__/ProjectDetailPage.test.tsx`

Expected: FAIL because components/hooks still import `useView()`.

- [ ] **Step 3: Write minimal implementation**

Implementation rules:
- add a lightweight route helper or hook (for example `useRoutePerspective`) built on `useLocation()`
- remove `isViewReady` gates from route-owned pages
- keep route perspective only for cache scoping and owner/manager UI defaults
- do not reintroduce selector-open or persisted localStorage state

Illustrative hook:

```ts
export const useRoutePerspective = () => {
  const { pathname } = useLocation();
  const perspective = getRoutePerspective(pathname);
  return {
    perspective,
    isPerspectiveRoute: perspective != null,
  };
};
```

- [ ] **Step 4: Run tests to verify they pass**

Run the same vitest pack again.
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/hooks frontend/src/pages/Assets frontend/src/pages/Project frontend/src/components/Project
git commit -m "refactor(frontend-perspective): derive page scope from route"
```

### Task 4: Remove `ViewProvider` and retire the banner plumbing

**Files:**
- Modify: `frontend/src/App.tsx`
- Delete: `frontend/src/contexts/ViewContext.tsx`
- Modify: `frontend/src/components/System/CurrentViewBanner.tsx`
- Test: `frontend/src/__tests__/app-view-provider.test.ts`

- [ ] **Step 1: Write the failing tests**

Update the app shell test to assert:
- `App.tsx` no longer imports `ViewProvider`
- `AuthProvider` wraps `AntdApp` directly
- `CurrentViewBanner` renders route-derived labels or is removed from layout intentionally

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd frontend && pnpm vitest run src/__tests__/app-view-provider.test.ts`
Expected: FAIL because `ViewProvider` is still imported and wrapped.

- [ ] **Step 3: Write minimal implementation**

```tsx
<AuthProvider>
  <AntdApp>
    <AppInitializer>
      <BrowserRouter>{/* ... */}</BrowserRouter>
    </AppInitializer>
  </AntdApp>
</AuthProvider>
```

If `CurrentViewBanner` stays, rewrite it to use route-derived labels only:

```tsx
if (perspective === 'owner') return <Alert description="业主视角" ... />;
if (perspective === 'manager') return <Alert description="经营视角" ... />;
return null;
```

- [ ] **Step 4: Run tests to verify they pass**

Run:
- `cd frontend && pnpm vitest run src/__tests__/app-view-provider.test.ts`
- `cd frontend && pnpm type-check`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/App.tsx frontend/src/components/System/CurrentViewBanner.tsx frontend/src/__tests__/app-view-provider.test.ts
git rm frontend/src/contexts/ViewContext.tsx
git commit -m "refactor(frontend-perspective): remove ViewProvider runtime"
```

## Chunk 3: Canonical Navigation and Redirect Retirement

### Task 5: Move all internal links to canonical owner/manager paths

**Files:**
- Modify: `frontend/src/constants/routes.ts`
- Modify: `frontend/src/routes/AppRoutes.tsx`
- Modify: `frontend/src/routes/LegacyRouteRedirect.tsx`
- Modify: `frontend/src/components/Layout/AppBreadcrumb.tsx`
- Modify: `frontend/src/components/Layout/AppSidebar.tsx`
- Modify: `frontend/src/components/Layout/MobileMenu.tsx`
- Modify: `frontend/src/pages/PropertyCertificate/PropertyCertificateDetailPage.tsx`
- Modify: `frontend/src/pages/PropertyCertificate/PropertyCertificateImport.tsx`
- Test: `frontend/src/components/Layout/__tests__/AppBreadcrumb.test.tsx`
- Test: `frontend/src/components/Layout/__tests__/AppSidebar.test.tsx`
- Test: `frontend/src/config/__tests__/menuConfig.perspective-grouping.test.tsx`
- Test: `frontend/src/config/__tests__/rental-retired-navigation.test.ts`

- [ ] **Step 1: Write the failing tests**

Add/adjust assertions that:
- menus never navigate to `/assets/list`, `/project`, `/property-certificates`
- breadcrumbs resolve detail back-links to canonical `/owner/*` or `/manager/*` pages
- `LegacyRouteRedirect` only remains for explicit legacy-entry compatibility, not internal navigation

- [ ] **Step 2: Run tests to verify they fail**

Run:
`cd frontend && pnpm vitest run src/components/Layout/__tests__/AppBreadcrumb.test.tsx src/components/Layout/__tests__/AppSidebar.test.tsx src/config/__tests__/menuConfig.perspective-grouping.test.tsx src/config/__tests__/rental-retired-navigation.test.ts`

Expected: FAIL until links and menus stop pointing at legacy shared routes.

- [ ] **Step 3: Write minimal implementation**

Rules:
- internal navigation from menus/buttons/breadcrumbs must target canonical owner/manager routes only
- keep `LegacyRouteRedirect` for a bounded list of direct legacy URLs during the migration window
- after all internal callers are switched, reduce `LegacyRouteRedirect` to explicit compatibility paths only

- [ ] **Step 4: Run tests to verify they pass**

Run the same vitest pack again.
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/constants/routes.ts frontend/src/routes/AppRoutes.tsx frontend/src/routes/LegacyRouteRedirect.tsx frontend/src/components/Layout
git commit -m "refactor(frontend-nav): canonicalize internal perspective routes"
```

### Task 6: Update E2E and finish fail-fast legacy exposure

**Files:**
- Modify: `frontend/tests/e2e/asset-flow.spec.ts`
- Modify: `frontend/tests/e2e/user/user-usability.spec.ts`
- Modify: `frontend/tests/e2e/user/import-guardrails.spec.ts`
- Modify: `frontend/tests/e2e/user/property-certificate-import-success.spec.ts`

- [ ] **Step 1: Write or update failing E2E expectations**

Target assertions:
- assets start from `/owner/assets`
- projects start from `/manager/projects`
- contract import starts from `/contract-groups/import`
- property certificate success flows land on `/owner/property-certificates`

- [ ] **Step 2: Run targeted E2E to verify failures**

Run:
`cd frontend && BASE_URL=http://127.0.0.1:5173 VITE_API_BASE_URL=http://127.0.0.1:8002/api/v1 E2E_ADMIN_USERNAME=admin E2E_ADMIN_PASSWORD='Admin123!@#' E2E_REQUIRE_AUTH_STATE=true pnpm playwright test tests/e2e/asset-flow.spec.ts tests/e2e/user/property-certificate-import-success.spec.ts tests/e2e/user/user-usability.spec.ts tests/e2e/user/import-guardrails.spec.ts --project=chromium`

Expected: FAIL until all route expectations and in-app navigations are canonical.

- [ ] **Step 3: Write minimal implementation / spec updates**

Update only the spec expectations and any remaining in-app navigation that still lands on shared legacy paths. Do not weaken assertions; point them at canonical active paths.

- [ ] **Step 4: Run targeted E2E to verify it passes**

Run the same Playwright command again.
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/tests/e2e/asset-flow.spec.ts frontend/tests/e2e/user/user-usability.spec.ts frontend/tests/e2e/user/import-guardrails.spec.ts frontend/tests/e2e/user/property-certificate-import-success.spec.ts
git commit -m "test(frontend-perspective): align canonical route coverage"
```

## Final Verification

- [ ] Run: `cd backend && uv run pytest tests/unit/config/test_ci_workflow.py --no-cov -q`
- [ ] Run: `cd frontend && pnpm lint`
- [ ] Run: `cd frontend && pnpm type-check`
- [ ] Run: `cd frontend && pnpm type-check:e2e`
- [ ] Run: `cd frontend && pnpm format:check`
- [ ] Run: `cd frontend && pnpm vitest run src/routes/__tests__/perspective.test.ts src/__tests__/app-view-provider.test.ts src/hooks/__tests__/useAnalytics.test.ts src/hooks/__tests__/useAssetAnalytics.test.ts src/hooks/__tests__/useAssets.test.ts src/hooks/__tests__/useProject.test.ts src/components/Layout/__tests__/AppBreadcrumb.test.tsx src/components/Layout/__tests__/AppSidebar.test.tsx src/config/__tests__/menuConfig.perspective-grouping.test.tsx src/config/__tests__/rental-retired-navigation.test.ts src/pages/Assets/__tests__/AssetListPage.test.tsx src/pages/Assets/__tests__/AssetDetailPage.test.tsx src/pages/Assets/__tests__/AssetCreatePage.test.tsx src/pages/Assets/__tests__/AssetAnalyticsPage.test.tsx src/components/Project/__tests__/ProjectList.test.tsx src/pages/Project/__tests__/ProjectDetailPage.test.tsx`
- [ ] Run: `cd frontend && BASE_URL=http://127.0.0.1:5173 VITE_API_BASE_URL=http://127.0.0.1:8002/api/v1 E2E_ADMIN_USERNAME=admin E2E_ADMIN_PASSWORD='Admin123!@#' E2E_REQUIRE_AUTH_STATE=true pnpm playwright test tests/e2e/asset-flow.spec.ts tests/e2e/user/property-certificate-import-success.spec.ts tests/e2e/user/user-usability.spec.ts tests/e2e/user/import-guardrails.spec.ts --project=chromium`
- [ ] Update `CHANGELOG.md` with the implementation evidence and move this plan to archive once all tasks are complete.

## Exit Criteria

- no runtime import of `ViewContext` remains in production code
- internal navigation no longer targets shared legacy `/assets/list`, `/project`, `/property-certificates`
- owner/manager perspective is resolved solely from canonical route prefixes
- targeted unit/E2E suites pass against canonical active paths
- any remaining legacy redirects are explicit, bounded, and removable in a subsequent cleanup pass
