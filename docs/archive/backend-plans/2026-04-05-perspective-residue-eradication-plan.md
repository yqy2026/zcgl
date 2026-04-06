# Perspective Residue Eradication Plan

> **Status**: ✅ Completed
> **Completed**: 2026-04-05
> **Parent REQ**: REQ-AUTH-002 / REQ-SCH-003

---

## Goal

彻底清理代码、测试和活跃文档中仍与数据范围模型冲突的“视角（perspective）”残留，统一区分：

- 请求缩窄语义：`scope_mode`
- 主体绑定语义：`binding_type`
- 能力集协议兼容面：保留 `X-Perspective` 与 `capabilities[].perspectives`

## Completed Scope

### Backend

- `PerspectiveContext` / `PerspectiveContextChecker` / `require_perspective_context()` 重命名为 `DataScopeContext` / `DataScopeContextChecker` / `require_data_scope_context()`。
- `build_party_filter_from_perspective_context()` 重命名为 `build_party_filter_from_scope_context()`。
- `BindingType` / `ScopeMode` 进入 `backend/src/schemas/authz.py`，请求上下文与服务层语义不再混用 `perspective`。
- `search/service.py` 改为 `scope_mode` 语义，并补齐 `all` 模式下的 union 范围过滤。
- `party/service.py` 与 `contract_group_service.py` 改为 `binding_type` 语义。

### Frontend

- 删除 `frontend/src/routes/AppRoutes.tsx` 中 `/owner/*`、`/manager/*` 的 legacy 业务路由入口。
- `frontend/src/hooks/useSmartPreload.tsx` 改为 canonical flat routes（`/assets/list` 等）。
- `frontend/src/components/Common/PartySelector.tsx` 不再从 URL 前缀推断 owner/manager 默认过滤模式。
- 大批测试夹具改为 `scope:` query token 与 flat routes。

### Docs

- `docs/architecture/auth-rbac-analysis.md` 同步改为 `DataScopeContextChecker` / `require_data_scope_context()` 表述。
- `CHANGELOG.md` 已记录本轮 residue eradication 的实现与验证证据。

## Explicitly Preserved

- `X-Perspective` 请求头：仍作为兼容协议面保留。
- `capabilities[].perspectives`：仍作为能力集协议字段保留。

## Verification Evidence

- `cd backend && uv run python -m pytest --no-cov tests/unit/middleware/test_perspective_context.py tests/unit/middleware/test_perspective_context_optional.py tests/unit/services/test_party_scope.py tests/unit/crud/test_query_builder.py tests/unit/services/search/test_search_service.py tests/unit/services/test_party_service.py tests/unit/services/contract/test_contract_group_service.py tests/unit/api/v1/test_search_api.py tests/unit/api/v1/test_party_api.py tests/unit/api/v1/test_contract_groups_layering.py tests/unit/api/v1/test_assets_authz_layering.py -q` → `151 passed, 19 skipped`
- `cd frontend && pnpm exec vitest run src/hooks/__tests__/useSmartPreload.test.tsx src/components/Common/__tests__/PartySelector.test.tsx src/routes/__tests__/AppRoutes.legacy-rental-retired.test.tsx src/hooks/__tests__/useAnalytics.test.ts src/hooks/__tests__/useAssets.test.ts src/hooks/__tests__/useProject.test.ts src/pages/Assets/__tests__/AssetAnalyticsPage.export.test.tsx src/pages/Assets/__tests__/AssetCreatePage.test.tsx src/pages/Assets/__tests__/AssetDetailPage.test.tsx src/pages/Assets/__tests__/AssetListPage.test.tsx src/pages/PropertyCertificate/__tests__/PropertyCertificateDetailPage.test.tsx src/pages/Dashboard/components/__tests__/QuickActions.test.tsx src/components/Layout/__tests__/AppHeader.test.tsx src/components/Layout/__tests__/AppBreadcrumb.test.tsx src/config/__tests__/menuConfig.perspective-grouping.test.tsx src/config/__tests__/rental-retired-navigation.test.ts src/components/System/__tests__/CapabilityGuard.test.tsx src/components/Project/__tests__/ProjectList.test.tsx --reporter=dot` → `18 files, 169 passed`

## Follow-up Notes

- 归档历史方案与历史问题记录中仍会出现 `PerspectiveContext`、"当前视角" 等旧词，这些属于历史证据，不再主动清洗。
- `TEST_DATABASE_URL` 相关的 db-backed unit tests 仍按 fixture 约定跳过，不计为失败。
