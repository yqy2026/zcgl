# 主体（Party）架构深度分析与重构方案

**状态**: ✅ 架构师已复核（基于 SSOT 需求修正定稿）
**分析日期**: 2026-04-05
**架构评审**: 肯定 A+C 提案。在严格遵守《需求规格说明书》(REQ-CUS-001, REQ-PTY-001) 的单主档约束下，该方案是最务实且符合项目数据治理边界的选择。
**触发原因**: 用户反馈"产权方、租户、运营方、集团内的、集团外的都混在一个主体界面，乱糟糟的，难用死了"

---

## 一、问题概述

系统当前采用 **Party-Role 双层模型**（ADR-0001），将"主体"与"角色"解耦。这一架构在理论上 elegant，但在实际用户体验层面产生了严重的可用性问题：

> **核心矛盾**: 用户在业务中思考的是"我要找一个产权方/租户/运营方"，而系统提供的是"所有主体的大杂烩，只按组织/法人/自然人分类"。

---

## 二、现状全景分析

### 2.1 数据模型层

#### Party 表结构（`backend/src/models/party.py`）

| 字段 | 类型 | 说明 | 问题 |
|------|------|------|------|
| `party_type` | Enum | `organization` / `legal_entity` / `individual` | ❌ 技术分类，非业务分类 |
| `name` | String(200) | 主体名称 | - |
| `code` | String(100) | 主体编码 | - |
| `status` | String(50) | `active` / `inactive` | - |
| `review_status` | Enum | `draft` / `pending` / `approved` / `reversed` | - |
| `metadata` | JSONB | 扩展信息 | ❌ 垃圾场模式 |

**关键发现**: `party_type` 的三个值描述的是**法律形式**，不是**业务角色**。

#### 业务表中的角色引用（角色通过外键位置隐式定义）

| 业务表 | 产权方字段 | 运营方字段 | 管理方字段 | 出租方/承租方 |
|--------|-----------|-----------|-----------|-------------|
| `assets` | `owner_party_id` | - | `manager_party_id` | - |
| `projects` | - | - | `manager_party_id` | - |
| `contract_groups` | `owner_party_id` | `operator_party_id` | - | - |
| `contracts` | - | - | - | `lessor_party_id` / `lessee_party_id` |
| `certificate_party_relations` | 通过 `relation_role` 区分 | - | - | `owner` / `co_owner` / `issuer` / `custodian` |
| `asset_management_history` | - | - | `manager_party_id` | - |

#### 被闲置的 PartyRole 体系

系统中存在 `party_role_defs` 和 `party_role_bindings` 两张表，设计用于定义和绑定角色（OWNER/MANAGER），但**当前代码中零 CRUD/Service/API 使用**。仅在 model 定义和 alembic 迁移中存在。角色判断完全依赖业务表中的 FK 字段位置。

#### 已启用但不够用的 UserPartyBinding 体系

`UserPartyBinding` 表通过 `relation_type`（`owner` / `manager` / `headquarters`）将用户与主体关联，是**当前唯一活跃使用的业务角色机制**，支撑数据权限隔离（`party_scope.py` + `PartyFilter`）。但它解决的是"**用户能看哪些主体的数据**"，而非"**这个主体在业务中是什么角色**"。两者维度不同：

| 维度 | 机制 | 角色值 | 解决的问题 |
|------|------|--------|-----------|
| 用户→主体 | `UserPartyBinding` | owner / manager / headquarters | 数据权限隔离 |
| 主体→业务 | ❌ 缺失 | 产权方 / 租户 / 运营方 / 集团内 / 集团外 | 业务分类与检索 |

### 2.2 API 层

#### 主体列表 API（`GET /api/v1/parties`）

```python
# 仅支持以下过滤参数
skip, limit, party_type, status, search
```

**问题**:
- ❌ 没有 `business_role` 过滤（无法按产权方/租户/运营方筛选）
- ❌ 没有 `customer_type` 过滤（无法按集团内/集团外筛选）
- ❌ 没有按业务使用频率排序
- ❌ 返回列表无业务上下文（不显示该主体在哪些业务中担任什么角色）

#### 客户档案 API（`GET /api/v1/customers/{party_id}`）

这是一个视角依赖的端点，返回特定视角（owner/manager）下的客户信息。

**问题**:
- ❌ 只在"客户"概念下工作，不适用于产权方/运营方
- ❌ 视角（perspective）由当前用户绑定推导，不够灵活
- ❌ 与 `/parties` 端点功能割裂，用户需要知道两个不同的入口

#### 完整 API 端点清单

系统实际有 **17 个** party 相关 API 端点：

| 端点 | 用途 |
|------|------|
| `GET /parties` | 列表（仅 5 个过滤参数） |
| `POST /parties` | 创建 |
| `POST /parties/import` | 批量导入 |
| `GET /parties/{id}` | 详情 |
| `PUT /parties/{id}` | 更新 |
| `DELETE /parties/{id}` | 软删除 |
| `POST /parties/{id}/submit-review` | 提交审核 |
| `POST /parties/{id}/approve-review` | 审核通过 |
| `POST /parties/{id}/reject-review` | 驳回审核 |
| `GET /parties/{id}/review-logs` | 审核日志 |
| `GET /parties/{id}/hierarchy` | 获取下级 |
| `POST /parties/{id}/hierarchy` | 新增层级 |
| `DELETE /parties/{id}/hierarchy` | 删除层级 |
| `GET /parties/{id}/contacts` | 获取联系人 |
| `POST /parties/{id}/contacts` | 新增联系人 |
| `GET /customers/{id}` | 客户档案（视角依赖） |
| `GET/POST/PUT/DELETE /users/{user_id}/party-bindings` | 用户主体绑定（CRUD） |

### 2.3 前端 UI 层

#### 主体列表页（`/system/parties`）

当前过滤条件仅有：
1. 名称/编码搜索
2. **主体类型**: 组织 / 法人主体 / 自然人
3. **状态**: active / inactive
4. **审核状态**: 草稿 / 待审核 / 已审核 / 已反审核

**问题清单**:

| # | 问题 | 严重程度 | 说明 |
|---|------|---------|------|
| 1 | 无业务角色过滤 | 🔴 严重 | 用户无法只看"产权方"或"租户" |
| 2 | 无集团内外过滤 | 🔴 严重 | 用户无法区分集团内/外主体 |
| 3 | 无业务关联信息 | 🟡 中等 | 列表不显示主体关联了多少资产/合同 |
| 4 | 列表无分页 | 🟡 中等 | `limit: 200` + `pagination={false}`，一次性加载 |
| 5 | 无主体性质标签 | 🟡 中等 | 无法快速识别企业/个人 |
| 6 | 创建表单过于简单 | 🟡 中等 | 只填 name/code/type，缺少业务属性 |

#### 主体详情页（`/system/parties/:id`）

详情页展示了所有字段（包括 metadata 中的 customer_type、subject_nature、identifier_type、risk_tags 等），**不论主体类型如何，表单字段完全相同**。

**问题**:
- ❌ 个人主体不需要"统一社会信用代码"
- ❌ 产权方不需要"账期偏好"（这是租户属性）
- ❌ 所有 metadata 字段平铺展示，无分组
- ❌ 无业务关联视图（不显示该主体关联的资产、合同、项目）

#### PartySelector 组件

这个组件在合同创建、资产编辑等场景中被广泛使用。

**问题**:
- ❌ `filterMode` 仅基于 URL 路径推断（`/owner/*` → owner），不够精确
- ❌ 搜索时不区分业务角色，返回结果混杂
- ❌ 快速新建主体时只填最基本信息，缺少业务上下文

**已有能力（文档补充）**:
- `filterMode` 为 `owner` / `manager` 时，会排除 `individual` 类型主体，仅返回 `organization` / `legal_entity`
- 已有一定的隐式业务角色过滤，只是不够精细

### 2.4 metadata JSONB 字段分析

当前 metadata 中存储的字段：

| metadata 字段 | 含义 | 适用主体类型 | 问题 |
|--------------|------|------------|------|
| `customer_type` | internal / external | 所有 | ❌ 名称误导（非客户也有此字段）|
| `subject_nature` | enterprise / individual | 所有 | ❌ 与 party_type 重复（可由 party_type 推导） |
| `identifier_type` | USCC / CN_ID_CARD / PASSPORT | 所有 | ❌ 应结构化 |
| `unified_identifier` | 统一标识值 | 所有 | ❌ 应结构化 |
| `contact_name` | 联系人 | 所有 | ❌ 已有 PartyContact 表，两处同时使用存在数据不一致风险 |
| `contact_phone` | 联系电话 | 所有 | ❌ 已有 PartyContact 表，两处同时使用存在数据不一致风险 |
| `address` | 地址 | 所有 | ❌ 应结构化 |
| `payment_term_preference` | 账期偏好 | 租户 | ❌ 仅租户需要 |
| `risk_tags` | 风险标签数组 | 所有 | ❌ 应结构化 |

**核心问题**: metadata 是一个无模式的 JSONB 字段，缺乏：
1. 数据库级约束和验证
2. 索引支持（搜索性能差）
3. 类型区分（不同业务角色的主体应有不同的 metadata schema）
4. 前端表单的差异化展示

**数据不一致风险**: `contact_name` / `contact_phone` 同时存在于 metadata 和 `PartyContact` 表。Service 层读取时先取 metadata，fallback 到 PartyContact（`service.py:700-707`），两处数据可能不一致。

### 2.5 审核工作流

系统具备完整的主体审核工作流：

```
草稿（draft）→ 提交 → 待审核（pending）→ 审核通过（approved）/ 驳回（draft）
                                              → 反审核（reversed）
```

- 草稿状态可编辑，待审核/已审核状态不可编辑
- 每次状态变更写入 `party_review_logs` 审计日志
- 导入的主体自动标记为已审核（`review_status=approved`，原因"初始化导入"）
- 合同提交前校验关联主体必须全部已审核（`assert_parties_approved`）

这是一个设计完善的机制，但审核状态本身不能替代业务角色分类。

---

## 三、根因分析

### 3.1 架构层面的根因

```
理想中的 Party-Role 模型:
  Party（主体注册表）+ PartyRoleBinding（角色绑定）= 清晰的业务角色

实际实现:
  Party（主体注册表）+ 业务表FK位置 = 隐式的业务角色
  UserPartyBinding（用户→主体绑定）= 数据权限隔离
```

**ADR-0001 的决策本身是合理的**（将主体与角色解耦），但实施不完整：

1. **PartyRoleBinding 体系被架空**: 设计了 `party_role_defs` 和 `party_role_bindings` 表，但业务代码直接使用 FK 字段（`owner_party_id`、`lessee_party_id` 等），零 CRUD/Service/API 使用
2. **缺少主体级业务角色维度**: `UserPartyBinding` 解决了用户权限隔离，但没有解决"主体自身是什么业务角色"的问题
3. **metadata 变成了垃圾场**: 没有为不同业务角色定义差异化的字段规范

### 3.2 用户体验层面的根因

用户的心智模型：
```
我是产权方管理员 → 我想管理"我的租户"
我是运营方管理员 → 我想管理"我运营的资产的产权方和租户"
我是集团管理员 → 我想管理"集团内的主体"和"集团外的合作方"
```

系统提供的界面：
```
主体主档管理 → 一个大列表，里面有所有类型的主体
  过滤: 组织/法人/自然人（技术分类，用户不关心）
  过滤: active/inactive（技术状态，用户不关心）
  过滤: 草稿/待审核/已审核（流程状态，次要关注）
```

**认知鸿沟**: 用户按业务角色思考，系统按技术分类组织。

### 3.3 （架构师复核）SSOT 需求对齐分析

经过复核 `docs/requirements-specification.md`（项目唯一需求真相），当前的架构决策必须在以下边界内进行：
1. **统一主档约束（REQ-PTY-001）**：Party 被强制确立为跨资产、合同、客户的统一主体主档。
2. **客户增强信息归属约束（REQ-CUS-001）**：客户特有属性（如`账期偏好`、`风险标签`）必须在 Party 主档中集中维护，保持 Party 为唯一主档，**明确不允许**双主档并行维护。
3. **前端呈现约束（REQ-CUS-001 / REQ-CUS-002）**：UI 要求在客户/主体展示时必须结构化展示上述信息，并显式展示“合同角色标签”。

**架构判断**：如果脱离需求大谈第一性原理（如纯粹的领域驱动模型将“账期偏好”视作特定属于租赁契约的附属物完全不挂在主体上），这在理论上是规范的，但**必然违背本项目的 SSOT 与既定系统定位**（即要求所有主体统一属性由管理员在 `/system/parties` 中维护）。
因此，采用“业务角色动态推导”虽然模型纯净，但无法满足 UI/API 直接检索和管理的统一入口需求。**采用原草案的 A（业务标签缓存） + C（结构化业务扩展表）组合，是在遵循 SSOT 约束前提下，解决用户体验问题的最佳技术折中。**

---

## 四、影响范围评估

### 4.1 直接影响的模块

| 模块 | 影响程度 | 说明 |
|------|---------|------|
| 主体管理 | 🔴 高 | 列表、详情、创建、导入全部需要改造 |
| 合同管理 | 🟡 中 | PartySelector 需要支持业务角色过滤 |
| 资产管理 | 🟡 中 | 产权方/管理方选择器需要改进 |
| 客户档案 | 🟡 中 | 需要与主体管理整合 |
| 数据分析 | 🟡 中 | 统计维度需要支持业务角色 |

### 4.2 受影响的文件

#### 后端
| 文件 | 改动类型 |
|------|---------|
| `backend/src/models/party.py` | 可能需要新增字段 |
| `backend/src/schemas/party.py` | 需要扩展 |
| `backend/src/crud/party.py` | 需要新增查询方法 |
| `backend/src/services/party/service.py` | 需要扩展服务逻辑 |
| `backend/src/api/v1/party.py` | 需要新增/修改端点 |
| `backend/src/models/party_role.py` | 可能需要启用 |

#### 前端
| 文件 | 改动类型 |
|------|---------|
| `frontend/src/pages/System/PartyListPage.tsx` | 需要重构 |
| `frontend/src/pages/System/PartyDetailPage.tsx` | 需要重构 |
| `frontend/src/components/Common/PartySelector.tsx` | 需要扩展 |
| `frontend/src/types/party.ts` | 需要扩展 |
| `frontend/src/services/partyService.ts` | 需要扩展 |

---

## 五、架构师定稿方案（基于 SSOT 约束）

### 5.1 架构方案裁决：批准 "A + C" 渐进策略

基于《需求规格》对 Party 唯一主档地位的强制设定（REQ-PTY-001, REQ-CUS-001），原草案提出的**“主体注册表 + 业务角色标签 + 差异化表单”**的三层结构是完全合理且务实的选择。我们将采纳方案 A 解决前端的高频过滤与状态混淆痛点，采纳方案 C 解决目前 metadata 特有字段堆积所带来的架构腐化风险。

### 5.2 数据模型改造方案

#### 方案 A: 新增 `business_roles` 字段（解决前端检索痛点）

在 Party 表新增一个 JSONB 字段 `business_roles`，专用于全局查询和列表过滤：
```python
business_roles: Mapped[dict | None] = mapped_column(
    JSONB,
    comment="业务角色标签缓存，如 {'owner': True, 'tenant': True, 'operator': False}"
)
```
**架构师注**：这是一个读模型的**反范式缓存（Denormalization Cache）**。虽然其一定程度上破坏了单一事实源，但是为了满足前端全维度的业务视角过滤，这是必要的妥协。只需在 Service 层设计合适的联动事件钩子，保证状态变更时刷新缓存即可。

#### 方案 C: 新增 `party_business_profiles` 表（解决元数据治理）

新建一张 1:1 的扩展表，专用于承载 REQ-CUS-001 中提及的客户增强属性：
```python
class PartyBusinessProfile(Base):
    __tablename__ = "party_business_profiles"
    
    party_id: FK -> parties.id
    is_group_internal: bool # 是否集团内 (用于替代原 metadata 中的 customer_type)
    payment_terms: JSONB    # 账期条款（REQ-CUS-001 指定的增强字段）
    risk_level: str | None  # 风险等级（REQ-CUS-001 指定）
    industry: str | None    # 行业分类
```
**架构师注**：通过 1:1 的 Profile 表物理拆分，我们既遵循了“保持 Party 为唯一主档界面”的 SSOT 约束，又保护了 Party 核心字典表不被各业务线的定制字段污染。方案 B（过度追求 Role Def 与 Binding 的完备度）在当前 MVP 阶段会导致链路改动过重，无需实施。

### 5.3 前端 UI 分域重构策略

UI 的核心重构逻辑必须围绕“在通用大列表中注入视角的切片（Tab）”展开：
1. **多 Tabs 呈现过滤**：在 `/system/parties` 中按 `business_roles` 拆分出独立的 Tab（所有 / 租户 / 产权方），替代掉当前反人类的“法人、个人”这种自然类型组合。
2. **动态差异化表单（Contextual Forms）**：在 `/system/parties/:id` 根据主体当前的 Business Roles 展示不同的卡片组合。企业法人展示统一信用代码；具备 `tenant` 租户角色的才展示“账期配置”与“风险标签”。

---

## 六、实施计划

### Phase 1: 业务角色标签缓存与查询提效

| 任务 | 模块 | 说明 |
|------|------|------|
| 新增 `business_roles` | `models/party.py` | 字段用于存储和缓存“产权方”、“租户”等标签属性。 |
| CRUD层挂载事件更新 | 资产与合同 Service | 在相关的契约或者资产绑定生效、解除时，反向更新所属主体 Party 的 `business_roles` 值。 |
| API扩充查询条件 | `api/v1/party.py` | 支持 `business_role=tenant|owner` 以备前端调用。 |
| 前端列表页分流视图 | `PartyListPage.tsx` | 新增快捷筛选 Tab：全部 / 产权方 / 租户。 |

### Phase 2: 源数据扩展归集结构化（满足 REQ-CUS-001）

| 任务 | 模块 | 说明 |
|------|------|------|
| 建立 1:1 特性表 | `party_business_profiles` | 结构化存储账期特征、风险标记与集团内企业特性。 |
| DB 数据流转升迁 | Alembic Scripts | 将原 metadata JSONB 数据清洗写入到新扩展表及结构中。 |
| Selector组件感知化 | `PartySelector.tsx` | PartySelector 选人支持精确过滤，并在返回后标记人员属性（是否集团内企业）。|

---

## 七、风险与注意事项

### 7.1 数据迁移风险

- metadata 中的数据可能不规范，迁移前需要清洗
- business_roles 字段需要从现有业务表中推导（扫描 assets.owner_party_id、contracts.lessee_party_id 等）

### 7.2 向后兼容

- 现有 API 参数保持不变，新增参数为可选
- 现有前端组件保持向后兼容

### 7.3 性能考量

- `business_roles` JSONB 字段需要 GIN 索引
- 关联数量统计需要缓存或物化视图

---

## 八、总结

### 问题本质

当前用户反馈体验乱象的核心原因是：**前端界面将“静态注册表（MDM技术分类）”通过自然语言暴露给了希望获取“动态业务分类（运营视角）”结果的业务人员。**

### 架构师复核与裁决

1. **直面需求 SSOT 约束**：根据 `requirements-specification.md` 需求文档 (REQ-PTY-001, REQ-CUS-001)，本系统项目不允许脱离 Party 重建一套孤立的业务侧客户/角色管理视图档案。系统强一致性地要求所有附加属性（如配置账期等）集中在关联的同一个 Party 实体上维护。
2. **自我修正与承认妥协**：纯粹的极简读写模型分离（如我第一版提出的激进 DDD 解析架构）虽然理论上最不发生代码冗余，但这**破坏了系统产品本身立项时界定的主档约束目标**。作为一个资深架构应该结合项目的业务本质提供解答。
3. **裁定实施 A+C**：原草案的方案是针对目前矛盾点的最合理迭代方式组合。方案 A（加 `business_roles` jsonb 反范式标签）保障了 UI 查询层高频视角的可用性；方案 C（建立关联配置表避免继续产生垃圾属性）保护了 DB Schema 的长期可维护性。

### 战略实施路径

1. 将 `business_roles` 定位为依赖业务事件更新的派生缓存（Derived Cache）。
2. 将 `party_business_profiles` 定位为为了隔离核心字段污染而作出的 **1:1 垂直物理拆分扩展表**。
3. **落地执行 Phase 1 和 Phase 2 的代码修改安排，即刻可排期研发。**

---

## 九、关键文件索引

### 后端
| 层级 | 文件路径 |
|------|---------|
| Model | `backend/src/models/party.py` |
| Model | `backend/src/models/party_role.py` |
| Model | `backend/src/models/user_party_binding.py` |
| Schema | `backend/src/schemas/party.py` |
| CRUD | `backend/src/crud/party.py` |
| Service | `backend/src/services/party/service.py` |
| Service | `backend/src/services/party_scope.py` |
| API | `backend/src/api/v1/party.py` |

### 前端
| 类型 | 文件路径 |
|------|---------|
| Types | `frontend/src/types/party.ts` |
| Service | `frontend/src/services/partyService.ts` |
| Page | `frontend/src/pages/System/PartyListPage.tsx` |
| Page | `frontend/src/pages/System/PartyDetailPage.tsx` |
| Component | `frontend/src/components/Common/PartySelector.tsx` |
| Utility | `frontend/src/pages/System/partyImport.ts` |

### 文档
| 类型 | 文件路径 |
|------|---------|
| ADR | `docs/architecture/ADR-0001-party-role-architecture.md` |
| 归档方案 | `docs/archive/backend-plans/2026-02-16-party-role-architecture-design.md` |
| 归档方案 | `docs/archive/backend-plans/2026-03-12-req-pty-001-002-party-remediation.md` |
| 需求规范 | `docs/requirements-specification.md` (REQ-PTY-001, REQ-PTY-002) |
