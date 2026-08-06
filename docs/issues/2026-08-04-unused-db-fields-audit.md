# 数据库中未实际使用字段审计

**状态**: 🔄 待处置
**分析日期**: 2026-08-04
**审计口径**: 全量提取 `backend/src/models/*.py` 48 张表的 ORM 字段共 613 个（排除系统性字段：`id` / `created_at` / `updated_at` / `created_by` / `updated_by` / `version` / `data_status` / `deleted_at` 及 synonym），对 `backend/src`、`frontend/src`、`backend/tests`、`backend/alembic`、`docs` 五区做静态引用扫描，逐一核实写入与读取路径。

**本报告只记录问题事实与证据，不给出修复方案。**

---

## 一、整表无业务写入（表存在但永远为空，或仅被读）

### 1.1 `asset_documents`（AssetDocument）

| 项 | 证据 |
|----|------|
| 模型 | `models/asset_history.py`（`class AssetDocument`），`models/asset.py:292-293` 关系引用 |
| Schema | `schemas/asset.py:632`（`AssetDocumentResponse`） |
| 问题 | 全代码库无任何 `AssetDocument(...)` 实例创建；`AssetDocumentResponse` 无 API 使用。附件实际走文件系统（`api/v1/assets/asset_attachments.py` → `services/asset/asset_attachment_upload_service`），无 DB 持久化路径 |

### 1.2 `party_role_defs` / `party_role_bindings`（PartyRoleDef / PartyRoleBinding）

| 项 | 证据 |
|----|------|
| 模型 | `models/party_role.py:27`（`class PartyRoleDef`）、`models/party_role.py:56`（`class PartyRoleBinding`）；`models/party.py:162-163` 关系引用 |
| 问题 | 无任何服务/API/CRUD 使用；仅模型、单测、alembic 迁移中存在。`docs/archive/issues/2026-04-party-architecture-analysis.md:59` 已记录"当前代码中零 CRUD/Service/API 使用"；随表死的字段：`party_role_defs.scope_type`、`party_role_bindings.scope_type`、`party_role_bindings.role_def_id` |

### 1.3 `asset_management_history`（AssetManagementHistory）

| 项 | 证据 |
|----|------|
| 模型 | `models/asset_management_history.py:21`（`class AssetManagementHistory`） |
| CRUD | `crud/asset_management_history.py:15-18`（含 `async def create`） |
| API | `api/v1/assets/assets.py:910`（GET 端点 `get_asset_management_history`）→ `services/asset/asset_service.py:589-602` |
| 问题 | 表由迁移 `20260219_phase2_add_party_columns_step1.py` 创建；GET 端点与 CRUD create 存在，但 **create 无任何调用方** → 表永远为空，端点恒返回空列表 |

---

## 二、活跃表上的死字段

### 2.1 `audit_logs.user_organization`

- 模型：`models/auth.py:276`
- 证据：`crud/auth.py:511-541` 的 `AuditLog` 写入路径共写 16 个字段（user_id / username / user_role / action / resource_type / resource_id / resource_name / api_endpoint / http_method / request_params / request_body / response_status / response_message / ip_address / user_agent / session_id），**不含** `user_organization`；全代码库无读取方

### 2.2 `abac_role_policies.priority_override` / `abac_role_policies.params_override`

- 模型：`models/abac.py:134`（`class ABACRolePolicy`）、`models/abac.py:164-165`
- 迁移：`20260219_create_abac_and_relation_tables.py:221-222`
- 证据：唯一实际写入路径 `services/authz/data_policy_service.py:124-127`（`set_role_policy_packages`）只设置 `role_id` / `policy_id` / `enabled` 三字段；`crud/authz.py:41/75/91/107` 的 `create_policy` / `create_policy_rule` / `bind_role_policy` / `unbind_role_policy` 均无服务/API 调用方（`crud/authz.py:15` 的 `get_policies_by_role_ids` 是唯一被 `data_policy_service` 使用的入口）；两字段无任何读取方

### 2.3 `certificate_party_relations.share_ratio`

- 模型：`models/certificate_party_relation.py`（含 `share_ratio`）
- 证据：后端全代码零引用；仅 `frontend/src/types/party.ts:103` 有类型声明。对照同表 `relation_role` 为活跃使用（`crud/property_certificate.py:155,184` 写入/筛选）

### 2.4 `assets.asset_form` / `assets.spatial_level` / `assets.business_usage`

- 模型：`models/asset.py:121,126,129`
- Schema：`schemas/asset.py:79-85`（`AssetBase`）及 269-271 / 436-438
- 迁移：`20260305_asset_field_enrichment_m1.py:28-30`（建列 + 回填默认值）
- 证据：无任何服务逻辑读取；前端零引用（含 type 声明）；仅能在 API 请求体中透传落库

### 2.5 `project_assets.bind_reason` / `project_assets.unbind_reason`

- 模型：`models/project_asset.py:54-55`
- 证据：唯一写入路径 `crud/project_asset.py:19`（`bind_asset`）/ `:35`（`unbind_asset`）**无任何服务/API 调用方**（仅 `tests/unit/crud/test_project_asset.py` 单测使用）；`scripts/migration/party_migration/backfill_project_assets.py` 的 INSERT 不写 `bind_reason`。对照：`project_assets` 表本身为活跃使用（`middleware/resource_context.py:47-59`、`services/asset/asset_service.py:613-620`、`services/project/service.py:769-863` 读取）

---

## 三、死代码配套证据（供决策参考）

| 位置 | 说明 |
|------|------|
| `crud/authz.py:41-107` | `create_policy` / `create_policy_rule` / `bind_role_policy` / `unbind_role_policy` 均无服务/API 调用方；`ABACPolicy` / `ABACRolePolicy` 表仅经 `data_policy_service` 的只读查询与固定模板写入在使用 |
| `crud/project_asset.py:19-35` | `bind_asset` / `unbind_asset` 无调用方，仅单测覆盖 |

---

## 四、高风险项（非死字段，属潜在运行时缺陷）

### 4.1 `project_ownership_relations`（ProjectOwnershipRelation）— 表已删除但代码仍引用

| 项 | 证据 |
|----|------|
| 建表 | `e4c9e4968dd7_initial_schema_creation.py:645-677`（upgrade 建表，downgrade 2027 行删表） |
| 删表 | `20260301_phase4_drop_legacy_party_columns.py`：`_LEGACY_TABLES` 含 `project_ownership_relations`（:38），`upgrade()` 经 `_drop_legacy_tables`（:65-69）**删除该表**；仅 `downgrade()` :124-135 重建 |
| 测试确认 | `tests/unit/migration/test_phase4_migrations.py:207` 断言 `project_ownership_relations` 已进入 dropped_tables |
| 仍写入 | `services/ownership/service.py:146-179`：`update_related_projects` 运行中 `ProjectOwnershipRelation()` 建行（:173-177）并 `db.add` |
| 仍暴露 | `api/v1/assets/ownership.py:209-255`：活跃端点 `PUT /api/v1/ownerships/{ownership_id}/projects` 调用 `update_related_projects`（:236） |
| 仍查询 | `crud/ownership.py:198`（`count_projects_async`）、`:222`（`delete_project_relations_async`）、`crud/project.py:292-301`（`owner_party_id` 搜索过滤）、`crud/project.py:293-298` |
| 已知留痕 | `services/project/service.py:424` 注释"Legacy relation table `project_ownership_relations` has been removed by migrations."，项目侧已拒写（`_replace_project_owner_relations` 抛 `OperationNotAllowedError`），**ownership 侧未同步下线** |

**事实**：在已执行 head 迁移的数据库上，调用 `PUT /api/v1/ownerships/{ownership_id}/projects`（以及任何触达 `count_projects_async` / 带 `owner_party_id` 的项目搜索）将因 `relation "project_ownership_relations" does not exist` 报错（500）。现有单测通过是因为 mock 了 service / 未连接已迁移库。

---

## 五、边界情况与建议测试用例

1. **D 项复现用例（真实数据库回归）**：对已迁移至 head 的 PostgreSQL 实例：
   - `PUT /api/v1/ownerships/{id}/projects`（body `{"project_ids": [...]}`）→ 预期当前失败（UndefinedTable），用于锁定问题存在
   - `GET /api/v1/projects/?owner_party_id=<id>` → 预期当前失败，用于锁定搜索过滤路径
   - `GET /api/v1/ownerships/{id}` → 核对其响应是否触达 `count_projects_async`
2. **A 类空表验证**：`SELECT count(*) FROM asset_management_history;`、`asset_documents`、`party_role_defs`、`party_role_bindings` → 全 0 行
3. **B 类写入验证**：
   - 写入一条 `audit_logs` 后断言 `user_organization IS NULL`
   - `set_role_policy_packages` 绑定策略后断言 `abac_role_policies.priority_override` / `params_override` 为 NULL
   - 创建带 identifier 的主体后断言 `identifier_fingerprint` 非空（**对照**：该字段属活跃路径，不应列入死字段）
4. **字段规格同步校验**：处置前运行 `make check-field-drift`，确认以上字段在 `docs/specs/domain-model.md` 中的记录与 ORM 一致
