# 2026-06-15 PRD Grill 代码收口清单

本清单汇总 2026-06-15 `/grill-with-docs docs/prd.md` 会话产出的**代码层收口项**。文档基线（PRD / domain-model / CONTEXT / ADR / trace / CHANGELOG）已在该会话对齐，以下按项跟踪代码改造状态。每项含触发决策、文件:行证据（2026-06-15 核实）、改造点与验收。

> 注：行号为 2026-06-15 快照，实施前以当前代码为准复核。

---

## F1. 通知接收人按主体绑定数据范围过滤

- **状态**：✅ 已实施（2026-06-15）
- **决策**：REQ-NTF-001（PRD §7.10）、§8 权限约束
- **原缺口**：定时通知对**全量活跃用户广播**含合同号、租户名等业务数据的通知，未按主体绑定过滤，违反 §8「所有业务查询必须按主体绑定过滤」。
- **证据**：
  - `backend/src/services/notification/scheduler.py:146` `list_active_users_async`（合同到期），`:218` `for user in active_users` 逐人创建
  - 同模式：`:253`/`:307`（付款逾期 `check_payment_overdue`），`:346`/`:400`（付款到期）
- **已改造**：`backend/src/services/notification/scheduler.py` 在业务提醒调度中先为活跃用户解析 `services/party_scope.resolve_user_party_filter()`，再按合同所属 `ContractGroup.owner_party_id/operator_party_id` 过滤接收人；合同到期、付款逾期、付款到期三条路径均只对可见接收人做批量去重和通知创建。`backend/src/crud/contract.py`、`backend/src/crud/contract_group.py` 同步预加载 `contract_group`，避免调度器访问范围字段时触发懒加载。系统通知查询/处理端点不受该业务对象过滤影响。
- **验收证据**：`backend/tests/unit/services/notification/test_scheduler.py` 覆盖合同到期、付款逾期、付款到期三类业务通知的 owner/operator/admin 可见接收人与范围外用户不接收；本地已通过 `ruff check` / `ruff format --check`。受当前 `backend/.venv` 解释器指向缺失的 `C:\Users\ygz\AppData\Local\Programs\Python\Python313\python.exe` 影响，定向 pytest 暂无法执行。

## F2. 合同更正陈旧已收台账派生风险 + 前端展示

- **状态**：✅ 已实施（2026-06-15）
- **决策**：ADR-0008、REQ-RNT-005
- **缺口**：重算跳过的 `paid`/`partial` 条目仅进 `skipped_entries` HTTP 返回值，零持久化、前端零渲染。
- **证据**：
  - `backend/src/services/contract/ledger_service_v2.py:347`、`:368` 追加 `skipped_entries`（reason `paid_or_partial_entry_requires_manual_resolution`），`:390` 作为返回值
  - 前端 `skipped_entries` 全库零引用
- **已改造**：
  1. 后端在 `backend/src/services/contract/ledger_service_v2.py` 抽出 `find_stale_paid_or_partial_ledger_entries()`，复用台账重算的账期展开、金额和到期日口径，派生 `paid`/`partial` 条目的金额/到期日不一致或已不在当前条款账期内的陈旧风险信号。
  2. `backend/src/services/project/service.py` 在项目风险摘要中按合同关系读取合同台账与租金条款，生成 `ledger_stale_after_correction` 风险；人工把已收/部分已收条目修正到当前条款目标后风险自然消失，不设手工关闭位。
  3. 前端 `frontend/src/services/ledgerService.ts` 新增合同台账重算 API；`frontend/src/pages/ContractGroup/ContractGroupDetailPage.tsx` 在合同关系明细页提供“重算台账”操作，并当场展示 `skipped_entries` 的账期、状态和原因。
- **验收证据**：`backend/tests/unit/services/contract/test_ledger_recalculate.py` 覆盖陈旧已收台账派生与人工对账后自愈；`backend/tests/unit/services/project/test_project_service.py::TestGetProjectRisks` 覆盖合同关系风险摘要出现/消失及上游合同同样派生；`frontend/src/pages/ContractGroup/__tests__/ContractGroupDetailPage.test.tsx` 覆盖重算后展示被跳过的已收条目。

## F3. 权限管理员授予边界（perm_admin 禁授业务角色）

- **状态**：✅ 已实施（2026-06-15）
- **决策**：ADR-0009、PRD §5、REQ-AUTH-001
- **原缺口**：授予角色无授予范围校验，`perm_admin` 可给自己授业务角色自我提权。
- **证据**：
  - `backend/src/api/v1/auth/roles.py:47` `_SYSTEM_MANAGEMENT_ROLE_CODES = ["admin", "system_admin", "perm_admin"]`；`:323`/`:326` `assign_role_to_user` 门控含 `perm_admin`
  - `backend/src/services/permission/rbac_service.py:415` `assign_role_to_user` 无授予范围/自授权校验
- **已改造**：`backend/src/services/permission/rbac_service.py` 在 service 层增加静态角色授予边界；业务数据角色需授予人实际持有 `admin`/`system_admin` 角色，`perm_admin` 授予业务角色被拒并写入 `role_assign_denied` 审计，`perm_admin` 授管理角色不受影响。
- **验收证据**：`backend/tests/unit/services/permission/test_rbac_service.py::TestAssignRoleToUser` 覆盖 `perm_admin` 拒绝业务角色、审计落点、仍可授管理角色，以及既有成功授予/重复授予/缓存失效路径。

## F4. 项目分析端点靶向抑制客户双指标

- **状态**：✅ 已实施（2026-06-15）
- **决策**：REQ-ANA-001、客户双指标视图口径规则
- **原缺口**：单视图守卫仅装在综合分析端点，项目分析端点漏装，`scope_mode=all` 下客户双指标在混合口径被算出。
- **证据**：
  - 守卫已装：`backend/src/api/v1/analytics/analytics.py:46` `_assert_analytics_customer_metrics_perspective`，`:89`、`:409` 调用
  - 漏装：`backend/src/api/v1/assets/project.py:633` `get_project_analytics` 未调守卫；`:56` `_build_project_party_filter` 不收敛 `all`
  - `backend/src/schemas/project.py:398-399`、`:425` `ProjectAnalyticsResponse` 携客户双指标
- **已改造**：`GET /api/v1/projects/{project_id}/analytics` 在 `scope_mode=all` 时向 service 传入 `suppress_customer_metrics=True`；`ProjectAnalyticsResponse` 与分区摘要的客户计数字段改为可空，并新增 `customer_metrics_suppression_reason`；前端项目详情在空指标处显示“需选视图”并展示标记，其余资产、合同关系、收付款、风险和趋势照常返回。
- **验收证据**：`backend/tests/unit/services/project/test_project_service.py::TestGetProjectAnalytics::test_get_project_analytics_should_suppress_customer_metrics_for_all_scope` 与 `backend/tests/unit/api/v1/test_project_layering.py::test_get_project_analytics_should_suppress_customer_metrics_for_all_scope` 固化 `all` 视图抑制行为；`frontend/src/services/__tests__/projectService.test.ts -t getProjectAnalytics` 覆盖前端服务解析。

---

## 删除类（与上述收口区分：以下是删代码，非补逻辑）

ADR-0006（催缴）、ADR-0007（逾期手工 `overdue` 态）的代码拆除与存量迁移详见各 ADR「影响」节：

- **ADR-0006**：✅ 已实施（2026-06-15）。已删 `models/collection.py`、`crud/collection.py`、`services/collection/`、`schemas/collection.py` 及 `api/v1/system/collection.py`；`api/v1/__init__.py` 不再触发催缴路由自注册；新增 `20260615_drop_collection_module.py` 删除 `collection_records` 表和 `collection` ABAC/RBAC 残留；已删前端 `types/collection.ts` 并移除 `capability.ts` 中的 `collection` 资源；相关 API/CRUD/service 功能单测已删除，新增路由删除护栏和迁移清理测试。
- **ADR-0007**：✅ 已实施（2026-06-16）。`ledger_service_v2.py` 删 `_MANUAL_LEDGER_PAYMENT_STATUSES` 中 `overdue` 及批量更新校验；`schemas/contract_group.py` 与 `api/v1/contracts/ledger.py` 去 `overdue` 查询/登记入口；`project/service.py` 风险、汇总和分析改为派生逾期，代理服务费通过来源台账到期日派生；`crud/contract_group.py:260` `sum_overdue_amount_by_ownership_async` 补 `due_date < today` 与未收清过滤；新增 `20260616_drop_manual_overdue_status.py` 迁移存量 `overdue`（→ `unpaid`，`paid_amount>0` 归 `partial`）；前端 `types/ledger.ts`、`FinancialLedgerPage.tsx` 去 `overdue` 状态选项、逾期改派生标签。

---

## 参考

- ADR-0006 ~ ADR-0009：`docs/architecture/`
- 追踪状态：`docs/traceability/requirements-trace.md`（REQ-RNT-005、REQ-AUTH-001、REQ-ANA-001 已有代码证据；通知见 §3.10）
- 变更记录：`CHANGELOG.md` 2026-06-15 段
