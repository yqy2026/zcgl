# 需求追踪矩阵

## 1. 文档定位

本文档记录 REQ 到实现状态、代码证据和测试证据的映射。产品目标见 [`docs/prd.md`](../prd.md)，字段和状态见 [`docs/specs/domain-model.md`](../specs/domain-model.md)，API 契约见 [`docs/specs/api-contract.md`](../specs/api-contract.md)。

2026-10-22 起，资产运营 v5 取代 v4.0 业务范围。旧业务 REQ 标记为“已移除”只表示不再属于产品基线；存量代码是否删除或迁移由当前活跃 V1 计划追踪，不能把其存在当作 v5 证据。

## 2. 状态定义

| 状态类型 | 取值 | 含义 |
|---|---|---|
| 产品状态 | MVP | 当前产品基线 |
| 产品状态 | vNext | 候选能力，不纳入当前验收 |
| 产品状态 | Out of Scope | 当前明确不纳入 |
| 产品状态 | 已移除 | 旧 REQ 被新基线取代，仅保留追溯 |
| 实现状态 | 未开始 | 只有规格或原型，无业务实现证据 |
| 实现状态 | 开发中 | 已有部分代码或测试，尚未形成完整切片 |
| 实现状态 | 已有证据 | 代码和测试能够证明需求行为，仍待产品验收 |
| 实现状态 | 已验收 | 已完成产品验收 |

## 3. v5 业务需求

### 3.1 工作台与资产单元

2026-10-27 PR #95 合并门禁补充：`frontend/tests/e2e/asset-flow.spec.ts`、`frontend/tests/e2e/auth/organization-scope-isolation.spec.ts` 与 `frontend/tests/e2e/smoke/main-pages-render.spec.ts` 已迁移到 v5 生产路径；隔离用例通过 `backend/scripts/dev_seed_v5_walkthrough.py` 的两方真实资产验证授权范围，旧入口有明确 404 断言。该阶段先完成静态检查；最终真实浏览器及完整 CI 已通过，证据见第 7 节复核记录。这不改变 REQ-UNT-001 的开发中状态。

| REQ | 产品状态 | 实现状态 | 代码证据 | 测试证据 | 备注 |
|---|---|---|---|---|---|
| REQ-WBK-001 | MVP | 未开始 | — | — | 本月截止事项与随时处理事项均为派生投影，不建立通用待办写模型 |
| REQ-UNT-001 | MVP | 开发中 | `backend/src/models/asset_unit.py`, `backend/src/crud/asset_unit.py`, `backend/src/crud/asset_unit_boundary.py`, `backend/src/services/asset_operations/boundary_command_service.py`, `backend/src/services/asset_operations/query_service.py`, `backend/src/api/v1/asset_units.py`, `backend/src/scripts/migration/asset_operations_v5/preflight.py`, `frontend/src/services/assetOperationsService.ts`, `frontend/src/pages/AssetOperations/AssetUnitsPage.tsx`, `frontend/src/routes/AppRoutes.tsx` | `backend/tests/unit/crud/test_asset_unit_v5.py`, `backend/tests/unit/crud/test_asset_unit_boundary.py`, `backend/tests/unit/services/asset_operations/test_boundary_command_service.py`, `backend/tests/unit/services/asset_operations/test_boundary_merge_command_service.py`, `backend/tests/unit/services/asset_operations/test_asset_unit_views.py`, `backend/tests/unit/api/v1/test_asset_unit_boundary_api.py`, `backend/tests/integration/database/test_asset_unit_boundary_command.py`, `frontend/src/pages/AssetOperations/__tests__/AssetUnitsPage.test.tsx`, `frontend/src/routes/__tests__/AppRoutes.authz-metadata.test.ts` | V1 已完成资产单元预检、事实模型、范围化列表/详情、更新/空置备注 API、拆分/合并预览—提交 API 与生产列表/详情页；V1-T05/T06/T08/T09 覆盖面积守恒、权利边界、乐观锁和幂等，V1-T10 覆盖 loading/empty/403/error 四态。完整 REQ 仍缺生产端空置备注、拆合操作/历史与合同时间轴；证照关系、考核状态及联动筛选依规格分别进入 V4/V3，完成前不得标为“已有证据” |

### 3.2 已签合同

| REQ | 产品状态 | 实现状态 | 代码证据 | 测试证据 | 备注 |
|---|---|---|---|---|---|
| REQ-CTR-001 | MVP | 已有证据 | `backend/src/models/asset_contract.py`, `backend/src/models/business_change_event.py`, `backend/src/services/asset_operations/business_change_service.py`, `backend/src/api/v1/business_change_events.py`, `backend/src/crud/asset_contract.py`, `backend/src/services/asset_operations/contract_command_service.py`, `backend/src/services/asset_operations/contract_lifecycle_command_service.py`, `backend/src/services/asset_operations/query_service.py`, `backend/src/api/v1/contract_intake_sessions.py`, `backend/src/api/v1/upstream_contracts.py`, `frontend/src/services/assetOperationsService.ts`, `frontend/src/pages/AssetOperations/ContractIntakePage.tsx`, `frontend/src/pages/AssetOperations/ContractListsPage.tsx`, `frontend/src/pages/AssetOperations/LifecycleActionsPage.tsx` | `backend/tests/unit/services/asset_operations/test_contract_command_service.py`, `backend/tests/unit/services/asset_operations/test_business_change_service.py`, `backend/tests/unit/migration/test_contract_field_rules_migration.py`, `backend/tests/unit/services/asset_operations/test_contract_lifecycle_exit_preview.py`, `backend/tests/unit/services/asset_operations/test_contract_lifecycle_renewal.py`, `backend/tests/unit/services/asset_operations/test_contract_query_views.py`, `backend/tests/unit/api/v1/test_upstream_contract_exit_api.py`, `backend/tests/integration/database/test_asset_contract_command.py`, `backend/tests/integration/database/test_contract_lifecycle_command.py`, `frontend/src/pages/AssetOperations/__tests__/ContractIntakePage.test.tsx`, `frontend/src/pages/AssetOperations/__tests__/ContractListsPage.test.tsx`, `frontend/src/pages/AssetOperations/__tests__/LifecycleActionsPage.test.tsx`, `backend/tests/e2e/test_asset_contract_lifecycle_e2e.py` | 上游合同录入、列表/详情/更新、退出预览—提交—撤销和续签均已接入 API 与生产页面；Party 范围、共享单元锁、有效终端全局阻断、事件重放、唯一后继、扫描件改绑和持久幂等均有单元及真实 PostgreSQL 证据；V1-T04/T07/T08/T09/T10 已覆盖，仍待产品验收 |
| REQ-CTR-002 | MVP | 已有证据 | `backend/src/models/asset_contract.py`, `backend/src/models/business_change_event.py`, `backend/src/services/asset_operations/business_change_service.py`, `backend/src/api/v1/business_change_events.py`, `backend/src/crud/asset_contract.py`, `backend/src/services/asset_operations/contract_command_service.py`, `backend/src/services/asset_operations/contract_lifecycle_command_service.py`, `backend/src/services/asset_operations/query_service.py`, `backend/src/api/v1/contract_intake_sessions.py`, `backend/src/api/v1/terminal_contracts.py`, `frontend/src/services/assetOperationsService.ts`, `frontend/src/pages/AssetOperations/ContractIntakePage.tsx`, `frontend/src/pages/AssetOperations/ContractListsPage.tsx`, `frontend/src/pages/AssetOperations/LifecycleActionsPage.tsx` | `backend/tests/unit/services/asset_operations/test_contract_command_service.py`, `backend/tests/unit/services/asset_operations/test_business_change_service.py`, `backend/tests/unit/migration/test_contract_field_rules_migration.py`, `backend/tests/unit/services/asset_operations/test_contract_lifecycle_termination_preview.py`, `backend/tests/unit/services/asset_operations/test_contract_lifecycle_renewal.py`, `backend/tests/unit/services/asset_operations/test_contract_update_service.py`, `backend/tests/unit/services/asset_operations/test_contract_query_views.py`, `backend/tests/unit/api/v1/test_terminal_contract_termination_api.py`, `backend/tests/integration/database/test_asset_contract_command.py`, `backend/tests/integration/database/test_contract_lifecycle_command.py`, `frontend/src/pages/AssetOperations/__tests__/ContractIntakePage.test.tsx`, `frontend/src/pages/AssetOperations/__tests__/ContractListsPage.test.tsx`, `frontend/src/pages/AssetOperations/__tests__/LifecycleActionsPage.test.tsx`, `backend/tests/e2e/test_asset_contract_lifecycle_e2e.py` | 终端合同录入、列表/详情/更新、终止预览—提交—撤销和续签均已接入 API 与生产页面；允许已签事实在上游缺失/越界时登记并稳定派生 warning，同期覆盖、Party 范围、覆盖截止/恢复、后继阻断、扫描件消费和幂等回放均有单元及真实 PostgreSQL 证据；V1-T01–T03/T06–T10 已覆盖，仍待产品验收 |

### 3.3 租金、押金与委托管理费

| REQ | 产品状态 | 实现状态 | 代码证据 | 测试证据 | 备注 |
|---|---|---|---|---|---|
| REQ-LED-001 | MVP | 开发中 | `backend/src/models/asset_ledger.py`, `backend/src/services/asset_operations/rent_obligation_service.py`, `backend/src/services/asset_operations/rent_payment_command_service.py`, `backend/src/services/asset_operations/rent_schedule_correction_service.py`, `backend/src/services/asset_operations/rent_ledger_query_service.py`, `frontend/src/pages/AssetOperations/LedgersPage.tsx` | `backend/tests/unit/services/asset_operations/test_rent_obligation_rules.py`, `backend/tests/integration/database/test_rent_commands.py`, `backend/tests/e2e/test_asset_rent_ledger_e2e.py`, `frontend/src/pages/AssetOperations/__tests__/LedgersPage.test.tsx` | 应付/应收义务、部分登记、跨月结转、凭证和有原因撤销；录入与续签核对租金阶段、租金阶段更正（往月已有阶段不改，往月缺口可补录）与提前退租补收免租 |
| REQ-DEP-001 | MVP | 开发中（PR-B 验收中） | `backend/src/models/deposit_ledger.py`, `backend/src/services/asset_operations/deposit_command_service.py`, `backend/src/services/asset_operations/deposit_query_service.py`, `backend/src/services/asset_operations/deposit_settlement_service.py`, `backend/src/api/v1/deposits.py`, `frontend/src/pages/AssetOperations/ContractDepositPanel.tsx` | `backend/tests/unit/services/asset_operations/test_deposit_rules.py`, `backend/tests/unit/services/asset_operations/test_deposit_query_service.py`, `backend/tests/unit/services/asset_operations/test_deposit_settlement_service.py`, `backend/tests/e2e/test_asset_deposit_e2e.py`, `frontend/src/pages/AssetOperations/__tests__/ContractDepositPanel.test.tsx` | 已接入条目创建、四类方向、续签结转、追加登记、抵扣与成对撤销、终止自动/手工分配和免租补收；具备真实 HTTP 抵扣及终止撤销证据，补齐自动抵扣续签前驱欠租与撤销恢复回归；PR #99 已有提交 CI 通过，新增修复 CI 与前端整体验收仍待完成 |
| REQ-FEE-001 | MVP | 已实现（2026-10-30 用户产品验收通过） | `backend/src/services/asset_operations/management_fee_rules.py`、`backend/src/models/management_fee_statement.py`、`backend/src/services/asset_operations/management_fee_entry_service.py`、`backend/src/services/asset_operations/management_fee_query_service.py`、`backend/src/services/asset_operations/management_fee_write_guard.py`、`backend/src/services/asset_operations/management_fee_command_service.py`、`backend/src/services/asset_operations/management_fee_stamp_service.py`、`backend/src/services/asset_operations/management_fee_confirmation_service.py`、`backend/src/services/asset_operations/management_fee_rate_service.py`、`backend/src/api/v1/management_fee_statements.py` | `backend/tests/unit/services/asset_operations/test_management_fee_rules.py`、`backend/tests/unit/services/asset_operations/test_management_fee_entry_service.py`、`backend/tests/unit/services/asset_operations/test_management_fee_query_service.py`、`backend/tests/unit/services/asset_operations/test_management_fee_command_service.py`、`backend/tests/unit/services/asset_operations/test_management_fee_confirmation_service.py`、`backend/tests/unit/services/asset_operations/test_management_fee_confirmation_sql.py`、`backend/tests/unit/services/asset_operations/test_management_fee_stamp_service.py`、`backend/tests/unit/api/v1/test_management_fee_api.py`、`backend/tests/unit/services/asset_operations/test_management_fee_upload_service.py` | 已有创建查询、到账锁定、顺延、比例失效、盖章绑定与确认/更正事务服务；七个 HTTP 接口、公开读模型和盖章上传已接入；前端七端点服务 `frontend/src/services/managementFeeService.ts` 及回归 `frontend/src/services/__tests__/managementFeeService.test.ts` 已接入，年度管理费矩阵 `backend/src/services/asset_operations/management_fee_matrix_service.py`、台账入口 `frontend/src/pages/AssetOperations/ManagementFeeLedger.tsx` 和纸面单据 `frontend/src/pages/AssetOperations/ManagementFeeStatementPage.tsx` 已接入；新增 `backend/tests/unit/api/v1/test_management_fee_matrix_api.py`、`frontend/src/pages/AssetOperations/__tests__/ManagementFeeStatementPage.test.tsx` 回归及隔离示例数据视觉验证，专用测试库三条管理费增量迁移已验证；`backend/tests/e2e/test_management_fee_e2e.py` 三条真实 PostgreSQL/Redis HTTP 用例已通过，新增部分管理方不得读取整单回归；`backend/tests/e2e/test_management_fee_concurrency.py` 两条独立连接更正竞争回归通过，验证真实锁等待、提交可见性与唯一回执/审计。确认与到账两种提交顺序竞争也已验证，并发文件共 4 条通过；真实登录/RBAC/绑定/resolver 的 `backend/tests/e2e/test_management_fee_scope_e2e.py` 两条通过；后端原全量环境约束失败项定向复验通过；修复 MSW 启动时序后前端全量 131 文件/1461 条通过，另有独立启动探针回归通过；完整应用真实登录、到账、顺延、盖章确认、更正与只读权限走查已通过；新增 `frontend/tests/e2e/smoke/management-fee-print.spec.ts` 验证动画中打印，1440/640/320 宽度及单页 A4 导出已复核；整体差异复核已通过（2026-10-30：双轴复核采纳项含 mypy 48 处清零、V2-T24 合计↔行合计与矩阵↔月度交叉断言、回填脚本 apply 模式对账单创建数报告、`.env.backup` 入 ignore、两条引用已演进 `voiding_entry` 参数的过期守卫测试按现行 `reversing_record_id` 契约清理；盖章上传无幂等键与 `reason` 默认空串经裁定维持 api-contract §5.9 原契约；受影响后端 1521 条与前端定向 28 条通过）；PR #100 CI 全绿（2026-10-30 七轮后 CI Summary pass，含 Frontend E2E 与 API Consistency 首次真跑通过；E2E 种子补管理费链路、runner 固定 ubuntu-24.04、矩阵调用改裸路径均在本 PR 修复）；产品验收仍待完成 |

### 3.4 报送、档案与导入

| REQ | 产品状态 | 实现状态 | 代码证据 | 测试证据 | 备注 |
|---|---|---|---|---|---|
| REQ-RPT-001 | MVP | 未开始 | — | — | 年度考核范围版本、排除原因、年中新增确认和影响预览 |
| REQ-RPT-002 | MVP | 未开始 | — | — | 月度草稿、门槛、逐宗明细、提交快照、撤回和差异提示 |
| REQ-ARC-001 | MVP | 未开始 | — | — | 业务对象挂档、已有/应有矩阵、多文件人工配对和版本替换 |
| REQ-IMP-001 | MVP | 未开始 | — | — | 新增/更新、逐行校验、差异选择、原子提交和七日内整批撤销 |

## 4. 保留的平台需求

这些能力继续服务 v5，但不出现在资产管理工作台导航中。

| REQ | 产品状态 | 实现状态 | 代码证据 | 测试证据 | 备注 |
|---|---|---|---|---|---|
| REQ-AUTH-001 | MVP | 已有证据 | `backend/src/api/v1/auth/`, `backend/src/services/authz/`, `frontend/src/routes/AppRoutes.tsx`, `frontend/src/pages/ExpiredPasswordForm.tsx` | `backend/tests/e2e/test_auth_flow_e2e.py`, `backend/tests/e2e/test_expired_password_e2e.py`, `frontend/src/pages/__tests__/ExpiredPasswordForm.test.tsx` | 会话、CSRF、受保护路由和统一鉴权继续保留；过期账号可在登录前验证当前密码并改密，成功后重新登录 |
| REQ-AUTH-002 | MVP | 已有证据 | `backend/src/services/party_scope.py`, `backend/src/middleware/data_scope.py`, `backend/src/services/authz/context_builder.py`, `backend/src/services/authz/service.py`, `backend/src/services/authz/resource_perspective_registry.py`, `backend/src/crud/asset_unit.py`, `backend/src/crud/asset_contract.py`, `backend/src/services/asset_operations/query_service.py`, `backend/src/api/v1/asset_units.py`, `backend/alembic/versions/20261024_asset_operations_v5_permissions.py` | `backend/tests/e2e/test_party_binding_scope_e2e.py`, `backend/tests/unit/crud/test_asset_unit_v5.py`, `backend/tests/unit/crud/test_asset_contract_v5.py`, `backend/tests/unit/services/asset_operations/test_query_service.py`, `backend/tests/unit/services/test_authz_service.py`, `backend/tests/unit/api/v1/test_asset_unit_boundary_api.py`, `backend/tests/unit/migration/test_asset_operations_v5_permissions_migration.py`, `backend/tests/integration/database/test_asset_operations_permissions.py` | 有效 Party 范围失败关闭，403 不伪装为空；资产按产权方/项目运营方、上游合同按合同双方、终端合同按覆盖资产范围查询；拆分/合并 API 强制 `asset_ops:write` 并由服务端解析 Party 范围，五类 `asset_ops` 能力已映射到内建运营/系统管理员且有 PostgreSQL 种子证据 |
| REQ-AUTH-003 | MVP | 已有证据 | `backend/src/services/authz/`, `backend/src/api/v1/auth/roles.py` | `backend/tests/e2e/test_role_authorization_e2e.py` | 平台角色授予边界与业务能力声明 |
| REQ-SYS-001 | MVP | 已有证据 | `backend/src/api/v1/auth/auth_modules/users.py`, `backend/src/services/core/user_management_service.py`, `frontend/src/pages/System/UserManagement/` | `backend/tests/e2e/test_user_lifecycle_e2e.py` | 用户、角色和组织管理作为平台基础保留 |
| REQ-PTY-001 | MVP | 已有证据 | `backend/src/api/v1/party.py`, `backend/src/services/party/`, `backend/src/models/party.py` | `backend/tests/e2e/test_party_lifecycle_e2e.py` | Party 审核、启停和统一身份继续作为业务引用前提 |
| REQ-PTY-002 | MVP | 已有证据 | `backend/src/api/v1/party.py`, `backend/src/services/party/`, `backend/src/services/organization/` | `backend/tests/e2e/test_party_enhancements_e2e.py` | 正式 Party 创建和组织代表关系继续保留 |
| REQ-XCUT-001 | MVP | 已有证据 | `backend/src/core/router_registry.py`, `backend/src/main.py` | `backend/tests/unit/api/v1/test_project_layering.py` | API 统一版本化 |
| REQ-XCUT-002 | MVP | 已有证据 | `backend/src/api/v1/`, `backend/src/services/` | `backend/tests/unit/api/v1/test_authentication_layering.py` | API 不承载业务逻辑，数据访问经 CRUD |
| REQ-XCUT-003 | MVP | 已有证据 | `backend/src/core/encryption.py`, `docs/security/encryption.md` | `backend/tests/unit/core/test_encryption.py` | PII 加密与脱敏 |
| REQ-XCUT-004 | MVP | 已有证据 | `frontend/src/constants/routes.ts`, `frontend/src/routes/AppRoutes.tsx` | `frontend/src/routes/__tests__/AppRoutes.authz-metadata.test.ts` | 路由、菜单和后端能力对齐 |

## 5. 被 v5 取代的旧 REQ

| REQ | 产品状态 | 实现状态 | 代码证据 | 测试证据 | 备注 |
|---|---|---|---|---|---|
| REQ-AST-001 | 已移除 | 开发中 | — | — | 旧 Asset/Space/登记单元分层由 REQ-UNT-001 资产单元模型取代 |
| REQ-AST-002 | 已移除 | 开发中 | — | — | 旧出租授权跟踪退出 v5 |
| REQ-AST-003 | 已移除 | 开发中 | — | — | 旧资产提交/复核状态机退出 v5 |
| REQ-AST-004 | 已移除 | 开发中 | — | — | 旧资产详情口径由资产单元台账取代 |
| REQ-AST-005 | 已移除 | 开发中 | — | — | 旧产权证验收口径由 REQ-ARC-001 和资产单元多对多关系取代 |
| REQ-PRJ-001 | 已移除 | 开发中 | — | — | Project 从经营事实容器收窄为管理归属标签 |
| REQ-PRJ-002 | 已移除 | 开发中 | — | — | 项目经营记录退出 v5 |
| REQ-PRJ-003 | 已移除 | 开发中 | — | — | 项目经营闭环退出 v5 |
| REQ-RNT-001 | 已移除 | 开发中 | — | — | 签署文书/项目经营记录分层由上游/终端合同链取代 |
| REQ-RNT-002 | 已移除 | 开发中 | — | — | 出租授权冻结退出 v5 |
| REQ-RNT-003 | 已移除 | 开发中 | — | — | 意向、外部审批和合同生效检查退出 v5 |
| REQ-RNT-005 | 已移除 | 开发中 | — | — | 旧退场/催收闭环由 v5 终止、退出和押金登记的较小边界取代 |
| REQ-RNT-006 | 已移除 | 开发中 | — | — | 结算项、银行匹配、发票、催收退出 v5；租金登记和管理费分别进入新 REQ |
| REQ-DOC-001 | 已移除 | 开发中 | — | — | 旧扫描解析验收由合同录入会话和 REQ-ARC-001 重新定义 |
| REQ-ANA-001 | 已移除 | 开发中 | — | — | 经营分析、利润和多视角分析退出 v5 |

## 6. Out of Scope 追踪

| 能力 | 产品状态 | 实现状态 | 说明 |
|---|---|---|---|
| 招商意向、报价、底价和生效检查 | Out of Scope | 存量代码待迁移裁决 | 不进入 v5 页面、端点和验收 |
| 银行流水、匹配复核、发票和收付分配 | Out of Scope | 存量代码待迁移裁决 | v5 只登记外部已发生付款/到账 |
| 催收账户、催收案件和法务 | Out of Scope | 存量代码待迁移裁决 | 欠款继续在租金台账跨月展示 |
| 产权方门户和领导驾驶舱 | Out of Scope | 原型资产已归档 | 不提供外部账号或第二业务视角 |
| 巡检、维修和改造工单 | Out of Scope | 不纳入当前验收 | 仅可在空置原因或档案备注中引用外部结果 |

## 7. 实施映射

2026-10-27，本次 V1 交付切片的双轴复核及完整 CI 已通过，[实施计划已归档](../archive/backend-plans/2026-10-23-asset-operations-v5-v1.md)，执行证据与边界见 [PR #95 复核记录](../archive/reviews/2026-10-27-asset-operations-v5-v1-pr95-review.md)。这不替代完整 REQ 的产品验收；REQ-UNT-001 继续保持开发中。

| 切片 | REQ | 状态 |
|---|---|---|
| V1 资产单元与合同链 | REQ-UNT-001、REQ-CTR-001、REQ-CTR-002 | 本实施切片已有证据；V1-0 至 V1-4 已形成模型、迁移、CRUD、服务、API 和约定的前端列表/详情/录入/生命周期纵向切片，V1-T01–V1-T10 均有自动化或真实 PostgreSQL/浏览器证据，旧业务路由和导航已清零。REQ-UNT-001 的生产端空置备注、拆合操作/历史与合同时间轴仍是合并后跟进项；证照/考核/台账依赖项分别进入 V4/V3/V2；未上线开发基线已直接切到 v5，旧域物理清理单独跟进 |
| V2 租金、押金与管理费 | REQ-LED-001、REQ-DEP-001、REQ-FEE-001 | PR-0 #97、租金 PR-A #98、押金 PR-B #99、管理费 PR-C #100 全部合入；真实 HTTP/并发/范围、完整应用浏览器走查、整体差异复核与 CI 全绿均有证据；2026-10-30 用户完成管理费（REQ-FEE-001）产品验收，V2 计划完结归档。REQ-LED-001 / REQ-DEP-001 维持各自行状态；遗留补收免租计入口径裁决移交 issue 跟踪 |
| V3 考核范围与报送 | REQ-RPT-001、REQ-RPT-002 | S0 规格已建立，迁移与测试清单待完成 |
| V4 档案与导入 | REQ-ARC-001、REQ-IMP-001 | S0 规格已建立，迁移与测试清单待完成 |
| V5 本月工作台 | REQ-WBK-001 | 依赖 V1–V4 投影 |

## 8. 维护规则

- 产品状态变化同步 `docs/prd.md`。
- 字段、状态或统计口径变化同步 `docs/specs/domain-model.md`。
- API、权限、幂等和错误变化同步 `docs/specs/api-contract.md`。
- 只有本文档记录实现状态、代码证据和测试证据。
- 资金流、状态机和数据范围需求开始实现前，必须把新 REQ 加入 E2E 准入守卫并先提交失败测试。
