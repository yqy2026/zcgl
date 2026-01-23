# 前端-后端-数据库 一致性排查报告

**生成日期**: 2026-01-23
**项目**: 土地物业资产管理系统
**分析范围**: 全栈一致性检查（数据库模型 → 后端Schema → API端点 → 前端类型 → 前端API调用）

---

## 1. 总体概览

| 层级 | 文件数 | 主要技术 | 状态 |
|------|--------|----------|------|
| **数据库** | 17个模型文件 | SQLAlchemy 2.0 + Mapped类型 | ✅ 结构清晰 |
| **后端Schema** | 多个Pydantic模块 | Pydantic v2 | ⚠️ 存在差异 |
| **后端API** | 65+端点文件 | FastAPI | ⚠️ 路径不一致 |
| **前端类型** | 127个.ts文件 | TypeScript | ⚠️ 存在差异 |
| **前端API** | 多个服务文件 | Axios | ⚠️ 端点不匹配 |

---

## 2. 数据库模型清单

### 2.1 核心资产模型 (`backend/src/models/asset.py`)

#### 表: `assets` (Model: Asset)
| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | String(UUID) | PK | 主键 |
| `property_name` | String | Required | 物业名称 |
| `address` | String | Required | 地址 |
| `ownership_entity` | String | - | 权属实体 |
| `ownership_category` | String | - | 权属类别 |
| `project_name` | String | - | 项目名称 |
| `ownership_status` | String | - | 权属状态 |
| `property_nature` | String | - | 物业性质 |
| `usage_status` | String | - | 使用状态 |
| `is_litigated` | Boolean | - | 是否涉诉 |
| `land_area` | Decimal(12,2) | - | 土地面积 |
| `actual_property_area` | Decimal(12,2) | - | 实际物业面积 |
| `rentable_area` | Decimal(12,2) | - | 可租面积 |
| `rented_area` | Decimal(12,2) | - | 已租面积 |
| `non_commercial_area` | Decimal(12,2) | - | 非商业面积 |
| `tenant_name` | String | - | 租户名称 |
| `tenant_type` | String | - | 租户类型 |
| `lease_contract_number` | String | - | 租约合同号 |
| `contract_start_date` | Date | - | 合同开始日期 |
| `contract_end_date` | Date | - | 合同结束日期 |
| `monthly_rent` | Decimal | - | 月租金 |
| `deposit` | Decimal | - | 押金 |
| `project_id` | String | FK→projects | 项目ID |
| `ownership_id` | String | FK→ownerships | 权属ID |

**关系**: `project`, `ownership`, `history_records`, `documents`, `rent_contracts` (M2M), `certificates` (M2M)

#### 表: `projects` (Model: Project)
| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | String(UUID) | PK | 主键 |
| `name` | String | Required | 项目名称 |
| `code` | String | Unique | 项目代码 |
| `short_name` | String | - | 简称 |
| `project_type` | String | - | 项目类型 |
| `project_status` | String | - | 项目状态 |
| `total_investment` | Decimal | - | 总投资 |

**关系**: `assets`, `ownership_relations`

#### 表: `ownerships` (Model: Ownership)
| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | String(UUID) | PK | 主键 |
| `name` | String | Required | 权属名称 |
| `code` | String | - | 权属代码 |
| `short_name` | String | - | 简称 |
| `management_entity` | String | - | 管理实体 |

**关系**: `assets`, `owned_rent_contracts`, `ownership_relations`

### 2.2 认证与用户模型 (`backend/src/models/auth.py`)

#### 表: `users` (Model: User)
| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | String(UUID) | PK | 主键 |
| `username` | String | Unique, Indexed | 用户名 |
| `email` | String | Unique, Indexed | 邮箱 |
| `full_name` | String | - | 全名 |
| `password_hash` | String | - | 密码哈希 |
| `role` | Enum | admin/user | 角色 |
| `is_active` | Boolean | Default: True | 是否激活 |
| `is_locked` | Boolean | Default: False | 是否锁定 |
| `last_login_at` | DateTime | - | 最后登录时间 |
| `failed_login_attempts` | Integer | - | 登录失败次数 |
| `locked_until` | DateTime | - | 锁定截止时间 |
| `employee_id` | String | FK→employees | 员工ID |
| `default_organization_id` | String | FK→organizations | 默认组织ID |

**关系**: `user_sessions`, `audit_logs`, `role_assignments`, `notifications`

#### 表: `user_sessions` (Model: UserSession)
| 字段 | 类型 | 说明 |
|------|------|------|
| `session_id` | String | 会话ID |
| `refresh_token` | String | 刷新令牌 |
| `device_info` | String | 设备信息 |
| `ip_address` | String | IP地址 |
| `expires_at` | DateTime | 过期时间 |

### 2.3 组织与人员模型 (`backend/src/models/organization.py`)

#### 表: `organizations` (Model: Organization)
| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | String(UUID) | PK | 主键 |
| `name` | String | Required | 组织名称 |
| `code` | String | - | 组织代码 |
| `level` | Integer | - | 层级 |
| `type` | String | - | 类型 |
| `parent_id` | String | FK→organizations | 父组织ID |
| `path` | String | - | 物化路径 |
| `is_deleted` | Boolean | Default: False | 软删除标记 |

**关系**: `children` (自引用), `positions`, `employees`

#### 表: `employees` (Model: Employee)
| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | String(UUID) | PK | 主键 |
| `employee_no` | String | Unique | 员工编号 |
| `name` | String | Required | 姓名 |
| `gender` | String | - | 性别 |
| `hire_date` | Date | - | 入职日期 |
| `employment_type` | String | - | 雇佣类型 |
| `organization_id` | String | FK→organizations | 组织ID |
| `position_id` | String | FK→positions | 职位ID |
| `direct_supervisor_id` | String | FK→employees | 直属上级ID |
| `is_deleted` | Boolean | Default: False | 软删除标记 |

### 2.4 RBAC权限模型 (`backend/src/models/rbac.py`)

#### 表: `roles` (Model: Role)
| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | String(UUID) | PK | 主键 |
| `name` | String | Unique | 角色名称 |
| `display_name` | String | - | 显示名称 |
| `level` | Integer | - | 角色级别 |
| `is_system_role` | Boolean | - | 是否系统角色 |
| `scope` | String | - | 作用域(global/organization/department) |

**关系**: `permissions` (M2M via role_permissions), `user_assignments`

#### 表: `permissions` (Model: Permission)
| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | String(UUID) | 主键 |
| `name` | String | 权限名称 |
| `resource` | String | 资源 |
| `action` | String | 动作(read/write/delete等) |
| `requires_approval` | Boolean | 是否需要审批 |
| `conditions` | JSON | 条件 |

#### 关联表
- `role_permissions`: 角色-权限 M2M关联
- `user_role_assignments`: 用户-角色关联，含`expires_at`

---

## 3. 发现的一致性问题

### 3.1 API 端点路径不一致 (严重 - P0)

| 功能 | 前端调用路径 | 后端定义路径 | 状态 |
|------|-------------|-------------|------|
| 租赁合同 | `/rent-contracts` | `/rental-contracts` | ❌ 不匹配 |
| PDF上传 | `/pdf/upload` | `/pdf-import/upload` | ❌ 不匹配 |
| PDF增强上传 | `/pdf/enhanced/upload` | `/pdf-import/process` | ❌ 不匹配 |
| 项目下拉 | `/projects/dropdown-options` | `/projects/options/dropdown` | ❌ 不匹配 |
| 用户会话 | `/auth/sessions` | 未定义 | ❌ 后端缺失 |
| 资产批量ID | `/assets/by-ids` | 未定义 | ❌ 后端缺失 |
| 资产验证 | `/assets/validate` | 未定义 | ❌ 后端缺失 |

**修复建议**:
```python
# 方案1: 后端添加别名路由
@router.get("/rent-contracts")  # 别名
@router.get("/rental-contracts")  # 原路径
async def get_contracts(): ...

# 方案2: 前端统一修改为后端路径
// rentContractService.ts
const API_PATH = '/rental-contracts';  // 修改为后端实际路径
```

### 3.2 数据类型不一致 (中等 - P1)

| 字段 | 数据库类型 | 后端Schema | 前端类型 | 问题 |
|------|-----------|-----------|---------|------|
| 金额字段 | `Decimal(12,2)` | `Decimal` | `number` | 精度丢失风险 |
| `total_investment` | `Decimal` | `float` | `number` | 应统一用Decimal |
| 日期字段 | `datetime`/`date` | `datetime` | `string` | 需要转换处理 |
| ID字段 | `String(UUID)` | `str` | `string` | ✅ 一致 |

**修复建议**:
```typescript
// 前端: 使用string传输金额，本地使用Decimal库处理
interface Asset {
  monthlyRent: string;  // "12345.67" 而非 number
  deposit: string;
}

// 使用时转换
import Decimal from 'decimal.js';
const rent = new Decimal(asset.monthlyRent);
```

### 3.3 响应结构命名风格不一致 (中等 - P1)

| 层级 | 响应包装结构 |
|------|--------------|
| 后端 | `{ is_success, message, data, timestamp, request_id }` |
| 前端期望 | `{ isSuccess, data, message, code }` |

**修复建议**:
```python
# 后端: 配置Pydantic使用camelCase
class Config:
    alias_generator = to_camel
    populate_by_name = True
```

或

```typescript
// 前端: 添加响应转换器
const transformResponse = (data: any) => ({
  isSuccess: data.is_success,
  message: data.message,
  data: data.data,
  timestamp: data.timestamp,
  requestId: data.request_id,
});
```

### 3.4 分页参数不一致 (低 - P2)

| 服务 | 前端参数 | 后端参数 |
|------|----------|----------|
| 资产列表 | `page`, `pageSize` | `page`, `limit` |
| 项目列表 | `page`, `size` | `page`, `limit` |

**修复建议**: 统一使用 `page` + `pageSize` (前端风格) 或 `page` + `limit` (后端风格)

### 3.5 枚举/状态值定义差异 (低 - P2)

| 实体 | 后端定义 | 前端定义 | 建议 |
|------|----------|----------|------|
| OwnershipStatus | `str` (宽松) | 严格枚举 | 后端添加枚举验证 |
| UsageStatus | `String` | 16个枚举成员 | 后端添加枚举 |
| PropertyNature | `String` | 17个枚举成员 | 后端添加枚举 |
| PaymentStatus | 后端枚举 | union类型 | ✅ 一致 |

---

## 4. 一致性良好的部分

| 项目 | 状态 | 说明 |
|------|------|------|
| ID策略 | ✅ | 全栈统一使用 String UUID |
| 审计字段 | ✅ | `created_at`, `updated_at`, `created_by`, `updated_by` 一致 |
| 多资产合同 | ✅ | V2架构 `asset_ids: list[str]` 三层一致 |
| 认证机制 | ✅ | JWT + HttpOnly Cookie 前后端配合正确 |
| RBAC权限 | ✅ | `require_permission(resource, action)` 设计一致 |
| 软删除策略 | ✅ | 组织模块统一使用 `is_deleted` 标记 |

---

## 5. 修复优先级与行动计划

### 5.1 P0 - 立即修复 (会导致功能失败)

```bash
# 任务清单
□ 1. 统一租赁合同端点路径
  - 文件: backend/src/api/v1/rent_contract.py
  - 文件: frontend/src/api/services/rentContractService.ts

□ 2. 修复PDF导入端点路径
  - 文件: frontend/src/api/services/pdfService.ts
  - 改为: /pdf-import/upload, /pdf-import/process

□ 3. 实现缺失的后端端点
  - /assets/by-ids (批量获取资产)
  - /assets/validate (资产数据验证)
  - /auth/sessions (用户会话管理)
```

### 5.2 P1 - 尽快修复 (可能导致数据问题)

```bash
□ 4. 统一响应字段命名风格
  - 选择: snake_case (后端风格) 或 camelCase (前端风格)
  - 实现: 后端中间件 或 前端适配器

□ 5. 统一分页参数名称
  - 推荐: page + pageSize

□ 6. 金额字段精度处理
  - 前端使用 string 传输
  - 引入 decimal.js 处理计算
```

### 5.3 P2 - 后续优化 (不影响功能)

```bash
□ 7. Project模型的float改为Decimal
□ 8. 后端Schema添加枚举验证
□ 9. 完善API文档与类型导出
```

---

## 6. 验证命令

修复完成后，运行以下命令验证：

```bash
# 前端类型检查
cd frontend && pnpm type-check

# 后端类型检查
cd backend && mypy src

# API测试
cd backend && pytest -m api

# 端到端测试
cd backend && pytest -m e2e
```

---

## 7. 附录：跨层数据流示意

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           数据流向示意                                    │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  [前端 TypeScript 类型]                                                  │
│         │                                                               │
│         ▼ axios request                                                 │
│  [前端 API 服务层]  ──────────────────────────────┐                      │
│         │                                        │                      │
│         ▼ HTTP Request                           │ 路径不一致问题         │
│  ┌──────────────────────────────────────────┐    │                      │
│  │     FastAPI 路由层 (/api/v1/*)           │◄───┘                      │
│  └──────────────────────────────────────────┘                           │
│         │                                                               │
│         ▼ Pydantic Schema 验证                                          │
│  [后端 Pydantic Schema]  ────────────────────────┐                      │
│         │                                        │ 类型不一致问题         │
│         ▼                                        │                      │
│  [后端 Service 层]                               │                      │
│         │                                        │                      │
│         ▼ SQLAlchemy ORM                         │                      │
│  ┌──────────────────────────────────────────┐    │                      │
│  │     SQLAlchemy Models                    │◄───┘                      │
│  └──────────────────────────────────────────┘                           │
│         │                                                               │
│         ▼ SQL                                                           │
│  [数据库 SQLite/PostgreSQL]                                              │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

**报告生成者**: Claude Code
**下次审查建议**: 2026-02-23


---

## 8. 本次执行修复记录（2026-01-23）

> 目标：优先消除 **P0 路径不一致** 导致的功能不可用，并对 **分页参数/分页字段命名** 做兼容。

### 8.1 已实施修复

#### A. 租赁合同端点 `/rent-contracts` vs `/rental-contracts`
- **后端新增兼容别名路由**：同时支持
  - `/api/v1/rental-contracts/*`（现行）
  - `/api/v1/rent-contracts/*`（兼容历史前端）
- 文件：`backend/src/api/v1/__init__.py`

#### B. PDF 导入端点
- **修复 `POST /api/v1/pdf-import/upload` 依赖可选 session service 导致的 503/不可用问题**：改为直接创建 `PDFImportSession` 记录。
- **新增兼容别名**：`POST /api/v1/pdf-import/process` → 与 `/upload` 行为一致（用于兼容前端/旧文档）。
- 文件：`backend/src/api/v1/pdf_upload.py`

#### C. 项目下拉端点
- **新增兼容端点**：`GET /api/v1/projects/dropdown-options`（返回 `{id,name,code,short_name,is_active}` 数组）
- **保留原端点**：`GET /api/v1/projects/options/dropdown`
- 文件：`backend/src/api/v1/project.py`

#### D. “缺失后端端点”校正
- 报告中列为缺失的端点实际已存在：
  - `POST /api/v1/assets/by-ids`（位于 `backend/src/api/v1/asset_batch.py`）
  - `POST /api/v1/assets/validate`（位于 `backend/src/api/v1/asset_batch.py`）
  - `GET /api/v1/auth/sessions`（位于 `backend/src/api/v1/auth_modules/sessions.py`）
- 同时修复前端调用不匹配：`/assets/validate` 的请求体应为 `{ data: ... }`
  - 文件：`frontend/src/services/asset/assetCoreService.ts`

#### E. 分页参数/字段命名兼容（pageSize vs limit/page_size）
- **后端接口兼容 query 参数**：支持 `pageSize`（alias）与原 `limit`
- **后端响应字段序列化兼容**：将 `page_size` 序列化为 `pageSize`
- 覆盖模块：资产列表、租赁合同列表、租金台账列表、项目列表
- 文件：
  - `backend/src/api/v1/assets.py`
  - `backend/src/api/v1/rent_contract.py`
  - `backend/src/api/v1/project.py`
  - `backend/src/schemas/asset.py`
  - `backend/src/schemas/rent_contract.py`
  - `backend/src/schemas/project.py`

#### F. 前端健康检查端点修正
- 修正硬编码：
  - `/rent-contracts/contracts` → `/rental-contracts/contracts`
  - `/auth/users/me` → `/auth/me`
- 文件：`frontend/src/services/apiHealthCheck.ts`

### 8.2 验证结果

- ✅ 后端语法检查：
  - `python -m compileall backend/src`

- ⚠️ 前端类型检查：
  - `pnpm type-check` 仍存在项目内既有 TypeScript 类型错误（例如 `loading` vs `isLoading`、若干页面/组件类型字段不一致）。
  - 这些错误与本报告的 **端点路径一致性** 修复不完全同一问题域；建议另开任务按 `pnpm type-check` 报错清单逐项修复。

### 8.3 仍建议后续处理（未在本次修复范围内）

- 金额字段在前端使用 `number` 可能导致精度风险（建议改为 string + decimal.js，或后端统一返回 string）。
- 响应包装结构目前在后端仍存在 `success` 与 `is_success` 两套风格共存（建议统一一套并生成前端类型）。
- 枚举/状态值建议后端增加校验（或提供字典接口作为枚举来源）。
