# 认证 API 文档

## 📋 Purpose
本文档详细说明土地物业管理系统的认证相关 API，包括登录、注册、令牌刷新、用户管理等接口。

## 🎯 Scope
- 用户认证流程
- JWT 令牌管理
- 用户注册和登录
- 密码修改和重置
- 会话管理
- 权限控制

## ✅ Status
**当前状态**: Active (2025-12-23 创建)
**API 版本**: v1.0.0
**基础路径**: `/api/v1/auth`

---

## 🔐 认证架构概述

### JWT Token 认证流程

```
┌─────────┐                ┌─────────┐                ┌─────────┐
│ Frontend│                │ Backend │                │ Database│
└────┬────┘                └────┬────┘                └────┬────┘
     │                          │                          │
     │ 1. POST /login           │                          │
     │ {username, password}     │                          │
     ├─────────────────────────>│                          │
     │                          │ 2. 验证用户凭据           │
     │                          ├─────────────────────────>│
     │                          │ 3. 返回用户信息           │
     │                          │<─────────────────────────┤
     │                          │                          │
     │                          │ 4. 生成 JWT Tokens        │
     │                          │ access_token (15min)     │
     │                          │ refresh_token (7days)    │
     │ 5. 返回 Tokens           │                          │
     │<─────────────────────────┤                          │
     │                          │                          │
     │ 6. 存储 Tokens           │                          │
     │ (localStorage/cookie)    │                          │
     │                          │                          │
     │ 7. GET /api/assets       │                          │
     │ Header: Authorization:  │                          │
     │ Bearer <access_token>    │                          │
     ├─────────────────────────>│                          │
     │                          │ 8. 验证 Token             │
     │ 9. 返回受保护资源         │                          │
     │<─────────────────────────┤                          │
```

### Token 类型说明

| Token 类型 | 有效期 | 用途 | 存储 |
|------------|--------|------|------|
| **Access Token** | 15 分钟（默认） | 访问受保护的 API 资源 | 内存/localStorage |
| **Refresh Token** | 7 天（默认） | 刷新 Access Token | HttpOnly Cookie/安全存储 |

**证据来源**: `backend/src/core/config.py:63-74`

---

## 📡 API 端点详解

### 1. 用户登录

**端点**: `POST /api/v1/auth/login`

**请求体**:
```json
{
  "username": "admin",
  "password": "admin123"
}
```

**响应示例**:
```json
{
  "success": true,
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "Bearer",
    "expires_in": 900,
    "user": {
      "id": "user_123",
      "username": "admin",
      "email": "admin@example.com",
      "full_name": "系统管理员",
      "is_active": true,
      "roles": ["admin"]
    }
  },
  "message": "登录成功",
  "code": "SUCCESS"
}
```

**错误响应**:
```json
{
  "success": false,
  "error": {
    "code": "AUTH_CREDENTIALS_INVALID",
    "message": "用户名或密码错误"
  }
}
```

**使用示例**:
```bash
# 使用 curl
curl -X POST "http://localhost:8002/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}'

# 使用 JavaScript fetch
const response = await fetch('/api/v1/auth/login', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ username, password })
});
const data = await response.json();
```

**证据来源**: `backend/src/api/v1/auth.py:32-100`

---

### 2. 刷新令牌

**端点**: `POST /api/v1/auth/refresh`

**请求体**:
```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**响应示例**:
```json
{
  "success": true,
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "Bearer",
    "expires_in": 900
  }
}
```

**错误响应**:
```json
{
  "success": false,
  "error": {
    "code": "AUTH_TOKEN_EXPIRED",
    "message": "刷新令牌已过期"
  }
}
```

**最佳实践**:
```typescript
// 前端自动刷新令牌
let refreshPromise: Promise<string> | null = null;

async function getAccessToken(): Promise<string> {
  let token = localStorage.getItem('access_token');

  if (!token) {
    throw new Error('No access token');
  }

  // 检查是否即将过期（提前 1 分钟刷新）
  const payload = parseJWT(token);
  const expiresSoon = payload.exp * 1000 - Date.now() < 60000;

  if (expiresSoon && refreshPromise) {
    token = await refreshPromise;
  } else if (expiresSoon) {
    refreshPromise = refreshToken();
    token = await refreshPromise;
    refreshPromise = null;
  }

  return token;
}

async function refreshToken(): Promise<string> {
  const refreshToken = localStorage.getItem('refresh_token');
  const response = await fetch('/api/v1/auth/refresh', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ refresh_token: refreshToken })
  });

  if (!response.ok) {
    // 刷新失败，跳转到登录页
    localStorage.clear();
    window.location.href = '/login';
    throw new Error('Token refresh failed');
  }

  const data = await response.json();
  localStorage.setItem('access_token', data.data.access_token);
  return data.data.access_token;
}
```

---

### 3. 获取当前用户信息

**端点**: `GET /api/v1/auth/me`

**请求头**:
```http
Authorization: Bearer <access_token>
```

**响应示例**:
```json
{
  "success": true,
  "data": {
    "id": "user_123",
    "username": "admin",
    "email": "admin@example.com",
    "full_name": "系统管理员",
    "is_active": true,
    "is_admin": true,
    "roles": [
      {
        "id": "role_1",
        "name": "admin",
        "description": "系统管理员"
      }
    ],
    "permissions": [
      "users.create",
      "users.read",
      "users.update",
      "users.delete",
      "assets.*"
    ],
    "organization": {
      "id": "org_1",
      "name": "总公司",
      "level": 1
    }
  }
}
```

**错误响应**:
```json
{
  "success": false,
  "error": {
    "code": "AUTH_TOKEN_INVALID",
    "message": "无效的访问令牌"
  }
}
```

**使用示例**:
```typescript
// 获取当前用户信息
async function getCurrentUser(): Promise<User> {
  const token = localStorage.getItem('access_token');

  const response = await fetch('/api/v1/auth/me', {
    headers: {
      'Authorization': `Bearer ${token}`
    }
  });

  if (!response.ok) {
    throw new Error('Failed to fetch user info');
  }

  const data = await response.json();
  return data.data;
}
```

---

### 4. 修改密码

**端点**: `PUT /api/v1/auth/change-password`

**请求头**:
```http
Authorization: Bearer <access_token>
```

**请求体**:
```json
{
  "old_password": "oldpass123",
  "new_password": "newpass456"
}
```

**响应示例**:
```json
{
  "success": true,
  "message": "密码修改成功",
  "code": "SUCCESS"
}
```

**密码要求**:
- 最小长度: 8 字符（可通过 `MIN_PASSWORD_LENGTH` 配置）
- 建议包含大小写字母、数字和特殊字符
- 不能与旧密码相同

**证据来源**: `backend/src/core/config.py:162`

---

### 5. 用户注销

**端点**: `POST /api/v1/auth/logout`

**请求头**:
```http
Authorization: Bearer <access_token>
```

**请求体**:
```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**响应示例**:
```json
{
  "success": true,
  "message": "注销成功",
  "code": "SUCCESS"
}
```

**前端处理**:
```typescript
async function logout() {
  const token = localStorage.getItem('access_token');
  const refreshToken = localStorage.getItem('refresh_token');

  await fetch('/api/v1/auth/logout', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ refresh_token: refreshToken })
  });

  // 清除本地存储
  localStorage.removeItem('access_token');
  localStorage.removeItem('refresh_token');
  localStorage.removeItem('user');

  // 跳转到登录页
  window.location.href = '/login';
}
```

---

### 6. 用户注册（管理员）

**端点**: `POST /api/v1/auth/users`

**请求头**:
```http
Authorization: Bearer <admin_access_token>
```

**请求体**:
```json
{
  "username": "newuser",
  "email": "newuser@example.com",
  "password": "password123",
  "full_name": "新用户",
  "organization_id": "org_1",
  "role_ids": ["role_user"]
}
```

**响应示例**:
```json
{
  "success": true,
  "data": {
    "id": "user_456",
    "username": "newuser",
    "email": "newuser@example.com",
    "full_name": "新用户",
    "is_active": true,
    "created_at": "2025-12-23T10:30:00Z"
  }
}
```

**权限要求**: 需要管理员权限（`users.create`）

---

## 🛡️ 权限控制

### 权限检查机制

系统使用 RBAC（基于角色的访问控制）模型：

```python
# 后端权限装饰器
@require_admin  # 需要管理员权限
async def admin_only_endpoint():
    pass

@require_permission("assets.create")  # 需要特定权限
async def create_asset():
    pass
```

**权限字符串格式**: `资源.操作`

| 权限 | 说明 |
|------|------|
| `users.create` | 创建用户 |
| `users.read` | 查看用户 |
| `users.update` | 更新用户 |
| `users.delete` | 删除用户 |
| `assets.*` | 资产管理所有权限 |
| `contracts.*` | 合同管理所有权限 |

### 前端权限守卫

```typescript
// PermissionGuard 组件使用
import { PermissionGuard } from '@/components/Router/PermissionGuard';

function UserManagementPage() {
  return (
    <PermissionGuard resource="users" action="read">
      <UserList />
    </PermissionGuard>
  );
}
```

**证据来源**: `frontend/src/components/Router/PermissionGuard.tsx`

---

## 🔒 安全最佳实践

### 1. Token 存储

**推荐方式**:
```typescript
// Access Token - 内存存储（最安全）
let accessToken: string | null = null;

// Refresh Token - HttpOnly Cookie（后端设置）
// 前端无法通过 JavaScript 访问
```

**不推荐方式**:
```typescript
// ❌ 不要存储在 localStorage（易受 XSS 攻击）
localStorage.setItem('token', token);

// ❌ 不要存储在 URL 中
window.location.hash = `#token=${token}`;
```

### 2. Token 自动刷新

```typescript
// Axios 拦截器自动刷新
apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      try {
        const newToken = await refreshToken();
        originalRequest.headers.Authorization = `Bearer ${newToken}`;
        return apiClient(originalRequest);
      } catch {
        // 刷新失败，跳转登录
        window.location.href = '/login';
      }
    }

    return Promise.reject(error);
  }
);
```

### 3. CSRF 保护

```http
# 后端应设置 CSRF Token
Set-Cookie: csrf_token=xxx; HttpOnly; Secure; SameSite=Strict

# 前端请求携带 CSRF Token
X-CSRF-Token: xxx
```

### 4. 安全配置

**生产环境必须设置** (`backend/.env`):
```bash
# 强密钥（至少 32 字符）
SECRET_KEY=<your-strong-random-key>

# 短期 Access Token
ACCESS_TOKEN_EXPIRE_MINUTES=120

# 启用 Token 黑名单
TOKEN_BLACKLIST_ENABLED=true

# 启用 JTI 声明
ENABLE_JTI_CLAIM=true
```

**证据来源**: `backend/src/core/config.py:62-81`

---

## 🧪 测试示例

### 使用 curl 测试

```bash
# 1. 登录获取 token
curl -X POST "http://localhost:8002/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}' \
  | jq -r '.data.access_token' > token.txt

# 2. 使用 token 访问受保护的 API
TOKEN=$(cat token.txt)
curl -X GET "http://localhost:8002/api/v1/assets" \
  -H "Authorization: Bearer $TOKEN"

# 3. 刷新 token
curl -X POST "http://localhost:8002/api/v1/auth/refresh" \
  -H "Content-Type: application/json" \
  -d '{"refresh_token": "<your_refresh_token>"}'
```

### 使用 Postman 测试

```javascript
// Pre-request Script - 自动获取 token
if (!pm.environment.get("access_token")) {
  const loginRequest = {
    url: pm.environment.get("API_URL") + "/api/v1/auth/login",
    method: "POST",
    header: { "Content-Type": "application/json" },
    body: {
      mode: "raw",
      raw: JSON.stringify({
        username: pm.environment.get("USERNAME"),
        password: pm.environment.get("PASSWORD")
      })
    }
  };

  pm.sendRequest(loginRequest, (err, res) => {
    if (res && res.code === 200) {
      pm.environment.set("access_token", res.json().data.access_token);
    }
  });
}

// Authorization - Bearer Token
// Header: Authorization = Bearer {{access_token}}
```

---

## 🚨 错误码说明

| 错误码 | HTTP状态码 | 说明 | 解决方案 |
|--------|------------|------|----------|
| `AUTH_CREDENTIALS_INVALID` | 401 | 用户名或密码错误 | 检查用户名密码 |
| `AUTH_TOKEN_EXPIRED` | 401 | Token 过期 | 使用 refresh_token 刷新 |
| `AUTH_TOKEN_INVALID` | 401 | Token 无效 | 重新登录 |
| `AUTH_PERMISSION_DENIED` | 403 | 权限不足 | 联系管理员分配权限 |
| `USER_NOT_FOUND` | 404 | 用户不存在 | 检查用户 ID |
| `USER_DISABLED` | 403 | 用户已禁用 | 联系管理员 |
| `PASSWORD_TOO_WEAK` | 400 | 密码强度不足 | 使用更强的密码 |
| `MAX_LOGIN_ATTEMPTS` | 429 | 登录尝试过多 | 等待或联系管理员 |

---

## 📋 审计日志

系统记录所有认证相关操作：

```json
{
  "id": "audit_123",
  "user_id": "user_123",
  "action": "user_login",
  "resource_type": "authentication",
  "ip_address": "192.168.1.100",
  "user_agent": "Mozilla/5.0...",
  "timestamp": "2025-12-23T10:30:00Z",
  "success": true
}
```

**查询审计日志**:
```bash
# 获取用户登录历史
GET /api/v1/auth/audit-logs?user_id=user_123&action=user_login
```

---

## 🔗 相关链接

### API 文档
- [API 总览](api-overview.md)
- [资产管理 API](assets-api.md)
- [前端后端集成](frontend-backend.md)

### 相关文档
- [环境配置](../guides/environment-setup.md)
- [数据库指南](../guides/database.md)

### 代码位置
- [认证路由](../../backend/src/api/v1/auth.py)
- [认证服务](../../backend/src/services/auth_service.py)
- [权限中间件](../../backend/src/middleware/auth.py)
- [认证 Schema](../../backend/src/schemas/auth.py)

## 📋 Changelog

### 2025-12-23 v1.0.0 - 初始版本
- ✨ 新增：认证 API 完整文档
- 🔐 新增：JWT 认证流程说明
- 📡 新增：所有认证端点详解
- 🛡️ 新增：权限控制机制说明
- 🔒 新增：安全最佳实践
- 🧪 新增：测试示例和错误码说明

## 🔍 Evidence Sources
- **认证路由**: `backend/src/api/v1/auth.py`
- **认证服务**: `backend/src/services/auth_service.py`
- **权限中间件**: `backend/src/middleware/auth.py`
- **配置文件**: `backend/src/core/config.py`
- **前端权限守卫**: `frontend/src/components/Router/PermissionGuard.tsx`
