# 视角机制（View Perspective）技术审计报告

**审计日期**：2026-03-17
**状态**：🔄 待修复
**关联需求**：REQ-AUTH-002

---

## 1. 机制概述

系统实现了全栈多主体数据隔离的视角机制，用户可在其绑定的不同主体（Party）之间切换视角（产权方 / 运营方），所有数据查询按当前视角自动过滤。

### 端到端数据流

```
用户选择视角 (GlobalViewSwitcher)
  → localStorage 持久化 (viewSelectionStorage)
  → API 拦截器注入 HTTP 头 (X-View-Perspective + X-View-Party-Id)
  → 后端 view_scope.py 校验头信息合法性
  → party_scope.py 解析用户绑定关系 → PartyFilter
  → QueryBuilder 将 PartyFilter 转为 SQL WHERE 子句
  → 数据库只返回当前视角范围内的数据
```

### 涉及的核心文件

| 层级 | 文件 | 职责 |
|------|------|------|
| ORM 模型 | `backend/src/models/user_party_binding.py` | 用户-主体绑定持久化 |
| 数据过滤 | `backend/src/crud/query_builder.py` | PartyFilter → SQL WHERE |
| 视角校验 | `backend/src/services/view_scope.py` | 校验 HTTP 头、构建 narrowed PartyFilter |
| 范围解析 | `backend/src/services/party_scope.py` | 用户 ID → PartyFilter（绑定解析核心） |
| ABAC 上下文 | `backend/src/services/authz/context_builder.py` | 构建 SubjectContext（含主体 ID 列表） |
| 授权中间件 | `backend/src/middleware/auth_authz.py` | ABAC 检查 + 过期视角检测 |
| 资源作用域 | `backend/src/middleware/auth_scope_loaders.py` | 加载资源的主体归属信息 |
| 能力 API | `backend/src/api/v1/auth/auth_modules/authentication.py` | `/me/capabilities` 端点 |
| 前端类型 | `frontend/src/types/capability.ts` | Perspective、CapabilityDataScope 类型 |
| 前端持久化 | `frontend/src/utils/viewSelectionStorage.ts` | localStorage 读写 |
| 前端状态 | `frontend/src/contexts/ViewContext.tsx` | 视角状态机、可用视角推导 |
| API 注入 | `frontend/src/api/interceptors.ts` | 请求拦截器注入视角头 |
| 过期检测 | `frontend/src/api/clientHelpers.ts` | 响应拦截器检测 X-Authz-Stale |
| 视角选择器 | `frontend/src/components/System/GlobalViewSwitcher.tsx` | 视角切换 UI |
| 视角横幅 | `frontend/src/components/System/CurrentViewBanner.tsx` | 当前视角提示条 |
| 能力评估 | `frontend/src/utils/authz/capabilityEvaluator.ts` | 权限判断 + 视角覆盖 |

---

## 2. 安全设计评价（正面）

视角机制的安全基座设计扎实：

| 安全属性 | 实现方式 | 位置 |
|---------|---------|------|
| 非法头信息 → 零行返回（fail-closed） | perspective 无效或 party_id 缺失时返回空 PartyFilter | `view_scope.py:66-73` |
| 空 party_ids → 零行返回 | `query.where(false())` | `query_builder.py:224-229` |
| 绑定解析异常 → fail-closed | 异常捕获后返回空 PartyFilter | `party_scope.py:243-248` |
| 视角选择必须在用户授权范围内 | 校验请求的 party_id 属于用户的 owner/manager 集合 | `view_scope.py:91-116` |
| 管理员跳过隔离（显式） | 特权用户返回 None 跳过 party_scope | `party_scope.py:250-259` |
| 权限变更后过期视角检测 | 403 时检测 X-Authz-Stale 头 + 前端 CustomEvent 总线 | `auth_authz.py:263-295` |

---

## 3. 发现的问题

### 3.1 前端 Bug

#### BUG-VIEW-001：CurrentViewBanner Ant Design API 误用

- **文件**：`frontend/src/components/System/CurrentViewBanner.tsx:15`
- **问题**：使用 `title="当前视角"` 作为 Alert 组件的 prop，但 Ant Design Alert 的主文本 prop 是 `message`，`title` 会被当作 HTML 属性忽略
- **影响**：横幅无主标题文本，只显示 description 行
- **修复**：将 `title` 改为 `message`

#### BUG-VIEW-002：GlobalViewSwitcher Space 组件 prop 错误

- **文件**：`frontend/src/components/System/GlobalViewSwitcher.tsx:68`
- **问题**：使用 `<Space orientation="vertical">`，Ant Design Space 的垂直布局 prop 是 `direction="vertical"`
- **影响**：选项可能水平排列而非预期的垂直排列
- **修复**：将 `orientation` 改为 `direction`

### 3.2 覆盖面不足

#### ISSUE-VIEW-003：前端视角提示覆盖不全

- **现状**：`CurrentViewBanner` 只展示在 3 个页面
  - `pages/Assets/AssetListPage.tsx:330`
  - `components/Project/ProjectList.tsx:275`
  - `pages/Project/ProjectDetailPage.tsx:321`
- **缺失**：合同组列表/详情、台账列表、收款记录、产权证列表/详情、主体列表等页面无视角提示
- **影响**：用户在这些页面不知道当前数据范围受哪个视角过滤

#### ISSUE-VIEW-004：写入路径无视角范围校验

- **现状**：视角过滤只作用于读取路径（列表/详情查询）
- **缺失**：创建和更新操作未校验目标资源是否在当前视角范围内
- **影响**：理论上用户可通过写入操作影响非当前视角范围的数据

#### ISSUE-VIEW-005：无视角级路由守卫

- **现状**：`currentView` 为 null 时页面仍会渲染并发起 API 调用
- **机制**：`selectionRequired` 打开模态框，但底层页面已挂载并触发数据请求
- **影响**：无视角选择时的请求无 header，可能返回无范围数据或 403

### 3.3 后端架构问题

#### ISSUE-VIEW-006：绑定解析逻辑重复

- **文件对比**：
  - `backend/src/services/party_scope.py:199-248`（resolve_user_party_filter）
  - `backend/src/services/authz/context_builder.py:51-79`（build_subject_context）
- **问题**：两处独立实现了相同逻辑：获取绑定 → 按 relation_type 分类 → 总部展开 → 默认组织回退
- **风险**：当前一致，但后续修改其中一处忘记同步另一处，可能导致 ABAC 授权通过但数据过滤不到（或反之）
- **建议**：抽取共享的绑定分类函数

#### ISSUE-VIEW-007：HTTP 头常量重复定义

- **位置**：
  - `backend/src/services/view_scope.py:20-21`：`_VIEW_PERSPECTIVE_HEADER`、`_VIEW_PARTY_ID_HEADER`
  - `backend/src/middleware/auth_authz.py:23-24`：`VIEW_PERSPECTIVE_HEADER_NAME`、`VIEW_PARTY_ID_HEADER_NAME`
- **问题**：同一字符串在两个文件中各定义一次
- **建议**：统一到 `constants/` 或 `core/` 下的单一定义

#### ISSUE-VIEW-008：成功视角切换无审计日志

- **现状**：`view_scope.py` 只在校验失败时记录 warning 日志（:67-73, :103-108, :110-116）
- **缺失**：成功构建 narrowed PartyFilter 时无 info 级日志
- **影响**：无法从日志中追溯用户的视角切换行为

### 3.4 前端设计问题

#### ISSUE-VIEW-009：localStorage 无 schema 校验

- **文件**：`frontend/src/utils/viewSelectionStorage.ts:18`
- **问题**：`JSON.parse(raw) as StoredViewSelection` 无运行时校验，损坏数据会导致 undefined 泄入 API 头
- **建议**：添加字段存在性校验，不合格时返回 null 并清除

#### ISSUE-VIEW-010：API 拦截器与 React 状态的双数据路径

- **文件**：`frontend/src/api/interceptors.ts:83-92`
- **问题**：拦截器直接读 localStorage，UI 读 React state（ViewContext），`selectView()` 先写 localStorage 后通过 `startTransition` 更新 React state，存在短暂不一致窗口
- **实际风险**：低（localStorage 先更新，拦截器总能拿到最新值），但架构上不够纯粹

#### ISSUE-VIEW-011：evaluateCapability 重复 merge

- **文件**：
  - `frontend/src/hooks/useCapabilities.ts:20-22`（useMemo merge）
  - `frontend/src/utils/authz/capabilityEvaluator.ts:131`（内部再 merge）
- **问题**：capabilities 被 merge 两次，后一次是冗余的 O(n) 操作
- **影响**：每次权限判断都有不必要的开销

#### ISSUE-VIEW-012：Party 名称解析失败静默吞没

- **文件**：`frontend/src/contexts/ViewContext.tsx:89-96`
- **问题**：`resolvePartyName()` catch 所有异常，回退到截断 ID 显示，无错误提示
- **影响**：Party 服务不可用时用户只看到 `主体 abcdef12`，不知道是故障

### 3.5 业务逻辑硬编码

#### ISSUE-VIEW-013：项目视角硬编码为仅 manager

- **文件**：`frontend/src/utils/authz/capabilityEvaluator.ts:30-32`
- **内容**：`PERSPECTIVE_OVERRIDES` 将 `project` 资源固定为 `['manager']` 视角
- **问题**：如未来项目需要产权方视角，需修改硬编码

---

## 4. 已接入视角过滤的后端 API 模块

| 模块 | 文件 | 是否使用 resolve_selected_view_party_filter |
|------|------|:---:|
| 资产列表/详情 | `api/v1/assets/assets.py` | ✅ |
| 项目 | `api/v1/assets/project.py` | ✅ |
| 产权证 | `api/v1/assets/property_certificate.py` | ✅ |
| 合同组 | `api/v1/contracts/contract_groups.py` | ✅ |
| 台账 | `api/v1/contracts/ledger.py` | ✅ |
| 收款 | `api/v1/system/collection.py` | ✅ |
| 历史记录 | `api/v1/system/history.py` | ✅ |
| 主体 | `api/v1/party.py` | ✅ |
| 分析/报表 | `api/v1/analytics/` | ❓ 待确认 |
| 文档/合同PDF | `api/v1/documents/` | ❌ 未接入 |

---

## 5. 优先级建议

| 优先级 | 编号 | 类型 | 说明 |
|--------|------|------|------|
| P0 | BUG-VIEW-001 | Bug | CurrentViewBanner 无主标题 |
| P0 | BUG-VIEW-002 | Bug | GlobalViewSwitcher 布局方向错误 |
| P1 | ISSUE-VIEW-005 | 设计缺陷 | 无视角时页面仍发起无范围 API 请求 |
| P1 | ISSUE-VIEW-003 | 覆盖不全 | 多数页面无视角提示 |
| P1 | ISSUE-VIEW-006 | 架构 | 绑定解析逻辑重复 |
| P2 | ISSUE-VIEW-004 | 覆盖不全 | 写入路径无视角校验 |
| P2 | ISSUE-VIEW-009 | 健壮性 | localStorage 无 schema 校验 |
| P2 | ISSUE-VIEW-007 | 代码规范 | 常量重复定义 |
| P2 | ISSUE-VIEW-008 | 可观测性 | 成功切换无审计日志 |
| P3 | ISSUE-VIEW-010 | 架构 | 双数据路径不一致窗口 |
| P3 | ISSUE-VIEW-011 | 性能 | evaluateCapability 重复 merge |
| P3 | ISSUE-VIEW-012 | 体验 | Party 名称解析失败无提示 |
| P3 | ISSUE-VIEW-013 | 灵活性 | 项目视角硬编码 |
