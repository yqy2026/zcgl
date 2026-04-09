# 角色-绑定-视图三维正交重构实施蓝图

- **状态**：✅ 已完成（2026-04-08）
- **创建日期**：2026-04-07
- **修订**：v4（2026-04-07），基于 `docs/archive/reviews/2026-04-07-orthogonal-restructure-blueprint-review-v2.md` 的第三轮复审修订
- **归档说明**：本文任务已全部执行完毕，最终需求状态与代码证据以 `docs/requirements-specification.md` 为准。
- **前置**：Phase 0（需求确认 + 文档矛盾消除）已完成（2026-04-06）
- **吸收方案**：
  - `2026-04-05-perspective-residue-eradication-plan.md` → Phase 2
  - `2026-04-05-requirements-update-plan.md` → Phase 4
  - `2026-04-05-rbac-role-realignment.md` → Phase 3 + Phase 5
- **里程碑对齐**：M2（~05-10）→ M3（05-11~06-07）→ M4（06-08~06-30）
- **决策依据**：`docs/interviews/2026-04-06-architecture-restructure-decisions.md`（Q1-Q6）

---

## 目录

1. [背景与根因](#1-背景与根因)
2. [当前状态速查](#2-当前状态速查)
3. [Phase 总览](#3-phase-总览)
4. [文件映射表](#4-文件映射表)
5. [Phase 1：🚧 需求收口](#5-phase-1需求收口)
6. [Phase 2：术语收口 + view_mode 最小承接](#6-phase-2术语收口--viewmode-最小承接)
7. [Phase 3：RBAC 角色重定义与权限资源补齐](#7-phase-3rbac-角色重定义与权限资源补齐)
8. [Phase 4：分析引擎增强](#8-phase-4分析引擎增强)
9. [Phase 5：ABAC 激活与安全加固](#9-phase-5abac-激活与安全加固)
10. [Phase 6：系统管理域多角色契约迁移](#10-phase-6系统管理域多角色契约迁移)
11. [Phase 7：死代码清理与验收闭环](#11-phase-7死代码清理与验收闭环)
12. [里程碑排期](#12-里程碑排期)
13. [异常项与技术债](#13-异常项与技术债)
14. [风险与缓释](#14-风险与缓释)
15. [验收场景对齐矩阵](#15-验收场景对齐矩阵)

---

## v2 修订摘要

基于复核报告 9 项意见的逐条回应：

| # | 复核意见 | 处置 |
|---|---------|------|
| 1 | 文件路径多处写错 | 采纳：新增 §4 文件映射表，全文路径修正 |
| 2 | action 命名方向写反 | 采纳：统一目标改为 `read/create/update/delete`，`permissions.py` 便捷层作为遗留清退 |
| 3 | Phase 2/4 时序冲突 | 采纳：Phase 2 新增 `currentViewMode` 最小实现 + 双绑定 auto-fallback，Phase 4 升级为完整 Segment UI |
| 4 | perm_admin 控制面不完整 | 采纳：拆为 3 层统一处理（`require_admin` / `require_authz` / 遗留 helper） |
| 5 | Phase 6 低估改造面 | 采纳：重写为"多角色契约迁移"，拆 3 步，工时上调至 5-7 天 |
| 6 | ABAC 存在重复建设风险 | 采纳：复用现有 `DataPolicyService` + policy package 体系，单一真相入口 |
| 7 | 资源目标 27+ 过低 | 采纳：改为先全量盘点再冻结，不预设固定数字 |
| 8 | REQ-ANA-001 状态互相打架 | 采纳：拆为 ANA-001.a/b/c 三个子状态 |
| 9 | 长兼容期与 0→1 原则冲突 | 采纳：改为一次性切换 + 明确回滚方案，不设长期双轨 |

---

## v3 修订摘要

基于 v2 复核报告 9 项意见的逐条回应：

| # | 复核意见 | 处置 |
|---|---------|------|
| P1-1 | REQ-RNT-002 "一资产一合同组"约束未落到任务清单 | 采纳：Phase 1 新增 DB 唯一约束 + Service 校验 + integration test |
| P1-2 | Phase 2 "primary binding 自动选定"没有真实数据来源 | 采纳：改为固定优先级规则（owner > manager），不依赖 is_primary 字段 |
| P1-3 | Phase 2/4 前端改造面偏窄，遗漏 service 层与导出调用点 | 采纳：文件映射表 + Phase 2/4 任务新增 `analyticsService.ts`、`AnalyticsDashboard.tsx`、`useDashboardData.ts` |
| P1-4 | Phase 2 缺少 SSOT 文档同步任务 | 采纳：Phase 2 新增 §6.3 SSOT 更新（`REQ-SCH-003` / `REQ-AUTH-002` 状态同步） |
| P1-5 | `trend`/`distribution` 端点未纳入 view_mode 改造 | 采纳：Phase 2 后端新增"分析端点全量审计"任务，覆盖 comprehensive/export/trend/distribution |
| P1-6 | "通过 DataPolicyService 创建默认策略包"表述不准确 | 采纳：Phase 5 任务 1 拆为两步（1a 确保模板入库 + 1b 绑定角色） |
| P2-1 | `require_role([...])` 多角色 helper 不存在 | 采纳：Phase 3 明确新增 `require_any_role(role_codes)` helper |
| P2-2 | 资源盘点 Step 0 需要定义清洗规则 | 采纳：补充 4 条清洗规则（snake_case 小写/排除伪值/分层标记/人工标注后冻结） |
| L1 | Phase 6 "保留 role_name 做兼容派生"与 0→1 原则有张力 | 采纳：标注为 Phase 6 过渡字段，Phase 7 强制移除 |

---

## v4 修订摘要

基于第三轮深审新增问题的逐条回应：

| # | 复核意见 | 处置 |
|---|---------|------|
| P1-7 | `asset_id` 全局唯一约束与“逻辑删除不清关联”实现冲突 | 采纳：Phase 1 改为“先 service 校验 + 集成测试”，DB 约束仅在补齐软删清关联或 active 关联模型后再上 |
| P1-8 | `statistics_modules/*.py` 未纳入分析域统一审计 | 采纳：Phase 2 后端任务扩展为覆盖 `analytics.py` + `statistics.py` + `statistics_modules/*.py` |
| P1-9 | Phase 5 内部仍残留“DataPolicyService 创建模板策略”的旧说法 | 采纳：统一改为“seed migration/Alembic 入库模板，DataPolicyService 负责绑定与管理” |
| P1-10 | `backfill_role_policies.py` 仍按旧角色关键词启发式映射策略包 | 采纳：Phase 5 新增显式角色→策略白名单映射改造，再执行绑定 |

---

## 1. 背景与根因

`perspective`（视角）一词同时承载了三个正交概念：

| 维度 | 含义 | 目标边界 |
|------|------|----------|
| **角色 (Role)** | 你能做什么操作 | 纯 RBAC + ABAC 权限矩阵 |
| **绑定 (Binding)** | 你属于哪个组织，看哪批数据 | 纯 Party 过滤 |
| **视图 (View)** | 同一数据用什么业务口径解读 | 纯展示/统计逻辑 |

三个先前活跃方案各有盲区（详见决策采访记录），现统一吸收为 7 个 Phase。

Phase 0（需求确认 + 文档矛盾消除）已于 2026-04-06 完成，涵盖：§5 三维模型重写、§8.3 修正、§15 补充、34 个验收场景、vNext 标注、字段附录对齐。

---

## 2. 当前状态速查

### 2.1 REQ 状态

> 归档快照：截至 2026-04-08，本文涉及 REQ 已全部收口为 ✅；本节以下表格保留执行期上下文，最终状态请以 `docs/requirements-specification.md` 为准。

REQ-ANA-001 拆为显式子状态以消除歧义：

| 状态 | 数量 | 明细 |
|------|------|------|
| DONE | 23 | REQ-AST-001/002/004, REQ-PRJ-001/002, REQ-RNT-001~006, REQ-DOC-001, REQ-CUS-001/002, REQ-PTY-001/002, REQ-SCH-001~003, REQ-AUTH-001/002, REQ-APR-001 |
| 🚧 开发中 | 3 | REQ-AST-003, REQ-RNT-002, REQ-ANA-001（整体 🚧；其中 ANA-001.a 综合分析/导出已完成，ANA-001.b 指标补充 Phase 1，ANA-001.c ViewMode 大屏 Phase 4） |
| 📋 待开发 | 3 | REQ-SYS-001, REQ-SYS-002, REQ-SYS-003 |
| XCUT 横切 | 4 | XCUT-001~004（全部 DONE） |

### 2.2 关键代码状态

| 模块 | 状态 | 备注 |
|------|------|------|
| RBAC 角色 | 旧 7 角色 | 目标 6 角色，迁移未开始 |
| ABAC | 未激活 | 模型/模板/策略包管理面已存在，`abac_role_policies` 未填充 |
| 权限资源 | seed 14 个 | 代码中实际出现 ~50 个 `resource_type`，需全量盘点后冻结 |
| analytics/statistics | 命名冲突 | seed 注册 `statistics`，代码使用 `analytics` |
| X-Perspective header | 仍在发送 | 需废弃，改为 `?view_mode=` |
| ViewMode Segment | 不存在 | 需新建大屏口径切换器 |
| 系统管理页面 | 已有实现但契约为单角色 | 需从 `role_id` 迁移到 `role_ids[]` 多角色契约 |
| asset review (AST-003) | 后端完成 | 需确认前端+审批联动 |
| 台账 (Ledger) | 已实现 | ContractLedgerEntry + ServiceFeeLedger |
| action 命名 | 不一致 | 主干 `require_authz` 用 `read/create/update/delete`；遗留 `permissions.py` 用 `view/create/edit/delete` |
| 授权入口 | 三层并存 | `require_admin`（超管短路）/ `require_authz`（ABAC/RBAC 主干）/ `permissions.py`（遗留 helper） |

---

## 3. Phase 总览

| Phase | 主题 | 涉及 REQ | 预估工时 | 里程碑 |
|-------|------|----------|----------|--------|
| ~~0~~ | ~~需求确认 + 文档矛盾消除~~ | — | ~~1 天~~ | ~~已完成~~ |
| **1** | 🚧 需求收口 | AST-003, RNT-002, ANA-001.b | 3 天 | M2 |
| **2** | 术语收口 + view_mode 最小承接 | AUTH-002 后续 | 2.5 天 | M2 |
| **3** | RBAC 角色重定义 + 权限资源补齐 | SYS-001 部分 | 4-5 天 | M3 |
| **4** | 分析引擎增强 | ANA-001.c | 2-3 天 | M3 |
| **5** | ABAC 激活与安全加固 | 新增 REQ-AUTH-003 | 2-3 天 | M3 |
| **6** | 系统管理域多角色契约迁移 | SYS-001/002/003 | 5-7 天 | M4 |
| **7** | 死代码清理 + 验收闭环 | 全部 | 2-3 天 | M4 |
| | **合计** | | **20.5-26.5 天** | |

---

## 4. 文件映射表

每个 Phase 涉及的**真实仓库路径**，消除执行时的路径歧义：

### 后端分析/统计

| 蓝图引用 | 真实路径 |
|----------|----------|
| 分析 API | `backend/src/api/v1/analytics/analytics.py` |
| 统计 API | `backend/src/api/v1/analytics/statistics.py` |
| 统计子模块 | `backend/src/api/v1/analytics/statistics_modules/*.py` |
| 分析服务 | `backend/src/services/analytics/analytics_service.py` |

### 后端权限/授权

| 蓝图引用 | 真实路径 |
|----------|----------|
| RBAC seed | `backend/scripts/setup/init_rbac_data.py` |
| 授权引擎 | `backend/src/services/authz/service.py` |
| 授权缓存 | `backend/src/services/authz/cache.py` |
| 数据策略服务 | `backend/src/services/authz/data_policy_service.py` |
| 数据策略 API | `backend/src/api/v1/auth/data_policies.py` |
| 遗留权限 helper | `backend/src/security/permissions.py` |
| ABAC 模型 | `backend/src/models/abac.py` |
| ABAC 回填脚本 | `backend/src/scripts/migration/party_migration/backfill_role_policies.py` |
| 策略包测试 | `backend/tests/unit/migration/test_policy_package_seed_actions.py` |
| auth middleware | `backend/src/middleware/auth.py` |

### 后端系统管理

| 蓝图引用 | 真实路径 |
|----------|----------|
| 用户管理 API | `backend/src/api/v1/auth/auth_modules/users.py` |
| 角色管理 API | `backend/src/api/v1/auth/roles.py` |
| 组织管理 API | `backend/src/api/v1/auth/organization.py` |
| 字典管理 API | `backend/src/api/v1/system/dictionaries.py` |
| 管理员 API | `backend/src/api/v1/auth/admin.py` |

### 前端

| 蓝图引用 | 真实路径 |
|----------|----------|
| API 客户端 | `frontend/src/api/client.ts` |
| 数据范围 store | `frontend/src/stores/dataScopeStore.ts` |
| 分析 hooks | `frontend/src/hooks/useAnalytics.ts` |
| 分析服务（前端） | `frontend/src/services/analyticsService.ts` |
| 分析组件 | `frontend/src/components/Analytics/` |
| 分析仪表盘组件 | `frontend/src/components/Analytics/AnalyticsDashboard.tsx` |
| 大屏页面 | `frontend/src/pages/Dashboard/DashboardPage.tsx` |
| 大屏数据 hook | `frontend/src/pages/Dashboard/useDashboardData.ts` |
| 用户管理页 | `frontend/src/pages/System/UserManagement/index.tsx` |
| 用户表格组件 | `frontend/src/pages/System/UserManagement/components/UserTable.tsx` |
| 角色管理页 | `frontend/src/pages/System/RoleManagementPage.tsx` |
| 组织管理页 | `frontend/src/pages/System/OrganizationPage.tsx` |
| 字典管理页 | `frontend/src/pages/System/DictionaryPage.tsx` |
| 数据策略管理页 | `frontend/src/pages/System/DataPolicyManagementPage.tsx` |
| 系统服务 | `frontend/src/services/systemService.ts` |

---

## 5. Phase 1：🚧 需求收口

**目标**：将 3 个 🚧 REQ 中的 AST-003、RNT-002 推进到 DONE，ANA-001.b 指标补充完成。

### 5.1 REQ-AST-003：关键主数据审核与反审核

**现状**：后端 6 个审核方法全部实现（submit/approve/reject/reverse/resubmit/withdraw），`AssetReviewStatus` 枚举、`AssetReviewLog` 模型、编辑/删除阻塞全部就位。

**剩余工作**：

| # | 任务 | 文件/模块 | TDD |
|---|------|-----------|-----|
| 1.1 | 前端资产详情页审核状态展示 + 操作按钮 | `frontend/src/pages/Assets/AssetDetailPage.tsx` | 先写 test：审核状态渲染、按钮可见性 |
| 1.2 | 前端审核操作调用 API（submit/approve/reject 等） | `frontend/src/api/` + `frontend/src/hooks/` | 先写 test：API 调用参数、成功/失败回调 |
| 1.3 | 审批流联动验证（REQ-APR-001 已实现的审批域与资产审核的集成） | `backend/src/services/approval/` ↔ `backend/src/services/asset/asset_service.py` | 先写 integration test：发起审批→审批通过→资产状态变更 |
| 1.4 | SSOT 更新：REQ-AST-003 状态标记 | `docs/requirements-specification.md` | — |

**验收标准**：
- 前端可完成资产审核全生命周期（提交→审批→驳回→重提→撤回→反审核）
- 审批域与资产审核状态联动正确
- 编辑/删除在审核中/已审核状态下被正确阻塞

### 5.2 REQ-RNT-002：承租模式与代理模式并行

**现状**：后端校验/服务/分析已实现，前端 `ContractGroupDetailPage.tsx` 已有代理口径提示。

**剩余工作**：

| # | 任务 | 文件/模块 | TDD |
|---|------|-----------|-----|
| 2.1 | 前端合同组表单：经营模式选择 + 模式互斥校验 UI 反馈 | `frontend/src/pages/ContractGroup/` | 先写 test：模式切换、互斥校验消息 |
| 2.2 | 前端列表/详情：代理模式口径标识清晰展示 | `frontend/src/pages/ContractGroup/` | 先写 test：口径标签渲染 |
| 2.3 | 回归验证：`validate_revenue_mode_compatibility()` 拦截正常工作 | `backend/tests/` | 已有测试，补充边界用例 |
| 2.4 | **一资产一合同组 Service 校验（先行落地）**：`_replace_assets()` 调用前检查资产是否已属于其他“有效合同组”，重复则拒绝 | `backend/src/crud/contract_group.py`, `backend/src/services/` | 先写 integration test：资产已绑定合同组 A → 绑定合同组 B → 拦截并返回明确错误 |
| 2.5 | **DB 约束方案评估并择机落地**：仅在补齐“软删合同组时同步清理关联”或“关联表支持 active/inactive 标记”后，才增加 `asset_id` 唯一约束/条件唯一约束 | `backend/src/models/associations.py`, `backend/alembic/versions/`, `backend/src/crud/contract_group.py` | 先写 design/migration test：逻辑删除后的历史重绑场景不被误伤 |
| 2.6 | SSOT 更新：REQ-RNT-002 状态标记 | `docs/requirements-specification.md` | — |

**验收标准**：
- 合同组创建时经营模式必选且不可混用
- 代理模式下前端展示清晰的口径标识
- 一个资产不允许同时关联多个**有效**合同组（Q1 决策）

### 5.3 REQ-ANA-001.b：指标补充

**现状**：综合分析 + Excel 导出已完成（ANA-001.a），但缺少"当期实收"和"租金收缴率"指标。

**剩余工作**（本 Phase 仅做数据补充，大屏 ViewMode 在 Phase 4）：

| # | 任务 | 文件/模块 | TDD |
|---|------|-----------|-----|
| 3.1 | 后端新增"当期实收"指标计算 | `backend/src/services/analytics/analytics_service.py` | 先写 test：实收计算逻辑、边界（无实收记录返回 0） |
| 3.2 | 后端新增"租金收缴率"指标（公式：§3.3 已冻结） | `backend/src/services/analytics/analytics_service.py` | 先写 test：收缴率计算、分母为 0 处理 |
| 3.3 | 前端分析页面展示新增指标 | `frontend/src/components/Analytics/` | 先写 test：指标渲染、数值格式化 |

### 边界情况

- 资产处于"审核中"状态时，合同签订应被拦截
- 代理模式下金额口径为"应付/实付"而非"应收/实收"
- 租金收缴率分母为 0 时返回 null 而非 0%
- 无实收台账记录的合同组，实收指标返回 0

### 建议测试用例

1. 资产审核状态机全路径覆盖（6 个方法 × 合法/非法前置状态）
2. 审批域联动：审批通过 → 资产自动变为已审核
3. 模式互斥：尝试在已有承租合同的合同组中添加代理合同 → 拦截
4. 一个资产关联第二个合同组 → 拦截
5. 收缴率分母为 0 → null
6. 双绑定用户访问分析指标 → 并集数据

---

## 6. Phase 2：术语收口 + view_mode 最小承接

**目标**：废弃 `X-Perspective` header，引入 `?view_mode=` query param，**同时落地 `currentViewMode` 最小实现**，确保双绑定用户分析页面不出现中间失败态。

**决策依据**：Q5（废弃 X-Perspective），Q2（大屏 Segment）

> **v2 修订说明**：原方案 Phase 2 仅做术语切换，Phase 4 才补 UI 承接，导致双绑定用户在 Phase 2~4 之间进入"前端不带 view_mode、后端要求显式指定"的故障态。现将最小 view_mode 状态管理前移到 Phase 2，Phase 4 仅升级为完整 Segment UI。

### 6.1 后端

| # | 任务 | 文件/模块 | TDD |
|---|------|-----------|-----|
| 1 | 新增 `view_mode` query param 支持（仅分析/大屏端点） | `backend/src/api/v1/analytics/analytics.py`, `backend/src/api/v1/analytics/statistics.py` | 先写 test：`?view_mode=owner` → 产权方口径数据 |
| 2 | view_mode 缺省行为：单绑定 → 自动选择对应口径；双绑定 → **固定优先级 owner > manager**（不返回 400） | `backend/src/api/v1/analytics/analytics.py` | 先写 test：双绑定无 view_mode → 自动 fallback 到 owner 口径 |
| 3 | 一次性移除 `X-Perspective` header 解析（0→1 不保留兼容层） | `backend/src/middleware/auth.py` | 先写 test：header 存在时被忽略，不影响请求处理 |
| 4 | 后端代码中 `perspective` 参数重命名为 `view_mode`（分析服务层） | `backend/src/services/analytics/` | 先写 test：服务层接受 view_mode 枚举 |
| 5 | 后端日志/注释中 `perspective` 引用清理 | 全局搜索替换 | grep 验证零残留 |
| 6 | **分析端点全量审计**：`analytics.py` + `statistics.py` + `statistics_modules/*.py` 全部统一接入 `view_mode` / `require_data_scope_context` / scope filter，确保分析域契约一致 | `backend/src/api/v1/analytics/analytics.py`, `backend/src/api/v1/analytics/statistics.py`, `backend/src/api/v1/analytics/statistics_modules/*.py` | 先写 test：trend/distribution/basic/area/financial 端点带 view_mode → 按口径过滤 |

### 6.2 前端

| # | 任务 | 文件/模块 | TDD |
|---|------|-----------|-----|
| 7 | 移除 `applyPerspectiveHeader` 函数 | `frontend/src/api/client.ts` (lines 133-147) | 先写 test：请求不再包含 X-Perspective header |
| 8 | 分析/大屏 API 调用改为 `?view_mode=` query param | `frontend/src/hooks/useAnalytics.ts` | 先写 test：API URL 包含 view_mode param |
| 9 | **`analyticsService.ts` 全量适配**：`getComprehensiveAnalytics`/`getBasicStatistics`/`getAreaSummary`/`getFinancialSummary`/`exportAnalyticsReport` 等方法统一传入 `view_mode` 参数 | `frontend/src/services/analyticsService.ts` | 先写 test：每个分析/导出方法的请求携带 view_mode |
| 10 | **Dashboard 数据 hook 适配**：`useDashboardData.ts` 调用 service 时传递 `currentViewMode` | `frontend/src/pages/Dashboard/useDashboardData.ts` | 先写 test：hook 发起的请求携带 view_mode |
| 11 | `dataScopeStore` 新增 `currentViewMode` 派生状态 + auto-select 逻辑（固定优先级 owner > manager） | `frontend/src/stores/dataScopeStore.ts` | 先写 test：单绑定 → 自动 view_mode；双绑定 → 默认 owner |
| 12 | 大屏页面适配：双绑定用户使用 auto-selected view_mode 渲染（Phase 4 替换为 Segment） | `frontend/src/pages/Dashboard/DashboardPage.tsx` | 先写 test：双绑定用户大屏正常渲染，不出 400 |
| 13 | 前端代码中 `perspective` 引用清理 | 全局搜索 | grep 验证零残留 |

### 6.3 SSOT 更新

> **v3 新增**：Phase 2 废弃 `X-Perspective` 后，必须同步更新 SSOT 文档。

| # | 任务 |
|---|------|
| 14 | 更新 `docs/requirements-specification.md` 中 `REQ-SCH-003` 状态描述：移除"代码仍活跃使用 X-Perspective，计划废弃"，标记"已完成废弃，改为 view_mode query param" |
| 15 | 更新 `docs/requirements-specification.md` 中 `REQ-AUTH-002` 状态描述：移除"前端单绑定时仍注入 X-Perspective header，计划废弃"，标记"已完成废弃" |
| 16 | 同步 `CHANGELOG.md` |

### 验收标准

- `X-Perspective` header 不再出现在任何 HTTP 请求中（一次性切除，无兼容期）
- 分析/大屏端点通过 `?view_mode=owner|manager` 接收口径选择
- **`analytics.py` 与 `statistics_modules/*.py` 全部分析端点同样接入 `view_mode` / scope context**，分析域契约一致
- 常规 CRUD 端点不使用 `view_mode`
- **双绑定用户在 Phase 2 完成后即可正常访问大屏**（auto-fallback 到 owner 口径）
- 单绑定用户行为不变
- **`REQ-SCH-003` / `REQ-AUTH-002` SSOT 状态已同步更新**

### 边界情况

- view_mode 缺省时行为：单绑定 → 自动选择，双绑定 → **固定优先级 owner > manager**（产权方优先，理由：产权方是平台主体、数据量更大；Phase 4 Segment UI 上线后用户可手动切换）
- admin 用户不传 view_mode 时 → 返回全量数据（不分口径）
- `currentViewMode` 需持久化用户偏好（localStorage），Phase 4 Segment 切换后写入

### 建议测试用例

1. 分析端点 + `?view_mode=owner` → 仅产权方口径数据
2. 分析端点 + `?view_mode=manager` → 仅运营方口径数据
3. 分析端点无 view_mode + 单绑定 → 自动选择
4. 分析端点无 view_mode + 双绑定 → 自动 fallback 到 owner 口径（不返回 400）
5. CRUD 端点 + view_mode → 忽略（不影响数据过滤）
6. admin → 全量数据
7. `trend` 端点 + `?view_mode=owner` → 按口径过滤趋势数据
8. `distribution` 端点 + `?view_mode=manager` → 按口径过滤分布数据
9. `statistics_modules/basic/area/financial` 端点 + `?view_mode=` → 按口径过滤
10. `analyticsService.ts` 各方法请求均携带 view_mode 参数

---

## 7. Phase 3：RBAC 角色重定义与权限资源补齐

**目标**：7 角色 → 6 角色，权限资源全量盘点后冻结，统一 action 命名，修复 analytics/statistics 冲突，审计授权入口三层覆盖。

**决策依据**：Q6（perm_admin 隔离），`docs/plans/2026-04-05-rbac-role-realignment.md` Phase 1

### 7.1 角色迁移

**旧角色（7 个）**：admin, manager, user, viewer, asset_manager, project_manager, auditor

**新角色（6 个）**：

| 角色 | 说明 | 业务数据 | 系统管理 |
|------|------|----------|----------|
| system_admin | 系统管理员 | 全量 | 全量 |
| ops_admin | 运营管理员 | 全量（受绑定约束） | 无 |
| perm_admin | 权限管理员 | **零访问**（Q6 决策） | 用户/角色/权限/数据策略 |
| reviewer | 审核员 | 只读 + 审批操作 | 无 |
| executive | 业务经办 | CRUD（受绑定约束） | 无 |
| viewer | 只读用户 | 只读（受绑定约束） | 无 |

| # | 任务 | 文件/模块 | TDD |
|---|------|-----------|-----|
| 1 | 重写 `init_rbac_data.py`：6 角色 + 盘点后冻结的资源 + 权限矩阵 | `backend/scripts/setup/init_rbac_data.py` | 先写 test：seed 后验证角色/权限数量 |
| 2 | Alembic 迁移：一次性角色重命名 + 用户角色绑定迁移（无兼容期） | `backend/alembic/versions/` | 先写 test：迁移前后数据一致性 |

### 7.2 权限资源全量盘点

> **v2 修订说明**：原方案预设"14→27+"目标，但仓库中实际存在 ~50 个 `resource_type`。应先全量盘点再冻结，而非预先写死数字。

| # | 任务 | 文件/模块 | TDD |
|---|------|-----------|-----|
| 3 | **Step 0**：从 `backend/src/**` 自动导出当前全部 `resource_type` 清单，按以下清洗规则处理 | 脚本 / grep | — |

> **v3 新增 — Step 0 清洗规则**：
> 1. 全部转 `snake_case` 小写（如 `Asset` → `asset`，`ApprovalInstance` → `approval_instance`）
> 2. 排除测试/示例/异常消息中的伪资源值
> 3. 内部实现资源（如 `user_role_assignment`、`primary_contact`）与对外授权资源分层标记
> 4. 输出清单后必须**人工标注"保留/合并/废弃"**再冻结，不自动采信脚本输出
| 4 | **Step 1**：标记每个资源"保留 / 合并 / 废弃"，冻结目标资源表 | 蓝图文档更新 | — |
| 5 | **Step 2**：seed data 覆盖冻结后的全部资源定义 | `backend/scripts/setup/init_rbac_data.py` | test：验证全部冻结资源存在 |

### 7.3 授权入口三层统一

> **v2 修订说明**：当前授权有三层入口并存，仅改 `permissions.py` 不能让 `perm_admin` 真正生效。

**三层现状**：
1. **`require_admin`**（超管短路）：`users.py`、`audit.py`、`security.py`、`admin.py`、`data_policies.py` 大量使用
2. **`require_authz`**（ABAC/RBAC 主干）：`roles.py`、`organization.py`、`assets.py`、`contract_groups.py` 等
3. **`permissions.py`**（遗留 helper）：使用 `view/edit` 命名，当前未被 API 层直接调用

| # | 任务 | 文件/模块 | TDD |
|---|------|-----------|-----|
| 6 | 审计全部 `require_admin` 调用点，按新角色策略逐个改写为 `require_authz` 或新的 `require_any_role(role_codes)` | 见文件映射表 auth 部分 | 先写 test：perm_admin 可访问用户/角色管理，不可访问业务数据 |
| 6a | **新增 `require_any_role(role_codes: list[str])` helper**：遍历用户角色取交集，匹配任一即放行；作为 `require_admin` → `require_authz` 过渡期间系统管理端点的守卫，Phase 7 评估是否全部统一到 `require_authz` | `backend/src/security/permissions.py` | 先写 test：`require_any_role(["system_admin", "perm_admin"])` → system_admin 通过、perm_admin 通过、executive 拒绝 |
| 7 | `perm_admin` 业务数据零权限强制（不仅是 `permissions.py`，还包括 `require_admin` 短路路径） | `backend/src/middleware/auth.py` + 全部 admin 入口 | 先写 test：perm_admin 请求 `/api/v1/assets` → 403 |
| 8 | 遗留 `permissions.py` helper 评估：能否退场或收窄为内部工具 | `backend/src/security/permissions.py` | — |

### 7.4 命名统一

> **v2 修订说明**：action 统一目标改为 `read/create/update/delete`（主干 `require_authz` 已在用），不是 `view/edit`。

| # | 任务 | 文件/模块 | TDD |
|---|------|-----------|-----|
| 9 | 确认 seed + `require_authz` 均已使用 `read/create/update/delete`（当前已一致） | `init_rbac_data.py` + API 层 | grep 验证 |
| 10 | 遗留 `permissions.py` 中 `view/edit` 便捷函数：标注 deprecated 或重写为 `read/update` | `backend/src/security/permissions.py` | test：新旧 action 映射正确 |
| 11 | 统一 analytics/statistics：合并为 `analytics` 资源，seed 中删除 `statistics` | `init_rbac_data.py` + `backend/src/api/v1/analytics/statistics.py` | test：statistics 端点使用 `resource_type="analytics"` |
| 12 | CRUD 层 party filtering 全量审计 | `backend/src/crud/*.py` | test：每个 CRUD list 方法正确应用 party filter |

### 验收标准

- 系统启动后有且仅有 6 个角色
- 权限矩阵覆盖盘点冻结后的全部资源 × 6 角色
- `perm_admin` 通过任何入口（`require_admin`/`require_authz`/helper）请求业务资源均 → 403
- `perm_admin` 可管理用户/角色/权限/数据策略
- analytics/statistics 命名统一，无 `resource_type` 不匹配
- action 命名全仓统一为 `read/create/update/delete`
- 所有 CRUD list 方法正确应用 party filtering

### 边界情况

- 旧角色名在数据库中已有用户绑定 → Alembic 迁移一次性映射
- admin → system_admin 后权限不变
- user + asset_manager + project_manager → 按实际权限映射到 executive 或拆分
- seed 幂等：重复运行不创建重复数据
- `data_policies.py` 当前走 `require_admin`，迁移后应同时允许 `perm_admin`

### 建议测试用例

1. perm_admin 请求 `/api/v1/assets` → 403
2. perm_admin 请求 `/api/v1/auth/users` → 200
3. perm_admin 请求 `/api/v1/auth/data-policies` → 200
4. system_admin 请求所有资源 → 200
5. viewer 尝试 POST → 403
6. reviewer 尝试 DELETE → 403
7. executive 请求自己绑定的数据 → 200
8. executive 请求其他组织数据 → 过滤后空列表
9. seed 运行两次 → 角色/权限数量不变
10. analytics/statistics 端点统一使用 `analytics` 资源 → 非管理员正确授权

---

## 8. Phase 4：分析引擎增强

**目标**：大屏 ViewMode Segment 切换器，替换 Phase 2 的 auto-fallback，提供用户可控的口径选择。

**决策依据**：Q2（大屏 Tab），`docs/plans/2026-04-05-requirements-update-plan.md` P2+P3

### 8.1 后端

| # | 任务 | 文件/模块 | TDD |
|---|------|-----------|-----|
| 1 | 分析服务按 view_mode 分口径返回数据（确认 Phase 2 基础已就位） | `backend/src/services/analytics/analytics_service.py` | 先写 test：owner 口径 vs manager 口径数据隔离 |
| 2 | 双绑定用户显式传 view_mode 时后端严格按指定口径（覆盖 auto-fallback） | `backend/src/api/v1/analytics/analytics.py` | test 已在 Phase 2 覆盖 |

### 8.2 前端

| # | 任务 | 文件/模块 | TDD |
|---|------|-----------|-----|
| 3 | 新建 `ViewModeSegment` 组件 | `frontend/src/components/Analytics/ViewModeSegment.tsx` | 先写 test：双绑定用户可见，单绑定隐藏 |
| 4 | 大屏/分析页面集成 Segment 切换器（替换 Phase 2 的 auto-select 行为） | `frontend/src/pages/Dashboard/DashboardPage.tsx`, `frontend/src/components/Analytics/` | 先写 test：切换后数据刷新 |
| 5 | Segment 选择写入 `currentViewMode` 并持久化（localStorage） | `frontend/src/stores/dataScopeStore.ts` | 先写 test：切换后持久化，刷新后恢复 |
| 6 | 默认激活主要角色侧（Q2 决策） | `frontend/src/stores/dataScopeStore.ts` | 先写 test：主绑定判定逻辑 |
| 7 | 导出功能按当前 view_mode 过滤 | `frontend/src/services/analyticsService.ts`, `frontend/src/components/Analytics/AnalyticsDashboard.tsx` | 先写 test：导出数据与当前口径一致 |

### 8.3 SSOT 更新

| # | 任务 |
|---|------|
| 8 | REQ-ANA-001 整体 → DONE（ANA-001.a + ANA-001.b Phase 1 + ANA-001.c Phase 4 全部收口） |

### 验收标准

- 单绑定用户：大屏无 Segment 切换器，直接展示对应口径
- 双绑定用户：大屏顶部中间 `[产权方口径 | 运营方口径]` Segment 切换器
- 切换口径后所有图表/指标/导出数据同步刷新
- 默认激活主要角色侧

### 边界情况

- 用户在切换口径的瞬间数据正在加载 → 取消上一次请求
- 双绑定用户的"主要角色"判定：**固定优先级 owner > manager**（与 Phase 2 auto-fallback 一致），Segment 默认选中 owner 侧
- admin 用户不展示 Segment（全量数据，不分口径）

### 建议测试用例

1. 单绑定用户 → Segment 不渲染
2. 双绑定用户 → Segment 渲染两个选项
3. 点击切换 → API 携带 `?view_mode=` 重新请求
4. admin → 无 Segment，全量数据
5. 导出 → 仅当前口径数据
6. 切换 → 持久化 → 刷新后恢复选择

---

## 9. Phase 5：ABAC 激活与安全加固

**目标**：在**现有 `DataPolicyService` / policy package 体系上**激活 ABAC 数据策略，修复已知安全 bug。

**决策依据**：Q4（ABAC MVP 必须），Q3（Deny-Overrides/SoD vNext）

> **v2 修订说明**：原方案计划新建 `init_abac_data.py` 直接灌表，但仓库已有完整的策略包管理面（`DataPolicyService` + `data_policies.py` API + `DataPolicyManagementPage.tsx` UI + `backfill_role_policies.py` 回填脚本）。应复用现有体系，**保持单一真相入口**，避免离线 seed 与线上 UI/API 两套来源互相覆盖。
>
> **v3 修订说明**：`DataPolicyService` 只负责绑定，不负责创建模板策略记录。任务 1 拆为 1a（seed migration 入库模板）+ 1b（backfill 绑定角色）两步。

### 9.1 ABAC 激活（复用现有体系）

| # | 任务 | 文件/模块 | TDD |
|---|------|-----------|-----|
| 1a | **确保 7 个模板策略已入库**：通过 Alembic seed migration 或扩展 `init_rbac_data.py` 将 7 个 `abac_policies` 模板记录写入数据库（`DataPolicyService` 本身不创建策略，只做绑定） | `backend/alembic/versions/` 或 `backend/scripts/setup/init_rbac_data.py` | 先写 test：seed 后 `abac_policies` 有 7 行模板记录 |
| 1b | **重写 `backfill_role_policies.py` 为显式角色→策略白名单映射**：不再依赖旧角色名关键词启发式，明确 6 个新角色分别绑定哪个策略包 | `backend/src/scripts/migration/party_migration/backfill_role_policies.py` | 先写 test：`perm_admin` → `no_data_access`，`ops_admin` ≠ `platform_admin` |
| 1c | **通过 `backfill_role_policies.py` 绑定角色-策略**：在显式映射冻结后，6 角色 × N 策略 → `abac_role_policies` 表 | `backend/src/scripts/migration/party_migration/backfill_role_policies.py` | 先写 test：绑定行数正确 |
| 2 | 确认 `data_policies.py` API 和 `DataPolicyManagementPage.tsx` UI 可在激活后正常管理策略 | 现有代码 | 手动验证 + 回归测试 |

**单一真相入口规则**：策略**模板记录**通过 seed migration 入库；策略**配置与绑定**统一通过 `DataPolicyService` → `data_policies.py` API 管理。不新建独立 seed 脚本直接操作 `abac_role_policies` 表。回填脚本 `backfill_role_policies.py` 仅用于初始化和迁移场景。

### 9.2 安全 Bug 修复

| # | 任务 | 文件/模块 | TDD |
|---|------|-----------|-----|
| 3 | 修复 ABAC deny 被 `authenticated_default` 覆盖 | `backend/src/services/authz/service.py` | 先写 test：ABAC deny → 最终结果为 deny |
| 4 | 授权缓存键纳入 party bindings | `backend/src/services/authz/cache.py` | 先写 test：不同绑定用户缓存不命中 |
| 5 | ABAC 激活日志模式（首周仅记录不拦截，降低风险） | `backend/src/services/authz/service.py` | 先写 test：日志模式下 deny 被记录但返回 allow |

### 9.3 REQ-AUTH-003 正式化

**发现**：§12.3 验收场景 P6 引用了 `REQ-AUTH-003`（ABAC 策略优先级排序），但该 REQ 从未被正式定义。

| # | 任务 |
|---|------|
| 6 | 在 `docs/requirements-specification.md` 正式定义 REQ-AUTH-003（ABAC 数据策略引擎） |
| 7 | 补充验收条件和代码证据 |

### 验收标准

- `abac_policies` 表有 7 条策略模板记录（通过 seed migration 入库，非 `DataPolicyService` 创建）
- `abac_role_policies` 表有完整的角色-策略绑定（通过显式角色→策略映射后的 `backfill_role_policies.py` 创建）
- 策略可通过 `data_policies.py` API / `DataPolicyManagementPage.tsx` UI 查看和管理
- ABAC deny 不再被 `authenticated_default` 覆盖
- 缓存键包含 party binding 信息
- 日志模式可通过配置开关启用

### 边界情况

- ABAC 激活后现有用户权限不应突然变化（日志模式过渡）
- `system_admin` 绕过 ABAC（全量访问）
- 策略条件中引用的 party_id 不存在 → 安全降级为 deny
- 并发请求时缓存一致性
- 策略包 UI 修改与 seed 初始化的先后顺序

### 建议测试用例

1. ABAC deny + authenticated_default → 最终 deny
2. 不同 party binding 的用户 → 缓存隔离
3. 日志模式 → deny 被记录但不拦截
4. 模板策略 seed migration / Alembic 重复运行 → 幂等（不重复创建模板记录）
5. `backfill_role_policies.py` 对 6 新角色的显式映射正确
6. system_admin → ABAC bypass
7. 无 party binding 的用户 → deny（除 system_admin/perm_admin）
8. 通过 API 修改策略后缓存正确失效

---

## 10. Phase 6：系统管理域多角色契约迁移

**目标**：将 REQ-SYS-001/002/003 从"单角色契约"迁移到"多角色契约"，对齐新的 6 角色体系。

> **v2 修订说明**：原方案将系统管理页面描述为"骨架待补 CRUD"。实际上用户管理（含表格/表单）、字典管理（748 行）等已是完整实现，但契约仍按单 `role_id` 工作（如 `UserManagement/index.tsx:161-172` 编辑表单、`UserTable.tsx:73-89` 列表展示、`systemService.ts:9-27` create payload）。真正的改造面是"多角色契约迁移"而非"补 CRUD"。工时上调至 5-7 天。

### 10.1 Step A：后端用户-角色契约迁移

| # | 任务 | 文件/模块 | TDD |
|---|------|-----------|-----|
| 1 | 用户创建/更新接口从 `role_id: str` 改为 `role_ids: list[str]` | `backend/src/api/v1/auth/auth_modules/users.py` | 先写 test：多角色分配、撤销 |
| 2 | 用户响应模型新增 `roles: list[RoleInfo]`（`role_name` 作为 **Phase 6 过渡字段**，仅用于同 Phase 内前端渐进迁移，**Phase 7 强制移除**，不进入长期契约） | `backend/src/schemas/` | 先写 test：响应包含多角色 |
| 3 | 角色管理接口对齐 6 角色 | `backend/src/api/v1/auth/roles.py` | 先写 test |
| 4 | 授权入口改造（Phase 3 `require_admin` 审计后续）：系统管理接口仅允许 `perm_admin` + `system_admin` | 全部 auth API | 先写 test：executive → 403 |

### 10.2 Step B：前端类型与表单模型迁移

| # | 任务 | 文件/模块 | TDD |
|---|------|-----------|-----|
| 5 | `systemService.ts` create/update payload 从 `role_id` 改为 `role_ids[]` | `frontend/src/services/systemService.ts` | 先写 test |
| 6 | 用户类型定义统一使用 `roles[]` / `role_ids[]`，废弃 `role_id` / `role_name` 单值 | `frontend/src/types/` | 先写 test |

### 10.3 Step C：页面对齐与权限边界修正

| # | 任务 | 文件/模块 | TDD |
|---|------|-----------|-----|
| 7 | 用户管理页面：编辑表单从单选角色改为多选 | `frontend/src/pages/System/UserManagement/index.tsx` | 先写 test：多角色选择 |
| 8 | 用户管理页面：列表从单 `role_name` 列改为多角色 Tag 展示 | `frontend/src/pages/System/UserManagement/components/UserTable.tsx` | 先写 test：多角色标签渲染 |
| 9 | 角色管理页面对齐 6 角色 | `frontend/src/pages/System/RoleManagementPage.tsx` | 先写 test |
| 10 | 组织管理完善：CRUD + UserPartyBinding 维护 | `backend/src/api/v1/auth/organization.py` + `frontend/src/pages/System/OrganizationPage.tsx` | 先写 test |
| 11 | 字典管理完善：字典分类 + 字典项 CRUD | `backend/src/api/v1/system/dictionaries.py` + `frontend/src/pages/System/DictionaryPage.tsx` | 先写 test |

### 验收标准

- 用户可创建/编辑/禁用/分配**多个**角色
- 仅 perm_admin 和 system_admin 可访问系统管理
- 列表展示多角色 Tag
- 表单支持多角色选择
- 组织树形结构展示正确，可绑定/解绑用户
- 字典分类和字典项 CRUD 完整

### 边界情况

- 禁用用户后该用户的活跃 session 应被清除
- 删除角色时已绑定用户的权限降级处理
- 组织树深度限制（建议 ≤5 层）
- 字典项被业务数据引用时不可删除
- 旧单 `role_id` 数据的迁移处理

### 建议测试用例

1. perm_admin 创建用户并分配 [executive, reviewer] 两个角色 → 成功
2. executive 请求用户管理 → 403
3. system_admin 分配角色 → 成功
4. 禁用用户 → 无法登录
5. 删除被引用的字典项 → 拦截
6. 列表展示多角色 Tag 正确
7. 编辑表单加载已有多角色 → 正确回显

---

## 11. Phase 7：死代码清理与验收闭环

**目标**：清理遗留代码，34 个验收场景全覆盖。

### 11.1 死代码清理

| # | 任务 | 文件/模块 |
|---|------|-----------|
| 1 | 删除未使用的 auth checker 类 / 遗留 `permissions.py` helper（如 Phase 3 评估后确认退场） | `backend/src/security/` 全量扫描 |
| 1a | **移除 Phase 6 过渡字段 `role_name`**：从用户响应 schema 中删除 `role_name` 单值字段，前端全部切换到 `roles[]` | `backend/src/schemas/` + `frontend/src/types/` + 全部引用 |
| 2 | 清理前端已废弃的 perspective 相关类型定义 | `frontend/src/types/` |
| 3 | 清理已合并到 `analytics` 的 `statistics` 资源残留 | `backend/scripts/setup/init_rbac_data.py` |

### 11.2 验收闭环

| # | 任务 |
|---|------|
| 4 | 逐条验证 §12 中 34 个验收场景，记录结果 |
| 5 | 修复验收中发现的 gap |
| 6 | 更新需求追踪矩阵（§11），全部 REQ → DONE |
| 7 | 前端 capabilities 统一 + 路由级权限守卫 |

### 11.3 文档收尾

| # | 任务 |
|---|------|
| 8 | 本方案移入 `docs/archive/backend-plans/` |
| 9 | 被吸收的 3 个方案移入 `docs/archive/backend-plans/` |
| 10 | `docs/plans/README.md` 更新 |
| 11 | `CHANGELOG.md` 最终更新 |

---

## 12. 里程碑排期

```
M2（~2026-05-10）
├── Phase 1：🚧 需求收口（3 天）
│   ├── REQ-AST-003 前端 + 审批联动
│   ├── REQ-RNT-002 前端收口
│   └── REQ-ANA-001.b 指标补充
└── Phase 2：术语收口 + view_mode 最小承接（2.5 天）
    ├── X-Perspective 一次性切除（无兼容层）
    ├── view_mode query param 上线
    └── currentViewMode auto-select（双绑定兜底）

M3（2026-05-11 ~ 2026-06-07）
├── Phase 3：RBAC 角色重定义（4-5 天）
│   ├── 7→6 角色一次性迁移
│   ├── resource_type 全量盘点→冻结→seed 覆盖
│   ├── 授权三层入口统一
│   └── action 命名统一 + analytics/statistics 合并
├── Phase 4：分析引擎增强（2-3 天）
│   ├── 大屏 ViewMode Segment 切换器（替换 Phase 2 auto-select）
│   └── 按口径隔离展示
└── Phase 5：ABAC 激活（2-3 天）
        ├── Alembic seed migration 确保模板策略入库
        ├── backfill_role_policies 显式映射改造
        ├── backfill_role_policies 绑定角色
        ├── 安全 bug 修复
        └── 日志模式过渡

M4（2026-06-08 ~ 2026-06-30）
├── Phase 6：系统管理域多角色迁移（5-7 天）
│   ├── Step A：后端契约 role_id → role_ids
│   ├── Step B：前端类型/表单迁移
│   └── Step C：页面对齐 + 组织/字典完善
└── Phase 7：清理与验收（2-3 天）
    ├── 死代码清理
    ├── 34 验收场景全覆盖
    └── 文档收尾
```

---

## 13. 异常项与技术债

本次审计发现的异常项，需在对应 Phase 中解决：

| # | 异常 | 严重性 | 解决 Phase |
|---|------|--------|------------|
| A1 | REQ-AUTH-003 幽灵引用：§12.3 P6 引用但未定义 | P0 | Phase 5（正式化） |
| A2 | analytics/statistics 命名冲突（授权 bug） | P0 | Phase 3 |
| A3 | action 命名不一致：主干 `require_authz` 用 `read/update/delete`，遗留 `permissions.py` 用 `view/edit/delete` | P1 | Phase 3（遗留层清退或对齐主干） |
| A4 | ABAC deny 被 authenticated_default 覆盖 | P0 | Phase 5 |
| A5 | 授权缓存键不含 party bindings | P1 | Phase 5 |
| A6 | X-Perspective header 仍在发送 | P1 | Phase 2（一次性切除） |
| A7 | ViewMode Segment 切换器不存在 | P2 | Phase 4（Phase 2 先做 auto-fallback） |
| A8 | 7 个 ABAC 数据策略模板未入库 | P0 | Phase 5（通过 seed migration / Alembic 入库） |
| A9 | CRUD 层 party filtering 未全量审计 | P1 | Phase 3 |
| A10 | 授权入口三层并存（`require_admin`/`require_authz`/`permissions.py`），perm_admin 无法统一生效 | P1 | Phase 3（三层统一） |
| A11 | seed 权限资源仅 14 个，代码中 ~50 个 `resource_type` | P1 | Phase 3（全量盘点后冻结） |
| A12 | 系统管理页面按单 `role_id` 契约实现，需迁移为多角色 | P2 | Phase 6 |

---

## 14. 风险与缓释

> **工程原则**：项目处于 0→1 阶段，不做长期兼容保留，充分暴露问题（`AGENTS.md`）。所有迁移采用一次性切换 + 明确回滚方案。

| 风险 | 影响 | 概率 | 缓释措施 |
|------|------|------|----------|
| RBAC 角色迁移导致用户权限中断 | 高 | 中 | Alembic 迁移脚本先在 staging 验证；一次性切换，不设兼容期；迁移前备份数据库，失败可回滚 |
| ABAC 激活后误拦截合法请求 | 高 | 中 | 日志模式过渡（首周记录不拦截），确认无误后配置开关切换为强制模式 |
| X-Perspective 一次性废弃导致前端异常 | 低 | 低 | 0→1 项目无已部署旧客户端；前后端同版本发布，一次性切换 |
| Phase 3 工时超出预估（resource_type 盘点+三层授权统一） | 中 | 中 | Phase 3 和 5 可并行部分任务；资源盘点可脚本化加速 |
| Phase 6 多角色迁移面大于预期 | 中 | 中 | 拆为 3 个 Step（后端契约/前端类型/页面对齐），逐步验收 |

---

## 15. 验收场景对齐矩阵

§12 共 34 个验收场景，与 Phase 的对齐关系：

### §12.1 资产域（P1-P5）

| 场景 | 描述 | Phase |
|------|------|-------|
| P1 | 创建资产并提交审核 | Phase 1 (AST-003) |
| P2 | 审核通过后资产生效 | Phase 1 (AST-003) |
| P3 | 反审核已审核资产 | Phase 1 (AST-003) |
| P4 | 审核中资产不可编辑/删除 | Phase 1 (AST-003) |
| P5 | 资产详情展示租赁汇总 | 已完成 (AST-004) |

### §12.2 合同域（P6-P15）

| 场景 | 描述 | Phase |
|------|------|-------|
| P6 | 创建合同组（承租模式） | Phase 1 (RNT-002) |
| P7 | 创建合同组（代理模式） | Phase 1 (RNT-002) |
| P8 | 模式互斥校验 | Phase 1 (RNT-002) |
| P9 | 一资产一合同组约束 | Phase 1 (RNT-002) |
| P10 | 台账自动生成 | 已完成 (RNT-006) |
| P11 | 台账逾期检测 | 已完成 (RNT-006) |
| P12 | 合同审核流 | 已完成 (RNT-004/005) |
| P13 | 续签合同 | 已完成 (RNT-003) |
| P14 | 服务费台账同步 | 已完成 (RNT-006) |
| P15 | 导出台账 Excel | 已完成 (ANA-001.a) |

### §12.3 权限域（P16-P22）

| 场景 | 描述 | Phase |
|------|------|-------|
| P16 | system_admin 全量访问 | Phase 3 |
| P17 | perm_admin 零业务数据 | Phase 3 + Phase 6 |
| P18 | executive 受绑定约束 | Phase 3 + Phase 5 |
| P19 | viewer 只读 | Phase 3 |
| P20 | reviewer 审批操作 | Phase 3 |
| P21 | ABAC 数据策略生效 | Phase 5 |
| P22 | ~~REQ-AUTH-003~~ ABAC 策略优先级 | Phase 5 (REQ-AUTH-003 正式化) |

### §12.4 分析域（P23-P27）

| 场景 | 描述 | Phase |
|------|------|-------|
| P23 | 综合分析数据正确 | 已完成 (ANA-001.a) |
| P24 | 当期实收指标 | Phase 1 (ANA-001.b) |
| P25 | 租金收缴率指标 | Phase 1 (ANA-001.b) |
| P26 | 大屏口径切换 | Phase 4 (ANA-001.c) |
| P27 | 导出按口径过滤 | Phase 4 (ANA-001.c) |

### §12.5 搜索域（P28-P30）

| 场景 | 描述 | Phase |
|------|------|-------|
| P28 | 全局聚合搜索 | 已完成 (SCH-001) |
| P29 | 按对象分组搜索 | 已完成 (SCH-002) |
| P30 | 搜索权限过滤 | 已完成 (SCH-003) |

### §12.6 系统管理域（P31-P34）

| 场景 | 描述 | Phase |
|------|------|-------|
| P31 | 用户 CRUD（多角色） | Phase 6 |
| P32 | 角色分配（多角色） | Phase 6 |
| P33 | 组织架构管理 | Phase 6 |
| P34 | 数据字典管理 | Phase 6 |

### 覆盖统计

| 状态 | 数量 | 占比 |
|------|------|------|
| 已完成 | 12 | 35% |
| Phase 1 覆盖 | 8 | 24% |
| Phase 2 覆盖 | 0 | 0%（基础设施，无直接验收场景） |
| Phase 3 覆盖 | 5 | 15% |
| Phase 4 覆盖 | 2 | 6% |
| Phase 5 覆盖 | 3 | 9% |
| Phase 6 覆盖 | 4 | 12% |
| **合计** | **34** | **100%** |
