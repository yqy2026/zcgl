# 2026-04-22 CI Format Remediation Plan

## Status

🔄 Active

## Goal

修复 PR `#59` 当前 GitHub Actions `CI Pipeline` 中的两条格式化失败：

- `Backend Lint & Type Check`
- `Frontend Lint & Type Check`

约束：本次只处理格式化门禁，不混入行为修改。

## Evidence

- Backend CI 失败根因：`cd backend && uv run ruff format --check src/`
  - 当前需格式化 `16` 个后端源码文件
- Frontend CI 失败根因：`cd frontend && pnpm format:check`
  - 当前需格式化 `63` 个前端文件

总计 `79` 个文件，超过仓库约定的 `20` 文件阈值，需拆分为更小任务分批执行。

## Execution Chunks

### Chunk 1: Backend format sweep

范围：

- `backend/src/api/v1/auth/data_policies.py`
- `backend/src/api/v1/contracts/ledger.py`
- `backend/src/crud/approval.py`
- `backend/src/crud/contract_group.py`
- `backend/src/middleware/auth.py`
- `backend/src/schemas/search.py`
- `backend/src/security/permissions.py`
- `backend/src/security/rate_limiting.py`
- `backend/src/services/analytics/analytics_export_service.py`
- `backend/src/services/analytics/analytics_service.py`
- `backend/src/services/approval/service.py`
- `backend/src/services/contract/contract_group_service.py`
- `backend/src/services/contract/ledger_compensation_service.py`
- `backend/src/services/contract/ledger_export_service.py`
- `backend/src/services/contract/service_fee_ledger_service.py`
- `backend/src/services/permission/rbac_service.py`

验证：

- `cd backend && uv run ruff format --check src/`
- `cd backend && uv run --frozen --extra dev python -m ruff check <affected files>`

### Chunk 2: Frontend core modules and page components

范围：

- `frontend/src/api/client.ts`
- `frontend/src/api/index.ts`
- `frontend/src/components/Analytics/AnalyticsDashboard.tsx`
- `frontend/src/components/Analytics/Charts.tsx`
- `frontend/src/components/Analytics/Filters/FiltersContext.tsx`
- `frontend/src/components/Asset/AssetDetailInfo.tsx`
- `frontend/src/components/Asset/index.ts`
- `frontend/src/components/Contract/PDFImport/types.ts`
- `frontend/src/components/Forms/Asset/AssetFormContext.tsx`
- `frontend/src/components/Forms/RentContractForm.tsx`
- `frontend/src/components/Layout/AppBreadcrumb.tsx`
- `frontend/src/components/Loading/LoadingProvider.tsx`
- `frontend/src/components/Notification/NotificationCenter.tsx`
- `frontend/src/components/Project/ProjectList.tsx`
- `frontend/src/contexts/AuthContext.tsx`
- `frontend/src/pages/Assets/AssetDetailPage.tsx`
- `frontend/src/pages/Assets/AssetImportPage.tsx`
- `frontend/src/pages/Assets/AssetListPage.tsx`
- `frontend/src/pages/Customer/CustomerDetailPage.tsx`
- `frontend/src/pages/ProfilePage.tsx`

验证：

- `cd frontend && pnpm format:check`
- `cd frontend && pnpm lint`

### Chunk 3: Frontend pages, stores, types, and service modules

范围：

- `frontend/src/pages/Search/GlobalSearchPage.tsx`
- `frontend/src/pages/System/PartyDetailPage.tsx`
- `frontend/src/pages/System/PartyListPage.tsx`
- `frontend/src/pages/System/UserManagement/components/UserTable.tsx`
- `frontend/src/services/asset/assetHistoryService.ts`
- `frontend/src/services/asset/assetImportExportService.ts`
- `frontend/src/services/backupService.ts`
- `frontend/src/services/monitoringService.ts`
- `frontend/src/stores/dataScopeStore.ts`
- `frontend/src/test/utils/handlers-statistics.ts`
- `frontend/src/types/party.ts`

验证：

- `cd frontend && pnpm format:check`
- `cd frontend && pnpm lint`

### Chunk 4A: Frontend component/page test files

范围：

- `frontend/src/api/__tests__/client.test.ts`
- `frontend/src/components/Asset/__tests__/AssetExport.test.tsx`
- `frontend/src/components/Asset/__tests__/AssetImport.test.tsx`
- `frontend/src/components/Contract/PDFImport/__tests__/PDFImportContext.test.tsx`
- `frontend/src/components/Contract/PDFImport/__tests__/PDFUploadArea.test.tsx`
- `frontend/src/components/ErrorHandling/__tests__/ErrorBoundary.test.tsx`
- `frontend/src/components/Forms/RentContract/__tests__/RelationInfoSection.test.tsx`
- `frontend/src/components/Forms/__tests__/OwnershipForm.test.tsx`
- `frontend/src/components/Layout/__tests__/AppBreadcrumb.test.tsx`
- `frontend/src/components/Project/__tests__/ProjectList.test.tsx`
- `frontend/src/config/__tests__/rental-retired-navigation.test.ts`
- `frontend/src/hooks/__tests__/useAssetAnalytics.test.ts`
- `frontend/src/hooks/__tests__/useDictionary.test.ts`
- `frontend/src/pages/Assets/__tests__/AssetDetailPage.test.tsx`
- `frontend/src/pages/Assets/__tests__/AssetListPage.test.tsx`
- `frontend/src/pages/Contract/__tests__/ContractImportReview.confirm-context.test.tsx`

验证：

- `cd frontend && pnpm format:check`
- `cd frontend && pnpm lint`

### Chunk 4B: Frontend remaining test and helper files

范围：

- `frontend/src/pages/Ownership/__tests__/OwnershipDetailPage.legacy-contract-retired.test.tsx`
- `frontend/src/pages/Search/__tests__/GlobalSearchPage.test.tsx`
- `frontend/src/pages/System/__tests__/NotificationCenter.legacy-contract-navigation-retired.test.tsx`
- `frontend/src/pages/System/__tests__/OrganizationPage.test.tsx`
- `frontend/src/pages/System/__tests__/SystemSettingsPage.test.tsx`
- `frontend/src/services/__tests__/analyticsService.test.ts`
- `frontend/src/services/__tests__/contactService.test.ts`
- `frontend/src/services/__tests__/llmPromptService.test.ts`
- `frontend/src/services/__tests__/notificationService.test.ts`
- `frontend/src/services/__tests__/organizationService.test.ts`
- `frontend/src/services/__tests__/propertyCertificateService.test.ts`
- `frontend/src/test/__tests__/browser-api-mocks.test.ts`
- `frontend/src/utils/__tests__/exportAnalytics.test.ts`
- `frontend/src/utils/__tests__/performance.test.ts`
- `frontend/src/utils/__tests__/responseExtractor.test.ts`
- `frontend/src/utils/__tests__/routeCache.test.ts`

验证：

- `cd frontend && pnpm format:check`
- `cd frontend && pnpm test`

## Exit Criteria

1. `cd backend && uv run ruff format --check src/` 通过
2. `cd frontend && pnpm format:check` 通过
3. PR `#59` 的 `Backend Lint & Type Check`、`Frontend Lint & Type Check` 变绿
4. 完成后更新 `CHANGELOG.md`
