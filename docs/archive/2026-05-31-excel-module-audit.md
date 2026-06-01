# Excel 模块审计报告

## 结论

不建议在第一轮瘦身中把 Excel 服务强行合并为 import/export 两个文件。

当前 `excel_import_service.py` 约 557 行，`excel_export_service.py` 约 374 行，已经是模块内最大的两个文件。继续把 preview、template、task、config、status 塞入这两个文件，会降低局部性，不能证明复杂度下降。

## 审计范围

| 文件 | 行数 | 主要职责 | 判断 |
|---|---:|---|---|
| `backend/src/services/excel/excel_import_service.py` | 557 | 资产 Excel 导入、字段映射、校验、查重、预览 | 保留独立服务 |
| `backend/src/services/excel/excel_export_service.py` | 374 | 资产导出、分析导出、导出文件、导出预览、列宽 | 保留独立服务，后续只做内部拆小 |
| `backend/src/services/excel/excel_template_service.py` | 88 | 资产导入模板生成 | 保留，用户可理解的独立流程节点 |
| `backend/src/services/excel/excel_preview_service.py` | 70 | 上传文件预览构建 | 保留，避免和导入执行耦合 |
| `backend/src/services/excel/excel_config_service.py` | 83 | Excel 任务配置 CRUD 委托 | 可后续评估是否并入任务配置服务，但不并入 import/export |
| `backend/src/services/excel/excel_status_service.py` | 106 | Excel 异步任务状态和历史 | 保留，和任务生命周期相关 |
| `backend/src/services/excel/excel_task_service.py` | 67 | Excel 异步任务创建、读取、更新和失败标记 | 保留，供 import/export 异步路由复用 |

## 调用关系

| 服务 | 主要调用方 |
|---|---|
| `ExcelImportService` | `api/v1/documents/excel/import_ops.py` |
| `ExcelExportService` | `api/v1/documents/excel/export_ops.py`、`api/v1/analytics/analytics.py`、`services/contract/ledger_export_service.py` |
| `ExcelTemplateService` | `api/v1/documents/excel/template.py` |
| `ExcelPreviewService` | `api/v1/documents/excel/preview.py` |
| `ExcelConfigService` | `api/v1/documents/excel/config.py` |
| `ExcelStatusService` | `api/v1/documents/excel/status.py` |
| `ExcelTaskService` | `api/v1/documents/excel/import_ops.py`、`api/v1/documents/excel/export_ops.py` |

## 决策

第一轮不合并 Excel 服务文件。后续如继续治理，应按以下顺序做小步改造：

1. 把 `excel_export_service.py` 内的导出格式化、数据获取、文件落盘拆成私有 helper 或子服务，先降低单文件复杂度。
2. 审计 `ExcelConfigService` 是否应归属通用 task config 服务，而不是 import/export。
3. 保留 template、preview、status、task 的用户流程语义，不为减少文件数合并。
4. 每次改动先补对应服务测试或 API layering 测试，再改实现。

## 验证依据

- 文件规模：`excel_import_service.py` 557 行，`excel_export_service.py` 374 行，其他服务 67-106 行。
- API 路由按 template/config/preview/import/export/status 分文件注册，服务边界与当前路由边界一致。
- 现有单测覆盖 import、export、template、task 以及 Excel API 分层测试；合并会扩大测试失败定位面。
