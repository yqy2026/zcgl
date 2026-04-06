# 🔄 RBAC 角色权限重定义与授权加固实施计划

> 状态：🔄 活跃
> 创建日期：2026-04-05
> 第三版修订日期：2026-04-05（修正架构认知错误后全面重写）
> 需求依据：`docs/requirements-specification.md` §5.1 / §5.2 / §5.3
> 分析依据：`docs/architecture/auth-rbac-analysis-review.md`（第三版）
> 涉及 REQ：REQ-AUTH-001, REQ-AUTH-002

---

## 1. 背景与目标

### 1.1 问题摘要

经第三版架构审阅确认，当前授权系统存在以下问题：

**架构事实**：系统采用 **ABAC-primary, RBAC-fallback** 架构。`require_authz`（ABAC 入口）是主要授权机制（338 次调用），但 ABAC 策略虽有模板和规则，`abac_role_policies`（角色-策略绑定表）**从未被填充**，导致所有非管理员请求 fallback 到 RBAC。

**P0 阻塞问题**：
1. **角色-需求不对齐**：代码定义 7 个系统角色 vs 需求 5 个业务角色，映射关系不成立
2. **权限资源缺失**：`require_authz` 使用约 30 个 resource_type，但只有 14 个有 RBAC 权限定义。缺失 13+ 个业务资源
3. **角色冗余**：`user` 和 `viewer` 权限 100% 重叠；`manager` 拥有 49 个权限（需求仅要求只读+导出）
4. **`analytics` vs `statistics` 名称不匹配**：API 使用 `analytics`，RBAC 定义 `statistics`，非管理员用户可能无法访问分析功能
5. **CRUD 层 party filtering 未经审计**：这是当前唯一生效的数据隔离机制，如有遗漏即为数据泄露

**P1 安全问题**：
6. **ABAC 数据策略未激活**：7 个策略模板已就绪，只差角色绑定。激活后可为单资源访问提供纵深防御
7. **缓存键不含 party bindings**：绑定变更不触发缓存失效，可能导致 5 分钟窗口期数据泄露
8. **ABAC deny 可被 authenticated_default 覆盖**：安全漏洞
9. **需求矛盾**（§5.2 vs §8.3）

### 1.2 目标

1. 将系统角色从"技术导向的 7 角色"重定义为"需求导向的 6 角色"，对齐 §5.1
2. 补齐全部缺失业务权限资源，使 RBAC fallback 能覆盖所有 API 端点
3. 审计并确保 CRUD 层 party filtering 对所有多租户数据生效
4. 激活 ABAC 数据策略，为单资源访问提供纵深防御
5. 修复缓存、命名不匹配等安全问题

### 1.3 范围约束

- **不改前端路由或页面逻辑**（Phase 1 & 2），仅改后端角色/权限定义、种子数据和授权逻辑
- **保持 `require_authz` 为唯一授权入口**——架构良好，不需要改
- **不新增 ABAC 高级策略**（时间窗口/金额阈值等归 vNext）

---

## 2. 实际授权架构（供实施参考）

### 2.1 授权决策流程

```
API 端点
  → Depends(require_authz(action, resource_type))
    → AuthzPermissionChecker.__call__()
      → authz_service.check_access()
        ├─ [1] Admin bypass → ALLOW
        ├─ [2] 加载 ABAC 策略（JOIN abac_role_policies）
        │     → 当前：空表 → 空列表
        ├─ [3] AuthzEngine 评估 → deny_by_default（无策略）
        ├─ [4] Fallback: RBAC check_permission()
        │     → 当前：这是实际授权路径
        └─ [5] 兜底: authenticated_default（仅 notification:read）
```

### 2.2 数据隔离层（独立于上述流程）

```
列表端点（GET /assets）
  → CRUD 层 party filtering（WHERE party_id IN owner_party_ids）
  → 这是唯一生效的数据隔离，ABAC 不参与列表过滤

单资源端点（GET /assets/{id}）
  → CRUD 层先查询
  → ABAC 可做二次校验（激活后）
```

---

## 3. 目标角色定义

### 3.1 从 7 角色到 6 角色

| 现有角色 | 处置 | 目标角色 | 对应需求 §5.1 |
|----------|------|----------|--------------|
| `admin` | 重命名 | `system_admin` | 系统管理员（§5.2 集团资产部） |
| `manager` | **废弃** | `executive`（新建） | 管理层（只读+导出） |
| `asset_manager` | 降为可选 | — | 可选细分角色 |
| `project_manager` | 降为可选 | — | 可选细分角色 |
| `auditor` | **废弃** | — | 外审 → viewer 不受 Party 约束 |
| `user` | **废弃** | — | 需求无对应 |
| `viewer` | 保留 | `viewer` | 只读查看者 |
| — | **新建** | `ops_admin` | 运营管理员 |
| — | **新建** | `perm_admin` | 权限管理员 |
| — | **新建** | `reviewer` | 业务审核人 |

### 3.2 目标角色权限矩阵

**资源类型**（现有 14 + 新增资源 = 全量覆盖）

下表中：`*` = 全部操作（read/create/update/delete）；`R` = read only；`RE` = read + export；`RW` = read + write；`—` = 无权限

| 资源 | system_admin | ops_admin | perm_admin | reviewer | executive | viewer |
|------|:-----------:|:---------:|:----------:|:--------:|:---------:|:------:|
| **asset** | * | * | — | R | R | R |
| **project** | * | * | — | R | R | R |
| **contract_group** ⬆ | * | * | — | R | R | R |
| **rent_contract** | * | * | — | R | R | R |
| **ledger** ⬆ | * | * | — | R | R | R |
| **property_certificate** | * | * | — | R | R | R |
| **ownership** | * | * | — | R | R | R |
| **occupancy** ⬆ | * | * | — | R | R | R |
| **customer** ⬆ | * | R | — | R | R | R |
| **party** ⬆ | * | R | — | R | R | R |
| **contact** ⬆ | * | * | — | R | R | R |
| **document** ⬆ | * | * | — | R | R | R |
| **search** ⬆ | * | R | — | R | R | R |
| **analytics** ⬆¹ | * | RE | — | RE | RE | R |
| **approval** | * | — | — | * | R | — |
| **audit** | * | — | RE | R | R | — |
| **user** | * | — | * | — | — | — |
| **role** | * | — | * | — | — | — |
| **organization** | * | — | * | — | — | — |
| **permission_grant** | * | — | * | — | — | — |
| **dictionary** ⬆ | * | — | RW | — | — | — |
| **custom_field** ⬆ | * | — | RW | — | — | — |
| **enum_field** ⬆ | * | — | RW | — | — | — |
| **collection** ⬆ | * | * | — | R | R | R |
| **system** | * | — | manage | — | — | — |
| **notification** | * | R | R | R | R | R |

⬆ = 新增权限资源
¹ = 需确认 API 端点实际使用的是 `analytics` 还是 `statistics`，然后统一命名

### 3.3 Level 值定义

| Level | 角色 | 语义 |
|-------|------|------|
| 1 | `system_admin` | 最高权限，全系统 |
| 2 | `ops_admin`, `perm_admin` | 管理级，各管各的域 |
| 3 | `reviewer` | 审核级，读+审批 |
| 4 | `executive` | 只读+导出 |
| 5 | `viewer` | 纯只读 |

---

## 4. 实施任务分解

### Phase 1：P0 — 角色权限重定义 + 数据隔离审计（预计 3 天）

#### Task 1.1：确认 `analytics` vs `statistics` 命名

- **动作**：搜索 `backend/src/api/v1/` 中所有 `require_authz` 调用，确认 analytics 相关端点实际使用的 resource_type 名称
- **决策**：统一为一个名称（推荐 `analytics`，更贴合功能语义）
- **Done when**：明确命名决策，记录在本计划中

#### Task 1.2：新增权限资源定义

- **文件**：`backend/src/security/permissions.py`
- **动作**：新增缺失业务资源的权限常量。需新增的资源：
  - `contract_group`: read, create, update, delete
  - `ledger`: read, create, update, delete
  - `party`: read, create, update, delete
  - `customer`: read, create, update, delete
  - `document`: read, create, update, delete
  - `search`: read
  - `dictionary`: read, write
  - `occupancy`: read, create, update, delete
  - `custom_field`: read, create, update, delete（或 read, write）
  - `analytics`: read, export（替代或对齐 `statistics`）
  - `enum_field`: read, create, update, delete（或 read, write）
  - `collection`: read, create, update, delete
  - `contact`: read, create, update, delete
  - `notification`: read, create, update
- **测试**：单元测试验证权限常量完整性（每个 resource_type 都有对应权限定义）
- **Done when**：`permissions.py` 包含全部资源类型的权限定义，且与 `require_authz` 调用中使用的 resource_type 名称完全一致

#### Task 1.3：重写角色种子数据

- **文件**：`backend/scripts/setup/init_rbac_data.py`
- **动作**：
  1. 替换现有 7 个角色定义为 6 个目标角色（§3.1）
  2. 重写权限分配逻辑，从"按条件过滤"改为"显式列举"（更安全、更可审计）
  3. 将 `asset_manager`、`project_manager` 保留为可选角色（`is_system_role=False`）
  4. 废弃 `manager`、`user`、`auditor` 角色（标记 `is_active=False` 或不再创建）
- **测试**：
  - 单元测试：验证每个角色的权限集合与 §3.2 矩阵完全一致
  - 集成测试：运行 `init_rbac_data.py`，验证数据库记录正确
- **Done when**：种子数据创建的角色-权限映射与 §3.2 矩阵 100% 一致

#### Task 1.4：Alembic 迁移

- **文件**：`backend/alembic/versions/YYYYMMDD_rbac_role_realignment.py`
- **动作**：
  1. 新增权限记录（全部新增资源类型的权限）
  2. 新增角色记录（`ops_admin`、`perm_admin`、`reviewer`、`executive`）
  3. 重命名 `admin` → `system_admin`
  4. 标记废弃角色 `is_active=False`
  5. 重建 `role_permissions` 关联
  6. 如确认 `statistics` → `analytics` 重命名，更新现有权限记录
- **注意**：迁移必须幂等
- **Done when**：`alembic upgrade head` 成功，数据库状态与种子数据一致

#### Task 1.5：审计 CRUD 层 party filtering

- **范围**：所有涉及多租户数据的 CRUD 函数
- **检查项**：
  1. 列表查询是否接收 `party_ids` 参数并在 WHERE 条件中使用？
  2. 非管理员调用时，`party_ids` 是否从 `UserPartyBinding` 正确传入？
  3. 单资源查询（by ID）是否检查 party 归属，还是允许直接访问？
  4. 更新/删除操作是否先验证 party 归属？
- **审计文件**：
  - `crud/asset.py`
  - `crud/rent_contract.py`
  - `crud/project.py`
  - `crud/party.py`
  - `crud/property_certificate.py`
  - `crud/ownership.py`
  - 所有其他涉及 party 数据的 CRUD 文件
- **输出**：party filtering 覆盖率报告（哪些 CRUD 函数有过滤、哪些缺失）
- **Done when**：所有多租户 CRUD 函数均有 party filtering，或已识别并记录所有缺口

#### Task 1.6：修复 admin dummy hash（如存在）

- **文件**：`backend/scripts/setup/init_rbac_data.py`
- **动作**：确保初始 admin 用户使用强随机密码或环境变量注入
- **Done when**：初始化脚本不包含硬编码弱密码

### Phase 2：P1 — ABAC 激活与安全加固（预计 1.5 天）

#### Task 2.1：种子化 `abac_role_policies` 绑定

- **文件**：`backend/scripts/setup/init_rbac_data.py` 或新建 Alembic 迁移
- **动作**：
  1. 为每个新角色创建 `ABACRolePolicy` 记录，绑定到已有的 7 个 ABAC 策略模板
  2. 绑定规则：
     - `ops_admin` → 运营方资产/合同数据策略
     - `viewer` / `executive` → 产权方或运营方策略（按绑定类型自动选择）
     - `reviewer` → 全部数据策略（审核人需要看所有待审数据）
  3. 或者使用 `backfill_role_policies.py` 脚本的逻辑整合进 `init_rbac_data.py`
- **测试**：
  - 集成测试：验证 `get_policies_by_role_ids()` 对每个角色返回正确的策略列表
  - 端到端测试：非管理员用户访问单资源端点，确认 ABAC 策略生效
- **Done when**：`abac_role_policies` 表非空，ABAC 评估对非管理员用户返回有意义的结果（而非 deny_by_default）

#### Task 2.2：修复 ABAC deny 被 authenticated_default 覆盖的 bug

- **文件**：`backend/src/services/authz/service.py`
- **动作**：调整 `check_access()` 的 elif 逻辑，确保 ABAC 显式 deny（`has_matching_policy_rule=True`）不会被 authenticated_default 覆盖
- **测试**：单元测试：构造 ABAC 显式 deny + notification:read 场景，验证结果为 deny
- **Done when**：ABAC 显式 deny 始终优先于 authenticated_default

#### Task 2.3：缓存键纳入 party bindings

- **文件**：`backend/src/services/authz/cache.py`
- **动作**：`compute_roles_hash()` 改为同时哈希 `role_ids` + `party_binding_ids`（或 `party_binding_updated_at`）
- **测试**：单元测试验证 binding 变更后 hash 值变化
- **Done when**：party 绑定变更立即导致缓存键失效

#### Task 2.4：更新需求文档 §8.3

- **文件**：`docs/requirements-specification.md`
- **动作**：将 §8.3 中"全局视角切换入口清晰可见，且支持手动切换"更新为"数据范围自动注入，用户无需手动切换"，与 §5.2 保持一致
- **Done when**：§5.2 与 §8.3 不再矛盾

### Phase 3：P2 — 技术债务清理（预计 2-3 天）

#### Task 3.1：清理从未使用的 auth checker 类

- **范围**：以下类/函数在 API 端点中**从未被调用**：
  - `require_permission` / 旧的 `PermissionChecker`
  - `PermissionGrant` 模型
  - `ResourcePermission` 模型
  - `OrganizationPermissionChecker`
  - 其他 DEPRECATED 标记的授权相关代码
- **前提**：Phase 1 和 Phase 2 完成后，确认无代码依赖
- **Done when**：所有从未使用的 auth checker 代码已删除，`make check` 通过

#### Task 3.2：前端 capabilities 统一

- **动作**：前端权限检查统一迁移到 capabilities API，移除 permissions 兼容层
- **前提**：后端 capabilities API 返回正确的新角色权限

#### Task 3.3：前端路由级权限守卫

- **动作**：在 `AppRoutes.tsx` 添加全局权限守卫，未授权路由自动跳转 403 页面
- **前提**：Task 3.2 完成

---

## 5. 向后兼容与迁移策略

### 5.1 角色迁移映射

对已有用户数据，需要执行一次性迁移：

| 现有角色 | 迁移到 | 迁移规则 |
|----------|--------|----------|
| `admin` | `system_admin` | 1:1 重命名 |
| `manager` | `executive` | 降权，需人工确认 |
| `asset_manager` | `ops_admin` | 升级为全业务域运营管理员 |
| `project_manager` | `ops_admin` | 合并到 ops_admin |
| `auditor` | `viewer`（无 Party 约束） | 需确认外审用户名单 |
| `user` | `viewer` | 合并（权限本就相同） |
| `viewer` | `viewer` | 不变 |

### 5.2 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| 现有 `manager` 用户降权后无法操作 | 高 | 迁移脚本需人工确认；部署前通知相关用户 |
| 前端权限检查用旧权限名 | 中 | Phase 2 Task 2.1 审计覆盖 |
| ABAC 激活后误拦截合法请求 | 中 | 先在日志模式运行（只记录 deny 不实际拦截），确认无误后切换为强制模式 |
| CRUD 层 party filtering 审计发现大量缺口 | 中 | Task 1.5 输出详细报告，逐个修复 |
| `analytics`/`statistics` 重命名影响现有数据 | 低 | 迁移脚本同时更新权限名 |

---

## 6. 测试策略

### 6.1 Phase 1 测试

```bash
# 权限定义完整性
cd backend && uv run pytest tests/unit/security/test_permissions.py -v

# 种子数据正确性
cd backend && uv run pytest tests/unit/scripts/test_init_rbac_data.py -v

# CRUD party filtering 审计（需新建）
cd backend && uv run pytest tests/integration/crud/test_party_filtering.py -v

# 迁移回归
cd backend && uv run pytest tests/integration/ -m "database" -v
```

### 6.2 Phase 2 测试

```bash
# ABAC 策略绑定
cd backend && uv run pytest tests/integration/services/authz/test_abac_binding.py -v

# ABAC deny 优先级 bug 修复
cd backend && uv run pytest tests/unit/services/authz/test_service.py -v -k "deny_override"

# 缓存键变更
cd backend && uv run pytest tests/unit/services/authz/test_cache.py -v

# 端到端授权链路
cd backend && uv run pytest tests/integration/api/test_authorization_flow.py -v
```

### 6.3 全量回归

```bash
make check  # lint + type-check + test + build + docs-lint
```

---

## 7. 验收条件

| # | 条件 | 验证方式 | Phase |
|---|------|----------|-------|
| 1 | 系统包含 6 个系统角色，与需求 §5.1 一一对应 | 查数据库 `roles` 表 | 1 |
| 2 | 权限资源覆盖全部 `require_authz` 使用的 resource_type | `permissions.py` + 数据库 `permissions` 表 | 1 |
| 3 | 每个角色的权限集合与 §3.2 矩阵一致 | 单元测试 + 数据库 `role_permissions` 表 | 1 |
| 4 | `user` / `auditor` / `manager` 角色已废弃 | 数据库 `is_active=False` | 1 |
| 5 | 所有多租户 CRUD 函数有 party filtering | 审计报告 + 集成测试 | 1 |
| 6 | `analytics`/`statistics` 命名统一 | `grep` 搜索确认 | 1 |
| 7 | `abac_role_policies` 表非空，ABAC 对非管理员返回有意义结果 | 集成测试 | 2 |
| 8 | ABAC 显式 deny 不被 authenticated_default 覆盖 | 单元测试 | 2 |
| 9 | 缓存键包含 party bindings | 单元测试 | 2 |
| 10 | §5.2 和 §8.3 不再矛盾 | 文档审查 | 2 |
| 11 | 从未使用的 auth checker 代码已删除 | `grep` 搜索 + `make check` | 3 |
| 12 | `make check` 全量通过 | CI | 所有 |

---

## 8. 时间线

| 阶段 | 预计工时 | 前置依赖 |
|------|---------|----------|
| Phase 1（P0 角色权限重定义 + 数据隔离审计） | 3 天 | 本计划审批 |
| Phase 2（P1 ABAC 激活 + 安全加固） | 1.5 天 | Phase 1 完成 |
| Phase 3（P2 技术债务清理） | 2-3 天 | Phase 2 完成 |
| **总计** | **6.5-7.5 天** | — |

---

## 9. 边界情况与建议测试用例

### 9.1 角色权限边界

| 场景 | 预期行为 | 测试用例 |
|------|----------|----------|
| ops_admin 尝试修改用户角色 | deny | `require_authz(action="update", resource_type="user")` 对 ops_admin → 403 |
| reviewer 尝试创建资产 | deny | `require_authz(action="create", resource_type="asset")` 对 reviewer → 403 |
| executive 尝试导出统计 | allow | `require_authz(action="export", resource_type="analytics")` 对 executive → 200 |
| viewer 尝试审批 | deny | `require_authz(action="approve", resource_type="approval")` 对 viewer → 403 |
| perm_admin 尝试读取资产 | deny | `require_authz(action="read", resource_type="asset")` 对 perm_admin → 403 |

### 9.2 数据隔离边界

| 场景 | 预期行为 | 测试用例 |
|------|----------|----------|
| 用户 A 通过 ID 直接访问用户 B 的资产 | deny（party 不匹配） | `GET /assets/{b_asset_id}` with user A credentials → 403 或 404 |
| Party 绑定变更后立即查询 | 使用新绑定 | 变更 binding → 查询资产列表 → 结果应反映新绑定 |
| 无 party 绑定的用户查询资产列表 | 空结果 | 无 binding 用户 `GET /assets` → `[]` |
| 外审用户（viewer + 无 Party 约束）查询 | 全部数据 | 外审 viewer `GET /assets` → 返回所有资产 |

### 9.3 ABAC 激活后边界

| 场景 | 预期行为 | 测试用例 |
|------|----------|----------|
| ABAC 显式 deny + notification:read | deny（不被覆盖） | 构造 ABAC deny 规则 + `notification:read` action → deny |
| ABAC 策略绑定存在 + RBAC 也允许 | ABAC 结果优先 | ABAC allow → 不进入 RBAC fallback |
| ABAC deny_by_default（空策略）+ RBAC 允许 | allow（RBAC fallback） | 确认 fallback 逻辑不变 |

---

## 10. 关联文档

| 文档 | 关系 |
|------|------|
| `docs/architecture/auth-rbac-analysis-review.md` | 分析依据（第三版） |
| `docs/architecture/auth-rbac-analysis.md` | 原始分析（归档参考） |
| `docs/requirements-specification.md` §5 | 需求来源 |
| `backend/scripts/setup/init_rbac_data.py` | 主要修改文件 |
| `backend/src/security/permissions.py` | 主要修改文件 |
| `backend/src/services/authz/service.py` | Phase 2 修改文件（deny 覆盖 bug） |
| `backend/src/services/authz/cache.py` | Phase 2 修改文件（缓存键） |
| `backend/src/middleware/auth.py` | 授权入口，参考不改 |
| `backend/src/crud/` | Phase 1 审计范围（party filtering） |
