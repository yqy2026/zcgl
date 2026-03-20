# 视角机制简化方案：从全局切换器到菜单入口路由

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**文档类型**: 实施方案
**创建日期**: 2026-03-17
**状态**: 🔄 评审修订中
**需求编号**: REQ-AUTH-002
**里程碑**: M2

---

## 1. 背景与动机

### 1.1 现状

系统当前实现了一套全栈的"全局视角切换器"机制（REQ-AUTH-002），用户通过页面顶部 Header 中的模态选择器选定视角（产权方/运营方 + 具体主体），之后所有页面自动按该视角过滤数据。

该机制涉及约 **1500-2000 行专用代码**，涵盖：

| 组件 | 文件 | 行数 | 作用 |
|------|------|------|------|
| ViewContext | `frontend/src/contexts/ViewContext.tsx` | 308 | 视角状态机 |
| GlobalViewSwitcher | `frontend/src/components/System/GlobalViewSwitcher.tsx` | 91 | 选择器 UI |
| CurrentViewBanner | `frontend/src/components/System/CurrentViewBanner.tsx` | 24 | 当前视角提示 |
| viewSelectionStorage | `frontend/src/utils/viewSelectionStorage.ts` | 37 | localStorage 持久化 |
| viewSelection 类型 | `frontend/src/types/viewSelection.ts` | 15 | TypeScript 类型 |
| API 拦截器头注入 | `frontend/src/api/interceptors.ts:83-92` | ~10 | 自动注入 HTTP 头 |
| authz-stale 检测 | `frontend/src/api/clientHelpers.ts:141-179` | ~40 | 过期视角检测 |
| view_scope.py | `backend/src/services/view_scope.py` | 142 | 后端头校验 |
| auth_authz stale 检测 | `backend/src/middleware/auth_authz.py:263-295` | ~30 | 过期视角信号 |

### 1.2 问题

1. **认知负担高**："视角"是一个抽象概念，用户需要先理解它，再通过模态框选择后才能操作。不如直接点击菜单入口直觉。
2. **全局状态代价大**：localStorage / React state / HTTP header 三者同步复杂，引入过期检测、双数据路径、页面渲染时序等问题。
3. **抑制页面差异化**：不同视角下关注的字段、操作、布局往往不同，全局视角下只能用条件渲染，容易变成 prop 地狱。
4. **存在已知 Bug**：CurrentViewBanner 的 Ant Design API 误用、GlobalViewSwitcher Space 布局 prop 错误（详见 `docs/issues/2026-03-17-view-perspective-mechanism-audit.md`）。
5. **覆盖不完整**：仅 3 个页面展示了 CurrentViewBanner，写入路径未受视角约束。

### 1.3 核心判断

**"视角"不应该是全局状态，而应该内联到页面路由中。** 用户点击不同菜单入口进入不同视角的页面，每个页面自己知道自己的数据范围，无需全局切换器。

---

## 2. 目标

1. **移除全局视角切换器**，用菜单入口路由替代。
2. **简化前端**：删除 ViewContext、GlobalViewSwitcher、CurrentViewBanner、viewSelectionStorage、API 拦截器头注入、authz-stale 事件总线。
3. **简化后端**：移除 `view_scope.py` 的 HTTP 头校验逻辑，改为接收显式 API 查询参数。
4. **保留数据隔离安全底线**：`PartyFilter`、`QueryBuilder`、`user_party_bindings`、RBAC/ABAC 全部保留，只改数据传入方式。
5. **菜单增加权限感知**：当前菜单对所有用户展示所有项，需改为按用户绑定/权限动态显示。

---

## 3. 设计

### 3.1 菜单结构重组

**当前菜单（视角无关）：**

```
数据看板
资产管理
  ├── 资产列表
  ├── 数据分析
  └── 产权证管理
合同组管理
权属方管理
项目管理
系统管理 (admin)
```

**目标菜单（视角内联到菜单分组）：**

```
数据看板
自有资产                        ← 产权方视角入口（owner perspective）
  ├── 资产总览                  ← /owner/assets
  ├── 产权证管理                ← /owner/property-certificates
  └── 自有合同                  ← /owner/contract-groups
代管业务                        ← 运营方视角入口（manager perspective）
  ├── 代管资产                  ← /manager/assets
  ├── 代管合同                  ← /manager/contract-groups
  ├── 台账管理                  ← /manager/ledger
  └── 项目管理                  ← /manager/projects
数据分析                        ← 跨视角（两次 API 各取所需）
权属方管理                      ← 视角无关
系统管理 (admin)
```

**设计要点：**

- 顶级菜单分组即代表视角语义，用户不需要理解"视角"这个词。
- 同一个业务模块（如资产列表）可以出现在多个分组中，通过不同路由前缀区分。
- 菜单项按用户的 `user_party_bindings` 动态显示/隐藏：
  - 用户无 owner 绑定 → "自有资产" 整个分组不显示
  - 用户无 manager 绑定 → "代管业务" 整个分组不显示
- 仪表盘和数据分析等跨视角页面不属于任何分组，独立展示。

### 3.2 路由设计

引入路由前缀 `/owner/` 和 `/manager/` 承载视角语义：

```typescript
// 路由定义（示意）
const routes = [
  // ── 产权方路由 ──
  { path: '/owner/assets',                page: AssetListPage,        perspective: 'owner' },
  { path: '/owner/assets/:id',            page: AssetDetailPage,      perspective: 'owner' },
  { path: '/owner/property-certificates', page: CertificateListPage,  perspective: 'owner' },
  { path: '/owner/contract-groups',       page: ContractGroupListPage,perspective: 'owner' },

  // ── 运营方路由 ──
  { path: '/manager/assets',              page: AssetListPage,        perspective: 'manager' },
  { path: '/manager/assets/:id',          page: AssetDetailPage,      perspective: 'manager' },
  { path: '/manager/contract-groups',     page: ContractGroupListPage,perspective: 'manager' },
  { path: '/manager/projects',            page: ProjectListPage,      perspective: 'manager' },
  { path: '/manager/ledger',              page: LedgerListPage,       perspective: 'manager' },

  // ── 视角无关路由 ──
  { path: '/dashboard',                   page: DashboardPage },
  { path: '/analytics',                   page: AnalyticsPage },
  { path: '/ownership',                   page: OwnershipPage },
  { path: '/system/*',                    page: SystemPages,          adminOnly: true },
];
```

**页面复用**：`AssetListPage`、`ContractGroupListPage` 等组件同时服务两个视角路由。通过 `usePerspective()` hook 获得当前视角，而非全局状态。

**页面复用策略**：当前阶段两个视角下的页面字段差异较小（主要是筛选条件和部分列的显隐），采用同一页面组件 + 少量条件渲染的方式。具体规则：

- **条件渲染适用场景**：仅列显隐、筛选项差异、操作按钮差异（如 owner 视角下无"项目管理"入口）。这些差异通过 `perspective` 判断，控制在单个组件内 3-5 处条件分支以内。
- **拆分为独立页面的触发条件**：如果某个页面在两个视角下的布局结构、数据源、交互流程有本质不同（超过 30% 的模板代码不同），则应拆分为 `OwnerXxxPage` / `ManagerXxxPage`，共享底层 `XxxTable` / `XxxForm` 组件。
- **当前预判**：`AssetListPage`、`ContractGroupListPage` 适合复用；如果后续"代管资产"需要展示项目归属等 owner 视角不需要的整块区域，再拆分。

### 3.3 页面获取视角的方式

引入轻量 hook 替代 ViewContext：

```typescript
// usePerspective.ts — 从路由前缀推导视角，纯计算，无全局状态
function usePerspective(): { perspective: 'owner' | 'manager' | null } {
  const location = useLocation();
  if (location.pathname.startsWith('/owner/'))   return { perspective: 'owner' };
  if (location.pathname.startsWith('/manager/')) return { perspective: 'manager' };
  return { perspective: null };
}
```

对于多主体场景（用户是多个主体的产权方/运营方），在页面内用标准下拉筛选器选择具体主体：

> **数据源说明**：`useMyParties` 需要返回主体名称供下拉展示，但当前 capabilities API 只返回 `party_id` 不返回 `party_name`。有两种解决路径：
> 1. **推荐**：在 capabilities API 的 `data_scope` 中增加 `owner_parties: {id, name}[]` / `manager_parties: {id, name}[]` 字段（替代当前的纯 id 数组），一次请求拿到完整信息。
> 2. **备选**：`useMyParties` 内部额外调用 `/api/v1/parties?ids=...` 获取名称，但会多一次网络请求。
>
> 具体方案在 Batch F 实施时确定。

```typescript
// 页面内使用
function AssetListPage() {
  const { perspective } = usePerspective();
  const { partyOptions } = useMyParties(perspective); // 基于绑定获取可选主体
  const [selectedPartyId, setSelectedPartyId] = useState<string | null>(null);

  // API 调用时显式传参
  const { data } = useQuery(['assets', perspective, selectedPartyId], () =>
    assetApi.list({ perspective, party_id: selectedPartyId })
  );
  // ...
}
```

### 3.4 前端数据传递方式变更

**移除**：API 拦截器自动注入 `X-View-Perspective` / `X-View-Party-Id` 头。

**替代**：各页面在 API 调用时显式传递查询参数：

```typescript
// 当前方式（移除）
// interceptor 自动注入 header → 后端 view_scope.py 读取

// 新方式
assetApi.list({
  perspective: 'owner',        // 查询参数，可选
  party_id: 'party-abc-123',   // 查询参数，可选
  // ...其他业务筛选参数
});
```

后端 API 端点从查询参数接收，替代从 HTTP 头读取：

```python
# 当前方式（移除）
@router.get("/assets")
async def list_assets(
    selected_view: PartyFilter | None = Depends(resolve_selected_view_party_filter_dependency),
):
    ...

# 新方式
@router.get("/assets")
async def list_assets(
    perspective: Literal["owner", "manager"] | None = Query(None),
    party_id: str | None = Query(None),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    # 总是返回 PartyFilter，永不返回 None
    party_filter = await build_party_filter_from_params(
        db=db,
        perspective=perspective,
        party_id=party_id,
        current_user_id=str(current_user.id),
    )
    # 直接传给 service，service 层不再二次解析
    result = await asset_service.list_assets(party_filter=party_filter, ...)
    ...
```

### 3.5 后端变更

#### 保留

| 组件 | 文件 | 原因 |
|------|------|------|
| `PartyFilter` | `crud/query_builder.py:18-30` | 数据隔离核心数据结构 |
| `QueryBuilder._apply_party_filter()` | `crud/query_builder.py:172-298` | SQL WHERE 生成 |
| `user_party_bindings` 模型 | `models/user_party_binding.py` | 绑定持久化 |
| `resolve_user_party_filter()` | `services/party_scope.py:172-344` | 用户 → PartyFilter 解析 |
| RBAC / ABAC | `middleware/auth_authz.py` | 权限控制 |
| `capabilities` API | `api/v1/auth/.../authentication.py:553-568` | 前端菜单权限判断仍需要 |
| `CapabilityItem.perspectives` | `schemas/authz.py:40` | 菜单可见性判断依赖该字段（详见 3.9，需改为 resource-level） |

#### 移除

| 组件 | 文件 | 原因 |
|------|------|------|
| `resolve_selected_view_party_filter_dependency` | `services/view_scope.py:124-134` | HTTP 头校验不再需要 |
| `resolve_selected_view_party_filter` | `services/view_scope.py:53-121` | 同上 |
| `_build_narrowed_party_filter` | `services/view_scope.py:32-50` | 同上 |
| `coerce_selected_view_party_filter` | `services/view_scope.py:137-142` | 同上（详见下方 DI 边界说明） |
| `_should_mark_authz_stale` | `middleware/auth_authz.py:263-295` | 过期检测不再需要 |
| stale 头注入 | `core/exception_handler.py` | 同上 |
| `BaseBusinessError.authz_stale` 字段 | `core/exception_handler.py` | 错误模型中的 stale 标记不再需要 |
| `forbidden(authz_stale=)` / `not_found(authz_stale=)` | `core/exception_handler.py` | 工厂函数的 stale 参数不再需要 |
| `_should_set_authz_stale_header()` | `core/exception_handler.py` | stale 头生成辅助函数 |

#### 新增

`build_party_filter_from_params()` — 从查询参数构建 PartyFilter 的公共函数，替代 `view_scope.py` 的 HTTP 头解析逻辑。

**关键设计决策：该函数总是返回 `PartyFilter`，永远不返回 `None`。**

当前架构中存在一个隐式的"双重解析"模式：API 层的 `resolve_selected_view_party_filter_dependency` 在无 header 时返回 `None`，随后 service 层的 `_resolve_party_filter()` 又会内部调用 `resolve_user_party_filter()` 来填充。这意味着数据范围的最终确定被分散在 API 层和 service 层两个地方，增加了理解和维护成本。

新函数的行为：

| 输入 | 输出 |
|------|------|
| `perspective=None, party_id=None` | 调用 `resolve_user_party_filter()` 返回用户的**完整**数据范围（普通用户返回全绑定 PartyFilter，特权用户返回 `PartyFilter(party_ids=[], filter_mode="any", allow_null=True)` 即全量放行） |
| `perspective="owner", party_id=None` | 调用 `resolve_user_party_filter()` 获取完整范围，然后按 `filter_mode="owner"` 收窄 |
| `perspective="owner", party_id="xxx"` | 验证 `xxx` 在用户绑定范围内 → 成功则返回单 party 收窄的 PartyFilter；失败则 fail-closed `PartyFilter(party_ids=[])` |
| `party_id="xxx"` 但 `perspective=None` | 返回 400（perspective 和 party_id 必须同时指定或同时为空） |

**连带影响**：API 层总是拿到确定的 `PartyFilter` 传给 service，service 层 `_resolve_party_filter()` 中的 `if party_filter is not None: return party_filter` 短路生效，不再发生内部二次解析。10 个 service 文件（`asset_query_service`、`project/service`、`contract_group_service`、`pdf_import_service`、`rbac_service`、`history_service`、`collection/service`、`ledger_service_v2`、`property_certificate/service`、`rbac_role`）中的 `_resolve_party_filter()` 方法在本方案完成后将成为透传壳，可在后续 cleanup task 中简化。

安全校验不变：仍需验证请求的 party_id 在用户绑定范围内，否则 fail-closed。

#### `coerce_selected_view_party_filter` DI 边界说明

当前 `project.py`、`collection.py`、`history.py` 三个 API 模块使用 `coerce_selected_view_party_filter()` 包裹 `Depends` 注入的结果（共 13 个调用点）。该函数存在的原因是 FastAPI 依赖注入在某些代码路径下可能返回未解析的 `DependsParam` 对象而非实际值，`coerce` 作为防御性转换层处理这一边界情况。

**新方案中该问题不再存在**：`build_party_filter_from_params` 不通过 `Depends` 返回 `PartyFilter`，而是在端点函数体内被显式调用（接收 `Query` 参数 + `db` + `current_user`），因此不存在 DI 延迟解析问题。移除 `coerce` 是安全的。

**迁移验证**：在 Batch C/D 迁移 `project.py`、`collection.py`、`history.py` 时，需确认端点签名不再使用 `Depends(resolve_selected_view_party_filter_dependency)`，而是直接声明 `perspective: ... = Query(None)` + `party_id: ... = Query(None)` 并在函数体内调用 `build_party_filter_from_params()`。

### 3.6 前端变更总览

#### 移除

| 文件 | 动作 |
|------|------|
| `contexts/ViewContext.tsx` | 删除 |
| `components/System/GlobalViewSwitcher.tsx` | 删除 |
| `components/System/CurrentViewBanner.tsx` | 删除 |
| `utils/viewSelectionStorage.ts` | 删除 |
| `types/viewSelection.ts` | 删除 |
| `api/interceptors.ts:83-92` | 移除视角头注入代码 |
| `api/clientHelpers.ts:141-179` | 移除 authz-stale 检测代码 |
| `App.tsx` 中 `ViewProvider` 包裹 | 移除 |
| `AppHeader.tsx` 中 `GlobalViewSwitcher` | 移除 |
| `AuthContext.tsx` 中 authz-stale 监听 | 移除 |

#### 新增

| 文件 | 内容 |
|------|------|
| `hooks/usePerspective.ts` | 从路由前缀推导当前视角（纯计算，~15 行） |
| `hooks/useMyParties.ts` | 基于 capabilities 获取当前视角下可选主体列表（~40 行） |
| `config/menuConfig.tsx` 重构 | 按视角分组 + 基于绑定动态显隐（~100 行改动） |
| `constants/routes.ts` | 增加 `/owner/*` 和 `/manager/*` 路由常量 |
| `routes/AppRoutes.tsx` | 增加视角路由映射 |

#### 改动

| 文件 | 改动内容 |
|------|----------|
| `components/Common/PartySelector.tsx` | `useView()` → `usePerspective()`，同功能更简实现 |
| `pages/Assets/AssetListPage.tsx` | 移除 `CurrentViewBanner`，API 调用改为显式传参 |
| `components/Project/ProjectList.tsx` | 同上 |
| `pages/Project/ProjectDetailPage.tsx` | 同上 |
| 所有使用 `resolve_selected_view_party_filter_dependency` 的后端 API | 改为 Query 参数接收 |

### 3.7 菜单权限感知

当前菜单（`menuConfig.tsx`）对所有用户显示所有项。本方案需要增加权限过滤：

```typescript
// menuConfig.tsx 改造示意
interface MenuItemConfig {
  key: string;
  label: string;
  icon: ReactNode;
  // 新增：可见性条件
  visibility?: {
    requirePerspective?: 'owner' | 'manager';  // 需要该视角的绑定
    adminOnly?: boolean;
  };
  children?: MenuItemConfig[];
}

// AppSidebar.tsx 改造示意
function AppSidebar() {
  const { capabilities } = useAuth();
  // 基于 resource-level perspectives 判断（依赖 3.9 后端改造）
  const hasOwnerResources = capabilities?.some(c =>
    c.perspectives.includes('owner')
  ) ?? false;
  const hasManagerResources = capabilities?.some(c =>
    c.perspectives.includes('manager')
  ) ?? false;

  const visibleItems = filterMenuItems(MENU_ITEMS, {
    hasOwnerBinding: hasOwnerResources,
    hasManagerBinding: hasManagerResources,
    isAdmin,
  });
  // ...
}
```

### 3.8 跨视角页面处理

仪表盘（Dashboard）和数据分析（Analytics）需要同时展示产权方和运营方数据。这些页面不属于任何视角路由前缀，直接发起多次 API 调用：

> **⚠️ Analytics API 当前状态**：截至方案编写时，`api/v1/analytics/` 下的 23 个端点均未接受 `perspective` / `party_id` 参数，数据不按主体/视角过滤。下方代码示例展示的是**目标状态**，实际实现有两种路径：
> 1. **推荐（Phase 1 同步实施）**：在 analytics 端点中增加 `perspective` + `party_id` 可选参数，复用 `build_party_filter_from_params()`。工作量约 1-2 天，需新增 Batch（见 Section 9 Batch D 后备注）。
> 2. **备选（延后处理）**：Dashboard 暂时调用现有无视角过滤的 analytics 端点，展示用户可见的全量汇总数据，不区分 owner/manager。在后续迭代中补充视角支持。
>
> 选择哪种路径在实施前确认。

```typescript
function DashboardPage() {
  // 分别获取两个视角的汇总数据
  const ownerStats = useQuery(['stats', 'owner'], () => analyticsApi.summary({ perspective: 'owner' }));
  const managerStats = useQuery(['stats', 'manager'], () => analyticsApi.summary({ perspective: 'manager' }));
  // 并排展示
}
```

### 3.9 `CapabilityItem.perspectives` 字段处理

当前 `CapabilityItem` 在后端 schema（`schemas/authz.py:40`）和前端类型（`types/capability.ts:49`）中均包含 `perspectives: list[str]` / `Perspective[]` 字段，表示该能力在哪些视角下可用。

#### 当前实现的缺陷

后端 `authz/service.py:145-156` 中，`perspectives` 在 `_resolve_perspectives()` 里基于用户的 `user_party_bindings` **一次性计算**，然后 **相同的值被打在每一个 CapabilityItem 上**。换句话说，`perspectives` 是 user-level 而非 resource-level：

```python
# authz/service.py 现状（简化）
perspectives = self._resolve_perspectives(subject_context)  # 用户级：["owner", "manager"]
for resource, actions in actions_by_resource.items():
    capabilities.append(CapabilityItem(
        resource=resource,
        perspectives=perspectives,  # ← 每个 resource 都拿到相同的 perspectives
        ...
    ))
```

这导致：一个同时绑定了 owner 和 manager 的用户，其 `project` 资源的 `perspectives` 会是 `["owner", "manager"]`，但项目管理实际上只在 manager 视角下有意义。前端通过 `PERSPECTIVE_OVERRIDES` 硬编码修正了这一问题：

```typescript
// capabilityEvaluator.ts 现状
const PERSPECTIVE_OVERRIDES: Partial<Record<ResourceType, Perspective[]>> = {
  project: ['manager'],
};
```

#### 本方案的决策

**保留 `perspectives` 字段，但将其改为 resource-level。** 具体做法：

1. **后端改造**（`authz/service.py`）：引入一个 `RESOURCE_PERSPECTIVE_MAP` 配置，定义每个 resource 支持哪些 perspectives。`_resolve_perspectives` 改为接收 `resource` 参数，返回该 resource 支持的且用户确实有对应绑定的 perspectives 交集。

```python
# 新设计
RESOURCE_PERSPECTIVE_MAP: dict[str, list[str]] = {
    "asset": ["owner", "manager"],
    "contract_group": ["owner", "manager"],
    "property_certificate": ["owner"],
    "project": ["manager"],
    "ledger": ["manager"],
    # ... 其他 resource 按实际业务定义
}

def _resolve_perspectives(subject_context, resource: str) -> list[str]:
    user_perspectives = []
    if subject_context.owner_party_ids:
        user_perspectives.append("owner")
    if subject_context.manager_party_ids:
        user_perspectives.append("manager")
    allowed = RESOURCE_PERSPECTIVE_MAP.get(resource, user_perspectives)
    return [p for p in allowed if p in user_perspectives]
```

2. **前端**：移除 `PERSPECTIVE_OVERRIDES` 硬编码，直接依赖后端返回的 resource-specific `perspectives`。

3. **菜单可见性判断**：不再用 `data_scope.owner_party_ids.length > 0` 判断整个分组的可见性（这仍然是 user-level），而是用 capabilities 中是否存在 `perspective` 包含 `owner`/`manager` 的 resource 来决定：

```typescript
// 更精确的菜单可见性判断
const hasOwnerResources = capabilities?.some(c =>
  c.perspectives.includes('owner')
) ?? false;
const hasManagerResources = capabilities?.some(c =>
  c.perspectives.includes('manager')
) ?? false;
```

#### 连带改动

| 文件 | 改动 |
|------|------|
| `backend/src/services/authz/service.py` | `_resolve_perspectives` 改为 resource-aware |
| `frontend/src/utils/authz/capabilityEvaluator.ts` | 删除 `PERSPECTIVE_OVERRIDES` |
| `frontend/src/hooks/useCapabilities.ts` | `getAvailablePerspectives` 不再需要 override 逻辑 |
| `backend/tests/` | 补充 resource-level perspectives 单测 |

### 3.10 旧路由兼容与重定向

现有路由（`/assets/list`、`/contract-groups`、`/project` 等）需要渐进迁移：

**策略：先加新路由，后废旧路由。**

1. **Phase A**：新增 `/owner/*` 和 `/manager/*` 路由，指向同一批页面组件，菜单改为指向新路由。旧路由保留但不在菜单中展示。
2. **Phase B**：旧路由添加重定向到新路由（需推导默认视角：如用户有 owner 绑定则重定向到 `/owner/*`，否则 `/manager/*`）。
3. **Phase C**：移除旧路由定义。

**重定向组件必须处理 capabilities 加载态**：旧路由重定向需要知道用户的绑定关系才能推导目标路由，而 capabilities 来自 API 异步加载。重定向组件应：
- capabilities 加载中 → 渲染 loading spinner（或 Skeleton），不做跳转
- capabilities 加载完成 → 按绑定推导目标并 `<Navigate replace>` 
- capabilities 加载失败 → 重定向到 `/dashboard`（安全降级）

```typescript
// LegacyRouteRedirect.tsx 示意
function LegacyRouteRedirect({ legacyPath }: { legacyPath: string }) {
  const { capabilities, capabilitiesLoading } = useAuth();
  if (capabilitiesLoading) return <PageSkeleton />;
  const target = resolveDefaultPerspectiveRoute(legacyPath, capabilities);
  return <Navigate to={target} replace />;
}
```

---

## 4. 实施计划

> 按依赖关系排序，每个任务都应独立完成：先写失败测试，再做最小实现，再跑受影响验证。

### Phase 1：后端 — 参数化视角传递（~2 天）

#### Task 1：为查询参数版视角收窄建立最小后端闭环

- [ ] **Step 1.1** 在 `backend/tests/unit/api/v1/test_view_scope.py` 旁新增或改写测试，先覆盖 `build_party_filter_from_params()` 的 5 个核心场景
  - 合法 `owner + party_id` → 返回单 party 收窄的 PartyFilter
  - 非法 `party_id` → fail-closed `PartyFilter(party_ids=[])`
  - `perspective=None, party_id=None` → 返回用户完整范围的 PartyFilter（**非 None**）
  - `party_id` 指定但 `perspective=None` → 返回 400
  - 特权用户 + 无参数 → 返回全量放行 PartyFilter（`allow_null=True`）
- [ ] **Step 1.2** 运行失败测试
  - Run: `cd backend && uv run pytest --no-cov tests/unit/api/v1/test_view_scope.py -q`
- [ ] **Step 1.3** 在 `backend/src/services/view_scope.py` 内新增 `build_party_filter_from_params()`，先复用现有 `resolve_user_party_filter()` 完成最小实现
- [ ] **Step 1.4** 再次运行 `test_view_scope.py`，确认新函数通过

#### Task 2：先打通一条代表性 API 链路（assets）

- [ ] **Step 2.1** 在 `backend/tests/integration/api/test_assets_visibility_real.py` 先新增 query 参数版用例，锁定“query 参数只收窄、不放大”
- [ ] **Step 2.2** 运行单文件测试，确认先失败
  - Run: `cd backend && uv run pytest --no-cov tests/integration/api/test_assets_visibility_real.py -q`
- [ ] **Step 2.3** 修改 `backend/src/api/v1/assets/assets.py`，增加 `perspective` / `party_id` 查询参数，并优先走 `build_party_filter_from_params()`
- [ ] **Step 2.4** 保留旧 header 路径作为过渡兼容，直到全部前端页面完成迁移
- [ ] **Step 2.5** 重跑 `test_assets_visibility_real.py` 与 `backend/tests/unit/api/v1/test_assets_authz_layering.py`

#### Task 3：批量迁移剩余 7 个后端 API 模块

- [ ] **Step 3.1** 先为 `project`、`property_certificate`、`contract_groups`、`ledger`、`collection`、`history`、`party` 各补一个 query 参数版最小回归
- [ ] **Step 3.2** 分两批改 API：
  - Batch A：`project.py`、`collection.py`、`history.py`（同步移除 `coerce_selected_view_party_filter()`）
  - Batch B：`property_certificate.py`、`contract_groups.py`、`ledger.py`、`party.py`
- [ ] **Step 3.3** 每完成一批即跑对应集成测试，避免一次性大面积回归
  - Run: `cd backend && uv run pytest --no-cov tests/integration/api/test_project_visibility_real.py tests/integration/api/test_collection_visibility_real.py tests/integration/api/test_history_visibility_real.py -q`
  - Run: `cd backend && uv run pytest --no-cov tests/integration/api/test_property_certificate_visibility_real.py tests/integration/api/test_contract_visibility_real.py tests/integration/api/test_party_api_real.py -q`

#### Task 4：移除后端 header 解析与 authz-stale 机制

- [ ] **Step 4.1** 在 `backend/tests/unit/middleware/test_authz_dependency.py`、`backend/tests/unit/core/test_exception_handling.py` 先删/改 stale 相关断言，使测试明确描述新行为
- [ ] **Step 4.2** 运行这两组测试，确认先失败
  - Run: `cd backend && uv run pytest --no-cov tests/unit/middleware/test_authz_dependency.py tests/unit/core/test_exception_handling.py -q`
- [ ] **Step 4.3** 修改 `backend/src/middleware/auth_authz.py`，移除 `_should_mark_authz_stale()` 及所有 `authz_stale=` 调用
- [ ] **Step 4.4** 修改 `backend/src/core/exception_handler.py`，移除 `BaseBusinessError.authz_stale` 字段、`forbidden()` / `not_found()` 的 `authz_stale` 参数、`_should_set_authz_stale_header()` 与响应头注入
- [ ] **Step 4.5** 删除 `backend/src/services/view_scope.py` 中旧 header 入口（或清空为只保留 `build_party_filter_from_params()`）
- [ ] **Step 4.6** 跑后端受影响测试集合
  - Run: `cd backend && uv run pytest --no-cov tests/unit/api/v1/test_view_scope.py tests/unit/middleware/test_authz_dependency.py tests/unit/core/test_exception_handling.py tests/integration/api/test_assets_visibility_real.py tests/integration/api/test_project_visibility_real.py tests/integration/api/test_contract_visibility_real.py tests/integration/api/test_collection_visibility_real.py tests/integration/api/test_history_visibility_real.py tests/integration/api/test_property_certificate_visibility_real.py tests/integration/api/test_party_api_real.py -q`

#### Task 4b：将 perspectives 改为 resource-level

- [ ] **Step 4b.1** 在 `backend/tests/unit/services/test_authz_service.py`（如不存在则新建）新增测试用例：
  - 同时有 owner 和 manager 绑定的用户 → `project` 资源的 `perspectives` 只包含 `["manager"]`
  - 同时有 owner 和 manager 绑定的用户 → `asset` 资源的 `perspectives` 包含 `["owner", "manager"]`
  - 仅 owner 绑定的用户 → `project` 资源的 `perspectives` 为空列表
- [ ] **Step 4b.2** 运行失败测试
- [ ] **Step 4b.3** 修改 `backend/src/services/authz/service.py`：引入 `RESOURCE_PERSPECTIVE_MAP`，改造 `_resolve_perspectives` 为接收 `resource` 参数
- [ ] **Step 4b.4** 重跑 capabilities 相关测试
  - Run: `cd backend && uv run pytest --no-cov tests/unit/services/test_authz_service.py -q`

### Phase 2：前端 — 路由、菜单、页面迁移（~3 天）

#### Task 5：先建立前端替代能力（新 hook + 路由常量）

- [ ] **Step 5.1** 新增 `frontend/src/hooks/__tests__/usePerspective.test.tsx`，覆盖 `/owner/*`、`/manager/*`、无视角路由三种情况
- [ ] **Step 5.2** 运行失败测试
  - Run: `cd frontend && pnpm test -- src/hooks/__tests__/usePerspective.test.tsx`
- [ ] **Step 5.3** 新增 `frontend/src/hooks/usePerspective.ts`
- [ ] **Step 5.4** 新增 `frontend/src/hooks/__tests__/useMyParties.test.tsx`，覆盖单主体自动选中、多主体列表、无绑定空数组
- [ ] **Step 5.5** 实现 `frontend/src/hooks/useMyParties.ts`
- [ ] **Step 5.6** 修改 `frontend/src/constants/routes.ts`、`frontend/src/routes/AppRoutes.tsx`，先加 `/owner/*` 和 `/manager/*`，旧路由保留
- [ ] **Step 5.7** 跑 hooks 受影响测试
  - Run: `cd frontend && pnpm test -- src/hooks/__tests__/usePerspective.test.tsx src/hooks/__tests__/useMyParties.test.tsx`

#### Task 6：先迁移菜单，再迁移页面消费者

- [ ] **Step 6.1** 在 `frontend/src/components/Layout/__tests__/AppHeader.test.tsx`、相关导航测试中先移除对 `GlobalViewSwitcher` 的期待，增加“按绑定显示菜单分组”的断言
- [ ] **Step 6.2** 修改 `frontend/src/config/menuConfig.tsx`、`frontend/src/components/Layout/AppSidebar.tsx`、`frontend/src/components/Layout/MobileMenu.tsx`
- [ ] **Step 6.3** 迁移 `frontend/src/components/Common/PartySelector.tsx` 到 `usePerspective()`
- [ ] **Step 6.4** 迁移页面消费者：`AssetListPage.tsx`、`ProjectList.tsx`、`ProjectDetailPage.tsx`，改为显式 API 参数
- [ ] **Step 6.5** 如 `ContractGroupListPage`、`LedgerListPage`、`PropertyCertificateListPage` 已存在相同消费模式，同批切换到 query 参数
- [ ] **Step 6.6** 跑页面与组件测试
  - Run: `cd frontend && pnpm test -- src/pages/Assets/__tests__/AssetListPage.test.tsx src/components/Project/__tests__/ProjectList.test.tsx src/pages/Project/__tests__/ProjectDetailPage.test.tsx src/components/Common/__tests__/PartySelector.test.tsx src/components/Layout/__tests__/AppHeader.test.tsx`

#### Task 7：删除前端全局视角机制

- [ ] **Step 7.1** 先改测试：`ViewContext.test.tsx`、`GlobalViewSwitcher.test.tsx` 标记删除；`useAuth.test.ts`、`client.test.ts`、`useCapabilities.test.tsx`、`CapabilityGuard.test.tsx` 去掉 stale / header / override 旧断言
- [ ] **Step 7.2** 删除 `frontend/src/contexts/ViewContext.tsx`、`frontend/src/components/System/GlobalViewSwitcher.tsx`、`frontend/src/components/System/CurrentViewBanner.tsx`、`frontend/src/utils/viewSelectionStorage.ts`、`frontend/src/types/viewSelection.ts`
- [ ] **Step 7.3** 修改 `frontend/src/App.tsx`、`frontend/src/components/Layout/AppHeader.tsx`、`frontend/src/api/interceptors.ts`、`frontend/src/api/clientHelpers.ts`、`frontend/src/contexts/AuthContext.tsx`
- [ ] **Step 7.4** 修改 `frontend/src/utils/authz/capabilityEvaluator.ts`、`frontend/src/hooks/useCapabilities.ts`、`frontend/src/components/System/CapabilityGuard.tsx`，移除 `PERSPECTIVE_OVERRIDES`，改为依赖后端 `perspectives`
- [ ] **Step 7.5** 跑前端受影响测试集合
  - Run: `cd frontend && pnpm test -- src/api/__tests__/client.test.ts src/hooks/__tests__/useAuth.test.ts src/hooks/__tests__/useCapabilities.test.tsx src/components/System/__tests__/CapabilityGuard.test.tsx src/components/Layout/__tests__/AppHeader.test.tsx`

### Phase 3：旧路由迁移、清理与文档收口（~1 天）

#### Task 8：旧路由重定向与最终清理

- [ ] **Step 8.1** 先新增 `frontend/src/routes/__tests__/AppRoutes.perspective-redirect.test.tsx`，锁定旧 `/assets/list`、`/contract-groups`、`/project`、`/property-certificates` 的跳转目标
- [ ] **Step 8.2** 新增 `frontend/src/routes/LegacyRouteRedirect.tsx`，处理 capabilities 加载中/完成/失败三种状态；在 `AppRoutes.tsx` 中为旧路由挂载该组件，默认目标按"优先 owner → manager → dashboard"推导
- [ ] **Step 8.3** 验证无 404 后，再删除旧路由定义和遗留菜单入口
- [ ] **Step 8.4** 运行前端路由/导航测试与一次全量类型检查
  - Run: `cd frontend && pnpm test -- src/routes`
  - Run: `cd frontend && pnpm type-check`

#### Task 9：文档与 SSOT 回写

- [ ] **Step 9.1** 更新 `docs/requirements-specification.md` 中 REQ-AUTH-002 的实现状态、验收和代码证据
- [ ] **Step 9.2** 如接口参数说明有变化，同步更新 `docs/features/requirements-appendix-fields.md`
- [ ] **Step 9.3** 更新 `CHANGELOG.md`
- [ ] **Step 9.4** 跑 `make docs-lint`

#### Task 10：最终验证

- [ ] **Step 10.1** 跑后端受影响测试集合
- [ ] **Step 10.2** 跑前端受影响测试集合
- [ ] **Step 10.3** 跑 `make check`
- [ ] **Step 10.4** 核对删除文件、路由死链、菜单显隐、query 参数过滤与 fail-closed 行为

---

## 5. 影响分析

### 5.1 需修改的前端文件清单

| 文件 | 动作 | Phase |
|------|------|-------|
| `contexts/ViewContext.tsx` | **删除** | 2.6 |
| `components/System/GlobalViewSwitcher.tsx` | **删除** | 2.6 |
| `components/System/CurrentViewBanner.tsx` | **删除** | 2.6 |
| `utils/viewSelectionStorage.ts` | **删除** | 2.6 |
| `types/viewSelection.ts` | **删除** | 2.6 |
| `hooks/usePerspective.ts` | **新增** | 2.1 |
| `hooks/useMyParties.ts` | **新增** | 2.2 |
| `App.tsx` | 改动（移除 ViewProvider） | 2.6 |
| `api/interceptors.ts` | 改动（移除头注入） | 2.6 |
| `api/clientHelpers.ts` | 改动（移除 stale 检测） | 2.6 |
| `contexts/AuthContext.tsx` | 改动（移除 stale 监听） | 2.6 |
| `components/Layout/AppHeader.tsx` | 改动（移除 GlobalViewSwitcher） | 2.6 |
| `config/menuConfig.tsx` | 改动（菜单重组） | 2.4 |
| `components/Layout/AppSidebar.tsx` | 改动（增加权限过滤） | 2.4 |
| `components/Layout/MobileMenu.tsx` | 改动（增加权限过滤） | 2.4 |
| `constants/routes.ts` | 改动（新增路由常量） | 2.3 |
| `routes/AppRoutes.tsx` | 改动（新增路由定义） | 2.3 |
| `routes/LegacyRouteRedirect.tsx` | **新增**（旧路由按绑定重定向） | 3.1 |
| `pages/Assets/AssetListPage.tsx` | 改动（API 参数化） | 2.5 |
| `components/Project/ProjectList.tsx` | 改动（API 参数化） | 2.5 |
| `pages/Project/ProjectDetailPage.tsx` | 改动（API 参数化） | 2.5 |
| `components/Common/PartySelector.tsx` | 改动（useView → usePerspective） | 2.5 |
| `utils/authz/capabilityEvaluator.ts` | 改动（移除 PERSPECTIVE_OVERRIDES） | 2.6 |
| `hooks/useCapabilities.ts` | 改动（简化 perspective 相关代码） | 2.6 |
| `components/System/CapabilityGuard.tsx` | 改动（perspective 参数来源改为 usePerspective） | 2.6 |
| `types/capability.ts` | 保留（`Perspective` 类型和 `CapabilityItem.perspectives` 字段不变） | — |

### 5.2 需修改的后端文件清单

| 文件 | 动作 | Phase |
|------|------|-------|
| `services/view_scope.py` | **删除**（或清空为仅保留 `build_party_filter_from_params`） | 1.3 |
| `api/v1/assets/assets.py` | 改动（Query 参数替代 Depends） | 1.2 |
| `api/v1/assets/project.py` | 改动 | 1.2 |
| `api/v1/assets/property_certificate.py` | 改动 | 1.2 |
| `api/v1/contracts/contract_groups.py` | 改动 | 1.2 |
| `api/v1/contracts/ledger.py` | 改动 | 1.2 |
| `api/v1/system/collection.py` | 改动 | 1.2 |
| `api/v1/system/history.py` | 改动 | 1.2 |
| `api/v1/party.py` | 改动 | 1.2 |
| `middleware/auth_authz.py` | 改动（移除 stale 检测） | 1.4 |
| `core/exception_handler.py` | 改动（移除 `authz_stale` 字段、工厂函数参数、`_should_set_authz_stale_header()`、stale 头注入） | 1.4 |
| `services/authz/service.py` | 改动（`_resolve_perspectives` 改为 resource-aware，引入 `RESOURCE_PERSPECTIVE_MAP`） | 1.4b |
| `schemas/authz.py` | 保留（`CapabilityItem.perspectives` 字段不变） | — |

### 5.3 需修改的测试文件清单

| 文件 | 动作 |
|------|------|
| `frontend/src/contexts/__tests__/ViewContext.test.tsx` | **删除** |
| `frontend/src/components/System/__tests__/GlobalViewSwitcher.test.tsx` | **删除** |
| `frontend/src/components/Project/__tests__/ProjectList.test.tsx` | 改动（移除 ViewContext mock） |
| `frontend/src/pages/Project/__tests__/ProjectDetailPage.test.tsx` | 改动（移除 ViewContext mock） |
| `frontend/src/components/Common/__tests__/PartySelector.test.tsx` | 改动（mock 改为 usePerspective） |
| `frontend/src/pages/Assets/__tests__/AssetListPage.test.tsx` | 改动（移除 ViewContext mock） |
| `frontend/src/api/__tests__/client.test.ts` | 改动（移除 header 注入相关断言） |
| `frontend/src/hooks/__tests__/usePerspective.test.tsx` | **新增**（路由前缀 → perspective 推导） |
| `frontend/src/hooks/__tests__/useMyParties.test.tsx` | **新增**（单主体自动选中 / 多主体列表） |
| `frontend/src/hooks/__tests__/useAuth.test.ts` | 改动（移除 authz-stale 事件派发/合并相关测试用例） |
| `frontend/src/hooks/__tests__/useCapabilities.test.tsx` | 改动（移除 perspective override 相关测试） |
| `frontend/src/components/Layout/__tests__/AppHeader.test.tsx` | 改动（移除 GlobalViewSwitcher mock） |
| `frontend/src/components/System/__tests__/CapabilityGuard.test.tsx` | 改动（移除 perspective prop 相关断言） |
| `frontend/src/routes/__tests__/AppRoutes.perspective-redirect.test.tsx` | **新增**（旧路由跳转目标） |
| `backend/tests/unit/api/v1/test_view_scope.py` | **删除**（或重写为 `build_party_filter_from_params` 测试） |
| `backend/tests/unit/middleware/test_authz_dependency.py` | 改动（移除 `_should_mark_authz_stale` 相关用例） |
| `backend/tests/unit/core/test_exception_handling.py` | 改动（移除 `authz_stale` 头相关断言） |
| `backend/tests/unit/services/test_authz_service.py` | **新增**（resource-level perspectives） |
| `backend/tests/integration/api/test_party_api_real.py` | **迁移**（`X-View-*` 头 → query 参数） |
| `backend/tests/integration/api/test_assets_visibility_real.py` | **迁移**（同上） |
| `backend/tests/integration/api/test_project_visibility_real.py` | **迁移**（同上） |
| `backend/tests/integration/api/test_contract_visibility_real.py` | **迁移**（同上；覆盖 `contract_groups` 与 `ledger/entries`） |
| `backend/tests/integration/api/test_collection_visibility_real.py` | **迁移**（同上） |
| `backend/tests/integration/api/test_history_visibility_real.py` | **迁移**（同上） |
| `backend/tests/integration/api/test_property_certificate_visibility_real.py` | **迁移**（同上） |

---

## 6. 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| 改动面较大（~25 前端文件 + ~11 后端文件） | 引入回归 | 分三个 Phase 推进，每 Phase 独立可验证；后端先加新接口再移旧接口 |
| 旧路由的外部链接/收藏夹失效 | 用户体验 | Phase 3 设重定向，不直接删除旧路由 |
| 菜单项增多 | 侧边栏空间 | 通过分组折叠控制，默认展开用户主要视角 |
| 多主体用户需要在页面内选择主体 | 比全局选择器多一步 | 如果用户只有一个主体则自动选中，无额外操作 |
| 跨视角导航（从自有资产跳转到该资产的代管合同） | 路由跳转需跨前缀 | 页面内链接直接用完整路径，不依赖当前视角上下文 |

---

## 7. 验收标准

1. 全局视角切换器 UI 已移除，所有相关代码已清理。
2. 用户通过菜单入口进入不同视角页面，数据按视角正确过滤。
3. 菜单项按用户绑定动态显隐（无 owner 绑定不显示"自有资产"）。
4. 多主体用户在页面内通过下拉筛选选择具体主体。
5. 单主体用户自动选中，无额外交互步骤。
6. 仪表盘等跨视角页面正常展示双视角数据。
7. 后端 PartyFilter 数据隔离仍然有效，fail-closed 安全特性保留。
8. 旧路由有重定向兜底，不产生 404。
9. 所有现有测试通过或已按新架构更新。
10. `make check` 全量门禁通过。

---

## 8. 净效果估算

| 指标 | 变更 |
|------|------|
| 删除代码 | ~1500-2000 行（ViewContext + GlobalViewSwitcher + viewSelectionStorage + view_scope.py + stale 机制） |
| 新增代码 | ~200-300 行（usePerspective + useMyParties + build_party_filter_from_params + 菜单重构） |
| 净减少 | ~1200-1700 行 |
| 消除的全局状态 | 1 个 React Context + 1 个 localStorage key + 2 个 HTTP header + 1 个 CustomEvent |
| 修复的 Bug | 2 个（CurrentViewBanner + GlobalViewSwitcher 的 Ant Design API 误用，随组件删除一并消除） |
| 消除的问题 | 审计报告中 13 个 Issue 中的 9 个直接消除（ISSUE-VIEW-003/004/005/009/010/011/012/013 随全局视角 UI 删除一并消除；ISSUE-VIEW-006/007/008 是独立于视角 UI 的后端架构问题，需单独处理；ISSUE-VIEW-013 的 PERSPECTIVE_OVERRIDES 硬编码改为依赖后端 perspectives 字段） |

---

## 9. 按文件批次执行建议

> 用于实际落地时控制改动半径。每个批次都应做到：测试先失败、最小实现、受影响验证通过后再进入下一批。

### Batch A：后端基础函数与单测骨架

**目标**：先把 query 参数版视角过滤能力建立起来，但暂不大面积改 API。

**建议改动文件：**

- `backend/src/services/view_scope.py`
- `backend/tests/unit/api/v1/test_view_scope.py`

**建议验证：**

- `cd backend && uv run pytest --no-cov tests/unit/api/v1/test_view_scope.py -q`

**完成标志：**

- `build_party_filter_from_params()` 已存在
- 总是返回 `PartyFilter`，永不返回 `None`
- `perspective=None, party_id=None` → 返回用户完整范围的 PartyFilter
- 非法 `party_id` 继续 fail-closed
- `party_id` 指定但 `perspective=None` → 400

### Batch B：代表性后端链路（assets）

**目标**：只打通一条最重要的读链路，验证“query 参数替代 header”在真实 API 上成立。

**建议改动文件：**

- `backend/src/api/v1/assets/assets.py`
- `backend/tests/integration/api/test_assets_visibility_real.py`
- `backend/tests/unit/api/v1/test_assets_authz_layering.py`

**建议验证：**

- `cd backend && uv run pytest --no-cov tests/integration/api/test_assets_visibility_real.py tests/unit/api/v1/test_assets_authz_layering.py -q`

**完成标志：**

- `GET /assets` 和 `GET /assets/{id}` 支持 query 参数版视角过滤
- 旧 header 路径仍可暂时工作

### Batch C：后端剩余 API 第一批

**目标**：优先清掉使用 `coerce_selected_view_party_filter()` 的 3 个模块，减少后续兼容包袱。

**建议改动文件：**

- `backend/src/api/v1/assets/project.py`
- `backend/src/api/v1/system/collection.py`
- `backend/src/api/v1/system/history.py`
- `backend/tests/integration/api/test_project_visibility_real.py`
- `backend/tests/integration/api/test_collection_visibility_real.py`
- `backend/tests/integration/api/test_history_visibility_real.py`

**建议验证：**

- `cd backend && uv run pytest --no-cov tests/integration/api/test_project_visibility_real.py tests/integration/api/test_collection_visibility_real.py tests/integration/api/test_history_visibility_real.py -q`

**完成标志：**

- 三个模块不再依赖 `coerce_selected_view_party_filter()`
- query 参数路径通过真实 A/B 测试

### Batch D：后端剩余 API 第二批

**目标**：完成剩余 4 个模块的 query 参数迁移。

**建议改动文件：**

- `backend/src/api/v1/assets/property_certificate.py`
- `backend/src/api/v1/contracts/contract_groups.py`
- `backend/src/api/v1/contracts/ledger.py`
- `backend/src/api/v1/party.py`
- `backend/tests/integration/api/test_property_certificate_visibility_real.py`
- `backend/tests/integration/api/test_contract_visibility_real.py`
- `backend/tests/integration/api/test_party_api_real.py`

**建议验证：**

- `cd backend && uv run pytest --no-cov tests/integration/api/test_property_certificate_visibility_real.py tests/integration/api/test_contract_visibility_real.py tests/integration/api/test_party_api_real.py -q`

**完成标志：**

- 8 个已接入 selected-view 的后端模块全部支持 query 参数

### Batch 4b：perspectives 改为 resource-level

**目标**：修正 `CapabilityItem.perspectives` 从 user-level 改为 resource-level，使前端菜单可见性判断不再依赖 `PERSPECTIVE_OVERRIDES` 硬编码。

**建议改动文件：**

- `backend/src/services/authz/service.py`
- `backend/tests/unit/services/test_authz_service.py`

**建议验证：**

- `cd backend && uv run pytest --no-cov tests/unit/services/test_authz_service.py -q`

**完成标志：**

- `RESOURCE_PERSPECTIVE_MAP` 已定义
- `_resolve_perspectives` 接收 `resource` 参数
- 双绑定用户的 `project` 资源 `perspectives` 为 `["manager"]`（非 `["owner", "manager"]`）
- 仅 owner 绑定用户的 `project` 资源 `perspectives` 为 `[]`

### Batch E：后端移除 stale / header 基础设施

**目标**：在 API 都已支持新路径后，再统一清掉旧的 stale/header 机制。

**建议改动文件：**

- `backend/src/middleware/auth_authz.py`
- `backend/src/core/exception_handler.py`
- `backend/src/services/view_scope.py`
- `backend/tests/unit/middleware/test_authz_dependency.py`
- `backend/tests/unit/core/test_exception_handling.py`

**建议验证：**

- `cd backend && uv run pytest --no-cov tests/unit/middleware/test_authz_dependency.py tests/unit/core/test_exception_handling.py tests/unit/api/v1/test_view_scope.py -q`

**完成标志：**

- `authz_stale` 字段、响应头、辅助函数和调用点全部清理
- `view_scope.py` 不再保留 header 入口

### Batch F：前端新能力层（hook + route）

**目标**：先加新能力，不立即删除旧视角机制，降低切换风险。

**建议改动文件：**

- `frontend/src/hooks/usePerspective.ts`
- `frontend/src/hooks/useMyParties.ts`
- `frontend/src/hooks/__tests__/usePerspective.test.tsx`
- `frontend/src/hooks/__tests__/useMyParties.test.tsx`
- `frontend/src/constants/routes.ts`
- `frontend/src/routes/AppRoutes.tsx`

**建议验证：**

- `cd frontend && pnpm test -- src/hooks/__tests__/usePerspective.test.tsx src/hooks/__tests__/useMyParties.test.tsx`

**完成标志：**

- `/owner/*`、`/manager/*` 路由已存在
- 页面可从路由推导 perspective

### Batch G：前端菜单与页面消费者迁移

**目标**：先让真实页面开始走新路由语义和 query 参数，不立即删除旧组件文件。

**建议改动文件：**

- `frontend/src/config/menuConfig.tsx`
- `frontend/src/components/Layout/AppSidebar.tsx`
- `frontend/src/components/Layout/MobileMenu.tsx`
- `frontend/src/components/Layout/__tests__/AppHeader.test.tsx`
- `frontend/src/components/Common/PartySelector.tsx`
- `frontend/src/components/Common/__tests__/PartySelector.test.tsx`
- `frontend/src/pages/Assets/AssetListPage.tsx`
- `frontend/src/pages/Assets/__tests__/AssetListPage.test.tsx`
- `frontend/src/components/Project/ProjectList.tsx`
- `frontend/src/components/Project/__tests__/ProjectList.test.tsx`
- `frontend/src/pages/Project/ProjectDetailPage.tsx`
- `frontend/src/pages/Project/__tests__/ProjectDetailPage.test.tsx`

**建议验证：**

- `cd frontend && pnpm test -- src/pages/Assets/__tests__/AssetListPage.test.tsx src/components/Project/__tests__/ProjectList.test.tsx src/pages/Project/__tests__/ProjectDetailPage.test.tsx src/components/Common/__tests__/PartySelector.test.tsx src/components/Layout/__tests__/AppHeader.test.tsx`

**完成标志：**

- 关键页面已不依赖 `useView()`
- 菜单已按 owner / manager 绑定动态显隐

### Batch H：前端删除全局视角机制

**目标**：在页面和菜单都已迁移后，再删除旧全局状态与请求注入链路。

**建议改动文件：**

- `frontend/src/contexts/ViewContext.tsx`
- `frontend/src/components/System/GlobalViewSwitcher.tsx`
- `frontend/src/components/System/CurrentViewBanner.tsx`
- `frontend/src/utils/viewSelectionStorage.ts`
- `frontend/src/types/viewSelection.ts`
- `frontend/src/App.tsx`
- `frontend/src/components/Layout/AppHeader.tsx`
- `frontend/src/api/interceptors.ts`
- `frontend/src/api/clientHelpers.ts`
- `frontend/src/contexts/AuthContext.tsx`
- `frontend/src/utils/authz/capabilityEvaluator.ts`
- `frontend/src/hooks/useCapabilities.ts`
- `frontend/src/components/System/CapabilityGuard.tsx`
- `frontend/src/contexts/__tests__/ViewContext.test.tsx`
- `frontend/src/components/System/__tests__/GlobalViewSwitcher.test.tsx`
- `frontend/src/api/__tests__/client.test.ts`
- `frontend/src/hooks/__tests__/useAuth.test.ts`
- `frontend/src/hooks/__tests__/useCapabilities.test.tsx`
- `frontend/src/components/System/__tests__/CapabilityGuard.test.tsx`

**建议验证：**

- `cd frontend && pnpm test -- src/api/__tests__/client.test.ts src/hooks/__tests__/useAuth.test.ts src/hooks/__tests__/useCapabilities.test.tsx src/components/System/__tests__/CapabilityGuard.test.tsx`

**完成标志：**

- 生产代码里不再出现 `useView` / `ViewContext` / `GlobalViewSwitcher` / `CurrentViewBanner`
- 请求不再自动注入 `X-View-*`

### Batch I：旧路由清理与 SSOT 回写

**目标**：最后再删除旧入口，避免中途文档和代码反复回滚。

**建议改动文件：**

- `frontend/src/routes/AppRoutes.tsx`
- `frontend/src/routes/LegacyRouteRedirect.tsx`（新增）
- `frontend/src/routes/__tests__/AppRoutes.perspective-redirect.test.tsx`（新增）
- `frontend/src/constants/routes.ts`
- `docs/requirements-specification.md`
- `docs/features/requirements-appendix-fields.md`
- `CHANGELOG.md`

**建议验证：**

- `cd frontend && pnpm type-check`
- `make docs-lint`
- `make check`

**完成标志：**

- 旧路由已重定向或删除
- SSOT 文档与代码证据同步回写完成

---

## 10. 最小实施顺序

> 如果后续真正开始落地，建议不要并行铺开所有批次，而是先完成下面 3 个最小批次，再决定是否继续扩大改动范围。

### First 1：Batch A（后端基础函数与单测骨架）

**为什么先做：**

- 这是所有后续 query 参数迁移的基础能力
- 改动面最小，只涉及 1 个服务文件 + 1 个单测文件
- 最容易先验证 fail-closed 语义没有被破坏

**进入条件：**

- 当前方案文档已确认不再修改数据隔离核心模型（`PartyFilter` / `QueryBuilder`）

**退出条件：**

- `build_party_filter_from_params()` 已可独立工作
- `backend/tests/unit/api/v1/test_view_scope.py` 通过

### First 2：Batch B（代表性后端链路：assets）

**为什么第二个做：**

- `assets` 是最核心的读链路，真实验证价值最高
- 已有 `test_assets_authz_layering.py` 和 `test_assets_visibility_real.py` 两层保护，最适合作为第一条迁移样板
- 一旦这条链路打通，剩余 API 可以照模板迁移

**进入条件：**

- Batch A 已完成

**退出条件：**

- `assets.py` 已支持 query 参数版视角过滤
- 旧 header 兼容仍然可用
- assets 的 unit/integration 测试都通过

### First 3：Batch F（前端新能力层：hook + route）

**为什么第三个做：**

- 先加 `usePerspective()` / `useMyParties()` 和新路由，再迁页面，能避免“后端新参数已就绪但前端没有承接能力”的空窗期
- 这一步仍然不删除旧全局视角机制，回退成本低

**进入条件：**

- Batch A、Batch B 已完成

**退出条件：**

- `/owner/*`、`/manager/*` 已存在
- 页面已经有可用的新 perspective 来源
- 尚未删除旧 `ViewContext` / `GlobalViewSwitcher` / `X-View-*` 注入链路

### 为什么不建议更早做的事项

- **不要先删前端全局视角机制**：否则页面还没迁完时会立刻失去现有可用路径
- **不要先删 authz-stale**：它属于旧链路清理项，应在 query 参数路径稳定后处理
- **不要先删旧路由**：应等新菜单、新页面参数、新测试全部稳定后再删

### 真正开工时的建议顺序

1. Batch A — 后端基础函数
2. Batch B — 代表性后端链路（assets）
3. Batch F — 前端新能力层（hook + route）
4. Batch C — 后端剩余 API 第一批（coerce 清理）
5. Batch D — 后端剩余 API 第二批
6. Batch 4b — perspectives 改为 resource-level（见 Task 4b）
7. Batch G — 前端菜单与页面消费者迁移
8. **Batch H — 前端删除全局视角机制（含 `X-View-*` header 注入）**
9. **Batch E — 后端移除 stale / header 基础设施**
10. Batch I — 旧路由清理与 SSOT 回写

> **⚠️ Batch E 必须在 Batch H 之后**：Batch E 移除后端对 `X-View-*` header 的解析能力，而 Batch H 才是前端停止注入这些 header 的步骤。如果 E 先于 H 执行，前端仍在发送 header 但后端已无法处理，会导致过渡期内所有视角过滤失效。正确顺序：前端先停止发送（H）→ 后端再移除接收（E）。
