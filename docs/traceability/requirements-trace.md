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
| REQ-AST-003 | MVP | 已有证据 | `backend/src/models/asset_review_log.py`, `backend/src/services/asset/asset_service.py`, `backend/src/api/v1/assets/assets.py`, `backend/src/api/v1/assets/asset_batch.py`, `frontend/src/pages/Assets/AssetDetailPage.tsx`, `frontend/src/pages/Assets/AssetListPage.tsx`, `frontend/src/services/asset/assetCoreService.ts` | `backend/tests/unit/services/asset/test_asset_review.py`, `backend/tests/unit/api/v1/test_asset_review_api.py`, `backend/tests/unit/api/v1/test_asset_batch_layering.py`, `backend/tests/unit/api/test_asset_batch_api.py`, `backend/tests/unit/models/test_asset_review_status.py`, `backend/tests/unit/migration/test_req_ast_003_asset_review_migration.py`, `frontend/src/pages/Assets/__tests__/AssetDetailPage.test.tsx`, `frontend/src/pages/Assets/__tests__/AssetListPage.test.tsx`, `frontend/src/services/__tests__/assetService.test.ts` | 资产两步确认、反审核、撤回和日志；已取消审核人/提交人互斥，确认仅按复核权限门控，并支持批量提交 `draft → pending` 与批量确认 `pending → approved`。 |
| REQ-AST-004 | MVP | 已有证据 | `backend/src/crud/contract.py`, `backend/src/services/asset/asset_service.py`, `backend/src/api/v1/assets/assets.py`, `frontend/src/pages/Assets/AssetDetailPage.tsx`, `frontend/src/services/assetService.ts` | `backend/tests/unit/services/asset/test_asset_lease_summary.py`, `backend/tests/unit/api/v1/test_asset_lease_summary.py`, `frontend/src/pages/Assets/__tests__/AssetDetailPage.test.tsx` | 资产租赁摘要、客户摘要和合同级金额口径 |
| REQ-AST-005 | MVP | 开发中 | `backend/src/models/property_certificate.py`, `backend/src/models/certificate_party_relation.py`, `backend/src/crud/property_certificate.py`, `backend/src/services/property_certificate/service.py`, `backend/src/api/v1/assets/property_certificate.py`, `backend/src/services/document/extractors/property_cert_adapter.py`, `frontend/src/services/propertyCertificateService.ts`, `frontend/src/types/propertyCertificate.ts`, `frontend/src/pages/PropertyCertificate/` | `frontend/src/services/__tests__/propertyCertificateService.test.ts`, `frontend/src/pages/PropertyCertificate/__tests__/PropertyCertificateImport.test.tsx`, `frontend/src/pages/PropertyCertificate/__tests__/PropertyCertificateDetailPage.test.tsx` | 产权证管理已有存量实现证据；本轮删除 `is_verified` 核验状态与“未核验”风险，正式保存硬门槛只保留证号唯一且非空、至少一个既有资产关联、至少一份附件、权利人引用已审核 Party。 |

### 3.2 项目域

| REQ | 产品状态 | 实现状态 | 代码证据 | 测试证据 | 备注 |
|---|---|---|---|---|---|
| REQ-PRJ-001 | MVP | 已有证据 | `backend/src/models/project.py`, `backend/src/schemas/project.py`, `backend/src/crud/project.py`, `backend/src/services/project/service.py`, `frontend/src/services/projectService.ts` | `backend/tests/unit/api/v1/test_project.py`, `backend/tests/unit/services/project/test_project_service.py` | 项目运营管理语义、项目编码、项目审核 |
| REQ-PRJ-002 | MVP | 已有证据 | `backend/src/api/v1/assets/project.py`, `backend/src/services/project/service.py`, `backend/src/schemas/project.py`, `frontend/src/pages/Project/ProjectDetailPage.tsx` | `backend/tests/unit/services/project/test_project_service.py`, `backend/tests/unit/api/v1/test_project.py` | 项目详情按当前有效资产汇总 |
| REQ-PRJ-003 | MVP | 已有证据 | `backend/src/api/v1/assets/project.py`, `backend/src/services/project/service.py`, `backend/src/schemas/project.py`, `backend/src/crud/contract_group.py`, `backend/src/services/analytics/analytics_service.py`, `frontend/src/services/projectService.ts`, `frontend/src/services/ledgerService.ts`, `frontend/src/pages/Project/ProjectDetailPage.tsx`, `frontend/src/pages/ContractGroup/ContractGroupFormPage.tsx`, `frontend/src/pages/ContractGroup/ContractInGroupFormPage.tsx`, `frontend/src/pages/Assets/AssetAnalyticsPage.tsx`, `frontend/src/pages/Finance/FinancialLedgerPage.tsx`, `frontend/src/config/menuConfig.tsx` | `backend/tests/unit/services/project/test_project_service.py`, `backend/tests/unit/api/v1/test_project_layering.py`, `backend/tests/unit/api/v1/test_project.py`, `backend/tests/unit/services/analytics/test_analytics_service.py`, `frontend/src/services/__tests__/projectService.test.ts`, `frontend/src/services/__tests__/ledgerService.test.ts`, `frontend/src/pages/Project/__tests__/ProjectDetailPage.test.tsx`, `frontend/src/pages/Assets/__tests__/AssetAnalyticsPage.test.tsx`, `frontend/src/pages/Finance/__tests__/FinancialLedgerPage.test.tsx`, `frontend/src/config/__tests__/menuConfig.perspective-grouping.test.tsx`, `frontend/src/pages/ContractGroup/__tests__/ContractGroupFormPage.test.tsx`, `frontend/src/pages/ContractGroup/__tests__/ContractInGroupFormPage.test.tsx` | 项目详情已承载当前有效资产、合同关系、收付款摘要、租户/客户、风险提示和项目分析入口。`GET /api/v1/projects/{project_id}/ledger-summary` 按“承租模式下游租金 + 代理服务费计入项目应收、承租模式上游租金计入项目应付、代理直租租金不计入运营方自营应收”的口径聚合应收、应付、实收、实付、逾期和服务费；`GET /api/v1/projects/{project_id}/risks` 不再生成 `missing_primary_contract` / `coverage_conflict` 主合同覆盖类风险，仅保留人工风险标签、合同到期提醒、付款逾期、产权证数据质量和空置等派生风险；`GET /api/v1/projects/{project_id}/tenants` 返回终端租户/客户摘要；`GET /api/v1/projects/{project_id}/analytics` 按承租转租、代理运营分区展示关系、资产、客户、收付款和风险指标，并返回按账期聚合的月度收付款趋势。前端项目详情已展示合同关系、收付款摘要、风险提示、租户/客户和项目分析趋势；全局经营分析已支持项目维度和经营模式分区，普通导航已按目标顺序重排为工作台、项目运营、资产资源、合同中心、财务台账、主体中心、经营分析、系统管理；全局财务台账页面已接入 `/api/v1/ledger/entries` 与导出接口，支持跨项目按账期、支付状态、合同、资产和主体筛选。 |

### 3.3 租赁与合同关系域

| REQ | 产品状态 | 实现状态 | 代码证据 | 测试证据 | 备注 |
|---|---|---|---|---|---|
| REQ-RNT-001 | MVP | 已有证据 | `backend/src/models/contract_group.py`, `backend/src/schemas/contract_group.py`, `backend/src/crud/contract_group.py`, `backend/src/crud/contract.py`, `backend/src/services/contract/contract_group_service.py`, `backend/src/api/v1/contracts/contract_groups.py`, `backend/src/api/v1/assets/project.py`, `backend/alembic/versions/20260513_project_contract_relation_phase1a.py`, `frontend/src/types/contractGroup.ts`, `frontend/src/config/menuConfig.tsx`, `frontend/src/config/breadcrumb.ts`, `frontend/src/constants/routes.ts`, `frontend/src/constants/api.ts`, `frontend/src/services/contractGroupService.ts`, `frontend/src/pages/Project/ProjectDetailPage.tsx`, `frontend/src/pages/ContractGroup/ContractGroupListPage.tsx`, `frontend/src/pages/ContractGroup/ContractGroupFormPage.tsx`, `frontend/src/pages/ContractGroup/ContractGroupDetailPage.tsx`, `frontend/src/pages/ContractGroup/ContractInGroupFormPage.tsx` | `backend/tests/unit/migration/test_project_contract_relation_phase1a_migration.py`, `backend/tests/unit/services/contract/test_contract_group_service.py`, `backend/tests/unit/services/project/test_project_service.py`, `backend/tests/unit/api/v1/test_contract_groups_layering.py`, `backend/tests/unit/api/v1/test_project_layering.py`, `frontend/src/services/__tests__/contractGroupService.test.ts`, `frontend/src/config/__tests__/menuConfig.perspective-grouping.test.tsx`, `frontend/src/config/__tests__/rental-retired-navigation.test.ts`, `frontend/src/constants/__tests__/routes.contract-resource.test.ts`, `frontend/src/components/Layout/__tests__/AppSidebar.test.tsx`, `frontend/src/pages/Project/__tests__/ProjectDetailPage.test.tsx`, `frontend/src/pages/ContractGroup/__tests__/ContractGroupListPage.test.tsx`, `frontend/src/pages/ContractGroup/__tests__/ContractGroupFormPage.test.tsx`, `frontend/src/pages/ContractGroup/__tests__/ContractGroupDetailPage.test.tsx`, `frontend/src/pages/ContractGroup/__tests__/ContractInGroupFormPage.test.tsx` | ContractGroup 已新增 `project_id` 归属字段；普通用户侧“合同关系”展示投影已在项目接口、菜单、面包屑、列表、表单和明细页落地；创建路径已改为项目详情发起，提交 `project_id`、项目内选中的 `asset_ids`、选择的主体 ID，以及由业务字段转换出的结算/收益规则对象；列表、明细页和表单编辑模式以“承租转租 / 代理运营 / 上游承租合同”等业务文案替代枚举与主体 ID；前端已接入关系内新增合同端点，并提供项目详情发起的四类合同录入表单，其中委托协议使用“委托方/受托方”标签，服务费比例按用户输入百分比转换为后端 0-1 小数；新增合同提交前会校验项目上下文和资产范围；合同关系列表接口和页面已补充所属项目名称与合同角色数量。 |
| REQ-RNT-002 | MVP | 已有证据 | `backend/src/models/contract_group.py`, `backend/src/services/contract/contract_group_service.py`, `backend/src/services/asset/asset_service.py`, `backend/src/services/analytics/analytics_service.py`, `frontend/src/pages/ContractGroup/ContractGroupDetailPage.tsx`, `frontend/src/pages/Assets/AssetDetailPage.tsx` | `backend/tests/unit/services/contract/test_contract_group_service.py`, `backend/tests/unit/services/asset/test_asset_lease_summary.py`, `backend/tests/unit/services/analytics/test_analytics_service.py`, `frontend/src/pages/ContractGroup/__tests__/ContractGroupDetailPage.test.tsx`, `frontend/src/pages/Assets/__tests__/AssetDetailPage.test.tsx` | 承租/代理双模式已有证据；合同关系服务会按模式约束合同角色，资产租赁摘要和经营分析按承租转租、代理运营拆分口径展示；资产覆盖校验已调整为项目内可复用、跨项目或无项目归属冲突仍阻断。 |
| REQ-RNT-003 | MVP | 已有证据 | `backend/src/models/contract_group.py`, `backend/src/services/contract/contract_group_service.py`, `backend/src/api/v1/contracts/contract_groups.py` | `backend/tests/unit/api/v1/test_contract_lifecycle_api.py`, `backend/tests/unit/services/contract/test_contract_group_service.py` | 合同生命周期、合同关系派生状态和审计日志 |
| REQ-RNT-004 | 已移除 | 已清理 | `backend/src/models/contract_group.py`, `backend/src/crud/contract_group.py`, `backend/src/schemas/contract_group.py`, `backend/src/services/contract/contract_group_service.py`, `backend/src/services/project/service.py`, `backend/alembic/versions/20260612_drop_contract_relations.py` | `backend/tests/unit/models/test_contract_group_model.py`, `backend/tests/unit/services/contract/test_contract_correction_flow.py`, `backend/tests/unit/services/contract/test_contract_joint_review.py`, `backend/tests/unit/services/project/test_project_service.py`, `backend/tests/unit/migration/test_drop_contract_relations_migration.py`, `backend/tests/unit/config/test_check_field_drift.py`, `frontend/src/pages/Project/__tests__/ProjectDetailPage.test.tsx` | 主合同覆盖风险与合同逐对配对表已从 MVP 实现面清理；项目风险不再生成 `missing_primary_contract` / `coverage_conflict`，上下游/委托/直租仅由 `group_relation_type` 作为收入/成本方向标记派生。纠错草稿来源改用 `contracts.correction_source_contract_id` 显式字段，不恢复配对或续签关系。 |
| REQ-RNT-005 | MVP | 已有证据 | `backend/src/services/contract/contract_group_service.py`, `backend/src/services/contract/ledger_service_v2.py`, `backend/src/crud/contract_group.py`, `backend/src/api/v1/contracts/contract_groups.py` | `backend/tests/unit/services/contract/test_contract_correction_flow.py`, `backend/tests/unit/api/v1/test_contract_lifecycle_api.py` | 反审核、纠错、作废、冲销和重建 |
| REQ-RNT-006 | MVP | 已有证据 | `backend/src/api/v1/contracts/ledger.py`, `backend/src/services/contract/ledger_service_v2.py`, `backend/src/services/contract/ledger_export_service.py`, `backend/src/services/contract/ledger_compensation_service.py`, `backend/src/services/contract/service_fee_ledger_service.py`, `backend/scripts/maintenance/run_ledger_compensation.py`, `frontend/src/services/ledgerService.ts`, `frontend/src/pages/Finance/FinancialLedgerPage.tsx` | `backend/tests/unit/services/contract/test_ledger_service_v2.py`, `backend/tests/unit/services/contract/test_ledger_export_service.py`, `backend/tests/unit/services/contract/test_ledger_compensation_service.py`, `backend/tests/unit/services/contract/test_service_fee_ledger_service.py`, `backend/tests/unit/api/v1/test_ledger_api.py`, `frontend/src/services/__tests__/ledgerService.test.ts`, `frontend/src/pages/Finance/__tests__/FinancialLedgerPage.test.tsx` | 台账生成、查询、导出、补偿和服务费台账；前端已提供全局财务台账入口，支持跨项目筛选、汇总、导出和实收登记。逾期为 `due_date` 已过且未收清且非 `voided` 的派生口径，不再依赖人工 `overdue` 登记状态。 |

### 3.4 客户域

| REQ | 产品状态 | 实现状态 | 代码证据 | 测试证据 | 备注 |
|---|---|---|---|---|---|
| REQ-CUS-001 | MVP | 已有证据 | `backend/src/services/party/service.py`, `backend/src/schemas/party.py`, `backend/src/api/v1/party.py`, `frontend/src/pages/Customer/CustomerDetailPage.tsx`, `frontend/src/pages/System/PartyDetailPage.tsx` | `backend/tests/unit/services/test_party_service.py`, `backend/tests/unit/api/v1/test_party_api.py`, `frontend/src/pages/Customer/__tests__/CustomerDetailPage.test.tsx`, `frontend/src/pages/System/__tests__/PartyPages.test.tsx` | 客户增强信息、风险标签和历史签约 |
| REQ-CUS-002 | MVP | 已有证据 | `backend/src/services/analytics/analytics_service.py`, `backend/src/services/analytics/analytics_export_service.py`, `frontend/src/components/Analytics/AnalyticsStatsCard.tsx`, `frontend/src/types/analytics.ts`, `frontend/src/services/analyticsService.ts` | `backend/tests/unit/services/analytics/test_analytics_service.py`, `backend/tests/unit/services/analytics/test_analytics_export_service.py`, `frontend/src/components/Analytics/__tests__/RevenueStatsGrid.test.tsx`, `frontend/src/services/__tests__/analyticsService.test.ts` | 客户主体数和客户合同数 |

### 3.5 搜索域

| REQ | 产品状态 | 实现状态 | 代码证据 | 测试证据 | 备注 |
|---|---|---|---|---|---|
| REQ-SCH-001 | MVP | 已有证据 | `backend/src/api/v1/search.py`, `backend/src/services/search/service.py`, `backend/src/schemas/search.py`, `frontend/src/services/searchService.ts`, `frontend/src/pages/Search/GlobalSearchPage.tsx`, `frontend/src/components/Layout/AppHeader.tsx` | `backend/tests/unit/services/search/test_search_service.py`, `backend/tests/unit/api/v1/test_search_api.py`, `frontend/src/services/__tests__/searchService.test.ts`, `frontend/src/pages/Search/__tests__/GlobalSearchPage.test.tsx`, `frontend/src/components/Layout/__tests__/AppHeader.test.tsx` | 全局搜索入口、对象范围和前端搜索页已有证据；MVP 搜索覆盖资产、项目、合同关系、合同和客户。产权证为 Out of Scope，不再作为 MVP 搜索对象；合同聚合结果使用“合同关系”对象文案，并跳转到合同中心详情路径。 |
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
| REQ-ANA-001 | MVP | 已有证据 | `backend/src/api/v1/analytics/analytics.py`, `backend/src/services/analytics/analytics_service.py`, `backend/src/services/analytics/analytics_export_service.py`, `backend/src/services/excel/excel_export_service.py`, `frontend/src/services/analyticsService.ts`, `frontend/src/hooks/useAssetAnalytics.ts`, `frontend/src/pages/Assets/AssetAnalyticsPage.tsx`, `frontend/src/config/menuConfig.tsx`, `frontend/src/routes/AppRoutes.tsx`, `frontend/src/components/Analytics/AnalyticsDashboard.tsx` | `backend/tests/unit/services/analytics/test_analytics_service.py`, `backend/tests/unit/api/v1/test_analytics.py`, `backend/tests/unit/api/v1/analytics/test_statistics.py`, `backend/tests/unit/services/analytics/test_analytics_export_service.py`, `frontend/src/services/__tests__/analyticsService.test.ts`, `frontend/src/pages/Assets/__tests__/AssetAnalyticsPage.test.tsx`, `frontend/src/config/__tests__/menuConfig.perspective-grouping.test.tsx`, `frontend/src/routes/__tests__/AppRoutes.authz-metadata.test.ts`, `frontend/src/hooks/__tests__/useAssetAnalytics.test.ts`, `frontend/src/components/Analytics/__tests__/RevenueStatsGrid.test.tsx` | 经营分析、收入拆分、实收、收缴率和导出；全局入口已从资产分析收口为“经营分析”，`GET /api/v1/analytics/comprehensive` 返回项目维度 `project_breakdown` 与经营模式 `mode_breakdown`，前端全局经营分析页按项目和“承租转租 / 代理运营”分区展示 |

### 3.8 主体与审批域

| REQ | 产品状态 | 实现状态 | 代码证据 | 测试证据 | 备注 |
|---|---|---|---|---|---|
| REQ-PTY-001 | MVP | 已有证据 | `backend/src/models/party.py`, `backend/src/schemas/party.py`, `backend/src/crud/party.py`, `backend/src/services/party/service.py`, `backend/src/api/v1/party.py`, `backend/alembic/versions/20260603_drop_generic_contacts.py`, `frontend/src/pages/System/PartyListPage.tsx`, `frontend/src/pages/System/PartyDetailPage.tsx`, `frontend/src/services/partyService.ts` | `backend/tests/unit/services/test_party_service.py`, `backend/tests/unit/api/v1/test_party_api.py`, `backend/tests/unit/migration/test_drop_generic_contacts_migration.py`, `frontend/src/services/__tests__/partyService.test.ts`, `frontend/src/pages/System/__tests__/PartyPages.test.tsx` | Party 单一主档、去重、启停用、审计和主体联系人；通用 `/contacts`、`Contact(entity_type, entity_id)` 与 `contact` 权限资源已退役，联系人统一走 `/parties/{party_id}/contacts` 和 `party_contacts` |
| REQ-PTY-002 | MVP | 已有证据 | `backend/src/models/party.py`, `backend/src/services/party/service.py`, `backend/src/api/v1/party.py`, `backend/src/services/contract/contract_group_service.py`, `frontend/src/components/Common/PartySelector.tsx`, `frontend/src/pages/System/partyImport.ts`, `frontend/src/services/partyService.ts` | `backend/tests/unit/services/test_party_service.py`, `backend/tests/unit/api/v1/test_party_api.py`, `backend/tests/unit/services/contract/test_contract_group_service.py`, `frontend/src/pages/System/__tests__/PartyPages.test.tsx`, `frontend/src/components/Common/__tests__/PartySelector.test.tsx` | 主体导入、业务过程创建和合同提审门禁 |
| REQ-APR-001 | 已移除 | 已清理 | `backend/src/api/v1/__init__.py`, `backend/src/models/__init__.py`, `backend/src/services/notification/notification_service.py`, `backend/scripts/setup/init_rbac_data.py`, `backend/alembic/versions/20260611_drop_approval_domain.py`, `frontend/src/types/notification.ts` | `backend/tests/unit/api/v1/test_legacy_contract_runtime_retired.py`, `backend/tests/unit/migration/test_drop_approval_domain_migration.py`, `backend/tests/unit/scripts/test_init_rbac_data.py` | 资产审批路由流不再属于 MVP。approval 模型、CRUD、schema、service、API、审批待办通知和 RBAC seed 已清理；资产改由 REQ-AST-003 的 `review_status` 两步确认承接。 |

### 3.9 系统管理域

| REQ | 产品状态 | 实现状态 | 代码证据 | 测试证据 | 备注 |
|---|---|---|---|---|---|
| REQ-SYS-001 | MVP | 已有证据 | `backend/src/api/v1/auth/auth_modules/users.py`, `backend/src/services/core/user_management_service.py`, `backend/src/models/rbac.py`, `frontend/src/pages/System/UserManagement/`, `frontend/src/services/systemService.ts` | `backend/tests/unit/api/v1/test_users.py`, `backend/tests/unit/api/v1/test_authentication.py`, `frontend/src/services/__tests__/systemService.test.ts`, `frontend/src/pages/System/__tests__/UserManagement.test.tsx`, `frontend/src/pages/__tests__/ProfilePage.test.tsx`, `frontend/src/hooks/__tests__/useAuth.test.ts`, `frontend/src/services/__tests__/authService.test.ts` | 用户生命周期、多角色和权限管理员边界 |
| REQ-SYS-002 | MVP | 已有证据 | `backend/src/api/v1/auth/organization.py`, `backend/src/api/v1/party.py`, `frontend/src/pages/System/Organization/`, `frontend/src/pages/System/Organization/components/OrganizationBindingDrawer.tsx` | `backend/tests/unit/api/v1/test_organization.py`, `backend/tests/unit/api/v1/test_organization_layering.py`, `frontend/src/pages/System/__tests__/Organization.test.tsx`, `frontend/src/pages/System/Organization/components/__tests__/OrganizationBindingDrawer.test.tsx` | 组织 CRUD 和主体绑定维护 |
| REQ-SYS-003 | MVP | 已有证据 | `backend/src/api/v1/system/dictionaries.py`, `backend/src/api/v1/system/system_dictionaries.py`, `frontend/src/pages/System/DictionaryPage.tsx` | `backend/tests/unit/api/v1/test_dictionaries_layering.py`, `backend/tests/unit/api/v1/test_system_dictionaries_layering.py`, `frontend/src/pages/System/__tests__/DictionaryPage.test.tsx` | 数据字典分类和字典项维护 |

### 3.10 通知域

| REQ | 产品状态 | 实现状态 | 代码证据 | 测试证据 | 备注 |
|---|---|---|---|---|---|
| REQ-NTF-001 | MVP | 开发中 | `backend/src/models/notification.py`, `backend/src/schemas/notification.py`, `backend/src/services/notification/scheduler.py`, `backend/src/services/notification/wecom_service.py`, `backend/src/api/v1/system/notifications.py`, `frontend/src/components/Notification/NotificationCenter.tsx`, `frontend/src/pages/System/NotificationCenter.tsx`, `frontend/src/services/notificationService.ts` | `backend/tests/unit/api/v1/test_notifications.py`, `backend/tests/unit/api/v1/test_notifications_layering.py`, `backend/tests/unit/services/notification/test_scheduler.py`, `frontend/src/services/__tests__/notificationService.test.ts` | 站内通知五类、企业微信可选推送与未读去重已有存量证据。缺口：通知接收人未按主体绑定数据范围过滤，`scheduler.py` 对全量活跃用户广播含合同号/租户名的业务通知，违反 §8 与 REQ-NTF-001 验收标准，待收口；付款逾期扫描需按 ADR-0007 派生口径统一。 |

### 3.11 跨模块约束

| REQ | 产品状态 | 实现状态 | 代码证据 | 测试证据 | 备注 |
|---|---|---|---|---|---|
| REQ-XCUT-001 | MVP | 已有证据 | `backend/src/core/router_registry.py`, `backend/src/main.py` | `backend/tests/unit/api/v1/test_project_layering.py` | API 统一版本化 |
| REQ-XCUT-002 | MVP | 已有证据 | `backend/src/api/v1/`, `backend/src/services/` | `backend/tests/unit/api/v1/test_project_layering.py`, `backend/tests/unit/api/v1/test_authentication_layering.py` | 路由层不得承载业务规则 |
| REQ-XCUT-003 | MVP | 已有证据 | `backend/src/core/encryption.py`, `backend/src/crud/asset.py`, `backend/src/crud/party.py`, `backend/alembic/versions/20260611_encrypt_party_contact_phone.py`, `docs/security/encryption.md` | `backend/tests/unit/core/test_encryption.py`, `backend/tests/unit/crud/test_party.py`, `backend/tests/unit/services/test_party_service.py` | PII 字段加密与开发降级；PartyContact 联系电话已接入确定性加密，存量迁移清理 `Party.metadata_json` 中的联系人 PII 并加密 `party_contacts.contact_phone`。 |
| REQ-XCUT-004 | MVP | 已有证据 | `frontend/src/constants/routes.ts`, `frontend/src/routes/AppRoutes.tsx` | `frontend/src/routes/__tests__/AppRoutes.authz-metadata.test.ts` | 前端导航与后端模块能力对齐 |

## 4. Out of Scope 追踪

| 能力 | 产品状态 | 实现状态 | 说明 |
|---|---|---|---|
| Ownership | Out of Scope | 代码骨架存在，路由和可见入口已冻结 | 权属方管理不纳入 MVP 功能验收；普通用户路径和注册路由不暴露该对象 |
| 通用 BPM 审批流引擎 | Out of Scope | 不纳入当前验收 | MVP 不建设通用流程引擎；资产审批路由流已删除，资产只保留 `review_status` 两步确认 |
| 财务总账、税票、支付结算 | Out of Scope | 不纳入当前验收 | 当前只做运营台账和经营统计 |
| 催缴管理 | Out of Scope | 不纳入当前验收 | 不建催缴工单、催缴状态机或催缴成功率统计；逾期处理依靠台账逾期查询和台账实收登记闭环 |

## 5. 维护规则

- 新增或修改 REQ 时必须同步本文档。
- 产品状态变化同步 `docs/prd.md`。
- 字段、状态或统计口径变化同步 `docs/specs/domain-model.md`。
- API 契约变化同步 `docs/specs/api-contract.md`。
- 实现状态变化只修改本文档，不回写 PRD。
- 代码证据和测试证据路径应尽量使用仓库内真实路径。
