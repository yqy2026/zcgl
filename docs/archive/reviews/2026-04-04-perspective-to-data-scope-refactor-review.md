# 视角机制 → 数据范围自动注入方案复核报告

**时间**: 2026-04-04（二次复核更新）  
**对象**: `docs/plans/2026-04-03-perspective-to-data-scope-refactor.md`  
**结论**: 方案已达到决策完备状态，上一轮提出的 3 个问题均已被正确吸收。二次复核发现 3 个低优先级文档准确性问题，不阻塞实施。

---

## 复核摘要

相较上一轮，这份方案已经完成了几项关键收口：

- 明确 **不修改** `/auth/me/capabilities` 结构，前端从现有 `capabilities[].data_scope` 聚合绑定信息
- 明确拆分 `PerspectiveName` 与 `EffectivePerspective`，`all` 只保留在后端运行时 Context
- 将 `project` owner/all 过滤下沉到 `CRUDProject._apply_project_party_filter()` 统一入口，而不是只在 API 列表端点分叉
- 将前端 query scope 与 API memory cache scope 统一到同一套 `buildScopeKey()` 规则
- 为 flat route 世界补入 `CanonicalEntryRedirect`，不再直接删除 `LegacyRouteRedirect` 而无替代

这些修订已经把上一次最核心的结构性问题基本补齐。

---

## 上一轮问题处置（3/3 已修复）

### ✅ 原 P1. `dataScopeStore` 生命周期示例里的 `isAdmin` 来源仍可能读到陈旧状态

**状态**: 已在方案中修复。

方案第 459 行已明确：

> `isAdmin` 必须作为显式参数传入，不能在函数体内读取 `user?.is_admin`。

方案第 461-515 行完整描述了 3 步修复：
1. 扩展 `refreshCapabilitiesByUser` 签名加 `context?: { isAdmin?: boolean }`
2. success/failure 分支使用传入的 `context?.isAdmin ?? false`
3. 所有调用点（`login()`、`restoreAuth()`、`refreshUser()`）显式传入 `isAdmin` 真值

**验证**: 对照当前 `AuthContext.tsx`（L127-165），`refreshCapabilitiesByUser` 的 `useCallback` 依赖为 `[]`，函数体内确实无法访问最新 `user` state。方案的显式参数方案正确。

### ✅ 原 P1. `CanonicalEntryRedirect` 的权限判定仍然过粗，只检查资源存在，不检查动作

**状态**: 已在方案中修复。

方案第 658-708 行的 `CanonicalEntryRedirectProps` 已包含 `action?: AuthzAction` 属性（默认 `'read'`），第 701 行使用 `canPerform(action, resource)` 做完整的 action + resource 判定。

**验证**: 对照当前 `useCapabilities.ts`（L24-38），`canPerform` 内部调用 `evaluateCapability()` 进行完整的 capability 匹配，包含 action、resource、perspective。方案复用路径正确。

### ✅ 原 P2. 顶部目标态仍残留 `/projects` 复数路径

**状态**: 已在方案中修复。

方案第 41 行目标态已统一为 `/project` 单数路径，与全篇实施细节和当前 `routes.ts`（`PROJECT_ROUTES.LIST: '/project'`）一致。

---

## 二次复核新发现问题

### P3. `party_scope.py` 的 else 分支是隐式 fallback，新增 `all` 后需收紧

**严重级别**: 低（不阻塞实施，但建议实施时修正）

当前 `party_scope.py` L54-67：

```python
if perspective == "owner":
    return PartyFilter(filter_mode="owner", ...)

# else: 隐式 fallback 到 manager
return PartyFilter(filter_mode="manager", ...)
```

方案在此处新增 `perspective == "all"` 分支后，函数变成三分支：`all` → `owner` → 隐式 else（manager）。如果未来有非法 perspective 值传入，仍会静默走 manager 路径。

**建议**：实施时将 else 改为显式 `elif perspective == "manager"` + 末尾 `raise ValueError(f"Unsupported perspective: {perspective}")`，使非法值不会静默通过。

相关位置：`backend/src/services/party_scope.py:44-67`

### P3. `service.py` 方案注释描述的行号与实际含义不匹配

**严重级别**: 低（文档准确性问题）

方案写道 "L190-195 处 `_get_user_role_ids` 用法"，但实际 L190-195 是 `resolve_capability_perspectives` + `resource_requires_perspective` 过滤逻辑。`_get_user_role_ids` 调用在 L152。方案的改动逻辑本身正确（L152 改调 `_get_user_role_summary`，L190-195 加 admin 分支），但注释中"L190-195"的描述应改为"perspective resolution 逻辑"而非"_get_user_role_ids 用法"。

相关位置：`backend/src/services/authz/service.py:146-212`

### P3. `CRUDProject` 方案行号偏移较大

**严重级别**: 低（文档准确性问题）

方案中"All project read paths covered"表格引用的行号（`get()` L150-169、`get_multi()` L171-190、`search()` L213-262、`get_statistics()` L282-307）与当前代码偏移较大。`_apply_project_party_filter` 实际在 L71-81，`create()` 从 L83 开始。实现者应以方法名而非行号定位。

相关位置：`backend/src/crud/project.py:71-81`

---

## 复核结论

**方案已达到决策完备状态，可进入 TDD 实施阶段。**

上一轮指出的 3 个问题已全部被正确吸收：

1. ✅ `isAdmin` 显式参数传入 — 方案第 459-515 行已完整描述
2. ✅ `CanonicalEntryRedirect` 使用 `canPerform(action, resource)` — 方案第 658-708 行已修复
3. ✅ `/projects` 统一为 `/project` — 方案第 41 行已修正

二次复核发现的 3 个 P3 问题均为文档准确性问题，不影响设计决策的完备性：

1. `party_scope.py` 隐式 else fallback — 建议实施时收紧为显式分支
2. `service.py` 注释行号描述不准确 — 不影响改动逻辑
3. `CRUDProject` 行号偏移 — 实现者以方法名定位即可

---

## 建议下一步

1. 按方案子任务 1 → 2 → 3 顺序进入 TDD 实施
2. 实施 `party_scope.py` 时顺手收紧 else 分支为显式判断
3. 方案中的行号引用仅作参考，以方法名和函数签名为准
