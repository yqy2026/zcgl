# 2026-06-19 PRD Grill 代码收口清单

> 状态：✅ 已完成；归档于 `docs/archive/backend-plans/`。

本清单汇总 2026-06-19 `/grill-with-docs prd.md` 会话产出的**代码层收口项**（ADR-0019~0020 + ADR-0012/0013 修订 + Q7 文档追平代码）。文档基线（PRD / domain-model / CONTEXT / ADR / CHANGELOG）已在该会话对齐，以下按项跟踪代码改造状态。每项含触发决策、文件:行证据（2026-06-19 核实）、改造点与验收。

> 注：行号为 2026-06-19 快照，实施前以当前代码为准复核。
  > 依赖顺序：K1 → K2（派生化后再迁存量/改前端）；K3 已与 ADR-0013 主体删除同批落地；K4 仍复用「定稿 `finalize_correction`」链路补快照。

---

## K1. `payment_status` 派生化（单一真相轴 = `paid_amount`）

- **状态**：✅ 已实施
- **决策**：ADR-0019、REQ-RNT-006、§3.2
- **缺口**：`payment_status`(`unpaid/partial/paid`) 是残留双真相轴——逾期/收缴率/实收全按 `paid_amount` 算、不读它，唯一消费者是重算跳过逻辑，却能与 `paid_amount` 漂移（登记 `paid` 但 `paid_amount=0` → 重算跳过又被逾期口径标逾期，自相矛盾）。
- **文件:行证据**：
  - `backend/src/models/contract_group.py:701`（`ContractLedgerEntry.payment_status` 列）、`:706`（`paid_amount`）、`:793/:798`（`ServiceFeeLedger.paid_amount`/`payment_status`）。
  - `backend/src/api/v1/contracts/ledger.py:33`（`LedgerPaymentStatus = Literal["unpaid","paid","partial","voided"]`）、`:42-78`（查询/登记入参 `payment_status`）。
  - `backend/src/services/contract/ledger_service_v2.py:603`（跳过判据 `if entry.payment_status in {"paid","partial"}`）、`:30-31`（`_MANUAL_LEDGER_PAYMENT_STATUSES`/`_STALE_LEDGER_PAYMENT_STATUSES`）、`:144-198`（`find_stale_paid_or_partial_ledger_entries`）。
  - `backend/src/services/contract/service_fee_ledger_service.py`（`payment_status` 同步来源台账处）。
- **已改造**：
  1. `ContractLedgerEntry.payment_status` 与 `ServiceFeeLedger.payment_status` 改为 hybrid 派生投影：`paid_amount == 0` → `unpaid`、`0 < paid_amount < amount_due` → `partial`、`paid_amount >= amount_due` → `paid`，仅 `voided` 保留为系统持久状态。
  2. `ContractLedgerBatchUpdateRequest` 去掉 `payment_status` 并 `extra="forbid"`；批量登记只接受 `entry_ids`、`paid_amount`、`notes`。
  3. 台账重算、陈旧已收识别、纠错源条目冲销保护均改按 `paid_amount > 0` 判定已登记实收，不再信任可漂移状态列。
  4. `ServiceFeeLedger` 创建/更新时按来源租金台账金额派生状态；查询筛选仍保留 `payment_status` 参数，但走 ORM 派生表达式过滤。
- **验收证据**：`backend/src/models/contract_group.py`、`backend/src/schemas/contract_group.py`、`backend/src/services/contract/ledger_service_v2.py`、`backend/src/services/contract/service_fee_ledger_service.py`、`backend/src/crud/contract_group.py`；`backend/tests/unit/models/test_contract_group_model.py` 覆盖派生投影与 `voided` 优先，`backend/tests/unit/api/v1/test_contract_lifecycle_api.py` 覆盖登记入参拒绝 `payment_status`，`backend/tests/unit/services/contract/test_ledger_recalculate.py` 覆盖跳过判据改按实收金额。

## K2. 存量迁移 + 前端去手选状态

- **状态**：✅ 已实施
- **决策**：ADR-0019
- **缺口**：存量行 `payment_status` 可能与 `paid_amount` 不一致；前端财务台账实收登记仍提供手选 `unpaid/partial/paid`。
- **文件:行证据**：迁移参照 `backend/alembic/versions/20260616_drop_manual_overdue_status.py`（同型迁移）；前端财务台账实收登记组件（含状态下拉与 `paid_amount` 录入）。
- **已改造**：
  1. 新增 `backend/alembic/versions/20260620_derive_ledger_payment_status.py`，对租金台账与服务费台账的非 `voided` 存量行按 `paid_amount`/`amount_due` 重派生，`voided` 不动。
  2. 前端财务台账实收登记弹窗移除手选 `unpaid/partial/paid` 控件，只提交 `paid_amount` 与备注；类型 `LedgerBatchUpdatePayload` 去掉 `payment_status`。
- **验收证据**：`backend/tests/unit/migration/test_derive_ledger_payment_status_migration.py` 覆盖存量归一；`frontend/src/pages/Finance/FinancialLedgerPage.tsx`、`frontend/src/types/ledger.ts`、`frontend/src/services/__tests__/ledgerService.test.ts`、`frontend/src/pages/Finance/__tests__/FinancialLedgerPage.test.tsx` 同步去掉登记状态入参。

## K3. `ContractAuditLog` 枚举收缩 + `finalize_correction`（ADR-0013 审计半边）

- **状态**：✅ 已实施
- **决策**：ADR-0013（补漏 §4.16）、Q4/Q5、§8
- **已改造**：`ContractAuditLog.action` 注释收缩为 `{terminate, void, start_correction, finalize_correction}`；`finalize_correction()` 对源合同终止与新合同生效均写 `finalize_correction` 审计；`review_status_old/new` 随 ADR-0013 迁移删除；显式 `/expire` 路由、`expire()` 服务动作与 `EXPIRED` 落库状态均下线，旧 `EXPIRED` 行由迁移转回 `ACTIVE`，到期只按 `effective_to` 派生展示。
- **验收证据**：`backend/src/models/contract_group.py`、`backend/src/services/contract/contract_group_service.py`、`backend/src/api/v1/contracts/contract_groups.py`、`backend/alembic/versions/20260619_drop_contract_review_workflow.py`；`backend/tests/unit/services/contract/test_lifecycle_v2.py` 覆盖 `finalize_correction` 审计与无 `expire` 操作，`backend/tests/unit/api/v1/test_contract_lifecycle_api.py` 护栏无 `/expire` 路由，`backend/tests/unit/models/test_contract_group_model.py` 护栏 action 注释不含 `expire`，`backend/tests/unit/migration/test_drop_contract_review_workflow_migration.py` 覆盖 enum 重建。

## K4. Contract 对手方名称定稿固化快照

- **状态**：✅ 已实施
- **决策**：ADR-0020、PRD §6.1、REQ-CUS
- **缺口**：§6.1 承诺「历史合同保留签署时主体名称快照、不追溯覆盖」，但 Contract 只有 `lessor_party_id`/`lessee_party_id` 外键（跟主档 live 变名），无快照列；唯一沾边的 `LeaseContractDetail.tenant_name` 只覆盖承租/下游，委托/直租漏。
- **文件:行证据**：`backend/src/models/contract_group.py:241`（`lessor_party_id`）、`:248`（`lessee_party_id`）、`:357-361`（party relationships）、`:452`（`LeaseContractDetail.tenant_name`）。
- **已改造**：
  1. Contract 增 `lessor_name_snapshot`/`lessee_name_snapshot` 列，并新增迁移 `20260620_contract_party_name_snapshots.py` 回填存量快照。
  2. 补录即生效和 `finalize_correction` 定稿时从当时 Party 主档名写入快照，Party 后续改名不回写，覆盖全部合同类型。
  3. 纠错草稿复制来源合同快照，定稿时刷新为当时主档名；`LeaseContractDetail.tenant_name` 从 `lessee_name_snapshot` 同步，不另立真相轴。
  4. 后端 schema/API 与前端合同关系详情类型/列表展示均暴露快照字段。
- **验收证据**：`backend/src/models/contract_group.py`、`backend/src/schemas/contract_group.py`、`backend/src/services/contract/contract_group_service.py`、`backend/alembic/versions/20260620_contract_party_name_snapshots.py`、`frontend/src/types/contractGroup.ts`、`frontend/src/pages/ContractGroup/ContractGroupDetailPage.tsx`；`backend/tests/unit/models/test_contract_group_model.py`、`backend/tests/unit/services/contract/test_contract_group_service.py`、`backend/tests/unit/services/contract/test_contract_correction_flow.py`、`backend/tests/unit/migration/test_contract_party_name_snapshots_migration.py`、`frontend/src/pages/ContractGroup/__tests__/ContractGroupDetailPage.test.tsx` 覆盖快照列、写入、纠错定稿刷新、迁移回填和展示。

## K5. Party 不合并 + `review_status` 枚举修

- **状态**：✅ 已实施
- **决策**：ADR-0020、§4.18 bug 修复
- **缺口**：`PartyReviewStatus.REVERSED`（抄串 Asset 可反审枚举），应为 `REJECTED`；Party 驳回后保留 `rejected` 态，可编辑后重新提审，但不提供 Asset 式反审闭环；「去重」语义须落为建档查重、MVP 无主体合并。
- **文件:行证据**：`backend/src/models/party.py:40-44`（`class PartyReviewStatus(StrEnum)` 含 `REVERSED = "reversed"`）、`:69-70`（`Party.review_status` 列）。
- **已改造**：
  1. `PartyReviewStatus` `REVERSED → REJECTED`（值 `reversed → rejected`），新增迁移 `20260620_party_rejected_review_status.py` 迁移存量行；驳回流转与审核日志写 `rejected`。
  2. `submit_party_review()` 允许 `draft/rejected` 提审，`update_party()` 允许 `rejected` 编辑，仍禁止 `pending/approved` 编辑；未引入主体合并能力。
  3. 前后端类型、状态标签、Party 页面与服务测试同步为 `rejected`。
- **验收证据**：`backend/src/models/party.py`、`backend/src/services/party/service.py`、`backend/alembic/versions/20260620_party_rejected_review_status.py`、`frontend/src/types/party.ts`、`frontend/src/pages/System/PartyListPage.tsx`、`frontend/src/pages/System/PartyDetailPage.tsx`；`backend/tests/unit/services/test_party_service.py`、`backend/tests/unit/api/v1/test_party_api.py`、`backend/tests/unit/migration/test_party_rejected_review_status_migration.py`、`frontend/src/pages/System/__tests__/PartyPages.test.tsx`、`frontend/src/services/__tests__/partyService.test.ts` 覆盖 rejected 状态、审核日志、迁移和展示。

## K6. 客户档案口径（代码已符合，仅回归断言）

- **状态**：✅ 已实施
- **决策**：Q7 收口（无 ADR）
- **缺口**：**代码本就正确**——`binding_type=all` 并集 + 按 `contract_id` 去重已实现，domain-model §4.12 此前落后于代码（已修文档）。仅需补回归断言锁住口径。
- **文件:行证据**：`backend/src/services/party/service.py:638-708`（`get_customer_profile`，`:708` `historical_contract_count = len(contract_summaries)`）、`:717-784`（`_list_customer_contracts`，`:764-765` `all`→`["owner","manager"]`、`:767/:779-781` 按 `contract_id` 去重）；`backend/src/schemas/party.py:200`（`binding_type` 描述 `owner/manager/all`）、`:208`（`historical_contract_count`）。
- **已改造**：无功能改造；补服务层回归断言，锁住 `all` 模式 `historical_contract_count` 按合同 ID 去重（一份合同两绑定可见只算一次）、不被分析端单视图守卫拦截（该守卫只约束 `customer_entity_count`/`customer_contract_count`）。
- **验收证据**：`backend/tests/unit/services/test_party_service.py` 覆盖 `binding_type=all` 同合同双绑定只计一次；`docs/specs/domain-model.md` 与 `CONTEXT.md` 已区分档案列表并集口径和分析端单视图口径。
