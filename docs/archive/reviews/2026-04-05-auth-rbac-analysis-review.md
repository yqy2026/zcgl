# Auth-RBAC 分析文档审阅报告（第三版 — 架构重审，历史快照）

> Historical snapshot. 本文为 2026-04-05 一次性审阅报告，不再作为当前授权架构基线。当前 API、权限与数据范围契约以 `docs/specs/api-contract.md` 为准，需求状态与实现证据以 `docs/traceability/requirements-trace.md` 为准。

> 审阅日期: 2026-04-05
> 第三版修订日期: 2026-04-05（修正 v1/v2 的三处重大架构认知错误）
> 审阅对象: `docs/architecture/auth-rbac-analysis.md`（2026-04-05 初稿）
> 对照标准: `docs/requirements-specification.md`§5、`backend/scripts/setup/init_rbac_data.py`、实际代码实现
> 结论: v1/v2 审阅对 ABAC 的定位判断存在重大错误。本版从第一性原理重新分析了实际授权决策流程，修正了三处架构层面的错误认知，并据此调整全部优先级建议。

---

## 〇、v1/v2 审阅勘误

### 0.1 v1 事实性错误（已在 v2 修正，此处保留记录）

| # | v1 错误断言 | 实际代码事实 |
|---|-------------|-------------|
| **E1** | Level 值为 100/80/60/40/20 | `init_rbac_data.py` 第 67-108 行：admin=1, manager=2, user=3, viewer=4。原 analysis 文档正确 |
| **E2** | user 只有 4 个 read 权限 | 分配逻辑为 `action in ["read"]`，对全部 14 个资源中含 read 的权限授予。实际 **13 个 `:read` 权限** |
| **E3** | viewer 比 user 少 rent_contract:read | viewer 的分配逻辑与 user 完全相同，权限列表 **100% 一致** |
| **权限总数** | 文档与 v1 均称 62 个 | 实际 52 个（14 个资源类型，notification 未生成权限） |

### 0.2 v2 架构认知错误（本版修正）

这是本审阅最关键的勘误。v2 的三层模型和 ABAC 定位判断建立在错误的代码理解之上。

| # | v2 错误声称 | 实际事实 | 证据 |
|---|-------------|---------|------|
| **W1** | "ABAC 是死代码，应降级为 vNext" | `require_authz`（ABAC 入口）是**主要授权机制**——在 50 个 API 文件中被调用 **338 次**。旧的 `require_permission` **从未**被 API 端点使用。 | `grep -r "require_authz" backend/src/api/` = 338 处；`grep -r "require_permission" backend/src/api/` = 0 处 |
| **W2** | "三层模型：L1 RBAC, L2 Party Scoping, L3 ABAC" | 实际架构是 **ABAC-primary, RBAC-fallback**。Party Scoping 是 ABAC 策略条件的内部机制（通过 `SubjectContext.owner_party_ids` / `manager_party_ids`），不是独立层。 | `backend/src/services/authz/service.py` 第 60-120 行：`check_access()` 先评估 ABAC 策略，无匹配时才 fallback 到 RBAC |
| **W3** | "`init_rbac_data.py` 不创建 ABAC 策略是正确的——不是遗漏" | 这**是**一个缺口。`abac_role_policies`（策略到角色的绑定表）在标准部署中**从未被填充**。每个非管理员请求都 fallback 到 RBAC。 | Alembic 迁移创建了 7 个 `ABACPolicy` + `ABACPolicyRule`，但**零** `ABACRolePolicy` 记录。`init_rbac_data.py` 也不创建绑定。 |

**影响评估**：W1/W2/W3 导致 v2 的优先级建议完全颠倒——将 ABAC 定位为"vNext 不需要"，而实际上 ABAC 框架已经是系统的主入口，只是数据绑定缺失导致它空转并 fallback 到 RBAC。正确的做法是**P0 修正 RBAC（当前实际生效的层），P1 激活 ABAC（补充绑定数据）**。

---

## 一、实际授权架构：ABAC-primary, RBAC-fallback

### 1.1 授权决策流程（从代码逐行还原）

```
每个 API 端点
  → Depends(require_authz(action="read", resource_type="asset"))
    → AuthzPermissionChecker.__call__()                          # auth.py
      → authz_service.check_access(user, action, resource_type, resource_context)
        │                                                          # service.py
        ├─ [1] Admin bypass?
        │     user.is_superuser == True → ALLOW (reason: rbac_admin_bypass)
        │
        ├─ [2] 加载用户角色绑定的 ABAC 策略
        │     crud: get_policies_by_role_ids()
        │     → INNER JOIN abac_role_policies ON role_id
        │     → 当前状态：abac_role_policies 表为空 → 返回空列表
        │
        ├─ [3] AuthzEngine.evaluate_with_reason(policies, context)
        │     → 空策略列表 → 返回 {allowed: False, reason: "deny_by_default"}
        │
        ├─ [4] Fallback 判定：
        │     engine_result.reason == "deny_by_default"
        │     AND has_matching_policy_rule == False
        │     → 进入 RBAC fallback 分支
        │
        ├─ [5] RBAC fallback:
        │     rbac_service.check_permission(user, f"{resource_type}:{action}")
        │     → 检查 user → roles → permissions 静态映射
        │     → 当前状态：这是实际授权所有非管理员用户的机制
        │
        └─ [6] Authenticated default (最后兜底):
              action 在 AUTHENTICATED_DEFAULT_ACTIONS 中？
              → 仅 notification:read
              → ALLOW (reason: authenticated_default_action)
```

### 1.2 关键架构事实

| 事实 | 含义 |
|------|------|
| `require_authz` 是唯一被 API 使用的授权入口（338 次） | ABAC 框架是系统的**主骨架**，不是可有可无的附加层 |
| `abac_role_policies` 表始终为空 | ABAC 策略虽然存在（7 个模板 + 规则），但从未绑定到角色，导致所有评估返回 `deny_by_default` |
| RBAC fallback 是当前唯一生效的授权判定 | 非管理员用户的权限完全由 `init_rbac_data.py` 中的角色-权限映射决定 |
| Party Scoping 在 CRUD 层实现，与 ABAC/RBAC 独立 | 列表端点的数据隔离不经过 `check_access()`，由 CRUD 层的 `party_id` 过滤实现 |

### 1.3 ABAC 适用性第一性原理分析

在决定 ABAC 的优先级之前，需要从第一性原理回答：**本系统的授权需求是否超出了 RBAC 的表达能力？**

#### RBAC 能表达什么

RBAC 回答的是：**"此角色是否拥有对此资源类型的此操作权限？"** — 即 `(role, resource_type, action) → allow/deny`。这是一个静态映射，不依赖运行时属性。

#### ABAC 额外能表达什么

ABAC 回答的是：**"在当前上下文条件下，是否允许此操作？"** — 即 `(subject_attrs, resource_attrs, action, env_attrs) → allow/deny`。它可以表达：
- 时间窗口（工作日才能审批）
- 金额阈值（超过 100 万需要二级审批）
- 字段级可见性（普通用户不能看租金字段）
- 资源所有权（只能修改自己创建的合同）
- 条件组合（运营方用户只能修改自己管理的资产，且金额不超过 X）

#### 本系统需要哪些

| 授权需求 | RBAC 能否满足 | 需要 ABAC？ |
|----------|:------------:|:-----------:|
| 角色-操作权限（运营管理员可编辑资产） | 是 | 否 |
| Party 数据隔离（用户只能看到绑定主体的数据） | 否（需要行级过滤） | 部分（ABAC 可做单资源检查，但不能修改 SQL 查询） |
| 统计口径按绑定类型区分 | 否（需要业务逻辑） | 否（这是业务逻辑，不是授权） |
| 大额合同审批需要更高级别（vNext） | 否 | 是 |
| 字段级可见性（vNext） | 否 | 是 |

#### 结论

- **MVP 阶段**：RBAC 满足操作级权限控制，Party 数据隔离由 CRUD 层完成。ABAC 不是 MVP 的硬性需求。
- **但 ABAC 框架不是死代码**：它是系统的主入口，已经在每个请求上运行。正确做法不是"降级到 vNext"，而是：
  1. P0：确保 RBAC fallback 正确（角色、权限、资源类型全覆盖）
  2. P1：激活 ABAC 数据策略绑定，为单资源端点提供纵深防御
  3. P2：清理真正的死代码（从未被调用的旧 auth checker）

### 1.4 ABAC 不能做列表过滤 — 架构约束

这是一个关键的架构约束，v1/v2 均未提及：

- ABAC `check_access()` 针对**单个资源**返回 allow/deny
- 列表端点（`GET /assets`）返回的是一个集合，ABAC 无法修改 SQL WHERE 条件
- 因此，Party 数据隔离**必须在 CRUD 层实现**（通过 `party_id IN (...)` 过滤）
- ABAC 对单资源端点（`GET /assets/{id}`、`PUT /assets/{id}`）可提供纵深防御：CRUD 层先过滤列表，ABAC 再在单资源访问时做二次校验

**当前 CRUD 层的 party filtering 是唯一生效的数据隔离机制，审计其正确性是 P0。**

---

## 二、核心问题：角色体系与需求不对齐

**此结论经三次复核均确认正确，是本系统最关键的 RBAC 问题。**

### 2.1 需求定义（§5.1）的 5 个业务角色

| 需求角色 | 职责边界 |
|----------|----------|
| **运营管理员** | 资产、项目、合同组与台账维护 |
| **权限管理员** | 角色授权、组织与字典配置 |
| **业务审核人** | 关键数据复核、审核与反审核 |
| **管理层** | 查看统计看板与导出报表（只读） |
| **只读查看者** | 仅可查看授权范围数据，不允许新增/编辑/审核/作废 |

### 2.2 实际实现（`init_rbac_data.py`）的 7 个系统角色

| 实现角色 | Level | 实际权限分配逻辑 | 实际权限数 |
|----------|-------|-----------------|-----------|
| `admin` | 1 | 全部权限 | **52** |
| `manager` | 2 | `not resource.startswith("system")` | **49**（去掉 system:admin/manage/backup） |
| `asset_manager` | 2 | `resource in ["asset", "statistics"]` | **8**（asset:5 + statistics:3） |
| `project_manager` | 2 | `resource in ["project", "statistics"]` | **8**（project:5 + statistics:3） |
| `auditor` | 2 | `resource in ["audit", "statistics"]` | **6**（audit:3 + statistics:3） |
| `user` | 3 | `action in ["read"]` | **13**（全部含 read 的资源） |
| `viewer` | 4 | `action in ["read"]` | **13**（与 user **完全相同**） |

### 2.3 映射差距分析

| 需求角色 | 映射到 | 问题 | 严重性 |
|----------|--------|------|--------|
| **运营管理员** | `asset_manager` + `project_manager` | 拆成两个角色，且**缺少 `contract_group:*`、`rent_contract:create/update/delete`、`rent_ledger:*` 权限**（这些资源本身就缺失）。运营管理员应能维护合同组和台账 | **P0** |
| **权限管理员** | 无对应角色 | 只能用 `admin`（全部权限）来做角色授权和组织配置，**违反最小权限原则** | **P0** |
| **业务审核人** | 无对应角色 | `auditor` 只有 `audit:read/export/create`，**没有 `approval:approve/reject` 等审批操作权限**。审批流代码已实现，但无角色可用 | **P0** |
| **管理层** | `manager` | `manager` 拥有除 `system:*` 外全部 CRUD，但需求仅要求"查看看板+导出报表"。**权限严重过大** | **P1** |
| **只读查看者** | `viewer` | 拥有 13 个 `:read` 权限覆盖面广，但缺少尚未定义的权限资源（`contract_group:read`、`rent_ledger:read` 等），数据可见范围比需求窄 | **P1** |

### 2.4 额外角色评估

- `admin`（系统管理员）：需求 §5.2 提到"系统管理员（集团资产部）可查看全部数据"，系统必需，合理
- `auditor`（审计员）：需求 §5.2 说"外部审计用户可查看全部数据"，但 `auditor` 仅有 `audit:*` + `statistics:*`（6 个权限），**不能查看全部数据**，与需求矛盾
- `user`（普通用户）：需求中无对应角色，权限与 `viewer` 完全相同，价值为零

### 2.5 关键发现汇总

- `user` 和 `viewer` 的分配逻辑完全相同，权限列表 100% 重叠，**其中一个是多余的**
- `manager` 拥有除 `system:*` 外的全部 49 个权限（含所有 CRUD），远超需求"只读+导出"
- analysis 文档 §9.1 列出 8 条"优势"，§9.2 列出 9 条"风险"，但**没有一条提到角色定义与需求不匹配**这个根本性问题

---

## 三、权限资源缺口（远超 v2 评估）

### 3.1 缺口范围

`require_authz` 使用了约 **30 个 resource_type**，但 `init_rbac_data.py` 只定义了 **14 个**有 RBAC 权限的资源。以下按业务重要性分为两组：

#### 3.1.1 业务资源缺失（非管理员用户需要 — P0）

| 缺失资源 | 对应 API/功能 | 需求依据 | 影响 |
|----------|---------------|----------|------|
| `contract_group` | 合同组 CRUD | §5.1 运营管理员、§6.6 REQ-CG-001 | 运营管理员核心功能无权限保护 |
| `ledger` | 租金台账 | §5.1 运营管理员、§6.7 REQ-LED-001 | 台账操作无权限控制 |
| `party` | 主体管理 CRUD | §5.3 客户定义 | 主体 CRUD 无权限保护 |
| `customer` | 客户视图 CRUD | §5.3、§6.8 REQ-CUST-001 | 客户档案无权限保护 |
| `document` | 文档/附件管理 | §6.5 REQ-DOC-001 | 文档上传下载无权限控制 |
| `search` | 全局搜索 | §6.10 REQ-SCH-001 | 搜索无权限定义 |
| `dictionary` | 数据字典配置 | §5.1 权限管理员 | 字典维护无权限保护 |
| `occupancy` | 入驻管理 CRUD | 资产入驻管理 | 入驻操作无权限控制 |
| `custom_field` | 自定义字段管理 | 自定义字段配置 | 无权限保护 |
| `analytics` | 数据分析/报表 | 统计分析功能 | **名称不匹配**：API 使用 `analytics` 但 RBAC 定义的是 `statistics` |
| `enum_field` | 枚举字段管理 | 字典/枚举相关 | 无权限保护 |
| `collection` | 集合管理 | 数据集合功能 | 无权限保护 |
| `contact` | 联系人管理 | 联系人信息维护 | 无权限保护 |

#### 3.1.2 管理员专用资源（由 `require_admin` 覆盖 — RBAC 定义可选）

以下资源的端点使用 `require_admin` 装饰器，只有超级管理员可访问，RBAC 权限定义为可选（管理员已 bypass 所有检查）：

`system_settings`, `system_monitoring`, `operation_log`, `task`, `error_recovery`, `history`, `backup`, `excel_config`, `llm_prompt`

### 3.2 `analytics` vs `statistics` 名称不匹配

这是一个隐蔽的 bug：
- API 端点使用 `require_authz(resource_type="analytics")`
- `init_rbac_data.py` 定义的权限资源是 `statistics`
- RBAC fallback 检查 `analytics:read` 权限 → 不匹配 `statistics:read` → **deny**
- 结果：非管理员用户可能无法访问数据分析功能，即使角色分配了 `statistics:read`

需要确认 API 端点实际使用的是 `analytics` 还是 `statistics`，然后统一命名。

---

## 四、ABAC 数据策略现状详细分析

### 4.1 已有策略模板

Alembic 迁移创建了 7 个 ABAC 策略模板：

| 策略 | 包含的规则 | 用途 |
|------|-----------|------|
| 产权方资产数据策略 | owner_party_id 匹配检查 | 产权方只能访问自己的资产 |
| 运营方资产数据策略 | manager_party_id 匹配检查 | 运营方只能访问自己管理的资产 |
| 产权方合同数据策略 | 通过合同关联的 party_id 检查 | 合同数据隔离 |
| 运营方合同数据策略 | 同上，manager 维度 | 合同数据隔离 |
| 产权方统计数据策略 | 统计口径过滤 | 产权方统计视图 |
| 所有权数据策略 | 产权关系过滤 | 产权证数据隔离 |
| 入驻占用数据策略 | 入驻关系过滤 | 入驻数据隔离 |

### 4.2 缺失的绑定

这些策略需要通过 `ABACRolePolicy` 记录绑定到角色才能生效。当前绑定数据的创建途径：

| 途径 | 状态 |
|------|------|
| Alembic 迁移 | **未创建**（只创建了策略模板和规则，没有创建角色绑定） |
| `init_rbac_data.py` | **未创建** |
| Admin API `PUT /roles/{role_id}/data-policies` | 可用，但需要管理员手动操作 |
| `backfill_role_policies.py` 脚本 | 可用，但需要手动运行 |

### 4.3 激活 ABAC 的预期效果

如果正确绑定策略到角色：
- **单资源端点**（`GET /assets/{id}`）：ABAC 策略会在 RBAC 之前生效，提供基于 party 绑定的纵深防御
- **列表端点**（`GET /assets`）：ABAC 无效果（不能修改 SQL），数据隔离仍完全依赖 CRUD 层
- **净效果**：对单资源访问增加一层安全检查，防止绕过 CRUD 层 party 过滤直接访问他人数据

### 4.4 一个 Bug：ABAC deny 被 authenticated_default 覆盖

`AuthzService.check_access` 中有一个逻辑问题：

```python
elif engine_result.reason == "deny_by_default" and not has_matching_policy_rule:
    # Fallback to RBAC — 这个分支正常
    ...
elif action in AUTHENTICATED_DEFAULT_ACTIONS:
    # 兜底：notification:read 默认允许
    # BUG: 如果 ABAC 显式 deny 但 action 是 notification:read，
    #       deny 会被覆盖为 allow
    ...
```

当 ABAC 策略**显式 deny**（`has_matching_policy_rule=True`）但 action 在 `AUTHENTICATED_DEFAULT_ACTIONS` 中时，deny 决定会被最后的 `elif` 分支覆盖为 allow。对 `notification:read` 来说这是一个安全漏洞（虽然当前因为 ABAC 策略未绑定，这个分支不会被触发）。

---

## 五、CRUD 层 Party Filtering 审计需求

### 5.1 为什么这是 P0

Party filtering 是当前**唯一生效的数据隔离机制**：
- ABAC 策略未绑定 → 不起作用
- RBAC 只控制操作权限（"能不能读资产"），不控制数据范围（"能读哪些资产"）
- 数据隔离完全依赖 CRUD 层的 `party_id IN owner_party_ids` 过滤

如果某个 CRUD 函数遗漏了 party 过滤，该端点就是一个数据泄露点。

### 5.2 审计范围

需要逐一检查所有涉及 party 数据的 CRUD 函数：
- `crud/asset.py` — 资产列表/详情查询
- `crud/rent_contract.py` — 合同列表/详情
- `crud/project.py` — 项目列表/详情
- `crud/party.py` — 主体列表
- `crud/property_certificate.py` — 产权证
- `crud/ownership.py` — 产权关系
- 所有其他涉及多租户数据的 CRUD 函数

### 5.3 审计检查项

对每个 CRUD 函数确认：
1. 是否接收 `party_ids` 参数并在查询 WHERE 条件中使用？
2. 非管理员用户调用时，`party_ids` 是否从 `UserPartyBinding` 正确传入？
3. 是否有绕过路径（如直接用 ID 查询而不检查 party 归属）？

---

## 六、数据范围/视角机制与需求矛盾

### 6.1 需求（§5.2，2026-04-03 更新）

> 数据范围由用户的**主体绑定（UserPartyBinding）**自动决定，不需要用户手动选择或切换。

### 6.2 需求自身矛盾

§5.2 说"不需要手动切换"，§8.3 说"全局视角切换入口清晰可见，且支持手动切换"。§5.2 有"2026-04-03 业务访谈确认，替代原'全局视角切换'设计"标注，说明 §8.3 是旧需求未更新。

### 6.3 代码实现

代码支持通过 `X-Perspective` 请求头手动选视角（`owner`/`manager`/`all`）。这与 §5.2 不矛盾——`X-Perspective` 可保留为技术实现细节，前端自动设置而非由用户手动选择。

### 6.4 建议

更新 §8.3 为"数据范围自动注入，用户无需手动切换"，与 §5.2 保持一致。

---

## 七、缓存机制的遗漏风险

### 7.1 Bug：`compute_roles_hash()` 不含 party bindings

`compute_roles_hash()` 只对 `role_ids` 做哈希。当用户的 Party 绑定变更但角色不变时，缓存不会失效。用户在绑定变更后仍看到旧数据范围，直到缓存过期（L1 5秒 / L2 300秒）。

结合需求 §5.2 的组织规模（20+ 产权方、4-5 运营方），这可能导致 **5 分钟窗口期的数据泄露**。

### 7.2 建议

将 `party_binding_ids` 或 `party_binding_hash` 纳入缓存键计算。

---

## 八、统计口径实现未评估

analysis 文档完全没有评估统计口径。需求 §5.2 定义了详细规则：
- 产权方用户：承租模式收入 = 内部租金；代理模式收入 = 终端租户租金
- 运营方用户：承租模式 = 终端租金收入 + 承租租金支出；代理模式 = 服务费收入

文档只提到 `statistics:read/export` 两个权限，未分析系统是否根据 `owner`/`manager` 绑定类型自动选择正确的统计口径。统计口径一致性是 MVP 成功指标之一（§3.2），这是 analysis 文档的重大遗漏。

---

## 九、修订后的优先级建议

### P0 — 阻塞业务正确性（RBAC 修正 + 数据隔离审计）

| # | 事项 | 理由 | 预计工时 |
|---|------|------|----------|
| 1 | **重新定义系统角色与权限映射，对齐需求 §5.1** | 运营管理员缺合同组/台账权限，业务审核人角色缺失，管理层权限过大，权限管理员角色缺失，user/viewer 100% 重叠 | 1 天 |
| 2 | **补充缺失业务权限资源**（13 个缺失 resource_type） | 核心业务域缺少权限定义，非管理员用户访问这些资源时 RBAC fallback 全部 deny | 0.5 天 |
| 3 | **修复 `analytics` vs `statistics` 名称不匹配** | 非管理员用户可能无法访问数据分析功能 | 2h |
| 4 | **审计 CRUD 层 party filtering** | 当前唯一生效的数据隔离机制，如有遗漏即为数据泄露 | 1 天 |

### P1 — 安全加固与 ABAC 激活

| # | 事项 | 理由 | 预计工时 |
|---|------|------|----------|
| 5 | **激活 ABAC 数据策略**（种子化 `abac_role_policies` 绑定） | ABAC 框架是系统主入口，策略模板已就绪，只差绑定数据。激活后为单资源访问提供纵深防御 | 0.5 天 |
| 6 | **缓存键纳入 party bindings 哈希** | 绑定变更不触发缓存失效，可能导致 5 分钟窗口期数据泄露 | 0.5 天 |
| 7 | **修复 ABAC deny 被 authenticated_default 覆盖的 bug** | ABAC 显式 deny 可被绕过 | 2h |
| 8 | **解决需求矛盾（§5.2 vs §8.3）** | 以 §5.2 为准，更新 §8.3 | 0.5h |

### P2 — 技术债务清理

| # | 事项 | 理由 | 预计工时 |
|---|------|------|----------|
| 9 | **清理从未使用的 auth checker 类** | `require_permission`、`PermissionGrant`、`ResourcePermission`、`OrganizationPermissionChecker` 等 4+ 个类从未被 API 调用 | 1-2 天 |
| 10 | 前端统一迁移到 capabilities，移除 permissions 兼容层 | 消除双轨制 | 1 天 |
| 11 | 前端实现全局路由级权限守卫 | 防止未授权 URL 直接访问 | 0.5 天 |

### vNext — 不在 MVP 范围

| # | 事项 | 理由 |
|---|------|------|
| 12 | ABAC 高级策略（时间窗口、金额阈值、字段级可见性） | RBAC + Party Scoping + 基础 ABAC 数据策略已满足 MVP |
| 13 | OAuth/SSO 支持 | 企业集成需求 |
| 14 | 集团汇总视图 | 需求 §5.2 已明确为 vNext |

---

## 十、建议的角色重新设计方案

### 10.1 系统角色（6 个，`is_system_role=True`）

| 角色名 | 显示名 | Level | 权限范围 | 对应需求 |
|--------|--------|-------|----------|----------|
| `system_admin` | 系统管理员 | 1 | 全部权限 | 系统必需（§5.2 "集团资产部"） |
| `ops_admin` | 运营管理员 | 2 | 业务域 CRUD + customer/party/search 只读 + statistics RE + document CRUD | §5.1 运营管理员 |
| `perm_admin` | 权限管理员 | 2 | user/role/organization/permission_grant CRUD + dictionary RW + audit RE + system:manage | §5.1 权限管理员 |
| `reviewer` | 业务审核人 | 3 | approval:* + 所有业务域 :read + audit:read | §5.1 业务审核人 |
| `executive` | 管理层 | 4 | 所有业务域 :read + statistics:RE + approval:read | §5.1 管理层（只读+导出） |
| `viewer` | 只读查看者 | 5 | 业务域 :read（不含 system, user, role, approval, dictionary） | §5.1 只读查看者 |

### 10.2 保留为可选自定义角色

`asset_manager`、`project_manager` 保留为可选细分角色（`is_system_role=False`），供权限管理员按需创建分配。

### 10.3 废弃角色

| 角色 | 处置 | 理由 |
|------|------|------|
| `admin` | 重命名为 `system_admin` | 更明确的语义 |
| `manager` | 废弃，由 `executive` 替代 | 权限从 49 个缩减到只读+导出 |
| `user` | 废弃 | 与 `viewer` 100% 重叠，需求无对应角色 |
| `auditor` | 废弃，外审用户设为 `viewer` + 不受 Party 约束 | 需求 §5.2："外部审计用户可查看全部数据" |

### 10.4 关键设计原则

1. **一个需求角色 = 一个系统角色**：避免组合多角色
2. **最小权限原则**：管理层只有 read + export
3. **审批权限独立**：`approval:*` 只给 reviewer，运营管理员不应自审自批（职责分离）
4. **权限管理员 ≠ 系统管理员**：权限管理员管用户和角色，但不能操作业务数据或 system:admin/backup
5. **Level 值连续递增**：1（最高）到 5（最低）

---

## 十一、文档结构建议（针对 analysis 文档）

| # | 建议 | 理由 |
|---|------|------|
| 1 | 新增"需求对齐分析"节 | 只做了代码分析，没有与需求交叉验证 |
| 2 | 修正授权架构描述为"ABAC-primary, RBAC-fallback" | 当前描述暗示"RBAC + ABAC 二层"，不准确 |
| 3 | §3.2.2 修正权限总数为 52 | 当前声称 62 与实际不一致 |
| 4 | 新增"ABAC 策略绑定现状"节 | 明确说明策略存在但未绑定的事实 |
| 5 | §9.3 优先级按"RBAC 修正 → 数据隔离审计 → ABAC 激活 → 技术债务"重排 | 当前排序偏技术视角 |
| 6 | 附录增加"缺失权限资源完整清单" | 从 7 个扩展到 13+ 个 |

---

## 十二、综合评分与总结

### 总体评分: 6/10（从 v2 的 7/10 下调）

下调原因：v2 的三层模型和 ABAC 定位判断本身就是错误的，该错误如果被执行会导致 ABAC 框架被错误地降级。

| 维度 | 评价 |
|------|------|
| **代码描述准确性** | 较高。认证流程、RBAC 检查链路、ABAC 引擎、Party 数据隔离的描述与代码基本一致，权限总数有误（62→52） |
| **架构判断准确性** | **v2 存在重大错误**。"三层模型"和"ABAC 是死代码"均不正确。实际是 ABAC-primary/RBAC-fallback |
| **需求对齐分析** | **严重缺失**。全文未与 §5 做交叉验证，最关键的角色不匹配问题未被发现 |
| **优先级建议** | v2 将 ABAC 降为 vNext 不妥。应为 P0 修 RBAC，P1 激活 ABAC 绑定 |
| **权限资源覆盖** | v2 识别了 7 个缺失资源，实际缺失 **13+ 个**业务资源 |
| **数据隔离** | **未评估** CRUD 层 party filtering 的正确性，这是唯一生效的数据隔离机制 |
| **统计口径** | 完全未评估，这是 MVP 成功指标之一 |

### 后续行动

1. 按 `docs/plans/2026-04-05-rbac-role-realignment.md` 执行角色权限重定义（P0）
2. 审计 CRUD 层 party filtering（P0）
3. 激活 ABAC 数据策略绑定（P1）
4. 更新 `requirements-specification.md` §8.3（P1）
5. 清理死代码（P2）
