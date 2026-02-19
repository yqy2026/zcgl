# Phase 1 实施计划：DDL + ORM 模型 + ABAC 引擎骨架

**文档类型**: 实施计划  
**创建日期**: 2026-02-18  
**最新更新**: 2026-02-19  
**上游依赖**: [Party-Role 架构设计 v3.9](./2026-02-16-party-role-architecture-design.md)  
**阶段定位**: Party-Role 架构的地基层实施。不改业务域模型与旧接口语义，仅新增能力并做最小接线改动（`v1/__init__.py` 导入触发注册、`models/__init__.py` 导出、`env.py` 导入、`pyproject.toml` 依赖）。
**执行状态**: ✅ 已完成（2026-02-19）

---

## 1. 范围界定

| 包含 | 不包含（Phase 2+） |
|---|---|
| Party/Hierarchy/Contact/RoleDef/RoleBinding 新表 | 业务表字段替换（asset/contract/project） |
| UserPartyBinding 新表 | TenantFilter → PartyFilter |
| project_assets / certificate_party_relations 新表 | 现有 organization/ownership 模型删除 |
| ABAC 引擎核心（policies/rules/role_policies）| 前端 capabilities 集成 |
| `/api/v1/authz/check` + `/api/v1/auth/me/capabilities` 端点骨架 | 迁移 Runbook 脚本（数据回填） |
| 防环触发器 | PermissionGrant/ResourcePermission 废弃标记 |
| ORM 模型 + CRUD + Schema + 单元测试 | 完整 E2E 集成测试 |
| 新增依赖 `python-jsonlogic` | — |

---

## 2. 前置依赖（开工前必须完成）

### 2.1 Python 依赖新增

**生产依赖**（`[project.dependencies]`）：

```toml
"python-jsonlogic>=0.1.0",    # JSONLogic 表达式引擎（Python 3.12 兼容）
```

**开发/测试依赖**（`[project.optional-dependencies]` → `dev = [...]`）：

```toml
"pytest-timeout>=2.2.0",      # 测试超时控制
```

> 选型说明：本期采用 `python-jsonlogic`，避免 `json-logic` 在 Python 3.12 运行期兼容性问题。若后续有性能需求，可评估 `jsonlogic-rs`。

### 2.2 PostgreSQL 扩展

排斥约束依赖 `btree_gist`，Alembic 迁移开头自动执行：
```sql
CREATE EXTENSION IF NOT EXISTS btree_gist;
```

---

## 3. 变更清单

### 3.1 ORM 模型（`backend/src/models/`）

> 项目约定：models/ 为扁平文件结构，每个模型文件导出到 `__init__.py`；使用 `Mapped[]` 风格（SQLAlchemy 2.0）。

> [!IMPORTANT]
> **ID 类型约定**（设计文档 §2 L108）：所有 `id` 列的 **物理列类型为 `String`**（`mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))`），与现网 22 张表一致。本文档中 "PK" 均指此实现方式，不使用 PostgreSQL 原生 `UUID` 列类型。FK 列同理为 `String`。

#### [NEW] `models/party.py`

对齐设计文档 §3.1（L117-169）：

| 类名 | 表名 | 字段 | 约束 |
|---|---|---|---|
| `PartyType` | — | Python StrEnum: `organization`, `legal_entity` | — |
| `Party` | `parties` | `id` String PK (uuid4), `party_type`, `name`, `code`, `external_ref`（可选）, `status`, `metadata` JSONB, `created_at`, `updated_at` | `UNIQUE(party_type, code)` |
| `PartyHierarchy` | `party_hierarchy` | `id` String PK (uuid4), `parent_party_id` String FK, `child_party_id` String FK, `created_at`, `updated_at` | `UNIQUE(parent, child)`, `CHECK(parent ≠ child)`, 防环触发器 |
| `PartyContact` | `party_contacts` | `id` String PK (uuid4), `party_id` String FK, `contact_name`, `contact_phone`, `contact_email`, `position`, `is_primary`, `notes`, `created_at`, `updated_at` | `UNIQUE(party_id) WHERE is_primary=true`（partial unique） |

#### [NEW] `models/party_role.py`

对齐设计文档 §3.2（L175-198）：

| 类名 | 表名 | 字段 | 约束 |
|---|---|---|---|
| `PartyRoleDef` | `party_role_defs` | `id` String PK (uuid4), `role_code`（如 OWNER/MANAGER/LESSOR/LESSEE）, `scope_type`（global/asset/contract/project/certificate）, `description` | `UNIQUE(role_code, scope_type)` |
| `PartyRoleBinding` | `party_role_bindings` | `id` String PK (uuid4), `party_id` String FK, `role_def_id` String FK, `scope_type`, `scope_id` String NULL, `valid_from`, `valid_to`, `attributes` JSONB, `created_at`, `updated_at` | 排斥约束（同主体同角色同资源不重叠）；`scope_type` 与 `party_role_defs.scope_type` 一致性；`scope_type='global'` → `scope_id IS NULL` |

#### [NEW] `models/user_party_binding.py`

对齐设计文档 §3.3（L209-226）：

| 类名 | 表名 | 字段 | 约束 |
|---|---|---|---|
| `RelationType` | — | Python StrEnum: `owner`, `manager`, `headquarters` | — |
| `UserPartyBinding` | `user_party_bindings` | `id` String PK (uuid4), `user_id` String FK → `users.id`, `party_id` String FK → `parties.id`, `relation_type`, `is_primary`, `valid_from`, `valid_to`, `created_at`, `updated_at` | `UNIQUE(user_id, relation_type) WHERE is_primary=true`；排斥约束 |

#### [NEW] `models/project_asset.py`

对齐设计文档 §3.4（L260-265）：

| 类名 | 表名 | 字段 |
|---|---|---|
| `ProjectAsset` | `project_assets` | `id` String PK (uuid4), `project_id` String FK → `projects.id`, `asset_id` String FK → `assets.id`, `valid_from`, `valid_to`, `bind_reason`, `unbind_reason`, `created_at`, `updated_at` |

#### [NEW] `models/certificate_party_relation.py`

对齐设计文档 §3.4（L284-300）：

| 类名 | 表名 | 字段 | 约束 |
|---|---|---|---|
| `CertificatePartyRelation` | `certificate_party_relations` | `id` String PK (uuid4), `certificate_id` String FK → `property_certificates.id`, `party_id` String FK → `parties.id`, **`relation_role`** ENUM(`owner`/`co_owner`/`issuer`/`custodian`), `is_primary` BOOL DEFAULT FALSE, `share_ratio` NUMERIC(5,2) NULL, `valid_from`, `valid_to`, **`metadata`** JSONB, `created_at`, `updated_at` | `valid_to IS NULL OR valid_to >= valid_from`；排斥约束（同证照同主体同角色不重叠）；`share_ratio IS NULL OR (share_ratio > 0 AND share_ratio <= 100)`；`UNIQUE(certificate_id) WHERE relation_role='owner' AND is_primary=true AND valid_to IS NULL` |

#### [NEW] `models/abac.py`

对齐设计文档 §4.2（L385-399）+ §4.2 `abac_role_policies`（L364-374）：

| 类名 | 表名 | 字段 | 约束 |
|---|---|---|---|
| `ABACPolicy` | `abac_policies` | `id` String PK (uuid4), `name`, `effect` ENUM(allow/deny), `priority` INT, `enabled` BOOL | — |
| `ABACPolicyRule` | `abac_policy_rules` | `id` String PK (uuid4), `policy_id` String FK, `resource_type`, `action` ENUM(单值：create\|read\|list\|update\|delete\|export), `condition_expr` JSONB, `field_mask` JSONB NULL | — |
| `ABACRolePolicy` | `abac_role_policies` | `id` String PK (uuid4), `role_id` String FK → `roles.id`, `policy_id` String FK → `abac_policies.id`, **`enabled`** BOOL, **`priority_override`** INT NULL, **`params_override`** JSONB NULL, `created_at`, `updated_at` | **`UNIQUE(role_id, policy_id)`** |

#### [MODIFY] `models/__init__.py`

新增所有新模型的 import 和 `__all__` 注册。

---

### 3.2 Alembic 迁移

> 约定：revision ID 格式 `YYYYMMDD_description`。  
> **`down_revision` 必须指向执行时的 Alembic HEAD**（通过 `alembic heads` 确认），不硬编码。当前 HEAD 为 `20260211_add_organization_scope_columns`，但如有新迁移插入，需以实际为准。

#### [NEW] `alembic/versions/20260219_create_party_tables.py`

第 1 个迁移文件，创建 Party 系表：
- 前置：`CREATE EXTENSION IF NOT EXISTS btree_gist`
- `parties` + `UNIQUE(party_type, code)` + 索引
- `party_hierarchy` + 约束 + 防环触发器（PL/pgSQL `BEFORE INSERT OR UPDATE`）
- `party_contacts` + partial unique 索引（`UNIQUE(party_id) WHERE is_primary=true`）
- `party_role_defs` + **`UNIQUE(role_code, scope_type)`** + seed 数据（owner/manager/headquarters）
- `party_role_bindings` + 排斥约束 + scope_type/scope_id 一致性约束
- `user_party_bindings` + partial unique + 排斥约束

#### [NEW] `alembic/versions/20260219_create_abac_and_relation_tables.py`

第 2 个迁移文件（`down_revision` = 第 1 个迁移的 revision ID）：
- `project_assets`
- `certificate_party_relations`（含 `relation_role` ENUM + `share_ratio` 范围约束 + 主产权方唯一约束）
- `abac_policies`
- `abac_policy_rules`
- `abac_role_policies`（含 `UNIQUE(role_id, policy_id)`）

#### [MODIFY] `alembic/env.py`

L23-36 模型导入块新增 6 个模块：`party`, `party_role`, `user_party_binding`, `project_asset`, `certificate_party_relation`, `abac`。

---

### 3.3 CRUD 数据访问层（`backend/src/crud/`）

> 项目约定：纯数据访问，不含业务逻辑；Service 层通过 CRUD 层访问 DB。

#### [NEW] `crud/party.py`

Party/Hierarchy/Contact/UserPartyBinding CRUD 方法：`create_party`, `get_party`, `get_parties`, `update_party`, `delete_party`, `add_hierarchy`, `remove_hierarchy`, `get_descendants`（递归 CTE），`create_contact`, `update_contact`, `delete_contact`, `create_user_party_binding`, `get_user_bindings`。

#### [NEW] `crud/authz.py`

ABAC 策略 CRUD：`get_policies_by_role_ids`, `create_policy`, `update_policy`, `create_policy_rule`, `bind_role_policy`, `unbind_role_policy`。

#### [NEW] `crud/project_asset.py`

项目-资产绑定：`bind_asset`, `unbind_asset`, `get_project_assets`, `get_asset_projects`。

---

### 3.4 Pydantic Schema（`backend/src/schemas/`）

#### [NEW] `schemas/party.py`

`PartyCreate`, `PartyUpdate`, `PartyResponse`, `PartyHierarchyResponse`, `PartyContactCreate`, `UserPartyBindingCreate`, `UserPartyBindingResponse` 等。

#### [NEW] `schemas/authz.py`

对齐设计文档 §5.1（L633-651）capabilities 最小 Schema：

```python
class AuthzCheckRequest(BaseModel):
    resource_type: str
    resource_id: str | None = None
    action: Literal["create", "read", "list", "update", "delete", "export"]

class AuthzCheckResponse(BaseModel):
    allowed: bool
    reason_code: str | None = None

class DataScope(BaseModel):
    owner_party_ids: list[str] = []
    manager_party_ids: list[str] = []

class CapabilityItem(BaseModel):
    resource: str
    actions: list[str]
    perspectives: list[str]
    data_scope: DataScope

class CapabilitiesResponse(BaseModel):
    version: str           # 必须字段，如 "2026-02-17.v1"
    generated_at: datetime  # 必须字段
    capabilities: list[CapabilityItem]
```

> 兼容约束（§5.1 L651）：前端按 `version` 解析；后端新增字段必须向后兼容，不得破坏既有枚举语义。

---

### 3.5 Service 服务层（`backend/src/services/`）

> 项目约定：业务逻辑在 Service 层；每个领域一个包（`services/{domain}/`）。

#### [NEW] `services/authz/`

| 文件 | 职责 |
|---|---|
| `__init__.py` | 包导出 |
| `engine.py` | JSONLogic 判定核心：`evaluate(subject, resource, action, policies) → bool`；本期唯一引擎 JSONLogic（§4.2） |
| `context_builder.py` | 构建判定上下文：从 `user_party_bindings` 加载 owner/manager/headquarters 分桶；headquarters 子树展开**仅并入 `manager_party_ids`**（§4.3 L414） |
| `service.py` | 对外服务层：`check_access()`, `get_capabilities()`, 策略加载 + 缓存 |

#### [NEW] `services/party/`

| 文件 | 职责 |
|---|---|
| `__init__.py` | 包导出 |
| `service.py` | Party CRUD 编排 + hierarchy 防环校验（应用层 + 触发器双重保证） |

---

### 3.6 API 端点（`backend/src/api/v1/`）

> 项目约定（AGENTS.md L116）：**新 API 使用 `route_registry.register_router()` 注册**。新模块在文件末尾调用 `register_router()`（参考 `collection.py` L164），同时在 `api/v1/__init__.py` 显式导入以触发模块加载。

#### [NEW] `api/v1/authz.py`

| 端点 | 方法 | 说明 |
|---|---|---|
| `POST /api/v1/authz/check` | POST | ABAC 判定（§5.1 第 7 项） |

```python
# 文件末尾注册（参考 collection.py L164）
route_registry.register_router(router, prefix="/api/v1", tags=["鉴权服务"], version="v1")
```

#### [NEW] `api/v1/party.py`

| 端点 | 方法 | 说明 |
|---|---|---|
| `/api/v1/parties` | GET/POST | Party 列表/创建 |
| `/api/v1/parties/{id}` | GET/PUT/DELETE | Party 详情/更新/删除 |
| `/api/v1/parties/{id}/hierarchy` | GET/POST/DELETE | 层级关系管理 |
| `/api/v1/parties/{id}/contacts` | GET/POST | 联系方式管理 |

```python
# 文件末尾注册
route_registry.register_router(router, prefix="/api/v1", tags=["主体管理"], version="v1")
```

#### [MODIFY] `api/v1/__init__.py`

新增导入以触发模块加载（参考 `collection.py` L164 `register_router()` 注册模式，仅导入不做其他操作）：

```python
# --- Party-Role Phase 1 新模块加载（触发 route_registry.register_router） ---
from . import authz  # noqa: F401
from . import party  # noqa: F401
```

> [!IMPORTANT]
> `route_registry.register_router()` 是模块级代码，必须有显式导入才会执行。如果不在 `__init__.py` 导入，注册语句不会被触发，路由将不生效。

> `GET /api/v1/auth/me/capabilities` 注册到**现有** `auth_router`（`api/v1/auth/auth.py`），因为它属于 `/auth/me/` 路径前缀，与 auth 路由共址。

---

## 4. 验证计划

### 4.1 自动化测试

| 测试文件 | 覆盖范围 |
|---|---|
| `tests/unit/models/test_party.py` | Party/PartyHierarchy/PartyContact 模型实例化、约束、枚举值 |
| `tests/unit/models/test_party_role.py` | PartyRoleDef/PartyRoleBinding, `UNIQUE(role_code, scope_type)`, scope_type 一致性 |
| `tests/unit/models/test_user_party_binding.py` | UserPartyBinding, RelationType 枚举 |
| `tests/unit/models/test_abac.py` | ABACPolicy/ABACPolicyRule/ABACRolePolicy, `UNIQUE(role_id, policy_id)` |
| `tests/unit/services/test_authz_engine.py` | JSONLogic evaluate(): owner/manager 路径命中、deny-by-default、field_mask |

```bash
# 新增测试
cd backend && python -m pytest tests/unit/models/test_party.py tests/unit/models/test_abac.py tests/unit/services/test_authz_engine.py -v

# 迁移验证（升级/降级/再升级）
cd backend && alembic upgrade head && alembic downgrade -1 && alembic upgrade head

# 现有测试回归（不依赖 pytest-timeout 插件的写法）
cd backend && python -m pytest -m "not slow" -x
```

### 4.2 手动验证

1. **表结构检查**：PostgreSQL `\dt` 确认新表 + `\d parties` 确认约束/索引
2. **防环触发器**：手动尝试插入环形层级数据 → 触发器阻止
3. **排斥约束**：尝试插入同主体同角色重叠时间段 → 约束拒绝
4. **capabilities Schema**：调用 `GET /api/v1/auth/me/capabilities` 确认返回含 `version` + `generated_at` + `capabilities` 数组

---

## 5. 文件总览

| 类型 | 新增 | 修改 |
|---|---|---|
| ORM 模型 | 6 | 1（`__init__.py`） |
| Alembic 迁移 | 3 | 1（`env.py`） |
| CRUD | 3 | — |
| Schema | 2 | — |
| Service 包 | 2（共 6 文件） | — |
| API 端点 | 2 | 2（`v1/__init__.py` 导入触发加载 + `auth/auth_modules/authentication.py` capabilities 端点） |
| 单元测试 | 5 | — |
| 依赖配置 | — | 1（`pyproject.toml`：生产 + dev 依赖） |
| **合计** | **~22** | **5** |

---

## 6. 文档历史

| 日期 | 版本 | 变更 |
|---|---|---|
| 2026-02-18 | 1.0 | 初始版 |
| 2026-02-19 | 1.1 | P0 修复：(1) 模型字段与 v3.7 对齐（party_contacts/party_role_defs/certificate_party_relations/abac_role_policies）；(2) Alembic down_revision 改为"执行时确认"策略；(3) 路由注册改为 `api_router.include_router()`；(4) 新增 `json-logic-quart` + `pytest-timeout` 依赖前置；(5) capabilities Schema 对齐 §5.1 最小 Schema 含 version/generated_at 硬约束 |
| 2026-02-19 | 1.2 | (1) P0: ID 类型统一为 `String` + `uuid4()`（对齐设计文档 §2 L108），全表 PK/FK 标注为 `String`；(2) P1: `pytest-timeout` 移到 `[project.optional-dependencies]` → `dev` 组；(3) P1: 路由注册改用 `route_registry.register_router()`（对齐 AGENTS.md L116） |
| 2026-02-19 | 1.3 | (1) P0: JSONLogic 依赖名修正为 `json-logic>=0.6.3`（PyPI 实测可用）；(2) P1: 阶段定位改为"不改业务域模型与旧接口语义，仅新增能力并做最小接线改动" |
| 2026-02-19 | 1.4 | (1) P0: 路由加载保障——在 `__init__.py` 显式导入新模块触发 `register_router()` 执行（与 `collection.py` L38 模式一致）；(2) P1: 能力接口路径统一为 `/api/v1/auth/me/capabilities`；(3) P1: L7 与路由段自冲突消除（明确包含 `__init__.py` 修改）；(4) P2: 设计文档元数据同步；(5) P2: CHANGELOG 同步 |
| 2026-02-19 | 1.5 | (1) P0: 上游基线版本升至 v3.9（对齐设计文档当前版本，含 capabilities 契约修复）；(2) P2: 路由注册参考行号修正为 `collection.py` L164（实际 `register_router()` 调用位置） |
| 2026-02-19 | 1.6 | (1) P0: 依赖口径修正为 `python-jsonlogic>=0.1.0`（Python 3.12 兼容）；(2) P1: API 变更文件路径与实际实现对齐（`authentication.py`）；(3) P1: 增补执行状态为“已完成”并记录回归验证结论 |
