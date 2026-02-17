# 认证 API

## ✅ Status
**当前状态**: Supplemental (2026-02-16)

## 认证模式
- 当前以 Cookie 认证为主
- 登录后由服务端写入 HttpOnly Cookie
- 登录/刷新会轮转 `auth_token` 与 `refresh_token` Cookie
- 登录请求字段为 `identifier`（用户名或手机号），响应体不返回 token

## 核心端点
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/auth/login` | 用户登录（写入 Cookie） |
| POST | `/api/v1/auth/logout` | 用户登出（清理 Cookie） |
| POST | `/api/v1/auth/refresh` | 刷新令牌 |
| GET  | `/api/v1/auth/me` | 获取当前用户信息 |

## 用户管理端点（管理员）
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/auth/users` | 用户列表 |
| POST | `/api/v1/auth/users` | 创建用户 |
| GET | `/api/v1/auth/users/{user_id}` | 用户详情 |
| PUT | `/api/v1/auth/users/{user_id}` | 更新用户 |
| DELETE | `/api/v1/auth/users/{user_id}` | 删除用户 |

## 组织与角色
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/organizations` | 组织列表 |
| GET | `/api/v1/roles` | 角色列表 |

## 会话与审计
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/auth/sessions` | 会话列表 |
| DELETE | `/api/v1/auth/sessions/{session_id}` | 撤销会话 |
| GET | `/api/v1/auth/logs` | 审计日志统计 |

## 权限控制
- 基础角色: `admin`, `user`
- 管理员接口需 `require_admin` 校验
- 权限细节见：
  - `backend/src/middleware/auth.py`
  - `backend/src/services/permission/rbac_service.py`

## 相关代码
- 认证入口: `backend/src/api/v1/auth/auth.py`
- 认证端点: `backend/src/api/v1/auth/auth_modules/authentication.py`
- 用户管理: `backend/src/api/v1/auth/auth_modules/users.py`
