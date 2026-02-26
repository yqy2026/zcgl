# Phase 3 实施计划深度审阅报告

**审阅对象**: [Phase 3 实施计划 v1.25](../plans/2026-02-20-phase3-implementation-plan.md)  
**审阅日期**: 2026-02-21  
**审阅方法**: 代码库逐项交叉验证（前端 + 后端 + Phase 2 计划 + Alembic 迁移 + 后端 API 路由）

---

## 总结矩阵

| 级别 | 数量 | 核心风险 |
|------|------|---------|
| **P0 — 严重** | 3 | Party search 接口无归属方、assetFormSchema 路径错误、Excel 路径门禁假设未验证 |
| **P1 — 重要** | 7 | 影响统计虚高 ×4、ProtectedRoute 处置缺失、`tenant_party_id` 后端不存在、页面清单遗漏 |
| **P2 — 中等** | 6 | resource_type 误用被低估、perspectives 映射缺失、feature flag 逻辑空白、冷启动时序、循环 403、门禁遗漏 |
| **P3 — 建议** | 4 | 文档历史过长、表述不统一、contactService 遗漏、"待补绑定"定义不足 |

**最大执行风险**：**P0 #1**——三个 P3b 硬门禁前置任务（parties search、project 空数组修复、ABAC 错误码）没有任何 Phase 正式承接。如果不为这些任务创建明确的归属和排期，Phase 3 将在 P3b Entry 处**无限期阻塞**。

---

## 一、严重问题（P0 — 必须修复，否则将导致执行失败）

### P0-1. 三个 P3b 硬门禁前置任务**没有归属方**

计划在 §1 v1.24 补充了三个"Phase 2 前置补丁"，但 Phase 2 计划文档中**完全不包含这些任务**：

| 阻断项 | 归属 | 现状 |
|--------|------|------|
| `/api/v1/parties?search=` 搜索接口 | 无人 | 后端 `party.py` 仅有 `skip/limit/party_type/status`，无 `search` 参数 |
| `project_to_response()` 修复 `ownership_relations=[]` 硬编码 | 无人 | `backend/src/services/project/service.py:57` 确认硬编码 `data["ownership_relations"] = []` |
| ABAC 403 结构化错误码 `error_code=AUTHZ_DENIED` | 无人 | 后端未实现 |

**代码验证**：

```python
# backend/src/api/v1/party.py — list endpoint 参数签名
async def list_parties(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    party_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    ...
)
# 无 search 参数
```

```python
# backend/src/services/project/service.py:57
data["ownership_relations"] = []  # 硬编码空数组，忽略实际关系数据
```

**风险**：这些被标注为"前置补丁"但无正式 Phase 归属，也无负责人/排期。P3b Entry 永远无法满足。

**建议**：将这三项正式纳入 Phase 2 补充批次（P2-patch），明确负责人与交付日期，或在本计划中新增 P3-prep 子阶段承接。

---

### P0-2. `assetFormSchema.ts` 路径声明有误

计划 §4.3 将 `assetFormSchema.ts` 列在"资产模块"改造文件列表中，§4.3 末尾也提到该文件需修改 Zod 校验规则。但实际文件位于 **`frontend/src/assetFormSchema.ts`**（项目根级 `src/` 目录），**不在** `components/` 或 `pages/` 目录下。

**代码验证**：

```
# 实际路径
frontend/src/assetFormSchema.ts            ← 存在
frontend/src/components/Asset/assetFormSchema.ts  ← 不存在
frontend/src/pages/Assets/assetFormSchema.ts      ← 不存在
```

```typescript
// frontend/src/assetFormSchema.ts:6
ownership_id: z.string().min(1, '权属方不能为空'),
```

执行者若按"资产组件目录"找文件将会遗漏此处改造。

**建议**：在 §4.3 资产模块文件表格中标注完整路径 `src/assetFormSchema.ts`，与其他 `components/` 路径明确区分。

---

### P0-3. `rentContractExcelService.ts` 路径修正逻辑假设未验证

计划 §4.2 要求：
> `baseUrl='/api/rental'` → 相对 `apiClient.baseURL` 的 `/rental-contracts/*`（禁止写 `/api/v1/*` 以避免双前缀）

P3e Entry 门禁命令要求**必须**存在 `'/rental-contracts'` 字面量。

**问题**：门禁正确性取决于 `apiClient.baseURL` 的值。若 `apiClient.baseURL = 'http://127.0.0.1:8002/api/v1'`（对应 `.env` 中 `VITE_API_BASE_URL`），则路径改为 `/rental-contracts` 后最终请求 `http://127.0.0.1:8002/api/v1/rental-contracts/*` 是正确的。但计划**未验证 `apiClient` 实例是否使用 `VITE_API_BASE_URL` 作为 baseURL**。

如果 `rentContractExcelService` 内部使用了独立的 axios 实例（不走 `apiClient`），路径修正可能打到错误端点。

**建议**：P3e Entry 探针门禁应先验证 `apiClient.baseURL` 的实际值（或该服务使用的 HTTP 客户端实例的 baseURL），并将确认结论写入执行记录。

---

## 二、重要问题（P1 — 强烈建议修复，影响工作量估算和执行准确性）

### P1-1. §3.1 旧字段影响统计严重虚高

对代码库执行实际 grep 验证（排除测试目录），发现计划声称的影响文件数与实际偏差显著：

| 旧字段 | 计划声称 | 实际验证 | 偏差率 |
|--------|---------|---------|-------|
| `organization_id` | 16 | **9** | +78% |
| `ownership_id` | 34 | **25~26** | +31% |
| `ownership_entity` | 25 | **18** | +39% |
| `usePermission` | 12 | **7** | +71% |

**实际 `organization_id` 命中文件（9 个）**：

| # | 文件 |
|---|------|
| 1 | `types/propertyCertificate.ts` |
| 2 | `types/organization.ts` |
| 3 | `types/auth.ts`（`default_organization_id`） |
| 4 | `services/systemService.ts` |
| 5 | `services/organizationService.ts` |
| 6 | `pages/System/UserManagement/index.tsx` |
| 7 | `pages/System/UserManagement/hooks/useUserManagementData.ts` |
| 8 | `pages/System/UserManagement/components/UserFormModal.tsx` |
| 9 | `hooks/usePermission.tsx` |

**实际 `usePermission` 命中文件（7 个）**：

| # | 文件 | 性质 |
|---|------|------|
| 1 | `hooks/usePermission.tsx` | 定义 |
| 2 | `components/System/PermissionGuard.tsx` | import |
| 3 | `components/Router/RouteBuilder.tsx` | `PERMISSIONS` import |
| 4 | `components/Router/index.ts` | 重导出 |
| 5 | `components/Router/DynamicRouteLoader.tsx` | import |
| 6 | `components/Router/DynamicRouteContext.tsx` | 定义引用 |
| 7 | `components/Asset/AssetList.tsx` | import + 使用 |

虽然 §3.1 注释说明"计数用于工作量估算"，但高达 30%~78% 的偏差会导致排期严重高估。

**建议**：按实际 grep 数据更新 §3.1 表格。可注明"含测试目录时为 N 个"以保留原始基数的上下文。

---

### P1-2. `types/rentContract.ts` 中 `ownership_id` 计数不准

计划 §4.1 声称"文件内所有含 `ownership_id` 的类型均纳入 P3a→P3e 迁移（**共 13 处**）"。

实际 grep 验证为 **12 处**（含一个复数 `ownership_ids` 变体）。

**建议**：复核并勘误为 12；若有第 13 处需列出行号。

---

### P1-3. `tenant_party_id` 在后端 RentContract 模型中**不存在**

计划 §4.1 新增 `tenant_party_id?: string` 到 `RentContract` 类型，§4.2 rentContractService 也提到新增该参数。

**代码验证**：

```python
# backend/src/models/rent_contract.py — RentContract model
# 仅存在以下 party 字段：
owner_party_id: Mapped[Optional[str]] = mapped_column(String, ForeignKey("parties.id"))
manager_party_id: Mapped[Optional[str]] = mapped_column(String, ForeignKey("parties.id"))
# 无 tenant_party_id
```

**风险**：前端定义了后端不存储/不响应的字段。API 响应中该字段始终为 `undefined`，前端表单即使填写了也不会持久化，造成数据丢失假象。

**建议**：
- 确认后端是否在 Phase 2 后续批次计划新增 `tenant_party_id` 列
- 若无计划新增，从 P3a 类型定义中移除此字段
- 若为远期目标，在类型定义中标注为 `// Phase 4+ 预留` 而非正式迁移字段

---

### P1-4. `ProtectedRoute.tsx` 的处置缺失

代码库中 `frontend/src/components/Router/ProtectedRoute.tsx` 是一个**已存在但未使用**的路由守卫组件（内部包装 `PermissionGuard`）。该组件未在 `AppRoutes.tsx` 或 `App.tsx` 中引用。

计划 §4.4 对 Router 目录说"Phase 3 仅执行目录级审计与遗留标记"，但未提及 `ProtectedRoute.tsx` 与新建 `CapabilityGuard` 的**功能重叠**。

**风险**：未来有人可能误将此组件接入路由，引入旧权限逻辑。

**建议**：在 §4.4 Router 目录审计范围中显式列出 `ProtectedRoute.tsx`，标记 `@deprecated` 并禁止新引用。

---

### P1-5. 页面层改造清单遗漏文件

| 遗漏文件 | 命中旧字段 | 原因 |
|----------|-----------|------|
| `services/asset/assetDictionaryService.ts` | `management_entity`, `ownership_entity` | §4.2 仅笼统写"asset/*"，未逐一列出该子文件 |
| `components/Asset/AssetList.tsx` | `usePermission` import | §4.3 仅提到字段替换，未提 `usePermission` → `useCapabilities` 迁移 |
| `hooks/useFormFieldVisibility.ts` | 引用 `assetFormSchema` | assetFormSchema 迁移后可能需要同步调整 |

**建议**：在相应子节补充明确列出这些文件的改造内容。

---

### P1-6. `types/auth.ts` 中 `default_organization_id` 未规划处置

`types/auth.ts:33` 存在 `default_organization_id?: string`。计划 §4.1 对 `types/auth.ts` 仅提到新增 `capabilities` 和 `data_policies`，**未规划 `default_organization_id` 的处理**。

**影响分析**：
- P3e 旧字段零引用门禁 `\borganization_id\b` 的 `\b` 词边界**不会**匹配 `default_organization_id`（`default_`前缀构成词边界），因此不会触发门禁失败
- 但该字段在 `User` 接口中长期保留，语义上仍旧与 organization 而非 party 绑定

**建议**：在 §4.1 `types/auth.ts` 改造说明中显式标注 `default_organization_id` 为"Phase 3 保留，待后端交付 `default_party_id` 后迁移（Phase 4）"，与 §4.2 systemService 的 v1.24 例外口径对齐。

---

### P1-7. 甘特图缺少 P3c → P3d 依赖线

§0 甘特图中 P3d 仅标注 `after p2d`，未画出 `P3c → P3d` 依赖线。虽然正文 §5 和 §0 注释都说明了 AND 双前置要求，但甘特图**视觉上暗示 P3c 和 P3d 可并行**。

对比正文 §0 的并行规则：
> P3d 必须等 **P2d Exit + P3c Exit** 后启动

**建议**：在甘特图中补上 `P3d after p3c` 关系（即使 Mermaid 只能表达主依赖，也比缺漏好），或在 P3d 行加注释 `%% ALSO requires P3c Exit`。

---

## 三、中等问题（P2 — 建议修复，提升计划健壮性）

### P2-1. 后端 `resource_type="asset"` 的系统性误用被低估

代码验证确认后端 `require_authz()` 的实际调用情况：

| 端点类型 | 实际 `resource_type` |
|----------|---------------------|
| Party CRUD | `"party"` ✅ |
| 合同模块 | `"rent_contract"` ✅ |
| **用户管理** | `"asset"` ❌ |
| **角色管理** | `"asset"` ❌ |
| **系统监控/设置/备份/恢复/字典** | `"asset"` ❌ |

这意味着如果 ABAC seed 为 `resource_type="user"/"role"/"system"` 创建了策略规则，这些规则**永远不会被后端匹配到**。当前的 `adminOnly` 守卫策略只是前端绕过，后端鉴权实际上形同虚设。

**建议**：在 §9 Phase 4 交接中将此标注为 **P0 遗留债务**（而非一般 TODO），并明确标注"后端资源名统一前，ABAC 对 user/role/system 端点无实际鉴权效力"。

---

### P2-2. `capabilities.perspectives` override 映射表缺失

计划 §4.4 推荐方案 B（前端 resource-specific perspective override），但：

- 没有给出 override 映射表的具体内容（哪些 resource 需要 override 什么 perspective）
- 没有定义后端返回值与 override 矛盾时的优先级规则
- `getAvailablePerspectives()` 的返回值是原始值还是 override 后的值？

**建议**：在 §4.4 或附录中提供 resource-specific perspective override 的映射表草案。至少覆盖 `project`（仅 manager 视角）等已知特例。

---

### P2-3. P3d feature flag (`VITE_ENABLE_CAPABILITY_GUARD`) 实施细节不足

§4.4.2 D8 要求权限守卫受 feature flag 控制，但：

| 缺失项 | 影响 |
|--------|------|
| flag 关闭时的路由逻辑未定义 | 无权限检查（仅认证）？还是走旧 PermissionGuard？ |
| flag 关闭时是否仍请求 capabilities 接口 | 不请求则开启时冷启动延迟；请求则 flag 无意义 |
| `renderProtectedElement` 伪代码中无 flag 分支 | 执行者无参考实现 |

**建议**：在 §4.4.2 伪代码中加入 flag 分支逻辑。推荐 flag 关闭时走"仅认证无权限检查"（最安全的降级），capabilities 接口仍然请求（保持缓存热备）。

---

### P2-4. 冷启动 `capabilitiesLoading` 失败路径未体现在代码骨架

计划 §4.2 要求 `capabilitiesLoading` 以 `hasToken ? true : false` 初始化，v1.24 补充"失败分支保证 `capabilitiesLoading=false`"。

**时序风险**：当 token 存在但已过期时：
1. `capabilitiesLoading = true`（因 hasToken）
2. `restoreAuth()` 刷新 token 失败 → `setUser(null)`
3. 若此时未 `setCapabilitiesLoading(false)` → 路由永远 loading

该要求仅在文字描述中，**未体现在 §4.2 的代码骨架中**。

**建议**：在代码骨架的 `restoreAuth()` 中补充 `finally { setCapabilitiesLoading(false) }` 示例。

---

### P2-5. `AuthzErrorBoundary` 静默 refresh 与 capabilities 接口 403 的循环风险

当后端返回 403 时：
1. `AuthzErrorBoundary` 触发静默 refresh → 调用 `fetchCapabilities()`
2. 如果 `fetchCapabilities()` 本身也返回 403（token 过期或 capabilities 端点配置错误）
3. 又触发 `AuthzErrorBoundary`

计划 §4.5 的"失败降级"说"单次失败波次最多触发 1 次静默 refresh"，但没有明确 `fetchCapabilities()` 自身的 403 是否排除在触发器之外。

**建议**：在 §4.5 触发信号中显式排除 capabilities 接口（`GET /api/v1/auth/me/capabilities`）的 403，或在 `capabilityService` 请求级别标记 `skipAuthzRefresh`。

---

### P2-6. P3e 门禁遗漏 `services/README.md`

`frontend/src/services/README.md` 包含 `ownership_id` 文本描述。虽然 §6.2 门禁命令通过 `--include="*.ts" --include="*.tsx"` 限制了扫描范围（不含 `.md`），目前不会误报。

但若有执行者扩大 grep 范围或使用其他搜索工具（如 IDE 全局搜索），会产生困惑。

**建议**：在 §6.2 门禁注释中补充说明"`.md` 文件不在扫描范围内；README/注释中的旧字段名残留不计入门禁"。

---

## 四、低优先级建议（P3 — 可改善文档质量）

### P3-1. 文档历史过于庞大

§10 文档历史占全文约 240+ 行（约 17%）。v1.0-v1.10 已归档到 Git，但 v1.11-v1.25 的 15 个版本条目仍然过长。

**建议**：仅保留 v1.23-v1.25 的要点（当前执行版本），将 v1.11-v1.22 折叠为一行摘要并注明"详见 Git 历史"。

---

### P3-2. `ownership_entity` 迁移目标字段表述不统一

- §4.1 `types/asset.ts`：`ownership_entity` 标记废弃，新增 `owner_party?: Party`（对象引用）
- §4.3 页面层表格：`ownership_entity` 显示 → "Party name"（字符串）

两者不矛盾（视图层显示 `owner_party.name`），但表述口径不一致，容易让执行者以为类型层也要改成字符串字段。

**建议**：在 §4.3 表格中统一表述为"→ `owner_party?.name`（从关联对象取值）"。

---

### P3-3. 遗漏 `contactService.ts` 评审

`frontend/src/services/contactService.ts` 存在并提供联系人管理功能。新增的 `PartyContact` 类型（§4.1 `types/party.ts`）与现有 `contactService` 存在**功能重叠**的可能性。

计划未提及此服务的评审或迁移策略。

**建议**：在 §4.2 [REVIEW] 节中新增 `contactService.ts` 条目，确认其是否需要迁移到 Party 体系下的联系人管理。

---

### P3-4. 无资产项目"待补绑定"标签逻辑未定义

§4.3 项目模块提到"无资产项目显示'待补绑定'标签"，但未定义：

| 缺失定义 | 备选方案 |
|----------|---------|
| 判定条件 | `project.asset_count === 0` 还是 `project.party_relations.length === 0`？ |
| UI 形态 | Ant Design `Tag` 组件还是 `Badge`？颜色？ |
| 展示位置 | 列表页行内？详情页顶部？两者都显示？ |

**建议**：在 §4.3 项目模块改造描述中补充判定条件和 UI 规格。

---

## 附录：代码库交叉验证关键发现

### A. 后端 API 与 Phase 3 计划对齐度

| 计划声称 | 验证结果 |
|----------|---------|
| Party API 存在 (`/parties`, `/parties/{id}`) | ✅ 存在 |
| `/parties?search=` 存在 | ❌ **不存在** — 仅有 `skip/limit/party_type/status` |
| `limit=1000` 在 `party.py:30` | ✅ 准确（`le=1000`，默认 100） |
| `/auth/me/capabilities` 存在 | ✅ 存在 |
| 数据策略 3 个端点存在 | ✅ 全部存在 |
| `AuthzAction` 为 6 种标准动作 | ✅ `create/read/list/update/delete/export` |
| Party 模型存在、`owner_party_id`/`manager_party_id` 在 asset/project/rent_contract | ✅ 全部存在（`Optional`） |
| `tenant_party_id` 在 rent_contract | ❌ **不存在** |
| 两个 Alembic 迁移文件存在 | ✅ 均存在 |
| `ownership_relations=[]` 硬编码 | ✅ 确认存在于 `service.py:57` |
| `certificate_party_relations` 表和模型存在 | ✅ 存在 |

### B. 前端现状与 Phase 3 起点确认

| 项目 | 现状 |
|------|------|
| `party.ts` / `capability.ts` / `dataPolicy.ts` 类型文件 | **不存在**（待创建） |
| `partyService` / `capabilityService` / `dataPolicyService` | **不存在**（待创建） |
| `useCapabilities` hook | **不存在**（待创建） |
| `CapabilityGuard` 组件 | **不存在**（待创建） |
| `AuthContext` 中 `capabilities` / `capabilitiesLoading` / `isAdmin` | **不存在**（待注入） |
| `AppRoutes.tsx` 路由元数据（permissions/adminOnly） | **不存在** — 纯 `{ path, element }` 结构 |
| `ROUTE_CONFIG`（`constants/routes.ts`）含 permissions 字段 | ✅ 存在但**未接入**路由渲染链 |
| `ProtectedRoute.tsx`（Router 目录） | ✅ 存在但**未使用** |
| `rentContractExcelService.ts` baseUrl | ✅ 确认为 `'/api/rental'` |
| `useAssetStore` 无旧主体字段 | ✅ 确认无命中 |
| `canAccessOrganization` 引用数 | ✅ 3 个文件（含测试） |
| `management_entity` 引用数 | ✅ 8 个文件 |
| 所有 `package.json` 脚本（lint/guard:ui/type-check 等） | ✅ 全部存在 |

---

## 附录C：采纳结果回写（基于计划 v1.26）

> 说明：本节用于闭环跟踪“本报告建议是否已被计划文档采纳”。原审阅正文保持不改，采纳状态以最新计划文档为准。

| 条目 | 采纳状态 | 回写结果 |
|------|----------|---------|
| P0-1 前置补丁无归属方 | ✅ 已采纳 | 计划新增“Phase 2-patch 后端承接批次”归属门禁，未交付不得进入 P3b/P3d。 |
| P0-2 `assetFormSchema` 路径错误 | ✅ 已采纳 | 文件清单已明确为 `src/assetFormSchema.ts`（根级路径）。 |
| P0-3 Excel 路径假设未验证 | ✅ 已采纳 | P3e Entry 新增 `apiClient` 复用与 `API_BASE_URL/VITE_API_BASE_URL` 校验门禁。 |
| P1-1 影响统计虚高 | ✅ 已采纳 | §3.1 已按统一口径重算并写明排除规则（测试目录不计入）。 |
| P1-2 `rentContract.ts` 计数不准 | ✅ 已采纳 | “13 处”已勘误为“12 处（含 `ownership_ids`）”。 |
| P1-3 `tenant_party_id` 后端不存在 | ❌ 不采纳（结论失效） | 复核后确认后端模型已存在 `tenant_party_id`，该条从“阻断”降为“已对齐”。 |
| P1-4 `ProtectedRoute` 处置缺失 | ✅ 已采纳 | Router 审计章节已显式纳入 `ProtectedRoute.tsx`，要求标记 deprecated 且禁止新主链引用。 |
| P1-6 `default_organization_id` 处置缺失 | ✅ 已采纳 | 已明确“Phase 3 保留，Phase 4 待后端交付 `default_party_id` 再迁移”。 |
| P1-7 甘特图依赖线缺失 | ✅ 已采纳 | 甘特图已改为 `P3d after p3c`，并保留 P2d 次依赖说明。 |
| P2-2 perspectives 映射缺失 | ✅ 已采纳 | 新增最小 override 映射与优先级规则（`project` 强制 `manager`）。 |
| P2-3 feature flag 逻辑空白 | ✅ 已采纳 | 已补 flag `off` 行为（仅认证守卫、仍拉取 capabilities 热缓存）。 |
| P2-5 capabilities 403 循环风险 | ✅ 已采纳 | 已新增“排除 capabilities 接口 403 / 或 `skipAuthzRefresh` 标记”约束。 |

### 仍待后续阶段处理（未在 v1.26 完整落地）

- P2-1 后端 `resource_type='asset'` 的系统性误用：属后端改造范围，建议在 Phase 4 作为高优先级债务处理。
- P1-5 / P3-3 / P3-4（页面清单遗漏、`contactService` 评审、“待补绑定”UI 规格）建议在后续执行任务单中继续细化，不阻断当前 v1.26 计划发布。

---

*审阅结束（已补充 v1.26 采纳闭环）。原始问题分级与证据链保持不变。*
