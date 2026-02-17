# 土地物业资产管理系统 - 项目概览

## 项目目的
土地物业资产管理系统（Land Property Asset Management System）是一个用于管理土地和物业资产的综合管理平台，支持资产全生命周期管理、租赁合同管理、认证与权限管理等功能。

## 技术栈

### 后端
- **框架**: FastAPI 0.104+
- **运行时**: Uvicorn 0.38+, Python 3.12+
- **ORM**: SQLAlchemy 2.0+
- **数据验证**: Pydantic v2
- **数据库迁移**: Alembic
- **数据库**: PostgreSQL 18.2+
- **缓存**: Redis 8.6+
- **文档AI**: Qwen-VL / GLM-4V / Hunyuan Vision / DeepSeek-VL

### 前端
- **框架**: React 19.x + TypeScript 5.x
- **构建工具**: Vite 6.x
- **UI库**: Ant Design 6.x
- **包管理**: pnpm
- **状态管理**: Zustand (全局UI) + React Query (服务器数据) + React Hook Form (表单)

## 核心业务模块

### 1. 资产管理 (Asset)
- 资产全生命周期：列表/详情/创建/更新/删除/恢复/彻底删除
- 批量操作、导入、附件管理
- 软删除与关联约束保护
- 面积计算（出租率等）

### 2. 租赁合同管理 (Rent Contract)
- 合同创建/续签/终止
- 生命周期冲突检测
- 租金台账生成与批量更新
- 租赁统计

### 3. 权属管理 (Ownership)
- 权属方管理
- 权属与资产关联

### 4. 产权证管理 (Property Certificate)
- 产权证信息管理
- 与资产关联

### 5. 项目管理 (Project)
- 项目基本信息
- 项目与资产、组织关联

### 6. 组织管理 (Organization)
- 组织架构层级管理
- 组织历史变更追踪

### 7. 认证与权限 (Auth/RBAC)
- HttpOnly Cookie 认证
- RBAC 权限管理

### 8. 系统功能
- PDF 智能导入
- 综合分析与统计
- 通知、任务、联系人管理
- 催缴管理

## 架构模式
```
React UI → ApiClient → FastAPI (/api/v1/*) → Service → CRUD → SQLAlchemy
```

**关键规则**:
- 业务逻辑必须放在 `services/` 层
- CRUD 为纯数据访问层
- API 路径统一按 `/api/v1/*` 版本化
- PII 字段由 `SensitiveDataHandler` 处理加密
