# Phase 3e Entry 就绪证据（2026-02-28）

## 元信息
- 日期：`2026-02-28`
- 责任人：`codex`
- release-id：`phase3e-entry-20260228`
- 范围：`P3e Entry hard gates + Excel path correction`

## 结论
- `P3e Entry`：`Pass（可开工）`
- 说明：P3c/P3d Exit 前置满足；`rentContractExcelService` 旧路径已切换为版本化 `/rental-contracts`；租户主体收紧前置 SQL 检查满足放行条件。

## Entry 门禁证据

1. 前置阶段门禁
- `P3c Exit`：`docs/plans/execution/phase3c-exit-readiness-20260228.md`
- `P3d Exit`：`docs/plans/execution/phase3d-exit-readiness-20260228.md`

2. Excel 路径门禁（P3e Entry）
- 代码修复：`frontend/src/services/rentContractExcelService.ts` 将 `baseUrl` 从 `'/api/rental'` 改为 `'/rental-contracts'`
- 门禁命令：
  - `! rg -n "['\"]/api/rental['\"]|['\"]/api/v1/rental-contracts['\"]" frontend/src/services/rentContractExcelService.ts`（PASS）
  - `rg -n "['\"]/rental-contracts['\"]" frontend/src/services/rentContractExcelService.ts`（命中 `baseUrl`）
  - `rg -n "from '@/api/client'|from \"@/api/client\"" frontend/src/services/rentContractExcelService.ts`（PASS）

3. 旧路径探针记录（联调）
- `GET /api/v1/api/rental/excel/template` → `404`
- `GET /api/v1/rental-contracts/excel/template` → `401`（鉴权拦截，符合预期路由存在性）

4. `tenant_party_id` 收紧前置量化检查
- 执行方式：读取 `backend/.env` 的 `DATABASE_URL`，通过 `backend/.venv` + SQLAlchemy 执行 SQL
- 结果：
  - `null_count = 0`
  - `total_count = 0`
  - `null_ratio = 0.0%`
- 判定：满足 `null_count=0` 放行条件。

5. `mocks` 口径确认
- `frontend/src/mocks/fixtures.ts` 仍命中 `ownership_entity`（仅 MSW 开发/测试链）
- 处置：保留，后续在 P3e Exit 报告中继续列为“非主运行链审计项”。

6. `PERMISSIONS/PAGE_PERMISSIONS` 与 `PermissionGuard` 调用链盘点（非阻断清单）
- Entry 初始扫描命中 `PermissionGuard + Router` 链路；Batch 1 已按 `A` 路径物理删除 Router，并删除 `usePermission`。
- 当前生产命中仅剩：
  - `frontend/src/services/systemService.ts`（`SYSTEM_API.PERMISSIONS` / `ROLE_PERMISSIONS`，API 常量名，不属于权限判定逻辑）
- `PermissionGuard` 当前状态：
  - 保留为 `@deprecated` 兼容组件（`frontend/src/components/System/PermissionGuard.tsx`）
  - 已移除 `PERMISSIONS/usePermission` 依赖，后续可按 P3e Exit 策略继续处理（保留或删除）。

## 本批次验证
### Entry + Batch 1
- `cd frontend && pnpm vitest run src/services/__tests__/rentContractExcelService.test.ts`（3 passed）
- `cd frontend && pnpm check`（PASS）

## 执行进展（Batch 1）
- 已按 P3e 默认 `A` 路径物理删除遗留 Router 体系：`frontend/src/components/Router/*`（含对应测试文件）。
- 已从统一导出中移除 `Router` 命名空间：`frontend/src/components/index.ts`。
- 已物理删除 `usePermission` 兼容壳及其测试：
  - `frontend/src/hooks/usePermission.tsx`
  - `frontend/src/hooks/__tests__/usePermission.test.tsx`
- `PermissionGuard` 保留为 `@deprecated` 兼容组件，但已去除对 `PERMISSIONS/usePermission` 的依赖，避免阻塞 P3e 收口。

## 执行进展（Batch 2）
- 运行时主链旧字段清理（`ownership_* / management_entity / ownership_entity`）：
  - 资产链路：`components/Asset/*`、`pages/Assets/components/AssetCard.tsx`、`hooks/useProject.ts`
  - 合同链路：`components/Forms/RentContract/RentContractFormContext.tsx`、`pages/Contract/ContractImportReview.tsx`、`components/Rental/ContractDetailInfo.tsx`、`pages/Rental/*`
  - 分析与图表：`components/Analytics/Filters/FiltersSection.tsx`、`components/Charts/*`
  - 项目与权属页面：`components/Project/ProjectList.tsx`、`pages/Ownership/OwnershipDetailPage.tsx`
- 类型层收口：`frontend/src/types/{asset,project,rentContract,pdfImport,propertyCertificate}.ts` 移除主链旧字段定义，统一收敛到 `owner_party_* / manager_party_*` 口径。
- 测试与夹具同步：`Asset*`/`ProjectList`/`AssetForm`/`ContractImportReview` 相关用例、`mocks/fixtures.ts`、`test-utils/factories/assetFactory.ts` 完成字段迁移。

### Batch 2 验证（2026-03-01 复核）
- 旧字段主链 grep（排除测试与非主链目录）：
  - `rg -n -w "organization_id|ownership_id|ownership_ids|management_entity|ownership_entity" frontend/src ...`（PASS，exit=1，无命中）
- `pnpm -C frontend type-check`（PASS）
- `pnpm -C frontend type-check:e2e`（PASS）
- `pnpm --dir frontend exec vitest run src/services/__tests__/rentContractExcelService.test.ts src/components/Asset/__tests__/AssetSearch.test.tsx src/components/Asset/__tests__/AssetCard.test.tsx src/components/Asset/__tests__/AssetDetailInfo.test.tsx src/components/Asset/__tests__/AssetList.test.tsx src/components/Forms/__tests__/AssetForm.test.tsx src/components/Project/__tests__/ProjectList.test.tsx src/pages/Contract/__tests__/ContractImportReview.owner-reference.test.ts`（8 files, 178 passed）
- `pnpm -C frontend check`（PASS）
- `pnpm -C frontend build`（PASS；保留既有 circular chunk / chunk size warning，不阻断）

## 剩余范围（Batch 2 后）
- P3e 旧字段清理主目标已达成：按计划口径，`components/pages/services/hooks/types` 主运行链无旧字段命中。
- 非主链残留仅见于测试辅助与文档样例（`frontend/src/test/utils/*`、`frontend/src/services/README.md`），不在 P3e 主门禁范围；后续可在 Exit 文档中作为技术债单列。

## 本批次变更文件（Entry + Batch 1 + Batch 2）
- `frontend/src/services/rentContractExcelService.ts`
- `frontend/src/services/__tests__/rentContractExcelService.test.ts`
- `frontend/src/components/index.ts`
- `frontend/src/components/System/PermissionGuard.tsx`
- `frontend/src/hooks/usePermission.tsx`（deleted）
- `frontend/src/hooks/__tests__/usePermission.test.tsx`（deleted）
- `frontend/src/components/Router/*`（deleted）
- `frontend/src/components/Asset/*`
- `frontend/src/components/Analytics/Filters/FiltersSection.tsx`
- `frontend/src/components/Charts/*`
- `frontend/src/components/Forms/{AssetForm.tsx,RentContract/RentContractFormContext.tsx}`
- `frontend/src/components/Project/ProjectList.tsx`
- `frontend/src/components/Rental/ContractDetailInfo.tsx`
- `frontend/src/pages/{Assets,Contract,Ownership,Rental}/*`
- `frontend/src/hooks/useProject.ts`
- `frontend/src/types/{asset.ts,project.ts,rentContract.ts,pdfImport.ts,propertyCertificate.ts}`
- `frontend/src/mocks/fixtures.ts`
- `frontend/src/test-utils/factories/assetFactory.ts`
- `docs/plans/execution/phase3e-entry-readiness-20260228.md`
