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
| 数据范围 | 业务查询、ABAC、资源上下文、搜索、通知和分析统一使用 `PartyScopeResolver`；显式用户绑定优先，无当前有效绑定记录时回退内部组织默认范围，异常失败关闭 |
| 项目主轴 | 项目端点承载资产、合同与协议、经营台账摘要、风险和项目分析等运营视图；经营台账、合同中心、资产资源、主体客户仍保留全局直接入口 |
| 分析视图 | 分析和大屏只接受公开 `view_mode=owner|manager|all`；省略时由有效范围解析，`scope_mode` 仅为服务端结果 |
| 搜索 | 搜索结果必须经过权限和数据范围过滤 |
| CSRF | 状态变更请求必须携带 CSRF token |
| 幂等 | 批量更新、补偿任务等关键写操作必须幂等 |
| 乐观锁 | 核心实体更新应使用版本冲突保护，冲突返回 409 |
| 删除 | 关键业务记录不提供用户侧物理删除入口 |

## 3. 请求范围与视图契约

### 3.1 EffectivePartyScope

常规业务端点不要求用户手动选择数据范围。服务端按固定优先级解析同一个有效主体范围，调用方不得自行拼接或猜测 Organization 与 Party 的关系。

| 范围来源 | 常规查询行为 |
|---|---|
| 当前有效分配内建 `admin` 或 `system_admin` 角色的用户 | 主体范围解析为 `unrestricted`，仍受动作权限与显式 deny 约束；`perm_admin` 和其他管理角色不进入该分支 |
| 当前有效显式绑定 | 全部有效 owner/manager 绑定构成完整范围，按业务主键去重；不与组织默认范围合并 |
| 无当前有效绑定记录 | 使用所属 Organization 直接关系，或继承最近有效祖先的 Party + owner/manager 视角 |
| 范围缺失或配置失效 | 失败关闭并返回稳定 403 原因码，不返回成功空列表，也不跳过无效直接关系继续向上继承 |

尚未生效、已到期或已关闭的绑定不属于当前有效记录。处于时间窗内但目标 Party 失效的绑定不授权并阻断组织回退；仍有其他有效显式绑定时只使用其范围，同时在诊断结果中报告异常。范围缓存的有效期不得越过最近的 `next_transition_at`。

### 3.2 ViewMode

`view_mode` 只用于分析和大屏端点，不用于常规 CRUD。

| 参数 | 含义 |
|---|---|
| `view_mode=owner` | 产权方统计口径 |
| `view_mode=manager` | 运营方统计口径 |
| `view_mode=all` | owner/manager 混合口径；需要客户双指标等单一视角的端点拒绝，其他端点按各自抑制契约处理 |
| 不传 | 有效范围仅含一种视角时自动采用；同时含 owner/manager 时解析为内部 `scope_mode=all`，不按绑定顺序或展示偏好猜选 |

`view_mode` 是唯一公开视角参数；`scope_mode` 只出现在服务端解析上下文或响应诊断中，不是第二个请求参数。`X-Perspective` HTTP header 已废弃，不作为当前契约。

### 3.3 敏感范围变更预览

Organization 代表主体、组织移动、human 用户调动、UserPartyBinding 和 Party 启停等会改变有效范围的操作必须遵循同一预览-提交契约：

1. 预览响应返回变更前后范围、影响摘要、短期有效的 opaque `preview_token` 与 `expires_at`。
2. `preview_token` 绑定当前操作者、目标、规范化后的完整提议和相关记录版本，不包含可由客户端解码的敏感数据。
3. 提交必须携带原 `preview_token`、原因和幂等键；服务端重新计算并校验摘要。提议、操作者、权限、目标状态或相关版本发生变化，或 token 过期时，返回 409 `SCOPE_CHANGE_PREVIEW_STALE`，要求重新预览。
4. 成功提交消费 token；相同幂等键的网络重试返回首次结果，不重复产生副作用。批量提交另要求同一事务内全成全败。

该机制只证明用户确认了当前影响，不引入审批流。

## 4. 端点契约

### 4.1 认证与当前用户

| 能力 | 方法与路径 | 契约 |
|---|---|---|
| 登录 | `POST /api/v1/auth/login` | 校验凭据并写入会话 Cookie |
| 刷新 | `POST /api/v1/auth/refresh` | 刷新登录会话 |
| 退出 | `POST /api/v1/auth/logout` | 清理会话 |
| 当前用户 | `GET /api/v1/auth/me` | 返回当前用户、不可变 `account_type`、`organization_id`、角色和能力摘要 |
| 本人有效主体范围 | `GET /api/v1/auth/me/party-scope` | 直接返回统一解析器的来源、`scope_mode`、所属/继承组织、owner/manager Party 摘要、下一时间边界和结构化 `issues`；自查视图省略异常节点 `node_ref`，不返回统一标识、指纹或外部引用 |

### 4.2 用户、角色与权限

| 能力 | 方法与路径 | 契约 |
|---|---|---|
| 用户管理 | `/api/v1/auth/users/*` | 普通 API 只创建不可变 `account_type=human` 的停用用户，并支持资料编辑、启停用、密码重置；通用创建/编辑不得写 `organization_id`，启用 human 用户前必须已通过专用调动动作归属有效 Organization；`service/system` 由受控系统流程建立 |
| 用户所属组织影响预览 | `POST /api/v1/auth/users/{user_id}/organization/preview` | 仅预览 human 用户调动；请求只含 `organization_id`，校验目标到根的完整启用 Organization 链并返回前后有效主体范围、显式绑定数量、组织与缓存影响，不提交变更 |
| 用户所属组织变更 | `PUT /api/v1/auth/users/{user_id}/organization` | 仅消费当前 human 用户调动预览；需 `user:manage_party_scope`、`preview_token`、`reason`、`idempotency_key`，锁定并重算范围后写入回执和组织归属，立即失效缓存；状态漂移返回 `409 SCOPE_CHANGE_PREVIEW_STALE` |
| 用户显式主体范围读取 | `GET /api/v1/users/{user_id}/party-bindings` | 只读返回当前或全部显式 owner/manager 绑定；不提供 `/parties/users/*` 兼容入口 |
| 用户范围影响预览 | `POST /api/v1/users/{user_id}/party-bindings/preview` | 提议 `create|update|close` 一个绑定，验证目标 Party 已审核且启用，返回前后有效范围、当前绑定数量、是否回退组织、短期 opaque `preview_token` 和过期时间；不写入绑定 |
| 用户范围变更提交 | `POST /api/v1/users/{user_id}/party-bindings/commit` | 仅消费同一操作者、同一用户、状态仍一致的预览；请求必须含 `preview_token`、`reason`、`idempotency_key`。成功写入绑定、持久化前后范围与结果回执并失效用户范围缓存；过期、已消费或状态漂移统一返回 `409 SCOPE_CHANGE_PREVIEW_STALE`。原 `POST /api/v1/users/{user_id}/party-bindings`、`PUT/DELETE /api/v1/users/{user_id}/party-bindings/{binding_id}` 直写入口已退役，不得绕过预览/提交 |
| 用户范围批量预览/提交 | `POST /api/v1/users/party-bindings/batch/preview`、`POST /api/v1/users/party-bindings/batch/commit` | 预览接收 2-100 条唯一的 `{user_id, operation, ...}`，逐用户需要 `user:manage_party_scope`。首次提交只消费同一操作者的 token，必须有 `reason` 与 `idempotency_key`；同键重试从同一操作者的持久化回执恢复目标并重新授权，不依赖已消费 token。锁定并重算后在一个事务内全成全败，状态漂移返回 `409 SCOPE_CHANGE_PREVIEW_STALE` |
| 管理员查看用户有效范围 | `GET /api/v1/auth/users/{user_id}/party-scope` | `admin`、`system_admin`、`perm_admin` 可查看任意用户的统一诊断结果；`issues.node_ref` 仅向具备对应范围管理权限者返回，`perm_admin` 仍不能据此读取业务对象 |
| 角色管理 | `/api/v1/roles/*` | 角色定义、权限勾选、角色分配 |
| 数据策略 | `/api/v1/auth/data-policies/*` | ABAC 策略包、模板和角色绑定管理 |

用户管理主契约使用多角色语义，支持单用户分配多个角色。多角色权限默认取允许权限并集；显式拒绝授权或拒绝数据策略优先于允许结论。

`organization:manage_party_scope` 与 `user:manage_party_scope` 默认仅授予 `admin`、`system_admin`、`perm_admin`。`perm_admin` 可配置和诊断范围，但不得读取业务数据或授予业务角色；主体范围始终与角色动作权限取交集。

#### 4.2.1 用户组织调动请求/响应

预览请求体固定为 `{ "organization_id": "<target-organization-id>" }`。成功响应包含 `before_scope`、`after_scope`、`impact`、短期 opaque `preview_token` 和 `expires_at`；`impact` 至少包含 `organization_changed`、`scope_changed`、`current_explicit_binding_count`、`uses_explicit_party_scope_after` 和 `cache_invalidation_required`。预览不会修改用户、Organization 或范围缓存。

提交请求体固定为 `{ "preview_token": "...", "reason": "...", "idempotency_key": "..." }`。服务端只接受与当前操作者、用户、目标组织和状态指纹一致的未消费 token；提交时锁定用户与目标 Organization，重新校验完整启用链并用 `PartyScopeResolver` 重新计算范围。相同 `(user_id, actor_id, idempotency_key)` 重试返回首次 `organization_id`、前后范围、影响摘要和 `committed_at`，不会重复写入。

普通 `PUT /api/v1/auth/users/{user_id}` 不接受 `organization_id`；其 `is_active=true` 与 `POST /api/v1/auth/users/{user_id}/activate` 在启用 human 用户前都必须校验该用户已有完整、启用且未删除的 Organization 祖先链。`service/system` 账号不得通过本动作分配 Organization。
### 4.3 资产

| 能力 | 方法与路径 | 契约 |
|---|---|---|
| 资产列表 | `GET /api/v1/assets` | 支持分页、筛选、排序、搜索，并按主体范围过滤；产权主体筛选仅接受 Party 原生 ID `owner_party_id`，不调用已冻结的 Ownership 路由 |
| 资产详情 | `GET /api/v1/assets/{asset_id}` | 返回资产主数据和必要投影 |
| 创建资产 | `POST /api/v1/assets` | 创建草稿资产，需通过权限和数据范围校验；`owner_party_id` 必填；`asset_code` 由系统按产权方编码段自动生成、只读，不接受客户端写入（ADR-0017，已实施） |
| 更新资产 | `PATCH /api/v1/assets/{asset_id}` | 审核态关键字段受控，需版本冲突保护 |
| 删除资产 | `DELETE /api/v1/assets/{asset_id}` | 逻辑删除，存在关联约束时拒绝 |
| 恢复资产 | `POST /api/v1/assets/{asset_id}/restore` | 恢复逻辑删除资产 |
| 批量操作 | `/api/v1/assets/batch-*` | 支持批量相关操作 |
| 导入资产 | `/api/v1/assets/import` | 支持模板校验和导入；**导入行必须有可解析到既有产权方 Party 的 owner，无主行直接拒绝**（对齐 ADR-0010 owner 内在必填、ADR-0017 编号生成前置，已实施）；导入 create 走与手动创建共享的 owner 必填校验，不直接裸调 crud；`asset_code` 系统生成、模板不含该列 |
| 资产变更历史 | `GET /api/v1/assets/{asset_id}/history` | 分页返回资产变更历史（`items` + `pagination`）；支持按 `operation_type` 过滤（`change_type` 查询参数）；每条记录含 `change_type`、`changed_fields` 增强字段（由基础字段回填） |
| 资产附件 | `/api/v1/assets/{asset_id}/attachments/*` | 管理资产附件 |
| 资产产权证 | `/api/v1/assets/{asset_id}/property-certificates/*` | 资产详情内维护产权证：列表、详情、新增、编辑、附件、轻量在线预览、扫描件解析预填。字段契约、5 项保存硬门槛、附件规则（类型/大小/上传不自动解析/预览/下载独立权限/日志/疑似重复/资产与附件 ≥1 下限）与 `warning` 风险派生见 domain-model §4.20（PropertyCertificate）、§4.21（权利人关系）、§4.22（Attachment）。**证号重复（端点专属契约）**：当前资产上下文提交的证号已存在时返回 409、既有产权证 ID/`asset_ids`/摘要与「当前资产详情页追加关联」确认目标，不创建新记录、不自动追加资产或附件；解析会话中的暂存扫描件作为既有产权证附件候选，须在同一确认端点显式选择是否追加，取消追加即清理暂存文件；若既有产权证 `attachment_ids` 为空则不得取消追加。保存闸门须按 domain-model §4.20 的 5 项校验，不得用解析字段校验器 `validate_extracted_fields` 代替、不得漏卡资产/附件/权利人 |
| 产权证附件列表/追加 | `GET/POST /api/v1/property-certificates/{certificate_id}/attachments` | 通用 `Attachment(owner_type=property_certificate)` 的域内入口；POST 接收一个或多个 PDF/JPEG/PNG，并按文件返回成功附件或可预期校验失败，不自动解析。列表要求 `property_certificate:read`，追加要求 `property_certificate:update` |
| 产权证附件替换/删除 | `PUT/DELETE /api/v1/property-certificates/{certificate_id}/attachments/{attachment_id}` | 替换不留旧版本；删除最后一份拒绝。要求 `property_certificate:update` / `property_certificate:delete`，并校验产权证-附件完整 owner 链 |
| 产权证附件预览/下载 | `GET /api/v1/property-certificates/{certificate_id}/attachments/{attachment_id}/preview`、`GET /api/v1/property-certificates/{certificate_id}/attachments/{attachment_id}/download` | 预览要求 `property_certificate:read` 且不单独记日志；下载使用独立 `property_certificate:export`，并记不含路径或 PII 的轻量日志 |
| 产权证扫描件解析 | `POST /api/v1/extraction-sessions`（新建暂存上传）和 `POST /api/v1/extraction-sessions`（既有正式附件引用） | 新建临时上传一份 PDF/JPEG/PNG；既有模式只引用通用附件、不接收文件。确认、取消与逐字段人工动作见 §4.10；`should_create_new_asset` / `create_new_asset` 不属于 MVP |
| 租赁摘要 | `GET /api/v1/assets/{asset_id}/lease-summary` | 按上游、下游、委托、直租展示租赁情况 |
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
| 合同扫描件解析 | `/api/v1/extraction-sessions/*` | 上传合同扫描件后解析合同编号、主体、资产、期间、金额、租金或服务费条款，返回字段候选值、置信度、轻量来源证据、候选匹配、匹配提示和字段来源候选；必须人工确认后创建或更新合同补录；主体候选仅限已审核 Party，资产候选仅限既有资产，候选不得自动绑定；主体未匹配已审核 Party 时只返回提示，不直接创建 Party 或写入合同主体引用；资产未匹配既有资产时只返回提示，不直接创建或绑定新资产 |
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
| 主体业务角色切片 | `GET /api/v1/parties?business_role=owner|operator|terminal_tenant` | 在既有主体列表分页、搜索和数据范围契约上增加服务端当前角色筛选；响应返回 `business_roles`。省略参数为“全部”，同一 Party 在全部列表仅一行；角色只按当前有效资产、项目和合同/协议关系派生，不将 `customer_type`、用户主体绑定或历史合同角色用于筛选。 |
| 主体创建 | `POST /api/v1/parties` | 只接受 `legal_entity` / `individual`、名称、正式统一标识和外部引用等业务字段；法人标识类型限 `unified_social_credit_code|legal_registration_number|foreign_registration_number`，自然人限 `national_id|passport`；`code` 由服务端生成且拒绝客户端写入 |
| 主体更新 | `PUT /api/v1/parties/{party_id}` | 更新草稿或已驳回 Party 的主档业务字段；拒绝 status，已审核 Party 的启停只能走专用动作 |
| 主体导入 | `POST /api/v1/parties/import` | 初始化批量导入法人主体或自然人；服务端生成编码，统一标识进入专用字段，不接受 `organization` 类型 |
| 主体审核 | `/api/v1/parties/{party_id}/submit-review|approve-review|reject-review` | 主体审核状态流转：`draft → pending → approved`，驳回写入 `rejected`；提审前统一标识必须成对、格式正确且唯一，不提供 Asset 式 `reverse-review` 反审端点 |
| 主体启停影响预览 | `POST /api/v1/parties/{party_id}/status/preview` | 请求体只接受 operation=deactivate|reactivate；仅已审核 Party 可预览，响应返回前后状态、组织/用户范围/业务引用影响、短期 preview_token 与过期时间，不提交状态变更 |
| 主体停用/重新启用 | `POST /api/v1/parties/{party_id}/deactivate|reactivate` | 请求体必须携带预览 token、原因和幂等键；重新锁定 Party 并复算影响，漂移返回 409 SCOPE_CHANGE_PREVIEW_STALE。成功写审核日志和持久化回执，重复幂等键返回首次响应 |
| 代表组织反查 | `GET /api/v1/parties/{party_id}/organizations` | 返回直接代表该 Party 的 Organization 只读列表，不提供主体详情侧编辑 |
| 主体联系人 | `GET/POST /api/v1/parties/{party_id}/contacts` | 维护主体主档下的联系人；联系人不提供通用实体联系人写入口 |

合同补录和产权证权利人引用的主体必须来自已审核 Party；新增业务引用、Organization 代表关系和用户范围绑定还要求目标 Party 启用。`PartyHierarchy` 及其 API 不属于目标契约。

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

分析端点公开接收 `view_mode=owner|manager|all`。不传时，有效范围仅含一种视角则自动采用；双视角则解析为内部 `scope_mode=all`，不从绑定顺序或展示偏好猜选。常规客户列表可使用混合并集视图；综合分析和分析导出产出客户双指标，必须选定 owner 或 manager 单一视角。

### 4.10 扫描件解析辅助补录

| 能力 | 方法与路径 | 契约 |
|---|---|---|
| 创建合同解析会话 | `POST /api/v1/extraction-sessions` | 合同上传使用单件临时会话。只接受明确的合同上下文与一份 PDF；`revenue_mode=lease` 仅允许 `上游/下游`，`revenue_mode=agency` 仅允许 `委托/直租`，不兼容组合在暂存文件或启动解析前返回 `422`；不提供草稿创建或恢复。 |
| 创建产权证解析会话 | `POST /api/v1/extraction-sessions` | 新建产权证绑定资产上下文并暂存恰好一份 PDF/JPEG/PNG；确认前不创建产权证、关系或正式附件。 |
| 创建已有产权证附件复核 | `POST /api/v1/extraction-sessions` | 只接受明确的资产和该产权证所属通用附件引用，不接收文件；要求产权证读取权限，并完整校验资产-产权证-附件 owner 链。 |
| 查询产权证解析状态 | `GET /api/v1/extraction-sessions/{session_id}` | 返回候选字段、置信度和轻量来源证据；不返回对象全量字段、不提供一键或批量采纳。 |
| 确认产权证新建或冲突关联 | `POST /api/v1/extraction-sessions/{session_id}/confirm` | 只提交五类逐字段人工动作和显式选择的已审核 Party；新建满足五项硬门槛后，以可补偿文件晋升和数据库事务创建产权证、关系及通用附件。证号冲突返回 409 并保留会话，只允许显式关联已有产权证及选择是否追加暂存附件。要求创建权限。 |
| 确认已有产权证附件复核 | `POST /api/v1/extraction-sessions/{session_id}/confirm` | 只提交逐字段人工动作，不创建 Party、Asset、产权证、关系或附件；会话必须绑定同一产权证和既有正式附件，要求读取权限。 |
| 取消产权证解析会话 | `POST /api/v1/extraction-sessions/{session_id}/cancel` | 取消新建会话会清理暂存文件；已有正式附件复核只删除临时会话，不删除正式附件。 |
| Query extraction capabilities | `GET /api/v1/document-extraction/capabilities` | Returns target types, input methods, and public limits without provider or engine details: contract PDFs are at most 50 MiB and 50 pages; optional DeepSeek text enrichment uses consecutive batches of at most 20 pages; property-certificate PDFs remain at most 20 pages. |
解析会话语义统一见 domain-model §2「字段来源」「扫描件解析确认」与 §4.23 ScanExtractionSession：临时不留档、无草稿 / 历史档案、失败 / 超时可重新创建会话或完全手工补录、低置信逐项处理、候选不自动绑定或覆盖、未匹配已审核 Party 或既有资产只提示不在确认动作中创建、不持久化解析工具 / 模型 / 置信度 / 页码 / 截图等元信息、字段来源枚举不拆子类型；产品级规则见 PRD §6.5。合同补录须保留 ≥1 盖章扫描件；新建产权证的暂存文件只在确认成功后晋升为通用附件，正式产权证须 ≥1 附件且 ≥1 既有资产关联。

### 4.11 审批（MVP 已删除）

资产路由审批 API（`/api/v1/approval/*`）连同 `ApprovalInstance` 机制一并删除。资产审核改由 §4.3「审核动作」(`/api/v1/assets/{asset_id}/submit-review|approve-review|...`) 的 `review_status` 两步生命周期承接，确认按复核权限门控、不限制审核人 ≠ 提交人。详见 `docs/architecture/ADR-0002-asset-review-no-approval-workflow.md`（含 2026-06-10 取消职责互斥的决策更新）。

### 4.12 系统管理

| 能力 | 方法与路径 | 契约 |
|---|---|---|
| 组织管理 | `/api/v1/organizations/*` | 内部组织创建、资料编辑、查询与启停；普通编辑不得修改 `parent_id` 或代表 Party 字段。停用组织前必须先处理启用子组织和 human 用户，不级联停用 |
| 组织代表主体影响预览 | `POST /api/v1/organizations/{organization_id}/party-scope/preview` | 预览直接关联、解除或视角切换对本组织、继承子树和用户的影响；组织移动使用独立预览端点 |
| 组织代表主体变更 | `PUT /api/v1/organizations/{organization_id}/party-scope` | 仅允许关联已审核启用法人 Party 与 owner/manager 视角；需 `organization:manage_party_scope` 并遵循 §3.3，记录前后值、立即失效缓存。空关系表示继承，不按名称、编码或 `external_ref` 自动关联 |
| 组织移动影响预览/提交 | `POST /api/v1/organizations/{organization_id}/move/preview`、`POST /api/v1/organizations/{organization_id}/move` | 移动导致直接或继承范围变化时需 `organization:manage_party_scope` 并遵循 §3.3；提交重新校验整棵受影响子树，普通组织更新不能改 `parent_id` 绕过该动作 |
| 组织代表主体批量预览/提交 | `POST /api/v1/organizations/party-scope/batch/preview`、`POST /api/v1/organizations/party-scope/batch/commit` | 预览接收 2-100 条唯一的 `{organization_id, represented_party_id, represented_party_perspective}`；同批禁止祖先/子孙重叠，逐 Organization 需要 `organization:manage_party_scope`。首次提交只消费同一操作者的 token，必须有 `reason` 与 `idempotency_key`；同键重试从同一操作者的持久化回执恢复目标并重新授权，不依赖已消费 token。锁定并重算后在一个事务内全成全败，状态漂移返回 `409 SCOPE_CHANGE_PREVIEW_STALE`，不按候选匹配结果自动授权 |
| 数据字典 | `/api/v1/system/dictionaries/*` | 字典分类和字典项维护 |
| 系统基础 | `/api/v1/system/health`、`/api/v1/system/info`、`/api/v1/system/root` | MVP 仅保留最小健康检查和系统信息；复杂 monitoring API 不作为产品能力暴露 |
| 通知 | `/api/v1/notifications/*` | 站内通知查询与处理（仅已读/未读，无处理闭环）；业务提醒生成时调用统一解析器并按有效主体范围过滤接收人（仅可见该对象 owner/operator 范围者），系统通知豁免范围过滤但须内容中立（`admin`/`system_admin` 发，见 domain-model §4.24）。业务通知仅覆盖合同/协议即将到期、合同/协议已到期、终端租户租金到期、终端租户租金逾期；运营方成本未付和服务费未收不生成逾期通知。档位幂等去重、优先级档位派生、系统通知生产者、企业微信按 `recipient_id` 定向应用消息（删群广播）等机制见 domain-model §4.24 Notification；ADR-0015 与系统通知生产者已实施。ADR-0016 代码已接企业微信应用消息并通过 `gettoken` 凭据验证，真实发送待企业微信可信 IP / 域名配置；正式用户 ↔ 企业微信 `userid` 映射仍待实施。 |

## 5. 错误与边界约定

| 场景 | 契约 |
|---|---|
| 未登录 | 返回 401 |
| 无权限 | 返回 403 |
| 主体范围缺失 | 返回 403，错误码 `PARTY_SCOPE_MISSING` |
| 所属组织或继承链无效 | 返回 403，错误码 `PARTY_SCOPE_INVALID_ORGANIZATION` |
| 组织直接配置 Party 无效 | 返回 403，错误码 `PARTY_SCOPE_INVALID_PARTY` |
| 当前应生效的显式绑定目标无效且无其他有效显式范围 | 返回 403，错误码 `PARTY_SCOPE_INVALID_BINDING`；不得回退组织 |
| 资源不存在 | 返回 404 |
| 乐观锁冲突 | 返回 409 |
| 敏感范围变更预览过期或状态漂移 | 返回 409，错误码 `SCOPE_CHANGE_PREVIEW_STALE`，不执行任何写入 |
| 业务规则冲突 | 返回明确业务错误和可读原因 |
| 校验失败 | 返回字段级校验信息 |
| 重复幂等请求 | 不重复创建记录，不重复产生副作用 |

组织代表主体单组织变更的具体请求/响应契约如下：

- `POST /api/v1/organizations/{organization_id}/party-scope/preview` 请求体必须同时提供 `represented_party_id` 和 `represented_party_perspective` 两个键；二者同时为 `null` 表示解除直接关系并继承，二者同时非空表示直接关联。`represented_party_id` 只能指向 `approved + active + legal_entity` Party，视角只能为 `owner` 或 `manager`。
- 预览响应返回 `organization_id`、`before_scope`、`after_scope`、`impact`、opaque `preview_token` 和 `expires_at`。范围状态包含直接关系、有效 Party、有效视角及来源 Organization；影响摘要包含 `organization_count`、`organization_scope_change_count`、`user_count` 和 `user_scope_change_count`。
- `PUT /api/v1/organizations/{organization_id}/party-scope` 请求体为 `preview_token`、非空 `reason`（最多 500 字符）和非空 `idempotency_key`（最多 128 字符）。提交只接受当前操作者签发、目标组织和规范化提议匹配的 token；token 一次性消费，陈旧或状态漂移返回 409 并要求重新预览。
- 提交响应返回更新后的 `organization`、前后范围、影响摘要、`committed_at` 和 `idempotent`。服务端将原因、前后值写入 `OrganizationHistory`，并用持久化回执支撑相同幂等键的重试；本端点不提供自动关联。
- `POST /api/v1/organizations/{organization_id}/move/preview` 请求体必须显式提供 `target_parent_id`；字符串表示目标父 Organization，`null` 表示迁移为根 Organization。预览拒绝源节点停用、目标父链缺失/停用/删除/环、目标位于当前子树或无变化提议；响应返回迁移节点的前后父级和有效 Party 范围、子树路径/范围及 active human 用户影响、opaque `preview_token` 和 `expires_at`，不写入组织。
- `POST /api/v1/organizations/{organization_id}/move` 请求体为 `preview_token`、非空 `reason`（最多 500 字符）和非空 `idempotency_key`（最多 128 字符）。提交需要 `organization:manage_party_scope`，锁定受影响子树及旧/新祖先链后重新解析范围；同一事务更新 `parent_id`、整棵子树 `level/path`、组织历史和 `organization_move_commits` 回执。token 过期、已消费或范围/状态漂移统一返回 `409 SCOPE_CHANGE_PREVIEW_STALE`，不产生部分写入；普通 `PUT /api/v1/organizations/{organization_id}` 不接受 `parent_id`。

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
