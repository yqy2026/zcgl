# API 总览

## 📋 Purpose
本文档概述土地物业管理系统的 API 架构、端点列表和使用规范。

## 🎯 Scope
- API 架构设计
- 33个 API 端点分类说明
- 认证和授权机制
- 请求/响应格式规范

## ✅ Status
**当前状态**: Active (2026-01-02 创建)
**API 版本**: v1.0.0
**基础路径**: `/api/v1`

---

## 🏗️ API 架构

### 架构设计

```
┌─────────────────────────────────────────────────────────┐
│                    Frontend (React)                      │
│                    Port: 5173 (dev)                      │
└───────────────────────────┬─────────────────────────────┘
                            │ HTTP/HTTPS
                            ▼
┌─────────────────────────────────────────────────────────┐
│                    Nginx (反向代理)                       │
│                    Port: 80/443                          │
└───────────────────────────┬─────────────────────────────┘
                            │ /api/v1/*
                            ▼
┌─────────────────────────────────────────────────────────┐
│                  FastAPI Backend                         │
│                    Port: 8002                            │
│  ┌─────────────┬─────────────┬─────────────┐           │
│  │  认证模块   │  资产模块   │  系统模块   │           │
│  │  auth.py    │  assets.py  │  admin.py   │           │
│  └─────────────┴─────────────┴─────────────┘           │
└───────────────────────────┬─────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────┐
│              Database (SQLite/PostgreSQL)                │
└─────────────────────────────────────────────────────────┘
```

### 版本化策略

所有 API 端点使用统一的版本化前缀：
- **当前版本**: `/api/v1/*`
- **路由注册**: 通过 `core/router_registry.py` 统一管理

---

## 📡 API 端点列表 (33个)

### 🔐 认证模块

| 端点文件 | 前缀 | 描述 |
|----------|------|------|
| [auth.py](../../backend/src/api/v1/auth.py) | `/auth` | 用户认证（登录、注册、令牌刷新） |
| [roles.py](../../backend/src/api/v1/roles.py) | `/roles` | 角色管理（RBAC） |

**详细文档**: [认证 API](auth-api.md)

---

### 🏢 资产管理模块

| 端点文件 | 前缀 | 描述 |
|----------|------|------|
| [assets.py](../../backend/src/api/v1/assets.py) | `/assets` | 资产 CRUD 操作 |
| [asset_attachments.py](../../backend/src/api/v1/asset_attachments.py) | `/assets/attachments` | 资产附件管理 |
| [asset_batch.py](../../backend/src/api/v1/asset_batch.py) | `/assets/batch` | 批量资产操作 |
| [asset_import.py](../../backend/src/api/v1/asset_import.py) | `/assets/import` | 资产导入 |
| [asset_statistics.py](../../backend/src/api/v1/asset_statistics.py) | `/assets/statistics` | 资产统计 |
| [ownership.py](../../backend/src/api/v1/ownership.py) | `/ownerships` | 权属关系管理 |
| [occupancy.py](../../backend/src/api/v1/occupancy.py) | `/occupancy` | 占用情况 |
| [history.py](../../backend/src/api/v1/history.py) | `/history` | 变更历史 |
| [project.py](../../backend/src/api/v1/project.py) | `/projects` | 项目管理 |

---

### 📋 合同模块

| 端点文件 | 前缀 | 描述 |
|----------|------|------|
| [rent_contract.py](../../backend/src/api/v1/rent_contract.py) | `/rent-contracts` | 租赁合同管理 |

---

### 📊 分析统计模块

| 端点文件 | 前缀 | 描述 |
|----------|------|------|
| [analytics.py](../../backend/src/api/v1/analytics.py) | `/analytics` | 数据分析 |
| [statistics.py](../../backend/src/api/v1/statistics.py) | `/statistics` | 统计报表 |
| [monitoring.py](../../backend/src/api/v1/monitoring.py) | `/monitoring` | 运行监控 |

---

### 📄 文档处理模块

| 端点文件 | 前缀 | 描述 |
|----------|------|------|
| [pdf_import_unified.py](../../backend/src/api/v1/pdf_import_unified.py) | `/pdf-import` | PDF 统一导入 |
| [pdf_import_routes.py](../../backend/src/api/v1/pdf_import_routes.py) | `/pdf` | PDF 路由入口 |
| [excel.py](../../backend/src/api/v1/excel.py) | `/excel` | Excel 导入导出 |

---

### ⚙️ 系统管理模块

| 端点文件 | 前缀 | 描述 |
|----------|------|------|
| [admin.py](../../backend/src/api/v1/admin.py) | `/admin` | 管理员操作 |
| [system.py](../../backend/src/api/v1/system.py) | `/system` | 系统信息 |
| [system_settings.py](../../backend/src/api/v1/system_settings.py) | `/system/settings` | 系统设置 |
| [system_monitoring.py](../../backend/src/api/v1/system_monitoring.py) | `/system/monitoring` | 系统监控 |
| [system_dictionaries.py](../../backend/src/api/v1/system_dictionaries.py) | `/system/dictionaries` | 系统字典 |
| [organization.py](../../backend/src/api/v1/organization.py) | `/organizations` | 组织架构 |
| [backup.py](../../backend/src/api/v1/backup.py) | `/backup` | 数据备份 |
| [operation_logs.py](../../backend/src/api/v1/operation_logs.py) | `/operation-logs` | 操作日志 |
| [tasks.py](../../backend/src/api/v1/tasks.py) | `/tasks` | 任务管理 |

---

### 📚 数据字典模块

| 端点文件 | 前缀 | 描述 |
|----------|------|------|
| [dictionaries.py](../../backend/src/api/v1/dictionaries.py) | `/dictionaries` | 数据字典 |
| [enum_field.py](../../backend/src/api/v1/enum_field.py) | `/enum-fields` | 枚举字段 |
| [custom_fields.py](../../backend/src/api/v1/custom_fields.py) | `/custom-fields` | 自定义字段 |

---

### 🔧 辅助功能模块

| 端点文件 | 前缀 | 描述 |
|----------|------|------|
| [defect_tracking.py](../../backend/src/api/v1/defect_tracking.py) | `/defects` | 缺陷跟踪 |
| [error_recovery.py](../../backend/src/api/v1/error_recovery.py) | `/error-recovery` | 错误恢复 |

---

## 🔑 认证机制

### JWT Token 认证

所有受保护的端点需要在请求头中携带 JWT Token：

```http
Authorization: Bearer <access_token>
```

### Token 类型

| 类型 | 有效期 | 用途 |
|------|--------|------|
| Access Token | 15分钟 | API 请求认证 |
| Refresh Token | 7天 | 刷新 Access Token |

### 权限控制

系统使用 RBAC（基于角色的访问控制）：
- 资源级别权限：`resource.action` 格式
- 示例：`assets.create`、`users.delete`

---

## 📝 请求/响应格式

### 成功响应

```json
{
  "success": true,
  "data": { ... },
  "message": "操作成功",
  "code": "SUCCESS"
}
```

### 错误响应

```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "错误描述"
  }
}
```

### 分页响应

```json
{
  "success": true,
  "data": {
    "items": [ ... ],
    "total": 100,
    "page": 1,
    "size": 20,
    "pages": 5
  }
}
```

---

## 🧪 API 测试

### 使用 curl

```bash
# 登录获取 Token
curl -X POST "http://localhost:8002/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "Admin123!@#"}'

# 使用 Token 访问资产列表
curl -X GET "http://localhost:8002/api/v1/assets" \
  -H "Authorization: Bearer <token>"
```

### API 文档

FastAPI 自动生成交互式 API 文档：
- **Swagger UI**: http://localhost:8002/docs
- **ReDoc**: http://localhost:8002/redoc

---

## 🔗 相关链接

### API 详细文档
- [认证 API](auth-api.md) - 登录、注册、权限管理

### 开发指南
- [后端开发指南](../guides/backend.md)
- [前端开发指南](../guides/frontend.md)

### 代码位置
- [API 路由目录](../../backend/src/api/v1/)
- [路由注册](../../backend/src/core/router_registry.py)

---

## 📋 Changelog

### 2026-01-02 v1.0.0 - 初始版本
- ✨ 新增：API 架构概述
- 📡 新增：33个端点分类说明
- 🔑 新增：认证机制说明
- 📝 新增：请求/响应格式规范

## 🔍 Evidence Sources
- **API 端点**: `backend/src/api/v1/` 目录
- **路由配置**: `backend/src/api/v1/__init__.py`
- **认证中间件**: `backend/src/middleware/auth.py`
