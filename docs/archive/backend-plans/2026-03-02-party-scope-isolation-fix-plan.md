# 组织数据权限隔离修复计划（全量排查版）

**文档类型**: 实施计划  
**创建日期**: 2026-03-02  
**作者**: Codex  
**状态**: ✅ 已完成（Party / ContractGroup / Ledger / Collection / History / Asset / Project / Property Certificate / Contact 的主体隔离链路已收口；前端已消费 `X-Authz-Stale` 并刷新权限快照）  
**需求编号**: REQ-AUTH-002  
**里程碑**: M4

---

## 1. 摘要

当前问题的核心是“鉴权放行”和“查询数据范围”在部分集合接口上脱节，导致同角色用户可能看到超出自身 `party` 绑定范围的数据。  
本计划是 `REQ-AUTH-002` 的活跃技术方案，采用以下固定策略：

1. 修复范围：全量排查并修复。  
2. 可见性规则：`owner_scope ∪ manager_scope`（并集可见）。  
3. 失败策略：`Fail-Closed`（范围不可解析时拒绝或返回空集合）。

---

## 2. 已确认根因

1. `party` 列表接口仅做 `require_authz(read, resource_type="party")`，但查询未按用户作用域收敛。  
2. `CRUDParty.get_parties()` 仅按 `party_type/status/search` 过滤，没有作用域条件。  
3. `Party` 模型没有 `party_id` 字段，无法直接复用 `QueryBuilder` 的通用 party filter，必须在 `party` 模块做显式 ID 级过滤。  
4. 结果表现为：ABAC 在集合读取阶段放行后，列表可能返回全量主体。

---

## 3. 目标与验收标准

1. 非管理员用户在所有集合查询中，只能看到其 `owner/manager/headquarters` 可见范围内的数据。  
2. `owner A` 用户无法看到 `owner B` 的主体及关联业务数据（除非同时有对应绑定）。  
3. `headquarters` 仅扩展到 `manager` 视角，不并入 `owner`。  
4. 作用域不可解析时，party-scoped 集合接口返回空集合；仅管理员专属全局资源返回 403，不得放行全量。  
5. 管理员旁路能力保持不变。  
6. 回归测试覆盖并通过，无新增越权路径。

---

## 4. 接口与类型变更（兼容）

1. 对外 API 路径与响应结构不变。  
2. 仅内部服务签名扩展（向后兼容）：  
   - `PartyService.get_parties(...)` 增加 `current_user_id` 与可选 `party_filter`。  
   - `CRUDParty.get_parties(...)` 增加可选 `scoped_party_ids`。  
3. `GET /api/v1/parties` 行为变更为“按用户作用域返回子集”。  
4. 当 `current_user_id` 与显式 `party_filter` 同时存在时，普通用户场景的最终范围**只能收窄、不能放大**：  
   - 最终生效范围 = `resolved_scope ∩ caller_scope`；  
   - 交集为空时按 `Fail-Closed` 返回空集合；  
   - 仅管理员/特权用户允许调用方传入的 `party_filter` 直接生效。  
5. 本计划**不顺手改变 ABAC 语义**；“全局资源”与“仅管理员可见”必须拆分建白名单，不得因为缺少 scope 收敛就直接改成管理员专属。

---

## 5. 实施步骤

## 5.1 优先修复高风险主路径（Party）

1. 在 `api/v1/party.py::list_parties` 将 `current_user.id` 传入 `party_service.get_parties(...)`。  
2. 在 `PartyService` 内统一调用 `resolve_user_party_filter(...)` 解析范围。  
3. 将 `PartyFilter` 归一为 `scoped_party_ids`：  
   - 并集规则：`owner_party_ids ∪ manager_party_ids`。  
   - 若为空且非管理员：Fail-Closed（返回空列表）。  
4. 在 `CRUDParty.get_parties` 追加 `Party.id.in_(scoped_party_ids)` 条件，与现有 `party_type/status/search` 叠加。

## 5.2 全量排查集合端点（同类缺陷）

1. 建立清单：扫描所有 `require_authz(action in read/list, resource_id absent)` 的集合接口。  
2. 逐接口分类并落地：  
   - 已有服务层 `current_user_id -> resolve_user_party_filter -> CRUD party_filter`：保留并补测试。  
   - 仅做鉴权未做查询范围收敛：补 `current_user_id` 链路或补 `authz_ctx` 范围过滤。  
   - 全局资源（确实不应按租户隔离）：仅当需求或既有 ABAC policy 已明确为管理员专属时，才进入“管理员可见”白名单，并写入注释与测试断言。  
3. 对使用 `resource_context` 的集合接口，禁止仅依赖首个 `party_id` hint 作为数据范围依据。

### 5.2.1 当前 inventory（以仓库现状为准）

| 模块 | 代码入口 | 现状 | 本轮动作 |
|------|----------|------|----------|
| Party | `backend/src/api/v1/party.py` / `backend/src/services/party/service.py` | 主路径已修复为按 `scoped_party_ids` 收敛 | 补路由层 + 服务层契约测试，锁定“显式 filter 只能收窄” |
| Asset | `backend/src/services/asset/asset_service.py` | 已接入 `resolve_user_party_filter` | 补 A/B 交叉主体可见性回归 |
| Project | `backend/src/services/project/service.py` | 已接入 `resolve_user_party_filter` | 补 A/B 交叉主体可见性回归 |
| Property Certificate | `backend/src/services/property_certificate/service.py` | 已接入 `resolve_user_party_filter`，真实 A/B 可见性集成测试已落地 | 本轮该域排查完成 |
| Collection | `backend/src/services/collection/service.py` | 已补 `current_user_id -> resolve_user_party_filter -> ContractGroup.owner/operator` 收敛，真实 A/B 可见性集成测试已落地 | 本轮该域排查完成 |
| PDF Import | `backend/src/services/document/pdf_import_service.py` | 主服务已接入 `resolve_user_party_filter`；当前公开 `/sessions` 端点仍为占位空响应，未走真实会话查询链路 | 标记为占位接口，待会话列表真正落库查询时再重新进入 inventory |
| Custom Field | `backend/src/services/custom_field/service.py` | 已确认应为全局配置资源；不按主体隔离 | 从主体收敛 inventory 移出，纳入全局资源白名单并补测试锁定 |
| RBAC | `backend/src/services/permission/rbac_service.py` | 混合域：`Role` 带 `party_id`，但 `Permission` / `PermissionGrant` / 权限统计本质是全局权限元数据 | 将 `Role` 继续视为主体资源；将 `Permission` / `PermissionGrant` / 权限统计列入全局资源白名单并补测试锁定 |
| Contracts / Rent Contracts | `backend/src/api/v1/contracts/` / `backend/src/api/v1/rent_contracts/` / `backend/src/services/contract/` / `backend/src/services/rent_contract/` | Contracts 域两条高风险集合读接口与 3 条关键资源级读口已完成作用域收敛修复，真实 A/B 跨主体与资源级集成测试已落地；`rent_contracts` 仅剩 `__pycache__` 产物 | Contracts 域本轮排查完成；`rent_contracts` 暂按非活跃路由处理 |

### 5.2.1.1 Contracts 域详细 inventory（2026-03-14 复核）

> 依据：当前活跃路由仅注册了 `.contracts` 下的 `contract_groups_router` / `ledger_router`，未注册 `rent_contracts` 路由；见 `backend/src/api/v1/__init__.py`。

| 路由 | 代码证据 | 当前现状 | 判定 | 本轮动作 |
|------|----------|----------|------|----------|
| `GET /contract-groups` | `backend/src/api/v1/contracts/contract_groups.py`（`list_contract_groups`）→ `backend/src/services/contract/contract_group_service.py`（`list_groups`）→ `backend/src/crud/contract_group.py`（`list_by_filters`） | 已补 `current_user_id -> resolve_user_party_filter -> owner/operator 条件收敛`，Fail-Closed 空 scope 直接返回空列表；已有路由/服务/CRUD 单测与真实 A/B 集成测试覆盖 | **主修复 + 跨主体验证已完成** | 后续仅补资源级回归 |
| `GET /ledger/entries` | `backend/src/api/v1/contracts/ledger.py`（`get_ledger_entries`）→ `backend/src/services/contract/ledger_service_v2.py`（`query_ledger_entries`）→ `backend/src/crud/contract_group.py`（`query_ledger_entries`） | 已补 `current_user_id -> resolve_user_party_filter -> ContractGroup.owner/operator 条件收敛`，Fail-Closed 空 scope 直接返回空页；已有路由/服务/CRUD 单测与真实 A/B 集成测试覆盖 | **主修复 + 跨主体验证已完成** | 后续仅补资源级回归 |
| `GET /contract-groups/{group_id}/contracts` | `backend/src/api/v1/contracts/contract_groups.py`（`list_contracts_in_group`） | 已补 `current_user_id -> scoped group existence check`，不再仅依赖 `resource_id` path hint；真实资源级集成测试已覆盖 | **资源级回归已完成** | 无 |
| `GET /contracts/{contract_id}/rent-terms` | `backend/src/api/v1/contracts/contract_groups.py`（`list_contract_rent_terms`） | 已补 `current_user_id -> scoped contract existence check`；真实资源级集成测试已覆盖 | **资源级回归已完成** | 无 |
| `GET /contracts/{contract_id}/ledger` | `backend/src/api/v1/contracts/contract_groups.py`（`get_contract_ledger`） | 已补 `current_user_id -> scoped contract existence check`；真实资源级集成测试已覆盖 | **资源级回归已完成** | 无 |

### 5.2.1.2 `rent_contracts` 目录处置结论

1. 截至 2026-03-14，`backend/src/api/v1/rent_contracts/` 与 `backend/src/services/rent_contract/` 仅剩 `__pycache__` 文件，未见可维护的 `.py` 源文件。  
2. 当前 API 聚合入口 `backend/src/api/v1/__init__.py` 仅注册 `.contracts` 下的路由，未注册 `rent_contracts` 路由。  
3. 因此本计划将 `rent_contracts` 视为**历史缓存产物而非活跃接口面**；本轮不把它计入“全量排查完成”证明。若后续恢复源码或重新注册路由，必须重新进入 inventory。

### 5.2.2 全局资源白名单原则

1. “未接入 scope 收敛” ≠ “管理员可见”。  
2. 只有需求文档或既有 ABAC policy 明确声明全局可见/管理员专属的资源，才允许进入白名单。  
3. 白名单项必须记录：资源类型、原因、ABAC 依据、测试断言。  
4. 白名单评审完成前，不修改该资源的授权语义，只补排查记录与守卫测试。
5. `custom_field`：按本轮需求决议视为**全局配置资源**，不再纳入主体范围收敛；读写继续受 `resource_type="custom_field"` 权限控制。
6. `rbac.permission` / `rbac.permission_grant` / 权限统计：按本轮复核视为**全局权限元数据**，不纳入主体范围收敛；`rbac.role` 仍保留 `party_id` 作用域模型。
7. `excel_config`：按本轮复核视为**全局 Excel 配置资源**，不再伪造 unscoped party context；继续受 `resource_type="excel_config"` 权限控制。
8. `system.tasks`：任务本体按**当前用户任务访问**隔离（`user_id` + admin 旁路），不属于 Party-scope 资源；其内嵌 `excel_config` 子路由按全局配置资源处理。
9. `system.notifications`：通知资源按**当前用户通知访问**隔离，不属于 Party-scope 资源；批量已读与手动触发任务不再伪造 unscoped party context。
10. `system.operation_logs`：操作日志按**全局审计资源**处理，不属于 Party-scope 资源；清理/导出等管理操作继续受 `resource_type="operation_log"` 与管理员约束控制。
11. `auth.users`：用户列表/统计为**管理员全局视图**；单用户详情/更新存在“本人旁路 + ABAC 资源级校验”双轨模型，不属于 Party-scope 资源。
12. `auth.sessions`：会话管理为**当前用户自助资源**，不接入通用 ABAC；只允许查询和撤销自己的会话。
13. `auth.organization`：组织列表/树/搜索为**全局共享组织元数据读口**；创建/更新/删除/移动为组织管理动作，批量操作需逐组织权限校验，不属于 Party-scope 资源。
14. `auth.data_policies` / `auth.admin`：角色数据策略包配置与系统管理重置操作均为**全局策略/系统管理资源**，按 `require_admin` 或管理员路由控制，不属于 Party-scope 资源。
15. `system.system_monitoring`：系统/数据库监控为**全局监控资源**，读写继续受 `resource_type="system_monitoring"` 与管理员约束控制，不再伪造 unscoped party context。
16. `system.error_recovery`：错误恢复策略、熔断器、历史清理为**全局运维资源**，继续受 `resource_type="error_recovery"` 控制，不再伪造 unscoped party context。
17. `system.system_settings`：系统设置/备份/恢复/安全事件为**全局系统配置资源**，继续受 `resource_type="system_settings"` 与管理员约束控制，不再伪造 unscoped party context。
18. `system.dictionaries`：统一字典管理为**全局配置资源**，继续受 `resource_type="dictionary"` 控制；当前活跃入口为 `system/dictionaries.py`，旧 `system_dictionaries.py` 未注册为活跃路由。
19. `system.enum_field`：枚举字段类型/值/用途/历史为**全局配置资源**，继续受 `resource_type="enum_field"` 控制，不再伪造 unscoped party context。

### 5.2.3 最终分类矩阵（最终）

| 分类 | 已确认资源 | 访问模型 | 当前状态 |
|------|------------|----------|----------|
| Party-scope | `party`、`contract_group`、`contract ledger`、`collection`、`history`、`asset`、`project`、`property_certificate`、`contact` | `current_user_id -> resolve_user_party_filter -> 查询层 owner/manager/party 收敛`，或对父实体/资源级读取做可信 scope 解析；异常时 Fail-Closed | 已完成主链路修复，且已有单测/真实 A/B 集成证据 |
| 用户级隔离 | `system.tasks`、`system.notifications`、`auth.sessions` | 基于 `user_id`/当前用户访问控制，管理员旁路 | 已完成口径收口，不纳入 Party-scope 修复 |
| 全局白名单 | `custom_field`、`excel_config`、`rbac.permission`、`rbac.permission_grant`、权限统计、`system.operation_logs`、`auth.organization`（读口）、`system.system_monitoring`、`system.error_recovery`、`system.system_settings`、`system.dictionaries`、`system.enum_field`、`llm_prompts`、`system.backup` | 全局配置/全局权限元数据/全局审计/全局组织元数据/全局运维/全局 AI 模板资源；不做主体收敛，仅受自身 `resource_type` 权限与管理员约束控制 | 已完成口径收口与分层测试锁定 |
| 占位/非活跃 | `pdf_import /sessions`、`rent_contracts` 目录 | 占位空响应或未注册活跃路由，不作为本轮“真实查询收敛”对象 | 待真实实现落地后重新进入 inventory |

### 5.2.4 收口结论

1. 本计划对应的“主体隔离缺陷”已全部收口，可以归档。  
2. `REQ-AUTH-002` 仍保留 `🚧` 的唯一剩余点，不再是 Party-scope 泄露，而是“全局视角机制/默认视角失效后的重新选择交互”产品链路；该项转由 `docs/plans/2026-03-15-m1-closure-acceptance-plan.md` 继续跟踪。  
3. 因此本计划不再作为 `REQ-AUTH-002` 的活跃方案保留在 `docs/plans/`。

## 5.3 防回归门禁

1. 新增“集合接口作用域收敛”守卫测试（路由层/服务层契约测试）。  
2. 对 `party` 模块新增强制测试：非管理员查询不得出现未绑定 party。  
3. 对关键业务模块（资产/合同/项目/产权证）增加交叉主体回归样例，确保 `A` 看不到 `B`。

---

## 6. 测试场景（必须新增/补齐）

1. `party list`：用户仅绑定 `owner=A`，返回仅包含 `A`，不含 `B`。  
2. `party list`：用户 `manager=A` + `headquarters=H`，返回 `A` 与 `H` 子孙 manager 范围，不含无关 `owner` 范围。  
3. `party list`：无绑定且无 legacy 映射，返回空集合（Fail-Closed）。  
4. `party list`：管理员账号仍可见全量（旁路不回归）。  
5. `party list`：普通用户同时传入 `current_user_id + party_filter` 时，显式 `party_filter` 只能缩小结果，不能扩大为未绑定主体。  
6. 资产/合同/项目至少各一条“交叉主体隔离”集成测试：`A` 用户不能看到 `B` 数据。  
7. party-scoped 集合接口在 scope 解析异常时，固定返回 `200 + 空集合`，不得返回全量。  
8. 仅管理员专属的全局资源接口在普通用户访问时固定返回 `403`，不得回退为全量可见。

---

## 7. 验证与发布

1. 先跑新增单元测试与目标集成测试（party + 资产/合同/项目关键链路）：`cd backend && uv run pytest --no-cov tests/unit/services/test_party_service.py tests/unit/api/v1/test_party_api.py tests/integration/api/test_assets_visibility_real.py tests/integration/api/test_project_visibility_real.py -q -x`。  
2. 再跑后端非慢测回归：`cd backend && uv run pytest --no-cov -m "not slow" -q -x`。  
3. 检查无 scope 泄露告警、无新增 5xx。  
4. 同步更新 `docs/requirements-specification.md`、`docs/plans/README.md` 与 `CHANGELOG.md`，保持唯一需求真相链路闭环。

---

## 8. 假设与默认值

1. 继续遵循现有模型：`headquarters` 仅并入 `manager_party_ids`。  
2. 可见范围规则固定为并集，不引入 owner/manager 视角切换参数。  
3. 不新增前端参数；后端自动按用户作用域收敛。  
4. 管理员旁路保留；普通用户严格 Fail-Closed。  
5. 本次不改 ABAC policy 语义，优先修复“查询层未收敛”缺陷；若排查中发现策略表达错误，再做单独补丁。
