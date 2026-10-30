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
| 台账 | `/asset-operations/ledgers` | `ledger_type`（`upstream_rent` / `terminal_rent` / `management_fee`）, `entry_id`, `period` | 读/写 |
| 委托管理费对账单 | `/asset-operations/management-fees/:statement_id` | `from=monthly` | 读/写 |
| 档案 | `/asset-operations/archive` | `target_type`, `target_id`, `document_type` | 读/档案 |
| 数据导入 | `/asset-operations/imports` | `mode`, `batch_id` | 读/导入 |

选中行必须反映到 URL 查询参数，刷新和分享链接后恢复同一对象；筛选后目标不在结果中时清除深链并选择第一行，不保留不可见陈旧详情。

## 5. 端点契约

### 5.1 认证与范围诊断

| 能力 | 方法与路径 | 契约 |
|---|---|---|
| 登录 | `POST /api/v1/auth/login` | 建立会话；资产工作台不提供角色选择器 |
| 过期密码更新 | `POST /api/v1/auth/expired-password` | 未登录时仅凭账号、当前密码与符合策略的新密码更新已过期凭据；校验账号启用/锁定、旧密码、强度和历史；沿用登录限流与失败审计；不创建完整登录会话，成功后重新登录 |
| 当前用户 | `GET /api/v1/auth/me` | 返回用户、业务能力和组织摘要 |
| 当前范围 | `GET /api/v1/auth/me/party-scope` | 返回来源、owner/manager Party、异常和下一时间边界 |
| 退出 | `POST /api/v1/auth/logout` | 销毁当前会话 |

用户、角色、组织、Party 和范围变更沿用平台端点；资产运营模块不新增第二套管理入口。

登录在当前密码校验通过但凭据过期时返回稳定 `PASSWORD_EXPIRED`，登录页展示更新入口。过期密码更新不允许绕过账号锁定或密码策略，不返回登录令牌；非过期账号继续使用已认证的个人资料改密流程。

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
| 确认上游 | `POST /api/v1/contract-intake-sessions/{session_id}/confirm-upstream` | 人工确认全部字段（承租合同含租金阶段）后创建上游合同 |
| 确认终端 | `POST /api/v1/contract-intake-sessions/{session_id}/confirm-terminal` | 人工确认上游、覆盖单元、租户、条款与租金阶段后创建终端合同 |
| 取消 | `POST /api/v1/contract-intake-sessions/{session_id}/cancel` | 关闭临时会话，不创建业务对象 |

扫描件必填；当前会话同步完成上传校验后即可进入 `ready_for_review`，自动提取不可用时返回 `EXTRACTION_UNAVAILABLE` warning，但不阻止手工确认。会话状态存储依赖 Redis 且按操作者隔离；其他操作者读取同一 ID 返回 404。候选值不得自动创建 Party、资产单元或业务关系。确认请求不得提交或覆盖合同类型、`scan_document_id` 或 `renewed_from_id`：类型与扫描件只从会话读取，续签关系只能经对应合同的 `/renewals` 端点建立。确认成功时，扫描件在合同事务内以附件行锁校验仍归当前会话后改绑正式合同；同一扫描件不能被第二份合同消费，冲突时整笔回滚。取消未确认会话则删除附件元数据和私有文件。

上游/终端确认请求均强制携带 `Idempotency-Key`。确认服务先按资产单元 ID 排序获取共享 `AssetUnit` 写锁，再校验当前 Party 范围、扫描件、资产单元在管期间、上游覆盖和租金阶段，最后在同一事务写入合同、逐单元覆盖、租金阶段及成功回执。终端合同未选择上游时返回 `UPSTREAM_CONTRACT_MISSING` warning；已选择上游但租期越界时返回 `TERMINAL_TERM_EXCEEDS_UPSTREAM` warning，二者均不阻止已签事实登记。已选择上游时，合同模式、出租方及终端开始日的单元覆盖必须与上游一致；未选择上游时，直签出租方必须等于全部覆盖单元唯一产权方，转租出租方必须等于全部覆盖单元所属项目的唯一运营 Party。出租方缺失、多主体或关系不一致均返回 `ASSET_CONTRACT_COVERAGE_INVALID` 409。终端同期覆盖先在写锁内检查，并由 PostgreSQL 排斥约束兜底。相同操作者、相同幂等键和相同规范化请求返回首次响应且 `idempotent=true`；同键改写请求返回 `IDEMPOTENCY_CONFLICT`。

### 5.5 上游合同

| 能力 | 方法与路径 | 契约 |
|---|---|---|
| 列表 | `GET /api/v1/upstream-contracts` | 分页返回派生状态行；支持 `contract_type`、`owner_party_id`、`q` 搜索；到期区间与项目过滤待后续切片；续签链与 warning 按调用方范围派生，范围外的关联方按缺失处理 |
| 详情 | `GET /api/v1/upstream-contracts/{contract_id}` | 返回条款、逐单元覆盖、租金阶段、版本链（前驱/当前/后继）、关联终端合同、生命周期事件和派生状态 |
| 更新 | `PATCH /api/v1/upstream-contracts/{contract_id}` | 乐观锁必填；可编辑 `name`、`end_date`、`management_fee_rate`（仅委托管理协议）、押金（委托管理协议只能为 0）和 `oa_reference`；合同级 `payment_cycle` / `payment_day` 确认后只读，付款方式以租金阶段为准；字段不适用于该合同类型返回 422 `CONTRACT_FIELD_NOT_APPLICABLE`；`end_date` 变更同事务跟随仍等于旧值的覆盖行并重排租金义务；不提供即不改 |
| 登记续签 | `POST /api/v1/upstream-contracts/{contract_id}/renewals` | 携带后继已签条款（编号、期限、租金/比例、押金、扫描件及其会话 owner）与幂等键；各方、类型和覆盖单元由前驱带出，同事务创建后继并追加 `renewed` 事件；已有未撤销后继返回 409 `CONTRACT_ALREADY_RENEWED` |
| 租金阶段更正预览 | `POST /api/v1/upstream-contracts/{contract_id}/rent-schedule-correction/preview` | 携带完整的新租金阶段列表和原因；返回新旧阶段对照、当月起及补录往月的义务新建 / 更新 / 作废 / 恢复数量、锁定不一致清单和 token；改动当前业务月首日之前已有的阶段内容返回 409 `RENT_SCHEDULE_HISTORY_IMMUTABLE`（往月中没有阶段覆盖的日期可以补录），阶段越出合同期限或重叠返回 422 `RENT_SCHEDULE_INVALID`，委托管理协议返回 422 `CONTRACT_FIELD_NOT_APPLICABLE`，已退出合同返回 409 `UPSTREAM_CONTRACT_ALREADY_EXITED` |
| 租金阶段更正提交 | `POST /api/v1/upstream-contracts/{contract_id}/rent-schedule-correction` | 携带 token、期望版本与幂等键；同事务追加新阶段、把被替换阶段标记为已更正（不物理删除）、重排当月起的未锁定义务和补录所在往月账期并写变更记录 |
| 退出预览 | `POST /api/v1/upstream-contracts/{contract_id}/exit/preview` | 返回逐单元覆盖截止（最后有效日为生效日前一日）、押金申报回显、租金义务影响、承租押金应收回金额和 token；仍有有效终端合同返回 409 `ACTIVE_TERMINAL_CONTRACTS_BLOCK_EXIT` |
| 退出提交 | `POST /api/v1/upstream-contracts/{contract_id}/exit` | 携带 token、期望版本与幂等键，日期与原因由 token 绑定的提议携带；同事务截止覆盖行、追加事件并重排租金义务 |
| 撤销退出 | `POST /api/v1/upstream-contracts/{contract_id}/exit-reversal` | 追加反向事件，原因必填；同事务恢复覆盖并重排租金义务；续签后继或他合同覆盖阻断 |

委托管理协议不约定保证金，也没有租金阶段：录入确认、续签和更新时押金必须为 0，录入确认和续签不得提交租金阶段，租金阶段更正不适用；否则返回 422 `CONTRACT_FIELD_NOT_APPLICABLE`。

### 5.6 终端合同

| 能力 | 方法与路径 | 契约 |
|---|---|---|
| 列表 | `GET /api/v1/terminal-contracts` | 分页返回派生状态与风险行；支持 `contract_mode`、`upstream_contract_id`、`q` 搜索，以及台账类 `filter`：`rent_unpaid`（转租：当前业务月及以前账期仍有剩余金额；直签：上月及以前账期产权方尚未报足；均不含 `void`）、`deposit_unsettled`（押金状态不是 `settled`）；上游关系 warning 按调用方范围派生，范围外上游按缺失处理 |
| 详情 | `GET /api/v1/terminal-contracts/{contract_id}` | 返回覆盖单元、模式、上游、条款、租金阶段、版本链、生命周期事件、版本和派生风险 |
| 更新 | `PATCH /api/v1/terminal-contracts/{contract_id}` | 乐观锁必填；可编辑绑上游（不得清空，改绑重验类型/出租方/覆盖）、`end_date`、押金，响应重算风险；`end_date` 变更同事务跟随覆盖行并重排租金义务，重叠 409 |
| 租金阶段更正预览 / 提交 | `POST /api/v1/terminal-contracts/{contract_id}/rent-schedule-correction/preview`、`POST /api/v1/terminal-contracts/{contract_id}/rent-schedule-correction` | 与上游合同同一契约；已终止合同返回 409 `TERMINAL_CONTRACT_ALREADY_TERMINATED` |
| 登记续签 | `POST /api/v1/terminal-contracts/{contract_id}/renewals` | 携带后继已签条款与幂等键；租户、出租方、模式和覆盖单元由前驱带出，可显式指定新上游（先续上游再续终端时必填）；已有未撤销后继返回 409 `CONTRACT_ALREADY_RENEWED` |
| 终止预览 | `POST /api/v1/terminal-contracts/{contract_id}/termination/preview` | 请求可携带押金抵扣方式（仅转租合同；缺省把账期首月不晚于当前业务月的未结租金按到期日从早到晚自动抵扣；可选不抵扣或给出抵扣明细）和补收免租金额与依据（仅提前终止的转租合同）；抵扣明细无效返回 409 `DEPOSIT_OFFSET_TARGET_INVALID`，不满足补收免租条件返回 409 `RENT_LEDGER_MANUAL_ENTRY_NOT_ALLOWED`；返回逐单元覆盖截止（最后有效日为生效日前一日）、押金与交接申报回显、租金义务影响、押金结算试算（已收、抵扣明细、补收免租、应退还租户或租户还需补缴）、warning 和 token；已终止合同返回 409 |
| 终止提交 | `POST /api/v1/terminal-contracts/{contract_id}/termination` | 携带 token、期望版本与幂等键，类型/日期/交接/押金/抵扣明细/补收免租/原因由 token 绑定的提议携带；同事务截止覆盖行、追加事件、重排租金义务、创建补收免租义务并写入押金抵扣 |
| 撤销终止 | `POST /api/v1/terminal-contracts/{contract_id}/termination-reversal` | 追加反向事件，原因必填；同事务先成对撤销随该终止写入的押金抵扣，再作废未锁定的补收免租义务，并恢复覆盖、重排租金义务；存在后继事实时失败关闭 |

上游缺失和租期越界返回 warning，不阻止登记；同一资产单元同日终端合同重叠返回 409。

终止请求的押金字段为 `deposit_offset_mode`（`auto` / `none` / `manual`，默认 `auto`）、`deposit_offsets`（`ledger_entry_id/amount` 明细）、`clawback_amount` 和 `clawback_basis`。预览 `deposit_settlement` 返回押金版本、持有金额、候选与规范化分配、`refundable_amount`（分配后待退押金）和 `additional_due_amount`（候选未结租金合计加补收金额减本次分配，最低为 0；补收免租恒计入，不因生效月在当月之后而被月份门槛排除，也不因此变为可抵扣候选）。尚未落库的租金及本次补收候选使用本次预览内稳定的标识，客户端在终止提议中原样回传；它们不能用于独立的押金抵租端点，提交时才解析成实际租金条目。

### 5.7 租金台账与登记

| 能力 | 方法与路径 | 契约 |
|---|---|---|
| 台账矩阵 | `GET /api/v1/rent-ledgers?ledger_type=&year=` | `ledger_type` 白名单：`upstream_rent`（承租租金应付）、`terminal_rent`（转租应收与直签产权方应报到账）、`management_fee`（按对账单状态）；返回合同行、1–12 月单元格（按账期首月归列，标注非付款月与免租期）、合计和当前月 |
| 条目详情 | `GET /api/v1/rent-ledger-entries/{entry_id}` | 返回来源条款、账期起止、义务、有效登记、撤销链、操作人和 warning（如 `RENT_LEDGER_PLAN_MISMATCH`） |
| 登记付款/到账 | `POST /api/v1/rent-ledger-entries/{entry_id}/records` | 接受记录类型、金额、日期、可选凭证、期望版本和幂等键 |
| 撤销登记 | `POST /api/v1/rent-payment-records/{record_id}/reversal` | 原记录不可更新；原因必填；同一事务重排该合同义务，返回重算状态 |
| 手工义务 | `POST /api/v1/rent-ledger-entries` | `origin=manual` 仅限 `custom` 账期段；`origin=clawback` 仅限有未撤销提前终止的转租终端合同（补收免租优惠，终止时未填可在此补登），账期与到期日固定为终止生效日、请求不另填；接受合同、账期起止（`manual`）、到期日（`manual`）、金额、依据说明（必填）和幂等键 |
| 作废手工义务 | `POST /api/v1/rent-ledger-entries/{entry_id}/void` | 仅限无有效登记的 `manual` / `clawback` 义务；原因、期望版本和幂等键 |

金额默认等于剩余义务但允许减少形成部分完成。超出剩余金额默认返回 409 `PAYMENT_AMOUNT_EXCEEDS_REMAINING`。记录类型与义务类型不匹配返回 422 `RENT_RECORD_TYPE_MISMATCH`（`deposit_offset` 只能经押金抵扣创建）；对 `void` 义务登记返回 409 `RENT_LEDGER_ENTRY_VOIDED`；手工义务不满足上述条件或作废 `generated` 义务返回 409 `RENT_LEDGER_MANUAL_ENTRY_NOT_ALLOWED`；作废有有效登记的手工义务返回 409 `RENT_LEDGER_ENTRY_LOCKED`；撤销已被确认对账单计入的产权方到账返回 409 `MANAGEMENT_FEE_STATEMENT_LOCKED`。

PR-A 矩阵响应为 `ledger_type` / `year` / `current_month` / `rows` 和三项金额合计；每合同行包含 12 个 `months`、warning 与应付/应收、有效登记、剩余金额合计。月份内的 `entries` 保留原始登记与撤销链，作废义务不参与合计。合同详情 `rent_summary` 返回本月金额、未结余额、已结账期数、下一到期日与条目；生命周期预览 `rent_impact` 返回新建/更新/作废/恢复数量及锁定不一致条目，提交指纹同时绑定义务与登记事实。PR-C 的 `management_fee` 分支返回 `ledger_type` / `year` / `current_month` / `rows` / `total_confirmed_amount`；每行按产权方包含 `owner_party_id`、`owner_name`、12 个 `months` 及 `total_confirmed_amount`，每月包含 `month`、可空 `statement_id`、`status` 与可空 `fee_amount`。有单状态为 `collecting` / `pending_stamp` / `confirmed`，无单的未来月为 `upcoming`、其他月为 `missing`；更正历史不占活动月份。全年及行合计只累加已确认金额，Decimal 精确计算，其他状态金额为试算。非当前年 `current_month=0`，按整单产权方范围读取，管理方不可读取部分协议拼出的整单。

`generated` 义务由合同确认、续签、期限更新、租金阶段更正、终止 / 退出及其撤销和登记撤销在同一事务内重排（规则见领域模型 §4.14、§4.16），不提供生成或重算端点；派生字段（`status`、`effective_paid_amount`、`remaining_amount`）不可写。终端终止和上游退出的预览在原有影响之外，返回租金义务的新建 / 更新 / 作废 / 恢复数量、锁定不一致清单和押金状态变化；预览 token 同时绑定受影响义务的版本。

### 5.8 押金

| 能力 | 方法与路径 | 契约 |
|---|---|---|
| 待处理列表 | `GET /api/v1/deposits?status=` | `status`：`receivable_uncollected`（应收未收）、`payable_unpaid`（应付未付）、`refundable_unreturned`（应退未退）、`recoverable_unreceived`（应收回）；缺省返回这四类，`settled` 须显式指定；支持合同、主体、项目筛选 |
| 详情 | `GET /api/v1/deposits/{deposit_id}` | 返回约定、收取方、持有余额、续签转入 / 转出、待处理方向与金额和记录链 |
| 登记处理 | `POST /api/v1/deposits/{deposit_id}/records` | 记录类型、金额、日期、可选凭证、期望版本和幂等键；`deduct` 必须指定被抵扣的终端租金义务；`forfeit`（押金扣除）必须填写原因 |
| 撤销处理 | `POST /api/v1/deposit-records/{record_id}/reversal` | 原记录保留，原因必填；撤销 `deduct` 时同一事务撤销配对的租金抵扣记录 |

押金条目随承租合同和终端合同确认（含续签后继）创建，每份合同一条，不提供手工创建端点；委托管理协议不约定保证金，没有押金条目；约定、持有余额和状态均派生（领域模型 §4.18）。直签终端合同由产权方收取押金，本系统只登记产权方报告，不提供抵扣操作；承租合同押金由本公司付给产权方，登记支付与收回。续签时押金整体转入后继合同，前驱显示已转入，不产生应退或应收回。转租押金只在合同结束阶段（已登记终止或已到期）可抵扣欠租，终止时默认自动抵扣截至当月的欠租（见 §5.6）。押金中不退还的部分（赔偿、违约金或产权方扣留）登记为 `forfeit`：只在合同结束阶段可用，原因必填，不生成租金记录；转租由本公司扣，直签按产权方报告，承租合同由产权方扣。

列表接受 `contract_kind`、`contract_id`、`party_id`、`project_id` 以及 `page`（默认 1）和 `page_size`（默认 20，上限 200）；返回 `items/total/page/page_size`。详情另返回 `ended`、`read_only` 与 `offset_candidates`；候选仅为结束阶段、未续签转出的转租押金提供，包含本合同及有效续签祖先中当前数据范围可见的未作废、未结清租金（`id/contract_id/period_start/period_end/due_date/remaining_amount`），用于界面选择而不扩展写权限。列表不加载候选，候选返回空数组。登记写入使用请求头 `Idempotency-Key`；金额以 Decimal 契约传输。

记录类型与收取方不匹配返回 422 `DEPOSIT_RECORD_TYPE_MISMATCH`；收入超出待收 / 待付金额或支出超出持有余额返回 409 `DEPOSIT_AMOUNT_EXCEEDS_REMAINING`；向已续签合同的押金条目登记返回 409 `DEPOSIT_ENTRY_CARRIED_FORWARD`；合同仍在期内时抵扣或扣除返回 409 `DEPOSIT_OFFSET_NOT_ALLOWED`；扣除缺原因返回 422 `FORFEIT_REASON_REQUIRED`；抵扣目标不是本合同或其续签前驱未作废、仍有剩余金额的转租终端租金义务，或金额超出其剩余金额，返回 409 `DEPOSIT_OFFSET_TARGET_INVALID`；重复撤销返回 409 `DEPOSIT_RECORD_ALREADY_REVERSED`。

### 5.9 委托管理费

| 能力 | 方法与路径 | 契约 |
|---|---|---|
| 月度列表 | `GET /api/v1/management-fee-statements?period=` | 每产权方每月一张活动对账单，未确认单返回派生状态与试算；同一产权方多份委托管理协议合并到同一张单，行级标注协议 |
| 详情 | `GET /api/v1/management-fee-statements/{statement_id}` | 返回协议、本月行、带入行、计入实收、顺延余额、比例、金额、截止日、状态、待补录上游的户和更正链 |
| 登记产权方到账 | `POST /api/v1/management-fee-statements/{statement_id}/owner-receipts` | 指定本单行对应的终端租金义务，登记金额和日期；内部委托租金登记服务写入 `owner_reported_receipt`，与 `POST /rent-ledger-entries/{entry_id}/records` 共用同一事实、校验和幂等 |
| 标记顺延 | `POST /api/v1/management-fee-statements/{statement_id}/deferrals` | 截止日前逐户标记顺延，原因必填；截止日（对账月次月最后一天）后未收余额自动顺延，无需标记 |
| 上传盖章件 | `POST /api/v1/management-fee-statements/{statement_id}/stamped-document` | 上传双方盖章版本，确认前可替换；返回文档和当前应收费用金额 |
| 确认 | `POST /api/v1/management-fee-statements/{statement_id}/confirmation` | 期望版本、幂等键；缺盖章件返回 422 `STAMPED_DOCUMENT_REQUIRED`；截止日前仍有未处理行返回 409 `MANAGEMENT_FEE_LINES_UNRESOLVED`；同一产权方存在更早未确认对账单返回 409 `MANAGEMENT_FEE_SEQUENCE_CONFLICT`；成功后快照行、比例和金额，并把未收余额带入下月单 |
| 更正 | `POST /api/v1/management-fee-statements/{statement_id}/successor` | 原因（缺失返回 422 `CORRECTION_REASON_REQUIRED`）、期望版本和幂等键；只能更正该产权方最近一张已确认对账单，否则返回 409 `MANAGEMENT_FEE_SEQUENCE_CONFLICT`；创建未确认的后继单，原单转 `superseded` 只读 |

对账单不提供创建端点：某产权方某月首次出现产权方应报到账义务时随义务生成创建，确认带出顺延余额时按需创建下月单。对 `confirmed` / `superseded` 单执行到账、顺延或上传盖章件返回 409 `MANAGEMENT_FEE_STATEMENT_LOCKED`。以上写端点均要求 `asset_ops:write`。

整单读取不能将可见的部分协议重算为产权方整单：产权方范围覆盖该产权方或全局范围可读；管理方范围须覆盖该产权方全部委托管理协议的运营方，否则按不可见返回 404。已确认及已更正历史只读取确认快照。未绑定上游的待补录警告还须单独通过终端合同的数据范围校验，不因可读该产权方其他协议而扩大可见范围。

顺延请求使用 `rent_ledger_entry_id`、`reason` 和 `expected_version`，幂等键按写命令公共约定提供；只接受本单投影中仍有未收余额的义务。对已收足行返回 409 `MANAGEMENT_FEE_LINE_NOT_DEFERRABLE`，另键重复标记同一户返回 409 `MANAGEMENT_FEE_LINE_ALREADY_DEFERRED`；同键同请求回放首次版本，不重复写标记、审计或增加版本。同键改变原因返回 `IDEMPOTENCY_CONFLICT`。持有产权方锁后刷新事实再校验余额，避免沿用等待锁前的旧投影。

盖章绑定服务使用已存储且归属于本单的 `document_id` 与 `expected_version`，回执包含 `statement_id`、`version`、`document_id`、当前 `fee_amount`；文件接收上传的 HTTP 边界另按文件上传契约实现。确认与更正均先验证当前整单权限，再重放幂等回执；首次写入才检查期望版本。历史补录单若有顺延余额而紧接次月已确认，返回 `MANAGEMENT_FEE_SEQUENCE_CONFLICT`，要求先更正后续确认单。更正创建同月份的新单，新单须重新上传盖章件。

HTTP 请求与响应细则：
- 列表 `period` 必填，格式为 `YYYY-MM`；非法业务月份返回 400 `INVALID_PERIOD`，只返回当前范围内非 `superseded` 单。详情可读取被更正历史。公开响应包含单据身份/版本、派生或历史状态、截止日、协议 ID、基数/费用、盖章件 ID、确认审计、更正链、强类型明细及待补录上游提示；金额为十进制字符串，不暴露草稿存储的空状态/空金额。
- 产权方到账请求为 `rent_ledger_entry_id`、`amount`、`occurred_on`、可选 `document_id` 和租金义务的 `expected_version`；服务固定写 `owner_reported_receipt`，客户端不可指定 `record_type`。与租金登记端点共用回执；先校验当前单据权限，首次写入在租金/产权方锁后重查状态和行归属，幂等回放不因原行后来作废而被当前投影阻断。
- 盖章端点使用 `multipart/form-data`，字段为 `file` 与对账单 `expected_version`，不接收 JSON 文档 ID。独立 `management_fee_stamp` 上传配置接受 PDF/JPG/JPEG/PNG，最大 20 MiB，图片最大 5000 万像素；复用文件类型/内容验证。文件暂存、晋升及元数据与盖章绑定协作，失败只补偿本次新文件并回滚元数据，旧盖章附件留存。
- 到账、顺延、确认及更正要求非空 `Idempotency-Key`（最长 100 字符，去除首尾空白）；上传使用期望版本。七个端点只做参数/身份传递，业务校验和事务由服务负责。

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
| `GET /api/v1/business-change-events?target_type=&target_id=&period=&page=&page_size=` | 按当前 Party 范围返回 `items` / `total`；`target_type` 支持 `upstream_contract` / `terminal_contract`，`target_id` 精确过滤，`period` 为上海业务月 `YYYY-MM`；分页默认 `page=1`、`page_size=50`（上限 200）；每项返回操作者、时间、动作、脱敏前后值、业务可读摘要、原因、关联对象和 `correlation_id` |

变更记录是审计读取，不提供创建、更新或删除端点；由业务服务在同一事务写入。

PR-0 先覆盖合同确认、修改、续签、终止、退出及撤销，动作码分别为 `confirmed` / `updated` / `renewed` / `terminated` / `exited` / `reversed`。续签的前驱与后继记录共用 `correlation_id`；幂等回放不追加第二份记录，失败事务不留下记录。无有效业务范围返回 403，范围外对象不出现在结果中；其他业务对象的变更记录随对应实施切片接入。

## 6. 预览—提交契约

拆分、合并、上游退出、终端终止、租金阶段更正、考核范围保存、报送提交/撤回和导入提交/撤销使用统一模式。涉及“今天”的生效日校验统一按 `Asia/Shanghai` 业务日计算，不以 UTC 日期代替：

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
| 409 | `RENT_LEDGER_MANUAL_ENTRY_NOT_ALLOWED` | 手工义务不满足 `custom` 账期段或补收免租条件，或作废 `generated` 义务 |
| 409 | `RENT_SCHEDULE_HISTORY_IMMUTABLE` | 租金阶段更正改动了当前业务月首日之前已有的阶段内容 |
| 409 | `RENT_LEDGER_ENTRY_LOCKED` | 作废仍有有效登记的手工义务 |
| 409 | `DEPOSIT_AMOUNT_EXCEEDS_REMAINING` | 押金收入超出待收 / 待付金额，或支出超出持有余额 |
| 409 | `DEPOSIT_ENTRY_CARRIED_FORWARD` | 向已续签合同的押金条目登记 |
| 409 | `DEPOSIT_OFFSET_NOT_ALLOWED` | 合同仍在期内，押金不能抵扣或扣除 |
| 409 | `DEPOSIT_OFFSET_TARGET_INVALID` | 押金抵扣目标或金额无效 |
| 409 | `DEPOSIT_RECORD_ALREADY_REVERSED` | 重复撤销押金记录 |
| 409 | `MANAGEMENT_FEE_STATEMENT_LOCKED` | 对账单已确认或已被更正不可修改，或要撤销的到账已被已确认对账单计入 |
| 409 | `MANAGEMENT_FEE_LINES_UNRESOLVED` | 截止日前对账单仍有未收足且未标记顺延的行 |
| 409 | `MANAGEMENT_FEE_SEQUENCE_CONFLICT` | 存在更早未确认的对账单，或更正的不是该产权方最近一张已确认对账单 |
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
| 422 | `CORRECTION_REASON_REQUIRED` | 租金阶段更正或对账单更正原因缺失 |
| 422 | `FORFEIT_REASON_REQUIRED` | 押金扣除原因缺失 |
| 422 | `CONTRACT_FIELD_NOT_APPLICABLE` | 字段不适用于该合同类型（如委托管理协议填押金或租金阶段、承租合同填管理费比例） |
| 422 | `RENT_RECORD_TYPE_MISMATCH` | 付款/到账记录类型与义务类型不匹配 |
| 422 | `DEPOSIT_RECORD_TYPE_MISMATCH` | 押金记录类型与收取方不匹配 |
| 422 | `STAMPED_DOCUMENT_REQUIRED` | 确认对账单缺双方盖章件 |
| 422 | `MANUAL_ENTRY_BASIS_REQUIRED` | 手工义务缺依据说明 |
| 422 | `SCAN_DOCUMENT_REQUIRED` | 合同确认缺已签扫描件 |
| 422 | `ASSET_UNIT_AREA_INVALID` | 可出租面积超过建筑面积 |
| 422 | `ASSET_UNIT_FIELD_NOT_EDITABLE` | 归属字段不可直接修改（走拆合） |
| 422 | `RENT_SCHEDULE_INVALID` | 租金阶段越出合同期限或互相重叠 |
| 422 | `DERIVED_FIELD_NOT_WRITABLE` | 请求试图写出租状态、合计等派生字段 |
| 422 | `REVERSAL_REASON_REQUIRED` | 租金登记撤销或手工义务作废未提供原因 |

以下是 warning，不作为错误码阻止登记：`UPSTREAM_CONTRACT_MISSING`、`TERMINAL_TERM_EXCEEDS_UPSTREAM`、`ARCHIVE_DOCUMENT_MISSING`、`RENT_SCHEDULE_GAP`（合同期限内有日期没有租金阶段覆盖）、`RENT_LEDGER_PLAN_MISMATCH`（已锁定义务与当前合同条款不一致）。

## 8. Out of Scope API

不新增租赁意向、报价、底价、授权冻结、合同生效检查、外部审批、银行流水、匹配复核、发票、开票分摊、催收案件、产权方门户、领导利润分析或物业工单端点。旧端点存在时按迁移计划下线，不能继续被 v5 页面消费。

## 9. 维护规则

- 新增或修改端点时同步本文档和需求追踪矩阵。
- 字段、状态或统计变化先修改领域模型，再修改 API。
- 权限名称、路由元数据和后端动作必须一致。
- 错误码一旦公开只能通过显式迁移替换，不得靠文案变化改变客户端行为。
