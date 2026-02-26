# Phase 3 实施计划（v1.27）完整审阅报告

**审阅对象**: `docs/plans/2026-02-20-phase3-implementation-plan.md`（v1.27）  
**审阅日期**: 2026-02-21  
**审阅方法**: 文档逐段精读 + 代码仓全量实证核验 + 后端契约交叉验证 + 上游设计文档一致性检查  
**审阅范围**: 文档完整性、统计基线准确性、门禁可执行性、架构一致性、隐性假设、边界条件、风险遗漏  
**审阅口径**: `frontend/src/**/*.ts(x)`，排除 `__tests__/`、`tests/`、`test/`、`*.test.*`、`*.spec.*`（与文档声明一致）

---

## 一、总体评价

**有条件通过**——计划经历了 27 个迭代版本，在架构方向、阶段依赖关系、主链识别上是正确和成熟的。但仍存在统计偏差（`ownership_id`/`ownership_entity` 计数失真）、关键基础设施缺失（`.env.production` 不存在、CI 不含 feature flag 断言）、部分后端契约实证与计划描述不一致（`require_authz` 资源名分布）以及若干门禁命令在实际环境中不可执行的问题。

完成本报告的 P0/P1 整改后可作为正式执行基线。

---

## 二、问题清单

### 严重级别定义

| 级别 | 含义 |
|------|------|
| **P0** | 必须在启动执行前修正，否则会导致迁移范围丢失、门禁假通过或环境不可用 |
| **P1** | 应在执行前修正，否则会增加显著返工或安全风险 |
| **P2** | 建议优化，提升执行效率与文档可维护性 |
| **P3** | 信息性建议，不阻塞执行 |

---

## P0（必须先修）

### P0-1：`ownership_id` 影响文件数失真（26 → 实际 25）

**文档声明**：§3.1 `ownership_id` 影响文件数为 **26**。

**实证复算**：按文档口径（排除测试目录）精确扫描为 **25 个非测试文件**。

| # | 文件路径 |
|---|----------|
| 1 | `frontend/src/assetFormSchema.ts` |
| 2 | `frontend/src/utils/assetCalculations.ts` |
| 3 | `frontend/src/types/rentContract.ts` |
| 4 | `frontend/src/types/project.ts` |
| 5 | `frontend/src/types/pdfImport.ts` |
| 6 | `frontend/src/types/asset.ts` |
| 7 | `frontend/src/services/projectService.ts` |
| 8 | `frontend/src/services/pdfImportService.ts` |
| 9 | `frontend/src/services/asset/types.ts` |
| 10 | `frontend/src/hooks/useProject.ts` |
| 11 | `frontend/src/pages/Rental/ContractRenewPage.tsx` |
| 12 | `frontend/src/pages/Rental/RentStatisticsPage.tsx` |
| 13 | `frontend/src/pages/Rental/RentLedgerPage.tsx` |
| 14 | `frontend/src/pages/Ownership/OwnershipDetailPage.tsx` |
| 15 | `frontend/src/pages/Contract/ContractImportReview.tsx` |
| 16 | `frontend/src/components/Project/ProjectList.tsx` |
| 17 | `frontend/src/components/Forms/ProjectForm.tsx` |
| 18 | `frontend/src/components/Forms/AssetForm.tsx` |
| 19 | `frontend/src/components/Forms/RentContract/RelationInfoSection.tsx` |
| 20 | `frontend/src/components/Forms/Asset/AssetBasicInfoSection.tsx` |
| 21 | `frontend/src/components/Forms/RentContract/RentContractFormContext.tsx` |
| 22 | `frontend/src/components/Asset/AssetSearch/AdvancedSearchFields.tsx` |
| 23 | `frontend/src/components/Asset/AssetSearch.tsx` |
| 24 | `frontend/src/components/Analytics/Filters/FiltersSection.tsx` |
| 25 | `frontend/src/components/Rental/ContractList/ContractFilterBar.tsx` |

**差异来源**：文档计入了 `test-utils/factories/projectFactory.ts`（位于 `test-utils/` 目录，按声明口径应排除）。

**影响**：若执行者按 26 盘点工作量并在 25 处完成后认为"还有 1 处未找到"，会浪费排查时间或引入错误修改。

**建议**：修正为 25（纯运行时）+ 1（`test-utils`，归入测试适配独立清单），并与 §3.1 统计口径排除声明保持一致。

---

### P0-2：`ownership_entity` 影响文件数失真（19 → 实际 18）

**文档声明**：§3.1 `ownership_entity` 影响文件数为 **19**。

**实证复算**：**18 个非测试文件**。若将 `test-utils/factories/assetFactory.ts` 计入则为 19——但该文件位于 `test-utils/` 目录，按文档声明的排除规则不应计入。

**遗漏但实际命中的文件**：
- `frontend/src/mocks/fixtures.ts` — 包含 `ownership_entity` 但不在 §3.1 的"主要分布"列表中。
- `frontend/src/pages/Assets/components/AssetCard.tsx` — 包含 `ownership_entity` 但 §3.1 仅列出 `pages/Assets/*` 而未具体展开。

**影响**：§3.1 的"主要分布"列表不完整，执行者可能遗漏 `mocks/fixtures.ts` 的适配（虽非生产运行时，但影响测试 mock 数据的正确性）。

**建议**：
1. 修正计数为 18（排除 `test-utils`）或 19（含 `test-utils`），并明确口径。
2. 在分布列表中补充 `mocks/fixtures.ts`。

---

### P0-3：`assetImportExportService.ts` 无旧字段命中但被列入 §4.3 改造清单

**文档声明**：§4.3 资产模块改造表中列出 `asset/assetImportExportService.ts` 需要"模板字段映射适配"。§4.6 也将其列入 P3e 改造范围。

**实证核验**：文件存在（310 行），但 **不包含** `ownership_id`、`organization_id`、`management_entity`、`ownership_entity` 中任何一个字段。

**影响**：
- 若该文件确实不含旧字段，则 §4.3 和 §4.6 的改造条目为虚增工作量。
- 若旧字段以间接方式引用（如通过计算属性或导入常量映射），需明确说明间接引用链路。

**建议**：验证该文件的实际迁移需求，若无则从改造清单移除或标注"仅做契约审计 + 回归验证"。类似地，`RentContractExcelImport.tsx` 也无旧字段直接命中，应统一处理。

---

### P0-4：`.env.production` 不存在——P3d 生产验签门禁无法执行

**文档声明**：§4.4.2 D9 要求"生产环境必须显式声明 `VITE_ENABLE_CAPABILITY_GUARD` 值"，P3d Entry 门禁包含 `grep -n "VITE_ENABLE_CAPABILITY_GUARD" frontend/.env.production`。

**实证核验**：`frontend/.env.production` **不存在**。目前仅有 `.env.development` 和 `.env.example`。

**影响**：P3d Entry 门禁直接失败——不是因为 flag 未配置，而是因为文件本身不存在。这会阻塞整个 P3d 启动。

**建议**：
1. 在执行 P3d 前创建 `frontend/.env.production`，至少包含 `VITE_ENABLE_CAPABILITY_GUARD=false`。
2. 或者修改门禁为"验证 `.env.production` 文件存在且包含显式声明"（含文件创建步骤）。

---

### P0-5：CI 工作流不含 `VITE_ENABLE_CAPABILITY_GUARD` 断言——P3d Entry 门禁假通过

**文档声明**：§4.4.2 D9 + §5.1 P3d Entry 门禁要求 `grep -rEn "VITE_ENABLE_CAPABILITY_GUARD" .github/workflows/ --include="*.yml"` 有输出。

**实证核验**：`.github/workflows/` 目录存在 3 个文件（`ci.yml`、`quality-trends.yml`、`security.yml`），均 **不包含** `VITE_ENABLE_CAPABILITY_GUARD`。

**影响**：P3d Entry 门禁要求"CI 发布前断言"，但事实上 CI 中没有任何 feature flag 相关检查。该门禁当前环境下必然失败。

**建议**：
1. P3d 执行前在 CI 配置中补充 feature flag 验证步骤，或
2. 将该门禁拆分为"P3d 可入但必须在 P3d Exit 前完成 CI 集成"（降低阻断级别）。

---

### P0-6：`require_authz` 资源名分布与计划 §4.4.1(B) 不一致

**文档声明**：§4.4.1(B) 资源名映射矩阵中声明：
- `user` → 后端实际为 `asset`
- `role` → 后端实际为 `asset`
- `system` → 后端实际为 `asset`

**实证核验**（后端代码实际使用）：

| `resource_type` | 实际使用位置 |
|---|---|
| `"asset"` | `backup.py`、`dictionaries.py`、`notifications.py`、`monitoring.py`、`roles.py`（大部分端点） |
| `"user"` | `users.py`（L130, L157, L533, L583, L636）及 `roles.py`（L119） |
| `"party"` | `party.py`、`contracts.py`（L83） |
| `"system"` | `system_settings.py`（L693, L754） |
| `"rent_contract"` | `excel_ops.py` |

**关键差异**：
1. `"user"` 在后端是**实际使用的 resource_type**（不仅是 `"asset"`）。`users.py` 多处端点使用 `require_authz(action=..., resource_type="user")`。
2. `"system"` 在后端也有独立使用（`system_settings.py`），不全是 `"asset"`。
3. `"role"` 确实不存在于任何 `require_authz` 调用中——角色管理端点几乎都用 `"asset"` 作为 resource_type。

**影响**：
- 计划声明"system/user/role 后端都是 asset"是**部分错误**的。`user` 和 `system` 在部分端点中是独立的 resource_type。
- 若前端按照计划一律走 `adminOnly` 而不走 `canPerform('read','user')`，可能在后端具备 `user.read` ABAC 规则的场景下过度限制（只有管理员能看，而实际应该有 `user.read` 能力的非管理员也可以看）。
- 当然，Phase 3 的 D2 决策（admin-only 守卫）是一个可接受的保守策略，但文档不应在事实描述上出错。

**建议**：修正 §4.4.1(B) 的"后端 resource_type"列，准确反映 `user` 和 `system` 的实际使用情况，并在 D2 决策文字中增加"虽然后端部分端点已使用 `user`/`system` resource_type，但因 ABAC 种子覆盖不完整，Phase 3 保守采用 adminOnly"的说明。

---

## P1（应在执行前修）

### P1-1：`rentContractExcelService.ts` 的 `baseUrl` 实际值与计划描述不完全对齐

**文档声明**：§4.2 要求修正 `baseUrl='/api/rental'` → 相对 `apiClient.baseURL` 的 `/rental-contracts/*`。

**实证核验**：
- `rentContractExcelService.ts` 实际 `baseUrl = '/api/rental'`（L43），确认与计划描述一致。
- 后端合同 Excel 路由注册路径为 `/api/v1/rental-contracts/excel/*`。
- `apiClient.baseURL` 在开发环境为 `/api/v1`（通过 Vite proxy），`.env.example` 为 `http://127.0.0.1:8002/api/v1`。

**问题**：
1. 计划要求改为 `/rental-contracts/*`（相对路径），加上 `apiClient.baseURL` (`/api/v1`) 后完整路径为 `/api/v1/rental-contracts/*` — 这与后端注册路径匹配。
2. 但计划同时声明"禁止写 `/api/v1/*` 以避免双前缀"。如果 `baseURL` 所在环境变量被设为 `http://127.0.0.1:8002/api/v1`，则 `/rental-contracts/*` 拼接后为 `http://127.0.0.1:8002/api/v1/rental-contracts/*` — 正确。
3. **但如果** `baseURL` 被设为 `http://127.0.0.1:8002`（无 `/api/v1`），则 `/rental-contracts/*` 会变成 `http://127.0.0.1:8002/rental-contracts/*` — 404。

**建议**：§4.2 中的 Excel 路径迁移步骤需增加对 `API_BASE_URL` 最终包含 `/api/v1` 的运行时断言，或在 `rentContractExcelService` 内部显式使用 `${API_BASE_URL}/rental-contracts/...` 并补充环境变量检查。

---

### P1-2：`OwnershipManagementPage.tsx` 无旧字段但列入改造清单

**文档声明**：§4.3 列出 `pages/Ownership/OwnershipManagementPage.tsx` 需要"标记 deprecated 或引导到 Party 管理"。

**实证核验**：该文件存在，但 **不包含** `ownership_id`、`ownership_entity`、`organization_id`、`management_entity`。

**影响**：
- 该文件不需要字段迁移，但可能需要整体 deprecated 标记或 UI 引导。
- 计划应区分"字段迁移"和"模块级 deprecated 标记"两种不同的改造类型。

**建议**：保持改造条目但标注为"模块级 deprecated 标记（无字段迁移）"，避免执行者在寻找旧字段时困惑。

---

### P1-3：后端 `project_to_response` 的 `ownership_relations=[]` 硬编码问题确认——但 Phase 2 修复责任未明确时间锚点

**文档声明**：§4.2 `v1.24 阻断补充` 要求"P3b Entry 前必须修复"。§1 `v1.26 承接归属补充` 将其归入"Phase 2-patch"。

**实证核验**：`backend/src/services/project/service.py` 中 `project_to_response()` 确实硬编码 `data["ownership_relations"] = []`，且不存在 `party_relations` 字段。

**影响**：
- 这是 P3b 的硬阻塞——确认正确。
- 但"Phase 2-patch"缺乏具体的 Alembic revision 或 PR 编号索引，执行时可能出现"Phase 2 说已修但实际未改"的模糊地带。

**建议**：在 §1 中增加"后端修复的验证方式"（如"调用 `GET /api/v1/projects/{id}` 返回非空 `party_relations[]` 或包含有效数据的 `ownership_relations[]`"），给 P3b Entry 一个可操作的验证步骤。

---

### P1-4：`usePermission` 命中文件数与计划分布不完全匹配

**文档声明**：§3.1 `usePermission` 影响文件数为 7，分布为：`hooks/usePermission` · `components/System/PermissionGuard` · `components/Asset/AssetList` · `components/Router/RouteBuilder` · `components/Router/DynamicRouteContext` · `components/Router/DynamicRouteLoader` · `components/Router/index`。

**实证核验**：按口径扫描确认 **7 个文件**命中，列表完全匹配。但需注意 `components/Router/*` 占 4/7（57%），且这些都是 Phase 3 明确不改造的"死代码"——意味着 P3e 物理删除 `usePermission.tsx` 后，Router 目录下 4 个文件将出现编译错误。

**影响**：
- 计划 §4.4 REVIEW/DEFER 部分声明 Router 目录"仅执行目录级审计与遗留标记"。
- 但 P3e 要求物理删除 `usePermission.tsx`，会直接导致 `RouteBuilder`、`DynamicRouteContext`、`DynamicRouteLoader`、`index.ts` 编译失败。
- P3d Exit 门禁（"非主链权限残留已形成处置结论"）必须明确是物理删除这些文件还是改为仅导入 `useCapabilities`。

**建议**：在 P3e 改造清单中显式列出 `components/Router/` 目录下 4 个文件的同步处理方式（删除 `usePermission` 引用或删除整个文件），避免 P3e 最后一步出现级联编译错误。

---

### P1-5：`canAccessOrganization` 在生产代码中从未被消费

**文档声明**：§3.1 列出 `canAccessOrganization` 影响文件数为 1（`hooks/usePermission`）。§4.4 要求废弃。

**实证核验**：`canAccessOrganization` 在 `usePermission.tsx` 中定义（L120）并导出（L187），但在**所有非测试前端代码中没有任何消费方**。仅在测试文件（`usePermission.test.tsx`、`PermissionGuard.test.tsx`）中被调用。

**影响**：该函数已经是死代码，文档将其作为一个需要迁移的"影响点"，实际上跟随 `usePermission.tsx` 物理删除即可——无需额外的功能迁移或兼容处理。

**建议**：在 §3.1 中标注"`canAccessOrganization` 为死代码（无生产消费方），随 `usePermission.tsx` 删除即完成"，避免执行者投入不必要的迁移分析。

---

### P1-6：`AuthGuard.tsx` 与 `PermissionGuard.tsx` 实际差异未被计划准确区分

**文档声明**：§4.4.2 D5 声明 `AuthGuard.tsx` "确认脱离主生效链"，仅标记 `@deprecated`。§4.4 要求 `PermissionGuard.tsx` 内部代理到 `CapabilityGuard`。

**实证核验**：
- `AuthGuard.tsx` 使用 `useAuth()` 的 `hasPermission/hasAnyPermission`，**不使用** `usePermission()`。
- `PermissionGuard.tsx` 使用 `usePermission()` hook。
- 两者**都不被** `App.tsx` 或 `AppRoutes.tsx` 引用——当前路由链只做认证判定。
- `PermissionGuard.tsx` 还导出若干预设守卫（`UserManagementGuard`、`AssetManagementGuard` 等）。

**影响**：
- P3d 要求 `PermissionGuard.tsx` 代理到 `CapabilityGuard`，但如果它同时也未被主链消费，这个代理改造的价值存疑。
- 需确认 `PermissionGuard.tsx` 的预设守卫（如 `AssetManagementGuard`）是否在某些页面组件内部被直接使用。如果是，则代理改造有价值；如果不是，则应和 `AuthGuard.tsx` 一样标记 deprecated 即可。

**建议**：执行以下 grep 确认消费情况后决定策略：
```bash
grep -rEn "PermissionGuard|UserManagementGuard|AssetManagementGuard|RoleManagementGuard|OrganizationManagementGuard|SystemLogsGuard|RentalManagementGuard|AssetCreateGuard" frontend/src/ --include="*.tsx" --exclude="PermissionGuard.tsx" --exclude-dir="__tests__"
```

---

### P1-7：`types/rentContract.ts` 改造点数声明勘误

**文档声明**：§4.1 `types/rentContract.ts` 修改说明中的"**全量迁移范围（v1.26 勘误）**"列出了"共 12 处"迁移位点，v1.12 文档历史提到"全文件 13 处"。这两个数字存在 1 的偏差。

**实证核验**：精确扫描结果为 **12 行**含 `ownership_id` 或 `ownership_ids` 的字段定义——与 v1.26 声明的 12 处一致。v1.12 的"13 处"可能是早期版本中存在后被删除的一处，或计数口径不同。

**影响**：v1.12 历史记录的"13 处"可能造成困惑。

**建议**：在 §10 文档历史 v1.12 条目中添加勘误说明"v1.26 修正为 12 处"。

---

### P1-8：§4.2 `services/assetService.ts` 变更表中列出 `ownership_entity`/`management_entity` 迁移但未列出具体涉及的子文件

**文档声明**：§4.2 资产服务变更表列出"过滤参数 `ownership_entity`/`management_entity` → `owner_party_id`/`manager_party_id`"。

**实证核验**：
- `services/asset/types.ts` 包含 `ownership_entity` 引用（L119-120, L194-195）——确认需要迁移。
- `services/asset/assetDictionaryService.ts` 包含 `management_entity`（L188）和 `ownership_entity`（L181）——确认需要迁移。
- 但这两个文件未在 §4.2 的变更表中显式列出（表中只有 `asset/types.ts` 和 `asset/assetImportExportService.ts`）。

**建议**：将 `asset/assetDictionaryService.ts` 显式加入 §4.2 变更表。

---

### P1-9：`party_relations[]` 契约字段命名的前后端一致性未验证

**文档声明**：§4.1 `types/project.ts` 中定义了 `party_relations[]` 字段契约（含 `party_id`、`party_name`、`relation_type`、`is_primary`）。§4.2 `projectService.ts` 要求前端统一消费 `party_relations[]`。

**实证核验**：后端 `project_to_response()` **当前不返回** `party_relations` 字段。后端 Project 模型/Schema 中也**未定义** `party_relations` 字段。

**影响**：前端定义了一个后端尚不存在的字段契约，P3b 执行时会发现 API 响应中没有这个字段。虽然 §4.2 已声明这是 P3b Entry 硬门禁（"后端必须交付"），但契约的具体字段名、嵌套结构、响应格式都还没有经过后端确认。

**建议**：在 §4.1 的 `party_relations[]` 字段契约旁增加"**待后端确认冻结**"标注，P3b Entry 时以后端实际 Schema PR 为准，避免前端按假定结构开发后需要大面积返工。

---

## P2（建议优化）

### P2-1：门禁命令可移植性改进空间

**现状**：v1.27 已新增 §6.4 PowerShell 等价命令，覆盖了主要门禁。但以下门禁仍仅有 bash 版本：

| 门禁 | 缺失平台 |
|------|----------|
| P3a Exit `grep -r "@deprecated" frontend/src/types/organization.ts frontend/src/types/ownership.ts` | PowerShell |
| P3b Exit 旧字段零引用（`! grep -rEl ...`） | PowerShell |
| P3d Exit 门禁 A/B（复杂 bash `find|xargs|grep`） | PowerShell |
| P3e Exit 旧字段类型移除验证 | PowerShell |
| §6.2 旧字段零引用全套命令 | PowerShell |

**建议**：至少为 P3d Exit 门禁 A（含 `find|xargs` 管道的复杂命令）提供 PowerShell 等价版，因为该命令是最容易在 Windows 上出错的。

---

### P2-2：§4.3 页面层改造清单与实际文件命中不完全对齐

**比较结果**（部分差异）：

| 文件 | §4.3 列入 | 实际含旧字段 | 说明 |
|------|-----------|-------------|------|
| `components/Rental/RentContractExcelImport.tsx` | ✅ | ❌ | 无旧字段直接命中 |
| `components/Forms/Asset/AssetBasicInfoSection.tsx` | ✅ `ownership_id → owner_party_id` | ✅ `ownership_id` | 一致 |
| `services/asset/assetImportExportService.ts` | ✅ 模板字段适配 | ❌ | 无旧字段直接命中 |
| `components/Rental/ContractDetailInfo.tsx` | ✅ | ✅ `ownership_entity` | 一致 |
| `services/asset/assetDictionaryService.ts` | ❌ 未列出 | ✅ `management_entity` + `ownership_entity` | **遗漏** |

**建议**：对 §4.3 改造清单中每个条目增加"实证依据列"（grep 命中行号），并清理无实际命中的条目或标注"间接依赖——需审计"。

---

### P2-3：§5.2 门禁排除清单缺少 `mocks/` 目录

**现状**：§5.2 定义的 `PHASE3_GREP_EXCLUDES` 排除了 `__tests__`、`test`、`test-utils`、`*.test.*`、`*.spec.*`、`Organization` 相关文件。

**遗漏**：
- `mocks/fixtures.ts` 包含 `ownership_entity`，但 `mocks/` 目录不在排除清单中。
- 如果 mock 数据需要同步迁移（保持测试正确性），则不应排除。
- 如果 mock 数据不在主链范围内，则应加入排除清单。

**建议**：明确 `mocks/` 目录的处理策略并在排除清单中体现。

---

### P2-4：`AuthContext` 现有 `hasPermission/hasAnyPermission` 的调用方盘点范围偏窄

**文档声明**：§4.2 提供了盘点命令 `grep -rEn "useAuth\(\)\.(hasPermission|hasAnyPermission)|\bhasPermission\(" frontend/src/ ...`。

**遗漏场景**：
- `useAuth()` 解构后调用：`const { hasPermission } = useAuth(); ... hasPermission(...)` — 此模式中 `hasPermission(` 能被匹配，但如果被赋值到另一个变量名则不行。
- `AuthGuard.tsx` 内部调用 `useAuth()` 的 `hasPermission`/`hasAnyPermission`——这个文件已声明 `@deprecated`，但如果它被某个页面导入使用，则形成间接调用链。

**建议**：在盘点命令中增加 `AuthGuard` 消费方搜索：
```bash
grep -rEn "AuthGuard" frontend/src/ --include="*.tsx" --exclude="AuthGuard.tsx" --exclude-dir="__tests__"
```

---

### P2-5：`capabilities` 缓存 TTL 10 分钟的合理性论证缺失

**文档声明**：§4.2 定义 capabilities TTL 为 10 分钟。

**问题**：
- 为什么是 10 分钟而不是 5 分钟或 30 分钟？缺乏选取依据。
- 如果管理员修改了某用户的角色权限，用户最长需要等 10 分钟才能感知变化（除非触发 403 → 静默 refresh）。
- 对于安全敏感操作（如导出、删除），10 分钟的延迟是否可接受？

**建议**：增加 TTL 选取理由说明（如"基于平均会话时长与权限变更频率评估"），并明确"对安全敏感操作是否需要实时校验"。

---

### P2-6：`ROUTE_CONFIG` 废弃决策（D6）的执行验证缺失

**文档声明**：§4.4.2 D6 声明 `ROUTE_CONFIG` 固定为"显式废弃"，运行时唯一路由权限真源为 `AppRoutes.tsx`。

**实证核验**：`ROUTE_CONFIG` 当前定义在 `constants/routes.ts`（L114+），但**不被** `AppRoutes.tsx` 或 `App.tsx` 消费。它被 `RouteBuilder.tsx` 等 Router 目录文件消费。

**问题**：计划声明 ROUTE_CONFIG 废弃，但没有为 P3d/P3e Exit 提供专门的验证命令来确认"ROUTE_CONFIG 未被新增代码引用"。

**建议**：在 P3d Exit 增加：
```bash
# ROUTE_CONFIG 未被新代码引用（仅允许在 routes.ts 自身和已冻结的 Router/* 中出现）
! grep -rEl "ROUTE_CONFIG" frontend/src/ --include="*.ts" --include="*.tsx" \
  --exclude="routes.ts" --exclude-dir="Router" --exclude-dir="__tests__"
```

---

### P2-7：`project` 资源的 `perspectives` override 与后端 `require_authz` 行为的一致性验证

**文档声明**：§4.4（v1.26）定义前端 `project` resource 的 perspectives override 为 `['manager']`。

**实证核验**：后端 `party.py` 的 `require_authz` 对 Party 资源使用 `resource_type="party"`；但后端的 capabilities 生成逻辑（`authz_service.get_capabilities()`）的 `perspectives` 实际生成方式未在计划中明确交叉验证。

**建议**：在 P3d Entry 前，用实际非管理员账号调用 `GET /api/v1/auth/me/capabilities` 并记录 `project` resource 的 `perspectives` 返回值。如果后端返回的 perspectives 已经无 `owner`，则前端 override 是冗余的；如果包含 `owner`，则 override 是必要的。记录此验证结论。

---

### P2-8：数据策略包管理页面的路由路径未定义

**文档声明**：§3.2 列出新增 `pages/System/DataPolicyManagementPage.tsx`。§4.3 常量与路由配置部分提到"新增 `DataPolicyManagementPage` 路由条目"。

**遗漏**：未定义该页面的具体路由路径（如 `/system/data-policies`），也未在 §4.4.2 的路由守卫策略中明确该路由的权限元数据（是 `adminOnly` 还是需要特定 capability？）。

**建议**：
1. 指定路由路径（建议 `/system/data-policies`）。
2. 在 §4.4.2 D2 adminOnly 路由清单中增加该路由。

---

## P3（信息性建议）

### P3-1：甘特图的并行依赖表达力限制已声明但可以改进

**现状**：Mermaid Gantt 不支持 AND 双前置——文档已用注释说明（v1.17 注记）。

**建议**：可将甘特图替换为 `graph LR` 流程图（文档§5中已有一个较好的示例），或者在甘特图旁增加一个简化的依赖矩阵表。

---

### P3-2：文档历史（§10）信息密度过高

**现状**：§10 记录了 v1.11–v1.27 共 17 个版本的变更摘要，占文档末尾约 100 行。

**建议**：仅保留最近 3 个版本（v1.25–v1.27）在正文，其余折叠到"详见 Git 历史"或独立的 changelog 文件。

---

### P3-3：§4.1 `types/party.ts` 的 `FrontendPartyHierarchyEdge` 命名与后端响应契约脱节

**问题**：后端 `GET /api/v1/parties/{id}/hierarchy` 返回 `list[str]`（子 Party ID 列表），但前端定义了 `FrontendPartyHierarchyEdge`（含 `parent_party_id`/`child_party_id`）—— 这在后端响应中不存在。文档已标注为"前端内部树组装辅助类型"，标注准确，但命名可能引起"是否应该与后端响应对齐"的困惑。

**建议**：考虑重命名为 `_InternalPartyTreeEdge` 或加上更显著的 JSDoc 说明"此类型不映射到任何 API 响应"。

---

### P3-4：`capabilityEvaluator.ts` 纯函数与 Hook 的职责边界需要更明确的接口定义

**文档声明**：§3.2 列出 `utils/authz/capabilityEvaluator.ts` 提供 `evaluateCapability()`/`hasPartyScopeAccess()` 纯函数。

**问题**：
- `evaluateCapability()` 应该接收什么参数？`(capabilities, action, resource, perspective?)` 还是 `(capability, action)`？
- `hasPartyScopeAccess()` 应该接收什么参数？`(capabilities, partyId, relationType)` 还是 `(dataScope, partyId, relationType)`？
- 目前只有函数名，没有签名。

**建议**：在 §4.4 中给出与 `useCapabilities` 同等详细程度的函数签名草案。

---

### P3-5：静默 refresh 的"诊断日志"（§4.5 条目 5）缺乏具体实现指引

**文档声明**：记录 `request_id`、触发原因、是否命中 cooldown。

**问题**：前端通常没有 `request_id`（这是后端概念）。如果指的是 `config.url + config.method`，应明确说明。

**建议**：修改为"记录 `request URL`、`HTTP method`、触发原因、是否命中 cooldown、距上次 refresh 间隔秒数"。

---

### P3-6：运行时请求载荷拦截器（§6.2 末尾）的正则表达式存在误判风险

**文档声明**：拦截 `organization_id|ownership_id|ownership_ids|management_entity|ownership_entity` 用正则匹配 JSON payload。

**问题**：
- 正则 `(^|["'{,\s])` 可能匹配到注释或 JSON 嵌套结构中的无关字符串。
- 如果后端在过渡期仍要求 `organization_id`（如 `systemService.ts` 的 `default_organization_id → organization_id` 映射），该拦截器会产生误报。

**建议**：增加白名单过滤（如排除发往 `/api/v1/users` 的请求中的 `organization_id`），或将拦截级别从 `console.error` 改为 `console.warn`，配合可选开关。

---

### P3-7：§7.3 回滚步骤中缺少前端启动验证

**现状**：回滚步骤包含 `pnpm install` → `type-check + lint + guard:ui` → `pnpm test`，但没有 `pnpm dev` 或 `pnpm build` 后的浏览器冒烟验证。

**建议**：增加"启动开发服务器 → 访问核心页面 → 确认无白屏"的回滚验证步骤。

---

## 三、上游一致性检查

### 与设计文档（Party-Role Architecture Design v3.9）的一致性

| 设计文档要求（§5.2） | Phase 3 计划对应 | 一致性 |
|---|---|---|
| 登录 + token refresh 必须重拉 capabilities | §4.2 `AuthContext.tsx` 改造 ✅ | **一致** |
| 前端用 capability snapshot 控制 UI 可见性 | §4.4 `useCapabilities` + `CapabilityGuard` ✅ | **一致** |
| 静默 refresh on 403，cooldown ≥30s，single-flight | §4.5 防风暴策略 ✅ | **一致** |
| 后端返回 `X-Authz-Stale: true` | §4.5 标注偏离（后端未实现），计划使用 403+错误标识降级 ✅ | **一致（已声明偏离）** |
| `usePermission` → `useCapabilities` | §4.4 ✅ | **一致** |
| "待补绑定"标签 + 面积 N/A | §4.3 项目模块 ✅ | **一致** |

### 与 Phase 2 实施计划的一致性

| Phase 2 交付物 | Phase 3 消费声明 | 一致性 |
|---|---|---|
| ABAC seed 策略包（7 包）| §1 列出具体 migration 文件名 ✅ | **一致**，实际文件已验证存在 |
| 数据策略管理 3 接口 | §4.4 `dataPolicyService.ts` ✅ | **一致**，后端接口已验证存在 |
| `GET /api/v1/auth/me/capabilities` | §4.2 `capabilityService.ts` ✅ | **一致**，后端接口已验证存在 |
| 旧权限服务 deprecated | §4.4 `usePermission` deprecated ✅ | **一致** |

---

## 四、代码仓现状快照（关键证据汇总）

| 核验项 | 实际状态 |
|--------|----------|
| `CapabilityGuard` 组件 | **不存在**（需创建） |
| `useCapabilities` Hook | **不存在**（需创建） |
| `capabilityEvaluator.ts` | **不存在**（需创建） |
| `AuthContext.capabilities` | **不存在**（需新增字段） |
| `AuthContext.isAdmin` | **不存在**（需新增字段） |
| `AuthContext.capabilitiesLoading` | **不存在**（需新增字段） |
| `protectedRoutes` 权限元数据 | **不存在**（只有 `path + element`） |
| 路由权限判定 | **仅认证判定**（无 capability/permission 检查） |
| `AuthGuard.tsx` | 存在但不在主链 |
| `PermissionGuard.tsx` | 存在但不在路由主链 |
| `ROUTE_CONFIG`（`constants/routes.ts`）| 存在，含 `permissions` 元数据，但不被主链消费 |
| `usePermission.tsx` | 存在，导出 `PERMISSIONS`/`PAGE_PERMISSIONS`/hook |
| 后端 `search` 参数（`/parties`）| **不存在**（P3b 硬阻塞确认） |
| 后端 `party_relations` 字段（项目响应）| **不存在**（P3b 硬阻塞确认） |
| 后端 `project_to_response` `ownership_relations=[]` 硬编码 | **确认存在** |
| 后端 `X-Authz-Stale` 响应头 | **不存在**（偏离已声明） |
| `.env.production` | **不存在**（P3d 门禁阻塞） |
| CI `VITE_ENABLE_CAPABILITY_GUARD` | **不存在**（P3d 门禁阻塞） |

---

## 五、整改优先级路径

```
1. [P0] 修正 §3.1 ownership_id (25) / ownership_entity (18) 计数
2. [P0] 清理 §4.3/§4.6 无实际命中文件的改造条目
3. [P0] 创建 .env.production 或修改 P3d 门禁
4. [P0] 修正 §4.4.1(B) require_authz 资源名分布描述
5. [P0] 在 CI 中补充 feature flag 检查或降级为 P3d Exit
6. [P1] 明确 components/Router/* 在 P3e 删除 usePermission 后的处理
7. [P1] 补充 assetDictionaryService.ts 到 §4.2 变更表
8. [P1] 标注 party_relations[] 契约为"待后端确认冻结"
9. [P2] 补 DataPolicyManagementPage 路由路径和权限元数据
10. [P2] 定义 capabilityEvaluator 纯函数签名
```

---

## 六、最终审阅意见

Phase 3 实施计划 v1.27 是一份经过深度迭代的高质量架构迁移文档。27 个版本的演进说明团队在持续纠偏。主要方向正确、阶段依赖清晰、门禁体系完备程度在业界同类文档中处于上游水平。

但仍存在 6 个 P0 问题和 9 个 P1 问题需要修正。其中最具阻塞性的是：
1. **`.env.production` 和 CI feature flag 断言不存在**——会直接导致 P3d Entry 门禁失败。
2. **`ownership_id`/`ownership_entity` 计数偏差**——会造成执行者迷惑（"找不到最后一个文件"）。
3. **`require_authz` 资源名实际情况与文档描述不一致**——可能影响 Phase 4 的前后端对齐决策。

完成上述 P0 + P1 整改后，本计划可作为 Phase 3 的正式执行基线。

---

*审阅完成于 2026-02-21。*
