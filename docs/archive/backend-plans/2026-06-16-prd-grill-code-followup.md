# 2026-06-16 PRD Grill 代码收口清单

本清单汇总 2026-06-16 `/grill-with-docs docs/prd.md` 会话产出的**代码层收口项**（ADR-0010~0014）。文档基线（PRD / domain-model / CONTEXT / ADR / trace / CHANGELOG）已在该会话对齐，以下按项跟踪代码改造状态。每项含触发决策、文件:行证据（2026-06-16 核实）、改造点与验收。

> 注：行号为 2026-06-16 快照，实施前以当前代码为准复核。
> 依赖顺序：C1 → C2/C3/C4（C1 让 re-org 成立，台账才需固化）；C5/C6/C7 保 C2 固化项目唯一；D-A/D-B 独立可并行。

---

## C1. `Asset.manager_party_id` 改派生（运营方单一权威轴）

- **状态**：✅ 已实施（2026-06-18）
- **决策**：ADR-0010、REQ-AST-002 / REQ-PRJ-001 / REQ-AUTH-002
- **已改造**：
  1. `Asset.manager_party_id` 保留兼容列，但创建、更新、批量更新和模型构造均忽略独立 `manager_party_id` / `management_entity` 输入；响应投影由当前有效 `Asset.project.manager_party_id` 派生，无项目时为空。
  2. 资产 manager 绑定数据范围过滤改读 active `project_assets` → `projects.manager_party_id`，不再读 `assets.manager_party_id`；无项目资产在 manager 视角自然排除。
  3. `owner_party_id` 不动，仍作为资产内在权属事实；资产列表的 `management_entity` / `manager_party_id` 筛选同样收敛到当前项目运营方。
- **验收证据**：`backend/tests/unit/crud/test_asset.py` 覆盖 manager 过滤按当前项目运营方、`any` 视角组合 owner/project manager、`management_entity` 筛选和 distinct 下拉值按项目运营方、通用/历史资产更新忽略独立 manager 输入；`backend/tests/unit/test_req_ast_002.py` 覆盖 service 更新不再写经营方历史；`backend/tests/unit/api/v1/test_assets_authz_layering.py` 覆盖创建端点清空独立 manager 输入；`backend/tests/unit/api/v1/test_asset_import_layering.py` 覆盖导入 create 鉴权不再信任行内独立 `manager_party_id`、manager-only 行回退 unscoped sentinel。Ruff check/format 已通过；pytest 受当前 `backend/.venv` 指向缺失的 `C:\Users\ygz\AppData\Local\Programs\Python\Python313\python.exe` 阻塞。

## C2. 台账条目固化归属（账本语义）

- **状态**：✅ 已实施（2026-06-18）
- **决策**：ADR-0011、REQ-RNT-006 / REQ-ANA-001
- **缺口**：`ContractLedgerEntry` 只带 `contract_id`，无归属快照（`ledger_service_v2.py` 中 `asset_id` 仅查询筛选参数、不落库）；历史口径靠 join 合同组/资产当前归属，re-org 改写历史。
- **收口证据**：`backend/src/models/contract_group.py`、`backend/alembic/versions/20260618_ledger_frozen_attribution.py`、`backend/src/crud/contract_group.py`、`backend/src/services/contract/ledger_service_v2.py`、`backend/src/services/contract/service_fee_ledger_service.py`、`backend/src/schemas/contract_group.py`。
- **改造点**：
  1. `ContractLedgerEntry` 增 `attributed_project_id` / `attributed_owner_party_id` / `attributed_operator_party_id` / `attributed_asset_ids` 列（+ 迁移）。
  2. 台账生成与重算新建未收条目时写入固化值：`project_id` = 合同所属单项目合同组的 `project_id`；`owner/operator` = 合同组归属；`asset_ids` = 生成该条目的 `Contract.asset_ids`，留空（整租）回退到生成时刻 `ContractGroup.asset_ids`。
  3. `ServiceFeeLedger` 继承来源租金台账固化归属（`service_fee_ledger_service.py`）。
- **验收证据**：`backend/tests/unit/services/contract/test_ledger_service_v2.py` 覆盖激活生成新条目固化项目/产权方/运营方/合同资产；`backend/tests/unit/services/contract/test_ledger_recalculate.py` 覆盖重算新建条目固化归属，以及 `Contract.asset_ids` 为空时回退 `ContractGroup.asset_ids`；`backend/tests/unit/services/contract/test_service_fee_ledger_service.py` 覆盖服务费台账创建与更新继承来源租金台账固化归属。Ruff check/format 已通过；pytest 受当前 `backend/.venv` 指向缺失的 `C:\Users\ygz\AppData\Local\Programs\Python\Python313\python.exe` 阻塞。

## C3. 历史/分析聚合改读固化归属

- **状态**：✅ 已实施（2026-06-19）
- **决策**：ADR-0011
- **已改造**：项目/产权方维度的收入、成本、收缴率、经营统计聚合改读条目 `attributed_*`，历史口径不再按合同组/资产当前 `project_id`/`owner_party_id` 回算。`backend/src/crud/contract_group.py` 的产权方金额汇总改读 `ContractLedgerEntry.attributed_owner_party_id`；台账资产筛选改读 `ContractLedgerEntry.attributed_asset_ids`；`ProjectService.get_project_ledger_summary()` / `get_project_analytics()` 改按 `list_ledger_entries_by_attributed_project()` 与 `list_service_fee_entries_by_attributed_project()` 聚合；`AnalyticsService.project_breakdown` 按租金/服务费条目的 `attributed_project_id` 拆分。当前资产、当前合同关系、租户与风险等当前投影仍读当前归属。
- **验收证据**：`backend/tests/unit/crud/test_contract_group.py` 覆盖产权方汇总不 join 当前合同组 owner、资产筛选读固化资产；`backend/tests/unit/services/project/test_project_service.py` 覆盖项目台账摘要、项目分析模式金额和月度趋势读固化项目（当前合同组可已迁走）；`backend/tests/unit/services/analytics/test_analytics_service.py` 覆盖全局经营分析项目拆分按 `attributed_project_id` 落历史项目。Ruff check/format 已通过；pytest 受当前 `backend/.venv` 指向缺失的 `C:\Users\ygz\AppData\Local\Programs\Python\Python313\python.exe` 阻塞。
## C4. 存量台账固化归属回填

- **状态**：✅ 已实施（2026-06-19）
- **决策**：ADR-0011
- **已改造**：新增 `backend/alembic/versions/20260618_backfill_ledger_frozen_attribution.py`，对存量 `ContractLedgerEntry` 按当前 `contracts -> contract_groups` 回填项目、产权方、运营方；资产集合优先 `contract_assets`，空则回退 `contract_group_assets`；`ServiceFeeLedger` 继承来源租金台账固化归属。迁移注释明确「回填值 = 迁移时点当前关联的近似」，并在回填后断言租金/服务费台账不得残留空项目/产权方/运营方/空资产集合，否则失败暴露。
- **验收证据**：`backend/tests/unit/migration/test_ledger_frozen_attribution_backfill.py` 覆盖迁移链、租金台账回填、服务费继承、缺失归属失败暴露。Ruff check/format 已通过；pytest 受当前 `backend/.venv` 指向缺失的 `C:\Users\ygz\AppData\Local\Programs\Python\Python313\python.exe` 阻塞。
## C5. 合同组覆盖资产与项目一致性校验

- **状态**：✅ 已实施（2026-06-19）
- **决策**：ADR-0012
- **已改造**：合同组创建/编辑时先按当前 `project_assets.valid_to IS NULL` 关系校验覆盖资产当前项目必须等于 `ContractGroup.project_id`，再执行既有「资产已绑定其他项目有效合同关系」冲突校验；资产不存在或无当前项目绑定会按「未绑定项目」失败暴露。
- **验收证据**：`backend/src/crud/contract_group.py` 新增 `list_current_project_bindings_for_assets()`；`backend/src/services/contract/contract_group_service.py` 新增 `_ensure_assets_belong_to_project()` 并接入 `create_contract_group()` / `update_contract_group()`；`backend/tests/unit/services/contract/test_contract_group_service.py` 覆盖创建/编辑时拒绝项目外资产。Ruff check/format 已通过；pytest 受当前 `backend/.venv` 指向缺失的 `C:\Users\ygz\AppData\Local\Programs\Python\Python313\python.exe` 阻塞。

## C6. `Contract.asset_ids ⊆ ContractGroup.asset_ids` 子集校验

- **状态**：✅ 已实施（2026-06-19）
- **决策**：ADR-0012
- **已改造**：新增合同入组时校验 `Contract.asset_ids ⊆ ContractGroup.asset_ids`；合同关系编辑资产范围时也会校验新范围不得小于已有合同显式覆盖资产；`asset_ids` 留空继续表示整租，跳过新增合同子集校验并传 `None` 给 CRUD，台账固化仍按 ADR-0011 回退组资产。当前后端无独立合同资产编辑端点；纠错草稿路径复制原合同资产并已有差异分类，C6 的写入口已封口。
- **验收证据**：`backend/src/crud/contract_group.py` 新增 `list_asset_ids_for_group()` / `list_contract_asset_ids_by_group()`；`backend/src/services/contract/contract_group_service.py` 新增 `_ensure_contract_assets_within_group()` / `_ensure_existing_contract_assets_within_group_assets()` 并分别接入 `add_contract_to_group()` 与 `update_contract_group()`；`backend/tests/unit/services/contract/test_contract_group_service.py` 覆盖合同资产超出关系范围被拒、缩小组资产范围不得挤出现有合同资产、留空按整租处理。Ruff check/format 已通过；pytest 受当前 `backend/.venv` 指向缺失的 `C:\Users\ygz\AppData\Local\Programs\Python\Python313\python.exe` 阻塞。

## C7. 代理合同跨项目共享盖章扫描件

- **状态**：✅ 已实施
- **决策**：ADR-0012
- **已改造**：`Contract.project_id` 随合同组项目写入并参与 `UNIQUE(contract_number, project_id)`，同一份委托协议可在多个项目下保留同号合同记录，同项目重号仍被拒，正常合同缺项目由 `ck_contracts_active_project_id_required` 持续拦截。新增 `ContractScanDocument` 与 `contract_scan_document_links`，盖章扫描件按 `storage_key` 单存、多 `Contract` 共享引用；`PUT /api/v1/contracts/{contract_id}/attachments` 只按同 `contract_number`、同委托方、同受托方、且位于正常代运营合同关系中的受托合同整体替换共享引用，复用既有 `storage_key` 时拒绝范围外链接，`DELETE` 删除时校验每个受影响合同仍至少保留 1 份扫描件；API 写入前逐条校验全部受影响合同 `contract:update` 权限。更正草稿复制来源扫描件，但后续更正仍按记录独立处理，不联动兄弟记录台账。
- **验收证据**：`backend/src/models/contract_group.py`、`backend/src/crud/contract.py`、`backend/src/services/contract/contract_group_service.py`、`backend/src/api/v1/contracts/contract_groups.py`、`backend/alembic/versions/20260620_contract_number_project_scan_documents.py`；`backend/tests/unit/models/test_contract_group_model.py`、`backend/tests/unit/services/contract/test_contract_group_service.py`、`backend/tests/unit/crud/test_contract.py`、`backend/tests/unit/api/v1/test_contract_groups_layering.py`、`backend/tests/unit/migration/test_contract_number_project_scan_documents_migration.py` 覆盖复合唯一、跨项目同号允许、共享作用域收窄、软删合同组排除、既有扫描件范围外链接拒绝、全部受影响合同鉴权、扫描件替换/删除 floor、迁移冲突、缺项目 fail-loud 与持续约束。Ruff/py_compile/docs-lint 可用校验已通过；pytest 受当前 `backend/.venv`/`uv` 环境阻塞。

## D-A. 删合同审批流，保留最小生命周期

- **状态**：✅ 已实施
- **决策**：ADR-0013（**REQ-RNT-004 联审残留的补完清理**——trace 标「已清理」但只清了主合同覆盖半边，联审半边漏拆仍在跑）
- **已改造**：删除合同审批流模型、端点、服务动作和联审测试残留；`start_correction` 只允许从 `ACTIVE` 合同发起；补录/纠错定稿直接进入 `ACTIVE`；`ContractLifecycleStatus` 存储轴收缩为 `{DRAFT, ACTIVE, TERMINATED}`，`已到期` 改为 `ACTIVE + effective_to < today` 的派生展示状态，无 `/expire` 路由、无 `expire()` 服务动作、无 `expire` 审计事件。
- **验收证据**：`backend/src/models/contract_group.py`、`backend/src/services/contract/contract_group_service.py`、`backend/src/api/v1/contracts/contract_groups.py`、`backend/alembic/versions/20260619_drop_contract_review_workflow.py`；`backend/tests/unit/api/v1/test_contract_lifecycle_api.py` 护栏退休审批/到期路由，`backend/tests/unit/services/contract/test_lifecycle_v2.py` 护栏无 `expire` 操作并覆盖定稿审计，`backend/tests/unit/models/test_contract_group_model.py` 锁定三态 lifecycle enum 与审计 action 注释，`backend/tests/unit/migration/test_drop_contract_review_workflow_migration.py` 覆盖 `PENDING_REVIEW`/`EXPIRED` 存量转 `ACTIVE` 与 enum 重建。

## D-B. 删 Project review 孤儿列

- **状态**：✅ 已实施
- **决策**：ADR-0014
- **已改造**：`ProjectReviewStatus` 与 Project review 四列已从运行模型/schema/字段白名单中移除，`20260619_drop_project_review_fields.py` 负责存量 drop；Party、Asset review 生命周期不动。
- **验收证据**：`backend/src/models/project.py`、`backend/src/schemas/project.py`、`backend/src/crud/field_whitelist.py`、`backend/alembic/versions/20260619_drop_project_review_fields.py`；`backend/tests/unit/schemas/test_project_schema.py` 与 `backend/tests/unit/crud/test_field_whitelist.py` 护栏拒收/不暴露 Project review 字段。
