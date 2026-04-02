# REQ-APR-001 资产审批流第一阶段实施计划

> 状态：✅ 已完成
> 关联需求：REQ-APR-001
> 目标：交付资产域审批流第一阶段后端最小闭环，在不接入 Flowable 真服务、不建设前端审批中心的前提下，完成审批实例创建、待办快照、审批动作、站内待办通知与资产审核状态联动。

## 1. 当前现状

### 已有基础
- 资产域已经具备独立审核状态机与审计日志：
  - `backend/src/services/asset/asset_service.py`
  - `backend/src/models/asset_review_log.py`
- 站内通知体系已经支持 `approval_pending` 类型：
  - `backend/src/models/notification.py`
  - `backend/src/services/notification/notification_service.py`
- RBAC / 路由注册 / API 分层基线已经稳定：
  - `backend/src/security/permissions.py`
  - `backend/src/core/router_registry.py`
  - `backend/src/api/v1/*`

### 缺口
- 没有审批域独立模型，资产审核仍是“直接改状态”，缺少审批实例与任务语义。
- 没有统一审批 API，无法沉淀为后续合同/产权证可复用的流程骨架。
- 没有“我的待办 / 我发起的 / 时间线”所需的后端聚合数据。
- 现阶段审批流方案仍停留在 Flowable 总体设计，未落地第一批最小可运行实现。

## 2. 范围

### 本次纳入
- `REQ-APR-001` 资产审批流第一阶段后端闭环
- 审批实例、任务快照、动作日志三类核心存储
- 资产发起审批、审批通过、审批驳回、审批撤回
- 基于审批动作的资产审核状态联动
- 审批待办查询、我发起的流程查询、流程时间线查询
- 审批待办站内通知（仅站内，不接企业微信）

### 本次不纳入
- Flowable / BPMN 真服务接入
- 前端审批中心页面与菜单
- 合同、产权证等其他业务域接入
- 催办、抄送、规则编排、自动对账修复

## 3. 核心决策

1. **先交付本地审批域骨架，不阻塞业务继续演进**
- 第一阶段使用业务库内审批模型承接“审批实例 / 待办 / 动作日志”。
- 结构上对齐长期 Flowable B 方案，后续可替换执行内核，但不为兼容保留旧接口。

2. **资产审核状态继续作为业务真相，审批域负责驱动状态变化**
- 发起审批时：资产从 `draft/reversed` 进入 `pending`。
- 审批通过时：资产进入 `approved`。
- 审批驳回或撤回时：资产回到 `draft`。
- 资产原有 `AssetReviewLog` 继续保留，审批动作同步写资产审核日志。

3. **审批待办按“显式候选人”最小化建模**
- 第一阶段不做复杂规则引擎。
- 发起时必须传入 `assignee_user_id`。
- 任务快照只支持单处理人，避免首批实现把复杂度推高。

4. **接口命名按审批域收口，不复用资产路由继续膨胀**
- 新增统一 `/api/v1/approval/*` 路由。
- 资产域仅保留“接入审批流”的桥接能力，不再新增一组资产专属审批端点。

## 4. 数据模型

### `approval_instances`
- 核心字段：
  - `id`
  - `approval_no`
  - `business_type` (`asset`)
  - `business_id`
  - `status` (`pending/approved/rejected/withdrawn`)
  - `current_task_id`
  - `starter_id`
  - `assignee_user_id`
  - `started_at`
  - `ended_at`
- 约束：
  - `business_type + business_id + status in pending` 同一时间仅允许一条运行中审批

### `approval_task_snapshots`
- 核心字段：
  - `id`
  - `approval_instance_id`
  - `business_type`
  - `business_id`
  - `task_name`
  - `assignee_user_id`
  - `status` (`pending/completed/cancelled`)
  - `created_at`
  - `completed_at`

### `approval_action_logs`
- 核心字段：
  - `id`
  - `approval_instance_id`
  - `approval_task_snapshot_id`
  - `action` (`start/approve/reject/withdraw`)
  - `operator_id`
  - `comment`
  - `created_at`
  - `context`

## 5. API 范围

### 新增审批 API
- `POST /api/v1/approval/processes/start`
  - 入参：`business_type=asset`、`business_id`、`assignee_user_id`、`comment`
- `GET /api/v1/approval/tasks/pending`
  - 返回当前用户待办审批任务
- `GET /api/v1/approval/processes/mine`
  - 返回当前用户发起的审批流程
- `GET /api/v1/approval/processes/{approval_instance_id}/timeline`
  - 返回流程动作时间线
- `POST /api/v1/approval/tasks/{task_id}/approve`
- `POST /api/v1/approval/tasks/{task_id}/reject`
- `POST /api/v1/approval/tasks/{task_id}/withdraw`

### 资产联动规则
- `start`:
  - 校验资产当前状态允许提审
  - 写审批实例 / 任务 / 动作日志
  - 资产状态转 `pending`
  - 为处理人创建 `approval_pending` 通知
- `approve`:
  - 仅待办处理人可操作
  - 资产状态转 `approved`
- `reject`:
  - 仅待办处理人可操作
  - 资产状态转 `draft`
- `withdraw`:
  - 仅发起人可操作
  - 资产状态转 `draft`
  - 若任务未处理则取消快照

## 6. 实施拆分

### 任务 A：审批域存储骨架
目标：补齐审批实例 / 待办快照 / 动作日志模型与迁移。

涉及文件（预计 < 20）：
- 新增：`backend/src/models/approval.py`
- 新增：`backend/src/schemas/approval.py`
- 新增：`backend/src/crud/approval.py`
- 新增：`backend/alembic/versions/20260402_req_apr_001_approval_domain.py`
- 修改：`backend/src/models/__init__.py`

TDD 顺序：
1. 先写 CRUD / service 所需的模型契约测试。
2. 再落 ORM 与迁移。

### 任务 B：审批服务与资产联动
目标：交付可运行的审批服务，并与资产审核状态机联动。

涉及文件（预计 < 20）：
- 新增：`backend/src/services/approval/__init__.py`
- 新增：`backend/src/services/approval/service.py`
- 可能新增：`backend/src/services/approval/constants.py`
- 修改：`backend/src/services/asset/asset_service.py`
- 修改：`backend/src/services/notification/notification_service.py`
- 修改：`backend/src/security/permissions.py`
- 修改：`backend/scripts/setup/init_rbac_data.py`

TDD 顺序：
1. 先写服务层失败测试：发起、通过、驳回、撤回、权限守卫、资产状态联动、通知创建。
2. 实现最小服务逻辑。
3. 补充资产联动回归。

### 任务 C：审批 API 与 SSOT 收口
目标：暴露统一审批 API，并同步需求、字段附录、计划索引和变更日志。

涉及文件（预计 < 20）：
- 新增：`backend/src/api/v1/approval.py`
- 修改：`backend/src/api/v1/__init__.py`
- 修改：`docs/requirements-specification.md`
- 修改：`docs/features/requirements-appendix-fields.md`
- 修改：`docs/plans/README.md`
- 修改：`CHANGELOG.md`

TDD 顺序：
1. 先写 API 失败测试：路由存在、参数必填、权限与处理人守卫、时间线结构。
2. 实现 API。
3. 跑定向测试 + `make docs-lint`。

## 7. 验证清单

### 后端定向
- `cd backend && uv run pytest --no-cov tests/unit/services/approval/test_approval_service.py -q`
- `cd backend && uv run pytest --no-cov tests/unit/api/v1/test_approval_api.py -q`
- `cd backend && uv run pytest --no-cov tests/unit/services/asset/test_asset_review.py -q`

### 文档 / 门禁
- `make docs-lint`
- `make check`

## 8. 风险

- 资产域已有审核端点，第一阶段引入统一审批 API 后，两套入口容易语义漂移，必须在服务层统一收口状态转换。
- 首批如果直接做“候选组 + 多处理人”，测试和权限边界会明显放大，不适合本轮。
- 站内通知已存在通用模型，但审批待办去重和已处理清理策略需要在服务层显式约束，避免积压脏消息。
