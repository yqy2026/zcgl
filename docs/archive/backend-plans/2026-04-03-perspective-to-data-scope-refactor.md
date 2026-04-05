# 视角机制 → 数据范围自动注入 重构实施计划 ✅

> **状态**: ✅ 已完成（2026-04-04，已归档）
> **需求依据**: `docs/requirements-specification.md` §5.2（2026-04-03 业务访谈修正版）
> **REQ 编号**: REQ-AUTH-002（🚧）
> **预估影响文件数**: 后端 ~8 文件 + 前端 ~45 文件（含测试）
> **拆分策略**: 3 个独立可交付子任务，每个完成后可独立通过 `make check`

---

## 0. 设计总纲

### 当前状态（As-Is）

```
前端 URL /owner/* 或 /manager/*
  → perspective.ts 从 pathname 解析 perspective
  → client.ts 拦截器注入 X-Perspective header
  → 后端 PerspectiveContextChecker 要求 X-Perspective 必传（否则 400）
  → party_scope.py 按单一 filter_mode（owner 或 manager）过滤数据
```

**问题**：
1. 管理员无 party binding → "视角不可用"错误
2. 多绑定用户无法看到并集数据
3. 前端维护 `/owner/*` 和 `/manager/*` 两套路由，菜单按视角硬编码
4. 产权方看不到项目

### 目标状态（To-Be）

```
用户登录 → /auth/me/capabilities 返回现有契约（不改接口结构）
  → 前端 dataScopeStore 从 capabilities[].data_scope 聚合 bindingTypes
  → isAdmin 从 AuthContext.isAdmin 获取（已有通路，不新增字段）
  → client.ts 拦截器：
      单绑定 → 自动注入 X-Perspective: owner/manager
      多绑定 → 不注入（后端 fallback 到 all）
      管理员 → 不注入（后端 admin bypass）
  → 后端 PerspectiveContextChecker 允许无 header（构建并集 context）
  → party_scope.py 支持 filter_mode=all 并集过滤
  → 前端统一路由 /assets, /project, /contract-groups
  → 菜单可见性由 RBAC 控制
```

### `/auth/me/capabilities` 接口契约（最终定稿）

**决策**：不修改 `CapabilitiesResponse` 结构。前端从现有 `capabilities[].data_scope` 聚合绑定信息。

当前响应结构保持不变：

```json
{
  "version": "2026-03-25.v1",
  "generated_at": "...",
  "capabilities": [
    {
      "resource": "asset",
      "actions": ["create", "read", "list", "update", "delete"],
      "perspectives": ["owner", "manager"],
      "data_scope": {
        "owner_party_ids": ["party-001"],
        "manager_party_ids": ["party-002"]
      }
    }
  ]
}
```

前端 `dataScopeStore.initFromCapabilities()` 聚合逻辑：

```typescript
// 从所有 capability 的 data_scope 收集并去重
const allOwnerIds = new Set<string>();
const allManagerIds = new Set<string>();
for (const cap of capabilities) {
  cap.data_scope.owner_party_ids.forEach(id => allOwnerIds.add(id));
  cap.data_scope.manager_party_ids.forEach(id => allManagerIds.add(id));
}

// bindingTypes 推导
const bindingTypes: BindingType[] = [];
if (allOwnerIds.size > 0) bindingTypes.push('owner');
if (allManagerIds.size > 0) bindingTypes.push('manager');
```

`isAdmin` 来源：`useAuth().isAdmin`（`AuthContext.tsx` L507 已有 `user?.is_admin`），通过 `initFromCapabilities(capabilities, isAdmin)` 传入。**不新增接口字段**。

### 核心设计原则

1. **运营方 ⊃ 产权方**：运营方看到的数据是产权方的超集，不冲突
2. **不切换**：多绑定用户直接看并集，无需选择
3. **渐进式**：子任务 1（后端）不破坏前端；子任务 2（前端 store）与旧路由共存；子任务 3 统一清理

---

## 子任务 1：后端 — X-Perspective 可选 + 并集查询 + 管理员 bypass

### 目标
让后端支持「不发送 X-Perspective」的情况，自动走并集查询。同时修复管理员和产权方的项目可见性。

### 前置条件
无。可独立开发和部署。

### TDD 测试先行

#### 新增/修改测试文件

**[NEW] `backend/tests/unit/middleware/test_perspective_context_optional.py`**
- `test_no_perspective_header_returns_all_binding_context` — 无 header 时返回包含所有绑定的 context
- `test_no_perspective_header_admin_bypass` — 管理员无 header 时 bypass
- `test_perspective_all_header_returns_union_context` — `X-Perspective: all` 返回并集
- `test_single_binding_user_no_header_returns_single_scope` — 单绑定用户无 header 也正常工作
- `test_non_exempt_path_without_header_no_longer_400` — 非豁免路径不再因缺 header 报 400

**[MODIFY] `backend/tests/unit/services/test_party_scope.py`**
- `test_build_party_filter_perspective_all` — perspective=all 时返回 owner+manager 并集的 PartyFilter
- `test_build_party_filter_perspective_none_with_both_bindings` — perspective=None 且用户有双绑定时走并集

**[MODIFY] `backend/tests/integration/api/test_project_visibility_real.py`**
- `test_owner_user_sees_projects_via_asset_relation` — owner 用户通过资产关联查看项目

### 代码改动

#### [MODIFY] `backend/src/middleware/auth.py` — PerspectiveContextChecker

```python
# 当前（L392-393）:
if raw_perspective is None:
    raise bad_request("缺少 X-Perspective 请求头")

# 改为:
if raw_perspective is None:
    # 无 header → 构建全绑定 context（并集查询）
    raw_perspective = "all"

# 当前（L395-396）:
if raw_perspective not in {"owner", "manager"}:
    raise bad_request("X-Perspective 仅支持 owner 或 manager")

# 改为:
if raw_perspective not in {"owner", "manager", "all"}:
    raise bad_request("X-Perspective 仅支持 owner、manager 或 all")
```

PerspectiveContext（`auth.py` L354-363）新增 `perspective="all"` 分支：
- `effective_party_ids` = `owner_party_ids + manager_party_ids`（并集）
- 管理员继续走 bypass（effective_party_ids=[]）
- `source` 字段从 `Literal["header"]` 改为 `Literal["header", "auto"]`（无 header 时标记 `source="auto"`）

需要新增 `EffectivePerspective` 类型，**不修改** `PerspectiveName`。

#### `all` 类型边界（最终定稿）

| 层次 | 类型 | 值域 | 说明 |
|------|------|------|------|
| `capabilities[].perspectives` | `PerspectiveName` | `owner \| manager` | **不变**。`all` 永远不出现在 capabilities 响应中 |
| `PerspectiveContext.perspective` | `EffectivePerspective` | `owner \| manager \| all` | 仅后端中间态 Context 使用 |
| `X-Perspective` header | `string` | `owner \| manager`（前端只发这两个）| 前端**永远不发** `all`。无 header = 后端自动推导 `all` |
| 前端 `dataScopeStore` | `BindingType` | `owner \| manager` | 前端不感知 `all` 概念 |

**结论**：
1. `capabilities[].perspectives` 永远只返回 `owner | manager`
2. `all` 只存在于后端 `PerspectiveContext`（无 header 时自动设置）
3. 前端不处理 `all`，仅通过"是否注入 header"间接触发

#### [MODIFY] `backend/src/schemas/authz.py` — 新增 EffectivePerspective

```python
# PerspectiveName 保持不变：
PerspectiveName = Literal["owner", "manager"]

# 新增：仅用于 PerspectiveContext：
EffectivePerspective = Literal["owner", "manager", "all"]
```

#### [MODIFY] `backend/src/services/party_scope.py` — build_party_filter_from_perspective_context

```python
# 当前（L47-67）: 仅支持 owner/manager 二选一
# 改为: 新增 perspective == "all" 分支

def build_party_filter_from_perspective_context(
    perspective_context: object,
) -> PartyFilter | None:
    perspective = getattr(perspective_context, "perspective", None)

    if perspective == "all":
        # 并集: owner + manager
        owner_ids = _normalize_identifier_sequence(
            getattr(perspective_context, "owner_party_ids", None)
        )
        manager_ids = _normalize_identifier_sequence(
            getattr(perspective_context, "manager_party_ids", None)
        )
        if len(owner_ids) == 0 and len(manager_ids) == 0:
            return None
        merged_ids = sorted(set(owner_ids + manager_ids))
        return PartyFilter(
            party_ids=merged_ids,
            filter_mode="any",  # 已有模式，OR 查询
            owner_party_ids=owner_ids,
            manager_party_ids=manager_ids,
        )

    # 原有 owner/manager 逻辑保持不变
    ...
```

#### [MODIFY] `backend/src/services/authz/resource_perspective_registry.py`

```python
# 当前（L17）:
"project": ("manager",),

# 改为:
"project": ("owner", "manager"),
```

#### [MODIFY] `backend/src/services/authz/service.py` — get_capabilities

`get_capabilities()` 中 `resolve_capability_perspectives()` 的过滤逻辑：
- 当前（L190-195）：`resource_requires_perspective(resource) and len(perspectives) == 0` 时跳过该资源
- 问题：管理员无 party binding 导致 `_resolve_perspectives()` 返回 `[]` → perspectives=[] → 所有 perspective-scoped 资源被跳过
- 修复：在循环前获取 `is_admin` 标识（复用 L152 处已有的 `_get_user_role_ids` 调用，改为 `_get_user_role_summary` 以同时获取 `is_admin`），管理员直接用注册表全量视角

```python
# L152 改为:
role_summary = await self._get_user_role_summary(db, user_id=user_id)
role_ids = role_summary.get("role_ids", [])
is_admin = bool(role_summary.get("is_admin"))

# L190-195 改为:
if is_admin:
    perspectives = list(get_registered_perspectives(resource))
else:
    perspectives = resolve_capability_perspectives(resource, subject_perspectives)
    if resource_requires_perspective(resource) and len(perspectives) == 0:
        continue
```

> **Note**: `_get_user_role_ids()` already calls `_get_user_role_summary()` internally (`service.py` L243-254). Changing L152 to call `_get_user_role_summary()` directly eliminates one layer of indirection without needing a new method.

#### Project owner/all unified filtering (final decision)

**Problem**: `Project` only has `manager_party_id`, no `owner_party_id`. The original plan only forked the API list endpoint for owner queries, but `CRUDProject._apply_project_party_filter()` is the **unified filter entry** used by `get`, `get_multi`, `search`, and `get_statistics`. Forking only at the API level would leave search/statistics inconsistent.

**Decision**: Sink owner/all semantics into `CRUDProject._apply_project_party_filter()`.

#### [MODIFY] `backend/src/crud/project.py` — `_apply_project_party_filter`

```python
async def _apply_project_party_filter(
    self,
    db: AsyncSession,
    stmt: Select[Any],
    party_filter: PartyFilter,
) -> Select[Any]:
    """Unified project filter: supports manager / owner / any(union) modes."""
    filter_mode = party_filter.filter_mode

    if filter_mode == "manager":
        # Original logic: filter by manager_party_id
        if self._supports_party_scope_columns():
            return self.query_builder.apply_party_filter(stmt, party_filter)
        principals = await self._resolve_creator_principals(db, party_filter)
        return self._apply_creator_scope(stmt, principals)

    if filter_mode == "owner":
        # New: query projects via asset association
        owner_ids = party_filter.owner_party_ids
        if not owner_ids:
            return stmt.where(false())
        asset_project_ids = (
            select(Asset.project_id)
            .where(Asset.owner_party_id.in_(owner_ids))
            .where(Asset.project_id.is_not(None))
            .distinct()
        )
        return stmt.where(Project.id.in_(asset_project_ids))

    # filter_mode == "any" (union): manager direct filter + owner via asset
    manager_ids = party_filter.manager_party_ids
    owner_ids = party_filter.owner_party_ids
    conditions = []
    if manager_ids:
        conditions.append(Project.manager_party_id.in_(manager_ids))
    if owner_ids:
        asset_project_ids = (
            select(Asset.project_id)
            .where(Asset.owner_party_id.in_(owner_ids))
            .where(Asset.project_id.is_not(None))
            .distinct()
        )
        conditions.append(Project.id.in_(asset_project_ids))
    if not conditions:
        return stmt.where(false())
    return stmt.where(or_(*conditions))
```

> Requires adding `from ..models.asset import Asset` at top of `crud/project.py`.

**Key point**: The change is contained within `_apply_project_party_filter()`. All consumers (`get`, `get_multi`, `search`, `get_statistics`) automatically get consistent owner/all behavior. **No API endpoint forking.**

#### [MODIFY] `backend/src/services/party_scope.py` — perspective=all branch

When `perspective=all`, the generated `PartyFilter` must carry both `owner_party_ids` and `manager_party_ids` with `filter_mode="any"` so the CRUD layer can distinguish:

```python
if perspective == "all":
    owner_ids = _normalize_identifier_sequence(
        getattr(perspective_context, "owner_party_ids", None)
    )
    manager_ids = _normalize_identifier_sequence(
        getattr(perspective_context, "manager_party_ids", None)
    )
    if len(owner_ids) == 0 and len(manager_ids) == 0:
        return None
    merged_ids = sorted(set(owner_ids + manager_ids))
    return PartyFilter(
        party_ids=merged_ids,
        filter_mode="any",
        owner_party_ids=owner_ids,
        manager_party_ids=manager_ids,
    )
```

**All project read paths covered** (all go through `_apply_project_party_filter`):

| Method | Location |
|--------|----------|
| `CRUDProject.get()` | `crud/project.py` L150-169 |
| `CRUDProject.get_multi()` | `crud/project.py` L171-190 |
| `CRUDProject.search()` | `crud/project.py` L213-262 |
| `CRUDProject.get_statistics()` | `crud/project.py` L282-307 |

### 验证

```bash
cd backend
uv run pytest tests/unit/middleware/test_perspective_context_optional.py -v
uv run pytest tests/unit/services/test_party_scope.py -v -k "perspective"
uv run pytest tests/integration/api/test_project_visibility_real.py -v
uv run pytest -m "not slow" --maxfail=3  # 全量回归
```

### 兼容性保证
- 前端继续发 `X-Perspective: owner/manager` → 后端行为不变
- 前端不发 header → 后端走并集（新行为，但前端本次不改，只是后端支持了）
- 管理员不发 header → 后端 bypass（修复了当前 400 错误）

---

## 子任务 2：前端 — DataScopeStore + ApiClient 改造

### 目标
新建 `dataScopeStore`（Zustand），改造 `client.ts` 请求拦截器从 store 读取绑定信息自动决定是否注入 `X-Perspective`。**不删除旧代码**，新旧并存。

### 前置条件
子任务 1 后端部署完成（后端必须支持无 `X-Perspective` 的请求）。

### TDD 测试先行

**[NEW] `frontend/src/stores/__tests__/dataScopeStore.test.ts`**
- `test_initializes_from_capabilities_response` — 从 /auth/me/capabilities 初始化
- `test_single_owner_binding` — 单 owner 绑定
- `test_single_manager_binding` — 单 manager 绑定
- `test_dual_binding` — 双绑定
- `test_admin_flag` — 管理员标识
- `test_reset_on_logout` — 登出时重置

**[MODIFY] `frontend/src/api/__tests__/client.test.ts`**
- `test_single_owner_injects_perspective_header` — 单 owner 自动注入
- `test_single_manager_injects_perspective_header` — 单 manager 自动注入
- `test_dual_binding_no_perspective_header` — 双绑定不注入
- `test_admin_no_perspective_header` — 管理员不注入
- `test_auth_exempt_no_perspective_header` — /auth/* 不注入

### 代码改动

#### [NEW] `frontend/src/stores/dataScopeStore.ts`

```typescript
import { create } from 'zustand';
import type { CapabilitiesResponse } from '@/types/capability';

type BindingType = 'owner' | 'manager';

interface DataScopeState {
  bindingTypes: BindingType[];
  ownerPartyIds: string[];
  managerPartyIds: string[];
  isAdmin: boolean;
  initialized: boolean;

  // 便捷属性
  isOwner: boolean;
  isManager: boolean;
  isDualBinding: boolean;
  isSingleOwner: boolean;
  isSingleManager: boolean;

  // actions
  initFromCapabilities: (response: CapabilitiesResponse, isAdmin: boolean) => void;
  reset: () => void;

  // header 策略
  getEffectivePerspective: () => BindingType | null;
}

export const useDataScopeStore = create<DataScopeState>((set, get) => ({
  // ... 初始值和 actions
}));
```

#### [MODIFY] `frontend/src/api/client.ts`

```typescript
// L18: 替换 import
// 当前:
import { getCurrentRoutePerspective } from '@/routes/perspective';
// 改为:
import { useDataScopeStore } from '@/stores/dataScopeStore';

// L133-146: 替换 applyPerspectiveHeader
const applyPerspectiveHeader = (config: InternalAxiosRequestConfig): void => {
  if (isPerspectiveHeaderExemptRequest(config.url)) {
    removeHeader(config.headers, 'X-Perspective');
    return;
  }

  const { getEffectivePerspective } = useDataScopeStore.getState();
  const perspective = getEffectivePerspective();

  if (perspective == null) {
    removeHeader(config.headers, 'X-Perspective');
    return;
  }

  setHeader(config.headers, 'X-Perspective', perspective);
};
```

#### [MODIFY] `frontend/src/contexts/AuthContext.tsx` — dataScopeStore complete lifecycle

`dataScopeStore` must be synced at **all** auth state change points in `AuthContext`:

| Scenario | AuthContext location | dataScopeStore action |
|----------|---------------------|----------------------|
| **Login success** | `login()` L364 `triggerCapabilitiesRefresh` callback | `initFromCapabilities(capabilities, isAdmin)` |
| **Page refresh session restore** | `restoreAuth()` L261 `triggerCapabilitiesRefresh` callback | `initFromCapabilities(capabilities, isAdmin)` |
| **Cross-tab user switch** | `restoreAuth()` L246-268 cross-user branch | First `reset()`, then `initFromCapabilities()` in new capabilities callback |
| **Capabilities force refresh** | `refreshCapabilities()` | Re-call `initFromCapabilities()` in `refreshCapabilitiesByUser` success callback |
| **Capabilities fetch failure** | `refreshCapabilitiesByUser()` L153 catch branch | `reset()` (degrade to empty bindings) |
| **Logout** | `logout()` L388-391 | `reset()` |
| **Session restore failure** | `restoreAuth()` catch branch L306-327 | `reset()` |

**Implementation**: Centralize in `refreshCapabilitiesByUser` try/catch.

> **⚠️ 关键决策**：`refreshCapabilitiesByUser` 的 `useCallback` 依赖为 `[]`，函数体内无法访问当前 `user` React state（会读到初始闭包的 `null`）。因此 `isAdmin` 必须作为显式参数传入，不能在函数体内读取 `user?.is_admin`。

**Step 1**: 扩展 `refreshCapabilitiesByUser` 签名，新增 `isAdmin` 参数：

```typescript
// 当前签名:
const refreshCapabilitiesByUser = useCallback(
  async (userId: string, options?: { forceRefresh?: boolean }) => { ... },
  []
);

// 改为:
const refreshCapabilitiesByUser = useCallback(
  async (
    userId: string,
    options?: { forceRefresh?: boolean },
    context?: { isAdmin?: boolean },
  ) => { ... },
  []
);
```

**Step 2**: 在 success/failure 分支使用传入的 `isAdmin`：

```typescript
// refreshCapabilitiesByUser success branch (after L144):
AuthStorage.setCapabilitiesSnapshot(snapshot);
setCapabilities(snapshot.capabilities);
// New: sync dataScopeStore —— isAdmin 来自调用方显式传入
const adminFlag = context?.isAdmin ?? false;
useDataScopeStore.getState().initFromCapabilities(snapshot.capabilities, adminFlag);

// refreshCapabilitiesByUser failure branch (after L157):
AuthStorage.clearCapabilitiesSnapshot();
setCapabilities([]);
// New: reset dataScopeStore
useDataScopeStore.getState().reset();
```

**Step 3**: 所有调用点传入 `isAdmin` 真值：

```typescript
// login() L364 — response.data.user 是刚获取的最新用户对象:
triggerCapabilitiesRefresh(response.data.user.id, { forceRefresh: true }, {
  isAdmin: response.data.user.is_admin ?? false,
});

// restoreAuth() L261 — currentUser 是刚从 /auth/me 获取的:
triggerCapabilitiesRefresh(currentUser.id, { forceRefresh: true }, {
  isAdmin: currentUser.is_admin ?? false,
});

// refreshUser() L427 — currentUser 是刚刷新的:
await refreshCapabilitiesByUser(currentUser.id, { forceRefresh: true }, {
  isAdmin: currentUser.is_admin ?? false,
});
```

> `triggerCapabilitiesRefresh` 也需要同步扩展签名以透传 `context` 参数。

In `logout()` (after L391):

```typescript
useDataScopeStore.getState().reset();
```

#### [MODIFY] `frontend/src/utils/queryScope.ts` — unified scope key

**Decision**: Unify `buildQueryScopeKey()` and `getCurrentRequestScopeKey()` into a single `buildScopeKey()` function reading from `dataScopeStore`. Delete `getCurrentRequestScopeKey()`.

```typescript
import { AuthStorage } from '@/utils/AuthStorage';
import { useDataScopeStore } from '@/stores/dataScopeStore';

const ANONYMOUS_USER_SCOPE = 'user:anonymous';

const normalizeUserScope = (userId: string | null | undefined): string => {
  const normalizedUserId = userId?.trim() ?? '';
  return normalizedUserId !== '' ? `user:${normalizedUserId}` : ANONYMOUS_USER_SCOPE;
};

/**
 * Unified scope key generator.
 * Used by both React Query keys and API memory cache keys.
 */
export const buildScopeKey = (): string => {
  const currentUser = AuthStorage.getCurrentUser();
  const { bindingTypes, isAdmin } = useDataScopeStore.getState();

  let scopeToken: string;
  if (isAdmin) {
    scopeToken = 'scope:admin';
  } else if (bindingTypes.length > 0) {
    scopeToken = `scope:${[...bindingTypes].sort().join(',')}`;
  } else {
    scopeToken = 'scope:none';
  }

  return `${normalizeUserScope(currentUser?.id)}|${scopeToken}`;
};

// Compat aliases, to be removed after full migration
export const buildQueryScopeKey = buildScopeKey;
export const getCurrentRequestScopeKey = buildScopeKey;
```

Also update `client.ts` L17 import from `getCurrentRequestScopeKey` to `buildScopeKey` to ensure API memory cache and React Query use the same scope token.

### 验证

```bash
cd frontend
pnpm test -- --run src/stores/__tests__/dataScopeStore.test.ts
pnpm test -- --run src/api/__tests__/client.test.ts
pnpm type-check
pnpm lint
```

### 兼容性保证
- 旧 `perspective.ts` / `useRoutePerspective()` 仍保留，但不再被 `client.ts` 使用
- 旧 `/owner/*` `/manager/*` 路由仍能工作（只是 header 逻辑变了来源）
- 双绑定用户不再发 `X-Perspective` → 后端子任务 1 支持并集查询

---

## 子任务 3：前端路由统一 + 菜单扁平化 + 废弃代码清理

### 目标
消除 `/owner/*` 和 `/manager/*` 路由前缀，统一为扁平路由。菜单按 RBAC 控制显示。删除所有废弃的 perspective 相关代码。

### 前置条件
子任务 2 完成（前端已用 dataScopeStore 代替 URL perspective 推断）。

### 3A：路由统一 + 菜单改造（~15 文件）

#### [MODIFY] `frontend/src/constants/routes.ts`

删除 `OWNER_ROUTES` 和 `MANAGER_ROUTES` 常量（L107-131）。

`ROUTE_CONFIG` 中删除 `/owner` 和 `/manager` 两个分组（L164-209），统一使用现有的 `/assets`、`/project`、`/contract-groups` 等路由。

#### [MODIFY] `frontend/src/config/menuConfig.tsx`

```typescript
// 当前：/owner (业主视角) 和 /manager (经营视角) 两个分组
// 改为：按功能扁平展示

export const MENU_ITEMS: MenuProps['items'] = [
  { key: '/dashboard', icon: <DashboardOutlined />, label: '数据看板' },
  {
    key: 'asset-management',
    icon: <HomeOutlined />,
    label: '资产管理',
    children: [
      { key: '/assets/list', icon: <UnorderedListOutlined />, label: '资产列表' },
      { key: '/project', icon: <AppstoreOutlined />, label: '项目管理' },
      { key: '/ownership', icon: <IdcardOutlined />, label: '权属方管理' },
    ],
  },
  {
    key: 'contract-management',
    icon: <FileTextOutlined />,
    label: '合同管理',
    children: [
      { key: '/contract-groups', icon: <FileTextOutlined />, label: '合同组列表' },
      { key: '/property-certificates', icon: <FileTextOutlined />, label: '产权证管理' },
    ],
  },
  // system 保持不变
  ...
];
```

`getSelectedKeys` 和 `getOpenKeys` 删除所有 `/owner/*` `/manager/*` 分支。

#### [MODIFY] `frontend/src/routes/AppRoutes.tsx`

- Delete `/owner/*` and `/manager/*` prefixed route definitions
- Add old route 301 redirects: `/owner/assets` -> `/assets/list`, `/manager/projects` -> `/project`, etc.
- **Replace `LegacyRouteRedirect` with `CanonicalEntryRedirect`** (see below)
- Delete `PerspectiveResolutionPage` references

#### Canonical entry dispatch replacement (final decision)

**Problem**: `LegacyRouteRedirect` is not just a prefix redirector. It also serves as a capability-aware dispatcher for canonical entries (`/assets`, `/assets/list`, `/contract-groups`, `/project`, `/property-certificates`), using `resolveLegacyPerspectiveTarget()` to decide which perspective-prefixed route to jump to. Deleting it without replacement loses this dispatch logic.

**Decision**: Replace with `CanonicalEntryRedirect` - a much simpler component for the flat-route world:

```typescript
// [NEW] frontend/src/routes/CanonicalEntryRedirect.tsx
import React from 'react';
import { Navigate } from 'react-router-dom';
import { Spin } from 'antd';
import { useAuth } from '@/contexts/AuthContext';
import { useCapabilities } from '@/hooks/useCapabilities';
import { useDataScopeStore } from '@/stores/dataScopeStore';
import { BASE_PATHS } from '@/constants/routes';
import type { AuthzAction, ResourceType } from '@/types/capability';

interface CanonicalEntryRedirectProps {
  /** Target flat page path, e.g. '/assets/list' */
  targetPath: string;
  /** RBAC resource required for this page */
  resource: ResourceType;
  /** RBAC action required — defaults to 'read'; entry pages typically need read/list */
  action?: AuthzAction;
}

/**
 * Simplified capability-aware entry dispatcher.
 * Replaces LegacyRouteRedirect for the flat-route world.
 *
 * Behavior:
 * 1. Capabilities still loading -> show spinner
 * 2. User has capability for resource + action -> Navigate to targetPath
 * 3. User lacks capability -> Navigate to dashboard
 *
 * Key difference from LegacyRouteRedirect:
 * - No perspective-based /owner/* or /manager/* URL selection
 * - In flat routes, check "can user perform this action on this resource"
 */
const CanonicalEntryRedirect: React.FC<CanonicalEntryRedirectProps> = ({
  targetPath,
  resource,
  action = 'read',
}) => {
  const { capabilitiesLoading, error } = useAuth();
  const { initialized } = useDataScopeStore();
  const { canPerform } = useCapabilities();

  if (capabilitiesLoading || !initialized) {
    return (
      <div>
        <Spin size="small" /> Loading...
      </div>
    );
  }

  if (error != null) {
    return <Navigate to={BASE_PATHS.DASHBOARD} replace />;
  }

  if (!canPerform(action, resource)) {
    return <Navigate to={BASE_PATHS.DASHBOARD} replace />;
  }

  return <Navigate to={targetPath} replace />;
};

export default CanonicalEntryRedirect;
```

**Usage in AppRoutes** (replacing LegacyRouteRedirect calls):

```typescript
// Before (uses LegacyRouteRedirect with perspective dispatch):
{ path: BASE_PATHS.ASSETS, element: () => <LegacyRouteRedirect legacyPath={BASE_PATHS.ASSETS} /> },
{ path: ASSET_ROUTES.LIST, element: () => <LegacyRouteRedirect legacyPath={ASSET_ROUTES.LIST} /> },

// After (uses CanonicalEntryRedirect, no perspective dispatch):
{ path: BASE_PATHS.ASSETS, element: () => <CanonicalEntryRedirect targetPath={ASSET_ROUTES.LIST} resource="asset" /> },
{ path: ASSET_ROUTES.LIST, element: assetListPage },  // Direct render, no redirect
{ path: CONTRACT_GROUP_ROUTES.LIST, element: contractGroupListPage },
{ path: PROJECT_ROUTES.LIST, element: projectManagementPage },
{ path: PROPERTY_CERTIFICATE_ROUTES.LIST, element: propertyCertificateListPage },
```

**Behavior comparison**:

| Scenario | Old LegacyRouteRedirect | New CanonicalEntryRedirect |
|----------|------------------------|---------------------------|
| User has capability | Jump to `/owner/*` or `/manager/*` based on perspective | Stay on flat route |
| User lacks capability | Jump to dashboard or show PerspectiveResolutionPage | Jump to dashboard |
| No available resource | Show PerspectiveResolutionPage | Jump to dashboard |

#### [MODIFY] `frontend/src/components/Layout/AppSidebar.tsx`

Consume unified menuConfig, no longer split by perspective.

### 3B: Page component adaptation (~12 files)

Pages currently using `useRoutePerspective()` need to switch to `dataScopeStore`:

| File | Current usage | Change to |
|------|--------------|-----------|
| `hooks/useAnalytics.ts` | `useRoutePerspective()` -> `enabled: isPerspectiveRoute` | Read from store, `enabled: initialized` |
| `hooks/useAssetAnalytics.ts` | `useRoutePerspective()` | Same as above |
| `hooks/useAssets.ts` | `useRoutePerspective()` | Same as above |
| `hooks/useProject.ts` | `useRoutePerspective()` | Same as above |
| `pages/Dashboard/DashboardPage.tsx` | Perspective selection entry UI | Remove perspective entry, show stats directly |
| `pages/Assets/AssetListPage.tsx` | `useRoutePerspective()` | store |
| `pages/Assets/AssetDetailPage.tsx` | perspective header | store |
| `pages/Assets/AssetCreatePage.tsx` | perspective header | store |
| `pages/Project/ProjectDetailPage.tsx` | `useRoutePerspective()` | store |
| `pages/Customer/CustomerDetailPage.tsx` | `useRoutePerspective()` | store |
| `pages/Search/GlobalSearchPage.tsx` | `useRoutePerspective()` | store |
| `components/Project/ProjectList.tsx` | perspective | store |
| `components/System/CapabilityGuard.tsx` | perspective logic | store |

### 3C: Deprecated file deletion + reference cleanup (~15 files)

#### Delete files

| File | Lines | Reason |
|------|-------|--------|
| `frontend/src/routes/perspective.ts` | 46 | URL perspective parsing no longer needed |
| `frontend/src/routes/perspectiveResolution.ts` | 369 | Perspective restore/switch/routing logic no longer needed |
| `frontend/src/routes/PerspectiveResolutionPage.tsx` | 51 | Perspective selection UI no longer needed |
| `frontend/src/routes/LegacyRouteRedirect.tsx` | 64 | Replaced by `CanonicalEntryRedirect` |
| `frontend/src/components/System/CurrentViewBanner.tsx` | ~50 | Perspective banner no longer needed |

> Info: These files were already deleted in prior cleanup: `ViewContext.tsx`, `GlobalViewSwitcher.tsx`, `viewSelectionStorage.ts`

#### New files

| File | Lines | Description |
|------|-------|-------------|
| `frontend/src/routes/CanonicalEntryRedirect.tsx` | ~55 | Simplified capability-aware entry dispatcher |

#### Delete test files

| File | Reason |
|------|--------|
| `frontend/src/routes/__tests__/perspective.test.ts` | Source deleted |
| `frontend/src/routes/__tests__/perspectiveResolution.test.tsx` | Source deleted |
| `frontend/src/routes/__tests__/AppRoutes.perspective-redirect.test.tsx` | Redirect logic simplified |
| `frontend/src/components/System/__tests__/CurrentViewBanner.test.tsx` | Source deleted |
| `frontend/src/constants/__tests__/routes.perspective-prefixes.test.ts` | Prefix routes deleted |
| `frontend/src/__tests__/app-view-provider.test.ts` | Perspective tests no longer needed |

#### New test files

| File | Description |
|------|-------------|
| `frontend/src/routes/__tests__/CanonicalEntryRedirect.test.tsx` | Test redirect behavior with/without capabilities |

#### Clean up references

Delete imports from all pages/hooks:
- `useRoutePerspective` / `getCurrentRoutePerspective` / `isPerspectiveRoute` / `getRoutePerspective`
- `useView` / `ViewContext`
- `PerspectiveResolutionPage` / `LegacyRouteRedirect`

### 验证

```bash
cd frontend
pnpm lint
pnpm type-check
pnpm test
pnpm build  # 确保无死引用
```

---

## 全量回归验证

所有 3 个子任务完成后：

```bash
make check  # lint + type-check + test + build + docs-lint
```

### 关键回归场景

| 场景 | 预期行为 |
|------|---------|
| 单绑定 owner 用户登录 | 自动看到 owner-scoped 数据，菜单按 RBAC 显示 |
| 单绑定 manager 用户登录 | 自动看到 manager-scoped 数据 |
| 双绑定用户登录 | 看到 owner + manager 并集数据 |
| 管理员登录 | 看到全部数据，不报"视角不可用" |
| 访问 /owner/assets（旧 URL） | 301 重定向到 /assets/list |
| 访问 /manager/projects（旧 URL） | 301 重定向到 /project |
| Dashboard 统计 | 根据绑定类型显示对应收入标签，无需选择视角 |

---

## 超出本次范围

| 发现 | 跟踪方式 |
|------|---------|
| 台账确认权限按收入归属方分离 | 另开需求讨论 |
| 承租模式台账独立 / 代理模式台账关联 | 另开需求讨论 |
| 集团汇总视图 | 已加入 §13 vNext |
| 模块附录缺 UserPartyBinding 等实体 | 整体补全，不在本任务范围 |
| 后端 `perspective` 变量/类型命名重构为 `data_scope` | 可选，作为后续代码清洁任务 |

---

## SSOT 同步清单

子任务完成后需同步更新：

| 文档 | 更新内容 |
|------|---------|
| `docs/requirements-specification.md` | REQ-AUTH-002 状态 🚧→✅，更新代码证据列表 |
| `docs/requirements-specification.md` | 追踪矩阵 REQ-AUTH-002 行恢复 ✅ |
| `docs/features/requirements-appendix-fields.md` | 如涉及字段变更则同步 |
| `CHANGELOG.md` | 每个子任务完成后追加条目 |
| 本方案文件 | 所有子任务完成后移入 `docs/archive/backend-plans/` |
