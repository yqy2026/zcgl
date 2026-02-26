# Phase 3 实施计划深度审阅报告

**审阅对象**: [docs/plans/2026-02-20-phase3-implementation-plan.md](../plans/2026-02-20-phase3-implementation-plan.md)（v1.38）  
**审阅日期**: 2026-02-22  
**审阅方法**: 全文逐节阅读 + 代码库交叉验证 + Phase 2 / 架构设计文档对照 + 后端实现核验  

---

## 0. 审阅总评

文档经过 38 轮迭代后已达到**高度细化**的水平。代码库引用统计全部精确匹配（§3.1 六类旧字段统计均与实际 grep 结果一致），上游文档引用（Phase 2 八项交付物、架构设计 §5.1/§5.2、Alembic 迁移文件）均可实证验证。门禁命令覆盖面广，且提供了 Bash/PowerShell 双平台等价实现。

但文档的**过度迭代**本身也带来了严重问题。1646 行、38 个版本的叠加修补导致**结构性缺陷**和**隐性风险**已被行文噪声掩盖。以下逐节列出所有发现的问题，按严重级别标注。

**严重级别定义**:

| 级别 | 含义 |
|------|------|
| 🔴 **阻断** (P0) | 可导致执行失败、门禁假通过/假失败、生产事故；必须在执行前修复 |
| 🟠 **重大** (P1) | 执行者可能误判或大幅返工；强烈建议修复 |
| 🟡 **中等** (P2) | 缺漏或不一致，可能导致效率损失；推荐修复 |
| 🔵 **建议** (P3) | 优化项或风格建议 |

---

## 1. 🔴 阻断级问题 (P0)

### 1.1 `PermissionGuard` 遗漏——Router 并行链未纳入收口

**位置**: §4.3 [REVIEW/DEFER] `components/Router/*` + §4.6 P3e Router 硬门禁

**问题**: 文档声称 `PermissionGuard.tsx` 将在 P3d 标记 `@deprecated` + 内部代理到 `CapabilityGuard`，P3e 物理删除 `usePermission.tsx`。但搜索发现 `PermissionGuard` 有 **3 个生产级消费者**：

- `components/Router/ProtectedRoute.tsx`
- `components/Router/LazyRoute.tsx`
- `components/Router/DynamicRouteRenderer.tsx`

虽然 Router 体系当前不在 `App.tsx` 主路由链中，但 `PermissionGuard` 的预设守卫导出（`UserManagementGuard`、`RoleManagementGuard`、`AssetManagementGuard` 等）如果在 P3d 内部实现改为代理 `CapabilityGuard`，必须确保这三个 Router 文件的运行时行为不受影响。§4.6 第 7 点仅提到"Router 残留调用链处置"针对 `usePermission`，**未覆盖 `PermissionGuard` → Router 的依赖链**。

**影响**: 若 P3e 物理删除 `PermissionGuard.tsx` 而未处理这三个 Router 文件的导入，运行时编译将直接断裂。即使选择 P3e Router 物理删除方案 (A)，也需要在引用评估命令中覆盖 `PermissionGuard` 而非仅 `usePermission`。

**建议**: 
1. §4.6 第 7 点的 grep 命令需补充 `PermissionGuard` 依赖扫描：`grep -rEl "from.*PermissionGuard|PermissionGuard" frontend/src/ --include="*.ts" --include="*.tsx"`
2. P3e 门禁需显式选择：Router 与 PermissionGuard 捆绑删除 (A) 或 PermissionGuard 保留为 CapabilityGuard 壳 (B)

---

### 1.2 psql 门禁命令用户名/数据库名缺占位——多环境不可执行

**位置**: §5.1 P3b/P3d Entry 门禁多处 SQL 命令

**问题**: 门禁 SQL 命令大量使用裸 `psql -c "..."` 格式（如 P3a, P3b, P3d Entry），未指定 `-U` 用户名和 `-d` 数据库名。Docker Compose 默认用户为 `zcgl_user`，数据库为 `zcgl`，但裸 `psql` 命令会使用当前操作系统用户名和默认 `postgres` 数据库，导致连接失败。

部分命令补充了 `docker compose exec db psql -U <user> -d <db>` 备选，但使用了 `<user>` / `<db>` 占位符而非从 `.env` 或 `docker-compose.yml` 解析的实际值。执行者必须先查找正确的连接信息才能运行。

**具体位点**:
- P3a Entry：`psql -c "SELECT COUNT(*) FROM parties WHERE status = 'active';"` — 无连接参数
- P3b Entry：`psql -c "\\dt abac_role_policies"` — 无连接参数
- P3b Entry：`party.read` 非管理员绑定验证 SQL — Docker 备选使用 `<user>` `<db>` 占位
- P3d Entry：seed 数据 spot-check — Docker 备选使用 `<user>` `<db>` 占位
- P3e Entry：`tenant_party_id IS NULL` 检查 — 无连接参数

**建议**: 统一定义数据库连接常量（如 `DB_CMD="docker compose exec db psql -U zcgl_user -d zcgl"`），所有门禁 SQL 引用该常量，或统一使用后端 Python 脚本执行检查避免 psql 依赖。

---

### 1.3 `mocks/fixtures.ts` 被排除但含 `ownership_entity` 主链显示字段

**位置**: §5.2 `PHASE3_GREP_EXCLUDES` + §3.1

**问题**: `PHASE3_GREP_EXCLUDES` 排除了 `--exclude-dir=mocks`。但 `mocks/fixtures.ts` 位于 `frontend/src/mocks/`（非 `__tests__/`/`test`/`test-utils`），在 §3.1 中被计入 `ownership_entity` 的 18 个主链文件之一。

如果 `mocks/` 是运行时 MSW handler 的 fixture（开发服务器 mock 数据），其中的旧字段可能导致开发态行为与生产态不一致。但如果 `mocks/` 仅用于测试，则排除合理。

**问题本质**: §3.1 将 `mocks/fixtures.ts` 计入"主链"（18+1 口径中的 18），但 §5.2 将 `mocks/` 整目录排除。两者口径矛盾——要么统计应为 17+2，要么门禁排除应去掉 `mocks/`。

**建议**: 明确 `mocks/` 性质。若为开发态 MSW handlers，应从排除列表移除，纳入迁移范围。

---

### 1.4 P3e `usePermission` 删除前置——`PERMISSIONS` 常量消费者盘点不完整

**位置**: §4.6 第 6 点 + §4.4.1

**问题**: §4.6 第 6 点要求"删除 `usePermission.tsx` 前完成 `PERMISSIONS/PAGE_PERMISSIONS` 常量消费者迁移盘点"。但根据代码库验证，`PERMISSIONS` 的消费者**不只是** `usePermission.tsx` 内部：

- `components/Router/RouteBuilder.tsx` 直接 `import { PERMISSIONS } from '@/hooks/usePermission'`
- `PermissionGuard.tsx` 导入 `PERMISSIONS`（间接通过守卫预设）

§4.4.1 的"批量替换清单"将 `usePermission.tsx` 中的 `PERMISSIONS` 迁移计划列出，但未明确说明 `PERMISSIONS` 被外部文件直接导入使用的情况。P3d 的门禁命令仅检查 `usePermission` 字样，不检查 `PERMISSIONS` 常量引用。

**影响**: P3e 删除 `usePermission.tsx` 时，`RouteBuilder.tsx` 的 `import { PERMISSIONS }` 将编译失败。若 Router 选择方案 B（保留+deprecated），需要将 `PERMISSIONS` 迁移到独立文件或 `useCapabilities` 导出。

**建议**: 增加盘点命令：`grep -rEn "from.*usePermission|PERMISSIONS|PAGE_PERMISSIONS" frontend/src/ --include="*.ts" --include="*.tsx" --exclude="usePermission.tsx"` 并在 P3e Entry 执行。

---

### 1.5 §4.4.1 门禁 A grep 命令逻辑缺陷——`find | xargs grep` 在零文件匹配时假通过

**位置**: §4.4.1 末尾门禁 A 命令

**问题**: 门禁 A 命令结构为：
```bash
test -f <file1> && test -f <file2> && ... && \
  ! find <files> -type f 2>/dev/null \
    | xargs -r grep -El "..."
```

当 `find` 匹配到文件但 `grep` 无命中时，`xargs -r grep -El` 返回 exit code 1，取反 `!` 后得到 0（通过）——这是期望行为。

但如果 `usePermission.tsx` 文件存在但 **`find` 输出通过管道传给 `xargs` 时行为异常**（例如文件包含空格/特殊字符），`xargs` 可能跳过文件导致假通过。更关键的是：`! find ... | xargs -r grep -El` 的 `!` 只取反了整条管道的退出码，而管道退出码默认由最后一个命令 (`xargs -r grep`)决定。如果 `find` 结果为空（所有 `test -f` 通过但 `find -type f` 不匹配——按当前写法不太可能但逻辑上有缝隙），`xargs -r` 什么都不做，返回 0，`!` 取反后得到 1（失败），导致假失败。

**建议**: 使用 `grep -El` 直接指定文件列表（已经用 `test -f` 确认了存在性），无需 `find | xargs` 间接层：
```bash
! grep -El "action\s*:\s*['\"](view|edit|import|settings|logs|dictionary|lock|assign_permissions)['\"]" \
  frontend/src/constants/routes.ts \
  frontend/src/routes/AppRoutes.tsx \
  ...
```

---

## 2. 🟠 重大问题 (P1)

### 2.1 `AuthGuard.tsx` 处置策略不充分

**位置**: §4.4.2 D5 + §5.1 P3d Exit

**问题**: D5 声明 `AuthGuard.tsx` 标记 `@deprecated` 并禁止新增主路由引用。P3d Exit 有门禁检查 `AuthGuard` 未回流主路由链。但代码库验证显示 `AuthGuard` 是**完全的死代码**——零生产消费者，仅测试文件引用。

文档未利用这一事实简化处置：直接在 P3d 物理删除 `AuthGuard.tsx`（连同测试），比标记 `@deprecated` + 禁止新引用 + P3e 再决策更干净，且消除了 D5 中"若 P3e 删除 `AuthContext.hasPermission`，需同步执行 `AuthGuard` 删除或改为 `useCapabilities` 兼容壳"的级联复杂度。

**建议**: 将 `AuthGuard.tsx` 处置从"P3d deprecated + P3e 联动决策"简化为 **P3d 直接物理删除**。

---

### 2.2 `project.party_relations[]` 后端契约——当前后端无此字段

**位置**: §1 Phase 2-patch + §4.2 P3b 门禁 + §5.1 P3b Entry

**问题**: 后端代码验证确认 `backend/src/schemas/project.py` 中 **不存在** `party_relations` 字段，仅有 `ownership_relations`。且 `project_to_response()` 中 `ownership_relations=[]` 是硬编码空数组。

文档正确将此列为 P3b Entry 硬门禁，但 Phase 2-patch 表中将此项责任方列为 "Backend Schema"，实际需要的改动跨越：
1. Schema 层新增 `party_relations` 字段
2. Service 层 `project_to_response()` 移除硬编码并构建转换逻辑
3. 若保持前后端字段兼容，可能需要后端同时返回 `ownership_relations` 和 `party_relations`

这三步的工作量远超"Schema 改一改"。文档未在 Phase 2-patch 中给出这三步的拆分估时或技术方案。

**影响**: 低估后端前置工作量，可能导致 P3b 无限延后。

**建议**: 在 Phase 2-patch 表中细化 `party_relations` 交付为独立技术方案（含 Schema + Service + 兼容层三步估时），或明确允许 P3b 在 `party_relations` 字段缺失时的降级方案（如前端直读 `ownership_relations` 并标注过渡）。

---

### 2.3 CORS `expose_headers` 缺失——`request_id` 响应头前端不可读

**位置**: §4.5 第 5 点（`request_id` 来源契约）+ v1.33 可观测前提

**问题**: 后端 CORS 配置（`main.py`）的 `CORSMiddleware` 设置了 `allow_headers=["X-Request-ID", ...]` 但**未设置 `expose_headers`**。根据 CORS 规范，`allow_headers` 控制请求头（客户端发→服务端），`expose_headers` 控制响应头（服务端发→客户端 JS 可读）。缺少 `expose_headers=["X-Request-ID"]` 意味着前端 JS 无法通过 `response.headers` 读取 `X-Request-ID`。

§4.5 v1.33 确实提到了"跨域环境需后端 `CORS expose_headers` 暴露 `X-Request-ID`"，但仅作为观测前提条件记录，**未列入 Phase 2-patch 阻断项或 P3d Entry 门禁**。

**影响**: §4.5 第 5 点定义的 `request_id` 解析优先级（header > body > local）在当前后端配置下永远命中 body 或 local，header 优先级形同虚设。

**建议**: 
1. 将 `expose_headers` 配置添加到 Phase 2-patch 表（或 P3d Entry 前置）
2. 或在 §4.5 中将 header 优先级标记为"当前环境不可用"且降级到 body 优先

---

### 2.4 `RentContractAsset` 子接口遗漏——变更清单文件未覆盖

**位置**: §4.1 [MODIFY] `types/rentContract.ts` + §4.3 合同模块

**问题**: §4.1 明确列出 `RentContractAsset` 子接口需迁移 `management_entity` 和 `ownership_entity`。但 §4.3 合同模块变更清单（8+ 文件）的 **所有文件条目中没有一个明确对应 `RentContractAsset` 子接口的运行时消费位置**。

`RentContractAsset` 的 `management_entity` / `ownership_entity` 在合同详情、合同创建等页面中被消费（显示关联资产的权属信息），但变更清单未列出这些具体文件的具体变更——只有泛化的"`ownership_entity` 显示 → Party name"。

**建议**: 在 §4.3 合同模块表中显式添加消费 `RentContractAsset.management_entity` / `RentContractAsset.ownership_entity` 的具体文件和变更内容。

---

### 2.5 `types/auth.ts` `AuthState` 与 `AuthContext` 字段不同步

**位置**: §4.1 [MODIFY] `types/auth.ts` + §4.2 [MODIFY] AuthContext

**问题**: §4.1 要求在 `types/auth.ts` 的 `AuthState` 新增 `capabilities?: Capability[]`。§4.2 要求在 `AuthContext` 新增 `capabilities: Capability[]`、`capabilitiesLoading: boolean`、`isAdmin: boolean`、`refreshCapabilities: () => Promise<void>`。

但 §4.2 还声明"`AuthStorage` 字段定义：`capabilities?: Capability[]`、`capabilities_cached_at?: string`、`capabilities_version?: string`"——这意味着 `AuthStorage` 的 `AuthData` 类型也需要修改。

当前 `AuthState`（`types/auth.ts`）和 `AuthData`（`AuthStorage.ts`）是**两个独立接口**。文档未明确说明：
1. `AuthState.capabilities` 与 `AuthData.capabilities` 的关系
2. `AuthState` 是否需要同步新增 `capabilitiesLoading` / `isAdmin`（还是这些仅在 Context 层面存在）
3. `AuthStorage.setAuthData()` 是否需要接受新的 `capabilities` 字段

**建议**: 为 `AuthState` / `AuthData` / `AuthContextType` 三者的字段新增关系画一个简单映射表，避免实现者在三处重复/遗漏。

---

### 2.6 `ownership_relations` → `party_relations` 迁移中间态——数据回显断路风险

**位置**: §4.1 [MODIFY] `types/project.ts` + §4.2 [MODIFY] `services/projectService.ts`

**问题**: 文档要求"前端 `projectService` 仅消费/提交 `party_relations[]`"，且"禁止前端硬编码 `ownership_to_party_map`"。但在 P3b+P3c 执行期间，如果后端 `project_to_response()` 的修复（移除 `ownership_relations=[]` 硬编码 + 新增 `party_relations[]` 转换）**交付质量不稳定**（如部分旧数据转换失败），前端将面临：

- `party_relations[]` 为空但 `ownership_relations[]` 有数据 → 前端丢失关系回显
- 前端被禁止使用 `ownership_relations` 回显 → 无降级方案

§4.3 产权证模块有"兼容读取 `party_relations ?? owners`"策略，但项目模块**无等价降级策略**。

**建议**: 在 P3c 项目详情页增加过渡期兼容读取：`party_relations ?? ownership_relations?.map(r => /* minimal mapping */)`，并在 P3e 移除。

---

### 2.7 §4.4.2 D8 feature flag 实现未落地到代码示例

**位置**: §4.4.2 D8 + D9

**问题**: D8 要求 `CapabilityGuard` 受 `VITE_ENABLE_CAPABILITY_GUARD` 控制。D9 要求生产环境显式声明。但 §4.4.2 的 `renderProtectedElement` 伪代码**完全没有包含 feature flag 检查**。执行者按伪代码实现后，将直接启用能力守卫，无法熔断。

**建议**: 在 `renderProtectedElement` 伪代码中增加 feature flag 分支：
```tsx
const capabilityGuardEnabled = import.meta.env.VITE_ENABLE_CAPABILITY_GUARD === 'true';
// flag off: skip capability deny, only auth check
if (!capabilityGuardEnabled) return <PageTransition>...</PageTransition>;
```

---

## 3. 🟡 中等问题 (P2)

### 3.1 文档历史噪声——§10 文档历史占全文 35%

**位置**: §10 文档历史

**问题**: §10 从 v1.11 到 v1.38 记录了 28 条版本历史，占文档约 580 行（全文 1646 行的 35%）。v1.0–v1.10 已移到 Git 历史，但 v1.11–v1.38 仍以全文形式留存。

这不仅增加阅读负担，还导致真正的执行内容被淹没。执行者必须在 1646 行中找到自己当前子阶段的 Entry/Exit/变更清单，实际有效执行内容约 1000 行。

**建议**: 将 v1.11–v1.35 也移到 Git 历史，仅保留最近 3 个版本（v1.36–v1.38）的摘要。

---

### 3.2 `types/capability.ts` 的 `ResourceType` 定义遗漏 `ledger`

**位置**: §4.1 [NEW] `types/capability.ts`

**问题**: `KnownResourceType` 代码示例列出 7 个值：`asset | project | rent_contract | ledger | party | system | property_certificate`。在 v1.29 修订中声明"在 `types/capability.ts` 的 `ResourceType` 纳入 `ledger`"，这已正确——7 个值包含 `ledger`。

但 §2 "后端 resource_type 覆盖策略" 表中的"业务路由主覆盖"列出 6 个资源：`asset / project / rent_contract / ledger / party / property_certificate`，不含 `system`。而 `KnownResourceType` 含 `system`。这一差异虽然在其他地方有解释（`system` 走 adminOnly），但在两个表中的不一致容易误导。

**建议**: 在 §2 表中增加一行注释，说明 `system` 虽在 `KnownResourceType` 中但不走 `canPerform` 路由判定。

---

### 3.3 `OwnershipRentStatistics` 统计字段迁移遗漏

**位置**: §4.1 [MODIFY] `types/rentContract.ts` "统计口径专项"

**问题**: 文档提及 `OwnershipRentStatistics` 需将 `ownership_name` / `ownership_short_name` 迁移为 `owner_party_name`。但验证代码库时，该接口的完整字段可能还包含其他旧语义名称（如统计维度汇总键名）。文档仅列出了名称字段的迁移，**未覆盖此接口被消费的统计页面**（`RentStatisticsPage.tsx`）中 **UI 维度标签文案** 的同步修改（如表头/图例从"权属方"改为"Party"或等价中文）。

**建议**: 在 §4.3 合同模块 `RentStatisticsPage.tsx` 变更说明中增加"统计维度标签文案同步迁移"。

---

### 3.4 `services/asset/types.ts` 遗漏于变更清单

**位置**: §4.2 [MODIFY] `services/assetService.ts` + `services/asset/*.ts`

**问题**: §4.2 表格列出 `asset/types.ts` 变更为"`ownership_id`/`ownership_entity` → `owner_party_id`"，这是正确的。但 §3.1 统计显示 `services/asset/types.ts` 同时命中了 `ownership_id` 和 `ownership_entity`（两个旧字段），§4.2 表格中的描述仅提到两个旧字段的其中一组映射。

此外，`services/asset/types.ts` 不在 §4.1 类型层清单中（因为它是服务层内部类型），需确保 P3b 变更清单明确覆盖此文件的**全部**旧字段替换。

**建议**: 在 §4.2 `asset/types.ts` 行项中补充完整字段映射清单。

---

### 3.5 P3d Exit `check:route-authz` 脚本依赖——Gate 前需确保脚本逻辑正确

**位置**: §5.1 P3d Exit + §6.1

**问题**: P3d Exit 门禁引用 `node frontend/scripts/check-route-authz-mutual-exclusive.mjs`（D10 互斥校验）。该脚本已确认存在，但文档未描述其校验逻辑或期望行为。如果脚本实现有 bug（如仅检查字面量 `adminOnly` 但 `AppRoutes` 使用 computed property），门禁将假通过。

**建议**: 在 §6.1 或附录中简述 `check-route-authz-mutual-exclusive.mjs` 的校验逻辑、期望输入/输出、测试用例，或至少要求 P3d 实现者在首次使用前 review 该脚本。

---

### 3.6 P3b Exit grep 命令混用 `PHASE3_GREP_EXCLUDES` 与 `--include`

**位置**: §5.1 P3b Exit

**问题**: P3b Exit 的旧字段零引用门禁：
```bash
! grep -rElw "organization_id|ownership_ids?|..." frontend/src/services/ frontend/src/utils/ --include="*.ts" "${PHASE3_GREP_EXCLUDES[@]}"
```

`PHASE3_GREP_EXCLUDES` 包含 `--exclude-dir=Organization` 等目录排除，但 `frontend/src/services/` 和 `frontend/src/utils/` 下没有 `Organization` 目录。更重要的是，`PHASE3_GREP_EXCLUDES` 包含 `--exclude=*organization.ts` 和 `--exclude=*organizationService*`，这意味着**所有**以 `organization` 命名的文件都被排除。

对于 P3b（服务层）这是正确的——`organizationService.ts` 确实需要排除。但 `--include="*.ts"` 和 `--exclude=*organization.ts` 之间的交互在不同 grep 实现中行为可能不一致（GNU grep vs macOS grep）。

**建议**: 在 §5.2 增加注释说明 `--include` 与 `--exclude` 的优先级假设（GNU grep：exclude 优先于 include），并建议统一使用 GNU grep。

---

### 3.7 `tenant_party_id` 收口 P3e 收紧为必填——后端契约联动缺失

**位置**: §4.1 `types/rentContract.ts` P3e 收紧语义 + §5.1 P3e Entry

**问题**: P3e 将 `tenant_party_id` 从 `string | null` 收紧为 `string`（必填且非 null）。P3e Entry 门禁要求先执行 `SELECT COUNT(*) FROM rent_contracts WHERE tenant_party_id IS NULL;` 并按量化阈值处理。

但文档未说明：
1. 后端 Schema 何时同步收紧（是 P3e 通知后端 → Phase 4 执行，还是 P3e 期间后端需同步收紧？）
2. 若前端收紧为必填但后端仍接受 `null`，前端强制必填会导致旧数据编辑时前端校验失败（后端回传 `tenant_party_id = null` → 前端表单加载 → 必填校验不通过）

**建议**: 在 P3e 收紧策略中增加前端处理子策略：后端返回 `null` 时前端展示为空（允许查看），但提交时强制要求填写（不允许保存为 `null`）。

---

### 3.8 `RentLedger` / `RentLedgerCreate` 等类型迁移在变更清单中无对应页面/组件项

**位置**: §4.1 `types/rentContract.ts` 12 处 + §4.3 合同模块

**问题**: §4.1 列出 `RentLedger` 和 `RentLedgerCreate` 的 `ownership_id` 迁移，但 §4.3 合同模块变更只列出 `RentLedgerPage.tsx`（台账页过滤）。创建台账记录的表单组件（如果存在单独的台账创建 UI）未在变更清单中出现。应确认台账创建是否仅通过合同创建联动，还是有独立 UI。

**建议**: 确认台账创建链路并补充变更清单。

---

### 3.9 P3c "无资产项目" 判定标准可能与后端返回结构不一致

**位置**: §5.1 P3c Exit

**问题**: 判定条件固定为：`(project.asset_count ?? project.assets?.length ?? 0) === 0`。但需验证后端项目列表/详情 API 是否返回 `asset_count` 或 `assets` 字段。如果后端仅在详情中返回 `assets` 而列表中不返回，则列表页的判定将因字段缺失而始终显示"待补绑定"。

**建议**: 确认后端项目列表 API 的返回字段，必要时在列表 API 中请求补充 `asset_count`。

---

## 4. 🔵 建议级问题 (P3)

### 4.1 `authz.py:8` 路径引用歧义

**位置**: §4.1 `types/capability.ts` 注释、§4.4.1

**问题**: 文档多处引用"后端 `authz.py:8`"定义 ABAC 标准动作。后端实际有 3 个 `authz.py` 文件：
- `backend/src/schemas/authz.py`（目标文件，含 `AuthzAction` 类型定义）
- `backend/src/crud/authz.py`
- `backend/src/api/v1/auth/authz.py`（或类似路径）

"`authz.py:8`"无法唯一定位。虽然内容正确（`AuthzAction = Literal["create", "read", "list", "update", "delete", "export"]`），但引用风格应使用完整路径。

**建议**: 统一引用为 `schemas/authz.py:8`。

---

### 4.2 甘特图 Mermaid 依赖限制说明过度分散

**位置**: §0 / §5.1 / §1 多处

**问题**: "Mermaid Gantt 对 AND 双前置表达能力有限" 的说明至少出现 3 次（§0 并行规则注释、§0 NOTE、§5.1 流程图后文字）。重复说明同一限制增加阅读负担。

**建议**: 仅在 §0 甘特图下方说明一次，后续引用 "见 §0 并行规则"。

---

### 4.3 PowerShell 门禁缺少 `PHASE3_GREP_EXCLUDES` 等价定义

**位置**: §6.3

**问题**: §6.3 提供了 PowerShell 等价命令覆盖核心门禁，但仅覆盖部分场景（P3d Entry/Exit、P3e Entry）。§5.2 定义了 bash `PHASE3_GREP_EXCLUDES` 和 PowerShell `$Phase3GrepExcludes`，但 §6.3 的 PowerShell 命令**未使用 `$Phase3GrepExcludes`**——因为 PowerShell 的 `Select-String` 不接受 `--exclude-dir` 语法。

这意味着 Windows 执行者**无法直接运行** P3b/P3e Exit 的旧字段零引用门禁。

**建议**: 在 §6.3 增加 PowerShell 等价的旧字段零引用检查（使用 `Get-ChildItem -Exclude` + `Select-String` 组合），或统一要求 Windows 环境使用 WSL/Git Bash 执行门禁。

---

### 4.4 `CapabilityGuard` 组件接口不支持 `adminOnly`

**位置**: §4.4 [NEW] `components/System/CapabilityGuard.tsx`

**问题**: `CapabilityGuardProps` 接口只有 `action`、`resource`、`perspective`、`fallback`、`children`，无 `adminOnly`。但 §4.4.2 的渲染伪代码中 `adminOnly` 判定在 `CapabilityGuard` **外部**（`renderProtectedElement` 函数中）。这虽然是合理的设计选择（路由级判定 vs 组件级判定），但文档中"CapabilityGuard 路由守卫正常工作（含 `adminOnly`）"的 P3d Exit 验收描述容易误解为 `CapabilityGuard` 组件自身支持 `adminOnly`。

**建议**: 在 P3d Exit 门禁中明确"`adminOnly` 由 `renderProtectedElement` 处理，非 `CapabilityGuard` 接口"。

---

### 4.5 `assetFactory.ts` 条件化表述——变更清单不确定

**位置**: §4.3 测试工厂与 Mock 表

**问题**: `test-utils/factories/assetFactory.ts` 写作"（若存在）"。代码库验证确认该文件**存在**。应直接列入变更清单，删除"若存在"。

**建议**: 移除"（若存在）"，直接写入。

---

### 4.6 `capabilities` TTL 10 分钟与静默 refresh 30s cooldown 的交互未说明

**位置**: §4.2 capabilities 存储策略（TTL 10 分钟）+ §4.5 Cooldown 30s

**问题**: 两个机制独立运作但可能交互：
- TTL 10 分钟到期后如何触发重拉？是被动（下次路由判定时检查）还是主动（定时器）？
- 若用户在 TTL 到期后 30s 内连续访问两个受保护路由，是否连续触发两次 refresh？是否命中 cooldown？

文档未说明 TTL 到期触发的 refresh 是否受 cooldown 限制。如果 TTL 机制使用 cooldown 同源，30s 内仅能刷新一次可能导致"第二个路由判定使用过期 capabilities"。

**建议**: 明确 TTL 驱动的刷新与 403 驱动的刷新是否共享 cooldown 状态。

---

### 4.7 `DataPolicyTemplate` 后端响应格式转换责任归属

**位置**: §4.1 `types/dataPolicy.ts` + §4.4 `services/dataPolicyService.ts`

**问题**: 后端 `GET /api/v1/auth/data-policies/templates` 返回 `dict[str, {name, description}]`（代码验证确认），键为 `code`。前端类型定义为 `{ code, name, description }` 数组。

文档在 §4.4 只写了"返回 `dict[code, {name, description}]`，前端转为 `DataPolicyTemplate[]`"。转换逻辑（`Object.entries(response).map(([code, v]) => ({ code, ...v }))`）虽简单但未显式写入代码示例。

**建议**: 在 `dataPolicyService.ts` 新增代码段中加入转换示例，避免实现者误以为后端直接返回数组。

---

### 4.8 "无资产项目"标签展示——UI 设计缺具体规格

**位置**: §4.3 项目详情页 + §5.1 P3c Exit

**问题**: 声明无资产项目显示"待补绑定"标签、面积统计显示 `N/A`。但未说明：
- 标签使用什么 Ant Design 组件（`Tag`? `Badge`?）
- 颜色/类型（`warning`? `default`?）
- 是否在列表页和详情页同时显示

**建议**: 补充 UI 规格或标注"由执行者按 Ant Design 规范自行选择"。

---

### 4.9 P3b `search` 响应截断近似判断——逻辑易出错

**位置**: §4.2 [NEW] `services/partyService.ts` v1.21 补充

**问题**: 文档要求"若后端暂未提供分页信封，前端需在 `partyService` 显式标注 `result.length === limit` 仅为截断近似判断"。该近似判断在 `limit=1000` 且实际恰好有 1000 条有效数据时会误判为截断。

这是 §4.2 三档阈值策略第三档的基础："返回数 = 1000 → 命中后端上限，结果已截断"。但**也可能**恰好有 1000 条匹配结果。

**建议**: 该风险已在"近似"标注中隐含说明，但建议在三档阈值策略表中增加脚注："当恰好有 1000 条结果时，提示具有过报风险，但倾向安全（宁可多提示不遗漏截断）"。

---

### 4.10 `BroadcastChannel` 兼容性

**位置**: §4.5 第 7 点

**问题**: `BroadcastChannel('authz-refresh')` 在旧版 Safari（< 15.4）和所有版本 IE 中不可用。文档提到"降级 `storage` 事件"，但未说明降级判断逻辑或是否需要 polyfill。

**建议**: 增加一行："使用 `typeof BroadcastChannel !== 'undefined'` 判断，不可用时降级 `storage` 事件"。

---

### 4.11 `ProjectSearchParams.ownership_id` deprecated + 新增 `manager_party_id`——语义不等价

**位置**: §4.1 [MODIFY] `types/project.ts`

**问题**: 搜索参数从 `ownership_id`（权属方 ID，对应项目的 owner 关系）迁移到 `manager_party_id`（管理方 ID）。这两个字段的**语义不同**：ownership（所有权）vs management（管理权）。

`ownership_relations[].ownership_id` 的 `relation_type` 可以是多种类型，直接用 `manager_party_id` 替代可能导致检索结果语义偏移。文档未解释为什么项目搜索口径从"按 owner 搜"变为"按 manager 搜"。

**建议**: 明确说明语义切换原因（如"项目模型仅支持 manager 视角"），或考虑同时提供 `owner_party_id` 和 `manager_party_id` 搜索参数。

---

## 5. 结构性评价

### 5.1 文档可维护性风险

38 轮迭代产生的叠加补丁使文档呈现"地质层"结构——同一决策点（如 `/403` 落点策略）的讨论分散在 §4.4.2 D7、§5.1 P3d Entry/Exit、§6.3 PowerShell 等多处，且每处附带不同版本号（v1.23/v1.29/v1.34）的修正历史。执行者需要跨越 5+ 个章节才能拼凑出一个决策的完整执行路径。

**建议**: 考虑产出一份精简版"P3 执行手册"（与本详细设计文档分离），仅包含每个子阶段的：入口门禁列表、变更清单、出口门禁列表、回滚步骤。去掉所有历史讨论和版本号标记。

### 5.2 门禁严谨性

文档的门禁设计整体严谨，特别是：
- 双平台命令覆盖（Bash + PowerShell）
- 排除单源统一管理（§5.2）
- Entry/Exit 分离，阻断项显式标注
- `/403` 落点、feature flag、权限单源等关键决策均强制冻结

这是文档的**最大亮点**，值得在后续 Phase 中沿用。

### 5.3 工作量估算缺失

文档详细列出了 84+ 修改文件和 17 新增文件，但**没有任何工时估算**。甘特图给出了天数（P3a=3d, P3b=4d, P3c=5d, P3d=3d, P3e=2d），但未说明假设的人力数量和每日有效工时。单人执行 P3c（30+ 组件 + 15+ 页面修改）在 5 天内完成极具挑战性。

---

## 6. 问题汇总统计

| 级别 | 数量 | 关键项 |
|------|------|--------|
| 🔴 阻断 (P0) | 5 | PermissionGuard 遗漏、psql 连接参数、mocks 口径矛盾、PERMISSIONS 消费者盘点、门禁 A 命令逻辑缺陷 |
| 🟠 重大 (P1) | 7 | AuthGuard 过度处置、party_relations 后端工作量、CORS expose_headers、RentContractAsset 遗漏、AuthState 三接口同步、项目降级方案、feature flag 伪代码缺失 |
| 🟡 中等 (P2) | 9 | 文档噪声、ResourceType 不一致、统计字段迁移、asset/types.ts、check:route-authz 脚本、grep 交互、tenant_party_id 联动、台账创建链路、无资产项目判定 |
| 🔵 建议 (P3) | 11 | authz.py 路径、甘特图重复、PowerShell 排除、CapabilityGuard adminOnly、assetFactory、TTL/cooldown 交互、DataPolicyTemplate 转换、UI 规格、截断近似、BroadcastChannel、搜索语义 |
| **合计** | **32** | |

---

## 7. 建议的后续动作

1. **执行前阻断修复**（P0 × 5）：在任何子阶段启动前修复全部阻断项，其中 psql 连接参数和 grep 命令修复成本最低。
2. **产出精简执行手册**：从 1646 行设计文档中提取约 400 行的纯执行手册，按子阶段组织。
3. **后端 Phase 2-patch 工作量细化**：特别是 `party_relations[]` 交付，需拆分为 Schema/Service/兼容层三步并估时。
4. **CORS `expose_headers` 补丁纳入 Phase 2-patch**。
5. **P3c/P3d 并行执行风险评估**：如果只有 1-2 人执行前端改造，P3c 和 P3d 的并行可能实际退化为串行。需明确人力分配。
