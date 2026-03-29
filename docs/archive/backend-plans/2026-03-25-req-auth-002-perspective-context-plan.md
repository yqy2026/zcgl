# REQ-AUTH-002 Perspective Context Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close `REQ-AUTH-002` by making route-derived perspective a backend-enforced request contract, so business requests execute under a single owner/manager data scope and invalid perspective sessions resolve through a unified recovery flow.

**Architecture:** Add a request-level `PerspectiveContext` contract spanning frontend route-derived header injection, backend perspective validation, and capability/resource perspective registration. Then thread that context through the active business query surfaces (assets, projects, contract groups, analytics) so every request uses explicit `effective_party_ids` instead of mixed scope fallbacks. Finally, unify frontend perspective failure recovery via a shared resolution layer used by both canonical routes and legacy redirects.

**Tech Stack:** React 19, TypeScript 5, Vite 6, Vitest, FastAPI, Python 3.12, SQLAlchemy 2.0, Pydantic v2

---

## Execution Status (2026-03-29)

Code-level implementation for this plan is in place: backend resource perspective registry, `PerspectiveContext`, frontend `X-Perspective` injection, `PerspectiveResolution`, and the main asset/project/contract-group/analytics read surfaces are already landed in the branch.

Fresh verification performed on 2026-03-29:

- `make check` PASS
- Direct API probes on local dev runtime: owner `project(owner)` returns `403 当前资源无可用视角`; manager `project(manager)` and `asset detail(manager)` return `200`
- Scoped browser inspection on `/project` and `/manager/assets/{id}` confirms login succeeds and both routes render main UI without redirecting to `/login` or `/403`
- `/ownership/*` remains neutral and out of scope for this plan

Closure update:

- Integration tests [`backend/tests/integration/api/test_project_visibility_real.py`](/home/y/projects/zcgl/backend/tests/integration/api/test_project_visibility_real.py) and [`backend/tests/integration/api/test_assets_visibility_real.py`](/home/y/projects/zcgl/backend/tests/integration/api/test_assets_visibility_real.py) now send explicit `X-Perspective` and lock the fail-closed `400` behavior for missing header.
- `notification:read` is now exposed as an authenticated-default capability, so non-admin route smoke checks no longer emit `/api/v1/notifications*` `403` warnings.
- Fresh browser inspection on `/project` and `/manager/assets/{id}` is now `ok`/`ok` with no warn/fail routes.

This plan is complete and ready for archive.

## Chunk 1: File Structure

### Backend ownership

- Create: `backend/src/services/authz/resource_perspective_registry.py`
  Responsibility: Single backend truth for `resource -> allowed perspectives`.
- Create: `backend/tests/unit/services/test_authz_service.py`
  Responsibility: Lock `/auth/me/capabilities` perspective generation against the registry.
- Create: `backend/tests/unit/middleware/test_perspective_context.py`
  Responsibility: Lock `X-Perspective` parsing, fail-closed rules, and neutral endpoint exemptions.
- Modify: `backend/src/schemas/authz.py`
  Responsibility: Keep capabilities schema aligned with explicit perspective semantics.
- Modify: `backend/src/services/authz/service.py`
  Responsibility: Apply registry-based perspective resolution when building capabilities.
- Modify: `backend/src/middleware/auth.py`
  Responsibility: Add `PerspectiveContext`, request parsing helpers, and perspective-aware auth dependencies.
- Modify: `backend/src/services/party_scope.py`
  Responsibility: Build perspective-specific `PartyFilter` values without mixed owner/manager fallbacks.
- Modify: `backend/src/crud/query_builder.py`
  Responsibility: Consume perspective-specific `PartyFilter` values without accidental union fallback.
- Modify: `backend/src/api/v1/auth/auth_modules/authentication.py`
  Responsibility: Keep `/auth/me/capabilities` as a neutral endpoint while returning resource-level perspectives.
- Modify: `backend/src/api/v1/assets/assets.py`
  Responsibility: Require perspective context for active asset list/detail business routes.
- Modify: `backend/src/api/v1/assets/project.py`
  Responsibility: Require perspective context for active project API routes.
- Modify: `backend/src/api/v1/contracts/contract_groups.py`
  Responsibility: Require perspective context for contract-group routes.
- Modify: `backend/src/services/contract/contract_group_service.py`
  Responsibility: Thread explicit perspective-scoped filters through contract-group business queries instead of relying on implicit shared scope.
- Modify: `backend/src/api/v1/analytics/analytics.py`
  Responsibility: Require perspective context for analytics routes.
- Modify: `backend/tests/unit/api/v1/test_analytics.py`
  Responsibility: Lock missing/invalid perspective failure behavior for analytics APIs.

### Frontend ownership

- Modify: `frontend/src/routes/perspective.ts`
  Responsibility: Expose current route perspective helpers usable outside React components.
- Modify: `frontend/src/api/client.ts`
  Responsibility: Inject `X-Perspective` for business requests and skip it for neutral routes.
- Modify: `frontend/src/api/__tests__/client.test.ts`
  Responsibility: Lock header injection and neutral-route exemptions.
- Modify: `frontend/src/services/capabilityService.ts`
  Responsibility: Preserve backend-provided `perspectives` semantics without local override assumptions.
- Modify: `frontend/src/services/__tests__/capabilityService.test.ts`
  Responsibility: Lock registry-driven perspective payload behavior.
- Create: `frontend/src/routes/perspectiveResolution.ts`
  Responsibility: Deterministic invalid-perspective fallback mapping and neutral-route classification.
- Create: `frontend/src/routes/PerspectiveResolutionPage.tsx`
  Responsibility: Unified recovery screen for invalid/expired perspectives.
- Create: `frontend/src/routes/__tests__/perspectiveResolution.test.tsx`
  Responsibility: Lock fallback mapping and recovery rendering.
- Modify: `frontend/src/App.tsx`
  Responsibility: Connect canonical protected-route failures to the shared perspective resolution flow.
- Modify: `frontend/src/routes/LegacyRouteRedirect.tsx`
  Responsibility: Reuse shared perspective-resolution logic instead of owner-first/manual branching.
- Modify: `frontend/src/routes/__tests__/AppRoutes.perspective-redirect.test.tsx`
  Responsibility: Lock shared redirect behavior after resolution refactor.
- Modify: `frontend/src/utils/authz/capabilityEvaluator.ts`
  Responsibility: Remove resource-specific perspective overrides and trust backend capabilities.
- Create: `frontend/src/utils/authz/__tests__/capabilityEvaluator.test.ts`
  Responsibility: Lock direct capability evaluation without local perspective overrides.
- Modify: `frontend/src/hooks/useCapabilities.ts`
  Responsibility: Continue exposing capability checks on top of backend perspectives only.
- Modify: `frontend/src/hooks/__tests__/useCapabilities.test.tsx`
  Responsibility: Lock resource perspective consumption without hardcoded overrides.
- Modify: `frontend/src/routes/AppRoutes.tsx`
  Responsibility: Integrate `PerspectiveResolutionPage` into canonical route failure handling.

### Explicitly out of scope for this plan

- `/ownership/*` route migration.
  Responsibility: Keep it as a documented neutral-business exception until a separate decision is made. Do not silently classify it as owner/manager canonical during implementation.

### Documentation ownership

- Modify: `docs/requirements-specification.md`
  Responsibility: Move `REQ-AUTH-002` from `📋` to `🚧` when implementation starts, then to `✅` only after verification.
- Modify: `docs/plans/README.md`
  Responsibility: Track this plan as the active AUTH-002 plan.
- Modify: `CHANGELOG.md`
  Responsibility: Record design, implementation, and final verification commands.

## Chunk 2: Capability Contract and Request Header

### Task 1: Add backend resource perspective registry and capability tests

**Files:**
- Create: `backend/src/services/authz/resource_perspective_registry.py`
- Create: `backend/tests/unit/services/test_authz_service.py`
- Modify: `backend/src/services/authz/service.py`
- Modify: `backend/src/schemas/authz.py`
- Modify: `backend/src/api/v1/auth/auth_modules/authentication.py`

- [ ] **Step 1: Write the failing capability test**

```python
@pytest.mark.asyncio
async def test_get_capabilities_should_use_resource_perspective_registry():
    service = AuthzService(...)
    result = await service.get_capabilities(db=mock_db, user_id="user-1")

    project_capability = next(item for item in result.capabilities if item.resource == "project")
    assert project_capability.perspectives == ["manager"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest --no-cov tests/unit/services/test_authz_service.py -k resource_perspective_registry -q`
Expected: FAIL because capabilities currently mirror subject owner/manager bindings for every resource.

- [ ] **Step 3: Write minimal implementation**

Implementation requirements:

- Add `resource_perspective_registry.py` with static backend truth for active resources.
- Keep neutral/admin resources as `[]`.
- Update `AuthzService.get_capabilities()` to intersect resource actions with registry-defined perspectives.
- Do not add ABAC schema migrations in this task.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && uv run pytest --no-cov tests/unit/services/test_authz_service.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/src/services/authz/resource_perspective_registry.py \
  backend/src/services/authz/service.py \
  backend/src/schemas/authz.py \
  backend/src/api/v1/auth/auth_modules/authentication.py \
  backend/tests/unit/services/test_authz_service.py
git commit -m "feat(authz): register resource perspective capabilities"
```

### Task 2: Inject route-derived `X-Perspective` in the API client

**Files:**
- Modify: `frontend/src/routes/perspective.ts`
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/api/__tests__/client.test.ts`
- Modify: `frontend/src/services/capabilityService.ts`
- Modify: `frontend/src/services/__tests__/capabilityService.test.ts`

- [ ] **Step 1: Write the failing client test**

```typescript
it('injects X-Perspective for owner business requests and skips auth routes', async () => {
  window.history.pushState({}, 'Test', '/owner/assets');
  // assert request interceptor adds X-Perspective: owner
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && pnpm exec vitest run src/api/__tests__/client.test.ts src/services/__tests__/capabilityService.test.ts --reporter=verbose`
Expected: FAIL because the client currently has no perspective-header injection.

- [ ] **Step 3: Write minimal implementation**

Implementation requirements:

- Expose a non-hook helper in `perspective.ts` for reading the current route perspective from `window.location.pathname`.
- In `client.ts`, inject `X-Perspective` only for business routes.
- Keep `/auth/*`, `/dashboard`, `/profile`, and `/system/*` exempt.
- Do not allow individual service calls to handcraft perspective headers.

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd frontend && pnpm exec vitest run src/api/__tests__/client.test.ts src/services/__tests__/capabilityService.test.ts --reporter=verbose`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/src/routes/perspective.ts \
  frontend/src/api/client.ts \
  frontend/src/api/__tests__/client.test.ts \
  frontend/src/services/capabilityService.ts \
  frontend/src/services/__tests__/capabilityService.test.ts
git commit -m "feat(auth): inject route perspective into business requests"
```

## Chunk 3: Frontend Resolution Before Backend Enforcement

### Task 3: Add shared perspective resolution utilities and canonical-route recovery

**Files:**
- Create: `frontend/src/routes/perspectiveResolution.ts`
- Create: `frontend/src/routes/PerspectiveResolutionPage.tsx`
- Create: `frontend/src/routes/__tests__/perspectiveResolution.test.tsx`
- Modify: `frontend/src/routes/LegacyRouteRedirect.tsx`
- Modify: `frontend/src/routes/AppRoutes.tsx`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/routes/__tests__/AppRoutes.perspective-redirect.test.tsx`
- Modify: `frontend/src/components/System/CapabilityGuard.tsx`
- Modify: `frontend/src/components/System/__tests__/CapabilityGuard.test.tsx`

- [ ] **Step 1: Write the failing route-resolution tests**

```typescript
it('routes invalid /owner/assets/:id sessions to the deterministic manager/detail or list fallback', () => {
  ...
});

it('renders the perspective resolution page when current route perspective is no longer allowed', () => {
  ...
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd frontend && pnpm exec vitest run src/routes/__tests__/AppRoutes.perspective-redirect.test.tsx src/components/System/__tests__/CapabilityGuard.test.tsx --reporter=verbose`
Expected: FAIL because no shared resolution utility/page exists.

- [ ] **Step 3: Write minimal implementation**

Implementation requirements:

- Add deterministic fallback mapping utility.
- Reuse it from `LegacyRouteRedirect`.
- Connect canonical protected-route failures through `App.tsx`, not only static route metadata.
- Add a dedicated resolution page for invalid current perspectives.
- Do not silently continue on create/edit/import routes; send them back to safe list/import landing pages.

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd frontend && pnpm exec vitest run src/routes/__tests__/AppRoutes.perspective-redirect.test.tsx src/routes/__tests__/perspectiveResolution.test.tsx src/components/System/__tests__/CapabilityGuard.test.tsx --reporter=verbose`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/src/routes/perspectiveResolution.ts \
  frontend/src/routes/PerspectiveResolutionPage.tsx \
  frontend/src/routes/__tests__/perspectiveResolution.test.tsx \
  frontend/src/routes/LegacyRouteRedirect.tsx \
  frontend/src/routes/AppRoutes.tsx \
  frontend/src/App.tsx \
  frontend/src/routes/__tests__/AppRoutes.perspective-redirect.test.tsx \
  frontend/src/components/System/CapabilityGuard.tsx \
  frontend/src/components/System/__tests__/CapabilityGuard.test.tsx
git commit -m "feat(auth): add perspective recovery flow"
```

## Chunk 4: Backend Perspective Context and Query Enforcement

### Task 4: Add `PerspectiveContext` middleware/dependency and fail-closed tests

**Files:**
- Create: `backend/tests/unit/middleware/test_perspective_context.py`
- Modify: `backend/src/middleware/auth.py`
- Modify: `backend/src/services/authz/context_builder.py`

- [ ] **Step 1: Write the failing middleware tests**

```python
@pytest.mark.asyncio
async def test_require_perspective_context_should_reject_missing_header_for_business_route():
    ...

@pytest.mark.asyncio
async def test_require_perspective_context_should_allow_neutral_auth_endpoint_without_header():
    ...
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest --no-cov tests/unit/middleware/test_perspective_context.py -q`
Expected: FAIL because `PerspectiveContext` does not exist yet.

- [ ] **Step 3: Write minimal implementation**

Implementation requirements:

- Add a request-level `PerspectiveContext` dataclass/model.
- Parse `X-Perspective` after authentication.
- Resolve allowed perspectives from `SubjectContext` plus resource registry.
- Compute `effective_party_ids` from a single relation only.
- Expose a reusable dependency factory for business routes.

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && uv run pytest --no-cov tests/unit/middleware/test_perspective_context.py tests/unit/middleware/test_authz_dependency.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/src/middleware/auth.py \
  backend/src/services/authz/context_builder.py \
  backend/tests/unit/middleware/test_perspective_context.py \
  backend/tests/unit/middleware/test_authz_dependency.py
git commit -m "feat(auth): add perspective request context"
```

### Task 5: Build perspective-specific `PartyFilter` helpers

**Files:**
- Modify: `backend/src/services/party_scope.py`
- Modify: `backend/src/crud/query_builder.py`
- Modify: `backend/tests/unit/services/test_party_scope.py`
- Modify: `backend/tests/unit/crud/test_query_builder.py`

- [ ] **Step 1: Write the failing party-scope tests**

```python
async def test_build_perspective_party_filter_should_use_owner_ids_only():
    ...

async def test_build_perspective_party_filter_should_use_manager_ids_only():
    ...
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest --no-cov tests/unit/services/test_party_scope.py tests/unit/crud/test_query_builder.py -k perspective -q`
Expected: FAIL because no perspective-specific helper exists yet.

- [ ] **Step 3: Write minimal implementation**

Implementation requirements:

- Add a dedicated helper for converting `PerspectiveContext` into `PartyFilter`.
- Preserve `owner_party_ids` / `manager_party_ids` separately.
- Do not fall back to `party_ids` unions when perspective is explicit.
- Keep legacy default organization fallback only for neutral paths that still require it.

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && uv run pytest --no-cov tests/unit/services/test_party_scope.py tests/unit/crud/test_query_builder.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/src/services/party_scope.py \
  backend/src/crud/query_builder.py \
  backend/tests/unit/services/test_party_scope.py \
  backend/tests/unit/crud/test_query_builder.py
git commit -m "feat(auth): enforce single-perspective party filters"
```

### Task 6: Thread perspective enforcement through active backend business routes

**Files:**
- Modify: `backend/src/api/v1/assets/assets.py`
- Modify: `backend/src/api/v1/assets/project.py`
- Modify: `backend/src/api/v1/contracts/contract_groups.py`
- Modify: `backend/src/services/contract/contract_group_service.py`
- Modify: `backend/src/api/v1/analytics/analytics.py`
- Modify: `backend/tests/unit/api/v1/test_analytics.py`
- Add or modify focused route tests alongside each module as needed

- [ ] **Step 1: Write the failing API contract tests**

```python
def test_asset_list_should_reject_missing_perspective_header(...):
    ...

def test_analytics_should_use_manager_scope_when_header_is_manager(...):
    ...
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && uv run pytest --no-cov tests/unit/api/v1/test_analytics.py tests/unit/api/v1/test_assets_authz_layering.py tests/unit/api/v1/test_project.py -k perspective -q`
Expected: FAIL because active business routes do not yet require the new dependency.

- [ ] **Step 3: Write minimal implementation**

Implementation requirements:

- Add `PerspectiveContext` dependency to active business endpoints only.
- Convert that context into explicit `PartyFilter` values before service calls.
- Start with canonical owner/manager-backed assets, projects, contract groups, and analytics first.
- Do not break neutral business routes before the shared frontend resolution layer from Task 3 is in place.
- Contract groups will require service-layer threading, not only API-layer dependency injection.
- Keep `/auth/*` and pure system monitoring endpoints exempt.
- Keep `/ownership/*` unchanged in this plan except for explicit documentation/comments if needed.

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && uv run pytest --no-cov tests/unit/api/v1/test_analytics.py tests/unit/api/v1/test_project.py tests/unit/api/v1/test_assets_authz_layering.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/src/api/v1/assets/assets.py \
  backend/src/api/v1/assets/project.py \
  backend/src/api/v1/contracts/contract_groups.py \
  backend/src/services/contract/contract_group_service.py \
  backend/src/api/v1/analytics/analytics.py \
  backend/tests/unit/api/v1/test_analytics.py \
  backend/tests/unit/api/v1/test_project.py \
  backend/tests/unit/api/v1/test_assets_authz_layering.py \
  backend/tests/unit/services/contract/test_contract_group_service.py
git commit -m "feat(auth): require perspective context on business APIs"
```

## Chunk 5: Frontend Capability Cleanup After Backend Contract

### Task 7: Remove frontend perspective overrides after backend contract is authoritative

**Files:**
- Create: `frontend/src/utils/authz/__tests__/capabilityEvaluator.test.ts`
- Modify: `frontend/src/utils/authz/capabilityEvaluator.ts`
- Modify: `frontend/src/hooks/useCapabilities.ts`
- Modify: `frontend/src/hooks/__tests__/useCapabilities.test.tsx`

- [ ] **Step 1: Write the failing evaluator test**

```typescript
it('uses backend-provided project perspectives instead of local override tables', () => {
  ...
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && pnpm exec vitest run src/hooks/__tests__/useCapabilities.test.tsx src/utils/authz/__tests__/capabilityEvaluator.test.ts --reporter=verbose`
Expected: FAIL because `PERSPECTIVE_OVERRIDES` still exists.

- [ ] **Step 3: Write minimal implementation**

Implementation requirements:

- Remove `PERSPECTIVE_OVERRIDES`.
- Treat backend `capabilities[].perspectives` as authoritative.
- Preserve admin bypass behavior.

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd frontend && pnpm exec vitest run src/hooks/__tests__/useCapabilities.test.tsx src/utils/authz/__tests__/capabilityEvaluator.test.ts --reporter=verbose`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/src/utils/authz/capabilityEvaluator.ts \
  frontend/src/utils/authz/__tests__/capabilityEvaluator.test.ts \
  frontend/src/hooks/useCapabilities.ts \
  frontend/src/hooks/__tests__/useCapabilities.test.tsx
git commit -m "refactor(auth): trust backend capability perspectives"
```

## Chunk 6: Documentation and Final Verification

### Task 8: Update SSOT and verify end-to-end

**Files:**
- Modify: `docs/requirements-specification.md`
- Modify: `docs/plans/README.md`
- Modify: `CHANGELOG.md`

- [ ] **Step 1: Update requirement state and evidence**

Update:

- `REQ-AUTH-002` status to `🚧` when implementation starts, then `✅` after final verification.
- Add real code evidence paths and test evidence.
- Keep `/ownership/*` explicitly documented as neutral pending separate decision unless that decision is completed in this same batch.

- [ ] **Step 2: Run focused backend verification**

Run:

```bash
cd backend && uv run pytest --no-cov \
  tests/unit/services/test_authz_service.py \
  tests/unit/middleware/test_perspective_context.py \
  tests/unit/services/test_party_scope.py \
  tests/unit/crud/test_query_builder.py \
  tests/unit/services/contract/test_contract_group_service.py \
  tests/unit/api/v1/test_analytics.py \
  tests/unit/api/v1/test_project.py \
  -q
```

Expected: PASS

- [ ] **Step 3: Run focused frontend verification**

Run:

```bash
cd frontend && pnpm exec vitest run \
  src/api/__tests__/client.test.ts \
  src/services/__tests__/capabilityService.test.ts \
  src/hooks/__tests__/useCapabilities.test.tsx \
  src/routes/__tests__/AppRoutes.perspective-redirect.test.tsx \
  src/components/System/__tests__/CapabilityGuard.test.tsx \
  src/routes/__tests__/perspectiveResolution.test.tsx \
  --reporter=verbose
```

Expected: PASS

- [ ] **Step 4: Run project gates**

Run:

```bash
make docs-lint
make check
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add docs/requirements-specification.md docs/plans/README.md CHANGELOG.md
git commit -m "docs(auth): record perspective context rollout"
```

## Risks and Checks

- `/ownership/*` must not be accidentally migrated into owner/manager canonical routing in this plan; if product decides it is owner-only, that requires a separate explicit decision update before implementation.
- The API client must not inject `X-Perspective` on `/auth/*`, `/dashboard`, `/profile`, or `/system/*` fetches.
- Backend fail-closed behavior must not break admin/system-neutral traffic; neutral route and endpoint exemptions need dedicated tests.
- `make check` already contains legacy-retirement gates; any new perspective-resolution utility must not reintroduce raw legacy rental route tokens or stale package references.
