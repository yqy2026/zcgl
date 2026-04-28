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
| 分析视图 | 分析和大屏端点使用 `view_mode` 指定 owner 或 manager 口径 |
| 搜索 | 搜索结果必须经过权限和数据范围过滤 |
| CSRF | 状态变更请求必须携带 CSRF token |
| 幂等 | 批量更新、补偿任务、审批回调等关键写操作必须幂等 |
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

用户管理主契约使用多角色语义，支持单用户分配多个角色。

### 4.3 资产

| 能力 | 方法与路径 | 契约 |
|---|---|---|
| 资产列表 | `GET /api/v1/assets` | 支持分页、筛选、排序、搜索，并按主体范围过滤 |
| 资产详情 | `GET /api/v1/assets/{asset_id}` | 返回资产主数据和必要投影 |
| 创建资产 | `POST /api/v1/assets` | 创建草稿资产，需通过权限和数据范围校验 |
| 更新资产 | `PATCH /api/v1/assets/{asset_id}` | 审核态关键字段受控，需版本冲突保护 |
| 删除资产 | `DELETE /api/v1/assets/{asset_id}` | 逻辑删除，存在关联约束时拒绝 |
| 恢复资产 | `POST /api/v1/assets/{asset_id}/restore` | 恢复逻辑删除资产 |
| 批量操作 | `/api/v1/assets/batch-*` | 支持批量相关操作 |
| 导入资产 | `/api/v1/assets/import` | 支持模板校验和导入 |
| 资产附件 | `/api/v1/assets/{asset_id}/attachments/*` | 管理资产附件 |
| 租赁摘要 | `GET /api/v1/assets/{asset_id}/lease-summary` | 按上游、下游、委托、直租展示租赁情况 |
| 经营方历史 | `GET /api/v1/assets/{asset_id}/management-history` | 返回经营方变更历史 |
| 项目历史 | `GET /api/v1/assets/{asset_id}/project-history` | 返回项目关系历史 |
| 审核动作 | `/api/v1/assets/{asset_id}/submit-review|approve-review|reject-review|reverse-review|resubmit-review|withdraw-review` | 资产审核状态流转 |
| 审核日志 | `GET /api/v1/assets/{asset_id}/review-logs` | 返回资产审核日志 |

### 4.4 项目

| 能力 | 方法与路径 | 契约 |
|---|---|---|
| 项目列表 | `GET /api/v1/projects` | 支持分页、筛选、搜索，并按主体范围过滤 |
| 项目详情 | `GET /api/v1/projects/{project_id}` | 返回项目主数据 |
| 创建项目 | `POST /api/v1/projects` | 项目必须绑定运营管理方 |
| 更新项目 | `PATCH /api/v1/projects/{project_id}` | 更新项目主数据 |
| 删除项目 | `DELETE /api/v1/projects/{project_id}` | 逻辑删除 |
| 当前有效资产 | `GET /api/v1/projects/{project_id}/assets` | 返回项目当前有效资产汇总 |

### 4.5 合同组与合同

| 能力 | 方法与路径 | 契约 |
|---|---|---|
| 合同组列表 | `GET /api/v1/contract-groups` | 支持主体范围过滤和业务筛选 |
| 合同组详情 | `GET /api/v1/contract-groups/{group_id}` | 返回合同组、主体、资产和合同信息 |
| 创建合同组 | `POST /api/v1/contract-groups` | 同组只能选择一种经营模式，一个资产不关联多个有效合同组 |
| 更新合同组 | `PATCH /api/v1/contract-groups/{group_id}` | 更新合同组主数据和关联信息 |
| 合同详情 | `GET /api/v1/contracts/{contract_id}` | 返回合同基表和类型明细 |
| 合同提审 | `POST /api/v1/contracts/{contract_id}/submit-review` | 草稿合同进入待审 |
| 合同通过 | `POST /api/v1/contracts/{contract_id}/approve` | 合同生效并生成台账 |
| 合同驳回 | `POST /api/v1/contracts/{contract_id}/reject` | 合同退回草稿 |
| 合同到期 | `POST /api/v1/contracts/{contract_id}/expire` | 合同自然到期 |
| 合同终止 | `POST /api/v1/contracts/{contract_id}/terminate` | 合同提前终止，原因必填 |
| 合同作废 | `POST /api/v1/contracts/{contract_id}/void` | 无台账或台账已处理后作废 |
| 纠错 | `POST /api/v1/contracts/{contract_id}/start-correction` | 发起作废、冲销和重建流程 |
| 审计日志 | `GET /api/v1/contracts/{contract_id}/audit-logs` | 返回合同审计日志 |
| 组联审 | `POST /api/v1/contract-groups/{group_id}/submit-review` | 关键变更触发同组联审 |

MVP 不提供续签端点。到期后继续合作按新签流程创建合同组和合同。

### 4.6 台账

| 能力 | 方法与路径 | 契约 |
|---|---|---|
| 合同台账 | `GET /api/v1/contracts/{contract_id}/ledger` | 查询单合同台账 |
| 批量更新 | `PATCH /api/v1/contracts/{contract_id}/ledger/batch-update-status` | 批量更新支付状态和实收金额，必须幂等 |
| 台账查询 | `GET /api/v1/ledger/entries` | 支持跨合同按资产、主体、时间区间查询 |
| 台账导出 | `GET /api/v1/ledger/entries/export` | 导出台账查询结果 |
| 台账重算 | `POST /api/v1/contracts/{contract_id}/ledger/recalculate` | 对受影响区间作废并重建 |
| 补偿任务 | `POST /api/v1/ledger/compensation/run` | 扫描并补齐缺失台账，必须幂等 |

多资产合同按合同级金额返回，不做资产级金额拆分；项目或主体汇总时按合同和账期去重。

### 4.7 客户与主体

| 能力 | 方法与路径 | 契约 |
|---|---|---|
| 客户详情 | `GET /api/v1/customers/{party_id}` | 返回客户基础信息、风险标签、历史签约和统计 |
| 主体列表 | `GET /api/v1/parties` | 查询主体主档 |
| 主体创建 | `POST /api/v1/parties` | 创建主体草稿 |
| 主体更新 | `PATCH /api/v1/parties/{party_id}` | 更新主体主档 |
| 主体导入 | `POST /api/v1/parties/import` | 初始化批量导入主体 |
| 主体审核 | `/api/v1/parties/{party_id}/submit-review|approve-review|reject-review` | 主体审核状态流转 |
| 主体绑定 | `/api/v1/parties/users/{user_id}/party-bindings*` | 维护用户和主体绑定关系 |

合同进入待审前，关联主体必须已审核通过。

### 4.8 搜索

| 能力 | 方法与路径 | 契约 |
|---|---|---|
| 全局搜索 | `GET /api/v1/search` | MVP 覆盖资产、项目、合同组、合同、客户 |

搜索结果支持全部视图和按对象分组视图。默认排序为相关度优先，同分时按业务置顶规则排序。未授权对象不返回。

### 4.9 分析与统计

| 能力 | 方法与路径 | 契约 |
|---|---|---|
| 综合分析 | `GET /api/v1/analytics/comprehensive` | 返回收入拆分、客户双指标、实收和收缴率 |
| 分析导出 | `GET /api/v1/analytics/export` | 导出带统计口径版本的结果 |
| 统计报表 | `/api/v1/statistics/*` | 提供基础、面积、财务、出租率、分布、趋势等统计能力 |

分析端点可接收 `view_mode=owner|manager`，不传时按用户绑定自动回落。

### 4.10 PDF 文档处理

| 能力 | 方法与路径 | 契约 |
|---|---|---|
| PDF 上传 | `/api/v1/pdf-upload/*` | 上传 PDF 文件 |
| PDF 导入 | `/api/v1/pdf-import/*` | 抽取、校验、确认落库 |
| PDF 批量 | 批量上传、状态、取消、清理 | 支持整体进度和失败重试 |

抽取失败支持手动重试；AI 抽取结果确认前可人工修正；单文件超时进入失败队列。

### 4.11 审批

| 能力 | 方法与路径 | 契约 |
|---|---|---|
| 发起审批 | `POST /api/v1/approval/processes/start` | 发起资产审批实例 |
| 待办查询 | `GET /api/v1/approval/tasks/pending` | 查询当前用户待办 |
| 我发起的流程 | `GET /api/v1/approval/processes/mine` | 查询当前用户发起的流程 |
| 流程时间线 | `GET /api/v1/approval/processes/{id}/timeline` | 查询审批时间线 |
| 通过 | `POST /api/v1/approval/tasks/{task_id}/approve` | 通过审批 |
| 驳回 | `POST /api/v1/approval/tasks/{task_id}/reject` | 驳回审批 |
| 撤回 | `POST /api/v1/approval/tasks/{task_id}/withdraw` | 撤回审批 |

第一阶段只承接资产审批，不接入通用 BPM 引擎。

### 4.12 系统管理

| 能力 | 方法与路径 | 契约 |
|---|---|---|
| 组织管理 | `/api/v1/organizations/*` | 组织 CRUD 和组织上下文绑定维护 |
| 数据字典 | `/api/v1/system/dictionaries/*` | 字典分类和字典项维护 |
| 系统基础 | `/api/v1/monitoring/health`、`/api/v1/system/info`、`/api/v1/system/root` | 健康检查和系统信息 |
| 通知 | `/api/v1/notifications/*` | 站内通知查询与处理 |

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
| 产权证管理 | 待补齐正式需求后激活 |
| 权属方管理 | 待补齐正式需求后激活 |
| 通用 BPM 引擎 | MVP 不建设通用审批流引擎 |
| 财务总账和支付结算 | 不属于当前产品边界 |
| 用户侧物理删除 | 关键业务记录不提供物理删除入口 |

## 7. 维护规则

- 新增 API 必须同步本文档。
- API 字段语义变更必须同步 `docs/specs/domain-model.md`。
- API 实现状态和证据变化只同步 `docs/traceability/requirements-trace.md`。
- 本文档不得记录实现文件路径、测试文件路径或历史迁移过程。
