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

2026-10-27 PR #95 合并门禁补充：`frontend/tests/e2e/asset-flow.spec.ts`、`frontend/tests/e2e/auth/organization-scope-isolation.spec.ts` 与 `frontend/tests/e2e/smoke/main-pages-render.spec.ts` 已迁移到 v5 生产路径；隔离用例通过 `backend/scripts/dev_seed_v5_walkthrough.py` 的两方真实资产验证授权范围，旧入口有明确 404 断言。当前静态检查通过，真实浏览器结果待本轮 CI；这不改变 REQ-UNT-001 的开发中状态。

| REQ | 产品状态 | 实现状态 | 代码证据 | 测试证据 | 备注 |
|---|---|---|---|---|---|
| REQ-WBK-001 | MVP | 未开始 | — | — | 本月截止事项与随时处理事项均为派生投影，不建立通用待办写模型 |
| REQ-UNT-001 | MVP | 开发中 | `backend/src/models/asset_unit.py`, `backend/src/crud/asset_unit.py`, `backend/src/crud/asset_unit_boundary.py`, `backend/src/services/asset_operations/boundary_command_service.py`, `backend/src/services/asset_operations/query_service.py`, `backend/src/api/v1/asset_units.py`, `backend/src/scripts/migration/asset_operations_v5/preflight.py`, `frontend/src/services/assetOperationsService.ts`, `frontend/src/pages/AssetOperations/AssetUnitsPage.tsx`, `frontend/src/routes/AppRoutes.tsx` | `backend/tests/unit/crud/test_asset_unit_v5.py`, `backend/tests/unit/crud/test_asset_unit_boundary.py`, `backend/tests/unit/services/asset_operations/test_boundary_command_service.py`, `backend/tests/unit/services/asset_operations/test_boundary_merge_command_service.py`, `backend/tests/unit/services/asset_operations/test_asset_unit_views.py`, `backend/tests/unit/api/v1/test_asset_unit_boundary_api.py`, `backend/tests/integration/database/test_asset_unit_boundary_command.py`, `frontend/src/pages/AssetOperations/__tests__/AssetUnitsPage.test.tsx`, `frontend/src/routes/__tests__/AppRoutes.authz-metadata.test.ts` | V1 已完成资产单元预检、事实模型、范围化列表/详情、更新/空置备注 API、拆分/合并预览—提交 API 与生产列表/详情页；V1-T05/T06/T08/T09 覆盖面积守恒、权利边界、乐观锁和幂等，V1-T10 覆盖 loading/empty/403/error 四态。完整 REQ 仍缺生产端空置备注、拆合操作/历史与合同时间轴；证照关系、考核状态及联动筛选依规格分别进入 V4/V3，完成前不得标为“已有证据” |

### 3.2 已签合同

| REQ | 产品状态 | 实现状态 | 代码证据 | 测试证据 | 备注 |
|---|---|---|---|---|---|
| REQ-CTR-001 | MVP | 已有证据 | `backend/src/models/asset_contract.py`, `backend/src/crud/asset_contract.py`, `backend/src/services/asset_operations/contract_command_service.py`, `backend/src/services/asset_operations/contract_lifecycle_command_service.py`, `backend/src/services/asset_operations/query_service.py`, `backend/src/api/v1/contract_intake_sessions.py`, `backend/src/api/v1/upstream_contracts.py`, `frontend/src/services/assetOperationsService.ts`, `frontend/src/pages/AssetOperations/ContractIntakePage.tsx`, `frontend/src/pages/AssetOperations/ContractListsPage.tsx`, `frontend/src/pages/AssetOperations/LifecycleActionsPage.tsx` | `backend/tests/unit/services/asset_operations/test_contract_command_service.py`, `backend/tests/unit/services/asset_operations/test_contract_lifecycle_exit_preview.py`, `backend/tests/unit/services/asset_operations/test_contract_lifecycle_renewal.py`, `backend/tests/unit/services/asset_operations/test_contract_query_views.py`, `backend/tests/unit/api/v1/test_upstream_contract_exit_api.py`, `backend/tests/integration/database/test_asset_contract_command.py`, `backend/tests/integration/database/test_contract_lifecycle_command.py`, `frontend/src/pages/AssetOperations/__tests__/ContractIntakePage.test.tsx`, `frontend/src/pages/AssetOperations/__tests__/ContractListsPage.test.tsx`, `frontend/src/pages/AssetOperations/__tests__/LifecycleActionsPage.test.tsx`, `backend/tests/e2e/test_asset_contract_lifecycle_e2e.py` | 上游合同录入、列表/详情/更新、退出预览—提交—撤销和续签均已接入 API 与生产页面；Party 范围、共享单元锁、有效终端全局阻断、事件重放、唯一后继、扫描件改绑和持久幂等均有单元及真实 PostgreSQL 证据；V1-T04/T07/T08/T09/T10 已覆盖，仍待产品验收 |
| REQ-CTR-002 | MVP | 已有证据 | `backend/src/models/asset_contract.py`, `backend/src/crud/asset_contract.py`, `backend/src/services/asset_operations/contract_command_service.py`, `backend/src/services/asset_operations/contract_lifecycle_command_service.py`, `backend/src/services/asset_operations/query_service.py`, `backend/src/api/v1/contract_intake_sessions.py`, `backend/src/api/v1/terminal_contracts.py`, `frontend/src/services/assetOperationsService.ts`, `frontend/src/pages/AssetOperations/ContractIntakePage.tsx`, `frontend/src/pages/AssetOperations/ContractListsPage.tsx`, `frontend/src/pages/AssetOperations/LifecycleActionsPage.tsx` | `backend/tests/unit/services/asset_operations/test_contract_command_service.py`, `backend/tests/unit/services/asset_operations/test_contract_lifecycle_termination_preview.py`, `backend/tests/unit/services/asset_operations/test_contract_lifecycle_renewal.py`, `backend/tests/unit/services/asset_operations/test_contract_update_service.py`, `backend/tests/unit/services/asset_operations/test_contract_query_views.py`, `backend/tests/unit/api/v1/test_terminal_contract_termination_api.py`, `backend/tests/integration/database/test_asset_contract_command.py`, `backend/tests/integration/database/test_contract_lifecycle_command.py`, `frontend/src/pages/AssetOperations/__tests__/ContractIntakePage.test.tsx`, `frontend/src/pages/AssetOperations/__tests__/ContractListsPage.test.tsx`, `frontend/src/pages/AssetOperations/__tests__/LifecycleActionsPage.test.tsx`, `backend/tests/e2e/test_asset_contract_lifecycle_e2e.py` | 终端合同录入、列表/详情/更新、终止预览—提交—撤销和续签均已接入 API 与生产页面；允许已签事实在上游缺失/越界时登记并稳定派生 warning，同期覆盖、Party 范围、覆盖截止/恢复、后继阻断、扫描件消费和幂等回放均有单元及真实 PostgreSQL 证据；V1-T01–T03/T06–T10 已覆盖，仍待产品验收 |

### 3.3 租金、押金与委托管理费

| REQ | 产品状态 | 实现状态 | 代码证据 | 测试证据 | 备注 |
|---|---|---|---|---|---|
| REQ-LED-001 | MVP | 未开始 | — | — | 应付/应收义务、部分登记、跨月结转、凭证和有原因撤销；租金阶段更正（当月起生效）与提前退租补收免租 |
| REQ-DEP-001 | MVP | 未开始 | — | — | 应收未收、应付未付、应退未退、应收回四类方向；续签转入；合同结束后转租押金抵扣欠租（终止默认自动抵扣截至当月的欠租）；不退部分登记为押金扣除；委托管理协议无保证金 |
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
| V1 资产单元与合同链 | REQ-UNT-001、REQ-CTR-001、REQ-CTR-002 | 本实施切片已有证据；V1-0 至 V1-4 已形成模型、迁移、CRUD、服务、API 和约定的前端列表/详情/录入/生命周期纵向切片，V1-T01–V1-T10 均有自动化或真实 PostgreSQL/浏览器证据，旧业务路由和导航已清零。REQ-UNT-001 的生产端空置备注、拆合操作/历史与合同时间轴仍是合并后跟进项；证照/考核/台账依赖项分别进入 V4/V3/V2；目标环境数据切换与旧表清理属于合并后的部署工作 |
| V2 租金、押金与管理费 | REQ-LED-001、REQ-DEP-001、REQ-FEE-001 | 实施就绪：计划、迁移路径与失败测试清单见 `docs/plans/2026-10-27-asset-operations-v5-v2.md`（PR-0 至 PR-C），待 V1 合并后开工 |
| V3 考核范围与报送 | REQ-RPT-001、REQ-RPT-002 | S0 规格已建立，迁移与测试清单待完成 |
| V4 档案与导入 | REQ-ARC-001、REQ-IMP-001 | S0 规格已建立，迁移与测试清单待完成 |
| V5 本月工作台 | REQ-WBK-001 | 依赖 V1–V4 投影 |

## 8. 维护规则

- 产品状态变化同步 `docs/prd.md`。
- 字段、状态或统计口径变化同步 `docs/specs/domain-model.md`。
- API、权限、幂等和错误变化同步 `docs/specs/api-contract.md`。
- 只有本文档记录实现状态、代码证据和测试证据。
- 资金流、状态机和数据范围需求开始实现前，必须把新 REQ 加入 E2E 准入守卫并先提交失败测试。
