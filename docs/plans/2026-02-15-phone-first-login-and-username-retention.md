# 手机号优先登录与用户名保留策略研究（2026-02-15）

## 1. 文档目标

本文用于回答两个决策问题：

1. 是否应保留 `username` 字段。
2. 是否应改为“直接手机号登录”为主入口。

结论先行：**建议保留用户名字段，但将登录体验切换为“手机号优先”；用户名转为内部稳定标识与备用登录方式。**

---

## 2. 当前系统基线（以 2026-02-15 代码为准）

### 2.1 后端用户模型与约束

- `backend/src/models/auth.py`
- 当前 `users` 表关键字段：
  - `id`：主键（UUID 字符串）
  - `username`：唯一、非空、索引
  - `email`：唯一、可空、索引
  - `phone`：唯一、非空、索引

说明：当前数据库层并非“无用户名”模型，而是用户名和手机号都处于强约束状态。

### 2.2 登录请求与认证链路

- `backend/src/schemas/auth.py` `LoginRequest`
  - 字段名仍是 `username`，描述为“用户名或邮箱”。
- `backend/src/services/core/authentication_service.py`
  - `authenticate_user(username, password)`
- `backend/src/crud/auth.py`
  - `find_active_by_login_async(...)` 仅查询 `User.username == login` 或 `User.email == login`

结论：**后端当前并不支持手机号作为登录标识。**

### 2.3 前端登录页现状

- `frontend/src/pages/LoginPage.tsx`
  - UI 文案是“用户名 / 手机号”，占位符“请输入手机号”。
  - 但提交参数仍是 `login({ username: formData.username, password })`。
- `frontend/src/types/auth.ts`
  - `LoginCredentials` 仍定义为 `{ username: string; password: string }`。
- `frontend/src/services/authService.ts`
  - 调用 `/auth/login` 直接透传 `credentials.username`。

结论：**前端文案与后端能力存在语义错位**（用户以为是手机号登录，但实际并不支持手机号识别）。

### 2.4 用户名耦合范围

代码中 `username` 被广泛用于：

- 权限与审计日志记录（如 `backend/src/security/permissions.py`、`backend/src/security/audit_logger.py`）
- 操作日志显示与反查（如 `backend/src/services/operation_log/service.py`）
- 系统管理页账号展示（如 `frontend/src/pages/System/UserManagement/components/UserTable.tsx`）

这意味着“直接删除用户名”会触发大面积回归风险。

---

## 3. 业务与架构目标

建议目标拆分为三层：

1. **体验目标**：普通用户尽量通过手机号快速登录。
2. **身份目标**：系统内部保持稳定、不可变、可审计的账号标识。
3. **安全目标**：登录便利性提升不降低风控能力（防撞库、防枚举、防短信滥用）。

---

## 4. 方案比较

| 方案 | 描述 | 优点 | 缺点 | 结论 |
|---|---|---|---|---|
| A | 删除用户名，仅保留手机号登录 | 前端心智最简单 | 账号稳定性差（换号/回收），系统账号难处理，历史耦合改造成本高 | 不建议 |
| B | 保留用户名与手机号，登录入口并列 | 改造平滑、兼容强 | 登录页仍有认知分叉 | 可行但不是最佳体验 |
| C | 保留用户名（内部/备用），主入口手机号优先 | 兼顾体验、稳定性、审计，能渐进上线 | 需要处理兼容协议与迁移细节 | **推荐** |

---

## 5. 推荐策略（手机号优先 + 用户名保留）

### 5.1 身份模型

- 不变主身份：`user.id`（JWT `sub` 继续使用 `id`）
- 稳定账号键：`username`（建议不可变或仅管理员可改）
- 首选登录键：`phone`
- 备用登录键：`username`（用于管理员、系统账号、异常场景）

### 5.2 为什么必须保留用户名

1. 手机号天然是联系方式，不是永久身份。
2. 审计日志和运维排障需要“稳定且可读”的账号标识。
3. 系统账号、集成账号不一定具备可接收短信的手机号。
4. 当前代码已广泛使用用户名作为显示与权限上下文，直接移除成本高且风险大。

---

## 6. 可执行改造设计

### 6.1 后端 API 设计（兼容优先）

### 6.1.1 登录请求模型改造

当前：

```json
{
  "username": "admin",
  "password": "***"
}
```

建议过渡期支持：

```json
{
  "identifier": "13800138000",
  "password": "***",
  "login_type": "password"
}
```

兼容规则：

1. 若有 `identifier`，优先使用 `identifier`。
2. 若无 `identifier` 且有 `username`，回退使用 `username`。
3. `identifier` 识别为手机号时，先按 `phone` 查；否则按 `username` 查。
4. 错误文案统一为“账号或密码错误”，避免账号枚举。

### 6.1.2 CRUD / Service 变更点

建议新增：

- `UserCRUD.get_by_phone_async(...)`
- `UserCRUD.find_active_by_identifier_async(...)`
- `AuthenticationService.authenticate_user(identifier, password)`

并将 `find_active_by_login_async` 的“用户名/邮箱”语义升级为“手机号/用户名/邮箱（可配置）”。

### 6.1.3 响应模型

`UserResponse` 保留 `username` 与 `phone`，避免前端管理页和审计页回归。

---

### 6.2 数据库与迁移策略

### 6.2.1 最小必要变更

建议新增字段：

- `phone_verified_at TIMESTAMP NULL`（手机号是否已验证）

可选新增字段：

- `phone_updated_at TIMESTAMP NULL`（辅助风控）

### 6.2.2 唯一约束策略

当前是 `phone UNIQUE NOT NULL`，短期可保持不变以降低风险。

若未来要支持“无手机号系统账号”，再进行第二阶段变更：

- `phone` 改为可空
- 使用 PostgreSQL 部分唯一索引：`WHERE phone IS NOT NULL`

示例 SQL（第二阶段用）：

```sql
-- 仅示意：需要放入 Alembic migration
ALTER TABLE users ALTER COLUMN phone DROP NOT NULL;
DROP INDEX IF EXISTS ix_users_phone;
CREATE UNIQUE INDEX uq_users_phone_not_null ON users(phone) WHERE phone IS NOT NULL;
```

### 6.2.3 数据清洗检查 SQL

上线前先检查手机号重复/非法：

```sql
-- 重复手机号
SELECT phone, COUNT(*)
FROM users
GROUP BY phone
HAVING COUNT(*) > 1;

-- 非法手机号（中国大陆11位）
SELECT id, username, phone
FROM users
WHERE phone !~ '^1[3-9][0-9]{9}$';
```

---

### 6.3 前端改造建议

### 6.3.1 类型与调用

建议逐步把 `LoginCredentials` 从：

```ts
{ username: string; password: string }
```

演进为：

```ts
{ identifier: string; password: string; loginType?: 'password' }
```

过渡期保留兼容：

```ts
{ identifier?: string; username?: string; password: string }
```

### 6.3.2 登录页交互

- 主文案改为“手机号登录”。
- 提供“使用账号登录”切换入口（不放主视觉路径）。
- 校验规则区分：
  - 手机号模式：严格手机号正则
  - 账号模式：长度/字符集校验

备注：当前 `LoginPage` 校验仍以“用户名长度 2-50”思路运行，应与“手机号优先”语义对齐。

---

### 6.4 安全与风控要求

手机号优先后，必须同步补齐：

1. 登录失败限流（账号/IP/设备维度）。
2. 短信验证码发送频控与日上限（若启用 OTP）。
3. 手机号变更二次验证（旧手机验证码或管理员审批）。
4. 审计日志新增登录类型：`phone_password` / `username_password` / `phone_otp`。
5. 统一错误返回，避免“手机号是否存在”泄露。

---

## 7. 分阶段上线计划

### 阶段 1（低风险，推荐先做）

- 后端支持 `identifier`，识别手机号登录。
- 保留 `username` 字段和旧请求兼容。
- 前端仅调整登录主入口文案与参数名。

验收标准：

1. 手机号 + 密码可登录。
2. 原用户名 + 密码仍可登录。
3. `/auth/me`、RBAC、会话刷新无回归。

### 阶段 2（增强体验）

- 引入短信验证码登录（可与密码并行）。
- 新增手机号验证状态与风控策略。

### 阶段 3（策略收敛）

- 普通用户默认隐藏用户名登录入口。
- 管理员与系统账号保留备用入口。

---

## 8. 影响面清单（重点回归）

### 8.1 后端

- `backend/src/schemas/auth.py`
- `backend/src/api/v1/auth/auth_modules/authentication.py`
- `backend/src/services/core/authentication_service.py`
- `backend/src/crud/auth.py`
- `backend/src/services/core/user_management_service.py`

### 8.2 前端

- `frontend/src/types/auth.ts`
- `frontend/src/services/authService.ts`
- `frontend/src/contexts/AuthContext.tsx`
- `frontend/src/pages/LoginPage.tsx`
- `frontend/src/pages/__tests__/LoginPage.test.tsx`
- `frontend/src/services/__tests__/authService.test.ts`

---

## 9. 回滚策略

若上线后出现登录异常：

1. 前端开关回退到“账号登录”入口。
2. 后端继续接受 `username` 字段，避免旧客户端中断。
3. 保留用户名登录链路至少一个发布周期后再考虑收口。

---

## 10. 最终建议

1. **保留用户名**：作为系统稳定账号标识与审计展示键。
2. **手机号优先登录**：提升日常使用便利性。
3. **兼容迁移而非一次切断**：先兼容、后引导、再收敛。

该策略能在不牺牲 RBAC 与审计稳定性的前提下，提升登录体验并控制改造风险。
