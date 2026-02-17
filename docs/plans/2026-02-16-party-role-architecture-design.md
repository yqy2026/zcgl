# 组织架构与资产权属关系设计（Party-Role 一次切换版）

**文档类型**: 技术设计文档  
**创建日期**: 2026-02-16  
**最新更新**: 2026-02-16  
**状态**: 待实施（方案冻结）  
**作者**: Codex

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

---

## 3. 目标数据模型

## 3.1 Party 主体层

### `parties`
- `id` UUID PK  
- `party_type` ENUM(`organization`,`legal_entity`)  
- `name`  
- `code`  
- `status`  
- `metadata` JSONB  
- `created_at`, `updated_at`

约束：
- `UNIQUE(party_type, code)`

### `party_hierarchy`
- `id` UUID PK  
- `parent_party_id` FK -> `parties.id`  
- `child_party_id` FK -> `parties.id`  
- `depth`  
- `path_snapshot`  
- `created_at`, `updated_at`

约束：
- `UNIQUE(parent_party_id, child_party_id)`  
- 禁止环（服务层校验 + DB 约束/触发器）

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
- `scope_id`  
- `valid_from`, `valid_to`  
- `attributes` JSONB  
- `created_at`, `updated_at`

约束：
- 区间合法：`valid_to IS NULL OR valid_to >= valid_from`  
- 同主体同角色同资源时间段不重叠（应用层 + 约束）

---

## 3.3 业务表字段替换（公共接口影响）

### 资产 `assets`
- 删除：`organization_id`, `ownership_id`, `management_entity`
- 新增：`owner_party_id` NOT NULL, `manager_party_id` NOT NULL
- 保留：`management_start_date`, `management_end_date`, `management_agreement`

### 合同 `rent_contracts`
- 删除：`ownership_id`
- 新增：`owner_party_id` NOT NULL, `manager_party_id` NOT NULL, `tenant_party_id` NULL

### 项目 `projects`
- 删除：`organization_id`、旧管理字符串字段
- 新增：`manager_party_id` NOT NULL
- 说明：项目仅代表运营管理归集单元，不设置 `owner_party_id`；项目下资产可关联多个不同产权方

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

### 历史表
新增 `asset_management_history`：
- `asset_id`, `manager_party_id`, `start_date`, `end_date`, `agreement`, `change_reason`, `changed_by`

---

## 4. 权限模型（角色入口 + ABAC 执行）

## 4.1 管理面：角色绑定策略（管理员视角）

### 复用现有 RBAC 表
- `roles`
- `user_role_assignments`

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
- `resource_type`, `action`
- `condition_expr`（JSONLogic / CEL）
- `field_mask`（可选）

本期收口约束：
- `abac_policy_subjects` 表结构本期直接删除。  
- 策略主体来源统一为“用户 -> 角色 -> `abac_role_policies` -> `abac_policies`”链路。

---

## 4.3 判定上下文
- Subject: `user_id`, `user_party_ids`, `user_tags`
- Role: `role_ids`, `role_scope(scope/scope_id/context)`
- Resource: `resource_type`, `resource_id`, `owner_party_id`, `manager_party_id`
- Action: `read/write/update/delete/export`
- Environment: 时间/IP/客户端
- 说明：`project` 资源仅使用 `manager_party_id` 参与判定，不使用 `owner_party_id`

---

## 4.4 关键策略（与当前口径对齐）

1. 默认拒绝（无命中策略即 deny）。  
2. 资产可见：命中 owner 路径或 manager 路径策略。  
3. 合同财务 `perspective=owner|manager` 必传。  
4. 管理视角写入：必须命中 manager 关系策略（或全局 allow）。  
5. 项目读写：仅基于 `manager_party_id` 路径判定（不使用 owner 路径）。  
6. 无权限详情 404，列表空。
7. `owner_party_id / manager_party_id` 以业务表字段为唯一事实来源；`party_role_bindings` 不参与实时权限真值判定（仅用于扩展/审计）。

## 4.5 角色策略包示例（推荐默认）

1. `platform_admin`：全资源 `allow all`。  
2. `asset_owner_operator`：资产/合同按 owner 路径可读，合同财务以 owner 视角。  
3. `asset_manager_operator`：资产/合同按 manager 路径可读写，合同财务以 manager 视角。  
4. `dual_party_viewer`：owner + manager 双路径只读。  
5. `no_data_access`：仅功能菜单权限，不含数据可见策略。

说明：
- “产权方/经营方”是资源关系语义（`owner_party_id / manager_party_id`），不是写死用户角色。
- 用户最终可见范围由“角色绑定的策略集合”运行时计算，不在业务 SQL 中硬编码固定角色名。

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

6. 新增鉴权接口
- `POST /api/v1/authz/check`（内部服务与调试使用）
- 入参：`subject + action + resource + context`
- 出参：`allow/deny + matched_policy`

7. 新增角色数据策略配置接口（管理面）
- `GET /api/v1/auth/roles/{role_id}/data-policies`
- `PUT /api/v1/auth/roles/{role_id}/data-policies`
- `GET /api/v1/auth/data-policies/templates`
- 说明：管理员按角色挂载策略包，不直接编辑底层表达式

8. 登录态能力清单接口（前端消费）
- `GET /api/v1/auth/me/capabilities`
- 出参：`resource + action + perspective + data_scope` 能力清单
- 说明：前端页面显隐和按钮可用性以能力清单为准，不在页面层频繁调用 `/authz/check`

## 5.2 前端 Type/Service

1. `frontend/src/types/*` 全面替换旧主体字段。  
2. `frontend/src/services/*` 请求参数与响应字段同步更新。  
3. 登录成功与 token refresh 后重拉 `capabilities`，前端基于能力清单做视角/按钮控制。  
4. 资源列表与详情仍由后端 ABAC 做最终裁决（前端能力清单仅做 UI 预裁剪）。  
5. 角色管理页新增“数据策略包配置”区域。

---

## 6. 一次切换迁移方案（Runbook）

## 6.1 上线前准备

1. 生产快照全量演练 >= 2 次。  
2. 生成映射表：
- `org_to_party_map`
- `ownership_to_party_map`
3. 修复脏数据：
- 代码重复
- 空 owner/manager
- 合同无权属主体
4. 项目数据校验：
- `projects.manager_party_id` 不得为空
- 历史项目资产关联（若有）需可回填到 `project_assets`
5. 发布前强校验：
- `abac_policy_subjects` 必须为空表
- 若非空，阻断发布窗口并先完成人工处置

## 6.2 发布窗口执行

1. 进入只读窗口。  
2. 执行 DDL：Party/Role/ABAC 新表 + `abac_role_policies`，并删除 `abac_policy_subjects`。  
3. 全量迁移与回填：
- Organization -> Party(`organization`)
- Ownership -> Party(`legal_entity`)
- 业务表旧 FK -> 新 party_id
- `projects` 仅回填 `manager_party_id`（不生成 `owner_party_id`）
- 回填 `project_assets`（从现有可识别项目-资产关系迁移，无法识别项进入人工清单）
- 回填 role bindings
- 回填角色策略绑定（默认包）
- 写入经营方历史首条记录
4. 同一窗口内物理删除旧业务字段（不延后版本删除）：
- `assets.organization_id / ownership_id / management_entity`
- `rent_contracts.ownership_id`
- `projects.organization_id` 及旧管理字符串字段
- `property_certificates.organization_id`
5. 部署后端（角色入口 + ABAC 判定生效）+ 前端（新字段）  
6. 执行门禁验证。  
7. 验证通过后开放写流量。

## 6.3 发布后收敛

1. 旧逻辑确认已下线（无兼容分支）  
2. 观察期仅保留监控与审计，不再做旧字段清理动作（已在窗口内物理删除）

---

## 7. 测试与验收

## 7.1 迁移对账（硬门禁）

1. 主体数量对账（Organization/Ownership -> Party）  
2. 资产 owner/manager 对账 100%  
3. 合同主体关系对账 100%  
4. 项目 `manager_party_id` 对账 100%  
5. 项目-资产关系（`project_assets`）对账 100%  
6. 产权证主体关系对账 100%

## 7.2 权限回归

1. 新用户 deny by default。  
2. owner 路径可见性正确。  
3. manager 路径可见性正确。  
4. 合同写入仅 manager 关系命中可通过。  
5. 角色策略包变更后，判定与数据查询结果在 `<5s` 内最终一致（含缓存失效）。  
6. 项目读写仅 manager 路径命中可通过。  
7. token refresh 后能力清单与最新角色策略保持一致（遵循 `<5s` 最终一致口径）。  
8. 无权限详情 404 行为一致。

## 7.3 业务回归

1. 资产/合同/项目/产权证 CRUD 全链路。  
2. 项目资产绑定/解绑与历史查询链路可用（支持“先创建项目后补绑定资产”）。  
3. 导入导出、统计报表、筛选分页。  
4. 前端关键页面冒烟通过。

## 7.4 性能门槛

1. 关键列表查询 P95 不劣于基线 10% 以上。  
2. ABAC 判定 P95 达标（建议 <20ms，含缓存）。  
3. 角色变更后权限缓存失效延迟可控（建议 <5s）。

## 7.5 权限缓存一致性验收

1. 角色策略变更后，按 `user_id + role_id` 精准删除缓存。  
2. 变更事件广播后，多实例节点权限缓存在目标时限内完成失效。  
3. 旧缓存命中不应超过时限窗口。

---

## 8. 回滚预案

1. 切换前做物理备份 + 逻辑快照。  
2. 回滚触发条件（任一）：
- 对账失败
- 权限关键用例失败
- 主流程不可用
3. 回滚步骤：
- **应用与数据库必须一起回滚**（禁止单边回滚）
- 回退应用版本到切换前版本
- 数据库恢复到切换前快照
- 导出失败差异清单

---

## 9. 实施任务拆解（可直接派工）

1. 数据库组：新表 + 约束 + Alembic + 回滚脚本  
2. 迁移组：映射、回填、对账工具、`abac_policy_subjects` 删表迁移、`project_assets` 关系回填  
3. 鉴权组：ABAC 引擎 + `abac_role_policies` + `/authz/check` + 缓存精准删除 + 失效事件广播  
4. 权限管理组：角色数据策略包后台配置与审计日志  
5. 业务后端组：asset/contract/project/certificate 全域字段替换 + `project_assets` 关系服务  
6. 前端组：类型、服务、页面联调、角色策略包配置页  
7. 测试组：迁移回归、角色到策略链路回归、性能基准  
8. 发布组：窗口执行与回滚值守

---

## 10. 重要假设与默认值

1. 不保留旧接口兼容层。  
2. 不做双写。  
3. Party 仅含组织与外部法人。  
4. 组织层级主数据迁移到 `party_hierarchy`。  
5. 外部产权方可仅作为 Party 存在，不要求必须有系统用户账号。  
6. 项目创建本期不强制要求已绑定资产（后续可再升级为硬约束）。  
7. 以数据正确性为唯一上线门禁优先级。

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
