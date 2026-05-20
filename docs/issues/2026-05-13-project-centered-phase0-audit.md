# 项目主轴资产运营 Phase 0 审计

## 状态

- 日期：2026-05-13
- 关联规划：`docs/plans/2026-05-12-project-centered-asset-operations-plan.md`
- 审计范围：前端菜单/路由/页面、后端 Project/ContractGroup/Contract/Asset/台账关系、SSOT 差距、Phase 1a/1b 前置设计
- 结论：可以进入 SSOT 同步和 Phase 1a 设计，但必须先处理 `ContractGroup.project_id`、项目合同关系 API 和“一资产一有效合同组”约束。

## 1. 总体结论

当前系统已经具备项目、资产有效期关系、合同组、合同、合同关系和台账基础，但仍以“合同组”为用户可见主对象：

- 前端普通菜单仍将 `/contract-groups` 放在资产管理下，文案为“合同组管理”。
- 路由、面包屑、服务、测试和多个页面仍直接暴露“合同组”。
- 项目详情页已能聚合项目资产，并按资产逐个展示租赁摘要，但没有项目级“合同关系、收付款、风险、项目分析”能力。
- 后端 `project_assets` 已具备有效期和同一资产仅一个当前项目的约束，可以承载资产项目历史归属。
- `ContractGroup` 和 `Contract` 当前均无 `project_id`，项目主轴落地的首个模型改动应是 `ContractGroup.project_id`。
- 现有“一资产一有效合同组”守卫会阻碍同一项目内多条合同关系并存，需要调整为项目内可多关系、单条关系内资产覆盖清晰，或至少按经营模式/时间范围约束。

## 2. 前端可见点清单

| 类别 | 位置 | 现状 | 建议 |
|---|---|---|---|
| 一级/二级菜单 | `frontend/src/config/menuConfig.tsx:52` | `/contract-groups` 在资产管理下，标签为“合同组管理” | Phase 1b 从普通菜单隐藏，项目详情内展示“合同关系” |
| 菜单选中/展开 | `frontend/src/config/menuConfig.tsx:134`, `frontend/src/config/menuConfig.tsx:148`, `frontend/src/config/menuConfig.tsx:164` | `/contract-groups` 仍按资产管理展开 | 隐藏入口后保留内部路由选中策略，后续删除 |
| 路由常量 | `frontend/src/constants/routes.ts:32`, `frontend/src/constants/routes.ts:165` | `CONTRACT_GROUP_ROUTES` 和 `ROUTE_CONFIG` 暴露合同组列表/新建/详情/编辑 | Phase 1b 增加项目合同关系路由或项目内 tab，旧常量转内部入口 |
| 受保护路由 | `frontend/src/routes/AppRoutes.tsx:104` | `/contract-groups`、`/contract-groups/new`、`/contract-groups/import`、详情和编辑均为普通受保护路由 | 保留作为回退路由，普通菜单隐藏；稳定后清理 |
| 列表页 | `frontend/src/pages/ContractGroup/ContractGroupListPage.tsx:32`, `frontend/src/pages/ContractGroup/ContractGroupListPage.tsx:94` | 表格列为“合同组编码”，页面标题“合同组管理”，展示 `LEASE/AGENCY` | 改为项目内“合同关系”投影，不直接展示编码和枚举 |
| 详情页 | `frontend/src/pages/ContractGroup/ContractGroupDetailPage.tsx:71`, `frontend/src/pages/ContractGroup/ContractGroupDetailPage.tsx:119`, `frontend/src/pages/ContractGroup/ContractGroupDetailPage.tsx:144` | 页面标题/错误/字段/卡片均直接显示合同组、组内合同、规则 JSON | 旧页可降级为内部排障页；项目详情页重做业务展示 |
| 表单页 | `frontend/src/pages/ContractGroup/ContractGroupFormPage.tsx:224`, `frontend/src/pages/ContractGroup/ContractGroupFormPage.tsx:257`, `frontend/src/pages/ContractGroup/ContractGroupFormPage.tsx:328` | 按“新建/编辑合同组”录入，存在“前驱合同组 ID” | Phase 2 改为从项目新增四类合同，系统维护底层关系 |
| PDF 导入 | `frontend/src/pages/Contract/ContractImportReview.tsx:725`, `frontend/src/pages/Contract/ContractImportReview.tsx:734`, `frontend/src/pages/Contract/ContractImportReview.tsx:754` | 导入要求显式提供合同组与 `LEASE/AGENCY` / 关系枚举 | Phase 2 保留 fail-closed，但从项目上下文带入 `project_id` 和业务化关系选择 |
| 客户详情 | `frontend/src/pages/Customer/CustomerDetailPage.tsx:39` | 合同历史列名为“合同组”，显示 `group_code` | 改为“所属项目/合同关系” |
| 搜索入口 | `frontend/src/pages/Search/GlobalSearchPage.tsx:107` | placeholder 包含“合同组” | 改为“合同关系”或“合同” |
| 后端搜索结果 | `backend/src/services/search/service.py:269`, `backend/src/services/search/service.py:276`, `backend/src/services/search/service.py:279` | `contract_group` 搜索结果路由到 `/contract-groups/{id}`，分组名“合同组” | 增加项目上下文后路由到项目详情合同关系锚点 |

## 3. 当前数据模型盘点

### 3.1 Project

`Project` 当前是轻量运营归集单元：

- 主字段：`project_name`、`project_code`、`status`、`manager_party_id`、审核字段和数据状态，见 `backend/src/models/project.py:37`。
- 通过 `project_assets` 间接关联资产，见 `backend/src/models/project.py:102`。
- `project_type`、`start_date`、`end_date` 等历史字段在构造器中被丢弃，见 `backend/src/models/project.py:115`。若后续恢复项目类型或项目周期，必须走新契约而不是兼容旧字段。

### 3.2 ProjectAsset

`ProjectAsset` 已满足项目主轴的核心历史关系要求：

- 有 `valid_from` / `valid_to`，见 `backend/src/models/project_asset.py:50`。
- 有 `ck_project_assets_valid_range`，见 `backend/src/models/project_asset.py:20`。
- 有 `uq_project_assets_active_asset`，保证同一资产同一时点只能有一个当前项目，见 `backend/src/models/project_asset.py:25`。
- `Asset.project` 通过 `project_assets.valid_to IS NULL` 只读反查当前项目，见 `backend/src/models/asset.py:321`。

结论：资产项目历史归属不需要新建历史表，优先沿用 `project_assets`。

### 3.3 ContractGroup / Contract / ContractRelation

当前合同聚合仍独立于项目：

- `ContractGroup` 有 `operator_party_id`、`owner_party_id`、`revenue_mode`、有效期、规则 JSON、风险标签，但没有 `project_id`，见 `backend/src/models/contract_group.py:103`。
- `ContractGroup.assets` 通过 `contract_group_assets` 关联资产，见 `backend/src/models/contract_group.py:226` 和 `backend/src/models/associations.py:11`。
- `Contract.contract_group_id` 是合同归属的唯一聚合外键，没有 `project_id`，见 `backend/src/models/contract_group.py:259`。
- `Contract.assets` 通过 `contract_assets` 关联资产，语义是合同组资产子集，见 `backend/src/models/associations.py:30`。
- `ContractRelation` 表达合同间父子关系，不适合作为用户可见主对象，见 `backend/src/models/contract_group.py:588`。

结论：Phase 1a 应在 `ContractGroup` 增加 `project_id`，不在 `Contract` 单独加项目外键。

## 4. 当前 API 和服务能力

### 4.1 项目 API

当前项目详情能力偏基础：

- `GET /projects/{project_id}` 返回项目主数据，见 `backend/src/api/v1/assets/project.py:467`。
- `GET /projects/{project_id}/assets` 返回当前有效资产和面积汇总，见 `backend/src/api/v1/assets/project.py:422`。
- `ProjectService.getProject()` 和 `getProjectAssets()` 只封装这两类能力，见 `frontend/src/services/projectService.ts:60` 和 `frontend/src/services/projectService.ts:82`。
- 前端 API 常量只定义 `DETAIL`、`ASSETS`、CRUD、搜索和下拉选项，见 `frontend/src/constants/api.ts:127`。

缺口：

- 无项目级合同关系 API。
- 无项目级台账摘要 API。
- 无项目级风险 API。
- 无项目级租户/客户 API。
- 无项目级分析 API。

### 4.2 项目详情页

当前项目详情页已经有一个可复用起点：

- 拉取项目主数据和项目资产，见 `frontend/src/pages/Project/ProjectDetailPage.tsx:219`、`frontend/src/pages/Project/ProjectDetailPage.tsx:230`。
- 展示资产清单，见 `frontend/src/pages/Project/ProjectDetailPage.tsx:461`。
- 通过每个资产调用 `assetService.getAssetLeaseSummary()` 展示租赁摘要，见 `frontend/src/pages/Project/ProjectDetailPage.tsx:89` 和 `frontend/src/pages/Project/ProjectDetailPage.tsx:486`。

问题：

- 当前是“资产 -> 租赁摘要”的分散查询，不是“项目 -> 合同关系”的项目级视图。
- 页面缺收付款、风险、项目分析、租户/客户分区。
- 注释承认出租率占位，见 `frontend/src/pages/Project/ProjectDetailPage.tsx:573`。

### 4.3 合同组服务约束

当前服务有一个关键阻塞：

- `_ensure_assets_not_bound_to_other_groups()` 会拒绝资产绑定到其他有效合同组，见 `backend/src/services/contract/contract_group_service.py:192`。
- 冲突查询只按资产和 `ContractGroup.data_status == "正常"` 判断，不区分项目、模式或时间范围，见 `backend/src/crud/contract_group.py:692`。

这和新规划“一个项目可包含多条合同关系”存在冲突。Phase 1a 需要决定：

- 是否保留“同一资产同一时点仅一个承租转租关系”。
- 是否允许同一资产在一个项目内同时存在上游/下游多合同。
- 代理运营和承租转租是否可同时覆盖同一资产但分别分区展示。

## 5. SSOT 差距

| 文档 | 当前问题 | 修订方向 |
|---|---|---|
| `docs/prd.md` | 仍写“合同组能力可用”“租赁管理包含合同组”“合同组作为主业务对象”，见 `docs/prd.md:31`、`docs/prd.md:52`、`docs/prd.md:143` | 改为项目主轴、合同关系为用户可见层、`ContractGroup` 为技术聚合根 |
| `docs/specs/domain-model.md` | `ContractGroup` 无 `project_id`，仍定位为“一笔经营关系的交易包”，见 `docs/specs/domain-model.md:28`、`docs/specs/domain-model.md:88` | 增加 `project_id`；定义合同关系展示投影；项目分析字段用派生口径 |
| `docs/specs/api-contract.md` | 项目 API 只有详情和当前资产，合同组仍是主端点，见 `docs/specs/api-contract.md:90`、`docs/specs/api-contract.md:101` | 增加项目合同关系、台账摘要、风险、租户、项目分析端点 |
| `docs/traceability/requirements-trace.md` | REQ-RNT-001 仍是“合同组五层模型和主业务对象”，见 `docs/traceability/requirements-trace.md:43` | 新增/调整 REQ-PRJ / REQ-RNT 追踪，记录项目主轴和合同关系展示层 |

## 6. `ContractGroup.project_id` 设计建议

### 6.1 模型和迁移

建议新增：

- `contract_groups.project_id VARCHAR NULL`，FK 到 `projects.id`。
- 索引：`ix_contract_groups_project_id`。
- 初始迁移允许 nullable，回填后再评估是否改为 not null。
- ORM 关系：`ContractGroup.project` 与 `Project.contract_groups`。
- Schema：`ContractGroupCreate.project_id` 必填，`ContractGroupListItem/Detail` 返回。

### 6.2 回填规则

回填优先级：

1. 若合同组所有资产当前有效项目唯一，回填该项目。
2. 若当前项目不唯一，按合同组 `effective_from/effective_to` 与 `project_assets.valid_from/valid_to` 匹配唯一项目。
3. 若仍无法唯一命中，写入审计输出或待人工确认清单，不猜测。

### 6.3 API 设计

Phase 1a 最小新增端点：

| API | 用途 |
|---|---|
| `GET /api/v1/projects/{project_id}/contract-relations` | 项目详情合同关系区 |
| `GET /api/v1/projects/{project_id}/ledger-summary` | 项目收付款摘要 |
| `GET /api/v1/projects/{project_id}/risks` | 项目风险摘要 |

Phase 1a 可以先不做完整项目分析和租户 API，避免一次改造过大。

## 7. 第一批实施切片

### 7.1 Phase 0 完成后立即做的 SSOT 批次

建议先改文档，不碰业务代码：

- `docs/prd.md`
- `docs/specs/domain-model.md`
- `docs/specs/api-contract.md`
- `docs/traceability/requirements-trace.md`
- `CHANGELOG.md`

目标：把项目主轴、合同关系展示投影、`ContractGroup.project_id` 写成 SSOT。

### 7.2 Phase 1a 后端基础

建议文件范围：

- Alembic migration：新增 `contract_groups.project_id`、索引、回填脚本或人工确认输出。
- `backend/src/models/contract_group.py`
- `backend/src/models/project.py`
- `backend/src/schemas/contract_group.py`
- `backend/src/schemas/project.py`
- `backend/src/crud/contract_group.py`
- `backend/src/services/contract/contract_group_service.py`
- `backend/src/services/project/service.py`
- `backend/src/api/v1/assets/project.py`
- 对应 unit / migration tests。

### 7.3 Phase 1b 前端重构

建议文件范围：

- `frontend/src/pages/Project/ProjectDetailPage.tsx`
- `frontend/src/services/projectService.ts`
- `frontend/src/types/project.ts`
- `frontend/src/constants/api.ts`
- `frontend/src/config/menuConfig.tsx`
- `frontend/src/config/breadcrumb.ts`
- `frontend/src/constants/routes.ts`
- `frontend/src/routes/AppRoutes.tsx`
- 对应页面、路由、菜单测试。

## 8. 风险和处理建议

| 风险 | 等级 | 处理 |
|---|---|---|
| `ContractGroup.project_id` 回填不唯一 | 高 | nullable 起步，输出人工确认清单 |
| 一资产一有效合同组约束阻塞项目多关系 | 高 | Phase 1a 前先定义新约束；测试覆盖同项目多关系 |
| 前端“合同组”引用广 | 中 | Phase 1b 先隐藏入口、保留路由；分批替换文案 |
| 项目详情一次性改造过大 | 中 | 先做合同关系、台账摘要、风险骨架；租户和分析后置 |
| SSOT 与实现短期不一致 | 中 | SSOT 批次独立提交，traceability 标记为待实现 |

## 9. 待决策问题

这些问题进入 Phase 1a 前必须明确：

1. `ContractGroup.project_id` 初期是否允许为空：建议允许，直到存量回填完成。
2. “一资产一有效合同组”是否改为“同一项目内可多合同关系，但同一关系内资产不重复”：建议改。
3. 同一资产是否允许同时存在承租转租和代理运营关系：建议允许，但项目分析必须分区。
4. 旧 `/contract-groups` 是否保留一个发布周期：建议保留内部路由，普通菜单隐藏。

## 10. 建议验证用例

- migration 新增 `contract_groups.project_id` 后，旧数据不会因空值失败。
- 回填脚本遇到多项目命中时输出待人工确认，不写入随机项目。
- 同一项目内同一资产可以被不同合同关系引用，若符合新规则不报错。
- 跨项目重复覆盖同一资产时仍能阻断或提示风险。
- 项目详情合同关系 API 只返回该项目下合同关系。
- 普通菜单不展示“合同组管理”，但内部回退路由仍受权限保护。
- 搜索结果不再以“合同组”作为普通用户分组名。

