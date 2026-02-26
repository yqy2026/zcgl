# ABAC `resource_type` 漂移矩阵（首轮）

- 日期：2026-02-22
- 范围：`backend/src/api/v1/**` 中所有 `require_authz(...)`
- 方法：AST 扫描调用点并聚合 `resource_type`

## 1) 全量分布

- 总调用点：`333`
- 分布：
  - `asset`: 229
  - `rent_contract`: 44
  - `system_monitoring`: 14
  - `excel_config`: 12
  - `party`: 10
  - `project`: 9
  - `error_recovery`: 8
  - `property_certificate`: 7

## 2) 模块热点（`asset` 占比）

- `auth`: `46/46`（100%）
- `system`: `93/121`（77%）
- `analytics`: `23/23`（100%）
- `llm_prompts.py`: `9/9`（100%）
- `assets`: `47/63`（75%，其余已语义化）
- `documents`: `11/33`（33%，其余已语义化）

## 3) 策略种子对照（迁移）

- 在 `backend/alembic/versions/**` 的 seed 迁移中，当前仅检测到：
  - `resource_type=asset`
  - `resource_type=project`

> 结论：若直接大规模把路由从 `asset` 改成语义化类型，而不补策略包/回填迁移，极易造成 deny 风险。

## 4) 第一批已落地（低风险）

已将监控主路由与现有子模块口径统一到 `system_monitoring`：

- 变更文件：
  - `backend/src/api/v1/system/monitoring.py`
  - `backend/tests/unit/api/v1/test_monitoring_layering.py`
- 变更内容：7 处 `resource_type="asset"` → `"system_monitoring"`
- 验证：
  - `pytest`: `tests/unit/api/v1/test_monitoring_layering.py tests/unit/api/v1/test_monitoring.py tests/unit/middleware/test_authz_dependency.py`（30 passed）
  - `ruff`: 上述变更文件通过

## 5) 第二批已落地（低风险，增量）

继续做最小范围语义对齐：

- 变更文件：
  - `backend/src/api/v1/system/system.py`
  - `backend/tests/unit/api/v1/test_system_layering.py`
- 变更内容：
  - `GET /monitoring/health`：`resource_type="asset"` → `"system_monitoring"`
  - `GET /system/info`、`GET /system/root` 暂保持 `asset`（避免跨语义一次性扩面）
- 验证：
  - `pytest`: `tests/unit/api/v1/test_system_layering.py tests/unit/middleware/test_authz_dependency.py`（5 passed）
  - `ruff`: 上述变更文件通过

## 6) 第三批已落地（最小粒度增量）

在保持低风险前提下，先做单端点语义对齐验证：

- 变更文件：
  - `backend/src/api/v1/system/tasks.py`
  - `backend/tests/unit/api/v1/test_tasks_layering.py`
- 变更内容：
  - `GET /tasks/{task_id}`：`resource_type="asset"` → `"task"`
  - 同步更新分层断言，仅变更 `get_task` 一项，其他任务端点暂保持 `asset`
- 验证：
  - `pytest`: `tests/unit/api/v1/test_tasks_layering.py tests/unit/middleware/test_authz_dependency.py`（8 passed）
  - `ruff`: 上述变更文件通过

## 7) 第四批已落地（最小粒度增量）

继续沿任务域做单端点语义对齐：

- 变更文件：
  - `backend/src/api/v1/system/tasks.py`
  - `backend/tests/unit/api/v1/test_tasks_layering.py`
- 变更内容：
  - `GET /tasks/{task_id}/history`：`resource_type="asset"` → `"task"`
  - 同步更新分层断言，仅变更 `get_task_history` 一项，其他任务端点暂保持 `asset`
- 验证：
  - `pytest`: `tests/unit/api/v1/test_tasks_layering.py tests/unit/middleware/test_authz_dependency.py`（8 passed）
  - `ruff`: 上述变更文件通过

## 8) 第五批已落地（最小粒度增量）

继续沿任务域做单端点语义对齐：

- 变更文件：
  - `backend/src/api/v1/system/tasks.py`
  - `backend/tests/unit/api/v1/test_tasks_layering.py`
- 变更内容：
  - `GET /tasks/statistics`：`resource_type="asset"` → `"task"`
  - 同步更新分层断言，仅变更 `get_task_statistics` 一项，其他任务端点暂保持 `asset`
- 验证：
  - `pytest`: `tests/unit/api/v1/test_tasks_layering.py tests/unit/middleware/test_authz_dependency.py`（8 passed）
  - `ruff`: 上述变更文件通过

## 9) 第六批已落地（最小粒度增量）

继续沿任务域做单端点语义对齐：

- 变更文件：
  - `backend/src/api/v1/system/tasks.py`
  - `backend/tests/unit/api/v1/test_tasks_layering.py`
- 变更内容：
  - `GET /tasks/running`：`resource_type="asset"` → `"task"`
  - 同步更新分层断言，仅变更 `get_running_tasks` 一项，其他任务端点暂保持 `asset`
- 验证：
  - `pytest`: `tests/unit/api/v1/test_tasks_layering.py tests/unit/middleware/test_authz_dependency.py`（8 passed）
  - `ruff`: 上述变更文件通过

## 10) 第七批已落地（最小粒度增量）

继续沿任务域做单端点语义对齐：

- 变更文件：
  - `backend/src/api/v1/system/tasks.py`
  - `backend/tests/unit/api/v1/test_tasks_layering.py`
- 变更内容：
  - `GET /tasks/recent`：`resource_type="asset"` → `"task"`
  - 同步更新分层断言，仅变更 `get_recent_tasks` 一项，其他任务端点暂保持 `asset`
- 验证：
  - `pytest`: `tests/unit/api/v1/test_tasks_layering.py tests/unit/middleware/test_authz_dependency.py`（8 passed）
  - `ruff`: 上述变更文件通过

## 11) 第八批已落地（最小粒度增量）

继续沿任务域做单端点语义对齐：

- 变更文件：
  - `backend/src/api/v1/system/tasks.py`
  - `backend/tests/unit/api/v1/test_tasks_layering.py`
- 变更内容：
  - `GET /tasks/cleanup`：`resource_type="asset"` → `"task"`
  - 同步更新分层断言，仅变更 `cleanup_old_tasks` 一项，任务域主查询端点已全部切换为 `task`
- 验证：
  - `pytest`: `tests/unit/api/v1/test_tasks_layering.py tests/unit/middleware/test_authz_dependency.py`（8 passed）
  - `ruff`: 上述变更文件通过

## 12) 第九批已落地（最小粒度增量）

从 `system` 模块切入，继续单端点语义对齐：

- 变更文件：
  - `backend/src/api/v1/system/system.py`
  - `backend/tests/unit/api/v1/test_system_layering.py`
- 变更内容：
  - `GET /system/info`：`resource_type="asset"` → `"system_settings"`
  - 同步更新分层断言，仅变更 `app_info` 一项，`api_root` 暂保持 `asset`
- 验证：
  - `pytest`: `tests/unit/api/v1/test_system_layering.py tests/unit/middleware/test_authz_dependency.py`（5 passed）
  - `ruff`: 上述变更文件通过

## 13) 第十批已落地（最小粒度增量）

继续在 `system` 模块做单端点语义对齐：

- 变更文件：
  - `backend/src/api/v1/system/system.py`
  - `backend/tests/unit/api/v1/test_system_layering.py`
- 变更内容：
  - `GET /system/root`：`resource_type="asset"` → `"system_settings"`
  - 同步更新分层断言，仅变更 `api_root` 一项；`system.py` 的 `asset` 漂移已清零
- 验证：
  - `pytest`: `tests/unit/api/v1/test_system_layering.py tests/unit/middleware/test_authz_dependency.py`（5 passed）
  - `ruff`: 上述变更文件通过

## 14) 第十一批已落地（最小粒度增量）

继续沿任务域做单端点语义对齐：

- 变更文件：
  - `backend/src/api/v1/system/tasks.py`
  - `backend/tests/unit/api/v1/test_tasks_layering.py`
- 变更内容：
  - `PUT /tasks/{task_id}`：`resource_type="asset"` → `"task"`
  - 同步更新分层断言，仅变更 `update_task` 一项，写操作端点仍按最小粒度推进
- 验证：
  - `pytest`: `tests/unit/api/v1/test_tasks_layering.py tests/unit/middleware/test_authz_dependency.py`（8 passed）
  - `ruff`: 上述变更文件通过

## 15) 第十二批已落地（最小粒度增量）

继续沿任务域做单端点语义对齐：

- 变更文件：
  - `backend/src/api/v1/system/tasks.py`
  - `backend/tests/unit/api/v1/test_tasks_layering.py`
- 变更内容：
  - `POST /tasks/{task_id}/cancel`：`resource_type="asset"` → `"task"`
  - 同步更新分层断言，仅变更 `cancel_task` 一项，删除端点仍暂保持 `asset`
- 验证：
  - `pytest`: `tests/unit/api/v1/test_tasks_layering.py tests/unit/middleware/test_authz_dependency.py`（8 passed）
  - `ruff`: 上述变更文件通过

## 16) 第十三批已落地（最小粒度增量）

继续沿任务域做单端点语义对齐：

- 变更文件：
  - `backend/src/api/v1/system/tasks.py`
  - `backend/tests/unit/api/v1/test_tasks_layering.py`
- 变更内容：
  - `DELETE /tasks/{task_id}`：`resource_type="asset"` → `"task"`
  - 同步更新分层断言，仅变更 `delete_task` 一项，任务主写操作端点已切换为 `task`
- 验证：
  - `pytest`: `tests/unit/api/v1/test_tasks_layering.py tests/unit/middleware/test_authz_dependency.py`（8 passed）
  - `ruff`: 上述变更文件通过

## 17) 第十四批已落地（最小粒度增量）

继续沿任务域做单端点语义对齐：

- 变更文件：
  - `backend/src/api/v1/system/tasks.py`
  - `backend/tests/unit/api/v1/test_tasks_layering.py`
- 变更内容：
  - `GET /tasks`：`resource_type="asset"` → `"task"`
  - 同步更新分层断言，仅变更 `get_tasks` 一项，`create_task` 仍暂保持 `asset`
- 验证：
  - `pytest`: `tests/unit/api/v1/test_tasks_layering.py tests/unit/middleware/test_authz_dependency.py`（8 passed）
  - `ruff`: 上述变更文件通过

## 18) 第十五批已落地（最小粒度增量）

继续沿任务域做单端点语义对齐：

- 变更文件：
  - `backend/src/api/v1/system/tasks.py`
  - `backend/tests/unit/api/v1/test_tasks_layering.py`
- 变更内容：
  - `POST /tasks/`：`resource_type="asset"` → `"task"`
  - 同步更新分层断言，仅变更 `create_task` 一项，任务主端点已全部切换为 `task`
- 验证：
  - `pytest`: `tests/unit/api/v1/test_tasks_layering.py tests/unit/middleware/test_authz_dependency.py`（8 passed）
  - `ruff`: 上述变更文件通过

## 19) 第十六批已落地（最小粒度增量）

从 `system` 模块转入 `enum_field` 子域，按单端点语义对齐推进：

- 变更文件：
  - `backend/src/api/v1/system/enum_field.py`
  - `backend/tests/unit/api/v1/test_enum_field_layering.py`
- 变更内容：
  - `GET /enum-fields/types`：`resource_type="asset"` → `"enum_field"`
  - 同步更新分层断言，仅变更 `get_enum_field_types` 一项，其余 `enum_field` 端点暂保持 `asset`
- 验证：
  - `pytest`: `tests/unit/api/v1/test_enum_field_layering.py tests/unit/middleware/test_authz_dependency.py`（7 passed）
  - `ruff`: 上述变更文件通过

## 20) 第十七批已落地（最小粒度增量）

继续在 `enum_field` 子域按单端点语义对齐推进：

- 变更文件：
  - `backend/src/api/v1/system/enum_field.py`
  - `backend/tests/unit/api/v1/test_enum_field_layering.py`
- 变更内容：
  - `GET /enum-fields/types/statistics`：`resource_type="asset"` → `"enum_field"`
  - 同步更新分层断言，仅变更 `get_enum_field_statistics` 一项，其余 `enum_field` 端点暂保持 `asset`
- 验证：
  - `pytest`: `tests/unit/api/v1/test_enum_field_layering.py tests/unit/middleware/test_authz_dependency.py`（7 passed）
  - `ruff`: 上述变更文件通过

## 21) 第十八批已落地（最小粒度增量）

继续在 `enum_field` 子域按单端点语义对齐推进：

- 变更文件：
  - `backend/src/api/v1/system/enum_field.py`
  - `backend/tests/unit/api/v1/test_enum_field_layering.py`
- 变更内容：
  - `GET /enum-fields/types/{type_id}`：`resource_type="asset"` → `"enum_field"`
  - 保留 `resource_id="{type_id}"` 与 `deny_as_not_found=True` 不变，仅替换资源类型
  - 同步更新分层断言，仅变更 `get_enum_field_type` 一项
- 验证：
  - `pytest`: `tests/unit/api/v1/test_enum_field_layering.py tests/unit/middleware/test_authz_dependency.py`（7 passed）
  - `ruff`: 上述变更文件通过

## 22) 第十九批已落地（最小粒度增量）

继续在 `enum_field` 子域按单端点语义对齐推进：

- 变更文件：
  - `backend/src/api/v1/system/enum_field.py`
  - `backend/tests/unit/api/v1/test_enum_field_layering.py`
- 变更内容：
  - `POST /enum-fields/types`：`resource_type="asset"` → `"enum_field"`
  - 同步更新分层断言，仅变更 `create_enum_field_type` 一项，其余 `enum_field` 端点暂保持现状
- 验证：
  - `pytest`: `tests/unit/api/v1/test_enum_field_layering.py tests/unit/middleware/test_authz_dependency.py`（7 passed）
  - `ruff`: 上述变更文件通过

## 23) 第二十批已落地（最小粒度增量）

继续在 `enum_field` 子域按单端点语义对齐推进：

- 变更文件：
  - `backend/src/api/v1/system/enum_field.py`
  - `backend/tests/unit/api/v1/test_enum_field_layering.py`
- 变更内容：
  - `PUT /enum-fields/types/{type_id}`：`resource_type="asset"` → `"enum_field"`
  - 保持 `resource_id="{type_id}"` 不变
  - 同步更新分层断言，仅变更 `update_enum_field_type` 一项，其余 `enum_field` 端点暂保持现状
- 验证：
  - `pytest`: `tests/unit/api/v1/test_enum_field_layering.py tests/unit/middleware/test_authz_dependency.py`（7 passed）
  - `ruff`: 上述变更文件通过

## 24) 第二十一批已落地（最小粒度增量）

继续在 `enum_field` 子域按单端点语义对齐推进：

- 变更文件：
  - `backend/src/api/v1/system/enum_field.py`
  - `backend/tests/unit/api/v1/test_enum_field_layering.py`
- 变更内容：
  - `DELETE /enum-fields/types/{type_id}`：`resource_type="asset"` → `"enum_field"`
  - 保持 `resource_id="{type_id}"` 不变
  - 同步更新分层断言，仅变更 `delete_enum_field_type` 一项，其余 `enum_field` 端点暂保持现状
- 验证：
  - `pytest`: `tests/unit/api/v1/test_enum_field_layering.py tests/unit/middleware/test_authz_dependency.py`（7 passed）
  - `ruff`: 上述变更文件通过

## 25) 第二十二批已落地（最小粒度增量）

继续在 `enum_field` 子域按单端点语义对齐推进：

- 变更文件：
  - `backend/src/api/v1/system/enum_field.py`
  - `backend/tests/unit/api/v1/test_enum_field_layering.py`
- 变更内容：
  - `GET /enum-fields/types/categories/list[Any]`：`resource_type="asset"` → `"enum_field"`
  - 同步更新分层断言，仅变更 `get_enum_field_categories` 一项，其余 `enum_field` 端点暂保持现状
- 验证：
  - `pytest`: `tests/unit/api/v1/test_enum_field_layering.py tests/unit/middleware/test_authz_dependency.py`（7 passed）
  - `ruff`: 上述变更文件通过

## 26) 第二十三批已落地（最小粒度增量）

继续在 `enum_field` 子域按单端点语义对齐推进：

- 变更文件：
  - `backend/src/api/v1/system/enum_field.py`
  - `backend/tests/unit/api/v1/test_enum_field_layering.py`
- 变更内容：
  - `GET /enum-fields/types/{type_id}/values`：`resource_type="asset"` → `"enum_field"`
  - 保持 `resource_id="{type_id}"` 与 `deny_as_not_found=True` 不变
  - 同步更新分层断言，仅变更 `get_enum_field_values` 一项，其余 `enum_field` 端点暂保持现状
- 验证：
  - `pytest`: `tests/unit/api/v1/test_enum_field_layering.py tests/unit/middleware/test_authz_dependency.py`（7 passed）
  - `ruff`: 上述变更文件通过

## 27) 第二十四批已落地（最小粒度增量）

继续在 `enum_field` 子域按单端点语义对齐推进：

- 变更文件：
  - `backend/src/api/v1/system/enum_field.py`
  - `backend/tests/unit/api/v1/test_enum_field_layering.py`
- 变更内容：
  - `GET /enum-fields/types/{type_id}/values/tree`：`resource_type="asset"` → `"enum_field"`
  - 保持 `resource_id="{type_id}"` 与 `deny_as_not_found=True` 不变
  - 同步更新分层断言，仅变更 `get_enum_field_values_tree` 一项，其余 `enum_field` 端点暂保持现状
- 验证：
  - `pytest`: `tests/unit/api/v1/test_enum_field_layering.py tests/unit/middleware/test_authz_dependency.py`（7 passed）
  - `ruff`: 上述变更文件通过

## 28) 第二十五批已落地（最小粒度增量）

继续在 `enum_field` 子域按单端点语义对齐推进：

- 变更文件：
  - `backend/src/api/v1/system/enum_field.py`
  - `backend/tests/unit/api/v1/test_enum_field_layering.py`
- 变更内容：
  - `GET /enum-fields/values/{value_id}`：`resource_type="asset"` → `"enum_field"`
  - 保持 `resource_id="{value_id}"` 与 `deny_as_not_found=True` 不变
  - 同步更新分层断言，仅变更 `get_enum_field_value` 一项，其余 `enum_field` 端点暂保持现状
- 验证：
  - `pytest`: `tests/unit/api/v1/test_enum_field_layering.py tests/unit/middleware/test_authz_dependency.py`（7 passed）
  - `ruff`: 上述变更文件通过

## 29) 第二十六批已落地（最小粒度增量）

继续在 `enum_field` 子域按单端点语义对齐推进：

- 变更文件：
  - `backend/src/api/v1/system/enum_field.py`
  - `backend/tests/unit/api/v1/test_enum_field_layering.py`
- 变更内容：
  - `POST /enum-fields/types/{type_id}/values`：`resource_type="asset"` → `"enum_field"`
  - 保持 `resource_id="{type_id}"` 不变
  - 同步更新分层断言，仅变更 `create_enum_field_value` 一项，其余 `enum_field` 端点暂保持现状
- 验证：
  - `pytest`: `tests/unit/api/v1/test_enum_field_layering.py tests/unit/middleware/test_authz_dependency.py`（7 passed）
  - `ruff`: 上述变更文件通过

## 30) 第二十七批已落地（最小粒度增量）

继续在 `enum_field` 子域按单端点语义对齐推进：

- 变更文件：
  - `backend/src/api/v1/system/enum_field.py`
  - `backend/tests/unit/api/v1/test_enum_field_layering.py`
- 变更内容：
  - `PUT /enum-fields/values/{value_id}`：`resource_type="asset"` → `"enum_field"`
  - 保持 `resource_id="{value_id}"` 不变
  - 同步更新分层断言，仅变更 `update_enum_field_value` 一项，其余 `enum_field` 端点暂保持现状
- 验证：
  - `pytest`: `tests/unit/api/v1/test_enum_field_layering.py tests/unit/middleware/test_authz_dependency.py`（7 passed）
  - `ruff`: 上述变更文件通过

## 31) 第二十八批已落地（最小粒度增量）

继续在 `enum_field` 子域按单端点语义对齐推进：

- 变更文件：
  - `backend/src/api/v1/system/enum_field.py`
  - `backend/tests/unit/api/v1/test_enum_field_layering.py`
- 变更内容：
  - `DELETE /enum-fields/values/{value_id}`：`resource_type="asset"` → `"enum_field"`
  - 保持 `resource_id="{value_id}"` 不变
  - 同步更新分层断言，仅变更 `delete_enum_field_value` 一项，其余 `enum_field` 端点暂保持现状
- 验证：
  - `pytest`: `tests/unit/api/v1/test_enum_field_layering.py tests/unit/middleware/test_authz_dependency.py`（7 passed）
  - `ruff`: 上述变更文件通过

## 32) 第二十九批已落地（最小粒度增量）

继续在 `enum_field` 子域按单端点语义对齐推进：

- 变更文件：
  - `backend/src/api/v1/system/enum_field.py`
  - `backend/tests/unit/api/v1/test_enum_field_layering.py`
- 变更内容：
  - `POST /enum-fields/types/{type_id}/values/batch`：`resource_type="asset"` → `"enum_field"`
  - 保持 `resource_id="{type_id}"` 不变
  - 同步更新分层断言，仅变更 `batch_create_enum_field_values` 一项，其余 `enum_field` 端点暂保持现状
- 验证：
  - `pytest`: `tests/unit/api/v1/test_enum_field_layering.py tests/unit/middleware/test_authz_dependency.py`（7 passed）
  - `ruff`: 上述变更文件通过

## 33) 第三十批已落地（最小粒度增量）

继续在 `enum_field` 子域按单端点语义对齐推进：

- 变更文件：
  - `backend/src/api/v1/system/enum_field.py`
  - `backend/tests/unit/api/v1/test_enum_field_layering.py`
- 变更内容：
  - `GET /enum-fields/usage`：`resource_type="asset"` → `"enum_field"`
  - 同步更新分层断言，仅变更 `get_enum_field_usage` 一项，其余 `enum_field` 端点暂保持现状
- 验证：
  - `pytest`: `tests/unit/api/v1/test_enum_field_layering.py tests/unit/middleware/test_authz_dependency.py`（7 passed）
  - `ruff`: 上述变更文件通过

## 34) 第三十一批已落地（最小粒度增量）

继续在 `enum_field` 子域按单端点语义对齐推进：

- 变更文件：
  - `backend/src/api/v1/system/enum_field.py`
  - `backend/tests/unit/api/v1/test_enum_field_layering.py`
- 变更内容：
  - `POST /enum-fields/usage`：`resource_type="asset"` → `"enum_field"`
  - 同步更新分层断言，仅变更 `create_enum_field_usage` 一项，其余 `enum_field` 端点暂保持现状
- 验证：
  - `pytest`: `tests/unit/api/v1/test_enum_field_layering.py tests/unit/middleware/test_authz_dependency.py`（7 passed）
  - `ruff`: 上述变更文件通过

## 35) 第三十二批已落地（最小粒度增量）

继续在 `enum_field` 子域按单端点语义对齐推进：

- 变更文件：
  - `backend/src/api/v1/system/enum_field.py`
  - `backend/tests/unit/api/v1/test_enum_field_layering.py`
- 变更内容：
  - `PUT /enum-fields/usage/{usage_id}`：`resource_type="asset"` → `"enum_field"`
  - 保持 `resource_id="{usage_id}"` 不变
  - 同步更新分层断言，仅变更 `update_enum_field_usage` 一项，其余 `enum_field` 端点暂保持现状
- 验证：
  - `pytest`: `tests/unit/api/v1/test_enum_field_layering.py tests/unit/middleware/test_authz_dependency.py`（7 passed）
  - `ruff`: 上述变更文件通过

## 36) 第三十三批已落地（最小粒度增量）

继续在 `enum_field` 子域按单端点语义对齐推进：

- 变更文件：
  - `backend/src/api/v1/system/enum_field.py`
  - `backend/tests/unit/api/v1/test_enum_field_layering.py`
- 变更内容：
  - `DELETE /enum-fields/usage/{usage_id}`：`resource_type="asset"` → `"enum_field"`
  - 保持 `resource_id="{usage_id}"` 不变
  - 同步更新分层断言，仅变更 `delete_enum_field_usage` 一项，其余 `enum_field` 端点暂保持现状
- 验证：
  - `pytest`: `tests/unit/api/v1/test_enum_field_layering.py tests/unit/middleware/test_authz_dependency.py`（7 passed）
  - `ruff`: 上述变更文件通过

## 37) 第三十四批已落地（最小粒度增量）

继续在 `enum_field` 子域按单端点语义对齐推进：

- 变更文件：
  - `backend/src/api/v1/system/enum_field.py`
  - `backend/tests/unit/api/v1/test_enum_field_layering.py`
- 变更内容：
  - `GET /enum-fields/types/{type_id}/history`：`resource_type="asset"` → `"enum_field"`
  - 保持 `resource_id="{type_id}"` 与 `deny_as_not_found=True` 不变
  - 同步更新分层断言，仅变更 `get_enum_field_type_history` 一项，其余 `enum_field` 端点暂保持现状
- 验证：
  - `pytest`: `tests/unit/api/v1/test_enum_field_layering.py tests/unit/middleware/test_authz_dependency.py`（7 passed）
  - `ruff`: 上述变更文件通过

## 38) 第三十五批已落地（最小粒度增量）

继续在 `enum_field` 子域按单端点语义对齐推进：

- 变更文件：
  - `backend/src/api/v1/system/enum_field.py`
  - `backend/tests/unit/api/v1/test_enum_field_layering.py`
- 变更内容：
  - `GET /enum-fields/values/{value_id}/history`：`resource_type="asset"` → `"enum_field"`
  - 保持 `resource_id="{value_id}"` 与 `deny_as_not_found=True` 不变
  - 同步更新分层断言，仅变更 `get_enum_field_value_history` 一项，其余 `enum_field` 端点暂保持现状
- 验证：
  - `pytest`: `tests/unit/api/v1/test_enum_field_layering.py tests/unit/middleware/test_authz_dependency.py`（7 passed）
  - `ruff`: 上述变更文件通过

## 39) 第三十六批已落地（最小粒度增量）

从 `enum_field` 子域收口后，切换到 `system/operation_logs` 子模块按单端点语义对齐推进：

- 变更文件：
  - `backend/src/api/v1/system/operation_logs.py`
  - `backend/tests/unit/api/v1/test_operation_logs_layering.py`
- 变更内容：
  - `GET /operation-logs`：`resource_type="asset"` → `"operation_log"`
  - 同步更新分层断言，仅变更 `get_operation_logs` 一项，其余 `operation_logs` 端点暂保持现状
- 验证：
  - `pytest`: `tests/unit/api/v1/test_operation_logs_layering.py tests/unit/middleware/test_authz_dependency.py`（7 passed）
  - `ruff`: 上述变更文件通过

## 40) 第三十七批已落地（最小粒度增量）

继续在 `system/operation_logs` 子模块按单端点语义对齐推进：

- 变更文件：
  - `backend/src/api/v1/system/operation_logs.py`
  - `backend/tests/unit/api/v1/test_operation_logs_layering.py`
- 变更内容：
  - `GET /operation-logs/{log_id}`：`resource_type="asset"` → `"operation_log"`
  - 保持 `resource_id="{log_id}"` 与 `deny_as_not_found=True` 不变
  - 同步更新分层断言，仅变更 `get_operation_log` 一项，其余 `operation_logs` 端点暂保持现状
- 验证：
  - `pytest`: `tests/unit/api/v1/test_operation_logs_layering.py tests/unit/middleware/test_authz_dependency.py`（7 passed）
  - `ruff`: 上述变更文件通过

## 41) 第三十八批已落地（最小粒度增量）

继续在 `system/operation_logs` 子模块按单端点语义对齐推进：

- 变更文件：
  - `backend/src/api/v1/system/operation_logs.py`
  - `backend/tests/unit/api/v1/test_operation_logs_layering.py`
- 变更内容：
  - `GET /operation-logs/statistics/user`：`resource_type="asset"` → `"operation_log"`
  - 同步更新分层断言，仅变更 `get_user_operation_statistics` 一项，其余 `operation_logs` 端点暂保持现状
- 验证：
  - `pytest`: `tests/unit/api/v1/test_operation_logs_layering.py tests/unit/middleware/test_authz_dependency.py`（7 passed）
  - `ruff`: 上述变更文件通过

## 42) 第三十九批已落地（最小粒度增量）

继续在 `system/operation_logs` 子模块按单端点语义对齐推进：

- 变更文件：
  - `backend/src/api/v1/system/operation_logs.py`
  - `backend/tests/unit/api/v1/test_operation_logs_layering.py`
- 变更内容：
  - `GET /operation-logs/statistics/module`：`resource_type="asset"` → `"operation_log"`
  - 同步更新分层断言，仅变更 `get_module_operation_statistics` 一项，其余 `operation_logs` 端点暂保持现状
- 验证：
  - `pytest`: `tests/unit/api/v1/test_operation_logs_layering.py tests/unit/middleware/test_authz_dependency.py`（7 passed）
  - `ruff`: 上述变更文件通过

## 43) 第四十批已落地（最小粒度增量）

继续在 `system/operation_logs` 子模块按单端点语义对齐推进：

- 变更文件：
  - `backend/src/api/v1/system/operation_logs.py`
  - `backend/tests/unit/api/v1/test_operation_logs_layering.py`
- 变更内容：
  - `GET /operation-logs/statistics/daily`：`resource_type="asset"` → `"operation_log"`
  - 同步更新分层断言，仅变更 `get_daily_operation_statistics` 一项，其余 `operation_logs` 端点暂保持现状
- 验证：
  - `pytest`: `tests/unit/api/v1/test_operation_logs_layering.py tests/unit/middleware/test_authz_dependency.py`（7 passed）
  - `ruff`: 上述变更文件通过

## 44) 第四十一批已落地（最小粒度增量）

继续在 `system/operation_logs` 子模块按单端点语义对齐推进：

- 变更文件：
  - `backend/src/api/v1/system/operation_logs.py`
  - `backend/tests/unit/api/v1/test_operation_logs_layering.py`
- 变更内容：
  - `GET /operation-logs/statistics/errors`：`resource_type="asset"` → `"operation_log"`
  - 同步更新分层断言，仅变更 `get_error_operation_statistics` 一项，其余 `operation_logs` 端点暂保持现状
- 验证：
  - `pytest`: `tests/unit/api/v1/test_operation_logs_layering.py tests/unit/middleware/test_authz_dependency.py`（7 passed）
  - `ruff`: 上述变更文件通过

## 45) 第四十二批已落地（最小粒度增量）

继续在 `system/operation_logs` 子模块按单端点语义对齐推进：

- 变更文件：
  - `backend/src/api/v1/system/operation_logs.py`
  - `backend/tests/unit/api/v1/test_operation_logs_layering.py`
- 变更内容：
  - `GET /operation-logs/statistics/summary`：`resource_type="asset"` → `"operation_log"`
  - 同步更新分层断言，仅变更 `get_operation_log_summary` 一项，其余 `operation_logs` 端点暂保持现状
- 验证：
  - `pytest`: `tests/unit/api/v1/test_operation_logs_layering.py tests/unit/middleware/test_authz_dependency.py`（7 passed）
  - `ruff`: 上述变更文件通过

## 46) 第四十三批已落地（最小粒度增量）

继续在 `system/operation_logs` 子模块按单端点语义对齐推进：

- 变更文件：
  - `backend/src/api/v1/system/operation_logs.py`
  - `backend/tests/unit/api/v1/test_operation_logs_layering.py`
- 变更内容：
  - `POST /operation-logs/export`：`resource_type="asset"` → `"operation_log"`
  - 同步更新分层断言，仅变更 `export_operation_logs` 一项，其余 `operation_logs` 端点暂保持现状
- 验证：
  - `pytest`: `tests/unit/api/v1/test_operation_logs_layering.py tests/unit/middleware/test_authz_dependency.py`（7 passed）
  - `ruff`: 上述变更文件通过

## 47) 第四十四批已落地（最小粒度增量）

继续在 `system/operation_logs` 子模块按单端点语义对齐推进：

- 变更文件：
  - `backend/src/api/v1/system/operation_logs.py`
  - `backend/tests/unit/api/v1/test_operation_logs_layering.py`
- 变更内容：
  - `POST /operation-logs/cleanup`：`resource_type="asset"` → `"operation_log"`
  - 同步更新分层断言，仅变更 `cleanup_old_logs` 一项，其余 `operation_logs` 端点暂保持现状
- 验证：
  - `pytest`: `tests/unit/api/v1/test_operation_logs_layering.py tests/unit/middleware/test_authz_dependency.py`（7 passed）
  - `ruff`: 上述变更文件通过

## 48) 第四十五批已落地（最小粒度增量）

从 `operation_logs` 子模块收口后，切换至 `system/backup` 子模块按单端点语义对齐推进：

- 变更文件：
  - `backend/src/api/v1/system/backup.py`
  - `backend/tests/unit/api/v1/test_backup_layering.py`
- 变更内容：
  - `POST /backup/create`：`resource_type="asset"` → `"backup"`
  - 同步更新分层断言，仅变更 `create_backup` 一项，其余 `backup` 端点暂保持现状
- 验证：
  - `pytest`: `tests/unit/api/v1/test_backup_layering.py tests/unit/middleware/test_authz_dependency.py`（6 passed）
  - `ruff`: 上述变更文件通过

## 49) 第四十六批已落地（最小粒度增量）

继续在 `system/backup` 子模块按单端点语义对齐推进：

- 变更文件：
  - `backend/src/api/v1/system/backup.py`
  - `backend/tests/unit/api/v1/test_backup_layering.py`
- 变更内容：
  - `GET /backup/list[Any]`：`resource_type="asset"` → `"backup"`
  - 同步更新分层断言，仅变更 `list_backups` 一项，其余 `backup` 端点暂保持现状
- 验证：
  - `pytest`: `tests/unit/api/v1/test_backup_layering.py tests/unit/middleware/test_authz_dependency.py`（6 passed）
  - `ruff`: 上述变更文件通过

## 50) 第四十七批已落地（最小粒度增量）

继续在 `system/backup` 子模块按单端点语义对齐推进：

- 变更文件：
  - `backend/src/api/v1/system/backup.py`
  - `backend/tests/unit/api/v1/test_backup_layering.py`
- 变更内容：
  - `GET /backup/download/{backup_name}`：`resource_type="asset"` → `"backup"`
  - 保持 `resource_id="{backup_name}"` 与 `deny_as_not_found=True` 不变
  - 同步更新分层断言，仅变更 `download_backup` 一项，其余 `backup` 端点暂保持现状
- 验证：
  - `pytest`: `tests/unit/api/v1/test_backup_layering.py tests/unit/middleware/test_authz_dependency.py`（6 passed）
  - `ruff`: 上述变更文件通过

## 51) 第四十八批已落地（最小粒度增量）

继续在 `system/backup` 子模块按单端点语义对齐推进：

- 变更文件：
  - `backend/src/api/v1/system/backup.py`
  - `backend/tests/unit/api/v1/test_backup_layering.py`
- 变更内容：
  - `POST /backup/restore/{backup_name}`：`resource_type="asset"` → `"backup"`
  - 保持 `resource_id="{backup_name}"` 不变
  - 同步更新分层断言，仅变更 `restore_backup` 一项，其余 `backup` 端点暂保持现状
- 验证：
  - `pytest`: `tests/unit/api/v1/test_backup_layering.py tests/unit/middleware/test_authz_dependency.py`（6 passed）
  - `ruff`: 上述变更文件通过

## 52) 第四十九批已落地（最小粒度增量）

继续在 `system/backup` 子模块按单端点语义对齐推进：

- 变更文件：
  - `backend/src/api/v1/system/backup.py`
  - `backend/tests/unit/api/v1/test_backup_layering.py`
- 变更内容：
  - `DELETE /backup/delete/{backup_name}`：`resource_type="asset"` → `"backup"`
  - 保持 `resource_id="{backup_name}"` 不变
  - 同步更新分层断言，仅变更 `delete_backup` 一项，其余 `backup` 端点暂保持现状
- 验证：
  - `pytest`: `tests/unit/api/v1/test_backup_layering.py tests/unit/middleware/test_authz_dependency.py`（6 passed）
  - `ruff`: 上述变更文件通过

## 53) 第五十批已落地（最小粒度增量）

继续在 `system/backup` 子模块按单端点语义对齐推进：

- 变更文件：
  - `backend/src/api/v1/system/backup.py`
  - `backend/tests/unit/api/v1/test_backup_layering.py`
- 变更内容：
  - `GET /backup/stats`：`resource_type="asset"` → `"backup"`
  - 同步更新分层断言，仅变更 `get_backup_stats` 一项，其余 `backup` 端点暂保持现状
- 验证：
  - `pytest`: `tests/unit/api/v1/test_backup_layering.py tests/unit/middleware/test_authz_dependency.py`（6 passed）
  - `ruff`: 上述变更文件通过

## 54) 第五十一批已落地（最小粒度增量）

继续在 `system/backup` 子模块按单端点语义对齐推进：

- 变更文件：
  - `backend/src/api/v1/system/backup.py`
  - `backend/tests/unit/api/v1/test_backup_layering.py`
- 变更内容：
  - `POST /backup/validate/{backup_name}`：`resource_type="asset"` → `"backup"`
  - 保持 `resource_id="{backup_name}"` 不变
  - 同步更新分层断言，仅变更 `validate_backup` 一项，其余 `backup` 端点暂保持现状
- 验证：
  - `pytest`: `tests/unit/api/v1/test_backup_layering.py tests/unit/middleware/test_authz_dependency.py`（6 passed）
  - `ruff`: 上述变更文件通过

## 55) 第五十二批已落地（最小粒度增量）

继续在 `system/backup` 子模块按单端点语义对齐推进：

- 变更文件：
  - `backend/src/api/v1/system/backup.py`
  - `backend/tests/unit/api/v1/test_backup_layering.py`
- 变更内容：
  - `POST /backup/cleanup`：`resource_type="asset"` → `"backup"`
  - 同步更新分层断言，仅变更 `cleanup_old_backups` 一项
- 验证：
  - `pytest`: `tests/unit/api/v1/test_backup_layering.py tests/unit/middleware/test_authz_dependency.py`（6 passed）
  - `ruff`: 上述变更文件通过

## 56) 第五十三批已落地（最小粒度增量）

切换到 `system/history` 子模块并按单端点语义对齐推进：

- 变更文件：
  - `backend/src/api/v1/system/history.py`
  - `backend/tests/unit/api/v1/test_history_layering.py`
- 变更内容：
  - `GET /history/`：`resource_type="asset"` → `"history"`
  - 同步更新分层断言，仅变更 `get_history_list` 一项，其余 `history` 端点暂保持现状
- 验证：
  - `pytest`: `tests/unit/api/v1/test_history_layering.py tests/unit/middleware/test_authz_dependency.py`（7 passed）
  - `ruff`: 上述变更文件通过

## 57) 第五十四批已落地（最小粒度增量）

继续在 `system/history` 子模块按单端点语义对齐推进：

- 变更文件：
  - `backend/src/api/v1/system/history.py`
  - `backend/tests/unit/api/v1/test_history_layering.py`
- 变更内容：
  - `GET /history/{history_id}`：`resource_type="asset"` → `"history"`
  - 同步更新分层断言，仅变更 `get_history_detail` 一项，其余 `history` 端点暂保持现状
- 验证：
  - `pytest`: `tests/unit/api/v1/test_history_layering.py tests/unit/middleware/test_authz_dependency.py`（7 passed）
  - `ruff`: 上述变更文件通过

## 58) 第五十五批已落地（最小粒度增量）

继续在 `system/history` 子模块按单端点语义对齐推进：

- 变更文件：
  - `backend/src/api/v1/system/history.py`
  - `backend/tests/unit/api/v1/test_history_layering.py`
- 变更内容：
  - `DELETE /history/{history_id}`：`resource_type="asset"` → `"history"`
  - 同步更新分层断言，仅变更 `delete_history` 一项
- 验证：
  - `pytest`: `tests/unit/api/v1/test_history_layering.py tests/unit/middleware/test_authz_dependency.py`（7 passed）
  - `ruff`: 上述变更文件通过

## 59) 第五十六批已落地（最小粒度增量）

切换到 `system/contact` 子模块并按单端点语义对齐推进：

- 变更文件：
  - `backend/src/api/v1/system/contact.py`
  - `backend/tests/unit/api/v1/test_contact_layering.py`
- 变更内容：
  - `POST /contact/`：`resource_type="asset"` → `"contact"`
  - 同步更新分层断言，仅变更 `create_contact` 一项，其余 `contact` 端点暂保持现状
- 验证：
  - `pytest`: `tests/unit/api/v1/test_contact_layering.py tests/unit/middleware/test_authz_dependency.py`（7 passed）
  - `ruff`: 上述变更文件通过

## 60) 第五十七批已落地（最小粒度增量）

继续在 `system/contact` 子模块按单端点语义对齐推进：

- 变更文件：
  - `backend/src/api/v1/system/contact.py`
  - `backend/tests/unit/api/v1/test_contact_layering.py`
- 变更内容：
  - `GET /contact/{contact_id}`：`resource_type="asset"` → `"contact"`
  - 保持 `resource_id="{contact_id}"` 与 `deny_as_not_found=True` 不变
  - 同步更新分层断言，仅变更 `get_contact` 一项，其余 `contact` 端点暂保持现状
- 验证：
  - `pytest`: `tests/unit/api/v1/test_contact_layering.py tests/unit/middleware/test_authz_dependency.py`（7 passed）
  - `ruff`: 上述变更文件通过

## 61) 第五十八批已落地（最小粒度增量）

继续在 `system/contact` 子模块按单端点语义对齐推进：

- 变更文件：
  - `backend/src/api/v1/system/contact.py`
  - `backend/tests/unit/api/v1/test_contact_layering.py`
- 变更内容：
  - `GET /contact/entity/{entity_type}/{entity_id}`：`resource_type="asset"` → `"contact"`
  - 保持 `resource_id="{entity_id}"` 与 `deny_as_not_found=True` 不变
  - 同步更新分层断言，仅变更 `get_entity_contacts` 一项，其余 `contact` 端点暂保持现状
- 验证：
  - `pytest`: `tests/unit/api/v1/test_contact_layering.py tests/unit/middleware/test_authz_dependency.py`（7 passed）
  - `ruff`: 上述变更文件通过

## 62) 第五十九批已落地（最小粒度增量）

继续在 `system/contact` 子模块按单端点语义对齐推进：

- 变更文件：
  - `backend/src/api/v1/system/contact.py`
  - `backend/tests/unit/api/v1/test_contact_layering.py`
- 变更内容：
  - `GET /contact/entity/{entity_type}/{entity_id}/primary`：`resource_type="asset"` → `"contact"`
  - 保持 `resource_id="{entity_id}"` 与 `deny_as_not_found=True` 不变
  - 同步更新分层断言，仅变更 `get_primary_contact` 一项，其余 `contact` 端点暂保持现状
- 验证：
  - `pytest`: `tests/unit/api/v1/test_contact_layering.py tests/unit/middleware/test_authz_dependency.py`（7 passed）
  - `ruff`: 上述变更文件通过

## 63) 第六十批已落地（最小粒度增量）

继续在 `system/contact` 子模块按单端点语义对齐推进：

- 变更文件：
  - `backend/src/api/v1/system/contact.py`
  - `backend/tests/unit/api/v1/test_contact_layering.py`
- 变更内容：
  - `PUT /contact/{contact_id}`：`resource_type="asset"` → `"contact"`
  - 保持 `resource_id="{contact_id}"` 不变
  - 同步更新分层断言，仅变更 `update_contact` 一项，其余 `contact` 端点暂保持现状
- 验证：
  - `pytest`: `tests/unit/api/v1/test_contact_layering.py tests/unit/middleware/test_authz_dependency.py`（7 passed）
  - `ruff`: 上述变更文件通过

## 64) 第六十一批已落地（最小粒度增量）

继续在 `system/contact` 子模块按单端点语义对齐推进：

- 变更文件：
  - `backend/src/api/v1/system/contact.py`
  - `backend/tests/unit/api/v1/test_contact_layering.py`
- 变更内容：
  - `DELETE /contact/{contact_id}`：`resource_type="asset"` → `"contact"`
  - 保持 `resource_id="{contact_id}"` 不变
  - 同步更新分层断言，仅变更 `delete_contact` 一项，其余 `contact` 端点暂保持现状
- 验证：
  - `pytest`: `tests/unit/api/v1/test_contact_layering.py tests/unit/middleware/test_authz_dependency.py`（7 passed）
  - `ruff`: 上述变更文件通过

## 65) 第六十二批已落地（最小粒度增量）

继续在 `system/contact` 子模块按单端点语义对齐推进：

- 变更文件：
  - `backend/src/api/v1/system/contact.py`
  - `backend/tests/unit/api/v1/test_contact_layering.py`
- 变更内容：
  - `POST /contact/batch/{entity_type}/{entity_id}`：`resource_type="asset"` → `"contact"`
  - 保持 `resource_id="{entity_id}"` 不变
  - 同步更新分层断言，仅变更 `create_contacts_batch` 一项
- 验证：
  - `pytest`: `tests/unit/api/v1/test_contact_layering.py tests/unit/middleware/test_authz_dependency.py`（7 passed）
  - `ruff`: 上述变更文件通过

## 66) 第六十三批已落地（最小粒度增量）

切换到 `system/dictionaries` 子模块并按单端点语义对齐推进：

- 变更文件：
  - `backend/src/api/v1/system/dictionaries.py`
  - `backend/tests/unit/api/v1/test_dictionaries_layering.py`
- 变更内容：
  - `GET /system/dictionaries/{dict_type}/options`：`resource_type="asset"` → `"dictionary"`
  - 保持 `resource_id="{dict_type}"` 与 `deny_as_not_found=True` 不变
  - 同步更新分层断言，仅变更 `get_dictionary_options` 一项，其余 `dictionaries` 端点暂保持现状
- 验证：
  - `pytest`: `tests/unit/api/v1/test_dictionaries_layering.py tests/unit/middleware/test_authz_dependency.py`（5 passed）
  - `ruff`: 上述变更文件通过

## 67) 第六十四批已落地（最小粒度增量）

继续在 `system/dictionaries` 子模块按单端点语义对齐推进：

- 变更文件：
  - `backend/src/api/v1/system/dictionaries.py`
  - `backend/tests/unit/api/v1/test_dictionaries_layering.py`
- 变更内容：
  - `POST /system/dictionaries/{dict_type}/quick-create`：`resource_type="asset"` → `"dictionary"`
  - 保持 `resource_id="{dict_type}"` 不变
  - 同步更新分层断言，仅变更 `quick_create_dictionary` 一项，其余 `dictionaries` 端点暂保持现状
- 验证：
  - `pytest`: `tests/unit/api/v1/test_dictionaries_layering.py tests/unit/middleware/test_authz_dependency.py`（5 passed）
  - `ruff`: 上述变更文件通过

## 68) 第六十五批已落地（最小粒度增量）

继续在 `system/dictionaries` 子模块按单端点语义对齐推进：

- 变更文件：
  - `backend/src/api/v1/system/dictionaries.py`
  - `backend/tests/unit/api/v1/test_dictionaries_layering.py`
- 变更内容：
  - `GET /system/dictionaries/types`：`resource_type="asset"` → `"dictionary"`
  - 同步更新分层断言，仅变更 `get_dictionary_types` 一项，其余 `dictionaries` 端点暂保持现状
- 验证：
  - `pytest`: `tests/unit/api/v1/test_dictionaries_layering.py tests/unit/middleware/test_authz_dependency.py`（5 passed）
  - `ruff`: 上述变更文件通过

## 69) 第六十六批已落地（最小粒度增量）

继续在 `system/dictionaries` 子模块按单端点语义对齐推进：

- 变更文件：
  - `backend/src/api/v1/system/dictionaries.py`
  - `backend/tests/unit/api/v1/test_dictionaries_layering.py`
- 变更内容：
  - `GET /system/dictionaries/validation/stats`：`resource_type="asset"` → `"dictionary"`
  - 同步更新分层断言，仅变更 `get_validation_statistics` 一项，其余 `dictionaries` 端点暂保持现状
- 验证：
  - `pytest`: `tests/unit/api/v1/test_dictionaries_layering.py tests/unit/middleware/test_authz_dependency.py`（5 passed）
  - `ruff`: 上述变更文件通过

## 70) 第六十七批已落地（最小粒度增量）

继续在 `system/dictionaries` 子模块按单端点语义对齐推进：

- 变更文件：
  - `backend/src/api/v1/system/dictionaries.py`
  - `backend/tests/unit/api/v1/test_dictionaries_layering.py`
- 变更内容：
  - `POST /system/dictionaries/{dict_type}/values`：`resource_type="asset"` → `"dictionary"`
  - 保持 `resource_id="{dict_type}"` 不变
  - 同步更新分层断言，仅变更 `add_dictionary_value` 一项，其余 `dictionaries` 端点暂保持现状
- 验证：
  - `pytest`: `tests/unit/api/v1/test_dictionaries_layering.py tests/unit/middleware/test_authz_dependency.py`（5 passed）
  - `ruff`: 上述变更文件通过

## 71) 第六十八批已落地（最小粒度增量）

继续在 `system/dictionaries` 子模块按单端点语义对齐推进：

- 变更文件：
  - `backend/src/api/v1/system/dictionaries.py`
  - `backend/tests/unit/api/v1/test_dictionaries_layering.py`
- 变更内容：
  - `DELETE /system/dictionaries/{dict_type}`：`resource_type="asset"` → `"dictionary"`
  - 保持 `resource_id="{dict_type}"` 不变
  - 同步更新分层断言，仅变更 `delete_dictionary_type` 一项
- 验证：
  - `pytest`: `tests/unit/api/v1/test_dictionaries_layering.py tests/unit/middleware/test_authz_dependency.py`（5 passed）
  - `ruff`: 上述变更文件通过

## 72) 第六十九批已落地（最小粒度增量）

切换到 `system/notifications` 子模块并按单端点语义对齐推进：

- 变更文件：
  - `backend/src/api/v1/system/notifications.py`
  - `backend/tests/unit/api/v1/test_notifications_layering.py`
- 变更内容：
  - `GET /notifications`：`resource_type="asset"` → `"notification"`
  - 同步更新分层断言，仅变更 `get_notifications` 一项，其余 `notifications` 端点暂保持现状
- 验证：
  - `pytest`: `tests/unit/api/v1/test_notifications_layering.py tests/unit/middleware/test_authz_dependency.py`（5 passed）
  - `ruff`: 上述变更文件通过

## 73) 第七十批已落地（最小粒度增量）

继续在 `system/notifications` 子模块按单端点语义对齐推进：

- 变更文件：
  - `backend/src/api/v1/system/notifications.py`
  - `backend/tests/unit/api/v1/test_notifications_layering.py`
- 变更内容：
  - `GET /notifications/unread-count`：`resource_type="asset"` → `"notification"`
  - 同步更新分层断言，仅变更 `get_unread_count` 一项，其余 `notifications` 端点暂保持现状
- 验证：
  - `pytest`: `tests/unit/api/v1/test_notifications_layering.py tests/unit/middleware/test_authz_dependency.py`（5 passed）
  - `ruff`: 上述变更文件通过

## 74) 第七十一批已落地（最小粒度增量）

继续在 `system/notifications` 子模块按单端点语义对齐推进：

- 变更文件：
  - `backend/src/api/v1/system/notifications.py`
  - `backend/tests/unit/api/v1/test_notifications_layering.py`
- 变更内容：
  - `POST /notifications/{notification_id}/read`：`resource_type="asset"` → `"notification"`
  - 保持 `resource_id="{notification_id}"` 不变
  - 同步更新分层断言，仅变更 `mark_notification_as_read` 一项，其余 `notifications` 端点暂保持现状
- 验证：
  - `pytest`: `tests/unit/api/v1/test_notifications_layering.py tests/unit/middleware/test_authz_dependency.py`（5 passed）
  - `ruff`: 上述变更文件通过

## 75) 第七十二批已落地（最小粒度增量）

继续在 `system/notifications` 子模块按单端点语义对齐推进：

- 变更文件：
  - `backend/src/api/v1/system/notifications.py`
  - `backend/tests/unit/api/v1/test_notifications_layering.py`
- 变更内容：
  - `POST /notifications/read-all`：`resource_type="asset"` → `"notification"`
  - 同步更新分层断言，仅变更 `mark_all_as_read` 一项，其余 `notifications` 端点暂保持现状
- 验证：
  - `pytest`: `tests/unit/api/v1/test_notifications_layering.py tests/unit/middleware/test_authz_dependency.py`（5 passed）
  - `ruff`: 上述变更文件通过

## 76) 第七十三批已落地（最小粒度增量）

继续在 `system/notifications` 子模块按单端点语义对齐推进：

- 变更文件：
  - `backend/src/api/v1/system/notifications.py`
  - `backend/tests/unit/api/v1/test_notifications_layering.py`
- 变更内容：
  - `DELETE /notifications/{notification_id}`：`resource_type="asset"` → `"notification"`
  - 保持 `resource_id="{notification_id}"` 不变
  - 同步更新分层断言，仅变更 `delete_notification` 一项，其余 `notifications` 端点暂保持现状
- 验证：
  - `pytest`: `tests/unit/api/v1/test_notifications_layering.py tests/unit/middleware/test_authz_dependency.py`（5 passed）
  - `ruff`: 上述变更文件通过

## 77) 第七十四批已落地（最小粒度增量）

继续在 `system/notifications` 子模块按单端点语义对齐推进：

- 变更文件：
  - `backend/src/api/v1/system/notifications.py`
  - `backend/tests/unit/api/v1/test_notifications_layering.py`
- 变更内容：
  - `POST /notifications/run-tasks`：`resource_type="asset"` → `"notification"`
  - 同步更新分层断言，仅变更 `run_notification_tasks_endpoint` 一项
- 验证：
  - `pytest`: `tests/unit/api/v1/test_notifications_layering.py tests/unit/middleware/test_authz_dependency.py`（5 passed）
  - `ruff`: 上述变更文件通过

## 78) 第七十五批已落地（最小粒度增量）

切换到 `system/collection` 子模块并按单端点语义对齐推进：

- 变更文件：
  - `backend/src/api/v1/system/collection.py`
  - `backend/tests/unit/api/v1/test_collection_layering.py`
- 变更内容：
  - `GET /collection/summary`：`resource_type="asset"` → `"collection"`
  - 同步更新分层断言，仅变更 `get_collection_summary` 一项，其余 `collection` 端点暂保持现状
- 验证：
  - `pytest`: `tests/unit/api/v1/test_collection_layering.py tests/unit/middleware/test_authz_dependency.py`（6 passed）
  - `ruff`: 上述变更文件通过

## 79) 第七十六批已落地（最小粒度增量）

继续在 `system/collection` 子模块按单端点语义对齐推进：

- 变更文件：
  - `backend/src/api/v1/system/collection.py`
  - `backend/tests/unit/api/v1/test_collection_layering.py`
- 变更内容：
  - `GET /collection/records`：`resource_type="asset"` → `"collection"`
  - 同步更新分层断言，仅变更 `list_collection_records` 一项，其余 `collection` 端点暂保持现状
- 验证：
  - `pytest`: `tests/unit/api/v1/test_collection_layering.py tests/unit/middleware/test_authz_dependency.py`（6 passed）
  - `ruff`: 上述变更文件通过

## 80) 第七十七批已落地（最小粒度增量）

继续在 `system/collection` 子模块按单端点语义对齐推进：

- 变更文件：
  - `backend/src/api/v1/system/collection.py`
  - `backend/tests/unit/api/v1/test_collection_layering.py`
- 变更内容：
  - `GET /collection/records/{record_id}`：`resource_type="asset"` → `"collection"`
  - 保持 `resource_id="{record_id}"` 与 `deny_as_not_found=True` 不变
  - 同步更新分层断言，仅变更 `get_collection_record` 一项，其余 `collection` 端点暂保持现状
- 验证：
  - `pytest`: `tests/unit/api/v1/test_collection_layering.py tests/unit/middleware/test_authz_dependency.py`（6 passed）
  - `ruff`: 上述变更文件通过

## 81) 第七十八批已落地（最小粒度增量）

继续在 `system/collection` 子模块按单端点语义对齐推进：

- 变更文件：
  - `backend/src/api/v1/system/collection.py`
  - `backend/tests/unit/api/v1/test_collection_layering.py`
- 变更内容：
  - `POST /collection/records`：`resource_type="asset"` → `"collection"`
  - 同步更新分层断言，仅变更 `create_collection_record` 一项，其余 `collection` 端点暂保持现状
- 验证：
  - `pytest`: `tests/unit/api/v1/test_collection_layering.py tests/unit/middleware/test_authz_dependency.py`（6 passed）
  - `ruff`: 上述变更文件通过

## 82) 第七十九批已落地（最小粒度增量）

继续在 `system/collection` 子模块按单端点语义对齐推进：

- 变更文件：
  - `backend/src/api/v1/system/collection.py`
  - `backend/tests/unit/api/v1/test_collection_layering.py`
- 变更内容：
  - `PUT /collection/records/{record_id}`：`resource_type="asset"` → `"collection"`
  - 保持 `resource_id="{record_id}"` 不变
  - 同步更新分层断言，仅变更 `update_collection_record` 一项，其余 `collection` 端点暂保持现状
- 验证：
  - `pytest`: `tests/unit/api/v1/test_collection_layering.py tests/unit/middleware/test_authz_dependency.py`（8 passed）
  - `ruff`: 上述变更文件通过

## 83) 第八十批已落地（最小粒度增量）

继续在 `system/collection` 子模块按单端点语义对齐推进：

- 变更文件：
  - `backend/src/api/v1/system/collection.py`
  - `backend/tests/unit/api/v1/test_collection_layering.py`
- 变更内容：
  - `DELETE /collection/records/{record_id}`：`resource_type="asset"` → `"collection"`
  - 保持 `resource_id="{record_id}"` 不变
  - 同步更新分层断言，仅变更 `delete_collection_record` 一项；`collection` 模块 `resource_type="asset"` 已清零
- 验证：
  - `pytest`: `tests/unit/api/v1/test_collection_layering.py tests/unit/middleware/test_authz_dependency.py`（8 passed）
  - `ruff`: 上述变更文件通过

## 84) 第八十一批已落地（最小粒度增量）

切换到 `llm_prompts` 模块并按单端点语义对齐推进：

- 变更文件：
  - `backend/src/api/v1/llm_prompts.py`
  - `backend/tests/unit/api/v1/test_llm_prompts_layering.py`
- 变更内容：
  - `POST /llm-prompts/`：`resource_type="asset"` → `"llm_prompt"`
  - 同步更新分层断言，仅变更 `create_prompt` 一项，其余 `llm_prompts` 端点暂保持现状
- 验证：
  - `pytest`: `tests/unit/api/v1/test_llm_prompts_layering.py tests/unit/middleware/test_authz_dependency.py`（7 passed）
  - `ruff`: 上述变更文件通过

## 85) 第八十二批已落地（最小粒度增量）

继续在 `llm_prompts` 模块按单端点语义对齐推进：

- 变更文件：
  - `backend/src/api/v1/llm_prompts.py`
  - `backend/tests/unit/api/v1/test_llm_prompts_layering.py`
- 变更内容：
  - `GET /llm-prompts/`：`resource_type="asset"` → `"llm_prompt"`
  - 同步更新分层断言，仅变更 `get_prompts` 一项，其余 `llm_prompts` 端点暂保持现状
- 验证：
  - `pytest`: `tests/unit/api/v1/test_llm_prompts_layering.py tests/unit/middleware/test_authz_dependency.py`（7 passed）
  - `ruff`: 上述变更文件通过

## 86) 第八十三批已落地（最小粒度增量）

继续在 `llm_prompts` 模块按单端点语义对齐推进：

- 变更文件：
  - `backend/src/api/v1/llm_prompts.py`
  - `backend/tests/unit/api/v1/test_llm_prompts_layering.py`
- 变更内容：
  - `GET /llm-prompts/{prompt_id}`：`resource_type="asset"` → `"llm_prompt"`
  - 保持 `resource_id="{prompt_id}"` 与 `deny_as_not_found=True` 不变
  - 同步更新分层断言，仅变更 `get_prompt` 一项，其余 `llm_prompts` 端点暂保持现状
- 验证：
  - `pytest`: `tests/unit/api/v1/test_llm_prompts_layering.py tests/unit/middleware/test_authz_dependency.py`（7 passed）
  - `ruff`: 上述变更文件通过

## 87) 第八十四批已落地（最小粒度增量）

继续在 `llm_prompts` 模块按单端点语义对齐推进：

- 变更文件：
  - `backend/src/api/v1/llm_prompts.py`
  - `backend/tests/unit/api/v1/test_llm_prompts_layering.py`
- 变更内容：
  - `PUT /llm-prompts/{prompt_id}`：`resource_type="asset"` → `"llm_prompt"`
  - 保持 `resource_id="{prompt_id}"` 不变
  - 同步更新分层断言，仅变更 `update_prompt` 一项，其余 `llm_prompts` 端点暂保持现状
- 验证：
  - `pytest`: `tests/unit/api/v1/test_llm_prompts_layering.py tests/unit/middleware/test_authz_dependency.py`（7 passed）
  - `ruff`: 上述变更文件通过

## 88) 第八十五批已落地（最小粒度增量）

继续在 `llm_prompts` 模块按单端点语义对齐推进：

- 变更文件：
  - `backend/src/api/v1/llm_prompts.py`
  - `backend/tests/unit/api/v1/test_llm_prompts_layering.py`
- 变更内容：
  - `POST /llm-prompts/{prompt_id}/activate`：`resource_type="asset"` → `"llm_prompt"`
  - 保持 `resource_id="{prompt_id}"` 不变
  - 同步更新分层断言，仅变更 `activate_prompt` 一项，其余 `llm_prompts` 端点暂保持现状
- 验证：
  - `pytest`: `tests/unit/api/v1/test_llm_prompts_layering.py tests/unit/middleware/test_authz_dependency.py`（7 passed）
  - `ruff`: 上述变更文件通过

## 89) 第八十六批已落地（最小粒度增量）

继续在 `llm_prompts` 模块按单端点语义对齐推进：

- 变更文件：
  - `backend/src/api/v1/llm_prompts.py`
  - `backend/tests/unit/api/v1/test_llm_prompts_layering.py`
- 变更内容：
  - `POST /llm-prompts/{prompt_id}/rollback`：`resource_type="asset"` → `"llm_prompt"`
  - 保持 `resource_id="{prompt_id}"` 不变
  - 同步更新分层断言，仅变更 `rollback_prompt` 一项，其余 `llm_prompts` 端点暂保持现状
- 验证：
  - `pytest`: `tests/unit/api/v1/test_llm_prompts_layering.py tests/unit/middleware/test_authz_dependency.py`（7 passed）
  - `ruff`: 上述变更文件通过

## 90) 第八十七批已落地（最小粒度增量）

继续在 `llm_prompts` 模块按单端点语义对齐推进：

- 变更文件：
  - `backend/src/api/v1/llm_prompts.py`
  - `backend/tests/unit/api/v1/test_llm_prompts_layering.py`
- 变更内容：
  - `GET /llm-prompts/{prompt_id}/versions`：`resource_type="asset"` → `"llm_prompt"`
  - 保持 `resource_id="{prompt_id}"` 与 `deny_as_not_found=True` 不变
  - 同步更新分层断言，仅变更 `get_prompt_versions` 一项，其余 `llm_prompts` 端点暂保持现状
- 验证：
  - `pytest`: `tests/unit/api/v1/test_llm_prompts_layering.py tests/unit/middleware/test_authz_dependency.py`（7 passed）
  - `ruff`: 上述变更文件通过

## 91) 第八十八批已落地（最小粒度增量）

继续在 `llm_prompts` 模块按单端点语义对齐推进：

- 变更文件：
  - `backend/src/api/v1/llm_prompts.py`
  - `backend/tests/unit/api/v1/test_llm_prompts_layering.py`
- 变更内容：
  - `GET /llm-prompts/statistics/overview`：`resource_type="asset"` → `"llm_prompt"`
  - 同步更新分层断言，仅变更 `get_statistics` 一项，其余 `llm_prompts` 端点暂保持现状
- 验证：
  - `pytest`: `tests/unit/api/v1/test_llm_prompts_layering.py tests/unit/middleware/test_authz_dependency.py`（7 passed）
  - `ruff`: 上述变更文件通过

## 92) 第八十九批已落地（最小粒度增量）

继续在 `llm_prompts` 模块按单端点语义对齐推进：

- 变更文件：
  - `backend/src/api/v1/llm_prompts.py`
  - `backend/tests/unit/api/v1/test_llm_prompts_layering.py`
- 变更内容：
  - `POST /llm-prompts/feedback`：`resource_type="asset"` → `"llm_prompt"`
  - 同步更新分层断言，仅变更 `collect_feedback` 一项
  - `llm_prompts` 路由层端点 `resource_type="asset"` 已清零
- 验证：
  - `pytest`: `tests/unit/api/v1/test_llm_prompts_layering.py tests/unit/middleware/test_authz_dependency.py`（7 passed）
  - `ruff`: 上述变更文件通过

## 93) 第九十批已落地（最小粒度增量）

切换到 `analytics` 模块并按单端点语义对齐推进：

- 变更文件：
  - `backend/src/api/v1/analytics/analytics.py`
  - `backend/tests/unit/api/v1/analytics/test_analytics_layering.py`
- 变更内容：
  - `GET /analytics/comprehensive`：`resource_type="asset"` → `"analytics"`
  - 同步更新分层断言，仅变更 `get_comprehensive_analytics` 一项，其余 `analytics` 端点暂保持现状
- 验证：
  - `ruff`: `src/api/v1/analytics/analytics.py tests/unit/api/v1/analytics/test_analytics_layering.py`（通过）
  - `pytest`: `tests/unit/api/v1/analytics/test_analytics_layering.py`（2 passed）

## 94) 第九十一批已落地（最小粒度增量）

继续在 `analytics` 模块按单端点语义对齐推进：

- 变更文件：
  - `backend/src/api/v1/analytics/analytics.py`
  - `backend/tests/unit/api/v1/analytics/test_analytics_layering.py`
- 变更内容：
  - `GET /analytics/cache/stats`：`resource_type="asset"` → `"analytics"`
  - 同步更新分层断言，仅变更 `get_cache_stats` 一项，其余 `analytics` 端点暂保持现状
- 验证：
  - `ruff`: `src/api/v1/analytics/analytics.py tests/unit/api/v1/analytics/test_analytics_layering.py`（通过）
  - `pytest`: `tests/unit/api/v1/analytics/test_analytics_layering.py`（2 passed）

## 95) 第九十二批已落地（最小粒度增量）

继续在 `analytics` 模块按单端点语义对齐推进：

- 变更文件：
  - `backend/src/api/v1/analytics/analytics.py`
  - `backend/tests/unit/api/v1/analytics/test_analytics_layering.py`
- 变更内容：
  - `POST /analytics/cache/clear`：`resource_type="asset"` → `"analytics"`
  - 同步更新分层断言，仅变更 `clear_cache` 一项，其余 `analytics` 端点暂保持现状
- 验证：
  - `ruff`: `src/api/v1/analytics/analytics.py tests/unit/api/v1/analytics/test_analytics_layering.py`（通过）
  - `pytest`: `tests/unit/api/v1/analytics/test_analytics_layering.py`（2 passed）

## 96) 第九十三批已落地（最小粒度增量）

继续在 `analytics` 模块按单端点语义对齐推进：

- 变更文件：
  - `backend/src/api/v1/analytics/analytics.py`
  - `backend/tests/unit/api/v1/analytics/test_analytics_layering.py`
- 变更内容：
  - `GET /analytics/trend`：`resource_type="asset"` → `"analytics"`
  - 同步更新分层断言，仅变更 `get_trend_data` 一项，其余 `analytics` 端点暂保持现状
- 验证：
  - `ruff`: `src/api/v1/analytics/analytics.py tests/unit/api/v1/analytics/test_analytics_layering.py`（通过）
  - `pytest`: `tests/unit/api/v1/analytics/test_analytics_layering.py`（2 passed）

## 97) 第九十四批已落地（最小粒度增量）

继续在 `analytics` 模块按单端点语义对齐推进：

- 变更文件：
  - `backend/src/api/v1/analytics/analytics.py`
  - `backend/tests/unit/api/v1/analytics/test_analytics_layering.py`
- 变更内容：
  - `GET /analytics/distribution`：`resource_type="asset"` → `"analytics"`
  - 同步更新分层断言，仅变更 `get_distribution_data` 一项，其余 `analytics` 端点暂保持现状
- 验证：
  - `ruff`: `src/api/v1/analytics/analytics.py tests/unit/api/v1/analytics/test_analytics_layering.py`（通过）
  - `pytest`: `tests/unit/api/v1/analytics/test_analytics_layering.py`（2 passed）

## 98) 第九十五批已落地（最小粒度增量）

继续在 `analytics` 模块按单端点语义对齐推进：

- 变更文件：
  - `backend/src/api/v1/analytics/analytics.py`
  - `backend/tests/unit/api/v1/analytics/test_analytics_layering.py`
- 变更内容：
  - `POST /analytics/export`：`resource_type="asset"` → `"analytics"`
  - 同步更新分层断言，仅变更 `export_analytics` 一项；`analytics/analytics.py` 中 `resource_type="asset"` 已清零
- 验证：
  - `ruff`: `src/api/v1/analytics/analytics.py tests/unit/api/v1/analytics/test_analytics_layering.py`（通过）
  - `pytest`: `tests/unit/api/v1/analytics/test_analytics_layering.py`（2 passed）

## 99) 第九十六批已落地（最小粒度增量）

切换到 `analytics/statistics_modules/trend_stats` 并按单端点语义对齐推进：

- 变更文件：
  - `backend/src/api/v1/analytics/statistics_modules/trend_stats.py`
  - `backend/tests/unit/api/v1/analytics/statistics_modules/test_trend_stats_layering.py`
- 变更内容：
  - `GET /analytics/trend/{metric}`：`resource_type="asset"` → `"analytics"`
  - 同步更新分层断言，仅变更 `get_trend_data` 一项，其余 `statistics_modules` 端点暂保持现状
- 验证：
  - `ruff`: `src/api/v1/analytics/statistics_modules/trend_stats.py tests/unit/api/v1/analytics/statistics_modules/test_trend_stats_layering.py`（通过）
  - `pytest`: `tests/unit/api/v1/analytics/statistics_modules/test_trend_stats_layering.py`（2 passed）

## 100) 第九十七批已落地（最小粒度增量）

切换到 `analytics/statistics_modules/distribution` 并按单端点语义对齐推进：

- 变更文件：
  - `backend/src/api/v1/analytics/statistics_modules/distribution.py`
  - `backend/tests/unit/api/v1/analytics/statistics_modules/test_distribution_layering.py`
- 变更内容：
  - `GET /analytics/ownership-distribution`：`resource_type="asset"` → `"analytics"`
  - 同步更新分层断言，仅变更 `get_ownership_distribution` 一项，其余 `distribution` 端点暂保持现状
- 验证：
  - `ruff`: `src/api/v1/analytics/statistics_modules/distribution.py tests/unit/api/v1/analytics/statistics_modules/test_distribution_layering.py`（通过）
  - `pytest`: `tests/unit/api/v1/analytics/statistics_modules/test_distribution_layering.py`（5 passed）

## 101) 第九十八批已落地（最小粒度增量）

继续在 `analytics/statistics_modules/distribution` 按单端点语义对齐推进：

- 变更文件：
  - `backend/src/api/v1/analytics/statistics_modules/distribution.py`
  - `backend/tests/unit/api/v1/analytics/statistics_modules/test_distribution_layering.py`
- 变更内容：
  - `GET /analytics/property-nature-distribution`：`resource_type="asset"` → `"analytics"`
  - 同步更新分层断言，仅变更 `get_property_nature_distribution` 一项，其余 `distribution` 端点暂保持现状
- 验证：
  - `ruff`: `src/api/v1/analytics/statistics_modules/distribution.py tests/unit/api/v1/analytics/statistics_modules/test_distribution_layering.py`（通过）
  - `pytest`: `tests/unit/api/v1/analytics/statistics_modules/test_distribution_layering.py`（5 passed）

## 102) 第九十九批已落地（最小粒度增量）

继续在 `analytics/statistics_modules/distribution` 按单端点语义对齐推进：

- 变更文件：
  - `backend/src/api/v1/analytics/statistics_modules/distribution.py`
  - `backend/tests/unit/api/v1/analytics/statistics_modules/test_distribution_layering.py`
- 变更内容：
  - `GET /analytics/usage-status-distribution`：`resource_type="asset"` → `"analytics"`
  - 同步更新分层断言，仅变更 `get_usage_status_distribution` 一项，其余 `distribution` 端点暂保持现状
- 验证：
  - `ruff`: `src/api/v1/analytics/statistics_modules/distribution.py tests/unit/api/v1/analytics/statistics_modules/test_distribution_layering.py`（通过）
  - `pytest`: `tests/unit/api/v1/analytics/statistics_modules/test_distribution_layering.py`（5 passed）

## 103) 第一百批已落地（最小粒度增量）

继续在 `analytics/statistics_modules/distribution` 按单端点语义对齐推进：

- 变更文件：
  - `backend/src/api/v1/analytics/statistics_modules/distribution.py`
  - `backend/tests/unit/api/v1/analytics/statistics_modules/test_distribution_layering.py`
- 变更内容：
  - `GET /analytics/asset-distribution`：`resource_type="asset"` → `"analytics"`
  - 同步更新分层断言，仅变更 `get_asset_distribution` 一项
  - `distribution` 路由层端点 `resource_type="asset"` 已清零
- 验证：
  - `ruff`: `src/api/v1/analytics/statistics_modules/distribution.py tests/unit/api/v1/analytics/statistics_modules/test_distribution_layering.py`（通过）
  - `pytest`: `tests/unit/api/v1/analytics/statistics_modules/test_distribution_layering.py`（5 passed）

## 104) 第一百零一批已落地（最小粒度增量）

切换到 `analytics/statistics_modules/basic_stats` 并按单端点语义对齐推进：

- 变更文件：
  - `backend/src/api/v1/analytics/statistics_modules/basic_stats.py`
  - `backend/tests/unit/api/v1/analytics/statistics_modules/test_basic_stats_layering.py`
- 变更内容：
  - `GET /statistics/basic`：`resource_type="asset"` → `"analytics"`
  - 同步更新分层断言，仅变更 `get_basic_statistics` 一项，其余 `basic_stats` 端点暂保持现状
- 验证：
  - `ruff`: `src/api/v1/analytics/statistics_modules/basic_stats.py tests/unit/api/v1/analytics/statistics_modules/test_basic_stats_layering.py`（通过）
  - `pytest`: `tests/unit/api/v1/analytics/statistics_modules/test_basic_stats_layering.py`（5 passed）

## 105) 第一百零二批已落地（最小粒度增量）

继续在 `analytics/statistics_modules/basic_stats` 按单端点语义对齐推进：

- 变更文件：
  - `backend/src/api/v1/analytics/statistics_modules/basic_stats.py`
  - `backend/tests/unit/api/v1/analytics/statistics_modules/test_basic_stats_layering.py`
- 变更内容：
  - `GET /statistics/summary`：`resource_type="asset"` → `"analytics"`
  - 同步更新分层断言，仅变更 `get_statistics_summary` 一项，其余 `basic_stats` 端点暂保持现状
- 验证：
  - `ruff`: `src/api/v1/analytics/statistics_modules/basic_stats.py tests/unit/api/v1/analytics/statistics_modules/test_basic_stats_layering.py`（通过）
  - `pytest`: `tests/unit/api/v1/analytics/statistics_modules/test_basic_stats_layering.py`（5 passed）

## 106) 第一百零三批已落地（最小粒度增量）

继续在 `analytics/statistics_modules/basic_stats` 按单端点语义对齐推进：

- 变更文件：
  - `backend/src/api/v1/analytics/statistics_modules/basic_stats.py`
  - `backend/tests/unit/api/v1/analytics/statistics_modules/test_basic_stats_layering.py`
- 变更内容：
  - `GET /statistics/dashboard`：`resource_type="asset"` → `"analytics"`
  - 同步更新分层断言，仅变更 `get_dashboard_data` 一项，其余 `basic_stats` 端点暂保持现状
- 验证：
  - `ruff`: `src/api/v1/analytics/statistics_modules/basic_stats.py tests/unit/api/v1/analytics/statistics_modules/test_basic_stats_layering.py`（通过）
  - `pytest`: `tests/unit/api/v1/analytics/statistics_modules/test_basic_stats_layering.py`（5 passed）

## 107) 第一百零四批已落地（最小粒度增量）

继续在 `analytics/statistics_modules/basic_stats` 按单端点语义对齐推进：

- 变更文件：
  - `backend/src/api/v1/analytics/statistics_modules/basic_stats.py`
  - `backend/tests/unit/api/v1/analytics/statistics_modules/test_basic_stats_layering.py`
- 变更内容：
  - `GET /statistics/comprehensive`：`resource_type="asset"` → `"analytics"`
  - 同步更新分层断言，仅变更 `get_comprehensive_statistics` 一项，其余 `basic_stats` 端点暂保持现状
- 验证：
  - `ruff`: `src/api/v1/analytics/statistics_modules/basic_stats.py tests/unit/api/v1/analytics/statistics_modules/test_basic_stats_layering.py`（通过）
  - `pytest`: `tests/unit/api/v1/analytics/statistics_modules/test_basic_stats_layering.py`（5 passed）

## 108) 第一百零五批已落地（最小粒度增量）

继续在 `analytics/statistics_modules/basic_stats` 按单端点语义对齐推进：

- 变更文件：
  - `backend/src/api/v1/analytics/statistics_modules/basic_stats.py`
  - `backend/tests/unit/api/v1/analytics/statistics_modules/test_basic_stats_layering.py`
- 变更内容：
  - `POST /statistics/cache/clear`：`resource_type="asset"` → `"analytics"`
  - 同步更新分层断言，仅变更 `clear_statistics_cache` 一项，其余 `basic_stats` 端点暂保持现状
- 验证：
  - `ruff`: `src/api/v1/analytics/statistics_modules/basic_stats.py tests/unit/api/v1/analytics/statistics_modules/test_basic_stats_layering.py`（通过）
  - `pytest`: `tests/unit/api/v1/analytics/statistics_modules/test_basic_stats_layering.py`（5 passed）

## 109) 第一百零六批已落地（最小粒度增量）

继续在 `analytics/statistics_modules/basic_stats` 按单端点语义对齐推进：

- 变更文件：
  - `backend/src/api/v1/analytics/statistics_modules/basic_stats.py`
  - `backend/tests/unit/api/v1/analytics/statistics_modules/test_basic_stats_layering.py`
- 变更内容：
  - `GET /statistics/cache/info`：`resource_type="asset"` → `"analytics"`
  - 同步更新分层断言，仅变更 `get_cache_info` 一项
  - `basic_stats` 路由层端点 `resource_type="asset"` 已清零
- 验证：
  - `ruff`: `src/api/v1/analytics/statistics_modules/basic_stats.py tests/unit/api/v1/analytics/statistics_modules/test_basic_stats_layering.py`（通过）
  - `pytest`: `tests/unit/api/v1/analytics/statistics_modules/test_basic_stats_layering.py`（5 passed）

## 110) 第一百零七批已落地（最小粒度增量）

切换到 `analytics/statistics_modules/area_stats` 并按单端点语义对齐推进：

- 变更文件：
  - `backend/src/api/v1/analytics/statistics_modules/area_stats.py`
  - `backend/tests/unit/api/v1/analytics/statistics_modules/test_area_stats_layering.py`
- 变更内容：
  - `GET /statistics/area-summary`：`resource_type="asset"` → `"analytics"`
  - 同步更新分层断言，仅变更 `get_area_summary` 一项，其余 `area_stats` 端点暂保持现状
- 验证：
  - `ruff`: `src/api/v1/analytics/statistics_modules/area_stats.py tests/unit/api/v1/analytics/statistics_modules/test_area_stats_layering.py`（通过）
  - `pytest`: `tests/unit/api/v1/analytics/statistics_modules/test_area_stats_layering.py`（5 passed）

## 111) 第一百零八批已落地（最小粒度增量）

继续在 `analytics/statistics_modules/area_stats` 按单端点语义对齐推进：

- 变更文件：
  - `backend/src/api/v1/analytics/statistics_modules/area_stats.py`
  - `backend/tests/unit/api/v1/analytics/statistics_modules/test_area_stats_layering.py`
- 变更内容：
  - `GET /statistics/area-statistics`：`resource_type="asset"` → `"analytics"`
  - 同步更新分层断言，仅变更 `get_area_statistics` 一项
  - `area_stats` 路由层端点 `resource_type="asset"` 已清零
- 验证：
  - `ruff`: `src/api/v1/analytics/statistics_modules/area_stats.py tests/unit/api/v1/analytics/statistics_modules/test_area_stats_layering.py`（通过）
  - `pytest`: `tests/unit/api/v1/analytics/statistics_modules/test_area_stats_layering.py`（5 passed）

## 112) 第一百零九批已落地（最小粒度增量）

切换到 `analytics/statistics_modules/occupancy_stats` 并按单端点语义对齐推进：

- 变更文件：
  - `backend/src/api/v1/analytics/statistics_modules/occupancy_stats.py`
  - `backend/tests/unit/api/v1/analytics/statistics_modules/test_occupancy_stats_layering.py`
- 变更内容：
  - `GET /statistics/occupancy-rate/overall`：`resource_type="asset"` → `"analytics"`
  - 同步更新分层断言，仅变更 `get_overall_occupancy_rate` 一项，其余 `occupancy_stats` 端点暂保持现状
- 验证：
  - `ruff`: `src/api/v1/analytics/statistics_modules/occupancy_stats.py tests/unit/api/v1/analytics/statistics_modules/test_occupancy_stats_layering.py`（通过）
  - `pytest`: `tests/unit/api/v1/analytics/statistics_modules/test_occupancy_stats_layering.py`（2 passed）

## 113) 第一百一十批已落地（最小粒度增量）

继续在 `analytics/statistics_modules/occupancy_stats` 按单端点语义对齐推进：

- 变更文件：
  - `backend/src/api/v1/analytics/statistics_modules/occupancy_stats.py`
  - `backend/tests/unit/api/v1/analytics/statistics_modules/test_occupancy_stats_layering.py`
- 变更内容：
  - `GET /statistics/occupancy-rate/by-category`：`resource_type="asset"` → `"analytics"`
  - 同步更新分层断言，仅变更 `get_occupancy_rate_by_category` 一项，其余 `occupancy_stats` 端点暂保持现状
- 验证：
  - `ruff`: `src/api/v1/analytics/statistics_modules/occupancy_stats.py tests/unit/api/v1/analytics/statistics_modules/test_occupancy_stats_layering.py`（通过）
  - `pytest`: `tests/unit/api/v1/analytics/statistics_modules/test_occupancy_stats_layering.py`（2 passed）

## 114) 第一百一十一批已落地（最小粒度增量）

继续在 `analytics/statistics_modules/occupancy_stats` 按单端点语义对齐推进：

- 变更文件：
  - `backend/src/api/v1/analytics/statistics_modules/occupancy_stats.py`
  - `backend/tests/unit/api/v1/analytics/statistics_modules/test_occupancy_stats_layering.py`
- 变更内容：
  - `GET /statistics/occupancy-rate`：`resource_type="asset"` → `"analytics"`
  - 同步更新分层断言，仅变更 `get_occupancy_rate_statistics` 一项
  - `occupancy_stats` 路由层端点 `resource_type="asset"` 已清零
- 验证：
  - `ruff`: `src/api/v1/analytics/statistics_modules/occupancy_stats.py tests/unit/api/v1/analytics/statistics_modules/test_occupancy_stats_layering.py`（通过）
  - `pytest`: `tests/unit/api/v1/analytics/statistics_modules/test_occupancy_stats_layering.py`（2 passed）

## 115) 第一百一十二批已落地（最小粒度增量）

切换到 `analytics/statistics_modules/financial_stats` 并按单端点语义对齐推进：

- 变更文件：
  - `backend/src/api/v1/analytics/statistics_modules/financial_stats.py`
  - `backend/tests/unit/api/v1/analytics/statistics_modules/test_financial_stats_layering.py`
- 变更内容：
  - `GET /statistics/financial-summary`：`resource_type="asset"` → `"analytics"`
  - 同步更新分层断言，仅变更 `get_financial_summary` 一项
  - `financial_stats` 路由层端点 `resource_type="asset"` 已清零
- 验证：
  - `ruff`: `src/api/v1/analytics/statistics_modules/financial_stats.py tests/unit/api/v1/analytics/statistics_modules/test_financial_stats_layering.py`（通过）
  - `pytest`: `tests/unit/api/v1/analytics/statistics_modules/test_financial_stats_layering.py`（2 passed）

## 116) 第一百一十三批已落地（最小粒度增量）

切换到 `assets/ownership` 并按单端点语义对齐推进：

- 变更文件：
  - `backend/src/api/v1/assets/ownership.py`
  - `backend/tests/unit/api/v1/test_ownership_layering.py`
- 变更内容：
  - `GET /ownership/dropdown-options`：`resource_type="asset"` → `"ownership"`
  - 同步更新分层断言，仅变更 `get_ownership_dropdown_options` 一项，其余 `ownership` 端点暂保持现状
- 验证：
  - `ruff`: `src/api/v1/assets/ownership.py tests/unit/api/v1/test_ownership_layering.py`（通过）
  - `pytest`: `tests/unit/api/v1/test_ownership_layering.py`（6 passed）

## 117) 第一百一十四批已落地（最小粒度增量）

继续在 `assets/ownership` 按单端点语义对齐推进：

- 变更文件：
  - `backend/src/api/v1/assets/ownership.py`
  - `backend/tests/unit/api/v1/test_ownership_layering.py`
- 变更内容：
  - `GET /ownership`：`resource_type="asset"` → `"ownership"`
  - 同步更新分层断言，仅变更 `get_ownerships` 一项，其余 `ownership` 端点暂保持现状
- 验证：
  - `ruff`: `src/api/v1/assets/ownership.py tests/unit/api/v1/test_ownership_layering.py`（通过）
  - `pytest`: `tests/unit/api/v1/test_ownership_layering.py`（6 passed）

## 118) 下一批建议（按风险排序）

1. `system` 模块其余端点（不含已语义化 `system_monitoring/error_recovery/excel_config`）
2. `auth` 模块（roles/users/organization/sessions/audit/security）
3. `llm_prompts` 与 `analytics`（若确认仍需 `asset`，应补明确设计说明并固化门禁）

## 119) 执行前置

在继续批量迁移前，建议先补齐“资源类型-策略命中矩阵”与迁移 seed 扩展计划，避免运行时误拒绝。

## 120) 第一百一十五批已落地（最小粒度增量）

继续在 `assets/ownership` 按单端点语义对齐推进：

- 变更文件：
  - `backend/src/api/v1/assets/ownership.py`
  - `backend/tests/unit/api/v1/test_ownership_layering.py`
- 变更内容：
  - `GET /ownership/search`：`resource_type="asset"` → `"ownership"`
  - 同步更新分层断言，仅变更 `search_ownerships` 一项，其余 `ownership` 端点暂保持现状
- 验证：
  - `ruff`: `src/api/v1/assets/ownership.py tests/unit/api/v1/test_ownership_layering.py`（通过）
  - `pytest`: `tests/unit/api/v1/test_ownership_layering.py`（6 passed）

## 121) 第一百一十六批已落地（最小粒度增量）

继续在 `assets/ownership` 按单端点语义对齐推进：

- 变更文件：
  - `backend/src/api/v1/assets/ownership.py`
  - `backend/tests/unit/api/v1/test_ownership_layering.py`
- 变更内容：
  - `GET /ownership/statistics/summary`：`resource_type="asset"` → `"ownership"`
  - 同步更新分层断言，仅变更 `get_ownership_statistics` 一项，其余 `ownership` 端点暂保持现状
- 验证：
  - `ruff`: `src/api/v1/assets/ownership.py tests/unit/api/v1/test_ownership_layering.py`（通过）
  - `pytest`: `tests/unit/api/v1/test_ownership_layering.py`（6 passed）

## 122) 第一百一十七批已落地（最小粒度增量）

继续在 `assets/ownership` 按单端点语义对齐推进：

- 变更文件：
  - `backend/src/api/v1/assets/ownership.py`
  - `backend/tests/unit/api/v1/test_ownership_layering.py`
- 变更内容：
  - `POST /ownership/{ownership_id}/toggle-status`：`resource_type="asset"` → `"ownership"`
  - 同步更新分层断言，仅变更 `toggle_ownership_status` 一项，其余 `ownership` 端点暂保持现状
- 验证：
  - `ruff`: `src/api/v1/assets/ownership.py tests/unit/api/v1/test_ownership_layering.py`（通过）
  - `pytest`: `tests/unit/api/v1/test_ownership_layering.py`（6 passed）

## 123) 第一百一十八批已落地（最小粒度增量）

继续在 `assets/ownership` 按单端点语义对齐推进：

- 变更文件：
  - `backend/src/api/v1/assets/ownership.py`
  - `backend/tests/unit/api/v1/test_ownership_layering.py`
- 变更内容：
  - `PUT /ownership/{ownership_id}`：`resource_type="asset"` → `"ownership"`
  - 同步更新分层断言，仅变更 `update_ownership` 一项，其余 `ownership` 端点暂保持现状
- 验证：
  - `ruff`: `src/api/v1/assets/ownership.py tests/unit/api/v1/test_ownership_layering.py`（通过）
  - `pytest`: `tests/unit/api/v1/test_ownership_layering.py`（6 passed）

## 124) 第一百一十九批已落地（最小粒度增量）

继续在 `assets/ownership` 按单端点语义对齐推进：

- 变更文件：
  - `backend/src/api/v1/assets/ownership.py`
  - `backend/tests/unit/api/v1/test_ownership_layering.py`
- 变更内容：
  - `PUT /ownership/{ownership_id}/projects`：`resource_type="asset"` → `"ownership"`
  - 同步更新分层断言，仅变更 `update_ownership_projects` 一项，其余 `ownership` 端点暂保持现状
- 验证：
  - `ruff`: `src/api/v1/assets/ownership.py tests/unit/api/v1/test_ownership_layering.py`（通过）
  - `pytest`: `tests/unit/api/v1/test_ownership_layering.py`（6 passed）

## 125) 第一百二十批已落地（最小粒度增量）

继续在 `assets/ownership` 按单端点语义对齐推进：

- 变更文件：
  - `backend/src/api/v1/assets/ownership.py`
  - `backend/tests/unit/api/v1/test_ownership_layering.py`
- 变更内容：
  - `DELETE /ownership/{ownership_id}`：`resource_type="asset"` → `"ownership"`
  - 同步更新分层断言，仅变更 `delete_ownership` 一项，其余 `ownership` 端点暂保持现状
- 验证：
  - `ruff`: `src/api/v1/assets/ownership.py tests/unit/api/v1/test_ownership_layering.py`（通过）
  - `pytest`: `tests/unit/api/v1/test_ownership_layering.py`（6 passed）

## 126) 第一百二十一批已落地（最小粒度增量）

继续在 `assets/ownership` 按单端点语义对齐推进：

- 变更文件：
  - `backend/src/api/v1/assets/ownership.py`
  - `backend/tests/unit/api/v1/test_ownership_layering.py`
- 变更内容：
  - `GET /ownership/{ownership_id}/financial-summary`：`resource_type="asset"` → `"ownership"`
  - 同步更新分层断言，仅变更 `get_ownership_financial_summary` 一项，其余 `ownership` 端点暂保持现状
- 验证：
  - `ruff`: `src/api/v1/assets/ownership.py tests/unit/api/v1/test_ownership_layering.py`（通过）
  - `pytest`: `tests/unit/api/v1/test_ownership_layering.py`（6 passed）

## 127) 第一百二十二批已落地（最小粒度增量）

继续在 `assets/ownership` 按单处语义对齐推进：

- 变更文件：
  - `backend/src/api/v1/assets/ownership.py`
  - `backend/tests/unit/api/v1/test_ownership_layering.py`
- 变更内容：
  - 创建鉴权 helper `_require_ownership_create_authz` 内 `authz_service.check_access(...)` 的 `resource_type`：`"asset"` → `"ownership"`
  - 同步更新 helper 单测断言，仅变更 create 鉴权校验项
- 验证：
  - `ruff`: `src/api/v1/assets/ownership.py tests/unit/api/v1/test_ownership_layering.py`（通过）
  - `pytest`: `tests/unit/api/v1/test_ownership_layering.py`（6 passed）

## 128) 第一百二十三批已落地（最小粒度增量）

继续在 `assets/ownership` 按单处语义对齐推进：

- 变更文件：
  - `backend/src/api/v1/assets/ownership.py`
- 变更内容：
  - 创建鉴权 helper `_require_ownership_create_authz` 返回的 `AuthzContext.resource_type`：`"asset"` → `"ownership"`
  - `ownership.py` 路由层 `resource_type="asset"` 漂移已清零
- 验证：
  - `ruff`: `src/api/v1/assets/ownership.py tests/unit/api/v1/test_ownership_layering.py`（通过）
  - `pytest`: `tests/unit/api/v1/test_ownership_layering.py`（6 passed）

## 129) 第一百二十四批已落地（最小粒度增量）

切换到 `assets/occupancy` 并按单端点语义对齐推进：

- 变更文件：
  - `backend/src/api/v1/assets/occupancy.py`
  - `backend/tests/unit/api/v1/test_occupancy_layering.py`
- 变更内容：
  - `GET /occupancy/rate`：`resource_type="asset"` → `"occupancy"`
  - 同步更新分层断言，仅变更 `calculate_occupancy_rate` 一项，其余 `occupancy` 端点暂保持现状
- 验证：
  - `ruff`: `src/api/v1/assets/occupancy.py tests/unit/api/v1/test_occupancy_layering.py`（通过）
  - `pytest`: `tests/unit/api/v1/test_occupancy_layering.py`（3 passed）

## 130) 第一百二十五批已落地（最小粒度增量）

继续在 `assets/occupancy` 按单端点语义对齐推进：

- 变更文件：
  - `backend/src/api/v1/assets/occupancy.py`
  - `backend/tests/unit/api/v1/test_occupancy_layering.py`
- 变更内容：
  - `GET /occupancy/analysis`：`resource_type="asset"` → `"occupancy"`
  - 同步更新分层断言，仅变更 `analyze_occupancy` 一项，其余 `occupancy` 端点暂保持现状
- 验证：
  - `ruff`: `src/api/v1/assets/occupancy.py tests/unit/api/v1/test_occupancy_layering.py`（通过）
  - `pytest`: `tests/unit/api/v1/test_occupancy_layering.py`（3 passed）

## 131) 第一百二十六批已落地（最小粒度增量）

继续在 `assets/occupancy` 按单端点语义对齐推进：

- 变更文件：
  - `backend/src/api/v1/assets/occupancy.py`
  - `backend/tests/unit/api/v1/test_occupancy_layering.py`
- 变更内容：
  - `GET /occupancy/trends`：`resource_type="asset"` → `"occupancy"`
  - 同步更新分层断言，仅变更 `get_occupancy_trends` 一项；`occupancy.py` 路由层端点 `resource_type="asset"` 已清零
- 验证：
  - `ruff`: `src/api/v1/assets/occupancy.py tests/unit/api/v1/test_occupancy_layering.py`（通过）
  - `pytest`: `tests/unit/api/v1/test_occupancy_layering.py`（3 passed）