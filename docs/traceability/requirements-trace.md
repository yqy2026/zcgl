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

| REQ | 产品状态 | 实现状态 | 代码证据 | 测试证据 | 备注 |
|---|---|---|---|---|---|
| REQ-WBK-001 | MVP | 未开始 | — | — | 本月截止事项与随时处理事项均为派生投影，不建立通用待办写模型 |
| REQ-UNT-001 | MVP | 开发中 | `backend/src/models/asset_unit.py`, `backend/src/schemas/asset_operations.py`, `backend/src/crud/asset_unit.py`, `backend/src/crud/asset_unit_boundary.py`, `backend/src/services/asset_operations/query_service.py`, `backend/src/services/asset_operations/boundary_rules.py`, `backend/src/services/asset_operations/boundary_command_service.py`, `backend/src/api/v1/asset_units.py`, `backend/alembic/versions/20261023_asset_operations_v5_asset_units.py`, `backend/src/scripts/migration/asset_operations_v5/preflight.py` | `backend/tests/unit/models/test_asset_unit.py`, `backend/tests/unit/schemas/test_asset_operations.py`, `backend/tests/unit/crud/test_asset_unit_v5.py`, `backend/tests/unit/crud/test_asset_unit_boundary.py`, `backend/tests/unit/services/asset_operations/test_query_service.py`, `backend/tests/unit/services/asset_operations/test_boundary_rules.py`, `backend/tests/unit/services/asset_operations/test_boundary_command_service.py`, `backend/tests/unit/services/asset_operations/test_boundary_merge_command_service.py`, `backend/tests/unit/api/v1/test_asset_unit_boundary_api.py`, `backend/tests/integration/database/test_asset_unit_boundary_command.py`, `backend/tests/unit/migration/test_asset_operations_v5_asset_units_migration.py`, `backend/tests/unit/migration/test_asset_operations_v5_preflight.py` | 预检、持久化、严格 schema、范围化查询及拆分/合并预览—提交服务/API 已完成；两条路径均覆盖共享资产单元行锁、唯一源消费、有效上游覆盖迁移、终端合同跨界阻断及 V1-T05/T06/T08/T09 的边界、版本和幂等语义，并有真实 PostgreSQL 事务、覆盖迁移与锁竞争证据；列表/详情/更新 API、证照/考核联动和页面尚未实现 |

### 3.2 已签合同

| REQ | 产品状态 | 实现状态 | 代码证据 | 测试证据 | 备注 |
|---|---|---|---|---|---|
| REQ-CTR-001 | MVP | 开发中 | `backend/src/models/asset_contract.py`, `backend/src/schemas/asset_operations.py`, `backend/src/crud/asset_contract.py`, `backend/src/services/asset_operations/query_service.py`, `backend/src/services/asset_operations/contract_projections.py`, `backend/src/services/asset_operations/contract_command_service.py`, `backend/src/services/asset_operations/contract_intake_service.py`, `backend/src/services/asset_operations/lifecycle_rules.py`, `backend/src/api/v1/contract_intake_sessions.py`, `backend/src/api/v1/upstream_contracts.py`, `backend/alembic/versions/20261023_asset_operations_v5_contracts.py`, `backend/alembic/versions/20261024_asset_contract_write_receipts.py`, `backend/src/scripts/migration/asset_operations_v5/preflight.py` | `backend/tests/unit/models/test_asset_contract.py`, `backend/tests/unit/schemas/test_asset_operations.py`, `backend/tests/unit/crud/test_asset_contract_v5.py`, `backend/tests/unit/services/asset_operations/test_query_service.py`, `backend/tests/unit/services/asset_operations/test_contract_projections.py`, `backend/tests/unit/services/asset_operations/test_contract_command_service.py`, `backend/tests/unit/services/asset_operations/test_contract_intake_service.py`, `backend/tests/unit/services/asset_operations/test_lifecycle_rules.py`, `backend/tests/unit/api/v1/test_contract_intake_api.py`, `backend/tests/unit/api/v1/test_upstream_contract_exit_api.py`, `backend/tests/unit/services/asset_operations/test_contract_query_views.py`, `backend/tests/integration/database/test_contract_lifecycle_command.py`, `backend/tests/unit/migration/test_asset_operations_v5_contracts_migration.py`, `backend/tests/unit/migration/test_asset_operations_v5_preflight.py`, `backend/tests/integration/database/test_asset_contract_command.py` | 上游合同录入会话与确认服务已完成扫描件、会话隔离、范围、共享单元锁、在管期间、产权方、租金阶段、原子聚合写入和持久幂等回放；上游退出预览/提交/撤销已完成——与终端终止同口径（生效日为新状态首日、覆盖截止到前一日、撤销为纠错恢复），有效终端合同按退出生效日重放派生并做无范围过滤的全局阻断，均有真实 PostgreSQL 证据；上游续签命令已完成——各方/类型/覆盖单元由前驱带出、后继起租晚于前驱覆盖截止、唯一后继阻断、后继+覆盖+租金阶段+扫描件+`renewed` 事件同事务、写回执幂等回放，有 PostgreSQL 证据；V1-T04、V1-T07 及创建/回放已有证据；上游列表/详情/更新端点已完成（更新走乐观锁与覆盖行 end_date 跟随）——列表行按事件重放派生状态、详情聚合逐单元覆盖/租金阶段/版本链（前驱-当前-后继）/关联终端合同/生命周期事件，批量查询经范围化批量方法避免 N+1，有 PostgreSQL 证据；列表页尚未实现 |
| REQ-CTR-002 | MVP | 开发中 | `backend/src/models/asset_contract.py`, `backend/src/schemas/asset_operations.py`, `backend/src/crud/asset_contract.py`, `backend/src/crud/asset_unit_boundary.py`, `backend/src/services/asset_operations/query_service.py`, `backend/src/services/asset_operations/contract_projections.py`, `backend/src/services/asset_operations/contract_command_service.py`, `backend/src/services/asset_operations/contract_intake_service.py`, `backend/src/services/asset_operations/contract_lifecycle_command_service.py`, `backend/src/services/asset_operations/boundary_rules.py`, `backend/src/services/asset_operations/boundary_command_service.py`, `backend/src/api/v1/asset_units.py`, `backend/src/api/v1/contract_intake_sessions.py`, `backend/src/api/v1/terminal_contracts.py`, `backend/alembic/versions/20261023_asset_operations_v5_contracts.py`, `backend/alembic/versions/20261024_asset_contract_write_receipts.py`, `backend/src/scripts/migration/asset_operations_v5/preflight.py` | `backend/tests/unit/models/test_asset_contract.py`, `backend/tests/unit/schemas/test_asset_operations.py`, `backend/tests/unit/crud/test_asset_contract_v5.py`, `backend/tests/unit/crud/test_asset_unit_boundary.py`, `backend/tests/unit/services/asset_operations/test_query_service.py`, `backend/tests/unit/services/asset_operations/test_contract_projections.py`, `backend/tests/unit/services/asset_operations/test_contract_command_service.py`, `backend/tests/unit/services/asset_operations/test_contract_intake_service.py`, `backend/tests/unit/services/asset_operations/test_contract_lifecycle_command_service.py`, `backend/tests/unit/services/asset_operations/test_contract_lifecycle_termination_preview.py`, `backend/tests/unit/services/asset_operations/test_contract_lifecycle_exit_preview.py`, `backend/tests/unit/services/asset_operations/test_contract_lifecycle_renewal.py`, `backend/tests/unit/services/asset_operations/test_asset_unit_views.py`, `backend/tests/unit/services/asset_operations/test_contract_update_service.py`, `backend/tests/unit/services/asset_operations/test_contract_query_views.py`, `backend/tests/unit/services/asset_operations/test_boundary_rules.py`, `backend/tests/unit/services/asset_operations/test_boundary_merge_command_service.py`, `backend/tests/unit/api/v1/test_asset_unit_boundary_api.py`, `backend/tests/unit/api/v1/test_contract_intake_api.py`, `backend/tests/unit/api/v1/test_terminal_contract_termination_api.py`, `backend/tests/unit/services/asset_operations/test_contract_query_views.py`, `backend/tests/unit/services/asset_operations/test_contract_update_service.py`, `backend/tests/unit/services/asset_operations/test_asset_unit_views.py`, `backend/tests/integration/database/test_asset_unit_boundary_command.py`, `backend/tests/integration/database/test_asset_contract_command.py`, `backend/tests/integration/database/test_contract_lifecycle_command.py`, `backend/tests/unit/migration/test_asset_operations_v5_contracts_migration.py`, `backend/tests/unit/migration/test_asset_operations_v5_preflight.py` | V1-T01–V1-T03、V1-T06、V1-T07、V1-T09 已由投影、范围查询、合并写服务/API、终止事件命令和 PostgreSQL 并发回放覆盖；终端录入会话允许上游缺失/租期越界 warning，按上游或已锁单元的产权方/项目运营方校验模式与出租方，锁内阻断同期覆盖并原子持久化回执；终止口径已裁定（生效日为新状态首日，最后有效日为前一日），终止命令在同事务截止覆盖行、阻断重复终止，预览/提交端点已接线并有 PostgreSQL 覆盖截止、后继合同不触发排斥约束与预览漂移证据；终止撤销为纠错事实——显式指向原事件、目标无效失败关闭、续签后继或他合同覆盖阻断、被截止覆盖行恢复到合同 `end_date`、撤销后可再终止，均有真实 PostgreSQL 证据；终端列表/详情端点已完成——列表行重放事件派生状态并重算上游缺失/越界/缺扫描件 warning（公共错误码），详情聚合覆盖/租金阶段/版本链/事件，有 PostgreSQL 证据；生产前端页面尚未实现 |

### 3.3 租金、押金与委托管理费

| REQ | 产品状态 | 实现状态 | 代码证据 | 测试证据 | 备注 |
|---|---|---|---|---|---|
| REQ-LED-001 | MVP | 未开始 | — | — | 应付/应收义务、部分登记、跨月结转、凭证和有原因撤销 |
| REQ-DEP-001 | MVP | 未开始 | — | — | 应收未收、应退未退、应收回三类方向 |
| REQ-FEE-001 | MVP | 未开始 | — | — | 产权方实际到账 × 协议比例，双方盖章后锁定月度对账 |

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
| REQ-AUTH-001 | MVP | 已有证据 | `backend/src/api/v1/auth/`, `backend/src/services/authz/`, `frontend/src/routes/AppRoutes.tsx` | `backend/tests/e2e/test_auth_flow_e2e.py` | 会话、CSRF、受保护路由和统一鉴权继续保留 |
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

| 切片 | REQ | 状态 |
|---|---|---|
| V1 资产单元与合同链 | REQ-UNT-001、REQ-CTR-001、REQ-CTR-002 | 开发中；V1-0 预检、V1-1 事实模型/严格 schema/范围化 CRUD 已完成，V1-T01–V1-T09 已有投影、服务或 PostgreSQL 集成证据；拆分/合并预览—提交 API 与 `asset_ops` 能力已接线，共享资产单元写锁协议已固化，已签上游/终端合同录入会话、确认写服务、终止事件幂等核心与持久回执已完成；终端终止影响模型（覆盖截止到生效日前一日、重复终止阻断）、终止预览/提交端点、终止撤销（纠错恢复 + 后继阻断）与上游退出预览/提交/撤销（有效终端合同全局阻断 + 同口径覆盖截止与撤销恢复）已完成并有 PostgreSQL 证据；两类续签命令（前驱事实带出 + 唯一后继 + 同事务建链 + 写回执幂等）已完成并有 PostgreSQL 证据；两类合同列表/详情端点已完成（列表行重放事件派生状态与 warning、详情聚合覆盖/租金阶段/版本链/事件，批量方法防 N+1）；合同更新端点、资产单元列表/更新端点和页面待实现 |
| V2 租金、押金与管理费 | REQ-LED-001、REQ-DEP-001、REQ-FEE-001 | S0 规格已建立，迁移与测试清单待完成 |
| V3 考核范围与报送 | REQ-RPT-001、REQ-RPT-002 | S0 规格已建立，迁移与测试清单待完成 |
| V4 档案与导入 | REQ-ARC-001、REQ-IMP-001 | S0 规格已建立，迁移与测试清单待完成 |
| V5 本月工作台 | REQ-WBK-001 | 依赖 V1–V4 投影 |

## 8. 维护规则

- 产品状态变化同步 `docs/prd.md`。
- 字段、状态或统计口径变化同步 `docs/specs/domain-model.md`。
- API、权限、幂等和错误变化同步 `docs/specs/api-contract.md`。
- 只有本文档记录实现状态、代码证据和测试证据。
- 资金流、状态机和数据范围需求开始实现前，必须把新 REQ 加入 E2E 准入守卫并先提交失败测试。
