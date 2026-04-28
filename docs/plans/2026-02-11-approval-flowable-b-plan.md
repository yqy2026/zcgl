# B 方案完整实施计划：Flowable 编排内核 + 业务系统任务中心

## Status

⏸ Deferred

## 1) 方案摘要（最终定版）
采用 **B 方案**：
- **Flowable** 仅负责流程建模与执行（BPMN、任务流转、历史实例）。
- **FastAPI** 负责业务规则、权限、统一 API、任务聚合、审计与通知。
- **React 前端** 在你们系统展示“我的待办/已办/流程轨迹”；流程设计与发布首期使用 Flowable 现成 UI。

该方案目标是：既拿到成熟流程能力，又保持你们系统对业务与权限的主导权，避免前端和权限体系被流程引擎绑定。

---

## 2) 范围与非范围

### 首期范围
- 业务域：资产关键变更审批（可扩展模板到合同/产权证）。
- 能力：发起、待办、审批通过、驳回、撤回、轨迹、催办、抄送（抄送可先做只读）。
- 配置：可视化流程定义、版本发布、按组织/金额/资产类型选择流程。

### 非范围（首期不做）
- 自研 BPMN 设计器。
- 跨系统分布式补偿编排平台。
- 所有业务域一次性接入。

---

## 3) 架构决策（必须遵守）
- **单一写入口**：审批动作统一走 `FastAPI`，前端不直连 Flowable 审批接口。
- **双存储职责分离**
  - Flowable DB：流程运行态与流程历史（标准引擎数据）。
  - 业务 DB：审批业务绑定、任务镜像、动作审计、通知。
- **一致性策略**：业务库作为“业务真相源”，Flowable 作为“流程真相源”；通过幂等同步与对账任务消除漂移。
- **接口幂等**：所有写操作强制 `idempotency_key`。
- **权限来源**：复用现有 RBAC，不在 Flowable 重建一套业务权限。

---

## 4) 公共接口/类型变更（决策完成）

### 4.1 新增后端 API（统一前缀 `/api/v1/approval`）
- `POST /processes/start`
  - 入参：`business_type`, `business_id`, `action_type`, `payload`, `idempotency_key`
  - 出参：`process_instance_id`, `approval_no`, `status`
- `GET /processes/{business_type}/{business_id}`
  - 查询当前审批状态、当前节点、发起人、开始时间、结束时间
- `GET /tasks/pending`
  - 入参：分页、筛选（流程定义、业务类型、紧急级别）
  - 出参：待办列表（来自任务镜像表，不直接透传 Flowable 原始结构）
- `GET /tasks/done`
- `POST /tasks/{task_id}/approve`
  - 入参：`comment`, `variables`, `idempotency_key`
- `POST /tasks/{task_id}/reject`
  - 入参：`comment`, `reject_to`（固定上一步/发起人）
- `POST /tasks/{task_id}/withdraw`
  - 仅发起人在“首节点未处理/流程策略允许”时可用
- `GET /processes/{process_instance_id}/timeline`
  - 审批时间线（聚合业务动作日志 + 流程历史）
- `POST /tasks/{task_id}/urge`
  - 催办，触发通知

### 4.2 新增后端内部接口（仅服务间）
- `POST /internal/approval/flowable/events`
  - 接收 Flowable webhook（若启用回调）
- `POST /internal/approval/sync/pull`
  - 手动触发增量拉取（运维排障）

---

## 5) 数据模型设计（业务库）

新增表（命名可按你们规范微调）：

### `approval_instance`
- 关键字段：`id`, `approval_no`, `business_type`, `business_id`, `process_def_key`, `process_def_version`, `process_instance_id`, `status`, `starter_id`, `current_node`, `started_at`, `ended_at`, `tenant_id(optional)`
- 约束：`(business_type, business_id, status in running)` 唯一（避免并发重复发起）

### `approval_task_snapshot`
- 关键字段：`id`, `flowable_task_id`, `process_instance_id`, `task_name`, `assignee_id`, `candidate_groups`, `priority`, `due_at`, `status`, `created_at`, `completed_at`
- 索引：`assignee_id+status`, `process_instance_id+status`

### `approval_action_log`
- 关键字段：`id`, `flowable_task_id`, `process_instance_id`, `action`, `operator_id`, `comment`, `variables_json`, `idempotency_key`, `created_at`
- 约束：`idempotency_key` 唯一

### `approval_flow_binding_rule`
- 关键字段：`id`, `business_type`, `rule_name`, `condition_expr`, `process_def_key`, `enabled`, `priority`, `effective_from`, `effective_to`

---

## 6) Flowable 侧定义（固定规范）
- 流程 key 规范：`asset_change_v1`、`asset_dispose_v1`（业务域+动作+版本）
- 变量规范：
  - 必填：`businessType`, `businessId`, `starterId`, `starterDeptId`, `amount(optional)`, `riskLevel(optional)`
  - 审批变量：`approved`（bool）, `approvalComment`, `nextAssignee(optional)`
- 用户/组映射：
  - Flowable 候选组命名：`rbac:{role_code}`，由后端映射并同步
- 节点设计约束：
  - 每流程至少包含：发起 -> 审批节点 -> 结束
  - 驳回路径必须显式定义（回发起人或回上一节点）

---

## 7) 核心流程（时序）

### 7.1 发起审批
1. 前端提交业务动作到后端。
2. 后端校验 `requires_approval`、权限、业务状态可流转。
3. 后端落库 `approval_instance(status=starting)`。
4. 后端调用 Flowable 启动流程（携带业务变量）。
5. 成功后更新 `approval_instance(status=running, process_instance_id=...)`。
6. 同步首批待办到 `approval_task_snapshot`，创建 `approval_pending` 通知。

### 7.2 审批动作
1. 前端调用后端 `approve/reject/withdraw`。
2. 后端校验操作者是否 assignee/candidate + 业务约束。
3. 后端写 `approval_action_log`（幂等键去重）。
4. 后端调用 Flowable 完成任务。
5. 拉取最新任务与流程状态，更新快照与通知。
6. 流程结束时回写业务单据终态（approved/rejected）。

### 7.3 对账与修复
- 定时任务每 5 分钟比对：
  - `approval_instance.status` vs Flowable 实例状态
  - `approval_task_snapshot` vs Flowable 活动任务
- 不一致时：自动修复一次；失败则告警+生成运维任务。

---

## 8) 权限与安全策略
- 权限点新增：
  - `approval.process.start`
  - `approval.task.approve`
  - `approval.task.reject`
  - `approval.task.withdraw`
  - `approval.task.view_all`
  - `approval.flow.manage`（仅流程管理员）
- 审批意见默认入审计；若含敏感信息按现有加密策略落库。
- Flowable 管理端仅内网或 VPN 访问；管理账户接入 SSO（若当前无法做，首期至少强密码+IP 白名单）。
- 后端调用 Flowable 使用服务账号与最小权限。

---

## 9) 前端改造范围（你们系统）
- 新增菜单：
  - `审批中心/我的待办`
  - `审批中心/我的已办`
  - `审批中心/我发起的`
- 业务详情页增加：
  - 审批状态条（当前节点、耗时）
  - 时间线（发起、审批意见、结果）
- 操作按钮：
  - 审批通过 / 驳回 / 撤回 / 催办（按权限与状态显隐）
- 不首期自研流程设计器，仅在管理后台放 Flowable 入口（外链或嵌入）。

---

## 10) 运维部署（Docker Compose）
- 新增服务：
  - `flowable-rest`
  - `flowable-task`（若采用 UI 组件）
  - `flowable-modeler`（流程配置）
  - `postgres_flowable`（或主库独立 schema）
- 环境变量新增（后端）：
  - `FLOWABLE_BASE_URL`
  - `FLOWABLE_USERNAME`
  - `FLOWABLE_PASSWORD`
  - `FLOWABLE_TIMEOUT_MS`
  - `APPROVAL_SYNC_INTERVAL_SEC`
- 日志链路：
  - 全链路统一 `trace_id` + `process_instance_id` + `business_id`
- 监控指标：
  - 流程启动成功率、任务处理耗时 P95、审批超时数、同步失败数、对账不一致数

---

## 11) 测试计划与验收场景

### 11.1 单元测试
- 规则匹配（`approval_flow_binding_rule`）
- 权限校验（可审批/不可审批）
- 幂等（重复 `idempotency_key` 不重复执行）
- 状态机合法流转（防越权跳转）

### 11.2 集成测试
- 发起 -> 待办 -> 通过 -> 业务状态更新
- 发起 -> 待办 -> 驳回 -> 业务回退
- 重复提交、并发审批、Flowable 短暂不可用重试恢复
- 对账任务自动修复漂移

### 11.3 E2E
- 申请人提交审批并查看进度
- 审批人处理待办并查看历史
- 管理员查看全局审批统计

### 11.4 验收标准
- 首期资产审批主链路通过率 >= 99%（测试环境回归集）
- 任一审批动作均可追溯“人+时间+意见+结果”
- 不存在未告警的状态不一致超过 10 分钟

---

## 12) 实施里程碑（可执行）
- **第 1 周**：Flowable 环境接入、连通性、认证方式、最小流程发布
- **第 2 周**：后端审批域模型 + `start/query` API + 规则匹配
- **第 3 周**：任务镜像、`approve/reject/withdraw`、通知联动
- **第 4 周**：前端审批中心页面、时间线、权限显隐
- **第 5 周**：对账修复、压测、灰度发布、运维手册
- **第 6 周**：资产域稳定后模板化扩展到合同/产权证

---

## 13) 代码落点（实现指引）
- 后端新增模块建议：
  - `backend/src/models/approval.py`
  - `backend/src/schemas/approval.py`
  - `backend/src/crud/approval.py`
  - `backend/src/services/approval/flowable_client.py`
  - `backend/src/services/approval/approval_service.py`
  - `backend/src/api/v1/system/approval.py`
- 路由接入：
  - 在 `api/v1` 汇总路由中 include `approval` 模块，保持 `/api/v1/*`
- 迁移：
  - Alembic 新增审批三张核心表 + 规则表 + 索引
- 文档：
  - 新增 `docs/guides/approval-flowable-integration.md`
- 变更记录：
  - 每次落地按要求更新 `CHANGELOG.md`

---

## 14) 明确假设与默认值（已锁定）
- 接受独立 Flowable 服务部署。
- 优先纯开源可控（Flowable 社区版能力优先）。
- 首期流程可视化配置使用 Flowable 现成 UI，不首期自研设计器。
- 审批统一走后端代理，前端不直连 Flowable 写接口。
- 首期覆盖资产关键变更，后续按模板复制到其他业务域。
