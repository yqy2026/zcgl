# 资产运营 v5 V1 开发交接

> 2026-10-27 补充：本次 V1 交付切片已完成双轴复核和完整 CI，方案已归档；收口证据及当前边界见 [PR #95 最终复核记录](reviews/2026-10-27-asset-operations-v5-v1-pr95-review.md)。下文保留交接当时的历史状态。

## 交接时的工作区状态

当前开发目录为 `D:\work\zcgl`，分支为 `codex/asset-ops-v5-s0`。分支指针仍停在提交 `2eb47e5c`，与 `develop` 当前基线一致。本轮资产运营 v5 的代码、文档、原型和测试改动都还在工作区内，没有形成提交。

接手后不要执行清理、重置或切换分支。工作区包含大量相互关联的已修改文件和新增文件，任何清理动作都可能直接丢失本轮实现。开始工作前先执行 `git status --short --branch`，确认状态与本文一致。

当前唯一有效的实施方案是 [资产运营 v5 V1 计划](backend-plans/2026-10-23-asset-operations-v5-v1.md)。产品事实以 [PRD](../prd.md) 为准，字段与状态以 [领域模型](../specs/domain-model.md) 为准，端点与错误码以 [API 契约](../specs/api-contract.md) 为准，实现证据以 [需求追踪表](../traceability/requirements-trace.md) 为准。

最初用于评审的原型目录 `C:\Users\y\Downloads\拯救项目原型 (1)` 仍然存在。已采纳的原型内容已经整理到 `frontend/prototype/`，后续开发和评审应以仓库内文件及 SSOT 为准，下载目录只用于追溯原始输入。

## 这一轮确定下来的产品边界

系统只服务一个业务岗位，也就是资产管理岗。平台从合同已经签署、收付款已经在外部发生以后开始记录事实，不承担招商审批、银行支付、催收案件或领导驾驶舱。

资产单元是最小可租边界，也是一宗统计的最小单位。合同覆盖多个资产单元时，每个单元独立计宗。项目只保留管理归属标签，不能成为经营数字的事实源。

Party 承担产权方、运营方和租户身份，Organization 只表示内部组织。前端和服务端都不能用组织名称代替 Party 关系。

出租状态、合同状态、风险、出租率和缺漏数量都从事实推导，不写回独立状态字段。续签、终止、退出、撤销和资产单元拆合都追加事实，历史记录不覆盖。

新实现不读取旧合同域作为运行时兜底，也不做新旧双写。旧表的迁移歧义必须在预检或导入底稿阶段暴露。

## 已经完成的工作

### 规格、原型与设计基线

- 完成资产运营 v5 的 PRD、领域模型、API 契约、需求追踪、验收清单和 ADR 收口。
- 完成最新资产运营原型及状态页，主要文件在 `frontend/prototype/asset-ops-v5.html` 和 `frontend/prototype/asset-ops-states.html`。
- 更新前端主题基础变量，落实平面化卡片、紧凑表格、方角标签、缩放和对比度约束。
- 归档 v4 实施方案，当前活跃计划只保留 v5 V1。

### 资产单元事实链

- 新增 `AssetUnit`、资产单元拆合事件、拆合来源关系和产权证时态关联模型。
- 新增 v5 数据预检，旧表缺失、字段缺失、资产映射歧义和旧业务事实非空时都会失败关闭。
- 完成拆分和合并的预览提交流程，包含预览 token、乐观锁、幂等回放、面积守恒、有效期衔接和 Party 范围校验。
- 拆分与合并按资产单元 ID 排序获取共享写锁。合同覆盖写入也使用同一个锁协议，避免边界变更和合同确认互相越过检查。
- 新增 `asset_ops` 的读、写、报送、档案和导入权限，并完成内建角色映射迁移。

关键入口包括 [资产单元命令端点](../../backend/src/api/v1/asset_units.py)、[边界命令模块](../../backend/src/services/asset_operations/boundary_command_service.py)、[资产单元数据访问](../../backend/src/crud/asset_unit.py) 和 [边界数据访问](../../backend/src/crud/asset_unit_boundary.py)。

### 已签合同录入

- 新增上游合同、终端合同、逐单元覆盖、租金阶段、生命周期事件和写入回执模型。
- 完成 Party 范围化的上游与终端合同查询数据访问，范围缺失时返回 403，不伪装为空列表。
- 完成合同录入会话的上传、读取、确认上游、确认终端和取消端点。端点统一要求 `asset_ops:write`。
- 会话使用 Redis 保存临时状态，扫描件保存在私有文件区。自动提取暂不可用时返回 `EXTRACTION_UNAVAILABLE`，操作员仍可手工核对并确认。
- 合同确认按资产单元排序加锁，在一个事务内写入合同、覆盖关系、租金阶段、扫描件绑定和幂等回执。
- 同一操作者使用同一请求标识重试时返回首次结果，不创建第二份合同。请求内容变化时返回 `IDEMPOTENCY_CONFLICT`。
- 扫描件绑定使用附件行锁并校验原 owner 仍为当前录入会话。一份已签扫描件只能消费一次，重复使用返回 `SCAN_DOCUMENT_ALREADY_BOUND` 并回滚全部合同事实。
- 普通录入确认不能提交 `renewed_from_id`。续签关系只能由后续独立续签命令建立。
- 已选择上游时，系统校验合同模式、上游类型、出租方和起租日覆盖。未选择上游时，直签按全部单元的唯一产权方校验出租方，转租按全部单元所属项目的唯一运营 Party 校验出租方。
- 终端上游缺失和租期越界保留为 warning，不阻断已签事实登记。委托管理协议下的直签越界也会产生相同 warning。

关键入口包括 [合同录入端点](../../backend/src/api/v1/contract_intake_sessions.py)、[录入会话模块](../../backend/src/services/asset_operations/contract_intake_service.py)、[合同写入模块](../../backend/src/services/asset_operations/contract_command_service.py)、[合同投影](../../backend/src/services/asset_operations/contract_projections.py) 和 [合同数据访问](../../backend/src/crud/asset_contract.py)。

### 生命周期幂等核心

- 新增 [生命周期命令模块](../../backend/src/services/asset_operations/contract_lifecycle_command_service.py)。
- `terminate_terminal()` 已封装 Party 范围、目标合同行锁、追加事件、提交回滚和并发幂等回放。
- 相同请求标识和相同终止内容只产生一条 `terminated` 事件，重试结果带 `idempotent=true`。
- 相同请求标识改写终止内容会返回 `IDEMPOTENCY_CONFLICT`。
- 真实 PostgreSQL 双会话并发测试已经证明只落一条生命周期事件。

这部分只完成了 V1-T09 所需的命令和持久化核心。终止预览、覆盖期间影响、撤销和 HTTP 端点还没有完成，不能把它当作可交付的完整终止功能。

## 独立复核已经处理的问题

合同写入完成后安排了只读复核。复核范围覆盖命令模块、数据访问、模型、测试和 SSOT。发现的问题都已采纳并修复，最终复核没有剩余 P0 或 P1。

已修内容包括并发相同请求标识的二次写入、所选上游裸 ID 越过 Party 范围、confirmed 会话重复确认、扫描件 owner 被覆盖、普通录入注入续签前驱、直签越界缺 warning、关系冲突错误码返回 422、无上游时出租方可任意填写，以及需求追踪表提前宣称 V1-T09 完成。

confirmed 或 confirming 会话在会话层提前拒绝不同请求标识仍可作为后续 P2 优化。当前数据库附件比较并交换已经阻止第二份合同落库，安全边界成立。

## 当前验证证据

最近一次相关回归共 `127 passed`，另有 6 条既有第三方或运行环境告警。覆盖范围包含资产单元边界、合同创建、合同录入会话、生命周期幂等、模型、schema、数据访问、迁移、权限和真实 PostgreSQL 竞态。

以下检查均已通过。

- Ruff 变更文件检查
- Mypy 变更源文件检查
- `docs-lint`
- 字段漂移检查
- 查询参数漂移检查
- 测试凭据检查
- `git diff --check`
- 后端导入烟测
- Alembic 单一 head 检查

当前 Alembic head 为 `20261024_asset_contract_write_receipts`。

字段漂移检查仍会报告 Party、Project 和 PropertyCertificate 的既有规格差异。AssetUnit、两类合同、覆盖关系、租金阶段和生命周期事件已经保持一致。这个输出是当前 0 到 1 阶段的已知状态，不是本轮门禁失败。

本机 Redis 位于 `localhost:16379`，验证时没有启动。默认后端导入会因此失败。设置 `REDIS_ENABLED=false` 后，后端导入烟测通过。合同录入会话的真实 Redis 与 HTTP 端到端测试仍需补做。

Windows 环境没有 `make`，因此没有在当前最终状态运行完整 `make check`。受影响的后端和文档门禁已经逐项执行。前端生产页面本轮没有新增，前端全量 lint、测试和构建也没有在这次最终状态重跑。

## 尚未完成的范围

- 终端终止的预览 token、提交端点、覆盖期间影响、后继合同冲突和撤销语义。
- 上游退出的预览提交和撤销，包含有效终端合同阻断。
- 上游与终端合同续签命令，包含唯一后继、同类型、同 Party 范围和覆盖关系校验。
- 上游与终端合同的列表、详情和更新端点。读取结果必须重放生命周期事件后再计算状态。
- 资产单元的列表、详情和普通更新端点。
- 产权证关联与考核范围在资产单元拆合后的联动。
- 生产前端的资产单元、上游合同、终端合同和录入页面。当前只有可点击原型和主题基础调整。
- 合同扫描件的 OCR 或模型提取接线。当前明确降级为手工核对。
- 新旧业务入口的一次性切换与旧运行时入口清理。
- 完整 `make check`、前端构建和浏览器 E2E。

## 推荐的接手顺序

第一步补终端终止的影响模型。需要先裁定事件生效日是否表示最后有效日，并确定终止后 `TerminalContractAssetUnit.effective_to` 的处理方式。这个口径会直接影响 PostgreSQL 的同期覆盖排斥约束和后继合同起租日，不能在端点里临时猜测。

第二步完成终止预览和提交。预览应绑定操作者、Party 范围、合同版本、覆盖期间、押金和交接状态。提交重新加锁并校验预览仍然有效，再调用现有生命周期命令核心。

第三步完成终止撤销、上游退出和两类续签。撤销必须显式指向原事件，已有后继事实时要失败关闭。续签只能创建后继合同，不能修改旧合同期限。

第四步接合同列表和详情。查询模块已有 Party 范围化基础，但响应还需要聚合覆盖单元、租金阶段、生命周期事件和后继合同，再统一计算 status 与 warning。

第五步实现生产前端。服务器数据使用 React Query，表单使用 React Hook Form，页面必须区分 loading、empty、403 和 error。原型只是设计输入，不能直接复制成生产代码。

第六步完成真实 Redis 加 HTTP 的合同录入 E2E、生命周期 E2E、前端构建和浏览器测试，随后执行一次完整门禁，再准备提交和合并。

## 接手后先执行的命令

```powershell
cd D:\work\zcgl
git status --short --branch
git diff --check

cd backend
uv run --frozen --extra dev alembic heads
uv run --frozen --extra dev python -m pytest tests/unit/services/asset_operations tests/unit/api/v1/test_asset_unit_boundary_api.py tests/unit/api/v1/test_contract_intake_api.py tests/unit/crud/test_asset_contract_v5.py tests/unit/crud/test_asset_unit_boundary.py tests/unit/crud/test_asset_unit_v5.py tests/unit/migration/test_asset_operations_v5_asset_units_migration.py tests/unit/migration/test_asset_operations_v5_contracts_migration.py tests/unit/migration/test_asset_operations_v5_permissions_migration.py tests/unit/migration/test_asset_operations_v5_preflight.py tests/unit/models/test_asset_contract.py tests/unit/models/test_asset_unit.py tests/unit/schemas/test_asset_operations.py tests/integration/database -q --no-cov
uv run --frozen --extra dev python -m ruff check src tests/unit/services/asset_operations tests/integration/database
uv run --frozen --extra dev python -m mypy src/services/asset_operations src/crud/asset_contract.py src/crud/asset_unit.py src/schemas/asset_operations.py

uv run --frozen --extra dev python ../scripts/check_requirements_authority.py
uv run --frozen --extra dev python ../scripts/check_field_drift.py
uv run --frozen --extra dev python ../scripts/check_query_param_drift.py
uv run --frozen --extra dev python ../scripts/check_test_credentials.py

$env:REDIS_ENABLED='false'
$env:SECRET_KEY='ZcglBackendImportSmoke2026StrongKey!42'
uv run --frozen --extra dev python -c "from src.main import app; print('import ok')"
```

如果要验证合同录入会话，需要先按项目现有方式启动 Redis，再执行 HTTP 级上传、确认和取消测试。不要在代码里增加 Redis 不可用时的内存兼容分支。

## 必须继续覆盖的边界场景

- 同一终止请求标识由两个数据库会话同时提交，只产生一条事件。
- 同一请求标识改写终止日期、原因或押金状态，返回 409。
- 终止预览后合同版本、覆盖期间或 Party 范围发生变化，提交拒绝且预览保留供诊断。
- 终止后新合同从允许日期开始，不触发旧覆盖的排斥约束。
- 撤销终止时已经存在后继合同，系统明确阻断，不静默恢复旧覆盖。
- 无上游直签跨多个产权方，或无上游转租跨多个运营方，确认返回 409。
- 两个请求同时消费同一扫描件，只允许一个成功，失败请求不留下合同、覆盖或回执。
- Party 范围缺失时返回 403，不返回空列表。
- 上海业务日跨 UTC 日期边界时，拆合和预览有效期保持一致。

## 交接结论

当前工作已经把资产单元拆合、已签合同录入和生命周期幂等核心接到了真实 PostgreSQL，并完成了权限、文档和独立复核。工作区仍处于开发中，V1 还不能发布。接手者最先要解决的是终止事件与合同覆盖期间之间的关系，随后才能安全公开生命周期端点和合同查询页面。

保留当前工作区，沿着活跃计划继续做小批次红绿循环。每次改动后同步 `CHANGELOG.md` 和需求追踪证据，任何未执行的测试都要在交接或提交说明中写清楚。
