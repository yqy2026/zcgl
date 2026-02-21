# Phase 3 实施计划深度审阅报告

**审阅对象**: [Phase 3 实施计划 v1.21](../plans/2026-02-20-phase3-implementation-plan.md)  
**审阅日期**: 2026-02-21  
**审阅类型**: 架构一致性 · 可执行性 · 风险盲区 · 遗漏分析  
**严重性分级**: P0 (阻断) · P1 (高风险/必须修复) · P2 (中等/建议修复) · P3 (低风险/改进建议)

---

## 执行摘要

Phase 3 计划 v1.21 已达到相当高的成熟度，但经与代码库实际状态交叉验证，当前版本应归类为 **2 项 P0 阻断级问题**、**8 项 P1 高风险问题**、**8 项 P2 中等问题** 和 **5 项 P3 改进建议**。其中原文 `P0-1` / `P0-2` 经二次复核后应降级为 P1。最关键的发现修正为：**capabilities 来源于 ABAC policy rules，而非仅由 endpoint 上 `require_authz` 字面资源名决定**；当前真实风险是“策略种子/角色绑定/环境迁移一致性缺少门禁验证”，而非“资源类型在后端不存在”。

---

## P1（原 P0 降级项）

### P0-1（严重性修正：P1）· capabilities 并非仅产出 `asset`，核心风险是覆盖验证缺失

**位置**: §4.4.1 / §4.4.2 — 前端路由守卫 `canPerform(action, resource)` 设计

**现状**:
- `GET /api/v1/auth/me/capabilities` 的资源集合来自 ABAC 规则聚合（`AuthzService.get_capabilities`），不是从 `require_authz` 调用点直接推导。
- Phase 2 策略种子已包含 `project` / `rent_contract` / `property_certificate` / `party` 资源。
- 相关业务端点已存在对应 `resource_type`（如 project / rent_contract / property_certificate / party），并非“全量 asset”。
- 但 `auth/system` 相关接口仍大量使用 `resource_type="asset"`，存在资源语义混合现象。

**影响**:
- 原“前端多资源判定将全面失效”结论过强，不符合当前代码状态。
- 真实风险变为部署/数据层风险：若策略种子未执行、角色策略包未绑定或环境数据漂移，`capabilities` 仍可能缺少预期资源，导致部分路由误拦截。

**计划盲区**:
- 计划未把“capabilities 资源覆盖抽检”定义为硬门禁。
- 计划未明确在不同环境（本地/测试/预发）如何验证角色绑定与策略种子一致性。

**建议修复**:
1. 将 `GET /auth/me/capabilities` 抽检纳入 P3b Entry：至少验证 `asset`、`party`、`project`、`rent_contract`、`property_certificate` 是否按预期出现（按角色矩阵校验）。
2. 将“策略种子已迁移 + 角色策略包已绑定 + 会话重登后 capabilities 生效”设为同一组门禁，而不是仅做代码 grep。
3. 保留回退策略：当目标资源缺失时仅对对应模块启用临时 `adminOnly`，避免全站级回退。

### P0-2（严重性修正：P1）· Organization ↔ Party 非“零同步”，但缺少在线闭环门禁

**位置**: §4.3 IMPORTANT（组织架构并行策略）

**现状**:
- 后端确有迁移与回填脚本：组织/权属到 Party 映射、`default_organization_id` 到 `user_party_bindings` 回填。
- `Party` 已提供 `external_ref` 字段承载外部对象映射。
- 但运行时在线链路中，`organization` 与 `party` 仍是并行体系，缺少自动双写/自动校验闭环。
- `User.default_organization_id` 通过 FK 指向 `organizations.id`，不指向 `parties.id`
- ABAC `data_scope` 使用 `owner_party_ids`/`manager_party_ids`（来自 `parties` 表）

**影响**:
- “零同步”表述不准确，但“未形成强制闭环”问题仍成立。
- 如果映射脚本未执行或结果未验收，`default_organization_id` 与 `party` 可见域会发生偏差，导致用户视角权限异常。
- ABAC 判定基于 `party_ids`，而用户管理仍展示 organization 归属，迁移窗口内语义易混淆。

**计划盲区**:
- §4.3 的 v1.21 执行冻结默认方案 B（组织页只读），但**没有定义"只读后 Organization 数据如何通过 Party 体系被消费"**
- 也未说明：当 P3b 开始使用 `PartySelector` 后，那些原来通过 `organization_id` 筛选的业务（如用户列表按组织过滤）将如何过渡

**建议修复**:
1. 将映射脚本执行与产物校验写成硬门禁：`org_to_party_map` 覆盖率、未匹配清单、抽样核验。
2. P3b Entry 增加一致性门禁：校验 `organizations` 与 `parties(external_ref)` 覆盖关系及 `user_party_bindings` 回填结果。
3. `default_organization_id` 迁移窗口内保留，但在文档中明确其“兼容字段”语义与退出条件。

---

## P0 — 阻断级问题（当前有效项）

### P0-3 · `assetFormSchema.ts` 中 `ownership_id` 为 required 验证——计划遗漏此文件

**位置**: §4.1 / §4.3 资产模块变更清单

**现状**:
`frontend/src/assetFormSchema.ts` 中 `ownership_id` 使用 `z.string().min(1, '权属方不能为空')` 作为 **必填字段验证**。`management_entity` 为 `z.string().optional()`。

**影响**:
- 计划 §4.3 虽然在表格中提及了 `assetFormSchema.ts`（"表单验证 schema 字段替换"），但：
  1. 未列入 §4.1 类型层变更（它不在 `types/` 目录下），P3a 改不到它
  2. 未明确 `ownership_id` 在此文件中是**必填验证**而非仅类型定义——如果 P3b 只改 service 参数名，但 zod schema 验证仍要求旧字段，表单提交将报"权属方不能为空"但实际新字段名已变
  3. P3e 的旧字段零引用 grep 命令中 include 是 `*.ts`/`*.tsx`，此文件（`assetFormSchema.ts`）会被命中——但前面几个子阶段若不改此文件，将导致运行时表单验证与 API 字段名不一致

**建议修复**:
1. 将 `assetFormSchema.ts` 显式列入 P3b 服务层变更，与 `assetService.ts` 同步改名
2. 验证字段名从 `ownership_id` → `owner_party_id`（required）, `management_entity` → `manager_party_id`（optional）
3. 在 P3b Exit 门禁中增加：`! grep -El "ownership_id|management_entity" frontend/src/assetFormSchema.ts`

---

### P0-4 · `pdfImport.ts` 迁移范围严重低估——`OwnershipMatch`/`matched_ownerships` 未纳入计划

**位置**: §4.1 `types/pdfImport.ts` 变更描述

**现状**:
计划仅提及 "`ownership_id` 标记 `@deprecated`，新增 `owner_party_id?: string`"（即 `ConfirmedContractData.ownership_id`）。但实际文件还包含：
- `OwnershipMatch` 接口（`id`/`ownership_name`/`similarity`）→ 需重命名为 `PartyMatch`
- `MatchingResult.matched_ownerships: OwnershipMatch[]` → 需重命名为 `matched_parties`
- 这两个类型用于 PDF 合同智能导入的权属方匹配逻辑——改名将影响 `pdfImportService.ts` 的调用链

**影响**:
- P3a 仅对 `ownership_id` 标记 deprecated，但遗漏了 `OwnershipMatch`/`matched_ownerships` 的迁移
- P3e 门禁 grep 会命中 `ownership_name` → 但该字段在计划中无迁移路径
- PDF 导入功能在迁移后可能静默失败（前端发送 `party_id` 但后端期望 `ownership_id`，或反之）

**建议修复**:
1. §4.1 `types/pdfImport.ts` 变更描述补齐 `OwnershipMatch` → `PartyMatch`、`matched_ownerships` → `matched_parties` 迁移
2. §4.2 `services/pdfImportService.ts` 需同步更新 `ConfirmedContractData` 构造代码
3. 确认后端 PDF 导入端点是否已切换为 `party_id` 接收——若未切换，需列为 P3b 的后端前置门禁

---

## P1 — 高风险问题

### P1-1 · `AuthStorage.AuthData` 接口无 `capabilities` 字段——持久化链路未设计

**位置**: §4.2 `services/authService.ts` 与 `contexts/AuthContext.tsx`

**现状**:
`AuthStorage` 的 `AuthData` 接口仅包含 `{ user, permissions }`。计划 §4.2 提到"AuthStorage 字段定义：`capabilities?: Capability[]`、`capabilities_cached_at?: string`"，但这需要扩展 `AuthData` 接口并修改 `AuthStorageClass` 多个方法（`getAuthData`/`setAuthData`/`clearAuthData`）。

**遗漏**:
- §4.2 没有将 `utils/AuthStorage.ts` 列入修改文件清单
- `AuthData` 接口变更属于 P3a 类型层（它是 TypeScript 接口），但 `AuthStorage.ts` 在 `utils/` 目录，非 `types/` 目录——P3a 的"类型定义层"是否覆盖此文件不明确

**建议**:
1. 在 §4.1 或 §4.2 显式列入 `utils/AuthStorage.ts` 修改
2. 定义 `AuthData` 接口扩展：`capabilities?: Capability[]`、`capabilities_cached_at?: string`

---

### P1-2 · `restoreAuth()` 早期 `setUser` 触发渲染——capabilities 注入存在竞态窗口

**位置**: §4.2 `services/authService.ts` 与 `contexts/AuthContext.tsx`

**现状**:
`AuthContext.restoreAuth()` 在验证服务端会话前，先执行 `setUser(storedUser)`（约 L119），这立即使 `isAuthenticated = true`，触发 `ProtectedRoutes` 渲染。此时 capabilities 尚未加载。

**影响**:
- 计划要求 `capabilitiesLoading` 为 `true` 时路由守卫"只显示 loading，不执行 deny"
- 但早期 `setUser` 与 `capabilitiesLoading` 的初始化时序需要精确控制：如果 `capabilitiesLoading` 初始为 `false`（默认值），而 `isAuthenticated` 已为 `true`，路由守卫将在 capabilities 为空时执行 deny → `/403` 闪断

**计划覆盖度**:
- §4.2 提到"capabilitiesLoading 采用 token 感知初始化（建议 `hasToken ? true : false`）"，这部分设计正确
- 但**未明确定义 `hasToken` 的判定逻辑**——是读 `AuthStorage` 还是检查 cookie？在 httpOnly cookie 模式下前端无法直接读 token

**建议**:
1. 定义 `hasToken` = `Boolean(AuthStorage.getAuthData()?.user)` 或 `hasCookieValue(CSRF_COOKIE)` 
2. 在 `restoreAuth` 流程图中标注 `capabilitiesLoading` 状态变迁的精确时序
3. 考虑将早期 `setUser(storedUser)` 延迟到 capabilities 加载完成后（但需评估对用户感知的影响）

---

### P1-3 · capabilities 缓存比对策略实操困难——`generated_at` 比较需考虑时钟漂移

**位置**: §4.2 `capabilities` 存储策略（v1.21 修正）

**现状**:
- v1.21 修正后，计划改为"比较 `generated_at` 或能力列表签名（hash）后决定是否覆盖本地缓存"
- 后端 `generated_at` 是 `datetime.now(UTC)` 的服务端时间
- 本地缓存的 `capabilities_cached_at` 是前端写入的时间

**问题**:
- `generated_at` 是**每次请求都会变**的（每次调用 `datetime.now(UTC)` 都产生新值），因此单纯比较 `generated_at > cached_generated_at` 没有意义——它永远为 true
- 如果用能力列表 hash 比较，需要定义 hash 算法且在每次 refresh 时计算——这增加了实现复杂度
- 计划未明确"何时比较"和"比较失配时的行为"

**建议**:
1. 简化策略：每次 capabilities 拉取成功后**直接覆盖缓存**（无条件），以 `capabilities_cached_at`（前端本地时间）作为 TTL 起算点
2. 移除"比较 `generated_at` 后决定是否覆盖"的复杂逻辑——capabilities 数据量小（每次 < 2KB），全量覆盖无性能问题
3. TTL 10 分钟的失效检查保留即可

---

### P1-4 · Excel 服务层旧字段实际为零引用——计划改造工作量可能指向错误文件

**位置**: §4.6 Excel 导入导出模板适配

**现状**:
经代码库验证：
- `services/rentContractExcelService.ts` — **零** `ownership`/`ownership_id` 引用
- `services/asset/assetImportExportService.ts` — **零** `ownership`/`ownership_id` 引用

这两个文件的 Excel 导入导出逻辑通过 API 端点 (`/api/rental/excel/*`、`/api/v1/excel/*`) 进行，字段映射发生在**后端**而非前端 Excel 服务文件中。

**影响**:
- P3e 描述的"合同 Excel 模板：`ownership_id` 列 → `owner_party_id`"改造目标**在这些前端文件中不存在**
- 真正的模板字段定义可能在后端 Excel 模板生成逻辑中
- 前端 Excel 服务仅负责调用 download/upload API，不直接操控列名

**建议**:
1. 重新审查 Excel 列名映射的真实位置（可能在后端 `export_service.py` / `excel_template.py` 等处）
2. 前端 Excel 服务文件的改造范围缩减为：仅更新传递给 API 的**查询/过滤参数**（如 `AssetSearchParams.ownership_id` → `owner_party_id`），而非模板列名本身
3. 将"旧模板兼容提示"需求明确归属到后端（模板生成/解析端），或明确前端在 upload 前做客户端列名检查的位置

---

### P1-5 · `contactService.ts` 已是实体多态设计——但计划未将其与 `PartyContact` 对齐

**位置**: §3.2 新增文件预估 / §4.1 `types/party.ts`

**现状**:
前端已存在 `services/contactService.ts`，使用 `entity_type`/`entity_id` 多态设计，支持任意实体类型的联系人 CRUD。而计划在 `types/party.ts` 中定义了 `PartyContact` 接口。

**遗漏**:
- 计划未提及现有 `contactService.ts` 与新增 `PartyContact` 类型的关系
- 是否应该复用 `contactService.ts`（`entity_type='party'`）来管理 Party 联系人？
- 还是为 Party 联系人新建独立的服务调用（如 `partyService.getContacts(partyId)`）？
- 后端 Party 联系人端点 (`/parties/{id}/contacts`) 与现有 `/contacts` 通用端点的关系也未澄清

**建议**:
1. 在 §4.2 `partyService.ts` 中明确 Party 联系人消费策略：调用 `GET /api/v1/parties/{id}/contacts` 还是复用 `contactService.getEntityContacts('party', partyId)`
2. 确保 `PartyContact` 类型与 `contactService.ts` 的 `Contact` 类型字段兼容

---

### P1-6 · `types/asset.ts` 统计类型中 `ownership_entity` 引用未纳入迁移清单

**位置**: §4.1 `types/asset.ts` 变更描述

**现状**:
`types/asset.ts` 定义了多个统计类型：
- `OwnershipEntityStat`（接口名本身包含 `ownership`）
- `AreaStatistics.by_ownership_entity`
- 其他以 `ownership_entity` 为维度的聚合字段

**遗漏**:
- §4.1 仅提到标记 `@deprecated` 的字段（`ownership_id`、`management_entity`、`ownership_entity`），但未提及**接口名**本身需要重命名（如 `OwnershipEntityStat` → `OwnerPartyEntityStat` 或重构为通用名）
- `AreaStatistics.by_ownership_entity` 这个属性名改名将影响后端 API 响应结构——需要确认后端统计 API 是否也在 Phase 2 中同步变更
- P3e 门禁 grep 会命中 `ownership_entity` → 但若接口名 + 属性名均含 `ownership`，仅标记 deprecated 不足以通过门禁

**建议**:
1. 将 `OwnershipEntityStat` 接口及 `AreaStatistics.by_ownership_entity` 属性重命名纳入 P3a/P3b 迁移范围
2. 与后端统计 API 确认响应字段名变更时机

---

## P2 — 中等风险问题

### P2-1 · `RentStatisticsQuery.ownership_ids` 复数形式在 P3a 迁移目标未定义

**位置**: §5.1 P3e Exit / §6.2 旧字段零引用验证

**现状**:
`types/rentContract.ts` 中 `RentStatisticsQuery` 使用 `ownership_ids?: string[]`（**复数形式**）。v1.21 已在门禁 grep 中改为 `\bownership_ids?\b`（匹配单/复数）。

**潜在问题**:
- P3a 类型层 §4.1 仅提到标记 `ownership_id` deprecated，未显式提到 `ownership_ids`（复数）的迁移目标字段名——是 `owner_party_ids` 还是其他？
- 后端接口是否接受复数形式参数？

**建议**:
1. 在 §4.1 `types/rentContract.ts` 中显式列出 `RentStatisticsQuery.ownership_ids` → `owner_party_ids` 的映射
2. 确认后端统计查询端点参数名

---

### P2-2 · `hooks/useOwnership.ts` 未在迁移清单中

**位置**: §4.4 / 前端 hooks 目录

**现状**:
`frontend/src/hooks/` 目录下存在 `useOwnership.ts`。该 hook 大概率包含 `ownership_id` 相关逻辑。

**遗漏**:
- 计划全文未提及 `useOwnership.ts` 的迁移或 deprecated 处理
- 如果此 hook 在页面组件中被使用，P3c 页面改造时可能遗漏对该 hook 调用的替换

**建议**:
1. 审查 `useOwnership.ts` 内容，确定是否需要标记 deprecated 或重定向到 `useParty`/`partyService`
2. 在 §4.3 或 §4.4 中列入该 hook 的处理策略

---

### P2-3 · `/api/v1/parties` 不返回分页信封——`partyService` 无法判断结果是否截断

**位置**: §4.2 `partyService.ts` WARNING 注释

**现状**:
后端 `GET /parties` 返回 `list[PartyResponse]`（裸数组），无 `total`/`skip`/`limit` 信封。计划已提到"推荐同批交付分页信封"和"`result.length === limit` 仅为截断近似判断"。

**残留风险**:
- 当 Party 数量恰好为 `limit` 的整数倍时，前端会误判"已截断"
- `search` 接口如果也不返回分页信封，无法显示 "共 N 条结果"
- `PartySelector` 下拉列表可能显示不完整数据而无明确提示

**建议**:
1. 将分页信封从"推荐同批交付"升级为 P3b Entry **软门禁**（不阻断但需记录风险偏差）
2. 在 `PartySelector` 组件中增加"可能存在更多结果"的视觉提示（即使在分页信封缺失时）

---

### P2-4 · P3d Exit 中 `AuthGuard.tsx` 门禁 grep 路径可能不匹配

**位置**: §5.1 P3d Exit — `AuthGuard` 迁移验证

**现状**:
P3d Exit 门禁命令为：
```bash
! grep -rEn "useAuth\\(\\)\\.(hasPermission|hasAnyPermission)" 
  frontend/src/components/Auth/AuthGuard.tsx 
  frontend/src/routes frontend/src/App.tsx --include="*.tsx"
```

**问题**:
- `AuthGuard.tsx` 使用 `useAuth()` 但可能通过解构访问：`const { hasPermission } = useAuth()`，grep pattern `useAuth()\.(hasPermission)` 不会匹配解构写法
- 如果代码写的是 `const auth = useAuth(); auth.hasPermission(...)` 则可以命中
- 需要验证 `AuthGuard.tsx` 的实际代码风格

**建议**:
1. 补充一条更宽泛的 grep：`grep -rEn "hasPermission|hasAnyPermission" frontend/src/components/Auth/AuthGuard.tsx`
2. 或直接检查 `AuthGuard.tsx` 是否还引用 `usePermission`

---

### P2-5 · `types/auth.ts` 中 `User.default_organization_id` 与 P3e 门禁的交互风险

**位置**: §4.1 `types/auth.ts` / §4.2 `services/systemService.ts`

**现状**:
- §4.2 v1.21 修正明确 "保持提交 `default_organization_id` 不变"
- 但 §4.1 `types/auth.ts` 变更中未提及 `User.default_organization_id` 的处理
- `types/auth.ts` 中 `User` 接口还有 `organization?: Organization` 字段

**问题**:
- 如果 `types/auth.ts` 中 `Organization` 相关字段被标记 deprecated（§4.1 已标整个 `types/organization.ts`），那 `User.organization` 的类型引用将指向 deprecated 模块
- P3e 门禁对 `organization_id` 的 grep 排除了 `*organization.ts` 但**未排除 `*auth.ts`**——如果 `types/auth.ts` 中保留 `default_organization_id`，门禁可能误报

**词边界验证**:
`\borganization_id\b` 在 GNU grep 中，`_` 被视为 word character（`\w` 包含 `_`），因此 `\borganization_id\b` **不会**匹配 `default_organization_id` 中的 `organization_id` 子串。但此行为值得在门禁执行前显式验证。

**建议**:
1. 在 §4.1 `types/auth.ts` 中显式声明 `User.default_organization_id` 保留（不标 deprecated）
2. 在门禁执行前用 `echo "default_organization_id" | grep -oP "\borganization_id\b"` 测试词边界行为
3. 若实际会误匹配，在 P3e grep 中增加 `--exclude="*auth.ts"`

---

### P2-6 · `types/rentContract.ts` 中 `ownership?: Ownership` 嵌套对象迁移路径未说明

**位置**: §4.1 `types/rentContract.ts` 变更描述

**现状**:
`RentContract.ownership?: Ownership` 和 `RentLedger.ownership?: Ownership` 是**嵌套关联对象**（后端 eager load 的），不是简单 ID 字段。

**遗漏**:
- 计划仅列出 ID 字段迁移（`ownership_id` → `owner_party_id`），但未说明关联对象 `ownership?: Ownership` → `owner_party?: Party` 的处理
- 这影响到合同详情页等处的字段渲染——前端当前读 `contract.ownership.name`，迁移后需读 `contract.owner_party.name`
- 后端 API 响应中是否已将 `ownership` 嵌套替换为 `owner_party` 嵌套？需确认

**建议**:
1. 在 §4.1 `types/rentContract.ts` 中增加 `ownership?: Ownership` → `owner_party?: Party` 的迁移条目
2. 确认后端响应中嵌套对象名的变更时机

---

### P2-7 · 前端 `asset/types.ts`（`services/asset/` 下）与 `types/asset.ts` 的分离未跟踪

**位置**: §4.2 资产服务改造

**现状**:
§4.2 表格提到"`asset/types.ts` — `ownership_id`/`ownership_entity` → `owner_party_id`"，指的是 `services/asset/types.ts` 而非顶层 `types/asset.ts`。前端资产相关类型实际分散在至少两个位置。

**问题**:
- `services/asset/types.ts` 与 `types/asset.ts` 可能存在同名字段的重复定义——迁移时需要两边同步
- 计划没有明确说明这两个文件的字段同步策略

**建议**:
1. 确认 `services/asset/types.ts` 的内容与 `types/asset.ts` 的关系（是引用还是独立定义）
2. 在 §4.2 中标注两文件的改造需要原子化同步

---

### P2-8 · P3a 类型层 `@deprecated` 标记不产生编译警告——渐进式迁移的"防遗忘"缺失

**位置**: §4.1 全局策略

**现状**:
TypeScript 的 `@deprecated` JSDoc 标记仅在 IDE 中显示删除线提示，**不产生编译错误或警告**。`pnpm type-check` 不会因为使用了 deprecated 字段而失败。

**影响**:
- P3a 的"标记 deprecated + 新增"策略依赖开发者主动查看 IDE 提示来识别待迁移字段
- 在 P3b-P3d 长周期改造过程中，新增代码可能继续使用旧字段而没有编译层面的拦截
- 直到 P3e Exit 的 grep 门禁才能最终发现遗漏——届时修复成本更高

**建议**:
1. 考虑在 P3a 完成后、P3b 开始前引入一个 ESLint/oxlint 自定义规则，对导入旧字段（如从 `types/ownership.ts` 导入 `Ownership`）发出 warning
2. 或者在 P3b Entry 增加一个 "旧字段新增引用数不增长" 的基线检查

---

## P3 — 改进建议

### P3-1 · `useCapabilities` 的 `hasPartyAccess` 缺少"headquarters"关系类型处理

**位置**: §4.4 `hooks/useCapabilities.ts`

设计文档 §5.1 说明 `headquarters` 展开结果并入 `manager_party_ids`。但 `hasPartyAccess(partyId, relationType)` 的 `relationType` 参数限制为 `'owner' | 'manager'`，未提供 `'headquarters'` 选项。虽然 `headquarters` 最终合并到 `manager`，但调用方若需要区分语义（如 UI 展示"总部管辖"标签），目前接口不支持。

**建议**: 考虑新增可选的 `relationType: 'headquarters'` 映射到 `'manager'` 的语法糖，或在文档中显式说明调用方应传入 `'manager'` 来覆盖总部场景。

---

### P3-2 · 静默 refresh 的 403 触发条件可能被 CORS 或 Nginx 的 403 干扰

**位置**: §4.5 静默 refresh 防风暴

v1.21 已增加"必须同时满足 `403 + 权限拒绝标识`"约束。但**权限拒绝标识**的具体匹配规则未定义——是检查 `error.response.data.code === 'PERMISSION_DENIED'` 还是检查 `error.response.data.detail` 包含特定字符串？

**建议**: 显式定义权限拒绝的匹配 pattern，如 `error.response?.data?.code === 'PERMISSION_DENIED'` 或 `error.response?.data?.detail?.includes('权限不足')`。

---

### P3-3 · 运行时请求载荷旧字段拦截（§6.2 建议）的正则可能误报

**位置**: §6.2 运行时请求载荷旧字段拦截

```javascript
/(^|["'{,\s])(organization_id|ownership_id|...)(["'}:,\s]|$)/.test(payload)
```

此正则可能误报以下场景：
- 日志/注释中的旧字段名
- `default_organization_id` 中的 `organization_id` 子串——虽然 JSON key 通常由引号包裹，但 payload 可能包含注释

**建议**: 改用 JSON key 精确匹配：`/"(organization_id|ownership_id|...)"\s*:/`

---

### P3-4 · P3c 浏览器冒烟测试缺少"PDF 合同导入"验证项

**位置**: §6.3 浏览器冒烟测试矩阵

冒烟测试 13 项中，覆盖了 Excel 导入/导出和普通合同创建，但缺少 **PDF 智能导入**（`/rental/contracts/pdf-import`）路径的验证。考虑到 P0-4（`pdfImport.ts` 迁移范围低估），PDF 导入是高风险链路。

**建议**: 在冒烟矩阵中增加第 14 项：PDF 合同导入 → 验证 PartyMatch 智能匹配正常、`owner_party_id` 字段带入确认数据。

---

### P3-5 · 文档历史版本信息过于冗长——建议精简至可执行决策摘要

**位置**: §10 文档历史

当前 v1.11-v1.21 的变更日志各包含 3-6 条修订明细，累计 ~120 行。虽然提供了变更追溯性，但在执行阶段可能分散注意力。

**建议**: 将 v1.11-v1.20 的详细变更合并为一行"参见 Git 历史"链接，仅保留 v1.21 当前版本的完整详情。

---

## 交叉验证矩阵——计划声称 vs 代码实际

| 计划声称 | 代码实际 | 验证结果 |
|----------|----------|----------|
| `store/useAssetStore.ts` 无旧字段命中 | 仅测试文件有 `ownership_entity` | **符合**（但测试文件需清理） |
| `services/statisticsService.ts` 无旧字段 | 经验证无 ownership/organization 引用 | **符合** |
| `services/analyticsService.ts` 无旧字段 | 经验证无旧字段引用 | **符合** |
| `services/rentContractExcelService.ts` 需改 ownership_id 列名 | 文件中**零** ownership 引用 | **不符合**（见 P1-4） |
| `services/asset/assetImportExportService.ts` 需改 ownership_id 列名 | 文件中**零** ownership 引用 | **不符合**（见 P1-4） |
| `AuthGuard` 不在路由链中使用 | 确认：`App.tsx` 和 `AppRoutes.tsx` 均不引用 `AuthGuard` | **符合** |
| `ROUTE_CONFIG` 定义了路由权限配置 | 确认存在，但**从未被路由渲染代码消费** | **符合**（意味着 P3d 需建立全新消费链路） |
| 后端 `/parties` 无 `search` 参数 | 确认：仅 `party_type` + `status` 过滤 | **符合**（P3b 硬门禁成立） |
| `types/propertyCertificate.ts` 旧字段仅在 `PropertyOwner` 子接口 | 确认：`PropertyOwner.organization_id` | **符合** |
| `types/rentContract.ts` 全量 14 处 `ownership_id` | 需计数验证（`ownership_id` + `ownership_ids` + `ownership_name` 等） | **大致符合**（复数形式需确认） |
| 后端 capabilities 有 `version` 和 `generated_at` | `version="2026-02-17.v1"`（协议版本），`generated_at` 为运行时 datetime | **符合**（v1.21 缓存判据修正正确） |
| 后端 data-policy 端点路径 | GET/PUT `/api/v1/auth/roles/{role_id}/data-policies`、GET `/api/v1/auth/data-policies/templates` | **符合** |
| Phase 3 不改后端鉴权资源名 | `auth/system` 模块大量仍为 `asset`，但 `project/rent_contract/property_certificate/party` 端点已使用对应 `resource_type`；capabilities 来源 ABAC rules | **部分符合**（原 P0-1 需降级为“覆盖验证风险”） |

---

## 改进建议优先级排列

| 优先级 | 编号 | 标题 | 建议处理时间 |
|--------|------|------|-------------|
| **P0** | P0-3 | `assetFormSchema.ts` ownership_id required 遗漏 | **计划修订 + P3b** |
| **P0** | P0-4 | `pdfImport.ts` 迁移范围低估 | **计划修订 + P3a** |
| **P1** | P0-1 | capabilities 覆盖验证缺失（原 P0） | **P3b Entry 前** |
| **P1** | P0-2 | Org ↔ Party 迁移闭环门禁不足（原 P0） | **P2 追加交付 / P3b Entry 前** |
| **P1** | P1-1 | `AuthStorage.AuthData` 无 capabilities 字段 | **P3a/P3b** |
| **P1** | P1-2 | `restoreAuth()` 竞态窗口 | **P3b 设计** |
| **P1** | P1-3 | capabilities 缓存比对策略过于复杂 | **计划修订** |
| **P1** | P1-4 | Excel 服务旧字段实际零引用 | **计划修订** |
| **P1** | P1-5 | `contactService.ts` 与 `PartyContact` 未对齐 | **P3b** |
| **P1** | P1-6 | `types/asset.ts` 统计类型名迁移遗漏 | **P3a** |
| **P2** | P2-1 | `ownership_ids` 复数迁移目标未定义 | **P3a** |
| **P2** | P2-2 | `useOwnership.ts` hook 未在迁移清单 | **计划修订** |
| **P2** | P2-3 | `/parties` 无分页信封 | **P3b 软门禁** |
| **P2** | P2-4 | P3d AuthGuard grep 路径不匹配解构写法 | **P3d 门禁修正** |
| **P2** | P2-5 | `auth.ts` 中 `default_organization_id` 门禁冲突 | **P3e 门禁修正** |
| **P2** | P2-6 | `rentContract` 嵌套对象迁移路径未说明 | **计划修订** |
| **P2** | P2-7 | `services/asset/types.ts` 与 `types/asset.ts` 分离 | **P3b 同步** |
| **P2** | P2-8 | `@deprecated` 不产生编译警告 | **P3b Entry** |
| **P3** | P3-1 | `hasPartyAccess` 缺 headquarters 语义 | **P3d** |
| **P3** | P3-2 | 403 权限拒绝标识匹配规则未定义 | **P3d** |
| **P3** | P3-3 | 运行时拦截正则可能误报 | **P3e** |
| **P3** | P3-4 | 冒烟测试缺 PDF 导入验证 | **P3c** |
| **P3** | P3-5 | 文档历史过于冗长 | **任意时间** |

---

## 总结

Phase 3 计划的核心设计（子阶段分层、门禁体系、渐进式 deprecated 策略、路由守卫双轨制）是合理且成熟的。主要风险集中在：

1. **capabilities 风险应表述为“覆盖验证与环境一致性风险”**（原 P0-1，现 P1），而非“后端仅 asset 导致必然失效”
2. **Organization 与 Party 已有离线迁移路径，但缺少强制门禁与在线闭环**（原 P0-2，现 P1）
3. **多个文件/字段的遗漏**（P0-3/P0-4/P1-6/P2-2）——表明当前影响分析需要一次基于实际 grep + AST 的全量扫描而非估算

建议在 P3a 启动前召开一次 Phase 2-3 联合评审，先闭环两项 P0 阻断，再同步落实两项“由 P0 降级为 P1”的环境与迁移门禁，确保后端交付物与前端消费预期完全对齐。
