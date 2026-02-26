# Phase 2 交接 TODO（2026-02-20）

> 目标：方便在新窗口继续执行 `docs/plans/2026-02-19-phase2-implementation-plan.md`。

## 0. 最新状态快照（2026-02-21 13:20）

- 当前执行焦点：Phase 2 维护模式（Gate 防漂移 + 回归稳态抽样）。
- assets 模块状态：`assets/project/property_certificate/asset_batch/asset_attachments/asset_import/custom_fields/ownership/occupancy` 已完成 ABAC 接入；`assets/assets.py`、`asset_batch.py`、`asset_import.py`、`property_certificate.py` 已清理遗留 `require_permission(...)` 依赖。
- analytics 模块状态：`analytics.py` 业务端点（`comprehensive/cache-stats/cache-clear/trend/distribution/export`）、`statistics_modules` 的 `financial_stats/basic_stats/area_stats/distribution/occupancy_stats/trend_stats` 以及聚合包装路由 `statistics.py` 已完成 ABAC 接入。
- rent_contracts 模块状态：`contracts/attachments/terms/ledger/statistics/excel_ops/lifecycle` 已完成 ABAC 接入。
- documents 模块状态：`pdf_batch_routes`（含 health）、`pdf_import_routes`（兼容路由）、`excel/import_ops`、`excel/template`、`excel/status`、`excel/preview`、`excel/export_ops`、`excel/config`、`pdf_upload`、`pdf_system`、`pdf_import`（包装路由）已完成 ABAC 接入。
- system 模块状态：`tasks.py` 的任务主端点（`create/list/detail/update/cancel/delete/history/statistics/running/recent/cleanup`）与 Excel 配置端点（`create/list/default/detail/update/delete`）已完成 ABAC 接入。
- system 模块状态：`history.py` 的历史记录端点（`list/detail/delete`）已完成 ABAC 接入。
- system 模块状态：`collection.py` 的催缴管理端点（`summary/list/detail/create/update/delete`）已完成 ABAC 接入。
- system 模块状态：`contact.py` 的联系人管理端点（`create/detail/entity-list/primary/update/delete/batch-create`）已完成 ABAC 接入。
- system 模块状态：`dictionaries.py` 的统一字典端点（`options/quick-create/types/validation-stats/add-value/delete-type`）已完成 ABAC 接入。
- system 模块状态：`notifications.py` 的通知端点（`list/unread-count/read/read-all/delete/run-tasks`）已完成 ABAC 接入。
- system 模块状态：`operation_logs.py` 的操作日志端点（`list/detail/statistics/export/cleanup`）已完成 ABAC 接入。
- system 模块状态：`enum_field.py` 的枚举字段端点（`types/values/tree/usage/history`，排除 debug）已完成 ABAC 接入。
- system 模块状态：`backup.py` 的数据备份端点（`create/list/download/restore/delete/stats/validate/cleanup`）已完成 ABAC 接入。
- system 模块状态：`system.py` 的系统核心端点（`monitoring/health/system/info/system/root`）已完成 ABAC 接入。
- system 模块状态：`error_recovery.py` 的错误恢复端点（`statistics/strategies/update/circuit-breakers/reset/history/test/clear`）已完成 ABAC 接入，并清理遗留 `require_permission(...)` 依赖。
- system 模块状态：`monitoring.py` 的系统监控端点（`route-performance/system-health/performance/dashboard/system-metrics/application-metrics/dashboard/metrics/collect`）已完成 ABAC 接入。
- system 模块状态：`system_settings.py` 的系统设置端点（`security/alerts/test/security/events/settings/info/backup/restore`）已完成 ABAC 接入。
- system 模块状态：`system_monitoring/*` 子模块（`endpoints/database_endpoints`）已完成 ABAC 接入，并修复子模块相对导入层级。
- party 模块状态：`party.py` 主体管理端点（主体 CRUD / 层级 / 联系人）已完成 ABAC 接入。
- llm_prompts 模块状态：`llm_prompts.py` 的模板管理端点（`create/list/detail/update/activate/rollback/versions/statistics/feedback`）已完成 ABAC 接入。
- auth 模块状态：`roles.py` 的角色与统一授权端点（`roles CRUD/assignments/users/permission-grants/permissions/statistics`）已完成 ABAC 接入。
- auth 模块状态：`organization.py` 的组织管理端点（`list/tree/search/statistics/detail/children/path/history/create/update/delete/move/batch/advanced-search`）已完成 ABAC 接入。
- auth 模块状态：`auth_modules/sessions.py` 的会话端点（`list/revoke`）已完成 ABAC 接入。
- auth 模块状态：`auth_modules/audit.py` 的审计统计端点（`logs`）已完成 ABAC 接入。
- auth 模块状态：`auth_modules/security.py` 的安全配置端点（`config`）已完成 ABAC 接入。
- auth 模块状态：`auth_modules/users.py` 的用户管理端点（`CRUD/状态管理/密码管理/统计`）已完成 ABAC 接入。
- 最新完成批次：assets 遗留链路（`assets.py`、`asset_batch.py`、`asset_import.py`、`property_certificate.py`）已清理 `require_permission(...)` 并统一为 `get_current_active_user + require_authz(...)`，完成定向分层与 API 回归。
- 最新完成批次：回归稳态修复（`tests/integration/test_asset_lifecycle.py` 登录夹具新增组织可见范围缓存失效；`tests/unit/services/test_rent_contract_service.py` 断言同步 `owner_party_id` 透传参数）并完成扩展回归。
- 最新完成批次：维护复核（P2d + Gate）已复跑，结果与第 2.63 节一致（见第 2.64 节）。
- 最新完成批次：鉴权/组织可见范围抽样回归已完成（见第 2.65 节），关键链路 `authz dependency + organization + project visibility + asset lifecycle` 通过。
- 最新完成批次：鉴权链路扩展抽样回归已完成（见第 2.66 节），关键链路 `auth routes layering + authz cache/events + project tenant scope` 通过。
- 最新完成批次：扩大回归复跑已完成（见第 2.67 节），`not slow and not e2e` 基线保持通过。
- 最新完成批次：Gate + 迁移 + 角色作用域复核已完成（见第 2.68 节），`BG-1/2/3/4` 与 `roles.scope` 继续保持零漂移。
- 最新完成批次：跨模块抽样回归（documents + analytics + rent_contract）已完成（见第 2.69 节），关键链路保持稳定。
- 最新完成批次：system/auth 抽样回归已完成（见第 2.70 节），系统与鉴权路由分层链路保持稳定。
- 最新完成批次：authz+project 可见范围抽样复核完成（见第 2.71 节通过项）；`asset_lifecycle` 在该批次暴露的 `422` 风险已在第 2.72 节闭环修复并复核通过。
- 最新完成批次：跨模块抽样回归（`pdf_import + statistics + rent_contract + system_settings + roles + project visibility + asset_lifecycle`）已完成（见第 2.73 节），回归继续稳定。
- 最新完成批次：扩大回归复跑（`not slow and not e2e`）已完成（见第 2.74 节），基线继续稳定。
- 最新完成批次：Gate + 迁移 + 角色作用域复核已完成（见第 2.75 节），`BG-1/2/3/4` 与 `roles.scope` 保持零漂移。
- 最新完成批次：扩大回归复跑（`not slow and not e2e`）+ Gate 同步已完成（见第 2.77 节），基线与 Gate 继续保持稳定。
- 最新完成批次：跨模块抽样回归 + Gate 同步已完成（见第 2.78 节），鉴权与可见范围链路继续稳定。
- 最新完成批次：扩大回归复跑 + Gate 同步已完成（见第 2.79 节），回归基线继续稳定。
- 最新完成批次：跨模块抽样回归 + Gate/作用域复核已完成（见第 2.82 节），`todo.md` 待完成项已清零。
- 最新完成批次：鉴权/组织可见范围抽样回归 + Gate 同步已完成（见第 2.83 节），关键链路继续稳定。
- 最新完成批次：扩大回归复跑 + Gate 同步已完成（见第 2.84 节），基线继续稳定。
- 最新完成批次：Gate + 迁移 + 角色作用域复核已完成（见第 2.85 节），`BG-1/2/3/4` 与 `roles.scope` 继续保持零漂移。
- 最新完成批次：鉴权/组织可见范围抽样回归 + Gate 同步已完成（见第 2.86 节），关键链路继续稳定。
- 最新完成批次：扩大回归复跑 + Gate 同步已完成（见第 2.87 节），基线继续稳定（`4537 passed`）。
- 最新完成批次：Gate + 迁移 + 角色作用域复核已完成（见第 2.88 节），`BG-1/2/3/4` 与 `roles.scope` 继续保持零漂移。
- 最新完成批次：鉴权/组织可见范围抽样回归 + Gate 同步已完成（见第 2.89 节），关键链路继续稳定（`32 passed`）。
- 最新完成批次：扩大回归复跑 + Gate 同步已完成（见第 2.90 节），基线继续稳定（`4537 passed`）。
- 最新完成批次：Gate + 迁移 + 角色作用域复核已完成（见第 2.91 节），`BG-1/2/3/4` 与 `roles.scope` 继续保持零漂移。
- 最新完成批次：鉴权/组织可见范围抽样回归 + Gate 同步已完成（见第 2.92 节），关键链路继续稳定（`32 passed`）。
- 最新完成批次：扩大回归复跑 + Gate 同步已完成（见第 2.93 节），基线继续稳定（`4538 passed`）。
- 最新完成批次：Gate + 迁移 + 角色作用域复核已完成（见第 2.94 节），`BG-1/2/3/4` 与 `roles.scope` 继续保持零漂移。
- 最新完成批次：鉴权/组织可见范围抽样回归 + Gate 同步已完成（见第 2.95 节），关键链路继续稳定（`32 passed`）。
- 最新完成批次：扩大回归复跑 + Gate 同步已完成（见第 2.96 节），基线继续稳定（`4538 passed`）。
- 最新完成批次：鉴权/组织可见范围抽样回归 + Gate 同步已完成（见第 2.97 节），关键链路继续稳定（`32 passed`）。
- 最新完成批次：扩大回归复跑 + Gate 同步已完成（见第 2.98 节），基线继续稳定（`4541 passed`）。
- 最新完成批次：鉴权/组织可见范围抽样回归 + Gate 同步已完成（见第 2.99 节），关键链路继续稳定（`32 passed`）。
- 最新完成批次：扩大回归复跑 + Gate 同步已完成（见第 2.100 节），基线继续稳定（`4543 passed`）。
- 最新完成批次：鉴权/组织可见范围抽样回归 + Gate 同步已完成（见第 2.101 节），关键链路继续稳定（`34 passed`）。
- 最新完成批次：扩大回归复跑 + Gate 同步已完成（见第 2.102 节），基线继续稳定（`4543 passed`）。
- 最新完成批次：鉴权/组织可见范围抽样回归 + Gate 同步已完成（见第 2.103 节），关键链路继续稳定（`34 passed`）。
- 最新完成批次：扩大回归复跑 + Gate 同步已完成（见第 2.104 节），基线继续稳定（`4543 passed`）。
- 最新完成批次：鉴权/组织可见范围抽样回归 + Gate 同步已完成（见第 2.105 节），关键链路继续稳定（`34 passed`）。
- 最新完成批次：扩大回归复跑 + Gate 同步已完成（见第 2.106 节），基线继续稳定（`4545 passed`）。
- 最新完成批次：鉴权/组织可见范围抽样回归 + Gate 同步已完成（见第 2.107 节），关键链路继续稳定（`34 passed`）。
- Gate 状态：`BG-1/2/3/4` 已全量复核通过（见第 2.63/2.64/2.66/2.68/2.69/2.70/2.71/2.72/2.73/2.74/2.75/2.77/2.78/2.79/2.80/2.81/2.82/2.83/2.84/2.85/2.86/2.87/2.88/2.89/2.90/2.91/2.92/2.93/2.94/2.95/2.96/2.97/2.98/2.99/2.100/2.101/2.102/2.103/2.104/2.105/2.106/2.107 节），`roles.scope` 非法值计数 `0`，迁移工具单测 `tests/unit/migration/test_backfill.py` 已通过。

### 0.1 新窗口三步启动

1. 执行 Gate 盘点命令（见第 4 节第 1 步），确认仍为 0。
2. 从第 2.107 节继续做维护复核（Gate + 鉴权链路抽样回归）。
3. 每批按第 4 节第 3/4 步执行：`ruff + pytest` 后更新 `CHANGELOG.md` 与本文件。

### 0.2 当前窗口已完成（便于新窗口直接接力）

- 已完成 assets 遗留权限依赖清理：
  - `backend/src/api/v1/assets/assets.py`
  - `backend/src/api/v1/assets/asset_batch.py`
  - `backend/src/api/v1/assets/asset_import.py`
  - `backend/src/api/v1/assets/property_certificate.py`
  - 清理项：移除路由层 `require_permission(...)`，统一为 `get_current_active_user + require_authz(...)`
- 已扩展对应分层约束测试（防止旧依赖回流）：
  - `backend/tests/unit/api/v1/test_assets_authz_layering.py`
  - `backend/tests/unit/api/v1/test_asset_batch_layering.py`
  - `backend/tests/unit/api/v1/test_asset_import_layering.py`
  - `backend/tests/unit/api/v1/test_property_certificate_authz_layering.py`
- 当前批验证结果：
  - `ruff check`（定向）通过
  - `pytest --no-cov`（定向）`64 passed`
- 已完成错误恢复模块遗留权限依赖清理：
  - `backend/src/api/v1/system/error_recovery.py`
  - 清理项：移除路由层 `require_permission("system:error_recovery", "...")`，统一为 `get_current_active_user + require_authz(...)`
- 已扩展对应分层约束测试（防止旧依赖回流）：
  - `backend/tests/unit/api/v1/test_error_recovery_layering.py`
- 当前批验证结果：
  - `ruff check`（定向）通过
  - `pytest --no-cov`（定向）`49 passed`
- 已完成遗留权限依赖清理（Excel 配置兼容链路）：
  - `backend/src/api/v1/documents/excel/config.py`
  - `backend/src/api/v1/system/tasks.py`
  - 清理项：移除路由层 `require_permission(...)`，统一为 `get_current_active_user + require_authz(...)`
- 已扩展对应分层约束测试（防止旧依赖回流）：
  - `backend/tests/unit/api/v1/test_excel_config_layering.py`
  - `backend/tests/unit/api/v1/test_tasks_layering.py`
- 当前批验证结果：
  - `ruff check`（定向）通过
  - `pytest --no-cov`（定向）`60 passed`
- 已完成任务模块 Excel 配置端点 ABAC 接入（`create/list/default/detail/update/delete`）：
  - `backend/src/api/v1/system/tasks.py`
- 已完成对应测试补齐：
  - layering：`backend/tests/unit/api/v1/test_tasks_layering.py`
  - 既有任务配置回归：`backend/tests/unit/api/v1/test_tasks.py`（`excel_config` 相关用例）
- 当前批验证结果：
  - `ruff check`（定向）通过
  - `pytest --no-cov`（定向）`19 passed`
- 已完成统计子模块剩余端点 ABAC 接入（`basic/area/distribution/occupancy/trend`）：
  - `backend/src/api/v1/analytics/statistics_modules/basic_stats.py`
  - `backend/src/api/v1/analytics/statistics_modules/area_stats.py`
  - `backend/src/api/v1/analytics/statistics_modules/distribution.py`
  - `backend/src/api/v1/analytics/statistics_modules/occupancy_stats.py`
  - `backend/src/api/v1/analytics/statistics_modules/trend_stats.py`
- 已完成对应测试补齐：
  - layering：`test_basic_stats_layering.py`、`test_area_stats_layering.py`、`test_distribution_layering.py`、`test_occupancy_stats_layering.py`、`test_trend_stats_layering.py`
  - TestClient 鉴权隔离：`test_basic_stats.py`、`test_area_stats.py`、`test_occupancy_stats.py`
- 当前批验证结果：
  - `ruff check`（定向）通过
  - `pytest --no-cov`（定向）`48 passed`
- 已完成主体管理路由 ABAC 接入（主体 CRUD / 层级 / 联系人）：
  - `backend/src/api/v1/party.py`
- 已新增对应分层约束测试：
  - `backend/tests/unit/api/v1/test_party_layering.py`
- 当前批验证结果：
  - `ruff check`（定向）通过
  - `pytest --no-cov`（定向）`7 passed`
- 已完成任务主端点 ABAC 接入（任务 CRUD / 历史 / 统计 / 运行中 / 最近 / 清理）：
  - `backend/src/api/v1/system/tasks.py`
- 已扩展对应分层约束测试：
  - `backend/tests/unit/api/v1/test_tasks_layering.py`
- 当前批验证结果：
  - `ruff check`（定向）通过
  - `pytest --no-cov`（定向）`56 passed`
- 已完成历史记录路由 ABAC 接入（历史记录列表 / 详情 / 删除）：
  - `backend/src/api/v1/system/history.py`
- 已扩展对应分层约束测试：
  - `backend/tests/unit/api/v1/test_history_layering.py`
- 当前批验证结果：
  - `ruff check`（定向）通过
  - `pytest --no-cov`（定向）`5 passed, 4 skipped`
- 已完成催缴管理路由 ABAC 接入（汇总 / 列表 / 详情 / 创建 / 更新 / 删除）：
  - `backend/src/api/v1/system/collection.py`
- 已新增对应分层约束测试：
  - `backend/tests/unit/api/v1/test_collection_layering.py`
- 当前批验证结果：
  - `ruff check`（定向）通过
  - `pytest --no-cov`（定向）`30 passed`
- 已完成联系人管理路由 ABAC 接入（创建 / 详情 / 实体列表 / 主要联系人 / 更新 / 删除 / 批量创建）：
  - `backend/src/api/v1/system/contact.py`
- 已扩展对应分层约束测试：
  - `backend/tests/unit/api/v1/test_contact_layering.py`
- 当前批验证结果：
  - `ruff check`（定向）通过
  - `pytest --no-cov`（定向）`4 passed, 28 skipped`
- 已完成统一字典路由 ABAC 接入（选项 / 快速创建 / 类型 / 验证统计 / 新增值 / 删除类型）：
  - `backend/src/api/v1/system/dictionaries.py`
- 已扩展对应分层约束测试：
  - `backend/tests/unit/api/v1/test_dictionaries_layering.py`
- 当前批验证结果：
  - `ruff check`（定向）通过
  - `pytest --no-cov`（定向）`5 passed, 8 skipped`（`test_dictionaries.py` 受 `TEST_DATABASE_URL` 缺失影响按预期跳过）
- 已完成通知路由 ABAC 接入（列表 / 未读数 / 标记已读 / 全部已读 / 删除 / 手动触发任务）：
  - `backend/src/api/v1/system/notifications.py`
- 已新增对应分层约束测试：
  - `backend/tests/unit/api/v1/test_notifications_layering.py`
- 当前批验证结果：
  - `ruff check`（定向）通过
  - `pytest --no-cov`（定向）`8 passed, 19 skipped`（`test_notifications.py` 受 `TEST_DATABASE_URL` 认证失败影响按预期跳过 db-backed 用例）
- 已完成操作日志路由 ABAC 接入（列表 / 详情 / 统计 / 导出 / 清理）：
  - `backend/src/api/v1/system/operation_logs.py`
- 已扩展对应分层约束测试：
  - `backend/tests/unit/api/v1/test_operation_logs_layering.py`
- 当前批验证结果：
  - `ruff check`（定向）通过
  - `pytest --no-cov`（定向）`8 passed, 4 skipped`（`test_operation_logs.py` 受 `TEST_DATABASE_URL` 缺失影响按预期跳过 db-backed 用例）
- 已完成枚举字段路由 ABAC 接入（`types/values/tree/usage/history`，排除 debug 端点）：
  - `backend/src/api/v1/system/enum_field.py`
- 已扩展对应分层约束测试：
  - `backend/tests/unit/api/v1/test_enum_field_layering.py`
- 当前批验证结果：
  - `ruff check`（定向）通过
  - `pytest --no-cov`（定向）`14 passed`
- 已完成数据备份路由 ABAC 接入（创建 / 列表 / 下载 / 恢复 / 删除 / 统计 / 校验 / 清理）：
  - `backend/src/api/v1/system/backup.py`
- 已新增对应分层约束测试：
  - `backend/tests/unit/api/v1/test_backup_layering.py`
- 当前批验证结果：
  - `ruff check`（定向）通过
  - `pytest --no-cov`（定向）`40 passed`
- 已完成系统核心路由 ABAC 接入（健康检查 / 系统信息 / API 根路径）：
  - `backend/src/api/v1/system/system.py`
- 已新增对应分层约束测试：
  - `backend/tests/unit/api/v1/test_system_layering.py`
- 当前批验证结果：
  - `ruff check`（定向）通过
  - `pytest --no-cov`（定向）`5 passed`（`test_system_layering.py + test_authz_dependency.py`）
- 已完成 LLM Prompt 路由 ABAC 接入（模板管理 / 版本 / 统计 / 反馈）：
  - `backend/src/api/v1/llm_prompts.py`
  - 覆盖端点：`POST /`、`GET /`、`GET /{prompt_id}`、`PUT /{prompt_id}`、`POST /{prompt_id}/activate`、`POST /{prompt_id}/rollback`、`GET /{prompt_id}/versions`、`GET /statistics/overview`、`POST /feedback`
- 已新增对应分层约束测试：
  - `backend/tests/unit/api/v1/test_llm_prompts_layering.py`
- 当前批验证结果：
  - `ruff check`（定向）通过
  - `pytest --no-cov`（定向）`5 passed`（`test_llm_prompts_layering.py + test_authz_dependency.py`）
  - 说明：`tests/unit/api/v1/test_llm_prompts.py` 在当前测试库环境执行会触发 Alembic 初始化冲突（`organizations already exists`），与本批 ABAC 依赖注入改动无关。
- 已完成错误恢复路由 ABAC 接入（统计 / 策略 / 熔断器 / 历史 / 测试 / 清理）：
  - `backend/src/api/v1/system/error_recovery.py`
  - 覆盖端点：`GET /statistics`、`GET /strategies`、`PUT /strategies/{category}`、`GET /circuit-breakers`、`POST /circuit-breakers/{category}/reset`、`GET /history`、`POST /test`、`DELETE /history/clear`
- 已新增对应分层约束测试：
  - `backend/tests/unit/api/v1/test_error_recovery_layering.py`
- 当前批验证结果：
  - `ruff check`（定向）通过
  - `pytest --no-cov`（定向）`49 passed`（`test_error_recovery_layering.py + test_error_recovery.py + test_authz_dependency.py`）
- 已完成系统监控路由 ABAC 接入（性能上报 / 健康检查 / 仪表板 / 指标查询 / 手动采集）：
  - `backend/src/api/v1/system/monitoring.py`
  - 覆盖端点：`POST /route-performance`、`GET /system-health`、`GET /performance/dashboard`、`GET /system-metrics`、`GET /application-metrics`、`GET /dashboard`、`POST /metrics/collect`
- 已新增对应分层约束测试：
  - `backend/tests/unit/api/v1/test_monitoring_layering.py`
- 当前批验证结果：
  - `ruff check`（定向）通过
  - `pytest --no-cov`（定向）`30 passed`（`test_monitoring_layering.py + test_monitoring.py + test_authz_dependency.py`）
- 已完成系统设置路由 ABAC 接入（安全事件 / 设置管理 / 系统信息 / 备份恢复）：
  - `backend/src/api/v1/system/system_settings.py`
  - 覆盖端点：`POST /security/alerts/test`、`GET /security/events`、`GET /settings`、`PUT /settings`、`GET /info`、`POST /backup`、`POST /restore`
- 已扩展对应分层约束测试：
  - `backend/tests/unit/api/v1/test_system_settings_layering.py`
- 当前批验证结果：
  - `ruff check`（定向）通过
  - `pytest --no-cov`（定向）`17 passed`（`test_system_settings_layering.py + test_system_settings.py + test_authz_dependency.py`）
- 已完成角色管理路由 ABAC 接入（角色 CRUD / 授权记录 / 用户角色 / 统计）：
  - `backend/src/api/v1/auth/roles.py`
  - 覆盖端点：`GET|POST /roles`、`POST /roles/permission-check`、`POST /roles/assignments`、`GET /roles/users/{user_id}/roles`、`DELETE /roles/users/{user_id}/roles/{role_id}`、`GET /roles/users/{user_id}/permissions/summary`、`POST|GET /roles/permission-grants`、`GET|PATCH|DELETE /roles/permission-grants/{grant_id}`、`GET|PUT|DELETE /roles/{role_id}`、`GET /roles/permissions/list`、`PUT /roles/{role_id}/permissions`、`GET /roles/{role_id}/users`、`GET /roles/statistics/summary`
- 已新增对应分层约束测试：
  - `backend/tests/unit/api/v1/test_roles_layering.py`
- 当前批验证结果：
  - `ruff check`（定向）通过
  - `pytest --no-cov`（定向）`23 passed`（`test_roles_layering.py + test_roles.py + test_roles_permission_grants.py + test_authz_dependency.py`）
- 已完成组织管理路由 ABAC 接入（组织查询 / 树形 / 统计 / CRUD / 移动 / 批量）：
  - `backend/src/api/v1/auth/organization.py`
  - 覆盖端点：`GET /organizations`、`GET /organizations/tree`、`GET /organizations/search`、`GET /organizations/statistics`、`GET /organizations/{org_id}`、`GET /organizations/{org_id}/children`、`GET /organizations/{org_id}/path`、`GET /organizations/{org_id}/history`、`POST /organizations`、`PUT /organizations/{org_id}`、`DELETE /organizations/{org_id}`、`POST /organizations/{org_id}/move`、`POST /organizations/batch`、`POST /organizations/advanced-search`
- 已新增对应分层约束测试：
  - `backend/tests/unit/api/v1/test_organization_layering.py`
- 当前批验证结果：
  - `ruff check`（定向）通过
  - `pytest --no-cov`（定向）`24 passed`（`test_organization_layering.py + test_organization.py + test_authz_dependency.py`）
- 已完成会话管理路由 ABAC 接入（会话列表 / 撤销）：
  - `backend/src/api/v1/auth/auth_modules/sessions.py`
  - 覆盖端点：`GET /sessions`、`DELETE /sessions/{session_id}`
- 已扩展对应分层约束测试：
  - `backend/tests/unit/api/v1/test_auth_sessions_layering.py`
- 当前批验证结果：
  - `ruff check`（定向）通过
  - `pytest --no-cov`（定向）`8 passed`（`test_auth_sessions_layering.py + test_authz_dependency.py`）
- 已完成审计日志路由 ABAC 接入（审计统计）：
  - `backend/src/api/v1/auth/auth_modules/audit.py`
  - 覆盖端点：`GET /audit/logs`
- 已扩展对应分层约束测试：
  - `backend/tests/unit/api/v1/test_auth_audit_layering.py`
- 当前批验证结果：
  - `ruff check`（定向）通过
  - `pytest --no-cov`（定向）`7 passed`（`test_auth_audit_layering.py + test_authz_dependency.py`）
- 已完成安全配置路由 ABAC 接入（安全配置查询）：
  - `backend/src/api/v1/auth/auth_modules/security.py`
  - 覆盖端点：`GET /security/config`
- 已新增对应分层约束测试：
  - `backend/tests/unit/api/v1/test_auth_security_layering.py`
- 当前批验证结果：
  - `ruff check`（定向）通过
  - `pytest --no-cov`（定向）`6 passed`（`test_auth_security_layering.py + test_authz_dependency.py`）
- 已完成用户管理路由 ABAC 接入（用户 CRUD / 状态管理 / 密码管理 / 统计）：
  - `backend/src/api/v1/auth/auth_modules/users.py`
  - 覆盖端点：`GET /users`、`GET /users/search`、`POST /users`、`GET /users/{user_id}`、`PUT /users/{user_id}`、`POST /users/{user_id}/change-password`、`POST /users/{user_id}/deactivate`、`DELETE /users/{user_id}`、`POST /users/{user_id}/activate`、`POST /users/{user_id}/lock`、`POST /users/{user_id}/unlock`、`POST /users/{user_id}/reset-password`、`GET /users/statistics/summary`
- 已扩展对应分层约束测试：
  - `backend/tests/unit/api/v1/test_users_layering.py`
- 当前批验证结果：
  - `ruff check`（定向）通过
  - `pytest --no-cov`（定向）`30 passed`（`test_users_layering.py + test_users.py + test_authz_dependency.py`）
- 已完成 `system_monitoring/*` 子模块 ABAC 接入（监控与数据库监控端点）：
  - `backend/src/api/v1/system/system_monitoring/endpoints.py`
  - `backend/src/api/v1/system/system_monitoring/database_endpoints.py`
  - `backend/src/api/v1/system/system_monitoring/collectors.py`
  - `backend/src/api/v1/system/system_monitoring/health.py`
- 已新增对应分层约束测试：
  - `backend/tests/unit/api/v1/test_system_monitoring_layering.py`
- 当前批验证结果：
  - `ruff check`（定向）通过
  - `pytest --no-cov`（定向）`21 passed`（`test_system_monitoring_layering.py + system_monitoring/test_health.py + test_authz_dependency.py`）
- 已完成统计聚合包装路由 ABAC 接入（`analytics/statistics.py`）：
  - `backend/src/api/v1/analytics/statistics.py`
  - 覆盖路由：`basic_stats/distribution/occupancy/area/financial/trend` 子路由挂载依赖
- 已新增对应分层约束测试：
  - `backend/tests/unit/api/v1/test_statistics_router_layering.py`
- 当前批验证结果：
  - `ruff check`（定向）通过
  - `pytest --no-cov`（定向）`17 passed`（`test_statistics_router_layering.py + test_statistics.py + analytics/test_statistics.py`）
- 已完成 PDF 导入包装路由 ABAC 接入（`documents/pdf_import.py`）：
  - `backend/src/api/v1/documents/pdf_import.py`
  - 覆盖挂载：`pdf_upload`（create）、`pdf_system`（read）、可选 `pdf_sessions`（read）
- 已新增对应分层约束测试：
  - `backend/tests/unit/api/v1/test_pdf_import_layering.py`
- 当前批验证结果：
  - `ruff check`（定向）通过
  - `pytest --no-cov`（定向）`13 passed`（`test_pdf_import_layering.py + documents/test_pdf_import_routes.py`）
- 新窗口建议起手（按顺序）：
  1. 先执行第 4 节 Gate 盘点命令（BG-3/BG-4）。
  2. 继续挑一个“尚未接入 require_authz 的业务 API 模块”做单批改造。
  3. 每批仅跑定向 `ruff + pytest`，通过后更新 `CHANGELOG.md` 和本文件。

## 1. 当前进展（已完成）

### 1.1 P2d（缓存/事件/策略包/迁移工具）
- 已完成 ABAC 缓存与事件基础设施：
  - `backend/src/services/authz/cache.py`
  - `backend/src/services/authz/events.py`
  - `backend/src/services/authz/service.py`（判定缓存接入）
  - `backend/src/services/authz/__init__.py`（单例装配）
- 已完成角色策略包持久化服务与 API：
  - `backend/src/services/authz/data_policy_service.py`
  - `backend/src/api/v1/auth/data_policies.py`
- 已完成 RBAC 侧用户角色变更事件发布：
  - `backend/src/services/permission/rbac_service.py`
- 已新增 seed 迁移：
  - `backend/alembic/versions/20260219_phase2_seed_data_policy_packages.py`
- 已完成迁移脚本骨架到可执行实现：
  - `backend/src/scripts/migration/party_migration/*.py`
- 已新增对应单测：
  - `backend/tests/unit/services/test_authz_cache.py`
  - `backend/tests/unit/services/test_authz_events.py`
  - `backend/tests/unit/migration/test_backfill.py`

### 1.2 P2c（ABAC 统一依赖接入）
- 已新增统一鉴权依赖 `require_authz(...)`：
  - `backend/src/middleware/auth.py`
  - 包含 `AuthzContext`、`AuthzPermissionChecker`
  - 支持：
    - `resource_id="{asset_id}"` 路径模板解析
    - 请求体上下文字段抽取（owner/manager/tenant/party/...）
    - `deny_as_not_found=True`（读场景 404）
    - 默认 fail-closed（拒绝 403）
- 已接入关键 CRUD 端点：
  - 资产：`backend/src/api/v1/assets/assets.py`
  - 项目：`backend/src/api/v1/assets/project.py`
  - 合同：`backend/src/api/v1/rent_contracts/contracts.py`
- 合同 API 已移除旧内联权限守卫：
  - `can_edit_contract`
  - `RBACService.is_admin`
- 单测基线已适配：
  - `backend/tests/unit/conftest.py` 增加 `AuthzPermissionChecker` 覆盖
  - 新增 `backend/tests/unit/middleware/test_authz_dependency.py`
  - 更新 `backend/tests/unit/api/v1/test_rent_contract_api.py` 的旧权限链路断言

### 1.3 P2d（数据策略包测试补齐）
- 已新增 `DataPolicyService` 持久化读写与异常路径单测：
  - `backend/tests/unit/services/test_data_policy_service.py`
  - 覆盖：模板读取、角色包读取排序/去重、角色不存在、策略包写入去重、未知包编码、seed 缺失异常
- 已新增 `api/v1/auth/data_policies.py` 路由处理单测：
  - `backend/tests/unit/api/v1/test_data_policies.py`
  - 覆盖：`GET/PUT /roles/{role_id}/data-policies` 成功与异常包装、`GET /data-policies/templates`

### 1.4 P2c（ABAC 覆盖扩展：产权证批次）
- 已为产权证关键 create/read/update/delete 端点接入统一 ABAC 依赖 `require_authz(...)`：
  - `backend/src/api/v1/assets/property_certificate.py`
  - 覆盖端点：`/upload`、`/confirm-import`、`/{certificate_id}`（GET/PUT/DELETE）、`/`（POST）
  - 约束：详情读取使用 `deny_as_not_found=True`，资源类型统一为 `property_certificate`
- 已新增分层约束测试：
  - `backend/tests/unit/api/v1/test_property_certificate_authz_layering.py`
  - 覆盖：模块引入 `AuthzContext/require_authz`、关键端点 ABAC 依赖注入

### 1.5 P2c（ABAC 覆盖扩展：资产批量批次）
- 已为资产批量关键写端点接入统一 ABAC 依赖 `require_authz(...)`：
  - `backend/src/api/v1/assets/asset_batch.py`
  - 覆盖端点：`/batch-update`、`/batch-custom-fields`、`/batch-delete`
  - 约束：资源类型统一为 `asset`，写动作映射 `update/delete`
- 已扩展分层约束测试：
  - `backend/tests/unit/api/v1/test_asset_batch_layering.py`
  - 覆盖：模块引入 `AuthzContext/require_authz`、关键写端点 ABAC 依赖注入

### 1.6 P2c（ABAC 覆盖扩展：合同附件/条款批次）
- 已为合同附件关键端点接入统一 ABAC 依赖 `require_authz(...)`：
  - `backend/src/api/v1/rent_contracts/attachments.py`
  - 覆盖端点：`POST /{contract_id}/attachments`、`GET /{contract_id}/attachments`、`GET /{contract_id}/attachments/{attachment_id}/download`、`DELETE /{contract_id}/attachments/{attachment_id}`
  - 约束：资源类型统一为 `rent_contract`，资源 ID 统一映射 `"{contract_id}"`，读操作使用 `deny_as_not_found=True`
- 已为合同条款关键端点接入统一 ABAC 依赖 `require_authz(...)`：
  - `backend/src/api/v1/rent_contracts/terms.py`
  - 覆盖端点：`GET /contracts/{contract_id}/terms`、`POST /contracts/{contract_id}/terms`
  - 约束：读取动作映射为 `read`（`deny_as_not_found=True`），新增条款动作映射为 `update`
- 已扩展分层约束测试：
  - `backend/tests/unit/api/v1/test_rent_contract_attachments_layering.py`
  - `backend/tests/unit/api/v1/test_rent_contract_terms_layering.py`
  - 覆盖：模块引入 `AuthzContext/require_authz`、关键端点 ABAC 依赖注入、既有服务层委托断言保持通过

### 1.7 P2c（ABAC 覆盖扩展：合同台账/统计批次）
- 已为合同台账关键读写端点接入统一 ABAC 依赖 `require_authz(...)`：
  - `backend/src/api/v1/rent_contracts/ledger.py`
  - 覆盖端点：`/contracts/{contract_id}/deposit-ledger`、`/contracts/{contract_id}/service-fee-ledger`、`/ledger/generate`、`/ledger`、`/ledger/{ledger_id}`、`/ledger/batch`、`/ledger/{ledger_id}`（PUT）、`/contracts/{contract_id}/ledger`
  - 约束：资源类型统一为 `rent_contract`；合同维度读取统一映射 `resource_id="{contract_id}"` 且使用 `deny_as_not_found=True`；台账列表/详情与写端点统一动作映射 `read/create/update`
- 已为租金统计端点接入统一 ABAC 依赖 `require_authz(...)`：
  - `backend/src/api/v1/rent_contracts/statistics.py`
  - 覆盖端点：`/statistics/overview`、`/statistics/ownership`、`/statistics/asset`、`/statistics/monthly`、`/statistics/export`
  - 约束：动作统一映射为 `read`，资源类型统一为 `rent_contract`
- 已扩展分层约束测试：
  - `backend/tests/unit/api/v1/test_rent_contract_ledger_layering.py`
  - `backend/tests/unit/api/v1/test_rent_contract_statistics_layering.py`
  - 覆盖：模块引入 `AuthzContext/require_authz`、关键端点 ABAC 依赖注入、既有服务层委托断言保持通过

### 1.8 P2c（回归与 Gate 收口批次）
- 已完成 `rent_contract_api` 测试基线适配（修复既有 4 个失败）：
  - `backend/tests/unit/api/v1/test_rent_contract_api.py`
  - 修复点：
    - 直接调用路由函数时，为 `owner_party_id(s)` / `asset_ids` / `start_month` / `end_month` 等 `Query(...)` 默认参数显式传 `None`，避免测试态传入 `Query` 对象
    - 合同/台账 mock 对象补齐 `owner_party_id`、`manager_party_id`、`tenant_party_id` 字段，避免 Pydantic 在 `model_validate` 时读取 `MagicMock` 伪值触发校验错误
- 已完成 Gate 盘点确认：
  - `BG-3` 非 `DEPRECATED` 运行时命中：`0`
  - `BG-4` 非 `DEPRECATED` 运行时命中：`0`
- 已完成 rent_contract 扩展分层回归：
  - 合同/附件/条款/台账/统计 layering + `authz_dependency` 一并通过

### 1.9 P2c（ABAC 覆盖扩展：合同 Excel/生命周期批次）
- 已为合同 Excel 关键端点接入统一 ABAC 依赖 `require_authz(...)`：
  - `backend/src/api/v1/rent_contracts/excel_ops.py`
  - 覆盖端点：`/excel/template`、`/excel/import`、`/excel/export`
  - 约束：资源类型统一为 `rent_contract`，动作映射分别为 `read/create/read`
- 已为合同生命周期关键端点接入统一 ABAC 依赖 `require_authz(...)`：
  - `backend/src/api/v1/rent_contracts/lifecycle.py`
  - 覆盖端点：`/contracts/{contract_id}/renew`、`/contracts/{contract_id}/terminate`
  - 约束：动作统一映射为 `update`，资源类型统一为 `rent_contract`，资源 ID 映射 `"{contract_id}"`
- 已扩展分层约束测试：
  - `backend/tests/unit/api/v1/test_rent_contract_excel_ops_layering.py`
  - `backend/tests/unit/api/v1/test_rent_contract_lifecycle_layering.py`
  - 覆盖：模块引入 `AuthzContext/require_authz`、关键端点 ABAC 依赖注入、既有服务层委托断言保持通过

### 1.10 P2c（ABAC 覆盖扩展：合同列表读取批次）
- 已为合同列表读取端点接入统一 ABAC 依赖 `require_authz(...)`：
  - `backend/src/api/v1/rent_contracts/contracts.py`
  - 覆盖端点：`GET /contracts`、`GET /assets/{asset_id}/contracts`
  - 约束：动作统一映射为 `read`，资源类型统一为 `rent_contract`
- 已扩展分层约束测试：
  - `backend/tests/unit/api/v1/test_rent_contract_contracts_layering.py`
  - 覆盖：模块引入 `AuthzContext/require_authz`、合同列表与资产合同列表端点 ABAC 依赖注入、既有服务层委托断言保持通过

### 1.11 P2c（ABAC 覆盖扩展：资产附件批次）
- 已为资产附件关键端点接入统一 ABAC 依赖 `require_authz(...)`：
  - `backend/src/api/v1/assets/asset_attachments.py`
  - 覆盖端点：`POST /{asset_id}/attachments`、`GET /{asset_id}/attachments`、`GET /{asset_id}/attachments/{filename}`、`DELETE /{asset_id}/attachments/{attachment_id}`
  - 约束：资源类型统一为 `asset`，资源 ID 统一映射 `"{asset_id}"`，读取端点使用 `deny_as_not_found=True`
- 已扩展分层约束测试：
  - `backend/tests/unit/api/v1/test_asset_attachments_layering.py`
  - 覆盖：模块引入 `AuthzContext/require_authz`、4 个关键端点 ABAC 依赖注入、既有服务委托断言保持通过

### 1.12 P2c（ABAC 覆盖扩展：资产导入批次）
- 已为资产导入关键端点接入统一 ABAC 依赖 `require_authz(...)`：
  - `backend/src/api/v1/assets/asset_import.py`
  - 覆盖端点：`POST /import`
  - 约束：动作映射为 `create`，资源类型统一为 `asset`
- 已扩展分层约束测试：
  - `backend/tests/unit/api/v1/test_asset_import_layering.py`
  - 覆盖：模块引入 `AuthzContext/require_authz`、导入端点 ABAC 依赖注入、既有服务委托断言保持通过

### 1.13 P2c（ABAC 覆盖扩展：自定义字段批次）
- 已为自定义字段关键端点接入统一 ABAC 依赖 `require_authz(...)`：
  - `backend/src/api/v1/assets/custom_fields.py`
  - 覆盖端点：`GET /`、`GET /{field_id}`、`POST /`、`PUT /{field_id}`、`DELETE /{field_id}`、`POST /validate`、`GET /types`、`GET /assets/{asset_id}/values`、`PUT /assets/{asset_id}/values`、`POST /assets/batch-values`
  - 约束：资源类型统一为 `asset`；资产维度读取/更新端点统一映射 `resource_id="{asset_id}"`，读取端点使用 `deny_as_not_found=True`
- 已扩展分层约束测试：
  - `backend/tests/unit/api/v1/test_custom_fields_layering.py`
  - 覆盖：模块引入 `AuthzContext/require_authz`、关键端点 ABAC 依赖注入、既有服务委托断言保持通过

### 1.14 P2c（ABAC 覆盖扩展：权属方批次）
- 已为权属方关键端点接入统一 ABAC 依赖 `require_authz(...)`：
  - `backend/src/api/v1/assets/ownership.py`
  - 覆盖端点：`GET /dropdown-options`、`POST /`、`PUT /{ownership_id}`、`PUT /{ownership_id}/projects`、`DELETE /{ownership_id}`、`GET /`、`POST /search`、`GET /statistics/summary`、`POST /{ownership_id}/toggle-status`、`GET /{ownership_id}/financial-summary`
  - 约束：资源类型统一为 `asset`；ownership 维度写/读端点统一映射 `resource_id="{ownership_id}"`；财务汇总读取端点使用 `deny_as_not_found=True`
- 已新增分层约束测试：
  - `backend/tests/unit/api/v1/test_ownership_layering.py`
  - 覆盖：模块引入 `AuthzContext/require_authz`、关键端点 ABAC 依赖注入、下拉接口服务委托断言保持通过

### 1.15 P2c（ABAC 覆盖扩展：出租率批次）
- 已为出租率关键读端点接入统一 ABAC 依赖 `require_authz(...)`：
  - `backend/src/api/v1/assets/occupancy.py`
  - 覆盖端点：`GET /rate`、`GET /analysis`、`GET /trends`
  - 约束：动作统一映射为 `read`，资源类型统一为 `asset`
- 已新增分层约束测试：
  - `backend/tests/unit/api/v1/test_occupancy_layering.py`
  - 覆盖：模块引入 `AuthzContext/require_authz`、3 个关键读端点 ABAC 依赖注入

### 1.16 P2c（ABAC 覆盖扩展：资产主路由剩余端点批次）
- 已为资产主路由剩余关键端点接入统一 ABAC 依赖 `require_authz(...)`：
  - `backend/src/api/v1/assets/assets.py`
  - 覆盖端点：`GET /`（列表）、`GET /ownership-entities`、`GET /business-categories`、`GET /usage-statuses`、`GET /property-natures`、`GET /ownership-statuses`、`POST /{asset_id}/restore`、`DELETE /{asset_id}/hard-delete`、`GET /{asset_id}/history`
  - 约束：筛选辅助与列表动作统一映射 `read`；恢复/硬删动作映射 `update/delete` 且统一映射 `resource_id="{asset_id}"`；历史读取使用 `deny_as_not_found=True`
- 已新增分层约束测试：
  - `backend/tests/unit/api/v1/test_assets_authz_layering.py`
  - 覆盖：模块引入 `AuthzContext/require_authz`、上述剩余端点 ABAC 依赖注入断言

### 1.17 P2c（ABAC 覆盖扩展：项目路由剩余读端点批次）
- 已为项目路由剩余读端点接入统一 ABAC 依赖 `require_authz(...)`：
  - `backend/src/api/v1/assets/project.py`
  - 覆盖端点：`GET /`、`POST /search`、`GET /dropdown-options`、`GET /stats/overview`
  - 约束：动作统一映射为 `read`，资源类型统一为 `project`
- 已统一 `project.py` 中 `_authz_ctx` 参数声明风格为 `= Depends(...)`，避免测试态直接调用路由函数时将鉴权依赖识别为必传位置参数。
- 已扩展分层约束测试：
  - `backend/tests/unit/api/v1/test_project_layering.py`
  - 覆盖：剩余读端点 ABAC 依赖注入断言 + 既有服务委托断言保持通过

### 1.18 P2c（ABAC 覆盖扩展：PDF 批处理批次）
- 已为 PDF 批处理关键端点接入统一 ABAC 依赖 `require_authz(...)`：
  - `backend/src/api/v1/documents/pdf_batch_routes.py`
  - 覆盖端点：`POST /upload`、`GET /status/{batch_id}`、`GET /list`、`POST /cancel/{batch_id}`、`DELETE /cleanup`
  - 约束：动作映射为 `create/read/read/update/delete`，资源类型统一为 `rent_contract`
- 已扩展分层约束测试：
  - `backend/tests/unit/api/v1/test_pdf_batch_routes_layering.py`
  - 覆盖：模块关键端点 ABAC 依赖注入断言 + 既有服务委托断言保持通过

### 1.19 P2c（ABAC 覆盖扩展：Excel 导入批次）
- 已为 Excel 导入关键端点接入统一 ABAC 依赖 `require_authz(...)`：
  - `backend/src/api/v1/documents/excel/import_ops.py`
  - 覆盖端点：`POST /import`、`POST /import/async`
  - 约束：动作统一映射为 `create`，资源类型统一为 `asset`
- 已扩展分层约束测试：
  - `backend/tests/unit/api/v1/test_excel_import_ops_layering.py`
  - 覆盖：模块关键端点 ABAC 依赖注入断言 + 既有任务创建/失败处理服务委托断言保持通过

### 1.20 P2c（ABAC 覆盖扩展：PDF 上传批次）
- 已为 PDF 上传端点接入统一 ABAC 依赖 `require_authz(...)`：
  - `backend/src/api/v1/documents/pdf_upload.py`
  - 覆盖端点：`POST /upload`
  - 约束：动作映射为 `create`，资源类型统一为 `rent_contract`
- 已新增分层约束测试：
  - `backend/tests/unit/api/v1/test_pdf_upload_layering.py`
  - 覆盖：模块关键端点 ABAC 依赖注入断言
- 已适配 TestClient 场景 ABAC 单测隔离：
  - `backend/tests/unit/api/v1/documents/test_pdf_import_routes.py`
  - 覆盖：在 `client` fixture 中补齐 `authz_service.check_access=allow` patch，避免上传 API 用例被真实 ABAC 依赖链路干扰

### 1.21 P2c（ABAC 覆盖扩展：PDF 系统信息批次）
- 已为 PDF 系统信息关键读端点接入统一 ABAC 依赖 `require_authz(...)`：
  - `backend/src/api/v1/documents/pdf_system.py`
  - 覆盖端点：`GET /info`、`GET /health`、`GET /sessions`
  - 约束：动作统一映射为 `read`，资源类型统一为 `rent_contract`
- 已新增分层约束测试：
  - `backend/tests/unit/api/v1/test_pdf_system_layering.py`
  - 覆盖：模块关键读端点 ABAC 依赖注入断言

### 1.22 P2c（ABAC 覆盖扩展：Excel 模板/状态批次）
- 已为 Excel 模板下载端点接入统一 ABAC 依赖 `require_authz(...)`：
  - `backend/src/api/v1/documents/excel/template.py`
  - 覆盖端点：`GET /template`
  - 约束：动作映射为 `read`，资源类型统一为 `asset`
- 已为 Excel 任务状态关键读端点接入统一 ABAC 依赖 `require_authz(...)`：
  - `backend/src/api/v1/documents/excel/status.py`
  - 覆盖端点：`GET /status/{task_id}`、`GET /history`
  - 约束：动作统一映射为 `read`，资源类型统一为 `asset`
- 已新增分层约束测试：
  - `backend/tests/unit/api/v1/test_excel_template_layering.py`
  - `backend/tests/unit/api/v1/test_excel_status_layering.py`
  - 覆盖：模板下载与状态/历史端点 ABAC 依赖注入断言

### 1.23 P2c（ABAC 覆盖扩展：Excel 预览批次）
- 已为 Excel 预览关键端点接入统一 ABAC 依赖 `require_authz(...)`：
  - `backend/src/api/v1/documents/excel/preview.py`
  - 覆盖端点：`POST /preview/advanced`、`POST /preview`
  - 约束：动作统一映射为 `create`，资源类型统一为 `asset`
- 已新增分层约束测试：
  - `backend/tests/unit/api/v1/test_excel_preview_layering.py`
  - 覆盖：高级预览与普通预览端点 ABAC 依赖注入断言

### 1.24 P2c（ABAC 覆盖扩展：Excel 导出批次）
- 已为 Excel 导出关键端点接入统一 ABAC 依赖 `require_authz(...)`：
  - `backend/src/api/v1/documents/excel/export_ops.py`
  - 覆盖端点：`GET /export`、`POST /export`、`POST /export/async`、`GET /download/{task_id}`
  - 约束：动作统一映射为 `read`，资源类型统一为 `asset`
- 已新增分层约束测试：
  - `backend/tests/unit/api/v1/test_excel_export_ops_layering.py`
  - 覆盖：导出/异步导出/下载关键端点 ABAC 依赖注入断言

### 1.25 P2c（ABAC 覆盖扩展：Excel 配置批次）
- 已为 Excel 配置关键端点接入统一 ABAC 依赖 `require_authz(...)`：
  - `backend/src/api/v1/documents/excel/config.py`
  - 覆盖端点：`POST /configs`、`GET /configs`、`GET /configs/default`、`GET /configs/{config_id}`、`PUT /configs/{config_id}`、`DELETE /configs/{config_id}`
  - 约束：动作映射为 `create/read/read/read/update/delete`，资源类型统一为 `asset`
- 已新增分层约束测试：
  - `backend/tests/unit/api/v1/test_excel_config_layering.py`
  - 覆盖：配置创建/列表/默认配置/详情/更新/删除端点 ABAC 依赖注入断言

### 1.26 P2c（ABAC 覆盖扩展：PDF 批处理健康检查批次）
- 已为 PDF 批处理健康检查端点接入统一 ABAC 依赖 `require_authz(...)`：
  - `backend/src/api/v1/documents/pdf_batch_routes.py`
  - 覆盖端点：`GET /pdf-import/batch/health`
  - 约束：动作映射为 `read`，资源类型统一为 `rent_contract`
- 已扩展分层约束测试：
  - `backend/tests/unit/api/v1/test_pdf_batch_routes_layering.py`
  - 覆盖：`batch_health_check` 端点 ABAC 依赖注入断言

### 1.27 P2c（ABAC 覆盖扩展：PDF 兼容路由批次）
- 已为 PDF 兼容路由关键端点接入统一 ABAC 依赖 `require_authz(...)`：
  - `backend/src/api/v1/documents/pdf_import_routes.py`
  - 覆盖端点：`GET /info`、`GET /sessions`、`POST /upload`
  - 约束：动作映射为 `read/read/create`，资源类型统一为 `rent_contract`
- 已新增分层约束测试：
  - `backend/tests/unit/api/v1/test_pdf_import_routes_layering.py`
  - 覆盖：兼容路由关键端点 ABAC 依赖注入断言

### 1.28 P2c（ABAC 覆盖扩展：资产批量读端点批次）
- 已为资产批量读端点接入统一 ABAC 依赖 `require_authz(...)`：
  - `backend/src/api/v1/assets/asset_batch.py`
  - 覆盖端点：`GET /all`、`POST /by-ids`
  - 约束：动作统一映射为 `read`，资源类型统一为 `asset`
- 已扩展分层约束测试：
  - `backend/tests/unit/api/v1/test_asset_batch_layering.py`
  - 覆盖：`get_all_assets` 与 `get_assets_by_ids` 端点 ABAC 依赖注入断言

### 1.29 P2c（ABAC 覆盖扩展：资产批量验证端点批次）
- 已为资产批量验证端点接入统一 ABAC 依赖 `require_authz(...)`：
  - `backend/src/api/v1/assets/asset_batch.py`
  - 覆盖端点：`POST /validate`
  - 约束：动作映射为 `read`，资源类型统一为 `asset`
- 已扩展分层约束测试：
  - `backend/tests/unit/api/v1/test_asset_batch_layering.py`
  - 覆盖：`validate_asset_data` 端点 ABAC 依赖注入断言

### 1.30 P2c（ABAC 覆盖扩展：产权证列表端点批次）
- 已为产权证列表端点接入统一 ABAC 依赖 `require_authz(...)`：
  - `backend/src/api/v1/assets/property_certificate.py`
  - 覆盖端点：`GET /property-certificates/`
  - 约束：动作映射为 `read`，资源类型统一为 `property_certificate`
- 已扩展分层约束测试：
  - `backend/tests/unit/api/v1/test_property_certificate_authz_layering.py`
  - 覆盖：`list_certificates` 端点 ABAC 依赖注入断言

### 1.31 P2c（ABAC 覆盖扩展：分析主路由批次）
- 已为分析主路由业务端点接入统一 ABAC 依赖 `require_authz(...)`：
  - `backend/src/api/v1/analytics/analytics.py`
  - 覆盖端点：`GET /comprehensive`、`GET /cache/stats`、`POST /cache/clear`、`GET /trend`、`GET /distribution`、`POST /export`
  - 约束：动作映射为 `read/read/update/read/read/read`，资源类型统一为 `asset`
- 已新增分层约束测试：
  - `backend/tests/unit/api/v1/analytics/test_analytics_layering.py`
  - 覆盖：分析主路由业务端点 ABAC 依赖注入断言
- 已适配 TestClient 场景 ABAC 单测隔离：
  - `backend/tests/unit/api/v1/analytics/test_analytics.py`
  - `backend/tests/unit/api/v1/test_analytics.py`
  - 覆盖：在测试夹具中补齐 `authz_service.check_access=allow` patch，避免分析 API 用例被真实 ABAC 依赖链路干扰

### 1.32 P2c（ABAC 覆盖扩展：财务统计子模块批次）
- 已为财务统计子模块端点接入统一 ABAC 依赖 `require_authz(...)`：
  - `backend/src/api/v1/analytics/statistics_modules/financial_stats.py`
  - 覆盖端点：`GET /statistics/financial-summary`
  - 约束：动作映射为 `read`，资源类型统一为 `asset`
- 已新增分层约束测试：
  - `backend/tests/unit/api/v1/analytics/statistics_modules/test_financial_stats_layering.py`
  - 覆盖：`get_financial_summary` 端点 ABAC 依赖注入断言
- 已适配 TestClient 场景 ABAC 单测隔离：
  - `backend/tests/unit/api/v1/analytics/statistics_modules/test_financial_stats.py`
  - 覆盖：在测试夹具中补齐 `authz_service.check_access=allow` patch，避免财务统计 API 用例被真实 ABAC 依赖链路干扰

### 1.33 P2c（ABAC 覆盖扩展：统计子模块剩余端点批次）
- 已为统计子模块剩余关键端点接入统一 ABAC 依赖 `require_authz(...)`：
  - `backend/src/api/v1/analytics/statistics_modules/basic_stats.py`
  - `backend/src/api/v1/analytics/statistics_modules/area_stats.py`
  - `backend/src/api/v1/analytics/statistics_modules/distribution.py`
  - `backend/src/api/v1/analytics/statistics_modules/occupancy_stats.py`
  - `backend/src/api/v1/analytics/statistics_modules/trend_stats.py`
  - 覆盖端点：
    - `basic/summary/dashboard/comprehensive/cache/clear/cache/info`
    - `area-summary/area-statistics`
    - `ownership-distribution/property-nature-distribution/usage-status-distribution/asset-distribution`
    - `occupancy-rate/overall`、`occupancy-rate/by-category`、`occupancy-rate`
    - `trend/{metric}`
  - 约束：动作映射统一为 `read`（`cache/clear` 为 `update`），资源类型统一为 `asset`
- 已扩展/新增分层约束测试：
  - `backend/tests/unit/api/v1/analytics/statistics_modules/test_basic_stats_layering.py`
  - `backend/tests/unit/api/v1/analytics/statistics_modules/test_area_stats_layering.py`
  - `backend/tests/unit/api/v1/analytics/statistics_modules/test_distribution_layering.py`
  - `backend/tests/unit/api/v1/analytics/statistics_modules/test_occupancy_stats_layering.py`
  - `backend/tests/unit/api/v1/analytics/statistics_modules/test_trend_stats_layering.py`
  - 覆盖：模块引入 `AuthzContext/require_authz`、关键端点 ABAC 依赖注入断言、既有服务层委托断言保持通过
- 已适配 TestClient 场景 ABAC 单测隔离：
  - `backend/tests/unit/api/v1/analytics/statistics_modules/test_basic_stats.py`
  - `backend/tests/unit/api/v1/analytics/statistics_modules/test_area_stats.py`
  - `backend/tests/unit/api/v1/analytics/statistics_modules/test_occupancy_stats.py`
  - 覆盖：在测试夹具中补齐 `authz_service.check_access=allow` patch，避免统计子模块 API 用例被真实 ABAC 依赖链路干扰

### 1.34 P2c（ABAC 覆盖扩展：任务模块 Excel 配置端点批次）
- 已为任务模块 Excel 配置关键端点接入统一 ABAC 依赖 `require_authz(...)`：
  - `backend/src/api/v1/system/tasks.py`
  - 覆盖端点：`POST /tasks/configs/excel`、`GET /tasks/configs/excel`、`GET /tasks/configs/excel/default`、`GET /tasks/configs/excel/{config_id}`、`PUT /tasks/configs/excel/{config_id}`、`DELETE /tasks/configs/excel/{config_id}`
  - 约束：动作映射为 `create/read/read/read/update/delete`，资源类型统一为 `asset`
- 已扩展分层约束测试：
  - `backend/tests/unit/api/v1/test_tasks_layering.py`
  - 覆盖：任务模块 Excel 配置端点 `require_authz` 依赖注入断言

### 1.35 P2c（ABAC 覆盖扩展：主体管理路由批次）
- 已为主体管理关键端点接入统一 ABAC 依赖 `require_authz(...)`：
  - `backend/src/api/v1/party.py`
  - 覆盖端点：`GET/POST /parties`、`GET/PUT/DELETE /parties/{party_id}`、`GET/POST/DELETE /parties/{party_id}/hierarchy`、`GET/POST /parties/{party_id}/contacts`
  - 约束：动作映射为 `read/create/read/update/delete/read/create/delete/read/create`，资源类型统一为 `party`
  - 细节：按 `party_id` 读取端点统一映射 `resource_id="{party_id}"` 且启用 `deny_as_not_found=True`
- 已新增分层约束测试：
  - `backend/tests/unit/api/v1/test_party_layering.py`
  - 覆盖：模块引入 `AuthzContext/require_authz`、10 个关键端点 ABAC 依赖注入断言、列表端点服务委托断言

### 1.36 P2c（ABAC 覆盖扩展：任务模块主端点批次）
- 已为任务模块主端点接入统一 ABAC 依赖 `require_authz(...)`：
  - `backend/src/api/v1/system/tasks.py`
  - 覆盖端点：`POST /tasks/`、`GET /tasks`、`GET /tasks/{task_id}`、`PUT /tasks/{task_id}`、`POST /tasks/{task_id}/cancel`、`DELETE /tasks/{task_id}`、`GET /tasks/{task_id}/history`、`GET /tasks/statistics`、`GET /tasks/running`、`GET /tasks/recent`、`GET /tasks/cleanup`
  - 约束：动作映射为 `create/read/read/update/update/delete/read/read/read/read/delete`，资源类型统一为 `asset`
- 已扩展分层约束测试：
  - `backend/tests/unit/api/v1/test_tasks_layering.py`
  - 覆盖：任务主端点 `require_authz` 依赖注入断言 + 既有服务委托断言保持通过

### 1.37 P2c（ABAC 覆盖扩展：历史记录路由批次）
- 已为历史记录关键端点接入统一 ABAC 依赖 `require_authz(...)`：
  - `backend/src/api/v1/system/history.py`
  - 覆盖端点：`GET /history/`、`GET /history/{history_id}`、`DELETE /history/{history_id}`
  - 约束：动作映射为 `read/read/delete`，资源类型统一为 `asset`
- 已扩展分层约束测试：
  - `backend/tests/unit/api/v1/test_history_layering.py`
  - 覆盖：模块引入 `AuthzContext/require_authz`、历史记录关键端点 ABAC 依赖注入断言、既有服务委托断言保持通过

### 1.38 P2c（ABAC 覆盖扩展：催缴管理路由批次）
- 已为催缴管理关键端点接入统一 ABAC 依赖 `require_authz(...)`：
  - `backend/src/api/v1/system/collection.py`
  - 覆盖端点：`GET /collection/summary`、`GET /collection/records`、`GET /collection/records/{record_id}`、`POST /collection/records`、`PUT /collection/records/{record_id}`、`DELETE /collection/records/{record_id}`
  - 约束：动作映射为 `read/read/read/create/update/delete`，资源类型统一为 `asset`
  - 细节：详情读取端点映射 `resource_id="{record_id}"` 且启用 `deny_as_not_found=True`
- 已新增分层约束测试：
  - `backend/tests/unit/api/v1/test_collection_layering.py`
  - 覆盖：模块引入 `AuthzContext/require_authz`、6 个关键端点 ABAC 依赖注入断言、列表端点服务委托断言

### 1.39 P2c（ABAC 覆盖扩展：联系人管理路由批次）
- 已为联系人管理关键端点接入统一 ABAC 依赖 `require_authz(...)`：
  - `backend/src/api/v1/system/contact.py`
  - 覆盖端点：`POST /contacts/`、`GET /contacts/{contact_id}`、`GET /contacts/entity/{entity_type}/{entity_id}`、`GET /contacts/entity/{entity_type}/{entity_id}/primary`、`PUT /contacts/{contact_id}`、`DELETE /contacts/{contact_id}`、`POST /contacts/batch/{entity_type}/{entity_id}`
  - 约束：动作映射为 `create/read/read/read/update/delete/create`，资源类型统一为 `asset`
  - 细节：按 `contact_id` 与 `entity_id` 读取端点映射 `resource_id`，读取端点启用 `deny_as_not_found=True`
- 已扩展分层约束测试：
  - `backend/tests/unit/api/v1/test_contact_layering.py`
  - 覆盖：模块引入 `AuthzContext/require_authz`、7 个关键端点 ABAC 依赖注入断言、既有服务委托断言保持通过

### 1.40 P2c（ABAC 覆盖扩展：统一字典路由批次）
- 已为统一字典关键端点接入统一 ABAC 依赖 `require_authz(...)`：
  - `backend/src/api/v1/system/dictionaries.py`
  - 覆盖端点：`GET /system/dictionaries/{dict_type}/options`、`POST /system/dictionaries/{dict_type}/quick-create`、`GET /system/dictionaries/types`、`GET /system/dictionaries/validation/stats`、`POST /system/dictionaries/{dict_type}/values`、`DELETE /system/dictionaries/{dict_type}`
  - 约束：动作映射为 `read/create/read/read/create/delete`，资源类型统一为 `asset`
  - 细节：按 `dict_type` 读取端点映射 `resource_id="{dict_type}"`，选项读取端点启用 `deny_as_not_found=True`
- 已扩展分层约束测试：
  - `backend/tests/unit/api/v1/test_dictionaries_layering.py`
  - 覆盖：模块引入 `AuthzContext/require_authz`、6 个关键端点 ABAC 依赖注入断言、路由层不直连 CRUD 断言保持通过

### 1.41 P2c（ABAC 覆盖扩展：通知路由批次）
- 已为通知关键端点接入统一 ABAC 依赖 `require_authz(...)`：
  - `backend/src/api/v1/system/notifications.py`
  - 覆盖端点：`GET /notifications`、`GET /notifications/unread-count`、`POST /notifications/{notification_id}/read`、`POST /notifications/read-all`、`DELETE /notifications/{notification_id}`、`POST /notifications/run-tasks`
  - 约束：动作映射为 `read/read/update/update/delete/update`，资源类型统一为 `asset`
  - 细节：按 `notification_id` 端点映射 `resource_id="{notification_id}"`，并保留 `run-tasks` 的管理员语义检查
- 已新增分层约束测试：
  - `backend/tests/unit/api/v1/test_notifications_layering.py`
  - 覆盖：模块引入 `AuthzContext/require_authz`、6 个关键端点 ABAC 依赖注入断言、路由层不直连 CRUD 断言保持通过

### 1.42 P2c（ABAC 覆盖扩展：操作日志路由批次）
- 已为操作日志关键端点接入统一 ABAC 依赖 `require_authz(...)`：
  - `backend/src/api/v1/system/operation_logs.py`
  - 覆盖端点：`GET /logs`、`GET /logs/{log_id}`、`GET /logs/statistics/user`、`GET /logs/statistics/module`、`GET /logs/statistics/daily`、`GET /logs/statistics/errors`、`GET /logs/statistics/summary`、`POST /logs/export`、`POST /logs/cleanup`
  - 约束：动作映射为 `read/read/read/read/read/read/read/read/delete`，资源类型统一为 `asset`
  - 细节：详情读取端点映射 `resource_id="{log_id}"`，并启用 `deny_as_not_found=True`；`errors/export/cleanup` 端点保留管理员语义检查
- 已扩展分层约束测试：
  - `backend/tests/unit/api/v1/test_operation_logs_layering.py`
  - 覆盖：模块引入 `AuthzContext/require_authz`、9 个关键端点 ABAC 依赖注入断言、路由层不直接导入 CRUD 与服务委托断言保持通过

### 1.43 P2c（ABAC 覆盖扩展：枚举字段路由批次）
- 已为枚举字段关键业务端点接入统一 ABAC 依赖 `require_authz(...)`（debug 端点除外）：
  - `backend/src/api/v1/system/enum_field.py`
  - 覆盖端点：`GET /types`、`GET /types/statistics`、`GET/POST/PUT/DELETE /types/{...}`、`GET /types/categories/list[Any]`、`GET /types/{type_id}/values`、`GET /types/{type_id}/values/tree`、`GET/PUT/DELETE /values/{value_id}`、`POST /types/{type_id}/values`、`POST /types/{type_id}/values/batch`、`GET/POST/PUT/DELETE /usage{...}`、`GET /types/{type_id}/history`、`GET /values/{value_id}/history`
  - 约束：动作映射覆盖 `read/create/update/delete`，资源类型统一为 `asset`
  - 细节：详情/历史读取端点按 `type_id/value_id` 映射 `resource_id`，并在读场景启用 `deny_as_not_found=True`
- 已扩展分层约束测试：
  - `backend/tests/unit/api/v1/test_enum_field_layering.py`
  - 覆盖：模块引入 `AuthzContext/require_authz`、20 个关键端点 ABAC 依赖注入断言、路由层不直接导入 CRUD 断言保持通过

### 1.44 P2c（ABAC 覆盖扩展：数据备份路由批次）
- 已为数据备份关键端点接入统一 ABAC 依赖 `require_authz(...)`：
  - `backend/src/api/v1/system/backup.py`
  - 覆盖端点：`POST /create`、`GET /list[Any]`、`GET /download/{backup_name}`、`POST /restore/{backup_name}`、`DELETE /delete/{backup_name}`、`GET /stats`、`POST /validate/{backup_name}`、`POST /cleanup`
  - 约束：动作映射为 `create/read/read/update/delete/read/read/delete`，资源类型统一为 `asset`
  - 细节：下载端点按 `backup_name` 映射 `resource_id` 且启用 `deny_as_not_found=True`
- 已新增分层约束测试：
  - `backend/tests/unit/api/v1/test_backup_layering.py`
  - 覆盖：模块引入 `AuthzContext/require_authz`、8 个关键端点 ABAC 依赖注入断言、列表端点服务委托断言

### 1.45 P2c（ABAC 覆盖扩展：系统核心路由批次）
- 已为系统核心端点接入统一 ABAC 依赖 `require_authz(...)`：
  - `backend/src/api/v1/system/system.py`
  - 覆盖端点：`GET /monitoring/health`、`GET /system/info`、`GET /system/root`
  - 约束：动作映射统一为 `read`，资源类型统一为 `asset`
- 已新增分层约束测试：
  - `backend/tests/unit/api/v1/test_system_layering.py`
  - 覆盖：模块引入 `AuthzContext/require_authz`、3 个核心端点 ABAC 依赖注入断言

### 1.46 P2c（ABAC 覆盖扩展：LLM Prompt 路由批次）
- 已为 LLM Prompt 关键端点接入统一 ABAC 依赖 `require_authz(...)`：
  - `backend/src/api/v1/llm_prompts.py`
  - 覆盖端点：`POST /`、`GET /`、`GET /{prompt_id}`、`PUT /{prompt_id}`、`POST /{prompt_id}/activate`、`POST /{prompt_id}/rollback`、`GET /{prompt_id}/versions`、`GET /statistics/overview`、`POST /feedback`
  - 约束：动作映射为 `create/read/read/update/update/update/read/read/create`，资源类型统一为 `asset`
  - 细节：按 `prompt_id` 读取端点映射 `resource_id="{prompt_id}"`，读取端点启用 `deny_as_not_found=True`
- 已新增分层约束测试：
  - `backend/tests/unit/api/v1/test_llm_prompts_layering.py`
  - 覆盖：模块引入 `AuthzContext/require_authz`、9 个关键端点 ABAC 依赖注入断言

### 1.47 P2c（ABAC 覆盖扩展：错误恢复路由批次）
- 已为错误恢复关键端点接入统一 ABAC 依赖 `require_authz(...)`：
  - `backend/src/api/v1/system/error_recovery.py`
  - 覆盖端点：`GET /statistics`、`GET /strategies`、`PUT /strategies/{category}`、`GET /circuit-breakers`、`POST /circuit-breakers/{category}/reset`、`GET /history`、`POST /test`、`DELETE /history/clear`
  - 约束：动作映射为 `read/read/update/read/update/read/update/delete`，资源类型统一为 `asset`
  - 细节：按 `category` 路径参数端点统一映射 `resource_id="{category}"`
- 已新增分层约束测试：
  - `backend/tests/unit/api/v1/test_error_recovery_layering.py`
  - 覆盖：模块引入 `AuthzContext/require_authz`、8 个关键端点 ABAC 依赖注入断言

### 1.48 P2c（ABAC 覆盖扩展：系统监控路由批次）
- 已为系统监控关键端点接入统一 ABAC 依赖 `require_authz(...)`：
  - `backend/src/api/v1/system/monitoring.py`
  - 覆盖端点：`POST /route-performance`、`GET /system-health`、`GET /performance/dashboard`、`GET /system-metrics`、`GET /application-metrics`、`GET /dashboard`、`POST /metrics/collect`
  - 约束：动作映射为 `create/read/read/read/read/read/update`，资源类型统一为 `asset`
- 已新增分层约束测试：
  - `backend/tests/unit/api/v1/test_monitoring_layering.py`
  - 覆盖：模块引入 `AuthzContext/require_authz`、7 个关键端点 ABAC 依赖注入断言

### 1.49 P2c（ABAC 覆盖扩展：系统设置路由批次）
- 已为系统设置关键端点接入统一 ABAC 依赖 `require_authz(...)`：
  - `backend/src/api/v1/system/system_settings.py`
  - 覆盖端点：`POST /security/alerts/test`、`GET /security/events`、`GET /settings`、`PUT /settings`、`GET /info`、`POST /backup`、`POST /restore`
  - 约束：动作映射为 `update/read/read/update/read/create/update`，资源类型统一为 `asset`
- 已扩展分层约束测试：
  - `backend/tests/unit/api/v1/test_system_settings_layering.py`
  - 覆盖：模块引入 `AuthzContext/require_authz`、7 个关键端点 ABAC 依赖注入断言、既有服务委托断言保持通过

### 1.50 P2c（ABAC 覆盖扩展：角色管理路由批次）
- 已为角色管理关键端点接入统一 ABAC 依赖 `require_authz(...)`：
  - `backend/src/api/v1/auth/roles.py`
  - 覆盖端点：`GET|POST /roles`、`POST /roles/permission-check`、`POST /roles/assignments`、`GET /roles/users/{user_id}/roles`、`DELETE /roles/users/{user_id}/roles/{role_id}`、`GET /roles/users/{user_id}/permissions/summary`、`POST|GET /roles/permission-grants`、`GET|PATCH|DELETE /roles/permission-grants/{grant_id}`、`GET|PUT|DELETE /roles/{role_id}`、`GET /roles/permissions/list`、`PUT /roles/{role_id}/permissions`、`GET /roles/{role_id}/users`、`GET /roles/statistics/summary`
  - 约束：动作映射覆盖 `read/create/update/delete`，资源类型统一为 `asset`
  - 细节：按 `user_id/grant_id/role_id` 路径参数端点补齐 `resource_id` 映射，详情读取端点启用 `deny_as_not_found=True`
- 已新增分层约束测试：
  - `backend/tests/unit/api/v1/test_roles_layering.py`
  - 覆盖：模块引入 `AuthzContext/require_authz`、19 个关键端点 ABAC 依赖注入断言

### 1.51 P2c（ABAC 覆盖扩展：组织管理路由批次）
- 已为组织管理关键端点接入统一 ABAC 依赖 `require_authz(...)`：
  - `backend/src/api/v1/auth/organization.py`
  - 覆盖端点：`GET /organizations`、`GET /organizations/tree`、`GET /organizations/search`、`GET /organizations/statistics`、`GET /organizations/{org_id}`、`GET /organizations/{org_id}/children`、`GET /organizations/{org_id}/path`、`GET /organizations/{org_id}/history`、`POST /organizations`、`PUT /organizations/{org_id}`、`DELETE /organizations/{org_id}`、`POST /organizations/{org_id}/move`、`POST /organizations/batch`、`POST /organizations/advanced-search`
  - 约束：动作映射覆盖 `read/create/update/delete`，资源类型统一为 `asset`
  - 细节：按 `org_id` 路径参数端点补齐 `resource_id` 映射，详情读取端点启用 `deny_as_not_found=True`
- 已新增分层约束测试：
  - `backend/tests/unit/api/v1/test_organization_layering.py`
  - 覆盖：模块引入 `AuthzContext/require_authz`、14 个关键端点 ABAC 依赖注入断言

### 1.52 P2c（ABAC 覆盖扩展：会话管理路由批次）
- 已为会话管理关键端点接入统一 ABAC 依赖 `require_authz(...)`：
  - `backend/src/api/v1/auth/auth_modules/sessions.py`
  - 覆盖端点：`GET /sessions`、`DELETE /sessions/{session_id}`
  - 约束：动作映射为 `read/delete`，资源类型统一为 `asset`
  - 细节：撤销端点按 `session_id` 路径参数补齐 `resource_id="{session_id}"` 映射
- 已扩展分层约束测试：
  - `backend/tests/unit/api/v1/test_auth_sessions_layering.py`
  - 覆盖：模块引入 `AuthzContext/require_authz`、2 个关键端点 ABAC 依赖注入断言、既有服务委托断言保持通过

### 1.53 P2c（ABAC 覆盖扩展：审计日志路由批次）
- 已为审计日志统计端点接入统一 ABAC 依赖 `require_authz(...)`：
  - `backend/src/api/v1/auth/auth_modules/audit.py`
  - 覆盖端点：`GET /audit/logs`
  - 约束：动作映射为 `read`，资源类型统一为 `asset`
- 已扩展分层约束测试：
  - `backend/tests/unit/api/v1/test_auth_audit_layering.py`
  - 覆盖：模块引入 `AuthzContext/require_authz`、审计统计端点 ABAC 依赖注入断言、既有服务委托断言保持通过

### 1.54 P2c（ABAC 覆盖扩展：安全配置路由批次）
- 已为安全配置端点接入统一 ABAC 依赖 `require_authz(...)`：
  - `backend/src/api/v1/auth/auth_modules/security.py`
  - 覆盖端点：`GET /security/config`
  - 约束：动作映射为 `read`，资源类型统一为 `asset`
- 已新增分层约束测试：
  - `backend/tests/unit/api/v1/test_auth_security_layering.py`
  - 覆盖：模块引入 `AuthzContext/require_authz`、安全配置端点 ABAC 依赖注入断言、配置响应结构断言

### 1.55 P2c（ABAC 覆盖扩展：用户管理路由批次）
- 已为用户管理关键端点接入统一 ABAC 依赖 `require_authz(...)`：
  - `backend/src/api/v1/auth/auth_modules/users.py`
  - 覆盖端点：`GET /users`、`GET /users/search`、`POST /users`、`GET /users/{user_id}`、`PUT /users/{user_id}`、`POST /users/{user_id}/change-password`、`POST /users/{user_id}/deactivate`、`DELETE /users/{user_id}`、`POST /users/{user_id}/activate`、`POST /users/{user_id}/lock`、`POST /users/{user_id}/unlock`、`POST /users/{user_id}/reset-password`、`GET /users/statistics/summary`
  - 约束：动作映射覆盖 `read/create/update/delete`，资源类型统一为 `asset`
  - 细节：按 `user_id` 路径参数端点补齐 `resource_id="{user_id}"` 映射，详情读取端点启用 `deny_as_not_found=True`
- 已扩展分层约束测试：
  - `backend/tests/unit/api/v1/test_users_layering.py`
  - 覆盖：模块引入 `AuthzContext/require_authz`、13 个关键端点 ABAC 依赖注入断言、既有服务委托断言保持通过

### 1.56 P2c（ABAC 覆盖扩展：system_monitoring 子模块批次）
- 已为 `system_monitoring/*` 子模块关键端点接入统一 ABAC 依赖 `require_authz(...)`：
  - `backend/src/api/v1/system/system_monitoring/endpoints.py`
  - `backend/src/api/v1/system/system_monitoring/database_endpoints.py`
  - 覆盖端点：
    - `GET /system-metrics`、`GET /application-metrics`、`GET /health`、`GET /metrics/history`、`GET /alerts`、`POST /alerts/{alert_id}/resolve`、`GET /dashboard`、`POST /metrics/collect`、`GET /encryption-status`
    - `GET /database/health`、`GET /database/slow-queries`、`POST /database/optimize`、`POST /database/cleanup`、`GET /database/connection-pool`
  - 约束：动作映射覆盖 `read/create/update/delete`，资源类型统一为 `asset`
- 已修复子模块导入层级问题（避免 `src.api.*` 错误相对路径）：
  - `backend/src/api/v1/system/system_monitoring/collectors.py`
  - `backend/src/api/v1/system/system_monitoring/health.py`
- 已新增分层约束测试：
  - `backend/tests/unit/api/v1/test_system_monitoring_layering.py`
  - 覆盖：两个子路由模块 `AuthzContext/require_authz` 引入与关键端点依赖注入断言

### 1.57 P2c（ABAC 覆盖扩展：统计聚合包装路由批次）
- 已为统计聚合包装路由接入统一 ABAC 依赖 `require_authz(...)`：
  - `backend/src/api/v1/analytics/statistics.py`
  - 覆盖挂载：`basic_stats/distribution/occupancy/area/financial/trend` 子路由统一附带 read 依赖
  - 约束：动作映射为 `read`，资源类型统一为 `asset`
- 已新增分层约束测试：
  - `backend/tests/unit/api/v1/test_statistics_router_layering.py`
  - 覆盖：包装路由 `AuthzContext/require_authz` 引入与 6 个 include_router 依赖注入断言

### 1.58 P2c（ABAC 覆盖扩展：PDF 导入包装路由批次）
- 已为 PDF 导入包装路由接入统一 ABAC 依赖 `require_authz(...)`：
  - `backend/src/api/v1/documents/pdf_import.py`
  - 覆盖挂载：`pdf_upload`（`create`）、`pdf_system`（`read`）、可选 `pdf_sessions`（`read`）
  - 约束：资源类型统一为 `rent_contract`
- 已新增分层约束测试：
  - `backend/tests/unit/api/v1/test_pdf_import_layering.py`
  - 覆盖：包装路由 `AuthzContext/require_authz` 引入与 3 个 include_router 依赖注入断言（含可选 sessions）

### 1.59 P2c（ABAC 覆盖扩展：Excel 配置兼容路由批次）
- 已完成 Excel 配置兼容路由遗留权限依赖清理：
  - `backend/src/api/v1/documents/excel/config.py`
  - 覆盖端点：`POST|GET /configs`、`GET /configs/default`、`GET|PUT|DELETE /configs/{config_id}`
  - 清理项：移除 `require_permission("excel_config", "...")`，统一为 `get_current_active_user + require_authz(...)`
  - 约束：动作映射覆盖 `create/read/update/delete`，资源类型统一为 `asset`
- 已扩展分层约束测试：
  - `backend/tests/unit/api/v1/test_excel_config_layering.py`
  - 覆盖：新增 `get_current_active_user` 引入断言与 `require_permission(` 禁止回流断言

### 1.60 P2c（ABAC 覆盖扩展：任务 Excel 配置端点遗留链路批次）
- 已完成任务模块 Excel 配置端点遗留权限依赖清理：
  - `backend/src/api/v1/system/tasks.py`
  - 覆盖端点：`POST|GET /tasks/configs/excel`、`GET /tasks/configs/excel/default`、`GET|PUT|DELETE /tasks/configs/excel/{config_id}`
  - 清理项：移除 `require_permission("excel_config", "...")`，统一为 `get_current_active_user + require_authz(...)`
  - 约束：动作映射覆盖 `create/read/update/delete`，资源类型统一为 `asset`
- 已扩展分层约束测试：
  - `backend/tests/unit/api/v1/test_tasks_layering.py`
  - 覆盖：新增 `get_current_active_user` 引入断言与 `require_permission(` 禁止回流断言

### 1.61 P2c（ABAC 覆盖扩展：错误恢复路由遗留链路批次）
- 已完成错误恢复路由遗留权限依赖清理：
  - `backend/src/api/v1/system/error_recovery.py`
  - 覆盖端点：`GET /statistics`、`GET /strategies`、`PUT /strategies/{category}`、`GET /circuit-breakers`、`POST /circuit-breakers/{category}/reset`、`GET /history`、`POST /test`、`DELETE /history/clear`
  - 清理项：移除 `require_permission("system:error_recovery", "...")`，统一为 `get_current_active_user + require_authz(...)`
  - 约束：动作映射保持 `read/update/delete`，资源类型统一为 `asset`（`category` 路径端点保留 `resource_id="{category}"` 映射）
- 已扩展分层约束测试：
  - `backend/tests/unit/api/v1/test_error_recovery_layering.py`
  - 覆盖：新增 `get_current_active_user` 引入断言与 `require_permission(` 禁止回流断言

### 1.62 P2c（ABAC 覆盖扩展：assets 遗留权限链路清理批次）
- 已完成 assets 遗留权限依赖清理：
  - `backend/src/api/v1/assets/assets.py`
  - `backend/src/api/v1/assets/asset_batch.py`
  - `backend/src/api/v1/assets/asset_import.py`
  - `backend/src/api/v1/assets/property_certificate.py`
  - 覆盖端点：资产主路由 CRUD、资产批量写/读端点、资产导入端点、产权证 CRUD/上传/确认导入端点
  - 清理项：移除 `require_permission(...)`，统一为 `get_current_active_user + require_authz(...)`
  - 约束：动作映射与 `resource_type` 保持既有定义不变（`asset`/`property_certificate`）
- 已扩展分层约束测试：
  - `backend/tests/unit/api/v1/test_assets_authz_layering.py`
  - `backend/tests/unit/api/v1/test_asset_batch_layering.py`
  - `backend/tests/unit/api/v1/test_asset_import_layering.py`
  - `backend/tests/unit/api/v1/test_property_certificate_authz_layering.py`
  - 覆盖：新增 `get_current_active_user` 引入断言与 `require_permission(` 禁止回流断言

### 1.63 P2c（回归稳态收口：生命周期缓存污染 + 合同服务断言同步）
- 已完成生命周期集成测试稳态修复：
  - `backend/tests/integration/test_asset_lifecycle.py`
  - 修复项：`authenticated_client` 登录夹具在登录前执行 `invalidate_user_accessible_organizations_cache(str(admin_user.id))`，避免组织可见范围缓存污染导致的读取 404/列表空集偶发失败。
- 已完成合同服务单测断言同步：
  - `backend/tests/unit/services/test_rent_contract_service.py`
  - 修复项：`get_contract_page_async` 委托断言补充 `owner_party_id=None`，与服务层当前入参签名保持一致。

## 2. 已验证结果

### 2.1 本批验证通过
- `ruff`（定向）通过：
  - `cd backend && ./.venv/bin/ruff check src/middleware/auth.py src/api/v1/assets/assets.py src/api/v1/assets/project.py src/api/v1/rent_contracts/contracts.py tests/unit/conftest.py tests/unit/middleware/test_authz_dependency.py tests/unit/api/v1/test_rent_contract_api.py`
- `pytest`（定向）通过（16 passed）：
  - `cd backend && ./.venv/bin/python -m pytest --no-cov tests/unit/middleware/test_authz_dependency.py tests/unit/api/v1/test_rent_contract_contracts_layering.py tests/unit/api/v1/test_rent_contract_api.py::TestUpdateContract::test_update_contract_success tests/unit/api/v1/test_rent_contract_api.py::TestUpdateContract::test_update_contract_should_not_use_legacy_can_edit_guard tests/unit/api/v1/test_rent_contract_api.py::TestDeleteContract::test_delete_contract_success_admin tests/unit/api/v1/test_rent_contract_api.py::TestDeleteContract::test_delete_contract_should_not_use_legacy_admin_guard tests/unit/api/v1/test_rent_contract_api.py::TestAdditionalErrorCases::test_update_contract_not_found tests/unit/api/v1/test_rent_contract_api.py::TestAdditionalErrorCases::test_delete_contract_not_found tests/unit/api/v1/test_assets_history_layering.py tests/unit/api/v1/test_assets_ownership_entities_layering.py -q`

### 2.2 已关闭阻塞（rent_contract_api）
- `cd backend && ./.venv/bin/python -m pytest --no-cov tests/unit/api/v1/test_rent_contract_api.py -q`（`34 passed`）
- 说明：此前因 mock 字段与 Query 默认参数不一致引发的既有失败已完成适配清理。

### 2.3 本批新增验证（已通过）
- `cd backend && ./.venv/bin/python -m pytest --no-cov tests/unit/services/test_data_policy_service.py tests/unit/api/v1/test_data_policies.py -q`（`12 passed`）
- `cd backend && ./.venv/bin/ruff check tests/unit/services/test_data_policy_service.py tests/unit/api/v1/test_data_policies.py`

### 2.4 本批新增验证（已通过，产权证 ABAC 覆盖）
- `cd backend && ./.venv/bin/python -m pytest --no-cov tests/unit/api/v1/test_property_certificate_authz_layering.py tests/unit/api/v1/test_property_certificate.py -q`（`3 passed, 20 skipped`）
- `cd backend && ./.venv/bin/python -m pytest --no-cov tests/unit/middleware/test_authz_dependency.py -q`（`3 passed`）
- `cd backend && ./.venv/bin/ruff check src/api/v1/assets/property_certificate.py tests/unit/api/v1/test_property_certificate_authz_layering.py`

### 2.5 本批新增验证（已通过，资产批量 ABAC 覆盖）
- `cd backend && ./.venv/bin/python -m pytest --no-cov tests/unit/api/v1/test_asset_batch_layering.py -q`（`4 passed`）
- `cd backend && ./.venv/bin/python -m pytest --no-cov tests/unit/middleware/test_authz_dependency.py -q`（`3 passed`）
- `cd backend && ./.venv/bin/ruff check src/api/v1/assets/asset_batch.py tests/unit/api/v1/test_asset_batch_layering.py`

### 2.6 本批新增验证（已通过，合同附件/条款 ABAC 覆盖）
- `cd backend && ./.venv/bin/python -m pytest --no-cov tests/unit/api/v1/test_rent_contract_attachments_layering.py tests/unit/api/v1/test_rent_contract_terms_layering.py -q`（`10 passed`）
- `cd backend && ./.venv/bin/python -m pytest --no-cov tests/unit/middleware/test_authz_dependency.py -q`（`3 passed`）
- `cd backend && ./.venv/bin/ruff check src/api/v1/rent_contracts/attachments.py src/api/v1/rent_contracts/terms.py tests/unit/api/v1/test_rent_contract_attachments_layering.py tests/unit/api/v1/test_rent_contract_terms_layering.py`

### 2.7 本批新增验证（已通过，合同台账/统计 ABAC 覆盖）
- `cd backend && ./.venv/bin/python -m pytest --no-cov tests/unit/api/v1/test_rent_contract_ledger_layering.py tests/unit/api/v1/test_rent_contract_statistics_layering.py -q`（`11 passed`）
- `cd backend && ./.venv/bin/python -m pytest --no-cov tests/unit/middleware/test_authz_dependency.py -q`（`3 passed`）
- `cd backend && ./.venv/bin/ruff check src/api/v1/rent_contracts/ledger.py src/api/v1/rent_contracts/statistics.py tests/unit/api/v1/test_rent_contract_ledger_layering.py tests/unit/api/v1/test_rent_contract_statistics_layering.py`

### 2.8 本批新增验证（已通过，Gate 与扩展回归）
- Gate 盘点：
  - `cd backend && { grep -rEn "PermissionGrant|ResourcePermission|OrganizationPermissionService|OrganizationPermissionChecker" src/api/v1 src/services src/middleware src/crud/rbac.py src/models/rbac.py src/crud/field_whitelist.py --include="*.py" > /tmp/bg3.txt || true; } && echo "BG3_NON_DEPRECATED=$(grep -Evc 'DEPRECATED|deprecated' /tmp/bg3.txt || true)"`（`BG3_NON_DEPRECATED=0`）
  - `cd backend && { grep -rEn "ownership_id|ownership_ids" src/models/rent_contract.py src/services/rent_contract/ src/crud/rent_contract.py src/crud/collection.py src/api/v1/rent_contracts/ --include="*.py" > /tmp/bg4.txt || true; } && echo "BG4_NON_DEPRECATED=$(grep -Evc 'DEPRECATED|deprecated' /tmp/bg4.txt || true)"`（`BG4_NON_DEPRECATED=0`）
- 扩展分层回归：
  - `cd backend && ./.venv/bin/python -m pytest --no-cov tests/unit/api/v1/test_rent_contract_contracts_layering.py tests/unit/api/v1/test_rent_contract_attachments_layering.py tests/unit/api/v1/test_rent_contract_terms_layering.py tests/unit/api/v1/test_rent_contract_ledger_layering.py tests/unit/api/v1/test_rent_contract_statistics_layering.py tests/unit/middleware/test_authz_dependency.py -q`（`27 passed`）
- 回归修复验证：
  - `cd backend && ./.venv/bin/python -m pytest --no-cov tests/unit/api/v1/test_rent_contract_api.py -q`（`34 passed`）
  - `cd backend && ./.venv/bin/ruff check tests/unit/api/v1/test_rent_contract_api.py`

### 2.9 本批新增验证（已通过，合同 Excel/生命周期 ABAC 覆盖）
- `cd backend && ./.venv/bin/python -m pytest --no-cov tests/unit/api/v1/test_rent_contract_excel_ops_layering.py tests/unit/api/v1/test_rent_contract_lifecycle_layering.py -q`（`9 passed`）
- `cd backend && ./.venv/bin/python -m pytest --no-cov tests/unit/middleware/test_authz_dependency.py -q`（`3 passed`）
- `cd backend && ./.venv/bin/python -m pytest --no-cov tests/unit/api/v1/test_rent_contract_api.py -k "download_excel_template_success or export_contracts_to_excel_success" -q`（`2 passed, 32 deselected`）
- `cd backend && ./.venv/bin/ruff check src/api/v1/rent_contracts/excel_ops.py src/api/v1/rent_contracts/lifecycle.py tests/unit/api/v1/test_rent_contract_excel_ops_layering.py tests/unit/api/v1/test_rent_contract_lifecycle_layering.py`

### 2.10 本批新增验证（已通过，合同列表读取 ABAC 覆盖）
- `cd backend && ./.venv/bin/python -m pytest --no-cov tests/unit/api/v1/test_rent_contract_contracts_layering.py -q`（`5 passed`）
- `cd backend && ./.venv/bin/python -m pytest --no-cov tests/unit/api/v1/test_rent_contract_api.py -k "get_contracts_default_params or get_contracts_with_pagination or get_asset_contracts_success" -q`（`3 passed, 31 deselected`）
- `cd backend && ./.venv/bin/python -m pytest --no-cov tests/unit/middleware/test_authz_dependency.py -q`（`3 passed`）
- `cd backend && ./.venv/bin/ruff check src/api/v1/rent_contracts/contracts.py tests/unit/api/v1/test_rent_contract_contracts_layering.py`

### 2.11 本批新增验证（已通过，资产附件 ABAC 覆盖）
- `cd backend && ./.venv/bin/python -m pytest --no-cov tests/unit/api/v1/test_asset_attachments_layering.py tests/unit/api/v1/test_asset_attachments.py -q`（`35 passed`）
- `cd backend && ./.venv/bin/python -m pytest --no-cov tests/unit/middleware/test_authz_dependency.py -q`（`3 passed`）
- `cd backend && ./.venv/bin/ruff check src/api/v1/assets/asset_attachments.py tests/unit/api/v1/test_asset_attachments_layering.py`

### 2.12 本批新增验证（已通过，资产导入 ABAC 覆盖）
- `cd backend && ./.venv/bin/python -m pytest --no-cov tests/unit/api/v1/test_asset_import_layering.py -q`（`4 passed`）
- `cd backend && ./.venv/bin/python -m pytest --no-cov tests/unit/middleware/test_authz_dependency.py -q`（`3 passed`）
- `cd backend && ./.venv/bin/ruff check src/api/v1/assets/asset_import.py tests/unit/api/v1/test_asset_import_layering.py`

### 2.13 本批新增验证（已通过，自定义字段 ABAC 覆盖）
- `cd backend && ./.venv/bin/python -m pytest --no-cov tests/unit/api/v1/test_custom_fields_layering.py tests/unit/api/v1/test_custom_fields.py -q`（`27 passed`）
- `cd backend && ./.venv/bin/python -m pytest --no-cov tests/unit/middleware/test_authz_dependency.py -q`（`3 passed`）
- `cd backend && ./.venv/bin/ruff check src/api/v1/assets/custom_fields.py tests/unit/api/v1/test_custom_fields_layering.py`

### 2.14 本批新增验证（已通过，权属方 ABAC 覆盖）
- `cd backend && ./.venv/bin/python -m pytest --no-cov tests/unit/api/v1/test_ownership_layering.py tests/unit/api/v1/test_ownership_api.py -q`（`20 passed`）
- `cd backend && ./.venv/bin/python -m pytest --no-cov tests/unit/middleware/test_authz_dependency.py -q`（`3 passed`）
- `cd backend && ./.venv/bin/ruff check src/api/v1/assets/ownership.py tests/unit/api/v1/test_ownership_layering.py`

### 2.15 本批新增验证（已通过，出租率 ABAC 覆盖）
- `cd backend && ./.venv/bin/python -m pytest --no-cov tests/unit/api/v1/test_occupancy_layering.py tests/unit/api/v1/test_occupancy.py -q`（`4 passed, 4 skipped`）
- `cd backend && ./.venv/bin/python -m pytest --no-cov tests/unit/middleware/test_authz_dependency.py -q`（`3 passed`）
- `cd backend && ./.venv/bin/ruff check src/api/v1/assets/occupancy.py tests/unit/api/v1/test_occupancy_layering.py`

### 2.16 本批新增验证（已通过，资产主路由剩余端点 ABAC 覆盖）
- `cd backend && ./.venv/bin/python -m pytest --no-cov tests/unit/api/v1/test_assets_authz_layering.py tests/unit/api/v1/test_assets_history_layering.py tests/unit/api/v1/test_assets_ownership_entities_layering.py tests/unit/api/v1/test_assets_projection_guard.py -q`（`8 passed`）
- `cd backend && ./.venv/bin/python -m pytest --no-cov tests/unit/middleware/test_authz_dependency.py -q`（`3 passed`）
- `cd backend && ./.venv/bin/ruff check src/api/v1/assets/assets.py tests/unit/api/v1/test_assets_authz_layering.py`

### 2.17 本批新增验证（已通过，项目路由剩余读端点 ABAC 覆盖）
- `cd backend && ./.venv/bin/python -m pytest --no-cov tests/unit/api/v1/test_project_layering.py -q`（`4 passed`）
- `cd backend && ./.venv/bin/python -m pytest --no-cov tests/unit/api/v1/test_project_layering.py tests/unit/api/v1/test_project.py -q`（`6 passed, 22 skipped`）
- `cd backend && ./.venv/bin/python -m pytest --no-cov tests/unit/middleware/test_authz_dependency.py -q`（`3 passed`）
- `cd backend && ./.venv/bin/ruff check src/api/v1/assets/project.py tests/unit/api/v1/test_project_layering.py`

### 2.18 本批新增验证（已通过，PDF 批处理 ABAC 覆盖）
- `cd backend && ./.venv/bin/python -m pytest --no-cov tests/unit/api/v1/test_pdf_batch_routes_layering.py -q`（`4 passed`）
- `cd backend && ./.venv/bin/python -m pytest --no-cov tests/unit/api/v1/test_pdf_batch_routes_layering.py tests/unit/api/v1/test_pdf_batch_routes.py -q`（`44 passed`）
- `cd backend && ./.venv/bin/python -m pytest --no-cov tests/unit/middleware/test_authz_dependency.py -q`（`3 passed`）
- `cd backend && ./.venv/bin/ruff check src/api/v1/documents/pdf_batch_routes.py tests/unit/api/v1/test_pdf_batch_routes_layering.py`

### 2.19 本批新增验证（已通过，Excel 导入 ABAC 覆盖）
- `cd backend && ./.venv/bin/python -m pytest --no-cov tests/unit/api/v1/test_excel_import_ops_layering.py tests/unit/api/v1/test_excel.py::TestImportExcelSync tests/unit/api/v1/test_excel.py::TestImportExcelAsync tests/unit/middleware/test_authz_dependency.py -q`（`14 passed`）
- `cd backend && ./.venv/bin/ruff check src/api/v1/documents/excel/import_ops.py tests/unit/api/v1/test_excel_import_ops_layering.py`

### 2.20 本批新增验证（已通过，PDF 上传 ABAC 覆盖）
- `cd backend && ./.venv/bin/python -m pytest --no-cov tests/unit/api/v1/test_pdf_upload_layering.py tests/unit/api/v1/test_pdf_upload.py tests/unit/api/v1/documents/test_pdf_import_routes.py::TestPDFUpload::test_upload_pdf_for_import tests/unit/middleware/test_authz_dependency.py -q`（`21 passed`）
- `cd backend && ./.venv/bin/ruff check src/api/v1/documents/pdf_upload.py tests/unit/api/v1/test_pdf_upload_layering.py tests/unit/api/v1/documents/test_pdf_import_routes.py`

### 2.21 本批新增验证（已通过，PDF 系统信息 ABAC 覆盖）
- `cd backend && ./.venv/bin/python -m pytest --no-cov tests/unit/api/v1/test_pdf_system_layering.py tests/unit/api/v1/documents/test_pdf_import_routes.py tests/unit/middleware/test_authz_dependency.py -q`（`15 passed`）
- `cd backend && ./.venv/bin/ruff check src/api/v1/documents/pdf_system.py tests/unit/api/v1/test_pdf_system_layering.py tests/unit/api/v1/documents/test_pdf_import_routes.py`

### 2.22 本批新增验证（已通过，Excel 模板/状态 ABAC 覆盖）
- `cd backend && ./.venv/bin/python -m pytest --no-cov tests/unit/api/v1/test_excel_template_layering.py tests/unit/api/v1/test_excel_status_layering.py tests/unit/api/v1/test_excel.py::TestDownloadTemplate tests/unit/api/v1/test_excel.py::TestGetExcelTaskStatus tests/unit/api/v1/test_excel.py::TestGetExcelHistory tests/unit/middleware/test_authz_dependency.py -q`（`15 passed`）
- `cd backend && ./.venv/bin/ruff check src/api/v1/documents/excel/template.py src/api/v1/documents/excel/status.py tests/unit/api/v1/test_excel_template_layering.py tests/unit/api/v1/test_excel_status_layering.py`

### 2.23 本批新增验证（已通过，Excel 预览 ABAC 覆盖）
- `cd backend && ./.venv/bin/python -m pytest --no-cov tests/unit/api/v1/test_excel_preview_layering.py tests/unit/api/v1/test_excel.py::TestPreviewExcelAdvanced tests/unit/api/v1/test_excel.py::TestPreviewExcel tests/unit/middleware/test_authz_dependency.py -q`（`11 passed`）
- `cd backend && ./.venv/bin/ruff check src/api/v1/documents/excel/preview.py tests/unit/api/v1/test_excel_preview_layering.py`

### 2.24 本批新增验证（已通过，Excel 导出 ABAC 覆盖）
- `cd backend && ./.venv/bin/python -m pytest --no-cov tests/unit/api/v1/test_excel_export_ops_layering.py tests/unit/api/v1/test_excel.py::TestExportExcel tests/unit/api/v1/test_excel.py::TestExportExcelAsync tests/unit/api/v1/test_excel.py::TestDownloadExportFile tests/unit/api/v1/test_excel.py::TestExportSelectedAssets tests/unit/middleware/test_authz_dependency.py -q`（`17 passed`）
- `cd backend && ./.venv/bin/ruff check src/api/v1/documents/excel/export_ops.py tests/unit/api/v1/test_excel_export_ops_layering.py`

### 2.25 本批新增验证（已通过，Excel 配置 ABAC 覆盖）
- `cd backend && ./.venv/bin/python -m pytest --no-cov tests/unit/api/v1/test_excel_config_layering.py tests/unit/api/v1/test_excel.py::TestCreateExcelConfig tests/unit/api/v1/test_excel.py::TestGetExcelConfigs tests/unit/api/v1/test_excel.py::TestGetDefaultExcelConfig tests/unit/api/v1/test_excel.py::TestGetExcelConfigDetails tests/unit/api/v1/test_excel.py::TestUpdateExcelConfig tests/unit/api/v1/test_excel.py::TestDeleteExcelConfig tests/unit/middleware/test_authz_dependency.py -q`（`16 passed`）
- `cd backend && ./.venv/bin/ruff check src/api/v1/documents/excel/config.py tests/unit/api/v1/test_excel_config_layering.py`

### 2.26 本批新增验证（已通过，PDF 批处理健康检查 ABAC 覆盖）
- `cd backend && ./.venv/bin/python -m pytest --no-cov tests/unit/api/v1/test_pdf_batch_routes_layering.py tests/unit/api/v1/test_pdf_batch_routes.py::TestBatchHealthCheck tests/unit/middleware/test_authz_dependency.py -q`（`9 passed`）
- `cd backend && ./.venv/bin/ruff check src/api/v1/documents/pdf_batch_routes.py tests/unit/api/v1/test_pdf_batch_routes_layering.py`

### 2.27 本批新增验证（已通过，PDF 兼容路由 ABAC 覆盖）
- `cd backend && ./.venv/bin/python -m pytest --no-cov tests/unit/api/v1/test_pdf_import_routes_layering.py tests/unit/api/v1/documents/test_pdf_import_routes.py::TestPDFImportInfo::test_get_pdf_import_info tests/unit/api/v1/documents/test_pdf_import_routes.py::TestPDFImportSessions::test_get_pdf_import_sessions_empty tests/unit/api/v1/documents/test_pdf_import_routes.py::TestPDFUpload::test_upload_pdf_for_import tests/unit/middleware/test_authz_dependency.py -q`（`7 passed`）
- `cd backend && ./.venv/bin/ruff check src/api/v1/documents/pdf_import_routes.py tests/unit/api/v1/test_pdf_import_routes_layering.py`

### 2.28 本批新增验证（已通过，资产批量读端点 ABAC 覆盖）
- `cd backend && ./.venv/bin/python -m pytest --no-cov tests/unit/api/v1/test_asset_batch_layering.py tests/unit/middleware/test_authz_dependency.py -q`（`8 passed`）
- `cd backend && ./.venv/bin/ruff check src/api/v1/assets/asset_batch.py tests/unit/api/v1/test_asset_batch_layering.py`

### 2.29 本批新增验证（已通过，资产批量验证端点 ABAC 覆盖）
- `cd backend && ./.venv/bin/python -m pytest --no-cov tests/unit/api/v1/test_asset_batch_layering.py tests/unit/middleware/test_authz_dependency.py -q`（`8 passed`）
- `cd backend && ./.venv/bin/ruff check src/api/v1/assets/asset_batch.py tests/unit/api/v1/test_asset_batch_layering.py`

### 2.30 本批新增验证（已通过，产权证列表端点 ABAC 覆盖）
- `cd backend && ./.venv/bin/python -m pytest --no-cov tests/unit/api/v1/test_property_certificate_authz_layering.py tests/unit/api/v1/test_property_certificate.py tests/unit/middleware/test_authz_dependency.py -q`（`6 passed, 20 skipped`）
- `cd backend && ./.venv/bin/ruff check src/api/v1/assets/property_certificate.py tests/unit/api/v1/test_property_certificate_authz_layering.py`

### 2.31 本批新增验证（已通过，分析主路由 ABAC 覆盖）
- `cd backend && ./.venv/bin/python -m pytest --no-cov tests/unit/api/v1/analytics/test_analytics_layering.py tests/unit/api/v1/analytics/test_analytics.py tests/unit/api/v1/test_analytics.py tests/unit/middleware/test_authz_dependency.py -q`（`35 passed`）
- `cd backend && ./.venv/bin/ruff check src/api/v1/analytics/analytics.py tests/unit/api/v1/analytics/test_analytics_layering.py tests/unit/api/v1/analytics/test_analytics.py tests/unit/api/v1/test_analytics.py`

### 2.32 本批新增验证（已通过，财务统计子模块 ABAC 覆盖）
- `cd backend && ./.venv/bin/python -m pytest --no-cov tests/unit/api/v1/analytics/statistics_modules/test_financial_stats_layering.py tests/unit/api/v1/analytics/statistics_modules/test_financial_stats.py tests/unit/middleware/test_authz_dependency.py -q`（`7 passed`）
- `cd backend && ./.venv/bin/ruff check src/api/v1/analytics/statistics_modules/financial_stats.py tests/unit/api/v1/analytics/statistics_modules/test_financial_stats.py tests/unit/api/v1/analytics/statistics_modules/test_financial_stats_layering.py`

### 2.33 本批新增验证（已通过，统计子模块剩余端点 ABAC 覆盖）
- `cd backend && ./.venv/bin/ruff check src/api/v1/analytics/statistics_modules/basic_stats.py src/api/v1/analytics/statistics_modules/area_stats.py src/api/v1/analytics/statistics_modules/distribution.py src/api/v1/analytics/statistics_modules/occupancy_stats.py src/api/v1/analytics/statistics_modules/trend_stats.py tests/unit/api/v1/analytics/statistics_modules/test_basic_stats.py tests/unit/api/v1/analytics/statistics_modules/test_area_stats.py tests/unit/api/v1/analytics/statistics_modules/test_occupancy_stats.py tests/unit/api/v1/analytics/statistics_modules/test_basic_stats_layering.py tests/unit/api/v1/analytics/statistics_modules/test_area_stats_layering.py tests/unit/api/v1/analytics/statistics_modules/test_distribution_layering.py tests/unit/api/v1/analytics/statistics_modules/test_occupancy_stats_layering.py tests/unit/api/v1/analytics/statistics_modules/test_trend_stats_layering.py`（通过）
- `cd backend && ./.venv/bin/python -m pytest --no-cov tests/unit/api/v1/analytics/statistics_modules/test_basic_stats_layering.py tests/unit/api/v1/analytics/statistics_modules/test_area_stats_layering.py tests/unit/api/v1/analytics/statistics_modules/test_distribution_layering.py tests/unit/api/v1/analytics/statistics_modules/test_occupancy_stats_layering.py tests/unit/api/v1/analytics/statistics_modules/test_trend_stats_layering.py tests/unit/api/v1/analytics/statistics_modules/test_basic_stats.py tests/unit/api/v1/analytics/statistics_modules/test_area_stats.py tests/unit/api/v1/analytics/statistics_modules/test_occupancy_stats.py tests/unit/api/v1/analytics/test_statistics.py -q`（`48 passed`）

### 2.34 本批新增验证（已通过，任务模块 Excel 配置端点 ABAC 覆盖）
- `cd backend && ./.venv/bin/ruff check src/api/v1/system/tasks.py tests/unit/api/v1/test_tasks_layering.py`（通过）
- `cd backend && ./.venv/bin/python -m pytest --no-cov tests/unit/api/v1/test_tasks_layering.py tests/unit/api/v1/test_tasks.py -k "excel_config or ExcelConfig" -q`（`19 passed, 36 deselected`）

### 2.35 本批新增验证（已通过，主体管理路由 ABAC 覆盖）
- `cd backend && ./.venv/bin/ruff check src/api/v1/party.py tests/unit/api/v1/test_party_layering.py`（通过）
- `cd backend && ./.venv/bin/python -m pytest --no-cov tests/unit/api/v1/test_party_layering.py tests/unit/middleware/test_authz_dependency.py -q`（`7 passed`）

### 2.36 本批新增验证（已通过，任务模块主端点 ABAC 覆盖）
- `cd backend && ./.venv/bin/ruff check src/api/v1/system/tasks.py tests/unit/api/v1/test_tasks_layering.py`（通过）
- `cd backend && ./.venv/bin/python -m pytest --no-cov tests/unit/api/v1/test_tasks_layering.py tests/unit/api/v1/test_tasks.py -q`（`56 passed`）

### 2.37 本批新增验证（已通过，历史记录路由 ABAC 覆盖）
- `cd backend && ./.venv/bin/ruff check src/api/v1/system/history.py tests/unit/api/v1/test_history_layering.py`（通过）
- `cd backend && ./.venv/bin/python -m pytest --no-cov tests/unit/api/v1/test_history_layering.py tests/unit/api/v1/test_history.py -q`（`5 passed, 4 skipped`）

### 2.38 本批新增验证（已通过，催缴管理路由 ABAC 覆盖）
- `cd backend && ./.venv/bin/ruff check src/api/v1/system/collection.py tests/unit/api/v1/test_collection_layering.py`（通过）
- `cd backend && ./.venv/bin/python -m pytest --no-cov tests/unit/api/v1/test_collection_layering.py tests/unit/api/v1/test_collection.py -q`（`30 passed`）

### 2.39 本批新增验证（已通过，联系人管理路由 ABAC 覆盖）
- `cd backend && ./.venv/bin/ruff check src/api/v1/system/contact.py tests/unit/api/v1/test_contact_layering.py`（通过）
- `cd backend && ./.venv/bin/python -m pytest --no-cov tests/unit/api/v1/test_contact_layering.py tests/unit/api/v1/test_contact.py -q`（`4 passed, 28 skipped`）

### 2.40 本批新增验证（已通过，统一字典路由 ABAC 覆盖）
- `cd backend && ./.venv/bin/ruff check src/api/v1/system/dictionaries.py tests/unit/api/v1/test_dictionaries_layering.py tests/unit/api/v1/test_dictionaries.py`（通过）
- `cd backend && ./.venv/bin/python -m pytest --no-cov tests/unit/api/v1/test_dictionaries_layering.py tests/unit/api/v1/test_dictionaries.py tests/unit/middleware/test_authz_dependency.py -q`（`5 passed, 8 skipped`）
- 说明：`test_dictionaries.py` 为数据库依赖用例，当前环境缺少 `TEST_DATABASE_URL` 时按预期跳过，不影响本批 ABAC 分层与依赖注入验证结论。

### 2.41 本批新增验证（已通过，通知路由 ABAC 覆盖）
- `cd backend && ./.venv/bin/ruff check src/api/v1/system/notifications.py tests/unit/api/v1/test_notifications_layering.py tests/unit/api/v1/test_notifications.py`（通过）
- `cd backend && ./.venv/bin/python -m pytest --no-cov tests/unit/api/v1/test_notifications_layering.py tests/unit/api/v1/test_notifications.py tests/unit/middleware/test_authz_dependency.py -q`（`8 passed, 19 skipped`）
- 说明：`test_notifications.py` 的 db-backed 用例受 `TEST_DATABASE_URL` 凭据认证失败影响按预期跳过，不影响本批 ABAC 分层与依赖注入验证结论。

### 2.42 本批新增验证（已通过，操作日志路由 ABAC 覆盖）
- `cd backend && ./.venv/bin/ruff check src/api/v1/system/operation_logs.py tests/unit/api/v1/test_operation_logs_layering.py tests/unit/api/v1/test_operation_logs.py`（通过）
- `cd backend && ./.venv/bin/python -m pytest --no-cov tests/unit/api/v1/test_operation_logs_layering.py tests/unit/api/v1/test_operation_logs.py tests/unit/middleware/test_authz_dependency.py -q`（`8 passed, 4 skipped`）
- 说明：`test_operation_logs.py` 的 db-backed 用例受 `TEST_DATABASE_URL` 缺失影响按预期跳过，不影响本批 ABAC 分层与依赖注入验证结论。

### 2.43 本批新增验证（已通过，枚举字段路由 ABAC 覆盖）
- `cd backend && ./.venv/bin/ruff check src/api/v1/system/enum_field.py tests/unit/api/v1/test_enum_field_layering.py tests/unit/api/v1/test_enum_field_api.py`（通过）
- `cd backend && ./.venv/bin/python -m pytest --no-cov tests/unit/api/v1/test_enum_field_layering.py tests/unit/api/v1/test_enum_field_api.py tests/unit/middleware/test_authz_dependency.py -q`（`14 passed`）

### 2.44 本批新增验证（已通过，数据备份路由 ABAC 覆盖）
- `cd backend && ./.venv/bin/ruff check src/api/v1/system/backup.py tests/unit/api/v1/test_backup_layering.py tests/unit/api/v1/test_backup.py`（通过）
- `cd backend && ./.venv/bin/python -m pytest --no-cov tests/unit/api/v1/test_backup_layering.py tests/unit/api/v1/test_backup.py tests/unit/middleware/test_authz_dependency.py -q`（`40 passed`）

### 2.45 本批新增验证（已通过，系统核心路由 ABAC 覆盖）
- `cd backend && ./.venv/bin/ruff check src/api/v1/system/system.py tests/unit/api/v1/test_system_layering.py tests/unit/api/v1/test_system.py`（通过）
- `cd backend && ./.venv/bin/python -m pytest --no-cov tests/unit/api/v1/test_system_layering.py tests/unit/middleware/test_authz_dependency.py -q`（`5 passed`）
- 说明：`tests/unit/api/v1/test_system.py` 在当前测试库环境执行会触发 Alembic 初始化冲突（`organizations already exists`），该问题与本批 ABAC 依赖注入改动无关，故本批采用“不依赖该迁移链路”的分层与鉴权依赖基线集进行验证。

### 2.46 本批新增验证（已通过，LLM Prompt 路由 ABAC 覆盖）
- Gate 盘点：
  - `cd backend && { grep -rEn "PermissionGrant|ResourcePermission|OrganizationPermissionService|OrganizationPermissionChecker" src/api/v1 src/services src/middleware src/crud/rbac.py src/models/rbac.py src/crud/field_whitelist.py --include="*.py" > /tmp/bg3.txt || true; } && echo "BG3_NON_DEPRECATED=$(grep -Evc 'DEPRECATED|deprecated' /tmp/bg3.txt || true)"`（`BG3_NON_DEPRECATED=0`）
  - `cd backend && { grep -rEn "ownership_id|ownership_ids" src/models/rent_contract.py src/services/rent_contract/ src/crud/rent_contract.py src/crud/collection.py src/api/v1/rent_contracts/ --include="*.py" > /tmp/bg4.txt || true; } && echo "BG4_NON_DEPRECATED=$(grep -Evc 'DEPRECATED|deprecated' /tmp/bg4.txt || true)"`（`BG4_NON_DEPRECATED=0`）
- `cd backend && ./.venv/bin/ruff check src/api/v1/llm_prompts.py tests/unit/api/v1/test_llm_prompts_layering.py tests/unit/api/v1/test_llm_prompts.py`（通过）
- `cd backend && ./.venv/bin/python -m pytest --no-cov tests/unit/api/v1/test_llm_prompts_layering.py tests/unit/middleware/test_authz_dependency.py -q`（`5 passed`）
- 说明：`tests/unit/api/v1/test_llm_prompts.py` 在当前测试库环境执行会触发 Alembic 初始化冲突（`organizations already exists`），该问题与本批 ABAC 依赖注入改动无关。

### 2.47 本批新增验证（已通过，错误恢复路由 ABAC 覆盖）
- Gate 盘点：
  - `cd backend && { grep -rEn "PermissionGrant|ResourcePermission|OrganizationPermissionService|OrganizationPermissionChecker" src/api/v1 src/services src/middleware src/crud/rbac.py src/models/rbac.py src/crud/field_whitelist.py --include="*.py" > /tmp/bg3.txt || true; } && echo "BG3_NON_DEPRECATED=$(grep -Evc 'DEPRECATED|deprecated' /tmp/bg3.txt || true)"`（`BG3_NON_DEPRECATED=0`）
  - `cd backend && { grep -rEn "ownership_id|ownership_ids" src/models/rent_contract.py src/services/rent_contract/ src/crud/rent_contract.py src/crud/collection.py src/api/v1/rent_contracts/ --include="*.py" > /tmp/bg4.txt || true; } && echo "BG4_NON_DEPRECATED=$(grep -Evc 'DEPRECATED|deprecated' /tmp/bg4.txt || true)"`（`BG4_NON_DEPRECATED=0`）
- `cd backend && ./.venv/bin/ruff check src/api/v1/system/error_recovery.py tests/unit/api/v1/test_error_recovery_layering.py tests/unit/api/v1/test_error_recovery.py`（通过）
- `cd backend && ./.venv/bin/python -m pytest --no-cov tests/unit/api/v1/test_error_recovery_layering.py tests/unit/api/v1/test_error_recovery.py tests/unit/middleware/test_authz_dependency.py -q`（`49 passed`）

### 2.48 本批新增验证（已通过，系统监控路由 ABAC 覆盖）
- Gate 盘点：
  - `cd backend && { grep -rEn "PermissionGrant|ResourcePermission|OrganizationPermissionService|OrganizationPermissionChecker" src/api/v1 src/services src/middleware src/crud/rbac.py src/models/rbac.py src/crud/field_whitelist.py --include="*.py" > /tmp/bg3.txt || true; } && echo "BG3_NON_DEPRECATED=$(grep -Evc 'DEPRECATED|deprecated' /tmp/bg3.txt || true)"`（`BG3_NON_DEPRECATED=0`）
  - `cd backend && { grep -rEn "ownership_id|ownership_ids" src/models/rent_contract.py src/services/rent_contract/ src/crud/rent_contract.py src/crud/collection.py src/api/v1/rent_contracts/ --include="*.py" > /tmp/bg4.txt || true; } && echo "BG4_NON_DEPRECATED=$(grep -Evc 'DEPRECATED|deprecated' /tmp/bg4.txt || true)"`（`BG4_NON_DEPRECATED=0`）
- `cd backend && ./.venv/bin/ruff check src/api/v1/system/monitoring.py tests/unit/api/v1/test_monitoring_layering.py tests/unit/api/v1/test_monitoring.py`（通过）
- `cd backend && ./.venv/bin/python -m pytest --no-cov tests/unit/api/v1/test_monitoring_layering.py tests/unit/api/v1/test_monitoring.py tests/unit/middleware/test_authz_dependency.py -q`（`30 passed`）

### 2.49 本批新增验证（已通过，系统设置路由 ABAC 覆盖）
- Gate 盘点：
  - `cd backend && { grep -rEn "PermissionGrant|ResourcePermission|OrganizationPermissionService|OrganizationPermissionChecker" src/api/v1 src/services src/middleware src/crud/rbac.py src/models/rbac.py src/crud/field_whitelist.py --include="*.py" > /tmp/bg3.txt || true; } && echo "BG3_NON_DEPRECATED=$(grep -Evc 'DEPRECATED|deprecated' /tmp/bg3.txt || true)"`（`BG3_NON_DEPRECATED=0`）
  - `cd backend && { grep -rEn "ownership_id|ownership_ids" src/models/rent_contract.py src/services/rent_contract/ src/crud/rent_contract.py src/crud/collection.py src/api/v1/rent_contracts/ --include="*.py" > /tmp/bg4.txt || true; } && echo "BG4_NON_DEPRECATED=$(grep -Evc 'DEPRECATED|deprecated' /tmp/bg4.txt || true)"`（`BG4_NON_DEPRECATED=0`）
- `cd backend && ./.venv/bin/ruff check src/api/v1/system/system_settings.py tests/unit/api/v1/test_system_settings_layering.py tests/unit/api/v1/test_system_settings.py`（通过）
- `cd backend && ./.venv/bin/python -m pytest --no-cov tests/unit/api/v1/test_system_settings_layering.py tests/unit/api/v1/test_system_settings.py tests/unit/middleware/test_authz_dependency.py -q`（`17 passed`）

### 2.50 本批新增验证（已通过，角色管理路由 ABAC 覆盖）
- Gate 盘点：
  - `cd backend && { grep -rEn "PermissionGrant|ResourcePermission|OrganizationPermissionService|OrganizationPermissionChecker" src/api/v1 src/services src/middleware src/crud/rbac.py src/models/rbac.py src/crud/field_whitelist.py --include="*.py" > /tmp/bg3.txt || true; } && echo "BG3_NON_DEPRECATED=$(grep -Evc 'DEPRECATED|deprecated' /tmp/bg3.txt || true)"`（`BG3_NON_DEPRECATED=0`）
  - `cd backend && { grep -rEn "ownership_id|ownership_ids" src/models/rent_contract.py src/services/rent_contract/ src/crud/rent_contract.py src/crud/collection.py src/api/v1/rent_contracts/ --include="*.py" > /tmp/bg4.txt || true; } && echo "BG4_NON_DEPRECATED=$(grep -Evc 'DEPRECATED|deprecated' /tmp/bg4.txt || true)"`（`BG4_NON_DEPRECATED=0`）
- `cd backend && ./.venv/bin/ruff check src/api/v1/auth/roles.py tests/unit/api/v1/test_roles_layering.py tests/unit/api/v1/test_roles.py tests/unit/api/v1/test_roles_permission_grants.py`（通过）
- `cd backend && ./.venv/bin/python -m pytest --no-cov tests/unit/api/v1/test_roles_layering.py tests/unit/api/v1/test_roles.py tests/unit/api/v1/test_roles_permission_grants.py tests/unit/middleware/test_authz_dependency.py -q`（`23 passed`）

### 2.51 本批新增验证（已通过，组织管理路由 ABAC 覆盖）
- Gate 盘点：
  - `cd backend && { grep -rEn "PermissionGrant|ResourcePermission|OrganizationPermissionService|OrganizationPermissionChecker" src/api/v1 src/services src/middleware src/crud/rbac.py src/models/rbac.py src/crud/field_whitelist.py --include="*.py" > /tmp/bg3.txt || true; } && echo "BG3_NON_DEPRECATED=$(grep -Evc 'DEPRECATED|deprecated' /tmp/bg3.txt || true)"`（`BG3_NON_DEPRECATED=0`）
  - `cd backend && { grep -rEn "ownership_id|ownership_ids" src/models/rent_contract.py src/services/rent_contract/ src/crud/rent_contract.py src/crud/collection.py src/api/v1/rent_contracts/ --include="*.py" > /tmp/bg4.txt || true; } && echo "BG4_NON_DEPRECATED=$(grep -Evc 'DEPRECATED|deprecated' /tmp/bg4.txt || true)"`（`BG4_NON_DEPRECATED=0`）
- `cd backend && ./.venv/bin/ruff check src/api/v1/auth/organization.py tests/unit/api/v1/test_organization_layering.py tests/unit/api/v1/test_organization.py`（通过）
- `cd backend && ./.venv/bin/python -m pytest --no-cov tests/unit/api/v1/test_organization_layering.py tests/unit/api/v1/test_organization.py tests/unit/middleware/test_authz_dependency.py -q`（`24 passed`）

### 2.52 本批新增验证（已通过，会话管理路由 ABAC 覆盖）
- Gate 盘点：
  - `cd backend && { grep -rEn "PermissionGrant|ResourcePermission|OrganizationPermissionService|OrganizationPermissionChecker" src/api/v1 src/services src/middleware src/crud/rbac.py src/models/rbac.py src/crud/field_whitelist.py --include="*.py" > /tmp/bg3.txt || true; } && echo "BG3_NON_DEPRECATED=$(grep -Evc 'DEPRECATED|deprecated' /tmp/bg3.txt || true)"`（`BG3_NON_DEPRECATED=0`）
  - `cd backend && { grep -rEn "ownership_id|ownership_ids" src/models/rent_contract.py src/services/rent_contract/ src/crud/rent_contract.py src/crud/collection.py src/api/v1/rent_contracts/ --include="*.py" > /tmp/bg4.txt || true; } && echo "BG4_NON_DEPRECATED=$(grep -Evc 'DEPRECATED|deprecated' /tmp/bg4.txt || true)"`（`BG4_NON_DEPRECATED=0`）
- `cd backend && ./.venv/bin/ruff check src/api/v1/auth/auth_modules/sessions.py tests/unit/api/v1/test_auth_sessions_layering.py`（通过）
- `cd backend && ./.venv/bin/python -m pytest --no-cov tests/unit/api/v1/test_auth_sessions_layering.py tests/unit/middleware/test_authz_dependency.py -q`（`8 passed`）

### 2.53 本批新增验证（已通过，审计日志路由 ABAC 覆盖）
- Gate 盘点：
  - `cd backend && { grep -rEn "PermissionGrant|ResourcePermission|OrganizationPermissionService|OrganizationPermissionChecker" src/api/v1 src/services src/middleware src/crud/rbac.py src/models/rbac.py src/crud/field_whitelist.py --include="*.py" > /tmp/bg3.txt || true; } && echo "BG3_NON_DEPRECATED=$(grep -Evc 'DEPRECATED|deprecated' /tmp/bg3.txt || true)"`（`BG3_NON_DEPRECATED=0`）
  - `cd backend && { grep -rEn "ownership_id|ownership_ids" src/models/rent_contract.py src/services/rent_contract/ src/crud/rent_contract.py src/crud/collection.py src/api/v1/rent_contracts/ --include="*.py" > /tmp/bg4.txt || true; } && echo "BG4_NON_DEPRECATED=$(grep -Evc 'DEPRECATED|deprecated' /tmp/bg4.txt || true)"`（`BG4_NON_DEPRECATED=0`）
- `cd backend && ./.venv/bin/ruff check src/api/v1/auth/auth_modules/audit.py tests/unit/api/v1/test_auth_audit_layering.py`（通过）
- `cd backend && ./.venv/bin/python -m pytest --no-cov tests/unit/api/v1/test_auth_audit_layering.py tests/unit/middleware/test_authz_dependency.py -q`（`7 passed`）

### 2.54 本批新增验证（已通过，安全配置路由 ABAC 覆盖）
- Gate 盘点：
  - `cd backend && { grep -rEn "PermissionGrant|ResourcePermission|OrganizationPermissionService|OrganizationPermissionChecker" src/api/v1 src/services src/middleware src/crud/rbac.py src/models/rbac.py src/crud/field_whitelist.py --include="*.py" > /tmp/bg3.txt || true; } && echo "BG3_NON_DEPRECATED=$(grep -Evc 'DEPRECATED|deprecated' /tmp/bg3.txt || true)"`（`BG3_NON_DEPRECATED=0`）
  - `cd backend && { grep -rEn "ownership_id|ownership_ids" src/models/rent_contract.py src/services/rent_contract/ src/crud/rent_contract.py src/crud/collection.py src/api/v1/rent_contracts/ --include="*.py" > /tmp/bg4.txt || true; } && echo "BG4_NON_DEPRECATED=$(grep -Evc 'DEPRECATED|deprecated' /tmp/bg4.txt || true)"`（`BG4_NON_DEPRECATED=0`）
- `cd backend && ./.venv/bin/ruff check src/api/v1/auth/auth_modules/security.py tests/unit/api/v1/test_auth_security_layering.py`（通过）
- `cd backend && ./.venv/bin/python -m pytest --no-cov tests/unit/api/v1/test_auth_security_layering.py tests/unit/middleware/test_authz_dependency.py -q`（`6 passed`）

### 2.55 本批新增验证（已通过，用户管理路由 ABAC 覆盖）
- Gate 盘点：
  - `cd backend && { grep -rEn "PermissionGrant|ResourcePermission|OrganizationPermissionService|OrganizationPermissionChecker" src/api/v1 src/services src/middleware src/crud/rbac.py src/models/rbac.py src/crud/field_whitelist.py --include="*.py" > /tmp/bg3.txt || true; } && echo "BG3_NON_DEPRECATED=$(grep -Evc 'DEPRECATED|deprecated' /tmp/bg3.txt || true)"`（`BG3_NON_DEPRECATED=0`）
  - `cd backend && { grep -rEn "ownership_id|ownership_ids" src/models/rent_contract.py src/services/rent_contract/ src/crud/rent_contract.py src/crud/collection.py src/api/v1/rent_contracts/ --include="*.py" > /tmp/bg4.txt || true; } && echo "BG4_NON_DEPRECATED=$(grep -Evc 'DEPRECATED|deprecated' /tmp/bg4.txt || true)"`（`BG4_NON_DEPRECATED=0`）
- `cd backend && ./.venv/bin/ruff check src/api/v1/auth/auth_modules/users.py tests/unit/api/v1/test_users_layering.py tests/unit/api/v1/test_users.py`（通过）
- `cd backend && ./.venv/bin/python -m pytest --no-cov tests/unit/api/v1/test_users_layering.py tests/unit/api/v1/test_users.py tests/unit/middleware/test_authz_dependency.py -q`（`30 passed`）

### 2.56 本批新增验证（已通过，system_monitoring 子模块 ABAC 覆盖）
- Gate 盘点：
  - `cd backend && { grep -rEn "PermissionGrant|ResourcePermission|OrganizationPermissionService|OrganizationPermissionChecker" src/api/v1 src/services src/middleware src/crud/rbac.py src/models/rbac.py src/crud/field_whitelist.py --include="*.py" > /tmp/bg3.txt || true; } && echo "BG3_NON_DEPRECATED=$(grep -Evc 'DEPRECATED|deprecated' /tmp/bg3.txt || true)"`（`BG3_NON_DEPRECATED=0`）
  - `cd backend && { grep -rEn "ownership_id|ownership_ids" src/models/rent_contract.py src/services/rent_contract/ src/crud/rent_contract.py src/crud/collection.py src/api/v1/rent_contracts/ --include="*.py" > /tmp/bg4.txt || true; } && echo "BG4_NON_DEPRECATED=$(grep -Evc 'DEPRECATED|deprecated' /tmp/bg4.txt || true)"`（`BG4_NON_DEPRECATED=0`）
- `cd backend && ./.venv/bin/ruff check src/api/v1/system/system_monitoring/collectors.py src/api/v1/system/system_monitoring/health.py src/api/v1/system/system_monitoring/endpoints.py src/api/v1/system/system_monitoring/database_endpoints.py tests/unit/api/v1/test_system_monitoring_layering.py`（通过）
- `cd backend && ./.venv/bin/python -m pytest --no-cov tests/unit/api/v1/test_system_monitoring_layering.py tests/unit/api/v1/system/system_monitoring/test_health.py tests/unit/middleware/test_authz_dependency.py -q`（`21 passed`）

### 2.57 本批新增验证（已通过，统计聚合包装路由 ABAC 覆盖）
- `cd backend && ./.venv/bin/ruff check src/api/v1/analytics/statistics.py tests/unit/api/v1/test_statistics_router_layering.py tests/unit/api/v1/test_statistics.py tests/unit/api/v1/analytics/test_statistics.py`（通过）
- `cd backend && ./.venv/bin/python -m pytest --no-cov tests/unit/api/v1/test_statistics_router_layering.py tests/unit/api/v1/test_statistics.py tests/unit/api/v1/analytics/test_statistics.py -q`（`17 passed`）

### 2.58 本批新增验证（已通过，PDF 导入包装路由 ABAC 覆盖）
- `cd backend && ./.venv/bin/ruff check src/api/v1/documents/pdf_import.py tests/unit/api/v1/test_pdf_import_layering.py tests/unit/api/v1/documents/test_pdf_import_routes.py`（通过）
- `cd backend && ./.venv/bin/python -m pytest --no-cov tests/unit/api/v1/test_pdf_import_layering.py tests/unit/api/v1/documents/test_pdf_import_routes.py -q`（`13 passed`）

### 2.59 本批新增验证（已通过，Excel 配置兼容链路遗留权限依赖清理）
- Gate 盘点：
  - `cd backend && { grep -rEn "PermissionGrant|ResourcePermission|OrganizationPermissionService|OrganizationPermissionChecker" src/api/v1 src/services src/middleware src/crud/rbac.py src/models/rbac.py src/crud/field_whitelist.py --include="*.py" > /tmp/bg3.txt || true; } && echo "BG3_NON_DEPRECATED=$(grep -Evc 'DEPRECATED|deprecated' /tmp/bg3.txt || true)"`（`BG3_NON_DEPRECATED=0`）
  - `cd backend && { grep -rEn "ownership_id|ownership_ids" src/models/rent_contract.py src/services/rent_contract/ src/crud/rent_contract.py src/crud/collection.py src/api/v1/rent_contracts/ --include="*.py" > /tmp/bg4.txt || true; } && echo "BG4_NON_DEPRECATED=$(grep -Evc 'DEPRECATED|deprecated' /tmp/bg4.txt || true)"`（`BG4_NON_DEPRECATED=0`）
- `cd backend && ./.venv/bin/ruff check src/api/v1/documents/excel/config.py src/api/v1/system/tasks.py tests/unit/api/v1/test_excel_config_layering.py tests/unit/api/v1/test_tasks_layering.py`（通过）
- `cd backend && ./.venv/bin/python -m pytest --no-cov tests/unit/api/v1/test_excel_config_layering.py tests/unit/api/v1/test_tasks_layering.py tests/unit/api/v1/test_tasks.py tests/unit/middleware/test_authz_dependency.py -q`（`60 passed`）

### 2.60 本批新增验证（已通过，错误恢复路由遗留权限依赖清理）
- Gate 盘点：
  - `cd backend && { grep -rEn "PermissionGrant|ResourcePermission|OrganizationPermissionService|OrganizationPermissionChecker" src/api/v1 src/services src/middleware src/crud/rbac.py src/models/rbac.py src/crud/field_whitelist.py --include="*.py" > /tmp/bg3.txt || true; } && echo "BG3_NON_DEPRECATED=$(grep -Evc 'DEPRECATED|deprecated' /tmp/bg3.txt || true)"`（`BG3_NON_DEPRECATED=0`）
  - `cd backend && { grep -rEn "ownership_id|ownership_ids" src/models/rent_contract.py src/services/rent_contract/ src/crud/rent_contract.py src/crud/collection.py src/api/v1/rent_contracts/ --include="*.py" > /tmp/bg4.txt || true; } && echo "BG4_NON_DEPRECATED=$(grep -Evc 'DEPRECATED|deprecated' /tmp/bg4.txt || true)"`（`BG4_NON_DEPRECATED=0`）
- `cd backend && ./.venv/bin/ruff check src/api/v1/system/error_recovery.py tests/unit/api/v1/test_error_recovery_layering.py`（通过）
- `cd backend && ./.venv/bin/python -m pytest --no-cov tests/unit/api/v1/test_error_recovery_layering.py tests/unit/api/v1/test_error_recovery.py tests/unit/middleware/test_authz_dependency.py -q`（`49 passed`）

### 2.61 本批新增验证（已通过，assets 遗留权限链路清理）
- Gate 盘点：
  - `cd backend && { grep -rEn "PermissionGrant|ResourcePermission|OrganizationPermissionService|OrganizationPermissionChecker" src/api/v1 src/services src/middleware src/crud/rbac.py src/models/rbac.py src/crud/field_whitelist.py --include="*.py" > /tmp/bg3.txt || true; } && echo "BG3_NON_DEPRECATED=$(grep -Evc 'DEPRECATED|deprecated' /tmp/bg3.txt || true)"`（`BG3_NON_DEPRECATED=0`）
  - `cd backend && { grep -rEn "ownership_id|ownership_ids" src/models/rent_contract.py src/services/rent_contract/ src/crud/rent_contract.py src/crud/collection.py src/api/v1/rent_contracts/ --include="*.py" > /tmp/bg4.txt || true; } && echo "BG4_NON_DEPRECATED=$(grep -Evc 'DEPRECATED|deprecated' /tmp/bg4.txt || true)"`（`BG4_NON_DEPRECATED=0`）
- `cd backend && ./.venv/bin/ruff check src/api/v1/assets/assets.py src/api/v1/assets/asset_batch.py src/api/v1/assets/asset_import.py src/api/v1/assets/property_certificate.py tests/unit/api/v1/test_assets_authz_layering.py tests/unit/api/v1/test_asset_batch_layering.py tests/unit/api/v1/test_asset_import_layering.py tests/unit/api/v1/test_property_certificate_authz_layering.py`（通过）
- `cd backend && ./.venv/bin/python -m pytest --no-cov tests/unit/api/v1/test_assets_authz_layering.py tests/unit/api/v1/test_asset_batch_layering.py tests/unit/api/v1/test_asset_import_layering.py tests/unit/api/v1/test_property_certificate_authz_layering.py tests/unit/api/v1/test_property_certificate.py tests/unit/api/test_asset_batch_api.py tests/unit/api/test_asset_import_api.py tests/unit/middleware/test_authz_dependency.py -q`（`64 passed`）

### 2.62 本批新增验证（已通过，回归稳态收口）
- `cd backend && ./.venv/bin/ruff check tests/integration/test_asset_lifecycle.py tests/unit/services/test_rent_contract_service.py`（通过）
- `cd backend && ./.venv/bin/python -m pytest --no-cov tests/unit/services/test_rent_contract_service.py::TestRentContractService::test_get_contract_page_async_delegates_to_crud -q`（`1 passed`）
- `cd backend && ./.venv/bin/python -m pytest --no-cov -m "not slow and not e2e" -x -q`（`4536 passed, 8 skipped, 14 deselected`）

### 2.63 本批新增验证（已通过，P2d/Gate 全量收口复核）
- `cd backend && ./.venv/bin/python -m pytest --no-cov tests/unit/migration/test_backfill.py -q`（`5 passed`）
- `cd backend && if ! grep -rEql "TenantFilter|_apply_tenant_filter|tenant_filter\\.organization_ids" src/ --include="*.py"; then echo "BG1_STATUS=PASS"; else echo "BG1_STATUS=FAIL"; fi`（`BG1_STATUS=PASS`）
- `cd backend && { grep -rEn "organization_id" src/models/rbac.py src/crud/rbac.py src/crud/field_whitelist.py src/services/permission/ --include="*.py" > /tmp/bg2.txt || true; } && echo "BG2_NON_DEPRECATED=$(grep -Evc 'DEPRECATED|deprecated' /tmp/bg2.txt || true)"`（`BG2_NON_DEPRECATED=0`）
- `cd backend && { grep -rEn "PermissionGrant|ResourcePermission|OrganizationPermissionService|OrganizationPermissionChecker" src/api/v1 src/services src/middleware src/crud/rbac.py src/models/rbac.py src/crud/field_whitelist.py --include="*.py" > /tmp/bg3.txt || true; } && echo "BG3_NON_DEPRECATED=$(grep -Evc 'DEPRECATED|deprecated' /tmp/bg3.txt || true)"`（`BG3_NON_DEPRECATED=0`）
- `cd backend && { grep -rEn "ownership_id|ownership_ids" src/models/rent_contract.py src/services/rent_contract/ src/crud/rent_contract.py src/crud/collection.py src/api/v1/rent_contracts/ --include="*.py" > /tmp/bg4.txt || true; } && echo "BG4_NON_DEPRECATED=$(grep -Evc 'DEPRECATED|deprecated' /tmp/bg4.txt || true)"`（`BG4_NON_DEPRECATED=0`）
- `cd backend && TEST_DATABASE_URL='postgresql+psycopg://zcgl_user:postgres@127.0.0.1:5432/zcgl_test' DATABASE_URL='postgresql+psycopg://zcgl_user:postgres@127.0.0.1:5432/zcgl_test' ./.venv/bin/python - <<'PY' ...`（`ROLES_SCOPE_INVALID_COUNT=0`）

### 2.64 本批新增验证（已通过，维护批次-Gate 漂移复核）
- `cd backend && ./.venv/bin/python -m pytest --no-cov tests/unit/migration/test_backfill.py -q`（`5 passed`）
- `cd backend && if ! grep -rEql "TenantFilter|_apply_tenant_filter|tenant_filter\\.organization_ids" src/ --include="*.py"; then echo "BG1_STATUS=PASS"; else echo "BG1_STATUS=FAIL"; fi`（`BG1_STATUS=PASS`）
- `cd backend && { grep -rEn "organization_id" src/models/rbac.py src/crud/rbac.py src/crud/field_whitelist.py src/services/permission/ --include="*.py" > /tmp/bg2.txt || true; } && echo "BG2_NON_DEPRECATED=$(grep -Evc 'DEPRECATED|deprecated' /tmp/bg2.txt || true)"`（`BG2_NON_DEPRECATED=0`）
- `cd backend && { grep -rEn "PermissionGrant|ResourcePermission|OrganizationPermissionService|OrganizationPermissionChecker" src/api/v1 src/services src/middleware src/crud/rbac.py src/models/rbac.py src/crud/field_whitelist.py --include="*.py" > /tmp/bg3.txt || true; } && echo "BG3_NON_DEPRECATED=$(grep -Evc 'DEPRECATED|deprecated' /tmp/bg3.txt || true)"`（`BG3_NON_DEPRECATED=0`）
- `cd backend && { grep -rEn "ownership_id|ownership_ids" src/models/rent_contract.py src/services/rent_contract/ src/crud/rent_contract.py src/crud/collection.py src/api/v1/rent_contracts/ --include="*.py" > /tmp/bg4.txt || true; } && echo "BG4_NON_DEPRECATED=$(grep -Evc 'DEPRECATED|deprecated' /tmp/bg4.txt || true)"`（`BG4_NON_DEPRECATED=0`）
- `cd backend && TEST_DATABASE_URL='postgresql+psycopg://zcgl_user:postgres@127.0.0.1:5432/zcgl_test' DATABASE_URL='postgresql+psycopg://zcgl_user:postgres@127.0.0.1:5432/zcgl_test' ./.venv/bin/python - <<'PY'\nfrom sqlalchemy import create_engine, text\nurl = \"postgresql+psycopg://zcgl_user:postgres@127.0.0.1:5432/zcgl_test\"\nengine = create_engine(url)\nwith engine.connect() as conn:\n    count = conn.execute(\n        text(\"SELECT COUNT(*) FROM roles WHERE scope NOT IN ('SYSTEM','ORGANIZATION')\")\n    ).scalar_one()\nprint(f\"ROLES_SCOPE_INVALID_COUNT={count}\")\nPY`（`ROLES_SCOPE_INVALID_COUNT=0`）

### 2.65 本批新增验证（已通过，鉴权/组织可见范围抽样回归）
- `cd backend && ./.venv/bin/python -m pytest --no-cov tests/unit/middleware/test_authz_dependency.py tests/unit/api/v1/test_organization_layering.py tests/unit/api/v1/test_organization.py tests/integration/api/test_project_visibility_real.py tests/integration/crud/test_project_tenant_scope_real.py tests/integration/test_asset_lifecycle.py -q`（`29 passed`）

### 2.66 本批新增验证（已通过，鉴权链路扩展抽样回归 + Gate 复核）
- `cd backend && ./.venv/bin/python -m pytest --no-cov tests/unit/middleware/test_authz_dependency.py tests/unit/api/v1/test_roles_layering.py tests/unit/api/v1/test_users_layering.py tests/unit/api/v1/test_auth_sessions_layering.py tests/unit/api/v1/test_auth_audit_layering.py tests/unit/api/v1/test_auth_security_layering.py tests/unit/api/v1/test_organization_layering.py tests/unit/services/test_authz_cache.py tests/unit/services/test_authz_events.py tests/unit/services/test_data_policy_service.py tests/integration/api/test_project_visibility_real.py tests/integration/crud/test_project_tenant_scope_real.py -q`（`41 passed`）
- `cd backend && if ! grep -rEql "TenantFilter|_apply_tenant_filter|tenant_filter\\.organization_ids" src/ --include="*.py"; then echo "BG1_STATUS=PASS"; else echo "BG1_STATUS=FAIL"; fi`（`BG1_STATUS=PASS`）
- `cd backend && { grep -rEn "organization_id" src/models/rbac.py src/crud/rbac.py src/crud/field_whitelist.py src/services/permission/ --include="*.py" > /tmp/bg2.txt || true; } && echo "BG2_NON_DEPRECATED=$(grep -Evc 'DEPRECATED|deprecated' /tmp/bg2.txt || true)"`（`BG2_NON_DEPRECATED=0`）
- `cd backend && { grep -rEn "PermissionGrant|ResourcePermission|OrganizationPermissionService|OrganizationPermissionChecker" src/api/v1 src/services src/middleware src/crud/rbac.py src/models/rbac.py src/crud/field_whitelist.py --include="*.py" > /tmp/bg3.txt || true; } && echo "BG3_NON_DEPRECATED=$(grep -Evc 'DEPRECATED|deprecated' /tmp/bg3.txt || true)"`（`BG3_NON_DEPRECATED=0`）
- `cd backend && { grep -rEn "ownership_id|ownership_ids" src/models/rent_contract.py src/services/rent_contract/ src/crud/rent_contract.py src/crud/collection.py src/api/v1/rent_contracts/ --include="*.py" > /tmp/bg4.txt || true; } && echo "BG4_NON_DEPRECATED=$(grep -Evc 'DEPRECATED|deprecated' /tmp/bg4.txt || true)"`（`BG4_NON_DEPRECATED=0`）

### 2.67 本批新增验证（已通过，扩大回归复跑）
- `cd backend && ./.venv/bin/python -m pytest --no-cov -m "not slow and not e2e" -x -q`（`4536 passed, 8 skipped, 14 deselected`）

### 2.68 本批新增验证（已通过，Gate + 迁移 + 角色作用域复核）
- `cd backend && ./.venv/bin/python -m pytest --no-cov tests/unit/migration/test_backfill.py -q`（`5 passed`）
- `cd backend && if ! grep -rEql "TenantFilter|_apply_tenant_filter|tenant_filter\\.organization_ids" src/ --include="*.py"; then echo "BG1_STATUS=PASS"; else echo "BG1_STATUS=FAIL"; fi`（`BG1_STATUS=PASS`）
- `cd backend && { grep -rEn "organization_id" src/models/rbac.py src/crud/rbac.py src/crud/field_whitelist.py src/services/permission/ --include="*.py" > /tmp/bg2.txt || true; } && echo "BG2_NON_DEPRECATED=$(grep -Evc 'DEPRECATED|deprecated' /tmp/bg2.txt || true)"`（`BG2_NON_DEPRECATED=0`）
- `cd backend && { grep -rEn "PermissionGrant|ResourcePermission|OrganizationPermissionService|OrganizationPermissionChecker" src/api/v1 src/services src/middleware src/crud/rbac.py src/models/rbac.py src/crud/field_whitelist.py --include="*.py" > /tmp/bg3.txt || true; } && echo "BG3_NON_DEPRECATED=$(grep -Evc 'DEPRECATED|deprecated' /tmp/bg3.txt || true)"`（`BG3_NON_DEPRECATED=0`）
- `cd backend && { grep -rEn "ownership_id|ownership_ids" src/models/rent_contract.py src/services/rent_contract/ src/crud/rent_contract.py src/crud/collection.py src/api/v1/rent_contracts/ --include="*.py" > /tmp/bg4.txt || true; } && echo "BG4_NON_DEPRECATED=$(grep -Evc 'DEPRECATED|deprecated' /tmp/bg4.txt || true)"`（`BG4_NON_DEPRECATED=0`）
- `cd backend && TEST_DATABASE_URL='postgresql+psycopg://zcgl_user:postgres@127.0.0.1:5432/zcgl_test' DATABASE_URL='postgresql+psycopg://zcgl_user:postgres@127.0.0.1:5432/zcgl_test' ./.venv/bin/python - <<'PY'\nfrom sqlalchemy import create_engine, text\nurl = \"postgresql+psycopg://zcgl_user:postgres@127.0.0.1:5432/zcgl_test\"\nengine = create_engine(url)\nwith engine.connect() as conn:\n    count = conn.execute(\n        text(\"SELECT COUNT(*) FROM roles WHERE scope NOT IN ('SYSTEM','ORGANIZATION')\")\n    ).scalar_one()\nprint(f\"ROLES_SCOPE_INVALID_COUNT={count}\")\nPY`（`ROLES_SCOPE_INVALID_COUNT=0`）

### 2.69 本批新增验证（已通过，跨模块抽样回归 + Gate 复核）
- `cd backend && ./.venv/bin/python -m pytest --no-cov tests/unit/middleware/test_authz_dependency.py tests/unit/api/v1/test_pdf_import_layering.py tests/unit/api/v1/documents/test_pdf_import_routes.py tests/unit/api/v1/test_statistics_router_layering.py tests/unit/api/v1/analytics/test_statistics.py tests/unit/api/v1/test_rent_contract_contracts_layering.py -q`（`33 passed`）
- `cd backend && ./.venv/bin/python -m pytest --no-cov tests/unit/api/v1/test_rent_contract_api.py -k "get_contracts_default_params or get_contracts_with_pagination or get_asset_contracts_success" -q`（`3 passed, 64 deselected`）
- `cd backend && if ! grep -rEql "TenantFilter|_apply_tenant_filter|tenant_filter\\.organization_ids" src/ --include="*.py"; then echo "BG1_STATUS=PASS"; else echo "BG1_STATUS=FAIL"; fi`（`BG1_STATUS=PASS`）
- `cd backend && { grep -rEn "organization_id" src/models/rbac.py src/crud/rbac.py src/crud/field_whitelist.py src/services/permission/ --include="*.py" > /tmp/bg2.txt || true; } && echo "BG2_NON_DEPRECATED=$(grep -Evc 'DEPRECATED|deprecated' /tmp/bg2.txt || true)"`（`BG2_NON_DEPRECATED=0`）
- `cd backend && { grep -rEn "PermissionGrant|ResourcePermission|OrganizationPermissionService|OrganizationPermissionChecker" src/api/v1 src/services src/middleware src/crud/rbac.py src/models/rbac.py src/crud/field_whitelist.py --include="*.py" > /tmp/bg3.txt || true; } && echo "BG3_NON_DEPRECATED=$(grep -Evc 'DEPRECATED|deprecated' /tmp/bg3.txt || true)"`（`BG3_NON_DEPRECATED=0`）
- `cd backend && { grep -rEn "ownership_id|ownership_ids" src/models/rent_contract.py src/services/rent_contract/ src/crud/rent_contract.py src/crud/collection.py src/api/v1/rent_contracts/ --include="*.py" > /tmp/bg4.txt || true; } && echo "BG4_NON_DEPRECATED=$(grep -Evc 'DEPRECATED|deprecated' /tmp/bg4.txt || true)"`（`BG4_NON_DEPRECATED=0`）

### 2.70 本批新增验证（已通过，system/auth 抽样回归 + Gate 复核）
- `cd backend && ./.venv/bin/python -m pytest --no-cov tests/unit/middleware/test_authz_dependency.py tests/unit/api/v1/test_system_settings_layering.py tests/unit/api/v1/test_tasks_layering.py tests/unit/api/v1/test_history_layering.py tests/unit/api/v1/test_operation_logs_layering.py tests/unit/api/v1/test_notifications_layering.py tests/unit/api/v1/test_roles_layering.py tests/unit/api/v1/test_users_layering.py tests/unit/api/v1/test_auth_sessions_layering.py tests/unit/api/v1/test_auth_audit_layering.py tests/unit/api/v1/test_auth_security_layering.py tests/unit/api/v1/test_organization_layering.py -q`（`49 passed`）
- `cd backend && if ! grep -rEql "TenantFilter|_apply_tenant_filter|tenant_filter\\.organization_ids" src/ --include="*.py"; then echo "BG1_STATUS=PASS"; else echo "BG1_STATUS=FAIL"; fi`（`BG1_STATUS=PASS`）
- `cd backend && { grep -rEn "organization_id" src/models/rbac.py src/crud/rbac.py src/crud/field_whitelist.py src/services/permission/ --include="*.py" > /tmp/bg2.txt || true; } && echo "BG2_NON_DEPRECATED=$(grep -Evc 'DEPRECATED|deprecated' /tmp/bg2.txt || true)"`（`BG2_NON_DEPRECATED=0`）
- `cd backend && { grep -rEn "PermissionGrant|ResourcePermission|OrganizationPermissionService|OrganizationPermissionChecker" src/api/v1 src/services src/middleware src/crud/rbac.py src/models/rbac.py src/crud/field_whitelist.py --include="*.py" > /tmp/bg3.txt || true; } && echo "BG3_NON_DEPRECATED=$(grep -Evc 'DEPRECATED|deprecated' /tmp/bg3.txt || true)"`（`BG3_NON_DEPRECATED=0`）
- `cd backend && { grep -rEn "ownership_id|ownership_ids" src/models/rent_contract.py src/services/rent_contract/ src/crud/rent_contract.py src/crud/collection.py src/api/v1/rent_contracts/ --include="*.py" > /tmp/bg4.txt || true; } && echo "BG4_NON_DEPRECATED=$(grep -Evc 'DEPRECATED|deprecated' /tmp/bg4.txt || true)"`（`BG4_NON_DEPRECATED=0`）

### 2.71 本批新增验证（维护复核：通过项 + 风险项）
- 通过项：`cd backend && ./.venv/bin/python -m pytest --no-cov tests/unit/middleware/test_authz_dependency.py tests/unit/services/test_authz_cache.py tests/unit/services/test_authz_events.py tests/unit/services/test_data_policy_service.py tests/integration/api/test_project_visibility_real.py tests/integration/crud/test_project_tenant_scope_real.py -q`（`17 passed`）
- 风险项：`cd backend && ./.venv/bin/python -m pytest --no-cov tests/integration/test_asset_lifecycle.py -q`（`2 failed`，`POST /api/v1/assets` 断言期望 `201` 实得 `422`）
- `cd backend && if ! grep -rEql "TenantFilter|_apply_tenant_filter|tenant_filter\\.organization_ids" src/ --include="*.py"; then echo "BG1_STATUS=PASS"; else echo "BG1_STATUS=FAIL"; fi`（`BG1_STATUS=PASS`）
- `cd backend && { grep -rEn "organization_id" src/models/rbac.py src/crud/rbac.py src/crud/field_whitelist.py src/services/permission/ --include="*.py" > /tmp/bg2.txt || true; } && echo "BG2_NON_DEPRECATED=$(grep -Evc 'DEPRECATED|deprecated' /tmp/bg2.txt || true)"`（`BG2_NON_DEPRECATED=0`）
- `cd backend && { grep -rEn "PermissionGrant|ResourcePermission|OrganizationPermissionService|OrganizationPermissionChecker" src/api/v1 src/services src/middleware src/crud/rbac.py src/models/rbac.py src/crud/field_whitelist.py --include="*.py" > /tmp/bg3.txt || true; } && echo "BG3_NON_DEPRECATED=$(grep -Evc 'DEPRECATED|deprecated' /tmp/bg3.txt || true)"`（`BG3_NON_DEPRECATED=0`）
- `cd backend && { grep -rEn "ownership_id|ownership_ids" src/models/rent_contract.py src/services/rent_contract/ src/crud/rent_contract.py src/crud/collection.py src/api/v1/rent_contracts/ --include="*.py" > /tmp/bg4.txt || true; } && echo "BG4_NON_DEPRECATED=$(grep -Evc 'DEPRECATED|deprecated' /tmp/bg4.txt || true)"`（`BG4_NON_DEPRECATED=0`）

### 2.72 本批新增验证（已通过，asset_lifecycle 422 风险闭环 + 维护复核）
- 修复项：`backend/tests/integration/test_asset_lifecycle.py` 增加资产枚举种子初始化（`ownership_status/property_nature/usage_status/data_status`），并将测试用例值同步到当前标准枚举（`property_nature=经营类`、`usage_status=出租|闲置`），消除测试环境跳过应用启动枚举初始化导致的 `422` 回归。
- `cd backend && ./.venv/bin/ruff check tests/integration/test_asset_lifecycle.py`（通过）
- `cd backend && ./.venv/bin/python -m pytest --no-cov tests/integration/test_asset_lifecycle.py -q`（`2 passed`）
- `cd backend && ./.venv/bin/python -m pytest --no-cov tests/unit/middleware/test_authz_dependency.py tests/unit/services/test_authz_cache.py tests/unit/services/test_authz_events.py tests/unit/services/test_data_policy_service.py tests/integration/api/test_project_visibility_real.py tests/integration/crud/test_project_tenant_scope_real.py tests/integration/test_asset_lifecycle.py -q`（`19 passed`）
- `cd backend && if ! grep -rEql "TenantFilter|_apply_tenant_filter|tenant_filter\\.organization_ids" src/ --include="*.py"; then echo "BG1_STATUS=PASS"; else echo "BG1_STATUS=FAIL"; fi`（`BG1_STATUS=PASS`）
- `cd backend && { grep -rEn "organization_id" src/models/rbac.py src/crud/rbac.py src/crud/field_whitelist.py src/services/permission/ --include="*.py" > /tmp/bg2.txt || true; } && echo "BG2_NON_DEPRECATED=$(grep -Evc 'DEPRECATED|deprecated' /tmp/bg2.txt || true)"`（`BG2_NON_DEPRECATED=0`）
- `cd backend && { grep -rEn "PermissionGrant|ResourcePermission|OrganizationPermissionService|OrganizationPermissionChecker" src/api/v1 src/services src/middleware src/crud/rbac.py src/models/rbac.py src/crud/field_whitelist.py --include="*.py" > /tmp/bg3.txt || true; } && echo "BG3_NON_DEPRECATED=$(grep -Evc 'DEPRECATED|deprecated' /tmp/bg3.txt || true)"`（`BG3_NON_DEPRECATED=0`）
- `cd backend && { grep -rEn "ownership_id|ownership_ids" src/models/rent_contract.py src/services/rent_contract/ src/crud/rent_contract.py src/crud/collection.py src/api/v1/rent_contracts/ --include="*.py" > /tmp/bg4.txt || true; } && echo "BG4_NON_DEPRECATED=$(grep -Evc 'DEPRECATED|deprecated' /tmp/bg4.txt || true)"`（`BG4_NON_DEPRECATED=0`）

### 2.73 本批新增验证（已通过，跨模块抽样回归 + Gate 复核）
- `cd backend && ./.venv/bin/python -m pytest --no-cov tests/unit/middleware/test_authz_dependency.py tests/unit/api/v1/test_pdf_import_layering.py tests/unit/api/v1/documents/test_pdf_import_routes.py tests/unit/api/v1/test_statistics_router_layering.py tests/unit/api/v1/analytics/test_statistics.py tests/unit/api/v1/test_rent_contract_contracts_layering.py tests/unit/api/v1/test_system_settings_layering.py tests/unit/api/v1/test_roles_layering.py tests/integration/api/test_project_visibility_real.py tests/integration/crud/test_project_tenant_scope_real.py tests/integration/test_asset_lifecycle.py -q`（`47 passed`）
- `cd backend && if ! grep -rEql "TenantFilter|_apply_tenant_filter|tenant_filter\\.organization_ids" src/ --include="*.py"; then echo "BG1_STATUS=PASS"; else echo "BG1_STATUS=FAIL"; fi`（`BG1_STATUS=PASS`）
- `cd backend && { grep -rEn "organization_id" src/models/rbac.py src/crud/rbac.py src/crud/field_whitelist.py src/services/permission/ --include="*.py" > /tmp/bg2.txt || true; } && echo "BG2_NON_DEPRECATED=$(grep -Evc 'DEPRECATED|deprecated' /tmp/bg2.txt || true)"`（`BG2_NON_DEPRECATED=0`）
- `cd backend && { grep -rEn "PermissionGrant|ResourcePermission|OrganizationPermissionService|OrganizationPermissionChecker" src/api/v1 src/services src/middleware src/crud/rbac.py src/models/rbac.py src/crud/field_whitelist.py --include="*.py" > /tmp/bg3.txt || true; } && echo "BG3_NON_DEPRECATED=$(grep -Evc 'DEPRECATED|deprecated' /tmp/bg3.txt || true)"`（`BG3_NON_DEPRECATED=0`）
- `cd backend && { grep -rEn "ownership_id|ownership_ids" src/models/rent_contract.py src/services/rent_contract/ src/crud/rent_contract.py src/crud/collection.py src/api/v1/rent_contracts/ --include="*.py" > /tmp/bg4.txt || true; } && echo "BG4_NON_DEPRECATED=$(grep -Evc 'DEPRECATED|deprecated' /tmp/bg4.txt || true)"`（`BG4_NON_DEPRECATED=0`）

### 2.74 本批新增验证（已通过，扩大回归复跑 + Gate 复核）
- `cd backend && ./.venv/bin/python -m pytest --no-cov -m "not slow and not e2e" -x -q`（`4536 passed, 8 skipped, 14 deselected`）
- `cd backend && if ! grep -rEql "TenantFilter|_apply_tenant_filter|tenant_filter\\.organization_ids" src/ --include="*.py"; then echo "BG1_STATUS=PASS"; else echo "BG1_STATUS=FAIL"; fi`（`BG1_STATUS=PASS`）
- `cd backend && { grep -rEn "organization_id" src/models/rbac.py src/crud/rbac.py src/crud/field_whitelist.py src/services/permission/ --include="*.py" > /tmp/bg2.txt || true; } && echo "BG2_NON_DEPRECATED=$(grep -Evc 'DEPRECATED|deprecated' /tmp/bg2.txt || true)"`（`BG2_NON_DEPRECATED=0`）
- `cd backend && { grep -rEn "PermissionGrant|ResourcePermission|OrganizationPermissionService|OrganizationPermissionChecker" src/api/v1 src/services src/middleware src/crud/rbac.py src/models/rbac.py src/crud/field_whitelist.py --include="*.py" > /tmp/bg3.txt || true; } && echo "BG3_NON_DEPRECATED=$(grep -Evc 'DEPRECATED|deprecated' /tmp/bg3.txt || true)"`（`BG3_NON_DEPRECATED=0`）
- `cd backend && { grep -rEn "ownership_id|ownership_ids" src/models/rent_contract.py src/services/rent_contract/ src/crud/rent_contract.py src/crud/collection.py src/api/v1/rent_contracts/ --include="*.py" > /tmp/bg4.txt || true; } && echo "BG4_NON_DEPRECATED=$(grep -Evc 'DEPRECATED|deprecated' /tmp/bg4.txt || true)"`（`BG4_NON_DEPRECATED=0`）

### 2.75 本批新增验证（已通过，Gate + 迁移 + 角色作用域复核）
- `cd backend && ./.venv/bin/python -m pytest --no-cov tests/unit/migration/test_backfill.py -q`（`5 passed`）
- `cd backend && if ! grep -rEql "TenantFilter|_apply_tenant_filter|tenant_filter\\.organization_ids" src/ --include="*.py"; then echo "BG1_STATUS=PASS"; else echo "BG1_STATUS=FAIL"; fi`（`BG1_STATUS=PASS`）
- `cd backend && { grep -rEn "organization_id" src/models/rbac.py src/crud/rbac.py src/crud/field_whitelist.py src/services/permission/ --include="*.py" > /tmp/bg2.txt || true; } && echo "BG2_NON_DEPRECATED=$(grep -Evc 'DEPRECATED|deprecated' /tmp/bg2.txt || true)"`（`BG2_NON_DEPRECATED=0`）
- `cd backend && { grep -rEn "PermissionGrant|ResourcePermission|OrganizationPermissionService|OrganizationPermissionChecker" src/api/v1 src/services src/middleware src/crud/rbac.py src/models/rbac.py src/crud/field_whitelist.py --include="*.py" > /tmp/bg3.txt || true; } && echo "BG3_NON_DEPRECATED=$(grep -Evc 'DEPRECATED|deprecated' /tmp/bg3.txt || true)"`（`BG3_NON_DEPRECATED=0`）
- `cd backend && { grep -rEn "ownership_id|ownership_ids" src/models/rent_contract.py src/services/rent_contract/ src/crud/rent_contract.py src/crud/collection.py src/api/v1/rent_contracts/ --include="*.py" > /tmp/bg4.txt || true; } && echo "BG4_NON_DEPRECATED=$(grep -Evc 'DEPRECATED|deprecated' /tmp/bg4.txt || true)"`（`BG4_NON_DEPRECATED=0`）
- `cd backend && TEST_DATABASE_URL='postgresql+psycopg://zcgl_user:postgres@127.0.0.1:5432/zcgl_test' DATABASE_URL='postgresql+psycopg://zcgl_user:postgres@127.0.0.1:5432/zcgl_test' ./.venv/bin/python - <<'PY'\nfrom sqlalchemy import create_engine, text\nurl = "postgresql+psycopg://zcgl_user:postgres@127.0.0.1:5432/zcgl_test"\nengine = create_engine(url)\nwith engine.connect() as conn:\n    count = conn.execute(\n        text("SELECT COUNT(*) FROM roles WHERE scope NOT IN ('SYSTEM','ORGANIZATION')")\n    ).scalar_one()\nprint(f"ROLES_SCOPE_INVALID_COUNT={count}")\nPY`（`ROLES_SCOPE_INVALID_COUNT=0`）

### 2.77 本批新增验证（已通过，扩大回归复跑 + Gate 同步）
- `cd backend && ./.venv/bin/python -m pytest --no-cov -m "not slow and not e2e" -x -q`（`4536 passed, 8 skipped, 14 deselected`）
- `cd backend && if ! grep -rEql "TenantFilter|_apply_tenant_filter|tenant_filter\\.organization_ids" src/ --include="*.py"; then echo "BG1_STATUS=PASS"; else echo "BG1_STATUS=FAIL"; fi`（`BG1_STATUS=PASS`）
- `cd backend && { grep -rEn "organization_id" src/models/rbac.py src/crud/rbac.py src/crud/field_whitelist.py src/services/permission/ --include="*.py" > /tmp/bg2.txt || true; } && echo "BG2_NON_DEPRECATED=$(grep -Evc 'DEPRECATED|deprecated' /tmp/bg2.txt || true)"`（`BG2_NON_DEPRECATED=0`）
- `cd backend && { grep -rEn "PermissionGrant|ResourcePermission|OrganizationPermissionService|OrganizationPermissionChecker" src/api/v1 src/services src/middleware src/crud/rbac.py src/models/rbac.py src/crud/field_whitelist.py --include="*.py" > /tmp/bg3.txt || true; } && echo "BG3_NON_DEPRECATED=$(grep -Evc 'DEPRECATED|deprecated' /tmp/bg3.txt || true)"`（`BG3_NON_DEPRECATED=0`）
- `cd backend && { grep -rEn "ownership_id|ownership_ids" src/models/rent_contract.py src/services/rent_contract/ src/crud/rent_contract.py src/crud/collection.py src/api/v1/rent_contracts/ --include="*.py" > /tmp/bg4.txt || true; } && echo "BG4_NON_DEPRECATED=$(grep -Evc 'DEPRECATED|deprecated' /tmp/bg4.txt || true)"`（`BG4_NON_DEPRECATED=0`）

### 2.78 本批新增验证（已通过，跨模块抽样回归 + Gate 同步）
- `cd backend && ./.venv/bin/python -m pytest --no-cov tests/unit/middleware/test_authz_dependency.py tests/unit/services/test_authz_cache.py tests/unit/services/test_authz_events.py tests/unit/api/v1/test_pdf_import_layering.py tests/unit/api/v1/documents/test_pdf_import_routes.py tests/unit/api/v1/test_statistics_router_layering.py tests/unit/api/v1/analytics/test_statistics.py tests/unit/api/v1/test_rent_contract_contracts_layering.py tests/unit/api/v1/test_system_settings_layering.py tests/unit/api/v1/test_roles_layering.py tests/integration/api/test_project_visibility_real.py tests/integration/crud/test_project_tenant_scope_real.py -q`（`50 passed`）
- `cd backend && if ! grep -rEql "TenantFilter|_apply_tenant_filter|tenant_filter\\.organization_ids" src/ --include="*.py"; then echo "BG1_STATUS=PASS"; else echo "BG1_STATUS=FAIL"; fi`（`BG1_STATUS=PASS`）
- `cd backend && { grep -rEn "organization_id" src/models/rbac.py src/crud/rbac.py src/crud/field_whitelist.py src/services/permission/ --include="*.py" > /tmp/bg2.txt || true; } && echo "BG2_NON_DEPRECATED=$(grep -Evc 'DEPRECATED|deprecated' /tmp/bg2.txt || true)"`（`BG2_NON_DEPRECATED=0`）
- `cd backend && { grep -rEn "PermissionGrant|ResourcePermission|OrganizationPermissionService|OrganizationPermissionChecker" src/api/v1 src/services src/middleware src/crud/rbac.py src/models/rbac.py src/crud/field_whitelist.py --include="*.py" > /tmp/bg3.txt || true; } && echo "BG3_NON_DEPRECATED=$(grep -Evc 'DEPRECATED|deprecated' /tmp/bg3.txt || true)"`（`BG3_NON_DEPRECATED=0`）
- `cd backend && { grep -rEn "ownership_id|ownership_ids" src/models/rent_contract.py src/services/rent_contract/ src/crud/rent_contract.py src/crud/collection.py src/api/v1/rent_contracts/ --include="*.py" > /tmp/bg4.txt || true; } && echo "BG4_NON_DEPRECATED=$(grep -Evc 'DEPRECATED|deprecated' /tmp/bg4.txt || true)"`（`BG4_NON_DEPRECATED=0`）

### 2.79 本批新增验证（已通过，扩大回归复跑 + Gate 同步）
- `cd backend && ./.venv/bin/python -m pytest --no-cov -m "not slow and not e2e" -x -q`（`4536 passed, 8 skipped, 14 deselected`）
- `cd backend && if ! grep -rEql "TenantFilter|_apply_tenant_filter|tenant_filter\\.organization_ids" src/ --include="*.py"; then echo "BG1_STATUS=PASS"; else echo "BG1_STATUS=FAIL"; fi`（`BG1_STATUS=PASS`）
- `cd backend && { grep -rEn "organization_id" src/models/rbac.py src/crud/rbac.py src/crud/field_whitelist.py src/services/permission/ --include="*.py" > /tmp/bg2.txt || true; } && echo "BG2_NON_DEPRECATED=$(grep -Evc 'DEPRECATED|deprecated' /tmp/bg2.txt || true)"`（`BG2_NON_DEPRECATED=0`）
- `cd backend && { grep -rEn "PermissionGrant|ResourcePermission|OrganizationPermissionService|OrganizationPermissionChecker" src/api/v1 src/services src/middleware src/crud/rbac.py src/models/rbac.py src/crud/field_whitelist.py --include="*.py" > /tmp/bg3.txt || true; } && echo "BG3_NON_DEPRECATED=$(grep -Evc 'DEPRECATED|deprecated' /tmp/bg3.txt || true)"`（`BG3_NON_DEPRECATED=0`）
- `cd backend && { grep -rEn "ownership_id|ownership_ids" src/models/rent_contract.py src/services/rent_contract/ src/crud/rent_contract.py src/crud/collection.py src/api/v1/rent_contracts/ --include="*.py" > /tmp/bg4.txt || true; } && echo "BG4_NON_DEPRECATED=$(grep -Evc 'DEPRECATED|deprecated' /tmp/bg4.txt || true)"`（`BG4_NON_DEPRECATED=0`）

### 2.80 本批新增验证（已通过，跨模块抽样回归 + Gate 同步）
- `cd backend && ./.venv/bin/python -m pytest --no-cov tests/unit/middleware/test_authz_dependency.py tests/unit/services/test_authz_cache.py tests/unit/services/test_authz_events.py tests/unit/api/v1/test_pdf_import_layering.py tests/unit/api/v1/documents/test_pdf_import_routes.py tests/unit/api/v1/test_statistics_router_layering.py tests/unit/api/v1/analytics/test_statistics.py tests/unit/api/v1/test_rent_contract_contracts_layering.py tests/unit/api/v1/test_system_settings_layering.py tests/unit/api/v1/test_roles_layering.py tests/integration/api/test_project_visibility_real.py tests/integration/crud/test_project_tenant_scope_real.py -q`（`50 passed`）
- `cd backend && if ! grep -rEql "TenantFilter|_apply_tenant_filter|tenant_filter\\.organization_ids" src/ --include="*.py"; then echo "BG1_STATUS=PASS"; else echo "BG1_STATUS=FAIL"; fi`（`BG1_STATUS=PASS`）
- `cd backend && { grep -rEn "organization_id" src/models/rbac.py src/crud/rbac.py src/crud/field_whitelist.py src/services/permission/ --include="*.py" > /tmp/bg2.txt || true; } && echo "BG2_NON_DEPRECATED=$(grep -Evc 'DEPRECATED|deprecated' /tmp/bg2.txt || true)"`（`BG2_NON_DEPRECATED=0`）
- `cd backend && { grep -rEn "PermissionGrant|ResourcePermission|OrganizationPermissionService|OrganizationPermissionChecker" src/api/v1 src/services src/middleware src/crud/rbac.py src/models/rbac.py src/crud/field_whitelist.py --include="*.py" > /tmp/bg3.txt || true; } && echo "BG3_NON_DEPRECATED=$(grep -Evc 'DEPRECATED|deprecated' /tmp/bg3.txt || true)"`（`BG3_NON_DEPRECATED=0`）
- `cd backend && { grep -rEn "ownership_id|ownership_ids" src/models/rent_contract.py src/services/rent_contract/ src/crud/rent_contract.py src/crud/collection.py src/api/v1/rent_contracts/ --include="*.py" > /tmp/bg4.txt || true; } && echo "BG4_NON_DEPRECATED=$(grep -Evc 'DEPRECATED|deprecated' /tmp/bg4.txt || true)"`（`BG4_NON_DEPRECATED=0`）

### 2.81 本批新增验证（已通过，扩大回归复跑 + Gate 同步）
- `cd backend && ./.venv/bin/python -m pytest --no-cov -m "not slow and not e2e" -x -q`（`4536 passed, 8 skipped, 14 deselected`）
- `cd backend && if ! grep -rEql "TenantFilter|_apply_tenant_filter|tenant_filter\.organization_ids" src/ --include="*.py"; then echo "BG1_STATUS=PASS"; else echo "BG1_STATUS=FAIL"; fi`（`BG1_STATUS=PASS`）
- `cd backend && { grep -rEn "organization_id" src/models/rbac.py src/crud/rbac.py src/crud/field_whitelist.py src/services/permission/ --include="*.py" > /tmp/bg2.txt || true; } && echo "BG2_NON_DEPRECATED=$(grep -Evc 'DEPRECATED|deprecated' /tmp/bg2.txt || true)"`（`BG2_NON_DEPRECATED=0`）
- `cd backend && { grep -rEn "PermissionGrant|ResourcePermission|OrganizationPermissionService|OrganizationPermissionChecker" src/api/v1 src/services src/middleware src/crud/rbac.py src/models/rbac.py src/crud/field_whitelist.py --include="*.py" > /tmp/bg3.txt || true; } && echo "BG3_NON_DEPRECATED=$(grep -Evc 'DEPRECATED|deprecated' /tmp/bg3.txt || true)"`（`BG3_NON_DEPRECATED=0`）
- `cd backend && { grep -rEn "ownership_id|ownership_ids" src/models/rent_contract.py src/services/rent_contract/ src/crud/rent_contract.py src/crud/collection.py src/api/v1/rent_contracts/ --include="*.py" > /tmp/bg4.txt || true; } && echo "BG4_NON_DEPRECATED=$(grep -Evc 'DEPRECATED|deprecated' /tmp/bg4.txt || true)"`（`BG4_NON_DEPRECATED=0`）

### 2.82 本批新增验证（已通过，跨模块抽样回归 + Gate/作用域复核）
- `cd backend && ./.venv/bin/python -m pytest --no-cov tests/unit/middleware/test_authz_dependency.py tests/unit/services/test_authz_cache.py tests/unit/services/test_authz_events.py tests/unit/api/v1/test_pdf_import_layering.py tests/unit/api/v1/documents/test_pdf_import_routes.py tests/unit/api/v1/test_statistics_router_layering.py tests/unit/api/v1/analytics/test_statistics.py tests/unit/api/v1/test_rent_contract_contracts_layering.py tests/unit/api/v1/test_system_settings_layering.py tests/unit/api/v1/test_roles_layering.py tests/integration/api/test_project_visibility_real.py tests/integration/crud/test_project_tenant_scope_real.py -q`（`50 passed`）
- `cd backend && if ! grep -rEql "TenantFilter|_apply_tenant_filter|tenant_filter\.organization_ids" src/ --include="*.py"; then echo "BG1_STATUS=PASS"; else echo "BG1_STATUS=FAIL"; fi`（`BG1_STATUS=PASS`）
- `cd backend && { grep -rEn "organization_id" src/models/rbac.py src/crud/rbac.py src/crud/field_whitelist.py src/services/permission/ --include="*.py" > /tmp/bg2.txt || true; } && echo "BG2_NON_DEPRECATED=$(grep -Evc 'DEPRECATED|deprecated' /tmp/bg2.txt || true)"`（`BG2_NON_DEPRECATED=0`）
- `cd backend && { grep -rEn "PermissionGrant|ResourcePermission|OrganizationPermissionService|OrganizationPermissionChecker" src/api/v1 src/services src/middleware src/crud/rbac.py src/models/rbac.py src/crud/field_whitelist.py --include="*.py" > /tmp/bg3.txt || true; } && echo "BG3_NON_DEPRECATED=$(grep -Evc 'DEPRECATED|deprecated' /tmp/bg3.txt || true)"`（`BG3_NON_DEPRECATED=0`）
- `cd backend && { grep -rEn "ownership_id|ownership_ids" src/models/rent_contract.py src/services/rent_contract/ src/crud/rent_contract.py src/crud/collection.py src/api/v1/rent_contracts/ --include="*.py" > /tmp/bg4.txt || true; } && echo "BG4_NON_DEPRECATED=$(grep -Evc 'DEPRECATED|deprecated' /tmp/bg4.txt || true)"`（`BG4_NON_DEPRECATED=0`）
- `cd backend && ./.venv/bin/python - <<'PY'
from sqlalchemy import create_engine, text
url = "postgresql+psycopg://zcgl_user:postgres@127.0.0.1:5432/zcgl_test"
engine = create_engine(url)
with engine.connect() as conn:
  count = conn.execute(text("SELECT COUNT(*) FROM roles WHERE scope NOT IN ('SYSTEM','ORGANIZATION')")).scalar_one()
print(f"ROLES_SCOPE_INVALID_COUNT={count}")
PY`（`ROLES_SCOPE_INVALID_COUNT=0`）

### 2.83 本批新增验证（已通过，鉴权/组织可见范围抽样回归 + Gate 同步）
- `cd backend && ./.venv/bin/python -m pytest --no-cov tests/unit/middleware/test_authz_dependency.py tests/unit/api/v1/test_organization_layering.py tests/unit/api/v1/test_roles_layering.py tests/unit/api/v1/test_users_layering.py tests/unit/api/v1/test_auth_sessions_layering.py tests/unit/api/v1/test_auth_audit_layering.py tests/unit/api/v1/test_auth_security_layering.py tests/integration/api/test_project_visibility_real.py tests/integration/crud/test_project_tenant_scope_real.py tests/integration/test_asset_lifecycle.py -q`（`32 passed`）
- `cd backend && if ! grep -rEql "TenantFilter|_apply_tenant_filter|tenant_filter\\.organization_ids" src/ --include="*.py"; then echo "BG1_STATUS=PASS"; else echo "BG1_STATUS=FAIL"; fi`（`BG1_STATUS=PASS`）
- `cd backend && { grep -rEn "organization_id" src/models/rbac.py src/crud/rbac.py src/crud/field_whitelist.py src/services/permission/ --include="*.py" > /tmp/bg2.txt || true; } && echo "BG2_NON_DEPRECATED=$(grep -Evc 'DEPRECATED|deprecated' /tmp/bg2.txt || true)"`（`BG2_NON_DEPRECATED=0`）
- `cd backend && { grep -rEn "PermissionGrant|ResourcePermission|OrganizationPermissionService|OrganizationPermissionChecker" src/api/v1 src/services src/middleware src/crud/rbac.py src/models/rbac.py src/crud/field_whitelist.py --include="*.py" > /tmp/bg3.txt || true; } && echo "BG3_NON_DEPRECATED=$(grep -Evc 'DEPRECATED|deprecated' /tmp/bg3.txt || true)"`（`BG3_NON_DEPRECATED=0`）
- `cd backend && { grep -rEn "ownership_id|ownership_ids" src/models/rent_contract.py src/services/rent_contract/ src/crud/rent_contract.py src/crud/collection.py src/api/v1/rent_contracts/ --include="*.py" > /tmp/bg4.txt || true; } && echo "BG4_NON_DEPRECATED=$(grep -Evc 'DEPRECATED|deprecated' /tmp/bg4.txt || true)"`（`BG4_NON_DEPRECATED=0`）

### 2.84 本批新增验证（已通过，扩大回归复跑 + Gate 同步）
- `cd backend && ./.venv/bin/python -m pytest --no-cov -m "not slow and not e2e" -x -q`（`4536 passed, 8 skipped, 14 deselected`）
- `cd backend && if ! grep -rEql "TenantFilter|_apply_tenant_filter|tenant_filter\\.organization_ids" src/ --include="*.py"; then echo "BG1_STATUS=PASS"; else echo "BG1_STATUS=FAIL"; fi`（`BG1_STATUS=PASS`）
- `cd backend && { grep -rEn "organization_id" src/models/rbac.py src/crud/rbac.py src/crud/field_whitelist.py src/services/permission/ --include="*.py" > /tmp/bg2.txt || true; } && echo "BG2_NON_DEPRECATED=$(grep -Evc 'DEPRECATED|deprecated' /tmp/bg2.txt || true)"`（`BG2_NON_DEPRECATED=0`）
- `cd backend && { grep -rEn "PermissionGrant|ResourcePermission|OrganizationPermissionService|OrganizationPermissionChecker" src/api/v1 src/services src/middleware src/crud/rbac.py src/models/rbac.py src/crud/field_whitelist.py --include="*.py" > /tmp/bg3.txt || true; } && echo "BG3_NON_DEPRECATED=$(grep -Evc 'DEPRECATED|deprecated' /tmp/bg3.txt || true)"`（`BG3_NON_DEPRECATED=0`）
- `cd backend && { grep -rEn "ownership_id|ownership_ids" src/models/rent_contract.py src/services/rent_contract/ src/crud/rent_contract.py src/crud/collection.py src/api/v1/rent_contracts/ --include="*.py" > /tmp/bg4.txt || true; } && echo "BG4_NON_DEPRECATED=$(grep -Evc 'DEPRECATED|deprecated' /tmp/bg4.txt || true)"`（`BG4_NON_DEPRECATED=0`）

### 2.85 本批新增验证（已通过，Gate + 迁移 + 角色作用域复核）
- `cd backend && ./.venv/bin/python -m pytest --no-cov tests/unit/migration/test_backfill.py -q`（`5 passed`）
- `cd backend && if ! grep -rEql "TenantFilter|_apply_tenant_filter|tenant_filter\\.organization_ids" src/ --include="*.py"; then echo "BG1_STATUS=PASS"; else echo "BG1_STATUS=FAIL"; fi`（`BG1_STATUS=PASS`）
- `cd backend && { grep -rEn "organization_id" src/models/rbac.py src/crud/rbac.py src/crud/field_whitelist.py src/services/permission/ --include="*.py" > /tmp/bg2.txt || true; } && echo "BG2_NON_DEPRECATED=$(grep -Evc 'DEPRECATED|deprecated' /tmp/bg2.txt || true)"`（`BG2_NON_DEPRECATED=0`）
- `cd backend && { grep -rEn "PermissionGrant|ResourcePermission|OrganizationPermissionService|OrganizationPermissionChecker" src/api/v1 src/services src/middleware src/crud/rbac.py src/models/rbac.py src/crud/field_whitelist.py --include="*.py" > /tmp/bg3.txt || true; } && echo "BG3_NON_DEPRECATED=$(grep -Evc 'DEPRECATED|deprecated' /tmp/bg3.txt || true)"`（`BG3_NON_DEPRECATED=0`）
- `cd backend && { grep -rEn "ownership_id|ownership_ids" src/models/rent_contract.py src/services/rent_contract/ src/crud/rent_contract.py src/crud/collection.py src/api/v1/rent_contracts/ --include="*.py" > /tmp/bg4.txt || true; } && echo "BG4_NON_DEPRECATED=$(grep -Evc 'DEPRECATED|deprecated' /tmp/bg4.txt || true)"`（`BG4_NON_DEPRECATED=0`）
- `cd backend && ./.venv/bin/python - <<'PY'
from sqlalchemy import create_engine, text
url = "postgresql+psycopg://zcgl_user:postgres@127.0.0.1:5432/zcgl_test"
engine = create_engine(url)
with engine.connect() as conn:
  count = conn.execute(text("SELECT COUNT(*) FROM roles WHERE scope NOT IN ('SYSTEM','ORGANIZATION')")).scalar_one()
print(f"ROLES_SCOPE_INVALID_COUNT={count}")
PY`（`ROLES_SCOPE_INVALID_COUNT=0`）

### 2.86 本批新增验证（已通过，鉴权/组织可见范围抽样回归 + Gate 同步）
- `cd backend && ./.venv/bin/python -m pytest --no-cov tests/unit/middleware/test_authz_dependency.py tests/unit/api/v1/test_organization_layering.py tests/unit/api/v1/test_roles_layering.py tests/unit/api/v1/test_users_layering.py tests/unit/api/v1/test_auth_sessions_layering.py tests/unit/api/v1/test_auth_audit_layering.py tests/unit/api/v1/test_auth_security_layering.py tests/integration/api/test_project_visibility_real.py tests/integration/crud/test_project_tenant_scope_real.py tests/integration/test_asset_lifecycle.py -q`（`32 passed`）
- `cd backend && if ! grep -rEql "TenantFilter|_apply_tenant_filter|tenant_filter\\.organization_ids" src/ --include="*.py"; then echo "BG1_STATUS=PASS"; else echo "BG1_STATUS=FAIL"; fi`（`BG1_STATUS=PASS`）
- `cd backend && { grep -rEn "organization_id" src/models/rbac.py src/crud/rbac.py src/crud/field_whitelist.py src/services/permission/ --include="*.py" > /tmp/bg2.txt || true; } && echo "BG2_NON_DEPRECATED=$(grep -Evc 'DEPRECATED|deprecated' /tmp/bg2.txt || true)"`（`BG2_NON_DEPRECATED=0`）
- `cd backend && { grep -rEn "PermissionGrant|ResourcePermission|OrganizationPermissionService|OrganizationPermissionChecker" src/api/v1 src/services src/middleware src/crud/rbac.py src/models/rbac.py src/crud/field_whitelist.py --include="*.py" > /tmp/bg3.txt || true; } && echo "BG3_NON_DEPRECATED=$(grep -Evc 'DEPRECATED|deprecated' /tmp/bg3.txt || true)"`（`BG3_NON_DEPRECATED=0`）
- `cd backend && { grep -rEn "ownership_id|ownership_ids" src/models/rent_contract.py src/services/rent_contract/ src/crud/rent_contract.py src/crud/collection.py src/api/v1/rent_contracts/ --include="*.py" > /tmp/bg4.txt || true; } && echo "BG4_NON_DEPRECATED=$(grep -Evc 'DEPRECATED|deprecated' /tmp/bg4.txt || true)"`（`BG4_NON_DEPRECATED=0`）

### 2.87 本批新增验证（已通过，扩大回归复跑 + Gate 同步）
- `cd backend && ./.venv/bin/python -m pytest --no-cov -m "not slow and not e2e" -x -q`（`4537 passed, 8 skipped, 14 deselected`）
- `cd backend && if ! grep -rEql "TenantFilter|_apply_tenant_filter|tenant_filter\\.organization_ids" src/ --include="*.py"; then echo "BG1_STATUS=PASS"; else echo "BG1_STATUS=FAIL"; fi`（`BG1_STATUS=PASS`）
- `cd backend && { grep -rEn "organization_id" src/models/rbac.py src/crud/rbac.py src/crud/field_whitelist.py src/services/permission/ --include="*.py" > /tmp/bg2.txt || true; } && echo "BG2_NON_DEPRECATED=$(grep -Evc 'DEPRECATED|deprecated' /tmp/bg2.txt || true)"`（`BG2_NON_DEPRECATED=0`）
- `cd backend && { grep -rEn "PermissionGrant|ResourcePermission|OrganizationPermissionService|OrganizationPermissionChecker" src/api/v1 src/services src/middleware src/crud/rbac.py src/models/rbac.py src/crud/field_whitelist.py --include="*.py" > /tmp/bg3.txt || true; } && echo "BG3_NON_DEPRECATED=$(grep -Evc 'DEPRECATED|deprecated' /tmp/bg3.txt || true)"`（`BG3_NON_DEPRECATED=0`）
- `cd backend && { grep -rEn "ownership_id|ownership_ids" src/models/rent_contract.py src/services/rent_contract/ src/crud/rent_contract.py src/crud/collection.py src/api/v1/rent_contracts/ --include="*.py" > /tmp/bg4.txt || true; } && echo "BG4_NON_DEPRECATED=$(grep -Evc 'DEPRECATED|deprecated' /tmp/bg4.txt || true)"`（`BG4_NON_DEPRECATED=0`）

### 2.88 本批新增验证（已通过，Gate + 迁移 + 角色作用域复核）
- `cd backend && ./.venv/bin/python -m pytest --no-cov tests/unit/migration/test_backfill.py -q`（`5 passed`）
- `cd backend && if ! grep -rEql "TenantFilter|_apply_tenant_filter|tenant_filter\\.organization_ids" src/ --include="*.py"; then echo "BG1_STATUS=PASS"; else echo "BG1_STATUS=FAIL"; fi`（`BG1_STATUS=PASS`）
- `cd backend && { grep -rEn "organization_id" src/models/rbac.py src/crud/rbac.py src/crud/field_whitelist.py src/services/permission/ --include="*.py" > /tmp/bg2.txt || true; } && echo "BG2_NON_DEPRECATED=$(grep -Evc 'DEPRECATED|deprecated' /tmp/bg2.txt || true)"`（`BG2_NON_DEPRECATED=0`）
- `cd backend && { grep -rEn "PermissionGrant|ResourcePermission|OrganizationPermissionService|OrganizationPermissionChecker" src/api/v1 src/services src/middleware src/crud/rbac.py src/models/rbac.py src/crud/field_whitelist.py --include="*.py" > /tmp/bg3.txt || true; } && echo "BG3_NON_DEPRECATED=$(grep -Evc 'DEPRECATED|deprecated' /tmp/bg3.txt || true)"`（`BG3_NON_DEPRECATED=0`）
- `cd backend && { grep -rEn "ownership_id|ownership_ids" src/models/rent_contract.py src/services/rent_contract/ src/crud/rent_contract.py src/crud/collection.py src/api/v1/rent_contracts/ --include="*.py" > /tmp/bg4.txt || true; } && echo "BG4_NON_DEPRECATED=$(grep -Evc 'DEPRECATED|deprecated' /tmp/bg4.txt || true)"`（`BG4_NON_DEPRECATED=0`）
- `cd backend && ./.venv/bin/python - <<'PY'
from sqlalchemy import create_engine, text
url = "postgresql+psycopg://zcgl_user:postgres@127.0.0.1:5432/zcgl_test"
engine = create_engine(url)
with engine.connect() as conn:
  count = conn.execute(text("SELECT COUNT(*) FROM roles WHERE scope NOT IN ('SYSTEM','ORGANIZATION')")).scalar_one()
print(f"ROLES_SCOPE_INVALID_COUNT={count}")
PY`（`ROLES_SCOPE_INVALID_COUNT=0`）

### 2.89 本批新增验证（已通过，鉴权/组织可见范围抽样回归 + Gate 同步）
- `cd backend && ./.venv/bin/python -m pytest --no-cov tests/unit/middleware/test_authz_dependency.py tests/unit/api/v1/test_organization_layering.py tests/unit/api/v1/test_roles_layering.py tests/unit/api/v1/test_users_layering.py tests/unit/api/v1/test_auth_sessions_layering.py tests/unit/api/v1/test_auth_audit_layering.py tests/unit/api/v1/test_auth_security_layering.py tests/integration/api/test_project_visibility_real.py tests/integration/crud/test_project_tenant_scope_real.py tests/integration/test_asset_lifecycle.py -q`（`32 passed`）
- `cd backend && if ! grep -rEql "TenantFilter|_apply_tenant_filter|tenant_filter\\.organization_ids" src/ --include="*.py"; then echo "BG1_STATUS=PASS"; else echo "BG1_STATUS=FAIL"; fi`（`BG1_STATUS=PASS`）
- `cd backend && { grep -rEn "organization_id" src/models/rbac.py src/crud/rbac.py src/crud/field_whitelist.py src/services/permission/ --include="*.py" > /tmp/bg2.txt || true; } && echo "BG2_NON_DEPRECATED=$(grep -Evc 'DEPRECATED|deprecated' /tmp/bg2.txt || true)"`（`BG2_NON_DEPRECATED=0`）
- `cd backend && { grep -rEn "PermissionGrant|ResourcePermission|OrganizationPermissionService|OrganizationPermissionChecker" src/api/v1 src/services src/middleware src/crud/rbac.py src/models/rbac.py src/crud/field_whitelist.py --include="*.py" > /tmp/bg3.txt || true; } && echo "BG3_NON_DEPRECATED=$(grep -Evc 'DEPRECATED|deprecated' /tmp/bg3.txt || true)"`（`BG3_NON_DEPRECATED=0`）
- `cd backend && { grep -rEn "ownership_id|ownership_ids" src/models/rent_contract.py src/services/rent_contract/ src/crud/rent_contract.py src/crud/collection.py src/api/v1/rent_contracts/ --include="*.py" > /tmp/bg4.txt || true; } && echo "BG4_NON_DEPRECATED=$(grep -Evc 'DEPRECATED|deprecated' /tmp/bg4.txt || true)"`（`BG4_NON_DEPRECATED=0`）

### 2.90 本批新增验证（已通过，扩大回归复跑 + Gate 同步）
- `cd backend && ./.venv/bin/python -m pytest --no-cov -m "not slow and not e2e" -x -q`（`4537 passed, 8 skipped, 14 deselected`）
- `cd backend && if ! grep -rEql "TenantFilter|_apply_tenant_filter|tenant_filter\\.organization_ids" src/ --include="*.py"; then echo "BG1_STATUS=PASS"; else echo "BG1_STATUS=FAIL"; fi`（`BG1_STATUS=PASS`）
- `cd backend && { grep -rEn "organization_id" src/models/rbac.py src/crud/rbac.py src/crud/field_whitelist.py src/services/permission/ --include="*.py" > /tmp/bg2.txt || true; } && echo "BG2_NON_DEPRECATED=$(grep -Evc 'DEPRECATED|deprecated' /tmp/bg2.txt || true)"`（`BG2_NON_DEPRECATED=0`）
- `cd backend && { grep -rEn "PermissionGrant|ResourcePermission|OrganizationPermissionService|OrganizationPermissionChecker" src/api/v1 src/services src/middleware src/crud/rbac.py src/models/rbac.py src/crud/field_whitelist.py --include="*.py" > /tmp/bg3.txt || true; } && echo "BG3_NON_DEPRECATED=$(grep -Evc 'DEPRECATED|deprecated' /tmp/bg3.txt || true)"`（`BG3_NON_DEPRECATED=0`）
- `cd backend && { grep -rEn "ownership_id|ownership_ids" src/models/rent_contract.py src/services/rent_contract/ src/crud/rent_contract.py src/crud/collection.py src/api/v1/rent_contracts/ --include="*.py" > /tmp/bg4.txt || true; } && echo "BG4_NON_DEPRECATED=$(grep -Evc 'DEPRECATED|deprecated' /tmp/bg4.txt || true)"`（`BG4_NON_DEPRECATED=0`）

### 2.91 本批新增验证（已通过，Gate + 迁移 + 角色作用域复核）
- `cd backend && ./.venv/bin/python -m pytest --no-cov tests/unit/migration/test_backfill.py -q`（`5 passed`）
- `cd backend && if ! grep -rEql "TenantFilter|_apply_tenant_filter|tenant_filter\\.organization_ids" src/ --include="*.py"; then echo "BG1_STATUS=PASS"; else echo "BG1_STATUS=FAIL"; fi`（`BG1_STATUS=PASS`）
- `cd backend && { grep -rEn "organization_id" src/models/rbac.py src/crud/rbac.py src/crud/field_whitelist.py src/services/permission/ --include="*.py" > /tmp/bg2.txt || true; } && echo "BG2_NON_DEPRECATED=$(grep -Evc 'DEPRECATED|deprecated' /tmp/bg2.txt || true)"`（`BG2_NON_DEPRECATED=0`）
- `cd backend && { grep -rEn "PermissionGrant|ResourcePermission|OrganizationPermissionService|OrganizationPermissionChecker" src/api/v1 src/services src/middleware src/crud/rbac.py src/models/rbac.py src/crud/field_whitelist.py --include="*.py" > /tmp/bg3.txt || true; } && echo "BG3_NON_DEPRECATED=$(grep -Evc 'DEPRECATED|deprecated' /tmp/bg3.txt || true)"`（`BG3_NON_DEPRECATED=0`）
- `cd backend && { grep -rEn "ownership_id|ownership_ids" src/models/rent_contract.py src/services/rent_contract/ src/crud/rent_contract.py src/crud/collection.py src/api/v1/rent_contracts/ --include="*.py" > /tmp/bg4.txt || true; } && echo "BG4_NON_DEPRECATED=$(grep -Evc 'DEPRECATED|deprecated' /tmp/bg4.txt || true)"`（`BG4_NON_DEPRECATED=0`）
- `cd backend && ./.venv/bin/python - <<'PY'
from sqlalchemy import create_engine, text
url = "postgresql+psycopg://zcgl_user:postgres@127.0.0.1:5432/zcgl_test"
engine = create_engine(url)
with engine.connect() as conn:
  count = conn.execute(text("SELECT COUNT(*) FROM roles WHERE scope NOT IN ('SYSTEM','ORGANIZATION')")).scalar_one()
print(f"ROLES_SCOPE_INVALID_COUNT={count}")
PY`（`ROLES_SCOPE_INVALID_COUNT=0`）

### 2.92 本批新增验证（已通过，鉴权/组织可见范围抽样回归 + Gate 同步）
- `cd backend && ./.venv/bin/python -m pytest --no-cov tests/unit/middleware/test_authz_dependency.py tests/unit/api/v1/test_organization_layering.py tests/unit/api/v1/test_roles_layering.py tests/unit/api/v1/test_users_layering.py tests/unit/api/v1/test_auth_sessions_layering.py tests/unit/api/v1/test_auth_audit_layering.py tests/unit/api/v1/test_auth_security_layering.py tests/integration/api/test_project_visibility_real.py tests/integration/crud/test_project_tenant_scope_real.py tests/integration/test_asset_lifecycle.py -q`（`32 passed`）
- `cd backend && if ! grep -rEql "TenantFilter|_apply_tenant_filter|tenant_filter\\.organization_ids" src/ --include="*.py"; then echo "BG1_STATUS=PASS"; else echo "BG1_STATUS=FAIL"; fi`（`BG1_STATUS=PASS`）
- `cd backend && { grep -rEn "organization_id" src/models/rbac.py src/crud/rbac.py src/crud/field_whitelist.py src/services/permission/ --include="*.py" > /tmp/bg2.txt || true; } && echo "BG2_NON_DEPRECATED=$(grep -Evc 'DEPRECATED|deprecated' /tmp/bg2.txt || true)"`（`BG2_NON_DEPRECATED=0`）
- `cd backend && { grep -rEn "PermissionGrant|ResourcePermission|OrganizationPermissionService|OrganizationPermissionChecker" src/api/v1 src/services src/middleware src/crud/rbac.py src/models/rbac.py src/crud/field_whitelist.py --include="*.py" > /tmp/bg3.txt || true; } && echo "BG3_NON_DEPRECATED=$(grep -Evc 'DEPRECATED|deprecated' /tmp/bg3.txt || true)"`（`BG3_NON_DEPRECATED=0`）
- `cd backend && { grep -rEn "ownership_id|ownership_ids" src/models/rent_contract.py src/services/rent_contract/ src/crud/rent_contract.py src/crud/collection.py src/api/v1/rent_contracts/ --include="*.py" > /tmp/bg4.txt || true; } && echo "BG4_NON_DEPRECATED=$(grep -Evc 'DEPRECATED|deprecated' /tmp/bg4.txt || true)"`（`BG4_NON_DEPRECATED=0`）

### 2.93 本批新增验证（已通过，扩大回归复跑 + Gate 同步）
- `cd backend && ./.venv/bin/python -m pytest --no-cov -m "not slow and not e2e" -x -q`（`4538 passed, 8 skipped, 14 deselected`）
- `cd backend && if ! grep -rEql "TenantFilter|_apply_tenant_filter|tenant_filter\\.organization_ids" src/ --include="*.py"; then echo "BG1_STATUS=PASS"; else echo "BG1_STATUS=FAIL"; fi`（`BG1_STATUS=PASS`）
- `cd backend && { grep -rEn "organization_id" src/models/rbac.py src/crud/rbac.py src/crud/field_whitelist.py src/services/permission/ --include="*.py" > /tmp/bg2.txt || true; } && echo "BG2_NON_DEPRECATED=$(grep -Evc 'DEPRECATED|deprecated' /tmp/bg2.txt || true)"`（`BG2_NON_DEPRECATED=0`）
- `cd backend && { grep -rEn "PermissionGrant|ResourcePermission|OrganizationPermissionService|OrganizationPermissionChecker" src/api/v1 src/services src/middleware src/crud/rbac.py src/models/rbac.py src/crud/field_whitelist.py --include="*.py" > /tmp/bg3.txt || true; } && echo "BG3_NON_DEPRECATED=$(grep -Evc 'DEPRECATED|deprecated' /tmp/bg3.txt || true)"`（`BG3_NON_DEPRECATED=0`）
- `cd backend && { grep -rEn "ownership_id|ownership_ids" src/models/rent_contract.py src/services/rent_contract/ src/crud/rent_contract.py src/crud/collection.py src/api/v1/rent_contracts/ --include="*.py" > /tmp/bg4.txt || true; } && echo "BG4_NON_DEPRECATED=$(grep -Evc 'DEPRECATED|deprecated' /tmp/bg4.txt || true)"`（`BG4_NON_DEPRECATED=0`）

### 2.94 本批新增验证（已通过，Gate + 迁移 + 角色作用域复核）
- `cd backend && ./.venv/bin/python -m pytest --no-cov tests/unit/migration/test_backfill.py -q`（`5 passed`）
- `cd backend && if ! grep -rEql "TenantFilter|_apply_tenant_filter|tenant_filter\\.organization_ids" src/ --include="*.py"; then echo "BG1_STATUS=PASS"; else echo "BG1_STATUS=FAIL"; fi`（`BG1_STATUS=PASS`）
- `cd backend && { grep -rEn "organization_id" src/models/rbac.py src/crud/rbac.py src/crud/field_whitelist.py src/services/permission/ --include="*.py" > /tmp/bg2.txt || true; } && echo "BG2_NON_DEPRECATED=$(grep -Evc 'DEPRECATED|deprecated' /tmp/bg2.txt || true)"`（`BG2_NON_DEPRECATED=0`）
- `cd backend && { grep -rEn "PermissionGrant|ResourcePermission|OrganizationPermissionService|OrganizationPermissionChecker" src/api/v1 src/services src/middleware src/crud/rbac.py src/models/rbac.py src/crud/field_whitelist.py --include="*.py" > /tmp/bg3.txt || true; } && echo "BG3_NON_DEPRECATED=$(grep -Evc 'DEPRECATED|deprecated' /tmp/bg3.txt || true)"`（`BG3_NON_DEPRECATED=0`）
- `cd backend && { grep -rEn "ownership_id|ownership_ids" src/models/rent_contract.py src/services/rent_contract/ src/crud/rent_contract.py src/crud/collection.py src/api/v1/rent_contracts/ --include="*.py" > /tmp/bg4.txt || true; } && echo "BG4_NON_DEPRECATED=$(grep -Evc 'DEPRECATED|deprecated' /tmp/bg4.txt || true)"`（`BG4_NON_DEPRECATED=0`）
- `cd backend && ./.venv/bin/python - <<'PY'
from sqlalchemy import create_engine, text
url = "postgresql+psycopg://zcgl_user:postgres@127.0.0.1:5432/zcgl_test"
engine = create_engine(url)
with engine.connect() as conn:
  count = conn.execute(text("SELECT COUNT(*) FROM roles WHERE scope NOT IN ('SYSTEM','ORGANIZATION')")).scalar_one()
print(f"ROLES_SCOPE_INVALID_COUNT={count}")
PY`（`ROLES_SCOPE_INVALID_COUNT=0`）

### 2.95 本批新增验证（已通过，鉴权/组织可见范围抽样回归 + Gate 同步）
- `cd backend && ./.venv/bin/python -m pytest --no-cov tests/unit/middleware/test_authz_dependency.py tests/unit/api/v1/test_organization_layering.py tests/unit/api/v1/test_roles_layering.py tests/unit/api/v1/test_users_layering.py tests/unit/api/v1/test_auth_sessions_layering.py tests/unit/api/v1/test_auth_audit_layering.py tests/unit/api/v1/test_auth_security_layering.py tests/integration/api/test_project_visibility_real.py tests/integration/crud/test_project_tenant_scope_real.py tests/integration/test_asset_lifecycle.py -q`（`32 passed`）
- `cd backend && if ! grep -rEql "TenantFilter|_apply_tenant_filter|tenant_filter\\.organization_ids" src/ --include="*.py"; then echo "BG1_STATUS=PASS"; else echo "BG1_STATUS=FAIL"; fi`（`BG1_STATUS=PASS`）
- `cd backend && { grep -rEn "organization_id" src/models/rbac.py src/crud/rbac.py src/crud/field_whitelist.py src/services/permission/ --include="*.py" > /tmp/bg2.txt || true; } && echo "BG2_NON_DEPRECATED=$(grep -Evc 'DEPRECATED|deprecated' /tmp/bg2.txt || true)"`（`BG2_NON_DEPRECATED=0`）
- `cd backend && { grep -rEn "PermissionGrant|ResourcePermission|OrganizationPermissionService|OrganizationPermissionChecker" src/api/v1 src/services src/middleware src/crud/rbac.py src/models/rbac.py src/crud/field_whitelist.py --include="*.py" > /tmp/bg3.txt || true; } && echo "BG3_NON_DEPRECATED=$(grep -Evc 'DEPRECATED|deprecated' /tmp/bg3.txt || true)"`（`BG3_NON_DEPRECATED=0`）
- `cd backend && { grep -rEn "ownership_id|ownership_ids" src/models/rent_contract.py src/services/rent_contract/ src/crud/rent_contract.py src/crud/collection.py src/api/v1/rent_contracts/ --include="*.py" > /tmp/bg4.txt || true; } && echo "BG4_NON_DEPRECATED=$(grep -Evc 'DEPRECATED|deprecated' /tmp/bg4.txt || true)"`（`BG4_NON_DEPRECATED=0`）

### 2.96 本批新增验证（已通过，扩大回归复跑 + Gate 同步）
- `cd backend && ./.venv/bin/python -m pytest --no-cov -m "not slow and not e2e" -x -q`（`4538 passed, 8 skipped, 14 deselected`）
- `cd backend && if ! grep -rEql "TenantFilter|_apply_tenant_filter|tenant_filter\\.organization_ids" src/ --include="*.py"; then echo "BG1_STATUS=PASS"; else echo "BG1_STATUS=FAIL"; fi`（`BG1_STATUS=PASS`）
- `cd backend && { grep -rEn "organization_id" src/models/rbac.py src/crud/rbac.py src/crud/field_whitelist.py src/services/permission/ --include="*.py" > /tmp/bg2.txt || true; } && echo "BG2_NON_DEPRECATED=$(grep -Evc 'DEPRECATED|deprecated' /tmp/bg2.txt || true)"`（`BG2_NON_DEPRECATED=0`）
- `cd backend && { grep -rEn "PermissionGrant|ResourcePermission|OrganizationPermissionService|OrganizationPermissionChecker" src/api/v1 src/services src/middleware src/crud/rbac.py src/models/rbac.py src/crud/field_whitelist.py --include="*.py" > /tmp/bg3.txt || true; } && echo "BG3_NON_DEPRECATED=$(grep -Evc 'DEPRECATED|deprecated' /tmp/bg3.txt || true)"`（`BG3_NON_DEPRECATED=0`）
- `cd backend && { grep -rEn "ownership_id|ownership_ids" src/models/rent_contract.py src/services/rent_contract/ src/crud/rent_contract.py src/crud/collection.py src/api/v1/rent_contracts/ --include="*.py" > /tmp/bg4.txt || true; } && echo "BG4_NON_DEPRECATED=$(grep -Evc 'DEPRECATED|deprecated' /tmp/bg4.txt || true)"`（`BG4_NON_DEPRECATED=0`）

### 2.97 本批新增验证（已通过，鉴权/组织可见范围抽样回归 + Gate 同步）
- `cd backend && ./.venv/bin/python -m pytest --no-cov tests/unit/middleware/test_authz_dependency.py tests/unit/api/v1/test_organization_layering.py tests/unit/api/v1/test_roles_layering.py tests/unit/api/v1/test_users_layering.py tests/unit/api/v1/test_auth_sessions_layering.py tests/unit/api/v1/test_auth_audit_layering.py tests/unit/api/v1/test_auth_security_layering.py tests/integration/api/test_project_visibility_real.py tests/integration/crud/test_project_tenant_scope_real.py tests/integration/test_asset_lifecycle.py -q`（`32 passed`）
- `cd backend && if ! grep -rEql "TenantFilter|_apply_tenant_filter|tenant_filter\\.organization_ids" src/ --include="*.py"; then echo "BG1_STATUS=PASS"; else echo "BG1_STATUS=FAIL"; fi`（`BG1_STATUS=PASS`）
- `cd backend && { grep -rEn "organization_id" src/models/rbac.py src/crud/rbac.py src/crud/field_whitelist.py src/services/permission/ --include="*.py" > /tmp/bg2.txt || true; } && echo "BG2_NON_DEPRECATED=$(grep -Evc 'DEPRECATED|deprecated' /tmp/bg2.txt || true)"`（`BG2_NON_DEPRECATED=0`）
- `cd backend && { grep -rEn "PermissionGrant|ResourcePermission|OrganizationPermissionService|OrganizationPermissionChecker" src/api/v1 src/services src/middleware src/crud/rbac.py src/models/rbac.py src/crud/field_whitelist.py --include="*.py" > /tmp/bg3.txt || true; } && echo "BG3_NON_DEPRECATED=$(grep -Evc 'DEPRECATED|deprecated' /tmp/bg3.txt || true)"`（`BG3_NON_DEPRECATED=0`）
- `cd backend && { grep -rEn "ownership_id|ownership_ids" src/models/rent_contract.py src/services/rent_contract/ src/crud/rent_contract.py src/crud/collection.py src/api/v1/rent_contracts/ --include="*.py" > /tmp/bg4.txt || true; } && echo "BG4_NON_DEPRECATED=$(grep -Evc 'DEPRECATED|deprecated' /tmp/bg4.txt || true)"`（`BG4_NON_DEPRECATED=0`）

### 2.98 本批新增验证（已通过，扩大回归复跑 + Gate 同步）
- `cd backend && ./.venv/bin/python -m pytest --no-cov -m "not slow and not e2e" -x -q`（`4541 passed, 8 skipped, 14 deselected`）
- `cd backend && if ! grep -rEql "TenantFilter|_apply_tenant_filter|tenant_filter\\.organization_ids" src/ --include="*.py"; then echo "BG1_STATUS=PASS"; else echo "BG1_STATUS=FAIL"; fi`（`BG1_STATUS=PASS`）
- `cd backend && { grep -rEn "organization_id" src/models/rbac.py src/crud/rbac.py src/crud/field_whitelist.py src/services/permission/ --include="*.py" > /tmp/bg2.txt || true; } && echo "BG2_NON_DEPRECATED=$(grep -Evc 'DEPRECATED|deprecated' /tmp/bg2.txt || true)"`（`BG2_NON_DEPRECATED=0`）
- `cd backend && { grep -rEn "PermissionGrant|ResourcePermission|OrganizationPermissionService|OrganizationPermissionChecker" src/api/v1 src/services src/middleware src/crud/rbac.py src/models/rbac.py src/crud/field_whitelist.py --include="*.py" > /tmp/bg3.txt || true; } && echo "BG3_NON_DEPRECATED=$(grep -Evc 'DEPRECATED|deprecated' /tmp/bg3.txt || true)"`（`BG3_NON_DEPRECATED=0`）
- `cd backend && { grep -rEn "ownership_id|ownership_ids" src/models/rent_contract.py src/services/rent_contract/ src/crud/rent_contract.py src/crud/collection.py src/api/v1/rent_contracts/ --include="*.py" > /tmp/bg4.txt || true; } && echo "BG4_NON_DEPRECATED=$(grep -Evc 'DEPRECATED|deprecated' /tmp/bg4.txt || true)"`（`BG4_NON_DEPRECATED=0`）

### 2.99 本批新增验证（已通过，鉴权/组织可见范围抽样回归 + Gate 同步）
- `cd backend && ./.venv/bin/python -m pytest --no-cov tests/unit/middleware/test_authz_dependency.py tests/unit/api/v1/test_organization_layering.py tests/unit/api/v1/test_roles_layering.py tests/unit/api/v1/test_users_layering.py tests/unit/api/v1/test_auth_sessions_layering.py tests/unit/api/v1/test_auth_audit_layering.py tests/unit/api/v1/test_auth_security_layering.py tests/integration/api/test_project_visibility_real.py tests/integration/crud/test_project_tenant_scope_real.py tests/integration/test_asset_lifecycle.py -q`（`32 passed`）
- `cd backend && if ! grep -rEql "TenantFilter|_apply_tenant_filter|tenant_filter\\.organization_ids" src/ --include="*.py"; then echo "BG1_STATUS=PASS"; else echo "BG1_STATUS=FAIL"; fi`（`BG1_STATUS=PASS`）
- `cd backend && { grep -rEn "organization_id" src/models/rbac.py src/crud/rbac.py src/crud/field_whitelist.py src/services/permission/ --include="*.py" > /tmp/bg2.txt || true; } && echo "BG2_NON_DEPRECATED=$(grep -Evc 'DEPRECATED|deprecated' /tmp/bg2.txt || true)"`（`BG2_NON_DEPRECATED=0`）
- `cd backend && { grep -rEn "PermissionGrant|ResourcePermission|OrganizationPermissionService|OrganizationPermissionChecker" src/api/v1 src/services src/middleware src/crud/rbac.py src/models/rbac.py src/crud/field_whitelist.py --include="*.py" > /tmp/bg3.txt || true; } && echo "BG3_NON_DEPRECATED=$(grep -Evc 'DEPRECATED|deprecated' /tmp/bg3.txt || true)"`（`BG3_NON_DEPRECATED=0`）
- `cd backend && { grep -rEn "ownership_id|ownership_ids" src/models/rent_contract.py src/services/rent_contract/ src/crud/rent_contract.py src/crud/collection.py src/api/v1/rent_contracts/ --include="*.py" > /tmp/bg4.txt || true; } && echo "BG4_NON_DEPRECATED=$(grep -Evc 'DEPRECATED|deprecated' /tmp/bg4.txt || true)"`（`BG4_NON_DEPRECATED=0`）

### 2.100 本批新增验证（已通过，扩大回归复跑 + Gate 同步）
- `cd backend && ./.venv/bin/python -m pytest --no-cov -m "not slow and not e2e" -x -q`（`4543 passed, 8 skipped, 14 deselected`）
- `cd backend && ./.venv/bin/ruff check src/crud/rbac.py`（通过）
- `cd backend && ./.venv/bin/python -m pytest --no-cov tests/unit/crud/test_rbac.py -q`（`20 passed`）
- `cd backend && if ! grep -rEql "TenantFilter|_apply_tenant_filter|tenant_filter\\.organization_ids" src/ --include="*.py"; then echo "BG1_STATUS=PASS"; else echo "BG1_STATUS=FAIL"; fi`（`BG1_STATUS=PASS`）
- `cd backend && { grep -rEn "organization_id" src/models/rbac.py src/crud/rbac.py src/crud/field_whitelist.py src/services/permission/ --include="*.py" > /tmp/bg2.txt || true; } && echo "BG2_NON_DEPRECATED=$(grep -Evc 'DEPRECATED|deprecated' /tmp/bg2.txt || true)"`（`BG2_NON_DEPRECATED=0`）
- `cd backend && { grep -rEn "PermissionGrant|ResourcePermission|OrganizationPermissionService|OrganizationPermissionChecker" src/api/v1 src/services src/middleware src/crud/rbac.py src/models/rbac.py src/crud/field_whitelist.py --include="*.py" > /tmp/bg3.txt || true; } && echo "BG3_NON_DEPRECATED=$(grep -Evc 'DEPRECATED|deprecated' /tmp/bg3.txt || true)"`（`BG3_NON_DEPRECATED=0`）
- `cd backend && { grep -rEn "ownership_id|ownership_ids" src/models/rent_contract.py src/services/rent_contract/ src/crud/rent_contract.py src/crud/collection.py src/api/v1/rent_contracts/ --include="*.py" > /tmp/bg4.txt || true; } && echo "BG4_NON_DEPRECATED=$(grep -Evc 'DEPRECATED|deprecated' /tmp/bg4.txt || true)"`（`BG4_NON_DEPRECATED=0`）

### 2.101 本批新增验证（已通过，鉴权/组织可见范围抽样回归 + Gate 同步）
- `cd backend && ./.venv/bin/python -m pytest --no-cov tests/unit/middleware/test_authz_dependency.py tests/unit/api/v1/test_organization_layering.py tests/unit/api/v1/test_roles_layering.py tests/unit/api/v1/test_users_layering.py tests/unit/api/v1/test_auth_sessions_layering.py tests/unit/api/v1/test_auth_audit_layering.py tests/unit/api/v1/test_auth_security_layering.py tests/integration/api/test_project_visibility_real.py tests/integration/crud/test_project_tenant_scope_real.py tests/integration/test_asset_lifecycle.py -q`（`34 passed`）
- `cd backend && if ! grep -rEql "TenantFilter|_apply_tenant_filter|tenant_filter\\.organization_ids" src/ --include="*.py"; then echo "BG1_STATUS=PASS"; else echo "BG1_STATUS=FAIL"; fi`（`BG1_STATUS=PASS`）
- `cd backend && { grep -rEn "organization_id" src/models/rbac.py src/crud/rbac.py src/crud/field_whitelist.py src/services/permission/ --include="*.py" > /tmp/bg2.txt || true; } && echo "BG2_NON_DEPRECATED=$(grep -Evc 'DEPRECATED|deprecated' /tmp/bg2.txt || true)"`（`BG2_NON_DEPRECATED=0`）
- `cd backend && { grep -rEn "PermissionGrant|ResourcePermission|OrganizationPermissionService|OrganizationPermissionChecker" src/api/v1 src/services src/middleware src/crud/rbac.py src/models/rbac.py src/crud/field_whitelist.py --include="*.py" > /tmp/bg3.txt || true; } && echo "BG3_NON_DEPRECATED=$(grep -Evc 'DEPRECATED|deprecated' /tmp/bg3.txt || true)"`（`BG3_NON_DEPRECATED=0`）
- `cd backend && { grep -rEn "ownership_id|ownership_ids" src/models/rent_contract.py src/services/rent_contract/ src/crud/rent_contract.py src/crud/collection.py src/api/v1/rent_contracts/ --include="*.py" > /tmp/bg4.txt || true; } && echo "BG4_NON_DEPRECATED=$(grep -Evc 'DEPRECATED|deprecated' /tmp/bg4.txt || true)"`（`BG4_NON_DEPRECATED=0`）

### 2.102 本批新增验证（已通过，扩大回归复跑 + Gate 同步）
- `cd backend && ./.venv/bin/python -m pytest --no-cov -m "not slow and not e2e" -x -q`（`4543 passed, 8 skipped, 14 deselected`）
- `cd backend && if ! grep -rEql "TenantFilter|_apply_tenant_filter|tenant_filter\\.organization_ids" src/ --include="*.py"; then echo "BG1_STATUS=PASS"; else echo "BG1_STATUS=FAIL"; fi`（`BG1_STATUS=PASS`）
- `cd backend && { grep -rEn "organization_id" src/models/rbac.py src/crud/rbac.py src/crud/field_whitelist.py src/services/permission/ --include="*.py" > /tmp/bg2.txt || true; } && echo "BG2_NON_DEPRECATED=$(grep -Evc 'DEPRECATED|deprecated' /tmp/bg2.txt || true)"`（`BG2_NON_DEPRECATED=0`）
- `cd backend && { grep -rEn "PermissionGrant|ResourcePermission|OrganizationPermissionService|OrganizationPermissionChecker" src/api/v1 src/services src/middleware src/crud/rbac.py src/models/rbac.py src/crud/field_whitelist.py --include="*.py" > /tmp/bg3.txt || true; } && echo "BG3_NON_DEPRECATED=$(grep -Evc 'DEPRECATED|deprecated' /tmp/bg3.txt || true)"`（`BG3_NON_DEPRECATED=0`）
- `cd backend && { grep -rEn "ownership_id|ownership_ids" src/models/rent_contract.py src/services/rent_contract/ src/crud/rent_contract.py src/crud/collection.py src/api/v1/rent_contracts/ --include="*.py" > /tmp/bg4.txt || true; } && echo "BG4_NON_DEPRECATED=$(grep -Evc 'DEPRECATED|deprecated' /tmp/bg4.txt || true)"`（`BG4_NON_DEPRECATED=0`）

### 2.103 本批新增验证（已通过，鉴权/组织可见范围抽样回归 + Gate 同步）
- `cd backend && ./.venv/bin/python -m pytest --no-cov tests/unit/middleware/test_authz_dependency.py tests/unit/api/v1/test_organization_layering.py tests/unit/api/v1/test_roles_layering.py tests/unit/api/v1/test_users_layering.py tests/unit/api/v1/test_auth_sessions_layering.py tests/unit/api/v1/test_auth_audit_layering.py tests/unit/api/v1/test_auth_security_layering.py tests/integration/api/test_project_visibility_real.py tests/integration/crud/test_project_tenant_scope_real.py tests/integration/test_asset_lifecycle.py -q`（`34 passed`）
- `cd backend && if ! grep -rEql "TenantFilter|_apply_tenant_filter|tenant_filter\\.organization_ids" src/ --include="*.py"; then echo "BG1_STATUS=PASS"; else echo "BG1_STATUS=FAIL"; fi`（`BG1_STATUS=PASS`）
- `cd backend && { grep -rEn "organization_id" src/models/rbac.py src/crud/rbac.py src/crud/field_whitelist.py src/services/permission/ --include="*.py" > /tmp/bg2.txt || true; } && echo "BG2_NON_DEPRECATED=$(grep -Evc 'DEPRECATED|deprecated' /tmp/bg2.txt || true)"`（`BG2_NON_DEPRECATED=0`）
- `cd backend && { grep -rEn "PermissionGrant|ResourcePermission|OrganizationPermissionService|OrganizationPermissionChecker" src/api/v1 src/services src/middleware src/crud/rbac.py src/models/rbac.py src/crud/field_whitelist.py --include="*.py" > /tmp/bg3.txt || true; } && echo "BG3_NON_DEPRECATED=$(grep -Evc 'DEPRECATED|deprecated' /tmp/bg3.txt || true)"`（`BG3_NON_DEPRECATED=0`）
- `cd backend && { grep -rEn "ownership_id|ownership_ids" src/models/rent_contract.py src/services/rent_contract/ src/crud/rent_contract.py src/crud/collection.py src/api/v1/rent_contracts/ --include="*.py" > /tmp/bg4.txt || true; } && echo "BG4_NON_DEPRECATED=$(grep -Evc 'DEPRECATED|deprecated' /tmp/bg4.txt || true)"`（`BG4_NON_DEPRECATED=0`）

### 2.104 本批新增验证（已通过，扩大回归复跑 + Gate 同步）
- `cd backend && ./.venv/bin/python -m pytest --no-cov -m "not slow and not e2e" -x -q`（`4543 passed, 8 skipped, 14 deselected`）
- `cd backend && if ! grep -rEql "TenantFilter|_apply_tenant_filter|tenant_filter\\.organization_ids" src/ --include="*.py"; then echo "BG1_STATUS=PASS"; else echo "BG1_STATUS=FAIL"; fi`（`BG1_STATUS=PASS`）
- `cd backend && { grep -rEn "organization_id" src/models/rbac.py src/crud/rbac.py src/crud/field_whitelist.py src/services/permission/ --include="*.py" > /tmp/bg2.txt || true; } && echo "BG2_NON_DEPRECATED=$(grep -Evc 'DEPRECATED|deprecated' /tmp/bg2.txt || true)"`（`BG2_NON_DEPRECATED=0`）
- `cd backend && { grep -rEn "PermissionGrant|ResourcePermission|OrganizationPermissionService|OrganizationPermissionChecker" src/api/v1 src/services src/middleware src/crud/rbac.py src/models/rbac.py src/crud/field_whitelist.py --include="*.py" > /tmp/bg3.txt || true; } && echo "BG3_NON_DEPRECATED=$(grep -Evc 'DEPRECATED|deprecated' /tmp/bg3.txt || true)"`（`BG3_NON_DEPRECATED=0`）
- `cd backend && { grep -rEn "ownership_id|ownership_ids" src/models/rent_contract.py src/services/rent_contract/ src/crud/rent_contract.py src/crud/collection.py src/api/v1/rent_contracts/ --include="*.py" > /tmp/bg4.txt || true; } && echo "BG4_NON_DEPRECATED=$(grep -Evc 'DEPRECATED|deprecated' /tmp/bg4.txt || true)"`（`BG4_NON_DEPRECATED=0`）

### 2.105 本批新增验证（已通过，鉴权/组织可见范围抽样回归 + Gate 同步）
- `cd backend && ./.venv/bin/python -m pytest --no-cov tests/unit/middleware/test_authz_dependency.py tests/unit/api/v1/test_organization_layering.py tests/unit/api/v1/test_roles_layering.py tests/unit/api/v1/test_users_layering.py tests/unit/api/v1/test_auth_sessions_layering.py tests/unit/api/v1/test_auth_audit_layering.py tests/unit/api/v1/test_auth_security_layering.py tests/integration/api/test_project_visibility_real.py tests/integration/crud/test_project_tenant_scope_real.py tests/integration/test_asset_lifecycle.py -q`（`34 passed`）
- `cd backend && if ! grep -rEql "TenantFilter|_apply_tenant_filter|tenant_filter\\.organization_ids" src/ --include="*.py"; then echo "BG1_STATUS=PASS"; else echo "BG1_STATUS=FAIL"; fi`（`BG1_STATUS=PASS`）
- `cd backend && { grep -rEn "organization_id" src/models/rbac.py src/crud/rbac.py src/crud/field_whitelist.py src/services/permission/ --include="*.py" > /tmp/bg2.txt || true; } && echo "BG2_NON_DEPRECATED=$(grep -Evc 'DEPRECATED|deprecated' /tmp/bg2.txt || true)"`（`BG2_NON_DEPRECATED=0`）
- `cd backend && { grep -rEn "PermissionGrant|ResourcePermission|OrganizationPermissionService|OrganizationPermissionChecker" src/api/v1 src/services src/middleware src/crud/rbac.py src/models/rbac.py src/crud/field_whitelist.py --include="*.py" > /tmp/bg3.txt || true; } && echo "BG3_NON_DEPRECATED=$(grep -Evc 'DEPRECATED|deprecated' /tmp/bg3.txt || true)"`（`BG3_NON_DEPRECATED=0`）
- `cd backend && { grep -rEn "ownership_id|ownership_ids" src/models/rent_contract.py src/services/rent_contract/ src/crud/rent_contract.py src/crud/collection.py src/api/v1/rent_contracts/ --include="*.py" > /tmp/bg4.txt || true; } && echo "BG4_NON_DEPRECATED=$(grep -Evc 'DEPRECATED|deprecated' /tmp/bg4.txt || true)"`（`BG4_NON_DEPRECATED=0`）

### 2.106 本批新增验证（已通过，扩大回归复跑 + Gate 同步）
- `cd backend && ./.venv/bin/python -m pytest --no-cov -m "not slow and not e2e" -x -q`（`4545 passed, 8 skipped, 14 deselected`）
- `cd backend && if ! grep -rEql "TenantFilter|_apply_tenant_filter|tenant_filter\\.organization_ids" src/ --include="*.py"; then echo "BG1_STATUS=PASS"; else echo "BG1_STATUS=FAIL"; fi`（`BG1_STATUS=PASS`）
- `cd backend && { grep -rEn "organization_id" src/models/rbac.py src/crud/rbac.py src/crud/field_whitelist.py src/services/permission/ --include="*.py" > /tmp/bg2.txt || true; } && echo "BG2_NON_DEPRECATED=$(grep -Evc 'DEPRECATED|deprecated' /tmp/bg2.txt || true)"`（`BG2_NON_DEPRECATED=0`）
- `cd backend && { grep -rEn "PermissionGrant|ResourcePermission|OrganizationPermissionService|OrganizationPermissionChecker" src/api/v1 src/services src/middleware src/crud/rbac.py src/models/rbac.py src/crud/field_whitelist.py --include="*.py" > /tmp/bg3.txt || true; } && echo "BG3_NON_DEPRECATED=$(grep -Evc 'DEPRECATED|deprecated' /tmp/bg3.txt || true)"`（`BG3_NON_DEPRECATED=0`）
- `cd backend && { grep -rEn "ownership_id|ownership_ids" src/models/rent_contract.py src/services/rent_contract/ src/crud/rent_contract.py src/crud/collection.py src/api/v1/rent_contracts/ --include="*.py" > /tmp/bg4.txt || true; } && echo "BG4_NON_DEPRECATED=$(grep -Evc 'DEPRECATED|deprecated' /tmp/bg4.txt || true)"`（`BG4_NON_DEPRECATED=0`）

### 2.107 本批新增验证（已通过，鉴权/组织可见范围抽样回归 + Gate 同步）
- `cd backend && ./.venv/bin/python -m pytest --no-cov tests/unit/middleware/test_authz_dependency.py tests/unit/api/v1/test_organization_layering.py tests/unit/api/v1/test_roles_layering.py tests/unit/api/v1/test_users_layering.py tests/unit/api/v1/test_auth_sessions_layering.py tests/unit/api/v1/test_auth_audit_layering.py tests/unit/api/v1/test_auth_security_layering.py tests/integration/api/test_project_visibility_real.py tests/integration/crud/test_project_tenant_scope_real.py tests/integration/test_asset_lifecycle.py -q`（`34 passed`）
- `cd backend && if ! grep -rEql "TenantFilter|_apply_tenant_filter|tenant_filter\\.organization_ids" src/ --include="*.py"; then echo "BG1_STATUS=PASS"; else echo "BG1_STATUS=FAIL"; fi`（`BG1_STATUS=PASS`）
- `cd backend && { grep -rEn "organization_id" src/models/rbac.py src/crud/rbac.py src/crud/field_whitelist.py src/services/permission/ --include="*.py" > /tmp/bg2.txt || true; } && echo "BG2_NON_DEPRECATED=$(grep -Evc 'DEPRECATED|deprecated' /tmp/bg2.txt || true)"`（`BG2_NON_DEPRECATED=0`）
- `cd backend && { grep -rEn "PermissionGrant|ResourcePermission|OrganizationPermissionService|OrganizationPermissionChecker" src/api/v1 src/services src/middleware src/crud/rbac.py src/models/rbac.py src/crud/field_whitelist.py --include="*.py" > /tmp/bg3.txt || true; } && echo "BG3_NON_DEPRECATED=$(grep -Evc 'DEPRECATED|deprecated' /tmp/bg3.txt || true)"`（`BG3_NON_DEPRECATED=0`）
- `cd backend && { grep -rEn "ownership_id|ownership_ids" src/models/rent_contract.py src/services/rent_contract/ src/crud/rent_contract.py src/crud/collection.py src/api/v1/rent_contracts/ --include="*.py" > /tmp/bg4.txt || true; } && echo "BG4_NON_DEPRECATED=$(grep -Evc 'DEPRECATED|deprecated' /tmp/bg4.txt || true)"`（`BG4_NON_DEPRECATED=0`）

## 3. 当前未完成项（已清零）

1. P2c API 层覆盖
  - 当前状态：已完成收口，`backend/src/api/v1/*` 无 `require_permission(...)` 运行时调用。
  - 收口结论：无需新增覆盖改造批次，维持门禁维护即可。

2. BG-1/2/3/4 Gate
  - 当前状态：本轮复核通过（`BG1_STATUS=PASS`，`BG2/3/4_NON_DEPRECATED=0`）。
  - 收口结论：门禁项已完成，本窗口无待处理。

3. 阶段性回归
  - 当前状态：已完成 Gate/迁移复核（2.91）+ 抽样回归（2.92）+ 扩大回归（2.93）+ Gate/迁移复核（2.94）+ 抽样回归（2.95）+ 扩大回归（2.96）+ 抽样回归（2.97）+ 扩大回归（2.98）+ 抽样回归（2.99）+ 扩大回归（2.100）+ 抽样回归（2.101）+ 扩大回归（2.102）+ 抽样回归（2.103）+ 扩大回归（2.104）+ 抽样回归（2.105）+ 扩大回归（2.106）+ 抽样回归（2.107）。
  - 收口结论：本窗口回归任务已完成，无待处理。

## 4. 建议执行顺序（新窗口）

1. 先做 grep 盘点（BG-3 / BG-4）
```bash
cd backend
{ grep -rEn "PermissionGrant|ResourcePermission|OrganizationPermissionService|OrganizationPermissionChecker" src/api/v1 src/services src/middleware src/crud/rbac.py src/models/rbac.py src/crud/field_whitelist.py --include="*.py" > /tmp/bg3.txt || true; } && [[ ! -s /tmp/bg3.txt || $(grep -Evc "DEPRECATED|deprecated" /tmp/bg3.txt) -eq 0 ]]
{ grep -rEn "ownership_id|ownership_ids" src/models/rent_contract.py src/services/rent_contract/ src/crud/rent_contract.py src/crud/collection.py src/api/v1/rent_contracts/ --include="*.py" > /tmp/bg4.txt || true; } && [[ ! -s /tmp/bg4.txt || $(grep -Evc "DEPRECATED|deprecated" /tmp/bg4.txt) -eq 0 ]]
```

2. 分批改造（每批只动一类模块）  
   - 先 API 层统一 `require_authz`，再 Service/CRUD 清理旧调用。

3. 每批验证  
```bash
cd backend
./.venv/bin/ruff check <changed-files>
./.venv/bin/python -m pytest --no-cov <target-tests> -q
```

4. 每批更新 `CHANGELOG.md`（项目约束）

## 5. 操作注意事项

- 使用 `backend/.venv` 运行后端命令。
- 当前工作树已有大量既存改动，避免回滚不相关文件。
- 文件编辑使用 `apply_patch`。
- 本文件用于交接，不替代正式计划文档，计划基线仍是：`docs/plans/2026-02-19-phase2-implementation-plan.md`。
