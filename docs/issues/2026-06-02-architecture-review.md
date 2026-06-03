# 架构技术债复核报告

**状态**: 🔄 分批实施中  
**源报告日期**: 2026-06-02  
**复核日期**: 2026-06-03  
**来源**: `C:\Users\ygz\AppData\Local\Temp\opencode\architecture-review-20260602-082816.html`

---

## 结论

源 HTML 报告提出 8 个架构候选项。复核后本文档将其合并为 7 个可执行方向：原候选 04（路由注册统一）和原候选 08（`system_settings` 静默加载）拆成“先 fail loud、再决策路由注册标准”两类问题；原候选 06（authz 覆盖率）并入前端 Capability/RBAC 测试面收口。核心方向成立：当前代码仍存在重复实现、迁移收口不彻底、可测试接口不集中等问题。但复核当前代码后，有两处原判断已经过时，不能原样执行：

1. `backend/src/services/authz/*` 已有后端单元测试，不再是原报告所说的 "0% 覆盖率"。当前风险应改为：前端 `capabilityEvaluator` 测试面过窄，且 `organization-scope-isolation.spec.ts` 仍有多处 `test.skip`。
2. `frontend/src/pages/System/*Page.tsx` 中部分旧页面已经变成 42-44 字节的 re-export 壳，不再是旧单体大页面。当前风险应改为：路由、预加载和测试入口仍指向迁移壳，未直接收口到目录模块。

2026-06-03 已完成候选项 01 第一轮收口：通用 `Contact(entity_type, entity_id)`、`/contacts` API、前端 `contactService` 和 `contact` 权限资源已退役；联系人统一从 `PartyContact`、`/parties/{party_id}/contacts` 和 `partyService` 维护。剩余候选项仍按下表排队。

建议第一轮继续做小而确定的收口：

| 优先级 | 候选项 | 当前判断 | 原因 |
|---|---|---|---|
| 已完成 | 合并 `Contact` 与 `PartyContact` 双通路 | 已实施第一轮收口 | 统一到 ADR-0001 的 `party_contacts`；通用 `/contacts` 已删除 |
| P0 | 收口前端 Capability/RBAC 入口 | 强建议 | 生产代码主要使用 `useCapabilities`，但 `AuthContext` 和 `AuthService` 仍保留过渡期 API |
| P1 | `system_settings` 路由 fail loud | 强建议，小改动 | 0-to-1 阶段不应静默吞掉导入失败 |
| P1 | System 页面迁移入口收口 | 建议 | 当前不是大规模死文件，而是路由/预加载/测试入口仍经由 wrapper |
| P1 | 路由注册标准冲突处理 | 需先决策 | AGENTS 要求新 API 用 `route_registry`，当前 `include_router` 仍是主流，不能直接反向修改标准 |
| P2 | 活跃页面的 `useQuery` 迁移 | 有选择推进 | `PropertyCertificate` 已冻结，`ProjectDetailPage` 的相关 `useEffect` 不是服务器取数 |
| P2 | 浅服务模块排查 | 仅能逐个审查 | API 直接调 CRUD 违反本仓库分层规则，不能照源报告执行 |

---

## 复核证据摘要

### 仍成立的问题

- 前端权限入口仍有三套公共表面：
  - `frontend/src/hooks/useCapabilities.ts`
  - `frontend/src/contexts/AuthContext.tsx` 中 deprecated `hasPermission` / `hasAnyPermission`
  - `frontend/src/services/authService.ts` 中 static `hasPermission` / `hasAnyPermission`
- `backend/src/api/v1/__init__.py` 仍通过 `_load_optional_router()` 静默加载 `system_settings_router`，导入失败时只记录日志并继续启动。
- `frontend/src/pages/PropertyCertificate/PropertyCertificateList.tsx` 仍用 `useState + useEffect` 请求服务器数据。

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
**涉及文件**:

- `frontend/src/hooks/useCapabilities.ts`
- `frontend/src/utils/authz/capabilityEvaluator.ts`
- `frontend/src/contexts/AuthContext.tsx`
- `frontend/src/services/authService.ts`
- `frontend/src/utils/authz/__tests__/capabilityEvaluator.test.ts`
- `frontend/tests/e2e/auth/organization-scope-isolation.spec.ts`

### 问题

生产代码已经主要通过 `useCapabilities()` 做权限判断，但过渡期 API 仍留在公共类型中：

- `AuthContext.hasPermission()`
- `AuthContext.hasAnyPermission()`
- `AuthService.hasPermission()`
- `AuthService.hasAnyPermission()`

当前复核未发现这些 deprecated 方法在非测试生产代码中被调用。它们继续存在会让后续调用者误选旧入口，并让权限回归测试分散在多个表面。

### 建议做法

1. 扩展 `capabilityEvaluator.test.ts`，至少覆盖：
   - admin bypass
   - action 命中 / 缺失
   - perspective 命中 / 缺失
   - owner/manager party scope 命中 / 拒绝
   - resource capability 缺失
2. 删除 `AuthContext` 类型和实现中的 deprecated 方法。
3. 删除 `AuthService` static 权限判断方法。
4. 更新测试 mock，避免继续把 deprecated 方法作为默认上下文字段。
5. 逐步恢复 `organization-scope-isolation.spec.ts` 中能够稳定断言的 skip 场景；不能恢复的要写明外部依赖或冻结原因。

**Done when**:

- 前端生产权限判断只有 `useCapabilities()` / `capabilityEvaluator` 一个入口。
- `capabilityEvaluator.test.ts` 不再只有 2 条窄用例。
- E2E skip 数量下降，剩余 skip 有明确冻结或环境原因。

---

## 候选项 03：让 `system_settings` 路由失败时显式暴露

**建议级别**: P1  
**涉及文件**:

- `backend/src/api/v1/__init__.py`
- `backend/src/api/v1/system/system_settings.py`
- `backend/tests/unit/api/v1/test_system_settings_layering.py`

### 问题

`system_settings_router` 通过 `_load_optional_router()` 加载。导入失败时，应用继续启动，只是 `/system` 下相关路由缺失。项目处于 0-to-1 阶段，AGENTS 明确要求不要做兼容隐藏，应该充分暴露问题。

### 建议做法

- 将 `system_settings_router` 改为直接导入。
- 如果确实存在可选模块需求，使用显式 feature flag，而不是吞掉 `ImportError`。
- 保留 `pdf_batch_router` 是否可选需要另行判断，不和本项混在一个改动里。

**Done when**:

- `system_settings` 导入失败会阻断启动或测试导入。
- `backend/src/api/v1/__init__.py` 不再对核心系统设置路由做静默缺失处理。
- 补充一个路由注册或导入护栏测试。

---

## 候选项 04：System 页面迁移入口收口

**建议级别**: P1  
**涉及文件**:

- `frontend/src/routes/AppRoutes.tsx`
- `frontend/src/hooks/useSmartPreload.tsx`
- `frontend/src/pages/System/UserManagementPage.tsx`
- `frontend/src/pages/System/RoleManagementPage.tsx`
- `frontend/src/pages/System/OrganizationPage.tsx`
- `frontend/src/pages/System/OperationLogPage.tsx`
- `frontend/src/pages/System/*/__tests__`

### 问题

源报告认为新目录树是“未被路由触达的 ghost tree”，但当前代码已经把旧 `*Page.tsx` 收缩为 re-export 壳。真实问题是迁移入口没有最后收口：

- 路由仍 import `../pages/System/UserManagementPage` 等壳文件。
- 预加载仍 import `UserManagementPage` / `RoleManagementPage`。
- 测试仍有部分以旧壳文件命名和导入。

这不是 P0 的大规模删除项，但属于 0-to-1 阶段应清掉的兼容壳。

### 建议做法

1. 将路由和预加载直接切到目录模块，例如 `../pages/System/UserManagement`。
2. 将测试导入同步切到目录模块。
3. 评估 CSS module 的旧命名依赖。当前目录模块仍引用 `UserManagementPage.module.css`、`RoleManagementPage.module.css`、`OrganizationPage.module.css` 和 `OperationLogPage.module.css`，所以不能只删 `*Page.tsx` 壳后就宣称收口完成。
4. 删除 42-44 字节的 re-export 壳文件。
5. 对 `PromptDashboard.tsx` 同样判断是否只是迁移壳；若是，纳入同一小 PR。

**Done when**:

- 每个 System 页面只有一个 canonical import path。
- `rg -n "import\\('../pages/System/(UserManagementPage|RoleManagementPage|OrganizationPage|OperationLogPage)'|from '../(UserManagementPage|RoleManagementPage|OrganizationPage|OperationLogPage)'" frontend/src/routes frontend/src/hooks frontend/src/pages/System/__tests__` 不再命中迁移壳入口。
- 相关前端路由和页面测试通过。

---

## 候选项 05：统一路由注册标准

**建议级别**: P1，但先决策  
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

### 建议做法

先形成一个明确架构决策：

| 选项 | 含义 | 代价 |
|---|---|---|
| 保留 `route_registry` 为新标准 | 后续逐步迁移 `include_router` | 改动面大，但符合 AGENTS |
| 承认 `include_router` 为标准 | 修改 AGENTS 与相关门禁 | 改动小，但推翻现有项目约束 |

在决策前，不建议把 `party.py` / `authz.py` / `collection.py` 单独改回 `include_router`，否则会继续扩大规则冲突。

**Done when**:

- AGENTS、代码和测试对“新 API 如何注册”只有一个答案。
- 如果保留 `route_registry`，新增路由有护栏防止回退到散落注册。
- 如果改用 `include_router`，需要同步修改 AGENTS 和 `main.py` 中 route registry 相关降级逻辑。

---

## 候选项 06：浅服务模块逐个排查

**建议级别**: P2  
**涉及文件示例**:

- `backend/src/services/collection/service.py`
- `backend/src/services/excel/excel_task_service.py`
- `backend/src/services/system_settings/service.py`

### 问题

部分 service 只是把调用转发给 CRUD，模块深度不足。但本仓库的分层规则是硬约束：业务逻辑必须在 `services/`，API 不得绕过 CRUD 直接操作数据库。因此不能采用源报告中“删除 service，让 API 直接调 CRUD”的方案。

### 建议做法

只对每个候选做逐个删除测试：

- 如果 service 所代表的业务概念仍成立，把校验、权限上下文、错误语义、审计或事务边界补进 service，让它成为真正的业务模块。
- 如果 service 所代表的概念不成立，把它合并进已有深模块，例如联系人合并进 `PartyService`。
- 禁止把 API 层改成直接调用 CRUD 作为“瘦身”。

**Done when**:

- 每个被处理 service 要么有清晰业务深度，要么被合并到已有深模块。
- API 仍保持 `api/v1 -> services -> crud -> models`。
- 分层测试同步更新。

---

## 候选项 07：只迁移活跃页面的服务器数据获取

**建议级别**: P2  
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

**Done when**:

- 活跃页面没有 `useState + useEffect` 直接拉服务器数据。
- 冻结模块不再出现在用户可见入口、全局搜索、面包屑或路由测试中。

---

## 建议执行顺序

1. **Contact / PartyContact 决策与收口**：先解决事实来源重复问题，避免后续 Party 相关重构继续被双通路拖住。
2. **Capability/RBAC 前端入口收口**：测试面先扩展，再删除 deprecated API，减少权限判断分散。
3. **`system_settings` fail-loud**：小改动，直接对齐 0-to-1 阶段规则。
4. **System 页面迁移入口收口**：删除迁移壳和旧测试入口。
5. **路由注册标准决策**：在 AGENTS 与代码之间选一个方向，再做迁移。
6. **活跃页面 React Query 清理**：只处理活跃页面，不给冻结模块增加功能性改动。
7. **浅服务逐个审查**：按业务概念逐个处理，不做批量删除。

---

## 不建议直接执行的源报告建议

- 不建议“删除 service 后 API 直接调用 CRUD”。这违反当前分层规则。
- 不建议把后端 authz 当作 0 测试覆盖重新立项。应先跑当前覆盖率和测试，再补缺口。
- 不建议按“System 目录有 30 个死文件”做批量删除。当前旧页面多为 re-export 壳，真实工作是入口收口。
- 不建议在未修改 AGENTS 或形成 ADR 前，把 `route_registry` 的少量调用直接改成 `include_router`。
