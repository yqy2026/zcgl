# Phase 1 实施计划：DDL + ORM 模型 + ABAC 引擎骨架

**文档类型**: 实施计划  
**创建日期**: 2026-02-18  
**上游依赖**: [Party-Role 架构设计 v3.7](./2026-02-16-party-role-architecture-design.md)  
**阶段定位**: Party-Role 架构的地基层实施。**纯新增**，不改动任何现有业务代码，零破坏性。

---

## 1. 范围界定

| 包含 | 不包含（Phase 2+） |
|---|---|
| Party/Hierarchy/Contact/RoleDef/RoleBinding 新表 | 业务表字段替换（asset/contract/project） |
| UserPartyBinding 新表 | TenantFilter → PartyFilter |
| project_assets / certificate_party_relations 新表 | 现有 organization/ownership 模型删除 |
| ABAC 引擎核心（policies/rules/role_policies）| 前端 capabilities 集成 |
| `/authz/check` + `/auth/me/capabilities` 端点骨架 | 迁移 Runbook 脚本（数据回填） |
| 防环触发器 | PermissionGrant/ResourcePermission 废弃标记 |
| ORM 模型 + CRUD + Schema + 单元测试 | 完整 E2E 集成测试 |

---

## 2. 变更清单

### 2.1 ORM 模型（`backend/src/models/`）

> 项目约定：models/ 为扁平文件结构，每个模型文件导出到 `__init__.py`；使用 `Mapped[]` 风格（SQLAlchemy 2.0）。

#### [NEW] `models/party.py`

| 类名 | 表名 | 关键字段 | 约束 |
|---|---|---|---|
| `PartyType` | — | Enum: `organization`, `legal_entity` | Python StrEnum |
| `Party` | `parties` | `id` UUID PK, `party_type`, `name`, `code`, `external_ref`, `status`, `metadata` JSONB | `UNIQUE(party_type, code)` |
| `PartyHierarchy` | `party_hierarchy` | `id`, `parent_party_id` FK, `child_party_id` FK | `UNIQUE(parent, child)`, `CHECK(parent ≠ child)` |
| `PartyContact` | `party_contacts` | `id`, `party_id` FK, `contact_type`, `value`, `is_primary` | partial unique: `(party_id, contact_type) WHERE is_primary` |

#### [NEW] `models/party_role.py`

| 类名 | 表名 | 关键字段 | 约束 |
|---|---|---|---|
| `PartyRoleDef` | `party_role_defs` | `id`, `role_code` ENUM, `label`, `scope_type` | `UNIQUE(role_code)` |
| `PartyRoleBinding` | `party_role_bindings` | `id`, `party_id` FK, `role_def_id` FK, `scope_type`, `scope_id`, `valid_from/to` | 排斥约束（同主体同角色同资源不重叠），`scope_type` 一致性 |

#### [NEW] `models/user_party_binding.py`

| 类名 | 表名 | 关键字段 | 约束 |
|---|---|---|---|
| `RelationType` | — | Enum: `owner`, `manager`, `headquarters` | Python StrEnum |
| `UserPartyBinding` | `user_party_bindings` | `id`, `user_id` FK, `party_id` FK, `relation_type`, `is_primary`, `valid_from/to` | partial unique: `(user_id, relation_type) WHERE is_primary`；排斥约束 |

#### [NEW] `models/project_asset.py`

| 类名 | 表名 | 关键字段 |
|---|---|---|
| `ProjectAsset` | `project_assets` | `id`, `project_id` FK → `projects.id`, `asset_id` FK → `assets.id`, `valid_from/to`, `bind_reason`, `unbind_reason` |

#### [NEW] `models/certificate_party_relation.py`

| 类名 | 表名 | 关键字段 |
|---|---|---|
| `CertificatePartyRelation` | `certificate_party_relations` | `id`, `certificate_id` FK, `party_id` FK, `relation_type`, `share_ratio`, `is_primary`, `valid_from/to` |

#### [NEW] `models/abac.py`

| 类名 | 表名 | 关键字段 |
|---|---|---|
| `ABACPolicy` | `abac_policies` | `id`, `name`, `effect` ENUM(allow/deny), `priority`, `enabled` |
| `ABACPolicyRule` | `abac_policy_rules` | `id`, `policy_id` FK, `resource_type`, `action` ENUM(单值：create\|read\|list\|update\|delete\|export), `condition_expr` JSONB, `field_mask` |
| `ABACRolePolicy` | `abac_role_policies` | `id`, `role_id` FK → `roles.id`, `policy_id` FK, `priority` |

#### [MODIFY] `models/__init__.py`

新增所有新模型的 import 和 `__all__` 注册（Party, PartyHierarchy, PartyContact, PartyType, PartyRoleDef, PartyRoleBinding, RelationType, UserPartyBinding, ProjectAsset, CertificatePartyRelation, ABACPolicy, ABACPolicyRule, ABACRolePolicy）。

---

### 2.2 Alembic 迁移

> 约定：revision ID 格式 `YYYYMMDD_description`；`down_revision` 链到当前 HEAD（`20260211_add_organization_scope_columns`）。

#### [NEW] `alembic/versions/20260218_create_party_tables.py`

创建 Party 系表：
- `parties` + `UNIQUE(party_type, code)` + 索引
- `party_hierarchy` + 约束 + 防环触发器（PL/pgSQL `BEFORE INSERT OR UPDATE` 递归检测）
- `party_contacts` + partial unique 索引
- `party_role_defs` + seed 数据（`owner` / `manager` / `headquarters`）
- `party_role_bindings` + 排斥约束（需 `btree_gist` 扩展）
- `user_party_bindings` + partial unique + 排斥约束

> **前置**：迁移开头 `op.execute('CREATE EXTENSION IF NOT EXISTS btree_gist')` — 排斥约束依赖。

#### [NEW] `alembic/versions/20260218_create_abac_and_relation_tables.py`

创建 ABAC + 关系表：
- `project_assets`
- `certificate_party_relations`
- `abac_policies`
- `abac_policy_rules`
- `abac_role_policies`

---

### 2.3 CRUD 数据访问层（`backend/src/crud/`）

> 项目约定：纯数据访问，不含业务逻辑；Service 层通过 CRUD 层访问 DB。

#### [NEW] `crud/party.py`

| 方法 | 说明 |
|---|---|
| `create_party()` | 创建 Party |
| `get_party()` / `get_parties()` | 单个/列表查询 |
| `update_party()` | 更新 Party |
| `delete_party()` | 删除 Party |
| `add_hierarchy()` / `remove_hierarchy()` | 层级关系增删 |
| `get_descendants()` | 递归获取子孙节点（CTE 查询） |
| `create_contact()` / `update_contact()` / `delete_contact()` | 联系方式 CRUD |
| `create_user_party_binding()` / `get_user_bindings()` | 用户-Party 绑定 |

#### [NEW] `crud/authz.py`

| 方法 | 说明 |
|---|---|
| `get_policies_by_role_ids()` | 根据角色 ID 集合加载关联策略 + 规则 |
| `create_policy()` / `update_policy()` | 策略 CRUD |
| `create_policy_rule()` | 规则 CRUD |
| `bind_role_policy()` / `unbind_role_policy()` | 角色-策略绑定 |

#### [NEW] `crud/project_asset.py`

| 方法 | 说明 |
|---|---|
| `bind_asset()` / `unbind_asset()` | 项目-资产绑定/解绑 |
| `get_project_assets()` / `get_asset_projects()` | 双向查询 |

---

### 2.4 Pydantic Schema（`backend/src/schemas/`）

#### [NEW] `schemas/party.py`

Party 相关 Schema：`PartyCreate`, `PartyUpdate`, `PartyResponse`, `PartyHierarchyResponse`, `PartyContactCreate`, `UserPartyBindingCreate`, `UserPartyBindingResponse` 等。

#### [NEW] `schemas/authz.py`

ABAC 鉴权 Schema：
- `AuthzCheckRequest`（`resource_type`, `resource_id`, `action`）
- `AuthzCheckResponse`（`allowed`, `reason_code`）
- `CapabilityItem`, `CapabilitiesResponse`（对齐设计文档 §5.1 最小 Schema）

---

### 2.5 Service 服务层（`backend/src/services/`）

> 项目约定：业务逻辑在 Service 层；每个领域一个包（`services/{domain}/`）。

#### [NEW] `services/authz/`

| 文件 | 职责 |
|---|---|
| `__init__.py` | 包导出 |
| `engine.py` | JSONLogic 判定核心：`evaluate(subject, resource, action, policies) → bool` |
| `context_builder.py` | 构建判定上下文：从 `user_party_bindings` 加载 owner/manager/headquarters 分桶 + headquarters 子树展开（仅并入 `manager_party_ids`） |
| `service.py` | 对外服务层：`check_access()`, `get_capabilities()`, 策略加载 + 缓存 |

#### [NEW] `services/party/`

| 文件 | 职责 |
|---|---|
| `__init__.py` | 包导出 |
| `service.py` | Party CRUD 编排 + hierarchy 防环校验（应用层 + 触发器双重保证） |

---

### 2.6 API 端点（`backend/src/api/v1/`）

#### [NEW] `api/v1/authz.py`

| 端点 | 方法 | 说明 |
|---|---|---|
| `POST /api/v1/authz/check` | POST | ABAC 判定（设计文档 §5.1 第 7 项） |
| `GET /api/v1/auth/me/capabilities` | GET | 能力清单（设计文档 §5.1 第 9 项） |

#### [NEW] `api/v1/party.py`

| 端点 | 方法 | 说明 |
|---|---|---|
| `/api/v1/parties` | GET/POST | Party 列表/创建 |
| `/api/v1/parties/{id}` | GET/PUT/DELETE | Party 详情/更新/删除 |
| `/api/v1/parties/{id}/hierarchy` | GET/POST/DELETE | 层级关系管理 |
| `/api/v1/parties/{id}/contacts` | GET/POST | 联系方式管理 |

---

### 2.7 注册修改

#### [MODIFY] `alembic/env.py`

L23-36 模型导入块新增 6 个模块：`party`, `party_role`, `user_party_binding`, `project_asset`, `certificate_party_relation`, `abac`。

#### [MODIFY] `api/v1/` 路由注册

通过 `route_registry.register_router()` 注册 `authz` 和 `party` 路由。

---

## 3. 验证计划

### 3.1 自动化测试

| 测试文件 | 覆盖范围 |
|---|---|
| `tests/unit/models/test_party.py` | Party/PartyHierarchy/PartyContact 模型实例化、约束、枚举值 |
| `tests/unit/models/test_party_role.py` | PartyRoleDef/PartyRoleBinding, scope_type 一致性 |
| `tests/unit/models/test_user_party_binding.py` | UserPartyBinding, RelationType 枚举 |
| `tests/unit/models/test_abac.py` | ABACPolicy/ABACPolicyRule/ABACRolePolicy |
| `tests/unit/services/test_authz_engine.py` | JSONLogic evaluate(): owner/manager 路径命中、deny-by-default、field_mask |

```bash
# 新增测试
cd backend && pytest tests/unit/models/test_party.py tests/unit/models/test_abac.py tests/unit/services/test_authz_engine.py -v

# 迁移验证（升级/降级/再升级）
cd backend && alembic upgrade head && alembic downgrade -1 && alembic upgrade head

# 现有测试回归
cd backend && pytest -m "not slow" --timeout=60
```

### 3.2 手动验证

1. **表结构检查**：PostgreSQL `\dt` 确认新表 + `\d parties` 确认约束/索引
2. **防环触发器**：手动尝试插入环形层级数据 → 触发器阻止
3. **btree_gist**：确认排斥约束生效（同主体同角色同资源重叠时间段拒绝 INSERT）

---

## 4. 文件总览

| 类型 | 新增 | 修改 |
|---|---|---|
| ORM 模型 | 6 | 1（`__init__.py`） |
| Alembic 迁移 | 2 | 1（`env.py`） |
| CRUD | 3 | — |
| Schema | 2 | — |
| Service 包 | 2（共 6 文件） | — |
| API 端点 | 2 | — |
| 单元测试 | 5 | — |
| **合计** | **~22** | **2** |

> 本阶段完成后，所有新表和模型可用，但不影响现有业务流程。Phase 2 将在此基础上做业务表字段替换和 TenantFilter → PartyFilter 迁移。
