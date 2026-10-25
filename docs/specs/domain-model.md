# 领域模型契约

## 1. 文档定位

本文档定义资产运营 v5 的业务对象、字段、状态机和统计口径。产品范围见 [`docs/prd.md`](../prd.md)，端点和错误契约见 [`docs/specs/api-contract.md`](api-contract.md)。

本契约是目标态规格，可以先于 ORM 落地。尚未落地的字段不得用旧模型近似替代；实施时按迁移计划一次切换，不做新旧事实源双写。

## 2. 跨对象规则

1. **事实与投影分离**：合同、资产单元、付款/到账、对账、考核范围、报送快照、档案和导入批次是事实；出租状态、本月事项、台账汇总、档案完成率和统计是投影。
2. **有效期半开区间**：业务有效期统一解释为 `[start_date, end_date + 1 day)`；日期重叠按自然日判断。
3. **追加而非覆盖**：付款撤销、合同终止、上游退出、报送撤回、导入撤销和边界调整均追加事件，不删除原事实。
4. **历史快照**：报送、已确认管理费对账和已结束合同保留确认时名称、金额、比例、范围与版本，不依赖当前主档回算。
5. **乐观并发**：可写聚合带 `version`；更新要求携带期望版本，冲突返回稳定 409。
6. **幂等写入**：高后果写操作保存 `idempotency_key`，同键同请求返回首次结果，同键不同请求拒绝。
7. **数据范围**：所有业务对象通过产权方 Party 或项目归属解析有效 Party 范围；无范围或范围失效失败关闭。
8. **金额**：金额使用定点十进制，币种 MVP 固定为 `CNY`；显示可格式化，存储和计算不得使用二进制浮点。
9. **面积**：面积使用定点十进制平方米；拆分/合并在允许误差内守恒。
10. **业务时区**：月末、截止日、撤销窗口和“今天”按 `Asia/Shanghai` 解释。

## 3. 核心对象

| 对象 | 类型 | 事实含义 |
|---|---|---|
| Party | 平台事实 | 产权方、运营方或终端租户身份 |
| Organization / User / EffectivePartyScope | 平台事实/投影 | 用户归属、业务角色和可访问 Party 范围 |
| Project | 业务事实 | 资产单元管理归属标签，不承载统计事实 |
| AssetUnit | 业务事实 | 最小可租物业边界，一宗的身份 |
| AssetUnitBoundaryChange | 业务事实 | 资产单元拆分或合并的有效期变化 |
| AssetUnitBoundarySource | 关系事实 | 边界变更消费的源单元；一个单元只能被消费一次 |
| PropertyCertificate | 业务事实 | 产权证登记信息 |
| PropertyCertificateAssetUnit | 关系事实 | 产权证与资产单元多对多关联 |
| UpstreamContract | 业务事实 | 已签承租合同或委托管理协议 |
| TerminalContract | 业务事实 | 已签终端转租或产权方直签合同 |
| ContractAssetUnit | 关系事实 | 合同在期间内覆盖的资产单元 |
| ContractRentSchedule | 业务事实 | 合同分阶段租金、账期、递增和免租条款 |
| ContractLifecycleEvent | 业务事实 | 续签、终止、退出和撤销等追加事件 |
| AssetContractWriteReceipt | 技术事实 | 已签合同确认命令的幂等请求指纹与首次响应 |
| RentLedgerEntry | 业务事实 | 某合同某账期的一笔应付、应收或产权方应报到账义务 |
| RentPaymentRecord | 业务事实 | 外部付款或到账的追加登记及其撤销 |
| DepositLedgerEntry | 业务事实 | 押金约定、应收/应退/应收回方向和余额 |
| ManagementFeeStatement | 业务事实 | 某产权方某月委托管理费对账单 |
| ManagementFeeStatementLine | 业务事实 | 纳入对账的产权方实际到账租金明细 |
| AssessmentScopeVersion | 业务事实 | 某年度已保存考核范围版本 |
| AssessmentScopeItem | 业务事实 | 版本内逐资产单元纳入/排除决定 |
| MonthlyOccupancyReport | 业务事实 | 月度报送草稿和已锁定快照 |
| MonthlyOccupancyReportLine | 快照事实 | 报送时逐资产单元的口径和数值 |
| ArchiveDocument | 业务事实 | 挂接业务对象的扫描件及版本 |
| ImportBatch / ImportBatchChange | 业务事实 | 批量新增或更新的校验、差异、提交和撤销链 |
| BusinessChangeEvent | 审计事实 | 谁在何时对哪个业务对象做了什么以及原因 |
| MonthlyWorkItem | 派生投影 | 当月截止事项和随时处理事项 |

## 4. 字段契约

### 4.1 Party

| 字段 | 类型 | 约束 |
|---|---|---|
| `id` | UUID | 主键 |
| `code` | string | 系统生成、创建后只读 |
| `name` | string | 当前主档名称 |
| `party_type` | enum | `legal_entity` / `individual` |
| `status` | enum | `draft` / `pending` / `approved` / `rejected` |
| `active` | boolean | 已审核主体启停状态 |
| `version` | integer | 乐观锁版本 |

Party 只保存身份，不保存“产权方/终端租户”等固定角色；角色由当前有效业务关系派生。

### 4.2 Organization

| 字段 | 类型 | 约束 |
|---|---|---|
| `id` | UUID | 主键 |
| `name` | string | 组织名称 |
| `parent_id` | UUID? | 上级组织；不得形成环 |
| `represented_party_id` | UUID? | 直接代表的法人 Party |
| `represented_party_perspective` | enum? | `owner` / `manager`；与 Party 字段同时空或同时有值 |
| `is_active` | boolean | 停用组织不产生默认业务范围 |
| `version` | integer | 乐观锁版本 |

### 4.3 User

| 字段 | 类型 | 约束 |
|---|---|---|
| `id` | UUID | 主键 |
| `username` | string | 唯一登录名 |
| `account_type` | enum | `human` / `service` / `system` |
| `organization_id` | UUID? | 启用 human 用户必填且唯一 |
| `is_active` | boolean | 停用后不可访问业务数据 |
| `version` | integer | 乐观锁版本 |

### 4.4 EffectivePartyScope

| 字段 | 类型 | 约束 |
|---|---|---|
| `source` | enum | `administrator` / `explicit_binding` / `organization` |
| `owner_party_ids` | UUID[] | 可读取产权方视角 Party 集合 |
| `manager_party_ids` | UUID[] | 可读取运营方视角 Party 集合 |
| `issues` | object[] | 范围配置异常；存在阻断项时业务请求返回 403 |
| `next_transition_at` | datetime? | 预约生效/到期的下一时间边界 |

该对象是运行时投影，不重复持久化业务数据。

### 4.5 Project

| 字段 | 类型 | 约束 |
|---|---|---|
| `id` | UUID | 主键 |
| `code` | string | 稳定项目编码 |
| `name` | string | 项目名称 |
| `manager_party_id` | UUID | 运营方 Party |
| `is_active` | boolean | 停用项目不可新增资产单元 |
| `version` | integer | 乐观锁版本 |

Project 只作管理归属标签。项目汇总必须逐资产单元或合同事实计算，不保存可独立编辑的宗数、面积、出租率或累计租金。

### 4.6 AssetUnit

| 字段 | 类型 | 约束 |
|---|---|---|
| `id` | UUID | 主键 |
| `unit_code` | string | 全局唯一、创建后只读 |
| `name` | string | 业务可读名称 |
| `project_id` | UUID | 管理归属标签 |
| `owner_party_id` | UUID | 已审核且启用的产权方 Party |
| `address` | string | 物业地址 |
| `usage_type` | enum | 业态类别字典值 |
| `acquisition_mode` | enum | `owned` / `leased` / `managed` |
| `is_operating` | boolean | 是否经营性物业 |
| `land_area` | decimal | 平方米，默认 `0`，不按单元强制分摊 |
| `building_area` | decimal | 建筑面积，非负 |
| `rentable_area` | decimal | 可出租面积，非负且不大于建筑面积 |
| `managed_from` | date | 接管生效日 |
| `managed_to` | date? | 停止在管日；不得早于开始日 |
| `vacancy_reason` | enum? | `renovation` / `marketing` / `repossession` / `pending_contract` / `other` |
| `expected_lease_start` | date? | 空置经营备注 |
| `predecessor_unit_ids` | UUID[] | 由拆分/合并接续的原单元 |
| `version` | integer | 乐观锁版本 |
| `created_at` | datetime | 创建时间 |
| `updated_at` | datetime | 最后修改时间 |

派生字段：`rental_status`、`active_terminal_contracts`、`assessment_status`、`certificate_gap`、`upstream_risk`。

### 4.7 AssetUnitBoundaryChange

| 字段 | 类型 | 约束 |
|---|---|---|
| `id` | UUID | 主键 |
| `change_type` | enum | `split` / `merge` |
| `effective_date` | date | 新旧单元切换日 |
| `source_unit_ids` | UUID[] | 至少一个；合并至少两个 |
| `result_unit_ids` | UUID[] | 至少一个；拆分至少两个 |
| `area_check` | object | 各面积维度变更前后合计；两侧必须严格相等 |
| `reason` | string | 必填 |
| `created_by` | UUID | 操作人 |
| `created_at` | datetime | 操作时间 |
| `idempotency_key` | string | 同一 `created_by` 内唯一 |
| `request_fingerprint` | string | 操作者范围内幂等请求指纹；同键不同请求拒绝 |
| `result_data` | object | 首次提交响应快照；同键同请求重试原样返回 |

拆分和合并只改变生效日后的有效边界；源单元在生效日前一日必须仍处于在管期间，提交后其 `managed_to` 为生效日前一日，结果单元的 `managed_from` 为生效日，历史报送和台账不回写。拆分结果继承源单元的 Project、产权方、用途、取得方式和经营标记，调用方只提交结果编号、名称和三类面积。生效日或之后仍覆盖源单元的有效/待生效终端合同必须先处理，边界调整失败关闭；晚于边界日开始的上游覆盖也必须先调整，不能遗留在即将退役的源单元上。源单元存在有效上游覆盖时，在同一事务将原覆盖于前一日截止，并从生效日起复制到结果单元；若上游覆盖恰在边界日开始，则直接删除源关系并在结果单元重建，不制造 `effective_to < effective_from` 的空区间；没有有效上游覆盖不阻断拆分。合并调用方只提交至少两个源单元 ID、生效日和结果编号/名称，三类结果面积由服务端汇总，不能手工覆盖。合并源单元的 Project、产权方、地址、用途、取得方式和经营标记必须一致；空置备注仅在所有源单元一致时继承，否则清空。合并生效日的每个源单元必须具有相同且非空的有效上游合同集合，“有效”同时检查覆盖区间、合同期限以及未被有效退出事件关闭；同一上游合同在各源单元上的未来覆盖截止边界也必须一致，防止合并后丢失合同权利边界。

### 4.7.1 AssetUnitBoundarySource

| 字段 | 类型 | 约束 |
|---|---|---|
| `id` | UUID | 主键 |
| `asset_unit_id` | UUID | 唯一；同一源单元只能进入一次拆分或合并 |
| `boundary_change_id` | UUID | 关联追加式边界事件 |

该关系是防止重复拆分/合并的耐久互斥事实，不能只靠 `managed_to` 或 JSON 数组判断。所有创建/修改合同覆盖或边界源关系的写服务必须先锁定受影响 `AssetUnit`（多单元时按 ID 排序），再读取覆盖、生命周期事件和该关系；否则不得写入，以避免检查—提交之间插入新的覆盖事实。

### 4.8 PropertyCertificate

| 字段 | 类型 | 约束 |
|---|---|---|
| `id` | UUID | 主键 |
| `certificate_number` | string | 非空且唯一 |
| `holder_party_id` | UUID | 权利人 Party |
| `registered_address` | string | 证载坐落 |
| `registered_land_area` | decimal? | 证载土地面积 |
| `registered_building_area` | decimal? | 证载建筑面积 |
| `valid_from` / `valid_to` | date? | 证载有效期 |
| `version` | integer | 乐观锁版本 |

### 4.9 PropertyCertificateAssetUnit

| 字段 | 类型 | 约束 |
|---|---|---|
| `certificate_id` | UUID | 联合唯一的一部分 |
| `asset_unit_id` | UUID | 联合唯一的一部分 |
| `effective_from` | date | 关系生效日 |
| `effective_to` | date? | 关系结束日 |

一本证可关联多个资产单元，一个资产单元可关联多本证。档案“应有产权证”按证计数，另派生未关联任何证的资产单元数。

### 4.10 UpstreamContract

| 字段 | 类型 | 约束 |
|---|---|---|
| `id` | UUID | 主键 |
| `contract_number` | string | 非空且唯一 |
| `contract_type` | enum | `lease` / `management_agreement` |
| `name` | string | 合同名称 |
| `owner_party_id` | UUID | 产权方/委托方 |
| `operator_party_id` | UUID | 本公司主体 |
| `start_date` | date | 已签期限开始日 |
| `end_date` | date | 已签期限结束日，不早于开始日 |
| `payment_cycle` | enum? | 承租合同：`monthly` / `quarterly` / `yearly` / `custom` |
| `payment_day` | integer? | 约定到期日 |
| `management_fee_rate` | decimal? | 委托管理协议比例，0–1 |
| `deposit_amount` | decimal | 非负 |
| `oa_reference` | string? | 外部 OA/合同系统单号，仅作关联信息 |
| `renewed_from_id` | UUID? | 前驱上游合同 |
| `scan_document_id` | UUID | 已签扫描件，确认前必填 |
| `version` | integer | 乐观锁版本 |
| `created_at` | datetime | 创建时间 |
| `updated_at` | datetime | 最后修改时间 |

派生状态由日期、后继合同和退出事件决定：`scheduled`、`active`、`expiring`、`expired_pending_action`、`exited`、`historical`。

### 4.11 UpstreamContractAssetUnit

| 字段 | 类型 | 约束 |
|---|---|---|
| `upstream_contract_id` | UUID | 联合唯一的一部分 |
| `asset_unit_id` | UUID | 联合唯一的一部分 |
| `effective_from` | date | 覆盖开始日 |
| `effective_to` | date? | 覆盖结束日 |

### 4.12 TerminalContract

| 字段 | 类型 | 约束 |
|---|---|---|
| `id` | UUID | 主键 |
| `contract_number` | string | 非空且唯一 |
| `contract_mode` | enum | `sublease` / `direct_lease` |
| `tenant_party_id` | UUID | 终端租户 Party |
| `lessor_party_id` | UUID | 转租为本公司，直签为产权方；按模式确定并冻结快照 |
| `upstream_contract_id` | UUID? | 允许暂缺；缺失时产生风险 |
| `start_date` | date | 已签期限开始日 |
| `end_date` | date | 已签期限结束日，不早于开始日 |
| `deposit_months` | decimal? | 约定押金月数 |
| `deposit_amount` | decimal | 非负；可由约定月数和月租生成后确认 |
| `rent_collector` | enum | `operator` / `owner`；按模式确定 |
| `renewed_from_id` | UUID? | 前驱终端合同 |
| `scan_document_id` | UUID | 已签扫描件，确认前必填 |
| `version` | integer | 乐观锁版本 |
| `created_at` | datetime | 创建时间 |
| `updated_at` | datetime | 最后修改时间 |

派生状态：`scheduled`、`active`、`expiring`、`ended`、`historical`。派生风险：`upstream_missing`、`term_exceeds_upstream`、`scan_missing`、`deposit_unsettled`。

### 4.13 TerminalContractAssetUnit

| 字段 | 类型 | 约束 |
|---|---|---|
| `terminal_contract_id` | UUID | 联合唯一的一部分 |
| `asset_unit_id` | UUID | 联合唯一的一部分 |
| `effective_from` | date | 覆盖开始日 |
| `effective_to` | date? | 覆盖结束日 |

同一资产单元同一自然日期不得被两份有效终端合同覆盖。一个终端合同可以覆盖多个资产单元。覆盖行在合同确认时写入，`effective_from` 与 `effective_to` 分别等于合同 `start_date` 与 `end_date`；终端终止提交在同一事务把仍延伸到终止生效日之后的覆盖行截止到生效日前一日，使后继合同最早可从终止生效日开始且不触发同期覆盖排斥约束。合同更新的 `end_date` 变更在同一事务把仍等于旧 `end_date` 的覆盖行重定向到新值（已被生命周期截止的行不动），延长后与他合同覆盖重叠由排斥约束兜底并整体回滚。

### 4.14 ContractRentSchedule

| 字段 | 类型 | 约束 |
|---|---|---|
| `id` | UUID | 主键 |
| `contract_kind` | enum | `upstream` / `terminal` |
| `contract_id` | UUID | 对应合同 |
| `stage_start` | date | 阶段开始日 |
| `stage_end` | date | 阶段结束日，不早于开始日 |
| `base_monthly_rent` | decimal | 原定月租，非负 |
| `increase_rate` | decimal | 本阶段相对前阶段递增比例 |
| `free_rent_months` | decimal | 免租月数 |
| `discount_amount` | decimal | 免租/减免合计 |
| `actual_monthly_rent` | decimal | 确认后的本阶段月租 |
| `payment_cycle` | enum | `monthly` / `quarterly` / `yearly` / `custom` |
| `due_day` | integer | 合同约定到期日 |

递增按阶段叠加；季付只在季初月份形成义务。租金表修改只影响尚未锁定的未来义务，历史义务不回写。

### 4.15 ContractLifecycleEvent

| 字段 | 类型 | 约束 |
|---|---|---|
| `id` | UUID | 主键 |
| `contract_kind` | enum | `upstream` / `terminal` |
| `contract_id` | UUID | 目标合同 |
| `event_type` | enum | `renewed` / `terminated` / `exited` / `reversed` |
| `effective_date` | date | 事件生效日，即新状态开始的第一天 |
| `termination_type` | enum? | `expiry` / `early` / `mutual` |
| `handover_status` | enum? | `pending` / `completed` / `not_applicable` |
| `deposit_settlement_status` | enum? | `pending` / `settled` / `not_applicable` |
| `successor_contract_id` | UUID? | 续签后继合同 |
| `reversed_event_id` | UUID? | 撤销事件明确指向的原事件；仅 `reversed` 必填 |
| `reason` | string | 终止、退出或撤销必填 |
| `created_by` | UUID | 操作人 |
| `created_at` | datetime | 操作时间 |
| `idempotency_key` | string | 唯一 |

上游退出时若仍有有效终端合同则拒绝；撤销事件不得删除原事件。

`effective_date` 统一表示新状态开始的第一天，与资产单元拆合的生效日语义一致。终端终止时合同最后有效日为 `effective_date` 前一日；`effective_date` 必须晚于合同 `start_date`，否则整个请求覆盖不到任何有效期间并失败关闭；到期后补登自然到期事实（`effective_date` 晚于 `end_date`）合法，此时覆盖截止无实际变化。同一合同存在未撤销的 `terminated` 事件时再次终止失败关闭；撤销后可重新终止。

撤销终止是纠错事实：原 `terminated` 事件自始有误。撤销请求必须显式携带目标事件 ID；目标不存在、不属于该合同或已被撤销时失败关闭。提交撤销在同一事务把被该终止截止的覆盖行（`effective_to` 等于该终止生效日前一日的行）恢复到合同 `end_date`——创建时覆盖 `effective_to` 恒等于合同 `end_date` 且除终止截止外无其他变更者，故恢复精确。存在指向后继合同的 `renewed` 事件，或其他合同在同单元 `[终止生效日, 合同 end_date]` 有覆盖时，撤销失败关闭：该期间已不属于本合同可主张的范围。撤销立即作用于覆盖数据（排斥约束即刻重新占住区间），状态派生仍按事件日期重放；撤销自身的 `effective_date` 为合同恢复在册首日，不约束与原终止生效日的先后。

上游退出与终端终止同一口径：`effective_date` 为新状态首日（上游合同不再有效的第一天），最后有效日为前一日；`effective_date` 不晚于 `start_date` 失败关闭；同一合同存在未撤销 `exited` 事件时再次退出失败关闭。退出前必须显式处理有效终端合同——按退出生效日重放终端生命周期事件后仍为 `active` / `expiring` 的终端合同阻断退出，阻断检查不做 Party 范围过滤（操作者看不到的有效终端合同同样阻断）。退出提交在同一事务把仍延伸到生效日之后的 `UpstreamContractAssetUnit` 覆盖行截止到前一日；退出撤销与终止撤销同构（显式目标、续签后继或其他上游合同在同单元 `[退出生效日, 合同 end_date]` 覆盖阻断、被截止覆盖行恢复到 `end_date`、撤销后可再退出）。

续签只创建后继合同，不修改旧合同期限或覆盖。各方、类型/模式与覆盖单元由前驱带出：请求只提交后继的已签条款（编号、期限、租金阶段、押金与扫描件），终端续签可显式指定新上游——上游已先行续签时必须指定，旧上游覆盖不到新起点会被既有校验拒绝。后继合同的起租日必须晚于前驱全部覆盖的截止日（含 NULL 视为违规），防止后继覆盖与前驱覆盖重叠。同一合同存在未撤销的 `renewed` 事件时再次续签失败关闭（`CONTRACT_ALREADY_RENEWED`）；后继合同、逐单元覆盖、租金阶段、扫描件绑定与 `renewed` 事件在同一事务提交，幂等经持久写回执回放，回放路径不重复追加事件。`renewed` 事件的撤销（撤销后允许再次续签）在状态派生与唯一后继判定中已被支持——被 `reversed` 指向的 `renewed` 事件不再阻断续签——但独立撤销端点保留给出现真实需要时实现；已知幂等边界：续签回放从当前前驱覆盖重建请求指纹，若前驱覆盖在其后已被终止/退出截断，同键重试会以 `IDEMPOTENCY_CONFLICT` 失败关闭而非回放（换键重试即可，不产生错误数据）。

### 4.16 RentLedgerEntry

| 字段 | 类型 | 约束 |
|---|---|---|
| `id` | UUID | 主键 |
| `entry_type` | enum | `upstream_payable` / `terminal_receivable` / `owner_receipt_expected` |
| `contract_id` | UUID | 对应上游或终端合同 |
| `period` | year-month | 账期 |
| `due_date` | date | 到期日 |
| `due_amount` | decimal | 本期义务金额 |
| `currency` | string | 固定 `CNY` |
| `locked_source` | object | 生成时合同、租金阶段和主体快照 |
| `version` | integer | 乐观锁版本 |

派生字段：`effective_paid_amount`、`remaining_amount`、`status`。`status` 为 `upcoming`、`unpaid`、`partial`、`paid`、`overdue`，由到期日和有效付款记录派生。

### 4.17 RentPaymentRecord

| 字段 | 类型 | 约束 |
|---|---|---|
| `id` | UUID | 主键 |
| `ledger_entry_id` | UUID | 对应租金义务 |
| `record_type` | enum | `payment` / `receipt` / `owner_reported_receipt` / `reversal` |
| `amount` | decimal | 正向记录大于 0；撤销引用原记录 |
| `occurred_on` | date | 外部实际发生日期 |
| `document_id` | UUID? | 可选凭证 |
| `reverses_record_id` | UUID? | 撤销时必填，且一笔记录只能有效撤销一次 |
| `reason` | string? | 撤销时必填 |
| `created_by` / `created_at` | UUID / datetime | 操作审计 |
| `idempotency_key` | string | 唯一 |

有效金额为未被有效撤销的正向记录合计。不得直接更新或删除正向记录。

### 4.18 DepositLedgerEntry

| 字段 | 类型 | 约束 |
|---|---|---|
| `id` | UUID | 主键 |
| `contract_kind` | enum | `upstream` / `terminal` |
| `contract_id` | UUID | 对应合同 |
| `direction` | enum | `receivable` / `refundable` / `recoverable` |
| `collector` | enum | `operator` / `owner` |
| `agreed_amount` | decimal | 约定金额 |
| `effective_amount` | decimal | 从追加收退记录派生 |
| `status` | enum | 派生：`receivable_uncollected` / `refundable_unreturned` / `recoverable_unreceived` / `settled` |

### 4.19 ManagementFeeStatement

| 字段 | 类型 | 约束 |
|---|---|---|
| `id` | UUID | 主键 |
| `owner_party_id` | UUID | 产权方 |
| `upstream_contract_id` | UUID | 委托管理协议 |
| `period` | year-month | 每产权方每月唯一有效版本 |
| `statement_number` | string | 唯一编号 |
| `fee_rate` | decimal | 确认时协议比例快照 |
| `base_amount` | decimal | 纳入行的产权方实际到账合计 |
| `fee_amount` | decimal | `base_amount × fee_rate`，按金额规则舍入 |
| `status` | enum | `collecting` / `pending_stamp` / `confirmed` / `superseded` |
| `stamped_document_id` | UUID? | `confirmed` 必填 |
| `confirmed_at` / `confirmed_by` | datetime? / UUID? | 确认审计 |
| `successor_statement_id` | UUID? | 更正时指向后继单 |
| `version` | integer | 乐观锁版本 |

### 4.20 ManagementFeeStatementLine

| 字段 | 类型 | 约束 |
|---|---|---|
| `id` | UUID | 主键 |
| `statement_id` | UUID | 对账单 |
| `terminal_contract_id` | UUID | 直签终端合同 |
| `asset_unit_ids` | UUID[] | 相关资产单元快照 |
| `tenant_name_snapshot` | string | 租户名称快照 |
| `rent_period` | year-month | 租金所属期 |
| `scheduled_rent` | decimal | 应收月租金 |
| `owner_received_amount` | decimal | 产权方实际到账金额 |
| `received_on` | date | 产权方报告日期 |
| `fee_rate` | decimal | 行级比例快照 |
| `fee_amount` | decimal | 行级费用金额 |
| `deferred` | boolean | 月末未收时顺延，不计入本单基数 |

确认后的行不可修改；更正生成后继对账单。

### 4.21 AssessmentScopeVersion

| 字段 | 类型 | 约束 |
|---|---|---|
| `id` | UUID | 主键 |
| `year` | integer | 考核年度 |
| `version_number` | integer | 同年度递增唯一 |
| `status` | enum | `draft` / `active` / `superseded` |
| `effective_from_period` | year-month | 首个适用报送月 |
| `based_on_version_id` | UUID? | 草稿来源版本 |
| `created_by` / `created_at` | UUID / datetime | 创建审计 |
| `activated_by` / `activated_at` | UUID? / datetime? | 保存生效审计 |
| `version` | integer | 乐观锁版本 |

### 4.22 AssessmentScopeItem

| 字段 | 类型 | 约束 |
|---|---|---|
| `scope_version_id` | UUID | 联合唯一的一部分 |
| `asset_unit_id` | UUID | 联合唯一的一部分 |
| `included` | boolean | 是否纳入 |
| `exclusion_reason` | string? | `included=false` 时必填 |
| `unit_snapshot` | object | 保存时名称、项目、面积和经营性质快照 |

### 4.23 MonthlyOccupancyReport

| 字段 | 类型 | 约束 |
|---|---|---|
| `id` | UUID | 主键 |
| `period` | year-month | 月度唯一活动报送链 |
| `status` | enum | `draft` / `submitted` / `withdrawn` |
| `scope_version_id` | UUID | 提交时锁定考核范围版本 |
| `change_note` | string? | 有较上月变动时提交必填 |
| `project_count` | integer | 快照汇总 |
| `operating_project_count` | integer | 快照汇总 |
| `non_operating_project_count` | integer | 快照汇总 |
| `unit_count` | integer | 纳入宗数 |
| `rented_unit_count` | integer | 已出租宗数 |
| `occupancy_rate` | decimal | 宗数出租率 |
| `land_area` | decimal | 纳入范围土地面积合计 |
| `building_area` | decimal | 纳入范围建筑面积合计 |
| `rentable_area` | decimal | 经营性可出租面积合计 |
| `rented_area` | decimal | 经营性已出租面积合计 |
| `submitted_by` / `submitted_at` | UUID? / datetime? | 提交审计 |
| `withdrawn_by` / `withdrawn_at` | UUID? / datetime? | 撤回审计 |
| `withdraw_reason` | string? | 撤回必填 |
| `predecessor_report_id` | UUID? | 撤回后重报链 |
| `version` | integer | 乐观锁版本 |

`submitted` 快照不可更新。撤回将其标为 `withdrawn` 并生成新的草稿，原行保留。

### 4.24 MonthlyOccupancyReportLine

| 字段 | 类型 | 约束 |
|---|---|---|
| `report_id` | UUID | 报送快照 |
| `asset_unit_id` | UUID | 资产单元稳定身份 |
| `owner_name_snapshot` | string | 产权方简称快照 |
| `usage_type_snapshot` | string | 业态快照 |
| `project_name_snapshot` | string | 项目名称快照 |
| `address_snapshot` | string | 地址快照 |
| `land_area` | decimal | 本行土地面积 |
| `rentable_area` | decimal | 本行经营性可出租面积 |
| `rented_area` | decimal | 本行经营性已出租面积 |
| `unit_count` | integer | 固定 `1` |
| `rented_unit_count` | integer | `0` / `1` |
| `rental_status` | enum | `rented` / `vacant` / `non_rentable` |
| `terminal_contract_ids` | UUID[] | 月末有效终端合同快照 |

### 4.25 ArchiveDocument

| 字段 | 类型 | 约束 |
|---|---|---|
| `id` | UUID | 主键 |
| `document_type` | enum | `property_certificate` / `upstream_contract` / `supplement` / `terminal_contract` / `handover` / `management_fee_statement` / `payment_voucher` |
| `target_type` | enum | 对应业务对象类型 |
| `target_id` | UUID | 对应业务对象 |
| `file_name` | string | 原文件名 |
| `content_type` | string | 允许的文件类型 |
| `content_hash` | string | 内容哈希，用于同对象去重 |
| `storage_key` | string | 私有存储引用 |
| `document_version` | integer | 同目标同类型递增 |
| `replaces_document_id` | UUID? | 替换链 |
| `uploaded_by` / `uploaded_at` | UUID / datetime | 上传审计 |

### 4.26 ContractIntakeSession

| 字段 | 类型 | 约束 |
|---|---|---|
| `id` | UUID | 主键 |
| `document_id` | UUID | 已上传盖章扫描件 |
| `contract_type` | enum | `upstream_lease` / `management_agreement` / `terminal` |
| `status` | enum | `uploaded` / `extracting` / `ready_for_review` / `confirmed` / `cancelled` / `failed` |
| `candidate_fields` | object | OCR/模型候选，不是业务事实 |
| `confirmed_fields` | object? | 人工确认后的输入 |
| `expires_at` | datetime | 临时会话失效时间 |

候选值不得自动创建 Party、资产单元或合同；确认后才调用正式合同写入。

### 4.27 ImportBatch

| 字段 | 类型 | 约束 |
|---|---|---|
| `id` | UUID | 主键 |
| `mode` | enum | `create` / `update` |
| `status` | enum | `uploaded` / `validating` / `invalid` / `ready` / `committed` / `reverted` |
| `file_document_id` | UUID | 原始导入文件 |
| `template_version` | string | 模板版本 |
| `row_count` | integer | 总行数 |
| `valid_count` | integer | 通过数 |
| `error_count` | integer | 错误数 |
| `warning_count` | integer | 提醒数 |
| `proposal_hash` | string | 规范化差异哈希 |
| `committed_at` / `committed_by` | datetime? / UUID? | 提交审计 |
| `reverted_at` / `reverted_by` | datetime? / UUID? | 撤销审计 |
| `revert_reason` | string? | 撤销必填 |
| `idempotency_key` | string | 提交时唯一 |
| `version` | integer | 乐观锁版本 |

### 4.28 ImportBatchChange

| 字段 | 类型 | 约束 |
|---|---|---|
| `id` | UUID | 主键 |
| `batch_id` | UUID | 导入批次 |
| `sheet_name` / `row_number` | string / integer | 来源定位 |
| `target_type` | enum | `asset_unit` / `upstream_contract` / `terminal_contract` |
| `target_key` | string | 单元编号或合同号 |
| `field_name` | string | 变更字段 |
| `old_value` / `new_value` | JSON | 现值和新值 |
| `selected` | boolean | 用户是否纳入提交 |
| `severity` | enum | `change` / `warning` / `error` |
| `effect_summary` | string | 业务可读影响说明 |

`error` 存在时批次不可提交。更新模式不创建未匹配对象；空白单元格不产生变更；派生字段产生 warning 并忽略。

### 4.29 BusinessChangeEvent

| 字段 | 类型 | 约束 |
|---|---|---|
| `id` | UUID | 主键 |
| `target_type` / `target_id` | enum / UUID | 业务对象 |
| `action` | string | 稳定动作码 |
| `before` / `after` | JSON | 前后值；敏感字段脱敏 |
| `reason` | string? | 撤销、退出、终止和报送撤回必填 |
| `actor_id` / `occurred_at` | UUID / datetime | 审计主体和时间 |
| `correlation_id` | string | 串联同一业务动作 |

### 4.30 MonthlyWorkItem

| 字段 | 类型 | 约束 |
|---|---|---|
| `item_type` | enum | `upstream_rent` / `terminal_rent` / `management_fee` / `occupancy_report` / `expired_upstream` / `expiring_contract` / `archive_gap` / `deposit` / `new_unit_scope` |
| `target_type` / `target_id` | enum / UUID | 深链目标 |
| `period` | year-month | 工作期 |
| `due_date` | date? | 无固定截止日事项为空 |
| `status` | enum | 派生：`pending` / `partial` / `completed` / `overdue` |
| `amount` | decimal? | 涉及金额时的待处理金额 |
| `days_overdue` | integer? | 逾期天数 |

该对象不持久化为可编辑待办；完成数只统计有截止日的四类月度事项。

### 4.31 AssetContractWriteReceipt

| 字段 | 类型 | 约束 |
|---|---|---|
| `id` | UUID | 主键 |
| `actor_id` | UUID | 发起确认的用户 |
| `command_kind` | enum | `create_upstream` / `create_terminal` |
| `idempotency_key` | string | 与 `actor_id` 联合唯一 |
| `request_fingerprint` | string | 规范化确认请求的 SHA-256 |
| `result_data` | object | 首次成功响应快照 |
| `created_at` | datetime | 首次成功时间 |

回执与合同、资产单元覆盖及租金阶段在同一事务写入。同一操作者以同键重试同一规范化请求时返回首次响应；同键改写合同条款、覆盖单元或命令类型时返回 `IDEMPOTENCY_CONFLICT`。回执是命令可靠性事实，不作为合同业务状态或审计事件的替代。

## 5. 状态机

### 5.1 上游合同

```text
scheduled -> active -> expiring -> expired_pending_action
                              \-> exited
active/expiring/expired_pending_action -> historical（存在后继且旧版本只读）
```

- `expiring`：剩余 180 天以内；90 天以内使用高风险提示。
- `expired_pending_action`：结束日已过且没有有效续签或退出事件。
- `exited`：无有效终端合同且已追加退出事件。

### 5.2 终端合同

```text
scheduled -> active -> expiring -> ended -> historical
                    \-> ended（提前/协商终止事件）
```

终止事件包含类型、退租日期、房屋交接和押金结算。结束后合同只读；撤销终止追加反向事件。

### 5.3 租金义务

```text
upcoming -> unpaid -> partial -> paid
                \-> overdue
partial ----------------> overdue（过期且仍有余额）
paid --撤销登记--> partial/unpaid/overdue（按剩余金额与日期重算）
```

### 5.4 委托管理费对账

```text
collecting -> pending_stamp -> confirmed -> superseded
```

- `collecting`：产权方到账尚在登记，未收户可以顺延。
- `pending_stamp`：纳入基数已确定，等待双方盖章文件。
- `confirmed`：盖章文件存在且确认动作完成，金额锁定。
- 更正创建后继对账单，原单转 `superseded`，不覆盖原行。

### 5.5 考核范围

```text
draft -> active -> superseded
```

同一年度只能有一个对当前及未来报送有效的 `active` 版本；已报月份继续引用原版本。

### 5.6 月度报送

```text
draft -> submitted -> withdrawn -> new draft
```

`submitted` 和 `withdrawn` 均不可更新明细。撤回要求原因，并以 `predecessor_report_id` 连接新的草稿/后继快照。

### 5.7 导入批次

```text
uploaded -> validating -> invalid
                      \-> ready -> committed -> reverted
```

`invalid` 可通过重新上传产生新批次或新文件版本；`committed` 后仅在提交起七个自然日内、且没有依赖冲突时允许整批撤销。

## 6. 统计口径

### 6.1 时点

- 月度出租率时点为统计月最后一天 24:00 前的最后有效状态。
- 合同和单元采用自然日有效期；结束日当天仍有效。
- 页面“今天”与逾期天数使用业务时区自然日。

### 6.2 宗数

- 分母候选为统计时点有效、经营性且在管的资产单元。
- 实际分母为候选中被报送引用的考核范围版本标记 `included=true` 的单元。
- 年中新增单元在确认前不进入当年分母。
- `unit_count = count(asset_unit_id)`，禁止按项目、地址、产权证或合同去重。

### 6.3 已出租宗数

- 单元在统计时点存在有效终端合同则 `rented_unit_count=1`，否则为 `0`。
- 上游尚未录入不改变出租事实。
- 同一单元同一时点最多一份有效终端合同；违反时拒绝写入而不是在统计时去重。

### 6.4 出租率

```text
occupancy_rate = rented_unit_count / unit_count
```

分母为 0 时返回 `null` 而不是 `0%`。页面显示和报送文本保留两位小数，但内部计算保留定点精度。

### 6.5 面积

- 土地面积、建筑面积、可出租面积逐资产单元求和。
- 经营性已出租面积只汇总 `rented_unit_count=1` 的单元 `rentable_area`。
- 土地面积不因多个单元共享宗地而自动分摊；数据录入为 0 就按 0 汇总。

### 6.6 项目数

- 在管项目数为报送明细中非空 `project_id` 去重数。
- 经营性项目数为至少包含一个经营性纳入单元的项目去重数。
- 非经营性项目数同理；一个混合项目可以按报送口径只计一次，具体分类取项目内是否存在经营性纳入单元优先。

### 6.7 租金完成金额

```text
effective_paid_amount = sum(未被有效撤销的正向 RentPaymentRecord.amount)
remaining_amount = max(due_amount - effective_paid_amount, 0)
```

超额登记必须显式提示并默认拒绝；确有业务依据时需独立规则扩展，不静默把负余额带入下一期。

### 6.8 委托管理费

```text
line_fee = owner_received_amount × fee_rate
statement_fee = sum(line_fee)
```

按金额舍入规则先算行再求和。月末仍未收到的租金行标记顺延，不计入本期基数。`confirmed` 后不因合同、租户或比例主档变化而重算。

### 6.9 档案完成率

```text
completion_rate = existing_required_documents / required_documents
```

“应有”从产权证、有效合同、补充协议、交接事件和已确认对账期间派生；不适用项不进入分母。分母为 0 时返回 `null`。

### 6.10 本月进度

- 只统计有固定截止日的承租租金、终端租金、委托管理费对账和出租率报送。
- 随时处理区不计入完成进度。
- 完成数和总数按具体义务/对账单/报送任务计数，不按页面卡片计数。

## 7. Out of Scope 对象

以下对象不属于 v5 目标模型：租赁意向、报价、底价、空间锁定、出租授权快照、合同生效检查、外部审批记录、银行原始行、匹配候选、收付分配、发票、开票分摊、未分配预收、催收账户、催收案件、法务案件、产权方门户任务、领导利润指标。

旧表或旧代码存在不等于对象仍在范围内；迁移阶段必须选择删除、归档或一次性转换，禁止继续作为新功能依赖。
