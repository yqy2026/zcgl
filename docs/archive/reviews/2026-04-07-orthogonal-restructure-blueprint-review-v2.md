# 三维正交重构蓝图复审报告（v2）

**时间**: 2026-04-07  
**对象**: `docs/plans/2026-04-07-orthogonal-restructure-blueprint.md`（v2）  
**结论**: 相比首轮版本已明显收敛，前次指出的路径、action 方向、Phase 2/4 时序、ABAC 复用、Phase 6 定位等关键问题大多已被正面修正。当前版本可作为后续修订底稿继续推进，但仍建议先修正以下 4 个实施级问题，再进入执行。

---

## 本轮结论摘要

本轮蓝图相较首版，已经完成了几项关键修正：

- 新增了 **文件映射表**，大部分关键路径已与仓库真实结构对齐。
- action 统一方向已修正为主干正在使用的 `read/create/update/delete`。
- Phase 2 前移了 `currentViewMode` 最小承接，避免了上版“双绑定用户中间态失效”的明显断层。
- `perm_admin` 已从“只改 `permissions.py`”扩展为审计 `require_admin` / `require_authz` / 遗留 helper 三层入口。
- Phase 6 已从“补骨架”重写为 **多角色契约迁移**，对真实改造面判断更准确。
- ABAC 已改为复用 `DataPolicyService` / `data_policies.py` / `backfill_role_policies.py` 现有体系，避免重复建设。
- 风险缓释已改成“一次性切换 + 回滚方案”，与当前仓库 0→1 原则更一致。

因此，本轮结论从上次的“不可直接执行”，调整为：

> **有条件通过**：方向已基本成立，但仍有 4 个需要在实施前补齐的缺口。

---

## 已修正项确认

### 1. 路径映射问题已基本修正

蓝图新增了 `§4 文件映射表`，并把关键路径纠正为真实仓库结构，例如：

- `backend/src/api/v1/analytics/analytics.py`
- `backend/src/api/v1/analytics/statistics.py`
- `backend/src/api/v1/auth/roles.py`
- `backend/src/scripts/migration/party_migration/backfill_role_policies.py`

这一点已消除首版最大的执行误导风险。

### 2. action 统一方向已修正

蓝图已明确主干统一目标为 `read/create/update/delete`，并把 `backend/src/security/permissions.py` 定位为遗留层清退/收敛对象。这个方向与当前仓库主干 `require_authz(...)` 的实际使用一致。

### 3. Phase 2 / Phase 4 时序已明显改善

蓝图已把 `currentViewMode` 最小承接前移至 Phase 2，不再坚持“先移除 header，Phase 4 再补承接”的高风险顺序。相比首版，这是正确修正。

### 4. ABAC 重复建设问题已被正面处理

蓝图已明确：

- 通过 `DataPolicyService` 创建默认策略包
- 通过 `backfill_role_policies.py` 绑定角色策略
- 通过 `data_policies.py` API / `DataPolicyManagementPage.tsx` 管理

这一点比首版“新建独立 seed 脚本直接灌表”的做法稳健得多。

---

## 剩余问题（建议实施前修正）

### P1-1：REQ-RNT-002 的“一资产一合同组”约束仍未落到任务清单

**蓝图位置**:

- `docs/plans/2026-04-07-orthogonal-restructure-blueprint.md:202-212`

**问题**:

蓝图的 Phase 1 已在验收标准里写明：

- “一个资产不允许关联多个合同组（Q1 决策）”

但任务清单仍主要是：

- 前端模式选择 / 展示
- `validate_revenue_mode_compatibility()` 回归

目前**没有显式的后端结构性约束任务**，而这条约束并不是前端或现有 `validate_revenue_mode_compatibility()` 能保证的。

**代码证据**:

- `backend/src/models/associations.py:11-28` 中 `contract_group_assets` 仅是 `(contract_group_id, asset_id)` 联合主键，并**没有** `asset_id` 全局唯一约束。
- `backend/alembic/versions/20260305_contract_group_m1.py:135-152` 建表时同样没有“一资产仅允许一个合同组”的唯一约束。
- `backend/src/crud/contract_group.py:671-688` 的 `_replace_assets()` 只是“删后重插”，并未检查该资产是否已属于其他合同组。

**影响**:

如果不把这条约束作为独立后端任务加入 Phase 1，蓝图会出现“验收标准声明存在，但执行任务并未真正落地”的断层。

**建议**:

在 Phase 1 / REQ-RNT-002 里新增独立任务，例如：

- 后端 service / CRUD 校验：资产已关联其他合同组时拒绝绑定
- 必要时补数据库唯一约束或迁移脚本
- 补对应 integration test

---

### P1-2：Phase 2 的“primary binding 自动选定”目前没有真实数据来源

**蓝图位置**:

- `docs/plans/2026-04-07-orthogonal-restructure-blueprint.md:256-284`
- `docs/plans/2026-04-07-orthogonal-restructure-blueprint.md:430-431`

**问题**:

蓝图把双绑定用户 Phase 2 的兜底策略定义为：

- “基于 primary binding 自动选定”

但当前能力快照和前端 store **并没有 primary binding 信息**，现状只暴露 owner / manager 的 party id 集合。

**代码证据**:

- `backend/src/services/authz/context_builder.py:52-109` 会读取用户 bindings，但最终只汇总成 `owner_party_ids` / `manager_party_ids`，没有把 `is_primary` 暴露出去。
- `backend/src/schemas/authz.py:34-55` 的 `DataScope` / `CapabilitiesResponse` 也只包含 `owner_party_ids` / `manager_party_ids`。
- `frontend/src/stores/dataScopeStore.ts` 当前同样只基于 owner / manager 两组 ids 推导单/双绑定状态。

**影响**:

蓝图虽然修正了时序问题，但新的 auto-fallback 规则仍然缺“谁来提供 primary binding”的数据源。若不补，实施时仍会卡在规则落地上。

**建议**:

二选一并写入蓝图：

1. **补能力快照字段**：在 `CapabilitiesResponse` / session profile 中显式返回 primary binding / primary role 信息；或
2. **改规则**：Phase 2 不依赖 primary binding，改为固定优先级（例如 owner 优先或 role precedence），等 Phase 4 再升级为更细粒度偏好。

当前蓝图已提出正确问题，但还没有闭合实现来源。

---

### P1-3：Phase 2 / Phase 4 对前端改造面的描述仍偏窄，遗漏 service 层与导出调用点

**蓝图位置**:

- `docs/plans/2026-04-07-orthogonal-restructure-blueprint.md:266-269`
- `docs/plans/2026-04-07-orthogonal-restructure-blueprint.md:409-413`

**问题**:

蓝图已开始列 `useAnalytics.ts`、`DashboardPage.tsx`、`components/Analytics/`，但真正承担分析请求与导出的关键调用点还在 **service 层**，目前任务描述仍偏轻。

**代码证据**:

- `frontend/src/services/analyticsService.ts:113-149`：`getComprehensiveAnalytics()` 直接组装请求参数。
- `frontend/src/services/analyticsService.ts:258-337`：`getBasicStatistics()` / `getAreaSummary()` / `getFinancialSummary()` / `exportAnalyticsReport()` 也都直接发请求。
- `frontend/src/components/Analytics/AnalyticsDashboard.tsx:82-89`：导出按钮直接调用 `analyticsService.downloadAnalyticsReport(...)`。
- `frontend/src/pages/Dashboard/useDashboardData.ts:5-6` 也直接调用 `analyticsService.getComprehensiveAnalytics()`。

**影响**:

如果 Phase 2 / 4 只改 hook 和 page，而没有把 `analyticsService.ts` 作为明确任务入口，实际很容易出现：

- 综合分析接口带了 `view_mode`
- 但导出、统计子接口没带
- 或页面 A 正常、页面 B/导出仍走旧契约

**建议**:

把以下文件显式加进蓝图的任务清单或文件映射：

- `frontend/src/services/analyticsService.ts`
- `frontend/src/components/Analytics/AnalyticsDashboard.tsx`
- `frontend/src/pages/Dashboard/useDashboardData.ts`（若保留）

这会让“view_mode 改造”从 UI 层描述升级为**完整数据调用链描述**。

---

### P1-4：Phase 2 仍缺少 SSOT 文档同步任务

**蓝图位置**:

- `docs/plans/2026-04-07-orthogonal-restructure-blueprint.md:244-294`

**问题**:

蓝图对 Phase 1、Phase 4、Phase 5 都写了显式的 SSOT / REQ 状态更新，但 **Phase 2 没有写**。

然而当前 SSOT 仍明确保留了 `X-Perspective` 的“过渡状态”描述，若 Phase 2 真的按蓝图一次性切除 header，这部分文档必须同步收口。

**代码证据**:

- `docs/requirements-specification.md:926`：`REQ-SCH-003` 仍写“代码仍活跃使用 `X-Perspective`，计划废弃”。
- `docs/requirements-specification.md:928`：`REQ-AUTH-002` 仍写“前端单绑定时仍注入 `X-Perspective` header，计划废弃”。

**影响**:

若 Phase 2 执行后不同步文档，SSOT 会再次变成“代码已切换，需求矩阵仍描述旧过渡态”，与仓库的 SSOT 工作流要求冲突。

**建议**:

在 Phase 2 增加单独的 SSOT 任务，例如：

- 更新 `docs/requirements-specification.md` 中 `REQ-SCH-003` / `REQ-AUTH-002` 的证据与状态描述
- 同步 `CHANGELOG.md`

---


### P1-5：分析域并非只有 `comprehensive/export`，`trend/distribution` 端点当前也未纳入 view_mode / 数据范围改造清单

**问题**:

蓝图在 Phase 2 / 4 中主要围绕综合分析与导出描述 `view_mode` 改造，但当前 `analytics.py` 里还有 `trend` / `distribution` 等分析端点。它们如果继续维持旧行为，会让“分析域 view_mode 统一”在落地时出现不完整状态。

**代码证据**:

- `backend/src/api/v1/analytics/analytics.py:46-127` 的 `comprehensive` 已接入 `require_data_scope_context(...)` 与 `build_party_filter_from_scope_context(...)`
- `backend/src/api/v1/analytics/analytics.py:363-458` 的 `export` 也已接入 scope context
- 但 `backend/src/api/v1/analytics/analytics.py:256-360` 的 `trend` / `distribution` 当前**没有** `require_data_scope_context(...)`，也没有显式传入 `party_filter`

**影响**:

若蓝图按当前写法推进，Phase 2 / 4 可能只修复综合分析页，而遗漏趋势/分布类端点，形成“同属 analytics 域但契约不一致”的新残留。

**建议**:

在 Phase 2 或 Phase 4 中明确追加一条：

- 对 `analytics.py` 下全部分析端点做 scope / view_mode 审计，至少确认 `comprehensive`、`export`、`trend`、`distribution` 四类端点的契约是否一致。

---

### P1-6：蓝图写“通过 `DataPolicyService` 创建默认策略包”不准确，当前 service 只负责绑定，不负责创建模板策略记录

**问题**:

蓝图已经改为复用现有 `DataPolicyService` 体系，这个方向是对的；但其中一句关键描述仍然不够准确：

- “通过现有 `DataPolicyService` 创建默认策略包（7 个数据策略模板 → `abac_policies` 表）”

当前 `DataPolicyService` 实际上**不会创建 `abac_policies` 记录**，它只：

- 提供模板元数据 `list_templates()`
- 把已存在的模板策略绑定给角色 `set_role_policy_packages()`
- 若模板策略不存在，会直接抛错要求“先执行 ABAC seed 迁移”

**代码证据**:

- `backend/src/services/authz/data_policy_service.py:71-78`：仅返回模板元数据
- `backend/src/services/authz/data_policy_service.py:95-132`：只做 role-policy 绑定
- `backend/src/services/authz/data_policy_service.py:169-177`：模板缺失时抛出“策略包模板缺失，请先执行 ABAC seed 迁移”

**影响**:

这会让 Phase 5 的实施顺序再次变模糊：

- 是先依赖现有 alembic / seed 把 `abac_policies` 模板灌入库
- 还是要补一个“模板策略初始化”步骤

如果不写清楚，执行时仍会遇到“service 能绑但没有可绑模板”的落空问题。

**建议**:

把 Phase 5 的表述改成两步：

1. **确保模板策略已入库**（复用现有 migration / seed 机制，而不是写成 DataPolicyService 负责创建）
2. 再通过 `DataPolicyService` / `backfill_role_policies.py` 完成角色绑定

---

### P2-1：蓝图引用了 `require_role([system_admin, perm_admin])` 这一实现形态，但仓库当前没有对应多角色 helper

**问题**:

蓝图在 Phase 3 “授权入口三层统一”中写到：

- “逐个改写为 `require_authz` 或新的 `require_role([system_admin, perm_admin])`”

但当前仓库并没有“接收角色列表”的 `require_role(...)` helper，现有只有单角色版本 `role_required(role_code: str)`。

**代码证据**:

- `backend/src/security/permissions.py:125-160`：只有 `role_required(role_code: str)`，没有 list 版本

**影响**:

这不算方向错误，但说明蓝图里这条任务仍停留在概念层，缺一条更具体的实现说明：

- 是新增多角色 helper
- 还是全部统一回 `require_authz`
- 还是只在系统管理域临时加一层组合依赖

**建议**:

在 Phase 3 补一句实现策略，避免执行时出现“文档提到的 helper 在仓库里并不存在”的落差。

---

### P2-2：资源盘点 Step 0 需要定义清洗规则，否则很容易把大小写/中文/非标准值一起盘进去

**问题**:

蓝图把 Phase 3 的第一步定义为：

- “从 `backend/src/**` 自动导出当前全部 `resource_type` 清单”

方向是对的，但如果不写“清洗规则”，这一步会把大小写不一致、调试值、历史残留值也一起导出，导致冻结清单噪音过大。

**代码证据**:

基于当前源码简单扫描，确实能提取出约 50 个 `resource_type` 值，但其中已经混有：

- 大小写不统一值：如 `Asset`、`ApprovalInstance`
- 非标准业务值：如 `主体`
- 中间态/细粒度内部资源：如 `user_role_assignment`、`primary_contact`

**影响**:

如果蓝图只写“自动导出”，不写如何归并/规范化，Step 0 很容易输出一份无法直接作为目标权限资源表的原始杂项清单。

**建议**:

在蓝图里补充盘点规则，例如：

- 统一转小写
- 排除测试/示例/异常 message 中的伪资源值
- 将内部实现资源与对外授权资源分层
- 输出清单后必须人工标注“保留 / 合并 / 废弃”再冻结

这样 Step 0 才真正可执行。

---


### P1-7：Phase 1 提议的 `asset_id` 全局唯一约束，与合同组当前“逻辑删除但不清关联”的实现存在冲突风险

**问题**:

v3 已经把“一资产一合同组”补进了任务清单，这是正确修正；但当前蓝图把实现直接写成：

- `contract_group_assets` 表增加 `asset_id` 全局唯一约束

这一点与现有合同组删除语义仍未完全对齐。

**代码证据**:

- `backend/src/crud/contract_group.py:113-126` 的 `soft_delete()` 只是把 `ContractGroup.data_status` 置为 `已删除`。
- 它**不会清理** `contract_group_assets` 关联表记录。
- `backend/src/models/associations.py:11-28` 的 `contract_group_assets` 只是纯关联表，本身没有 `active` 标记列。

**影响**:

如果直接给 `asset_id` 加全局唯一约束：

- 一个资产即使其原合同组已逻辑删除，只要关联表记录还在，就仍无法重新绑定到新合同组。

这会把“禁止一资产同时属于多个活跃合同组”，错误实现成“禁止一资产历史上曾属于任何其他合同组”。

**建议**:

把 Phase 1 的这条任务再 уточ准为三选一：

1. 软删合同组时同步清理 `contract_group_assets` 关联；或
2. 关联表改造成可表达 active/inactive 的模型后做条件唯一；或
3. 先以 **service 校验 + integration test** 为主，DB 约束放到结构调整后再上。

当前蓝图如果不补这一层说明，实施时很容易引入误伤。

---

### P1-8：Phase 2/4 目前只审计 `analytics.py`，但 `statistics_modules/*.py` 也属于分析域，仍未纳入 scope/view_mode 统一计划

**问题**:

v3 已把 `trend/distribution` 端点补进 Phase 2，这是进步；但当前蓝图的“分析端点全量审计”仍只写在 `backend/src/api/v1/analytics/analytics.py` 上。

实际上统计域还有一整组：

- `backend/src/api/v1/analytics/statistics_modules/*.py`

这些模块当前大量只有 `require_authz(...)`，没有显式 `require_data_scope_context(...)` / `build_party_filter_from_scope_context(...)`。

**代码证据**:

- `backend/src/api/v1/analytics/statistics_modules/area_stats.py`
- `backend/src/api/v1/analytics/statistics_modules/basic_stats.py`
- `backend/src/api/v1/analytics/statistics_modules/distribution.py`
- `backend/src/api/v1/analytics/statistics_modules/financial_stats.py`
- `backend/src/api/v1/analytics/statistics_modules/occupancy_stats.py`
- `backend/src/api/v1/analytics/statistics_modules/trend_stats.py`

当前检索结果显示，这些模块都有 `require_authz(...)`，但没有与 `analytics.py` 对齐的 scope context 接入。

**影响**:

如果只修 `analytics.py` 主文件，不审计 `statistics_modules`，最终仍会留下：

- `comprehensive/export/trend/distribution` 一套契约
- `statistics_modules/*` 另一套契约

这会让“analysis 域 view_mode / scope 一致化”只完成一半。

**建议**:

把 Phase 2 或 Phase 4 的后端任务明确扩成：

- `backend/src/api/v1/analytics/analytics.py`
- `backend/src/api/v1/analytics/statistics.py`
- `backend/src/api/v1/analytics/statistics_modules/*.py`

统一做一次分析域端点契约审计。

---

### P1-9：Phase 5 已修正文案，但内部仍残留两处旧说法，容易误导执行

**问题**:

v3 已把 Phase 5 主任务拆成“模板入库”+“角色绑定”两步，这是正确的；但文档内部仍残留两处旧表述：

1. 建议测试用例里仍写：`通过 DataPolicyService 创建 → 幂等`
2. 异常项 A8 仍写：`7 个 ABAC 数据策略模板未入库 | Phase 5（通过 DataPolicyService 创建）`

这两处与 v3 已经修正后的主叙述不一致。

**影响**:

会让执行者再次误以为：

- `DataPolicyService` 负责创建模板策略记录

而实际上它只负责绑定。

**建议**:

把这两处同步改为：

- “模板通过 seed migration / Alembic 入库”
- “DataPolicyService 负责绑定与管理”

避免 Phase 5 内部自相矛盾。

---


### P1-10：现有 `backfill_role_policies.py` 的策略包选择逻辑仍基于旧角色命名启发式，直接用于新 6 角色会映射错误

**问题**:

v3 已把 Phase 5 改为复用 `backfill_role_policies.py` 做角色-策略绑定，但当前脚本的 `_choose_policy_package()` 仍是基于旧角色名/类别里的关键词做启发式判断，并不是为新 6 角色显式设计的映射表。

**代码证据**:

- `backend/src/scripts/migration/party_migration/backfill_role_policies.py:38-59`
- 其中规则包括：
  - 只要 token 里包含 `admin` 就返回 `platform_admin`
  - 包含 `manager` / `运营` 就返回 `asset_manager_operator`
  - `viewer` / `只读` → `dual_party_viewer`
  - 其余默认 `no_data_access`

**影响**:

如果直接把该脚本用于新 6 角色：

- `perm_admin` 会因为名字里有 `admin` 被错误映射到 `platform_admin`，这与“零业务数据权限”直接冲突；
- `ops_admin` 也大概率会被映射成 `platform_admin`；
- `reviewer` / `executive` 这类新角色也缺少显式映射规则。

这会让 Phase 5 的“复用现有 backfill 脚本”在新角色体系下产生错误授权。

**建议**:

在蓝图中补一句强约束：

- **Phase 3 完成新角色冻结后，先重写 `backfill_role_policies.py` 的角色→策略映射为显式白名单表，再执行 Phase 5 绑定**；
- 不应继续依赖旧的关键词启发式。

---

## 低优先级建议

### L1：Phase 6 中“保留 `role_name` 做兼容派生”与 0→1 原则略有张力

**蓝图位置**:

- `docs/plans/2026-04-07-orthogonal-restructure-blueprint.md:519-520`

蓝图写到：

- 用户响应模型新增 `roles: list[RoleInfo]`，并“保留 `role_name` 做兼容派生”

这比首版更务实，但与项目 AGENTS.md 中“0→1 阶段不要做兼容保留”的原则略有张力。

**建议**:

如果保留 `role_name`，建议在蓝图中补一句：

- 仅作为 **同 Phase 内过渡字段**，Phase 6 完成前移除，不进入长期契约。

这样能避免再次引入“临时兼容变长期遗留”的风险。

---

## 复审建议结论

本轮蓝图已经从“不可直接执行”提升到“可继续推进的修订底稿”。

### 建议评级

- **APPROVAL**: COMMENT / 有条件通过

### 进入实施前建议先补齐的 4 项

1. 为 REQ-RNT-002 明确加入“一资产一合同组”的后端约束任务
2. 为 Phase 2 的 primary binding auto-select 补充真实数据来源或改成不依赖 primary 的规则
3. 将 `frontend/src/services/analyticsService.ts` / 导出调用点纳入 view_mode 改造范围
4. 为 Phase 2 增加 SSOT 文档同步任务

若以上 4 项补齐，我认为这份蓝图就可以进入执行准备阶段。
