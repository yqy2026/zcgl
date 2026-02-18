# 组织架构与资产权属关系设计（Party-Role 一次切换版）

**文档类型**: 技术设计文档  
**创建日期**: 2026-02-16  
**最新更新**: 2026-02-18  
**状态**: 待实施（方案冻结）  
**作者**: Codex

---

## 快速导航（TOC）

- [0. 摘要](#0-摘要)
- [1. 目标与边界](#1-目标与边界)
- [1.1 目标](#11-目标)
- [1.2 范围（本期）](#12-范围本期)
- [1.3 非目标（本期不做）](#13-非目标本期不做)
- [2. 关键决策（已冻结）](#2-关键决策已冻结)
- [3. 目标数据模型](#3-目标数据模型)
- [3.1 Party 主体层](#31-party-主体层)
- [3.2 Role 关系层](#32-role-关系层)
- [3.3 用户-Party 绑定](#33-用户-party-绑定)
- [3.4 业务表字段替换（公共接口影响）](#34-业务表字段替换公共接口影响)
- [4. 权限模型（角色入口 + ABAC 执行）](#4-权限模型角色入口--abac-执行)
- [4.1 管理面：角色绑定策略（管理员视角）](#41-管理面角色绑定策略管理员视角)
- [4.2 决策面：ABAC 策略表（运行时）](#42-决策面abac-策略表运行时)
- [4.3 判定上下文](#43-判定上下文)
- [4.4 关键策略（与当前口径对齐）](#44-关键策略与当前口径对齐)
- [4.5 角色策略包示例（推荐默认）](#45-角色策略包示例推荐默认)
- [4.6 既有 RBAC 角色到策略包映射（迁移强制）](#46-既有-rbac-角色到策略包映射迁移强制)
- [4.7 ABAC 缓存键与失效广播规范（本期落地）](#47-abac-缓存键与失效广播规范本期落地)
- [4.8 ABAC 策略规则示例（JSONLogic）](#48-abac-策略规则示例jsonlogic)
- [5. API / Schema / Type 变更清单](#5-api--schema--type-变更清单)
- [5.1 后端 Schema（破坏性）](#51-后端-schema破坏性)
- [5.2 前端 Type/Service](#52-前端-typeservice)
- [5.3 外部调用方切换要求（破坏性变更治理）](#53-外部调用方切换要求破坏性变更治理)
- [5.4 登录时权限展开逻辑（后端实现约束）](#54-登录时权限展开逻辑后端实现约束)
- [5.5 创建接口 ABAC 资源注入规范（强制）](#55-创建接口-abac-资源注入规范强制)
- [5.6 数据隔离层替代方案（TenantFilter → PartyFilter）](#56-数据隔离层替代方案tenantfilter--partyfilter)
- [6. 一次切换迁移方案（Runbook）](#6-一次切换迁移方案runbook)
- [6.1 上线前准备](#61-上线前准备)
- [6.2 发布窗口执行](#62-发布窗口执行)
- [6.3 发布后收敛](#63-发布后收敛)
- [6.4 `project_assets` 人工清单处置规则](#64-project_assets-人工清单处置规则)
- [7. 测试与验收](#7-测试与验收)
- [7.1 迁移对账（硬门禁）](#71-迁移对账硬门禁)
- [7.2 权限回归](#72-权限回归)
- [7.3 业务回归](#73-业务回归)
- [7.4 性能门槛](#74-性能门槛)
- [7.5 权限缓存一致性验收](#75-权限缓存一致性验收)
- [7.6 组织层级防环验收](#76-组织层级防环验收)
- [7.7 审计与合规验收（强制项）](#77-审计与合规验收强制项)
- [8. 回滚预案](#8-回滚预案)
- [9. 实施任务拆解（可直接派工）](#9-实施任务拆解可直接派工)
- [9.1 审计与合规（推荐增强）](#91-审计与合规推荐增强)
- [9.2 发布前责任矩阵（RACI，推荐）](#92-发布前责任矩阵raci推荐)
- [10. 重要假设与默认值](#10-重要假设与默认值)
- [11. 文档历史](#11-文档历史)

---

## 0. 摘要

本方案将现有 `Organization + Ownership` 模型升级为 **Party-Role 模式**，并按“**一次切换**”落地：

1. 主体统一到 `Party`（组织、外部法人）。  
2. 角色统一为“主体角色 + 资源关系角色”。  
3. 权限统一为“**角色配置入口 + ABAC 执行判定**”双层模型。  
4. 资产、合同、项目、产权证全域替换主体关联字段。  
5. 单窗口发布，数据正确性优先，失败即回滚。

---

## 1. 目标与边界

### 1.1 目标

1. 消除 `organization_id / ownership_id / management_entity` 的多语义冲突。  
2. 支持“同一主体在不同资源扮演不同角色”的标准表达。  
3. 权限判定从“组织字段过滤”升级为“关系+策略”判定。  
4. 支持历史追溯（经营方变更、关系有效期）。

### 1.2 范围（本期）

1. 后端：`asset / rent_contract / project / property_certificate / authz` 全量改造。  
2. 前端：上述模块类型、接口、视图参数同步切换。  
3. 数据库：新增 Party 体系、ABAC 策略表及“角色-策略绑定”表，旧字段下线。  
4. 运维：一次窗口迁移与回滚机制。

### 1.3 非目标（本期不做）

1. 不引入自然人 Party。  
2. 不保留旧接口兼容层。  
3. 不做“渐进双写”。

---

## 2. 关键决策（已冻结）

1. 上线模式：**一次切换**。  
2. 权限模型：**混合模型**（RBAC 作为管理入口，ABAC 作为运行时决策）。  
3. 管理员配置方式：**仅角色入口**（禁止直接给用户/主体绑数据策略）。  
4. 层级存储：迁移至 `party_hierarchy`。  
5. 业务范围：全域替换（资产+合同+项目+产权证+权限）。  
6. ID 策略：Party 侧全部新 ID，使用映射表回填。  
7. 本期不保留 `abac_policy_subjects`，直接删除表结构。  
8. 门禁原则：数据正确性优先，未通过不发布。  
9. ID 类型：统一为 `String`（与现网 22 张表一致，本轮不引入 UUID 类型迁移轴；新表 DDL 中 `UUID PK` 实际实现为 `String + Python uuid4()`）。  
10. ABAC 条件引擎：JSONLogic（`json-logic-py` 或等价库），需新增依赖。

---

## 3. 目标数据模型

### 3.1 Party 主体层

### `parties`
- `id` UUID PK  
- `party_type` ENUM(`organization`,`legal_entity`)  
- `name`  
- `code`  
- `external_ref`（外部主数据唯一标识，可选）  
- `status`  
- `metadata` JSONB  
- `created_at`, `updated_at`

约束：
- `UNIQUE(party_type, code)`
- `code` 治理口径（强制）：
  - 迁移期间允许临时空值，但正式放流前必须清零（`parties.code IS NULL = 0`）。
  - `code` 缺失时必须在迁移阶段生成可追溯补位值（建议：`AUTO-{party_type}-{legacy_id}`），禁止长期保留 `NULL`。
- 匹配优先级（迁移映射）：
  - `external_ref`（若有） > 法定统一标识（如统一社会信用代码） > `code` > 人工清单。
  - 禁止仅按名称模糊匹配自动合并主体。

### `party_hierarchy`
- `id` UUID PK  
- `parent_party_id` FK -> `parties.id`  
- `child_party_id` FK -> `parties.id`  
- `created_at`, `updated_at`

约束：
- `UNIQUE(parent_party_id, child_party_id)`  
- `CHECK(parent_party_id <> child_party_id)`（禁止自环）
- 禁止环（服务层校验 + DB 触发器双重保证）

语义约束（必须统一）：
- 本表采用**邻接表**语义：一行仅表示一条“直接父子边”，不存闭包路径。
- 子孙展开统一通过递归 CTE（如 `get_descendant_parties`）运行时计算；`party_hierarchy` 本身不作为闭包表维护。

防环实现约束（本期必须落地）：
- `BEFORE INSERT OR UPDATE` 触发器执行递归 CTE：若存在 `NEW.child_party_id -> ... -> NEW.parent_party_id` 路径，则拒绝写入。
- 触发器错误码统一为业务可识别码（如 `PARTY_HIERARCHY_CYCLE_DETECTED`），前端提示“组织层级存在循环依赖，保存失败”。
- 必备索引：`party_hierarchy(parent_party_id)`、`party_hierarchy(child_party_id)`；避免递归校验全表扫描。

### `party_contacts`
- `id` UUID PK  
- `party_id` FK -> `parties.id`  
- `contact_name`  
- `contact_phone`  
- `contact_email`  
- `position`  
- `is_primary`  
- `notes`  
- `created_at`, `updated_at`

约束：
- 同一 `party_id` 仅一个 `is_primary=true`（部分唯一）
- 实现要求：`UNIQUE(party_id) WHERE is_primary=true`（PostgreSQL Partial Unique Index）

---

## 3.2 Role 关系层

### `party_role_defs`
- `id` UUID PK  
- `role_code`（如 `OWNER`,`MANAGER`,`LESSOR`,`LESSEE`）  
- `scope_type`（`global`,`asset`,`contract`,`project`,`certificate`）  
- `description`

约束：
- `UNIQUE(role_code, scope_type)`

### `party_role_bindings`
- `id` UUID PK  
- `party_id` FK -> `parties.id`  
- `role_def_id` FK -> `party_role_defs.id`  
- `scope_type`  
- `scope_id` UUID NULL（`scope_type='global'` 时必须为 `NULL`；其余 scope 必须非 `NULL`）  
- `valid_from`, `valid_to`  
- `attributes` JSONB  
- `created_at`, `updated_at`

约束：
- 区间合法：`valid_to IS NULL OR valid_to >= valid_from`  
- 同主体同角色同资源时间段不重叠（应用层 + DB 排斥约束）
- `scope_type` 必须与 `party_role_defs.scope_type` 一致（通过复合唯一 + 复合外键或等价触发器保证，禁止仅应用层校验）
- `scope_type/scope_id` 一致性：`scope_type='global'` -> `scope_id IS NULL`；`scope_type!='global'` -> `scope_id IS NOT NULL`

本期定位（强制说明）：
- `party_role_bindings` 不参与实时 ABAC 真值判定（真值来源见 4.4）。
- 本期写入来源：迁移回填 + 业务服务在关系变更时写入（禁止人工直改 DB）。
- 本期读取场景：审计追溯、历史报表、后续扩展（例如关系时序分析）。

---

## 3.3 用户-Party 绑定

### `user_party_bindings`
- `id` UUID PK
- `user_id` FK -> `users.id`
- `party_id` FK -> `parties.id`
- `relation_type` ENUM(`owner`,`manager`,`headquarters`)
- `is_primary` BOOL DEFAULT FALSE
- `valid_from`, `valid_to`
- `created_at`, `updated_at`

约束：
- 区间合法：`valid_to IS NULL OR valid_to >= valid_from`
- `UNIQUE(user_id, party_id, relation_type, valid_from)`（允许历史多版本）
- 同一 `user_id + party_id + relation_type` 时间段不重叠（应用层 + DB 排斥约束）
- 同一用户同一关系类型仅允许一个当前主绑定：`UNIQUE(user_id, relation_type) WHERE is_primary=true AND valid_to IS NULL`
- 上述“当前主绑定唯一”必须通过 PostgreSQL Partial Unique Index 实现（禁止仅用应用层唯一校验）。

治理门禁（非 DB 硬约束）：
- 生产有效用户（排除停用用户与 `no_data_access`）若需要写权限，至少有一条 `relation_type in ('manager','headquarters')` 的有效绑定。
- `owner`-only 用户允许保留为只读口径（如仅产权查看）；不得授予写权限。
- 未满足写入门禁的用户不得开放写流量。

关系类型说明：
| relation_type | 说明 | 权限范围 |
|---|---|---|
| `owner` | 产权方 | 仅该 Party 的产权数据 |
| `manager` | 管理方 | 仅该 Party 的运营数据 |
| `headquarters` | 集团总部 | 该 Party 及所有子 Party 的管理路径数据（通过 `party_hierarchy` 展开） |

补充说明：
- `headquarters` 展开范围为“该节点自身 + 其子孙”，不包含其上级链路。
- 本期权限并入口径：`headquarters` 展开结果仅并入 `manager_party_ids`，不并入 `owner_party_ids`。

---

## 3.4 业务表字段替换（公共接口影响）

### 资产 `assets`
- 删除：`organization_id`, `ownership_id`, `management_entity`
- 新增：`owner_party_id` NOT NULL, `manager_party_id` NOT NULL
- 保留：`management_start_date`, `management_end_date`, `management_agreement`

### 合同 `rent_contracts`
- 删除：`ownership_id`（现有 FK 指向 `ownerships.id`，迁移时需通过 `ownership_to_party_map` 映射）
- 新增：`owner_party_id` NOT NULL, `manager_party_id` NOT NULL, `tenant_party_id` NULL
- `tenant_party_id` 迁移策略：`tenant_name` 为 `String(200)` 自由文本，本期 `tenant_party_id` 仅做选填标注，不从 `tenant_name` 自动迁移（本期不引入自然人 Party，承租方可能含个人）；已知企业承租方可后续人工补绑

### 项目 `projects`
- 删除：`organization_id`、`management_entity`（String(200) 管理单位）、`ownership_entity`（String(200) 权属单位）
- 新增：`manager_party_id` NOT NULL
- 说明：项目仅代表运营管理归集单元，不设置 `owner_party_id`；项目下资产可关联多个不同产权方
- `ownership_entity` 处置：该字段语义为“权属单位”，迁移时对 `parties.name` 模糊匹配写入 `party_role_bindings`（`role_code=OWNER` + `scope_type=project`），未匹配项进入人工清单

### 项目-资产关系 `project_assets`
- `id` UUID PK
- `project_id` FK -> `projects.id`
- `asset_id` FK -> `assets.id`
- `valid_from`, `valid_to`
- `bind_reason`, `unbind_reason`
- `created_by`, `updated_by`
- `created_at`, `updated_at`

约束：
- 区间合法：`valid_to IS NULL OR valid_to >= valid_from`
- 同一 `project_id + asset_id` 时间段不重叠（应用层 + 约束）
- 建议索引：`(project_id, valid_to)`、`(asset_id, valid_to)`

说明：
- 业务流程约定：先有资产后有项目（软约束，不做数据库硬限制）。
- 本期**暂不硬约束**“创建项目时必须已绑定资产”。
- 绑定关系通过 `project_assets` 维护，支持资产跨时间迁移与历史追溯。

### 产权证 `property_certificates` 及关联表
- `organization_id` 全面替换为 `party_id`
- owner 关联改为 `certificate_party_relations`

### `certificate_party_relations`
- `id` UUID PK
- `certificate_id` FK -> `property_certificates.id`
- `party_id` FK -> `parties.id`
- `relation_role` ENUM(`owner`,`co_owner`,`issuer`,`custodian`)
- `is_primary` BOOL DEFAULT FALSE
- `share_ratio` NUMERIC(5,2) NULL
- `valid_from`, `valid_to`
- `metadata` JSONB
- `created_at`, `updated_at`

约束：
- 区间合法：`valid_to IS NULL OR valid_to >= valid_from`
- 同证照同主体同角色时间段不重叠（应用层 + DB 排斥约束）
- `share_ratio` 范围：`share_ratio IS NULL OR (share_ratio > 0 AND share_ratio <= 100)`
- 同一证照仅允许一个当前主产权方：`UNIQUE(certificate_id) WHERE relation_role='owner' AND is_primary=true AND valid_to IS NULL`
- 语义对齐：同一证照同一时刻仅允许一个“主产权方（owner + is_primary=true）”
- 建议索引：`(certificate_id, relation_role, valid_to)`、`(party_id, valid_to)`

### 历史表
新增 `asset_management_history`：
- `asset_id`, `manager_party_id`, `start_date`, `end_date`, `agreement`, `change_reason`, `changed_by`

### 台账 `rent_ledger`
- 删除：`ownership_id`
- 新增：`owner_party_id` NOT NULL
- 说明：`RentDepositLedger` 和 `ServiceFeeLedger` 仅含 `contract_id`，无 `ownership_id`，无需单独处理
- 代码联动：`RentContract.__init__` 构造函数中硬编码的 `ownership_id` 必填验证需同步改为 `owner_party_id`；`ledger_service.py` 中 `db_ledger.ownership_id = contract.ownership_id` 需改为 `db_ledger.owner_party_id = contract.owner_party_id`

### RBAC `roles` 表字段迁移
- 删除：`organization_id` FK → `organizations.id`
- `scope` 值域变更：`global/organization/department` → `global/party/party_subtree`
- `scope_id` 语义变更：原指向 `organizations.id`，改为指向 `parties.id`（`scope='global'` 时仍为 `NULL`）
- 说明：§4.1 "复用现有 RBAC 表"口径不变，仅修改上述字段

### `Asset.project_id` 处置
- 本期删除 `Asset.project_id` 直接 FK（`projects.id`），统一走 `project_assets` M2M 关系表
- 前端 `Asset` 类型中 `project_id` 同步移除
- 迁移时先将现有 `Asset.project_id` 回填到 `project_assets`，再删除该列

### `Asset.project_name` 去规范化字段处置
- `Asset.project_name`（`String(200)`）为去规范化冗余字段，迁移到 `project_assets` M2M 后存在数据不一致风险（一个资产可能关联多个项目）
- 本期保留该列但标记 **deprecated**：仅供搜索兼容使用，不再由业务逻辑写入
- `field_whitelist.py` 中 `AssetWhitelist.search_fields` 和 `sort_fields` 均含 `"project_name"`，本期保留搜索能力
- 后续版本计划：搜索改为 `JOIN project_assets + projects`，届时删除该列

### `RentContract` 冗余 owner 字段处置
- `owner_name`、`owner_contact`、`owner_phone` 保留为**历史快照**（只读）
- 迁移后不再从 Party 实时同步更新这些字段
- 新建合同时不再填写这些字段（由 `owner_party_id` 关联推导显示）

### 旧关联表处置
- `project_ownership_relations`：数据迁移到 `project_assets`（项目维度）+ `party_role_bindings`（主体维度）后物理删除
- `property_owners` + `property_certificate_owners`：数据迁移到 `certificate_party_relations` 后物理删除

---

## 4. 权限模型（角色入口 + ABAC 执行）

### 4.1 管理面：角色绑定策略（管理员视角）

### 复用现有 RBAC 表
- `roles`（字段迁移见 §3.4「RBAC roles 表字段迁移」）
- `user_role_assignments`

### 既有权限表处置（本期决策）

| 表 | 处置 | 说明 |
|---|---|---|
| `permission_grants` | 本期标记 **deprecated**，迁移窗口后物理删除 | 已有 grant 数据不迁入 ABAC；角色策略包为唯一权限判定路径 |
| `resource_permissions` | 同上 | `resource_type + permission_level` 功能由 `abac_policy_rules` 替代 |
| `permission_audit_logs` | 保留为历史审计（只读），不再新增写入 | 新审计走 §7.7 规范 |

既有权限服务处置：
- `OrganizationPermissionService`（282 行）：由 ABAC 引擎 + PartyFilter（§5.6）替代，标记废弃
- `OrganizationPermissionChecker`（中间件层）：由 `/authz/check` 端点替代，标记废弃
- `rbac_service.py` 中涉及 `PermissionGrant` 的 9 个方法（`_check_grant_permission` / `_get_matching_permission_grants` / `_scope_matches` / `_conditions_match` / `grant_permission_to_user` / `get_permission_grant` / `list_permission_grants` / `update_permission_grant` / `revoke_permission_grant`）：逐步迁移到 ABAC 策略包路径

判定路径统一原则：**仅 ABAC**。迁移后系统中不得存在 `PermissionGrant` 运行时读取路径，避免双重权限判定。

### 新增 `abac_role_policies`
- `id` UUID PK
- `role_id` FK -> `roles.id`
- `policy_id` FK -> `abac_policies.id`
- `enabled` BOOL
- `priority_override` INT NULL
- `params_override` JSONB（可选）
- `created_at`, `updated_at`

约束：
- `UNIQUE(role_id, policy_id)`

说明：
- 系统管理员只需要“给角色绑定策略包，再把角色分配给用户”。
- 新用户默认无角色或角色无策略绑定时，天然无数据权限（deny by default）。
- 策略绑定唯一入口是角色；不支持“用户直绑策略”或“主体直绑策略”。

---

## 4.2 决策面：ABAC 策略表（运行时）

### `abac_policies`
- `id`, `name`, `effect(allow|deny)`, `priority`, `enabled`

### `abac_policy_rules`
- `id`, `policy_id`
- `resource_type`, `action`（单值枚举：`create|read|list|update|delete|export`）
- `condition_expr`（**本期唯一引擎：JSONLogic**）
- `field_mask`（可选）

本期收口约束：
- `abac_policy_subjects` 表结构本期直接删除。  
- 策略主体来源统一为“用户 -> 角色 -> `abac_role_policies` -> `abac_policies`”链路。
- 本期禁止引入双表达式栈（JSONLogic + CEL）并行解析；CEL 标记为后续可选能力，不进入本期实现与验收范围。
- 命名映射约束：数据库持久化字段名为 `condition_expr`；文档/接口示例中的 `condition` 仅为展示别名，与 `condition_expr` 一一对应。
- 多动作规则落库约束：若业务希望一条策略覆盖多个动作，必须在存储层拆分为多条 `abac_policy_rules` 记录（每条单一 `action`）。

---

## 4.3 判定上下文
- Subject: `user_id`, `owner_party_ids`, `manager_party_ids`, `headquarters_party_ids`, `user_tags`
- Role: `role_ids`, `role_scope(scope/scope_id/context)`
- Resource: `resource_type`, `resource_id`, `owner_party_id`, `manager_party_id`
- Action（统一枚举）: `create|read|list|update|delete|export`
- Environment: 时间/IP/客户端
- 权威口径：本节为判定上下文与动作枚举的唯一权威定义；`abac_policy_rules.action`、`/api/v1/authz/check` 入参 `action`、`capabilities.actions` 必须与本节一致。
- 说明：`owner_party_ids / manager_party_ids / headquarters_party_ids` 来源于 `user_party_bindings` 有效记录，在登录与 token refresh 时加载并缓存
- 说明：`headquarters` 绑定会自动展开 `party_hierarchy` 子树；展开结果仅并入 `manager_party_ids`
- 说明：`project` 资源仅使用 `manager_party_id` 参与判定，不使用 `owner_party_id`
- 说明：`headquarters` 不隐式授予 owner 路径；owner 路径需 `owner` 绑定或独立策略命中。
- 权威口径：`headquarters` 语义仅为“并入 `manager_party_ids`”；本节为唯一权威定义，其它章节如有差异以本节为准。

---

## 4.4 关键策略（与当前口径对齐）

1. 默认拒绝（无命中策略即 deny）。  
2. 资产可见：命中 owner 路径或 manager 路径策略。  
3. 合同财务 `perspective=owner|manager` 必传。  
4. 管理视角写入：必须命中 manager 路径策略（`create/update/delete`，或全局 allow）。  
5. 项目读写：仅基于 `manager_party_id` 路径判定（不使用 owner 路径）。  
6. 无权限详情 404，列表空。
7. `owner_party_id / manager_party_id` 以业务表字段为唯一事实来源；`party_role_bindings` 不参与实时权限真值判定（仅用于扩展/审计）。
8. 可观测性要求：对“列表空/详情 404/403”权限拒绝，服务端必须记录 `request_id`、`resource_type`、`resource_id`（真实 ID，仅服务端可见）、`action`、`reason_code`、`subject_snapshot_hash`。
9. `headquarters` 仅影响 manager 路径集合，不影响 owner 路径集合。

## 4.5 角色策略包示例（推荐默认）

1. `platform_admin`：全资源 `allow all`。  
2. `asset_owner_operator`：资产/合同按 owner 路径可读，合同财务以 owner 视角。  
3. `asset_manager_operator`：资产/合同按 manager 路径可读写，合同财务以 manager 视角。  
4. `dual_party_viewer`：owner + manager 双路径只读。  
5. `project_manager_operator`：项目与 `project_assets` 按 manager 路径读写；资产/合同默认只读。  
6. `audit_viewer`：审计/统计只读（`read/export`），不含业务写权限。  
7. `no_data_access`：仅功能菜单权限，不含数据可见策略。

说明：
- “产权方/经营方”是资源关系语义（`owner_party_id / manager_party_id`），不是写死用户角色。
- 用户最终可见范围由“角色绑定的策略集合”运行时计算，不在业务 SQL 中硬编码固定角色名。

## 4.6 既有 RBAC 角色到策略包映射（迁移强制）

来源基线：`backend/scripts/setup/init_rbac_data.py` 中基础角色（`admin/manager/user/viewer/asset_manager/project_manager/auditor`）。

默认映射表（本期执行口径）：

| 现有角色 | 目标策略包 | 备注 |
|---|---|---|
| `admin` | `platform_admin` | 全量放行 |
| `manager` | `asset_manager_operator` + `project_manager_operator` + `dual_party_viewer` | 保持“大部分管理权限”口径 |
| `asset_manager` | `asset_manager_operator` | 资产侧读写 |
| `project_manager` | `project_manager_operator` | 项目侧读写 |
| `user` | `dual_party_viewer` | 双路径只读 |
| `viewer` | `dual_party_viewer` | 双路径只读 |
| `auditor` | `audit_viewer` | 审计/统计只读 |
| 未识别角色 | `no_data_access` | 默认拒绝，需人工补映射 |

“未识别角色”定义（强制）：
1. `role.code` 未命中上述“现有角色 -> 目标策略包”映射表，且未命中别名表。  
2. 角色来源不在迁移白名单（例如临时脚本插入、历史脏数据角色）。  
3. 同名角色但 `category` 与基线定义冲突时，按未识别处理（禁止自动放权）。

`category` 维度使用规则（强制）：
1. `category` 仅用于“推荐映射提示”，**不得**自动生效为权限映射。  
2. 推荐口径（供管理员确认，不自动应用）：
- `system` -> `platform_admin`
- `management` -> `asset_manager_operator` + `project_manager_operator`
- `business` -> `dual_party_viewer` 或按岗位选择 `asset_manager_operator`
- `read_only` -> `dual_party_viewer`
- `asset` -> `asset_manager_operator`
- `project` -> `project_manager_operator`
- `audit` -> `audit_viewer`

门禁要求：
- 迁移前产出“角色映射 dry-run 报告”（角色数、用户数、策略包命中数、未识别角色清单）。
- `未识别角色用户数 > 0` 时不得开放写流量，除非发布负责人 + 业务负责人共同签字豁免。

## 4.7 ABAC 缓存键与失效广播规范（本期落地）

缓存分层：
1. L1：进程内短 TTL 缓存（建议 3-5s）。  
2. L2：Redis 判定缓存（建议 TTL 300s）。  

缓存键规范：
1. 角色策略快照：`abac:subject:{user_id}:roles:{roles_hash}:policies`  
2. 判定结果：`abac:decision:{user_id}:{resource_type}:{resource_id}:{action}:{perspective}:{ctx_hash}`  
3. 反向索引：`abac:index:user_role:{user_id}:{role_id}`（用于精准删除）  

`roles_hash` 生成规范：
- `roles_hash = sha256(','.join(sorted(set(role_ids))))`（UTF-8，小写十六进制）。
- 对同一 `role_ids` 集合必须稳定一致；不得引入请求顺序、实例本地顺序等非确定性因素。
- 策略内容变更口径：不把“策略版本”拼入缓存键；统一依赖 `authz.role_policy.updated` 事件驱动失效，避免双轨键策略。
- 策略更新约束：策略内容变更必须通过事件链路触发失效（至少发布 `authz.policy.updated`，并按影响面补充 `authz.role_policy.updated` / `authz.user_role.updated` / `authz.user_scope.updated`）；禁止直接改表不发事件。

失效事件规范：
1. 事件类型：`authz.role_policy.updated`、`authz.user_role.updated`、`authz.policy.updated`、`authz.user_scope.updated`  
2. 事件字段：
- 通用字段：`event_id`、`occurred_at`、`operator_id`、`reason`
- `authz.role_policy.updated`：`role_id`、`affected_user_ids[]`
- `authz.user_role.updated`：`user_id`、`role_ids[]`
- `authz.user_scope.updated`：`user_id`、`scope_change_type(user_party_bindings|party_hierarchy)`、`affected_party_ids[]`
3. 消费要求：所有实例订阅同一广播通道并执行本地 + Redis 双删除。  
4. 时效目标：从事件提交成功到所有实例缓存失效 `<5s`（最终一致）。  

`hierarchy_version` 生命周期协议（本期必须）：

| 阶段 | 机制 | 说明 |
|---|---|---|
| **生成** | `party_hierarchy` 写入触发器执行 `INCR party:hierarchy_version`（Redis） | 每次层级变更递增全局版本号 |
| **传播** | `authz.user_scope.updated` 事件携带 `new_hierarchy_version` | 所有实例感知版本变更 |
| **失效** | 缓存键 `party:descendants:{party_id}:{version}` 版本变更后自动 miss | 无需显式删除旧键 |
| **冷启动** | 无版本时 fallback 到 DB 递归 CTE 查询 + 写入初始版本 | 首次启动或 Redis 丢失时自愈 |
| **存储** | Redis key `party:hierarchy_version`（全局单键） | TTL = -1（永不过期，仅递增） |

## 4.8 ABAC 策略规则示例（JSONLogic）

表达式引擎口径：
- 本节示例与运行时实现均以 JSONLogic 为唯一语义基线。
- CEL 仅作为后续扩展预留，本期不提供解析器、不纳入测试矩阵与发布门禁。
- 示例命名说明：示例对象中的 `condition` 等价于落库存储字段 `condition_expr`（见 4.2）。
- 示例简写说明：若示例中 `action` 展示为数组，仅表示同构规则的阅读简写；实际落库必须拆分为单 `action` 规则记录（见 4.2）。

create 场景执行顺序（统一口径）：
1. 先按 5.5 将请求体字段注入 `resource.*`。  
2. 再按本节规则执行 ABAC 判定。  

### 资产读取（owner 路径）
```json
{
  "resource_type": "asset",
  "action": ["read", "list"],
  "condition": {
    "in": [
      { "var": "resource.owner_party_id" },
      { "var": "subject.owner_party_ids" }
    ]
  }
}
```

### 资产读取（manager 路径）
```json
{
  "resource_type": "asset",
  "action": ["read", "list"],
  "condition": {
    "in": [
      { "var": "resource.manager_party_id" },
      { "var": "subject.manager_party_ids" }
    ]
  }
}
```

### 资产写入（仅 manager）
```json
{
  "resource_type": "asset",
  "action": ["create", "update", "delete"],
  "condition": {
    "in": [
      { "var": "resource.manager_party_id" },
      { "var": "subject.manager_party_ids" }
    ]
  }
}
```

### 项目读写（仅 manager 路径）
```json
{
  "resource_type": "project",
  "action": ["read", "list", "create", "update", "delete"],
  "condition": {
    "in": [
      { "var": "resource.manager_party_id" },
      { "var": "subject.manager_party_ids" }
    ]
  }
}
```

说明：
- `create` 场景中的 `resource.*` 必须按 5.5 的固定映射注入判定上下文。  
- `headquarters` 不需要额外写规则；其展开结果仅并入 `subject.manager_party_ids`。  

---

## 5. API / Schema / Type 变更清单

## 5.1 后端 Schema（破坏性）

1. `AssetCreate/Update/Response`
- 移除：`organization_id`,`ownership_id`,`management_entity`
- 新增：`owner_party_id`,`manager_party_id`

2. `RentContractCreate/Update/Response`
- `ownership_id -> owner_party_id`
- 新增：`manager_party_id`,`tenant_party_id`

3. `Project*`
- 统一为 `manager_party_id`（必填），不引入 `owner_party_id`

4. `ProjectAssetRelation*`
- 新增 `project_assets` 关系模型与接口（绑定/解绑/历史查询）
- 项目创建接口不强制要求初始资产集合

5. `PropertyCertificate*`
- 统一改为 `party_id` 或证照关系表

6. `RentLedger*`
- `ownership_id → owner_party_id`

7. 新增鉴权接口
- `POST /api/v1/authz/check`（内部服务与调试使用）
- 入参：`action + resource + context`（默认）
- `subject` 仅允许内部服务账号透传；用户态请求一律以后端从 token 解析的 subject 为准（忽略/拒绝外部传入 subject）
- 出参：`allow/deny + matched_policy`

8. 新增角色数据策略配置接口（管理面）
- `GET /api/v1/auth/roles/{role_id}/data-policies`
- `PUT /api/v1/auth/roles/{role_id}/data-policies`
- `GET /api/v1/auth/data-policies/templates`
- 说明：管理员按角色挂载策略包，不直接编辑底层表达式

9. 登录态能力清单接口（前端消费）
- `GET /api/v1/auth/me/capabilities`
- 出参：`resource + action + perspective + data_scope` 能力清单
- 说明：前端页面显隐和按钮可用性以能力清单为准，不在页面层频繁调用 `/authz/check`
- 最小 Schema（本期固定）：
```json
{
  "version": "2026-02-17.v1",
  "generated_at": "2026-02-17T00:00:00Z",
  "capabilities": [
    {
      "resource": "asset",
      "actions": ["read", "list", "update"],
      "perspectives": ["owner", "manager"],
      "data_scope": {
        "owner_party_ids": ["uuid"],
        "manager_party_ids": ["uuid"]
      }
    }
  ]
}
```
- 兼容约束：前端按 `version` 解析；后端新增字段必须向后兼容，不得破坏既有枚举语义。

## 5.2 前端 Type/Service

1. `frontend/src/types/*` 全面替换旧主体字段。  
2. `frontend/src/services/*` 请求参数与响应字段同步更新。  
3. 登录成功与 token refresh 后重拉 `capabilities`，前端基于能力清单做视角/按钮控制。  
4. 前端 `capabilities` 为会话级快照；结构定义以 5.1 为准，会话语义以第 10 节为准。  
5. 资源列表与详情仍由后端 ABAC 做最终裁决（前端能力清单仅做 UI 预裁剪）。  
6. 前端关键写操作若收到后端 `403/404`（权限变化导致），需提示“权限已更新，请刷新会话”并触发一次静默 refresh。  
7. 角色管理页新增“数据策略包配置”区域。  
8. 无资产项目展示约定：显示“待补绑定”标签；面积相关统计显示 `N/A`；不阻断项目基础信息查询。
9. 静默 refresh 防风暴约束（本期必须）：
- 同一会话最小触发间隔 `>= 30s`（cooldown）。
- 并发失败请求采用 single-flight（同一时刻仅允许一个 refresh 请求在途）。
- 单次失败波次最多触发 `1` 次静默 refresh，仍失败则提示用户手动刷新/重新登录。
10. 后端建议在权限变化导致的拒绝中返回 `X-Authz-Stale: true` 响应头；前端仅在命中该信号或首次权限拒绝时触发静默 refresh。
11. 触发与抑制行为需写入前端诊断日志（含 `request_id`、触发原因、是否命中 cooldown），用于排查 refresh 风暴。
12. `usePermission` Hook 重构为 `useCapabilities`：
- 废弃 `canAccessOrganization(organizationId)` 对比逻辑
- 新增 `canPerform(action, resourceType, perspective?)` 基于能力清单判定
- 新增 `hasPartyAccess(partyId, relationType)` 替代旧组织 ID 比较
- 接口规范：`capabilities` 清单结构为 `{ resource, action, perspective, data_scope }[]`，与 §5.1 的 `GET /auth/me/capabilities` 出参对齐

## 5.3 外部调用方切换要求（破坏性变更治理）

1. 本期不保留旧接口兼容层，`/api/v1/*` 字段变更按同窗口生效。  
2. 发布前必须完成调用方盘点（前端、脚本、BI 报表、第三方集成），形成签收清单。  
3. 盘点结果要求：
- 对每个调用方给出负责人、升级版本、联调状态、回退联系人。
- 未签收调用方不得进入发布窗口。  
4. 发布窗口前 24h 冻结 API 契约，不再新增字段语义变更。  

## 5.4 登录时权限展开逻辑（后端实现约束）

执行步骤（登录与 token refresh 一致）：
1. 查询 `user_party_bindings` 当前有效绑定。  
2. 按 `relation_type` 分桶：`owner`、`manager`、`headquarters`。  
3. `headquarters` 调用 `get_descendant_parties` 展开子孙，并将“自身 + 子孙”仅并入 `manager_party_ids`。  
4. 生成去重后的 `owner_party_ids / manager_party_ids / headquarters_party_ids` 并写入判定上下文缓存。  

说明：
- 判定上下文字段定义与展开语义以 4.3 为准。  
- 当 `user_party_bindings` 或 `party_hierarchy` 发生变更时，必须触发 `authz.user_scope.updated` 失效事件，确保上下文缓存 `<5s` 收敛。  

`headquarters` 展开性能约束（本期必须）：
1. `get_descendant_parties` 必须支持批量输入（一次展开多个 `headquarters_party_id`），避免 N 次递归查询。  
2. 子树展开结果必须进入 L2 缓存：`party:descendants:{party_id}:{hierarchy_version}`（TTL 建议 300s，与 4.7 一致）。  
3. `party_hierarchy` 变更时递增 `hierarchy_version` 并触发 `authz.user_scope.updated`，保证旧缓存自动失效。  
4. 登录阶段展开性能目标：
- 单个 `headquarters` + 500 子节点：缓存命中 P95 `<50ms`
- 冷启动（缓存未命中）P95 `<200ms`
5. 预热要求：在发布窗口和高峰前，按活跃 `headquarters` TopN 预热子树缓存；预热失败需告警但不得放宽鉴权。

## 5.5 创建接口 ABAC 资源注入规范（强制）

1. 资产创建：`resource.owner_party_id = body.owner_party_id`，`resource.manager_party_id = body.manager_party_id`。  
2. 合同创建：`resource.owner_party_id = body.owner_party_id`，`resource.manager_party_id = body.manager_party_id`，`resource.tenant_party_id = body.tenant_party_id`。  
3. 项目创建：`resource.manager_party_id = body.manager_party_id`。  
4. 字段缺失、空字符串或 `NULL` 时一律 fail-closed（deny），不得回退到默认组织/默认角色推断。  
   - 必填字段：`owner_party_id`、`manager_party_id`（创建资产/合同）与 `manager_party_id`（创建项目）必须 fail-closed。  
   - 选填字段：`tenant_party_id` 允许 `NULL`，但不得在 ABAC 组件中被替换成默认值。  
5. 禁止各接口自定义注入逻辑；由统一鉴权组件负责映射与校验。  

---

## 5.6 数据隔离层替代方案（TenantFilter → PartyFilter）

> 本节解决核心数据隔离机制的替换问题。现有 `TenantFilter` 硬编码 `organization_ids`，删除 `organization_id` 列后将完全失效。

### 现状
- `TenantFilter`（`query_builder.py`）：frozen dataclass，`organization_ids: list[TenantIdentifier]`
- `_apply_tenant_filter`：对 `model.organization_id` 列做 `IN` 过滤
- 被 **16+ 个文件**（含 CRUD/Service/API 层）使用（CRUD 层：`asset.py`, `project.py`, `property_certificate.py`, `rbac.py`, `base.py` 等 10 个文件；Service/API 层另有 6+ 个文件）

### 替代方案

`PartyFilter`（新 dataclass）：
```python
@dataclass(frozen=True)
class PartyFilter:
    """主体过滤上下文（Party 维度）"""
    party_ids: list[str]                       # 来源：user_party_bindings 展开结果
    filter_mode: Literal["owner", "manager", "any"] = "any"
    mode: Literal["strict"] = "strict"
    allow_null: bool = False
```

`_apply_party_filter`（新方法）：
```python
def _apply_party_filter(self, query, model):
    if self.filter_mode == "owner" and hasattr(model, "owner_party_id"):
        return query.where(model.owner_party_id.in_(self.party_ids))
    elif self.filter_mode == "manager" and hasattr(model, "manager_party_id"):
        return query.where(model.manager_party_id.in_(self.party_ids))
    else:  # "any"
        conditions = []
        if hasattr(model, "owner_party_id"):
            conditions.append(model.owner_party_id.in_(self.party_ids))
        if hasattr(model, "manager_party_id"):
            conditions.append(model.manager_party_id.in_(self.party_ids))
        return query.where(or_(*conditions)) if conditions else query
```

### `field_whitelist.py` 批量更新

| 操作 | 详细 |
|---|---|
| 字段替换（9 处） | `organization_id → owner_party_id/manager_party_id`（5 处）；`ownership_id → owner_party_id`（3 处）；`ownership_entity → manager_party_id`（1 处） |
| 类删除（2 个） | `OrganizationWhitelist`、`OwnershipWhitelist` 整个类删除 |

### `management_entity` 自由文本映射策略

`Asset.management_entity` 和 `Project.management_entity` 为 `String(200)` 自由文本，无法直接映射为 `manager_party_id`。迁移策略：
1. 模糊匹配 `parties.name`：自动映射匹配结果写入 `manager_party_id`
2. 未匹配项进入人工清单（类似 `project_assets` 处置流程）
3. 迁移顺序：先回填 `manager_party_id`，再删除 `management_entity` 列

---

## 6. 一次切换迁移方案（Runbook）

## 6.1 上线前准备

1. 生产快照全量演练 >= 2 次。  
2. PostgreSQL 前置能力校验（No-Go）：
- 安装并校验 `btree_gist` 扩展（排斥约束依赖）。
- 排斥约束涉及列/操作符在目标库可用，演练环境与生产版本一致。
- 执行计划校验：对排斥约束相关写入与关键查询执行 `EXPLAIN (ANALYZE, BUFFERS)`；不得出现不可接受的长期全表扫描，若出现退化需按查询模式补充索引或调整 SQL 后再放流。
3. 生成映射表：
- `org_to_party_map`
- `ownership_to_party_map`
4. 修复脏数据：
- 代码重复
- 空 owner/manager
- 合同无权属主体
5. Party 映射与去重规则（强制）：
- `Organization -> Party`：优先按 `external_ref` / 统一标识 / `code` 映射，禁止仅按名称自动合并。
- `Ownership -> Party` 去重优先级：统一标识（如统一社会信用代码） > 注册号 + 规范化名称 > `code`。
- 仅“同名”不得自动合并；命中冲突一律进入人工清单并保留证据链。
6. 用户-Party 绑定数据校验：
- 有效用户 `user_party_bindings` 主绑定冲突（同 relation_type 多主绑定）必须清零
- `headquarters` 绑定对应 Party 必须存在于 `parties.id`；允许其在 `party_hierarchy` 中无子节点（仅展开自身）
7. `user_party_bindings` 回填来源定义与决策树（强制）：
- “业务明确映射”定义：经业务 owner 签字的映射源，来源仅限
  `migration_user_party_manual_map`（人工确认表/CSV）或可追溯业务关系清单（含证据链与审核人）。
- 回填优先级：`业务明确映射 > roles.organization_id > users.default_organization_id > 人工清单`。
- 兼容约定：若目标库无 `users.default_organization_id` 字段（历史版本差异），该来源自动跳过，不得因缺列中断迁移。
- 决策树（伪代码）：
```python
for user in active_users:
    bindings = []

    explicit = load_signed_business_mapping(user.id)
    if explicit.exists():
        bindings += explicit.to_bindings()  # 允许 owner/manager/headquarters
    elif user.roles.with_org_id().exists():
        bindings += to_manager_bindings(user.roles.org_ids())
    elif hasattr(user, "default_organization_id") and user.default_organization_id is not None:
        bindings += to_manager_binding(user.default_organization_id)
    else:
        add_manual_queue(user.id, reason="NO_BINDING_SOURCE")
        continue

    if has_conflict(bindings):
        add_manual_queue(user.id, reason="SOURCE_CONFLICT")
        continue

    persist_bindings(bindings)
```
8. 回填冲突处理规则（强制）：
- 不同来源给出不同 `party_id` 且同 `relation_type` 冲突时，禁止自动合并，必须进入人工清单。
- 自动推导来源（`roles.organization_id` / `default_organization_id`）只允许生成 `manager` 绑定，禁止推导 `owner/headquarters`。
9. 项目数据校验：
- `projects.manager_party_id` 不得为空
- 历史项目资产关联（若有）需可回填到 `project_assets`
10. 发布前强校验：
- `abac_policy_subjects` 必须为空表
- 若非空，阻断发布窗口并先完成人工处置
11. 全局依赖排查（删表门禁）：
- 代码/脚本/SQL 全局检索 `abac_policy_subjects|policy_subjects`，形成证据清单（文件 + 行号 + 处理结论）
- 数据库对象扫描（视图/函数/触发器）不得再引用 `abac_policy_subjects`
- 任何未处置引用项均为 No-Go
12. 生产副本演练输出“不可自动迁移统计”：
- `owner_party_id / manager_party_id` 无法映射数量
- `user_party_bindings` 无法自动映射数量（从 `users.default_organization_id`、`roles.organization_id` 推导）
- 合同主体无法映射数量
- `project_assets` 无法识别数量
- 以上统计需在正式窗口前清零，或有双负责人（技术 + 业务）签字豁免
13. 角色映射演练：
- 产出“现有角色 -> 策略包” dry-run 报告
- `未识别角色用户数 > 0` 视为 No-Go
14. 执行 5.3 外部调用方签收核验，未签收不得进入发布窗口。
15. `project_assets` 人工清单预案：
- 明确责任人（迁移组负责人 + 业务数据 owner）
- 明确时限（窗口内清零，未清零不开放写流量）

### P0 Blocker Gate（全部关闭后方可进入发布窗口）

| # | Blocker | 关闭标准 |
|---|---|---|
| BG-1 | PartyFilter 替代方案落地并通过回归 | `_apply_party_filter` 覆盖所有 16+ 文件（含 CRUD/Service/API 层），无 `organization_id` 遍历引用 |
| BG-2 | `roles.organization_id` 迁移完成 | FK 替换/删除 + `scope` 值域更新 + 相关 whitelist 同步 |
| BG-3 | 权限判定路径统一为 ABAC | `PermissionGrant`/`ResourcePermission` 确认无运行时读取 + 标记 deprecated |
| BG-4 | 台账链路 `ownership_id` 全清 | `RentLedger.ownership_id` 改为 `owner_party_id` + `ledger_service.py` 业务逻辑 + `RentContract.__init__` 验证 |

## 6.2 发布窗口执行

窗口时长估算基线（必须在演练中实测修正）：
| 阶段 | 小规模（S） | 中规模（M） | 大规模（L） | 说明 |
|---|---:|---:|---:|---|
| DDL + 索引/约束 | 5-10 分钟 | 10-20 分钟 | 20-40 分钟 | 含新表、约束、删表 |
| 数据回填（Party + 业务表 + bindings） | 15-30 分钟 | 30-90 分钟 | 90-180 分钟 | 与数据量线性相关 |
| 门禁验证（对账/权限/冒烟） | 20-30 分钟 | 30-45 分钟 | 45-60 分钟 | 含人工抽检 |
| 总窗口建议（含缓冲） | 90 分钟 | 180 分钟 | 360 分钟 | 建议额外预留 30% 缓冲 |

数据量分档参考（可按生产实际调整）：
- S：资产 `<100k`、合同 `<50k`、项目 `<10k`
- M：资产 `100k-500k`、合同 `50k-200k`、项目 `10k-50k`
- L：资产 `>500k` 或合同 `>200k` 或项目 `>50k`

No-Go 规则：
1. 生产副本演练总时长 `> 目标窗口 * 0.8` 且无并行优化方案时，不得进入正式窗口。  
2. 任一关键阶段耗时较演练基线劣化 `>30%`，需发布负责人确认后才能继续。

1. 进入维护窗口，并在网关层阻断**全部业务读写流量**（含 API/批处理/导入/报表查询）；仅保留健康检查与发布运维最小通道。  
2. 确认“无在途事务 + 无待执行任务队列 + 旧应用实例已摘流”后再执行 DDL。  
3. 执行 DDL：Party/Role/ABAC 新表 + `abac_role_policies`，并删除 `abac_policy_subjects`。  
4. 全量迁移与回填：
- Organization -> Party(`organization`)
- Ownership -> Party(`legal_entity`)
- 业务表旧 FK -> 新 party_id
- `projects` 仅回填 `manager_party_id`（不生成 `owner_party_id`）
- 回填 `project_assets`（从现有可识别项目-资产关系迁移）
- 生成 `project_assets` 人工清单（包含 `project_id`、候选 `asset_id`、失败原因、处理人、处理状态）
- 顺序要求：先执行“可自动回填”部分，再对“无法自动回填”生成并冻结人工清单。
- 回填 `user_party_bindings`（优先来源：业务明确映射 > `roles.organization_id` > `users.default_organization_id`）
- 回填 role bindings
- 回填角色策略绑定（默认包）
- 写入经营方历史首条记录
5. 部署新后端（角色入口 + ABAC 判定生效）+ 新前端（新字段），并完成基础冒烟。  
6. 同一窗口内物理删除旧业务字段（不延后版本删除）：
- `assets.organization_id / ownership_id / management_entity / project_id`
- `rent_contracts.ownership_id`
- `rent_ledger.ownership_id`
- `projects.organization_id` 及旧管理字符串字段
- `property_certificates.organization_id`
- `roles.organization_id`
7. 同一窗口内物理删除旧关联表：
- `project_ownership_relations`
- `property_owners` + `property_certificate_owners`
8. 执行门禁验证（对账 + 权限 + 性能 + 外部调用方冒烟）。  
9. 仅当门禁全部通过且 `project_assets` 人工清单清零（或签字豁免）后，恢复业务流量。
10. 任一门禁失败：保持维护窗口并执行双回滚（应用 + DB）。

## 6.3 发布后收敛

1. 旧逻辑确认已下线（无兼容分支）  
2. 观察期仅保留监控与审计，不再做旧字段清理动作（已在窗口内物理删除）  
3. 发布后公告中明确：前端 `capabilities` 为会话级快照（详见第 10 节）。

## 6.4 `project_assets` 人工清单处置规则

1. 清单字段最少包含：`project_id`、`project_name`、`candidate_assets`、`failure_reason`、`owner`、`status`、`resolved_at`。  
2. 状态机：`pending -> in_progress -> resolved/rejected`，禁止跳过中间状态。  
3. `rejected` 必须填写原因并由业务负责人确认。  
4. 导出格式（强制双轨）：
- `CSV`：用于业务批量处理与签字流转（UTF-8 BOM）。
- `JSON`：用于程序复核与审计归档（保留原始候选集与处置轨迹）。
5. 验收签字流程（强制）：
- 迁移组负责人确认技术处置完成。
- 业务数据 owner 确认业务语义正确。
- 发布负责人确认“清零”或“豁免范围”后方可进入放流步骤。
6. 未清零业务影响（必须明确）：
- 无签字豁免：不得恢复业务写流量（维持维护窗口）。
- 有签字豁免：仅允许恢复不受影响模块写流量；受影响 `project_id` 的 `project_assets` 写操作继续封禁，直到清单关闭。
7. 清单关闭后必须归档到发布证据包，保存不少于 180 天。

---

## 7. 测试与验收

## 7.1 迁移对账（硬门禁）

1. 主体数量对账（Organization/Ownership -> Party）  
2. `user_party_bindings` 对账 100%（用户绑定数、主绑定、有效期）。  
3. 资产 owner/manager 对账 100%  
4. 合同主体关系对账 100%  
5. 项目 `manager_party_id` 对账 100%  
6. 项目-资产关系（`project_assets`）对账 100%  
7. 产权证主体关系对账 100%  
8. `certificate_party_relations` 约束验证通过（时间区间、主产权方唯一、比例范围）。  
9. `abac_policy_subjects` 依赖扫描报告为“零未处置引用”。  
10. 角色映射对账 100%（现有活跃角色均命中策略包映射）。  
11. `project_assets` 人工清单清零或签字豁免完成。

## 7.2 权限回归

1. 新用户 deny by default。  
2. owner 路径可见性正确。  
3. manager 路径可见性正确。  
4. 合同写入仅 manager 关系命中可通过。  
5. 角色/绑定变更后，权限与上下文缓存在 4.7 规定时限内失效（详细验收见 7.5）。  
6. 项目读写仅 manager 路径命中可通过。  
7. `headquarters` 绑定用户可覆盖其绑定 Party 子树的 manager 路径；owner 路径需显式 `owner` 绑定或独立策略。  
8. token refresh 后能力清单与最新角色策略保持一致（遵循 `<5s` 最终一致口径）。  
9. 前端会话未 refresh 前能力清单允许短暂陈旧，但不得绕过后端 ABAC。  
10. 无权限详情 404 行为一致。
11. 前端静默 refresh 防风暴策略生效：single-flight、30s cooldown、失败后不重复风暴触发。
12. `PartyFilter` 数据隔离全链路回归：各 CRUD 模块租户隔离行为与旧 `TenantFilter` 等价。
13. `PermissionGrant`/`ResourcePermission` 确认无运行时引用（grep 全库 + 冒烟测试覆盖）。

## 7.3 业务回归

1. 资产/合同/项目/产权证 CRUD 全链路。  
2. 项目资产绑定/解绑与历史查询链路可用（支持“先创建项目后补绑定资产”）。  
3. 导入导出、统计报表、筛选分页。  
4. 前端关键页面冒烟通过。  
5. 无资产项目展示符合 5.2 约定。

## 7.4 性能门槛

1. 关键列表查询 P95 不劣于基线 10% 以上。  
2. ABAC 判定 P95 达标（建议 <20ms，含缓存）。  
3. 角色变更后权限缓存失效延迟可控（建议 <5s）。
4. `headquarters` 子树展开满足 5.4 约束：500 子节点缓存命中 P95 `<50ms`，冷启动 P95 `<200ms`。

## 7.5 权限缓存一致性验收

1. 角色策略变更后，按 `user_id + role_id` 精准删除缓存。  
2. `user_party_bindings / party_hierarchy` 变更后，按 `user_id` 精准删除用户上下文缓存。  
3. 变更事件广播后，多实例节点权限缓存在目标时限内完成失效。  
4. 缓存键命名、反向索引键、事件字段与 4.7 节规范一致。  
5. 同一 `user_id` + 同一角色集合在多实例下生成相同 `roles_hash`。  
6. 旧缓存命中不应超过时限窗口。
7. 事件发布后 5 秒内，对同一 `resource+action` 重放判定请求应返回更新后的结果（或至少不再命中旧策略缓存）。
8. 验证 Outbox 可靠性：制造投递失败后，重试/重放可恢复，且最终完成缓存失效。
9. 验证幂等性：同一 `event_id` 重复投递不应导致重复副作用或异常。

## 7.6 组织层级防环验收

1. 自环写入（`parent_party_id == child_party_id`）必须被 DB 拒绝。  
2. 三节点环路写入（A->B->C 后 C->A）必须被 DB 触发器拒绝。  
3. 复杂层级（>5 层）新增边性能满足基线，不出现明显退化。  
4. 服务层错误码与 DB 错误码语义一致（统一返回循环依赖错误）。

## 7.7 审计与合规验收（强制项）

说明：
- 本节为发布验收强制项。  
- 9.1 节为推荐增强项，不作为默认上线硬门禁（除非项目/监管另有要求）。

1. 角色策略包变更（`abac_role_policies`）必须写入审计日志。  
2. 用户主体绑定变更（`user_party_bindings` 新增/修改/删除）必须写入审计日志。  
3. 审计日志字段完整：`operator_id`、`occurred_at`、`target_type`、`target_id`、`before`、`after`、`reason`、`request_id`、`source_ip`。  
4. 审计查询可按用户、角色、主体、时间范围检索，并支持导出。  
5. 人工清单处置与回填冲突人工修复动作必须入审计（建议 `target_type=user_party_binding_manual_fix`），禁止线下补数绕过审计通道。

---

## 8. 回滚预案

1. 切换前做物理备份 + 逻辑快照。  
2. 回滚触发条件（任一）：
- 对账失败
- 权限关键用例失败
- 主流程不可用
3. 回滚步骤：
- 重新进入只读 + 写请求阻断（防止回滚过程中继续产生新写入）
- **应用与数据库必须一起回滚**（禁止单边回滚）
- 回退应用版本到切换前版本
- 数据库恢复到切换前快照
- 若发现窗口期间写流量泄漏，必须生成“泄漏写入差异清单”并人工补偿后再开放流量
- 导出失败差异清单

---

## 9. 实施任务拆解（可直接派工）

1. 数据库组：新表 + 约束 + Alembic + 回滚脚本 + `party_hierarchy` 防环触发器。  
2. 迁移组：映射、回填、对账工具、`abac_policy_subjects` 删表迁移、`project_assets` 关系回填、`user_party_bindings` 回填、`management_entity` 自由文本映射、人工清单闭环。  
3. 鉴权组：ABAC 引擎（含 JSONLogic 依赖集成） + `abac_role_policies` + `/authz/check` + 登录/refresh 上下文展开 + 缓存键标准化 + 精准删除 + 失效事件广播 + `OrganizationPermissionService`/`OrganizationPermissionChecker` 废弃与替代。  
4. 权限管理组：角色数据策略包后台配置、既有角色映射 dry-run、审计日志（角色策略包与 `user_party_bindings` 变更全量留痕）。  
5. 业务后端组：asset/contract/project/certificate 全域字段替换 + `project_assets` 关系服务 + `certificate_party_relations` 落地 + `ledger_service.py` 台账链路修改 + `RentContract.__init__` 构造函数修改 + `field_whitelist.py` 批量更新（9 字段 + 2 类） + Excel 导入导出模板适配。  
6. 前端组：类型、服务、页面联调、角色策略包配置页、能力清单陈旧态交互提示 + `usePermission` → `useCapabilities` 重构 + `ownership_id` 33 文件替换。  
7. 测试组：迁移回归、角色到策略链路回归、`headquarters` 展开回归、防环专项、性能基准 + `PartyFilter` 数据隔离回归。  
8. 发布组：窗口执行、外部调用方签收核验、回滚值守。

各组交付物要求（强制）：
- 每组必须产出**“受影响文件冻结清单”**（模块-文件-责任人-状态），在发布前冲刺阶段冻结
- 清单估算：后端 ~50+ 文件，前端 ~51+ 文件（基于评审发现的 `organization_id` 50+ 、`ownership_id` 34+ 影响分析）

## 9.1 审计与合规（推荐增强）

说明：
- 本节为增强建议，默认不作为发布硬门禁；如项目方或监管要求，可升级为强制项。

事件范围：
1. `authz.role_policy.updated`（角色策略包变更）。  
2. `authz.user_party_binding.created` / `updated` / `deleted`（用户主体绑定变更）。  

最小审计字段：
1. `event_id`、`occurred_at`、`operator_id`、`source_ip`、`request_id`。  
2. `target_type`、`target_id`、`action`。  
3. `before`、`after`、`reason`（支持审计追溯与差异比对）。  

合规要求（推荐）：
1. 审计日志采用追加写（append-only），禁止覆盖更新。  
2. 审计日志默认保留 >= 180 天。  
3. 提供按“谁/何时/改了什么”的查询与导出能力（CSV/JSON）。  

## 9.2 发布前责任矩阵（RACI，推荐）

| 工作项 | R（负责执行） | A（最终负责） | C（协作） | I（知会） |
|---|---|---|---|---|
| DDL/迁移脚本与回滚脚本 | 数据库组 | 发布负责人 | 迁移组、鉴权组 | 业务负责人 |
| 数据映射回填与人工清单清零 | 迁移组 | 迁移负责人 | 业务数据 owner、数据库组 | 发布负责人 |
| ABAC 引擎与缓存失效链路 | 鉴权组 | 鉴权负责人 | 权限管理组、平台运维 | 测试组 |
| 角色策略包映射与后台配置 | 权限管理组 | 权限负责人 | 鉴权组、业务负责人 | 发布负责人 |
| 前端能力清单与交互收敛 | 前端组 | 前端负责人 | 鉴权组、业务后端组 | 测试组 |
| 对账/回归/性能验收与放流决策 | 测试组 | 发布负责人 | 全体实施组 | 业务负责人 |

---

## 10. 重要假设与默认值

1. 不保留旧接口兼容层。  
2. 不做双写。  
3. Party 仅含组织与外部法人。  
4. 组织层级主数据迁移到 `party_hierarchy`。  
5. 外部产权方可仅作为 Party 存在，不要求必须有系统用户账号。  
6. 项目创建本期不强制要求已绑定资产（后续可再升级为硬约束）。  
7. 前端 `capabilities` 为会话级快照；权限实时真值以后端 ABAC 判定为准。  
   - 权威口径：会话与 `capabilities` 语义以本节为准；其它章节如有表述差异，以本节为准。  
8. 有效业务用户默认要求具备 `manager/headquarters` 有效绑定；`no_data_access` 角色用户可例外。  
   - `owner`-only 用户允许存在，但仅可授予 owner 路径只读策略，不得授予写策略。  
9. 以数据正确性为唯一上线门禁优先级。

---

## 11. 文档历史

| 日期 | 版本 | 变更内容 | 作者 |
|---|---|---|---|
| 2026-02-16 | 1.0 | 初始版 | Claude & yellowUp |
| 2026-02-16 | 2.0 | Party-Role 一次切换（纯 ABAC、全域替换）实施方案冻结 | Codex |
| 2026-02-16 | 2.1 | 权限方案调整为“角色配置入口 + ABAC 执行判定”，补齐角色策略包治理与验收 | Codex |
| 2026-02-16 | 2.2 | 收口5项澄清：仅角色入口、业务表事实源、登录能力清单、强制双回滚、精准失效+通知 | Codex |
| 2026-02-16 | 2.3 | 本期删除 `abac_policy_subjects` 表结构，权限主体链路统一为角色入口 | Codex |
| 2026-02-16 | 2.4 | 项目模型收口为仅 `manager_party_id` 必填；能力清单改为登录+refresh 重拉 | Codex |
| 2026-02-16 | 2.5 | 引入 `project_assets` 关系表与历史能力，明确项目创建暂不强制绑定资产 | Codex |
| 2026-02-17 | 2.6 | 补齐实施风险控制：证照关系表 schema、防环触发器、角色映射规则、删表依赖排查、能力清单会话级口径、人工清单治理、ABAC 缓存键/失效规范与外部调用方切换门禁 | Codex |
| 2026-02-17 | 2.7 | 补齐用户主体上下文：新增 `user_party_bindings`、判定上下文 owner/manager/headquarters 拆分、ABAC 规则示例、登录/refresh 上下文展开逻辑与迁移回填/验收要求 | Codex |
| 2026-02-17 | 2.8 | 收紧实现口径：主绑定部分唯一索引实现、headquarters 展开语义（自身+子孙）、`roles_hash` 稳定算法与创建接口 ABAC 资源注入 fail-closed 规范 | Codex |
| 2026-02-17 | 2.9 | 增加文首快速导航目录（一级/二级锚点）与审计合规增强：补充 9.1 审计规范、任务拆解审计职责、7.7 审计验收项 | Codex |
| 2026-02-17 | 3.0 | 文档去重压缩：合并 5.3/6.1 外部签收条目，精简 5.4 与 4.3 重复描述，统一无资产项目展示口径，收敛 capabilities 与缓存验收到单一权威章节引用 | Codex |
| 2026-02-17 | 3.1 | 修复评审问题：统一动作枚举、收口 `party_hierarchy` 邻接表语义、明确 `/authz/check` subject 信任边界、修正 `tenant_party_id` 可空与 fail-closed 冲突、补齐排斥约束 `btree_gist` 前置、发布窗口改为全量维护流量切断、`headquarters` 叶子节点校验放宽、补充 `scope_type` 一致性约束与权限回归编号修正 | Codex |
| 2026-02-17 | 3.2 | 补齐实施闭环：明确 `user_party_bindings` 回填来源定义与决策树、补充 `headquarters` 展开性能与缓存预热约束、新增迁移窗口时长估算与 No-Go 门禁、完善 `project_assets` 人工清单生命周期、增加前端 capabilities 静默 refresh 防风暴规范、细化“未识别角色”定义与 `category` 推荐映射规则（仍 deny-by-default） | Codex |
| 2026-02-17 | 3.3 | 补齐审阅遗留细节：显式化 `party_contacts` partial unique、明确 `scope_id` 类型与 `global` 可空约束、补充证照“同一时刻唯一主产权方”语义、增加 `default_organization_id` 缺列兼容、澄清 `roles_hash` 不含策略版本（仅事件失效）、补充 7.5 的 `<5s` 可验证用例，并明确 7.7（强制）与 9.1（推荐）边界 | Codex |
| 2026-02-17 | 3.4 | 修复复核遗留：TOC 补齐 7.7 锚点、`party_contacts.is_primary` 部分唯一索引改为强制实现口径、`user_party_bindings` 回填伪代码补充 `default_organization_id` 字段存在性判断，避免照抄导致缺列错误 | Codex |
| 2026-02-18 | 3.5 | 合并评审补丁：新增 Blocker Gate(C1-C4)、既有权限表处置(C3)、台账/角色/关联表迁移补齐(C2/C4/C5/C6/C7)、PartyFilter 替代(C1)、hierarchy_version 生命周期(R5)、ID 类型冻结(R4)、useCapabilities 规范(S4)、文件冻结清单要求(S1)、management_entity 映射策略(R7)、Excel 导入导出任务(S5) | Antigravity |
| 2026-02-18 | 3.6 | 重审修订：显式列出 Project.ownership_entity 删除与迁移策略；新增 Asset.project_name 去规范化处置；补齐 tenant_party_id 迁移口径（本期选填不自动映射）；修正 PermissionGrant 方法计数(11→09)；修正 TenantFilter 文件范围描述；修正 §3.1/§4.1 heading 层级 | Antigravity |
| 2026-02-18 | 3.7 | 语义收窄与实施增强：`headquarters` 展开结果仅并入 `manager_party_ids`（不再并入 `owner_party_ids`）；`parties` 新增 `external_ref` + `code` 治理口径 + 匹配优先级；`party_role_bindings` 本期定位明确为非实时 ABAC；`abac_policy_rules.action` 收为单值枚举 + 多动作拆单落库；`condition_expr` 本期唯一引擎 JSONLogic（CEL 后续预留）；新增 capabilities 最小 Schema 与版本兼容约束；新增 §9.2 RACI 发布责任矩阵；§4.4 可观测性要求；§4.7 策略更新约束；§6.1 Party 去重规则 + EXPLAIN 校验 + 步骤重编号；§7.5 Outbox/幂等验收；§7.7 人工清单审计；§10 capabilities 权威口径 | yellowUp + Antigravity |
