# Phase 3 实施计划 v1.40 — 完整交叉审阅报告（第三轮）

**审阅对象**: `docs/plans/2026-02-20-phase3-implementation-plan.md` (v1.40)  
**审阅日期**: 2026-02-22  
**审阅方法**: 全文逐节交叉验证（计划文本 × 实际代码库 × Phase 2 计划 × 架构设计文档 v3.9）  
**审阅结论**: 计划整体架构清晰、门禁体系严密，但存在 **6 个阻断级 / 15 个严重级 / 18 个中等级 / 12 个低级** 问题，需在执行前修正。

---

## 目录

1. [阻断级问题（P0 — 必须修复后方可执行）](#1-阻断级问题p0--必须修复后方可执行)
2. [严重级问题（P1 — 不修复将在执行中产生重大偏差）](#2-严重级问题p1--不修复将在执行中产生重大偏差)
3. [中等级问题（P2 — 可能导致返工或门禁误判）](#3-中等级问题p2--可能导致返工或门禁误判)
4. [低级问题（P3 — 建议修正，不影响主链执行）](#4-低级问题p3--建议修正不影响主链执行)
5. [亮点与认可](#5-亮点与认可)
6. [总结与建议](#6-总结与建议)

---

## 1. 阻断级问题（P0 — 必须修复后方可执行）

### P0-1：后端 `party_relations[]` 契约不存在，计划核心假设落空

**位置**: §1 Phase 2-patch 工单追踪 / §4.2 `projectService.ts` / §5.1 P3b Entry

**问题**: 计划在多处假设后端将交付 `project.party_relations[]` 字段（P3b Entry 硬门禁），并要求后端在 `project_to_response()` 中完成 `ownership_relations[] -> party_relations[]` 转换。然而经代码库验证：

- [backend/src/schemas/project.py](backend/src/schemas/project.py) **不存在** `party_relations` 字段定义
- [backend/src/services/project/service.py](backend/src/services/project/service.py) **不存在** `party_relations` 相关代码
- Phase 2 计划 ([docs/plans/2026-02-19-phase2-implementation-plan.md](docs/plans/2026-02-19-phase2-implementation-plan.md)) 完全未提及 `party_relations` 的交付
- `ownership_relations` 仅在 Phase 2 计划中出现一次（数据迁移上下文，非 API 交付）

**影响**: P3b、P3c、P3e 的项目模块改造全部依赖此字段。若后端无此交付计划，Phase 3 项目模块改造将完全阻塞。

**建议**:
1. 在 Phase 2-patch 中显式新增此后端任务并拆分 ticket
2. 明确后端 `ProjectResponse` schema 增加 `party_relations` 字段的具体数据结构与实现方案
3. 或降级方案：Phase 3 项目模块暂不消费 `party_relations`，仅迁移顶层 `manager_party_id`

---

### P0-2：`/api/v1/parties?search=` 端点不存在且 Phase 2 未规划

**位置**: §4.2 / §5.1 P3b Entry 硬门禁

**问题**: 计划在 P3b 设置了 `/api/v1/parties?search=` 硬门禁。但实际后端 `GET /parties`（[backend/src/api/v1/party.py#L28](backend/src/api/v1/party.py)）仅支持 `skip`/`limit`/`party_type`/`status` 四个查询参数，**无 `search` 参数**。Phase 2 计划也完全未提及此端点增强。

后端签名实际为：
```python
async def list_parties(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    party_type: str | None = Query(None),
    status: str | None = Query(None),
    ...
)
```

**影响**: `PartySelector` 组件依赖此 API，P3b 无法启动。

**建议**:
1. 立即在 Phase 2-patch 工单中新增此后端任务，明确实现 `search` 模糊查询（建议基于 `name` + `code` ILIKE）
2. 计划 §1 的 Phase 2-patch 表已列出此项，但需确认后端团队已接收并排期
3. 同时补齐分页信封 `{items,total,skip,limit}` 响应格式（当前返回裸 `list[PartyResponse]`）

---

### P0-3：CORS `expose_headers` 未配置，`request_id` 可观测性前提不满足

**位置**: §1 Phase 2-patch / §4.5 / §5.1 P3d Entry

**问题**: 计划要求 `backend/src/main.py` 配置 `expose_headers` 暴露 `X-Request-ID`/`Request-ID`，作为 P3d Entry 门禁。实际验证：`main.py` 当前 **无 `expose_headers` 配置**。Phase 2 计划也未提及此项。

**影响**: P3d 静默 refresh 的诊断日志（`request_id` 来源）将始终降级为 `body` 或 `local`，`request_id_source` 契约无法按设计执行。

**建议**:
1. 确认此补丁已纳入 Phase 2-patch 并指定后端责任人
2. 若优先级不足以在 P3d 前完成，将 P3d Entry 改为"登记降级模式"而非硬门禁

---

### P0-4：`ownership_relations=[]` 硬编码位置描述错误

**位置**: §1 Phase 2-patch / §4.2 `projectService.ts`

**问题**: 计划多处提到"修复 `project_to_response()` 中 `ownership_relations=[]` 硬编码"。但实际硬编码位于 [backend/src/schemas/project.py](backend/src/schemas/project.py) 的 `ProjectResponse.coerce_project_model` Pydantic model validator（L173），不在 `project_to_response()` 方法内。

`project_to_response()` 实际实现（[backend/src/services/project/service.py#L41](backend/src/services/project/service.py)）仅做：
```python
data = {attr.key: getattr(project, attr.key) for attr in sa_inspect(project).mapper.column_attrs}
return ProjectResponse.model_validate(data)
```
真正的空数组 fallback 在 Pydantic model validator 中：
```python
data["ownership_relations"] = [] if rel_value is no_value else rel_value  # L173
data["ownership_relations"] = []  # except block, L175
```

**影响**: 后端修复时将定位到错误位置，浪费调试时间。

**建议**: 修正描述为"修复 `ProjectResponse.coerce_project_model()` model validator 中的 `ownership_relations=[]` 默认赋值"，并标注文件路径 `backend/src/schemas/project.py:173`。

---

### P0-5：`ownership_id` 主链影响文件数统计正确但测试链严重低估

**位置**: §3.1 旧字段引用统计表

**问题**: 计划声称 `ownership_id` 影响 "25（主链）+1（test-utils）" 文件。实际验证：

- 排除 `__tests__/test/test-utils/*.test.*/*.spec.*` 后：**25 文件**（主链）✓ 此数字正确
- 含测试目录后总计：**33 文件**（与架构设计文档 §3.1 的 "33 文件替换" 吻合）
- `+1（test-utils）` 严重偏低——实际测试链包含 `projectFactory.ts`（test-utils）+ `AssetSearch.test.tsx`、`ContractDetailInfoV2.test.tsx`、`RentStatisticsPage.test.tsx`、`assetService.test.ts`、`projectService.test.ts`、`RentContractForm.test.tsx`、`assetCalculations.test.ts` 等 **7+ 测试文件**

**影响**: 测试迁移工作量被严重低估（7× 差距），P3c/P3e 阶段可能因测试修改量不足导致回归失败。

**建议**: 修正为 "25（主链）+8（test/test-utils/mocks）"或按完整计数标注。同时 `ownership_entity` 的统计也需校验——计划称 "17+1+1"，实际粗略 grep 约 25 文件，差异显著，需重新按主链/测试链拆分。

---

### P0-6：`assetService.ts` 变更清单声称包含旧字段，但文件实际无命中

**位置**: §4.2 `[MODIFY] services/assetService.ts + services/asset/*.ts`

**问题**: 计划声称 `assetService.ts` 的表格中包含"请求参数：`organization_id`→`manager_party_id`；`ownership_id`→`owner_party_id`"。但实际 `frontend/src/services/assetService.ts` **不包含** `organization_id`、`ownership_id`、`management_entity` 或 `ownership_entity` 的直接引用——这些都位于子模块 `services/asset/types.ts` 和 `services/asset/assetDictionaryService.ts`。

主服务文件仅有委托方法如 `getOwnershipEntities()` → 调用子服务，无直接字段映射。

**影响**: 执行者在 `assetService.ts` 中找不到声称的旧字段，会混淆改造范围并怀疑门禁完整性。

**建议**: 将变更清单拆分明确：
- `assetService.ts`：无直接旧字段，仅需审计委托调用链中的方法名（如 `getOwnershipEntities()`）
- `asset/types.ts`：`AssetSearchFilters.ownership_id`、`AssetDistributionStats.by_ownership_entity`/`by_ownership_status`、`OccupancyRateStats.by_ownership_entity`、`AssetStats.byOwnership` 等需迁移
- `asset/assetDictionaryService.ts`：`getOwnershipEntitiesFromDict()` 和 `getManagementEntitiesFromDict()` 的字典键 `'ownership_entity'`/`'management_entity'` 需评估是否为后端字典 `dict_type` 标识

---

## 2. 严重级问题（P1 — 不修复将在执行中产生重大偏差）

### P1-1：`types/rentContract.ts` 迁移位点列表需逐行锚定

**位置**: §4.1 `[MODIFY] types/rentContract.ts`

**问题**: 计划声称"共 12 处"。实际验证 `ownership_id` 出现 **11 次**（L77/110/182/206/250/293/338/350/398/452/460），`ownership_ids` 出现 **1 次**（L326），合计 12 处 ✓。但计划列出的类型清单（`RentContract`、`RentLedger`、`RentContractCreate` 等约 12 个类型名）与 12 个位点的对应关系未一一验证。

**建议**: 在计划或执行记录中建立"位点-类型名"映射表，确保每处 `ownership_id/ownership_ids` 命中都被覆盖。

---

### P1-2：`services/asset/types.ts` 的间接旧语义字段未纳入变更清单

**位置**: §4.2 变更清单

**问题**: [frontend/src/services/asset/types.ts](frontend/src/services/asset/types.ts) 包含多个间接旧语义字段名：

| 字段 | 接口 | 语义 |
|------|------|------|
| `byOwnership` | `AssetStats` | 统计维度 |
| `by_ownership_entity` | `OccupancyRateStats` | 入住率分布维度 |
| `by_ownership_status` | `AssetDistributionStats` | 分布维度 |
| `by_ownership_entity` | `AssetDistributionStats` | 分布维度 |
| `ownership_id` | `AssetSearchFilters` | 搜索过滤 |

计划 §4.2 仅在"asset/types.ts"行提到 `ownership_id/ownership_entity → owner_party_id`，未覆盖上述统计维度字段名的语义迁移。

**影响**: 统计接口字段名若不迁移，图表组件将在 P3c 改造时出现数据断层。

**建议**: 将 `services/asset/types.ts` 的统计维度字段迁移纳入 P3b 或 P3c 变更清单，明确后端统计接口是否同步改名。

---

### P1-3：`AuthContext` 当前无 `capabilities`/`isAdmin`/`capabilitiesLoading` 字段，改造量远超"修改"

**位置**: §4.2 `AuthContext.tsx` 改造描述

**问题**: 计划详细描述了 `AuthContextType` 需新增 `capabilities`/`capabilitiesLoading`/`isAdmin`/`refreshCapabilities` 四个字段和对应逻辑。但当前 `AuthContext.tsx` 的 `AuthContextType` 接口（[L11-24](frontend/src/contexts/AuthContext.tsx)）为：
```typescript
user: User | null;
permissions: Permission[];
isAuthenticated: boolean;
initializing: boolean;
login/logout/refreshUser/hasPermission/hasAnyPermission/clearError/loading/error
```
完全不含 `capabilities`、`isAdmin`、`capabilitiesLoading`。这意味着 P3d 改造量接近"重构"而非简单"修改"——需要新增 4 个状态字段、修改 `restoreAuth()`/`login()`/`refreshUser()` 三个异步流程、新增 `capabilityService` 集成。

**影响**: P3d 工作量评估偏低，`AuthContext` 是全局依赖项，改动影响面极大。

**建议**: 
1. 在 P3d 工作量预估中将 `AuthContext` 改造列为核心风险项
2. 考虑在 P3b 提前植入 `capabilities` 骨架（空数组 + loading 状态），降低 P3d 单次变更风险

---

### P1-4：`AuthContext` 无 `AbortController`，引入建议需重构支撑

**位置**: §4.2 `v1.24 竞态补充`

**问题**: 计划建议"在开发模式使用 `AbortController` 取消 Strict Mode 双调用的过期请求"。但当前 `AuthContext` 的 `restoreAuth()` 使用 `isMounted` boolean 模式清理（[L73](frontend/src/contexts/AuthContext.tsx)、[L198](frontend/src/contexts/AuthContext.tsx)），无 `AbortController`。如要引入，需重构整个异步流程的 cleanup 模式。

**影响**: 若执行者仅在 capabilities 拉取处局部添加 `AbortController` 而不重构整体，将产生混合式竞态管理代码（一半 `isMounted`、一半 `AbortController`）。

**建议**: 将 `AbortController` 明确为"建议但非强制"，或说明需将整个 `restoreAuth` 的 `isMounted` 模式一并替换为 `AbortController.signal` 模式。

---

### P1-5：`PermissionGuard` 导出 7 个预构建 Guard，消费者清单未盘点

**位置**: §4.4 / §4.6 / §5.1 P3e

**问题**: [frontend/src/components/System/PermissionGuard.tsx](frontend/src/components/System/PermissionGuard.tsx) 导出了：
- `UserManagementGuard`
- `RoleManagementGuard`
- `OrganizationManagementGuard`
- `SystemLogsGuard`
- `AssetManagementGuard`
- `AssetCreateGuard`
- `RentalManagementGuard`

共 7 个预构建命名导出 Guard。计划 §4.6 P3e 要求完成 `PermissionGuard` 依赖链处置，但未列出这 7 个导出的消费位点。

**影响**: 若在 P3d 代理到 `CapabilityGuard` 时未保留这些命名导出，或在 P3e 删除时未迁移所有消费者，将产生编译断裂。

**建议**: 在 §4.4 或 §4.6 中增加 `PermissionGuard` 导出消费盘点命令：
```bash
grep -rEn "UserManagementGuard|RoleManagementGuard|OrganizationManagementGuard|SystemLogsGuard|AssetManagementGuard|AssetCreateGuard|RentalManagementGuard" frontend/src/ --include="*.ts" --include="*.tsx" --exclude="PermissionGuard.tsx"
```

---

### P1-6：`AuthGuard` 使用 `useAuth()` 而非 `usePermission`，D5 与 P3d Exit 门禁矛盾

**位置**: §4.4.2 D5 / §5.1 P3d Exit

**问题**: 
- D5 声称"Phase 3 不做功能改造；仅标记 `@deprecated`"
- 但 [AuthGuard.tsx](frontend/src/components/Auth/AuthGuard.tsx) 从 `useAuth()` 解构 `{ hasPermission, hasAnyPermission }`
- P3e 要求删除 `AuthContext.hasPermission/hasAnyPermission`
- P3d Exit 门禁明确要求 `AuthGuard` 无 `useAuth().hasPermission` 残留

D5("不做功能改造") 与 P3d Exit 门禁("无 `hasPermission` 残留") 直接矛盾——不改造就无法满足门禁。

**建议**: 修正 D5 为：P3d 必须修改 `AuthGuard` 使其不依赖 `hasPermission`（迁移到 `useCapabilities` 代理或直接标记 `@deprecated` + 内部重定向到 capabilities 壳）。

---

### P1-7：P3d Entry `ROUTE_CONFIG` 门禁无法检测 import 引用

**位置**: §5.1 P3d Entry

**问题**: 门禁命令检测 `ROUTE_CONFIG` 在 `constants/routes.ts` 之外的文件中出现。但如果 `AppRoutes.tsx` 通过解构 import（如 `import { ROUTE_PATHS } from '@/constants/routes'`）间接依赖 `ROUTE_CONFIG` 的派生值（如 `ROUTE_PATHS` 来源于 `ROUTE_CONFIG.map()`），门禁将漏报。

**建议**: 补充 import 链检测：
```bash
grep -rEn "from.*constants/routes" frontend/src/ --include="*.ts" --include="*.tsx" \
  --exclude-dir="constants" --exclude-dir="__tests__" | head -20
```
确认 `ROUTE_CONFIG` 的所有派生导出不被运行时依赖。

---

### P1-8：`statisticsService.ts` 存在 `ownership` 语义链路但计划声称"无命中"

**位置**: §4.2 `[REVIEW] services/statisticsService.ts`

**问题**: 计划声称"该文件当前未命中旧主体字段"。虽然严格来说 `ownership_id`/`ownership_entity` 等精确字段名未出现，但 `getOwnershipDistribution()` 方法（[L147](frontend/src/services/statisticsService.ts)）调用 `/ownership-distribution` 端点——`ownership` 语义链路仍活跃。

**影响**: Phase 4 后端端点改名时，此处将断裂且无前置标记。

**建议**: 标注 `getOwnershipDistribution()` 为"Phase 4 待评估迁移项"，在 P3e Exit 审计记录中显式登记。

---

### P1-9：`assetDictionaryService.ts` 的旧字段引用是字典 `dict_type` 标识，迁移需后端同步

**位置**: §4.2 变更清单

**问题**: [assetDictionaryService.ts](frontend/src/services/asset/assetDictionaryService.ts) 中 `getOwnershipEntitiesFromDict()` → `getSystemDictionaries('ownership_entity')` 和 `getManagementEntitiesFromDict()` → `getSystemDictionaries('management_entity')` 传递的是后端字典服务的 `dict_type` 标识符，不是 ORM 字段名。前端单方面改名将导致字典查询 404 或空数据。

**影响**: 若后端字典 `dict_type` 不改，前端不应改动字符串值。计划变更清单标注"迁移"会误导执行者。

**建议**: 明确此字典键名是否纳入 Phase 3 迁移范围。若后端不改名，变更描述应改为"保留方法名与字典键，标记 `@deprecated`，Phase 4 统一迁移"。

---

### P1-10：P3c 与 P3d 的并行边界模糊，`AssetList.tsx` 权限改造归属不清

**位置**: §0 Gantt / §4.3 / §5 依赖图

**问题**: §4.3 资产模块变更清单中 `AssetList.tsx` 要求"权限判定改 `useCapabilities`"，这属于 P3d 的改造范围（`useCapabilities` 在 P3d 创建）。但 `AssetList.tsx` 被列在 P3c 的文件清单中。

同样，多个 P3c 文件（如 `ContractListPage.tsx`）的"过滤条件替换"可能需要 `PartySelector`（P3c 组件）但也需要 `useCapabilities`（P3d Hook）。

**影响**: 开发者无法确定这些文件的权限相关改造属于 P3c 还是 P3d 并行任务。

**建议**: 在 §4.3 中对每个文件的变更内容拆分标注 `[P3c]`/`[P3d]`，或增加一个"P3c/P3d 交叉文件处理规则"说明并行分工。

---

### P1-11：P3a Exit `types/index.ts` 新增导出门禁仅为"手动验证"

**位置**: §5.1 P3a Exit

**问题**: 证据命令为"手动验证 import 路径"。当前 [types/index.ts](frontend/src/types/index.ts) 有 513 行的 barrel 导出，手动验证容易遗漏 `Party`、`Capability`、`DataPolicyTemplate` 等新类型。

**建议**: 改为自动化命令：
```bash
grep -nE "export.*from.*party|export.*from.*capability|export.*from.*dataPolicy" frontend/src/types/index.ts
```

---

### P1-12：P3b Entry `party.read` 非管理员 SQL 门禁过度复杂且脆弱

**位置**: §5.1 P3b Entry

**问题**: 门禁 SQL 依赖四表 JOIN + 大小写不敏感匹配 + 硬编码管理员角色名排除。在非 Docker 环境、角色名大小写不一致、或 DB 未就绪场景下极易假失败。

**建议**: 
1. 主验证改为 API 级别：用非管理员用户调用 `GET /api/v1/auth/me/capabilities` 检查结果含 `party.read`
2. SQL 仅作辅助验证

---

### P1-13：P3d Exit `@authz-minimal` E2E 测试不存在

**位置**: §5.1 P3d Exit / §6.2

**问题**: 计划要求 P3d Exit 通过 `@authz-minimal` E2E 测试，但当前无此标签的测试用例。注记中承认可降级为 `pnpm e2e` 兜底。

**建议**: 将 `@authz-minimal` E2E **测试编写** 纳入 P3d 的显式交付物（§4.4 变更清单中新增条目），而非假设已存在。

---

### P1-14：`canPerform()` 对 `TemporaryAdminAction` 的分支逻辑未在伪代码中体现

**位置**: §4.4 / §4.4.1

**问题**: `canPerform(action: AuthzAction | TemporaryAdminAction, resource)` 的签名接受 `'backup'` 等临时豁免动作。但伪代码和纯函数 `evaluateCapability` 的描述中未展示如何处理非标准动作——在 `capabilities` 中查找 `backup` 将必然返回 `false`（后端不生成此动作的能力条目）。

**建议**: 在 `useCapabilities.ts` 伪代码中显式补充分支：
```typescript
// 临时豁免: backup 等非标准动作走 admin-only
if (isTemporaryAdminAction(action)) return isAdmin;
// 标准动作: 查 capabilities
return evaluateCapability(capabilities, action, resourceType, perspective);
```

---

### P1-15：D8 伪代码中 `VITE_ENABLE_CAPABILITY_GUARD` 未设置时行为与 D9 矛盾

**位置**: §4.4.2 D8 伪代码 / D9

**问题**: D8 伪代码 `const capabilityGuardEnabled = import.meta.env.VITE_ENABLE_CAPABILITY_GUARD === 'true'`。若 `.env.production` 未设置此变量，值为 `undefined`，`=== 'true'` 为 `false`——实际效果是"默认 `false`"。

D9 则要求"禁止依赖默认值"（v1.33："禁止'未声明时自动回退默认 `false`'"）。

**实际矛盾**: 代码层面的行为就是默认 `false`，且 `frontend/.env.production` 当前不存在。

**建议**: 
1. 在启动代码中加入断言/警告：
```typescript
if (import.meta.env.VITE_ENABLE_CAPABILITY_GUARD == null) {
  console.error('[authz] VITE_ENABLE_CAPABILITY_GUARD is not explicitly set');
}
```
2. 在 D9 中澄清"禁止依赖默认值"的实际强制力：是 CI 阻断还是运行时日志警告

---

## 3. 中等级问题（P2 — 可能导致返工或门禁误判）

### P2-1：`ownership_entity` 统计口径 "17+1+1" 与实际差距较大

**位置**: §3.1

**问题**: 实际 `ownership_entity` grep 约 25 文件（全量），但计划声称主链 17。差值 ~6 个文件的归属需分类确认。

**建议**: 重新执行分类统计，逐文件确认主链/测试链归属，以更新统计表。

---

### P2-2：`organization_id` 影响分布描述缺少间接引用路径

**位置**: §3.1

**问题**: 影响分布列出 `types/auth`、`hooks/usePermission` 等。但 `AuthContext.tsx`（[L67](frontend/src/contexts/AuthContext.tsx)）通过 `useState<User>` 间接引用 `User.default_organization_id`（来自 `types/auth.ts`）。此间接路径虽不需直接改动 `AuthContext` 的 `organization_id`，但影响评估应提及。

**建议**: 补充"间接引用路径"说明或在注记中标注"`AuthContext.tsx` 通过 `User` 类型间接引用，Phase 3 不改名，Phase 4 统一"。

---

### P2-3：`rentContractExcelService.ts` 的 `baseUrl` 修正需先验证 `apiClient.baseURL`

**位置**: §4.2 / §4.6

**问题**: 计划要求从 `'/api/rental'` 修正为 `'/rental-contracts'`（相对路径）。但实际效果取决于 `apiClient.baseURL` 的值——若 `baseURL` 为 `http://127.0.0.1:8002/api/v1`，最终请求路径为 `http://127.0.0.1:8002/api/v1/rental-contracts/excel/template`，这取决于后端是否有此路由。

P3e Entry 门禁检查了 `baseUrl` 字符串内容，但未验证最终请求 URL 是否可达。

**建议**: 在 P3e Entry 增加 `apiClient.baseURL` 自动化检查：
```bash
grep -nE "baseURL|BASE_URL" frontend/src/api/client.ts frontend/src/api/config.ts | head -10
```
并在联调中验证 `GET {baseURL}/rental-contracts/excel/template` 返回 200。

---

### P2-4：产权证契约冻结缺乏自动化门禁

**位置**: §4.3 / §5.1 P3c Entry

**问题**: "P3c Entry 前必须二选一冻结"，证据为"决策记录 + 联调样本"——纯人工证据。

**建议**: 增加最小自动化验证（P3c Entry 执行）：
```bash
# 检查后端产权证 schema 是否已有 party_relations
grep -nE "party_relations" backend/src/schemas/property_certificate.py 2>/dev/null \
  && echo "方案 A: 后端已交付 party_relations" \
  || echo "方案 B: 保持 owners[] 兼容"
```

---

### P2-5：P3c 组织架构"只读"改造缺乏自动化 Exit 验证

**位置**: §4.3 / §5.1 P3c Exit

**问题**: 方案 B 要求禁用五类写入口（新增/编辑/删除/移动/导入）且在 `organizationService` 写方法增加保护性拦截。但 P3c Exit 无自动化命令验证这些操作被禁用。

**建议**: 新增 P3c Exit 门禁（方案 B 时）：
```bash
# 验证 organizationService 写方法有保护性拦截
grep -nE "throw|禁止|只读|readonly|deprecated.*write|Phase 3" frontend/src/services/organizationService.ts | head -10
```

---

### P2-6：`hasPartyAccess` 的 `tenant` relationType 与后端 `data_scope` 不匹配

**位置**: §4.4 `useCapabilities.ts`

**问题**: `hasPartyAccess(partyId, relationType: 'owner'|'manager'|'tenant', resourceType?)` 的 `tenant` 选项在后端 `data_scope` 中无对应字段（仅有 `owner_party_ids` 和 `manager_party_ids`）。调用 `hasPartyAccess(id, 'tenant')` 将无法匹配任何 ID 列表。

**建议**: 要么移除 `'tenant'` 选项并在 JSDoc 中说明原因，要么定义 `tenant` 的 fallback 行为（如"tenant 归属判定不通过 data_scope，由业务逻辑自行处理，此方法对 tenant 始终返回 `true`（不做 scope 约束）"）。

---

### P2-7：`usePermission.tsx` 行号引用会在涉前修改后漂移

**位置**: §4.4.1

**问题**: 引用 `PERMISSIONS.SYSTEM_BACKUP`（`usePermission.tsx:236`），但文件 264 行。任何前置改动都会导致行号失效。

**建议**: 仅引用常量名，不绑定行号。

---

### P2-8：`KnownResourceType` 含 `ledger` 但 ABAC seed 覆盖未验证

**位置**: §4.1 / §4.4.2 D3

**问题**: D3 将 `/rental/ledger` 归为 capability 路由 `canPerform('read','ledger')`。但 P3b Entry ABAC seed 门禁矩阵中仅提到 `party.read`、`project.read|list`、`rent_contract.read`、`property_certificate.read`、`asset.create|delete|export`——**不含 `ledger.read`**。

若后端 ABAC seed 无 `ledger.read` 规则，非管理员将永远无法访问台账页。

**建议**: 在 P3b Entry ABAC seed 门禁中显式增加 `ledger.read` 检查，或将 `/rental/ledger` 改为 adminOnly。

---

### P2-9：`test-utils/factories/` 缺少 `rentContractFactory.ts`

**位置**: §4.3 / §4.6

**问题**: `test-utils/factories/` 包含 `assetFactory.ts`、`ownershipFactory.ts`、`projectFactory.ts`——无合同工厂。合同模块测试改造涉及大量旧字段（11 处 `ownership_id`），测试数据可能散落在各测试文件中。

**建议**: 在 P3c 中评估是否新建 `rentContractFactory.ts` 以集中管理。

---

### P2-10：`ownershipFactory.ts` 未纳入迁移/废弃清单

**位置**: §4.3 / §4.6

**问题**: `test-utils/factories/ownershipFactory.ts` 存在但未在任何变更清单中提及。既然 `types/ownership.ts` 要标记 `@deprecated`，对应工厂也应同步处理。

**建议**: 纳入 P3e 废弃/删除清单。

---

### P2-11：`DB_PSQL_CMD` 默认值假设 Docker 环境

**位置**: §5.2

**问题**: 默认 `docker compose exec db psql -U zcgl_user -d zcgl`，本地直连 PostgreSQL 的开发者需自行覆盖。

**建议**: 补充本地直连示例：
```bash
export DB_PSQL_CMD="psql -U zcgl_user -d zcgl -h localhost -p 5432"
```

---

### P2-12：`PHASE3_GREP_EXCLUDES` 中 `--exclude=*organizationService*` 使用通配符

**位置**: §5.2

**问题**: 计划注记中明确说"禁止使用 `*systemService*` 宽匹配"，但 `--exclude=*organizationService*` 和 `--exclude=*ownershipService*` 使用了同样的通配模式。若出现 `partyOrganizationService.ts` 等文件名，将被错误排除。

**建议**: 收窄为精确文件名匹配：`--exclude=organizationService.ts` 和 `--exclude=ownershipService.ts`。

---

### P2-13：`tenant_party_id` 收紧的 T0 快照与执行日可能有时差

**位置**: §5.1 P3e Entry

**问题**: 统计时点固定为"执行门禁当日 T0 首次 SQL 快照"，但从门禁评估到实际收紧执行可能间隔数日，新增 NULL 数据会逃逸。

**建议**: 增加"P3e 执行日 D-1 复查"要求。

---

### P2-14：多权限语义默认 `any` 缺乏决策理由

**位置**: §4.4.2

**问题**: "多权限语义约定为 `any`（任一满足即可进入路由）"但未说明为何不用 `all`。对于涉及多资源的综合页面，`any` 可能过于宽松。

**建议**: 补充决策理由，说明当前路由粒度足够细、不存在需要 `all` 语义的场景。

---

### P2-15：`capabilities` 变更判据 "hash" 未定义算法

**位置**: §4.2

**问题**: v1.21 要求"比较 `generated_at` 或能力列表签名（hash）"，但 hash 算法未指定。

**建议**: 明确推荐"直接比较 `generated_at` 字符串"（最简且可靠），hash 仅作可选优化。

---

### P2-16：§8 文件影响总览 "Types 修改 8" 可能少算

**位置**: §8

**问题**: 实际还需修改 `services/asset/types.ts`（统计维度字段）和 `types/index.ts`（新增导出），这两个未计入 Types 修改数。

**建议**: 更新统计或标注"不含 service 层类型文件和 barrel 导出"。

---

### P2-17：门禁 A 命令中 `test -f` 路径扩展名需确认

**位置**: §4.4.1

**问题**: `test -f frontend/src/hooks/usePermission.tsx` — 文件扩展名 `.tsx` 正确 ✓；`test -f frontend/src/components/System/CapabilityGuard.tsx` 正确 ✓；`test -f frontend/src/contexts/AuthContext.tsx` 正确 ✓；`test -f frontend/src/constants/routes.ts` — `.ts` 正确 ✓。

但 §5.1 P3d Exit 的 `useCapabilities` 引用使用 `.ts` 但实际 hook 文件可能是 `.tsx`（若使用 JSX）——需确认。

**建议**: 在 P3d 实施规范中明确 `useCapabilities` 文件扩展名（纯逻辑 hook 建议用 `.ts`）。

---

### P2-18：`BroadcastChannel` 兼容性降级未指定检测方式

**位置**: §4.5

**问题**: `BroadcastChannel` 在 Safari < 15.4 中不可用。计划提到"降级 `storage` 事件"但未说明运行时检测逻辑。

**建议**: 补充：`typeof BroadcastChannel !== 'undefined' ? new BroadcastChannel(...) : fallbackStorageSync()`。

---

## 4. 低级问题（P3 — 建议修正，不影响主链执行）

### P3-1：§10 文档历史占全文 ~35%，信息密度极低

**位置**: §10（约 L1095-L1667）

**问题**: 30 条变更记录约 570 行，占全文 1667 行的 34%。对执行者的价值极低，增加阅读负担。

**建议**: 精简为"最近 3 个版本摘要"，历史归档到 Git blame 或独立 changelog 文件。

---

### P3-2：`ResourceType = KnownResourceType | (string & {})` 技巧需注释

**位置**: §4.1

**问题**: `(string & {})` 是 TypeScript 联合类型穷尽性保留技巧（允许自动补全 known 值同时接受任意字符串），但对新成员不友好。

**建议**: 在类型定义 TSDoc 中说明此写法的目的和行为。

---

### P3-3：`FrontendPartyHierarchyEdge` 类型可能过度抽象

**位置**: §4.1

**问题**: 后端 `GET /parties/{id}/hierarchy` 返回 `list[str]`（子 Party ID 列表），前端仅需 `string[]`。专门定义 `FrontendPartyHierarchyEdge` 接口可能是过度设计。

**建议**: 除非确认有具体树组装消费场景，否则延后创建。

---

### P3-4：`CertificatePartyRelation` 中 `relation_role` 枚举值需与后端核验

**位置**: §4.1

**问题**: 定义了 `'owner' | 'co_owner' | 'issuer' | 'custodian'`，需确认后端 `certificate_party_relations` 表的 `relation_role` 枚举是否一致。

**建议**: P3a 执行时增加后端 schema 核验步骤。

---

### P3-5：`PartyListParams` 缺少 `search` 参数预留

**位置**: §4.1

**问题**: `PartyListParams` 定义了 `party_type/status/skip/limit`，但 `search` 参数（P3b 硬门禁依赖的后端参数）未在类型中预留。

**建议**: 加入 `search?: string` 以与 P3b 的 `searchParties()` 对齐。

---

### P3-6：§6.2 运行时拦截器正则可能误报

**位置**: §6.2

**问题**: `JSON.stringify` 全文正则匹配旧字段名会命中 API 响应中的正常字段名或错误消息。

**建议**: 改为检查 `Object.keys(config.data ?? {}).concat(Object.keys(config.params ?? {}))` 中是否含旧字段 key。

---

### P3-7：`OwnershipRentStatistics` 的 `ownership_name/ownership_short_name` 迁移未入变更清单

**位置**: §4.1 注记

**问题**: 统计口径专项提到 `ownership_name / ownership_short_name → owner_party_name`，但 §4.2/§4.3 无具体文件变更条目。

**建议**: 在 P3c 合同统计页变更条目中显式列出。

---

### P3-8：PowerShell 等价命令覆盖不完整

**位置**: §6.3

**问题**: 仅覆盖 P3b/P3d/P3e 部分门禁，P3a/P3c 缺失。

**建议**: 补齐或标注"P3a/P3c 门禁仅限 WSL/Git Bash"。

---

### P3-9：`check-route-authz-mutual-exclusive.mjs` 需适配新路由结构

**位置**: §5.1 P3d Exit

**问题**: 脚本已存在但未确认是否能处理 P3d 新增的 `permissions: Array<{action, resource}>` + `adminOnly` 路由结构。

**建议**: P3d 实施时增加验证/更新任务。

---

### P3-10：回滚步骤 `pnpm install` 可能因 lock 文件版本冲突失败

**位置**: §7.3

**问题**: `git checkout <tag> -- frontend` 回滚 `pnpm-lock.yaml` 后，若 Node/pnpm 版本已升级，`pnpm install` 可能失败。

**建议**: 补充"若 `pnpm install` 失败，使用 `pnpm install --no-frozen-lockfile`"。

---

### P3-11：§2 "不包含" 列缺少 Party CRUD 管理页面

**位置**: §2

**问题**: 新增了 `PartySelector` 和 `partyService`，但无独立 Party CRUD 页面。Phase 3 后 Party 数据只能通过后端 API 管理。

**建议**: 在"不包含"列增加"Party 独立管理页面（CRUD）— Phase 4+"。

---

### P3-12：`DataPolicyManagementPage` "嵌入角色管理或独立页面" 未冻结

**位置**: §4.4

**问题**: §4.4 描述为"嵌入角色管理或独立页面"，但 D2 已将 `/system/data-policies` 列入 adminOnly 路由（暗示独立页面）。两处描述需统一。

**建议**: 冻结为"独立路由 `/system/data-policies`"并在 P3d `AppRoutes.tsx` 变更中显式列出。

---

## 5. 亮点与认可

尽管存在上述问题，本计划在以下方面表现出色：

1. **门禁体系极其严密**: 从 Entry 到 Exit，几乎每个子阶段都有可执行的 bash/PowerShell 证据命令，且区分了 Bash/PowerShell 双环境。这在同类项目实施计划中极为罕见。

2. **排除单源机制（§5.2）**: `PHASE3_GREP_EXCLUDES` 统一了所有门禁命令的排除项，解决了大型迁移项目中最常见的"门禁口径漂移"问题。

3. **并行规则与依赖关系清晰**: Gantt 图 + Mermaid 依赖图 + 文字注释三重表达，且在 v1.36 中修正了 P3c/P3d 并行冲突。

4. **阻断项实名追踪**: §1 Phase 2-patch 工单表标注了责任方、deadline、验收证据，可追溯性极强。

5. **偏离管理（Deviation）**: 对架构设计文档的偏离（如 `X-Authz-Stale` 头缺失）在 §4.5 显式声明，并指向 Phase 4 回收——这是成熟工程实践。

6. **分层 deprecated 策略**: P3a 标记 → P3b/P3c 渐进切换 → P3e 物理移除的三段式生命周期，最大程度降低编译断裂风险。

7. **feature flag 熔断（D8/D9）**: `VITE_ENABLE_CAPABILITY_GUARD` 机制提供权限守卫快速回退能力——关键安全网。

8. **40 轮迭代的工程严谨度**: v1.0 到 v1.40 经历了代码实证复核、门禁可执行性审计、阻断项纠偏等 40 轮审阅，体现极高的专业水准。

---

## 6. 总结与建议

### 问题汇总

| 等级 | 数量 | 核心主题 |
|------|------|----------|
| **P0 阻断** | 6 | 后端交付物假设与现实 gap（`party_relations`/`search`/`expose_headers`）、统计口径错误、变更清单事实偏差 |
| **P1 严重** | 15 | `AuthContext` 改造量低估、`PermissionGuard` 7 导出未盘点、`AuthGuard` D5 矛盾、E2E 测试不存在 |
| **P2 中等** | 18 | 字典键名迁移策略模糊、`tenant` data_scope 缺失、hash 算法未定义、门禁环境脆弱 |
| **P3 低级** | 12 | 文档冗余、TypeScript 技巧注释、PowerShell 覆盖不全、过度抽象类型 |

### 修复优先级

1. **立即修复（启动前）**: P0-1 ~ P0-6 — 与后端确认 `party_relations`/`search` 交付计划，修正统计口径和变更清单事实性错误
2. **P3d 启动前**: P1-3 ~ P1-6 — AuthContext 改造量重估、PermissionGuard 消费者盘点、AuthGuard 迁移策略冻结
3. **执行中持续关注**: P2 级 — 门禁环境适配、类型系统 gap、字典键名决策
4. **方便时修正**: P3 级

### 总体评价

本计划是一份**工业级的前端全量迁移实施计划**，在 40 轮迭代中积累了极高的工程严谨度和门禁精度。核心问题集中在 **后端交付物假设与实际代码库的 gap**（P0-1、P0-2、P0-3）和 **部分影响统计与变更清单的事实性偏差**（P0-5、P0-6）。修正这些问题后，计划具备高质量落地的条件。

---

*审阅工具：代码库 grep 全量验证、Phase 2 计划交叉比对、架构设计文档 v3.9 对照、后端 Schema/ORM/API 实际代码逐行检查*
