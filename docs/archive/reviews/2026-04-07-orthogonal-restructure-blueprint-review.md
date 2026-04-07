# 三维正交重构蓝图复核报告

**时间**: 2026-04-07  
**对象**: `docs/plans/2026-04-07-orthogonal-restructure-blueprint.md`  
**结论**: 方案方向正确，且确实建立在现有代码基础之上；但当前版本仍有若干会直接影响实施的 P0/P1 级问题。建议先修正文档路径、动作命名方向、Phase 2/4 时序，以及 `perm_admin` 控制面定义，再进入执行。

---

## 复核摘要

这份蓝图的优点很明确：

- 已把 Q1~Q6 的关键业务决策吸收到统一 Phase 结构中，方向上比三个分散方案更收敛。
- 项目并非从零开始：
  - 分析端点与服务已存在：`backend/src/api/v1/analytics/analytics.py`、`backend/src/api/v1/analytics/statistics.py`、`backend/src/services/analytics/analytics_service.py`
  - 数据范围与 `X-Perspective` 注入链路已存在：`backend/src/middleware/auth.py`、`frontend/src/api/client.ts`、`frontend/src/stores/dataScopeStore.ts`
  - 合同组、资产详情、系统管理页都已有实现基础，而不是纯空壳。
- 方案已经识别出真实异常：`analytics/statistics` 资源名漂移、ABAC deny 覆盖、缓存键未显式表达 binding、旧 header 残留，这些判断基本准确。

但这份方案目前还不能直接作为无修订执行底稿，核心问题集中在 8 类：

1. **文档中的关键文件路径与仓库实际结构不一致**；
2. **action 命名统一方向选反了**；
3. **Phase 2 会先把双绑定分析页打挂，Phase 4 才补 UI/状态承接**；
4. **`perm_admin`/`system_admin` 控制面不只在 `permissions.py`，方案当前覆盖不全**；
5. **Phase 6 低估了“单角色 → 多角色”改造面，且把已有页面误判为“骨架”**；
6. **ABAC 已有数据策略包管理面与回填脚本，蓝图没有复用，存在重复建设风险**；
7. **Phase 3 对“资源总数”的目标定得过低，和仓库真实 `resource_type` 面不匹配**；
8. **风险缓释里保留长兼容期，与当前仓库“0→1 不做兼容保留”的工程约束有冲突**。

---

## P0：阻塞实施的问题

### 1. 关键文件路径多处写错，执行时会直接误导实现者

**方案位置**:

- `docs/plans/2026-04-07-orthogonal-restructure-blueprint.md:176`
- `docs/plans/2026-04-07-orthogonal-restructure-blueprint.md:273`
- `docs/plans/2026-04-07-orthogonal-restructure-blueprint.md:315`
- `docs/plans/2026-04-07-orthogonal-restructure-blueprint.md:367`
- `docs/plans/2026-04-07-orthogonal-restructure-blueprint.md:418-424`
- `docs/plans/2026-04-07-orthogonal-restructure-blueprint.md:483`

**证据**:

- 方案写的是 `backend/src/api/v1/analytics.py` / `backend/src/api/v1/statistics.py`，但实际文件是：
  - `backend/src/api/v1/analytics/analytics.py`
  - `backend/src/api/v1/analytics/statistics.py`
- 方案写的是 `backend/src/api/v1/auth/auth_modules/roles.py`，实际文件是：
  - `backend/src/api/v1/auth/roles.py`
- 方案写“现有脚本” `backfill_role_policies.py`，实际路径是：
  - `backend/src/scripts/migration/party_migration/backfill_role_policies.py`
- 方案引用 `backend/src/api/v1/statistics.py` 作为 Phase 3 / Phase 7 清理目标，但该文件不存在。
- 方案计划新建 `backend/scripts/setup/init_abac_data.py`，仓库当前不存在同名脚本。

**影响**:

- 直接导致 TDD 起点、测试挂载点、代码提交范围和 reviewer 预期全部漂移。
- 如果按错误路径拆任务，团队执行时会出现“找不到文件 / 误判未实现”的假阻塞。

**建议**:

先补一张“蓝图文件映射表”，把每个 Phase 的目标文件统一校正为仓库真实路径，再开始实现。

---

### 2. action 命名统一方向写反了：主干是 `read/update`，不是 `view/edit`

**方案位置**:

- `docs/plans/2026-04-07-orthogonal-restructure-blueprint.md:74`
- `docs/plans/2026-04-07-orthogonal-restructure-blueprint.md:272`

**证据**:

- seed 的确使用 `read/create/update/delete`：`backend/scripts/setup/init_rbac_data.py:25-90`
- 现行主授权入口大量使用 `require_authz(action="read|create|update|delete", ...)`：
  - `backend/src/api/v1/auth/roles.py:205-207`
  - `backend/src/api/v1/auth/auth_modules/users.py:294-299`
  - `backend/src/api/v1/auth/organization.py`、`backend/src/api/v1/system/dictionaries.py` 等也都是同一模式
- 真正使用 `view/edit` 的是旧辅助层：`backend/src/security/permissions.py:241-278`

**判断**:

当前“代码使用 `view/create/edit/delete`”并不准确。更精确地说：

- **主干 ABAC/RBAC API 面**：`read/create/update/delete`
- **遗留 helper 面**：`view/create/edit/delete`

也就是说，问题不是“主干要迁到 view/edit”，而是“遗留 helper 要么退场，要么对齐主干”。

**影响**:

如果按方案把全仓往 `view/edit` 迁移，会把变更面从局部兼容修复，扩大成一次跨 API / policy / seed / test 的反向重构。

**建议**:

将 Phase 3 的动作命名目标改为：

- **统一到 `read/create/update/delete`**；
- `backend/src/security/permissions.py` 作为遗留兼容层收敛或清退；
- 不要反向推动主授权链路迁回 `view/edit`。

---

### 3. Phase 2 与 Phase 4 顺序冲突，会让双绑定分析/大屏先坏掉

**方案位置**:

- `docs/plans/2026-04-07-orthogonal-restructure-blueprint.md:185-208`
- `docs/plans/2026-04-07-orthogonal-restructure-blueprint.md:321-349`

**证据**:

- 当前前端仍通过 `applyPerspectiveHeader()` 自动注入 `X-Perspective`：`frontend/src/api/client.ts:133-147`
- 当前 `useAnalytics()` 没有 `view_mode` 参数，直接发分析请求：`frontend/src/hooks/useAnalytics.ts:8-26`
- 当前 `DashboardPage` 直接调用 `useAnalytics()`，没有 ViewMode 选择器或兜底状态：`frontend/src/pages/Dashboard/DashboardPage.tsx:19-24`
- 方案又要求：
  - Phase 2 移除 header，改为 `?view_mode=`
  - 双绑定用户在缺省 `view_mode` 时返回 `400`：`docs/plans/...:199-208`
  - 但真正的 `ViewModeSegment` 与 `currentViewMode` 承接要到 Phase 4 才落地：`docs/plans/...:321-324`

**影响**:

Phase 2 完成但 Phase 4 未完成时，双绑定用户的大屏/分析页会进入“前端不会带 `view_mode`、后端又要求显式指定”的中间失败态。

**建议**:

二选一：

1. **把 `currentViewMode` 最小实现 + 双绑定兜底策略前移到 Phase 2**；或
2. Phase 2 保留后端缺省回退策略（例如基于 primary binding 自动选定），直到 Phase 4 Segment 上线后再切到严格模式。

当前蓝图的时序不闭环。

---

## P1：高风险但可修正的问题

### 4. `perm_admin` / `system_admin` 控制面定义不完整，不能只改 `permissions.py`

**方案位置**:

- `docs/plans/2026-04-07-orthogonal-restructure-blueprint.md:239`
- `docs/plans/2026-04-07-orthogonal-restructure-blueprint.md:424`

**证据**:

- 方案把关键控制点落在 `backend/src/security/permissions.py`，但当前很多系统管理接口并不走这条路径。
- 用户创建接口直接依赖 `require_admin`：`backend/src/api/v1/auth/auth_modules/users.py:289-299`
- 数据策略包接口也直接依赖 `require_admin`：`backend/src/api/v1/auth/data_policies.py:25-29`, `47-52`, `74-78`
- 角色接口主干走的是 `require_authz`：`backend/src/api/v1/auth/roles.py:205-207`

**判断**:

若只改 `permissions.py`，并不能让 `perm_admin` 真正接管“用户/角色/权限”管理，也不能保证 `system_admin` / `perm_admin` 的边界一致。

**建议**:

把 Phase 3 / Phase 6 的权限面拆成 3 层统一处理：

1. `require_admin` 这类超级管理员短路依赖；
2. `require_authz` 资源授权入口；
3. 旧 `security/permissions.py` helper。

否则会出现“文档上 perm_admin 可以，实际接口仍然只认 admin”的半迁移状态。

---

### 5. Phase 6 低估了系统管理域改造面：现在不是“骨架”，而是“已有实现但契约仍是单角色”

**方案位置**:

- `docs/plans/2026-04-07-orthogonal-restructure-blueprint.md:71`
- `docs/plans/2026-04-07-orthogonal-restructure-blueprint.md:418-446`

**证据**:

- 用户管理并非空骨架，已有完整页面/组件树：`frontend/src/pages/System/UserManagement/index.tsx`、`components/UserTable.tsx`
- 但当前编辑表单仍按单角色 `role_id` 工作：`frontend/src/pages/System/UserManagement/index.tsx:161-172`
- 列表展示也是单 `role_name` 列：`frontend/src/pages/System/UserManagement/components/UserTable.tsx:73-89`
- 前端类型虽然额外暴露了 `roles` / `role_ids`，但 create/update 仍是单 `role_id`：`frontend/src/services/systemService.ts:9-27`, `47-65`
- 字典页也已是 748 行的大页面，不属于“骨架待补”：`frontend/src/pages/System/DictionaryPage.tsx`

**影响**:

Phase 6 真正要做的不是“补 CRUD”，而是：

- 用户/角色契约从单角色升级为多角色；
- 表单、表格、筛选、详情、接口 payload 一起改；
- 旧 `role_id/role_name` 与新 `role_ids/roles` 的兼容策略要明确。

**建议**:

将 Phase 6 拆成：

1. **后端用户-角色契约迁移**（含响应模型与写接口）；
2. **前端类型与表单模型迁移**；
3. **页面对齐与权限边界修正**。

否则当前 4-5 天估时偏乐观。

---

### 6. ABAC 已有“策略包管理面”和现成回填脚本，蓝图未复用，存在重复建设风险

**方案位置**:

- `docs/plans/2026-04-07-orthogonal-restructure-blueprint.md:365-367`

**证据**:

- 后端已有 `DataPolicyService`：`backend/src/services/authz/data_policy_service.py`
- 后端已有数据策略包 API：`backend/src/api/v1/auth/data_policies.py:25-81`
- 前端已有数据策略包管理页：`frontend/src/pages/System/DataPolicyManagementPage.tsx:26-120`
- 现有 `backfill_role_policies.py` 的真实路径存在：`backend/src/scripts/migration/party_migration/backfill_role_policies.py`
- 还有与策略包 seed 相关的测试：`backend/tests/unit/migration/test_policy_package_seed_actions.py`

**判断**:

仓库并不是“完全没有 ABAC 运维面”，而是已经有一套 **policy package** 思路，只是蓝图改写成了“新建 `init_abac_data.py` 直接灌表”。

**风险**:

如果 Phase 5 不先说明“复用现有 package 体系，还是另起一套 seed 体系”，后面很容易出现：

- 一套配置 UI / API；
- 另一套离线 seed；
- 两套来源都能改 `abac_role_policies`。

**建议**:

优先把 Phase 5 明确为：

- **在现有 `DataPolicyService` / policy package 体系上落地默认包与回填**；
- 仅在确认现有机制不足时，才补 `init_abac_data.py`；
- 蓝图中显式写清“单一真相入口”。

---

### 7. `27+` 资源目标过低，Phase 3 应先做 API 资源盘点再定目标数

**方案位置**:

- `docs/plans/2026-04-07-orthogonal-restructure-blueprint.md:243-266`

**证据**:

- 当前 seed 里只有 14 个资源：`backend/scripts/setup/init_rbac_data.py:25-90`
- 但当前后端源码里实际出现的 `resource_type` 已有 46 个，包括：
  - `analytics`、`contract_group`、`contract`、`custom_field`、`search`
  - `task`、`backup`、`system_monitoring`、`system_settings`
  - `operation_log`、`notification`、`llm_prompt`、`party`、`user_party_binding`
- 这意味着“14 → 27+”只是比当前 seed 更接近真实，但**仍不足以覆盖现有 API 面**。

**影响**:

- 如果按“补到 27+ 即完成”推进，Phase 3 结束后仍会留下大量未建模资源；
- `perm_admin` / `system_admin` / `viewer` 的权限矩阵会继续有盲区；
- reviewer 很难判断“哪些资源是故意不纳入，哪些是漏了”。

**建议**:

先把 Phase 3 的第一步改成：

1. 从 `backend/src/**` 自动导出当前全部 `resource_type` 清单；
2. 标记“保留 / 合并 / 废弃”；
3. 再据此冻结目标资源表。

也就是说，**目标应该是“覆盖真实资源全集”**，而不是预先写死“27+”。

---

## P2：文档一致性与估时问题

### 8. 方案内部对 `REQ-ANA-001` 的状态描述互相打架

**方案位置**:

- `docs/plans/2026-04-07-orthogonal-restructure-blueprint.md:56-57`
- `docs/plans/2026-04-07-orthogonal-restructure-blueprint.md:146`
- `docs/plans/2026-04-07-orthogonal-restructure-blueprint.md:330`
- `docs/plans/2026-04-07-orthogonal-restructure-blueprint.md:600`
- `docs/plans/2026-04-07-orthogonal-restructure-blueprint.md:618`

**问题**:

同一文档里同时存在以下说法：

- `REQ-ANA-001(部分)` 被记入 DONE 数量；
- `REQ-ANA-001` 又被记入“开发中”；
- Phase 1 说 REQ-ANA-001 要等 Phase 4 才能 DONE；
- 但验收矩阵又把 P15 / P23 写成 `ANA-001 DONE`。

**影响**:

这会让实施中途的状态同步、SSOT 更新和里程碑汇报都失真。

**建议**:

把 `REQ-ANA-001` 拆成显式子状态，例如：

- ANA-001.a 综合分析/导出：已完成
- ANA-001.b 指标补充：Phase 1
- ANA-001.c ViewMode 大屏：Phase 4

或者在蓝图里统一写成“REQ-ANA-001 整体仍为 🚧，其下部分能力已完成”。

### 9. 风险缓释里的长兼容期，与仓库当前执行约束冲突

**方案位置**:

- `docs/plans/2026-04-07-orthogonal-restructure-blueprint.md:565-567`

**证据**:

- 蓝图风险表提出：
  - “旧角色保留 7 天兼容期”
  - “后端保留 deprecated 兼容层，直到确认无旧客户端”
- 但仓库协作约束明确写的是：
  - “项目目前在从0到1阶段的开发中，不要做兼容保留操作，充分的暴露问题，要打牢系统基础。”（`AGENTS.md:4-5`）

**影响**:

- 文档执行原则会互相打架：实现者无法判断应优先“快速收口”还是“长期兼容”；
- Phase 2 / Phase 3 都会倾向引入临时双轨逻辑，扩大测试面和清理成本。

**建议**:

将兼容策略改成**有截止日期的短窗口迁移**，而不是开放式兼容：

- 例如“同版本内保留 1 个发布窗口，仅用于回滚兜底”；
- 或者在 0→1 阶段直接采用“一次性切换 + 明确回滚方案”。

至少蓝图正文需要与 `AGENTS.md` 的工程原则保持一致。

---

## 正向结论：哪些部分已经具备执行基础

以下内容说明这份蓝图不是“空中楼阁”，修正文档后可以快速落地：

1. **Phase 1 有现成前端落点**
   - `frontend/src/pages/Assets/AssetDetailPage.tsx` 已有详情承载位；
   - `frontend/src/pages/ContractGroup/ContractGroupDetailPage.tsx` 已有代理模式提示，说明口径标识不是从零开始。

2. **Phase 2 有完整迁移抓手**
   - 后端 header 解析集中在 `backend/src/middleware/auth.py`；
   - 前端 header 注入集中在 `frontend/src/api/client.ts`；
   - 数据范围状态集中在 `frontend/src/stores/dataScopeStore.ts`。

3. **Phase 3/5 的真实问题已在代码中能定位**
   - `statistics` seed vs `analytics` resource_type 冲突可直接复现：`backend/scripts/setup/init_rbac_data.py:52-53` 对比 `backend/src/api/v1/analytics/analytics.py:56-61`
   - ABAC deny 覆盖与缓存键问题已有明确实现入口：`backend/src/services/authz/service.py:118-130`、`backend/src/services/authz/cache.py:27-40`

4. **Phase 6 不是没基础，而是要重构现有系统管理契约**
   - 用户、角色、组织、字典页都已存在；
   - 说明风险更多在“契约迁移”，不是“从零搭页面”。

---

## 复核结论

**建议结论：有条件通过。**

这份蓝图可以继续作为总蓝图保留，但在正式执行前，至少应先完成以下修订：

1. 修正所有错误文件路径；
2. 把 action 统一目标改为 `read/create/update/delete`；
3. 重排 Phase 2 / Phase 4 的 `view_mode` 承接顺序；
4. 扩大 `perm_admin` 改造范围，覆盖 `require_admin` 与 `require_authz` 实际入口；
5. 将 Phase 6 改写为“多角色契约迁移 + 页面对齐”，重估工时；
6. 明确 ABAC 只保留一套配置真相源，优先复用现有 data policy package 体系；
7. 先基于真实 `resource_type` 全量盘点再冻结资源矩阵目标；
8. 让兼容策略与仓库“0→1 不做长期兼容保留”的原则一致。

如果这 8 点不先修，方案在实施中大概率会出现：路径偏差、动作命名反向重构、双绑定分析页中间态故障、权限矩阵漏资源、以及 `perm_admin` 落地不一致。
