# REQ-ANA-001 Export Closure Implementation Plan

## Status

✅ Completed / Archived

## Goal

Close `REQ-ANA-001` by making `/api/v1/analytics/export` the single export authority, returning real CSV/XLSX output with ANA-001 metrics, and routing both frontend analytics entry points through that same backend download path.

## Executed Tasks

### 1. Backend export mapper

- Added `backend/src/services/analytics/analytics_export_service.py`
- Added `backend/tests/unit/services/analytics/test_analytics_export_service.py`

完成内容：

- 固定 ANA-001 导出行顺序
- 统一金额/计数/文本格式化
- 输出真实 CSV 表格文本，而不是 JSON dump

### 2. `/analytics/export` 契约收口

- Updated `backend/src/api/v1/analytics/analytics.py`
- Updated `backend/src/services/excel/excel_export_service.py`
- Updated `backend/tests/unit/api/v1/test_analytics.py`

完成内容：

- CSV 导出改为使用统一导出行
- XLSX 导出改为消费统一导出行
- PDF 导出改为明确返回 `501 Not Implemented`

### 3. Frontend export gateway unification

- Updated `frontend/src/services/analyticsService.ts`
- Updated `frontend/src/services/__tests__/analyticsService.test.ts`
- Updated `frontend/src/hooks/useAssetAnalytics.ts`
- Updated `frontend/src/hooks/__tests__/useAssetAnalytics.test.ts`
- Updated `frontend/src/components/Analytics/AnalyticsDashboard.tsx`
- Updated `frontend/src/components/Analytics/__tests__/AnalyticsDashboard.test.tsx`

完成内容：

- `analyticsService` 现在负责统一发起导出请求与浏览器下载
- `useAssetAnalytics` 不再调用本地 `analyticsExportService`
- `AnalyticsDashboard` 与资产分析页统一走后端下载链路

### 4. SSOT and archive updates

- Updated `docs/requirements-specification.md`
- Updated `docs/plans/README.md`
- Updated `CHANGELOG.md`

完成内容：

- `REQ-ANA-001` 状态改为 `✅`
- 补充本轮新增代码证据与测试证据
- 将本设计和实施计划归档到 `docs/archive/backend-plans/`

## Verification

```bash
cd backend && uv run pytest --no-cov tests/unit/services/analytics/test_analytics_export_service.py tests/unit/api/v1/test_analytics.py -q
cd frontend && pnpm exec vitest run src/services/__tests__/analyticsService.test.ts src/hooks/__tests__/useAssetAnalytics.test.ts src/components/Analytics/__tests__/AnalyticsDashboard.test.tsx --reporter=verbose
make docs-lint
```

## Notes

- 本轮没有实现真正的 PDF 导出。
- 本轮没有改动 ANA-001 经营口径算法，只收口导出链路与前端调用路径。
