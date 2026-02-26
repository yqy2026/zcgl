# Phase 3 实施计划 v1.28 — 全量审计评审报告

**审阅文档**: `docs/plans/2026-02-20-phase3-implementation-plan.md`（v1.28）  
**审阅日期**: 2026-02-22  
**审阅方法**: 文档逐节精读 + 代码库全量交叉验证 + 后端契约实证 + 上游文档（架构设计 v3.9 / Phase 1 / Phase 2）一致性比对  
**先前审阅**: v1.26 深审（8 项）、v1.27 综审（24 项）  
**本轮定位**: 在前两轮审阅基础上，验证 v1.28 是否有效闭合已知问题，并深挖剩余或新增风险

---

## 0. 总体评价

**结论: 有条件通过（Conditionally Approved）**

v1.28 相较 v1.27 已显著进步：`ownership_id/ownership_entity` 统计口径已校正为"主链 + test-utils 残留"双列示；`assetImportExportService` / `RentContractExcelImport` 已从"字段迁移"调正为"契约审计+回归验证"；P3e 收口新增 Router 级联处置清单；feature flag 门禁增加 `.env.production` 创建前置。

但本轮深审仍发现 **34 项问题**（5 P0 / 10 P1 / 12 P2 / 7 P3），涵盖遗漏资源类型、后端真实契约对齐盲区、多标签竞态、UI 语义落差等领域。前两轮已提出但 v1.28 仍未完全闭合的问题也在本轮归档标记。

---

## 1. 问题清单

### 严重等级定义

| 等级 | 含义 | 行动要求 |
|------|------|----------|
| **P0** | 会导致生产阻断或架构失败 | **实施前必须修复** |
| **P1** | 执行歧义或返工风险高 | 实施启动前强烈建议修复 |
| **P2** | 改进建议，不修不阻断 | 执行期渐进修复 |
| **P3** | 文档质量 / 可读性 | 后续迭代整改 |

---

### P0 — 阻断级

#### P0-1. `ResourceType` 联合类型缺少 `ledger`，台账路由将无法获得权限保护

**位置**: §4.1 `types/capability.ts` → `ResourceType` 联合类型

**现状**:
- 前端 `ResourceType` 仅定义 `asset | project | rent_contract | party | system | property_certificate`。
- 后端 `require_authz` 实际使用 `resource_type="ledger"`（非 `rent_ledger`）对台账端点鉴权（`backend/src/api/v1/rent_contracts/ledger.py`）。
- 文档 §4.4.1(B) 资源名映射矩阵**未列出 `ledger`**。
- 前端 `pages/Rental/RentLedgerPage.tsx` 是运行时可达页面，若用 `canPerform('read', 'rent_contract')` 守卫则语义不精确（台账与合同是独立资源）；若无守卫则权限真空。

**风险**: P3d 路由守卫部署后，台账页面要么权限真空（任何人可访问），要么使用错误资源名（与后端不一致导致 capabilities 匹配失败）。

**建议**:
1. `ResourceType` 增加 `'ledger'`。
2. 在 §4.4.1(B) 资源名映射矩阵增加 `ledger` 行。
3. P3d 路由元数据为 `/rental/ledger` 补充 `canPerform('read', 'ledger')` 或 `canPerform('read', 'rent_contract')` 并显式记录抉择原因。

---

#### P0-2. 后端 `require_authz` 实际资源类型数量（31+）远超计划覆盖范围，capabilities 生成盲区未评估

**位置**: §4.4.1(B) / §2 范围界定

**现状**:
后端共使用 **31+ 种不同的 `resource_type`** 值（包括 `alert`, `attachment`, `backup`, `collection_record`, `contact`, `contract`, `custom_field`, `excel_config`, `file`, `ledger`, `notification`, `organization`, `ownership`, `party_hierarchy`, `permission_grant`, `primary_contact`, `recovery_strategy`, `session`, `system_dictionary`, `system_settings`, `task`, `user_role_assignment` 等）。

但计划的 `ResourceType` 仅覆盖 6 种，`capabilities` 端点当前可能也只生成这 6 种的能力项。**所有未覆盖资源类型的端点在 ABAC 模式下的行为（放行？拒绝？降级？）均未记录**。

**风险**: 如果后端 `capabilities` 生成器仅针对已注册的规则生成能力项，而大量端点使用了未注册资源类型（如 `attachment`, `notification`），则：
- 这些端点可能对所有人 403（过度拒绝）
- 或因后端降级逻辑而对所有人放行（过度放行）
- 两种情况均无前端感知

**建议**:
1. 在 §2 或 §4.4.1(B) 新增"后端资源类型完整清单 vs. 本期覆盖子集"对照表。
2. **显式声明不在 `ResourceType` 中的资源类型** 走何种降级策略（admin-only / 透传 / 忽略）。
3. 评估 `capabilities` 端点是否按需生成所有有效资源类型的能力项。

---

#### P0-3. `OwnershipRentStatistics` 字段迁移 `ownership_name` / `ownership_short_name` → `owner_party_name` 隐含后端契约变更，但 Phase 3 定义为"纯前端改造"

**位置**: §4.1 `types/rentContract.ts` 最后一条补充

**现状**:
计划要求将 `OwnershipRentStatistics.ownership_name` / `ownership_short_name` 同步迁移为 `owner_party_name`。但该字段来源于**后端 API 响应**——如果后端仍返回 `ownership_name`，纯前端改名会导致字段读空。

Phase 3 明确定位为"纯前端改造"（§7.3 回滚说明：后端在 Phase 2 已可兼容），但此处要求的字段名变更超出了纯重映射范畴（前端不是简单替换 `ownership_id` → `owner_party_id`，而是重命名一个"展示字段名"，这需要后端返回新名称的字段）。

**建议**:
1. 确认后端 API 是否在 Phase 2 已同步交付 `owner_party_name` 返回字段。
2. 若未交付，将 `OwnershipRentStatistics` 改为前端映射层处理（读 `ownership_name` 映射为 `owner_party_name` 展示），并标注后端交付节奏。
3. 或将该迁移推迟到 Phase 4（后端字段名统一后）。

---

#### P0-4. `project_to_response()` 硬编码 `ownership_relations=[]` 是 P3b 执行阻断项，但修复责任方和排期未明确闭环

**位置**: §4.2 `services/projectService.ts` / §1 衔接 / §5.1 P3b Entry

**现状**:
- 后端 `project_to_response()` 确认仍硬编码 `ownership_relations = []`（已通过代码实证验证）。
- P3b Entry 门禁要求"后端项目响应不再硬编码 `ownership_relations=[]`"，但此条阻断项**没有指定修复版本、负责人、联调窗口**。
- §1 的 "v1.26 承接归属补充" 将其归入"Phase 2-patch"，但 Phase 2 计划文档本身未记录此补丁。

**风险**: 阻断项无实际执行闭环，P3b 可能被无限期阻塞或"踩过"门禁强行启动。

**建议**:
1. 在 §1 新增"Phase 2-patch 工单追踪表"，为每个前置补丁指定具体负责人与 deadline。
2. 补充修复方案选型（返回实际 `ownership_relations` 数据 / 转换为 `party_relations` / 两者皆提供）。

---

#### P0-5. 多标签页 capabilities 静默 refresh 竞态未考虑

**位置**: §4.5 防风暴策略

**现状**:
文档的 cooldown 与 single-flight 设计均为**单页面（单 React 实例）粒度**。但实际用户可能同时打开多个浏览器标签页，每个标签共享同一 `AuthStorage`（localStorage/sessionStorage）。

场景：
1. 标签 A 触发 403 → 发起 refresh → 更新 AuthStorage。
2. 标签 B 同一秒也触发 403 → 发起 refresh（因为 single-flight 是 per-tab 的 in-memory 变量）。
3. 两个 refresh 请求同时到达后端，可能造成 token 双花（如果 refresh 端点有 token 消耗语义）或 capabilities 缓存不一致。

**建议**:
1. 在 §4.5 增加"跨标签页同步"策略——推荐使用 `BroadcastChannel` 或 `storage` 事件监听，确保一个标签完成 refresh 后通知其他标签直接使用新结果。
2. 或在 AuthStorage 写入时附带时间戳锁，其他标签检测到最近 N 秒内已有写入则跳过 refresh。

---

### P1 — 高风险

#### P1-1. `organizationService.ts` 行数描述不准确

**位置**: §4.3 IMPORTANT 注释

**现状**: 文档称"约 688 行"，实际代码库为 **598 行**。差异 ~15%。

**影响**: 工作量评估参考偏差。

**建议**: 更正为"约 600 行"或"598 行（截至当前提交）"。

---

#### P1-2. `types/capability.ts` 的 `AuthzAction` 联合类型缺少 `list` 的实际生产适用场景说明

**位置**: §4.1 `types/capability.ts`

**现状**:
- `AuthzAction` 包含 `list` 动作（源自后端 `authz.py:8`）。
- 但前端路由守卫实际使用场景中，`read` 和 `list` 的区分语义未明确。例如：访问资产列表页用 `canPerform('list', 'asset')` 还是 `canPerform('read', 'asset')`？访问资产详情页呢？
- 后端 capabilities 响应中，`actions` 数组可能包含 `['read', 'list']` 或仅 `['read']`。如果列表页使用 `list` 而后端只返回 `read`，该用户将无法访问列表页。

**建议**:
1. 在 `types/capability.ts` 或 §4.4.1(A) 明确 `read` vs `list` 的前端使用规则：
   - 路由守卫一律使用 `read`（含义为"可访问该资源"）
   - `list` 仅用于精细控制"可否调用列表 API"（如果有此需求）
2. 或在 capabilities 响应中保证 `actions` 始终包含 `read` 当 `list` 存在时（后端契约）。

---

#### P1-3. `default_organization_id` 波及范围未完整盘点

**位置**: §4.2 `services/systemService.ts` / §4.1 `types/auth.ts`

**现状**:
文档在 `systemService.ts` 节说明"Phase 3 保持提交 `default_organization_id` 不变"，并在 `types/auth.ts` 节说明保持兼容。但实际波及 **5 个文件**：

| 文件 | 引用 |
|------|------|
| `types/auth.ts` | `User.default_organization_id?: string` |
| `services/systemService.ts` | 接口定义 + API 参数映射（6 处） |
| `pages/System/UserManagement/index.tsx` | 传值 |
| `pages/System/UserManagement/components/UserFormModal.tsx` | 表单字段 |
| `hooks/usePermission.tsx` | `authData.user.default_organization_id` |

文档仅在 `systemService.ts` 和 `types/auth.ts` 两处提及此字段，**UserManagement 页面和 `usePermission.tsx` 的引用未显式标注为 Phase 3 例外**。当 P3e 门禁 grep 扫描 `\borganization_id\b` 时，需确认 `default_organization_id` **不会**被词边界匹配命中（实际上不会，因为 `\b` 包围 `organization_id` 不匹配 `default_organization_id` 的前缀）。

**建议**:
1. 在 §4.1 `types/auth.ts` 或 §4.2 `services/systemService.ts` 新增完整波及文件清单。
2. 显式注释 `\borganization_id\b` grep 不会命中 `default_organization_id` 的原因（目前只有 §6.2 的一行注释提到）。

---

#### P1-4. `mocks/fixtures.ts` 旧字段引用不完整——仅有 `ownership_entity`，但计划将其归入多字段迁移

**位置**: §4.3 测试工厂与 Mock / §3.1

**现状**:
- §3.1 统计中将 `mocks/fixtures.ts` 列入 `ownership_entity` 的 18 个影响文件之一。
- 但 §4.3 的测试工厂表格列出 `mocks/fixtures.ts` 的变更为"旧主体字段 → 新字段"，暗示多字段迁移。
- **实际**：该文件仅包含 `ownership_entity: '测试权属方'`（在 `mockAsset` 中），不包含 `organization_id`、`ownership_id`、`management_entity`。

**影响**: 执行者可能花时间查找实际不存在的字段。

**建议**: 将 `mocks/fixtures.ts` 变更说明精确化为"仅 `ownership_entity → owner_party_name（或等价展示字段）`"。

---

#### P1-5. Excel 模板字段迁移的 i18n 盲区——grep 门禁可能无法捕获中文列名

**位置**: §4.6 / §5.1 P3e Exit

**现状**:
- P3e 门禁依赖 grep 扫描 `\borganization_id\b`、`\bownership_ids?\b` 等英文字段名。
- 但 Excel 导入导出模板的列名通常为**中文**（如"权属主体"、"管理主体"、"权属方"）。如果模板配置中使用中文字段名映射到后端字段，grep 扫描完全无法发现。
- `assetExportConfig.ts` 和 `rentContractExcelService.ts` 中的列映射可能以中文为键名。

**建议**:
1. 在 §6.2 增加中文旧字段名 grep 扫描：`grep -rEl "权属主体|权属方|管理主体|[所有]方编号" frontend/src/ --include="*.ts" --include="*.tsx"`。
2. 或在 P3e Exit 增加"模板下载 + 人工检查列名"的冒烟步骤（§6.3 第 12/13 条已有但未覆盖中文列名检查）。

---

#### P1-6. `PartyContact` 管理 UI 未规划——仅定义类型但无页面

**位置**: §3.2 新增文件 / §4.1 `types/party.ts`

**现状**:
- `types/party.ts` 定义了 `PartyContact` 接口。
- 后端 Party CRUD 已包含 `/parties/{id}/contacts` 子端点（Phase 1 交付）。
- 但 Phase 3 无任何页面或组件规划来管理 PartyContact（创建/编辑/删除联系人）。
- `partyService.ts` 的 API 清单也未列出 contact 相关方法。

**风险**: 定义了类型和后端接口但不提供管理入口，导致联系人数据只能通过 API 直接操作，无前端管理能力。

**建议**:
1. 在 §3.2 或 §4.2 明确"Party 联系人管理"是否属于 Phase 3 范围。
2. 若属于，在 `partyService.ts` 增加 contact CRUD 方法，并在 PartySelector 或独立页面提供管理入口。
3. 若不属于，在 §2 "不包含" 列明确标注。

---

#### P1-7. P3d 路由守卫伪代码中 `Navigate to="/403"` 依赖 D7 决策但未提供 fallback 兜底

**位置**: §4.4.2 `routes/AppRoutes.tsx` + `App.tsx` 步骤 2

**现状**:
- D7 要求 P3d Entry 前冻结 `/403` 策略（新增路由 or 内联 fallback）。
- 但伪代码中 `route.fallback ?? <Navigate to="/403" replace />` 的 fallback 链假设 D7 选择 A（新增 `/403` 路由），注释说"仅当 D7 选择 A 且 /403 路由已存在"。
- **问题**：若 D7 最终选择 B（内联 fallback），伪代码需要调整为渲染内联 403 组件而非 `Navigate`。但伪代码只提供了一种实现。

**建议**: 提供两套伪代码或将 fallback 默认值改为内联 403 组件（更安全，不依赖路由存在性），并在注释中说明 D7-A 场景可替换为 `Navigate`。

---

#### P1-8. `AuthGuard.tsx` 使用 `useAuth()` 而非 `usePermission()`——与计划描述局部脱节

**位置**: §4.4.2 D5

**现状**:
- D5 说"`components/Auth/AuthGuard.tsx` 确认脱离主生效链，Phase 3 不做兼容改造"。
- 实际代码验证：`AuthGuard.tsx` 使用 `useAuth().hasPermission()` 进行权限判定。
- 而计划 §4.2 的 `AuthContext.hasPermission` 迁移路径说"P3d 内部实现改为调用共享纯函数……P3e 物理移除 `AuthContext.hasPermission`"。
- **矛盾**：如果 P3e 移除 `AuthContext.hasPermission`，`AuthGuard.tsx`（未被改造）将编译断裂。

D5 说"仅标记 `@deprecated` 并禁止新增主路由引用"，但没有处理 `AuthContext.hasPermission` 移除后 `AuthGuard` 的编译兼容性。

**建议**:
1. 在 P3e 收口清单（§4.6 第 7 条 Router 级联）中明确增加 `AuthGuard.tsx` 的处置：同步删除或保留 `hasPermission` 兼容壳。
2. 或将 `AuthContext.hasPermission` 的物理移除从 P3e 推迟到 Phase 4（与 Router 体系整体重构同批）。

---

#### P1-9. P3e 删除 `usePermission.tsx` 的 Router 级联处置清单仅提供"二选一"但未指定默认方案

**位置**: §4.6 第 7 条

**现状**:
v1.28 新增了 Router 级联处置清单，列出 `RouteBuilder.tsx`、`DynamicRouteContext.tsx`、`DynamicRouteLoader.tsx`、`index.ts` 四个文件。要求"至少实现'迁移到 `useCapabilities` 或物理删除'二选一"。

但：
- 未指定默认推荐方案。
- 未评估"物理删除"的影响——如果这些 Router 组件被其他地方间接引用（即使主路由不走该路径），删除可能导致编译错误的级联扩散。
- `components/Router/index.ts` 是整个 Router 目录的汇总导出，删除它会影响所有 `import from '@/components/Router'` 的文件。

**建议**:
1. 明确推荐方案（建议默认物理删除，因为主路由已确认不走 Router 体系）。
2. 在执行前增加 `grep -rEl "from.*components/Router" frontend/src/ --include="*.ts" --include="*.tsx"` 影响评估步骤。
3. 若删除范围过大，降级为"迁移到 `useCapabilities` 空壳"。

---

#### P1-10. 静默 refresh 重放幂等约束缺少"用户确认"交互设计

**位置**: §4.5 第 6 条

**现状**:
v1.27 新增了"写操作（POST/PUT/PATCH/DELETE）仅在 `replaySafe=true` 时重放"的约束。但：
- 未定义"不重放时"的用户体验——是显示 Toast？Modal？自动关闭操作面板？
- "返回可恢复提示"的具体 UI 形态未设计。
- 用户不知道操作是否已部分成功（服务端可能已受理但 403 发生在响应拦截阶段）。

**建议**: 在 §4.5 或 `AuthzErrorBoundary.tsx` 设计中补充写操作失败的具体 UI 交互流程：
- 弹出 Modal："操作未完成，权限已刷新，是否重试？"
- 若操作可能已部分成功（如批量导入），提示"请检查操作结果后再决定"。

---

### P2 — 改进建议

#### P2-1. §3.1 `organization_id` 分布列表中缺少 `services/systemService.ts`

**位置**: §3.1 表格

**现状**: 9 个文件的"主要分布"列中，`services/systemService.ts` 未被列出（但实际包含 `organization_id`，通过 `default_organization_id → organization_id` 参数映射）。

**说明**: 严格来说 `systemService.ts` 中的是 `organization_id` API 参数名（非主体字段），但可能造成阅读者遗漏。

**建议**: 在分布列中补充 `services/systemService（API 参数映射，Phase 3 例外）`。

---

#### P2-2. `party_relations` 在前端不存在任何引用——零起步迁移

**位置**: §4.1 `types/project.ts` / §4.2 `services/projectService.ts`

**现状**:
- 前端代码库中 `party_relations` **零命中**——该字段完全不存在于当前代码中。
- 后端 `project_to_response()` 也不返回 `party_relations`。
- 即便后端修复了 `ownership_relations=[]` 硬编码，也只返回 `ownership_relations`，不返回 `party_relations`。

**问题**: P3b 要求 `projectService` 增加兼容适配层支持 `party_relations[]` 消费，但适配层的**数据来源**（后端 `party_relations[]` 字段）本身是另一个 Phase 2-patch 阻断项。计划中"backend delivers `party_relations[]`"的承诺没有落地证据。

**建议**: 明确 `party_relations` 的后端交付形式：
- 方案 A：后端在 `ProjectResponse` 中新增 `party_relations` 字段（需后端改动）。
- 方案 B：前端 `projectService` 从 `ownership_relations[]` 自行转换为 `party_relations[]`（不依赖后端，但需要映射数据）。
- 选定方案后回写文档。

---

#### P2-3. `FrontendPartyHierarchyEdge` 类型用途不明确

**位置**: §4.1 `types/party.ts`

**现状**: 定义了 `FrontendPartyHierarchyEdge`（含 `parent_party_id` 和 `child_party_id`），说明"后端层级接口返回子 Party ID 列表（`list[str]`），此接口用于补充 parent/child 边关系"。

但：
- 后端 `GET /parties/{id}/hierarchy` 返回的是 `list[str]`（后代 Party ID 列表），不是 parent-child 边关系。
- 前端从 `list[str]` 到 `FrontendPartyHierarchyEdge` 的转换逻辑未定义——如何知道哪个 Party 是哪个的 parent？
- Phase 3 没有任何组件或页面实际消费这个类型。

**建议**: 如果 Phase 3 不使用 Party 层级树，移除 `FrontendPartyHierarchyEdge` 类型定义（避免死代码）。如需保留，补充转换逻辑说明。

---

#### P2-4. `owner_name` / `owner_contact` / `owner_phone` 在新合同创建时的填充逻辑未说明

**位置**: §4.1 `types/rentContract.ts`

**现状**: 文档声明"保留 `owner_name`, `owner_contact`, `owner_phone`（只读快照）"。但未说明：
- 创建新合同时，这些快照字段从何处获取？是后端根据 `owner_party_id` 自动填充，还是前端从 PartyContact 读取后手动填入？
- PartySelector 选中后，是否需要联动回填这些快照字段？

**建议**: 在 §4.3 合同创建组件变更中明确快照字段的填充链路。

---

#### P2-5. `Capability.data_scope` 定义为"用户级全局范围"但 per-resource 限制未体现

**位置**: §4.1 `types/capability.ts`

**现状**:
```typescript
data_scope: {
  owner_party_ids: string[];
  manager_party_ids: string[];
}
```
注释说"`data_scope` 为用户级全局范围（subject scope），非按 resource 差异化返回"。但设计文档 §5.1 的响应示例将 `data_scope` 放在每个 `CapabilityItem`（per-resource）级别下。

**矛盾**: 如果 `data_scope` 在每个 capability 项中相同（全局），为什么放在 per-resource 的结构体中？这会造成数据冗余。如果实际上按 resource 差异化，注释就是错误的。

**建议**: 与后端确认 `data_scope` 是否按 resource 差异化返回，并修正注释或结构体位置。

---

#### P2-6. 门禁排除单源清单（§5.2）缺少 `*ownershipService*` 和 `*OwnershipManagementPage*`

**位置**: §5.2

**现状**: 排除清单包含 `--exclude=*organizationService*` 和 `--exclude-dir=Organization`，但缺少对等的权属模块排除：
- `*ownershipService*`（§4.2 已标记 `@deprecated`）
- `*OwnershipManagementPage*`（§4.3 标记 deprecated / 无迁移动作）

如果 `ownershipService.ts` 内部仍有 `ownership_id` 引用（它作为权属管理服务，几乎肯定有），P3e 门禁 grep 将误报。

**建议**: 在 §5.2 排除清单增加 `--exclude=*ownershipService*` 和 `--exclude=*OwnershipManagementPage*`（或整个 Ownership 目录）。

---

#### P2-7. P3d Exit `usePermission` 残留扫描的 `--exclude` 只排除了文件名，未排除 `@deprecated` 注释中的字符串命中

**位置**: §5.1 P3d Exit

**现状**: `! grep -rEl "usePermission" frontend/src/ --include="*.ts" --include="*.tsx" --exclude="usePermission.tsx" --exclude-dir="__tests__"`

该命令会匹配**注释中的 `usePermission`**（如 `// @deprecated: use useCapabilities instead of usePermission`）。如果修改后的文件中添加了迁移注释引用旧名称，grep 将误报。

**建议**: 改为 `grep -rEl "\busePermission\b" ... | xargs grep -L "@deprecated"` 或接受注释命中为合理残留。

---

#### P2-8. P3a Entry 的 Party 数量容量评估 SQL 仍使用 `status = 'active'`，但后端 Party 模型可能无该状态值

**位置**: §5.1 P3a Entry

**现状**: 门禁命令 `SELECT COUNT(*) FROM parties WHERE status = 'active';`。需确认后端 Party 模型的 `status` 枚举是否包含 `active`。如果 Party 使用的是 `enabled/disabled` 或其他状态约定，SQL 将返回 0 并可能误触发风险提示。

**建议**: 与后端确认 Party.status 枚举值，或使用退化版本 `SELECT COUNT(*) FROM parties;`（文档已提到但语义为备选）。

---

#### P2-9. `capabilityService.ts` 的缓存 TTL（10 分钟）与 cooldown（30 秒）的关系未阐明

**位置**: §4.2 `services/authService.ts` / `capabilityService.ts`

**现状**:
- capabilities TTL = 10 分钟（超时视为冷缓存）。
- 静默 refresh cooldown = 30 秒。
- 未说明：TTL 到期后会主动拉取还是等下次 403 触发？如果主动拉取，是否受 cooldown 约束？

**建议**: 明确 TTL 过期行为——推荐"TTL 过期后在下次 `canPerform` 调用时惰性刷新（不主动拉取），但不受 cooldown 约束（cooldown 仅约束 403 触发的 refresh）"。

---

#### P2-10. 项目详情页"无资产项目显示'待补绑定'标签"缺少具体实现标准

**位置**: §4.3 项目模块

**现状**: 仅说明"无资产项目显示'待补绑定'标签"和"面积统计显示 `N/A`"，但：
- "无资产"的判定条件未明确（`project.assets.length === 0`？`project.asset_count === 0`？后端是否返回此字段？）
- 标签的 UI 位置、样式（Tag 组件？Banner？）未指定。
- `N/A` 的展示方式（灰色文本？Tooltip 解释？）未设计。

**建议**: 在 §4.3 或 §6.3 冒烟矩阵中补充判定条件和 UI 标准，避免实现自由度过大。

---

#### P2-11. §8 文件影响总览的"Tests 新增 6"与实际新增文件清单仅 6 个测试文件一致，但修改 10+ 未列出

**位置**: §8

**现状**: "Tests: 新增 6 / 修改 10+" 但修改的 10+ 测试文件未列出清单。考虑到所有被修改的组件（30+ components）可能各自有测试文件，10+ 可能偏低。

**建议**: 补充"修改测试"的预估基于（被修改组件中有测试的占比 × 组件数）并列出已知待修改测试文件。

---

#### P2-12. `RentContractExcelImport.tsx` 和 `assetImportExportService.ts` 的"契约审计 + 回归验证"缺少具体操作规程

**位置**: §4.3 / §4.6

**现状**: v1.28 将这两个文件从"字段迁移"调正为"契约审计 + 回归验证"。但"审计"和"验证"的具体步骤未定义——审计什么？验证什么？通过标准是什么？

**建议**: 补充最小审计清单：
1. 确认模板列名不含旧字段中文名。
2. 导入一条测试数据，验证新字段落库正确。
3. 导出后对比模板列名与后端接口字段名。

---

### P3 — 文档质量

#### P3-1. 文档历史（§10）过于庞大，占据文档约 30% 篇幅

**位置**: §10

**现状**: v1.11 ~ v1.28 的详细变更记录占据约 430 行（1479 行中的 ~29%），且 v1.0-v1.10 已声明保留在 Git 历史中。文档的"信噪比"偏低——实施者需要穿越大量历史变更才能找到当前有效内容。

**建议**:
1. 仅保留最近 3 个版本（v1.26/v1.27/v1.28）的详细变更记录。
2. 其余折叠到 `<details>` 标签或移至附录文件。

---

#### P3-2. Gantt 图与实际依赖关系的表达力不足已在注释中说明，但可通过不同图表类型改善

**位置**: §0

**现状**: 文档自己承认"Mermaid Gantt 对 AND 双前置表达能力有限"。但可以使用 Mermaid `graph` 图（已在 §5 使用）完全替代 Gantt 来表达依赖关系。

**建议**: 在 §0 增加 graph 图或将 Gantt 改为 graph，准确表达所有 AND/OR 依赖（包括 P3b 需要 P2c+P3a 两个前置、P3d 需要 P2d+P3c 两个前置）。

---

#### P3-3. §4.4.1(B) 资源映射表的"后端 resource_type"列对 `user`、`role`、`system` 的描述含混

**位置**: §4.4.1(B)

**现状**:
- `user` 行写"后端 resource_type = `user` + `asset`（混用）"——实际含义是后端部分 user 端点使用 `resource_type="user"`，部分使用 `resource_type="asset"` 作为 catch-all。但"混用"一词容易误解为同一个端点同时使用两个值。
- 类似地，`system` 行写"`system` + `asset`（混用）"。

**建议**: 重组描述为："`user` 发现于 `users.py`（前端需按 adminOnly 守卫）；其他系统管理端点 fallback 到 `asset`"。

---

#### P3-4. 门禁命令中 bash 与 PowerShell 二分提供，但部分门禁仅有 bash 版

**位置**: §5.1 / §6.2 vs §6.4

**现状**: §6.4 提供了"核心门禁 PowerShell 等价命令"，但仅覆盖 P3b Entry、P3d Entry/Exit、P3e Entry/Exit 的子集。§5.1 中大量 Exit grep 命令（如 P3b Exit 的服务层旧字段零引用、P3c Exit 的组件测试）仍只有 bash 版。

**建议**: 将 §5.1 各子阶段的关键门禁命令统一在命令后方附注 PowerShell 等价写法，或将 §6.4 扩展为完整覆盖。

---

#### P3-5. 伪代码 `renderProtectedElement` 中使用了 `<Route>` 但缺少 `react-router-dom` import 声明

**位置**: §4.4.2 步骤 2

**现状**: 伪代码直接使用 `<Route>`、`<Navigate>`、`<Suspense>` 但未标注所需 import，且当前 `App.tsx` 已有这些 import。这对伪代码来说可以接受，但建议在注释中明确这些组件已在现有文件中 import。

---

#### P3-6. 部分表格的"变更"列过于简略

**位置**: §4.3 多处修改表格

**现状**: 如"合同模块"表中 `ContractFilterBar.tsx` 的变更仅写"筛选条件适配"——对执行者来说缺乏足够信息判断具体改什么。

**建议**: 至少列出受影响的字段名（如"`ownership_id` → `owner_party_id` 过滤参数"）。

---

#### P3-7. §6.2 运行时请求载荷旧字段拦截的正则可能误报

**位置**: §6.2

**现状**: 正则 `/(^|["'{,\s])(organization_id|ownership_id|...)(["'}:,\s]|$)/` 会匹配 **注释、日志字符串、错误消息** 中的旧字段名。虽然有注释说明"仅在 dev/test 开启"，但高频误报会导致开发者忽略此拦截。

**建议**: 将拦截范围限定到 `config.data`（请求体）和 `config.params`（查询参数）的 JSON 序列化结果，排除 headers 和 url 中的匹配。

---

## 2. 上游文档一致性检查

### 与架构设计 v3.9 的对齐

| 检查项 | 设计文档 | Phase 3 计划 | 结论 |
|--------|---------|-------------|------|
| capabilities 响应结构 | `{version, generated_at, capabilities: [{resource, actions, perspectives, data_scope}]}` | 一致 | ✅ |
| 动作枚举 | `create\|read\|list\|update\|delete\|export` | 一致 + `backup` 临时豁免 | ✅ 偏离已声明 |
| `X-Authz-Stale` 头 | "建议"级别 | 降级为 403+标识 | ✅ 偏离已声明(§9 第5条) |
| 防风暴规格 | 30s cooldown + single-flight + 1次重试 | 一致 | ✅ |
| `perspectives` 含义 | per-resource 的 owner/manager 视角 | 前端 override 方案 B | ✅ 偏离已声明 |
| `data_scope` 粒度 | per-CapabilityItem | 注释称"用户级全局" | ⚠️ 见 P2-5 |
| `rent_ledger` 资源 | §5.1 提及 | 未纳入 ResourceType | ❌ 见 P0-1 |

### 与 Phase 2 计划的对齐

| 检查项 | Phase 2 | Phase 3 | 结论 |
|--------|---------|---------|------|
| 旧字段移除条件 | "Phase 3 完成后" | P3e Exit + §9 交接 | ✅ |
| 策略包 seed 迁移 | `20260219_...` + `20260221_...` | 引用正确 | ✅ |
| `ownership_relations` 修复 | 未在 Phase 2 计划中记录 | 作为 Phase 2-patch 阻断项 | ⚠️ 无追踪 |
| `parties?search=` 接口 | Phase 2 未规划 | 作为 P3b 硬门禁 | ⚠️ 无追踪 |
| `require_authz` 资源名统一 | 未规划 | Phase 3 显式排除（§2） | ✅ |

### 与 Phase 1 计划的对齐

| 检查项 | Phase 1 | Phase 3 | 结论 |
|--------|---------|---------|------|
| `certificate_party_relations` 表 | 已创建 | `types/party.ts` 定义对应类型 | ✅ |
| `capabilities` 端点 | 已上线 | Phase 3 消费 | ✅ |
| Party CRUD 端点 | 已上线（无 search） | Phase 3 消费 + search 门禁 | ✅ |

---

## 3. 代码库实证验证快照

### 旧字段引用统计交叉验证（排除测试目录）

| 字段 | 计划数 | 实测数 | 状态 |
|------|--------|--------|------|
| `organization_id` | 9 文件 | **9 文件** | ✅ 匹配 |
| `ownership_id` | 25 主链 + 1 test-utils | **25 + 1** | ✅ 匹配 |
| `management_entity` | 8 文件 | **8 文件** | ✅ 匹配 |
| `ownership_entity` | 18 主链 + 1 test-utils | **18 + 1** | ✅ 匹配 |
| `usePermission` | 7 文件 | **7 文件** | ✅ 匹配 |
| `canAccessOrganization` | 1（定义），0（生产消费） | **1 / 0** | ✅ 匹配 |

### 新增文件不存在确认

| 文件 | 状态 |
|------|------|
| `types/party.ts` | ✅ 不存在（待创建） |
| `types/capability.ts` | ✅ 不存在（待创建） |
| `types/dataPolicy.ts` | ✅ 不存在（待创建） |
| `services/partyService.ts` | ✅ 不存在（待创建） |
| `owner_party_id` / `manager_party_id` / `tenant_party_id` | ✅ 前端零引用（完全新增） |

### 后端契约现状

| 检查项 | 状态 |
|--------|------|
| `GET /api/v1/parties` 无 `search` 参数 | ✅ 确认（阻断项） |
| `project_to_response()` 硬编码 `ownership_relations = []` | ✅ 确认（阻断项） |
| `GET /api/v1/auth/me/capabilities` 可用 | ✅ 确认 |
| `require_authz` 资源类型 31+ 种 | ✅ 确认（见 P0-2） |
| 台账端点使用 `resource_type="ledger"` | ✅ 确认（见 P0-1） |
| `frontend/.env.production` 不存在 | ✅ 确认（D9 已提前置步骤） |
| `rentContractExcelService.ts` baseUrl = `/api/rental` | ✅ 确认 |
| `apiClient.baseURL = VITE_API_BASE_URL \|\| '/api/v1'` | ✅ 确认 |

---

## 4. 前两轮审阅闭合状态

### v1.26 深审（8 项）

| 原始问题 | v1.28 是否闭合 | 备注 |
|----------|---------------|------|
| `organization_id` 统计偏差 (3→9) | ✅ 已修正为 9 | |
| `usePermission` 统计偏差 (4→7) | ✅ 已修正为 7 | |
| 门禁排除规则散写 | ✅ §5.2 单源清单 | 但仍不完整（见 P2-6） |
| 死代码处置策略缺失 | ✅ v1.28 新增 Router 级联处置 | 但未指定默认方案（见 P1-9） |
| Feature flag 无生产保障 | ✅ D9 + .env.production 前置 | |
| 幂等重放风险 | ✅ v1.27 增加 replaySafe | 但缺用户交互设计（见 P1-10） |
| Windows 门禁命令缺失 | ✅ §6.4 新增 | 但覆盖不完整（见 P3-4） |
| grep 代替行为验证 | ⚠️ P3d Exit 增加 E2E | 但 E2E tag `@authz-minimal` 尚未实现 |

### v1.27 综审（24 项重点）

| 原始问题 | v1.28 是否闭合 |
|----------|---------------|
| `ownership_id` 统计口径 (26→25) | ✅ 修正为 25+1 |
| `ownership_entity` 统计口径 (19→18) | ✅ 修正为 18+1 |
| 虚增迁移项（assetImportExportService 等） | ✅ 调正为契约审计 |
| `.env.production` 不存在 | ✅ D9 增加创建前置 |
| `require_authz` 资源名差异 | ⚠️ 部分记录但未完整覆盖（见 P0-2） |
| 删除 `usePermission` 级联编译断裂 | ✅ v1.28 增加 Router 处置清单 |
| `canAccessOrganization` 生产消费为 0 | ✅ 已记录 |

---

## 5. 修复优先路径建议

| 顺序 | 问题编号 | 行动 | 阻断关系 |
|------|----------|------|----------|
| 1 | P0-1 | `ResourceType` 增加 `ledger`，补充台账路由权限映射 | P3d 阻断 |
| 2 | P0-2 | 新增后端资源类型完整清单 vs. 覆盖子集对照表 | P3d 阻断 |
| 3 | P0-3 | 确认 `OwnershipRentStatistics` 字段可映射性 | P3a/P3e 阻断 |
| 4 | P0-4 | 创建 Phase 2-patch 工单追踪表 | P3b 阻断 |
| 5 | P0-5 | 增加跨标签 refresh 同步策略 | P3d 阻断 |
| 6 | P1-1~P1-10 | 按子阶段关联批量修复 | 对应子阶段 Entry 前 |
| 7 | P2-1~P2-12 | 执行期渐进整改 | 不阻断 |
| 8 | P3-1~P3-7 | 后续文档维护 | 不阻断 |

---

## 6. 附录：审阅覆盖矩阵

| 文档章节 | 审阅深度 | 交叉验证 |
|----------|----------|----------|
| §0 路线图 | 精读 | Gantt 依赖 vs. Entry 门禁 |
| §1 衔接 | 精读 | Phase 2 计划 / 后端代码 |
| §2 范围界定 | 精读 | — |
| §3 影响分析 | 精读 | **全量 grep 交叉验证** |
| §4.1 类型定义层 | 精读 | 后端 Schema / 设计文档类型 |
| §4.2 服务层 | 精读 | 后端 API 端点 / baseURL 实证 |
| §4.3 页面层 | 精读 | 组件文件存在性 |
| §4.4 权限重构 | 精读 | PERMISSIONS 常量 / ROUTE_CONFIG / AuthGuard / AuthContext 实证 |
| §4.5 防风暴 | 精读 | 设计文档 §5.2 |
| §4.6 Excel + 收口 | 精读 | 服务文件旧字段扫描 |
| §5 门禁 | 精读 | 命令可执行性 / 排除清单完整性 |
| §6 验证计划 | 精读 | package.json scripts |
| §7 回滚 | 精读 | — |
| §8 文件总览 | 精读 | — |
| §9 交接 | 精读 | Phase 2 §4.5 |
| §10 文档历史 | 扫读 | — |

---

**审阅人**: GitHub Copilot  
**审阅完成日期**: 2026-02-22
