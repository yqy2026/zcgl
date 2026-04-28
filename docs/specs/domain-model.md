# 领域模型契约

## 1. 文档定位

本文档描述当前目标态的业务对象、字段、状态、枚举和统计口径。产品叙事见 `docs/prd.md`，API 契约见 `docs/specs/api-contract.md`，实现追踪见 `docs/traceability/requirements-trace.md`。

本文档只保留当前目标态，不记录历史字段清理过程、访谈过程或实现证据。

## 2. 跨对象规则

| 规则 | 说明 |
|---|---|
| 主键 | 业务对象主键统一使用字符串 ID |
| 时间字段 | `created_at`、`updated_at` 由系统写入 |
| 审核字段 | 需要审核的对象统一包含 `review_status`、`review_by`、`reviewed_at`、`review_reason` |
| 关键记录删除 | 合同组、合同、台账等关键记录禁止物理删除，只允许逻辑删除、作废、冲销或重建 |
| 派生字段 | 出租率、汇总金额、计数等派生字段不允许人工直接写入 |
| 编码规则 | `asset_code` 按产权方编码段生成，`project_code` 按运营方编码段生成，`group_code` 按经营主责方编码段生成 |
| 编码格式 | `<TYPE>-<SEGMENT>-<SERIAL>`，`SERIAL` 为 6 位数字并按 `TYPE + SEGMENT` 单调递增 |

## 3. 核心对象

| 对象 | 定位 |
|---|---|
| Party | 统一主体主档，承载产权方、运营方、客户等主体身份 |
| Asset | 资产核心主实体 |
| Project | 资产运营管理归集单元 |
| ContractGroup | 一笔经营关系的交易包 |
| Contract | 合同基表，承载所有合同公共字段 |
| LeaseContractDetail | 租赁类合同明细 |
| AgencyAgreementDetail | 代理协议明细 |
| ContractRentTerm | 分阶段租金条款 |
| ContractRelation | 上下游或代理合同关系 |
| ContractLedgerEntry | 租金台账条目 |
| ServiceFeeLedger | 代理服务费台账 |
| ContractAuditLog | 合同操作审计日志 |
| CustomerProfile | 客户视图档案，由 Party 和合同历史投影形成 |
| ApprovalInstance | 审批实例 |
| ApprovalTaskSnapshot | 审批待办快照 |
| ApprovalActionLog | 审批动作日志 |

## 4. 字段契约

### 4.1 Asset

| 字段 | 类型 | 必填 | 规则 |
|---|---|---|---|
| `asset_id` | string | 是 | 资产主键 |
| `asset_code` | string | 是 | 全局唯一，格式 `AST-[A-Z0-9]{4,12}-[0-9]{6}` |
| `asset_name` | string | 是 | 资产名称 |
| `asset_form` | enum | 是 | 土地、建筑、构筑物、车位、仓储、其他 |
| `spatial_level` | enum | 是 | 地块、园区、楼宇、楼层、房间、商铺 |
| `business_usage` | enum | 是 | 商业、办公、仓储、工业、综合、其他 |
| `province_code` | string | 是 | 省级行政区代码 |
| `city_code` | string | 是 | 市级行政区代码 |
| `district_code` | string | 是 | 区县行政区代码 |
| `address_detail` | string | 是 | 详细地址，trim 后长度 5-200 |
| `address` | string | 是 | 系统拼接的只读展示地址 |
| `rentable_area` | number | 是 | 可出租面积，>= 0 |
| `rented_area` | number | 否 | 已出租面积，>= 0 |
| `occupancy_rate_total` | number | 否 | 总出租率，派生 |
| `project_id` | string | 否 | 当前有效关联项目，同一时点只允许一个 |
| `owner_party_id` | string | 是 | 当前有效主产权主体，同一时点只允许一个 |
| `manager_party_id` | string | 是 | 运营管理主体 |
| `data_status` | enum | 是 | 正常、已删除 |
| `review_status` | enum | 是 | `draft`、`pending`、`approved`、`reversed` |
| `review_by` | string | 否 | 审核人 |
| `reviewed_at` | datetime | 否 | 审核时间 |
| `review_reason` | string | 否 | 审核原因，反审核时必填 |

### 4.2 Project

| 字段 | 类型 | 必填 | 规则 |
|---|---|---|---|
| `project_id` | string | 是 | 项目主键 |
| `project_code` | string | 是 | 唯一，格式 `PRJ-[A-Z0-9]{4,12}-[0-9]{6}` |
| `project_name` | string | 是 | 项目名称 |
| `manager_party_id` | string | 是 | 项目运营管理方 |
| `asset_ids_current` | string[] | 否 | 当前有效资产，派生 |
| `asset_count_current` | number | 否 | 当前有效资产数，派生 |
| `status` | enum | 是 | `planning`、`active`、`paused`、`completed`、`terminated` |
| `data_status` | enum | 是 | 正常、已删除 |
| `review_status` | enum | 是 | `draft`、`pending`、`approved`、`rejected`，项目不支持反审核 |
| `review_by` | string | 否 | 审核人 |
| `reviewed_at` | datetime | 否 | 审核时间 |
| `review_reason` | string | 否 | 驳回原因 |

### 4.3 ContractGroup

| 字段 | 类型 | 必填 | 规则 |
|---|---|---|---|
| `contract_group_id` | string | 是 | 合同组主键 |
| `group_code` | string | 是 | 唯一，格式 `GRP-[A-Z0-9]{4,12}-[0-9]{6}` |
| `revenue_mode` | enum | 是 | `lease` 承租模式，`agency` 代理模式，同组不混用 |
| `operator_party_id` | string | 是 | 运营方主体 |
| `owner_party_id` | string | 是 | 产权方主体 |
| `asset_ids` | string[] | 是 | 关联合同组资产 |
| `derived_status` | enum | 否 | 筹备中、生效中、已结束，派生只读 |
| `effective_from` | date | 是 | 生效开始日期 |
| `effective_to` | date | 否 | 生效结束日期，可由组内合同派生 |
| `upstream_contract_ids` | string[] | 否 | 上游合同引用，派生 |
| `downstream_contract_ids` | string[] | 否 | 下游合同引用，派生 |
| `settlement_rule` | json | 是 | 最小键为 `version`、`cycle`、`settlement_mode`、`amount_rule`、`payment_rule` |
| `revenue_attribution_rule` | json | 否 | 收入归集口径配置 |
| `revenue_share_rule` | json | 否 | 分润规则配置，MVP 只结构化留存 |
| `risk_tags` | string[] | 否 | 风险标签 |

### 4.4 Contract

| 字段 | 类型 | 必填 | 规则 |
|---|---|---|---|
| `contract_id` | string | 是 | 合同主键 |
| `contract_group_id` | string | 是 | 所属合同组 |
| `contract_direction` | enum | 是 | 出租、承租 |
| `group_relation_type` | enum | 是 | 上游、下游、委托、直租 |
| `lessor_party_id` | string | 是 | 出租方或委托方主体 |
| `lessee_party_id` | string | 是 | 承租方或受托方主体 |
| `asset_ids` | string[] | 否 | 关联资产，为所属合同组资产子集 |
| `sign_date` | date | 否 | 签订日期，进入待审或生效前必填 |
| `effective_from` | date | 是 | 生效开始日期 |
| `effective_to` | date | 否 | 生效结束日期 |
| `currency_code` | enum | 是 | MVP 固定 `CNY` |
| `tax_rate` | decimal | 否 | 范围 `[0, 1]` |
| `is_tax_included` | boolean | 是 | 是否含税，默认 true |
| `status` | enum | 是 | 草稿、待审、生效、已到期、已终止 |
| `review_status` | enum | 是 | 草稿、待审、已审、反审核 |
| `review_by` | string | 否 | 审核人 |
| `reviewed_at` | datetime | 否 | 审核时间 |
| `review_reason` | string | 否 | 反审核原因 |
| `data_status` | enum | 是 | 正常、已删除 |
| `contract_notes` | text | 否 | 合同备注 |

### 4.5 LeaseContractDetail

| 字段 | 类型 | 必填 | 规则 |
|---|---|---|---|
| `lease_detail_id` | string | 是 | 明细主键 |
| `contract_id` | string | 是 | 合同主键 |
| `total_deposit` | decimal | 否 | 总押金金额，>= 0 |
| `rent_amount` | decimal | 是 | 合同级租金汇总金额，>= 0 |
| `rent_amount_excl_tax` | decimal | 否 | 不含税金额，派生 |
| `monthly_rent_base` | decimal | 否 | 基础月租金 |
| `payment_cycle` | enum | 否 | 月付、季付、半年付、年付 |
| `payment_terms` | text | 否 | 支付条款 |
| `tenant_name` | string | 否 | 承租方名称冗余展示 |
| `tenant_contact` | string | 否 | 承租方联系人 |
| `tenant_phone` | string | 否 | 承租方联系电话 |
| `tenant_address` | string | 否 | 承租方地址 |
| `tenant_usage` | string | 否 | 用途说明 |
| `owner_name` | string | 否 | 出租方名称冗余展示 |
| `owner_contact` | string | 否 | 出租方联系人 |
| `owner_phone` | string | 否 | 出租方联系电话 |

### 4.6 ContractRentTerm

| 字段 | 类型 | 必填 | 规则 |
|---|---|---|---|
| `rent_term_id` | string | 是 | 租金条款主键 |
| `contract_id` | string | 是 | 合同主键 |
| `sort_order` | int | 是 | 条款排序，从 1 开始，同一合同内唯一 |
| `start_date` | date | 是 | 本阶段开始日 |
| `end_date` | date | 是 | 本阶段结束日，须晚于开始日 |
| `monthly_rent` | decimal | 是 | 本阶段月租金，>= 0 |
| `management_fee` | decimal | 否 | 管理费，>= 0，默认 0 |
| `other_fees` | decimal | 否 | 其他费用，>= 0，默认 0 |
| `total_monthly_amount` | decimal | 否 | 月合计金额，派生 |
| `notes` | text | 否 | 阶段备注 |
| `created_at` | datetime | 是 | 创建时间 |
| `updated_at` | datetime | 是 | 更新时间 |

约束：同一合同各阶段日期范围不得重叠；台账按 `sort_order` 升序展开自然月生成。

### 4.7 AgencyAgreementDetail

| 字段 | 类型 | 必填 | 规则 |
|---|---|---|---|
| `agency_detail_id` | string | 是 | 明细主键 |
| `contract_id` | string | 是 | 合同主键 |
| `service_fee_ratio` | decimal | 是 | 服务费比例，例如 0.05 表示 5% |
| `fee_calculation_base` | enum | 是 | `actual_received` 或 `due_amount`，MVP 默认 `actual_received` |
| `agency_scope` | text | 否 | 代理范围描述 |

### 4.8 ContractRelation

| 字段 | 类型 | 必填 | 规则 |
|---|---|---|---|
| `relation_id` | string | 是 | 关系主键 |
| `parent_contract_id` | string | 是 | 上级合同，即上游合同或委托协议 |
| `child_contract_id` | string | 是 | 下级合同，即下游合同或直租合同 |
| `relation_type` | enum | 是 | `upstream_downstream` 或 `agency_direct` |
| `created_at` | datetime | 是 | 创建时间 |

约束：MVP 不提供续签关系；同一 child 在同一关系类型下只能有一个 parent。

### 4.9 CustomerProfile

| 字段 | 类型 | 必填 | 规则 |
|---|---|---|---|
| `customer_party_id` | string | 是 | 客户主体 ID，列表唯一键 |
| `customer_name` | string | 是 | 客户名称 |
| `customer_type` | enum | 是 | 内部、外部 |
| `subject_nature` | enum | 是 | `enterprise` 或 `individual` |
| `binding_type` | enum | 是 | `owner` 或 `manager` |
| `contract_roles` | enum[] | 是 | 合同角色集合 |
| `contact_name` | string | 否 | 联系人 |
| `contact_phone` | string | 否 | 联系电话 |
| `identifier_type` | enum | 条件必填 | 有统一标识时必填 |
| `unified_identifier` | string | 否 | 企业 18 位统一社会信用代码，个人按证件类型校验 |
| `address` | string | 否 | 地址 |
| `status` | enum | 是 | 正常、停用 |
| `historical_contract_count` | number | 否 | 历史签约数，派生 |
| `risk_tags` | string[] | 否 | 风险标签，MVP 仅人工标注 |
| `payment_term_preference` | string | 否 | 账期偏好 |

### 4.10 AnalyticsMetrics

| 字段 | 类型 | 必填 | 规则 |
|---|---|---|---|
| `stat_period` | string | 是 | 统计周期，默认本月 |
| `scope_party_id` | string | 是 | 查询方主体 ID |
| `total_income` | number | 是 | 总收入合计，派生 |
| `self_operated_rent_income` | number | 是 | 自营租金收入，派生 |
| `agency_service_income` | number | 是 | 代理服务费收入，派生 |
| `customer_entity_count` | number | 是 | 客户主体数，按客户主体去重 |
| `customer_contract_count` | number | 是 | 客户合同数，按合同去重 |
| `metrics_version` | string | 是 | 统计口径版本标识 |
| `internal_rent_income` | number | 否 | 内部租赁收入，派生 |
| `terminal_rent_income` | number | 否 | 终端租赁收入，派生 |

### 4.11 ContractLedgerEntry

| 字段 | 类型 | 必填 | 规则 |
|---|---|---|---|
| `entry_id` | string | 是 | 台账主键 |
| `contract_id` | string | 是 | 合同主键 |
| `year_month` | string | 是 | 账期，格式 `YYYY-MM`，同一合同内唯一 |
| `due_date` | date | 是 | 应收或应付日 |
| `amount_due` | decimal | 是 | 应收或应付金额，>= 0 |
| `currency_code` | string | 是 | MVP 固定 `CNY` |
| `is_tax_included` | boolean | 是 | 是否含税，继承合同 |
| `tax_rate` | decimal | 否 | 税率，继承合同 |
| `payment_status` | enum | 是 | `unpaid`、`paid`、`overdue`、`partial`、`voided` |
| `paid_amount` | decimal | 否 | 实收金额，>= 0，默认 0 |
| `notes` | text | 否 | 备注 |
| `created_at` | datetime | 是 | 创建时间 |
| `updated_at` | datetime | 是 | 更新时间 |

约束：`voided` 仅允许由系统流程写入；合同到期或终止后停止生成未来台账，历史台账只读。

### 4.12 ServiceFeeLedger

| 字段 | 类型 | 必填 | 规则 |
|---|---|---|---|
| `service_fee_entry_id` | string | 是 | 服务费台账主键 |
| `contract_group_id` | string | 是 | 合同组主键 |
| `agency_contract_id` | string | 是 | 直租合同主键 |
| `source_ledger_id` | string | 是 | 来源租金台账主键，唯一 |
| `year_month` | string | 是 | 账期，格式 `YYYY-MM` |
| `amount_due` | decimal | 是 | 服务费应收金额，派生 |
| `paid_amount` | decimal | 否 | 服务费实收金额，派生 |
| `payment_status` | enum | 是 | 同步来源台账状态 |
| `currency_code` | string | 是 | 继承来源台账 |
| `service_fee_ratio` | decimal | 是 | 代理服务费比例 |
| `created_at` | datetime | 是 | 创建时间 |
| `updated_at` | datetime | 是 | 更新时间 |

### 4.13 ContractAuditLog

| 字段 | 类型 | 必填 | 规则 |
|---|---|---|---|
| `log_id` | string | 是 | 审计日志主键 |
| `contract_id` | string | 是 | 合同主键 |
| `action` | enum | 是 | `submit_review`、`approve`、`reject`、`expire`、`terminate`、`void`、`start_correction`、`reverse_review` |
| `old_status` | string | 否 | 操作前状态 |
| `new_status` | string | 否 | 操作后状态 |
| `review_status_old` | string | 否 | 操作前审核状态 |
| `review_status_new` | string | 否 | 操作后审核状态 |
| `reason` | string | 条件必填 | 驳回、作废、终止等动作必填 |
| `operator_id` | string | 否 | 操作人 ID |
| `operator_name` | string | 否 | 操作人名称 |
| `related_entry_id` | string | 否 | 关联台账条目 |
| `context` | json | 否 | 审计上下文 |
| `created_at` | datetime | 是 | 操作时间 |

约束：审计日志只允许新增，不允许修改或删除。

### 4.14 Approval

#### ApprovalInstance

| 字段 | 类型 | 必填 | 规则 |
|---|---|---|---|
| `approval_instance_id` | string | 是 | 审批实例主键 |
| `approval_no` | string | 是 | 审批单号，全局唯一 |
| `business_type` | enum | 是 | 第一阶段固定为 `asset` |
| `business_id` | string | 是 | 业务对象主键 |
| `status` | enum | 是 | `pending`、`approved`、`rejected`、`withdrawn` |
| `starter_id` | string | 是 | 发起人用户 ID |
| `assignee_user_id` | string | 是 | 当前处理人用户 ID |
| `current_task_id` | string | 否 | 当前待办快照 ID |
| `started_at` | datetime | 是 | 发起时间 |
| `ended_at` | datetime | 否 | 结束时间 |

#### ApprovalTaskSnapshot

| 字段 | 类型 | 必填 | 规则 |
|---|---|---|---|
| `approval_task_id` | string | 是 | 待办快照主键 |
| `approval_instance_id` | string | 是 | 审批实例主键 |
| `business_type` | enum | 是 | 第一阶段固定为 `asset` |
| `business_id` | string | 是 | 业务对象主键 |
| `task_name` | string | 是 | 第一阶段默认“资产审批” |
| `assignee_user_id` | string | 是 | 处理人用户 ID |
| `status` | enum | 是 | `pending`、`completed`、`cancelled` |
| `created_at` | datetime | 是 | 创建时间 |
| `completed_at` | datetime | 否 | 完成时间 |

#### ApprovalActionLog

| 字段 | 类型 | 必填 | 规则 |
|---|---|---|---|
| `approval_action_log_id` | string | 是 | 动作日志主键 |
| `approval_instance_id` | string | 是 | 审批实例主键 |
| `approval_task_id` | string | 否 | 待办快照主键 |
| `action` | enum | 是 | `start`、`approve`、`reject`、`withdraw` |
| `operator_id` | string | 是 | 操作人用户 ID |
| `comment` | string | 否 | 审批意见或撤回原因 |
| `context` | json | 否 | 附加上下文 |
| `created_at` | datetime | 是 | 创建时间 |

### 4.15 Party

| 字段 | 类型 | 必填 | 规则 |
|---|---|---|---|
| `id` | string | 是 | 主体主键 |
| `party_type` | enum | 是 | `organization`、`legal_entity` |
| `name` | string | 是 | 主体名称 |
| `code` | string | 是 | 主体编码，同类型内唯一 |
| `external_ref` | string | 否 | 外部系统引用 |
| `status` | enum | 是 | `active`、`inactive` |
| `review_status` | enum | 是 | `draft`、`pending`、`approved`、`reversed` |
| `review_by` | string | 否 | 审核人 |
| `reviewed_at` | datetime | 否 | 审核时间 |
| `review_reason` | string | 否 | 审核原因 |
| `metadata_json` | json | 否 | 扩展信息 |

## 5. 状态机

### 5.1 ContractGroup 派生状态

| 派生状态 | 判定规则 |
|---|---|
| 筹备中 | 组内无生效合同 |
| 生效中 | 组内存在至少一份生效合同 |
| 已结束 | 组内全部合同已到期或已终止，且至少有一份合同 |

### 5.2 Contract 生命周期

| 当前状态 | 动作 | 目标状态 | 约束 |
|---|---|---|---|
| 草稿 | 提审 | 待审 | 签订日期必填，关联主体必须已审核 |
| 待审 | 审核通过 | 生效 | 写入审计日志并生成台账 |
| 待审 | 驳回 | 草稿 | 驳回原因必填 |
| 生效 | 自然到期 | 已到期 | 停止生成未来台账 |
| 生效 | 提前终止 | 已终止 | 终止原因必填 |
| 生效 | 纠错 | 新草稿 + 原合同反审核 | 原合同相关台账作废或冲销 |
| 生效 | 作废 | 草稿作废标记 | 无台账或台账已全部作废 |

### 5.3 审核状态

| 对象 | 状态 |
|---|---|
| Asset | `draft`、`pending`、`approved`、`reversed` |
| Project | `draft`、`pending`、`approved`、`rejected` |
| Party | `draft`、`pending`、`approved`、`reversed` |
| Contract | 草稿、待审、已审、反审核 |

### 5.4 Approval 状态

| 对象 | 状态 |
|---|---|
| ApprovalInstance | `pending`、`approved`、`rejected`、`withdrawn` |
| ApprovalTaskSnapshot | `pending`、`completed`、`cancelled` |
| ApprovalActionLog.action | `start`、`approve`、`reject`、`withdraw` |

## 6. 统计口径

| 指标 | 公式或规则 |
|---|---|
| 台账自动生成覆盖率 | 系统自动生成成功条目数 / 应生成条目总数 * 100% |
| 台账覆盖率分母 | 生命周期为生效、已到期、已终止且审核通过的合同 |
| 租金收缴率 | 当月实收金额 / 当月应收金额 * 100% |
| 租金收缴率分母 | 当月非作废租金台账 `amount_due` 之和，不含服务费台账 |
| 租金收缴率分子 | 当月非作废租金台账 `paid_amount` 之和 |
| 总收入 | 自营租金收入 + 代理服务费收入 |
| 自营租金收入 | 承租模式下游租金收入 |
| 代理服务费收入 | 代理模式服务费收入 |
| 客户主体数 | 按客户主体 ID 去重 |
| 客户合同数 | 按合同 ID 去重 |
| 多资产合同金额 | 合同级口径，不按资产分摊；汇总时按合同去重 |

## 7. Out of Scope 对象

| 对象 | 说明 |
|---|---|
| PropertyCertificate | 产权证管理不纳入 MVP 需求基线 |
| Ownership | 权属方管理不纳入 MVP 需求基线 |
