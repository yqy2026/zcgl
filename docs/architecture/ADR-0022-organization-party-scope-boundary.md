# ADR-0022: Organization 与 Party 正交及主体范围单一解析

**状态**：✅ 已实施（2026-08-07）
**决策日期**：2026-08-03
**相关需求**：REQ-SYS-001、REQ-SYS-002、REQ-AUTH-002、REQ-PTY-001、REQ-PTY-002
**实施方案**：[`../archive/backend-plans/2026-08-03-organization-party-scope-cutover.md`](../archive/backend-plans/2026-08-03-organization-party-scope-cutover.md)

---

## 背景

系统同时存在独立的 `organizations` 与 `parties`，但二者没有明确外键。现有组织页面的“主体绑定”实际维护组织成员的 `UserPartyBinding`，并不维护 Organization 与 Party 的关系；后端又通过 ID、`external_ref`、编码和名称猜测组织对应 Party。主体范围解析分别散落在查询过滤、ABAC subject context 和资源上下文中，其中一条路径汇总全部有效绑定，一条展开 `headquarters`，另一条只取一条 `is_primary` 并同时写入 owner/manager，行为互相冲突。

ADR-0001 将 Party 注册表描述为“企业/个人/部门”，以 `PartyHierarchy` 承载组织树，并声称前端组织页已切换到 Party-Role API；当前实现仍保留独立 Organization 模型和页面。该历史结论把内部人员组织、法律业务身份和数据范围授权混在了一起，已不能作为目标模型。

## 决策

### 1. 两条正交身份轴

- `Organization` 只表达内部公司层级、部门和项目组，以及普通业务用户的唯一内部归属。
- `Party` 只表达可独立承担产权、运营、签约或租赁角色的业务主体。
- 内部部门和项目组永远不创建 Party；公司同时具有内部组织身份和外部业务身份时，分别创建 Organization 与 Party 并显式关联。
- Party 类型只保留 `legal_entity` 和 `individual`。删除含糊的 `organization`，不新增 `other_organization`。
- Organization 只能代表已审核且启用的 `legal_entity`，不能代表自然人。

### 2. Organization 直接关系与继承

在 `organizations` 增加一对不可拆分的可空字段：

| 字段 | 规则 |
|---|---|
| `represented_party_id` | 指向已审核、启用、`legal_entity` Party 的显式 FK |
| `represented_party_perspective` | 仅 `owner` 或 `manager` |

数据库约束保证二者同时为空或同时有值。空值表示继承最近的、直接配置了有效关系的上级 Organization；直接配置覆盖继承。继承结果运行时计算，不落库、不批量回写。根节点及整条上级链均无直接配置时，不产生默认主体范围。

失效的直接配置不是“未配置”：若直接关联 Party 后来停用或删除，该关系保留用于审计，当前组织及其继承子树的默认范围失败关闭，并阻断继续向上查找。Organization 自身及全部祖先也必须启用；停用节点同样阻断继承。

同一 Organization 最多代表一个 Party，同一 Party 可以被多个 Organization 代表。不建立 Organization-Party 关联表，也不按名称、普通编码或 `external_ref` 自动生效；批量匹配最多生成候选，必须人工确认 Party ID。

### 3. 用户归属与显式范围

- `users.default_organization_id` 一次重命名为 `users.organization_id`，不保留别名、双写或兼容读。
- User 增加创建后不可变的 `account_type=human|service|system`，不得按用户名或角色猜测例外。每个启用的 `human` 用户必须且只能归属一个启用 Organization，且该组织的完整祖先链必须启用；`service/system` 必须无组织且不继承组织默认范围，`system` 仅由部署初始化或迁移建立。
- 有当前生效的显式 `UserPartyBinding` 时，全部有效显式绑定是完整且唯一的范围来源；组织默认范围不与之合并。
- 显式绑定只保留 `owner` 和 `manager`。删除 `headquarters` 与 `is_primary`；所有有效绑定地位相同，不沿 Party 层级自动扩权。
- 仅当用户确实没有当前生效的显式绑定记录时，才回退 Organization 默认范围。尚未生效、已到期或已明确关闭的绑定不计入当前集合。
- 处于生效时间窗的绑定若因目标 Party 停用或删除而失效，该条不授权并产生配置异常，但不得触发组织回退；其他有效显式绑定继续生效。

### 4. Party 主档收口

- `Party.code` 改为并发安全生成、创建后不可变的内部编码：法人主体使用 `LE-000001`，自然人使用 `NP-000001`。该编码继续作为资产、项目和合同组编码段来源，不承载统一社会信用代码、个人证件号或外部系统 ID。
- `identifier_type` 与 `identifier_value` 成为 Party 正式字段。法人允许 `unified_social_credit_code`、`legal_registration_number`、`foreign_registration_number`，自然人允许 `national_id`、`passport`；草稿可暂缺，提审前必须成对填写并通过格式校验。
- 法人标识规范化保存并按（类型，规范化值）唯一；自然人证件号加密存储、脱敏返回，并按（类型，不可逆指纹）唯一。统一标识不再写入 `metadata`。
- `external_ref` 仅表示外部系统记录 ID；无外部来源时为空。
- 已审核 Party 不允许硬删除。停用和重新启用使用独立动作，展示影响、要求原因并审计；停用保留历史事实但禁止新增业务引用并使授权关系失效，重新启用经确认后恢复保留关系的效力。
- 删除 `PartyHierarchy` 模型、表和 API。未来母子公司、控股或关联企业关系必须按带类型、有效期间的关系重新设计。

### 5. 唯一范围解析与失败语义

建立唯一 `PartyScopeResolver`，统一解析：

1. 当前有效分配内建 `admin` 或 `system_admin` 角色的用户不受主体范围限制；`perm_admin` 与其他管理角色不进入该分支；
2. 当前有效的显式用户绑定；
3. Organization 直接或继承的默认 Party 与视角；
4. 未配置、组织链异常、Party 失效或绑定失效的失败关闭结果。

解析结果必须包含来源、owner/manager Party 集合、服务端 `scope_mode`、来源 Organization、下一次预约生效或到期时间、稳定原因码和结构化异常项。异常项包含节点类型与脱敏标签，数据库节点 ID 只向具备对应管理权限的诊断查看者返回，统一标识、指纹和外部引用永不返回。查询过滤、ABAC、资源上下文、通知、搜索与分析均调用该服务；删除其他回退实现、猜测映射和 `legacy_org_ids`。缓存不得越过下一次授权时间边界。

`view_mode` 是分析与大屏唯一公开视角参数；`scope_mode` 仅为服务端结果。省略 `view_mode` 时，单视角范围自动采用 owner 或 manager，双视角范围解析为 `all`，不得从绑定顺序、已删除的 `is_primary` 或展示偏好猜选。需要单一视角的分析端点拒绝 `all`，其他端点按明确的混合视图抑制契约处理。

业务接口遇到无效范围时返回 `403`，不得伪装成成功空列表：

| 原因码 | 含义 |
|---|---|
| `PARTY_SCOPE_MISSING` | 没有显式范围，也无法从组织获得默认范围 |
| `PARTY_SCOPE_INVALID_ORGANIZATION` | 所属组织或继承链无效 |
| `PARTY_SCOPE_INVALID_PARTY` | 组织直接配置的 Party 无效 |
| `PARTY_SCOPE_INVALID_BINDING` | 当前应生效的显式绑定目标无效 |

### 6. 权限、审计与界面

- `organization:manage_party_scope` 控制组织代表主体、默认视角及会改变继承范围的组织移动。
- `user:manage_party_scope` 控制用户显式绑定。
- 两个动作默认只授予 `admin`、`system_admin`、`perm_admin`。`perm_admin` 仍不得读取业务数据或授予业务角色；主体范围不能绕过角色动作权限。
- 组织范围、组织移动、human 用户调动、用户绑定和 Party 启停均先预览影响。预览返回绑定操作者、目标、规范化完整提议和相关记录版本的短期 opaque `preview_token`；提交携带 token、原因和幂等键并重新校验，过期或状态漂移返回 `409 SCOPE_CHANGE_PREVIEW_STALE`。成功后记录操作人、时间和前后值并立即失效相关授权缓存；批量写在同一事务内全成全败。普通组织或用户资料更新不得写 `parent_id` / `organization_id` 绕过敏感动作。该 token 不是审批，MVP 不增加审批流，也不强制重新登录。
- “组织架构”是 Organization-Party 关系唯一写入口；表单展示直接/继承模式、有效 Party、视角和来源组织。“主体中心”只展示反向 Organization 列表。
- 组织页原“主体绑定”改名为“用户数据范围”，明确其维护的是用户显式覆盖。
- 普通用户可只读查看自己的有效范围；`admin`、`system_admin`、`perm_admin` 可查看任意用户的同一诊断结果。诊断不得暴露自然人证件等敏感值。

### 7. 一次切换

该变更不提供兼容层。迁移前必须列出全部 `party_type=organization` 记录及业务引用：可丢弃数据清理后重建，保留数据逐条明确重分类并同步引用；存在未决记录时迁移中止。后端、前端和数据库迁移在同一发布门禁完成，不能部署会继续按旧字段或旧解析路径运行的中间状态。

## 部分取代 ADR-0001

ADR-0001 的 Party-Role 核心原则仍保留：Party 是唯一业务主体主档，业务角色与主体身份分离，业务对象通过 Party ID 关联，RBAC 与 ABAC 共同授权。

本 ADR 取代 ADR-0001 中以下结论：

- Party 注册表包含内部部门；
- `PartyHierarchy` 承载组织树；
- `headquarters` 通过 Party 下级自动扩权；
- Organization 与 Party 可以靠历史标识、名称或编码隐式映射；
- 前端组织架构页面以 Party-Role API 代替独立 Organization 模型。

## 被否决的方案

| 方案 | 否决原因 |
|---|---|
| 每个内部部门都创建 Party | 把人员组织误作业务身份，污染产权、合同和租赁主体选择。 |
| Organization 可关联多个 Party | 将跨主体特例下沉到组织主档，用户调动会静默改变大量授权。 |
| 显式绑定与组织默认范围自动并集 | 显式绑定无法收窄范围，只会持续扩权。 |
| 按名称、编码或外部引用自动绑定 | Organization 与 Party 编码不在同一命名空间，误匹配会直接造成越权。 |
| 保留 `headquarters` 与 `PartyHierarchy` | 将视角与下级扩展混为一体，新建子主体会让用户静默扩权。 |
| 单独 Organization-Party 关联表 | 已冻结 0..1 基数，额外表只增加有效行竞争和查询复杂度。 |
| 范围异常返回空列表 | 隐藏配置错误，用户与运维无法区分“没有数据”和“授权链失效”。 |
| 分阶段双写兼容 | 当前处于 0→1，双轨解析会延长最危险的授权歧义窗口。 |

## 影响

这是模型、API、鉴权和前端的协调切换。实现必须先用测试锁定范围优先级、继承阻断、时间边界和 403 原因码，再迁移数据和删除旧路径。完成前，REQ-SYS-001、REQ-SYS-002、REQ-AUTH-002、REQ-PTY-001、REQ-PTY-002 均不得标记为“已有证据”。
