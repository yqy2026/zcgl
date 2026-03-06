# 土地物业资产运营管理系统需求规格说明书

## ✅ Status
**当前状态**: Active Baseline (2026-03-04)
**文档类型**: 唯一需求规格（目标 + 实现状态合并）
**字段附录**: `docs/features/requirements-appendix-fields.md`
**模块附录**: `docs/features/requirements-appendix-modules.md`

> 实现状态标记：✅ 已实现 | 🚧 开发中 | 📋 待开发

---

## 1. 文档定位

本文档是项目的 **唯一需求真相（SSOT）**：
- 立项与范围冻结依据
- 开发实现与验收依据
- 需求变更的唯一修改入口

变更规则：
- 需求变更时直接修改本文档并更新 `CHANGELOG.md`。
- 历史版本通过 Git 追溯，不另建文件。

---

## 2. 业务背景与问题定义

### 2.1 业务背景
- 土地/物业资产管理存在"资产台账分散、合同链路割裂、证照管理离散、统计口径不统一"的问题。
- 现实经营同时存在承租模式与代理模式，业务关系链条长且跨主体。
- 目标是建设统一平台，覆盖资产、产权、租赁合同、台账与分析，支持运营管理闭环。

### 2.2 当前痛点
- 资产与项目、权属、合同之间关联关系不清晰，导致查询与追责困难。
- "客户"概念缺少视角定义，导致内部租赁与终端租赁统计口径冲突。
- 租金台账依赖人工维护，易出现漏记、延迟与口径不一致。
- 权限粒度不一致，跨角色协作效率低且风险高。

---

## 3. 产品目标与成功指标

### 3.1 MVP 一票否决目标（未达标不放量）
- 清晰展示资产基本信息、租赁情况（按合同类型：上游承租/下游转租/委托运营汇总）与客户信息。
- 建立"合同组"能力，支撑承租模式与代理模式，且二者不混用。
- 提供可审计的合同审核/反审核与纠错闭环（作废/冲销 + 重建）。
- 提供经营统计口径：总收入合计 + 自营租金/代理服务费拆分。

### 3.2 成功指标（上线后 3 个月）
- 资产台账完整率 >= 98%。
- 合同台账自动生成覆盖率 >= 95%。
- 关键报表口径一致性问题 <= 2 个/月。
- 核心流程（资产新增、合同组新增）平均处理时长下降 >= 40%。

### 3.3 指标口径定义（MVP）
- 合同台账自动生成覆盖率（按"应生成条目"口径）：
  - 统计范围：统计周期内处于生效状态且应生成台账的合同计费条目。
  - 计算公式：`系统自动生成成功条目数 / 应生成条目总数 * 100%`。
  - 说明：手工补录条目计入"应生成条目总数"，但不计入"自动生成成功条目数"。
- 关键报表口径一致性问题（按"已确认问题单"口径）：
  - 判定标准：同一统计周期、同一视角、同一指标在两个及以上系统入口结果不一致，且经产品+业务+数据三方确认。
  - 统计来源：自动化口径校验任务 + 用户上报工单（合并去重后计数）。
  - 统计对象：按自然月统计"新发现并确认"的问题单数量。

---

## 4. 范围定义

### 4.1 In Scope（MVP 必须实现）
- 资产管理：列表、详情、新增、编辑、删除/恢复、导入、附件。
- 项目管理：项目与资产关系管理，项目汇总视图。
- 租赁管理：承租模式与代理模式、合同组、合同生命周期、台账生成与维护。
- 客户管理：客户增强信息、历史签约、风险标签、账期偏好。
- 搜索能力：全局搜索入口 + 模块内搜索并存。
- 权限体系：登录、会话刷新、角色权限配置、关键操作鉴权、全局视角切换。
- 数据分析：概览、趋势、分布、收入拆分、客户双指标。
- 文档处理：PDF 上传、解析、批处理、进度追踪。

### 4.2 Out of Scope（MVP 不纳入）
- 通用 BPM 审批流引擎。
- 财务总账、税票、支付结算系统。
- 跨法人多租户隔离产品化（SaaS 多租户）。
- 高级 BI 建模与自定义分析语言。
- 不提供用户侧物理删除入口；关键业务记录仅支持逻辑删除/作废。

---

## 5. 角色、视角与客户定义

### 5.1 角色
- 运营管理员：资产、项目、合同组与台账维护。
- 权限管理员：角色授权、组织与字典配置。
- 业务审核人：关键数据复核、审核与反审核。
- 管理层：查看统计看板与导出报表。
- 只读查看者（含外审/临时查看）：仅可查看授权范围数据，不允许新增/编辑/审核/作废。

### 5.2 全局视角机制
- 视角采用全局切换，不限定在单模块内。
- 用户首次登录必须手动选择"当前主体/视角"。
- 当用户仅有一个可用视角时，系统自动锁定该视角并跳过手动选择。
- 后续默认使用最近一次选择的视角，并允许手动切换。
- 所有查询与统计都基于当前视角执行权限与口径判定。

### 5.3 客户定义（强制口径）
- 客户不是固定身份，而是"当前视角下合同对方主体"。
- 同一主体可在不同合同中扮演不同角色（如运营管理方、承租方、出租方）。
- 所有客户展示必须包含：`客户名称 + 当前视角 + 合同角色`。
- 同一主体在不同视角下可出现多条客户记录，列表唯一键为 `party_id + current_view + contract_role`。
- UI 必须显式展示"当前视角标签"和"合同角色标签"，避免同名主体误判为重复数据。

### 5.4 核心场景
- 场景 S1：资产详情页一屏展示资产基本信息、租赁情况（按合同类型汇总：上游承租/下游转租/委托运营）、客户摘要。
- 场景 S2：项目详情页汇总当前有效资产并展示同口径租赁与客户信息。
- 场景 S3：承租模式与代理模式按合同组管理，支持关键合同联审。
- 场景 S4：统计页展示总收入合计及自营租金/代理服务费拆分。

---

## 6. 功能需求

> 需求编号规则：`REQ-<域>-<序号>`

### 6.1 资产域

#### REQ-AST-001 资产主数据统一管理 ✅
- 描述：支持资产全生命周期管理及条件查询。
- 验收：
  - 支持分页、筛选、排序、搜索。
  - 支持软删除、恢复（受关联约束）。
  - MVP 不提供用户侧物理删除入口。
  - 支持批量导入与模板校验。
- 字段映射（附录 v0.3 / 3.1 Asset）：
  - `asset_code`：按产权方编码段生成。
  - `asset_form` / `spatial_level` / `business_usage`：资产分类三字段拆分。
  - `address`：采用半结构化地址口径（`province_code/city_code/district_code/address_detail`），其中 `address_detail` 必填且 `trim` 后长度 `5-200`；`address` 为系统拼接只读展示字段。
- 代码证据：
  - `backend/src/api/v1/assets/assets.py`
  - `backend/src/services/asset/asset_service.py`
  - `backend/src/models/asset.py`（`AssetForm`/`SpatialLevel`/`BusinessUsage`/`AssetReviewStatus` 枚举，新增分类字段和半结构化地址字段，`_compose_address` 自动拼接）
  - `backend/src/schemas/asset.py`（`asset_name`/`asset_code`/`asset_form`/`spatial_level`/`business_usage`/`address_detail` 校验器）
  - `backend/alembic/versions/20260305_asset_field_enrichment_m1.py`
  - `backend/tests/unit/api/v1/test_assets_projection_guard.py`
  - `backend/tests/unit/services/asset/test_asset_service.py`
  - `backend/src/api/v1/assets/asset_batch.py`
  - `backend/src/api/v1/assets/asset_import.py`
  - `backend/src/api/v1/assets/asset_attachments.py`

#### REQ-AST-002 资产与项目、权属关系可追踪 🚧
- 描述：资产需可关联项目与权属并支持关系变更留痕。
- 验收：
  - 单资产支持多维关联信息展示。
  - 关系变更保留审计记录。
- 代码证据：
  - `backend/src/models/asset.py`（`ownership_entity` 动态投影已实现）
  - `backend/src/crud/asset.py`（计算/投影字段不落库）

#### REQ-AST-003 关键主数据支持审核与反审核 📋
- 描述：资产等关键主数据需支持审核状态流转。
- 验收：
  - 审核前后状态可追踪，保留操作者与时间。
  - 反审核后可恢复可编辑状态。
  - 审核态关键字段变更受控。

#### REQ-AST-004 资产详情口径清晰展示 📋
- 描述：资产详情必须默认展示经营所需核心信息。
- **实现依赖**：REQ-RNT-001（五层合同模型）✅ 已于 2026-03-06 落地，前置依赖已满足。
- 验收：
  - 展示资产基本信息、租赁情况（按合同角色分类汇总）、客户摘要。
  - 默认展示周期为"本月"，并支持周期切换。
  - 租赁情况分类维度：按 `Contract.group_relation_type`（附录 §3.4）+ `ContractGroup.revenue_mode` 分两组四类：
    - 承租模式（`revenue_mode = lease`）：
      - `group_relation_type = 上游`（上游承租）：运营方与产权方签署，运营方为承租方；内部入约合同。
      - `group_relation_type = 下游`（下游转租）：运营方与终端租户签署，运营方为出租方；对外出约合同。
    - 代理模式（`revenue_mode = agency`）：
      - `group_relation_type = 委托`（委托协议）：运营方与产权方签署，运营方为受托管理方；内部入约合同。
      - `group_relation_type = 直租`（直租合同）：产权方与终端租户直接签署，运营方代为管理；对外出约合同。
  - MVP 约束：一个资产只属于一种运营模式（承租或代理），禁止混用，不做系统强制校验，依赖录入规范。
  - 各类型分别展示：合同数量、租用/管理面积、月度金额合计。
  - 汇总行展示：总合同数、总出租/管理面积、出租率（`已出租面积 / 可出租面积`）。
  - 客户摘要展示：**仅展示对外出约合同的对方承租方**（`下游`、`直租` 的 `lessee_party_id` 对应名称）；内部入约合同（`上游`、`委托`）不计入客户摘要。
  - 注：`ContractType` 旧枚举（`LEASE_UPSTREAM/LEASE_DOWNSTREAM/ENTRUSTED`）已废弃（见附录 §10.1），不以此为分类依据。

### 6.2 项目与主体关系域

#### REQ-PRJ-001 项目关系遵循运营管理语义 ✅
- 描述：项目是资产运营管理归集单元，需明确与资产、运营管理方、产权方的关系边界。
- 验收：
  - 先有资产后有项目，项目可关联多个资产。
  - 项目必须绑定运营管理方。
  - 项目不直接绑定产权方，产权关系归属于项目下资产。
  - 单项目可通过资产间接关联多个产权方。
- 字段映射（附录 v0.3 / 3.2 Project）：
  - `project_code`：按 `PRJ-YYYYMM-NNNNNN` 格式自动生成。
  - `project_name`：项目名称，必填。
  - `status`：项目业务状态代码值冻结为 `planning/active/paused/completed/terminated`（展示值：`规划中/进行中/暂停/已完成/已终止`）；`data_status` 仅用于逻辑删除（`正常/已删除`）。
  - `review_status`：代码值冻结为 `draft/pending/approved/rejected`。
  - `manager_party_id`：项目运营管理主体，单值必填。
- 字段清出（DB 已存在但不在运营管理语义内，M1 迁移时 DROP）：
  - 工程管理类：`short_name`、`project_type`、`project_scale`、`start_date`、`end_date`、`expected_completion_date`、`actual_completion_date`、`construction_company`、`design_company`、`supervision_company`
  - 投资金额类：`total_investment`、`planned_investment`、`actual_investment`、`project_budget`
  - 文本描述类：`project_description`、`project_objectives`、`project_scope`
  - 地址/联系人类：`address`、`city`、`district`、`province`、`project_manager`、`project_phone`、`project_email`
  - 冗余状态类：`is_active`（已由 `data_status` 替代）
  - 以上字段均属早期工程项目管理模板残留，与资产运营管理定位无关，不保留兼容。
- 代码证据：
  - `backend/src/models/project.py`
  - `backend/alembic/versions/20260305_project_field_enrichment_m1.py`
  - `backend/src/schemas/project.py`
  - `backend/src/crud/project.py`
  - `backend/src/services/project/service.py`
  - `frontend/src/types/project.ts`
  - `frontend/src/services/projectService.ts`

#### REQ-PRJ-002 项目详情默认按当前有效资产汇总 ✅
- 描述：项目页面默认聚合当前有效资产，不混入历史失效资产。
- 验收：
  - 默认统计范围为 `project_assets` 当前有效关系。
  - 资产、项目双入口可进入同一合同组详情（合同组双入口，M2 实现，依赖 REQ-RNT-001）。
- 代码证据：
  - `backend/src/api/v1/assets/project.py`（`GET /api/v1/projects/{project_id}/assets`）
  - `backend/src/services/project/service.py`（`get_project_active_assets`）
  - `backend/src/schemas/project.py`（`ProjectAssetSummary` / `ProjectActiveAssetsResponse`）
  - `backend/tests/unit/services/project/test_project_service.py`（`TestGetProjectActiveAssets`）
  - `backend/tests/unit/api/v1/test_project.py`（`TestGetProjectActiveAssets`）
  - `frontend/src/services/projectService.ts`（`getProjectAssets`）
  - `frontend/src/pages/Project/ProjectDetailPage.tsx`
  - `frontend/src/types/project.ts`

### 6.3 租赁与合同组域

#### REQ-RNT-001 合同组作为主业务对象 ✅
- 描述：系统以"合同组（交易包）"管理一笔经营关系，不以单合同孤立管理。
- 验收：
  - 合同组至少包含：经营模式、运营方、产权方、状态、生效区间、关联资产、上下游合同、结算规则、收入归集口径、分润规则、风险标签。
  - `分润规则` 在 MVP 阶段仅要求结构化留存与版本化，不要求自动分润计算。
  - 一个合同组只能属于一种经营模式（承租或代理），禁止混用。
- 字段映射（附录 v0.3 / 3.3 ContractGroup）：
  - `group_code`：按经营主责方编码段生成（承租/代理均按运营方）。
- 代码证据（M1–M3 已完成）：
  - ORM 模型：`backend/src/models/contract_group.py`
  - Alembic 迁移：`backend/alembic/versions/20260305_contract_group_m1.py`
  - Pydantic Schema：`backend/src/schemas/contract_group.py`
  - CRUD 层：`backend/src/crud/contract_group.py`、`backend/src/crud/contract.py`
  - Service 层：`backend/src/services/rent_contract/contract_group_service.py`
  - API 端点：`backend/src/api/v1/rent_contracts/contract_groups.py`（`/api/v1/contract-groups/*`，`/api/v1/contracts/*`）
  - 单元测试：`backend/tests/unit/services/rent_contract/test_contract_group_service.py`、`backend/tests/unit/api/v1/test_contract_groups_layering.py`

#### REQ-RNT-002 承租模式与代理模式并行支持 📋
- 描述：系统需同时支持两种现实经营模式，通过 `ContractGroup.revenue_mode` + `Contract.group_relation_type` 覆盖完整业务结构。
- 验收：
  - 承租模式（`revenue_mode = lease`）：
    - `group_relation_type = 上游`：运营方与产权方签署，运营方为承租方；为内部入约合同。
    - `group_relation_type = 下游`：运营方与终端租户签署，运营方为出租方；为对外出约合同。
    - 终端租户（`下游` 合同的 `lessee_party`）在资产详情客户摘要中可见。
  - 代理模式（`revenue_mode = agency`）：
    - `group_relation_type = 委托`：运营方与产权方签署，运营方为受托管理方；为内部入约合同。对应 `AgencyAgreementDetail`。
    - `group_relation_type = 直租`：产权方与终端租户直接签署，运营方代为管理；为对外出约合同。对应 `LeaseContractDetail`。
    - 终端租户（`直租` 合同的 `lessee_party`）在资产详情客户摘要中可见。
  - MVP 约束：一个合同组（ContractGroup）只能属于一种运营模式，禁止混用。
  - 代理模式数据在运营视角下可见，且必须标注"代理口径，非自营出租"。
- 字段映射（附录 v0.3 / §3.3 ContractGroup + §3.4 Contract）：
  - `ContractGroup.revenue_mode`：`lease`(承租模式) / `agency`(代理模式)。
  - `Contract.group_relation_type`：`上游` / `下游` / `委托` / `直租`。

#### REQ-RNT-003 合同生命周期与状态流转 🚧
- 描述：合同组与组内合同需有可追溯状态管理。
- 验收：
  - 合同组状态最小集为：`草稿 -> 待审 -> 生效 -> 变更中 -> 已到期 / 已终止`。
  - `已到期` 表示按合同自然到期结束；`已终止` 表示提前解约或提前终止。
  - 合同组"已终止"判定为组内全部关键合同终止。
- 字段映射（附录 v0.3 / 3.3 ContractGroup）：
  - `settlement_rule`：最小必填键固定为 `version/cycle/settlement_mode/amount_rule/payment_rule`。
- 代码证据：
  - `backend/src/services/rent_contract/lifecycle_service.py`
  - `backend/src/api/v1/rent_contracts/lifecycle.py`（冲突检测与状态流转）

#### REQ-RNT-004 合同组主审与关键合同联审 📋
- 描述：审核机制采用"合同组主审 + 关键合同联审"。
- 验收：
  - 支持混合联审策略：金额/周期/计费/分润/主体/资产变更走强联审，非关键文本类改动可单审。
  - 审核记录包含审核范围、审核结论与关联合同清单。

#### REQ-RNT-005 反审核与纠错闭环 📋
- 描述：已出账数据不允许直接反审核，需走纠错链路。
- 验收：
  - 已产生台账或结算时，不允许直接反审核。
  - 必须先作废/冲销后再重建，禁止物理删除关键业务记录。
  - 全流程强制留痕（原因、操作人、审批人、前后值、关联单号）。

#### REQ-RNT-006 台账自动化 🚧
- 描述：合同生效后自动生成台账并支持批量维护。
- 验收：
  - 支持按合同、资产、主体、时间区间查询。
  - 支持批量更新支付状态并导出。
  - 触发时机（MVP 冻结）：
    - 初次生成：合同组状态由 `待审 -> 生效` 后立即按全生效区间生成台账。
    - 变更重算：金额/周期/计费规则变更并重新生效后，仅对受影响区间作废并重建。
    - 补偿任务：每日离线任务扫描缺失条目并补齐，确保覆盖率指标可达成。
- 字段映射（附录 v0.3 / 3.4 RentContract）：
  - `rent_amount` / `currency_code` / `tax_rate` / `is_tax_included`：金额税口径冻结。
  - `rent_amount_excl_tax`：派生字段，不允许直接写入。
- 代码证据：
  - `backend/src/api/v1/rent_contracts/ledger.py`
  - `backend/src/services/rent_contract/ledger_service.py`

### 6.4 客户域

#### REQ-CUS-001 客户增强信息管理 📋
- 描述：客户信息需覆盖增强版字段与历史信息。
- 验收：
  - 基础信息：名称、客户类型、联系人、联系电话、统一标识、地址、状态。
  - 增强信息：历史签约记录、风险标签、账期偏好。
  - 风险标签支持"人工标注 + 规则自动标注"双来源，并保留来源与更新时间。
  - 资产/项目页展示摘要，客户详情页展示全量。
- 字段映射（附录 v0.3 / 3.5 CustomerProfile）：
  - `subject_nature` / `identifier_type` / `unified_identifier`：企业与个人标识差异化校验与去重。

#### REQ-CUS-002 客户统计双指标 📋
- 描述：客户统计需同时反映主体规模与合同规模。
- 验收：
  - 同时展示"客户主体数"和"客户合同数"。
  - 支持按合同类型（上游承租/下游转租/委托运营）维度拆分。

### 6.5 搜索域

#### REQ-SCH-001 全局搜索入口与对象范围 📋
- 描述：系统需提供统一全局搜索入口，并保留模块内搜索。
- 验收：
  - MVP 全局搜索覆盖：资产、项目、合同组、合同、客户、产权证。
  - 任务、通知搜索能力列入 V1.1 范围（非 MVP 验收阻塞项）。
  - 统一入口与模块内搜索并存。

#### REQ-SCH-002 搜索结果组织与排序 📋
- 描述：搜索结果需支持多视图浏览与业务友好排序。
- 验收：
  - 支持"全部视图"和"按对象分组视图"切换。
  - 默认排序为"相关度优先 + 业务置顶规则"。

#### REQ-SCH-003 搜索权限过滤 📋
- 描述：搜索结果必须严格受权限约束。
- 验收：
  - 未授权对象完全不返回。
  - 权限判定基于当前全局视角。

### 6.6 认证与授权域

#### REQ-AUTH-001 会话安全与统一鉴权 ✅
- 描述：采用 Cookie 会话与 RBAC + ABAC 鉴权模型。
- 验收：
  - 登录、刷新、退出流程闭环。
  - 关键写操作必须经过鉴权。
  - 非授权访问应拒绝。
- 代码证据：
  - `backend/src/api/v1/auth/auth_modules/authentication.py`
  - `backend/src/security/cookie_manager.py`
  - `backend/src/middleware/auth.py`
  - `frontend/src/api/client.ts`
  - `frontend/src/services/authService.ts`
  - `backend/tests/unit/middleware/test_optional_auth.py`
  - `backend/src/services/permission/rbac_service.py`
  - `backend/tests/unit/api/v1/test_roles_permission_grants.py`

#### REQ-AUTH-002 视角上下文强制注入 📋
- 描述：所有业务请求需携带当前视角上下文。
- 验收：
  - 业务查询、统计、搜索均使用当前视角口径。
  - 当默认视角权限失效时，系统要求重新选择视角。

### 6.7 文档与分析域

#### REQ-DOC-001 PDF 智能导入流程 ✅
- 描述：支持 PDF 上传、抽取、校验、确认落库。
- 验收：
  - 单文件与批量文件都可追踪处理状态。
  - 抽取失败可回退人工修正。
- 代码证据：
  - `backend/src/api/v1/documents/pdf_import.py`
  - `backend/src/api/v1/documents/pdf_upload.py`
  - `backend/src/api/v1/documents/pdf_batch_routes.py`

#### REQ-ANA-001 经营分析与导出 🚧
- 描述：提供可直接用于经营决策的分析能力。
- 验收：
  - 提供总收入合计并强制拆分"自营租金收入/代理服务费收入"。
  - 提供客户双指标（主体数/合同数）。
  - 支持结果导出并标记统计口径版本。
- 代码证据：
  - `backend/src/api/v1/analytics/analytics.py`（综合分析/趋势/分布已实现）
  - `backend/src/services/analytics/analytics_service.py`

### 6.8 主体（Party）域

#### REQ-PTY-001 Party 单一主档管理 📋
- 描述：Party 作为跨资产、项目、合同、客户的统一主体主档，必须可维护且可追溯。
- 验收：
  - 支持 Party 新增、编辑、启停用、查询。
  - 支持统一标识去重与重名校验。
  - Party 变更保留审计轨迹。

#### REQ-PTY-002 Party 数据来源与创建路径 📋
- 描述：Party 支持"初始化导入 + 业务过程创建"双路径进入主档。
- 验收：
  - 支持初始化批量导入主体主档。
  - 合同组创建流程支持按权限快速创建 Party 草稿并进入审核。
  - 未审核通过的 Party 不得进入统计口径。

---

## 7. 跨模块约束

### REQ-XCUT-001 API 统一版本化 ✅
- 所有业务 API 统一挂载到 `/api/v1/*`。
- 证据：`backend/src/core/router_registry.py`、`backend/src/main.py`

### REQ-XCUT-002 路由层不得绕过服务层直接承载业务规则 ✅
- 证据：`backend/tests/unit/api/v1/test_project_layering.py`、`test_authentication_layering.py`

### REQ-XCUT-003 敏感字段采用字段级加密，并允许开发环境降级 ✅
- PII 字段通过 `SensitiveDataHandler` + `FieldEncryptor` 处理；无有效密钥时降级明文并记录告警。
- 证据：`backend/src/core/encryption.py`、`backend/src/crud/asset.py`

### REQ-XCUT-004 前端导航与路由应与后端模块能力对齐 ✅
- 证据：`frontend/src/constants/routes.ts`、`frontend/src/routes/AppRoutes.tsx`

---

## 8. 非功能需求

### 8.1 安全与合规
- PII 字段必须字段级加密存储（生产强制）。
- 会话凭证必须使用 HttpOnly Cookie，并带 `SameSite` 策略。
- CORS 必须允许 `Authorization`、`X-CSRF-Token` 等关键请求头。
- 关键操作必须记录审计日志（含操作者、时间、对象、动作）。
- 关键业务记录默认禁止物理删除。
- 生产环境禁止弱密钥与部分降级配置。

### 8.2 性能
- 列表接口 P95 响应时间 <= 800ms（常规筛选条件）。
- 统计接口 P95 响应时间 <= 2s（默认维度）。
- 全局搜索 P95 响应时间 <= 2s（默认分页）。
- 批量导入任务应支持异步执行与进度查询。
- 性能基线数据量（MVP 估算）：资产 <= 5,000，合同组 <= 10,000，合同 <= 20,000，台账 <= 500,000，客户 <= 10,000。

### 8.3 可用性与可维护性
- 全局视角切换入口清晰可见，且支持手动切换。
- 核心模块可观测（健康检查、关键错误日志、任务状态）。
- 接口统一版本化（`/api/v1/*`）。
- 路由层与业务层分离，便于长期演进。

---

## 9. 数据与集成要求

### 9.1 核心数据实体
- Party（主体，单一主档）
- Asset（资产）
- Project（项目）
- ContractGroup（合同组/交易包）
- RentContract（租赁合同）
- RentLedger（租金台账）
- CustomerProfile（客户视图档案）
- PropertyCertificate（产权证）

### 9.2 外部/周边集成
- 文件存储：合同附件与导出文件管理。
- AI 服务：PDF 字段提取与结构化识别。
- 缓存服务：统计、搜索与会话相关缓存。

### 9.3 Party 数据治理约束
- Party 主档由"初始化导入 + Party 管理 + 合同组流程快速创建"共同维护。
- 合同组中引用的主体必须可映射到 Party 主档，不允许游离主体直接参与台账与统计。
- Party 与客户视图（CustomerProfile）为"主档 + 视角投影"关系，不允许双主档并行维护。

---

## 10. 里程碑与发布策略

### 10.1 里程碑
1. M1：资产/项目清晰展示能力上线（含按合同类型分类的租赁情况与客户摘要）。目标窗口：`2026-03-04 ~ 2026-03-31`。
2. M2：合同组与承租/代理模式能力上线（含联审与纠错闭环）。目标窗口：`2026-04-01 ~ 2026-05-10`。
3. M3：经营统计口径上线（总收入 + 自营/代理拆分 + 客户双指标）。目标窗口：`2026-05-11 ~ 2026-06-07`。
4. M4：搜索、权限、审计与上线验收闭环。目标窗口：`2026-06-08 ~ 2026-06-30`。

### 10.2 MVP 放量硬门槛（访谈冻结）
- G1：资产页/项目页可清晰展示资产信息 + 按合同类型分类的租赁情况（上游承租/下游转租/委托运营）+ 客户摘要。
- G2：合同组能力可用（承租/代理、关键合同联审、状态流转）。
- G3：统计口径可用（总收入合计 + 自营租金/代理服务费拆分 + 客户主体数/客户合同数）。

---

## 11. 需求追踪矩阵

| 需求ID | 状态 | 关键端点/能力 | 关键测试证据 |
|---|---|---|---|
| REQ-AST-001 | ✅ | `/api/v1/assets` (CRUD + batch + import) | `test_assets_projection_guard.py`, `test_asset_service.py` |
| REQ-AST-002 | 🚧 | 投影/关联 | `test_asset.py` |
| REQ-AST-003 | 📋 | — | — |
| REQ-AST-004 | 📋 | `GET /api/v1/assets/{id}/lease-summary` | — |
| REQ-PRJ-001 | ✅ | `/api/v1/projects` (CRUD + search) | `test_project.py`, `test_project_service.py` |
| REQ-PRJ-002 | ✅ | `/api/v1/projects/{project_id}/assets` | `test_project_service.py`, `test_project.py` |
| REQ-RNT-001 | ✅ | M1 ORM/DDL ✅ M2 Schema/CRUD/Service ✅ M3 API ✅ | — |
| REQ-RNT-002 | 📋 | — | — |
| REQ-RNT-003 | 🚧 | 生命周期 + 冲突检测 | `lifecycle_service.py` |
| REQ-RNT-004 | 📋 | — | — |
| REQ-RNT-005 | 📋 | — | — |
| REQ-RNT-006 | 🚧 | `/rental-contracts/ledger/*` | `ledger_service.py` |
| REQ-CUS-001 | 📋 | — | — |
| REQ-CUS-002 | 📋 | — | — |
| REQ-SCH-001 | 📋 | — | — |
| REQ-AUTH-001 | ✅ | `/auth/login`, `/auth/refresh` | `test_optional_auth.py` |
| REQ-AUTH-002 | 📋 | — | — |
| REQ-DOC-001 | ✅ | `/pdf-import/*` | `pdf_import.py` |
| REQ-ANA-001 | 🚧 | `/analytics/*` | `analytics_service.py` |
| REQ-PTY-001 | 📋 | — | — |
| REQ-PTY-002 | 📋 | — | — |

---

## 12. 验收场景（最小集）

### 12.1 资产
- A1：创建资产重名拦截。
- A2：面积不一致拦截（`rented_area > rentable_area`）。
- A3：资产已关联合同时删除拦截。
- A4：`include_relations` 开关影响投影字段返回。

### 12.2 认证与权限
- P1：登录后 Cookie 写入成功。
- P2：刷新令牌走 Cookie 读取流程。
- P3：普通用户访问他人权限摘要被拒绝。

### 12.3 租赁
- R1：创建合同时关联资产不存在应失败。
- R2：合同生命周期冲突检测触发拒绝。
- R3：台账批量更新成功并更新欠费状态字段。

### 12.4 推荐验证命令
```bash
cd backend
pytest -m unit tests/unit/services/asset/test_asset_service.py -q
pytest -m unit tests/unit/api/v1/test_assets_projection_guard.py -q
pytest -m unit tests/unit/api/v1/test_authentication_layering.py -q
pytest -m unit tests/unit/api/v1/test_roles_permission_grants.py -q
```

---

## 13. vNext 候选需求（未实现）

以下为"已观察到工程迹象但未纳入当前正式基线"的候选项：

1. **错误恢复模块正式化** — `error_recovery` 路由在聚合处被临时禁用。
2. **系统设置模块能力稳定化** — `system_settings_router` 为条件导入/条件注册。
3. **PDF 批量导入从"可选加载"提升为"必选能力"** — 批量路由当前通过可导入性判断注册。

---

## 14. 风险与依赖

- 承租/代理双模式并存，若视角口径不一致会引发统计争议。
- 历史数据质量差异可能影响合同组建模与统计一致性。
- 存量 Excel/旧系统数据迁移存在主档去重、字段缺失、初始台账重建风险，可能影响 MVP 上线节奏。
- 权限模型收敛需要跨模块改造协同，需阶段推进。
- AI 提取准确率不足时，需预留人工校验流程。

---

## 15. 访谈冻结结论（2026-02-28）

- 主定位：范围与目标冻结优先。
- 客户口径：客户为"当前视角下合同对方主体"，非固定身份。
- 视角机制：首次手动选择，后续默认最近选择，支持全局切换。
- 经营模式：承租模式与代理模式并存，合同组单模式不混用。
- 审核策略：合同组主审 + 关键合同混合联审。
- 反审核策略：已出账场景仅允许作废/冲销 + 重建，禁止物理删除。
- 搜索策略：统一入口 + 模块内搜索并存，未授权对象不返回。
- 字段冻结补充：编码规则按主体编码段生成（资产=产权方、项目=运营方、合同组=经营主责方），资产分类拆分为 `asset_form/spatial_level/business_usage` 三字段。
- 字段冻结补充：资产地址采用半结构化口径（行政区三级 + `address_detail`），`address_detail` 必填且 `trim` 后长度 `5-200`，`address` 仅作系统拼接展示字段。
- 字段冻结补充：项目域 DEPRECATED 字段直接收口（不做兼容），状态语义收敛为 `status + data_status`，`is_active` 下线。
- 放量门槛：G1/G2/G3 三项必须同时满足。

---

## 16. 变更规则

- 需求变更时直接修改本文档对应章节。
- 同步更新 `CHANGELOG.md`。
- 历史版本通过 Git tag 或 Git diff 追溯。
