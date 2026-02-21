# Phase 3 实施计划审阅报告

**审阅对象**: [Phase 3 实施计划](./2026-02-20-phase3-implementation-plan.md)  
**审阅日期**: 2026-02-20  
**审阅版本**: v1.11（二次审阅）  
**审阅方法**: 计划文档逐条交叉比对前端代码库（types/hooks/services/routes/contexts/store/components/Router 等 16 类文件）及后端模型/Schema/API 实际状态  
**前次审阅**: v1.10 首轮审阅发现 11 条问题（6 P0 / 4 P1 / 1 P2），v1.11 已修正其中 9 条

---

## 审阅结论

v1.11 有效修正了首轮审阅中 6 条 P0 阻断级问题中的 5 条（propertyCertificate 子接口归属、RentContract 主/子接口拆分、Gantt 依赖显式化、Router 目录冻结、isAdmin 导出、双数据源收口策略）。4 条 P1 中修正 3 条（PartySelector fetcher 架构、Ownership/Project 权限映射、Capabilities 存储策略定版）。文档工程层面也完成了版本历史精简。

**当前状态**：首轮 P0 阻断级问题已全部清除。剩余 **2 条新发现 + 3 条残余**问题，均为 Medium 或 Low 级别。

---

## 一、v1.10 → v1.11 修正验证结果

### 已修正（9/11）——逐条验证

| 首轮编号 | 问题 | v1.11 处理 | 验证结论 |
|---|---|---|---|
| P0-1 | `propertyCertificate.ts` 字段归属 | §4.1 改为 `PropertyOwner.organization_id`；P3a Exit 新增专项门禁；P3e 第 4 条显式标注 | ✅ 代码确认 `PropertyOwner.organization_id` 在 L55 |
| P0-2 | `RentContract` 主/子接口拆分 | §4.1 分拆为主接口（`ownership_id`）+ `RentContractAsset` 子接口（`management_entity`/`ownership_entity`） | ✅ 代码确认主接口 L77 `ownership_id`；子接口 L67-68 `ownership_entity`/`management_entity` |
| P0-3 | §3.1 统计偏差 | §3.1 增加注记"以子接口语义位置为准" | ✅ 注记准确 |
| P0-4 | `isAdmin` 不在 AuthContextType | §4.2 接口补充新增 `isAdmin: boolean`（`= user?.is_admin ?? false`）；§4.4.2 D2 冻结为 `AuthContext.isAdmin` | ✅ 来源链完整 |
| P0-5 | 双数据源冲突 | §4.1 usePermission 新增生命周期约束（P3d 代理壳/P3e 物理删除）；§4.2 新增 AuthService 直调清理要求；§4.4 P3d Exit 新增门禁 `AuthService.(hasPermission\|getLocalPermissions\|hasAnyPermission)` | ✅ grep 确认当前 3 处生产代码命中（均在 AuthContext.tsx L293/297/310），门禁可覆盖 |
| P0-6 | Router 目录死代码 | 改为 `[REVIEW/DEFER]`，明确"Phase 3 仅改主路由链"，不做功能改造 | ✅ 无矛盾残留 |
| P1-7 | PartySelector 全量加载 | 改为 `fetcher(query)` 可替换架构 + 三档阈值仅在降级模式生效 | ✅ 设计合理 |
| P1-9 | Ownership/Project 权限真空 | §4.4.1 资源映射矩阵新增 `ownership→party`、`project→project`；§4.4.2 D3 显式补齐；P3d Exit 新增浏览器验证 | ✅ 覆盖完整 |
| P1-10 | Capabilities 缓存策略未决 | §4.2 定版：AuthStorage 持久化 + 10min TTL + version 校验 + token refresh 强制重拉 | ✅ 决策明确 |

### 部分修正但仍有残余（1/11）

| 首轮编号 | 问题 | v1.11 处理 | 残余 |
|---|---|---|---|
| P1-8 | Gantt 依赖误导 | P3b 改为 `after p2c`，P3d 改为 `after p2d` | Gantt 中 P3a→P3b 串行依赖丢失（见 R-1） |

### 未修正（1/11）

| 首轮编号 | 问题 | v1.11 处理 | 状态 |
|---|---|---|---|
| P2-11 | 过度文档化 | §10 历史精简为单条 v1.11 摘要 | ✅ 已改善。但信息重复问题（X-Authz-Stale 4 处提及）未完全消除——降级为建议级 |

---

## 二、v1.11 残余问题

### [R-1] Gantt 图 P3a→P3b 串行依赖丢失（Low）

**现状**：Gantt 中 `P3b` 标注 `after p2c`（修正了首轮的 `after p3a`），但 P3b 的 Entry 门禁要求"P3a Exit + P2c Exit"。Gantt 图丢失了 P3a→P3b 的串行前置。

**影响**：当 P2c 先于 P3a 完成时（P2 内部进度超预期），Gantt 图暗示 P3b 可立即启动，但实际还需等 P3a Exit。

**修正建议**：Gantt 无法原生表达多前置依赖，建议在 P3b 行加注释 `%% also requires p3a`，或在 §0 注记中补充说明。

**严重程度**：Low——§5.1 Entry 门禁文字已明确双前置，Gantt 仅为辅助视图。

---

### [R-2] `rentContract.ts` 迁移范围不完整——仅覆盖 2/13 个含 `ownership_id` 的类型（Medium）

**现状**：§4.1 `[MODIFY] types/rentContract.ts` 仅列出：
- `RentContract` 主接口：deprecated `ownership_id`
- `RentContractAsset` 子接口：deprecated `management_entity`/`ownership_entity`

**但实际代码中 `ownership_id` 在该文件出现 11 处**，分布在 13 个不同类型/接口中：

| 类型 | 行号 | `ownership_id` 性质 |
|---|---|---|
| `RentContract` | L77 | required `string` |
| `RentLedger` | L110 | required `string` |
| `RentContractCreate` | L182 | required `string` |
| `RentContractUpdate` | L206 | optional `string` |
| `RentLedgerCreate` | L250 | required `string` |
| `OwnershipRentStatistics` | L293 | required `string`（含 `ownership_name`/`ownership_short_name`） |
| `RentStatisticsQuery` | L338 | `ownership_ids?: string[]` |
| `RentContractQueryParams` | L350 | optional `string` |
| `RentLedgerQueryParams` | L360 | optional `string` |
| `RentContractFormData.basicInfo` | L398 | required `string` |
| `RentContractSearchFilters` | L452 | optional `string` |
| `RentLedgerSearchFilters` | L460 | optional `string` |

**影响**：

- 执行者只会对 `RentContract` 和 `RentContractAsset` 做 deprecated + 新增字段，**遗漏 Create/Update/Query/FormData/Statistics 等 10+ 个类型**
- P3e Exit 门禁（`! grep -rEl "\bownership_id\b" frontend/src/types/ ...`）会因这些遗漏类型而失败
- `OwnershipRentStatistics` 尤其特殊——其 `ownership_name`/`ownership_short_name` 也需要迁移为 Party 名称

**修正建议**：§4.1 rentContract 部分增加一行总括说明：

> 文件内所有含 `ownership_id` 的类型（含 Create/Update/Query/FormData/Statistics/Filters，共 13 处）均需 deprecated + 新增 `owner_party_id`。`OwnershipRentStatistics` 额外需将 `ownership_name`/`ownership_short_name` 迁移为 `owner_party_name`。

---

## 三、v1.11 新引入的问题

### [N-1] `default_organization_id` 导致 P3e/§6.2 门禁假阳性（Medium）

**问题**：§6.2 旧字段零引用验证使用 `\borganization_id\b` 词边界 grep。但 `default_organization_id` 中包含完整的 `organization_id` 子串，`\b` 标记的词边界在 `default_` 和 `organization_id` 之间**不会触发**（因为 `_` 是 word character）。

等等——让我重新验证。`\b` 在 `default_organization_id` 中：`default_` → `o` 处没有词边界，所以 `\borganization_id\b` 不会匹配 `default_organization_id`。这里需要验证实际 grep 行为。

**实际验证**：

```
"default_organization_id" 中的 "organization_id" 部分：
- 前边界：`_` 和 `o` 之间 → _ 是 \w，o 是 \w → 不是词边界 → \b 不匹配
- 后边界：`d` 和字符串末尾 → \b 匹配
```

因此 `\borganization_id\b` **不会匹配** `default_organization_id`。门禁不存在假阳性。

**但**：`systemService.ts` L75 和 L85 有**裸** `organization_id`：

```typescript
organization_id?: string;           // L75 — getUsers 参数中的独立字段
{ organization_id: default_organization_id }  // L85 — 赋值语句
```

这两处是 `systemService` 将用户管理接口的 `default_organization_id` 前端参数转换为后端 `organization_id` 查询参数。**这些是合法的待迁移代码**。

| 文件 | 命中 | P3b Exit grep 覆盖？ |
|---|---|---|
| `services/systemService.ts` L75, L85 | 裸 `organization_id` | ✅ `services/` 目录在 P3b Exit grep 范围内 |

**但问题是**：`systemService.ts` **不在** P3b Exit grep 的 `--exclude` 列表中（仅排除 `*organizationService*` 和 `*ownershipService*`），所以这两行会被 P3b Exit 门禁捕获。

**实际影响**：这是**正确的预期行为**——`systemService.ts` 的 `organization_id` 确实需要迁移到 Party 体系。但 §4.2 服务层变更清单中**遗漏了 `systemService.ts`**——没有明确说明这个文件的 `organization_id → party_id` 迁移。

**修正建议**：§4.2 增加 `[MODIFY] services/systemService.ts`：

> - `getUsers()` 参数中的 `organization_id` → 迁移为 Party 关联查询
> - `CreateUserData`/`UpdateUserData` 中的 `default_organization_id` → 迁移为 `default_party_id`（需与后端 User 模型对齐）

---

### [N-2] `AuthContext.tsx` 中 3 处 `AuthService.hasPermission` 直调与 v1.11 capabilities 存储策略的时序矛盾（Medium）

**现状**：v1.11 §4.2 定义 `AuthContextType` 新增 `capabilities`，且 P3d Exit 门禁要求清除所有 `AuthService.(hasPermission|getLocalPermissions|hasAnyPermission)` 直调。

**当前代码**（`AuthContext.tsx`）：

```typescript
// L293: hasPermission callback
const hasPermission = useCallback((resource: string, action: string) => {
  return AuthService.hasPermission(resource, action);
}, []);

// L297: hasAnyPermission callback
const hasAnyPermission = useCallback((permissions: Array<{resource: string; action: string}>) => {
  return AuthService.hasAnyPermission(permissions);
}, []);

// L310: getLocalPermissions for context value
permissions: AuthService.getLocalPermissions() as Permission[],
```

**矛盾**：`AuthContext` 自身向外暴露的 `hasPermission`/`hasAnyPermission` 方法是**代理到 `AuthService`** 的。如果 P3d 要消除 `AuthService` 直调，就意味着 `AuthContext.hasPermission` 和 `AuthContext.hasAnyPermission` 的**实现**必须同时迁移到基于 `capabilities` 的判定。

但计划§4.2 仅说"新增 `capabilities`/`capabilitiesLoading`/`refreshCapabilities`/`isAdmin`"，**没有说改造或废弃 `hasPermission`/`hasAnyPermission`**。

**两种可能路径**：

1. P3d 将 `AuthContext.hasPermission` 实现从 `AuthService.hasPermission()` 改为基于 `capabilities` 的 `canPerform()`——但这改变了 `hasPermission` 的语义（旧的基于角色字符串匹配，新的基于 ABAC 能力清单），可能影响所有 `useAuth().hasPermission()` 调用方
2. P3d 废弃 `AuthContext.hasPermission`/`hasAnyPermission`，调用方统一改用 `useCapabilities().canPerform()`——但计划没有列出所有 `useAuth().hasPermission()` 调用方的迁移

**影响**：P3d 执行者无法判断应选路径 1 还是路径 2，且两者的改造范围差异很大。

**修正建议**：§4.2 明确以下决策之一：

- **路径 1**：P3d 将 `AuthContext.hasPermission()` 内部实现改为代理 `canPerform()`（含动作词映射），保留接口兼容——风险低但有映射成本
- **路径 2（推荐）**：P3d 将 `AuthContext.hasPermission`/`hasAnyPermission` 标记 `@deprecated`，不改实现；调用方逐步迁移到 `useCapabilities().canPerform()`；P3e 物理移除——与 `usePermission` 废弃路径一致

无论哪条路径，需补充 `useAuth().hasPermission()` 的调用方搜索与迁移清单。

---

### [N-3] 插入位置使用脆弱行号引用（Low）

**现状**：§4.2 `AuthContext.tsx` 插入位置使用"第 136、170 行附近"、"第 219 行附近"。

**实际偏差**：

| 计划行号 | 描述 | 实际位置 | 偏差 |
|---|---|---|---|
| L136 | `persistAuthDataSafely(...)` 第一次调用 | L137 | ~1 行 |
| L170 | `persistAuthDataSafely(...)` 第二次调用 | L171 | ~1 行 |
| L219 | `login()` 成功设置用户后 | L223 `setUser(...)` | ~4 行 |

**影响**：执行者可能在错误位置插入代码。随着其他 PR 合入，行号会进一步漂移。

**修正建议**：改用描述性锚点，例如：
- "在 `restoreAuth()` 的 stored-user 恢复分支中，`persistAuthDataSafely(currentUser, permissions, authPersistence)` 调用之后"
- "在 `login()` 中 `setUser(response.data.user)` 调用之后"

---

## 四、修正优先级总览（v1.11 二次审阅）

| 编号 | 级别 | 问题 | 修正动作 |
|---|---|---|---|
| R-2 | 🟡 Medium | `rentContract.ts` 迁移仅覆盖 2/13 个类型 | §4.1 增加总括说明覆盖全部 13 个含 `ownership_id` 的类型 |
| N-1 | 🟡 Medium | `systemService.ts` 的 `organization_id` 迁移遗漏 | §4.2 新增 `[MODIFY] services/systemService.ts` 条目 |
| N-2 | 🟡 Medium | `AuthContext.hasPermission` 迁移路径未决 | §4.2 明确废弃/改造路径 + 调用方迁移清单 |
| R-1 | 🔵 Low | Gantt P3a→P3b 依赖丢失 | Gantt 加注释或在 §0 注记补充 |
| N-3 | 🔵 Low | 插入位置用脆弱行号 | 改用描述性锚点 |

**总体评价**：v1.11 已消除所有阻断级问题。剩余 3 条 Medium 问题中，R-2 和 N-1 影响迁移完整性（可能导致门禁失败），N-2 影响执行决策清晰度。建议在实施前完成这三项补充。

---

## 五、验证方法说明

本报告所有事实性结论均基于以下验证：

1. **前端代码直接读取**：`frontend/src/types/*.ts`（重点 `rentContract.ts` 全文 543 行、`propertyCertificate.ts`、`auth.ts`）、`hooks/usePermission.tsx`、`contexts/AuthContext.tsx`、`services/authService.ts`、`services/systemService.ts`、`routes/AppRoutes.tsx`、`App.tsx`、`constants/routes.ts`、`store/useAssetStore.ts`、`components/Router/*.tsx`
2. **Grep 验证**：`\borganization_id\b`（7 命中）、`\bownership_id\b` in rentContract.ts（11 命中）、`default_organization_id`（20 命中）、`AuthService\.(hasPermission|getLocalPermissions|hasAnyPermission)`（6 命中，3 生产 + 3 测试）
3. **后端代码交叉比对**：`backend/src/api/v1/party.py`（确认无 search 参数）、`backend/src/schemas/authz.py`（capabilities 结构）
4. **上游文档比对**：Phase 2 实施计划 v1.12、Party-Role 架构设计 v3.9
