# 视角机制 → 数据范围自动注入方案复核报告

**时间**: 2026-04-04  
**对象**: `docs/plans/2026-04-03-perspective-to-data-scope-refactor.md`  
**结论**: 方案已经吸收上一轮大部分关键问题，整体接近可实施状态；但仍有 3 个实现级缺口，暂时还不能算完全“决策完备”。

---

## 复核摘要

相较上一轮，这份方案已经完成了几项关键收口：

- 明确 **不修改** `/auth/me/capabilities` 结构，前端从现有 `capabilities[].data_scope` 聚合绑定信息
- 明确拆分 `PerspectiveName` 与 `EffectivePerspective`，`all` 只保留在后端运行时 Context
- 将 `project` owner/all 过滤下沉到 `CRUDProject._apply_project_party_filter()` 统一入口，而不是只在 API 列表端点分叉
- 将前端 query scope 与 API memory cache scope 统一到同一套 `buildScopeKey()` 规则
- 为 flat route 世界补入 `CanonicalEntryRedirect`，不再直接删除 `LegacyRouteRedirect` 而无替代

这些修订已经把上一次最核心的结构性问题基本补齐。当前剩余问题主要集中在实现细节仍有不一致，尚未达到“实现者无需自行判断”的程度。

---

## 剩余问题

### P1. `dataScopeStore` 生命周期示例里的 `isAdmin` 来源仍可能读到陈旧状态

方案在 `AuthContext` 生命周期章节里要求把 `dataScopeStore` 的同步收口到 `refreshCapabilitiesByUser()`，这一点方向正确；但给出的示例实现仍然直接在该函数里读取 `user?.is_admin`：

```typescript
const isAdmin = user?.is_admin ?? false;
useDataScopeStore.getState().initFromCapabilities(snapshot.capabilities, isAdmin);
```

这和当前 `refreshCapabilitiesByUser(userId, options)` 的真实签名不匹配。该函数只拿到 `userId`，而不是最新的 `User` 快照；当前 `AuthContext` 里 `isAdmin` 也是在更后面由 `user?.is_admin` 计算得出。如果按文档直接实现，在以下场景里都有机会读到旧的 `user` 闭包值：

- 登录成功后首次拉取 capabilities
- 页面刷新后的 session restore
- 跨标签切换用户
- capabilities 强刷过程中用户状态尚未同步

建议把 `isAdmin` 作为显式参数传入 `refreshCapabilitiesByUser()`，或在拉 capabilities 前先获取并传入当前 `User` 真值，避免依赖 React state 闭包。

相关位置：

- 方案生命周期实现：`docs/plans/2026-04-03-perspective-to-data-scope-refactor.md:443-471`
- 当前能力刷新函数：`frontend/src/contexts/AuthContext.tsx:127-165`
- 当前 `isAdmin` 真值位置：`frontend/src/contexts/AuthContext.tsx:507`

### P1. `CanonicalEntryRedirect` 的权限判定仍然过粗，只检查资源存在，不检查动作

新方案为 canonical 入口补了 `CanonicalEntryRedirect`，替代 `LegacyRouteRedirect`，这是正确方向。但当前定义的判定条件是：

```typescript
const hasCapability = capabilities.some(cap => cap.resource === resource);
```

这只检查“有没有这个 resource 的 capability 项”，没有检查页面真正需要的动作语义。对于列表页和入口页，当前路由体系实际依赖的是 `read` 或 `list`，而不是“只要有任意 action 就能进”。如果后续出现“仅有 create、没有 read”的资源组合，按当前文档实现会先跳转进去，再由页面/路由层二次拒绝，入口分发就会和真正的权限门禁不一致。

这里建议把 `CanonicalEntryRedirectProps` 改为显式接收 `action + resource`，或者直接复用 `useCapabilities().canPerform(...)`。

相关位置：

- 方案组件设计：`docs/plans/2026-04-03-perspective-to-data-scope-refactor.md:611-655`
- 当前能力判定工具：`frontend/src/hooks/useCapabilities.ts:17-38`

### P2. 顶部目标态仍残留 `/projects` 复数路径，与当前全篇其余决策不一致

方案顶部目标态仍写着：

```text
前端统一路由 /assets, /projects, /contract-groups
```

但同一份方案后文所有真正的实施细节、重定向示例、现有常量体系，使用的都是 `/project` 单数路径。这是个文档一致性问题，不会阻塞设计本身，但会让实现者在真正改路由和写测试时多做一次判断。

建议直接统一为仓库当前主链使用的 `/project`，避免目标态和实施章节出现两套口径。

相关位置：

- 目标态：`docs/plans/2026-04-03-perspective-to-data-scope-refactor.md:31-42`
- 路由示例：`docs/plans/2026-04-03-perspective-to-data-scope-refactor.md:592-593`
- 当前路由常量：`frontend/src/constants/routes.ts`

---

## 复核结论

这份方案现在已经不是“结构性不可实施”状态了。上一轮指出的 6 个关键问题里，大部分已经被正确吸收，尤其是：

1. capabilities 契约已收口  
2. `all` 类型边界已收口  
3. `project` owner/all 统一过滤落点已收口  
4. scope key 统一规则已收口  
5. canonical 入口替代方案已补齐

当前剩余的是 2 个实现级问题和 1 个文档一致性问题。只要把这 3 处补掉，这份方案就可以进入 TDD 和实现阶段。

---

## 建议修订动作

1. 将 `refreshCapabilitiesByUser()` 所需的 `isAdmin` 改为显式输入，不要在示例里读取 `user?.is_admin` 闭包状态。
2. 将 `CanonicalEntryRedirect` 的 props 从 `resource` 扩展为 `resource + action`，或直接改为复用 `canPerform()`。
3. 将目标态中的 `/projects` 统一改成 `/project`，和后文实施细节保持一致。
