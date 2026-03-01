# Phase 3e Exit 验收证据（2026-03-01）

## 元信息
- 日期：`2026-03-01`
- 责任人：`codex`
- release-id：`phase3e-exit-20260301`
- 范围：`P3e Excel 适配 + 旧字段前端主链收口 + 权限遗留壳处置验收`

## 结论
- `P3e Exit`：`Pass`
- 说明：P3c/P3d 前置均已完成；前端主运行链旧字段清零；`usePermission`/`Router` 已物理删除；`PermissionGuard` 以 `@deprecated` 兼容壳保留且主路由零引用；Excel 导入链路补齐旧模板友好提示。

## Entry 前置复核
1. 前置阶段已完成
- `docs/plans/execution/phase3c-exit-readiness-20260228.md`
- `docs/plans/execution/phase3d-exit-readiness-20260228.md`

2. Excel 路径前置
- `frontend/src/services/rentContractExcelService.ts` 使用 `'/rental-contracts'` 相对路径，未命中 `'/api/rental'` / `'/api/v1/rental-contracts'`
- 已确认复用统一 `apiClient`

## Exit 门禁证据
1. 旧字段类型定义移除（例外文件除外）
- 命令：`rg -n -w "organization_id|ownership_id|ownership_ids|management_entity|ownership_entity" frontend/src/types --glob '*.ts' --glob '!frontend/src/types/organization.ts' --glob '!frontend/src/types/ownership.ts'`
- 结果：`PASS（无命中）`

2. 产权证类型旧字段移除
- 命令：`rg -n -w "organization_id" frontend/src/types/propertyCertificate.ts`
- 结果：`PASS（无命中）`

3. Excel 服务链旧字段清零
- 命令：`rg -n -w "organization_id|ownership_id|ownership_ids|management_entity|ownership_entity" frontend/src/services/excelService.ts frontend/src/services/rentContractExcelService.ts frontend/src/services/asset/assetImportExportService.ts`
- 结果：`PASS（无命中）`

4. Excel 旧模板导入友好提示
- 代码：`frontend/src/services/rentContractExcelService.ts` 新增 `LEGACY_TEMPLATE_HINT = "系统已升级，请下载最新模板后重试"`
- 测试：`frontend/src/services/__tests__/rentContractExcelService.test.ts` 新增 `throws upgrade hint when import fails due to legacy template fields`
- 结果：`PASS（4 passed）`

5. 权限遗留壳处置
- `usePermission` 物理删除：
  - `frontend/src/hooks/usePermission.tsx`（deleted）
  - `frontend/src/hooks/__tests__/usePermission.test.tsx`（deleted）
- Router 物理删除：
  - `frontend/src/components/Router/*`（deleted）
- `PermissionGuard` 兼容壳策略（B）：
  - 文件保留并标记 `@deprecated`
  - 主生效链 `frontend/src/App.tsx` + `frontend/src/routes/AppRoutes.tsx` 无 `PermissionGuard` 引用

6. 运行时主链旧字段复核（P3e 口径）
- 命令（排除测试与非主链目录后）：
  - `rg -n -w "organization_id|ownership_id|ownership_ids|management_entity|ownership_entity" frontend/src ...`
- 结果：`PASS（无命中）`

## 验证记录
- `pnpm --dir frontend exec vitest run src/services/__tests__/rentContractExcelService.test.ts`（`4 passed`）
- `pnpm -C frontend type-check`（PASS）
- `pnpm -C frontend check`（PASS）
- `pnpm -C frontend build`（PASS）
- `pnpm -C frontend test`（PASS，存在历史 warning 日志但命令退出码为 0）

## 残余风险与后续
- 构建阶段仍有既有 `circular chunk` / `chunk size` 警告，未阻断本次 Exit；建议在后续性能专项中处理 chunk 切分策略。
- 非主链残留（测试辅助与文档样例）仍可能出现旧字段字面量，不计入本阶段阻断，后续作为技术债跟踪。

## 本批次变更文件
- `frontend/src/services/rentContractExcelService.ts`
- `frontend/src/services/__tests__/rentContractExcelService.test.ts`
- `docs/plans/execution/phase3e-exit-readiness-20260301.md`
