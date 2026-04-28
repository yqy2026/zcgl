# 主体与角色权限控制机制深度分析报告（历史快照）

> Historical snapshot. 本文为 2026-04-05 一次性架构分析报告，不再作为当前授权架构基线。当前 API、权限与数据范围契约以 `docs/specs/api-contract.md` 为准，需求状态与实现证据以 `docs/traceability/requirements-trace.md` 为准。

> **文档类型**: 架构分析
> **创建日期**: 2026-04-05
> **适用范围**: 认证 (Authentication) / 授权 (Authorization) / RBAC / ABAC / 多租户数据隔离
> **状态**: 初稿
> **关键发现**: ⚠️ ABAC 策略表为空，当前实际运行的是**纯 RBAC**，ABAC 层仅为空壳代码

---

## 一、整体架构概览

### 1.1 权限架构分层

系统**设计为** RBAC + ABAC + Grant + Party多租户 四层混合权限架构，但**当前实际仅运行静态 RBAC 层**：

```
请求 → 认证(Authentication) → 静态RBAC → ABAC策略(空壳) → 数据范围(Party) → 资源
          JWT Cookie验证        角色权限    ❌ 策略表为空    主体归属隔离
```

> ⚠️ **重要**: ABAC 策略表 (`abac_policies`, `abac_policy_rules`, `abac_role_policies`) 全部为空。
> `init_rbac_data.py` 不创建任何 ABAC 策略。所有 `check_access()` 调用都会走到 `deny_by_default`，
> 然后 fallback 到静态 RBAC。**当前系统实质上是纯 RBAC，不是 RBAC+ABAC 混合模型。**
请求 → 认证(Authentication) → 静态RBAC → ABAC策略 → 数据范围(Party) → 资源
         JWT Cookie验证        角色权限    JSONLogic    主体归属隔离
```

### 1.2 核心组件关系图

```
┌─────────────────────────────────────────────────────────────────┐
│                        请求入口                                  │
│              FastAPI Middleware Layer                           │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────────┐   │
│  │ Security  │ │  CSRF    │ │ Rate     │ │ TokenBlacklist   │   │
│  │ Headers   │ │ Middleware│ │ Limiting │ │ Guard (熔断)     │   │
│  └──────────┘ └──────────┘ └──────────┘ └──────────────────┘   │
└────────────────────────────┬────────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    认证层 (Authentication)                        │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ get_current_user / get_current_active_user               │   │
│  │  - JWT Cookie 读取 → 验签 → 验过期 → 黑名单 → DB查用户    │   │
│  │  - is_active 检查 + is_locked_now 检查                    │   │
│  └──────────────────────────────────────────────────────────┘   │
└────────────────────────────┬────────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    授权层 (Authorization)                         │
│  ┌─────────────────┐  ┌─────────────────┐  ┌────────────────┐  │
│  │ require_admin   │  │ require_authz   │  │ require_       │  │
│  │ (管理员检查)     │  │ (ABAC鉴权)       │  │ permissions    │  │
│  │                 │  │                 │  │ (静态RBAC)      │  │
│  └─────────────────┘  └────────┬────────┘  └────────────────┘  │
│                                │                                │
│  ┌─────────────────────────────┴────────────────────────────┐  │
│  │              AuthzService.check_access()                  │  │
│  │  1. 管理员绕过 → 2. Subject Context → 3. 资源上下文       │  │
│  │  4. ABAC策略评估 → 5. RBAC Fallback → 6. 决策缓存         │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────────────────────┬────────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    数据层 (Data Scoping)                          │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ DataScopeContextChecker + PartyFilter                     │   │
│  │  - owner / manager / all scope_mode                       │   │
│  │  - effective_party_ids 自动注入查询                        │   │
│  │  - UserPartyBinding 绑定关系                               │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### 1.3 涉及的核心文件

| 层级 | 文件路径 | 职责 |
|------|----------|------|
| 模型 | `backend/src/models/rbac.py` | Role, Permission, UserRoleAssignment, PermissionGrant |
| 模型 | `backend/src/models/auth.py` | User, UserSession, AuditLog |
| 模型 | `backend/src/models/abac.py` | ABACPolicy, ABACPolicyRule, ABACRolePolicy |
| 模型 | `backend/src/models/user_party_binding.py` | 用户-主体绑定 |
| 中间件 | `backend/src/middleware/auth.py` | get_current_user, require_admin, AuthzPermissionChecker |
| 中间件 | `backend/src/middleware/token_blacklist_guard.py` | Token 黑名单熔断器 |
| 中间件 | `backend/src/middleware/security_middleware.py` | 安全头、CSRF、速率限制 |
| 安全 | `backend/src/security/jwt_security.py` | JWT 安全配置 |
| 安全 | `backend/src/security/cookie_manager.py` | httpOnly Cookie 管理 |
| 安全 | `backend/src/security/token_blacklist.py` | Redis Token 黑名单 |
| 服务 | `backend/src/services/permission/rbac_service.py` | RBAC 核心业务逻辑 |
| 服务 | `backend/src/services/authz/service.py` | ABAC 授权编排 |
| 服务 | `backend/src/services/authz/engine.py` | JSONLogic 策略评估引擎 |
| 服务 | `backend/src/services/authz/context_builder.py` | Subject Context 构建 |
| 服务 | `backend/src/services/authz/cache.py` | 决策缓存 |
| 服务 | `backend/src/services/authz/events.py` | 缓存失效事件总线 |
| 服务 | `backend/src/services/party_scope.py` | Party 数据范围解析 |
| CRUD | `backend/src/crud/auth.py` | UserCRUD, UserSessionCRUD, AuditLogCRUD |
| CRUD | `backend/src/crud/rbac.py` | CRUDRole, CRUDPermission, CRUDUserRoleAssignment |
| CRUD | `backend/src/crud/authz.py` | CRUDAuthz (ABAC 策略 CRUD) |
| 初始化 | `backend/scripts/setup/init_rbac_data.py` | RBAC 种子数据 |
| 前端 | `frontend/src/contexts/AuthContext.tsx` | React 认证上下文 |
| 前端 | `frontend/src/components/Auth/AuthGuard.tsx` | 认证守卫 |
| 前端 | `frontend/src/components/System/PermissionGuard.tsx` | 权限守卫 |
| 前端 | `frontend/src/components/System/CapabilityGuard.tsx` | 能力集守卫 |

---

## 二、认证机制 (Authentication)

### 2.1 认证流程详解

#### 2.1.1 登录流程

```
POST /api/v1/auth/login
  │
  ├─ 1. 接收 identifier (username/phone) + password
  │
  ├─ 2. AsyncAuthenticationService.authenticate_user()
  │     ├─ 查找用户 (username 或 phone)
  │     ├─ bcrypt 密码验证
  │     ├─ 检查 is_active / is_locked_now
  │     └─ 更新 last_login_at, 重置 failed_login_attempts
  │
  ├─ 3. 创建 JWT Token
  │     ├─ Access Token: HS256, 30min, 包含 sub/userid, username, jti, iat, exp
  │     └─ Refresh Token: 7天, 独立 jti
  │
  ├─ 4. 设置 httpOnly Cookie
  │     ├─ auth_token (Access Token)
  │     ├─ refresh_token (Refresh Token)
  │     └─ csrf_token (CSRF 防护)
  │
  ├─ 5. 创建 UserSession 记录
  │     └─ 记录 refresh_token + device_info + expires_at
  │
  └─ 6. 返回响应 (body 中不含 token)
        └─ { user, permissions, message }
```

**关键文件**: `backend/src/api/v1/auth/auth_modules/authentication.py`

#### 2.1.2 Token 验证流程 (每次请求)

```
请求进入 → get_current_user()
  │
  ├─ 1. 从 httpOnly Cookie 读取 auth_token
  │     └─ Cookie 名称由 cookie_manager.cookie_name 配置
  │
  ├─ 2. _validate_jwt_token()
  │     ├─ jwt.decode() 验证签名 (HS256)
  │     ├─ 验证 audience (aud) 和 issuer (iss)
  │     ├─ 提取 sub, username, exp, iat, jti
  │     └─ 检查 Token 黑名单 (JTI + user_id + iat)
  │
  ├─ 3. 从数据库查询 User
  │     └─ SELECT * FROM users WHERE id = token_data.sub
  │
  ├─ 4. 检查用户状态
  │     ├─ is_active == True?
  │     └─ is_locked_now() == False?
  │
  └─ 5. 返回 User 对象
```

**关键文件**: `backend/src/middleware/auth.py:157-195`

#### 2.1.3 Token 刷新流程

```
POST /api/v1/auth/refresh
  │
  ├─ 1. 从 httpOnly Cookie 读取 refresh_token
  │
  ├─ 2. 验证 JWT 签名和过期
  │
  ├─ 3. 检查 UserSession 是否仍活跃
  │
  ├─ 4. Token 轮换 (Rotation)
  │     ├─ 旧 refresh_token 加入黑名单
  │     ├─ 创建新的 Access Token + Refresh Token
  │     └─ 更新 UserSession 记录
  │
  └─ 5. 设置新的 httpOnly Cookie
```

#### 2.1.4 登出流程

```
POST /api/v1/auth/logout
  │
  ├─ 1. 当前 Access Token 加入黑名单 (JTI + exp)
  │
  ├─ 2. 撤销用户所有 UserSession
  │
  ├─ 3. 清除 httpOnly Cookie (设置过期时间为过去)
  │
  └─ 4. 记录审计日志
```

### 2.2 安全特性

| 特性 | 实现方式 | 配置位置 |
|------|----------|----------|
| **密码加密** | bcrypt (salt rounds 12) | `services/core/password_service.py` |
| **密码策略** | 8+字符，大写+小写+数字+特殊字符 | `middleware/auth.py:1474-1484` |
| **账户锁定** | failed_login_attempts 计数器 + locked_until 时间戳 | `models/auth.py` |
| **Token 黑名单** | Redis 驱动，支持 JTI 级和用户级撤销 | `security/token_blacklist.py` |
| **熔断保护** | TokenBlacklistGuard 熔断器，Redis 不可用时 fail-closed | `middleware/token_blacklist_guard.py` |
| **CSRF 防护** | Double-submit Cookie 模式 | `middleware/security_middleware.py` |
| **安全头** | X-Content-Type-Options, X-Frame-Options, HSTS, CSP | `middleware/security_middleware.py` |
| **速率限制** | IP 级速率限制 + XSS 模式检测 | `middleware/security_middleware.py` |
| **会话管理** | 最大并发会话数、会话过期时间、设备信息记录 | `middleware/auth.py:1454-1496` |

### 2.3 JWT 配置

| 参数 | 默认值 | 说明 |
|------|--------|------|
| 算法 | HS256 | HMAC-SHA256 |
| Access Token 过期 | 30 分钟 | `ACCESS_TOKEN_EXPIRE_MINUTES` |
| Refresh Token 过期 | 7 天 | `REFRESH_TOKEN_EXPIRE_DAYS` |
| Audience | 配置值 | `JWT_AUDIENCE` |
| Issuer | 配置值 | `JWT_ISSUER` |
| 最大并发会话 | 配置值 | `MAX_CONCURRENT_SESSIONS` |

### 2.4 存在的问题

| # | 问题 | 严重性 | 位置 |
|---|------|--------|------|
| 1 | 管理员初始密码为 dummy hash (`$2b$12$dummy_hash_for_admin`)，首次使用需手动重置 | **高** | `init_rbac_data.py:184` |
| 2 | 无邮箱验证流程，新用户注册后邮箱未验证 | 中 | 整体架构 |
| 3 | 无自助密码重置流程，密码遗忘只能靠管理员重置 | 中 | 整体架构 |
| 4 | 无 OAuth/SSO 支持，仅支持用户名密码 | 低 | 整体架构 |
| 5 | 登录接口无 IP 级速率限制（仅依赖全局中间件） | 低 | `auth_modules/authentication.py` |
| 6 | 测试用户也使用 dummy hash | 低 | `init_rbac_data.py:329` |

---

## 三、RBAC 核心 (Role-Based Access Control)

### 3.1 数据模型详解

#### 3.1.1 数据库 ER 关系

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                  users                                       │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │ id (PK, UUID)                                                       │    │
│  │ username (unique), email, phone, full_name                          │    │
│  │ password_hash, password_history (JSON)                              │    │
│  │ is_active, is_locked, failed_login_attempts                         │    │
│  │ last_login_at, locked_until                                         │    │
│  │ default_organization_id (FK → organizations)                        │    │
│  │ created_at, updated_at, created_by, updated_by                      │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│     │ 1:N                        │ 1:N                    │ N:M            │
│     ▼                            ▼                        ▼                │
│  user_sessions              audit_logs          user_role_assignments      │
│  ┌──────────────┐          ┌─────────────┐     ┌──────────────────────┐   │
│  │ refresh_token│          │ action      │     │ id (PK)              │   │
│  │ device_info  │          │ resource_type│    │ user_id (FK)         │   │
│  │ expires_at   │          │ response_status│   │ role_id (FK)         │   │
│  │ ...          │          │ ...         │     │ expires_at           │   │
│  └──────────────┘          └─────────────┘     │ is_active            │   │
│                                                │ reason, notes        │   │
│                                                │ context (JSON)       │   │
│                                                └──────────┬───────────┘   │
└───────────────────────────────────────────────────────────┼───────────────┘
                                                            │
┌───────────────────────────────────────────────────────────┼───────────────┐
│                                  roles                   │               │
│  ┌───────────────────────────────────────────────────────┼──────────┐    │
│  │ id (PK, UUID)                                         │          │    │
│  │ name (unique), display_name, description              │          │    │
│  │ level (int), category, is_system_role                 │          │    │
│  │ is_active                                             │          │    │
│  │ party_id (FK → parties)                               │          │    │
│  │ scope (global/party/party_subtree), scope_id          │          │    │
│  │ created_at, updated_at, created_by, updated_by        │          │    │
│  └───────────────────────────────────────────────────────┼──────────┘    │
│     │ N:M (role_permissions)                             │               │
│     ▼                                                    ▼               │
│  permissions                                     user_assignments        │
│  ┌──────────────────────────────────────────────────────────────────┐    │
│  │ id (PK, UUID)                                                    │    │
│  │ name (unique), display_name, description                         │    │
│  │ resource (e.g. "asset"), action (e.g. "read")                    │    │
│  │ is_system_permission, requires_approval                          │    │
│  │ max_level, conditions (JSON)                                     │    │
│  │ created_at, updated_at, created_by, updated_by                   │    │
│  └──────────────────────────────────────────────────────────────────┘    │
│     │ 1:N (DEPRECATED)                                                   │
│     ▼                                                                    │
│  permission_grants (DEPRECATED)                                          │
│  ┌──────────────────────────────────────────────────────────────────┐    │
│  │ id (PK), user_id (FK), permission_id (FK)                        │    │
│  │ grant_type, effect (allow/deny), scope, scope_id                 │    │
│  │ conditions (JSON), starts_at, expires_at, priority               │    │
│  │ is_active, source_type, source_id, granted_by, reason            │    │
│  │ revoked_at, revoked_by                                           │    │
│  └──────────────────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────┐
│                             role_permissions (关联表)                     │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │ role_id (FK → roles.id), permission_id (FK → permissions.id)     │   │
│  │ created_at, created_by                                           │   │
│  └──────────────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────────────┘
```

#### 3.1.2 核心模型属性

**Role 模型** (`backend/src/models/rbac.py:40-116`):

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | String (UUID) | 主键 |
| `name` | String(100) | 角色名称（唯一） |
| `display_name` | String(200) | 显示名称 |
| `level` | Integer | 角色级别（1=最高，数字越小权限越高） |
| `category` | String(50) | 角色类别（system/management/business/read_only/asset/project/audit） |
| `is_system_role` | Boolean | 是否系统角色（系统角色不可修改/删除） |
| `is_active` | Boolean | 是否激活 |
| `party_id` | String (FK) | 所属主体ID（多租户隔离） |
| `scope` | String(50) | 权限范围（global/party/party_subtree） |
| `scope_id` | String | 范围ID |

**Permission 模型** (`backend/src/models/rbac.py:118-186`):

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | String (UUID) | 主键 |
| `name` | String(100) | 权限名称（唯一，格式 `resource:action`） |
| `display_name` | String(200) | 显示名称 |
| `resource` | String(50) | 资源类型（如 "asset", "user", "role"） |
| `action` | String(50) | 操作类型（如 "read", "create", "update", "delete"） |
| `is_system_permission` | Boolean | 是否系统权限 |
| `requires_approval` | Boolean | 是否需要审批 |
| `max_level` | Integer | 最大级别限制 |
| `conditions` | JSON | 权限条件表达式 |

**UserRoleAssignment 模型** (`backend/src/models/rbac.py:188-241`):

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | String (UUID) | 主键 |
| `user_id` | String (FK) | 用户ID |
| `role_id` | String (FK) | 角色ID |
| `assigned_by` | String(100) | 分配人 |
| `assigned_at` | DateTime | 分配时间 |
| `expires_at` | DateTime | 过期时间（支持临时角色分配） |
| `is_active` | Boolean | 是否激活 |
| `reason` | Text | 分配原因 |
| `notes` | Text | 备注 |
| `context` | JSON | 上下文信息 |

### 3.2 预置角色与权限

#### 3.2.1 7 个系统角色

| 角色名 | 显示名 | Level | Category | 权限范围 |
|--------|--------|-------|----------|----------|
| `admin` | 系统管理员 | 1 | system | 全部 62 个权限 |
| `manager` | 管理员 | 2 | management | 除 `system:*` 外的所有权限 |
| `user` | 普通用户 | 3 | business | 仅 `*:read` 操作 |
| `viewer` | 只读用户 | 4 | read_only | 仅 `*:read` 操作 |
| `asset_manager` | 资产管理员 | 2 | asset | asset:* + statistics:* |
| `project_manager` | 项目经理 | 2 | project | project:* + statistics:* |
| `auditor` | 审计员 | 2 | audit | audit:* + statistics:* |

#### 3.2.2 62 个权限清单

按资源分组：

| 资源 | 操作 | 权限名 | 说明 |
|------|------|--------|------|
| **asset** | read, create, update, delete | asset:read 等 | 资产管理 |
| **property_certificate** | read, create, update, delete | property_certificate:read 等 | 产权证管理 |
| **project** | read, create, update, delete | project:read 等 | 项目管理 |
| **ownership** | read, create, update, delete | ownership:read 等 | 权属管理 |
| **rent_contract** | read, create, update, delete | rent_contract:read 等 | 租金合同管理 |
| **statistics** | read, export | statistics:read, statistics:export | 统计分析 |
| **excel_config** | read, write | excel_config:read, excel_config:write | Excel 配置 |
| **approval** | read, start, approve, reject, withdraw | approval:read 等 | 审批流 |
| **system** | admin, manage, audit, backup | system:admin 等 | 系统管理 |
| **user** | read, create, update, delete | user:read 等 | 用户管理 |
| **role** | read, create, update, delete, assign | role:read 等 | 角色管理 |
| **organization** | read, create, update, delete | organization:read 等 | 组织管理 |
| **permission_grant** | read, assign, revoke, check | permission_grant:read 等 | 统一授权管理 |
| **audit** | read, export | audit:read, audit:export | 审计日志 |

### 3.3 权限检查链路

`RBACService.check_permission()` 的完整检查流程：

```
check_permission(user_id, PermissionCheckRequest)
  │
  ├─ 1. 用户存在且活跃?
  │     └─ 否 → has_permission=False, reason="用户不存在或已禁用"
  │
  ├─ 2. _check_static_permission() ── 静态 RBAC 检查
  │     ├─ 获取用户所有活跃角色 (get_user_roles)
  │     ├─ _user_has_admin_permission() ── 检查 system:admin 或 system:manage
  │     │   └─ 是 → has_permission=True, granted_by=["system_admin_permission"]
  │     ├─ 无角色 → has_permission=False, reason="用户未分配任何角色"
  │     └─ 遍历角色，匹配 resource:action
  │         └─ 命中 → has_permission=True, granted_by=["role_xxx"]
  │
  ├─ 3. 静态 RBAC 通过?
  │     └─ 是 → 返回结果
  │
  ├─ 4. _check_grant_permission() ── 动态授权检查 (DEPRECATED)
  │     ├─ 查找匹配的 PermissionGrant 记录
  │     ├─ 过滤 scope 匹配
  │     ├─ 过滤 conditions 匹配
  │     ├─ 按 priority 排序
  │     ├─ Deny 优先检查
  │     │   └─ 命中 Deny → has_permission=False, reason="命中拒绝授权"
  │     └─ Allow 检查
  │         └─ 命中 Allow → has_permission=True, granted_by=["grant_xxx"]
  │
  └─ 5. 均未命中 → has_permission=False, reason="权限不足"
```

**关键文件**: `backend/src/services/permission/rbac_service.py:488-515`

### 3.4 管理员权限判断

`RBACService.is_admin()` 的判断逻辑：

```
is_admin(user_id)
  │
  ├─ 1. 检查用户角色是否具有 system:admin 或 system:manage 权限
  │     └─ _role_has_admin_permission(): 遍历角色权限
  │
  └─ 2. 检查 PermissionGrant 中是否有 system:admin 或 system:manage 授权 (DEPRECATED)
```

注意：管理员判断基于**权限**而非**角色名**，这是一个好的设计实践。

### 3.5 权限缓存体系

#### 3.5.1 缓存层级

```
┌─────────────────────────────────────────────────────┐
│              PermissionCacheService                  │
│                                                      │
│  用户级缓存: user:{user_id}:permissions              │
│  角色级缓存: role:{role_id}:permissions              │
│  组织级缓存: org:{org_id}:accessible_organizations   │
│                                                      │
│  存储: Redis (内存回退)                               │
└─────────────────────────────────────────────────────┘
```

#### 3.5.2 缓存失效链路

```
角色/权限变更
  │
  ├─ 1. invalidate_user_permission_cache(user_id)
  │     ├─ 清除用户权限缓存
  │     ├─ 清除组织可见范围缓存
  │     └─ 发布 AuthzEventBus 事件 (AUTHZ_USER_ROLE_UPDATED)
  │
  ├─ 2. invalidate_permission_cache_for_role(role_id)
  │     ├─ 清除角色缓存
  │     └─ 查询该角色所有活跃用户 → 逐个失效用户缓存
  │
  └─ 3. AuthzEventBus (支持 Redis 传输)
        └─ 多实例间缓存同步失效
```

**风险**: 缓存失效链复杂，高并发下可能出现竞态条件。角色变更时需要查询数据库获取所有关联用户，存在 N+1 查询风险。

### 3.6 RBACService 核心 API

| 方法 | 功能 | 说明 |
|------|------|------|
| `create_role()` | 创建角色 | 检查名称唯一性，同时分配权限 |
| `update_role()` | 更新角色 | 系统角色不可修改，检查名称唯一性 |
| `delete_role()` | 删除角色 | 系统角色不可删除，检查是否有用户使用 |
| `update_role_permissions()` | 更新角色权限 | 系统角色权限不可修改 |
| `assign_role_to_user()` | 分配角色给用户 | 支持重新激活已过期分配 |
| `revoke_role_from_user()` | 撤销角色 | 软删除（设置 is_active=False） |
| `check_permission()` | 检查用户权限 | 静态 RBAC + Grant 检查 |
| `is_admin()` | 判断管理员 | 基于权限而非角色名 |
| `get_user_permissions_summary()` | 获取权限汇总 | 含缓存，合并角色+资源+Grant 权限 |

---

## 四、ABAC 机制 (Attribute-Based Access Control)

### 4.1 数据模型

```
┌──────────────────────────────────────────────────────────────────┐
│                        abac_policies                              │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │ id (PK, UUID)                                              │  │
│  │ name, effect (allow/deny), priority, enabled               │  │
│  │ created_at, updated_at, created_by, updated_by             │  │
│  └────────────────────────────────────────────────────────────┘  │
│     │ 1:N                              │ N:M                     │
│     ▼                                  ▼                         │
│  abac_policy_rules                abac_role_policies             │
│  ┌──────────────────────┐          ┌──────────────────────┐     │
│  │ id (PK)              │          │ policy_id (FK)       │     │
│  │ resource_type        │          │ role_id (FK)         │     │
│  │ action               │          └──────────────────────┘     │
│  │ condition_expr (JSONB)│                                      │
│  │ field_mask (JSONB)   │                                       │
│  └──────────────────────┘                                       │
└──────────────────────────────────────────────────────────────────┘
```

**ABACPolicy 模型** (`backend/src/models/abac.py`):

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | UUID | 主键 |
| `name` | String | 策略名称 |
| `effect` | Enum (allow/deny) | 策略效果 |
| `priority` | Integer | 优先级（数字越小越优先） |
| `enabled` | Boolean | 是否启用 |

**ABACPolicyRule 模型**:

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | UUID | 主键 |
| `policy_id` | FK | 所属策略 |
| `resource_type` | String | 资源类型 |
| `action` | String | 操作类型 |
| `condition_expr` | JSONB | JSONLogic 条件表达式 |
| `field_mask` | JSONB | 字段级可见性掩码 |

### 4.2 评估引擎 (AuthzEngine)

**文件**: `backend/src/services/authz/engine.py`

#### 4.2.1 评估流程

```
evaluate_with_reason(subject, resource, action, policies)
  │
  ├─ 1. 验证 resource_type 非空
  │     └─ 空 → allowed=False, reason_code="missing_resource_type"
  │
  ├─ 2. 检查 policies 非空
  │     └─ 空 → allowed=False, reason_code="deny_by_default"
  │
  ├─ 3. 构建评估数据: { subject, resource, action }
  │
  ├─ 4. 策略排序: priority ASC, deny 优先
  │
  ├─ 5. 遍历策略
  │     ├─ 跳过未启用的策略
  │     ├─ 遍历策略规则
  │     │   ├─ 匹配 resource_type
  │     │   ├─ 匹配 action
  │     │   └─ 评估 condition_expr (JSONLogic)
  │     │       └─ 匹配 → 返回 allow/deny + matched_policy/rule_id + field_mask
  │     └─ 未匹配 → 继续下一个策略
  │
  └─ 6. 无匹配 → allowed=False, reason_code="deny_by_default"
```

#### 4.2.2 JSONLogic 支持的操作符

引擎支持以下 JSONLogic 操作符：

| 类别 | 操作符 | 说明 |
|------|--------|------|
| 变量 | `var` | 路径访问（支持点分隔和数组索引） |
| 比较 | `==`, `!=`, `>`, `>=`, `<`, `<=` | 基本比较 |
| 逻辑 | `and`, `or`, `!`, `!!` | 逻辑运算 |
| 集合 | `in` | 成员检查 |
| 条件 | `if` | 条件分支 |
| 算术 | `+`, `-`, `*`, `/`, `%` | 数学运算 |

#### 4.2.3 Fallback 评估器

当 JSONLogic 库评估失败时，引擎内置的 `_fallback_eval` 方法会尝试自行评估表达式，支持上述所有操作符的子集。这是一个防御性设计，确保在依赖库异常时仍能工作。

### 4.3 AuthzService 决策链路

**文件**: `backend/src/services/authz/service.py`

```
check_access(db, user_id, resource_type, action, resource_id, resource)
  │
  ├─ 1. 获取用户角色摘要 (role_ids, is_admin)
  │
  ├─ 2. 管理员绕过
  │     └─ is_admin → allowed=True, reason_code="rbac_admin_bypass"
  │
  ├─ 3. 构建 Subject Context
  │     └─ owner_party_ids, manager_party_ids, role_ids, perspectives
  │
  ├─ 4. 构建 Resource Payload
  │     └─ { resource_type, resource_id, ...resource }
  │
  ├─ 5. 决策缓存检查
  │     └─ 命中缓存 → 返回缓存决策
  │
  ├─ 6. 加载 ABAC 策略 (按 role_ids 查询)
  │
  ├─ 7. AuthzEngine 评估
  │     └─ evaluate_with_reason(subject, resource, action, policies)
  │
  ├─ 8. 无匹配策略时 Fallback
  │     ├─ 无匹配 policy rule → 检查静态 RBAC
  │     │   └─ RBAC 通过 → allowed=True, reason_code="rbac_permission_fallback"
  │     └─ 有匹配 policy rule → 不 fallback
  │
  ├─ 9. Authenticated Default 检查
  │     └─ action 在白名单中 → allowed=True, reason_code="authenticated_default_permission"
  │
  └─ 10. 缓存决策并返回
```

### 4.4 Subject Context 构建

**文件**: `backend/src/services/authz/context_builder.py`

`AuthzContextBuilder.build_subject_context()` 构建的上下文包含：

| 字段 | 来源 | 说明 |
|------|------|------|
| `user_id` | 参数 | 当前用户ID |
| `role_ids` | 参数/DB | 用户角色ID列表 |
| `owner_party_ids` | UserPartyBinding | 用户作为所有者的主体ID列表 |
| `manager_party_ids` | UserPartyBinding | 用户作为管理者的主体ID列表 |
| `perspectives` | 推导 | 可用视角列表 (owner/manager) |

### 4.5 Authenticated Default 权限

当 ABAC 策略未匹配且静态 RBAC 也未通过时，系统检查 action 是否在"认证用户默认白名单"中。这是一个安全网机制，确保已认证用户可以执行基本的读操作。

### 4.6 决策缓存

| 组件 | 说明 |
|------|------|
| `AuthzDecisionCache` | 内存缓存（可选 Redis 后端） |
| 缓存键 | `user_id:resource_type:resource_id:action:perspective:context_hash` |
| 失效触发 | `AUTHZ_USER_ROLE_UPDATED` 事件 |
| 角色哈希 | `compute_roles_hash(role_ids)` 用于检测角色变更 |

### 4.7 现状评估 ⚠️ 关键发现

**ABAC 策略表全部为空，当前系统实质上是纯 RBAC。**

| 表 | 状态 |
|---|---|
| `abac_policies` | 空表 |
| `abac_policy_rules` | 空表 |
| `abac_role_policies` | 空表 |

**根因**: `init_rbac_data.py` **不创建任何 ABAC 策略**。

**实际决策链路**:
```
check_access()
  → 管理员绕过? (是则允许)
  → 加载 ABAC 策略 → 空列表
  → AuthzEngine 评估 → deny_by_default
  → 无匹配 policy rule → Fallback 到静态 RBAC ✅ 实际生效的路径
  → RBAC 通过 → allowed=True, reason_code="rbac_permission_fallback"
```

**结论**: ABAC 引擎代码完整且功能齐全，但因为没有策略数据，所有授权决策最终都由静态 RBAC 决定。
ABAC 层当前仅为空壳代码，**不是真正的 RBAC+ABAC 混合模型**。

---

## 五、Party 多租户数据隔离

### 5.1 Party 体系概述

系统从 `organization_id` 迁移到 `party_id` 体系，支持更灵活的多租户数据隔离。

| 概念 | 说明 |
|------|------|
| `Party` | 主体实体，支持多种类型（组织、法人实体、个人等） |
| `UserPartyBinding` | 用户-主体绑定关系，支持有效期和主绑定 |
| `owner_party_ids` | 用户作为所有者的主体ID列表 |
| `manager_party_ids` | 用户作为管理者的主体ID列表 |

### 5.2 UserPartyBinding 模型

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | UUID | 主键 |
| `user_id` | FK | 用户ID |
| `party_id` | FK | 主体ID |
| `role_type` | String | 绑定角色类型（owner/manager） |
| `is_primary` | Boolean | 是否主绑定 |
| `valid_from` | DateTime | 生效时间 |
| `valid_to` | DateTime | 过期时间 |

### 5.3 视角机制 (Perspective)

#### 5.3.1 三种视角

| 视角 | 说明 | 数据范围 |
|------|------|----------|
| `owner` | 所有者视角 | 仅查看用户作为所有者的主体关联数据 |
| `manager` | 管理者视角 | 仅查看用户作为管理者的主体关联数据 |
| `all` | 全局视角 | 查看用户所有主体关联数据 (owner ∪ manager) |

#### 5.3.2 DataScopeContextChecker

**文件**: `backend/src/middleware/auth.py:366-475`

```
DataScopeContextChecker(request, current_user, db)
  │
  ├─ 1. 读取 X-Perspective 请求头
  │     └─ 未设置 → 默认 "all"
  │
  ├─ 2. 验证视角值 (owner/manager/all)
  │
  ├─ 3. 构建 Subject Context
  │     └─ 获取用户的 owner_party_ids 和 manager_party_ids
  │
  ├─ 4. 解析允许视角
  │     ├─ 管理员 → 所有注册视角
  │     └─ 普通用户 → 仅 subject_perspectives
  │
  ├─ 5. 验证请求视角是否允许
  │     └─ 不允许 → 403 Forbidden
  │
  └─ 6. 计算 effective_party_ids
        ├─ 管理员 → [] (无限制)
        ├─ perspective="all" → owner ∪ manager
        └─ perspective="owner/manager" → 对应 party_ids
```

#### 5.3.3 视角注册表

**文件**: `backend/src/services/authz/resource_perspective_registry.py`

每种资源类型可以注册支持的视角。例如：
- `asset` 资源可能支持 `owner` 和 `manager` 视角
- `user` 资源可能仅支持 `owner` 视角

### 5.4 资源上下文自动加载

`AuthzPermissionChecker._resolve_trusted_resource_context()` 支持 12 种资源类型的 party 上下文自动加载：

| 资源类型 | 加载的 party 字段 | 查询方式 |
|----------|-------------------|----------|
| `asset` | owner_party_id, manager_party_id | 直接查询 Asset 表 |
| `project` | manager_party_id | 直接查询 Project 表 |
| `contract` | owner_party_id, manager_party_id, tenant_party_id | 关联 ContractGroup 查询 |
| `ownership` | party_id (通过 code/name 查找 Party) | Ownership → Party 映射 |
| `party` | party_id | 直接查询 Party 表 |
| `role` | party_id (角色归属主体) | 直接查询 Role 表 |
| `user` | party_id (通过 UserPartyBinding) | User → UserPartyBinding → Party |
| `task` | party_id (通过任务关联用户推导) | AsyncTask → User → Party |
| `organization` | party_id (organization → Party 映射) | Organization → Party 映射 |
| `property_certificate` | party_id (通过 CertificatePartyRelation) | PropertyCertificate → CertificatePartyRelation → Party |

**设计亮点**: 自动从数据库加载资源的"可信" party 上下文，防止客户端伪造资源归属信息。

### 5.5 集合查询 Scope Hint 注入

当执行列表查询（`action=read/list`）且未指定具体 resource_id 时，系统自动注入 scope hint：

```
_build_subject_scope_hint()
  │
  └─ 注入:
       ├─ owner_party_ids / owner_party_id
       ├─ manager_party_ids / manager_party_id
       └─ party_id (第一个可用的)
```

这使得列表查询可以自动过滤出用户有权查看的数据。

### 5.6 Organization → Party 迁移状态

系统中仍存在 `organization_id` 的兼容层：

| 组件 | 状态 | 说明 |
|------|------|------|
| `OrganizationPermissionChecker` | DEPRECATED | 旧组织权限检查器 |
| `require_organization_access()` | DEPRECATED | 旧组织权限装饰器 |
| `organization_id` 参数 | DEPRECATED alias | 映射到 `party_id` |
| `User.default_organization_id` | 兼容保留 | 仍用作 Party 映射的回退 |

---

## 六、API 端点保护机制

### 6.1 三层防护架构

```
┌─────────────────────────────────────────────────────────────┐
│ Layer 3: Middleware (全局)                                   │
│  ┌──────────────┐ ┌──────────┐ ┌────────────┐ ┌──────────┐ │
│  │ Security     │ │ CSRF     │ │ Rate       │ │ Token    │ │
│  │ Headers      │ │ Validate │ │ Limiting   │ │ Blacklist│ │
│  └──────────────┘ └──────────┘ └────────────┘ └──────────┘ │
├─────────────────────────────────────────────────────────────┤
│ Layer 2: FastAPI Dependencies (路由级)                       │
│  ┌──────────────┐ ┌──────────┐ ┌────────────┐ ┌──────────┐ │
│  │ get_current_ │ │ require_ │ │ require_   │ │ require_ │ │
│  │ active_user  │ │ admin    │ │ authz()    │ │ perms()  │ │
│  └──────────────┘ └──────────┘ └────────────┘ └──────────┘ │
├─────────────────────────────────────────────────────────────┤
│ Layer 1: 装饰器 (函数级，遗留)                                │
│  ┌──────────────┐ ┌──────────┐ ┌────────────┐              │
│  │ @permission_ │ │ @admin_  │ │ @role_     │              │
│  │ required     │ │ required │ │ required   │              │
│  └──────────────┘ └──────────┘ └────────────┘              │
└─────────────────────────────────────────────────────────────┘
```

### 6.2 主要依赖详解

#### 6.2.1 认证依赖

| 依赖 | 功能 | 失败行为 |
|------|------|----------|
| `get_current_user` | 从 Cookie 读取 JWT 验证并返回 User | 401 Unauthorized |
| `get_current_active_user` | 包装 get_current_user + is_active 检查 | 400 Bad Request (未激活) |
| `get_optional_current_user` | 可选认证，无 token 返回 None | 不抛出异常 |

#### 6.2.2 授权依赖

| 依赖 | 功能 | 失败行为 |
|------|------|----------|
| `require_admin` | 检查 system:admin 或 system:manage 权限 | 403 Forbidden |
| `require_authz(action, resource_type, ...)` | ABAC 鉴权 + 资源上下文加载 | 403/404 |
| `require_permissions([resource:action])` | 静态 RBAC 权限检查 | 403 Forbidden |
| `require_data_scope_context(resource_type)` | 数据范围上下文解析与验证 | 403 Forbidden |

#### 6.2.3 AuthzPermissionChecker 详解

**文件**: `backend/src/middleware/auth.py:477-1308`

这是系统中最复杂的授权依赖，执行以下步骤：

1. **解析 Resource ID**: 从路径参数或 resolver 函数获取
2. **加载可信资源上下文**: 从数据库查询资源的真实 party 归属
3. **注入集合查询 Scope Hint**: 列表查询时自动注入用户 party 范围
4. **调用 AuthzService.check_access()**: 执行 ABAC 评估
5. **处理结果**: 允许则返回 AuthzContext，拒绝则 403/404

**deny_as_not_found 参数**: 当设置为 True 时，权限不足返回 404 而非 403，用于防止信息泄露（攻击者无法通过 403 判断资源是否存在）。

### 6.3 双轨制问题

系统中存在两套并行的权限检查模式：

| 模式 | 机制 | 使用场景 |
|------|------|----------|
| **新模式** | `require_authz()` | ABAC + Party 数据范围 + 资源上下文 |
| **旧模式** | `require_admin` / `PermissionChecker` | 纯静态 RBAC 检查 |

**不一致性示例**:
- 部分端点同时使用两者（冗余检查）
- 部分端点仅使用旧模式（缺少 Party 数据范围过滤）
- 部分端点仅使用新模式（无 RBAC 回退）

### 6.4 中间件清单

| 中间件 | 功能 | 状态 |
|--------|------|------|
| `SecurityHeadersMiddleware` | 安全 HTTP 头 (CSP, HSTS, X-Frame-Options) | 活跃 |
| `CSRFMiddleware` | Double-submit CSRF Token 验证 | 活跃 |
| `RequestValidationMiddleware` | 速率限制、IP 黑名单、XSS 检测 | 活跃 |
| `FileUploadSecurityMiddleware` | 文件上传安全检查 | 活跃 |
| `TokenBlacklistGuard` | Token 黑名单检查（熔断器） | 活跃 |
| `OrganizationPermissionChecker` | 组织权限检查 | DEPRECATED |

---

## 七、前端权限控制

### 7.1 AuthContext 架构

**文件**: `frontend/src/contexts/AuthContext.tsx`

#### 7.1.1 提供的能力

| 属性/方法 | 类型 | 说明 |
|-----------|------|------|
| `user` | User \| null | 当前用户信息 |
| `permissions` | Permission[] | 权限摘要（旧机制，@deprecated） |
| `capabilities` | CapabilityItem[] | 能力集（新机制，Phase 3） |
| `capabilitiesLoading` | boolean | 能力集加载状态 |
| `isAuthenticated` | boolean | 是否已认证 |
| `isAdmin` | boolean | 是否管理员 |
| `initializing` | boolean | 初始化中（阻止渲染） |
| `login()` | async | 登录 |
| `logout()` | async | 登出 |
| `refreshUser()` | async | 刷新用户信息 |
| `refreshCapabilities()` | async | 刷新能力集 |
| `hasPermission(resource, action)` | boolean | 权限检查（兼容层） |
| `hasAnyPermission(permissions)` | boolean | 多权限检查（兼容层） |

#### 7.1.2 状态恢复流程

```
AuthProvider 初始化
  │
  ├─ 1. 从 AuthStorage 读取本地元数据
  │     ├─ user
  │     ├─ permissions
  │     └─ capabilities
  │
  ├─ 2. 有本地元数据?
  │     ├─ 是 → 先展示旧用户信息
  │     │     ├─ 调用 /auth/me 校验当前会话
  │     │     ├─ 检测跨标签账号切换
  │     │     ├─ 刷新权限和能力集
  │     │     └─ 同步最新用户信息
  │     └─ 否 → 检查会话 Cookie 提示
  │             ├─ 有 Cookie → 调用 /auth/me 恢复会话
  │             └─ 无 Cookie → 保持未登录状态
  │
  └─ 3. 设置 initializing = false
```

**设计亮点**:
- 跨标签账号切换检测：通过 `/auth/me` 校验，避免多标签页登录不同账号时展示错误用户
- 能力集失效版本控制：`capabilityRequestVersionRef` 防止竞态
- 降级策略：权限/能力集拉取失败时使用兜底数据

### 7.2 权限检查优先级

`hasPermission(resource, action)` 的检查顺序：

```
1. user.is_admin === true → 返回 true (管理员全通)
2. capabilities 匹配:
   └─ capabilities.some(c => c.resource === resource && c.actions.includes(action))
3. permissions 兼容回退:
   └─ permissions.some(p => p.resource === resource && p.action === action)
```

### 7.3 前端 Guards

#### 7.3.1 AuthGuard

**文件**: `frontend/src/components/Auth/AuthGuard.tsx`

功能：
- 检查 `isAuthenticated`
- 未认证时重定向到登录页
- 处理 `initializing` 状态（显示加载中）

#### 7.3.2 PermissionGuard

**文件**: `frontend/src/components/System/PermissionGuard.tsx`

功能：
- 检查 `hasPermission(resource, action)`
- 无权限时显示 fallback UI 或重定向
- 支持 `requiredPermissions` 数组（任一匹配即可）

#### 7.3.3 CapabilityGuard

**文件**: `frontend/src/components/System/CapabilityGuard.tsx`

功能：
- 基于 capabilities 的新守卫（Phase 3）
- 支持 `resource` + `action` 检查
- 支持 `perspective` 检查
- 支持 `dataScope` 检查

### 7.4 数据范围前端控制

**文件**: `frontend/src/stores/dataScopeStore.ts`

`useDataScopeStore` 从 capabilities 初始化数据范围：

```
initFromCapabilities(capabilities, isAdmin)
  │
  └─ 提取每个 capability 的 dataScope:
       ├─ owner_party_ids
       └─ manager_party_ids
```

### 7.5 前端问题

| # | 问题 | 严重性 | 说明 |
|---|------|--------|------|
| 1 | 路由级守卫覆盖不完整 | **中** | 依赖组件级 PermissionGuard，缺少全局路由守卫 |
| 2 | 双轨权限并存 | 中 | capabilities (新) 和 permissions (旧) 同时存在 |
| 3 | 数据范围前端控制复杂 | 低 | Party 绑定逻辑在前端需要更多抽象 |
| 4 | 能力集加载失败降级 | 低 | 降级为空能力集可能导致功能不可用 |

---

## 八、DEPRECATED 组件清单

### 8.1 后端 DEPRECATED 组件

| 组件 | 类型 | 位置 | 替代方案 |
|------|------|------|----------|
| `ResourcePermission` | Model | `models/rbac.py:243-311` | ABAC 资源上下文 |
| `PermissionGrant` | Model | `models/rbac.py:313-399` | Capabilities 机制 |
| `CRUDResourcePermission` | CRUD | `crud/rbac.py` | ABAC CRUD |
| `CRUDPermissionGrant` | CRUD | `crud/rbac.py` | Capabilities CRUD |
| `OrganizationPermissionChecker` | Middleware | `middleware/auth.py:1335-1372` | DataScopeContextChecker |
| `require_organization_access()` | Factory | `middleware/auth.py:1368-1372` | `require_authz()` |
| `organization_id` 参数 | 参数 | 多处 | `party_id` |
| `grant_permission_to_user()` | Service | `rbac_service.py:909-988` | Capabilities API |
| `update_permission_grant()` | Service | `rbac_service.py:1021-1109` | Capabilities API |
| `revoke_permission_grant()` | Service | `rbac_service.py:1111-1148` | Capabilities API |
| `list_permission_grants()` | Service | `rbac_service.py:996-1019` | Capabilities API |
| `_check_grant_permission()` | Service | `rbac_service.py:773-842` | ABAC 评估 |

### 8.2 前端 DEPRECATED 组件

| 组件 | 类型 | 位置 | 替代方案 |
|------|------|------|----------|
| `permissions` 数组 | State | `AuthContext.tsx` | `capabilities` |
| `hasPermission()` | Method | `AuthContext.tsx:490-513` | `canPerform()` / `useCapabilities` |
| `hasAnyPermission()` | Method | `AuthContext.tsx:515-522` | `canPerform()` / `useCapabilities` |

### 8.3 清理建议

1. **Phase 1**: 移除 `PermissionGrant` 相关 CRUD 和 Service 方法
2. **Phase 2**: 移除 `ResourcePermission` 模型和关联逻辑
3. **Phase 3**: 移除 `OrganizationPermissionChecker` 和 `require_organization_access()`
4. **Phase 4**: 前端统一迁移到 capabilities，移除 permissions 兼容层
5. **Phase 5**: 清理所有 `organization_id` 兼容参数

---

## 九、综合评估与建议

### 9.1 优势

| # | 优势 | 说明 |
|---|------|------|
| 1 | **架构设计先进** | RBAC + ABAC + Party 多租户混合模型，扩展性强，支持未来细粒度权限需求 |
| 2 | **安全基线扎实** | httpOnly Cookie、JWT 黑名单、CSRF、bcrypt、账户锁定、熔断 fail-closed |
| 3 | **审计完善** | 权限变更审计日志 + 认证审计日志，满足合规要求 |
| 4 | **缓存体系完整** | 多层缓存 + 事件驱动失效，支持多实例部署 |
| 5 | **前端能力集** | Capabilities 机制支持数据范围 + 视角 + 动作的结构化权限 |
| 6 | **资源上下文可信加载** | 自动从数据库加载资源 party 归属，防止客户端伪造 |
| 7 | **管理员判断基于权限** | 不依赖角色名，而是检查 system:admin/system:manage 权限 |
| 8 | **Token 熔断保护** | Redis 不可用时 fail-closed，宁可拒绝也不放行 |

### 9.2 风险与不足

| # | 风险 | 严重性 | 影响 | 位置 |
|---|------|--------|------|------|
| 1 | **ABAC 未激活，实际为纯 RBAC** | **高** | 设计文档声称 RBAC+ABAC 混合模型，但 ABAC 策略表全空，所有请求 fallback 到静态 RBAC | `init_rbac_data.py` |
| 2 | **管理员初始密码为 dummy hash** | **高** | 首次部署无法正常登录 | `init_rbac_data.py:184` |
| 3 | **双轨并行** | **高** | 新旧两套权限系统并存，维护成本高，易出错 | 全局 |
| 4 | **DEPRECATED 代码未清理** | 中 | 大量废弃代码仍在运行，增加代码复杂度 | 全局 |
| 5 | **缓存竞态** | 中 | 复杂的多层缓存失效链在高并发下可能不一致 | `rbac_service.py` |
| 6 | **前端路由守卫不完整** | 中 | 缺少全局路由级权限拦截 | 前端路由 |
| 7 | **无自助密码重置** | 低 | 密码遗忘只能靠管理员重置，运维负担 | 整体架构 |
| 8 | **无邮箱验证** | 低 | 新用户注册后邮箱未验证 | 整体架构 |
| 9 | **N+1 查询风险** | 低 | 角色缓存失效时查询所有关联用户 | `rbac_service.py:655-670` |

### 9.3 建议优先级

#### P0 - 必须修复

| # | 事项 | 理由 | 预计工作量 |
|---|------|------|------------|
| 1 | 修复 admin dummy hash，实现安全的初始密码设置流程 | 阻塞首次部署 | 2h |
| 2 | 清理 DEPRECATED 代码，消除双轨制 | 降低维护成本，减少 bug 风险 | 1-2 天 |

#### P1 - 应该修复

| # | 事项 | 理由 | 预计工作量 |
|---|------|------|------------|
| 3 | 初始化 ABAC 策略种子数据，让 ABAC 真正生效 | 发挥架构设计能力 | 1 天 |
| 4 | 前端实现全局路由级权限守卫 | 防止未授权访问 | 0.5 天 |
| 5 | 统一 API 端点的权限检查模式 | 消除不一致性 | 0.5 天 |

#### P2 - 建议改进

| # | 事项 | 理由 | 预计工作量 |
|---|------|------|------------|
| 6 | 添加邮箱验证 + 自助密码重置 | 降低运维负担 | 1-2 天 |
| 7 | 缓存一致性压力测试 | 验证高并发场景下的正确性 | 1 天 |
| 8 | 补充 RBAC/ABAC 单元测试 | 提高代码质量 | 1-2 天 |
| 9 | 添加 OAuth/SSO 支持 | 企业集成需求 | 2-3 天 |

### 9.4 架构演进路线图

```
当前状态 (Phase 1) — 纯 RBAC
  │
  ├── 静态 RBAC 为主（唯一生效的授权层）
  ├── ABAC 空壳（策略表全空，代码完整但未激活）
  ├── 双轨并行 (新旧权限系统)
  └── Party 体系迁移中
  │
  ▼
Phase 2: 清理与统一
  │
  ├── 清理所有 DEPRECATED 代码
  ├── 统一 API 端点使用 require_authz()
  ├── 修复 admin 初始密码
  └── 前端统一使用 capabilities
  │
  ▼
Phase 3: ABAC 激活
  │
  ├── 初始化 ABAC 策略种子
  ├── 定义资源-视角-数据范围映射
  ├── 为关键资源编写 ABAC 策略
  └── 验证 ABAC 评估性能
  │
  ▼
Phase 4: 增强与优化
  │
  ├── 全局路由级权限守卫
  ├── 缓存一致性优化
  ├── 自助密码重置
  └── 邮箱验证
  │
  ▼
Phase 5: 企业集成
  │
  ├── OAuth/SSO 支持
  ├── SAML 集成
  ├── SCIM 用户同步
  └── 审计日志增强
```

### 9.5 边界情况与建议测试用例

#### 9.5.1 边界情况

1. **用户同时拥有多个角色**：权限合并是否正确？
2. **角色分配过期**：expires_at 过期后权限是否立即失效？
3. **Token 黑名单熔断**：Redis 不可用时是否正确 fail-closed？
4. **跨标签账号切换**：多标签页登录不同账号时是否正确同步？
5. **Party 绑定变更**：UserPartyBinding 变更后权限是否立即更新？
6. **ABAC 策略为空**：fallback 到 RBAC 是否正确？
7. **系统角色保护**：尝试修改/删除系统角色是否正确拒绝？
8. **角色正在使用**：删除有用户绑定的角色是否正确拒绝？

#### 9.5.2 建议测试用例

| # | 测试场景 | 预期结果 |
|---|----------|----------|
| 1 | admin 用户访问任意资源 | 允许（admin bypass） |
| 2 | viewer 用户尝试创建资产 | 拒绝（无 asset:create 权限） |
| 3 | asset_manager 访问项目资源 | 拒绝（仅 asset + statistics） |
| 4 | Token 过期后访问 API | 401 Unauthorized |
| 5 | 登出后使用旧 Token | 401（Token 在黑名单） |
| 6 | Redis 不可用时认证 | 401（fail-closed） |
| 7 | 修改系统角色 | 403（OperationNotAllowedError） |
| 8 | 角色分配过期后访问 | 拒绝（expires_at 检查） |
| 9 | X-Perspective 设置为无效值 | 400 Bad Request |
| 10 | 用户无 Party 绑定时访问资源 | 使用 fallback 或拒绝 |
| 11 | ABAC deny 策略匹配 | 拒绝（deny 优先） |
| 12 | 权限缓存失效后访问 | 从 DB 重新加载 |

---

## 附录 A：关键文件索引

| 类别 | 文件路径 | 行数 |
|------|----------|------|
| 模型 | `backend/src/models/rbac.py` | 448 |
| 模型 | `backend/src/models/auth.py` | - |
| 模型 | `backend/src/models/abac.py` | - |
| 中间件 | `backend/src/middleware/auth.py` | 1529+ |
| 服务 | `backend/src/services/permission/rbac_service.py` | 1373 |
| 服务 | `backend/src/services/authz/service.py` | 382 |
| 服务 | `backend/src/services/authz/engine.py` | 331 |
| 前端 | `frontend/src/contexts/AuthContext.tsx` | 576 |
| 初始化 | `backend/scripts/setup/init_rbac_data.py` | 552 |

## 附录 B：权限命名规范

权限命名格式：`{resource}:{action}`

| 资源 (resource) | 操作 (action) | 示例 |
|-----------------|---------------|------|
| asset | read, create, update, delete | `asset:read` |
| property_certificate | read, create, update, delete | `property_certificate:create` |
| project | read, create, update, delete | `project:update` |
| ownership | read, create, update, delete | `ownership:delete` |
| rent_contract | read, create, update, delete | `rent_contract:read` |
| statistics | read, export | `statistics:export` |
| system | admin, manage, audit, backup | `system:admin` |
| user | read, create, update, delete | `user:create` |
| role | read, create, update, delete, assign | `role:assign` |
| organization | read, create, update, delete | `organization:read` |
| permission_grant | read, assign, revoke, check | `permission_grant:revoke` |
| audit | read, export | `audit:export` |
| excel_config | read, write | `excel_config:write` |
| approval | read, start, approve, reject, withdraw | `approval:approve` |

## 附录 C：安全配置清单

| 配置项 | 环境变量 | 默认值 | 说明 |
|--------|----------|--------|------|
| JWT 密钥 | `SECRET_KEY` | 必须设置 | HS256 签名密钥 |
| 数据加密密钥 | `DATA_ENCRYPTION_KEY` | 可选 | AES-256-CBC 加密 PII |
| Access Token 过期 | `ACCESS_TOKEN_EXPIRE_MINUTES` | 30 | 分钟 |
| Refresh Token 过期 | `REFRESH_TOKEN_EXPIRE_DAYS` | 7 | 天 |
| 最大失败次数 | `MAX_FAILED_ATTEMPTS` | 配置值 | 账户锁定阈值 |
| 锁定持续时间 | `LOCKOUT_DURATION` | 配置值 | 分钟 |
| 最大并发会话 | `MAX_CONCURRENT_SESSIONS` | 配置值 | 会话限制 |
| 审计日志保留 | `AUDIT_LOG_RETENTION_DAYS` | 配置值 | 天 |
| 密码最小长度 | `MIN_PASSWORD_LENGTH` | 配置值 | 字符 |
