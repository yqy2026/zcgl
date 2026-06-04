# 架构技术债复核报告

**状态**: ✅ 源报告候选项第一轮收口完成
**源报告日期**: 2026-06-02  
**复核日期**: 2026-06-03  
**来源**: `C:\Users\ygz\AppData\Local\Temp\opencode\architecture-review-20260602-082816.html`

---

## 结论

源 HTML 报告提出 8 个架构候选项。复核后本文档将其合并为 7 个可执行方向：原候选 04（路由注册统一）和原候选 08（`system_settings` 静默加载）拆成“先 fail loud、再决策路由注册标准”两类问题；原候选 06（authz 覆盖率）并入前端 Capability/RBAC 测试面收口。核心方向成立：当前代码仍存在重复实现、迁移收口不彻底、可测试接口不集中等问题。但复核当前代码后，有两处原判断已经过时，不能原样执行：

1. `backend/src/services/authz/*` 已有后端单元测试，不再是原报告所说的 "0% 覆盖率"。当前风险应改为：前端 `capabilityEvaluator` 测试面过窄，且 `organization-scope-isolation.spec.ts` 仍有多处 `test.skip`。
2. `frontend/src/pages/System/*Page.tsx` 中部分旧页面已经变成 42-44 字节的 re-export 壳，不再是旧单体大页面。当前风险应改为：路由、预加载和测试入口仍指向迁移壳，未直接收口到目录模块。

2026-06-03 已完成候选项 01 第一轮收口：通用 `Contact(entity_type, entity_id)`、`/contacts` API、前端 `contactService` 和 `contact` 权限资源已退役；联系人统一从 `PartyContact`、`/parties/{party_id}/contacts` 和 `partyService` 维护。

2026-06-03 已完成候选项 02 主入口收口：前端权限判断公共入口收敛到 `useCapabilities()` / `capabilityEvaluator`，`AuthContext.hasPermission()`、`AuthContext.hasAnyPermission()`、`AuthService.hasPermission()` 和 `AuthService.hasAnyPermission()` 已删除；`capabilityEvaluator.test.ts` 已从 2 条窄用例扩展为覆盖 admin bypass、action、perspective、party scope 和 resource 缺失的矩阵。`organization-scope-isolation.spec.ts` 的剩余 skip 经复核均为运行时环境或测试数据准备守卫，且显式环境变量无效时已有 hard fail，本轮不做无语义的 skip 数量改写。

2026-06-03 已完成候选项 03：`system_settings_router` 已改为直接导入并无条件注册，导入失败会在应用启动或测试导入阶段暴露；`pdf_batch_router` 仍保留可选加载，不与本项混合处理。新增 `test_api_v1_should_register_system_settings_router_fail_loud` 护栏，锁定核心系统设置路由不得回退到 `_load_optional_router()`。

2026-06-03 已完成候选项 04：System 管理页路由、预加载和页面测试入口已直接指向目录模块，`UserManagementPage.tsx`、`RoleManagementPage.tsx`、`OrganizationPage.tsx`、`OperationLogPage.tsx` 四个迁移壳已删除；`PromptDashboard.tsx` 经确认也是 re-export 壳，已纳入同批删除。CSS module 文件名暂保留，因为目录模块和子组件仍直接引用这些样式文件。

2026-06-03 已完成候选项 05 决策与第一处代码收口：路由标准明确为“应用级入口统一通过 `route_registry` 注册；历史 `api_router.include_router()` 仅作为既有 v1 聚合内部布线；模块内已经 `route_registry.register_router()` 自注册的路由不得再被聚合路由二次 include”。`collection` 路由原本同时自注册并被聚合为 `/collections/collection/*` 别名，本轮已移除该二次入口，并新增 `test_registry_owned_routes_should_not_be_included_by_api_router` 护栏。

2026-06-03 已完成候选项 06 第一轮排查：对源报告点名的浅服务候选逐个核对后，未采用“删除 service、API 直连 CRUD”的方案。`ContactService` 已随候选项 01 合并进 `PartyService`；`CollectionService`、`ExcelTaskService`、`SystemSettingsService` 和 `HistoryService` 均保留服务层边界；`document/cache.py` 当前只是缓存子模块聚合导出，不按业务 service 删除。本轮新增 `test_collection_service.py` 与 `test_history_service.py` 服务层业务护栏，补齐催缴服务和历史服务不是浅转发层的代码证据。

2026-06-03 已完成候选项 07 活跃页面复核：System 用户、角色、组织和操作日志四个活跃管理页的服务器数据已经通过各自 `use*Data` React Query hook 获取，页面级 `useEffect` 仅承担错误提示或本地 UI 状态同步。本轮新增 `system-active-pages-data-fetching.test.ts` 静态护栏，锁定活跃页不得回退到页面内直接调用列表、统计或组织历史等服务器服务。`PropertyCertificateList.tsx` 仍是冻结模块残留，不在本轮做功能性 React Query 重构，后续只随冻结可见面清理或归档处理。

源报告候选项第一轮已完成收口；后续若继续扩展浅服务或冻结模块治理，应作为新增候选逐项立案，不再按源报告做批量删除。

第一轮收口结果：

| 优先级 | 候选项 | 当前判断 | 原因 |
|---|---|---|---|
| 已完成 | 合并 `Contact` 与 `PartyContact` 双通路 | 已实施第一轮收口 | 统一到 ADR-0001 的 `party_contacts`；通用 `/contacts` 已删除 |
| 已完成 | 收口前端 Capability/RBAC 入口 | 已实施主入口收口 | 生产权限判断公共入口已统一到 `useCapabilities` / `capabilityEvaluator`；E2E 剩余 skip 为环境守卫 |
| 已完成 | `system_settings` 路由 fail loud | 已实施 | 核心系统设置路由直接导入并无条件注册，失败会阻断启动或测试导入 |
| 已完成 | System 页面迁移入口收口 | 已实施 | 路由、预加载和页面测试入口已直接指向目录模块，迁移壳已删除 |
| 已完成 | 路由注册标准冲突处理 | 已形成标准并修复双注册别名 | 应用级入口统一走 `route_registry`；既有 `include_router` 只作为 v1 内部聚合布线；自注册模块不得再被二次 include |
| 已完成 | 浅服务模块排查 | 已完成源报告点名示例排查 | 点名候选均已逐个处理：通用联系人合并进 Party，其余保留或归类为缓存聚合导出；新增催缴与历史服务层护栏，不做批量删除 |
| 已完成 | 活跃页面的 `useQuery` 迁移 | 活跃页和冻结可见面均已完成复核和护栏 | System 活跃管理页列表、统计、组织历史等服务器取数均走 React Query hook；`PropertyCertificate` 冻结残留不再出现在用户可见入口、全局搜索、面包屑或路由测试中 |

---

## 复核证据摘要

### 已处理的问题

- 前端权限入口已从三套公共表面收口为一套：
  - 生产判断入口：`frontend/src/hooks/useCapabilities.ts`
  - 纯判定器：`frontend/src/utils/authz/capabilityEvaluator.ts`
  - 已删除 `frontend/src/contexts/AuthContext.tsx` 中 deprecated `hasPermission` / `hasAnyPermission`
  - 已删除 `frontend/src/services/authService.ts` 中 static `hasPermission` / `hasAnyPermission`
- `system_settings_router` 已从静默可选加载改为直接导入并无条件注册：
  - `backend/src/api/v1/__init__.py` 直接导入 `backend/src/api/v1/system/system_settings.py`
  - `backend/tests/unit/api/v1/test_system_settings_layering.py` 锁定 `/system/settings` 注册和禁止 `_load_optional_router(".system.system_settings")`
- System 页面迁移入口已收口：
  - `frontend/src/routes/AppRoutes.tsx` 和 `frontend/src/hooks/useSmartPreload.tsx` 直接指向目录模块
  - `frontend/src/pages/System/__tests__/UserManagement.test.tsx` 等页面测试直接导入目录模块
  - 已删除 `UserManagementPage.tsx`、`RoleManagementPage.tsx`、`OrganizationPage.tsx`、`OperationLogPage.tsx` 和 `PromptDashboard.tsx` 迁移壳
- 路由注册标准已明确并补护栏：
  - `AGENTS.md` 明确应用级新 API 通过 `route_registry.register_router()` 注册，历史 `api_router.include_router()` 仅作为既有 v1 聚合内部布线
  - `backend/src/api/v1/__init__.py` 不再把自注册的 `collection` 路由二次 include 到 `/collections/collection/*`
  - `backend/tests/unit/api/v1/test_route_registration_standard.py` 锁定自注册模块不得再被聚合路由二次 include
- 浅服务模块已完成源报告点名示例排查：
  - `backend/src/services/contact/service.py` 已随候选项 01 删除，联系人事实来源合并进 `backend/src/services/party/service.py`
  - `backend/src/services/collection/service.py` 保留汇总口径、台账存在性校验、操作人补全，新增 `backend/tests/unit/services/test_collection_service.py` 业务护栏
  - `backend/src/services/excel/excel_task_service.py` 已有 `mark_task_failed()` 回滚和失败态封装，并由 `backend/tests/unit/services/excel/test_excel_task_service.py` 覆盖
  - `backend/src/services/system_settings/service.py` 已有审计日志封装和数据库连通性检查降级，并由 `backend/tests/unit/services/test_system_settings_service.py` 与 `backend/tests/unit/api/v1/test_system_settings_layering.py` 覆盖
  - `backend/src/services/history/history_service.py` 保留资产筛选存在性校验、详情缺失 404 和删除前存在性检查，新增 `backend/tests/unit/services/test_history_service.py` 业务护栏
  - `backend/src/services/document/cache.py` 是 `cache_sync` / `cache_async` / `cache_extraction` 的聚合导出，现有 `backend/tests/unit/services/document/test_cache.py` 已覆盖通过该导出入口访问缓存能力，不按浅业务 service 删除
- 活跃 System 管理页服务器取数边界已补护栏：
  - `frontend/src/pages/System/UserManagement/hooks/useUserManagementData.ts`、`RoleManagement/hooks/useRoleManagementData.ts`、`Organization/hooks/useOrganizationData.ts`、`OperationLog/hooks/useOperationLogData.ts` 均通过 React Query 获取列表、统计、组织树、权限列表或组织历史等服务器数据
  - `frontend/src/pages/System/__tests__/system-active-pages-data-fetching.test.ts` 锁定四个页面入口不得直接调用对应 list/stat/history 服务方法
  - `frontend/src/routes/__tests__/AppRoutes.authz-metadata.test.ts`、`frontend/src/config/__tests__/rental-retired-navigation.test.ts`、`frontend/src/components/Layout/__tests__/AppSidebar.test.tsx`、`frontend/src/components/Layout/__tests__/AppBreadcrumb.test.tsx` 和 `frontend/src/pages/Search/__tests__/GlobalSearchPage.test.tsx` 锁定冻结 `PropertyCertificate` 不再出现在用户可见入口、菜单、面包屑、路由或搜索提示中

### 仍成立的问题

- `frontend/src/pages/PropertyCertificate/PropertyCertificateList.tsx` 文件仍存在且仍用 `useState + useEffect` 请求服务器数据，但该模块当前属于 Out of Scope 冻结残留，且已不在用户可见入口、全局搜索、面包屑或受保护路由中暴露；后续若要删除文件或恢复功能，应另行立项，不在本轮追加功能性 React Query 重构。

### 原报告需修正的问题

- 后端 authz 测试已存在：
  - `backend/tests/unit/services/test_authz_engine.py`
  - `backend/tests/unit/services/test_authz_cache.py`
  - `backend/tests/unit/services/test_authz_context_builder.py`
  - `backend/tests/unit/services/test_authz_events.py`
  - `backend/tests/unit/services/test_authz_service.py`
- 前端 System 目录迁移不是源报告描述的 "old monolithic page vs ghost tree"：
  - `UserManagementPage.tsx`、`RoleManagementPage.tsx`、`OrganizationPage.tsx`、`OperationLogPage.tsx` 当前只是 re-export 壳。
  - `frontend/src/routes/AppRoutes.tsx` 和 `frontend/src/hooks/useSmartPreload.tsx` 仍指向这些壳文件。
- `ProjectDetailPage.tsx` 的相关 `useEffect` 是把 React Query 得到的 `assets` 送入 `useArrayListData` 做本地分页，并非直接服务器取数；不应按 React Query 违规处理。
- 源报告建议浅服务删除后让 API 直接调用 CRUD，这与本项目分层约束冲突。任何收口都必须保持 `api/v1 -> services -> crud -> models`。

---

## 候选项 01：合并 `Contact` 与 `PartyContact`

**建议级别**: P0  
**实施状态**: ✅ 2026-06-03 已完成第一轮收口  
**涉及文件**:

- `backend/src/models/party.py`
- `backend/src/api/v1/party.py`
- `backend/src/services/party/service.py`
- `backend/src/crud/party.py`
- `backend/src/schemas/party.py`
- `backend/alembic/versions/20260603_drop_generic_contacts.py`
- `frontend/src/services/partyService.ts`
- `frontend/src/types/party.ts`

### 问题

ADR-0001 已把 `party_contacts` 列为 Party-Role 模型核心表。实施前仍保留一条通用 `Contact(entity_type, entity_id)` 通路。两条通路都能表达“联系人”，但约束不同：

| 通路 | 接口 | 数据模型 | 风险 |
|---|---|---|---|
| Party 联系人 | `/parties/{party_id}/contacts` | `PartyContact.party_id` | 与 ADR-0001 一致 |
| 通用联系人 | `/contacts/entity/{entity_type}/{entity_id}` | `Contact.entity_type/entity_id` | 把实体类型判断外泄给调用方，且容易绕开 Party 主档 |

当前决策：联系人是主体主档的一部分，统一从 Party 模块读写。若未来系统需要“项目联系人 / 资产现场联系人”等非 Party 联系人，必须在领域模型和 API 契约中显式定义，不得恢复自由字符串 `entity_type`。

### 已实施内容

- 删除通用 `/contacts` API、`ContactService`、`ContactCRUD`、`Contact` ORM、`schemas/contact.py`、前端 `contactService.ts` 和 `types/contact.ts`。
- 保留 `PartyService.create_contact()` / `PartyService.get_contacts()`，前端通过 `partyService.getPartyContacts()` / `createPartyContact()` 访问 `/parties/{party_id}/contacts`。
- 新增迁移 `backend/alembic/versions/20260603_drop_generic_contacts.py`，删除已落库的 `contacts` 表、`contact` 权限和 `contact` ABAC 规则。
- 同步移除 `backend/src/security/field_validation.py` 与系统监控加密状态中对通用 `Contact` 的引用。
- 同步 `docs/specs/domain-model.md`、`docs/specs/api-contract.md`、`docs/traceability/requirements-trace.md` 和 `CHANGELOG.md`。

### 后续边界

**Done when**:

- 仓库只剩一个联系人事实来源，或非 Party 联系人有明确领域模型。
- API 不再暴露同义联系人写入口。
- 相关单测覆盖主体联系人列表、新增、权限入口和迁移删除。
- `docs/specs/domain-model.md`、`docs/specs/api-contract.md`、`docs/traceability/requirements-trace.md` 和 `CHANGELOG.md` 同步。

---

## 候选项 02：收口前端 Capability/RBAC 入口

**建议级别**: P0  
**实施状态**: ✅ 2026-06-03 已完成主入口收口，E2E 剩余 skip 保留为环境守卫
**涉及文件**:

- `frontend/src/hooks/useCapabilities.ts`
- `frontend/src/utils/authz/capabilityEvaluator.ts`
- `frontend/src/contexts/AuthContext.tsx`
- `frontend/src/services/authService.ts`
- `frontend/src/utils/authz/__tests__/capabilityEvaluator.test.ts`
- `frontend/tests/e2e/auth/organization-scope-isolation.spec.ts`
- `docs/guides/frontend.md`

### 问题

实施前，生产代码已经主要通过 `useCapabilities()` 做权限判断，但过渡期 API 仍留在公共类型中：

- `AuthContext.hasPermission()`
- `AuthContext.hasAnyPermission()`
- `AuthService.hasPermission()`
- `AuthService.hasAnyPermission()`

当前复核未发现这些 deprecated 方法在非测试生产代码中被调用。它们继续存在会让后续调用者误选旧入口，并让权限回归测试分散在多个表面。

### 已实施内容

1. 扩展 `capabilityEvaluator.test.ts`，覆盖：
   - admin bypass
   - action 命中 / 缺失
   - perspective 命中 / 缺失
   - owner/manager party scope 命中 / 拒绝
   - resource capability 缺失
2. 删除 `AuthContext` 类型和实现中的 deprecated 方法。
3. 删除 `AuthService` static 权限判断方法。
4. 更新测试 mock，避免继续把 deprecated 方法作为默认上下文字段。
5. 更新 `docs/guides/frontend.md`，明确权限判断不放入 Zustand，统一走 `useCapabilities().canPerform()` 和 `capabilityEvaluator`。
6. 复核 `organization-scope-isolation.spec.ts` 中的 `test.skip`：剩余 skip 是 CSRF cookie、可用非管理员角色、可用主体 pair、资产读写准备、测试用户创建等运行时环境/测试数据守卫；显式环境变量无效时已有 hard fail。本轮没有发现可稳定恢复且不引入外部前置依赖的 skip 场景，因此不做无语义的 skip 数量改写。

**Done when**:

- 前端生产权限判断只有 `useCapabilities()` / `capabilityEvaluator` 一个入口。
- `capabilityEvaluator.test.ts` 不再只有 2 条窄用例。
- `organization-scope-isolation.spec.ts` 的剩余 skip 有明确环境或测试数据原因；若后续要减少 skip 数量，应先固定 E2E 基础数据或环境变量契约，而不是在本项中改写运行时守卫。

---

## 候选项 03：让 `system_settings` 路由失败时显式暴露

**建议级别**: P1
**实施状态**: ✅ 2026-06-03 已完成
**涉及文件**:

- `backend/src/api/v1/__init__.py`
- `backend/src/api/v1/system/system_settings.py`
- `backend/tests/unit/api/v1/test_system_settings_layering.py`

### 问题

实施前，`system_settings_router` 通过 `_load_optional_router()` 加载。导入失败时，应用继续启动，只是 `/system` 下相关路由缺失。项目处于 0-to-1 阶段，AGENTS 明确要求不要做兼容隐藏，应该充分暴露问题。

### 已实施内容

- 将 `system_settings_router` 改为顶部直接导入。
- 将系统设置路由改为无条件 `include_router()`，导入失败会阻断应用启动或测试导入。
- 保留 `pdf_batch_router` 的可选加载，不和本项混在一个改动里。
- 新增路由注册护栏测试，确认 `/system/settings` 已注册，且 `system_settings` 不再走 `_load_optional_router()`。

**Done when**:

- `system_settings` 导入失败会阻断启动或测试导入。
- `backend/src/api/v1/__init__.py` 不再对核心系统设置路由做静默缺失处理。
- 补充一个路由注册或导入护栏测试。

---

## 候选项 04：System 页面迁移入口收口

**建议级别**: P1
**实施状态**: ✅ 2026-06-03 已完成
**涉及文件**:

- `frontend/src/routes/AppRoutes.tsx`
- `frontend/src/hooks/useSmartPreload.tsx`
- `frontend/src/pages/System/UserManagementPage.tsx`
- `frontend/src/pages/System/RoleManagementPage.tsx`
- `frontend/src/pages/System/OrganizationPage.tsx`
- `frontend/src/pages/System/OperationLogPage.tsx`
- `frontend/src/pages/System/*/__tests__`

### 问题

源报告认为新目录树是“未被路由触达的 ghost tree”，但实施前代码已经把旧 `*Page.tsx` 收缩为 re-export 壳。真实问题是迁移入口没有最后收口：

- 路由仍 import `../pages/System/UserManagementPage` 等壳文件。
- 预加载仍 import `UserManagementPage` / `RoleManagementPage`。
- 测试仍有部分以旧壳文件命名和导入。

这不是 P0 的大规模删除项，但属于 0-to-1 阶段应清掉的兼容壳。

### 已实施内容

1. 将路由和预加载直接切到目录模块，例如 `../pages/System/UserManagement`。
2. 将测试导入同步切到目录模块，并将测试文件名从 `*Page.test.tsx` 收口为目录模块名。
3. 删除 42-44 字节的 re-export 壳文件。
4. 对 `PromptDashboard.tsx` 完成同样判断：它只是 `./PromptDashboard/index` 的 re-export 壳，已纳入同批删除。
5. CSS module 文件名暂保留。当前目录模块仍引用 `UserManagementPage.module.css`、`RoleManagementPage.module.css`、`OrganizationPage.module.css` 和 `OperationLogPage.module.css`，这些是样式依赖而非页面入口。

**Done when**:

- 每个 System 页面只有一个 canonical import path。
- `rg -n "import\\('../pages/System/(UserManagementPage|RoleManagementPage|OrganizationPage|OperationLogPage)'|from '../(UserManagementPage|RoleManagementPage|OrganizationPage|OperationLogPage)'" frontend/src/routes frontend/src/hooks frontend/src/pages/System/__tests__` 不再命中迁移壳入口。
- 相关前端路由和页面测试通过。

---

## 候选项 05：统一路由注册标准

**建议级别**: P1
**实施状态**: ✅ 2026-06-03 已完成标准决策与第一处双注册收口
**涉及文件**:

- `AGENTS.md`
- `backend/src/api/v1/__init__.py`
- `backend/src/api/v1/party.py`
- `backend/src/api/v1/authz.py`
- `backend/src/api/v1/system/collection.py`
- `backend/src/main.py`
- `backend/src/core/router_registry.py`

### 问题

AGENTS 要求新 API 使用 `route_registry.register_router()`，但当前 `backend/src/api/v1/__init__.py` 仍以大量 `api_router.include_router(...)` 为主。源报告建议“选主流 include_router 并更新 AGENTS”，这与当前项目规则冲突，不能直接照做。

复核后需要把问题拆成两层：

- 应用级注册边界：`backend/src/main.py` 调用 `register_api_routes()`，再通过 `route_registry.include_all(app, version="v1")` 挂载路由。这一层继续以 `route_registry` 为唯一标准。
- v1 内部聚合布线：`backend/src/api/v1/__init__.py` 中既有大量 `api_router.include_router(...)`，这是历史聚合路由内部实现，不等同于新增 API 的注册标准。

真实代码风险出现在混用边界上：`backend/src/api/v1/system/collection.py` 已在模块内 `route_registry.register_router()` 自注册，同时又被 `api_router.include_router(collection_router, prefix="/collections", ...)` 聚合，导致同一 handler 形成 `/api/v1/collection/*` 与 `/api/v1/collections/collection/*` 两套公共入口。

### 已实施内容

当前决策：

| 层级 | 标准 | 说明 |
|---|---|---|
| 应用级注册 | `route_registry.register_router()` | 新 API 与自注册模块使用此标准；`main.py` 继续通过 registry include all |
| 既有 v1 聚合内部 | `api_router.include_router()` | 保留历史聚合路由内部布线，不在本轮批量迁移 |
| 自注册模块 | 禁止再进入聚合 `include_router()` | 避免同一路由产生双公共入口 |

- `AGENTS.md` 明确上述边界：历史 `include_router()` 仅作为既有 v1 聚合内部布线；已自注册的路由不得再被聚合二次 include。
- `backend/src/api/v1/__init__.py` 保留导入 `party`、`authz`、`collection` 以触发自注册，但移除 `collection_router` 的聚合 include。
- 新增 `backend/tests/unit/api/v1/test_route_registration_standard.py`，锁定 `party`、`authz`、`collection` 这类自注册模块不得再被 `api_router` 二次 include。

### 后续边界

不在本轮把所有历史 `api_router.include_router(...)` 批量迁移到 `route_registry`。如果后续要迁移，应按模块分批处理，并为每批证明旧入口没有残留别名。

**Done when**:

- AGENTS、代码和测试对“新 API 如何注册”只有一个答案：应用级新 API 使用 `route_registry.register_router()`。
- 自注册模块不会再被 `api_router.include_router()` 二次聚合。
- 后续历史聚合路由迁移必须逐模块完成，不做无验证的批量替换。

---

## 候选项 06：浅服务模块逐个排查

**建议级别**: P2  
**实施状态**: ✅ 2026-06-04 已完成源报告点名示例排查，后续按新增候选逐个处理
**涉及文件示例**:

- `backend/src/services/contact/service.py`
- `backend/src/services/collection/service.py`
- `backend/src/services/document/cache.py`
- `backend/src/services/history/history_service.py`
- `backend/src/services/excel/excel_task_service.py`
- `backend/src/services/system_settings/service.py`

### 问题

部分 service 只是把调用转发给 CRUD，模块深度不足。但本仓库的分层规则是硬约束：业务逻辑必须在 `services/`，API 不得绕过 CRUD 直接操作数据库。因此不能采用源报告中“删除 service，让 API 直接调 CRUD”的方案。

### 第一轮排查结论

本轮只处理源报告点名示例和已在本文档列入的浅服务候选，不做批量删除：

| 候选 | 当前判断 | 证据 |
|---|---|---|
| `ContactService` | 合并进 Party | 通用联系人通路已随候选项 01 删除，联系人统一由 `PartyService` 和 `party_contacts` 承载 |
| `CollectionService` | 保留并补测试 | `get_summary_async()` 汇总逾期台账、待催缴、本月催缴与成功率；`create_async()` 做台账存在性校验并补操作人上下文 |
| `ExcelTaskService` | 保留 | `mark_task_failed()` 统一回滚事务、查询任务并写入失败态、进度、完成时间和结果清空 |
| `SystemSettingsService` | 保留 | 审计日志创建和数据库连通性检查从 API 层下沉，DB 检查失败返回 `False` 并记录日志 |
| `HistoryService` | 保留并补测试 | 列表按 `asset_id` 筛选前先校验资产存在性；详情和删除缺失时统一抛出业务 404；删除前先确认记录存在 |
| `document/cache.py` | 不作为浅业务 service 删除 | 当前文件只聚合导出 `PDFCache`、`AsyncDocumentCache`、`CachedExtractor`、`ExtractionCache` 等缓存子模块；真实缓存逻辑在 `cache_sync.py`、`cache_async.py`、`cache_extraction.py` |

已新增服务层业务护栏：

- `test_summary_should_calculate_success_rate`
- `test_create_should_fail_loud_when_ledger_missing`
- `test_create_should_fill_operator_context_before_crud`
- `test_list_should_fail_loud_when_asset_filter_missing`
- `test_list_should_delegate_when_asset_filter_exists`
- `test_detail_should_fail_loud_when_history_missing`
- `test_delete_should_not_remove_missing_history`

### 后续做法

只对每个候选做逐个删除测试：

- 如果 service 所代表的业务概念仍成立，把校验、权限上下文、错误语义、审计或事务边界补进 service，让它成为真正的业务模块。
- 如果 service 所代表的概念不成立，把它合并进已有深模块，例如联系人合并进 `PartyService`。
- 禁止把 API 层改成直接调用 CRUD 作为“瘦身”。

**Done when**:

- 每个被处理 service 要么有清晰业务深度，要么被合并到已有深模块。
- API 仍保持 `api/v1 -> services -> crud -> models`。
- 分层测试同步更新。
- 当前第一轮已覆盖源报告点名示例；后续若继续处理其他 service，需要逐个补业务边界或合并证据。

---

## 候选项 07：只迁移活跃页面的服务器数据获取

**建议级别**: P2  
**实施状态**: ✅ 2026-06-04 活跃 System 页面与冻结可见面已完成复核和护栏
**涉及文件**:

- `frontend/src/pages/PropertyCertificate/PropertyCertificateList.tsx`
- `frontend/src/pages/System/UserManagement/index.tsx`
- `frontend/src/pages/System/RoleManagement/index.tsx`
- `frontend/src/pages/System/Organization/index.tsx`
- `frontend/src/pages/System/OperationLog/index.tsx`

### 问题

`PropertyCertificateList.tsx` 确实用 `useEffect` 请求服务器数据，但 PropertyCertificate 当前属于 Out of Scope 冻结模块，优先级应低于活跃主线。System 管理页中的多个 `useEffect` 主要用于错误 toast，而不是服务器数据获取本身；它们可以整理，但不应和服务器数据迁移混为一类。

### 建议做法

- 活跃页面中，服务器数据统一使用 React Query。
- 冻结模块若仍保留文件，应作为冻结可见面清理或归档的一部分处理，而不是单独做功能性重构。
- 错误 toast 的 `useEffect` 可抽成小 helper，但不作为 P0。

### 已实施内容

- 复核 `UserManagement`、`RoleManagement`、`Organization`、`OperationLog` 四个活跃 System 管理页：列表、统计、组织树、权限列表、组织历史等服务器数据均由各自 `use*Data` hook 通过 React Query 获取。
- 页面入口中的 `useEffect` 保留为错误 toast、本地表单同步或抽屉状态处理，不再按“服务器数据获取违规”处理。
- 新增 `frontend/src/pages/System/__tests__/system-active-pages-data-fetching.test.ts`，静态读取活跃页和 hook 源码，锁定 hook 必须使用 React Query，页面入口不得直接调用对应 list/stat/history 服务方法。
- `PropertyCertificateList.tsx` 暂不迁移。该模块已冻结，本轮不为冻结残留增加功能性改造；当前受保护路由、菜单、面包屑和全局搜索提示均已由测试锁定不暴露产权证入口。若后续要删除文件或恢复用户可见入口，应另行按冻结模块清理或恢复立项处理。

**Done when**:

- 活跃页面没有 `useState + useEffect` 直接拉服务器数据。
- 冻结模块不再出现在用户可见入口、全局搜索、面包屑或路由测试中。

---

## 执行顺序

1. ✅ **Contact / PartyContact 决策与收口**：已完成第一轮，联系人事实来源统一到 Party。
2. ✅ **Capability/RBAC 前端入口收口**：已完成主入口收口，测试面已扩展。
3. ✅ **`system_settings` fail-loud**：已完成，核心路由不再静默缺失。
4. ✅ **System 页面迁移入口收口**：已完成，迁移壳和旧测试入口已删除。
5. ✅ **路由注册标准决策**：已明确应用级 registry 标准，并移除 `collection` 双注册别名。
6. ✅ **浅服务逐个审查**：已完成源报告点名示例排查；后续按业务概念逐个处理，不做批量删除。
7. ✅ **活跃页面 React Query 清理**：活跃 System 管理页已完成复核并补护栏；冻结模块可见面已有路由、菜单、面包屑和搜索提示护栏。

---

## 不建议直接执行的源报告建议

- 不建议“删除 service 后 API 直接调用 CRUD”。这违反当前分层规则。
- 不建议把后端 authz 当作 0 测试覆盖重新立项。应先跑当前覆盖率和测试，再补缺口。
- 不建议按“System 目录有 30 个死文件”做批量删除。当前旧页面多为 re-export 壳，真实工作是入口收口。
- 不建议把已经 `route_registry.register_router()` 自注册的路由改回 `api_router.include_router()`；应用级注册标准已经明确，后续只允许逐模块迁移历史聚合布线。
