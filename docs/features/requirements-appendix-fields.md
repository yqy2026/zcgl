# 需求规格附录：字段冻结清单（v0.3）

## ✅ Status
**当前状态**: Draft Freeze Candidate (2026-03-06, v0.4 — M2 字段采纣更新：新增 §3.5.1 ContractRentTerm / §3.10 ContractLedgerEntry / §3.11 ContractAuditLog；更新 §11.2 台账生成口径)  
**对应主文档**: `docs/requirements-specification.md`  
**用途**: 将业务口径转为可评审字段口径（必填/枚举/校验/展示）

---

## 1. 说明

本附录用于回答“需求有没有字段确认与讨论”的问题，作为 MVP 字段冻结入口。

字段状态说明：
- `已确认`：已在访谈中冻结，可进入接口与开发设计。
- `待确认`：需业务/产品补充后才能进入冻结。
- `派生`：由系统计算或关联推导，不允许人工直接写入。

---

## 2. 跨对象字段规则（MVP）

- 主键统一：`*_id`（字符串 ID）。
- 时间字段统一：`created_at`、`updated_at`（系统写入）。
- 审核相关对象统一包含：`review_status`、`review_by`、`reviewed_at`、`review_reason`。
- 关键业务记录（合同组、合同、台账）禁止物理删除，仅允许作废/冲销 + 重建。
- 统计类字段（占用率、汇总金额、计数）标记为 `派生`，不得直接写库。
- 编码规则统一按“主体编码段”生成：`asset_code` 按产权方、`project_code` 按运营方、`group_code` 按经营主责方（承租/代理均按运营方）。
- 编码格式冻结：`<TYPE>-<SEGMENT>-<SERIAL>`，分隔符固定 `-`，`SERIAL` 为 6 位数字并按 `TYPE+SEGMENT` 维度单调递增。
- 编码生成后不回写历史编码，主体变更仅记录映射留痕。

---

## 3. 字段清单（MVP）

## 3.1 Asset（资产）

| 字段 | 类型 | 必填 | 规则/说明 | 状态 |
|---|---|---|---|---|
| `asset_id` | string | 是 | 资产主键 | 已确认 |
| `asset_code` | string | 是 | 资产编码，全局唯一；按产权方编码段生成，格式：`AST-[A-Z0-9]{4,12}-[0-9]{6}` | 已确认 |
| `asset_name` | string | 是 | 资产名称 | 已确认 |
| `asset_form` | enum | 是 | 资产形态：`土地/建筑/构筑物/车位/仓储/其他` | 已确认 |
| `spatial_level` | enum | 是 | 空间层级：`地块/园区/楼宇/楼层/房间/商铺` | 已确认 |
| `business_usage` | enum | 是 | 经营用途：`商业/办公/仓储/工业/综合/其他` | 已确认 |
| `address` | string | 是 | 资产地址（半结构化）：行政区三级 + 详细地址；详细地址 `trim` 后长度 `5-200` | 已确认 |
| `rentable_area` | number | 是 | 可出租面积，>=0 | 已确认 |
| `rented_area` | number | 否 | 已出租面积（总口径），>=0 | 已确认 |
| `occupancy_rate_total` | number | 否 | 总出租率（派生） | 已确认（派生） |
| `project_id` | string | 否 | 当前有效关联项目 ID（单值，同一时点只允许一个当前有效项目，历史关联通过审计日志追溯） | 已确认 |
| `owner_party_id` | string | 是 | 当前有效主产权主体（单值，同一时点只允许一个主产权主体，历史关联通过审计日志追溯） | 已确认 |
| `manager_party_id` | string | 是 | 运营管理主体 | 已确认 |
| `data_status` | enum | 是 | 正常/已删除 | 已确认 |
| `review_status` | enum | 是 | 草稿/待审/已审/反审核 | 已确认 |
| `review_by` | string | 否 | 审核人（通过/反审核时必填） | 已确认 |
| `reviewed_at` | datetime | 否 | 审核时间（通过/反审核时必填） | 已确认 |
| `review_reason` | string | 否 | 审核原因（反审核时必填） | 已确认 |

## 3.2 Project（项目）

| 字段 | 类型 | 必填 | 规则/说明 | 状态 |
|---|---|---|---|---|
| `project_id` | string | 是 | 项目主键 | 已确认 |
| `project_code` | string | 是 | 项目编码，唯一；按运营方编码段生成，格式：`PRJ-[A-Z0-9]{4,12}-[0-9]{6}` | 已确认 |
| `project_name` | string | 是 | 项目名称 | 已确认 |
| `manager_party_id` | string | 是 | 项目运营管理方 | 已确认 |
| `asset_ids_current` | string[] | 否 | 当前有效资产（派生） | 已确认（派生） |
| `asset_count_current` | number | 否 | 当前有效资产数（派生） | 已确认（派生） |
| `status` | enum | 是 | 业务状态（代码值）：`planning/active/paused/completed/terminated`；展示值：`规划中/进行中/暂停/已完成/已终止` | 已确认 |
| `data_status` | enum | 是 | 数据状态：`正常/已删除`（仅逻辑删除） | 已确认 |
| `review_status` | enum | 是 | 草稿/待审/已审/反审核 | 已确认 |
| `review_by` | string | 否 | 审核人（通过/反审核时必填） | 已确认 |
| `reviewed_at` | datetime | 否 | 审核时间（通过/反审核时必填） | 已确认 |
| `review_reason` | string | 否 | 审核原因（反审核时必填） | 已确认 |

### 3.2.1 废弃字段（M1 迁移时 DROP）

以下字段在数据库中存在，但不属于运营管理语义，M1 里程碑迁移时物理删除：

| 字段 | 废弃理由 |
|------|----------|
| `short_name` | 工程管理模板残留，无业务用途 |
| `project_type` | 工程管理模板残留，无业务用途 |
| `project_scale` | 工程管理模板残留，无业务用途 |
| `start_date` | 工程周期字段，非运营管理语境 |
| `end_date` | 工程周期字段，非运营管理语境 |
| `expected_completion_date` | 工程周期字段，非运营管理语境 |
| `actual_completion_date` | 工程周期字段，非运营管理语境 |
| `address` | 项目无独立地址，地址归属于资产 |
| `city` | 同上 |
| `district` | 同上 |
| `province` | 同上 |
| `project_manager` | 联系人信息，不在运营管理对象模型内 |
| `project_phone` | 联系人信息，不在运营管理对象模型内 |
| `project_email` | 联系人信息，不在运营管理对象模型内 |
| `total_investment` | 投融资字段，不在运营管理语境 |
| `planned_investment` | 投融资字段，不在运营管理语境 |
| `actual_investment` | 投融资字段，不在运营管理语境 |
| `project_budget` | 投融资字段，不在运营管理语境 |
| `project_description` | 工程文本模板残留 |
| `project_objectives` | 工程文本模板残留 |
| `project_scope` | 工程文本模板残留 |
| `construction_company` | 施工管理字段，与本系统无关 |
| `design_company` | 施工管理字段，与本系统无关 |
| `supervision_company` | 施工管理字段，与本系统无关 |
| `is_active` | 已由 `data_status` 替代，冗余 |

## 3.3 ContractGroup（合同组/交易包）

> 定位：纯容器，用于将同一笔交易涉及的所有合同打包管理。ContractGroup **不拥有独立生命周期状态**，其“状态”由组内合同状态派生计算（见 §8）。审核在合同级进行，不在组级进行。

| 字段 | 类型 | 必填 | 规则/说明 | 状态 |
|---|---|---|---|---|
| `contract_group_id` | string | 是 | 合同组主键 | 已确认 |
| `group_code` | string | 是 | 合同组编码，唯一；按经营主责方编码段生成（承租/代理均按运营方），格式：`GRP-[A-Z0-9]{4,12}-[0-9]{6}` | 已确认 |
| `revenue_mode` | enum | 是 | `lease`(承租模式) / `agency`(代理模式)，单组不混用 | 已确认 |
| `operator_party_id` | string | 是 | 运营方主体 | 已确认 |
| `owner_party_id` | string | 是 | 产权方主体 | 已确认 |
| `asset_ids` | string[] | 是 | 关联合同组资产 | 已确认 |
| `derived_status` | enum | 否 | 派生状态：`筹备中/生效中/已结束`（由组内合同状态实时计算，不允许手工写入） | 已确认（派生） |
| `effective_from` | date | 是 | 生效开始日期 | 已确认 |
| `effective_to` | date | 否 | 生效结束日期（派生：= MAX(组内非终止合同的 effective_to)，允许手动设定初始值） | 已确认 |
| `upstream_contract_ids` | string[] | 否 | 上游合同引用（派生只读，由 ContractRelation 计算） | 已确认（派生） |
| `downstream_contract_ids` | string[] | 否 | 下游合同引用（派生只读，由 ContractRelation 计算） | 已确认（派生） |
| `settlement_rule` | json | 是 | 结算规则对象，最小必填：`version/cycle/settlement_mode/amount_rule/payment_rule`；仅定义“谁付给谁、按什么算、什么时候付”；扩展键（违约金/减免/分期）本次不纳入组级，试行下沉合同级 | 已确认 |
| `revenue_attribution_rule` | json | 否 | 收入归集口径配置 | 已确认 |
| `revenue_share_rule` | json | 否 | 分润规则配置（本次仅结构化留存，不做自动分润计算） | 已确认 |
| `risk_tags` | string[] | 否 | 风险标签 | 已确认 |
| `predecessor_group_id` | string | 否 | FK → ContractGroup，前一周期的合同组（续签时填入） | 已确认 |



## 3.4 Contract（合同基表）

> 定位：所有合同类型的公共字段。类型差异字段下沉到明细表（§3.5 / §3.6）。台账（RentLedger / ServiceFeeLedger）FK 挂本表。

| 字段 | 类型 | 必填 | 规则/说明 | 状态 |
|---|---|---|---|---|
| `contract_id` | string | 是 | 合同主键 | 已确认 |
| `contract_group_id` | string | 是 | 所属合同组 FK → ContractGroup | 已确认 |
| `contract_direction` | enum | 是 | `出租` / `承租`（从哪个视角看这份合同） | 已确认 |
| `group_relation_type` | enum | 是 | `上游` / `下游` / `委托` / `直租` | 已确认 |
| `lessor_party_id` | string | 是 | 出租方/委托方主体（代理模式下 lessor = 委托方） | 已确认 |
| `lessee_party_id` | string | 是 | 承租方/受托方主体（代理模式下 lessee = 受托方） | 已确认 |
| `asset_ids` | string[] | 否 | 关联资产 ID 列表（多对多），为所属 ContractGroup.asset_ids 的子集 | 已确认 |
| `sign_date` | date | 否 | 签订日期；草稿可空，进入 `待审/生效` 前必填；支持单条与批量补录并留痕 | 已确认 |
| `effective_from` | date | 是 | 生效开始日期 | 已确认 |
| `effective_to` | date | 否 | 生效结束日期 | 已确认 |
| `currency_code` | enum | 是 | 币种，MVP 固定 `CNY` | 已确认 |
| `tax_rate` | decimal(5,4) | 否 | 税率，范围 `[0,1]` | 已确认 |
| `is_tax_included` | boolean | 是 | 含税标记，默认 `true` | 已确认 |
| `status` | enum | 是 | `草稿/待审/生效/已到期/已终止` | 已确认 |
| `review_status` | enum | 是 | `草稿/待审/已审/反审核` | 已确认 |
| `review_by` | string | 否 | 审核人（通过/反审核时必填） | 已确认 |
| `reviewed_at` | datetime | 否 | 审核时间（通过/反审核时必填） | 已确认 |
| `review_reason` | string | 否 | 审核原因（反审核时必填） | 已确认 |
| `data_status` | enum | 是 | `正常/已删除`（仅逻辑删除） | 已确认 |
| `contract_notes` | text | 否 | 合同备注 | 已确认 |

## 3.5 LeaseContractDetail（租赁合同明细）

> 定位：租赁类合同（上游承租 / 下游出租 / 终端租赁）的专有字段。一份 Contract 最多关联一条 LeaseContractDetail。

| 字段 | 类型 | 必填 | 规则/说明 | 状态 |
|---|---|---|---|---|
| `lease_detail_id` | string | 是 | 明细主键 | 已确认 |
| `contract_id` | string | 是 | FK → Contract 基表 | 已确认 |
| `total_deposit` | decimal(18,2) | 否 | 总押金金额，>=0 | 已确认 |
| `rent_amount` | decimal(18,2) | 是 | 合同级租金汇总金额（>=0）；不替代 RentTerm 分阶段明细，台账按 RentTerm 生成 | 已确认 |
| `rent_amount_excl_tax` | decimal(18,2) | 否 | 不含税金额（派生） | 已确认（派生） |
| `monthly_rent_base` | decimal(15,2) | 否 | 基础月租金 | 已确认 |
| `payment_cycle` | enum | 否 | 付款周期：`月付/季付/半年付/年付`，默认 `月付` | 已确认 |
| `payment_terms` | text | 否 | 支付条款 | 已确认 |
| `tenant_name` | string | 否 | 承租方名称（冗余展示，主数据以 `lessee_party_id` 为准） | 已确认 |
| `tenant_contact` | string | 否 | 承租方联系人 | 已确认 |
| `tenant_phone` | string | 否 | 承租方联系电话 | 已确认 |
| `tenant_address` | string | 否 | 承租方地址 | 已确认 |
| `tenant_usage` | string | 否 | 用途说明 | 已确认 |
| `owner_name` | string | 否 | 甲方/出租方名称（冗余展示，主数据以 `lessor_party_id` 为准） | 已确认 |
| `owner_contact` | string | 否 | 甲方联系人 | 已确认 |
| `owner_phone` | string | 否 | 甲方联系电话 | 已确认 |

> 说明：RentTerm（分阶段租金条款）保持为独立子表 FK → Contract 基表，不归入 LeaseContractDetail。

### 3.5.1 ContractRentTerm（分阶段租金条款子表）

> 定位：`LeaseContractDetail` 关联的分阶段租金条款，一份合同可有多个阶段（如阶梯租金）。台账按本表逐阶段展开自然月生成，不依赖 `monthly_rent_base`。  
> 独立子表：`contract_rent_terms`，FK → `contracts.contract_id`（非旧 `rent_contracts`）。

| 字段 | 类型 | 必填 | 规则/说明 | 状态 |
|---|---|---|---|---|
| `rent_term_id` | string | 是 | 主键（UUID） | 已确认 |
| `contract_id` | string | 是 | FK → Contract 基表（`contracts.contract_id`） | 已确认 |
| `sort_order` | int | 是 | 条款排序，从 1 开始；唯一约束：`(contract_id, sort_order)` | 已确认 |
| `start_date` | date | 是 | 本阶段开始日 | 已确认 |
| `end_date` | date | 是 | 本阶段结束日；须 `> start_date` | 已确认 |
| `monthly_rent` | decimal(15,2) | 是 | 本阶段月租金，>=0 | 已确认 |
| `management_fee` | decimal(15,2) | 否 | 管理费，>=0，默认 0 | 已确认 |
| `other_fees` | decimal(15,2) | 否 | 其他费用，>=0，默认 0 | 已确认 |
| `total_monthly_amount` | decimal(15,2) | 否 | 月合计金额（派生：`monthly_rent + management_fee + other_fees`） | 已确认（派生） |
| `notes` | text | 否 | 阶段备注 | 已确认 |
| `created_at` | datetime | 是 | 系统字段 | 已确认 |
| `updated_at` | datetime | 是 | 系统字段 | 已确认 |

**约束**：
- 同一合同各阶段日期范围不得重叠。
- 台账生成时按 `sort_order` 升序遍历，每阶段覆盖 `[start_date, end_date]` 内的完整自然月。
- `total_monthly_amount` 为派生字段，禁止直接写入；由 Service 层计算后写库。

## 3.6 AgencyAgreementDetail（代理协议明细）

> 定位：代理模式下委托协议的专有字段。一份 Contract 最多关联一条 AgencyAgreementDetail。代理模式下 `lessor_party_id` = 委托方（产权方），`lessee_party_id` = 受托方（运营方），不另设 `principal_party_id` / `agent_party_id`。

| 字段 | 类型 | 必填 | 规则/说明 | 状态 |
|---|---|---|---|---|
| `agency_detail_id` | string | 是 | 明细主键 | 已确认 |
| `contract_id` | string | 是 | FK → Contract 基表 | 已确认 |
| `service_fee_ratio` | decimal(5,4) | 是 | 服务费比例（如 0.05 = 5%） | 已确认 |
| `fee_calculation_base` | enum | 是 | 计费基数：`actual_received`(实收租金) / `due_amount`(应收租金)；MVP 默认 `actual_received` | 已确认 |
| `agency_scope` | text | 否 | 代理范围描述（自由文本） | 已确认 |

> 说明：代理交易包结构 = 1 份委托协议（关联 AgencyAgreementDetail）+ N 份直租合同（`group_relation_type=直租`，关联 LeaseContractDetail），通过 ContractRelation 建立关联。

## 3.7 ContractRelation（合同关系）

> 定位：记录合同间的上下游、代理、续签等关系。采用 parent/child 模型，不做反向冗余存储。

| 字段 | 类型 | 必填 | 规则/说明 | 状态 |
|---|---|---|---|---|
| `relation_id` | string | 是 | 关系主键 | 已确认 |
| `parent_contract_id` | string | 是 | FK → Contract，上级合同（上游 / 委托协议 / 旧合同） | 已确认 |
| `child_contract_id` | string | 是 | FK → Contract，下级合同（下游 / 终端合同 / 新合同） | 已确认 |
| `relation_type` | enum | 是 | `upstream_downstream`(上下游) / `agency_direct`(代理-直租) / `renewal`(续签) | 已确认 |
| `created_at` | datetime | 是 | 系统字段 | 已确认 |

**约束**：
- `(parent_contract_id, child_contract_id)` 联合唯一。
- 一个 child 在同一 `relation_type` 下只能有一个 parent。
- ContractGroup 的 `upstream_contract_ids` / `downstream_contract_ids` 由本表派生计算。

## 3.8 CustomerProfile（客户视图档案）

> 口径：客户为“当前视角下合同对方主体”，非固定身份。

| 字段 | 类型 | 必填 | 规则/说明 | 状态 |
|---|---|---|---|---|
| `customer_party_id` | string | 是 | 客户主体 ID | 已确认 |
| `customer_name` | string | 是 | 客户名称 | 已确认 |
| `customer_type` | enum | 是 | 内部/外部 | 已确认 |
| `subject_nature` | enum | 是 | 主体性质：`enterprise/individual` | 已确认 |
| `perspective_type` | enum | 是 | 当前视角（运营方/产权方等） | 已确认 |
| `contract_role` | enum | 是 | 当前视角下合同角色（承租/出租） | 已确认 |
| `contact_name` | string | 否 | 联系人 | 已确认 |
| `contact_phone` | string | 否 | 联系电话 | 已确认 |
| `identifier_type` | enum | 条件必填 | 有 `unified_identifier` 时必填；企业=`USCC`，个人=`CN_ID_CARD/PASSPORT/OTHER_GOV_ID` | 已确认 |
| `unified_identifier` | string | 否 | 统一标识；企业 18 位大写字母数字，个人按证件类型校验 | 已确认 |
| `address` | string | 否 | 地址 | 已确认 |
| `status` | enum | 是 | 正常/停用 | 已确认 |
| `historical_contract_count` | number | 否 | 历史签约数（派生） | 已确认（派生） |
| `risk_tags` | string[] | 否 | 风险标签 | 已确认 |
| `payment_term_preference` | string | 否 | 账期偏好 | 已确认 |

## 3.9 AnalyticsMetrics（统计口径字段）

| 字段 | 类型 | 必填 | 规则/说明 | 状态 |
|---|---|---|---|---|
| `stat_period` | string | 是 | 统计周期（默认本月，可切换） | 已确认 |
| `perspective_party_id` | string | 是 | 当前视角主体 | 已确认 |
| `total_income` | number | 是 | 总收入合计（派生） | 已确认（派生） |
| `self_operated_rent_income` | number | 是 | 自营租金收入（派生） | 已确认（派生） |
| `agency_service_income` | number | 是 | 代理服务费收入（派生） | 已确认（派生） |
| `customer_entity_count` | number | 是 | 客户主体数（派生）；按 `customer_party_id` 去重 | 已确认（派生） |
| `customer_contract_count` | number | 是 | 客户合同数（派生）；按 `contract_id` 去重 | 已确认（派生） |
| `internal_rent_income` | number | 否 | 内部租赁收入（派生） | 已确认（派生） |
| `terminal_rent_income` | number | 否 | 终端租赁收入（派生） | 已确认（派生） |

## 3.10 ContractLedgerEntry（合同台账条目）

> 定位：合同激活（`status → ACTIVE`）时自动生成的月度台账，记录每个自然月的应收/应付金额与回款状态。  
> 物理表：`contract_ledger_entries`，FK → `contracts.contract_id`，完全取代旧 `rent_ledger`。

| 字段 | 类型 | 必填 | 规则/说明 | 状态 |
|---|---|---|---|---|
| `entry_id` | string | 是 | 主键（UUID） | 已确认 |
| `contract_id` | string | 是 | FK → Contract 基表（`contracts.contract_id`） | 已确认 |
| `year_month` | string | 是 | 账期，格式 `YYYY-MM`；唯一约束：`(contract_id, year_month)` 防重复生成 | 已确认 |
| `due_date` | date | 是 | 应付/应收日（按 `LeaseContractDetail.payment_cycle` 规则计算） | 已确认 |
| `amount_due` | decimal(18,2) | 是 | 应付金额，>=0；含税/不含税口径与 `is_tax_included` 一致 | 已确认 |
| `currency_code` | string | 是 | 币种，MVP 固定 `CNY` | 已确认 |
| `is_tax_included` | boolean | 是 | 含税标记，从所属合同继承 | 已确认 |
| `tax_rate` | decimal(5,4) | 否 | 税率，从所属合同继承；范围 `[0,1]` | 已确认 |
| `payment_status` | enum | 是 | `unpaid`（未付）/ `paid`（已付）/ `overdue`（逾期）/ `partial`（部分付）；默认 `unpaid` | 已确认 |
| `paid_amount` | decimal(18,2) | 否 | 实收金额，>=0，默认 0 | 已确认 |
| `notes` | text | 否 | 备注 | 已确认 |
| `created_at` | datetime | 是 | 系统字段 | 已确认 |
| `updated_at` | datetime | 是 | 系统字段 | 已确认 |

**约束**：
- 合同 `已到期/已终止` 后停止生成未来台账，历史台账只读。
- `payment_status` 由人工或外部回款系统更新，不自动计算。
- 幂等：`year_month` 已存在则跳过，不重新生成。

## 3.11 ContractAuditLog（合同操作审计日志）

> 定位：合同每次状态流转或关键操作的审计留痕，不可修改。物理表：`contract_audit_logs`。

| 字段 | 类型 | 必填 | 规则/说明 | 状态 |
|---|---|---|---|---|
| `log_id` | string | 是 | 主键（UUID） | 已确认 |
| `contract_id` | string | 是 | FK → Contract 基表 | 已确认 |
| `action` | string | 是 | 操作类型：`submit_review` / `approve` / `reject` / `expire` / `terminate` / `void` | 已确认 |
| `old_status` | string | 否 | 操作前的 `status` 值 | 已确认 |
| `new_status` | string | 否 | 操作后的 `status` 值 | 已确认 |
| `review_status_old` | string | 否 | 操作前的 `review_status` 值 | 已确认 |
| `review_status_new` | string | 否 | 操作后的 `review_status` 值 | 已确认 |
| `reason` | string | 条件必填 | `reject` / `void` / `terminate` 时必填 | 已确认 |
| `operator_id` | string | 否 | 操作人 ID | 已确认 |
| `operator_name` | string | 否 | 操作人姓名（冗余展示） | 已确认 |
| `related_entry_id` | string | 否 | 关联单号（冲销台账时填写，对应 `ContractLedgerEntry.entry_id`） | 已确认 |
| `created_at` | datetime | 是 | 系统字段；操作时刻，不可修改 | 已确认 |

**约束**：
- 仅允许 INSERT，禁止 UPDATE / DELETE（审计表不可篡改）。
- 每次成功状态流转必须同事务内写入一条日志。

---

## 4. 仍需确认（v1.0 前必须闭环）

---

## 5. 冻结与变更规则

- 每个字段变更必须标注影响对象、接口、报表与迁移策略。
- `已确认` 字段变更需评审，禁止直接改口径。
- 附录版本建议：`v0.3 -> v1.0`，`v1.0` 作为开发冻结版本。

---

## 6. 当前系统资产字段对照（As-Built -> v0.3，已收敛）

> 目的：以当前实现字段为基准，给出“准备如何处理”的候选方案，供评审拍板。  
> 说明：本章为 As-Built 对照与落地策略，不直接替代第 3.1 节冻结口径。

### 6.1 当前资产主表字段与拟处理策略

| 当前字段（As-Built） | 当前语义 | 与 v0.3 关系 | 拟处理策略（当前口径） |
|---|---|---|---|
| `id` | 资产主键 | 对应 `asset_id` | 直接更名为 `asset_id`，不保留 `id` 兼容字段 |
| `ownership_category` | 权属类别 | v0.3 未纳入核心 | 直接删除，不再作为资产主档字段保留 |
| `project_name` | 项目名称（冗余展示字段） | v0.3 用 `project_id` | 直接删除；项目名称通过 `project_id` 关联 `Project.project_name` 获取 |
| `property_name` | 物业名称 | 对应 `asset_name` | 直接改为 `asset_name` |
| `address` | 资产地址 | 同名字段 | 保留；v1.0 必填，不可空 |
| `ownership_status` | 产权确权状态 | v0.3 未纳入核心 | 更名为 `title_status`；定义为法律确权状态，建议枚举：`已确权/部分确权/未确权/权属争议` |
| `property_nature` | 资产属性（经营性/公房/其他非经营） | v0.3 未纳入核心 | 保留并收敛口径；与 `usage_status` 解耦 |
| `usage_status` | 资产使用状态 | v0.3 未纳入核心 | 保留并收敛枚举：`出租/自用/空置/改造中/停用` |
| `management_entity` | 经营管理单位（旧口径） | v0.3 用 `manager_party_id` | 直接下线删除；统一通过 `manager_party_id` 关联主体获取展示 |
| `business_category` | 业态类别 | 非冻结核心字段 | 删除，不再保留 |
| `is_litigated` | 是否涉诉 | v0.3 未纳入核心 | 保留为扩展字段 |
| `notes` | 备注 | v0.3 未纳入核心 | 保留为扩展字段 |
| `land_area` | 土地面积 | v0.3 未纳入核心 | 保留为扩展字段 |
| `actual_property_area` | 实际房产面积 | v0.3 未纳入核心 | 保留为扩展字段 |
| `rentable_area` | 可出租面积 | 同名字段 | 保留；创建接口改为必填 |
| `rented_area` | 已出租面积（总） | 对应总口径 | 保留为资产主档总已租面积；不拆分内部/终端 |
| `cached_occupancy_rate` | 缓存出租率（总） | 对应 `occupancy_rate_total` | 直接更名为 `occupancy_rate_total`；派生只读，系统自动重算，不允许手工写入 |
| `non_commercial_area` | 非经营面积 | v0.3 未纳入核心 | 保留为扩展字段；约束 `>=0`，且不大于 `actual_property_area`（如维护该字段） |
| `include_in_occupancy_rate` | 是否计入出租率统计 | v0.3 未纳入核心 | 保留为扩展字段；默认 `true`，仅影响统计口径 |
| `certificated_usage` | 证载用途 | v0.3 未纳入核心 | 保留为扩展字段（文本型） |
| `actual_usage` | 实际用途 | v0.3 未纳入核心 | 删除，不再作为资产主档字段保留 |
| `tenant_type` | 承租方类型 | 非冻结核心字段 | 下沉到合同域，资产主档删除 |
| `is_sublease` | 是否分租/转租 | v0.3 未纳入核心 | 下沉到合同域，资产主档删除 |
| `sublease_notes` | 分租备注 | v0.3 未纳入核心 | 下沉到合同域，资产主档删除 |
| `revenue_mode` | 经营模式（承租/代理） | v0.3 未纳入核心 | 统一命名为 `revenue_mode`（显示名：经营模式），不保留双字段兼容 |
| `operation_status` | 经营状态 | v0.3 未纳入核心 | 删除，不再保留 |
| `manager_name` | 管理责任人 | v0.3 未纳入核心 | 删除；通过 `manager_party_id` 关联主体名称获取 |
| `operation_agreement_start_date` | 接收协议开始 | v0.3 未纳入核心 | 下沉到协议/合同域，资产主档删除 |
| `operation_agreement_end_date` | 接收协议结束 | v0.3 未纳入核心 | 下沉到协议/合同域，资产主档删除 |
| `operation_agreement_attachments` | 接收协议文件 | v0.3 未纳入核心 | 下沉到协议/合同域，资产主档删除 |
| `terminal_contract_files` | 终端合同文件 | 与终端场景相关 | 下沉到终端合同域，资产主档删除 |
| `data_status` | 数据状态 | 同名字段 | 保留（冻结核心字段）；枚举 `正常/已删除`，仅逻辑删除 |
| `version` | 乐观锁版本 | v0.3 未纳入核心 | 保留系统字段 |
| `tags` | 标签 | v0.3 未纳入核心 | 保留为扩展字段；需配套打标签功能（创建/编辑/筛选/清除），否则暂不入库 |
| `created_by` | 创建人 | v0.3 跨对象系统字段 | 保留系统字段；创建自动写入 |
| `updated_by` | 更新人 | v0.3 跨对象系统字段 | 保留系统字段；更新自动写入 |
| `audit_notes` | 审核备注（旧口径） | 近似 `review_reason` | 直接收敛到 `review_reason`；迁移完成后删除 `audit_notes` |
| `created_at` | 创建时间 | 跨对象统一字段 | 保留系统字段；系统自动写入，只读 |
| `updated_at` | 更新时间 | 跨对象统一字段 | 保留系统字段；系统自动更新，只读 |
| `project_id` | 单项目关联 | 对应 `project_id` | 保留为当前有效项目关联（单值）；历史关联通过审计日志追溯 |
| `owner_party_id` | 单产权主体 | 对应 `owner_party_id` | 保留为当前有效主产权主体（单值）；历史关联通过审计日志追溯 |
| `manager_party_id` | 运营管理主体 | 同名字段 | 保留核心字段；单值必填，不升级多值 |
| `organization_id` | 组织 ID（deprecated） | v0.3 未纳入核心 | 直接下线删除；不再作为资产主档字段 |
| `ownership_id` | 权属 ID（deprecated） | v0.3 用主体关系 | 直接下线删除；统一使用 `owner_party_id` |

### 6.2 当前已存在的投影/计算字段（非主表列）

| 当前字段 | 类型 | 拟处理策略（当前口径） |
|---|---|---|
| `unrented_area` | 计算字段 | 保持派生，不允许写库 |
| `occupancy_rate` | 计算字段 | 旧投影名下线；对外统一 `occupancy_rate_total` |
| `ownership_entity` | 关联投影 | 保持投影，不写库 |
| `tenant_name` | 合同投影 | 保持投影，不写库 |
| `lease_contract_number` | 合同投影 | 保持投影，不写库 |
| `contract_start_date` | 合同投影 | 保持投影，不写库 |
| `contract_end_date` | 合同投影 | 保持投影，不写库 |
| `monthly_rent` | 合同投影 | 保持投影，不写库 |
| `deposit` | 合同投影 | 保持投影，不写库 |

### 6.3 准备新增（已确认落地）

| 目标字段（v0.3） | 准备方式（已确认） |
|---|---|
| `asset_code` | 新增物理列 + 唯一约束 + 编码生成规则 |
| `asset_form` | 新增枚举列 |
| `spatial_level` | 新增枚举列 |
| `business_usage` | 新增枚举列 |
| `project_id` | 当前有效项目关联（单值，As-Built 已存在，直接保留） |
| `owner_party_id` | 当前有效主产权主体（单值，As-Built 已存在，直接保留） |
| `review_status` | 新增审核状态字段，v1.0 落地 |
| `review_by` | 新增审核人字段，v1.0 落地 |
| `reviewed_at` | 新增审核时间字段，v1.0 落地 |
| `review_reason` | 新增审核原因字段（与 `audit_notes` 收敛），v1.0 落地 |

### 6.4 已拍板决策（2026-03-03）

1. `address` 保持必填，不调整为可选。
2. `owner_party_id` 保持单值，表示当前有效主产权主体；历史产权变更通过审计日志追溯。
3. `review_*`（`review_status/review_by/reviewed_at/review_reason`）在 v1.0 落地。
4. Asset 地址校验策略冻结为“半结构化地址”：
   - 字段形态：`province_code`、`city_code`、`district_code` + `address_detail`（均必填）。
   - 校验：`address_detail` 需 `trim` 后长度 `5-200`，禁止纯空白。
   - 展示：`address` 作为展示字段由系统拼接生成（只读，不允许手工覆盖）。
   - 字典：行政区代码统一来源于国家标准行政区划代码字典（GB/T 2260 口径）。
   - 存量迁移：可解析数据自动回填结构化字段，不可解析数据标记人工补录。

### 6.5 已确认结论（2026-03-03，按 6.1 字段顺序）

1. `id`：直接更名为 `asset_id`，不保留 `id` 兼容字段。
2. `ownership_category`：直接删除，不再作为资产主档字段保留。
3. `project_name`：直接下线删除；所属项目名称通过 `project_id` 关联 `Project.project_name` 获取。
4. `property_name`：直接更名为 `asset_name`，不保留旧字段。
5. `address`：保持必填，采用半结构化地址规则（行政区三级 + `address_detail`），`address_detail` 需 `trim` 后长度 `5-200`。
6. `ownership_status`：更名为 `title_status`（显示名：产权确权状态），用于表达法律确权状态，不承载经营或使用语义。
7. `property_nature`：保留，语义定义为“资产属性”，用于区分 `经营性/公房/其他非经营`。
8. `usage_status`：保留，枚举冻结为 `出租/自用/空置/改造中/停用`。
9. `management_entity`：直接下线删除，统一使用 `manager_party_id` 表达与关联管理主体。
10. `business_category`：删除，不再作为资产主档字段保留。
11. `is_litigated`：保留为扩展字段。
12. `notes`：保留为扩展字段。
13. `land_area`：保留为扩展字段。
14. `actual_property_area`：保留为扩展字段。
15. `rentable_area`：保留核心字段，创建接口必填。
16. `rented_area`：保留资产主档总已租面积，不拆分内部/终端口径。
17. `cached_occupancy_rate`：直接更名为 `occupancy_rate_total`，作为派生只读字段，系统根据 `rented_area/rentable_area` 自动重算。
18. `non_commercial_area`：保留扩展字段，约束 `>=0`，且不大于 `actual_property_area`（如维护该字段）。
19. `include_in_occupancy_rate`：保留扩展字段，默认 `true`，仅影响统计口径。
20. `certificated_usage`：保留扩展字段（文本型）。
21. `actual_usage`：删除，不再作为资产主档字段保留。
22. `tenant_type`：下沉到合同域，资产主档删除。
23. `is_sublease`：下沉到合同域，资产主档删除。
24. `sublease_notes`：下沉到合同域，资产主档删除。
25. `revenue_mode`：统一命名为 `revenue_mode`（显示名：经营模式），不保留双字段兼容。
26. `operation_status`：删除，不再保留。
27. `manager_name`：删除，通过 `manager_party_id` 关联主体名称获取。
28. `operation_agreement_start_date`：下沉到协议/合同域，资产主档删除。
29. `operation_agreement_end_date`：下沉到协议/合同域，资产主档删除。
30. `operation_agreement_attachments`：下沉到协议/合同域，资产主档删除。
31. `terminal_contract_files`：下沉到终端合同域，资产主档删除。
32. `data_status`：保留核心字段（`正常/已删除`），仅逻辑删除。
33. `version`：保留系统乐观锁字段，不作为业务可编辑字段。
34. `tags`：保留扩展字段，但必须配套打标签功能（创建/编辑/筛选/清除）；若本期不建设则暂不入库。
35. `created_by`：保留系统字段，创建时自动写入。
36. `updated_by`：保留系统字段，更新时自动写入。
37. `audit_notes`：直接收敛到 `review_reason`，迁移完成后删除 `audit_notes`。
38. `created_at`：保留系统字段，系统自动写入且只读。
39. `updated_at`：保留系统字段，系统自动更新且只读。
40. `project_id`：保留为当前有效项目关联（单值）；历史关联通过审计日志追溯。
41. `owner_party_id`：保留为当前有效主产权主体（单值）；历史产权变更通过审计日志追溯。
42. `manager_party_id`：保留核心字段，单值必填，不升级多值。
43. `organization_id`：直接下线删除，不再作为资产主档字段保留。
44. `ownership_id`：直接下线删除，统一使用 `owner_party_id`。

补充落地项（非 As-Built 字段映射）：
- `review_*`（`review_status/review_by/reviewed_at/review_reason`）在 v1.0 全量落地。
说明口径：
- 出租：已对外租赁并产生收益。
- 自用：内部业务部门正常使用中。
- 空置：具备使用条件，随时可租、可用的待消化状态。
- 改造中：因装修、翻新、施工等原因，短期内不具备使用条件的过渡状态。
- 停用：因查封、危房、报废、准备出售等原因，被主动冻结或长期不可用。

---

## 7. 当前系统项目字段对照（As-Built -> v0.3，已收敛）

> 目的：以当前实现字段为基准，给出项目域“直接收口”落地策略。  
> 说明：本章用于指导项目域字段修订，不替代第 3.2 节冻结口径。

### 7.1 当前项目主表字段与拟处理策略

| 当前字段（As-Built） | 当前语义 | 与 v0.3 关系 | 拟处理策略（当前口径） |
|---|---|---|---|
| `id` | 项目主键 | 对应 `project_id` | 直接更名为 `project_id`，不保留 `id` 兼容字段 |
| `name` | 项目名称 | 对应 `project_name` | 直接更名为 `project_name` |
| `short_name` | 项目简称 | v0.3 未纳入核心 | 保留为扩展字段 |
| `code` | 项目编码 | 对应 `project_code` | 直接更名为 `project_code`；统一格式 `PRJ-[A-Z0-9]{4,12}-[0-9]{6}` |
| `project_type` | 项目类型 | v0.3 未纳入核心 | 保留为扩展字段 |
| `project_scale` | 项目规模 | v0.3 未纳入核心 | 保留为扩展字段 |
| `project_status` | 项目业务状态 | 对应 `status` | 直接收敛为 `status`；枚举代码值冻结为 `planning/active/paused/completed/terminated` |
| `start_date` | 开始日期 | v0.3 未纳入核心 | 保留为扩展字段 |
| `end_date` | 结束日期 | v0.3 未纳入核心 | 保留为扩展字段 |
| `expected_completion_date` | 预计完成日期 | v0.3 未纳入核心 | 保留为扩展字段 |
| `actual_completion_date` | 实际完成日期 | v0.3 未纳入核心 | 保留为扩展字段 |
| `address` | 项目地址 | v0.3 未纳入核心 | 保留为扩展字段 |
| `city` | 城市 | v0.3 未纳入核心 | 保留为扩展字段 |
| `district` | 区域 | v0.3 未纳入核心 | 保留为扩展字段 |
| `province` | 省份 | v0.3 未纳入核心 | 保留为扩展字段 |
| `project_manager` | 项目经理 | v0.3 未纳入核心 | 保留为扩展字段 |
| `project_phone` | 项目电话 | v0.3 未纳入核心 | 保留为扩展字段 |
| `project_email` | 项目邮箱 | v0.3 未纳入核心 | 保留为扩展字段 |
| `total_investment` | 总投资 | v0.3 未纳入核心 | 保留为扩展字段 |
| `planned_investment` | 计划投资 | v0.3 未纳入核心 | 保留为扩展字段 |
| `actual_investment` | 实际投资 | v0.3 未纳入核心 | 保留为扩展字段 |
| `project_budget` | 项目预算 | v0.3 未纳入核心 | 保留为扩展字段 |
| `project_description` | 项目描述 | v0.3 未纳入核心 | 保留为扩展字段 |
| `project_objectives` | 项目目标 | v0.3 未纳入核心 | 保留为扩展字段 |
| `project_scope` | 项目范围 | v0.3 未纳入核心 | 保留为扩展字段 |
| `management_entity` | 管理单位（DEPRECATED） | v0.3 用 `manager_party_id` | 直接下线删除，不做兼容 |
| `manager_party_id` | 项目经营管理主体 | 同名核心字段 | 保留核心字段；单值必填 |
| `organization_id` | 所属组织 ID（DEPRECATED） | v0.3 未纳入核心 | 直接下线删除（含 API/Service alias 与 CRUD fallback） |
| `ownership_entity` | 权属单位（DEPRECATED） | v0.3 未纳入核心 | 直接下线删除，不做兼容 |
| `construction_company` | 施工单位 | v0.3 未纳入核心 | 保留为扩展字段 |
| `design_company` | 设计单位 | v0.3 未纳入核心 | 保留为扩展字段 |
| `supervision_company` | 监理单位 | v0.3 未纳入核心 | 保留为扩展字段 |
| `is_active` | 是否启用 | 与 `status` 语义重叠 | 直接下线删除，统一使用 `status` |
| `data_status` | 数据状态 | 对应 `data_status` | 保留核心字段；枚举 `正常/已删除`，仅逻辑删除 |
| `created_at` | 创建时间 | 跨对象统一字段 | 保留系统字段；系统自动写入且只读 |
| `updated_at` | 更新时间 | 跨对象统一字段 | 保留系统字段；系统自动更新且只读 |
| `created_by` | 创建人 | 跨对象统一字段 | 保留系统字段；创建时自动写入 |
| `updated_by` | 更新人 | 跨对象统一字段 | 保留系统字段；更新时自动写入 |
| `assets` | 项目-资产直连关系（DEPRECATED） | v0.3 用 `asset_ids_current` | 删除直连关系；统一通过 `project_assets` 关系聚合 |
| `ownership_relations` | 项目-权属关系 | v0.3 未纳入核心 | 保留关系模型，不作为项目主档字段直写 |

### 7.2 当前兼容入参与别名（DEPRECATED）

| 兼容项（As-Is） | 位置 | 拟处理策略（当前口径） |
|---|---|---|
| `ownership_ids` | `ProjectCreate/ProjectUpdate` 入参 | 直接下线删除，不做入参兼容 |
| `organization_id` alias | `ProjectService.create_project(...)` 参数 | 直接下线删除，不做 alias 兼容 |
| `organization_id` legacy fallback | `CRUDProject` 过滤与作用域回退 | 直接下线删除，不做 legacy fallback |

### 7.3 准备新增（已确认落地）

| 目标字段（v0.3） | 准备方式（已确认） |
|---|---|
| `status` | 由 `project_status` 直接收敛并统一枚举代码值 |
| `project_code` | 由 `code` 直接收敛并统一编码格式 `PRJ-[A-Z0-9]{4,12}-[0-9]{6}` |
| `asset_ids_current` | 读模型聚合字段（由 `project_assets` 映射） |
| `asset_count_current` | 派生字段（由 `project_assets` 聚合） |
| `review_status` | 新增审核状态字段，v1.0 落地 |
| `review_by` | 新增审核人字段，v1.0 落地 |
| `reviewed_at` | 新增审核时间字段，v1.0 落地 |
| `review_reason` | 新增审核原因字段，v1.0 落地 |

### 7.4 已拍板决策（2026-03-03）

1. 项目域 DEPRECATED 字段全部直接收口，不做兼容保留。
2. 状态字段收敛为 `status + data_status` 两层语义，`is_active` 直接下线。
3. 项目编码统一为 `project_code`，编码格式冻结为 `PRJ-[A-Z0-9]{4,12}-[0-9]{6}`。
4. `manager_party_id` 保留为核心字段并改为单值必填。
5. `review_*`（`review_status/review_by/reviewed_at/review_reason`）在 v1.0 全量落地。

---

## 8. ContractGroup 派生状态与合同生命周期（2026-03-03 确认）

> 说明：ContractGroup 为纯容器，不拥有独立生命周期状态。组“状态”由组内合同状态实时派生。审核在合同级进行。

### 8.1 ContractGroup 派生状态规则

| 派生状态 | 判定规则 | 含义 |
|---|---|---|
| `筹备中` | 组内无任何 `生效` 合同 | 交易尚未开始执行 |
| `生效中` | 组内存在至少一份 `生效` 合同 | 交易正在执行中 |
| `已结束` | 组内全部合同为 `已到期` 或 `已终止`（且至少有一份合同） | 交易已完结 |

- 派生状态为只读展示字段，**不允许手工写入**。
- 查询/筛选/统计时通过聚合组内合同状态实时计算。

### 8.2 Contract（合同）状态定义

| 状态 | 含义 | 进入统计 | 生成台账 |
|---|---|---|---|
| `草稿` | 录入阶段，可自由编辑 | 否 | 否 |
| `待审` | 审核阶段，关键字段锁定 | 否 | 否 |
| `生效` | 执行阶段 | 是 | 是（按 RentTerm 自动生成） |
| `已到期` | 按 `effective_to` 自然到期 | 历史只读 | 停止新增 |
| `已终止` | 人工提前终止 | 历史只读 | 停止执行，保留终止原因 |

- `已到期` 与 `已终止` 互斥。
- 合同 `effective_from` 不得早于所属合同组的 `effective_from`（组的 `effective_to` 为派生字段，不作为合同约束）。
- 禁止物理删除，仅允许作废/冲销+重建。
- 反审核 = 作废+重建，不是回退到上一状态。

### 8.3 结算与关联边界（试行）

- `settlement_rule` 仅保留组级结算框架（最小 5 键），不承载合同执行明细。
- 违约金/减免/分期等执行细节字段本次不纳入组级，试行下沉到合同级维护。
- `revenue_share_rule` 本次仅结构化留存，不纳入自动分润计算。
- `upstream_contract_ids`、`downstream_contract_ids` 由 ContractRelation 实时派生。

### 8.4 Contract `sign_date` 补录策略（已确认）

- `sign_date` 在草稿阶段允许为空，不自动回填（禁止用 `effective_from` 代填）。
- 合同在进入 `待审` 或 `生效` 前，`sign_date` 必填。
- 支持单条补录与批量补录（建议最小键：`contract_id` + `sign_date` + `补录说明`）。
- 补录动作必须记录审计留痕（操作人、时间、前后值、补录原因）。
- 列表需支持“`sign_date` 为空”筛选，便于集中治理。

---

## 9. 风险防控功能参考（后续版本，不纳入本次）

> 说明：本节仅作为后续风险防控能力建设参考（V1.1+ 候选），不纳入本次 v0.3 字段冻结与 MVP 验收范围。

### 9.1 定位

- `risk_tags` 在当前版本仅作为结构化标签与筛选条件使用。
- 后续版本可升级为“风险发现 + 审核分流 + 运营监控 + 复盘统计”统一入口。

### 9.2 典型场景（参考）

1. 收益倒挂：承租模式下上游应付高于下游应收，标记现金流倒挂风险并提升审核等级。
2. 关键条款缺失：`settlement_rule` 关键键缺失，标记关键条款缺失风险并阻止提审。
3. 主体关系不一致：合同组主体与组内关键合同主体不一致，标记主体一致性风险并阻止生效。
4. 代理口径冲突：代理模式下误将租金作为运营方收入，标记口径冲突风险并阻止生效。
5. 生效后逾期集中：连续周期回款异常，标记履约风险并进入重点跟踪清单。
6. 外部法律事件：人工标记涉诉/查封等事件，触发高风险分层管理。

### 9.3 后续建设边界（参考）

- 风险标签来源可演进为“规则自动 + 人工补充”双来源。
- 规则命中可分为硬门禁（阻断）与软门禁（预警）两类。
- 建议保留风险事件留痕（来源、证据、处理人、处理时间）用于审计与复盘。

---

## 10. 合同旧字段 DEPRECATED 清单与映射（2026-03-03 确认）

> 说明：当前 `RentContract` As-Built 字段到五层模型的映射。口径：不迁移，测试数据可删。

### 10.1 直接下线删除

| As-Built 字段 | 原因 |
|---|---|
| `ownership_id` | DEPRECATED legacy FK，统一使用 `lessor_party_id` |
| `contract_type` 枚举 | 被 `contract_direction` + `group_relation_type` 替代 |
| `upstream_contract_id` (FK 自关联) | 下沉到 `ContractRelation` 表 |
| `source_session_id` | PDF 导入追踪，移到导入任务关联 |
| `contract_status` (旧字符串) | 统一为基表 `status` 枚举 |

### 10.2 下沉到 LeaseContractDetail

| As-Built 字段 | 新归属 |
|---|---|
| `total_deposit` | `LeaseContractDetail.total_deposit` |
| `rent_amount` | `LeaseContractDetail.rent_amount` |
| `rent_amount_excl_tax` | `LeaseContractDetail.rent_amount_excl_tax`（派生） |
| `monthly_rent_base` | `LeaseContractDetail.monthly_rent_base` |
| `payment_cycle` | `LeaseContractDetail.payment_cycle` |
| `payment_terms` | `LeaseContractDetail.payment_terms` |
| `tenant_name/contact/phone/address` | `LeaseContractDetail.tenant_*` |
| `tenant_usage` | `LeaseContractDetail.tenant_usage` |
| `owner_name/contact/phone` | `LeaseContractDetail.owner_*` |

### 10.3 下沉到 AgencyAgreementDetail

| As-Built 字段 | 新归属 |
|---|---|
| `service_fee_rate` | `AgencyAgreementDetail.service_fee_ratio` |

### 10.4 保留在 Contract 基表

| As-Built 字段 | 新字段名 | 说明 |
|---|---|---|
| `id` | `contract_id` | 主键更名 |
| `contract_number` | `contract_number` | 保留 |
| `sign_date` | `sign_date` | 保留 |
| `start_date` | `effective_from` | 更名 |
| `end_date` | `effective_to` | 更名 |
| `owner_party_id` | `lessor_party_id` | 语义升级为出租方/委托方 |
| `manager_party_id` | 保留 | 经营管理方 |
| `tenant_party_id` | `lessee_party_id` | 语义升级为承租方/受托方 |
| `asset_ids`（新增） | `asset_ids` | 关联资产（多对多），为 ContractGroup.asset_ids 子集 |
| `contract_notes` | `contract_notes` | 保留 |
| `data_status` / `version` | 保留 | 系统字段 |
| `created_at` / `updated_at` | 保留 | 系统字段 |

### 10.5 新增（无 As-Built 对应）

| 新字段 | 归属 | 说明 |
|---|---|---|
| `contract_group_id` | Contract 基表 | 所属合同组 |
| `contract_direction` | Contract 基表 | 出租/承租 |
| `group_relation_type` | Contract 基表 | 上游/下游/委托/直租 |
| `review_*` 四件套 | Contract 基表 | 审核状态/人/时间/原因 |
| `fee_calculation_base` | AgencyAgreementDetail | 计费基数 |
| `agency_scope` | AgencyAgreementDetail | 代理范围 |
| ContractRelation 全表 | 独立表 | 合同关系 |

---

## 11. 可执行约束（2026-03-03 确认）

### 11.1 审核触发

- 审核在 **合同级** 进行（`Contract.review_status`），不在合同组级进行。
- 审核通过 (`已审`) 是合同从 `待审` 进入 `生效` 的前置条件。
- 反审核 = 将合同作废 + 重建新合同，禁止直接回退状态。
- 反审核必须填写 `review_reason`。

### 11.2 台账生成

- 触发时机：合同 `status` 变为 `生效`（`ACTIVE`）时，由 `approve()` 在同一事务内触发。
- 数据来源：按 **`ContractRentTerm`**（分阶段租金条款子表，见 §3.5.1）逐阶段展开自然月，生成月度 **`ContractLedgerEntry`**（见 §3.10，物理表 `contract_ledger_entries`）。
- 台账 FK 挂 `contracts.contract_id`（新 Contract 基表，不区分租赁/代理）。
- 代理协议合同（`AgencyAgreementDetail`，无 `ContractRentTerm`）激活时台账生成跳过，不报错；服务费台账为 M3 范围。
- 合同 `已到期/已终止` 后停止生成未来台账，历史台账只读。
- 幂等：`(contract_id, year_month)` 唯一约束保证重复触发不重复生成。

### 11.3 统计入库

- 仅 `status = 生效` 的合同进入统计口径。
- ContractGroup `derived_status` 由组内合同聚合，不直接参与统计过滤。
- 收入口径按 `ContractGroup.revenue_mode` 区分：`lease` 模式计入自营租金收入，`agency` 模式计入代理服务费收入。


### 11.4 补充协议与合同变更



- 补充协议（如延期、金额调整）通过直接修改现有合同字段实现，MVP 不将补充协议建模为独立对象。

- 变更必须记录审计留痕（RentContractHistory：操作人、时间、old_data/new_data、变更原因）。

- 补充协议文件作为附件上传到合同（RentContractAttachment）。

- 合同 `effective_to` 变更后，所属 ContractGroup 的 `effective_to` 自动重新派生。

- 合同变更不影响已生成的历史台账；仅未来期间的台账按新条款重新生成。



### 11.5 续签与周期管理



- ContractGroup 代表一个交易周期，不代表交易关系。续签 = 新建 ContractGroup。

- 新组的 `predecessor_group_id` 指向旧组，新合同通过 ContractRelation `renewal` 链接旧合同。

- 旧组保持 `已结束` 状态，不允许重新激活。

- 续签时系统自动复制旧组的 `asset_ids`、`revenue_mode`、相同主体信息作为新组初始值。

