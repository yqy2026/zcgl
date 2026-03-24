# REQ-ANA-001 导出链路收口设计

## 状态

✅ 已完成 / 已归档

## 背景

`REQ-ANA-001` 在本轮收口前存在两套导出真值：

1. `AssetAnalyticsPage` 通过前端 `analyticsExportService` 本地拼装 Excel/CSV。
2. `AnalyticsDashboard` 通过后端 `/api/v1/analytics/export` 下载文件。

同时，后端 `csv` 导出实际上返回的是 JSON 文本伪装成 `text/csv`，无法满足“支持结果导出并标记统计口径版本”的稳定契约。

## 收口目标

- 后端 `/api/v1/analytics/export` 成为唯一导出真值。
- 资产分析页与 dashboard 统一走后端下载链路。
- CSV 与 XLSX 复用同一份结构化导出映射。
- `REQ-ANA-001` 的经营口径字段与 `metrics_version` 在导出结果中稳定可见。

## 设计结论

采用“后端导出单真值”方案：

- 新增 `backend/src/services/analytics/analytics_export_service.py`，负责把综合分析结果转换成统一的导出行。
- `backend/src/api/v1/analytics/analytics.py` 的 `/api/v1/analytics/export` 统一使用这份导出行生成 CSV/XLSX。
- `backend/src/services/excel/excel_export_service.py` 改为接受结构化导出行，避免 Excel 和 CSV 维护两套映射。
- 前端 `frontend/src/services/analyticsService.ts` 新增统一下载入口，`useAssetAnalytics` 与 `AnalyticsDashboard` 都只调它。

## 本轮非目标

- 不修改 `AnalyticsService` 中 ANA-001 的收入/客户统计口径。
- 不实现真正的 PDF 导出；该分支明确返回 `501 Not Implemented`。
- 不重做分析页面 UI。
- 不删除旧的 `analyticsExportService` 文件，只让它退出 ANA-001 主链路。

## 结果

本设计已按 TDD 落地，并由下列验证支撑：

- `cd backend && uv run pytest --no-cov tests/unit/services/analytics/test_analytics_export_service.py tests/unit/api/v1/test_analytics.py -q`
- `cd frontend && pnpm exec vitest run src/services/__tests__/analyticsService.test.ts src/hooks/__tests__/useAssetAnalytics.test.ts src/components/Analytics/__tests__/AnalyticsDashboard.test.tsx --reporter=verbose`
- `make docs-lint`
