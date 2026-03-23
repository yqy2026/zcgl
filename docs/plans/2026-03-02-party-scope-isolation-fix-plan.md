# 组织数据权限隔离修复计划（全量排查版）

**文档类型**: 实施计划  
**创建日期**: 2026-03-02  
**作者**: Codex  
**状态**: 🔄 进行中（§5.1 已完成，§5.2 评估落地，§6 补测完成，§5.2 资产/合同/项目跨主体集成测试待补）

---

## 1. 摘要

当前问题的核心是“鉴权放行”和“查询数据范围”在部分集合接口上脱节，导致同角色用户可能看到超出自身 `party` 绑定范围的数据。  
本计划采用以下固定策略：

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
4. 作用域不可解析时，接口返回空集合或 403，不得放行全量。  
5. 管理员旁路能力保持不变。  
6. 回归测试覆盖并通过，无新增越权路径。

---

## 4. 接口与类型变更（兼容）

1. 对外 API 路径与响应结构不变。  
2. 仅内部服务签名扩展（向后兼容）：  
   - `PartyService.get_parties(...)` 增加 `current_user_id` 与可选 `party_filter`。  
   - `CRUDParty.get_parties(...)` 增加可选 `scoped_party_ids`。  
3. `GET /api/v1/parties` 行为变更为“按用户作用域返回子集”。

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
   - 全局资源（不应按租户隔离）：明确仅管理员可见，写入注释与测试断言。  
3. 对使用 `resource_context` 的集合接口，禁止仅依赖首个 `party_id` hint 作为数据范围依据。

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
5. 资产/合同/项目至少各一条“交叉主体隔离”集成测试：`A` 用户不能看到 `B` 数据。  
6. 集合接口在 scope 解析异常时不得返回全量（403 或空集合，按接口语义固定）。

---

## 7. 验证与发布

1. 先跑新增单元测试与目标集成测试（party + 资产/合同/项目关键链路）。  
2. 再跑后端非慢测回归：`pytest --no-cov -m "not slow" -q -x`。  
3. 检查无 scope 泄露告警、无新增 5xx。  
4. 更新 `CHANGELOG.md` 记录“组织/主体数据权限隔离修复”与测试证据。

---

## 8. 假设与默认值

1. 继续遵循现有模型：`headquarters` 仅并入 `manager_party_ids`。  
2. 可见范围规则固定为并集，不引入 owner/manager 视角切换参数。  
3. 不新增前端参数；后端自动按用户作用域收敛。  
4. 管理员旁路保留；普通用户严格 Fail-Closed。  
5. 本次不改 ABAC policy 语义，优先修复“查询层未收敛”缺陷；若排查中发现策略表达错误，再做单独补丁。

