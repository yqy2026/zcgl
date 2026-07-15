# API 契约

## 1. 文档定位

本文档描述当前目标态 API、权限和请求契约。产品需求见 `docs/prd.md`，领域对象见 `docs/specs/domain-model.md`，实现追踪见 `docs/traceability/requirements-trace.md`。

本文档只描述对外契约，不记录实现文件、测试文件或历史迁移过程。

## 2. 全局 API 规则

| 规则 | 契约 |
|---|---|
| 版本前缀 | 所有业务 API 统一使用 `/api/v1/*` |
| 认证 | 登录态使用 HttpOnly Cookie，会话支持刷新和退出 |
| 鉴权 | 写操作和受保护读操作必须鉴权 |
| 授权 | 使用 RBAC + ABAC，按钮和接口级动作均需授权 |
| 数据范围 | 业务查询按用户主体绑定自动过滤 |
| 项目主轴 | 项目端点承载资产、合同与协议、经营台账摘要、风险和项目分析等运营视图；经营台账、合同中心、资产资源、主体客户仍保留全局直接入口 |
| 分析视图 | 分析和大屏端点使用 `view_mode` 指定 owner 或 manager 口径 |
| 搜索 | 搜索结果必须经过权限和数据范围过滤 |
| CSRF | 状态变更请求必须携带 CSRF token |
| 幂等 | 批量更新、补偿任务等关键写操作必须幂等 |
| 乐观锁 | 核心实体更新应使用版本冲突保护，冲突返回 409 |
| 删除 | 关键业务记录不提供用户侧物理删除入口 |

## 3. 请求范围与视图契约

### 3.1 BindingContext

常规业务端点不要求用户手动选择数据范围。系统根据用户绑定的主体自动过滤数据。

| 用户类型 | 常规查询行为 |
|---|---|
| 产权方绑定用户 | 只返回绑定产权方范围内数据 |
| 运营方绑定用户 | 只返回绑定运营方范围内数据 |
| 多绑定用户 | 返回各绑定范围的数据并集，按业务主键去重 |
| 管理员或审计用户 | 按授权查看全量或审计范围内数据 |

### 3.2 ViewMode

`view_mode` 只用于分析和大屏端点，不用于常规 CRUD。

| 参数 | 含义 |
|---|---|
| `view_mode=owner` | 产权方统计口径 |
| `view_mode=manager` | 运营方统计口径 |
| 不传 | 系统按用户绑定类型自动回落 |

`X-Perspective` HTTP header 已废弃，不作为当前契约。

## 4. 端点契约

### 4.1 认证与当前用户

| 能力 | 方法与路径 | 契约 |
|---|---|---|
| 登录 | `POST /api/v1/auth/login` | 校验凭据并写入会话 Cookie |
| 刷新 | `POST /api/v1/auth/refresh` | 刷新登录会话 |
| 退出 | `POST /api/v1/auth/logout` | 清理会话 |
| 当前用户 | `GET /api/v1/auth/me` | 返回当前用户、角色和能力摘要 |

### 4.2 用户、角色与权限

| 能力 | 方法与路径 | 契约 |
|---|---|---|
| 用户管理 | `/api/v1/auth/users/*` | 用户创建、编辑、启停用、密码重置 |
| 角色管理 | `/api/v1/roles/*` | 角色定义、权限勾选、角色分配 |
| 数据策略 | `/api/v1/auth/data-policies/*` | ABAC 策略包、模板和角色绑定管理 |

用户管理主契约使用多角色语义，支持单用户分配多个角色。多角色权限默认取允许权限并集；显式拒绝授权或拒绝数据策略优先于允许结论。

### 4.3 资产

| 能力 | 方法与路径 | 契约 |
|---|---|---|
| 资产列表 | `GET /api/v1/assets` | 支持分页、筛选、排序、搜索，并按主体范围过滤 |
| 资产详情 | `GET /api/v1/assets/{asset_id}` | 返回资产主数据和必要投影 |
| 创建资产 | `POST /api/v1/assets` | 创建草稿资产，需通过权限和数据范围校验；`owner_party_id` 必填；`asset_code` 由系统按产权方编码段自动生成、只读，不接受客户端写入（ADR-0017，已实施） |
| 更新资产 | `PATCH /api/v1/assets/{asset_id}` | 审核态关键字段受控，需版本冲突保护 |
| 删除资产 | `DELETE /api/v1/assets/{asset_id}` | 逻辑删除，存在关联约束时拒绝 |
| 恢复资产 | `POST /api/v1/assets/{asset_id}/restore` | 恢复逻辑删除资产 |
| 批量操作 | `/api/v1/assets/batch-*` | 支持批量相关操作 |
| 导入资产 | `/api/v1/assets/import` | 支持模板校验和导入；**导入行必须有可解析到既有产权方 Party 的 owner，无主行直接拒绝**（对齐 ADR-0010 owner 内在必填、ADR-0017 编号生成前置，已实施）；导入 create 走与手动创建共享的 owner 必填校验，不直接裸调 crud；`asset_code` 系统生成、模板不含该列 |
| 资产附件 | `/api/v1/assets/{asset_id}/attachments/*` | 管理资产附件 |
| 资产产权证 | `/api/v1/assets/{asset_id}/property-certificates/*` | 资产详情内维护产权证：列表、详情、新增、编辑、附件、轻量在线预览、扫描件解析预填。字段契约、5 项保存硬门槛、附件规则（类型/大小/上传不自动解析/预览/下载独立权限/日志/疑似重复/资产与附件 ≥1 下限）与 `warning` 风险派生见 domain-model §4.20（PropertyCertificate）、§4.21（权利人关系）、§4.22（Attachment）。**证号重复（端点专属契约）**：当前资产上下文提交的证号已存在时返回既有产权证提示、ID、当前 `asset_ids`、摘要与「当前资产详情页追加关联」确认目标，不创建新记录、不自动追加资产或附件；本次扫描件作为既有产权证附件候选返回，须确认载荷显式确认才写入、用户可取消；若既有产权证 `attachment_ids` 为空则不得取消本次附件追加（否则校验错误、拒绝追加资产关联）。保存闸门须按 domain-model §4.20 的 5 项校验，不得用解析字段校验器 `validate_extracted_fields` 代替、不得漏卡资产/附件/权利人 |
| 产权证扫描件解析 | `/api/v1/assets/{asset_id}/property-certificates/extraction-sessions/*` | 只能对当前产权证 `attachment_ids` 中的附件发起解析、不接收新文件（需解析新文件先经附件接口上传或追加）；重新解析新结果取代旧未确认候选、不覆盖已确认字段。解析会话语义、低置信逐项处理、候选不自动绑定/覆盖、字段来源与确认写入校验统一见 §4.10 与 domain-model §2/§4.23；确认写入前须满足 domain-model §4.20 的 5 项保存硬门槛；证号重复返回既有产权证冲突契约（同上「资产产权证」行）。`should_create_new_asset` / `create_new_asset` 类载荷不属于 MVP 正式确认契约 |
| 租赁摘要 | `GET /api/v1/assets/{asset_id}/lease-summary` | 按上游、下游、委托、直租展示租赁情况 |
| 经营方历史 | `GET /api/v1/assets/{asset_id}/management-history` | 返回经营方变更历史 |
| 项目历史 | `GET /api/v1/assets/{asset_id}/project-history` | 返回项目关系历史 |
| 审核动作 | `/api/v1/assets/{asset_id}/submit-review|approve-review|reject-review|reverse-review|resubmit-review|withdraw-review`；`POST /api/v1/assets/batch-submit-review`；`POST /api/v1/assets/batch-approve-review` | 资产 `review_status` 两步生命周期流转；`approve-review` 按复核权限门控，**不限制审核人 ≠ 提交人**（持权限者均可，含提交人本人）；批量提交支持 `draft → pending`，批量确认支持 `pending → approved`，已在目标状态的资产幂等成功，状态不匹配逐项返回错误；资产不走路由审批流 |
| 审核日志 | `GET /api/v1/assets/{asset_id}/review-logs` | 返回资产审核日志 |

### 4.4 项目

| 能力 | 方法与路径 | 契约 |
|---|---|---|
| 项目列表 | `GET /api/v1/projects` | 支持分页、筛选、搜索，并按主体范围过滤 |
| 项目详情 | `GET /api/v1/projects/{project_id}` | 返回项目主数据 |
| 创建项目 | `POST /api/v1/projects` | 项目必须绑定运营管理方；`project_code` 由系统按运营方 `party_code` 段自动生成（`PRJ-{operator_seg}-{YYYYMM}-{SEQ4}`）、只读；生成前要求运营方主体及 `party.code` 均存在，并按运营方+月份前缀串行取号（ADR-0018，已实施） |
| 更新项目 | `PATCH /api/v1/projects/{project_id}` | 更新项目主数据 |
| 删除项目 | `DELETE /api/v1/projects/{project_id}` | 逻辑删除 |
| 当前有效资产 | `GET /api/v1/projects/{project_id}/assets` | 返回项目当前有效资产汇总 |
| 合同与协议 | `GET /api/v1/projects/{project_id}/contract-relations` | 返回项目下承租合同、转租合同、委托协议、直租合同摘要投影；路径可沿用内部 `contract-relations`，用户侧文案不得展示“合同关系” |
| 经营台账摘要 | `GET /api/v1/projects/{project_id}/ledger-summary` | 返回项目维度四类视图摘要：终端租户收缴、运营方收入、运营方成本、服务费结算；终端租户收缴包含承租转租下游租金和代理直租租金，是唯一逾期来源；运营方收入包含承租转租租金收入和代理服务费收入，不含代理直租租金；运营方成本记录承租上游租金应付/实付/未付，不产生逾期 |
| 风险摘要 | `GET /api/v1/projects/{project_id}/risks` | 返回项目风险项；MVP 已覆盖人工风险标签、30 天内合同/协议到期提醒、终端租户租金逾期、当前有效资产可出租面积大于已出租面积时的空置风险（MVP 不含主合同覆盖类风险）、合同更正后已收付台账与当前条款不一致的 `ledger_stale_after_correction` 风险（见 ADR-0008）、已生成服务费台账与当前来源租金不一致或冻结来源租金条目已与当前合同条款不一致的 `service_fee_source_mismatch` 风险，以及产权证证照信息不完整或权利人与关联资产当前主产权主体不一致的 `warning` 级数据质量风险（MVP 已删「未核验」触发，见 ADR-0005）；运营方成本未付、服务费未收不作为逾期风险；该风险只作为项目风险摘要或详情页数据质量提示；接口不返回任务、待办、审批或处置工单对象；产权证数据质量风险由当前数据实时派生，接口不接受关闭、忽略或标记已处理请求 |
| 租户客户 | `GET /api/v1/projects/{project_id}/tenants` | 返回项目下终端租户、客户主体和合同数摘要 |
| 项目分析 | `GET /api/v1/projects/{project_id}/analytics` | 返回项目维度分析摘要，包含有效资产汇总、合同/协议数、客户数、风险数、终端租户收缴、运营方收入、运营方成本、服务费结算、经营结果和按租金账期聚合的月度趋势，并按承租转租、代理运营分区返回；代理直租租金计入终端租户收缴但不计入运营方收入；`scope_mode=all` 混合视图下客户双指标置空并返回 `customer_metrics_suppression_reason=customer_metrics_requires_single_perspective`，其余项目分析字段照常返回 |

### 4.5 合同与协议

| 能力 | 方法与路径 | 契约 |
|---|---|---|
| 合同与协议列表 | `GET /api/v1/contract-groups` | 支持主体范围过滤、项目筛选和业务筛选；路径可沿用内部 `contract-groups`，用户侧展示承租合同、转租合同、委托协议、直租合同，不展示“合同关系”对象名 |
| 合同与协议详情 | `GET /api/v1/contract-groups/{group_id}` | 返回内部聚合投影、主体、资产和合同/协议信息；前端文案为“合同与协议” |
| 创建合同/协议经营事项 | `POST /api/v1/contract-groups` | 必须归属项目；同一经营事项只能选择一种经营模式 |
| 更新合同/协议经营事项 | `PATCH /api/v1/contract-groups/{group_id}` | 更新内部聚合主数据和关联信息 |
| 新增合同/协议 | `POST /api/v1/contract-groups/{group_id}/contracts` | 在既有经营事项内补录承租合同、转租合同、委托协议或直租合同；路径 `group_id` 必须与请求体一致。创建载荷可携带初始 `rent_terms`，合同服务在同一事务内先落租金条款、再生成经营台账，不允许生效后绕过纠错流程补写条款 |
| 合同详情 | `GET /api/v1/contracts/{contract_id}` | 返回合同基表和类型明细；暴露只读 `lessor_name_snapshot` / `lessee_name_snapshot` 作为签署时主体名称快照，历史合同显示快照名而非跟随 Party 主档改名；可返回 `field_sources` 供编辑或补录来源上下文按需查看，业务详情主视图不要求默认展示；签订日期、付款周期或备注类关键经营字段缺失时，可返回轻量补录完整性提示，不返回任务、待办或审批对象，也不阻断保存 |
| 更新合同补录信息 | `PATCH /api/v1/contracts/{contract_id}` | 更正合同补录字段；需记录操作痕迹，已生成经营台账按规则重算或作废（重算只动未收/未付且无收付流水的条目，已有收付流水条目不静默改写、留待人工处理；MVP 无红字冲销） |
| 合同扫描件附件 | `GET/PUT/DELETE /api/v1/contracts/{contract_id}/attachments*` | 查询、整体替换和删除盖章扫描件引用；扫描件文档按 `storage_key` 单存，多条同委托协议合同可共享引用；替换/删除只联动同合同号 + 同委托方 + 同受托方 + 正常代运营受托合同，且需对全部受影响合同逐条通过 `contract:update` 授权；复用既有 `storage_key` 时若该文档已链接到本次受影响集合外的合同，替换必须失败暴露；删除受「每合同 ≥1 盖章扫描件」保护 |
| 合同扫描件解析 | `/api/v1/contract-groups/{group_id}/contracts/extraction-sessions/*` | 上传合同扫描件后解析合同编号、主体、资产、期间、金额、租金或服务费条款，返回字段候选值、置信度、轻量来源证据、候选匹配、匹配提示和字段来源候选；必须人工确认后创建或更新合同补录；主体候选仅限已审核 Party，资产候选仅限既有资产，候选不得自动绑定；主体未匹配已审核 Party 时只返回提示，不直接创建 Party 或写入合同主体引用；资产未匹配既有资产时只返回提示，不直接创建或绑定新资产 |
| 合同作废 | `POST /api/v1/contracts/{contract_id}/void` | 补录错误或业务作废时保留历史记录；相关台账按规则作废（已收/部分已收条目需先人工处理；MVP 无红字冲销） |
| 审计日志 | `GET /api/v1/contracts/{contract_id}/audit-logs` | 返回合同补录、更正、作废和台账重算操作日志 |

MVP 不提供合同提审、审核通过、驳回、反审核或关系联审主契约。合同补录**即生效**，仅保留最小生命周期（草稿/生效/已到期/已终止 + 纠错草稿，纠错门禁绑生命周期状态）。原合同审批流端点（`submit-review`/`approve`/`reject`/`reverse`/合同组 `submit-review` 批量提审、`_requires_joint_review` 联审）是已移出基线需求 REQ-RNT-004 联审半边的残留实现，已按 ADR-0013 删除而非保留；显式 `expire` 端点同样下线，`已到期` 仅由 `effective_to` 派生展示。

MVP 不提供续签端点。到期后继续合作按新合同/协议补录流程创建记录。承租合同、转租合同、委托协议、直租合同仅为经营影响方向标记，MVP 不做主合同覆盖判定或覆盖风险。

代理委托协议跨项目按 ADR-0012：同一份委托协议覆盖 N 个项目时，在每个项目下各建一条合同/协议记录、共享引用同一份盖章扫描件（扫描件只存一份、多记录引用，替换只联动同合同号 + 同委托方 + 同受托方 + 正常代运营受托角色兄弟记录，并对全部受影响合同逐条鉴权；复用既有 `storage_key` 时若发现范围外链接则拒绝；删除受「每合同 ≥1 扫描件」保护）；`contract_number` 已由全局唯一改为 `UNIQUE(contract_number, project_id)` 按项目复合唯一（N 条同号靠项目区分），正常合同缺 `project_id` 由 DB check constraint 持续拦截；更正按记录独立、只重算本项目台账，不联动兄弟记录（2026-06-20 已落地）。

### 4.6 经营台账与收付流水

| 能力 | 方法与路径 | 契约 |
|---|---|---|
| 合同/协议台账 | `GET /api/v1/contracts/{contract_id}/ledger` | 查询单合同/协议台账，返回账期、四类视图归属、应收/应付、实收/实付、未收/未付和派生状态 |
| 收付流水登记 | `POST /api/v1/ledger/payment-flows` | 创建轻量收付流水，支持 `terminal_rent_receipt`、`service_fee_receipt`、`upstream_cost_payment`；请求字段包含发生日期、金额、备注和可选凭证附件，登记人由服务端从认证用户固化、客户端不得指定；返回流水主键、类型、发生日期、金额、登记人、对方主体、凭证附件、备注、状态和时间戳 |
| 收付流水分摊 | `POST /api/v1/ledger/payment-flows/{flow_id}/allocations` | 一笔流水可人工分摊到多个账期，系统校验分摊金额合计等于流水金额；账期归属按租金账期，流水发生日期仅用于查询、导出和审计；返回分摊主键、流水 ID、目标类型、目标 ID、账期、金额和时间戳 |
| 收付流水明细 | `GET /api/v1/ledger/payment-flows?target_type={type}&target_id={id}` | 按单个租金或服务费台账目标返回关联流水、分摊和已授权凭证元数据；查询目标先按冻结项目/产权方/运营方归属做主体范围校验，不提供跨类型混排入口 |
| 收付流水作废 | `POST /api/v1/ledger/payment-flows/{flow_id}/void` | 仅允许 `active` 流水；原因必填，操作人由服务端固化；原流水转 `voided`，其分摊不再参与汇总，并在同一事务内重算全部受影响台账 |
| 收付流水更正 | `POST /api/v1/ledger/payment-flows/{flow_id}/correct` | 仅允许 `active` 流水；原因、新流水和完整新分摊必填；新流水类型及项目/产权方/运营方/币种范围必须与原流水一致，新旧分摊目标按稳定顺序一次加锁；同一事务把原流水转 `corrected`、创建通过 `corrected_from_flow_id` 关联的唯一新 `active` 流水并重算新旧目标；不得直接写 `status`、`paid_amount` 或复制原流水凭证 ID，新流水凭证在更正成功后单独上传 |
| 收付流水凭证上传 | `POST /api/v1/ledger/payment-flows/{flow_id}/vouchers` | 仅允许为当前主体范围内的 `active` 流水上传单个 PDF/JPG/JPEG/PNG，最大 20MB；入口只做 `20MB + 1 byte` 有界读取，并校验 MIME、扩展名、固定文件头和可疑内容，伪装类型失败暴露；返回受限附件元数据，不返回存储路径 |
| 收付流水凭证下载 | `GET /api/v1/ledger/payment-flows/{flow_id}/vouchers/{attachment_id}/download` | 使用独立 `ledger_voucher:read` 权限并再次校验流水冻结主体范围与附件归属；记录用户、流水、附件、时间及 `success` / `not_found` 结果 |
| 凭证下载审计 | `GET /api/v1/ledger/payment-flows/{flow_id}/voucher-download-audits` | 仅向可读取该流水冻结主体范围的用户返回轻量下载证据；响应不暴露存储路径、客户端 IP 或设备信息 |
| 经营台账查询 | `GET /api/v1/ledger/entries` | 支持项目上下文和全局上下文；按合同租金台账视图 `ledger_view=terminal_collection/operator_income/operator_cost`、`project_id`、资产、主体、合同/协议、账期、有效收付流水发生日期 `flow_occurred_on_start/end` 和派生支付状态查询，作为全局“经营台账”入口的数据源；响应包含 `ledger_views` 与 `flow_occurred_on_dates`。服务费结算由 `ServiceFeeLedger` 与服务费生成/分摊路径承载，不复用合同租金台账响应暗中混排 |
| 经营台账导出 | `GET /api/v1/ledger/entries/export` | 按当前经营台账筛选条件导出查询结果；导出列包含 `ledger_views`、账期 `year_month` 和有效流水发生日期集合 `flow_occurred_on_dates` |
| 台账跟进状态 | `PATCH /api/v1/ledger/entries/{entry_id}/follow-up` | 仅维护终端租户收缴视图的轻量跟进字段：`follow_up_status`、`next_follow_up_date`、`follow_up_note`；不修改台账金额或派生支付状态 |
| 服务费月度生成 | `POST /api/v1/ledger/service-fees/generate` | 按租金账期月份、项目、委托协议和产权方汇总代理直租实收，固化服务费比例、计算基数和来源账期生成服务费应收；不逐笔生成 |
| 服务费台账查询 | `GET /api/v1/ledger/service-fees` | 按 `contract_group_id` 或 `project_id` 查询代理模式月度服务费台账，并按当前主体数据范围过滤；响应包含服务费台账 ID、服务费账期、应收/实收/派生状态、计算基数、服务费比例、固化归属字段和 `source_ledger_ids` 来源租金台账集合，用于服务费结算视图展示来源账期并登记服务费收款 |
| 服务费来源校准 | `POST /api/v1/ledger/service-fees/{entry_id}/reconcile` | 人工确认采用当前唯一可计算来源，必须提交处理原因并通过当前主体数据范围校验；只处理现有服务费台账与当前来源桶字段不一致的场景，底层租金台账仍陈旧、当前来源已消失、无法唯一匹配，或重算应收低于已登记服务费实收时拒绝，不自动冲销收付事实 |
| 台账重算 | `POST /api/v1/contracts/{contract_id}/ledger/recalculate` | 对受影响区间作废并重建；响应返回 `created`/`updated`/`voided` 与 `skipped_entries`，已收/部分已收条目被跳过时需在前端当场展示 |
| 补偿任务 | `POST /api/v1/ledger/compensation/run` | 扫描并补齐缺失台账，必须幂等 |

实收/实付唯一写路径是「创建收付流水 → 保存账期分摊」。旧 `PATCH /api/v1/contracts/{contract_id}/ledger/batch-update-status` 已下线，不提供直接改写累计 `paid_amount` 的兼容入口。

Authorization boundary: ledger ABAC rules admit the configured role/action pair; service methods then fail closed against each ledger row's frozen owner/operator attribution. Project and contract-group access alone never authorizes historical rows whose frozen attribution is outside the active party scope. Allocation replacement and payment-flow void/correction lock the payment flow and all affected target rows, while service-fee reconciliation locks its target row, so allocation totals, terminal lifecycle actions, and reconciliation cannot race to overwrite each other. Voucher download additionally requires `ledger_voucher:read`; ledger read alone is insufficient for file download.

Payment-flow creation records an authenticated actor but has no ledger target and therefore does not alter any receivable/payable balance. Party-scope authorization is mandatory when allocations bind that flow to ledger targets; a flow cannot affect ledger totals until the allocation service validates every target's frozen project/owner/operator scope.

When an existing service-fee receivable no longer matches its monthly key because the owner or entrusted agreement changed, generation must not create a second receivable if the frozen and current buckets share a unique source-ledger identity. It preserves the existing row as a source mismatch; explicit reconciliation may re-key it only when exactly one current bucket matches and the reconciled amount is not below active receipt allocations. If the preserved row belongs to a different frozen party scope, scoped generation fails loudly without disclosing that row and requires an unrestricted administrator to perform the cross-party reconciliation.

多资产合同按合同级金额返回，不做资产级金额拆分；项目或主体汇总时按合同和账期去重。逾期只由终端租户租金收缴派生；运营方成本未付、服务费未收不产生逾期。

### 4.7 客户与主体

| 能力 | 方法与路径 | 契约 |
|---|---|---|
| 客户详情 | `GET /api/v1/customers/{party_id}` | 返回客户基础信息、风险标签、历史签约和统计 |
| 主体列表 | `GET /api/v1/parties` | 查询主体主档 |
| 主体创建 | `POST /api/v1/parties` | 创建主体草稿 |
| 主体更新 | `PATCH /api/v1/parties/{party_id}` | 更新主体主档 |
| 主体导入 | `POST /api/v1/parties/import` | 初始化批量导入主体 |
| 主体审核 | `/api/v1/parties/{party_id}/submit-review|approve-review|reject-review` | 主体审核状态流转：`draft → pending → approved`，驳回写入 `rejected`；`rejected` 可编辑后重新提审，不提供 Asset 式 `reverse-review` 反审端点 |
| 主体联系人 | `GET/POST /api/v1/parties/{party_id}/contacts` | 维护主体主档下的联系人；联系人不提供通用实体联系人写入口 |
| 主体绑定 | `/api/v1/parties/users/{user_id}/party-bindings*` | 维护用户和主体绑定关系 |

合同补录引用的主体必须来自已审核 Party。

### 4.8 搜索

| 能力 | 方法与路径 | 契约 |
|---|---|---|
| 全局搜索 | `GET /api/v1/search` | MVP 覆盖资产、项目、合同/协议、客户 |

搜索结果支持全部视图和按对象分组视图。**默认排序按业务置顶优先 → 文本相关度 → 标题**：业务置顶 = 查询命中业务编码（资产/项目编码、合同号/协议号）精确或前缀匹配的结果，优先于纯文本相关度（修正原契约「相关度优先、同分按业务置顶」与代码 `_business_rank` 先于 `_score_text` 排序的方向矛盾）。未授权对象不返回。产权证不作为 MVP 全局搜索对象，用户通过资产结果进入资产详情后查看产权证信息；产权证数据质量风险也不进入全局搜索结果。

### 4.9 分析与统计

| 能力 | 方法与路径 | 契约 |
|---|---|---|
| 综合分析 | `GET /api/v1/analytics/comprehensive` | 返回 `operational_metric_groups`（终端租户收缴、运营方收入、运营方成本、经营结果四组）、统计口径版本 `metrics_version`、账期归属字段 `period_attribution_basis/label`、客户双指标、按项目分区的 `project_breakdown` 和按经营模式分区的 `mode_breakdown`；承租转租统计下游租金收入和上游成本，代理运营统计代理直租收缴和服务费，代理直租租金不计入运营方收入；默认按租金账期归属，流水发生日期仅用于经营台账查询/导出；`customer_entity_breakdown` / `customer_contract_breakdown` 仅含终端客户桶 `downstream_sublease`、`direct_lease`，上游/委托等非客户对手方只通过 `counterparty_entity_breakdown` / `counterparty_contract_breakdown` 的 `upstream_lease`、`entrusted_operation` 返回；客户双指标分析拒绝 `view_mode=all` |
| 分析导出 | `GET /api/v1/analytics/export` | 导出带统计口径版本的结果；客户双指标分析拒绝 `view_mode=all`；导出应标记账期归属口径和流水发生日期字段 |
| 统计报表 | `/api/v1/statistics/*` | 提供基础、面积、财务、出租率、分布、趋势等统计能力 |

分析端点可接收 `view_mode=owner|manager`，不传时按用户绑定自动回落。常规客户列表可使用 `all` 并集视图；综合分析和分析导出产出客户双指标，必须选定 owner 或 manager 单一视角。

### 4.10 扫描件解析辅助补录

| 能力 | 方法与路径 | 契约 |
|---|---|---|
| 创建解析会话 | `POST /api/v1/extraction-sessions` | 上传合同扫描件，或对当前产权证已有附件发起解析（`target_type=contract\|property_certificate`）；产权证只能引用现有 `attachment_ids`、不接收新文件或临时文件；重新解析新结果取代旧未确认候选、不影响已确认字段；不提供草稿创建/恢复；返回临时会话 ID。会话语义见 domain-model §4.23 |
| 查询解析状态 | `GET /api/v1/extraction-sessions/{session_id}` | 返回候选字段、置信度、轻量来源证据、候选匹配、低置信标记、差异提示与少量建议补全字段（合同限签订日期/付款周期/备注，产权证限证载面积/期限/限制）；不返回目标对象全量字段作为确认页表单、不提供一键或批量采纳；建议补全为质量提示不作硬校验；差异提示不得致自动覆盖。详见 domain-model §2/§4.23 |
| 确认解析结果 | `POST /api/v1/extraction-sessions/{session_id}/confirm` | 提交确认/修正/手工补齐/留空载荷、`confirmed_field_keys` 与 `field_sources`；服务端按 domain-model §2「字段来源」「扫描件解析确认」校验（每写入字段须带来源否则阻断、低置信须处理、候选不自动采纳或覆盖、主体/权利人/资产引用须用户显式选择已审核 Party 或既有资产、字段契约外临时字段拒绝、不接收 `accept_all` 类批量采纳）并按目标对象保存硬门槛（合同 ≥1 盖章扫描件；产权证按 domain-model §4.20 的 5 项）写入；产权证证号重复返回冲突契约（见 §4.3 资产产权证），既有产权证无附件且取消本次附件追加时返回附件硬门槛校验错误；确认成功清理会话、不长期保留来源证据 |
| 取消解析会话 | `POST /api/v1/extraction-sessions/{session_id}/cancel` | 取消未确认会话，不写入业务主数据，并清理临时会话；不保留草稿，也不提供稍后继续确认入口 |

解析会话语义统一见 domain-model §2「字段来源」「扫描件解析确认」与 §4.23 ScanExtractionSession：临时不留档、无草稿 / 历史档案、失败 / 超时可重试或完全手工补录、低置信逐项处理、候选不自动绑定或覆盖、未匹配已审核 Party 或既有资产只提示不在确认动作中创建、不持久化解析工具 / 模型 / 置信度 / 页码 / 截图等元信息、字段来源枚举不拆子类型；产品级规则见 PRD §6.5。合同补录须保留 ≥1 盖章扫描件，产权证须 ≥1 附件且 ≥1 既有资产关联。

### 4.11 审批（MVP 已删除）

资产路由审批 API（`/api/v1/approval/*`）连同 `ApprovalInstance` 机制一并删除。资产审核改由 §4.3「审核动作」(`/api/v1/assets/{asset_id}/submit-review|approve-review|...`) 的 `review_status` 两步生命周期承接，确认按复核权限门控、不限制审核人 ≠ 提交人。详见 `docs/architecture/ADR-0002-asset-review-no-approval-workflow.md`（含 2026-06-10 取消职责互斥的决策更新）。

### 4.12 系统管理

| 能力 | 方法与路径 | 契约 |
|---|---|---|
| 组织管理 | `/api/v1/organizations/*` | 组织 CRUD 和组织上下文绑定维护 |
| 数据字典 | `/api/v1/system/dictionaries/*` | 字典分类和字典项维护 |
| 系统基础 | `/api/v1/system/health`、`/api/v1/system/info`、`/api/v1/system/root` | MVP 仅保留最小健康检查和系统信息；复杂 monitoring API 不作为产品能力暴露 |
| 通知 | `/api/v1/notifications/*` | 站内通知查询与处理（仅已读/未读，无处理闭环）；业务提醒生成时按主体绑定数据范围过滤接收人（仅可见该对象 owner/operator 范围者），系统通知豁免范围过滤但须内容中立（`admin`/`system_admin` 发，见 domain-model §4.24）。业务通知仅覆盖合同/协议即将到期、合同/协议已到期、终端租户租金到期、终端租户租金逾期；运营方成本未付和服务费未收不生成逾期通知。档位幂等去重、优先级档位派生、系统通知生产者、企业微信按 `recipient_id` 定向应用消息（删群广播）等机制见 domain-model §4.24 Notification；ADR-0015 与系统通知生产者已实施。ADR-0016 代码已接企业微信应用消息并通过 `gettoken` 凭据验证，真实发送待企业微信可信 IP / 域名配置；正式用户 ↔ 企业微信 `userid` 映射仍待实施。 |

## 5. 错误与边界约定

| 场景 | 契约 |
|---|---|
| 未登录 | 返回 401 |
| 无权限 | 返回 403 |
| 资源不存在 | 返回 404 |
| 乐观锁冲突 | 返回 409 |
| 业务规则冲突 | 返回明确业务错误和可读原因 |
| 校验失败 | 返回字段级校验信息 |
| 重复幂等请求 | 不重复创建记录，不重复产生副作用 |

## 6. Out of Scope API

以下能力可存在代码骨架或历史入口，但不进入 MVP API 验收：

| 能力 | 说明 |
|---|---|
| 权属方管理 | 路由和用户可见入口已冻结，待补齐正式需求后重新激活 |
| 通用 BPM 引擎 | MVP 不建设通用审批流引擎 |
| 财务总账和支付结算 | 不属于当前产品边界 |
| 扫描件批量解析 | 批量上传、批量解析、批量确认或批量落库不作为 MVP API 契约；如保留存量入口，不进入用户主路径和验收范围 |
| 用户侧物理删除 | 关键业务记录不提供物理删除入口 |

## 7. 维护规则

- 新增 API 必须同步本文档。
- API 字段语义变更必须同步 `docs/specs/domain-model.md`。
- API 实现状态和证据变化只同步 `docs/traceability/requirements-trace.md`。
- 本文档不得记录实现文件路径、测试文件路径或历史迁移过程。
