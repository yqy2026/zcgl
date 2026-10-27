# API 契约

## 1. 文档定位

本文档定义资产运营 v5 的 API、权限、并发、幂等和错误契约。产品范围见 [`docs/prd.md`](../prd.md)，字段和状态口径见 [`docs/specs/domain-model.md`](domain-model.md)。

目标端点尚未落地时不得用旧 Asset、ContractGroup 或台账响应拼装第二套临时契约。迁移按照活跃 V1 计划一次切换。

## 2. 全局 API 规则

| 规则 | 契约 |
|---|---|
| 版本前缀 | 所有业务 API 使用 `/api/v1/*` |
| 认证 | HttpOnly Cookie 会话，支持刷新和退出 |
| 鉴权 | RBAC 动作权限与 ABAC 数据范围同时通过 |
| CSRF | 状态变更请求必须携带 CSRF token |
| 数据范围 | 业务查询统一使用 EffectivePartyScope；范围缺失或失效返回稳定 403，不返回成功空列表 |
| 金额与面积 | 响应使用十进制字符串；前端服务层统一转换，页面不得临时 `parseFloat` |
| 日期 | 日期为 `YYYY-MM-DD`，月份为 `YYYY-MM`，时间为带时区 ISO 8601 |
| 分页 | 列表使用 `page` / `page_size`；最大值由端点声明，不允许无限量列表 |
| 排序 | 只接受端点白名单字段；未知字段返回 422 |
| 搜索 | 服务端完成，并在返回前应用动作权限和 Party 范围 |
| 幂等 | 高后果写请求使用 `Idempotency-Key`；同键不同规范化请求返回 409 |
| 乐观锁 | 更新/提交携带 `expected_version`；版本漂移返回 409 |
| 删除 | 业务事实不提供物理删除；取消、撤销、终止、退出和替换均追加记录 |
| 操作审计 | 响应返回 `correlation_id`；失败返回稳定错误码和可报障错误编号 |

### 2.1 列表响应

```json
{
  "items": [],
  "page": 1,
  "page_size": 20,
  "total": 0
}
```

聚合页可返回分组数组，但不得同时存在另一套未分页的相同资源列表。

### 2.2 错误响应

```json
{
  "code": "STABLE_ERROR_CODE",
  "message": "业务可读说明",
  "details": {},
  "correlation_id": "..."
}
```

页面只使用 `code` 选择恢复动作，不能解析 `message` 路由逻辑。

## 3. 权限与范围

### 3.1 能力权限

| 权限 | 能力 |
|---|---|
| `asset_ops:read` | 本月、物业、合同、台账、报送、档案和导入记录只读 |
| `asset_ops:write` | 资产单元、合同、租金、押金、委托管理费对账（含盖章件上传与确认）、终止和退出维护 |
| `asset_ops:report` | 考核范围保存、报送提交和撤回 |
| `asset_ops:archive` | 档案上传、替换、下载和配对 |
| `asset_ops:import` | 模板下载、文件校验、批次提交和撤销 |

内建“资产管理岗”映射上述五类能力。平台角色不因为能进入系统管理页面而自动获得业务能力；`admin` / `system_admin` 的全局边界沿用平台规则。

### 3.2 EffectivePartyScope

常规端点不接受调用方手工传入 Party ID 列表。服务端按管理员全量、当前有效显式绑定、组织默认范围的固定优先级解析；显式绑定存在时不与组织范围合并。

| 情况 | 响应 |
|---|---|
| 有效范围 | 查询只返回范围内对象 |
| 无范围 | 403 `PARTY_SCOPE_MISSING` |
| 组织链失效 | 403 `PARTY_SCOPE_INVALID_ORGANIZATION` |
| 代表 Party 失效 | 403 `PARTY_SCOPE_INVALID_PARTY` |
| 当前绑定失效 | 403 `PARTY_SCOPE_INVALID_BINDING` |
| 对单对象无权 | 404 或 403 按端点防枚举策略声明；列表绝不返回占位行 |

### 3.3 四态响应约定

- **加载**：前端请求状态，不由 API 伪造。
- **空**：200 且 `items=[]`，代表有权但确实无数据。
- **无权限**：403 且稳定范围或动作权限错误码。
- **出错**：5xx 或网络失败，响应包含 `correlation_id`；已有旧数据时客户端继续展示并标记刷新失败。

## 4. 前端页面与深链

| 页面 | 路由 | 深链参数 | 权限 |
|---|---|---|---|
| 本月 | `/asset-operations/monthly` | `item_type`, `target_id` | `asset_ops:read` |
| 报送 | `/asset-operations/reporting` | `period`, `report_id`, `unit_id` | 读：`asset_ops:read`；写：`asset_ops:report` |
| 物业 | `/asset-operations/units` | `unit_id`, `filter`, `project_id` | 读/写 |
| 上游合同 | `/asset-operations/contracts/upstream` | `contract_id`, `terminal_contract_id` | 读/写 |
| 终端合同 | `/asset-operations/contracts/terminal` | `contract_id`, `filter` | 读/写 |
| 台账 | `/asset-operations/ledgers` | `ledger_type`, `entry_id`, `period` | 读/写 |
| 委托管理费对账单 | `/asset-operations/management-fees/:statement_id` | `from=monthly` | 读/写 |
| 档案 | `/asset-operations/archive` | `target_type`, `target_id`, `document_type` | 读/档案 |
| 数据导入 | `/asset-operations/imports` | `mode`, `batch_id` | 读/导入 |

选中行必须反映到 URL 查询参数，刷新和分享链接后恢复同一对象；筛选后目标不在结果中时清除深链并选择第一行，不保留不可见陈旧详情。

## 5. 端点契约

### 5.1 认证与范围诊断

| 能力 | 方法与路径 | 契约 |
|---|---|---|
| 登录 | `POST /api/v1/auth/login` | 建立会话；资产工作台不提供角色选择器 |
| 当前用户 | `GET /api/v1/auth/me` | 返回用户、业务能力和组织摘要 |
| 当前范围 | `GET /api/v1/auth/me/party-scope` | 返回来源、owner/manager Party、异常和下一时间边界 |
| 退出 | `POST /api/v1/auth/logout` | 销毁当前会话 |

用户、角色、组织、Party 和范围变更沿用平台端点；资产运营模块不新增第二套管理入口。

### 5.2 本月工作台

| 方法与路径 | 契约 |
|---|---|
| `GET /api/v1/asset-operations/monthly?period=YYYY-MM` | 返回日期、四类有截止日事项、随时处理事项、完成数和金额汇总 |

每条事项返回 `item_type`、`target_type`、`target_id`、`title`、`subtitle`、`due_date`、`status`、`amount`、`days_overdue` 和目标深链。工作台不提供通用“完成事项”写端点，事项完成从对应业务事实自动消失或折叠。

### 5.3 资产单元

| 能力 | 方法与路径 | 契约 |
|---|---|---|
| 列表 | `GET /api/v1/asset-units` | 分页返回派生租出状态行；支持 `filter`（本切片 `all`/`non_rentable`，`vacant_rentable` 等待租出批量派生与考核/证照联动切片）、`project_id`、`owner_party_id`、`usage_type`、`q` |
| 详情 | `GET /api/v1/asset-units/{unit_id}` | 返回基础信息、派生租出状态/已租面积/出租率与当前有效终端合同；考核/证照状态与时间轴待联动切片 |
| 更新基本信息 | `PATCH /api/v1/asset-units/{unit_id}` | 乐观锁必填；手工字段（名称/地址/用途/面积/在管期等），可租面积不得超建筑面积（422 `ASSET_UNIT_AREA_INVALID`），在管期变化与活跃终端覆盖冲突返回 `ASSET_UNIT_PERIOD_OVERLAP` |
| 更新空置备注 | `PUT /api/v1/asset-units/{unit_id}/vacancy-note` | 接受原因、预计起租和期望版本 |
| 拆分预览 | `POST /api/v1/asset-units/{unit_id}/split/preview` | 校验生效日、子单元编号、面积守恒和历史影响，返回 `preview_token` |
| 拆分提交 | `POST /api/v1/asset-units/{unit_id}/split` | 消费 token、原因、期望版本和幂等键，原子创建新单元及边界事件 |
| 合并预览 | `POST /api/v1/asset-units/merge/preview` | 接受源单元集合、生效日和结果编号/名称，校验归属、同一上游范围、期间、面积和合同冲突 |
| 合并提交 | `POST /api/v1/asset-units/merge` | 消费 token、原因、完整期望版本集合和幂等键 |

`filter` 白名单：`all`、`assessment_included`、`vacant_rentable`、`non_rentable`、`certificate_missing`。搜索覆盖地址、单元编号、当前租户和产权证号。

拆分预览请求包含 `effective_date` 和至少两个 `parts`；源单元 ID 只取自路径，请求体不得重复或覆盖；每个 part 只接受 `unit_code`、`name`、`land_area`、`building_area`、`rentable_area`。结果单元的 Project、产权方、地址、用途、取得方式、经营标记和经营备注由源单元继承，不允许客户端覆盖。结果编号在全局范围内不得与现有单元重复。

拆分预览响应返回规范化结果、三类面积的 source/result 合计、生效日前一日/生效日影响、宗数变化、warning、`versions`、不可解码的 `preview_token` 和 `expires_at`。拆分提交请求体只接受 `preview_token`、`reason`、`expected_version`，幂等键通过必填 `Idempotency-Key` 请求头传递；尚无成功回执时，提交路径中的源单元必须与 token 绑定目标一致，不一致返回 `PREVIEW_STALE`。提交成功原子截止源单元及其现有有效上游覆盖、创建结果单元与对应新覆盖、追加 `AssetUnitBoundaryChange` 和唯一源关系；源单元没有有效上游覆盖时仍可拆分。一个源单元只能被一次边界变更消费，重复预览或并发提交返回 `ASSET_UNIT_BOUNDARY_INVALID`。同一操作者的同键同请求返回首次结果并标记 `idempotent=true`；同键用于不同请求（包括改用其他源单元路径）返回 `IDEMPOTENCY_CONFLICT`。仅成功提交或确认并发请求已经成功时删除 token；校验失败和数据库版本冲突保留 token 供诊断或重试。

合并预览请求只接受 `source_unit_ids`（至少两个且不得重复）、`effective_date` 和 `result.unit_code/name`；服务端按 ID 排序规范化源集合并自动汇总土地、建筑和可出租面积，请求体不得提交结果面积或归属字段。源单元的 Project、产权方、地址、用途、取得方式和经营标记必须一致；其有效上游合同集合必须相同且非空，同一上游合同的未来覆盖截止边界也必须一致。任一源单元在生效日或之后仍有有效/待生效终端合同覆盖时返回 `ASSET_UNIT_PERIOD_OVERLAP`；存在晚于边界日才开始的上游覆盖时返回 `ASSET_UNIT_BOUNDARY_INVALID`，避免覆盖遗留在退役源单元。预览响应的 `versions` 必须覆盖全部规范化源 ID。合并提交请求只接受 `preview_token`、`reason`、与 token 源集合完全一致的 `expected_versions`，并通过必填 `Idempotency-Key` 请求头提交；缺少、多出或替换版本键返回 `PREVIEW_STALE`，任一版本漂移返回 `VERSION_CONFLICT`。提交按 ID 排序锁定全部源单元，在同一事务截止源单元及原有效上游覆盖，创建一个接续单元及每份上游合同的一条新覆盖，并追加一条边界事件和逐源唯一消费关系；恰在边界日开始的上游覆盖直接迁移到结果单元，不保留空有效期源关系。

所有新建或修改上游/终端合同覆盖的写服务必须先按 ID 排序锁定相关 `AssetUnit`，再写覆盖关系；边界提交使用同一锁协议，防止检查后插入覆盖的幻读。合同写服务未遵守该协议时不得进入 API 接线。

### 5.4 合同录入会话

| 能力 | 方法与路径 | 契约 |
|---|---|---|
| 上传 | `POST /api/v1/contract-intake-sessions` | 上传已签扫描件并选择合同类型，返回临时会话 |
| 读取 | `GET /api/v1/contract-intake-sessions/{session_id}` | 返回提取状态、候选字段、warning 和有效期 |
| 确认上游 | `POST /api/v1/contract-intake-sessions/{session_id}/confirm-upstream` | 人工确认全部字段后创建上游合同 |
| 确认终端 | `POST /api/v1/contract-intake-sessions/{session_id}/confirm-terminal` | 人工确认上游、覆盖单元、租户、条款后创建终端合同 |
| 取消 | `POST /api/v1/contract-intake-sessions/{session_id}/cancel` | 关闭临时会话，不创建业务对象 |

扫描件必填；当前会话同步完成上传校验后即可进入 `ready_for_review`，自动提取不可用时返回 `EXTRACTION_UNAVAILABLE` warning，但不阻止手工确认。会话状态存储依赖 Redis 且按操作者隔离；其他操作者读取同一 ID 返回 404。候选值不得自动创建 Party、资产单元或业务关系。确认请求不得提交或覆盖合同类型、`scan_document_id` 或 `renewed_from_id`：类型与扫描件只从会话读取，续签关系只能经对应合同的 `/renewals` 端点建立。确认成功时，扫描件在合同事务内以附件行锁校验仍归当前会话后改绑正式合同；同一扫描件不能被第二份合同消费，冲突时整笔回滚。取消未确认会话则删除附件元数据和私有文件。

上游/终端确认请求均强制携带 `Idempotency-Key`。确认服务先按资产单元 ID 排序获取共享 `AssetUnit` 写锁，再校验当前 Party 范围、扫描件、资产单元在管期间、上游覆盖和租金阶段，最后在同一事务写入合同、逐单元覆盖、租金阶段及成功回执。终端合同未选择上游时返回 `UPSTREAM_CONTRACT_MISSING` warning；已选择上游但租期越界时返回 `TERMINAL_TERM_EXCEEDS_UPSTREAM` warning，二者均不阻止已签事实登记。已选择上游时，合同模式、出租方及终端开始日的单元覆盖必须与上游一致；未选择上游时，直签出租方必须等于全部覆盖单元唯一产权方，转租出租方必须等于全部覆盖单元所属项目的唯一运营 Party。出租方缺失、多主体或关系不一致均返回 `ASSET_CONTRACT_COVERAGE_INVALID` 409。终端同期覆盖先在写锁内检查，并由 PostgreSQL 排斥约束兜底。相同操作者、相同幂等键和相同规范化请求返回首次响应且 `idempotent=true`；同键改写请求返回 `IDEMPOTENCY_CONFLICT`。

### 5.5 上游合同

| 能力 | 方法与路径 | 契约 |
|---|---|---|
| 列表 | `GET /api/v1/upstream-contracts` | 分页返回派生状态行；支持 `contract_type`、`owner_party_id`、`q` 搜索；到期区间与项目过滤待后续切片；续签链与 warning 按调用方范围派生，范围外的关联方按缺失处理 |
| 详情 | `GET /api/v1/upstream-contracts/{contract_id}` | 返回条款、逐单元覆盖、租金阶段、版本链（前驱/当前/后继）、关联终端合同、生命周期事件和派生状态 |
| 更新 | `PATCH /api/v1/upstream-contracts/{contract_id}` | 乐观锁必填；可编辑 `name`/`end_date`/付款字段/押金/`oa_reference`，`end_date` 变更同事务跟随仍等于旧值的覆盖行；不提供即不改，不可清空已选上游 |
| 登记续签 | `POST /api/v1/upstream-contracts/{contract_id}/renewals` | 携带后继已签条款（编号、期限、租金/比例、押金、扫描件及其会话 owner）与幂等键；各方、类型和覆盖单元由前驱带出，同事务创建后继并追加 `renewed` 事件；已有未撤销后继返回 409 `CONTRACT_ALREADY_RENEWED` |
| 退出预览 | `POST /api/v1/upstream-contracts/{contract_id}/exit/preview` | 返回逐单元覆盖截止（最后有效日为生效日前一日）、押金申报回显和 token；仍有有效终端合同返回 409 `ACTIVE_TERMINAL_CONTRACTS_BLOCK_EXIT` |
| 退出提交 | `POST /api/v1/upstream-contracts/{contract_id}/exit` | 携带 token、期望版本与幂等键，日期与原因由 token 绑定的提议携带；同事务截止覆盖行并追加事件 |
| 撤销退出 | `POST /api/v1/upstream-contracts/{contract_id}/exit-reversal` | 追加反向事件，原因必填；续签后继或他合同覆盖阻断 |

### 5.6 终端合同

| 能力 | 方法与路径 | 契约 |
|---|---|---|
| 列表 | `GET /api/v1/terminal-contracts` | 分页返回派生状态与风险行；支持 `contract_mode`、`upstream_contract_id`、`q` 搜索，以及台账类 `filter`：`rent_unpaid`（存在剩余金额大于 0 的已到期非 `void` 租金义务）、`deposit_unsettled`（存在非 `settled` 押金条目）；上游关系 warning 按调用方范围派生，范围外上游按缺失处理 |
| 详情 | `GET /api/v1/terminal-contracts/{contract_id}` | 返回覆盖单元、模式、上游、条款、租金阶段、版本链、生命周期事件、版本和派生风险 |
| 更新 | `PATCH /api/v1/terminal-contracts/{contract_id}` | 乐观锁必填；可编辑绑上游（不得清空，改绑重验类型/出租方/覆盖）、`end_date`、押金，响应重算风险；`end_date` 变更同事务跟随覆盖行，重叠 409 |
| 登记续签 | `POST /api/v1/terminal-contracts/{contract_id}/renewals` | 携带后继已签条款与幂等键；租户、出租方、模式和覆盖单元由前驱带出，可显式指定新上游（先续上游再续终端时必填）；已有未撤销后继返回 409 `CONTRACT_ALREADY_RENEWED` |
| 终止预览 | `POST /api/v1/terminal-contracts/{contract_id}/termination/preview` | 返回逐单元覆盖截止（最后有效日为生效日前一日）、押金与交接申报回显、warning 和 token；已终止合同返回 409 |
| 终止提交 | `POST /api/v1/terminal-contracts/{contract_id}/termination` | 携带 token、期望版本与幂等键，类型/日期/交接/押金/原因由 token 绑定的提议携带；同事务截止覆盖行并追加事件 |
| 撤销终止 | `POST /api/v1/terminal-contracts/{contract_id}/termination-reversal` | 追加反向事件，原因必填；存在后继事实时失败关闭 |

上游缺失和租期越界返回 warning，不阻止登记；同一资产单元同日终端合同重叠返回 409。

### 5.7 租金台账与登记

| 能力 | 方法与路径 | 契约 |
|---|---|---|
| 台账矩阵 | `GET /api/v1/rent-ledgers?ledger_type=&year=` | 返回合同/物业行、1–12 月单元格、合计和当前月 |
| 条目详情 | `GET /api/v1/rent-ledger-entries/{entry_id}` | 返回来源条款、义务、有效登记、撤销链和操作人 |
| 登记付款/到账 | `POST /api/v1/rent-ledger-entries/{entry_id}/records` | 接受记录类型、金额、日期、可选凭证、期望版本和幂等键 |
| 撤销登记 | `POST /api/v1/rent-payment-records/{record_id}/reversal` | 原记录不可更新；原因必填，返回重算状态 |
| 手工义务 | `POST /api/v1/rent-ledger-entries` | 仅限 `custom` 账期的合同阶段；接受合同、账期、到期日、金额、依据说明（必填）和幂等键 |

金额默认等于剩余义务但允许减少形成部分完成。超出剩余金额默认返回 409 `PAYMENT_AMOUNT_EXCEEDS_REMAINING`。记录类型与义务类型不匹配返回 422 `RENT_RECORD_TYPE_MISMATCH`；对 `void` 义务登记返回 409 `RENT_LEDGER_ENTRY_VOIDED`；非 `custom` 账期创建手工义务返回 409 `RENT_LEDGER_MANUAL_ENTRY_NOT_ALLOWED`。

义务由合同确认、续签、期限或租金阶段更新、终止/退出及其撤销在同一事务内重建，不提供生成或重算端点；派生字段（`status`、`effective_paid_amount`、`remaining_amount`）不可写。

### 5.8 押金

| 能力 | 方法与路径 | 契约 |
|---|---|---|
| 待处理列表 | `GET /api/v1/deposits?status=` | 支持三类待处理状态和合同/主体/项目筛选 |
| 详情 | `GET /api/v1/deposits/{deposit_id}` | 返回约定、收取方、已处理金额和记录链 |
| 登记处理 | `POST /api/v1/deposits/{deposit_id}/records` | 登记收取、退还或收回；金额、日期、凭证和幂等键 |
| 撤销处理 | `POST /api/v1/deposit-records/{record_id}/reversal` | 原记录保留，原因必填 |

直签终端合同由产权方收取押金，本系统只登记产权方报告，不提供抵扣操作。押金条目由合同确认与生命周期事件生成，不提供手工创建端点。记录类型与押金方向或收取方不匹配返回 422 `DEPOSIT_RECORD_TYPE_MISMATCH`；正向登记超出未处理金额返回 409 `DEPOSIT_AMOUNT_EXCEEDS_REMAINING`；重复撤销返回 409 `DEPOSIT_RECORD_ALREADY_REVERSED`。

### 5.9 委托管理费

| 能力 | 方法与路径 | 契约 |
|---|---|---|
| 月度列表 | `GET /api/v1/management-fee-statements?period=` | 每产权方每月一张活动对账单；同一产权方多份委托管理协议合并到同一张单，行级标注协议 |
| 详情 | `GET /api/v1/management-fee-statements/{statement_id}` | 返回协议、到账行、顺延行、基数、比例、金额、状态和版本链 |
| 登记产权方到账 | `POST /api/v1/management-fee-statements/{statement_id}/owner-receipts` | 关联终端租金义务，登记金额和日期，重算试算；内部委托租金登记服务写入 `owner_reported_receipt`，与 `POST /rent-ledger-entries/{entry_id}/records` 共用同一事实、校验和幂等 |
| 标记顺延 | `POST /api/v1/management-fee-statements/{statement_id}/deferrals` | 用户逐户标记，不自动顺延；原因必填；部分到账时余额顺延至下月单 |
| 上传盖章件 | `POST /api/v1/management-fee-statements/{statement_id}/stamped-document` | 上传双方盖章版本，返回文档和期望金额 |
| 确认 | `POST /api/v1/management-fee-statements/{statement_id}/confirmation` | 期望版本、幂等键；缺盖章件返回 422 `STAMPED_DOCUMENT_REQUIRED`；仍有未足额且未顺延的行返回 409 `MANAGEMENT_FEE_LINES_UNRESOLVED`；锁定行、比例和金额 |
| 更正 | `POST /api/v1/management-fee-statements/{statement_id}/successor` | 创建后继对账单，原单只读 |

对 `confirmed` / `superseded` 单执行到账、顺延或上传盖章件返回 409 `MANAGEMENT_FEE_STATEMENT_LOCKED`。以上写端点均要求 `asset_ops:write`。

### 5.10 年度考核范围

| 能力 | 方法与路径 | 契约 |
|---|---|---|
| 当前版本 | `GET /api/v1/assessment-scopes/{year}` | 返回活动版本、逐宗决定和当前出租率 |
| 创建草稿 | `POST /api/v1/assessment-scopes/{year}/drafts` | 从当前版本或上一年度复制；覆盖前返回影响数 |
| 更新草稿 | `PUT /api/v1/assessment-scope-drafts/{draft_id}` | 批量纳入/排除；排除原因必填 |
| 影响预览 | `POST /api/v1/assessment-scope-drafts/{draft_id}/preview` | 返回纳入/排除宗数、未填原因、出租率变化和受影响月份 |
| 保存版本 | `POST /api/v1/assessment-scope-drafts/{draft_id}/commit` | 消费预览 token、期望版本和幂等键，生成新版本 |

年中新增单元默认不进入当年活动版本，必须通过草稿明确纳入或排除。

### 5.11 月度出租率报送

| 能力 | 方法与路径 | 契约 |
|---|---|---|
| 草稿 | `GET /api/v1/occupancy-reports/{period}/draft` | 实时返回汇总、逐宗明细、变动、门槛、差异和当前范围版本 |
| 保存变动说明 | `PUT /api/v1/occupancy-reports/{period}/draft-note` | 保存草稿说明，不生成快照 |
| 提交预览 | `POST /api/v1/occupancy-reports/{period}/submission-preview` | 返回必处理项、建议项、规范化说明和 `preview_token` |
| 提交 | `POST /api/v1/occupancy-reports/{period}/submissions` | 消费 token、期望范围版本和幂等键，原子生成报送与逐宗快照 |
| 历史快照 | `GET /api/v1/occupancy-reports/{report_id}` | 只读返回提交时数值、明细、范围版本和当前台账差异 |
| 撤回预览 | `POST /api/v1/occupancy-reports/{report_id}/withdrawal-preview` | 返回影响和新草稿生成规则 |
| 撤回 | `POST /api/v1/occupancy-reports/{report_id}/withdrawal` | 原因、token 和幂等键必填，原快照保留 |
| 导出 | `POST /api/v1/occupancy-reports/{report_id}/exports` | 生成对应快照的异步导出任务 |

有较上月变动但说明为空，或存在改变分母的必处理项时，提交预览返回 `can_submit=false`；提交端点再次校验，不能只依赖按钮置灰。

### 5.12 档案

| 能力 | 方法与路径 | 契约 |
|---|---|---|
| 完成率 | `GET /api/v1/archive/completion` | 返回四类已有/应有、完成率和缺漏数 |
| 矩阵 | `GET /api/v1/archive/matrix` | 按物业分组返回各类型已有/应有和详情深链 |
| 目标文件 | `GET /api/v1/archive/documents?target_type=&target_id=&document_type=` | 返回现行及历史版本 |
| 上传 | `POST /api/v1/archive/documents` | 单文件挂接目标；重复内容按目标和哈希拒绝 |
| 批量配对预览 | `POST /api/v1/archive/batch-matches/preview` | 多文件识别候选，只返回建议，不自动挂接 |
| 批量配对提交 | `POST /api/v1/archive/batch-matches` | 人工确认目标后原子或逐文件明确结果提交 |
| 替换 | `POST /api/v1/archive/documents/{document_id}/replacement` | 创建新版本，不覆盖旧文件 |
| 下载 | `GET /api/v1/archive/documents/{document_id}/content` | 鉴权后返回私有文件流 |

### 5.13 数据导入

| 能力 | 方法与路径 | 契约 |
|---|---|---|
| 下载新增模板 | `GET /api/v1/imports/templates/create` | 返回版本化三表模板 |
| 导出更新底稿 | `POST /api/v1/imports/templates/update` | 生成当前授权范围内的异步导出任务 |
| 上传批次 | `POST /api/v1/import-batches` | 接受 `mode` 和文件，返回批次 |
| 校验状态 | `GET /api/v1/import-batches/{batch_id}` | 返回表级数量、错误、提醒和差异摘要 |
| 差异列表 | `GET /api/v1/import-batches/{batch_id}/changes` | 分页返回现值、新值、影响和可选择状态 |
| 更新选择 | `PUT /api/v1/import-batches/{batch_id}/selection` | 更新模式下选择/取消变更，刷新提议哈希 |
| 提交预览 | `POST /api/v1/import-batches/{batch_id}/commit-preview` | 错误清零后返回影响、提议哈希和 token |
| 提交 | `POST /api/v1/import-batches/{batch_id}/commit` | 消费 token、期望版本、提议哈希和幂等键；整批事务 |
| 撤销预览 | `POST /api/v1/import-batches/{batch_id}/revert-preview` | 校验七日窗口和后继依赖 |
| 撤销 | `POST /api/v1/import-batches/{batch_id}/revert` | 原因、token 和幂等键必填，追加反向变更 |

新增模式遇到已存在编号时报错；更新模式遇到不存在编号时报错且绝不新增。空白不覆盖现值，派生字段忽略并提示。提交和撤销不得改变已提交报送快照。

### 5.14 变更记录

| 方法与路径 | 契约 |
|---|---|
| `GET /api/v1/business-change-events?target_type=&target_id=&period=` | 返回操作者、时间、动作、业务可读摘要、原因和关联对象 |

变更记录是审计读取，不提供创建、更新或删除端点；由业务服务在同一事务写入。

## 6. 预览—提交契约

拆分、合并、上游退出、终端终止、考核范围保存、报送提交/撤回和导入提交/撤销使用统一模式。涉及“今天”的生效日校验统一按 `Asia/Shanghai` 业务日计算，不以 UTC 日期代替：

1. 预览返回影响、阻断、warning、规范化提议、`preview_token`、`expires_at` 和相关版本。
2. token 绑定操作者、动作、目标、规范化提议、数据范围和版本，客户端不可解码。
3. 提交携带 token、单一 `expected_version` 或完整 `expected_versions` 集合、必要原因和 `Idempotency-Key`。
4. 操作者、权限、提议、范围或版本变化返回 409，要求重新预览。
5. 成功提交消费 token；相同幂等键同请求重试返回首次结果。

预览表示影响确认，不是审批流。

## 7. 稳定错误码

| HTTP | 错误码 | 场景 |
|---|---|---|
| 400 | `INVALID_PERIOD` | 月份或日期区间格式错误 |
| 403 | `ASSET_OPS_PERMISSION_DENIED` | 缺少动作权限 |
| 403 | `PARTY_SCOPE_MISSING` | 无有效业务范围 |
| 403 | `PARTY_SCOPE_INVALID_ORGANIZATION` | 组织链失效 |
| 403 | `PARTY_SCOPE_INVALID_PARTY` | 代表 Party 失效 |
| 403 | `PARTY_SCOPE_INVALID_BINDING` | 当前绑定失效 |
| 403 | `PARTY_SCOPE_INVALID_MODE` | 范围模式缺少对应主体轴 |
| 404 | `RESOURCE_NOT_FOUND` | 对象不存在或按防枚举策略隐藏 |
| 409 | `VERSION_CONFLICT` | 期望版本漂移 |
| 409 | `IDEMPOTENCY_CONFLICT` | 同幂等键对应不同请求 |
| 409 | `PREVIEW_STALE` | 预览 token 过期、已消费或相关事实变化 |
| 409 | `ASSET_UNIT_PERIOD_OVERLAP` | 资产单元边界变更跨越有效终端合同，或同期终端覆盖冲突 |
| 409 | `ASSET_UNIT_BOUNDARY_INVALID` | 拆分/合并数量或生效日边界无效 |
| 409 | `ASSET_UNIT_AREA_MISMATCH` | 拆分/合并面积不守恒 |
| 409 | `ASSET_UNIT_UPSTREAM_SCOPE_MISMATCH` | 合并源单元没有相同且非空的有效上游合同范围 |
| 409 | `ASSET_CONTRACT_COVERAGE_INVALID` | 合同覆盖超出资产单元在管期间，或所选上游在终端开始日不覆盖目标单元 |
| 409 | `CONTRACT_ALREADY_RENEWED` | 合同已存在未撤销的续签后继 |
| 409 | `ACTIVE_TERMINAL_CONTRACTS_BLOCK_EXIT` | 上游仍有有效终端合同时退出 |
| 409 | `PAYMENT_AMOUNT_EXCEEDS_REMAINING` | 登记金额超出剩余义务 |
| 409 | `PAYMENT_RECORD_ALREADY_REVERSED` | 重复撤销付款/到账记录 |
| 409 | `RENT_LEDGER_ENTRY_VOIDED` | 对已作废租金义务登记 |
| 409 | `RENT_LEDGER_MANUAL_ENTRY_NOT_ALLOWED` | 非 `custom` 账期创建手工义务 |
| 409 | `DEPOSIT_AMOUNT_EXCEEDS_REMAINING` | 押金登记金额超出未处理金额 |
| 409 | `DEPOSIT_RECORD_ALREADY_REVERSED` | 重复撤销押金记录 |
| 409 | `MANAGEMENT_FEE_STATEMENT_LOCKED` | 已确认或已被更正的对账单不可再修改 |
| 409 | `MANAGEMENT_FEE_LINES_UNRESOLVED` | 对账单仍有未足额且未顺延的行 |
| 409 | `REPORT_SUBMISSION_BLOCKED` | 报送必处理项未清零或变动说明缺失 |
| 409 | `REPORT_SCOPE_VERSION_STALE` | 提交时考核范围版本已变化 |
| 409 | `IMPORT_HAS_ERRORS` | 导入仍有错误 |
| 409 | `IMPORT_PROPOSAL_CHANGED` | 提交差异与预览哈希不一致 |
| 409 | `IMPORT_REVERT_WINDOW_EXPIRED` | 导入撤销窗口已过 |
| 409 | `IMPORT_REVERT_DEPENDENCY_CONFLICT` | 后继事实阻止整批撤销 |
| 409 | `SCAN_DOCUMENT_ALREADY_BOUND` | 已签扫描件已被其他合同消费或不再归当前录入会话 |
| 409 | `TERMINAL_CONTRACT_ALREADY_TERMINATED` | 终端合同已存在未撤销的终止事件，再次终止被拒绝 |
| 409 | `TERMINATION_REVERSAL_TARGET_INVALID` | 撤销目标不是该合同未撤销的终止事件 |
| 409 | `TERMINATION_REVERSAL_BLOCKED` | 已存在续签后继或其他合同覆盖，终止事件不可撤销 |
| 409 | `UPSTREAM_CONTRACT_ALREADY_EXITED` | 上游合同已存在未撤销的退出事件，再次退出被拒绝 |
| 409 | `EXIT_REVERSAL_TARGET_INVALID` | 撤销目标不是该合同未撤销的退出事件 |
| 409 | `EXIT_REVERSAL_BLOCKED` | 已存在续签后继或其他上游合同覆盖，退出事件不可撤销 |
| 422 | `EXCLUSION_REASON_REQUIRED` | 考核排除原因缺失 |
| 422 | `REVERSAL_REASON_REQUIRED` | 撤销原因缺失 |
| 422 | `DEFERRAL_REASON_REQUIRED` | 委托管理费顺延原因缺失 |
| 422 | `RENT_RECORD_TYPE_MISMATCH` | 付款/到账记录类型与义务类型不匹配 |
| 422 | `DEPOSIT_RECORD_TYPE_MISMATCH` | 押金记录类型与方向或收取方不匹配 |
| 422 | `STAMPED_DOCUMENT_REQUIRED` | 确认对账单缺双方盖章件 |
| 422 | `MANUAL_ENTRY_BASIS_REQUIRED` | 手工义务缺依据说明 |
| 422 | `SCAN_DOCUMENT_REQUIRED` | 合同确认缺已签扫描件 |
| 422 | `ASSET_UNIT_AREA_INVALID` | 可出租面积超过建筑面积 |
| 422 | `ASSET_UNIT_FIELD_NOT_EDITABLE` | 归属字段不可直接修改（走拆合） |
| 422 | `RENT_SCHEDULE_INVALID` | 租金阶段越出合同期限或互相重叠 |
| 422 | `DERIVED_FIELD_NOT_WRITABLE` | 请求试图写出租状态、合计等派生字段 |

以下是 warning，不作为错误码阻止合同登记：`UPSTREAM_CONTRACT_MISSING`、`TERMINAL_TERM_EXCEEDS_UPSTREAM`、`ARCHIVE_DOCUMENT_MISSING`。

## 8. Out of Scope API

不新增租赁意向、报价、底价、授权冻结、合同生效检查、外部审批、银行流水、匹配复核、发票、开票分摊、催收案件、产权方门户、领导利润分析或物业工单端点。旧端点存在时按迁移计划下线，不能继续被 v5 页面消费。

## 9. 维护规则

- 新增或修改端点时同步本文档和需求追踪矩阵。
- 字段、状态或统计变化先修改领域模型，再修改 API。
- 权限名称、路由元数据和后端动作必须一致。
- 错误码一旦公开只能通过显式迁移替换，不得靠文案变化改变客户端行为。
