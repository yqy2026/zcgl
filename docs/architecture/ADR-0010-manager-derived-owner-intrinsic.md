# ADR-0010: 运营方单一权威轴——随项目派生；产权方挂资产

**状态**: ✅ 已实施（2026-06-18）
**决策日期**: 2026-06-16
**相关需求**: REQ-AST-002（资产与项目、权属关系可追踪）、REQ-PRJ-001（项目关系遵循运营管理语义）、REQ-AUTH-002（数据范围上下文自动注入）、PRD §5 角色权限与数据范围模型

---

## 背景

数据范围绑定是安全模型的地基：用户按 `binding_type = owner | manager` 绑定 Party，查询按资产的 `owner_party_id`（owner 绑定）或 `manager_party_id`（manager 绑定）过滤（domain-model §4.12 `CustomerProfile.binding_type`、REQ-AUTH-002）。

但「运营方」轴 `manager_party_id` 同时作为**独立必填字段**出现在 `Asset`、`Project` 上（domain-model §4.1/§4.2），且 `Asset.project_id` 为**选填**。这留下一个口径歧义：

- REQ-PRJ-001 的语义是「项目绑定运营管理方，**通过资产间接关联产权方**」——运营方的权威轴本应在**项目**上；编码规则也印证（`asset_code` 按**产权方**编码段、`project_code` 按**运营方**编码段，domain-model §line18），资产的身份锚在产权方。
- 然而 `Asset.manager_party_id` 是个可自由设置的独立必填字段。对**有项目**的资产，文档未约束它必须等于所属 `Project.manager_party_id`，两者可漂移。
- 项目是「资产的业务管理归集，可能调整」（2026-06-16 决策访谈）。一旦把资产从「甲运营的 P1」挪到「乙运营的 P2」，若 `Asset.manager_party_id` 不联动，**「谁能看到这个资产」就有了两套口径**——按资产字段 vs 按项目字段。这是数据范围安全的歧义，不是展示问题。

## 决策

**运营方与产权方性质不同，不用同一种字段形态——非对称处理：**

1. **`Asset.manager_party_id` 改为派生**：= 资产当前有效 `project_id` 所属项目的 `manager_party_id`，不再让用户单独填、单独改。运营方权威轴**唯一落在 Project**。资产挪项目，运营方随之改变，数据范围自动跟随。
2. **`Asset.owner_party_id` 保持独立必填**：产权方是资产的内在权属事实，与「资产归在哪个项目」解耦。挪项目**不改变谁拥有它**。
3. **无项目资产 = 无运营方**：`Asset.project_id` 选填，未归入任何项目的资产 `manager_party_id` 派生为空，对**运营方绑定**用户一律不可见；其**产权方绑定**视角照常可见（产权方是资产自带事实）。这符合直觉——还没被归入任何运营项目的资产，本就「还没有人在运营它」。
4. **manager 绑定的数据范围一律按「资产当前项目的运营方」过滤**，不再读资产上的独立运营方字段。

## 被否决的方案

| 方案 | 否决原因 |
|------|----------|
| 维持 `Asset.manager_party_id` 独立必填可自由设置 | 与所属项目运营方可漂移，「谁能看这个资产」出现两套口径，数据范围安全歧义 |
| 保留独立字段，但加「有项目时必须等于项目运营方」硬约束 | 可消歧义，但留了一份必须时刻校验的冗余可变状态；既然有项目时必等于项目、无项目时无运营方语义，独立字段无信息增量，不如直接派生（符合 MVP 减法方向） |
| 把产权方也做成随项目派生 | 错误——产权方是权属事实，挪项目不改变所有权；与「资产身份锚在产权方」「项目通过资产间接关联产权方」矛盾 |

## 关键冻结决策

1. **运营方派生、产权方独立**——非对称是有意的，不是笔误。
2. **运营方权威轴唯一在 Project**；资产不再持有可独立设置的运营方。
3. **无项目资产对运营绑定用户不可见、对产权绑定用户可见**，是接受的取舍。

## 影响

已实施的工程项：

- **后端**：保留 `assets.manager_party_id` 兼容列，但收敛为只读派生投影：创建、更新、批量更新和 `Asset.__init__` 均忽略 `manager_party_id` / `management_entity` 独立输入；资产响应由当前有效 `Asset.project.manager_party_id` 派生，无项目时为空。资产 manager 绑定数据范围过滤已改为通过 active `project_assets` join `projects.manager_party_id`，不再读取资产列；无项目资产自然不进入 manager 视角。资产列表的 `management_entity` / `manager_party_id` 筛选同样收敛到当前项目运营方。
- **domain-model**：§4.1 `Asset.manager_party_id` 改标「派生，= 当前项目运营方，无项目时空」（本次随手落）。
- **PRD**：REQ-AST-002、REQ-PRJ-001 明文「运营方随项目派生、产权方挂资产」（本次随手落）。
- **CONTEXT.md**：增「运营方单一权威轴（随项目派生）」词条（本次随手落）。
- **traceability**：REQ-AST-002 / REQ-AUTH-002 已补代码与测试证据。
- **CHANGELOG.md**：已记录本次代码收口。

待实施缺口（2026-06-18 grill 发现）：

- **导入旁路 owner 必填**：手动创建已强制 `owner_party_id`（`asset_service.py:292`），但**导入路径未卡** owner——`validators.py:REQUIRED_FIELDS` 不含产权方，ownership 仅在提供时校验，且导入 create 直接调 `asset_crud.create_with_history_async`（`import_service.py:180`）**绕过** service 层 owner 必填校验，可建无产权方资产（违反本 ADR「owner 内在必填」，并卡死 ADR-0017 编号生成）。须补：导入 owner 必填（无法解析到产权方 Party 的行直接拒绝）、解析到 `owner_party_id`（legacy `ownership_id` 在 Party 迁移收口前作兼容入口）、导入 create 走与手动创建共享的 owner 必填校验、不绕 crud。

## 参考

- `CONTEXT.md`：`运营方单一权威轴（随项目派生）` 词条
- domain-model §4.1 Asset、§4.2 Project、§4.12 CustomerProfile（`binding_type`）
- 相关簇：REQ-PRJ-001（项目通过资产间接关联产权方）、REQ-AUTH-002（数据范围自动注入）
