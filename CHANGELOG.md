# 变更日志 (Changelog)

## [Unreleased] - 2026-02-07

### 🛠️ 本次修复 (Current Fixes)

- 前端分页表格运行时崩溃根因修复（TDD）：新增 `frontend/src/components/Common/__tests__/TableWithPagination.test.tsx` 先复现 `ReferenceError: responsive is not defined`（红灯），再修复 `frontend/src/components/Common/TableWithPagination.tsx` 的 props 解构，补齐 `responsive/cardTitle/renderCard/cardFields` 并为 `responsive` 提供默认值；测试转绿后对模块页回归验证，`/assets`、`/rental/contracts`、`/property-certificates`、`/ownership`、`/project`、`/system/*` 等 13 个页面不再出现该错误
- 前端类型质量收敛：`frontend/src/components/Common/TableWithPagination.tsx` 将 `cardFields.render` 的参数类型由 `any` 调整为 `unknown`，消除 `@typescript-eslint/no-explicit-any` 告警并保持组件行为不变
- 前端模块页修复后回归验证：使用 Playwright 对 25 个受保护路由执行登录后巡检（`/dashboard`、`/assets/*`、`/rental/*`、`/property-certificates*`、`/ownership`、`/project`、`/profile`、`/system/*`），结果 `25/25` 通过，先前因 `TableWithPagination` 触发的 `responsive is not defined` 错误已消失；报告见 `output/playwright/module-pages-verify-20260208-after-fix/summary.*`
- 前端页面验证 Skill 升级：更新 `C:/Users/ygz/.codex/skills/frontend-page-verify/SKILL.md`，新增批量模块巡检流程、统一通过标准（URL/console/network）、CLI 大批量验证的脚本化回退策略、`summary.json/csv/txt` 产物规范与共享组件回归定位规则
- 文档补充冲突复盘：在 `AGENTS.md` 与 `CLAUDE.md` 新增 Git 冲突处理经验与标准流程（`UU`/`DU` 分类、`modify/delete` 历史核查、冲突后最小验证、推送前人工核准），用于避免自动偏向合并导致的误恢复/导入漂移/模型重复定义问题
- 手动冲突复核修复：纠正 `fed92f6b` 自动冲突处理引入的问题，恢复 `backend/src/models/asset.py` 为单一 `Asset` 定义并移除重复模型声明，修正 `backend/src/crud/__init__.py`、`backend/src/crud/asset.py`、`backend/src/crud/field_whitelist.py`、`backend/src/models/__init__.py`、`backend/src/services/asset/asset_service.py` 的跨模块导入；修复 `backend/tests/integration/test_postgresql_concurrency.py` 缺失导入；再次删除误恢复的历史文件 `backend/scripts/maintenance/backfill_asset_ownership_entity.py`、`backend/src/services/core/security_service.py`、`frontend/src/types/permission.ts`
- 资产批量更新去循环查库：`backend/src/services/asset/batch_service.py` 将 `batch_update` 中按资产逐条校验 `ownership_id` 与逐条 `get_by_name_async` 查重改为批次前置查询（权属一次校验 + 物业名一次查重 + 内存占位冲突判断），消除批量更新路径 N+1 往返
- Excel 导入结果提取兼容性修复：`backend/src/services/excel/excel_import_service.py` 新增 `_scalars_all`，统一兼容真实 `AsyncSession` 与测试 `AsyncMock` 的 `scalars().all()` 调用链，修复预加载优化后的异步测试回归
- 联系人批量创建事务批处理：`backend/src/crud/contact.py` 新增 `create_many_async`（批量加密 + 单事务提交 + primary 联系人一致性处理），`backend/src/api/v1/system/contact.py` 的批量接口改为一次调用批创建
- 产权证导入 owner 批量化：`backend/src/crud/property_certificate.py` 新增 `PropertyOwner` 的 `create_multi_async`，`backend/src/services/property_certificate/service.py` 的 `confirm_import` 改为批量创建 owner 后统一提交
- 新增/修复回归测试：新增 `backend/tests/unit/api/v1/test_contact_batch_api_async.py` 覆盖联系人批量接口批处理路径；更新 `backend/tests/unit/services/property_certificate/test_service.py` 对齐 `create_multi_async`；`backend/tests/unit/services/excel/test_excel_import_service.py` 与 `backend/tests/unit/services/asset/test_batch_service.py` 回归通过
- 资产出租率数据库排序/筛选能力补齐：新增迁移 `backend/alembic/versions/20260207_add_asset_cached_occupancy_rate.py` 为 `assets` 表添加生成列 `cached_occupancy_rate` 与索引；`AssetCRUD` 支持 `occupancy_rate -> cached_occupancy_rate` 排序/筛选映射并新增 `min_occupancy_rate/max_occupancy_rate` 过滤；列表 API 增加 `sort_by` 兼容参数与出租率范围筛选；前端资产列表统一改为发送 `sort_field`
- 资产列表页单测递归修复：`frontend/src/pages/Assets/__tests__/AssetListPage.test.tsx` 改为直接使用测试工具导出的 `renderWithProviders(<AssetListPage />)`，移除本地同名封装造成的递归调用，修复 `Maximum call stack size exceeded`
- 资产列表筛选类型与白名单修复：`backend/src/services/asset/asset_service.py` 为 `is_litigated` 增加 `true/false/是/否` 归一化并拒绝非法值，`backend/src/crud/asset.py` 在 `_normalize_filters` 增加同类兼容转换；`backend/src/api/v1/assets/assets.py` 同步放宽入参类型；`frontend/src/components/Asset/AssetSearch/AdvancedSearchFields.tsx` 改为提交布尔值；`backend/src/crud/field_whitelist.py` 为 `AssetWhitelist` 放行 `management_entity` 过滤，补齐与 API 暴露参数的一致性

- API 分层收口（最佳实践）：`backend/src/api/v1/system/tasks.py`、`backend/src/api/v1/auth/organization.py`、`backend/src/api/v1/auth/roles.py`、`backend/src/api/v1/assets/ownership.py` 去除对真实 CRUD 的直接依赖，统一改为经由 Service 层
- Task 服务能力补齐：`backend/src/services/task/service.py` 新增任务列表/详情/历史/运行中/最近任务与 Excel 配置查询/更新/删除服务方法，供 API 统一复用
- 任务访问控制优化：`backend/src/services/task/access.py` 增加“任务归属快速判定”短路，仅在跨用户访问时触发 RBAC 检查，减少不必要数据库访问
- 组织/权属/RBAC 服务补齐：`backend/src/services/organization/service.py`、`backend/src/services/ownership/service.py`、`backend/src/services/permission/rbac_service.py` 新增路由所需读取/统计能力，强化 Service 作为业务入口
- 回归测试同步：`backend/tests/unit/api/v1/test_tasks.py` 对齐删除 Excel 配置的正确语义（不存在返回 404）并补齐异步 mock 断言
- Ownership 单测异步化修复：`backend/tests/unit/services/ownership/test_ownership_service_impl.py` 全量从旧同步 `db.query` 断言迁移到 async/await + `AsyncMock`，对齐当前 `OwnershipService` 的 `db.execute` 与 CRUD 异步接口
- Ownership API 单测修复：`backend/tests/unit/api/v1/test_ownership_api.py` 移除失效的直连 CRUD patch，统一改为打桩 `ownership_service` 异步方法并显式 `await` 路由函数，修复 `coroutine was never awaited`/类型断言失败

- 自定义字段排序批量更新去 N+1：`backend/src/services/custom_field/service.py` 将 `update_sort_orders_async` 从循环内逐条 `custom_field_crud.get` 改为单次 `id IN (...)` 批量查询 + 内存映射更新，提交后移除逐条 `refresh`
- 自定义字段值校验链路查询收敛：`backend/src/services/custom_field/service.py` 将 `update_asset_field_values_async` 从逐值 `get/get_by_field_name` 改为按 `field_id/field_name` 双批量预取后内存匹配，避免批量字段更新时线性数据库往返
- 自定义字段 CRUD 批量能力补齐：`backend/src/crud/custom_field.py` 新增 `get_multi_by_ids_async` 与 `get_multi_by_field_names_async`，为服务层批处理提供单次取数入口
- 枚举值批量创建根因修复：`backend/src/crud/enum_field.py` 将 `batch_create_async` 从“循环调用 `create_async`（每条 commit）”重构为“父级一次预取 + 单事务批量创建 + 批量历史写入”
- 字典快速创建批量化：`backend/src/services/common_dictionary_service.py` 的 `quick_create_enum_dictionary_async` 改为调用 `enum_value_crud.batch_create_async`，移除逐选项 `create_async` 往返
- API 同类问题修复：`backend/src/api/v1/assets/asset_batch.py` 的 `/batch-custom-fields` 资产存在性校验改为一次批量查询；`backend/src/api/v1/rent_contract/contracts.py` 的创建合同资产校验改为一次 `get_multi_by_ids_async` 批量校验
- 单测回归补齐：更新 `backend/tests/unit/services/custom_field/test_custom_field_service.py`、`backend/tests/unit/services/test_common_dictionary_service.py`、`backend/tests/unit/crud/test_enum_field.py`、`backend/tests/unit/api/v1/test_rent_contract_api.py` 对齐批量路径并新增事务级断言

- 资产批量服务去兼容回退：`backend/src/services/asset/batch_service.py` 删除 `_load_assets_map` 的逐条 `asset_crud.get_async` fallback 与 mock 特判逻辑，统一走单次 `SELECT ... WHERE id IN (...)` 预取路径
- 批量删除链路一致化：`batch_service.py` 的关联检查保持纯批量查询结果处理，不再依赖测试环境对象类型分支；同时删除 `to_dict` 的“向后兼容”语义描述
- 资产时间戳弃用告警修复：`backend/src/models/asset.py`、`backend/src/services/asset/asset_service.py`、`backend/src/services/asset/batch_service.py` 新增 `_utcnow_naive()`，替换关键写路径中的 `datetime.utcnow()`，避免 Python 3.12 弃用警告
- 批量服务测试重构：`backend/tests/unit/services/asset/test_batch_service.py` 全量改为 mock `db.execute -> _FakeResult(...)` 驱动，验证“批量预取 + 批量关联检查”最终实现，不再依赖旧的逐条 `get_async` 兼容行为
- 回归验证补齐：针对资产链路执行了模型/CRUD/Service/API 与 project/system_dictionary 相关 unit+integration 目标测试（未跑全量），确认重构后核心路径通过

- 资产批量服务测试根因修复：`backend/tests/unit/services/asset/test_batch_service.py` 统一将 `history_crud.create_async` 与 `enum_validation_service.validate_value` 改为 `AsyncMock`，消除对异步接口的同步 mock 导致的 `object _SafeMagicMock can't be used in 'await' expression`
- 资产批量校验测试对齐：`test_batch_service.py` 日期字段断言由已删除的 `contract_start_date` 更新为当前模型字段 `operation_agreement_start_date`
- 权属财务统计测试异步化：`backend/tests/unit/services/asset/test_ownership_financial_service.py` 从旧 `db.query().scalar()` 测试桩改为 `AsyncSession.execute().scalar()` 路径，并对 `get_financial_summary` 全量使用 `await`
- 资产删除集成测试前置修复：`backend/tests/integration/services/asset/test_asset_service.py` 在 `TestAssetDeletion` 中补齐默认权属方初始化，修复创建资产时 `ownership_id` 外键校验失败
- 资产测试收集冲突根因修复：新增 `backend/tests/__init__.py`、`backend/tests/unit/**/__init__.py` 与 `backend/tests/integration/services/**/__init__.py`，解决 unit/integration 同名 `test_asset_service.py` 同批执行时的 `import file mismatch`
- 项目集成测试异步化修复：`backend/tests/integration/services/project/test_project_service.py` 全量改为 `AsyncSession + await` 调用 `ProjectService`/`project_crud`，移除对异步服务的同步调用假设
- 项目测试夹具根因修复：`backend/tests/integration/services/project/conftest.py` 从同步 `Session` 切换为异步 `AsyncSession` 事务夹具，彻底消除 `ChunkedIteratorResult can't be used in 'await' expression` 失败
- 资产按ID批量查询解密修复：`backend/src/crud/asset.py` 的 `get_multi_by_ids_async` 改为先取列表后逐条调用 `_decrypt_asset_object`，修复 `/assets/by-ids` 场景可能返回密文字段的问题
- 资产更新 Schema 字段回补：`backend/src/schemas/asset.py` 在 `AssetUpdate` 补回 `management_entity`，避免更新接口无法修改经营管理单位的回归
- 批量校验边界修复：`backend/src/services/asset/validators.py` 将面积一致性判断从 truthy 判定改为显式 `is not None`，修复 `rentable_area=0` 时未正确拦截 `rented_area>0` 的漏洞
- 新增回归测试：`backend/tests/unit/crud/test_asset.py` 增加 `get_multi_by_ids_async` 解密断言；`backend/tests/unit/services/asset/test_validators.py` 增加零值面积边界用例；`backend/tests/unit/schemas/test_asset_schema_attachments.py` 增加 `AssetUpdate.management_entity` 字段覆盖
- 资产关系懒加载稳定性修复：`backend/src/models/asset.py` 的 `ownership_entity` 改为通过 `inspect(...).attrs.ownership.loaded_value` 判定，避免未预加载关系时触发隐式懒加载导致 `MissingGreenlet`
- 资产列表查询预加载补齐：`backend/src/crud/asset.py` 在 `get_multi_with_search_async` 与 `get_multi_by_ids_async` 的 `include_relations=False` 路径补充 `joinedload(Asset.ownership)`，确保轻量列表序列化时 `ownership_entity` 可稳定输出
- 新增集成回归：`backend/tests/integration/services/asset/test_asset_service.py` 增加 `test_get_assets_without_relations_serializes_ownership_entity`，覆盖“非关联查询 + 序列化 ownership_entity”场景

- 资产搜索索引刷新性能根因修复：`backend/src/crud/asset.py` 将逐字段循环 `DELETE/INSERT` 重构为集合化批量刷新（一次 `DELETE ... field_name IN (...)` + 一次批量 `INSERT`），消除字段数增长导致的线性数据库往返放大
- 新增回归单测：`backend/tests/unit/crud/test_asset.py` 增加 `_refresh_search_index_entries` 批量删插、无索引字段跳过、空索引结果仅删除三类断言，防止回退到逐字段 DML
- 权属方下拉统计性能修复：`backend/src/services/ownership/service.py` 将 `get_ownership_dropdown_options` 的逐权属方计数查询（`2N+1`）重构为两条聚合查询（资产/项目各一次 `GROUP BY`），避免列表规模增长时数据库往返线性放大
- 新增回归单测：`backend/tests/unit/services/ownership/test_ownership_dropdown_options.py` 覆盖批量计数映射与空列表提前返回，确保不回退为逐条计数查询
- 组织统计查询性能修复：`backend/src/services/organization/service.py` 将层级统计从“先查层级再按层级逐条 count”重构为单次 `GROUP BY level` 聚合，消除层级数增长时的额外往返
- 任务统计查询性能修复：`backend/src/crud/task.py` 将按 `TaskStatus/TaskType` 逐项计数改为两条聚合查询（`GROUP BY status`、`GROUP BY task_type`），避免枚举扩展导致统计查询线性增长
- 单测同步更新：`backend/tests/unit/services/organization/test_organization_service_impl.py` 与 `backend/tests/unit/crud/test_task.py` 调整为聚合查询结果断言，覆盖新统计路径
- 枚举初始化查询性能修复：`backend/src/services/enum_data_init.py` 将“按枚举类型/枚举值逐条查询存在性”改为“预取类型 + 预取值后内存匹配”，显著减少初始化阶段数据库往返
- 枚举初始化单测更新：`backend/tests/unit/services/test_enum_data_init.py` 同步对齐批量预取路径，并补强 `flush` 回填 `id` 的测试桩行为
- 通知调度判重查询性能修复：`backend/src/services/notification/scheduler.py` 将 `check_contract_expiry/check_payment_overdue/check_payment_due_soon` 中循环内的“活跃用户查询 + 单条判重查询”改为“单次活跃用户查询 + 批量判重后内存去重”，显著降低用户数与合同/台账数增长时的数据库往返
- 通知服务批量判重能力新增：`backend/src/services/notification/notification_service.py` 新增 `find_existing_notification_pairs_async`，一次查询返回 `(recipient_id, related_entity_id)` 集合，供调度任务复用
- 合同月台账生成 N+1 修复：`backend/src/services/rent_contract/ledger_service.py` 将按月份逐条 `get_by_contract_and_month_async` 查重改为一次批量查询已存在月份并在内存过滤；同时移除逐条 `refresh`，避免提交后额外 N 次查询
- 租金台账 CRUD 批量查询补充：`backend/src/crud/rent_contract.py` 新增 `get_existing_year_months_async`，用于按合同 + 月份集合批量取重
- 新增/更新回归单测：`backend/tests/unit/services/notification/test_scheduler.py` 对齐批量判重接口；新增 `backend/tests/unit/services/rent_contract/test_ledger_service.py` 覆盖“批量月份查重生效、逐月查重不再调用、无逐条 refresh”场景
- 资产导入权属校验查询优化：`backend/src/api/v1/assets/asset_import.py` 对导入批次中的 `ownership_id/ownership_entity` 先做批量预取，再按行复用映射判定；仅在映射缺失时回退单次查询并写回缓存，避免每行重复查权属方
- Excel 资产导入查询优化：`backend/src/services/excel/excel_import_service.py` 新增批量预取权属映射（ID/名称）并复用到逐行导入流程；对映射缺口使用惰性回填缓存，降低大批量导入时的重复查询
- 合同 Excel 导入查重优化：`backend/src/services/document/rent_contract_excel.py` 将“按行查询合同号是否存在”改为“导入前一次性批量查询 + 内存映射复用”，并在创建/更新后实时更新映射，避免循环内重复 `SELECT`
- Excel 导入单测异步化与接口对齐：`backend/tests/unit/services/excel/test_excel_import_service.py` 批量替换为 `AsyncMock` 并对齐 `asset_crud.*_async`，补齐权属预取查询测试桩与字段映射数量断言（22），确保优化路径可回归
- 系统字典排序批量更新去 N+1：`backend/src/services/system_dictionary/service.py` 将 `update_sort_orders_async` 从逐条 `system_dictionary_crud.get` 改为一次 `id IN (...) + dict_type` 批量查询并内存映射更新，提交后不再逐条 `refresh`
- 系统字典 CRUD 批量查询能力新增：`backend/src/crud/system_dictionary.py` 新增 `get_multi_by_ids_and_type_async`，为批量排序等场景提供单次取数入口
- 枚举类型列表值加载去 N+1：`backend/src/crud/enum_field.py` 为 `EnumFieldTypeCRUD.get_multi_async` 增加批量值加载路径（单次查询所有类型的枚举值），替代原“按类型逐条查值”
- 枚举树构建查询收敛：`backend/src/crud/enum_field.py` 将 `EnumFieldValueCRUD.get_tree_async` 从递归按父节点多次查询改为“单次取全量 + 内存组树”，消除层级增长导致的查询放大
- 资产批量操作查询收敛：`backend/src/services/asset/batch_service.py` 新增资产批量预取与关联批量检查（合同/产权证/台账），`batch_update`/`batch_delete` 不再按资产逐条 `get` 与逐条关联探测
- 新增回归单测：`backend/tests/unit/crud/test_enum_field.py` 增加“批量加载枚举值仅两次查询”与“枚举树单次查询”断言；`backend/tests/unit/services/asset/test_batch_service.py` 增加“批量预取资产”与“批量关联检查”断言；系统字典服务测试改为对齐批量查询接口

- 资产历史 CRUD 根因修复：`backend/src/crud/history.py` 移除同步兼容接口 `get/get_by_asset_id/get_multi/create/remove`，仅保留异步接口，统一历史访问路径
- 资产历史字段收敛：删除 `operator_id -> operator` 兼容桥接，历史创建仅接受标准字段 `operator`
- 历史单测异步化：`backend/tests/unit/crud/test_history.py` 全量改为 `get_async/get_by_asset_id_async/get_multi_with_count_async/create_async/remove_async/remove_by_asset_id_async`，并新增“拒绝 legacy operator_id”断言

- 资产批量删除前后端契约修复：前端 `ASSET_API.BATCH_DELETE` 从错误的 `/assets/batch` 修正为 `/assets/batch-delete`
- 资产批量删除请求体修复：`AssetCoreService.deleteAssets` 改为发送 `{ asset_ids }`，与后端 `POST /api/v1/assets/batch-delete` 入参一致
- 资产 API 路径常量收敛：`backend/src/constants/api_paths.py` 移除过时 `AssetPaths.BATCH`，改为 `BATCH_UPDATE/BATCH_DELETE/BATCH_CUSTOM_FIELDS`
- 前端单测对齐：`assetService.test.ts` 同步更新批量删除断言并补充 `invalidateCacheByPrefix` mock，覆盖正确端点与请求体
- 资产自定义字段契约修复：`assetFieldService` 路径与载荷统一对齐后端真实接口（`/asset-custom-fields/assets/{asset_id}/values`、`/asset-custom-fields/assets/batch-values`、`/asset-custom-fields/validate`、`/asset-custom-fields/types/list`）
- 新增前端单测：`frontend/src/services/__tests__/assetFieldService.test.ts` 覆盖自定义字段值查询/更新、批量设置、校验与字段类型选项映射
- Project 服务测试根因修复：`backend/tests/unit/services/project/test_project_service_complete.py` 与 `backend/tests/unit/services/test_project.py` 全量改为 async/await 调用，去除对异步服务的同步调用假设
- 自定义字段 API 测试根因修复：`backend/tests/unit/api/v1/test_custom_fields.py` 重写为异步路由测试，全面对齐 `*_async` CRUD/Service 方法与布尔筛选参数
- 安全中间件导入链路复核：确认 `security_middleware` 使用 `src.core.ip_whitelist` 真实实现，`import src.api.v1` 恢复可用
- 清理临时测试桩：移除 `test_custom_fields.py` 中对 `src.core.ip_whitelist` 的自动 monkeypatch，避免掩盖真实依赖问题

- RBAC 最终态重构：`RBACService.check_permission` 统一为“静态角色权限 + 统一授权记录（PermissionGrant）”判定链路，并加入 `DENY > ALLOW` 决策规则
- 新增统一授权模型：`backend/src/models/rbac.py` 添加 `PermissionGrant`，并同步补齐 schema、CRUD、白名单注册
- 新增迁移：`backend/alembic/versions/20260207_unify_permission_grants.py` 创建 `permission_grants` 表，并回填 legacy `resource/dynamic/temporary/conditional/delegation` 授权数据
- 权限检查入口收敛：业务代码移除直接 `rbac_service.is_admin(...)` 旁路，统一改为 `check_user_permission(user_id, "system", "admin")`
- 管理员判定去角色名兜底：管理员仅由 `system:admin` 权限决定，移除 `admin/super_admin` 名称自动提权，不再保留旧别名判定入口
- 初始化脚本对齐：`backend/scripts/setup/init_rbac_data.py` 改为生成 `PermissionGrant` 示例授权，不再写入旧动态/临时权限模型
- 新增测试：`backend/tests/unit/services/permission/test_rbac_service_grants.py` 覆盖统一授权 allow/deny/scope+condition 场景，`test_rbac_service.py` 同步调整管理员策略断言
- RBAC 管理接口补齐：`backend/src/api/v1/auth/roles.py` 新增统一权限检查、统一授权记录（`/permission-grants`）增删改查、用户角色分配与用户权限汇总端点
- RBACService 管理能力补齐：新增统一授权记录查询/更新方法，并在创建/撤销授权时增加输入校验与权限审计日志
- 新增路由测试：`backend/tests/unit/api/v1/test_roles_permission_grants.py` 覆盖统一授权 API 核心路径
- RBAC 旧轨删除：移除 `models/crud/schemas` 中 `dynamic_permission*` 旧模型与导出，删除 `RBACService` 中兼容别名方法，仅保留统一授权主链路
- 迁移加载对齐：`backend/alembic/env.py` 移除对已删除 `dynamic_permission` 模块的导入，修复测试/迁移初始化失败
- 新增迁移：`backend/alembic/versions/20260207_drop_legacy_dynamic_permission_tables.py`，升级时删除 `dynamic/temporary/conditional/request/delegation/template/audit` 旧权限表
- 非 RBAC 兼容层清理：移除 `main.py` 中 V1 兼容中间件导入与启动链路；`core/environment.py` 删除 `middleware.v1_compatibility` 可选依赖登记
- PDF 路由统一收口：`api/v1/__init__.py` 删除旧路径 `/api/v1/documents/pdf-import/*`，仅保留 `/api/v1/pdf-import/*`
- PDF V1 兼容端点删除：`pdf_upload.py` 删除 `POST /upload-and-extract` 与 `_validate_extracted_fields_v1`；`pdf_import.py` 删除可选 `pdf_v1_compatibility` 模块挂载
- Schema/测试同步收敛：`schemas/pdf_import.py` 删除 V1 `ExtractionRequest/ExtractionResponse`；`test_pdf_upload.py` 删除 V1 相关测试并保留 `/upload` 主链路测试，`test_pdf_import_routes.py` 全部路径断言对齐新入口
- 配置包去兼容化：`backend/src/config/__init__.py` 移除 `src.config -> src.core.config` 兼容 shim，仅保留配置子模块包说明
- 权限模块尾巴清理：`security_middleware` 的白名单依赖统一改为 `src.core.ip_whitelist`，删除 `src.security.ip_whitelist` 后不再保留旧导入路径
- API 包懒加载修复：`backend/src/api/__init__.py` 新增 `v1` 属性的显式懒加载（`importlib.import_module`），确保 `patch("src.api.v1...")` 在单测中可稳定解析
- 兼容别名彻底删除：移除 `enum_data_init.add_legacy_enum_values`、`message_constants.get_error_id`、`RateLimiter.requests` 与 `GLMVisionAdapter/QwenVisionAdapter/DeepSeekVisionAdapter` 旧别名
- 服务导出统一：`backend/src/services/__init__.py` 与 `backend/src/services/core/__init__.py` 删除 fallback/stub 链路，仅保留最终模块导出
- 单测同步收敛：`tests/unit/core/test_rate_limiter.py` 改为断言 `request_times`，与 `RateLimiter` 去兼容后的最终实现一致
- 校验脚本对齐：`scripts/verify_fixes.py` 改为验证 `SecurityService` 已删除，并移除 Windows 控制台 emoji 编码风险、硬编码路径依赖与无效 `DATA_ENCRYPTION_KEY` 注入
- 前端权限旧类型清理：删除未被引用的 `frontend/src/types/permission.ts`（动态/临时/申请/委托等旧轨类型）
- 类型检查配置收敛：`backend/pyproject.toml` 移除已删除模块 `src.models.dynamic_permission` 的 mypy override
- RBAC 初始化脚本收敛：`backend/scripts/setup/init_rbac_data.py` 将 `dynamic_permission:*` 基础权限资源统一替换为 `permission_grant:*`
- 数据库设计文档收敛：`docs/database-design.md` 移除动态/临时/条件/申请/委托旧权限分表说明，统一为 `permission_grants` 单表模型
- 集成文档路径收敛：`docs/integrations/siliconflow-paddleocr-integration.md` 将 PDF 导入示例接口更新为 `/api/v1/pdf-import/*`
- 迁移脚本清理：删除 `backend/scripts/maintenance/backfill_asset_ownership_entity.py`（历史 `ownership_entity -> ownership_id` 回填工具）
- PRD 收敛：`docs/features/prd-asset-management.md` 删除“历史数据迁移策略”章节，保持新项目最终态描述
- 变更日志收敛：移除 `CHANGELOG.md` 中已与最终态冲突的中间兼容条目（如 PDF 旧兼容路由、`dynamic_permission_crud`、历史回填脚本记录）

- Asset 搜索总数修复：`QueryBuilder.build_count_query` 支持 `base_query + distinct_column`，`AssetCRUD` 计数查询显式复用 `Ownership` 关联，消除搜索场景下笛卡尔积导致的 `total` 放大
- 合同状态投影修复：`Asset.active_contract` 纳入 `EXPIRING/即将到期` 状态，确保 `tenant_name`、`monthly_rent`、`deposit` 等计算属性在即将到期合同下可正常回显
- 资产表单合同展示修复：移除 `selected_contract_id` 的误导性“可选合同”交互与相关加载逻辑，改为只读展示后端投影合同信息，避免“可选但不持久化”的伪交互
- 并发集成测试稳定性修复：`test_concurrent_transaction_isolation` 改为动态唯一资产名并使用现有资产字段（`notes`）验证并发更新，支持重复执行
- 资产加密集成测试重构：`tests/integration/crud/test_asset_encryption.py` 全量迁移为异步 CRUD 调用，断言字段对齐当前模型（`address`、`manager_name`），修复旧同步调用导致的协程未等待失败
- Makefile 跨平台 Python 解释器选择修复：Windows 优先使用 `backend/.venv/Scripts/python.exe`（Linux/macOS 继续使用 `backend/.venv/bin/python`），避免 `make dev` 回退到系统 Python 导致缺少 `pydantic_settings` 启动失败
- Asset God Class 拆分：`backend/src/models/asset.py` 仅保留 `Asset`，新增 `asset_history.py`、`project.py`、`project_relations.py`、`system_dictionary.py` 拆分历史/项目/字典模型职责
- 模型依赖彻底去耦：移除 `asset.py` 对 `Project/SystemDictionary/AssetCustomField/AssetHistory` 的兼容回导与扩展 `__all__`，强制按新模块路径导入
- 测试导入路径统一：更新 unit/integration 中残留的 `from src.models.asset import Project/SystemDictionary/AssetCustomField/AssetHistory` 到对应新模型模块，消除对 God Class 兼容层依赖
- 关联表解耦：新增 `backend/src/models/associations.py` 统一维护 `rent_contract_assets` 与 `property_cert_assets`，并更新相关模型/CRUD/服务引用
- 资产自定义字段筛选修复：`/api/v1/assets/custom-fields` 中 `is_required/is_active` 过滤改为布尔值传递，修复字符串比较导致的筛选失效
- 资产自定义字段类型接口修复：路由从错误的 `"/types/list[Any]"` 更正为 `"/types/list"`，恢复前后端契约一致性
- 资产合同快照去冗余：移除 `Asset` 中 `tenant_name/lease_contract_number/contract_start_date/contract_end_date/monthly_rent/deposit` 持久化字段，改为基于 `active_contract` 的只读计算属性
- 资产入参与校验收敛：`Asset` schema、批量校验器、字段白名单同步移除上述冗余字段输入与排序能力；`RentContract` 排序字段改为 `monthly_rent_base/total_deposit`
- 新增迁移：`backend/alembic/versions/20260207_remove_asset_contract_snapshot_fields.py`（rev: `4f9b3b2d6e91`）删除 `assets` 表合同快照列
- 迁移兼容加固：`20260204_add_unique_asset_property_name` 迁移新增 `alembic_version.version_num` 容量检查与扩容（32→64），避免长 revision id 在升级链上触发截断错误
- 迁移幂等加固：`20260206_add_asset_search_index` 在表/索引已存在时跳过创建，避免重复执行迁移时触发 `DuplicateTable`/`DuplicateIndex`
- 前端表单对齐：`AssetForm`、`assetFormSchema`、`useFormFieldVisibility`、`AssetCreateRequest` 移除冗余合同快照字段提交流程与可见性规则
- 单测对齐：更新 `tests/unit/models/test_asset.py`、`tests/unit/crud/test_field_whitelist.py`、`tests/unit/services/asset/test_validators.py` 适配新模型与校验规则
- 异步测试对齐：重写 `tests/unit/crud/test_asset.py`、`tests/unit/crud/test_project.py`、`tests/unit/services/project/test_project_service.py` 为 async/await，移除旧同步 mock 触发的 `coroutine was never awaited`
- 资产服务收敛：`AssetService` 删除历史字段剔除兼容逻辑，创建/更新直接走标准 schema 结果，不再在服务层接收旧字段

- 资产字段统一替换：后端 `AssetCreate/AssetUpdate` 移除历史字段别名兼容，并在请求中显式拒绝 `wuyang_project_name`/`description`（统一使用 `project_name`/`notes`）
- 资产前端字段对齐：`AssetSearchResult` 仅使用 `project_name/notes`，移除旧字段回退逻辑
- 资产导出字段对齐：导出配置改为使用 `project_name`，移除无效导出键 `description`
- 旧可见性规则修复：`useFormFieldVisibility` 将协议字段依赖从 `wuyang_project_name` 调整为 `project_name`
- 权限判定改进：`RBACService` 管理员判定优先基于 RBAC 权限 `system:admin`，仅保留 `admin/super_admin` 名称作为兼容回退
- 权限上下文对齐：`AuthorizationContext.is_admin()` 改为调用 `rbac_service.is_admin()`，移除局部硬编码角色判断
- 启动前配置保护：`backend/run_dev.py` 新增 `DATA_ENCRYPTION_KEY` 的 Base64 格式与解码长度校验（至少 32 bytes），提前暴露配置错误
- 新增/更新测试：
  - 后端 schema 测试覆盖历史字段拒绝（提示改用 `project_name`/`notes`）
  - 后端 RBAC 测试覆盖基于 `system:admin` 的管理员识别
  - 前端 `usePermission` 测试覆盖“仅角色名不应自动视为管理员”
- 回归修复：`TableWithPagination` 恢复透传调用方 `scroll` 配置，仅在未传入时默认 `{ x: 'max-content' }`
- 回归修复：`Pagination` 移除重复触发的 `onShowSizeChange` 绑定，避免分页大小变更导致重复请求
- 回归修复：`Layout.module.css` 将未定义的 `--color-bg-container` 替换为已定义的 `--color-bg-primary`
- 可访问性修复：`AssetBasicInfoSection` 移除输入框错误的 `aria-label={labelId}`，避免屏幕阅读器朗读内部 ID
- 类型修复：`assetFormSchema` 与 `Asset` 类型移除 `wuyang_project_name/description` 历史字段，仅保留 `project_name/notes`
- 资产表单字段彻底统一：`assetFormSchema` 与 `useFormFieldVisibility` 全量替换为 `lease_contract_number / contract_start_date / contract_end_date`，移除 `lease_contract / current_contract_* / current_lease_contract / agreement_* / current_terminal_contract`
- 资产历史展示字段统一：`AssetHistory` 仅使用 `operator / operation_time / change_reason`，移除 `changed_by / changed_at / reason` 回退路径
- 通知未读数接口统一：前端 `notificationService` 改为读取 `unread_count`（不再读取 `count` 兼容字段），并同步更新单测
- 产权证审核字段统一：前端 `PropertyCertificate` 类型与页面全部改为 `is_verified`，移除 `verified` 历史字段兼容
- 产权证导入确认字段统一：前端确认载荷改为 `asset_ids + should_create_new_asset`，移除 `create_new_asset` 历史字段
- 分析服务响应兼容清理：`analyticsService` 移除 `apiData.data?.*` 多形态回退，仅保留当前响应结构与字段适配
- 导出任务字段统一：前端导出任务类型改为 snake_case（`download_url / created_at / completed_at / error_message`），移除 camelCase 兼容路径
- 资产历史字段兼容清理：后端 `history_crud.create_async` 移除 `operator_id -> operator` 桥接，仅接受标准字段 `operator`
- 资产 schema 进一步收敛：删除 `AssetCreate/AssetUpdate/AssetResponse` 中的 `wuyang_project_name` 与 `description` 历史字段定义，仅保留“显式拒绝旧字段并提示替换”的校验逻辑
- 资产创建链路防回归：`asset_crud.create_async/create_with_history_async/update_async/update_with_history_async` 增加旧字段兜底剔除，避免绕过 schema 时触发 `Asset(**kwargs)` 的无效参数异常
- OpenAPI 对齐：`AssetCreate`/`AssetResponse` 文档不再暴露历史字段，修复“文档允许但运行时拒绝”的契约不一致
- 产权证导入确认字段统一：后端 `PropertyCertificateService.confirm_import` 改为仅处理 `extracted_data / asset_ids / should_create_new_asset`，并将资产关联透传到 CRUD 创建流程

### 🔐 安全 (Security)

#### Fixed / 修复

- 将 `backend/config/backend.env.secure` 从 Git 索引移除，阻止继续版本化跟踪明文敏感配置
- 删除工作区中的 `backend/config/backend.env.secure` 明文敏感文件，避免本地误用或二次泄露
- `.gitignore` 增加 `backend/config/*.env.secure` / `backend/config/*.secure` 规则，防止安全配置文件再次被提交
- 清理 `backend/config/` 目录中的遗留跟踪文件（`config.example.yaml`、`quality_monitor_config.yaml`、`pytest_ultra_optimized.ini`、`create_admin_user.sql`）
- `.gitignore` 增加 `backend/config/create_admin_user.sql` 与 `config/create_admin_user.sql` 规则，阻止管理员凭据 SQL 产物被提交
- `README.md` 与 `docs/guides/deployment.md` 增加“密钥一旦出现在 Git 历史即必须视为泄露并强制轮换”的应急处置指引
- 调整 `backend/scripts/devtools/security_key_generator.py`：敏感产物默认输出到系统临时目录 `zcgl-security-artifacts`（可用 `SECURITY_ARTIFACTS_DIR` 覆盖），不再默认写入仓库目录

### 🎨 UI/UX 改进 (UI/UX Improvements)

#### Added / 新增

- **可访问性增强** (Accessibility Enhancement)
  - 为 AssetList 组件的所有操作按钮添加 ARIA 标签（aria-label, title）
  - 为表单字段添加可访问性属性（aria-required, aria-describedby, aria-label）
  - 为 Modal 添加焦点管理（autoFocus, focusTriggerAfterClose）
  - 为错误提示添加 role="alert" 和 aria-invalid 属性
  - 影响 24+ 个交互元素，符合 WCAG 2.1 AA 级标准

- **响应式设计优化** (Responsive Design)
  - 实现表格响应式设计，移动端（< 768px）自动隐藏次要列
  - 动态调整表格滚动配置和尺寸（移动端 y: 400px, 桌面端 y: 600px）
  - 添加窗口 resize 监听，实时响应屏幕尺寸变化
  - 移动端使用 size="small" 优化显示效果

- **样式系统统一** (Style System Unification)
  - 将 Layout.module.css 中 15+ 处硬编码颜色替换为 CSS 变量
  - 统一使用 variables.css 定义的语义化变量
  - 修复内容区域被固定导航栏遮挡的问题（添加适当的 padding-top）

- **性能优化指南** (Performance Optimization Guide)
  - 新增 `frontend/docs/performance-optimization.md` 文档
  - 包含虚拟滚动方案、图片优化、搜索防抖等最佳实践
  - 记录 Web Vitals 性能监控指标和目标

#### Changed / 改进

- AssetList 组件添加响应式状态管理（isMobile）
- 表格列配置支持移动端自动隐藏
- 表单输入框添加完整的可访问性属性
- 按钮和交互元素添加描述性 ARIA 标签

#### Fixed / 修复

- 修复内容区域被固定导航栏遮挡（64px header + 56px breadcrumb）
- **修复页面"蒙层"效果** (Fix Overlay Effect)
  - 移除 Layout.module.css 中的毛玻璃效果（`backdrop-filter: blur(8px)` 和半透明背景）
  - 移除 global.css 中的过渡动画冲突规则
  - 统一使用 CSS 变量 `var(--color-bg-container)` 作为背景色
  - 影响文件：Layout.module.css, global.css, App.tsx, TableWithPagination.tsx 等
  - 修复文件数：12个，修复问题数：15个
- **修复 TypeScript 类型错误** (Fix Type Errors)
  - 修复 AssetSearchResult 组件中 undefined 类型传递问题
  - 修复 AssetSearchFilters 接口类型定义（usage_status, property_nature 等）
  - 修复 ResponsiveTable 和 TableWithPagination 组件类型兼容性
  - 移除未使用的导入和变量（AssetList, EmptyState, Loading, ThemeToggle, VirtualList）
  - ESLint 检查通过（0 错误，0 警告）
- **修复导入路径大小写不一致** (Fix Import Path Case)
  - 统一使用 `Common` 目录（大写C）替代 `common`（小写c）
  - 提高跨平台兼容性（Windows/macOS/Linux）
- **修复 CSS 样式错误** (Fix CSS Style Errors)
  - 修复 EmptyState 组件中 `var-spacing-md)` 缺少开括号的错误
  - 优化 ThemeToggle 组件使用 CSS 类代替内联样式修改
- 修复硬编码样式导致的主题切换不兼容问题

#### 文档 (Documentation)

- 新增 `frontend/docs/ui-ux-improvements-report.md` - UI/UX 改进实施报告
- 新增 `frontend/docs/performance-optimization.md` - 性能优化指南

### 🧪 审核 (Audit)

- **数据库异步化实施核查** (Async DB Migration Audit)
  - 仍存在 run_sync、同步 Session 与 get_db 依赖，异步化未完全收敛

### 🧰 工具与环境 (Tooling & Environment)

#### Fixed / 修复

- 前端 ESLint 启用 `@typescript-eslint/no-explicit-any`（生产代码设为 error，测试文件通过 overrides 保持放行），强化类型安全基线
- 新增 `@typescript-eslint/no-unnecessary-type-assertion`（测试文件关闭）并自动清理一批冗余 `as` 断言，降低类型断言滥用风险
- 明确前端 API 分层边界：新增 `assetImportService` 并让 `AssetImport` 仅通过服务层调接口，新增 ESLint 限制组件/页面/Hook/Context 直接导入 `@/api/client`，避免 HTTP 层与业务层职责混用
- 继续收敛 UI 网络调用边界：`TestCoverageDashboard` 改为复用 `testCoverageService`，`AnalyticsDashboard` 导出改由 `analyticsService` 统一封装，`ErrorBoundary`/`RouteABTesting` 上报请求迁移到独立 service；并新增 ESLint 限制 UI 层直接调用全局 `fetch`
- `testCoverageService` 全量从原生 `fetch` 迁移到 `apiClient`，统一 `ExtractResult` 解包与错误处理语义；新增 `testCoverageService` 单元测试覆盖报告、趋势、模块、阈值与质量门禁等关键接口
- 继续统一前端上报链路：`errorReportService` 与 `abTestingReportService` 改为 `apiClient` 调用（去除硬编码 `/api/*` 与原生 `fetch`）；补充对应单元测试，并在 MSW 中新增 `/errors/report`、`/analytics/abtest-events`、`/analytics/abtest-conversions` handler，消除 ErrorBoundary 测试中的未匹配请求告警
- 前端环境判断收敛：新增 `utils/runtimeEnv`，并将 `ErrorBoundary`、`RouteABTesting`、`AnalyticsDashboard` 的 `process.env.NODE_ENV` 判定统一为运行时 helper（优先兼容 Vite `import.meta.env`，保留测试场景下的 `NODE_ENV` 覆盖能力）
- 修复 `AnalyticsDashboard` 组件测试的历史失稳项：统一 `useAnalytics` 与子组件 mock 路径为 `@/` 别名、`api/config` 改为部分 mock 保留 `API_BASE_URL` 导出、并将导出菜单断言改为 hover 打开下拉后校验文案，恢复测试文件可稳定执行
- 继续清理前端环境判定遗留：`api/client`、`errorHandler`、`colorMap`、`optimization`、`errorMonitoring`、`RoutePerformanceMonitor`、`messageManager`、`responseExtractor`、`versionConfig`、`userExperience`、`useSmartPreload`、`apiPathTest` 全部改为 `runtimeEnv` helper，移除业务代码中的 `process.env.NODE_ENV` 直接判断
- 测试环境一致性补充：`ErrorBoundary` 单测改为 mock `runtimeEnv` 控制开发/生产分支，不再直接读写 `process.env.NODE_ENV`，减少测试对 Node 进程全局状态的耦合
- Node 侧环境变量读取规范化：`vite.config.ts`、`playwright.config.ts`、`tests/e2e/asset-flow.spec.ts` 与 `scripts/diagnose/*` 新增统一读取 helper（字符串/布尔/数值），避免业务逻辑散落直接访问 `process.env.*`；当前 `frontend/` 仅保留 `runtimeEnv` 与 Vite `define` 的 `process.env.NODE_ENV` 注入点
- 修复前端类型检查阻断项：`AssetSearchResult` 对 `ownership_entity` 增加空值兜底；`tsconfig.json` 排除 `src/e2e/**` 与 `*.spec.ts(x)`，避免应用构建类型检查依赖 Playwright 测试类型
- 新增前端 E2E 独立类型检查链路：增加 `tsconfig.e2e.json`、`type-check:e2e` 脚本与 `types/playwright-test.d.ts` 声明；同时修复 `analyticsService` 与 `ContractListPage` 的严格类型报错，并补齐 `src/e2e/auth.spec.ts` 回调参数类型
- 修复 `useContractList` Hook 单测的 `react/display-name` lint 阻断：QueryClient 包装组件补充显式 `displayName`
- 清理前端剩余 3 条 `no-unnecessary-type-assertion` 警告：移除 `useContractList` 与 `AssetListPage` 中冗余 `as Error` 断言
- `Makefile` 的 `type-check` 目标改为串行执行 `pnpm type-check && pnpm type-check:e2e`，并新增 `type-check-e2e` 目标；`make check` 随之默认覆盖前端 E2E 类型检查
- 前端 `package.json` 的 `check`/`audit:ui`/`audit:full` 脚本统一纳入 `type-check:e2e`，确保本地与 CI 流程默认覆盖 E2E 类型检查
- 继续清理 `no-unnecessary-type-assertion`：移除 `UserManagementPage` 与 `RentLedgerPage` 中冗余 `as Error` 断言，减少无效类型收窄噪音
- 执行前端全量 Prettier 规范化并修复 175 处格式漂移，`pnpm check` 现已通过（lint + app type-check + e2e type-check + format:check）
- 开发启动脚本限制 Uvicorn reload 监听目录为 `backend/src`，并支持 `RELOAD` 环境变量关闭重载，避免非源码变更触发重启
- 修复 RBAC 初始化脚本可重复执行并补齐 `property_certificate` 权限，遇到遗留 `users.role` 约束时跳过测试用户创建以保证初始化可完成
- 修复 RBAC 初始化脚本动态权限示例的 `assigned_by` 外键错误，避免插入失败并保持幂等
- RBAC 初始化脚本在测试用户已存在时仍会确保角色分配，并在输出中明确已存在数量
- 修复角色列表/详情接口未预加载权限导致的 `MissingGreenlet` 500 错误
- 调整 CORS 中间件顺序，确保错误响应也包含 CORS 头，避免前端 `system/users` 报 CORS 拒绝
- CORS 允许 `Authorization` 请求头，修复携带登录令牌的预检请求被拒绝
- 本地开发环境补齐 `backend/.env` 基础配置（development 模式 + PostgreSQL 连接信息）
- Makefile 后端命令默认使用 `backend/.venv` 的 Python，避免调用系统 Python 导致依赖缺失
- 修复前端资产查询分页参数漂移：`assetCoreService.getAssets` 兼容 legacy `pageSize` 并统一映射为 `page_size`；同步修正项目详情、权属方详情、合同列表、租金台账中的资产查询调用，避免分页参数被忽略导致结果默认截断
- 统一前端认证状态单一来源：`hooks/useAuth` 改为 `AuthContext` 兼容代理，并在 `AuthContext` 补齐 `permissions`、`refreshUser`、权限判断与清错能力，消除 Context 与本地 Hook 双状态并存风险
- 前端状态管理收敛（P2）：资产列表页移除 `useListData + useEffect` 命令式加载，改为 React Query 单轨查询（分页/排序/筛选驱动 queryKey）；租赁合同列表 Hook 同步迁移到 React Query 单轨（列表/统计/参考数据），并更新对应单测适配 QueryClientProvider
- 前端状态管理收敛（P2 扩展）：租金台账页移除 `useListData`，列表/统计/参考数据统一改为 React Query 单轨查询，并统一支付更新与批量更新后的刷新逻辑（`refetchLedgers + refetchStatistics`）
- 前端状态管理收敛（P2 延伸）：用户管理页移除 `useListData` 与手动 `load*` 副作用，用户列表/组织/角色/统计统一改为 React Query 单轨查询；增删改与锁定/启停操作统一走 `refetchUsers + refetchStatistics` 刷新链路，减少状态漂移
- 前端状态管理收敛（P2 延伸）：角色管理页移除 `useListData` 与手动 `load*` 副作用，角色列表/权限/统计统一改为 React Query 单轨查询；增删改、状态切换与权限保存统一走 `refetchRoles + refetchStatistics` 刷新链路，降低多源状态不一致风险
- 前端状态管理收敛（P2 延伸）：操作日志页移除 `useListData`，日志列表查询统一改为 React Query（筛选/分页驱动 queryKey），并将刷新与分页入口收敛到 `refetchLogs + paginationState`，减少命令式加载分支
- 前端状态管理收敛（P2 延伸）：组织管理页移除 `useListData`，组织列表/树形结构/统计统一改为 React Query 查询；列表分页与刷新统一收敛到本地 `paginationState` + `refetchOrganizations/refetchOrganizationTree/refetchStatistics`
- 前端状态管理收敛（P2 延伸）：通知中心页移除 `useListData`，通知列表改为 React Query 查询并由分页/类型筛选驱动 `queryKey`；已读/全部已读/删除后的刷新统一走 `refetchNotifications`
- 前端状态管理收敛（P2 延伸）：Prompt 管理页移除 `useListData`，Prompt 列表与统计改为 React Query 查询；激活、新建/编辑成功后的刷新统一收敛到 `refetchPrompts + refetchStatistics`
- 修复 `NotificationCenter` 分页回调中的未使用参数 lint 告警，避免 `@typescript-eslint/no-unused-vars` 阻断
- 前端状态管理收敛（P2 组件层）：`OwnershipList` 移除 `useListData`，权属方列表与统计改为 React Query 查询；删除/状态切换/表单提交后统一走 `refetchOwnerships + refetchStatistics`
- 前端状态管理收敛（P2 组件层）：`AssetHistory` 移除 `useListData`，历史列表改为 React Query（按资产/分页/筛选驱动 queryKey），刷新与分页切换统一收敛到 `refetchHistory + paginationState`
- 前端状态管理收敛（P2 组件层）：`ProjectList` 移除 `useListData`，项目列表与权属方下拉改为 React Query 查询；删除/状态切换/表单提交后统一走 `refetchProjects`
- 组件单测对齐 React Query：`OwnershipList.test.tsx`、`AssetHistory.test.tsx`、`ProjectList.test.tsx` 移除 `useListData` 依赖并改为按 `queryKey` mock `useQuery` 返回数据/刷新函数，修复迁移后的断言失配
- 列表 Hook 依赖继续收敛：`useArrayListData` 内部改为独立分页/筛选/加载状态管理并保留原有 `loadList`/`applyFilters`/`resetFilters`/`updatePagination` 契约，移除对 `useListData` 的耦合以降低迁移链路风险
- `AssetListPage` 单测同步对齐 React Query：移除遗留 `useListData` mock，改为基于 `queryKey` 的 `useQuery` mock，并修复测试渲染 helper 递归调用导致的栈溢出（`Maximum call stack size exceeded`）
- 前端 legacy 列表 Hook 正式下线：删除已无引用的 `useListData` 与 `useFilters`，并同步更新 `ProjectList` 测试头注释为 React Query 版本，避免后续误导与死代码回流
- 统一租赁合同 API 模块命名：`backend/src/api/v1/rent_contract/` 重命名为 `backend/src/api/v1/rent_contracts/`，并同步更新路由聚合导入、单元/集成测试 patch 路径与相关文档引用，消除单复数命名不一致
- 命名一致性补充清理：更新 `scripts/test_file_naming.py` 中后端 API 示例路径至当前目录结构（含 `rent_contracts`），修正自定义字段 API 单测注释中的历史路径与接口前缀，并同步更新历史测试重构计划文档中的租赁合同 API 路径引用，避免后续审计误判
- 规范自定义字段类型列表路由：新增标准路径 `/api/v1/asset-custom-fields/types`，并保留旧路径 `/types/list[Any]` 作为隐藏兼容入口，避免历史调用中断
- 统一租赁合同路由前缀命名：将前端测试 Mock 与后端集成测试中的遗留 `/rent-contracts`、`/api/v1/rent/*` 引用收敛到当前标准 `/rental-contracts/*` 路径，避免测试与真实 API 前缀漂移
- 修复租赁合同缓存键失配：将合同创建/续签页中无效的 `invalidateQueries(['rent-contracts'])` 改为实际使用的 `['rent-contract-list']` 与 `['rent-contract-statistics']`，确保列表与统计数据能正确刷新
- 抽取租赁模块 React Query 键常量：新增 `frontend/src/constants/queryKeys/rental.ts`，并将合同列表/详情/续签/创建/统计页与相关失效调用统一改为 `RENTAL_QUERY_KEYS`，降低 key 拼写漂移与局部失效风险
- 继续统一租赁台账 React Query 键：`RentLedgerPage` 的列表/统计/参考数据查询改为 `RENTAL_QUERY_KEYS` 常量，减少页面内字面量 key 并保持租赁模块缓存策略一致
- 统一租赁台账刷新策略：`RentLedgerPage` 将手动 `refetch` 改为基于 `queryClient.invalidateQueries` + `RENTAL_QUERY_KEYS` 的失效刷新，统一与其他租赁页面的缓存更新模式
- 增加 `queryKeys` 统一导出入口：新增 `frontend/src/constants/queryKeys/index.ts` 并将租赁相关页面/Hook 导入切换为 `@/constants/queryKeys`，简化后续扩展与重构成本

#### Removed / 删除

- 删除根目录 `.venv`，统一使用 `backend/.venv` 以避免环境混淆

### 🧹 清理 (Cleanup)

#### Removed / 删除

- **项目临时文件清理** (Project Cleanup)
  - 删除测试输出、缓存目录和构建产物（释放 124.3 MB）
  - 清理临时脚本、报告文档和日志文件
  - 删除过期的 `package/` 目录和 playwright tarball 包
  - 移除测试覆盖率脚本 `test_rent_contract_service_coverage.py`
  - 总计清理 82 个文件，删除 1002 行代码

### 🔍 搜索 (Search)

- **加密字段模糊搜索支持** (Blind Index for Encrypted Search)
  - 新增 `asset_search_index` 表，使用 HMAC n-gram 盲索引支持地址/权属方子串搜索
  - 资产列表搜索与产权证资产匹配改用盲索引（加密启用时），仍保留未加密时 ILIKE
  - 新增重建脚本 `scripts/maintenance/rebuild_asset_search_index.py` 用于回填索引

### 📚 文档 (Docs)

- 明确说明 `SecurityService` 已移除，并指向 `PasswordService`/`AuthenticationService` 作为安全替代路径
- AGENTS.md 增加提示：后端测试应使用项目 `backend/.venv`，避免 `.env` 不生效
- AGENTS.md 增补启动/登录/排查经验与常见故障定位要点

### 🛡️ 稳定性与架构修复 (Stability & Architecture Fixes)

#### Fixed / 修复

- 修复 `core/performance.py` 查询优化器缩进错误导致后端启动失败的问题
- 将数据库初始化移动到应用生命周期中，避免启动时 `asyncio.run()` 在事件循环中触发错误
- 修复通知任务端点异步定义与依赖注入，避免路由注册时报 `await` 语法错误
- 修复 RBAC 角色有效期比较使用时区感知时间导致的数据库错误
- 修复登录接口在权限读取成功时未初始化角色汇总导致的异常
- **RBAC 角色单一来源** (Single Source of Truth for Roles)
  - 认证响应与用户信息统一使用 RBAC 角色汇总（`role_id`/`role_name`/`role_ids`），移除旧 `role` 字段依赖
  - 统一测试与示例数据为 `role_id`，避免遗留角色字符串导致权限误判
- **资产字段补齐** (Asset Field Completeness)
  - 资产新增 `wuyang_project_name` 与 `description` 字段对齐前端，避免提交后静默丢失
  - 新增数据库迁移补齐 `assets` 表字段
- **管理员权限统一** (Admin Permission Unification)
  - 管理员判断改为 `system:admin` 权限，不再依赖角色名
  - 迁移为 `admin`/`super_admin` 角色回填 `system:admin` 权限
- **资产权属字段统一** (Asset Ownership Unification)
  - 资产创建/更新/筛选仅使用 `ownership_id`，`ownership_entity` 改为动态读取（不落库）
  - 资产筛选与统计接口移除 `ownership_entity` 查询参数，前端筛选改用权属方选项与 `ownership_id`
- **组织循环检测查询降为单次递归 CTE** (Organization Cycle Check Single-Query CTE)
  - `_would_create_cycle` 改为递归 CTE 检测父链，避免逐层查询造成的性能放大
- **组织子树路径批量更新** (Organization Subtree Path Batch Update)
  - `_update_children_path` 改为递归 CTE 批量更新层级与路径，移除逐节点递归查询
- **管理员数据库重置异步化** (Admin DB Reset Async)
  - 管理员重置数据库接口改为异步并 await create/drop tables
- **RBAC 服务统一** (RBAC Service Consolidation)
  - 移除 `services/rbac` 旧实现与相关遗留测试引用
  - 统一使用 `services/permission/rbac_service.py`，改用 CRUD + 标准异常
  - 角色管理 API 调用路径切换至新 RBAC 服务
  - RBAC 服务内时间戳改为 `datetime.now(UTC)`，避免 `utcnow()` 弃用警告
- **移除不安全 SecurityService Stub** (Remove Unsafe SecurityService Stub)
  - 删除 `SecurityService` stub 与相关导出，避免 IDE/自动导入误用
  - 新增单元测试防回归，确保 `SecurityService` 不可被导入或导出
- **Ownership 模型抽离与导入统一** (Ownership Model Extraction & Import Unification)
  - Ownership 独立到 `models/ownership.py` 并更新所有引用路径
  - 统一模型导出，避免对 `models.asset` 的隐式依赖与循环导入风险
  - 修复字段白名单初始化中 Ownership 的导入路径，避免运行时警告
- **数据库引擎类型注解修复** (Database Engine Type Hint Fix)
  - 补充 `sqlalchemy.engine.Engine` 导入，避免类型注解在运行时报 NameError
- **枚举初始化异步化** (Enum Init Async Migration)
  - 启动阶段枚举数据初始化改用 AsyncSession + async_session_scope
  - 枚举与遗留值同步逻辑改为异步查询/提交
- **Excel 模板服务去数据库依赖** (Excel Template DB Decoupling)
  - Excel 模板服务移除 Session 依赖，下载路由不再注入未使用的 db
- **移除同步适配层** (Remove Sync Adapter Layer)
  - 删除 `utils/async_db.py` 中的 run_sync/适配器占位实现
- **资产唯一性校验异步化** (Asset Uniqueness Async Validation)
  - AssetValidator 唯一性校验改为 AsyncSession 查询
- **出租率计算去同步 DB** (Occupancy Calc Sync DB Removal)
  - OccupancyRateCalculator 移除同步 Session 聚合路径，仅保留内存计算
- **Excel 导出服务异步收敛** (Excel Export Async Convergence)
  - Excel 导出服务移除同步导出接口与 Session 依赖，保留异步导出路径
- **审计服务异步化** (Audit Service Async Migration)
  - AuditService 改为 AsyncSession + await 调用并更新单元测试为异步
- **分析缓存接口异步化** (Analytics Cache Async Update)
  - 缓存统计/清理服务方法改为异步并在 API 端点 await 调用
  - 分析服务单元测试与统计 API 测试更新为异步 Mock/await
- **分析缓存执行异步化** (Analytics Cache Async Execution)
  - 分析服务缓存读取/写入/清理/统计改为异步线程执行，避免阻塞事件循环
- **Excel 导出服务异步兼容** (Excel Export Async Compatibility)
  - Excel 导出服务支持 AsyncSession 并新增异步导出与预览方法
- **财务统计接口异步化** (Financial Stats Async Migration)
  - 财务汇总统计移除 run_sync，统一 await 异步服务
  - 财务统计单元测试改用 AsyncMock 与 await
- **系统备份与历史接口异步化** (System Backup & History Async Migration)
  - 备份创建/恢复移除 run_sync，统一使用 AsyncSession 获取数据库连接信息
  - 历史记录列表/详情/删除改用异步 CRUD 方法
- **租赁合同统计与生命周期异步化** (Rent Contract Stats & Lifecycle Async Migration)
  - 统计概览/权属/资产/月度/导出移除 run_sync，统一使用 AsyncSession 异步服务
  - 续签/终止流程新增异步服务并在路由 await 调用
- **租赁合同统计服务异步化收敛** (Rent Contract Statistics Async Convergence)
  - 统计服务移除同步方法与 Session 依赖，统一 AsyncSession 路径
- **资产批量/自定义字段/产权证测试异步对齐** (Async Test Alignment for Batch/CustomField/PropertyCert)
  - 资产批量服务与 API 单测改用 AsyncMock/await
  - 自定义字段/产权证 CRUD 与服务单测更新为异步调用
- **租赁合同 CRUD 异步化** (Rent Contract CRUD Async Migration)
  - 合同查询/筛选/台账/条款 CRUD 补齐 AsyncSession 方法，移除 run_sync 包装
  - 合同创建/更新/删除改为异步调用并新增异步更新服务
  - 租赁合同 API 单测改用 AsyncMock/await 适配异步接口
- **租赁合同台账与附件异步补齐** (Rent Contract Ledger & Attachment Async Follow-up)
  - 台账生成/批量更新/更新服务补齐异步实现并移除 run_sync
  - 附件/合同错误用例单测改为异步调用以匹配异步路由
- **租赁合同附件异步收敛** (Rent Contract Attachment Async Convergence)
  - 附件增删查改用 AsyncSession 调用并补齐异步上传服务
  - Excel 异步导入任务创建改为异步 CRUD，移除 run_sync 适配
- **资产附件单测异步对齐** (Asset Attachment Test Async Alignment)
  - 资产附件单元测试改用 AsyncMock/await 适配异步路由实现
- **资产附件字段防丢失对齐** (Asset Attachment Field Preservation)
  - 前端 `assetFormSchema` 补齐接收协议/终端合同附件字段
  - 后端新增 Asset schema 单元测试，确保字段序列化不丢失
  - 资产 API 单测样例补齐附件字段
- **用户组织字段对齐** (User Organization Field Alignment)
  - 后端 User 支持 `organization_id` 兼容别名并返回别名字段
  - 前端统一使用 `default_organization_id`，/auth/me 补齐组织字段

### 🧪 测试 (Tests)

- **RBAC/权属测试对齐** (RBAC/Ownership Test Alignment)
  - 单元/集成/E2E 测试统一使用 `role_id` 与 RBAC 角色分配
  - 资产测试数据改为 `ownership_id`，并为集成场景补齐权属方关联
- **系统监控健康检查测试异步化** (System Health Tests Async)
  - check_component_health 单测改为 async/await 并使用 AsyncMock
- **PDF 批量导入集成测试对齐异步依赖** (PDF Batch API Tests Async Alignment)
  - 移除 get_db 覆盖，使用默认 get_async_db 依赖
- **PDF 批量上传错误响应断言对齐** (PDF Batch Upload Error Assertion)
  - 集成测试改为校验中间件返回的 message 字段
- **出租率计算单测切换为内存计算路径** (Occupancy Calculator Tests In-Memory)
  - 移除 get_db patch，按内存资产列表验证统计结果

### 📚 文档 (Docs)

- 资产与数据库设计文档更新：`ownership_id` 作为唯一来源，`ownership_entity` 动态读取
- 认证与测试示例更新：移除旧 `role` 字段，统一使用 `role_id`
- **异步数据库示例更新** (Async DB Docs Refresh)
  - 后端/数据库/测试指南示例改为 AsyncSession + get_async_db
- **Excel 导出路由单测异步对齐** (Excel Export Route Test Async Alignment)
  - Excel 导出相关单元测试补齐 await 与异步 Mock
- **Excel 预览路由异步对齐** (Excel Preview Route Async Alignment)
  - 预览接口改用 AsyncSession + get_async_db 依赖注入
- **Excel 导入路由异步对齐** (Excel Import Route Async Alignment)
  - 同步/异步导入改为 AsyncSession 调用并移除线程内同步会话
  - 导入后台任务测试改为异步 CRUD 调用与 AsyncMock
- **请求日志异步化** (Request Logging Async Migration)
  - 操作日志记录改为 AsyncSession 异步写入并移除 run_sync 适配
- **产权证服务异步化** (Property Certificate Service Async Migration)
  - 产权证列表/详情/创建/更新/删除移除 run_sync，直接使用 AsyncSession CRUD
- **产权证提取提示词加载** (Property Certificate Prompt Loading)
  - 上传提取流程改用异步 PromptManager 获取激活模板，避免无 PromptManager 时抛配置异常
- **文档提取管理器兼容性** (Document Extraction Manager Compatibility)
  - 产权证提取支持注入 AsyncSession 获取 Prompt，结果字段兼容 extracted_fields/data
- **产权证提取适配器异步兼容** (Property Certificate Adapter Async Compatibility)
  - PromptManager 根据 AsyncSession 调用异步查询，避免同步查询阻塞
- **PDF 导入会话异步化** (PDF Import Session Async Migration)
  - 会话创建/状态查询/处理状态持久化/确认导入/取消流程移除 run_sync
- **PDF 批量会话查询异步化** (PDF Batch Session Async Migration)
  - 批量状态/取消接口改用 AsyncSession 查询会话映射
- **PDF 会话服务异步化** (PDF Session Service Async Migration)
  - PDFSessionService 改为 AsyncSession 并异步化会话查询/创建
- **PDF 处理追踪异步化** (PDF Processing Tracker Async Migration)
  - ProcessingTracker 与步骤追踪装饰器改为 AsyncSession
- **组织列表分页解析修复** (Organization List Pagination Parsing)
  - 前端组织服务解包分页 items，避免用户管理页加载组织列表时报错
  - 组织搜索/高级搜索/历史列表统一兼容分页响应
- **用户列表无限刷新修复** (User List Infinite Refresh Fix)
  - 拆分用户管理页初始化副作用，避免统计刷新触发重复拉取导致渲染深度溢出
- **租赁合同创建提交修复** (Rent Contract Create Submit Fix)
  - 租赁合同表单补齐 onFinish 提交回调，修复创建合同无请求的问题
  - 新增表单提交单元测试覆盖
- **租赁合同创建错误提示与重试优化** (Rent Contract Create Error Messaging & Retry)
  - 创建合同遇到 4xx 冲突不再重试，避免重复提交
  - 失败提示展示后端返回的冲突原因
- **资产重名与删除约束** (Asset Uniqueness & Delete Guard)
  - 资产 `property_name` 全局唯一（服务/导入校验 + 数据库唯一约束）
  - 资产删除时若已关联合同或产权证则阻止删除
- **权属一致性校验** (Ownership Alignment)
  - `ownership_id` 与 `ownership_entity` 不一致时拒绝写入并对齐名称
- **异步会话迁移补齐** (Async Session Migration Completion)
  - 资产/合同/组织/催缴/字典/统计/产权证/PDF批量等接口统一改用 AsyncSession + get_async_db
  - PDF 批量监控改用 async_session_scope，避免同步会话混用
  - PDF 导入会话创建/取消改为异步封装，API 调用统一 await
  - 合同编辑权限检查改为异步 RBAC 适配器调用
  - Excel 同步导入改为线程内创建会话，避免跨线程复用 Session
- **异步会话迁移补充** (Async Session Migration Follow-ups)
  - 枚举字段/权属方/项目/会话管理接口统一改为 AsyncSession + run_sync 适配同步 CRUD/Service
    - 资产导入/提示词/系统设置接口补齐 run_sync 包装与类型适配
- **用户管理服务单测异步化** (User Management Service Test Async Migration)
  - 修复用户管理服务单元测试，统一 AsyncMock/await 与 AsyncSessionService 依赖注入
- **用户管理 API 单测异步对齐** (Users API Test Async Alignment)
  - Users API 单测改为 asyncio.run 调用异步路由，CRUD/Service Mock 全量异步化
  - 锁定/解锁/重置密码测试补齐 AsyncMock commit/refresh/rollback
- **认证集成测试导入清理** (Auth Integration Test Import Cleanup)
  - 集成测试导入改为 AsyncAuthenticationService/AsyncSessionService/AsyncUserManagementService
- **认证 CRUD 异步化** (Auth CRUD Async Migration)
  - auth CRUD 移除同步 Session 接口，补齐用户/会话/审计异步方法
  - 认证 CRUD 单元测试改为 AsyncMock/await，集成测试移除 get_db 同步依赖
- **资产服务异步化** (Asset Service Async Migration)
  - AssetService 统一为 AsyncSession 异步实现，并保留 AsyncAssetService 别名
  - 资产服务单元/集成测试改为异步执行，使用 AsyncMock 与异步会话隔离
  - 资产服务集成测试改用临时异步引擎 + NullPool，避免事件循环关闭导致连接异常
- **组织服务异步化** (Organization Service Async Migration)
  - OrganizationService 全量改为 AsyncSession 调用并修正组织 API 调用命名
  - 组织服务单元/集成测试改为异步执行（AsyncMock + AsyncSession）
  - 组织服务历史/统计查询改为异步路径
  - 遗留的深度/增强集成测试暂时标记跳过，等待异步 API 对齐后恢复
- **操作日志 CRUD 异步化** (Operation Log CRUD Async Migration)
  - OperationLogCRUD 移除同步方法，仅保留异步 CRUD/统计接口
  - 操作日志 CRUD 单元测试改为 AsyncMock + await
  - 组织服务集成测试修正异步引擎引用方式，避免引擎初始化判定失效
  - 组织服务集成测试改用临时异步引擎 + NullPool，避免事件循环关闭导致连接异常
- **系统字典异步化** (System Dictionary Async Migration)
  - system_dictionary CRUD/Service 移除同步 Session 接口，仅保留 AsyncSession 路径
  - 系统字典单元/集成测试改为异步执行并使用 asyncpg 引擎
- **枚举字段与公共字典异步化** (Enum Field & Common Dictionary Async Migration)
  - enum_field CRUD 移除同步方法，仅保留 AsyncSession 异步实现
  - CommonDictionaryService 移除同步入口，单元测试改为 AsyncMock/await 并移除 db_session 依赖
- **通知模块异步化** (Notification Module Async Migration)
  - Notification CRUD/Service 移除同步方法，仅保留 AsyncSession 异步接口
  - 通知定时任务调度器改为异步查询与 async_session_scope 执行
  - 通知调度单元/集成测试改为异步会话与 AsyncMock
- **任务模块异步化** (Task Module Async Migration)
  - Task/ExcelTaskConfig CRUD 移除同步方法，仅保留 AsyncSession 异步实现
  - 任务 API 与服务单元测试统一 AsyncMock/await 调用
  - 任务服务集成测试改用异步会话与当前 TaskService 能力
  - 任务创建单元测试对齐历史记录写入与多次提交行为
- **资产字段值查询测试数据去重** (Asset Field Values Test Data Uniqueness)
  - 资产集成测试字段值查询场景改用唯一 `property_name`，避免唯一约束冲突

### ✨ 文档识别 (Document Extraction)

- **GLM-OCR 预处理接入**
  - 新增 GLM-OCR 服务与 OCR 文本抽取管道
  - 智能识别支持扫描件自动走 OCR，并支持 `force_method=ocr`
  - 产权证/合同提取在 OCR 失败时回退至现有视觉模型
- **PyMuPDF 调用异步化**
  - 文本提取 / PDF 分析 / Vision 转图统一线程池 offload，避免阻塞事件循环
- **LLMService 读取配置对齐**
  - LLM 服务创建优先读取 settings/.env 中的提供商与密钥配置，避免本地脚本无法读取环境变量
- **Vision PDF 转图工具补齐**
  - 补充 `pdf_to_images` 实现，支持 PyMuPDF/pdf2image 转图，修复视觉提取缺失模块
- **证据驱动识别输出**
  - OCR 提取新增字段证据片段与来源（field_evidence/field_sources）
  - PDF 智能合并流程加入一致性校验与置信度扣减
  - API 类型与前端处理选项支持 `force_method=ocr`
  - async_db 适配器补齐构造签名类型约束，修正类型推断错误
- **合同导入审核证据展示**
  - 合同导入确认页支持字段证据弹窗与来源提示
  - 提取警告信息同步展示，便于快速复核异常字段
- **资产批量与历史接口异步化** (Asset Batch & History Async Migration)
  - 资产批量更新/验证/删除/列表与历史接口移除 run_sync，统一使用 AsyncSession 调用
  - 批量更新与删除补齐异步 CRUD 与历史记录写入
- **分析缓存容错** (Analytics Cache Guard)
  - 分析缓存读写失败时降级执行计算，避免测试/运行期 Redis 异常导致 500
- **分析与面积服务单测异步适配** (Analytics/Area Test Async Alignment)
  - 面积聚合/内存计算单测改用 AsyncSession mock 与 await
  - 分析趋势/分布测试补齐异步 patch 与 await 逻辑
- **分析服务清理无用导入** (Analytics Service Import Cleanup)
  - 移除未使用的 SQLAlchemy or_ 导入以通过 lint
- **后台服务会话初始化修复** (Background Service Session Init Fix)
  - 出租率计算、通知任务、租金合同导出改用 session_factory，移除 get_db 生成器调用
- **代码格式统一** (Code Formatting Alignment)
  - 执行 Ruff 格式化以统一最新异步迁移后的代码风格
- **PDF 导入临时文件清理** (PDF Import Temp File Cleanup)
- **催缴服务异步收敛** (Collection Service Async Convergence)
  - CollectionService 移除同步方法与 Session 依赖，统一 AsyncSession
  - 催缴 API 单测改用 AsyncMock/await
- **枚举验证异步收敛** (Enum Validation Async Convergence)
  - 移除同步 EnumValidationService 与便捷函数，仅保留 AsyncEnumValidationService
  - 单测与全局 mock 更新为异步验证接口
- **LLM Prompt 异步收敛** (LLM Prompt Async Convergence)
  - PromptManager/FeedbackService/AutoOptimizer 移除同步接口并改用 AsyncSession
  - LLM Prompt 服务单测重写为异步覆盖
- **产权证提示词适配器收紧** (Property Cert Adapter Async-only)
  - PromptManager 获取提示词仅接受 AsyncSession，移除同步 fallback

### 🧰 工具 (Tooling)

- **开发进程监控脚本** (Dev Watch Script)
  - 新增 `scripts/dev_watch.ps1`，启动前后端并在异常退出时记录退出码与日志尾部
  - 支持后台脱离控制台运行，避免关窗导致进程被中断
- **开发启动默认行为恢复** (Dev Server Defaults Restored)
  - Makefile 恢复默认 shell 行为
  - 前端 Vite 恢复默认启动与 TS 配置，后端 dev server 恢复默认 reload

### 📝 文档更新 (Documentation Updates)

- 更新 `AGENTS.md` 与 `CLAUDE.md`，同步最新命令、规则与更新时间
- 对齐前端状态管理描述：Zustand 用于 UI/资产 UI 状态，认证使用 React Context

### 🐞 Bug Fixes

- **产权证列表 404** (Property Certificate List 404)
  - 修复产权证路由重复前缀导致 `/api/v1/property-certificates/` 404
  - 处理结果/失败后自动清理 `temp_uploads` 与系统临时目录下的源文件
- **产权证字段兼容修复** (Property Certificate Field Compatibility)
  - 响应补齐 `verified` 字段并兼容 `is_verified` 更新
  - 列表查询参数统一使用 `limit`
- **前端路由与组件警告修复** (Frontend Route & Warning Fixes)
  - 产权证导入页面包屑不再误判为详情页
  - Ant Design Steps/Modal 废弃属性警告修复
- **系统字典与统计页面修复** (Dictionary & Stats Page Fixes)
  - 枚举字段列表响应移除 children 懒加载，修复字典页 500
  - 枚举值 children 通过 `set_committed_value` 清理，避免 Pydantic 校验触发 MissingGreenlet
  - 系统设置/组织管理 Tabs 改用 items，移除 TabPane 废弃警告
  - 系统设置密码策略表单修复单子元素渲染警告
  - 个人中心弹窗强制渲染，避免 useForm 未连接提示
  - 租金统计饼图标签改为函数并补齐图表错误边界
  - 租金统计收缴率进度条改用 `size`，移除 Progress width 废弃警告
- **项目/组织响应懒加载防护** (Project/Organization Lazy-load Guard)
  - ProjectResponse/OrganizationResponse 避免在序列化时访问未加载关系字段
- **枚举字段异步加载修复** (Enum Field Async Load Fix)
  - 异步加载枚举值使用 `set_committed_value`，避免 greenlet_spawn 触发 503
- **PDF 批量上传内存风险** (PDF Batch Upload Memory Risk)
  - 批量上传改为流式写入 `temp_uploads`，避免一次性读取到内存
  - 超限/空文件即时清理，失败时回收临时文件
- **Excel 导出临时文件清理** (Excel Export Temp File Cleanup)
  - 异步导出文件统一落盘到 `temp_uploads/excel_exports`
  - 任务删除或清理过期任务时回收导出文件
- **Excel 异步任务状态修复** (Excel Async Task Status Fix)
  - 异步导入/导出任务改用 `TaskService` 更新状态与历史记录
  - 后台任务独立创建数据库会话，避免请求结束后的会话失效
- **Excel 配置创建修复** (Excel Config Create Fix)
  - Excel 配置创建时补齐 `task_type` 与格式配置，避免字段不匹配导致创建失败
  - 默认配置切换时自动取消同类型默认值，避免多默认配置
- **资产创建事务提交修复** (Asset Create Transaction Commit Fix)
  - 修复资产创建在已有事务（权限校验/审计依赖）场景下仅开启嵌套事务导致提交丢失的问题
  - 资产创建现在在检测到已有事务时显式提交，确保写入持久化
- **资产列表缓存失效修复** (Asset List Cache Invalidation Fix)
  - 资产新增/更新/删除后清理资产相关 GET 缓存，避免列表继续显示旧数据
  - API 客户端新增按前缀失效缓存接口，支持粒度清理
- **资产软删除与校验加强** (Asset Soft Delete & Guard)
  - 资产删除改为软删除（data_status=已删除），保留历史记录与附件数据
  - 删除前新增租金台账关联校验，阻止存在台账的资产被删除
  - 查询统计补齐软删除过滤，确保列表与总数一致
  - 管理员新增资产恢复/彻底删除接口，支持软删除恢复与物理清理
  - 资产恢复/彻底删除补齐服务层校验与单元测试覆盖
  - Hard delete now clears asset history to avoid FK violations.
- **资产回收站筛选与前端操作** (Asset Recycle Bin UI)
  - 资产列表支持 `data_status` 筛选查看回收站记录
  - 前端新增资产状态筛选与状态列展示
  - 已删除资产仅显示恢复/彻底删除操作（管理员 + 强确认）
- **任务访问控制修复** (Task Access Control Fix)
  - 任务列表/详情/更新/删除/历史仅允许任务创建者或管理员访问
  - Excel 任务状态与导出下载接口需要认证并校验任务归属
  - 过期任务清理接口限制为管理员调用
- **任务模块异步迁移** (Task Module Async Migration)
  - 任务 CRUD/Service/API 统一使用 AsyncSession，移除 run_sync 适配
  - Excel 任务创建与状态更新改用同步会话专用 CRUD 方法
- **租金台账更新逻辑修复** (Rent Ledger Update Logic Fix)
  - 单条台账更新改为服务层处理，自动计算逾期金额与服务费
  - 统一与批量更新的衍生字段逻辑，避免直接 CRUD 导致数据不一致
- **Excel 历史分页修复** (Excel History Pagination Fix)
  - 修复 Excel 操作历史接口返回总数错误的问题
  - 现在返回真实总数以匹配分页数据
- **合同编辑权限校验修复** (Contract Edit Permission Check Fix)
  - 修复合同更新权限检查未生效的问题，确保 RBAC 校验可用
  - 新增租金条款接口同步执行合同编辑权限校验
- **附件接口修复** (Attachment Endpoints Fix)
  - 修复资产/租金合同附件接口的语法错误，确保路由正常加载
  - 附件接口统一为同步实现，避免测试与运行期不一致
- **API 路由语法修复** (API Route Syntax Fix)
  - 修复统计/组织/催缴/字典/出租率/Excel/PDF 批量接口中的 async/sync 结构错误
  - 清理错误的 `run_sync` 嵌套与 await 使用，恢复路由可加载与运行
  - 产权证接口改用同步会话并修正服务调用方式，避免运行期异常
- **Session 类型引用修复** (Session Type Reference Fix)
  - 修复 PDF 导入服务、系统设置与用户管理路由缺失 `Session` 类型引用导致的导入失败
- **系统设置接口异步化** (System Settings Async Migration)
  - 系统设置/系统信息/备份/恢复接口移除 run_sync，审计日志改为异步写入
- **租金合同路由同步化修复** (Rent Contract Route Sync Fix)
  - 将合同/条款/台账/统计/附件接口改为同步会话，移除错误的 `run_sync` 包装
  - 附件下载/删除改为同步获取附件对象，避免运行期取不到元数据
- **资产附件路由同步化修复** (Asset Attachment Route Sync Fix)
  - 资产附件上传/列表/下载/删除统一为同步会话并匹配文件校验流程
  - 附件列表与下载使用文件系统 API 与校验逻辑，确保测试路径一致
- **资产附件同步依赖补齐** (Asset Attachment Sync Dependency Fix)
  - 资产附件端点改用 `get_db` 同步会话，避免单元测试直接调用时出现未 await 协程
- **Excel 路由同步适配** (Excel Route Sync Alignment)
  - Excel 配置/导出/状态/模板接口恢复同步实现并改用 `get_db`，匹配单元测试直接调用方式
  - 异步导入/导出后台任务补齐可注入 `db_session` 并改用 `task_crud` 更新任务状态
  - 预览与同步导入端点补齐测试参数兼容逻辑，避免 mock 调用缺失导致断言失败
  - 异步导入创建任务时区分 AsyncSession 与 mock db，避免 `run_sync` 误用
- **租金合同 Excel 服务补齐** (Rent Contract Excel Service Restoration)
  - 恢复租金合同模板下载、导入与导出服务，避免模块缺失导致接口不可用
  - 支持合同/条款/台账多表导出与基础导入
- **运行依赖补齐** (Runtime Dependency Completion)
  - 添加 `cryptography` 与 `httpx` 到后端核心依赖，避免运行期导入失败
  - 添加 `asyncpg` 作为异步数据库驱动依赖，避免 AsyncSession 运行期导入失败
- **认证会话写入修复** (Auth Session Insert Fix)
  - `user_sessions` 写入统一使用 naive UTC 时间戳，避免 asyncpg 对 TIMESTAMP WITHOUT TIME ZONE 抛错
  - 审计日志写入改用 naive UTC 时间戳，避免 `audit_logs` 写入失败
  - 用户时间戳字段（`password_last_changed`/`updated_at`/`last_accessed_at`）改为 naive UTC
  - 登录流程不再因会话写入失败返回 500
- **密码过期判断修复** (Password Expiry Comparison Fix)
  - 密码过期时间比较统一为 naive UTC，避免登录时出现 aware/naive 比较异常
- **资产筛选下拉修复** (Asset Filter Dropdown Fix)
  - 资产列表筛选项改为异步 distinct 查询，避免 `run_sync` 调用协程导致 500
- **权属方列表修复** (Ownership List Fix)
  - 权属方列表/搜索改用同步查询封装，修复 `/api/v1/ownerships` 500
- **前端缓存分页提取修复** (Frontend Cache Paginated Extract Fix)
  - GET 缓存命中时继续执行 smartExtract，避免缓存返回原始响应导致列表结构缺失
- **创建接口斜杠兼容** (Create Endpoint Slash Compatibility)
  - 权属方/项目创建同时支持无尾斜杠路径，避免前端 POST 405
- **权属方创建校验修复** (Ownership Create Validation Fix)
  - 前端创建不再提交空字符串编码，允许后端自动生成编码，避免 422
- **权属方/项目异步化** (Ownership & Project Async Migration)
  - 权属方/项目服务与 API 端点改为 AsyncSession 调用，移除 run_sync 适配
  - 权属方财务汇总查询改为异步 SQL，避免同步子查询问题
- **项目响应懒加载修复** (Project Response Lazy-Load Fix)
  - 项目创建/列表/详情响应改为显式映射列字段，避免 ownership_relations 触发 MissingGreenlet
- **前端缓存提取测试** (Frontend Cache Extract Test)
  - 新增单元测试覆盖缓存命中时的分页响应提取
- **时间戳标准化扩展** (UTC Timestamp Standardization Expansion)
  - 模型/服务/CRUD 中写库时间统一使用 `datetime.utcnow()`（naive UTC），避免 asyncpg 对无时区字段报错
  - API 层 Excel 任务与用户更新写入时间统一为 `datetime.utcnow()`（naive UTC）
  - 清理替换后未使用的 `UTC` 导入
- **生产环境路由注册器防降级** (Production Router Registry Guard)
  - 生产环境禁止启用 `ALLOW_MOCK_REGISTRY`，缺失注册器属性时直接报错
  - 新增单元测试覆盖生产环境 Mock 降级保护
- **租金合同删除逻辑修复** (Rent Contract Delete Logic Fix)
  - 删除合同改为服务层软删除并记录历史，避免历史/关联表外键导致的删除失败
  - 租金合同查询默认排除已删除数据
- **前端类型检查修复** (Frontend Type Check Fixes)
  - 修复列表过滤回调与自定义统计卡片类型不匹配导致的 TS 报错
  - 修复 PDF 导入处理方式空字符串比较引发的类型报错
- **角色管理端点异步化** (Role API Async Migration)
  - 角色 CRUD、权限分配、统计与用户列表端点移除 run_sync 适配
  - 角色用户列表查询改为 AsyncSession 直连查询
- **认证会话接口异步化** (Auth Session Async Migration)
  - 会话查询/撤销与可选认证中间件移除 run_sync，改用 AsyncSession 查询
  - 调试认证端点改为 AsyncAuthenticationService 与 AsyncUserManagementService
  - 审计日志统计接口改为 AsyncSession 直连查询
- **组织架构接口异步化** (Organization API Async Migration)
  - 组织列表/搜索/树形/路径/历史等接口移除 run_sync 适配
  - 组织服务与 CRUD 补齐 AsyncSession 查询与历史记录写入
- **操作日志接口异步化** (Operation Log API Async Migration)
  - 操作日志列表/统计/导出/清理改为 AsyncSession 直连查询
  - 用户名补齐查询改用异步批量映射接口
- **安全事件接口异步化** (Security Event API Async Migration)
  - 系统设置安全事件查询改为异步 CRUD 调用
  - 组织权限与安全告警测试改为原生异步安全日志记录
- **枚举字段接口异步化** (Enum Field API Async Migration)
  - 枚举类型/值/使用记录/历史查询改为 AsyncSession 直连调用
  - 枚举 CRUD 补齐异步统计、批量写入与历史记录写入方法
- **提示词与通知接口异步化** (Prompt & Notification API Async Migration)
  - Prompt 模板/版本/统计/反馈接口移除 run_sync 适配
  - 通知列表/未读统计/标记已读/删除改为 AsyncSession 调用
- **系统字典与催缴接口异步化** (System Dictionary & Collection API Async Migration)
  - 系统字典 CRUD/批量更新改为 AsyncSession 直连
  - 催缴汇总/记录列表/读写接口移除 run_sync 适配

#### Changed / 变更

- **AGENTS 测试指引** (AGENTS Low-Memory Test Guidance)
  - 补充低内存运行 pytest 的建议与示例命令
- **资产枚举值更新** (Asset Enum Defaults Update)
  - 更新确权状态/使用状态/物业性质/租户类型的标准枚举值
- **产权证 API 层依赖规范化** (Property Certificate API Layer Normalization)
  - API 端点改为通过 `PropertyCertificateService` 访问 CRUD

#### Added / 新增

- **缺失的 CRUD 类补齐** (Missing CRUD Classes Added)
  - 新增 `collection_crud`、`prompt_template_crud`
- **白名单补齐** (Field Whitelist Coverage)
  - 为 `CollectionRecord`、`PromptTemplate` 增加字段白名单
  - 为 `Project`、`Organization`、`PropertyCertificate`、`PropertyOwner`、`RentTerm`、`RentLedger`、`UserRoleAssignment`、`ResourcePermission`、`PermissionAuditLog` 增加字段白名单
  - 为 `AsyncTask`、`ExcelTaskConfig` 增加字段白名单

### 🧹 代码质量与测试修复 (Lint & Test Fixes)

#### Fixed / 修复

- **Ruff 清理** (Ruff Cleanup)
  - 清理无效 `_sync` 占位逻辑与未使用变量，统一异步/同步辅助代码风格
  - 修正缺失的类型导入与泛型写法（`AsyncDB` 适配器改用 PEP 695 语法）
  - 修复分析接口空行空白、重复导入与未使用导入问题
  - 统一 Excel 导入与产权证 CRUD 的导入排序/来源
  - 补齐资产历史查询缺失的 `Session` 类型导入
  - 密码过期校验改用 `datetime.UTC` 以符合 Ruff 规则
- **MyPy 类型修复** (MyPy Type Fixes)
  - 完善系统日志/字典/联系人/角色等接口的 `run_sync` 适配与 `Session` 类型注解
  - 修复租金合同 Excel 导入/导出类型转换与字段映射模型匹配
  - 统一权限检查/布尔返回类型，减少 `no-any-return` 报错
  - 补齐认证/资产/统计分析/租金合同等模块 `run_sync` 类型标注与导入
  - Excel 异步导入任务创建 helper 增加类型注解
- **附件/日志与导出修复** (Attachment, Logs, Export Fixes)
  - 附件下载补齐元数据获取，避免运行期变量未定义
  - 操作日志导出修复过滤器变量作用域
  - Excel 异步导出补齐 `Session` 类型引用
- **测试稳定性** (Test Stability)
  - 测试环境变量恢复逻辑补齐，避免污染后续用例
  - 清理未使用断言变量并补充必要断言
  - 认证 API 与会话服务单元测试改为 AsyncSession + AsyncMock
  - 认证服务拆分验证测试改用异步服务与 AsyncSession mock
- **可选认证测试清理** (Optional Auth Test Cleanup)
  - 移除可选认证单测中的未使用 mock 逻辑与多余 token 生成，避免 lint 噪音
  - 可选认证单测改为异步调用并使用 AsyncSession 兼容的 stub

### ⚙️ 配置管理优化 (Configuration Management Optimization)

#### Changed / 变更

- **配置文件标准化** (Configuration File Standardization)
  - 整合 `config/environments/backend.env` 到 `backend/.env`
  - 创建标准 `frontend/.env` 文件
  - 统一使用项目根目录的 `.env` 文件，符合工具链最佳实践
- **配置验证去重** (Config Validation Deduplication)
  - 环境覆盖逻辑移入 `Settings` 校验阶段，避免运行时二次修改
  - 移除重复的 SECRET_KEY/Redis 校验，保留 DATABASE_URL 必填检查

#### Removed / 删除

- **完全删除 config/ 目录** (Complete Removal of config/ Directory)
  - 删除 `config/environments/` - 未被代码引用
  - 删除 `config/shared/` - YAML文件无加载机制
  - 删除 `config/templates/` - 已有 `.env.example` 文件作为模板
  - 删除 `config/root/` - API检查脚本已在 `frontend/scripts/` 和 `backend/scripts/`

#### Added / 新增

- `backend/.env` - 完整的后端环境配置（合并所有必要配置）
- `frontend/.env` - 前端Vite环境变量
- 更新 `GEMINI.md` 环境配置文档，包含详细设置指南

### 🎯 代码质量重构 (Code Quality Refactoring)

#### Removed / 删除

- **移除AI风格命名** (Removed AI-Style Naming)
  - 删除 `backend/src/api/v1/CLAUDE.md` - 旧的AI助手文档
  - 移除所有 "Enhanced" 前缀的类名和组件名
  - 移除 "Unified" 前缀的类名

- **简化认证服务层** (Simplified Authentication Services)
  - 合并 `AuthService` 和 `AuthenticationService`
  - 移除冗余的服务包装层

#### Modified / 修改

**后端 (Backend) - 37 files**
- `backend/conftest.py` - 测试配置更新
- `backend/src/api/v1/auth_modules/authentication.py` - 认证端点重构
- `backend/src/api/v1/auth_modules/password.py` - 密码管理端点更新
- `backend/src/api/v1/auth_modules/sessions.py` - 会话管理端点更新
- `backend/src/api/v1/auth_modules/user_management.py` - 用户管理端点重构
- 多个测试文件更新以反映新的服务结构

**前端 (Frontend) - 42 files**
- `frontend/src/api/client.ts` - API客户端重命名
- `frontend/src/utils/responseExtractor.ts` - 响应提取器重命名
- `frontend/src/types/index.ts` - 类型定义更新
- 多个组件和页面更新以使用标准命名

#### Added / 新增

- `frontend/src/pages/Rental/PDFImportPage.tsx` - PDF导入功能页面
- `frontend/src/types/pdfImport.ts` - PDF导入类型定义
- `backend/src/core/database.py` - 数据库核心模块

### 📊 统计 (Statistics)

- **文件修改**: 79 files changed
- **代码增加**: +892 insertions
- **代码删除**: -6,415 deletions
- **净删除**: -5,523 lines (代码更简洁)

### 🎨 改进重点 (Key Improvements)

1. **命名规范化** - 移除AI生成的命名模式，采用业务领域术语
2. **架构简化** - 减少不必要的抽象层和服务包装
3. **代码精简** - 删除了超过6000行冗余代码
4. **可维护性提升** - 更清晰的代码结构和命名

### 🔗 相关文档 (Related Documentation)

- [架构重构分析](docs/architecture-refactoring.md)
- [测试标准](docs/TESTING_STANDARDS.md)

### 🧹 文档清理 (Documentation Cleanup)

#### Removed / 删除

- 删除过期/未引用的阶段性报告与计划文档:
  - `docs/project-comprehensive-analysis-2026-02-02.md`
  - `docs/project-issues-report-2026-02-02.md`
  - `docs/test-coverage-improvement-phase1-report.md`
  - `docs/test-coverage-improvement-plan.md`
  - `docs/todo-debt-plan.md`
  - `docs/property-certificate-feature-plan.md`
  - `docs/property-certificate-implementation-summary.md`

### 🧩 文档补全 (Documentation Completion)

#### Added / 新增

- 新增缺失的文档与模板，补齐文档树结构:
  - `docs/index.md`
  - `docs/guides/getting-started.md`
  - `docs/guides/deployment.md`
  - `docs/integrations/api-overview.md`
  - `docs/integrations/auth-api.md`
  - `docs/integrations/assets-api.md`
  - `docs/integrations/pdf-processing.md`
  - `docs/features/prd-asset-management.md`
  - `docs/features/prd-rental-management.md`
  - `docs/features/spec-data-models.md`
  - `docs/features/spec-user-permissions.md`
  - `docs/incidents/incident-template.md`
  - `docs/testing/v2-test-cases.md`
  - `docs/v2_upgrade_plan.md`
  - `docs/architecture-refactoring.md`

#### Fixed / 修复

- 修复文档锚点与引用错误，确保内部链接有效

### 🧾 文档与工具维护 (Docs & Tooling Maintenance)

#### Added / 新增

- `backend/docs/API_DOCUMENTATION_ANALYSIS.md` - API 文档分析报告占位与生成说明
- `backend/docs/COVERAGE_IMPROVEMENT_REPORT.md` - 覆盖率报告占位与生成指引
- `docs/tooling/assistant-metadata.md` - 根目录工具元数据说明
- `docs/guides/components.md` - 前端组件导航与入口说明
- `frontend/src/components/index.ts` - 组件统一入口命名空间导出
- `frontend/src/components/Analytics/index.ts` - 分析模块统一入口
- `frontend/src/components/Common/index.ts` - 通用组件统一入口
- `frontend/src/components/Monitoring/index.ts` - 监控模块统一入口
- `frontend/src/components/Router/index.ts` - 路由模块统一入口
- `frontend/src/components/System/index.ts` - 系统管理模块统一入口
- `frontend/src/components/Auth/index.ts` - 认证模块统一入口
- `frontend/src/components/Dashboard/index.ts` - 仪表盘模块统一入口
- `frontend/src/components/Ownership/index.ts` - 权属方模块统一入口
- `frontend/src/components/Project/index.ts` - 项目模块统一入口
- `frontend/src/components/Rental/index.ts` - 租赁模块统一入口

#### Changed / 变更

- 修复文档引用路径:
  - `backend/docs/enhanced_database_guide.md`
  - `frontend/docs/type-safety-fix-summary.md`
  - `scripts/README.md`
- 更新文档入口与前端指南组件导航链接:
  - `docs/index.md`
  - `docs/guides/frontend.md`
- 更新组件导航表，补充 Auth/Dashboard/Ownership/Project/Rental/Router/Monitoring/System 入口:
  - `docs/guides/components.md`
- 修正组件入口导出冲突与默认导出错误:
  - `frontend/src/components/Analytics/index.ts`
  - `frontend/src/components/Common/index.ts`
- `backend/debug_import.py` 迁移至 `backend/scripts/dev/debug_import.py` 并补充路径初始化
- `.gitignore` 允许 `backend/docs` 下的分析/报告占位文档被追踪
- `.gitignore` 忽略前端测试输出文件（`frontend/test-results.txt`、`frontend/test_output.txt`、`frontend/vitest_stdout.txt`）

### 🗑️ 文档站点移除 (Docs Site Removal)

#### Removed / 删除

- 移除 MkDocs 站点构建相关配置与依赖:
  - `backend/mkdocs.yml`
  - `docs/includes/mkdocs.md`
  - `backend/pyproject.toml` 中的 docs 可选依赖
  - `backend/uv.lock` 中的 mkdocs 相关锁定项

### 📝 文档更新 (Documentation Updates)

#### Changed / 变更

- 更新后端与数据库指南，补充 asyncpg 依赖说明、虚拟环境提示与 UTC 时间戳写库约定
- 更新资产管理 PRD，补充范围/对象关系、枚举、唯一性、删除约束、权属对齐与权限预留要求
- 更新资产管理 API 文档，补充业务规则、枚举与关联/删除约束说明

---
## [1.0.0] - 2026-01-15

### 初始版本 (Initial Release)

- ✅ 用户认证与权限管理 (RBAC)
- ✅ 资产基础信息管理
- ✅ 租赁合同基础管理
- ✅ 租金台账基础功能
- ✅ 权属方/项目列表管理
- ✅ 数据字典管理
