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
| 关键记录删除 | 合同组、合同、台账等关键记录禁止物理删除，只允许逻辑删除、作废或重建；MVP 不提供红字冲销机制 |
| 派生字段 | 出租率、汇总金额、计数等派生字段不允许人工直接写入 |
| 编码规则 | 三类业务编码的「段」**统一由相关主体的 `party_code` 经共享 `_build_*_code_segment` 派生**（ADR-0018）：`asset_code` 用 owner、`project_code` 与 `group_code` 用 operator 的 `party_code` 段，生成后冻结只读、主体变更不重编号。**实施状态**：`group_code` 已实现；`asset_code` 已由创建/导入路径自动生成并经迁移回填收紧为必填；`project_code` 已改为按运营方 `party_code` 段 + 年月 + 4 位序号生成。|
| 编码格式 | 段来源统一、字面格式按键角色分两族（不强求字面统一）：运营方键编码带月——`project_code`=`PRJ-{operator_seg}-{YYYYMM}-{SEQ4}`、`group_code`=`GRP-{operator_seg}-{YYYYMM}-{SEQ4}`（序号按运营方+月计）；owner 键编码不带月——`asset_code`=`AST-{owner_seg}-{NNNNNN}`（6 位序、按段单调，对齐 §3 line 53）|
| 项目主轴 | 项目是普通运营用户的默认主工作对象，但资产、合同与协议、经营台账、主体客户、经营分析保留同级直接入口 |
| 合同与协议展示层 | 用户侧展示“合同与协议”，不展示“合同关系”作为页面对象名；内部可由 `ContractGroup` / `ContractRelationProjection` 承载聚合与投影 |
| 资产项目归属 | 资产通过有效期关系归属项目，同一资产同一时点只能有一个当前有效项目 |
| 并发控制 | MVP 乐观锁只在 `Asset` 启用；台账等批量写路径依靠幂等约束，`ContractGroup` / `Contract` 不保留未接入 ORM `version_id_col` 的误导性 `version` 列 |
| 字段来源 | 解析或编辑写入目标对象字段时记 `field_sources` 快照，取值 `manual` / `ocr_prefill_confirmed` / `ocr_prefill_corrected`（纯手工录入与「解析未识别后手工补齐」统一为 `manual`，不拆 `manual_after_ocr_miss` 等子类型）；解析确认提交时每个写入字段必须带来源、缺失即阻断保存，普通非解析编辑缺失可由服务端默认补 `manual`；字段来源仅供编辑或补录来源上下文按需查看，业务详情主视图不默认展示 |
| 扫描件解析确认 | 解析会话（`ScanExtractionSession`）仅当前补录过程的临时工作区，确认 / 取消 / 失败 / 放弃后不留档、不存草稿、不可稍后继续；OCR/AI 候选必须人工逐项确认或修正后才写入，低置信字段必须逐项处理（确认候选值 / 修正为手工值 / 非必填字段显式留空），未处理不得提交确认；候选不因高置信自动绑定 Party·Asset、不自动覆盖已保存字段（冲突默认保留旧值、仅作差异提示）；解析失败 / 超时 / 低置信不阻断完全手工补录；目标对象不保存解析工具、模型、供应商、置信度、确认时间、页码、文本片段或截图区域等解析元信息 |
| 主体范围解析 | 业务查询、ABAC、资源上下文、搜索、通知和分析只消费统一 `EffectivePartyScope`；显式用户绑定完整优先于 Organization 默认范围，范围缺失或无效时失败关闭，不按 Organization 与 Party 的名称、编码或外部引用猜测映射 |

## 3. 核心对象

| 对象 | 定位 |
|---|---|
| Party | 统一主体主档，承载产权方、运营方、客户等主体身份 |
| Organization | 内部公司、部门和项目组层级；与 Party 正交，可直接代表一个法人 Party 或继承上级默认范围 |
| User | 系统账号；以不可变账号类型区分 human、service、system，并由 human 的唯一 Organization 归属承接默认主体范围 |
| UserPartyBinding | 用户跨 Party 的显式 owner/manager 范围；存在当前有效记录时完整取代组织默认范围 |
| UserPartyScopeCommit | 单用户显式范围敏感变更的持久化幂等回执；保存原因、规范化提议、前后范围与提交结果 |
| PartyLifecycleCommit | 已审核 Party 停用/重新启用的持久化幂等回执；保存原因、前后状态、影响快照与首次提交响应 |
| EffectivePartyScope | 唯一范围解析器产生的运行时投影，不持久化 |
| Asset | 资产核心主实体 |
| Project | 资产运营管理主业务单元 |
| ContractGroup | 合同与协议经营事项的内部技术聚合根 |
| ContractRelationProjection | 合同与协议用户侧摘要投影，由 `ContractGroup` 派生 |
| Contract | 合同基表，承载所有合同公共字段 |
| LeaseContractDetail | 租赁类合同明细 |
| AgencyAgreementDetail | 代理协议明细 |
| ContractRentTerm | 分阶段租金条款 |
| ContractLedgerEntry | 租金台账条目 |
| ServiceFeeLedger | 代理服务费台账 |
| OperationalPaymentFlow | 轻量收付流水，承载租金收款、服务费收款和上游成本付款事件 |
| PaymentAllocation | 收付流水到账期条目的人工分摊 |
| ContractAuditLog | 合同操作审计日志 |
| CustomerProfile | 客户视图档案，由 Party 和合同历史投影形成 |
| PartyBusinessRoleSlice | 当前有效经营关系下的 Party 业务角色实时投影，不单独持久化 |
| PropertyCertificate | 资产产权证照记录，作为资产详情内能力维护 |
| CertificatePartyRelation | 产权证与 Party 权利人的关系 |
| ScanExtractionSession | 合同或产权证扫描件解析辅助补录的临时会话 |
| Attachment | 资产、合同、产权证和收付流水凭证的通用附件元数据 |
| Notification | 站内业务提醒与系统通知（提醒非工单，只有已读 / 未读） |

## 4. 字段契约

### 4.1 Asset

| 字段 | 类型 | 必填 | 规则 |
|---|---|---|---|
| `asset_id` | string | 是 | 资产主键 |
| `asset_code` | string | 是 | 全局唯一，格式 `AST-[A-Z0-9]{4,12}-[0-9]{6}` |
| `asset_name` | string | 是 | 资产名称 |
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
| `manager_party_id` | string | 否 | 运营管理主体，**派生**：= 当前有效 `project_id` 所属项目的运营方；资产未归入项目时为空，对运营方绑定用户不可见。不作为独立可填字段，运营方权威轴唯一在 Project（见 ADR-0010） |
| `data_status` | enum | 是 | 正常、已删除 |
| `review_status` | enum | 是 | `draft`、`pending`、`approved`、`reversed`；两步生命周期为制单人提交 `draft → pending`、确认 `pending → approved`；确认仅按复核权限门控，不限制审核人 ≠ 提交人，并支持批量提交与批量确认 |
| `review_by` | string | 否 | 确认人；不要求与提交人不同 |
| `reviewed_at` | datetime | 否 | 审核时间 |
| `review_reason` | string | 否 | 审核原因，反审核时必填 |

### 4.2 Project

| 字段 | 类型 | 必填 | 规则 |
|---|---|---|---|
| `project_id` | string | 是 | 项目主键 |
| `project_code` | string | 是 | 唯一，格式 `PRJ-[A-Z0-9]{4,12}-[0-9]{6}` |
| `project_name` | string | 是 | 项目名称 |
| `project_type` | enum | 否 | 园区、楼宇、片区、物业组合、其他 |
| `manager_party_id` | string | 是 | 项目运营管理方 |
| `start_date` | date | 否 | 项目经营开始日期 |
| `end_date` | date | 否 | 项目经营结束日期，须晚于开始日期 |
| `asset_ids_current` | string[] | 否 | 当前有效资产，派生 |
| `asset_count_current` | number | 否 | 当前有效资产数，派生 |
| `contract_relation_count` | number | 否 | 当前合同与协议经营事项数量，派生 |
| `revenue_mode_summary` | json | 否 | 承租转租和代理运营分布，派生 |
| `status` | enum | 是 | `planning`、`active`、`paused`、`completed`、`terminated` |
| `data_status` | enum | 是 | 正常、已删除 |

> 项目**无 review 生命周期**：原 `review_status`/`review_by`/`reviewed_at`/`review_reason` 是零消费孤儿列（无流转、无门禁、无筛选、API 不暴露），MVP 删除——项目只是资产的业务管理归集桶，无下游要求「项目已审」（见 ADR-0014）。Asset 两步确认、Party 两步审核各自保留（均承重）。

### 4.3 ContractGroup

| 字段 | 类型 | 必填 | 规则 |
|---|---|---|---|
| `contract_group_id` | string | 是 | 合同组主键 |
| `project_id` | string | 条件必填 | 所属项目；目标态一条合同/协议经营事项必须归属一个项目，**单项目硬不变量**：覆盖 `asset_ids` 须同属该项目，承租转租/代理运营一律如此（代理委托协议跨项目靠共享盖章扫描件、各项目各建一条合同/协议记录，不让合同组跨项目，见 ADR-0012）。Phase 1a migration 初始允许为空，存量回填完成后再评估是否改为数据库 NOT NULL |
| `group_code` | string | 是 | 唯一，格式 `GRP-[A-Z0-9]{4,12}-[0-9]{6}` |
| `revenue_mode` | enum | 是 | `lease` 承租转租，`agency` 代理运营，同一合同/协议经营事项不混用 |
| `operator_party_id` | string | 是 | 运营方主体 |
| `owner_party_id` | string | 是 | 产权方主体 |
| `asset_ids` | string[] | 是 | 合同/协议经营事项覆盖资产 |
| `derived_status` | enum | 否 | 筹备中、生效中、已结束，派生只读 |
| `effective_from` | date | 是 | 生效开始日期 |
| `effective_to` | date | 否 | 生效结束日期，可由组内合同派生 |
| `upstream_contract_ids` | string[] | 否 | 上游合同引用，派生 |
| `downstream_contract_ids` | string[] | 否 | 下游合同引用，派生 |
| `settlement_rule` | json | 否 | 创建时选填、可缓填；缺失不阻断合同/协议保存，也不参与经营台账生成。结构键为 `version`、`cycle`、`settlement_mode`、`amount_rule`、`payment_rule`，用于留存运营约定；经营台账仍以组内合同条款明细为数据源。详见 `docs/architecture/ADR-0004-settlement-rule-optional-at-creation.md` |
| `revenue_attribution_rule` | json | 否 | 收入归集口径配置 |
| `revenue_share_rule` | json | 否 | 分润规则配置，MVP 只结构化留存 |
| `risk_tags` | string[] | 否 | 风险标签；项目风险摘要会叠加人工标签、30 天内合同/协议到期提醒、终端租户租金逾期、产权证数据质量、空置风险和合同更正后陈旧已收付台账风险（`ledger_stale_after_correction`，见 ADR-0008）；MVP 不再生成主合同覆盖类风险 |

### 4.4 ContractRelationProjection

该对象是项目详情和搜索结果中的合同与协议用户侧摘要投影，不单独持久化；对象名保留为内部技术名称，界面文案不得展示“合同关系”。

| 字段 | 类型 | 必填 | 规则 |
|---|---|---|---|
| `contract_relation_id` | string | 是 | 对应 `contract_group_id` |
| `project_id` | string | 是 | 所属项目 |
| `project_name` | string | 否 | 所属项目名称，列表和跨项目查询展示使用 |
| `display_name` | string | 是 | 面向用户展示的合同与协议摘要名称 |
| `revenue_mode` | enum | 是 | `lease` 承租转租，`agency` 代理运营 |
| `relation_kind` | enum | 是 | 由 `revenue_mode` 派生：`lease` -> `lease_sublease`，`agency` -> `agency_operation` |
| `owner_party_id` | string | 是 | 产权方主体 |
| `operator_party_id` | string | 是 | 运营方主体 |
| `asset_ids` | string[] | 是 | 覆盖资产范围 |
| `primary_contract_ids` | string[] | 否 | 组内 `group_relation_type` 为上游/委托的合同，按方向派生；不再表达合同对合同配对 |
| `terminal_contract_ids` | string[] | 否 | 组内 `group_relation_type` 为下游/直租的合同，按方向派生；不再做主合同覆盖判定 |
| `contract_role_counts` | map | 否 | 按 `group_relation_type` 聚合的合同数量，用于合同中心展示业务角色 |
| `derived_status` | enum | 否 | 筹备中、生效中、已结束，派生只读 |
| `ledger_summary` | json | 否 | 经营台账摘要，派生；终端租户收缴包含承租转租下游租金和代理直租租金；运营方收入包含承租转租租金收入和代理服务费收入；运营方成本包含承租上游租金成本；服务费结算单独展示应收、实收、未收 |
| `risk_tags` | string[] | 否 | 风险标签 |

### 4.5 ProjectAnalytics

该对象是项目详情“项目分析”区和项目分析 API 的派生摘要，不单独持久化。MVP 口径复用项目有效资产、合同与协议、经营台账、租户客户和风险摘要，不引入新的分析事实表。

| 字段 | 类型 | 必填 | 规则 |
|---|---|---|---|
| `asset_summary` | json | 是 | 当前有效资产汇总，口径同 `GET /api/v1/projects/{project_id}/assets` |
| `contract_relation_count` | number | 是 | 项目合同与协议经营事项总数 |
| `tenant_count` | number | 是 | 项目终端客户主体数，按 Party 去重 |
| `customer_contract_count` | number | 是 | 项目终端客户合同数 |
| `risk_count` | number | 是 | 项目风险项总数 |
| `high_risk_count` | number | 是 | `critical`、`error`、`high` 风险项数量 |
| `terminal_rent_receivable` | decimal | 是 | 终端租户租金应收，承租转租下游租金 + 代理直租租金 |
| `terminal_rent_received` | decimal | 是 | 终端租户租金实收，承租转租下游租金实收 + 代理直租租金实收 |
| `terminal_rent_unreceived` | decimal | 是 | 终端租户租金未收 |
| `terminal_rent_overdue` | decimal | 是 | 终端租户租金逾期，唯一逾期口径 |
| `operator_income_receivable` | decimal | 是 | 运营方收入应收，承租转租下游租金收入 + 代理服务费收入，不含代理直租租金 |
| `operator_income_received` | decimal | 是 | 运营方收入实收，承租转租下游租金实收 + 代理服务费实收 |
| `operator_cost_payable` | decimal | 是 | 运营方成本应付，承租转租上游租金成本 |
| `operator_cost_paid` | decimal | 是 | 运营方成本实付，承租转租上游租金实付 |
| `operator_cost_unpaid` | decimal | 是 | 运营方成本未付，不产生逾期 |
| `service_fee_receivable` | decimal | 是 | 代理服务费应收 |
| `service_fee_received` | decimal | 是 | 代理服务费实收 |
| `net_operating_inflow` | decimal | 是 | 经营净流入（已登记实收实付）= 运营方收入实收 - 运营方成本实付，金额看实收/实付、时间按账期归属 |
| `book_operating_spread` | decimal | 是 | 账面经营差额（应收应付）= 运营方收入应收 - 运营方成本应付 |
| `mode_summaries` | array | 是 | 按 `lease_sublease` / `agency_operation` 分区的指标；每个分区包含合同/协议数、资产数、终端租户收缴、运营方收入、运营方成本、服务费和风险数 |
| `monthly_trends` | array | 是 | 按租金账期 `year_month` 聚合的项目经营趋势；流水发生日期仅用于流水查询、导出和审计，不作为默认经营分析归属月 |

### 4.5.1 ProjectRisk

该对象是项目风险摘要 API 的派生项，不单独持久化。风险项必须能够回溯到合同/协议经营事项或资产，避免只给出无来源的总体提示。

| 字段 | 类型 | 必填 | 规则 |
|---|---|---|---|
| `risk_id` | string | 是 | 稳定风险标识，按来源对象、风险类型和消息派生 |
| `risk_type` | enum | 是 | `manual_tag`、`property_certificate_data_quality`、`contract_expiring`、`payment_overdue`、`vacancy`、`ledger_stale_after_correction`（已收/部分已收台账与当前合同条款不一致，合同更正重算时派生，人工对账后消除，见 ADR-0008）、`service_fee_source_mismatch`（已生成服务费台账与当前来源租金集合、计算基数、比例、金额或归属不一致，或冻结来源租金条目已与当前合同条款不一致，人工处理后消除）；MVP 已移除 `missing_primary_contract` / `coverage_conflict` 主合同覆盖类风险 |
| `severity` | enum | 是 | `info`、`warning`、`high`、`critical`、`error` |
| `message` | string | 是 | 面向业务用户的风险说明 |
| `contract_relation_id` | string/null | 否 | 合同/协议经营事项风险必须填写；产权证数据质量风险和资产空置风险为空 |
| `display_name` | string/null | 否 | 合同/协议经营事项名称或资产名称 |

空置风险口径：项目当前有效资产的 `rentable_area - rented_area > 0` 时生成 `vacancy` 风险，消息展示资产名称和空置面积；删除、异常或已失效项目资产关系不参与计算。

产权证数据质量风险口径：项目当前有效资产关联的产权证存在证照信息不完整，或产权证权利人与关联资产当前主产权主体不一致时，可生成 `property_certificate_data_quality` 风险，严重级别固定为 `warning`。MVP 已删除 `is_verified` 核验状态与“未核验”风险；风险只能通过补齐证照信息或修正权利人/资产关联自然消除，不生成待办、任务或审批。

### 4.6 GlobalAnalytics

该对象是全局“经营分析”入口的派生摘要，不单独持久化。MVP 复用 `GET /api/v1/analytics/comprehensive` 结果，在全局层按项目和经营模式分区，避免把承租转租和代理运营口径混合成单一指标。

| 字段 | 类型 | 必填 | 规则 |
|---|---|---|---|
| `total_income` | decimal | 是 | 运营方收入，承租转租下游租金收入 + 代理服务费收入；不含代理直租租金 |
| `self_operated_rent_income` | decimal | 是 | 承租转租下游租金收入 |
| `agency_service_income` | decimal | 是 | 代理运营服务费收入；代理直租租金不计入运营方收入 |
| `terminal_rent_receivable` | decimal | 是 | 终端租户租金应收，承租转租下游租金 + 代理直租租金 |
| `terminal_rent_received` | decimal | 是 | 终端租户租金实收 |
| `terminal_rent_overdue` | decimal | 是 | 终端租户租金逾期 |
| `operator_cost_paid` | decimal | 是 | 运营方成本实付，承租转租上游租金成本 |
| `net_operating_inflow` | decimal | 是 | 经营净流入（已登记实收实付） |
| `collection_rate` | number/null | 是 | 终端租户租金收缴率，分母为 0 时返回 null，按租金账期归属 |
| `customer_entity_count` | number | 是 | 终端客户主体数，仅统计下游转租 / 代理直租 lessee，按 Party 去重；不包含上游产权方或委托对手方 |
| `customer_contract_count` | number | 是 | 终端客户合同数，仅统计下游转租 / 代理直租合同，按合同 ID 去重 |
| `customer_entity_breakdown` | map | 是 | 终端客户主体拆分，仅包含 `downstream_sublease`、`direct_lease` |
| `customer_contract_breakdown` | map | 是 | 终端客户合同拆分，仅包含 `downstream_sublease`、`direct_lease` |
| `counterparty_entity_breakdown` | map | 是 | 非客户对手方主体拆分，包含 `upstream_lease`、`entrusted_operation`，不得并入客户口径 |
| `counterparty_contract_breakdown` | map | 是 | 非客户对手方合同拆分，包含 `upstream_lease`、`entrusted_operation`，不得并入客户口径 |
| `project_breakdown` | array | 是 | 按项目分区；每项包含项目 ID、项目名称、合同/协议数、承租转租数、代理运营数、终端租户收缴、运营方收入、运营方成本、经营结果、客户主体数和客户合同数 |
| `mode_breakdown` | array | 是 | 按 `lease_sublease` / `agency_operation` 分区；每项包含合同/协议数、运营方收入、终端租户收缴、服务费、客户主体数和客户合同数 |
| `metrics_version` | string | 是 | 经营分析口径版本 |

### 4.7 Contract

| 字段 | 类型 | 必填 | 规则 |
|---|---|---|---|
| `contract_id` | string | 是 | 合同主键 |
| `contract_group_id` | string | 是 | 所属合同组 |
| `project_id` | string | 是 | 合同所属项目快照，创建时取所属 `ContractGroup.project_id`；用于 `UNIQUE(contract_number, project_id)` 复合唯一，允许同一份委托协议在不同项目下保留同号合同记录；DB 以 `data_status <> '正常' OR project_id IS NOT NULL` 持续约束正常合同不得缺项目 |
| `contract_direction` | enum | 是 | 出租、承租 |
| `group_relation_type` | enum | 是 | 上游、下游、委托、直租 |
| `lessor_party_id` | string | 是 | 出租方或委托方主体 |
| `lessee_party_id` | string | 是 | 承租方或受托方主体 |
| `lessor_name_snapshot` | string | 否 | 出租/委托方**签署时名称快照**，定稿（补录即生效 / `finalize_correction`）时从当时主档名写入，之后不随主档改名回写（§6.1，见 ADR-0020） |
| `lessee_name_snapshot` | string | 否 | 承租/受托方**签署时名称快照**，定稿时写入、不随主档改名回写（§6.1，见 ADR-0020）；`LeaseContractDetail.tenant_name` 退为展示冗余、从此快照同步 |
| `correction_source_contract_id` | string | 否 | 纠错草稿显式来源合同；仅用于纠错溯源，不表达上下游、续签或主从配对 |
| `asset_ids` | string[] | 否 | 关联资产，须为所属合同/协议经营事项覆盖资产**子集**（`⊆ ContractGroup.asset_ids`，service 层校验）；**留空表示「覆盖本经营事项全部资产（整租）」**，台账固化时回退到组 `asset_ids`（见 ADR-0011/0012） |
| `sign_date` | date | 否 | 签订日期，进入生效前必填（补录即生效，无待审态，见 ADR-0013） |
| `effective_from` | date | 是 | 生效开始日期 |
| `effective_to` | date | 否 | 生效结束日期 |
| `currency_code` | enum | 是 | MVP 固定 `CNY` |
| `tax_rate` | decimal | 否 | 范围 `[0, 1]` |
| `is_tax_included` | boolean | 是 | 是否含税，默认 true |
| `status` | enum | 是 | 最小生命周期；**存储轴只有 `{草稿（纠错草稿/录入中）, 生效, 已终止}`**，`已到期` 是 `生效` + `effective_to < today` 的**派生展示状态、非落库写入值**（同逾期口径，无到期 job 写标记，台账生成器直接比对 `effective_to`，见 ADR-0007/0013）；补录即落 `生效`，无「待审」步骤，不做路由审批。MVP 已删 `待审` 态、`review_status`/`review_by`/`reviewed_at`/`review_reason` 审批列 |
| `data_status` | enum | 是 | 正常、已删除 |
| `contract_notes` | text | 否 | 合同备注 |

约束：合同通过 `project_id` 固化所属 `ContractGroup.project_id`，用于按项目合同号复合唯一；正常合同缺 `project_id` 在迁移时 fail-loud，迁移后由 DB check constraint 持续拦截；`contract_group_id` 仍为单值，不挂多组。合同**不做 BPM 路由审批流**（提审/审核/联审/反审核/制审分离整体降级 vNext，同 ADR-0002 资产口径）；MVP 保留最小生命周期：补录即生效、按 `effective_to` 派生 `已到期` + 显式 `已终止`（台账据此停生成未来条目、生效中合同删除保护），`草稿 → 定稿` 承载 REQ-RNT-005 更正，纠错草稿发起门禁绑生命周期状态（只能从生效合同发起），不再依赖已删的 `review_status`（见 ADR-0013）。一份委托协议覆盖多个项目时，其盖章扫描件可被多个项目下的代运营受托合同记录共享引用（扫描件只传一份、多条 `Contract` 引用），跨项目落在扫描件层，不提升为跨项目经营事项或台账（见 ADR-0012）。

### 4.7.1 ContractScanDocument

| 字段 | 类型 | 必填 | 规则 |
|---|---|---|---|
| `document_id` | string | 是 | 扫描件文档主键 |
| `storage_key` | string | 是 | 文件存储键，唯一；同一物理盖章扫描件只保存一份文档行 |
| `original_filename` | string | 是 | 原始文件名 |
| `content_type` | string | 否 | MIME 类型 |
| `file_size` | int | 否 | 文件大小，>= 0 |
| `checksum_sha256` | string | 否 | 文件内容校验和 |
| `contract_ids` | string[] | 否 | 通过 `contract_scan_document_links` 关联的合同记录 |

约束：扫描件文档可被多条同委托协议 `Contract` 共享引用；`PUT /contracts/{contract_id}/attachments` 只同步替换同 `contract_number`、同委托方、同受托方、正常合同组、且位于代运营合同/协议经营事项中的受托合同扫描件引用；API 层必须对全部受影响合同逐条校验 `contract:update` 权限。复用既有 `storage_key` 时，该文档已链接的全部合同必须落在本次受影响合同集合内；若存在范围外链接，拒绝替换，避免未授权合同的可见扫描件元数据被改写。删除时每个受影响合同必须至少保留 1 份盖章扫描件。

### 4.8 LeaseContractDetail

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

### 4.9 ContractRentTerm

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

### 4.10 AgencyAgreementDetail

| 字段 | 类型 | 必填 | 规则 |
|---|---|---|---|
| `agency_detail_id` | string | 是 | 明细主键 |
| `contract_id` | string | 是 | 合同主键 |
| `service_fee_ratio` | decimal | 是 | 服务费比例，例如 0.05 表示 5% |
| `fee_calculation_base` | enum | 是 | `actual_received` 或 `due_amount`，MVP 默认 `actual_received` |
| `agency_scope` | text | 否 | 代理范围描述 |

### 4.11 ContractRelation（MVP 已删除）

合同上下游逐对配对表已删除。上下游、委托、直租只由每份合同的 `group_relation_type` 表达方向；收入、成本、服务费全部按方向计算，盈亏沿“合同 -> 资产 -> 项目”归属链汇总，不依赖合同对合同配对。`ContractRelationType.RENEWAL` 随表一并删除，对齐“MVP 不提供续签”。纠错草稿来源改用 `Contract.correction_source_contract_id` 显式字段，仅用于纠错溯源，不表达上下游、续签或主从配对。

### 4.12 CustomerProfile

| 字段 | 类型 | 必填 | 规则 |
|---|---|---|---|
| `customer_party_id` | string | 是 | 客户主体 ID，列表唯一键 |
| `customer_name` | string | 是 | 客户名称 |
| `customer_type` | enum | 是 | 内部、外部 |
| `subject_nature` | enum | 是 | `enterprise` 或 `individual` |
| `binding_type` | enum | 是 | `owner`、`manager` 或 `all`；`all` = 该客户经 owner 与 manager 两绑定均可见（多绑定用户 `all` 模式下按主体去重的并集行）。列表唯一键 `customer_party_id`、一客户一行 |
| `contract_roles` | enum[] | 是 | 合同角色集合 |
| `contact_name` | string | 否 | 联系人 |
| `contact_phone` | string | 否 | 联系电话 |
| `identifier_type` | enum | 条件必填 | 与 Party 正式标识类型一致；有 `identifier_display` 时必填 |
| `identifier_display` | string | 否 | Party 正式标识的只读安全投影；法人可返回规范化值，自然人只能返回脱敏值，不返回密文、指纹或明文 |
| `address` | string | 否 | 地址 |
| `status` | enum | 是 | 正常、停用 |
| `historical_contract_count` | number | 否 | 历史签约数，派生：按**有效主体范围并集、合同 ID 去重**计（同一合同在 owner+manager 两视角均可见也只算一次）；属**列表/档案字段**，`all` 模式合法、**不受**「分析必选视图」约束——单视图铁律只约束分析端点客户双指标（`customer_entity_count`/`customer_contract_count`），见 CONTEXT「客户双指标」 |
| `risk_tags` | string[] | 否 | 风险标签，MVP 仅人工标注 |
| `payment_term_preference` | string | 否 | 账期偏好 |

### 4.12.1 PartyBusinessRoleSlice

该对象是主体列表的当前业务角色投影，不是 Party 主档字段，也不替代 CustomerProfile。查询先按既有 Party 数据范围过滤，再按当前有效关系派生角色；不得把 `customer_type`、`UserPartyBinding.relation_type` 或历史合同角色当作业务角色来源。

| 字段 | 类型 | 必填 | 规则 |
|---|---|---|---|
| `party_id` | string | 是 | Party 主键；“全部”列表按该值唯一 |
| `party_name` | string | 是 | 当前 Party 主档名称 |
| `business_roles` | enum[] | 是 | 可并列 `owner`、`operator`、`terminal_tenant`；无角色的 Party 仅在“全部”列表可见 |

派生规则：`owner` 来自当前有效资产的 `owner_party_id`；`operator` 来自当前有效项目的 `manager_party_id`；`terminal_tenant` 来自当前有效下游转租或直租合同的 lessee。有效性只复用资产、项目和合同/协议既有生命周期口径；一个 Party 因多个来源命中同一角色时去重。当前切片不返回仅存在于历史合同中的角色，历史签约由 CustomerProfile 承载。
### 4.13 AnalyticsMetrics

| 字段 | 类型 | 必填 | 规则 |
|---|---|---|---|
| `stat_period` | string | 是 | 统计周期，默认本月 |
| `scope_party_id` | string | 是 | 查询方主体 ID |
| `total_income` | number | 是 | 总收入合计，派生 |
| `self_operated_rent_income` | number | 是 | 承租转租租金收入，派生 |
| `agency_service_income` | number | 是 | 代理服务费收入，派生 |
| `customer_entity_count` | number | 是 | 终端客户主体数，仅统计下游转租 / 代理直租 lessee，按 Party 去重 |
| `customer_contract_count` | number | 是 | 终端客户合同数，仅统计下游转租 / 代理直租合同，按合同去重 |
| `metrics_version` | string | 是 | 统计口径版本标识 |
| `internal_rent_income` | number | 否 | 内部租赁收入，派生 |
| `terminal_rent_income` | number | 否 | 终端租赁收入，派生 |

### 4.14 ContractLedgerEntry

| 字段 | 类型 | 必填 | 规则 |
|---|---|---|---|
| `entry_id` | string | 是 | 台账主键 |
| `contract_id` | string | 是 | 合同主键 |
| `attributed_project_id` | string | 否 | **生成时固化**的所属项目；台账是账本，历史/分析口径读此固化值聚合，不 join 合同组/资产的当前归属，re-org 不回写（见 ADR-0011） |
| `attributed_owner_party_id` | string | 否 | 生成时固化的产权方，同上不随 re-org 改写 |
| `attributed_operator_party_id` | string | 否 | 生成时固化的运营方，同上 |
| `attributed_asset_ids` | string[] | 否 | 生成时固化的对应资产集合，取生成该条目的 `Contract.asset_ids`（留空整租时回退到组 `asset_ids`）；仅表达「这条账当时对应哪些资产」，金额仍合同级、不按资产分摊（§6，见 ADR-0011/0012） |
| `year_month` | string | 是 | 账期，格式 `YYYY-MM`，同一合同内唯一 |
| `due_date` | date | 是 | 应收或应付日 |
| `amount_due` | decimal | 是 | 应收或应付金额，>= 0 |
| `ledger_views` | enum[] | 是 | 经营台账视图归属：`terminal_collection` 终端租户收缴、`operator_income` 运营方收入、`operator_cost` 运营方成本；承租转租下游租金同时进入终端租户收缴与运营方收入，代理直租只进入终端租户收缴，上游承租租金只进入运营方成本 |
| `currency_code` | string | 是 | MVP 固定 `CNY` |
| `is_tax_included` | boolean | 是 | 是否含税，继承合同 |
| `tax_rate` | decimal | 否 | 税率，继承合同 |
| `payment_status` | enum | 是 | `unpaid`/`paid`/`partial` 由收付流水汇总额对 `amount_due` 纯派生，不手登记状态；`voided` 仅系统重算/作废写入；“逾期”另为派生口径、不是登记状态（见 ADR-0007/0019） |
| `paid_amount` | decimal | 否 | 已收/已付汇总金额，>= 0，默认 0；查询时由有效 `PaymentAllocation` 汇总派生，历史存量累计值已通过迁移回填为系统流水和分摊 |
| `follow_up_status` | enum | 否 | 仅终端租户收缴可维护：`pending_follow_up`、`contacted`、`promised_payment`、`disputed`、`offline_received_pending_entry`、`deferred`；不改变逾期金额、收缴率或实收金额 |
| `next_follow_up_date` | date | 否 | 终端租户收缴跟进日期 |
| `follow_up_note` | text | 否 | 终端租户收缴跟进备注 |
| `notes` | text | 否 | 备注 |
| `created_at` | datetime | 是 | 创建时间 |
| `updated_at` | datetime | 是 | 更新时间 |

约束：台账是**账本（历史记录）** 而非实时情况列表——每条是绑定账期的经营事实，实时情况（当前欠款、出租率、当前归属）是另算的派生投影。`voided` 仅允许由系统流程写入；合同到期或终止后停止生成未来台账，历史台账只读。条目在生成时固化归属（`attributed_project_id` / `attributed_owner_party_id` / `attributed_operator_party_id` / `attributed_asset_ids`），项目/产权方维度的历史与分析口径只读固化值聚合，禁止 join 合同组/资产当前归属回算历史（见 ADR-0011）。台账重算只调整未收/未付且无收付流水的条目；已有收付流水条目系统不自动改写或作废，自动跳过；被跳过条目以「重算结果当场列出」+「持久派生风险 `ledger_stale_after_correction`（条目与当前合同/协议条款重算目标不一致时派生，人工对账后消除）」两条机制提醒，不设手工标记位（见 ADR-0008）。逾期只属于终端租户租金收缴，口径为 `due_date` 已过且终端租户租金 `paid_amount < amount_due` 且状态非 `voided`，统计、风险、筛选与通知统一按此派生；运营方成本未付、服务费未收不产生逾期。

### 4.14.1 OperationalPaymentFlow

| 字段 | 类型 | 必填 | 规则 |
|---|---|---|---|
| `flow_id` | string | 是 | 收付流水主键 |
| `flow_type` | enum | 是 | `terminal_rent_receipt`、`service_fee_receipt`、`upstream_cost_payment` |
| `occurred_on` | date | 是 | 实际收款/付款发生日期，用于流水查询、导出和审计，不作为默认经营分析归属月 |
| `amount` | decimal | 是 | 流水金额，> 0 |
| `registered_by` | string | 是 | 登记人；由服务端从认证用户固化，客户端请求不得指定 |
| `counterparty_id` | string | 否 | 对方主体；终端租户、产权方或运营方 |
| `voucher_attachment_ids` | string[] | 否 | 可选凭证附件；不上传不阻断登记 |
| `notes` | text | 否 | 备注 |
| `status` | enum | 是 | `active`、`voided`、`corrected`；客户端不得直接写入，作废/更正只能走显式动作 |
| `corrected_from_flow_id` | string | 否 | 更正产生的新 `active` 流水指向原流水；唯一约束保证一条原流水最多有一个更正后继 |
| `status_changed_by` | string | 条件 | `voided` / `corrected` 必填，由服务端从认证用户固化；`active` 必须为空 |
| `status_changed_at` | datetime | 条件 | `voided` / `corrected` 必填；`active` 必须为空 |
| `status_change_reason` | text | 条件 | `voided` / `corrected` 必填且非空白；`active` 必须为空 |
| `created_at` | datetime | 是 | 创建时间 |
| `updated_at` | datetime | 是 | 更新时间 |

约束：流水是实收/实付事实来源。经营分析默认按 `PaymentAllocation.year_month` / 台账账期归属，流水 `occurred_on` 只用于查看实际发生日期。只有 `active` 流水的分摊参与实收/实付汇总；作废把原流水转为 `voided` 并在同一事务内重算受影响台账，更正把原流水转为 `corrected`、创建唯一的新 `active` 流水及其分摊并完成重算。更正不得改变流水类型，也不得把事实迁移到不同项目、产权方、运营方或币种；新旧分摊目标必须合并后按稳定 ID 顺序一次加锁。重复终态动作与并发第二次更正必须失败，不删除原流水或原分摊。原流水凭证继续归属原流水以保留历史证据，更正请求不得把旧凭证 ID 复制给新流水；新流水凭证在更正成功后单独上传。MVP 不对接银行流水、支付通道或财务总账。

### 4.14.2 PaymentAllocation

| 字段 | 类型 | 必填 | 规则 |
|---|---|---|---|
| `allocation_id` | string | 是 | 分摊主键 |
| `flow_id` | string | 是 | 所属收付流水 |
| `target_type` | enum | 是 | `contract_ledger_entry` 或 `service_fee_ledger` |
| `target_id` | string | 是 | 被分摊账期条目 ID |
| `year_month` | string | 是 | 租金账期 / 服务费归属账期，格式 `YYYY-MM` |
| `amount` | decimal | 是 | 分摊金额，> 0 |
| `created_at` | datetime | 是 | 创建时间 |
| `updated_at` | datetime | 是 | 更新时间 |

约束：一笔流水可人工分摊到多个账期，系统校验同一流水的分摊金额合计等于流水金额；各账期实收/实付由分摊汇总派生。

### 4.15 ServiceFeeLedger

| 字段 | 类型 | 必填 | 规则 |
|---|---|---|---|
| `service_fee_entry_id` | string | 是 | 服务费台账主键 |
| `contract_group_id` | string | 是 | 合同组主键 |
| `agency_contract_id` | string | 是 | 直租合同主键；必须明确关联一份委托协议 |
| `agency_agreement_contract_id` | string | 是 | 委托协议合同主键；服务费比例从该委托协议固化 |
| `source_ledger_ids` | string[] | 是 | 来源代理直租租金台账集合；服务费按租金账期月份汇总生成，不逐笔生成 |
| `year_month` | string | 是 | 租金账期月份，格式 `YYYY-MM`；服务费归属按租金账期，不按实际收款月份 |
| `amount_due` | decimal | 是 | 服务费应收金额，= 代理直租租金实收 × 委托协议服务费比例 |
| `paid_amount` | decimal | 否 | 服务费实收金额，目标态由服务费收款流水分摊汇总生成 |
| `payment_status` | enum | 是 | 由服务费 `paid_amount` 对 `amount_due` 派生；不产生逾期 |
| `currency_code` | string | 是 | 继承来源台账 |
| `service_fee_ratio` | decimal | 是 | 代理服务费比例 |
| `calculation_base_amount` | decimal | 是 | 服务费计算基数，即该租金账期内代理直租租金已登记实收金额 |
| `attributed_project_id` | string | 否 | Inherits frozen project attribution from source rent ledgers for historical service-fee aggregation |
| `attributed_owner_party_id` | string | 否 | Inherits frozen owner-party attribution from source rent ledgers |
| `attributed_operator_party_id` | string | 否 | Inherits frozen operator-party attribution from source rent ledgers |
| `attributed_asset_ids` | string[] | 否 | Inherits frozen asset IDs from source rent ledgers; amounts remain contract-level and are not split by asset |
| `created_at` | datetime | 是 | 创建时间 |
| `updated_at` | datetime | 是 | 更新时间 |

约束：服务费应收只在代理直租租金实际收到后形成，按租金账期月份 / 项目 / 委托协议 / 产权方汇总生成。`ContractGroup` 固定归属单一项目，因此月度唯一键中的 `contract_group_id` 已隐含项目边界，不重复增加 `project_id`。当前业务服务费比例存在历史差异：当前合同 30%，更早合同 20%；台账生成后固化比例、计算基数和来源账期。每条可计算服务费的租金账期必须命中单一委托协议比例；若账期跨比例区间，系统提示拆分账期，不自动按天拆分。已生成服务费应收后的租金实收更正，不得静默覆盖既有服务费应收；来源租金条目被合同更正重算跳过时，既有服务费台账不自动重算或覆盖，必须派生服务费来源不一致风险并交由人工处理；人工校准必须提交原因，只允许把既有条目更新到当前唯一可计算来源，底层租金条目仍陈旧、来源已消失、无法唯一匹配，或校准后应收低于有效服务费收款分摊时失败暴露。尚未生成服务费的账期按修正后的实收进入后续月度生成。服务费实收是产权方支付给运营方的收款事实，通过 `OperationalPaymentFlow(flow_type=service_fee_receipt)` 登记；服务费未收不产生逾期。

Concurrency and scope constraints: replacing allocations locks the payment flow and every old/new target row before recalculating `paid_amount`; reconciling a service-fee source locks the service-fee row before reading active allocations. Service-fee source rent rows are scope-filtered before monthly aggregation; service-fee queries/generation and project summaries/analytics/risks authorize each historical row against its frozen owner/operator attribution, not only the contract group's current parties. If a current monthly bucket and an unmatched existing receivable share a unique source-ledger identity after an owner/agreement key change, generation preserves the existing receivable as a mismatch instead of creating a duplicate; reasoned reconciliation is the only path that may re-key it. When the preserved row is outside the caller's frozen party scope, generation fails loudly without exposing the row and requires unrestricted administrative reconciliation.

### 4.16 ContractAuditLog

| 字段 | 类型 | 必填 | 规则 |
|---|---|---|---|
| `log_id` | string | 是 | 审计日志主键 |
| `contract_id` | string | 是 | 合同主键 |
| `action` | enum | 是 | `terminate`、`void`、`start_correction`、`finalize_correction`（对应最小合同生命周期的**显式操作**；`expire`/已到期是派生状态、非操作，不入审计，同逾期口径；审批流动作 `submit_review`/`approve`/`reject`/`reverse_review` 已随 ADR-0013 删除） |
| `old_status` | string | 否 | 操作前生命周期落库状态（草稿/生效/已终止；已到期为派生展示态，不入审计状态字段） |
| `new_status` | string | 否 | 操作后生命周期状态 |
| `reason` | string | 条件必填 | 作废、终止等动作必填 |
| `operator_id` | string | 否 | 操作人 ID |
| `operator_name` | string | 否 | 操作人名称 |
| `related_entry_id` | string | 否 | 关联台账条目 |
| `context` | json | 否 | 审计上下文 |
| `created_at` | datetime | 是 | 操作时间 |

约束：审计日志只允许新增，不允许修改或删除。`finalize_correction`（纠错草稿定稿）是触发台账重算/作废（ADR-0008）的有财务后果的关键操作，必须留痕（§8）；不记录任何审核状态转移（`ContractReviewStatus` 已随 ADR-0013 整删，合同无审批流）。

### 4.17 Approval（MVP 已删除）

`ApprovalInstance`、`ApprovalTaskSnapshot`、`ApprovalActionLog` 已从 MVP 目标态删除。资产不走路由审批流，仅保留 `Asset.review_status` 两步确认；通用 BPM 审批流引擎属于 Out of Scope。

### 4.18 Party

| 字段 | 类型 | 必填 | 规则 |
|---|---|---|---|
| `id` | string | 是 | 主体主键 |
| `party_type` | enum | 是 | 仅 `legal_entity`、`individual`；内部部门和项目组不是 Party |
| `name` | string | 是 | 主体名称 |
| `code` | string | 是 | 系统并发安全生成、全局唯一、创建后不可变；法人 `LE-000001`，自然人 `NP-000001` |
| `identifier_type` | enum | 条件 | 法人仅 `unified_social_credit_code`、`legal_registration_number`、`foreign_registration_number`；自然人仅 `national_id`、`passport`；草稿可空，提审前与 `identifier_value` 成对必填 |
| `identifier_value` | string | 条件 | 法人规范化保存并按（`identifier_type`, 规范化值）唯一；自然人加密存储并只脱敏返回；提审前须格式正确 |
| `identifier_fingerprint` | string | 条件 | 自然人由（类型，规范化明文）生成的不可逆指纹，并按（`identifier_type`, `identifier_fingerprint`）唯一；法人为空，不对外返回 |
| `external_ref` | string | 否 | 外部系统记录 ID；无外部来源时为空，不承载统一标识或内部编码 |
| `status` | enum | 是 | `active`、`inactive` |
| `review_status` | enum | 是 | `draft`、`pending`、`approved`、`rejected`（两步审核；驳回后保留 `rejected` 态，可编辑后重新提审；**不可反审**——可反审的是 Asset 的 `reversed`，见 CONTEXT「轻量提交标记」/ADR-0014） |
| `review_by` | string | 否 | 审核人 |
| `reviewed_at` | datetime | 否 | 审核时间 |
| `review_reason` | string | 否 | 审核原因 |
| `metadata_json` | json | 否 | 非正式扩展信息；不得存放统一标识 |

约束：`party_type` 与 `identifier_type` 必须匹配；标识唯一性约束忽略草稿空值但覆盖全部非空记录。已审核 Party 不允许硬删除。停用和重新启用均为独立敏感动作，执行前展示业务引用与授权影响，要求原因并记录前后值；停用保留历史事实，禁止新增业务引用并使组织关系和用户绑定停止授权。重新启用经影响确认后恢复保留关系的效力。`PartyHierarchy` 不属于目标模型；未来企业关系必须使用带关系类型和有效期间的独立模型重新设计。

#### PartyLifecycleCommit

已审核 Party 的停用或重新启用不通过普通主档更新提交。预览仅保存于绑定操作者、Party、动作和状态指纹的短期服务端缓存；成功提交后写入一条持久化回执，既支持同一幂等键重放，也与审核日志共同构成审计事实。

| 字段 | 类型 | 必填 | 规则 |
|---|---|---|---|
| id | string | 是 | 回执主键 |
| party_id | string | 是 | 目标 Party；外键 RESTRICT |
| actor_id | string | 是 | 提交操作者；外键 RESTRICT |
| idempotency_key | string | 是 | 与 party_id、actor_id 联合唯一 |
| operation | enum | 是 | deactivate 或 reactivate |
| reason | string | 是 | 1-500 字，说明本次状态变更 |
| before_state / after_state | json | 是 | Party 状态、审核状态和新引用可用性的快照 |
| impact_summary | json | 是 | 代表组织、潜在组织、当前用户绑定、范围变化用户及资产/项目/合同引用计数 |
| result_data | json | 是 | 首次成功提交的 API 响应，用于幂等重放 |
| committed_at | datetime | 是 | 服务端提交时间 |

提交重新锁定 Party 并复算影响指纹；预览被消费、过期、操作者或动作不符、Party 状态或影响漂移时，以 409 SCOPE_CHANGE_PREVIEW_STALE 拒绝且不写入回执。停用保留历史 FK，但使组织默认范围和有效用户绑定不再授权；重新启用只恢复保留关系的效力。
### 4.18.1 Organization

| 字段 | 类型 | 必填 | 规则 |
|---|---|---|---|
| `id` | string | 是 | 内部组织主键 |
| `name` | string | 是 | 内部组织名称 |
| `code` | string | 是 | 内部组织编码，仅在 Organization 命名空间内唯一，不用于匹配 Party |
| `type` | enum | 是 | 内部公司、部门或项目组等组织分类；不改变 Party 身份 |
| `parent_id` | string | 否 | 上级 Organization；必须无环 |
| `level` | integer | 是 | 由层级关系维护的组织层级 |
| `path` | string | 否 | 由层级关系维护的祖先路径，不作为主体范围授权来源 |
| `sort_order` | integer | 是 | 同级展示顺序 |
| `status` | enum | 是 | `active`、`inactive` |
| `description` | text | 否 | 内部组织说明 |
| `is_deleted` | boolean | 是 | 组织逻辑删除标记；启用子组织或用户未处理时不得删除 |
| `represented_party_id` | string | 否 | 直接代表的 Party；只能引用 `approved + active + legal_entity` |
| `represented_party_perspective` | enum | 否 | 仅 `owner`、`manager`；与 `represented_party_id` 同时为空或同时有值 |

约束：同一 Organization 至多直接代表一个 Party，同一 Party 可被多个 Organization 代表。关系为空时运行时继承最近的、直接配置了有效关系的启用祖先；直接配置覆盖继承，继承结果不落库。直接关系存在但 Party 已失效时保留 FK 供审计并阻断上溯，不视为未配置。Organization 自身及完整祖先链必须启用；停用前必须先处理启用子组织和启用用户，不级联停用。会改变直接/继承范围的关联、解除、视角切换或组织移动必须先做影响预览、要求原因、记录前后值并立即失效授权缓存。批量关系变更使用幂等键并在同一事务内全成全败。

#### 4.18.1.1 OrganizationPartyScopeCommit

组织代表主体的预览结果只保存在带 TTL 的服务端缓存中，不进入业务数据库；提交成功后写入一条持久化回执，作为幂等重试和审计关联的事实来源。

| 字段 | 类型 | 必填 | 规则 |
|---|---|---|---|
| `id` | string | 是 | 回执主键 |
| `organization_id` | string | 是 | 目标 Organization；删除采用 RESTRICT |
| `actor_id` | string | 是 | 提交人；删除采用 RESTRICT |
| `idempotency_key` | string(128) | 是 | 与 Organization、提交人组成唯一幂等键 |
| `reason` | string(500) | 是 | 提交时必填的变更原因 |
| `proposal` | json | 是 | 规范化后的直接 Party/视角提议 |
| `before_scope` | json | 是 | 提交前范围快照 |
| `after_scope` | json | 是 | 提交后范围快照 |
| `impact_summary` | json | 是 | 组织和用户影响计数 |
| `result_data` | json | 是 | 完整提交响应快照，供幂等重试返回 |
| `committed_at` | datetime | 是 | 实际提交时间 |

约束：回执与组织关系、组织历史和直接字段在同一事务内写入；预览 token 只能消费一次，提交前重新计算指纹，提议、操作者、目标或相关范围状态变化时拒绝写入并返回 `SCOPE_CHANGE_PREVIEW_STALE`。

#### 4.18.1.2 OrganizationPartyScopeBatchCommit

批量代表主体变更只接受 2-100 条不同的直接 Organization 提议。服务端不允许同一批次同时选择祖先和子孙 Organization，避免独立预览基线互相覆盖；每个目标均需通过 `organization:manage_party_scope` 数据范围校验。

| 字段 | 类型 | 必填 | 规则 |
|---|---|---|---|
| `id` | string | 是 | 回执主键 |
| `actor_id` | string | 是 | 提交人；删除采用 RESTRICT |
| `idempotency_key` | string(128) | 是 | 与提交人组成唯一幂等键 |
| `reason` | string(500) | 是 | 提交时必填的变更原因 |
| `proposal` | json | 是 | 逐 Organization 规范化后的直接 Party/视角提议 |
| `before_scope` / `after_scope` | json | 是 | 每个目标提交前后的范围快照 |
| `impact_summary` | json | 是 | 去重后非重叠子树的组织和用户影响计数 |
| `result_data` | json | 是 | 首次批量提交响应快照，供幂等重试返回 |
| `committed_at` | datetime | 是 | 实际提交时间 |

约束：预览 token 绑定完整有序提议和操作者；提交先锁定每个目标的祖先链与子树，再重新解析所有提议并比对组合状态指纹。任一目标缺失、停用、Party 失效、层级重叠或状态漂移时，整个批次返回 `SCOPE_CHANGE_PREVIEW_STALE` 或相应校验错误，不写入任一 Organization。成功时在同一事务写入所有直接关系、每个 OrganizationHistory 和单个批量回执，并失效 Organization 访问缓存；相同操作者以同一幂等键重试时，从该回执的 `proposal` 恢复所有目标后逐个重新授权，不依赖已消费的预览 token。

#### 4.18.1.3 OrganizationMoveCommit

`parent_id` 只能通过专用组织移动预览/提交动作变更。预览不写 Organization 记录，提交消费绑定操作者、组织、规范化目标父组织和状态指纹的一次性 token，并保存可重放的提交回执。

| 字段 | 类型 | 必填 | 规则 |
|---|---|---|---|
| `id` | string | 是 | 回执主键 |
| `organization_id` | string | 是 | 被迁移 Organization；外键 RESTRICT |
| `target_parent_id` | string | 否 | 目标父 Organization；`null` 表示提升为根节点 |
| `actor_id` | string | 是 | 提交操作者；外键 RESTRICT |
| `idempotency_key` | string(128) | 是 | 与 `organization_id`、`actor_id` 组成唯一约束；同键重试返回首次结果 |
| `reason` | string(500) | 是 | 1-500 字符的迁移原因 |
| `proposal` | json | 是 | 规范化后的 `target_parent_id` |
| `before_scope` / `after_scope` | json | 是 | 被迁移节点的父级和有效 Party 范围快照 |
| `impact_summary` | json | 是 | 子树路径、组织范围和 active human 用户范围影响摘要 |
| `result_data` | json | 是 | 首次提交的 API 响应，用于幂等重试 |
| `committed_at` | datetime | 是 | 服务端提交时间 |

约束：预览和提交均拒绝源节点停用、目标父链缺失/停用/删除/环状、目标位于当前子树或无变化的提议。提交锁定受影响子树及旧/新祖先链，重新解析所有 active human 用户的范围并校验状态指纹；成功时在同一事务内写入 `parent_id`、整棵子树 `level/path`、`OrganizationHistory(action=move)` 和持久化回执。普通更新在 schema 和 service 两层拒绝 `parent_id`，成功后失效 Organization 可见范围和受影响用户 Party scope 缓存；token 过期、已消费或状态漂移返回 `SCOPE_CHANGE_PREVIEW_STALE`，不执行任何写入。

### 4.18.2 User

本节只列出本次主体范围切换新增或重命名的 User 字段；其余认证字段沿用现有用户契约。

| 字段 | 类型 | 必填 | 规则 |
|---|---|---|---|
| `account_type` | enum | 是 | `human`、`service`、`system`；创建后不可变，不能按用户名或角色推断 |
| `organization_id` | string | 条件 | 启用 `human` 用户必填且指向完整启用链上的 Organization；`service/system` 必须为空 |

约束：普通用户 API 只创建 `human`；`service` 仅由受控系统管理流程创建，`system` 仅由部署初始化或迁移建立。二者都不继承 Organization 默认范围。`default_organization_id` 一次重命名后不保留别名或双写。`human` 用户调动不得通过普通资料更新修改 `organization_id`，必须走 `user:manage_party_scope` 控制的影响预览与专用变更动作。

### 4.18.3 UserPartyBinding

| 字段 | 类型 | 必填 | 规则 |
|---|---|---|---|
| `id` | string | 是 | 显式范围绑定主键 |
| `user_id` | string | 是 | 被授权用户 |
| `party_id` | string | 是 | 仅可引用 `approved + active` Party |
| `relation_type` | enum | 是 | 仅 `owner`、`manager` |
| `valid_from` | datetime | 是 | 生效时间；创建时未指定则由服务端写入当前时间，也可预约未来生效 |
| `valid_to` | datetime | 否 | 到期时间；不得早于 `valid_from` |
| `created_at` | datetime | 是 | 创建时间 |
| `updated_at` | datetime | 是 | 更新时间 |

约束：不保留 `headquarters`、`is_primary` 或 Party 下级自动展开。全部当前有效绑定地位相同并按 owner/manager 分组；当前存在时间窗内绑定记录时，组织默认范围不参与并集。时间窗内绑定的目标 Party 后续失效时，该条不授权且阻断组织回退；其他有效显式绑定继续生效。创建、编辑、关闭和批量操作均需 `user:manage_party_scope`，并执行影响预览、必填原因、前后值审计和缓存失效；批量提交使用幂等键并在同一事务内全成全败。

#### UserPartyScopeCommit

单用户 `UserPartyBinding` 的 `create`、`update`、`close` 不直接写绑定表，只能先预览再提交。预览 token 绑定操作者、用户、规范化后的完整提议和状态指纹；提交要求原因和幂等键，成功后立即失效该用户的范围缓存。客户端传入的带时区 `valid_from`/`valid_to` 先统一规范为无时区 UTC 再参与数据库比较和指纹计算。

| 字段 | 类型 | 必填 | 规则 |
|---|---|---|---|
| `id` | string | 是 | 回执主键 |
| `user_id` | string | 是 | 被调整显式范围的用户；外键 RESTRICT |
| `actor_id` | string | 是 | 提交操作者；外键 RESTRICT |
| `idempotency_key` | string | 是 | 与 `user_id`、`actor_id` 组成唯一约束；同键重试返回首次结果 |
| `reason` | string | 是 | 1-500 字符，记录本次范围调整理由 |
| `proposal` | json | 是 | 服务端规范化后的操作、绑定、Party、关系类型和生效区间 |
| `before_scope` / `after_scope` | json | 是 | 单一 `PartyScopeResolver` 的提交前后结果 |
| `impact_summary` | json | 是 | 当前绑定数量、范围变化与组织回退影响 |
| `result_data` | json | 是 | 首次提交的 API 响应，用于幂等重放 |
| `committed_at` | datetime | 是 | 服务端提交时间 |

单用户显式绑定、human 用户调动、已审核 Party 启停、单组织移动和 Organization 直接代表主体批量提交协议已实施；用户显式绑定批量提交仍按同一契约待实施，不得复用已退役的直写用户绑定路由、普通用户更新入口或普通 Organization 更新入口。

#### UserOrganizationTransferCommit

`human` 用户的 `organization_id` 只能通过专用预览/提交动作变更。预览不写用户记录，提交必须消费绑定操作者、用户、规范化目标组织与状态指纹的一次性 token，并保存可重放的提交回执。

| 字段 | 类型 | 必填 | 规则 |
|---|---|---|---|
| `id` | string | 是 | 回执主键 |
| `user_id` | string | 是 | 被调动的 human 用户；外键 RESTRICT |
| `actor_id` | string | 是 | 提交操作者；外键 RESTRICT |
| `target_organization_id` | string | 是 | 目标 Organization；外键 RESTRICT |
| `idempotency_key` | string(128) | 是 | 与 `user_id`、`actor_id` 组成唯一约束；同键重试返回首次结果 |
| `reason` | string(500) | 是 | 1-500 字符的调动原因 |
| `proposal` | json | 是 | 规范化后的目标 `organization_id` |
| `before_scope` / `after_scope` | json | 是 | 单一 `PartyScopeResolver` 的提交前后结果 |
| `impact_summary` | json | 是 | 组织、作用域、显式绑定和缓存影响摘要 |
| `result_data` | json | 是 | 首次提交 API 响应，用于幂等重试 |
| `committed_at` | datetime | 是 | 服务端提交时间 |

约束：提交前锁定用户和目标 Organization，重新解析有效范围，并校验目标到根的完整、启用、未删除且无环的 Organization 链。普通用户更新和激活动作在把 `human` 账号置为 active 前执行同一组织链校验；`service/system` 账号不适用。成功提交消费 token、立即失效用户 Organization 可见范围缓存和 Party 范围缓存；提议、操作者、目标状态、组织链、显式绑定、角色或范围结果漂移时返回 `SCOPE_CHANGE_PREVIEW_STALE`，不写入用户组织。
### 4.18.4 EffectivePartyScope

唯一 `PartyScopeResolver` 返回的运行时投影，不建表。

| 字段 | 类型 | 必填 | 规则 |
|---|---|---|---|
| `source` | enum | 是 | `unrestricted`、`explicit`、`organization`、`fail_closed` |
| `scope_mode` | enum | 是 | `owner`、`manager`、`all`；仅作为服务端解析结果，双视角为 `all`，不从绑定顺序猜默认 |
| `owner_party_ids` | string[] | 是 | 可见产权方 Party 集合 |
| `manager_party_ids` | string[] | 是 | 可见运营方 Party 集合 |
| `organization_id` | string | 否 | 用户直接所属 Organization |
| `inherited_from_organization_id` | string | 否 | 组织默认范围的直接配置来源；用户本人诊断仅返回可安全展示的信息 |
| `next_transition_at` | datetime | 否 | 最近预约生效或到期边界；缓存不得越过该时刻 |
| `error_code` | enum | 否 | `PARTY_SCOPE_MISSING`、`PARTY_SCOPE_INVALID_ORGANIZATION`、`PARTY_SCOPE_INVALID_PARTY`、`PARTY_SCOPE_INVALID_BINDING` |
| `issues` | array | 是 | 配置异常集合；每项含 `code`、`node_type=organization|party|binding`、脱敏 `safe_label`，`node_ref` 仅向具备对应管理权限的查看者返回；禁止返回统一标识、指纹或外部引用 |

解析顺序固定为：当前有效分配内建 `admin`/`system_admin` 角色的不受限用户 → 当前有效显式绑定集合 → Organization 直接或最近祖先默认范围 → 失败关闭。`perm_admin` 与其他管理角色不进入不受限分支。失效显式记录存在但仍有其他有效显式绑定时，只使用有效集合并在 `issues` 中暴露配置异常；若没有任何可授权的有效显式绑定，则以 `PARTY_SCOPE_INVALID_BINDING` 拒绝业务请求，绝不回退组织。无显式记录时，组织链或关系异常分别按稳定原因码返回 403；配置、登录和不受限管理端点不受该业务范围错误阻断。

### 4.19 PartyContact

| 字段 | 类型 | 必填 | 规则 |
|---|---|---|---|
| `id` | string | 是 | 主体联系人主键 |
| `party_id` | string | 是 | 所属主体 ID |
| `contact_name` | string | 是 | 联系人姓名 |
| `contact_phone` | string | 否 | 联系电话，PII 字段，写入时确定性加密，读取时解密；生产环境必须配置 `REQUIRE_ENCRYPTION=true` |
| `contact_email` | string | 否 | 联系邮箱 |
| `position` | string | 否 | 职位 |
| `is_primary` | boolean | 是 | 是否主联系人；同一主体最多一个主联系人 |
| `notes` | text | 否 | 备注 |

### 4.20 PropertyCertificate

| 字段 | 类型 | 必填 | 规则 |
|---|---|---|---|
| `id` | string | 是 | 产权证主键 |
| `certificate_number` | string | 是 | 证号，全局唯一且非空（正式保存硬门槛）；重复证号不得新建第二条，应维护既有产权证的资产关联 |
| `certificate_type` | enum | 是 | 证照类型，如不动产权 / 房屋 / 土地 / 其他 |
| `property_address` | string | 条件 | 坐落 / 地址；不动产权 / 房屋 / 土地证类型必填，其他证照类型按证号；非空为正式保存硬门槛（2026-06-18 grill 扩 ADR-0005 原四项为五项，已实施）|
| `asset_ids` | string[] | 是 | 关联既有资产（ORM 经 `assets` 关系），至少一个；产权证↔资产为多对多平等关联，不分主 / 附属资产；可追加或移除，但更新后不得为空、删除最后一个关联应拒绝，不允许保存为孤立证照 |
| `attachment_ids` | string[] | 是 | 附件 ID 列表，至少一份（见 §4.22 Attachment）；附件是证照事实底座，不区分「证照扫描件」与「其他附件」，删除最后一份应拒绝 |
| `holder_party_ids` | string[] | 是 | 权利人（ORM 经 `party_relations` / `CertificatePartyRelation` 关联，见 §4.21），必须引用已审核 Party |
| `building_area` | number | 否 | 证载建筑面积；缺失只作 `warning` 级补录完整性提示，不阻断保存 |
| `land_area` | number | 否 | 证载土地面积；缺失同上只 `warning` |
| `land_use_term_start` | date | 否 | 期限（土地使用起）；缺失同上只 `warning` |
| `land_use_term_end` | date | 否 | 期限（土地使用止）；缺失同上只 `warning` |
| `restrictions` | string | 否 | 限制信息；缺失同上只 `warning` |

约束：

- **正式保存 5 项硬门槛**：证号全局唯一且非空、≥1 既有资产关联、≥1 附件、权利人引用已审核 Party、坐落 / 地址非空（按 `certificate_type`）。保存闸门须按此 5 项校验，不得用解析字段校验器代替、不得漏卡资产 / 附件 / 权利人。
- 其余证照信息（证载面积 / 期限 / 限制）为空只 `warning` 级补录完整性提示，不阻断资产维护、合同补录、台账生成或经营统计。
- MVP 不含核验状态（`is_verified` 已删，见 ADR-0005）。数据质量风险只两类客观项——证照信息不完整、权利人与关联资产当前主产权主体不一致，均 `warning` 级、由当前数据实时派生、人工修正源数据自然消除，不可手工关闭 / 忽略 / 标记已处理，不进全局搜索、不建独立处置流程（风险落点见 §4.5.1 ProjectRisk）。
- 解析辅助补录与附件遵循 §2「字段来源」「扫描件解析确认」跨对象规则；产品级规则见 PRD §6.5。

### 4.21 CertificatePartyRelation

| 字段 | 类型 | 必填 | 规则 |
|---|---|---|---|
| `id` | string | 是 | 关系主键 |
| `certificate_id` | string | 是 | 所属产权证 ID |
| `party_id` | string | 是 | 权利人主体 ID，必须引用已审核 Party（背 REQ-PTY-002）|
| `relation_type` | enum | 是 | 权利人 |

### 4.22 Attachment

| 字段 | 类型 | 必填 | 规则 |
|---|---|---|---|
| `id` | string | 是 | 附件主键 |
| `owner_type` | enum | 是 | `asset`、`contract`、`property_certificate`、`payment_flow` |
| `owner_id` | string | 是 | 所属业务对象 ID |
| `file_name` | string | 是 | 文件名；仅作展示与日志字段，不作为 MVP 筛选条件 |
| `file_type` | enum | 是 | 仅接受 PDF、JPG/JPEG、PNG；其他类型拒绝 |
| `file_size` | number | 是 | 单文件大小上限 20MB，超限拒绝并提示压缩或拆分 |
| `file_hash` | string | 否 | 用于同名或相同哈希的疑似重复提示 |
| `storage_key` | string | 是 | 服务端生成的唯一相对存储键，不接受客户端路径 |
| `created_by` | string | 是 | 上传人，由服务端从认证用户固化 |
| `created_at` | datetime | 是 | 上传时间 |

约束：

- **预览**跟随所属对象查看权限，PDF 内嵌预览、JPG/PNG 图片预览，不单独记操作日志；预览失败只提示「预览失败，可下载查看」，不阻断保存、附件保留或扫描件解析；MVP 不做批注、旋转、裁剪、全文搜索或 OCR 原文高亮。
- **下载**是独立资料外流动作，必须校验独立下载权限（≠ 查看权限）；收付流水凭证使用 `ledger_voucher:read`，并在确认附件属于当前流水且流水冻结归属位于当前主体范围后下载。轻量下载日志记录下载人、流水、附件、下载时间和结果（`success` / `not_found`），其中 `success` 表示服务端已授权且文件已就绪，不声明客户端已完整接收；不记下载原因、来源页 / 入口、客户端 IP 或设备信息，不触发审批或告警。未通过主体范围校验的用户不得读取附件或审计元数据。下载日志仅在系统操作日志 / 审计查询、详情不默认展示；MVP 只支持单附件下载，不做打包下载。
- **追加 / 替换 / 删除**：替换不保留旧档，删除不记原因；删到最后一份被阻止（产权证、合同补录附件均须 ≥1）。变更日志记附件 ID、文件名、动作类型、操作人、操作时间，不记原因、不留旧文件内容、不做差异追踪。
- **疑似重复**只提示「疑似重复附件」、不展示命中依据、默认不追加，用户显式追加即确认、不二次弹窗、不阻断保存。
- 附件上传后不自动触发解析（上传与解析是两个独立动作）。MVP 不做附件版本管理、替换审批、差异追踪、备注字段、维护来源字段、容量配额、打包下载、批量解析 / 确认或复杂上传队列。
- 通用 `Attachment` 是产权证正式附件的唯一持久化模型，固定使用 `owner_type=property_certificate`、`owner_id=certificate_id`；产权证专用附件表/关系和客户端传入 `storage_key` 不属于目标模型。公开上传接口保持在资产/产权证域内嵌套，由服务端确定 owner；格式与资源限制使用用途 profile 做有界、fail-loud 校验。

### 4.23 ScanExtractionSession

合同或产权证扫描件解析辅助补录的临时会话，仅当前补录过程的临时工作区，不持久化为长期记录。

| 字段 | 类型 | 必填 | 规则 |
|---|---|---|---|
| `session_id` | string | 是 | 临时会话 ID；确认 / 取消 / 失败 / 放弃后不留档，不提供草稿保存、历史档案或稍后继续确认（见 §2「扫描件解析确认」）|
| `target_type` | enum | 是 | `contract`、`property_certificate` |
| `input_mode` | enum | 是 | `upload`、`attachment_reference`；产权证新建使用前者，既有产权证解析使用后者 |
| `target_asset_id` | string | 条件 | 产权证分支必填；新建时是发起资产上下文，既有时还用于校验产权证确实关联该资产 |
| `target_certificate_id` | string | 条件 | 既有产权证解析必填；新建分支禁止传入 |
| `target_attachment_id` | string | 条件 | 既有产权证解析必填，且必须属于 `target_certificate_id`；新建分支禁止传入 |
| `staged_file_metadata` | json | 条件 | `input_mode=upload` 时由服务端生成的临时存储键、规范 MIME、大小与 SHA-256；仅会话内部可见，不返回公开临时 URL |
| `status` | enum | 是 | 解析中、待确认、失败、超时（临时态，不作为长期记录）|
| `candidate_fields` | json | 否 | 候选字段值、置信度、低置信标记、轻量来源证据（页码 / 文本片段 / 截图区域）、候选匹配、差异提示、建议补全字段；均临时，确认后不长期保存 |

约束：

- 确认写入目标对象的字段来源只取 `manual` / `ocr_prefill_confirmed` / `ocr_prefill_corrected`（见 §2「字段来源」）；候选不自动绑定 Party·Asset、不自动覆盖已保存字段（冲突仅作差异提示）。
- 产权证新建分支恰好接收一个 PDF/JPEG/PNG 临时文件；确认时满足 §4.20 五项硬门槛，并通过可补偿的文件晋升与数据库事务一次创建产权证、资产/权利人关系和通用 `Attachment`。取消、失败、超时、过期或提交失败均清理暂存文件，不创建产权证草稿或孤儿附件。
- 产权证既有分支不接收文件，只引用当前产权证的通用 `Attachment`；普通附件上传后不自动解析。证号冲突只允许用户显式关联既有产权证并决定是否追加本次暂存文件，不自动新建重复证号记录或绑定资产。
- 不持久化解析工具、模型、供应商、置信度、确认时间、页码、文本片段或截图区域等元信息。
- 同一附件重新解析废弃旧未确认候选、不留版本对比；已确认写入主数据的字段不受影响。建议补全字段不填写不阻断确认保存。

### 4.24 Notification

站内业务提醒与系统通知。**通知是提醒不是工单**——只有已读 / 未读，无处理闭环、不指派、不承载待办或任务语义。

| 字段 | 类型 | 必填 | 规则 |
|---|---|---|---|
| `id` | string | 是 | 通知主键 |
| `recipient_id` | string | 是 | 接收用户 ID；业务提醒按统一解析的有效主体范围过滤——仅向可见该对象（owner / operator 范围）的用户创建（正文含合同号 / 租户名等业务数据，受 §8 约束） |
| `type` | enum | 是 | `contract_expiring`、`contract_expired`、`payment_overdue`、`payment_due`、`system_notice` 五类；`payment_due` / `payment_overdue` 仅用于终端租户租金到期/逾期 |
| `priority` | enum | 是 | `low` / `normal` / `high` / `urgent`；为 `days_overdue` / `days_remaining` 实时派生的优先级档位、不存标记位（口径同 ADR-0007） |
| `title` | string | 是 | 通知标题 |
| `content` | text | 是 | 通知正文 |
| `related_entity_type` | string | 否 | 关联实体类型（contract / asset 等）；系统通知强制为空 |
| `related_entity_id` | string | 否 | 关联实体 ID；系统通知强制无该值（内容中立硬约束，见下） |
| `is_read` | boolean | 是 | 已读 / 未读（唯一状态轴，无处理闭环） |
| `read_at` | datetime | 否 | 已读时间 |
| `is_sent_wecom` | boolean | 是 | 是否已推送企业微信 |
| `wecom_sent_at` | datetime | 否 | 企业微信推送时间 |
| `wecom_send_error` | text | 否 | 推送错误信息；推送失败不影响站内通知创建、不做送达重试保障 |
| `extra_data` | text | 否 | 额外数据（JSON） |

约束：

- **档位幂等去重**（ADR-0015）：幂等键 =（`recipient_id`, 对象, `type`, 优先级档位），同档位不重复生成、跨档位升级各生成一次。终端租户租金逾期按 `days_overdue` 派生 `NORMAL→HIGH(≥7天)→URGENT(≥30天)`；合同/协议到期与终端租户租金到期按剩余天数派生 30→15→7 天档位。档位实时派生、不存标记位，既不按天重发刷屏、也不因首条未读漏发后续升级。到期与逾期提醒由定时扫描生成，逾期判定按终端租户收缴派生口径（`due_date` 已过且终端租户租金 `paid_amount < amount_due` 且非 `voided`，见 §4.14、ADR-0007）。运营方成本未付、服务费未收不生成逾期通知。
- **系统通知广播豁免 + 内容中立硬约束**：`system_notice` 是唯一可豁免数据范围、广播全体活跃用户的类型，前提是内容中立——仅 `admin` / `system_admin` 可发，服务端强制无 `related_entity_id`、不挂业务实体、不含 PII，违反即拒绝创建；管理员手动一次性创建，不进定时扫描、不做档位幂等（那套只管派生类业务提醒）。
- **企业微信推送**（ADR-0016）：可选通道、配置开关控制；按 `recipient_id` 定向推送应用消息（`touser` + `agentid`），不走群机器人广播——推给本人天然落在其数据范围内、自洽 §8，正文可含合同号 / 租户名 / 金额。是个人消息提醒不是企业微信待办（无完成态 / 处理闭环，同 ADR-0006）。当前代码已接入企业微信应用消息与 `gettoken` / `message/send`，真实发送验证受企业微信可信 IP / 域名前置配置阻塞（本地报 `errcode=60020`）；正式上线前仍需补系统用户 ↔ 企业微信 `userid` 映射，避免长期依赖 `recipient_id == touser` 的本地假设。
- **提醒非工单**：只有 `is_read` / `read_at`，无处理闭环、不指派、不承载待办语义。MVP 不做通知模板配置、用户自定义订阅规则、短信或邮件通道。

## 5. 状态机

### 5.1 ContractGroup 派生状态

| 派生状态 | 判定规则 |
|---|---|
| 筹备中 | 组内无生效合同 |
| 生效中 | 组内存在至少一份生效合同 |
| 已结束 | 组内全部正常合同均已终止，或仍为生效但 `effective_to < today` 自然到期，且至少有一份合同 |

### 5.2 Contract 生命周期

最小生命周期，不做 BPM 路由审批流（无提审/审核/联审/反审核，补录即生效，见 ADR-0013）。

| 当前状态 | 动作 | 目标状态 | 约束 |
|---|---|---|---|
| 草稿（纠错/录入中） | 补录定稿 | 生效 | 签订日期必填，关联主体必须已审核；补录即生效，无提审/审核步骤，写入审计日志并生成台账 |
| 生效 | 自然到期 | 生效（展示派生为已到期） | 停止生成未来台账；不写 `status`、不生成 `expire` 审计 |
| 生效 | 提前终止 | 已终止 | 终止原因必填 |
| 生效 | 纠错 | 新纠错草稿（原合同不反审核） | 门禁：纠错草稿只能从生效合同发起；原合同相关台账按重算或作废处理（**无冲销**，见 ADR-0008、台账重算口径） |
| 生效 | 作废 | 已作废（`data_status`） | 无台账或台账已全部作废 |

### 5.3 审核状态

仅承重对象保留审核生命周期；Contract 无 `review_status`（补录即生效，见 ADR-0013）、Project 无 review 生命周期（孤儿列已删，见 ADR-0014）。

| 对象 | 状态 |
|---|---|
| Asset | `draft`、`pending`、`approved`、`reversed`（两步确认，可反审，见 ADR-0002） |
| Party | `draft`、`pending`、`approved`、`rejected`（两步审核，背 REQ-PTY-002 已审主体引用） |

### 5.4 Approval 状态（MVP 已删除）

审批实例、审批待办和审批动作日志不属于当前目标态。

## 6. 统计口径

| 指标 | 公式或规则 |
|---|---|
| 终端租户收缴率 | 租金账期实收金额 / 租金账期应收金额 * 100% |
| 终端租户收缴率分母 | 指定租金账期内非作废终端租户租金台账 `amount_due` 之和，包含承租转租下游租金和代理直租租金，不含服务费台账和上游成本 |
| 终端租户收缴率分子 | 指定租金账期内上述条目截至当前已登记实收金额之和，不按实际收款发生月份归属 |
| 运营方收入 | 承租转租租金收入 + 代理服务费收入，不含代理直租租金 |
| 承租转租租金收入 | 承租转租下游租金收入 |
| 代理服务费收入 | 代理运营服务费收入 |
| 运营方成本 | 承租转租上游租金成本 |
| 经营净流入 | 运营方收入实收 - 运营方成本实付，金额看已登记实收/实付、时间按账期归属 |
| 账面经营差额 | 运营方收入应收 - 运营方成本应付 |
| 项目经营模式分布 | 项目下合同与协议经营事项按 `revenue_mode` 分组计数和汇总 |
| 全局项目分区 | 全局经营分析按 `ContractGroup.project_id` 聚合合同/协议、终端租户收缴、运营方收入/成本、经营结果和客户指标 |
| 全局模式分区 | 全局经营分析按 `lease_sublease` / `agency_operation` 聚合合同/协议、终端租户收缴、运营方收入/成本、服务费和客户指标 |
| 客户主体数 | 仅统计下游转租 / 代理直租终端 lessee，按 Party 去重；`customer_type` 只是展示标签，不参与经营指标过滤 |
| 客户合同数 | 仅统计下游转租 / 代理直租合同，按合同 ID 去重 |
| 逾期金额 | `due_date` 已过且 `paid_amount < amount_due` 且状态非 `voided` 的终端租户租金未收金额；运营方成本未付、服务费未收不计逾期 |
| 多资产合同金额 | 合同级口径，不按资产分摊；汇总时按合同去重 |

## 7. Out of Scope 对象

| 对象 | 说明 |
|---|---|
| Ownership | 权属方管理不纳入 MVP 需求基线；当前保留代码骨架，路由和菜单可见面冻结 |
| 通用 BPM 审批流引擎 | MVP 不建设通用流程引擎；资产审批路由流已删除 |
| 催缴管理 | MVP 不建催缴工单、催缴状态机或催缴成功率统计；逾期处理依靠终端租户收缴逾期查询、轻量跟进状态和收款流水登记闭环 |
