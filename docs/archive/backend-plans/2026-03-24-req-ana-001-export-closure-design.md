# REQ-ANA-001 导出链路收口设计

## 状态

✅ 已完成（2026-03-25）

## 背景

`REQ-ANA-001` 当前仍处于 `🚧` 状态，经营口径字段已经进入综合分析结果，但导出链路仍存在两套真值：

1. `AssetAnalyticsPage` 通过前端 `analyticsExportService` 本地拼装 Excel/CSV。
2. `AnalyticsDashboard` 通过后端 `/api/v1/analytics/export` 下载文件。

这导致三个直接问题：

- 导出契约不一致，两个入口的字段、标题、文件内容可能继续漂移。
- 后端 `csv` 导出当前并不是真正的表格文本，而是把 JSON 文本伪装成 `text/csv`。
- `REQ-ANA-001` 的“支持结果导出并标记统计口径版本”虽然部分可见，但未在统一导出链路上形成闭环。

## 目标

本轮只完成 `REQ-ANA-001` 的导出链路收口，不重做经营口径计算本身。

收口后应满足：

- 后端 `/api/v1/analytics/export` 成为唯一导出真值。
- `AssetAnalyticsPage` 与 `AnalyticsDashboard` 使用同一条后端下载链路。
- `csv` 与 `excel` 导出使用同一份结构化导出数据。
- 导出结果必须稳定包含 `REQ-ANA-001` 经营口径字段与 `metrics_version`。

## 非目标

本轮明确不做以下事项：

- 不修改 `AnalyticsService` 中 `REQ-ANA-001` 的收入/客户统计口径。
- 不实现真正的 PDF 导出，仅保留“暂未实现”的明确返回。
- 不重做分析页面 UI 布局或统计卡片展示。
- 不清理或删除历史 `analyticsExportService` 文件，只让它退出 `REQ-ANA-001` 主链路。

## 选择方案

采用“后端导出单真值”方案：

- 保留 `/api/v1/analytics/export` 作为唯一导出入口。
- 在后端新增一个轻量导出 helper/service，把综合分析结果转换为统一的导出载荷。
- `csv` 与 `excel` 都基于同一份导出载荷生成，避免字段顺序、中文标题、经营口径字段存在性不一致。
- 前端两个分析入口都复用 `analyticsService.exportAnalyticsReport()` 发起下载，不再各自生成文件。

不采用“保留双链路”方案，因为它会继续制造字段漂移。

不采用“全部改前端本地导出”方案，因为导出契约无法由后端统一冻结，也更容易在大结果集与权限口径上继续分叉。

## 设计细节

### 1. 后端导出结构

后端仍保留 [analytics.py](/home/y/projects/zcgl/backend/src/api/v1/analytics/analytics.py) 的 `/api/v1/analytics/export` 路由，但把“如何组织导出内容”的职责下沉到单独 helper/service。

统一导出载荷至少覆盖以下块：

- 概览统计
- 经营口径指标
- 主要分布数据
- 口径版本

`REQ-ANA-001` 必须稳定导出的字段：

- `total_income`
- `self_operated_rent_income`
- `agency_service_income`
- `customer_entity_count`
- `customer_contract_count`
- `metrics_version`

CSV 导出要求：

- 返回真正的表格文本，而不是 JSON 字符串。
- 中文标题与字段顺序固定，便于测试锁定与业务侧核对。

Excel 导出要求：

- 与 CSV 共享同一份结构化导出数据，不允许单独维护第二套 ANA-001 字段映射。

PDF 导出要求：

- 继续返回“暂未实现”，不伪装成功。

### 2. 前端导出链路

前端统一以 [analyticsService.ts](/home/y/projects/zcgl/frontend/src/services/analyticsService.ts) 为唯一导出入口。

调整方向：

- [useAssetAnalytics.ts](/home/y/projects/zcgl/frontend/src/hooks/useAssetAnalytics.ts) 不再自己组装 `exportData` 并调用本地 `analyticsExportService`。
- [AnalyticsDashboard.tsx](/home/y/projects/zcgl/frontend/src/components/Analytics/AnalyticsDashboard.tsx) 保持走后端导出，但抽出与资产分析页一致的下载逻辑。
- 资产分析页与 dashboard 使用一致的文件名规则、成功/失败提示与筛选参数透传方式。

历史 [analyticsExportService.ts](/home/y/projects/zcgl/frontend/src/services/analyticsExportService.ts) 本轮先保留，不作为 `REQ-ANA-001` 主链路。

### 3. API 形状与边界

本轮不修改分析 API 的筛选参数形状：

- 继续使用现有 `date_from` / `date_to`
- 不引入新的 year-month 参数

边界约束：

- 缺失 `metrics_version` 时导出空字符串，不报错。
- `export_format=pdf` 明确返回错误响应。
- 若后端导出失败，前端统一展示导出失败提示，不回退到本地导出。

## TDD 与验证

### 后端

先在 [test_analytics.py](/home/y/projects/zcgl/backend/tests/unit/api/v1/test_analytics.py) 写失败用例，锁定：

- `csv` 返回可读表格文本，而非 JSON。
- CSV 中出现 `总收入（经营口径）`、`自营租金收入`、`代理服务费收入`、`客户主体数`、`客户合同数`、`口径版本`。
- `metrics_version` 的值实际出现在导出文件中。
- `pdf` 仍返回“暂未实现”。

若新增后端导出 helper/service，再补对应 unit test，单独锁定字段映射与顺序。

### 前端

先改测试，再改实现，锁定：

- 资产分析页导出不再调用本地 `exportAnalyticsData`。
- 资产分析页与 dashboard 最终都调用 `analyticsService.exportAnalyticsReport()`。
- 下载成功与失败提示保持一致。

## 影响文件

后端预计涉及：

- `backend/src/api/v1/analytics/analytics.py`
- `backend/src/services/analytics/` 下新增或调整导出 helper/service
- `backend/tests/unit/api/v1/test_analytics.py`
- 可能新增 `backend/tests/unit/services/analytics/` 导出映射测试

前端预计涉及：

- `frontend/src/hooks/useAssetAnalytics.ts`
- `frontend/src/components/Analytics/AnalyticsDashboard.tsx`
- `frontend/src/services/analyticsService.ts`
- `frontend/src/hooks/__tests__/useAssetAnalytics.test.ts`
- 可能补充 dashboard 或相关下载链路测试

文档预计涉及：

- `docs/requirements-specification.md`
- `docs/plans/README.md`
- `CHANGELOG.md`

## 完成定义

当以下条件同时满足时，本设计对应的实现任务可以视为完成：

- `REQ-ANA-001` 的“导出并标记口径版本”在后端统一导出链路上闭环。
- 分析页两个入口导出行为一致。
- 相关单测通过。
- 文档状态和 `CHANGELOG.md` 已同步更新。
