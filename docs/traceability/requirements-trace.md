# 需求追踪矩阵

## 1. 文档定位

本文档记录 REQ 到实现状态、代码证据和测试证据的映射。产品目标态见 `docs/prd.md`，字段和状态口径见 `docs/specs/domain-model.md`，API 契约见 `docs/specs/api-contract.md`。

本文档是实现追踪信息的归属地。PRD、领域模型契约和 API 契约不承载代码路径和测试路径。

## 2. 状态定义

| 状态类型 | 取值 | 含义 |
|---|---|---|
| 产品状态 | MVP | 当前 MVP 需求基线 |
| 产品状态 | vNext | 候选能力，不纳入当前 MVP 验收 |
| 产品状态 | Out of Scope | 当前明确不纳入范围 |
| 实现状态 | 未开始 | 尚无实现证据 |
| 实现状态 | 开发中 | 有部分实现或计划，尚未形成完整证据 |
| 实现状态 | 已有证据 | 已有代码和测试证据，仍需按产品验收标准最终确认 |
| 实现状态 | 已验收 | 已完成产品验收并可作为放量依据 |

## 3. 追踪矩阵

### 3.1 资产域

| REQ | 产品状态 | 实现状态 | 代码证据 | 测试证据 | 备注 |
|---|---|---|---|---|---|
| REQ-AST-001 | MVP | 已有证据 | `backend/src/api/v1/assets/assets.py`, `backend/src/services/asset/asset_service.py`, `backend/src/models/asset.py`, `backend/src/schemas/asset.py`, `frontend/src/services/assetService.ts` | `backend/tests/unit/api/v1/test_assets_projection_guard.py`, `backend/tests/unit/services/asset/test_asset_service.py` | 资产 CRUD、筛选、导入、附件和字段校验 |
| REQ-AST-002 | MVP | 已有证据 | `backend/src/models/project_asset.py`, `backend/src/models/asset_management_history.py`, `backend/src/crud/asset_management_history.py`, `backend/src/services/asset/asset_service.py` | `backend/tests/unit/test_req_ast_002.py` | 当前有效项目、主产权主体和经营方历史 |
| REQ-AST-003 | MVP | 已有证据 | `backend/src/models/asset_review_log.py`, `backend/src/services/asset/asset_service.py`, `backend/src/api/v1/assets/assets.py`, `frontend/src/pages/Assets/AssetDetailPage.tsx` | `backend/tests/unit/services/asset/test_asset_review.py`, `backend/tests/unit/api/v1/test_asset_review_api.py`, `backend/tests/unit/models/test_asset_review_status.py`, `backend/tests/unit/migration/test_req_ast_003_asset_review_migration.py`, `frontend/src/pages/Assets/__tests__/AssetDetailPage.test.tsx` | 资产审核、反审核、撤回和日志 |
| REQ-AST-004 | MVP | 已有证据 | `backend/src/crud/contract.py`, `backend/src/services/asset/asset_service.py`, `backend/src/api/v1/assets/assets.py`, `frontend/src/pages/Assets/AssetDetailPage.tsx`, `frontend/src/services/assetService.ts` | `backend/tests/unit/services/asset/test_asset_lease_summary.py`, `backend/tests/unit/api/v1/test_asset_lease_summary.py`, `frontend/src/pages/Assets/__tests__/AssetDetailPage.test.tsx` | 资产租赁摘要、客户摘要和合同级金额口径 |

### 3.2 项目域

| REQ | 产品状态 | 实现状态 | 代码证据 | 测试证据 | 备注 |
|---|---|---|---|---|---|
| REQ-PRJ-001 | MVP | 已有证据 | `backend/src/models/project.py`, `backend/src/schemas/project.py`, `backend/src/crud/project.py`, `backend/src/services/project/service.py`, `frontend/src/services/projectService.ts` | `backend/tests/unit/api/v1/test_project.py`, `backend/tests/unit/services/project/test_project_service.py` | 项目运营管理语义、项目编码、项目审核 |
| REQ-PRJ-002 | MVP | 已有证据 | `backend/src/api/v1/assets/project.py`, `backend/src/services/project/service.py`, `backend/src/schemas/project.py`, `frontend/src/pages/Project/ProjectDetailPage.tsx` | `backend/tests/unit/services/project/test_project_service.py`, `backend/tests/unit/api/v1/test_project.py` | 项目详情按当前有效资产汇总 |

### 3.3 租赁与合同组域

| REQ | 产品状态 | 实现状态 | 代码证据 | 测试证据 | 备注 |
|---|---|---|---|---|---|
| REQ-RNT-001 | MVP | 已有证据 | `backend/src/models/contract_group.py`, `backend/src/schemas/contract_group.py`, `backend/src/crud/contract_group.py`, `backend/src/crud/contract.py`, `backend/src/services/contract/contract_group_service.py`, `backend/src/api/v1/contracts/contract_groups.py` | `backend/tests/unit/services/contract/test_contract_group_service.py`, `backend/tests/unit/api/v1/test_contract_groups_layering.py` | 合同组五层模型和主业务对象 |
| REQ-RNT-002 | MVP | 已有证据 | `backend/src/models/contract_group.py`, `backend/src/services/contract/contract_group_service.py`, `backend/src/services/asset/asset_service.py`, `backend/src/services/analytics/analytics_service.py`, `frontend/src/pages/ContractGroup/ContractGroupDetailPage.tsx`, `frontend/src/pages/Assets/AssetDetailPage.tsx` | `backend/tests/unit/services/contract/test_contract_group_service.py`, `backend/tests/unit/services/asset/test_asset_lease_summary.py`, `backend/tests/unit/services/analytics/test_analytics_service.py`, `frontend/src/pages/ContractGroup/__tests__/ContractGroupDetailPage.test.tsx`, `frontend/src/pages/Assets/__tests__/AssetDetailPage.test.tsx` | 承租/代理双模式和一资产一有效合同组 |
| REQ-RNT-003 | MVP | 已有证据 | `backend/src/models/contract_group.py`, `backend/src/services/contract/contract_group_service.py`, `backend/src/api/v1/contracts/contract_groups.py` | `backend/tests/unit/api/v1/test_contract_lifecycle_api.py`, `backend/tests/unit/services/contract/test_contract_group_service.py` | 合同生命周期、合同组派生状态和审计日志 |
| REQ-RNT-004 | MVP | 已有证据 | `backend/src/services/contract/contract_group_service.py`, `backend/src/models/contract_group.py`, `backend/src/schemas/contract_group.py`, `backend/src/api/v1/contracts/contract_groups.py` | `backend/tests/unit/services/contract/test_contract_joint_review.py`, `backend/tests/unit/api/v1/test_contract_lifecycle_api.py` | 关键合同联审 |
| REQ-RNT-005 | MVP | 已有证据 | `backend/src/services/contract/contract_group_service.py`, `backend/src/services/contract/ledger_service_v2.py`, `backend/src/crud/contract_group.py`, `backend/src/api/v1/contracts/contract_groups.py` | `backend/tests/unit/services/contract/test_contract_correction_flow.py`, `backend/tests/unit/api/v1/test_contract_lifecycle_api.py` | 反审核、纠错、作废、冲销和重建 |
| REQ-RNT-006 | MVP | 已有证据 | `backend/src/api/v1/contracts/ledger.py`, `backend/src/services/contract/ledger_service_v2.py`, `backend/src/services/contract/ledger_export_service.py`, `backend/src/services/contract/ledger_compensation_service.py`, `backend/src/services/contract/service_fee_ledger_service.py`, `backend/scripts/maintenance/run_ledger_compensation.py` | `backend/tests/unit/services/contract/test_ledger_service_v2.py`, `backend/tests/unit/services/contract/test_ledger_export_service.py`, `backend/tests/unit/services/contract/test_ledger_compensation_service.py`, `backend/tests/unit/services/contract/test_service_fee_ledger_service.py`, `backend/tests/unit/api/v1/test_ledger_api.py` | 台账生成、查询、导出、补偿和服务费台账 |

### 3.4 客户域

| REQ | 产品状态 | 实现状态 | 代码证据 | 测试证据 | 备注 |
|---|---|---|---|---|---|
| REQ-CUS-001 | MVP | 已有证据 | `backend/src/services/party/service.py`, `backend/src/schemas/party.py`, `backend/src/api/v1/party.py`, `frontend/src/pages/Customer/CustomerDetailPage.tsx`, `frontend/src/pages/System/PartyDetailPage.tsx` | `backend/tests/unit/services/test_party_service.py`, `backend/tests/unit/api/v1/test_party_api.py`, `frontend/src/pages/Customer/__tests__/CustomerDetailPage.test.tsx`, `frontend/src/pages/System/__tests__/PartyPages.test.tsx` | 客户增强信息、风险标签和历史签约 |
| REQ-CUS-002 | MVP | 已有证据 | `backend/src/services/analytics/analytics_service.py`, `backend/src/services/analytics/analytics_export_service.py`, `frontend/src/components/Analytics/AnalyticsStatsCard.tsx`, `frontend/src/types/analytics.ts`, `frontend/src/services/analyticsService.ts` | `backend/tests/unit/services/analytics/test_analytics_service.py`, `backend/tests/unit/services/analytics/test_analytics_export_service.py`, `frontend/src/components/Analytics/__tests__/RevenueStatsGrid.test.tsx`, `frontend/src/services/__tests__/analyticsService.test.ts` | 客户主体数和客户合同数 |

### 3.5 搜索域

| REQ | 产品状态 | 实现状态 | 代码证据 | 测试证据 | 备注 |
|---|---|---|---|---|---|
| REQ-SCH-001 | MVP | 已有证据 | `backend/src/api/v1/search.py`, `backend/src/services/search/service.py`, `backend/src/schemas/search.py`, `frontend/src/services/searchService.ts`, `frontend/src/pages/Search/GlobalSearchPage.tsx`, `frontend/src/components/Layout/AppHeader.tsx` | `backend/tests/unit/services/search/test_search_service.py`, `backend/tests/unit/api/v1/test_search_api.py`, `frontend/src/services/__tests__/searchService.test.ts`, `frontend/src/pages/Search/__tests__/GlobalSearchPage.test.tsx`, `frontend/src/components/Layout/__tests__/AppHeader.test.tsx` | MVP 搜索覆盖资产、项目、合同组、合同、客户 |
| REQ-SCH-002 | MVP | 已有证据 | `backend/src/services/search/service.py`, `frontend/src/pages/Search/GlobalSearchPage.tsx` | `backend/tests/unit/services/search/test_search_service.py`, `frontend/src/pages/Search/__tests__/GlobalSearchPage.test.tsx` | 搜索结果分组和排序 |
| REQ-SCH-003 | MVP | 已有证据 | `backend/src/api/v1/search.py`, `backend/src/services/search/service.py`, `backend/src/services/authz/resource_perspective_registry.py` | `backend/tests/unit/api/v1/test_search_api.py`, `backend/tests/unit/services/search/test_search_service.py` | 搜索权限过滤和数据范围收口 |

### 3.6 认证与授权域

| REQ | 产品状态 | 实现状态 | 代码证据 | 测试证据 | 备注 |
|---|---|---|---|---|---|
| REQ-AUTH-001 | MVP | 已有证据 | `backend/src/api/v1/auth/auth_modules/authentication.py`, `backend/src/security/cookie_manager.py`, `backend/src/middleware/auth.py`, `frontend/src/api/client.ts`, `frontend/src/services/authService.ts`, `backend/src/services/permission/rbac_service.py` | `backend/tests/unit/middleware/test_optional_auth.py`, `backend/tests/unit/api/v1/test_roles_permission_grants.py` | Cookie 会话、刷新、退出和统一鉴权 |
| REQ-AUTH-002 | MVP | 已有证据 | `backend/src/services/authz/service.py`, `backend/src/middleware/auth.py`, `backend/src/services/party_scope.py`, `backend/src/crud/project.py`, `backend/src/api/v1/analytics/analytics.py`, `frontend/src/api/client.ts`, `frontend/src/stores/dataScopeStore.ts`, `frontend/src/utils/queryScope.ts` | `backend/tests/unit/services/test_authz_service.py`, `backend/tests/unit/middleware/test_perspective_context.py`, `backend/tests/unit/middleware/test_perspective_context_optional.py`, `backend/tests/unit/services/test_party_scope.py`, `backend/tests/integration/api/test_project_visibility_real.py`, `backend/tests/integration/api/test_assets_visibility_real.py`, `frontend/src/api/__tests__/client.test.ts`, `frontend/src/stores/__tests__/dataScopeStore.test.ts`, `frontend/src/utils/__tests__/queryScope.test.ts` | 数据范围自动注入和 ViewMode 分析口径 |
| REQ-AUTH-003 | MVP | 已有证据 | `backend/src/services/authz/service.py`, `backend/src/services/authz/engine.py`, `backend/src/services/authz/cache.py`, `backend/src/services/authz/data_policy_service.py`, `backend/src/services/authz/events.py`, `backend/src/api/v1/auth/data_policies.py` | `backend/tests/unit/services/test_authz_service.py`, `backend/tests/unit/services/test_data_policy_service.py`, `backend/tests/unit/migration/test_backfill.py` | ABAC 策略包、角色绑定、deny 优先、日志模式和缓存失效 |

### 3.7 文档与分析域

| REQ | 产品状态 | 实现状态 | 代码证据 | 测试证据 | 备注 |
|---|---|---|---|---|---|
| REQ-DOC-001 | MVP | 已有证据 | `backend/src/api/v1/documents/pdf_import.py`, `backend/src/api/v1/documents/pdf_upload.py`, `backend/src/api/v1/documents/pdf_batch_routes.py` | `backend/tests/unit/api/v1/documents/test_pdf_import_routes.py` | PDF 上传、抽取、人工修正、重试和批量进度 |
| REQ-ANA-001 | MVP | 已有证据 | `backend/src/api/v1/analytics/analytics.py`, `backend/src/services/analytics/analytics_service.py`, `backend/src/services/analytics/analytics_export_service.py`, `backend/src/services/excel/excel_export_service.py`, `frontend/src/services/analyticsService.ts`, `frontend/src/hooks/useAssetAnalytics.ts`, `frontend/src/components/Analytics/AnalyticsDashboard.tsx` | `backend/tests/unit/services/analytics/test_analytics_service.py`, `backend/tests/unit/api/v1/test_analytics.py`, `backend/tests/unit/api/v1/analytics/test_statistics.py`, `backend/tests/unit/services/analytics/test_analytics_export_service.py`, `frontend/src/services/__tests__/analyticsService.test.ts`, `frontend/src/hooks/__tests__/useAssetAnalytics.test.ts`, `frontend/src/components/Analytics/__tests__/RevenueStatsGrid.test.tsx` | 经营分析、收入拆分、实收、收缴率和导出 |

### 3.8 主体与审批域

| REQ | 产品状态 | 实现状态 | 代码证据 | 测试证据 | 备注 |
|---|---|---|---|---|---|
| REQ-PTY-001 | MVP | 已有证据 | `backend/src/models/party.py`, `backend/src/schemas/party.py`, `backend/src/crud/party.py`, `backend/src/services/party/service.py`, `backend/src/api/v1/party.py`, `frontend/src/pages/System/PartyListPage.tsx`, `frontend/src/pages/System/PartyDetailPage.tsx` | `backend/tests/unit/services/test_party_service.py`, `backend/tests/unit/api/v1/test_party_api.py`, `frontend/src/pages/System/__tests__/PartyPages.test.tsx` | Party 单一主档、去重、启停用和审计 |
| REQ-PTY-002 | MVP | 已有证据 | `backend/src/models/party.py`, `backend/src/services/party/service.py`, `backend/src/api/v1/party.py`, `backend/src/services/contract/contract_group_service.py`, `frontend/src/components/Common/PartySelector.tsx`, `frontend/src/pages/System/partyImport.ts`, `frontend/src/services/partyService.ts` | `backend/tests/unit/services/test_party_service.py`, `backend/tests/unit/api/v1/test_party_api.py`, `backend/tests/unit/services/contract/test_contract_group_service.py`, `frontend/src/pages/System/__tests__/PartyPages.test.tsx`, `frontend/src/components/Common/__tests__/PartySelector.test.tsx` | 主体导入、业务过程创建和合同提审门禁 |
| REQ-APR-001 | MVP | 已有证据 | `backend/src/models/approval.py`, `backend/src/crud/approval.py`, `backend/src/schemas/approval.py`, `backend/src/services/approval/service.py`, `backend/src/api/v1/approval.py`, `backend/src/services/asset/asset_service.py`, `backend/src/services/notification/notification_service.py` | `backend/tests/unit/services/approval/test_approval_service.py`, `backend/tests/unit/api/v1/test_approval_api.py`, `backend/tests/unit/services/asset/test_asset_review.py` | 资产审批第一阶段闭环 |

### 3.9 系统管理域

| REQ | 产品状态 | 实现状态 | 代码证据 | 测试证据 | 备注 |
|---|---|---|---|---|---|
| REQ-SYS-001 | MVP | 已有证据 | `backend/src/api/v1/auth/auth_modules/users.py`, `backend/src/services/core/user_management_service.py`, `backend/src/models/rbac.py`, `frontend/src/pages/System/UserManagement/`, `frontend/src/services/systemService.ts` | `backend/tests/unit/api/v1/test_users.py`, `backend/tests/unit/api/v1/test_authentication.py`, `frontend/src/services/__tests__/systemService.test.ts`, `frontend/src/pages/System/__tests__/UserManagementPage.test.tsx`, `frontend/src/pages/__tests__/ProfilePage.test.tsx`, `frontend/src/hooks/__tests__/useAuth.test.ts`, `frontend/src/services/__tests__/authService.test.ts` | 用户生命周期、多角色和权限管理员边界 |
| REQ-SYS-002 | MVP | 已有证据 | `backend/src/api/v1/auth/organization.py`, `backend/src/api/v1/party.py`, `frontend/src/pages/System/Organization/`, `frontend/src/pages/System/Organization/components/OrganizationBindingDrawer.tsx` | `backend/tests/unit/api/v1/test_organization.py`, `backend/tests/unit/api/v1/test_organization_layering.py`, `frontend/src/pages/System/__tests__/OrganizationPage.test.tsx`, `frontend/src/pages/System/Organization/components/__tests__/OrganizationBindingDrawer.test.tsx` | 组织 CRUD 和主体绑定维护 |
| REQ-SYS-003 | MVP | 已有证据 | `backend/src/api/v1/system/dictionaries.py`, `backend/src/api/v1/system/system_dictionaries.py`, `frontend/src/pages/System/DictionaryPage.tsx` | `backend/tests/unit/api/v1/test_dictionaries_layering.py`, `backend/tests/unit/api/v1/test_system_dictionaries_layering.py`, `frontend/src/pages/System/__tests__/DictionaryPage.test.tsx` | 数据字典分类和字典项维护 |

### 3.10 跨模块约束

| REQ | 产品状态 | 实现状态 | 代码证据 | 测试证据 | 备注 |
|---|---|---|---|---|---|
| REQ-XCUT-001 | MVP | 已有证据 | `backend/src/core/router_registry.py`, `backend/src/main.py` | `backend/tests/unit/api/v1/test_project_layering.py` | API 统一版本化 |
| REQ-XCUT-002 | MVP | 已有证据 | `backend/src/api/v1/`, `backend/src/services/` | `backend/tests/unit/api/v1/test_project_layering.py`, `backend/tests/unit/api/v1/test_authentication_layering.py` | 路由层不得承载业务规则 |
| REQ-XCUT-003 | MVP | 已有证据 | `backend/src/core/encryption.py`, `backend/src/crud/asset.py` | `backend/tests/unit/core/test_encryption.py` | PII 字段加密与开发降级 |
| REQ-XCUT-004 | MVP | 已有证据 | `frontend/src/constants/routes.ts`, `frontend/src/routes/AppRoutes.tsx` | `frontend/src/routes/__tests__/AppRoutes.authz-metadata.test.ts` | 前端导航与后端模块能力对齐 |

## 4. Out of Scope 追踪

| 能力 | 产品状态 | 实现状态 | 说明 |
|---|---|---|---|
| PropertyCertificate | Out of Scope | 代码骨架存在 | 产权证管理不纳入 MVP 功能验收 |
| Ownership | Out of Scope | 代码骨架存在 | 权属方管理不纳入 MVP 功能验收 |
| 通用 BPM 审批流引擎 | Out of Scope | 不纳入当前验收 | MVP 只交付资产审批第一阶段最小闭环 |
| 财务总账、税票、支付结算 | Out of Scope | 不纳入当前验收 | 当前只做运营台账和经营统计 |

## 5. 维护规则

- 新增或修改 REQ 时必须同步本文档。
- 产品状态变化同步 `docs/prd.md`。
- 字段、状态或统计口径变化同步 `docs/specs/domain-model.md`。
- API 契约变化同步 `docs/specs/api-contract.md`。
- 实现状态变化只修改本文档，不回写 PRD。
- 代码证据和测试证据路径应尽量使用仓库内真实路径。
