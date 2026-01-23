# CLAUDE.md
每次回复我都叫我【yellowUp】
本文件为 Claude Code 提供项目上下文，遵循 2026 最佳实践。详细文档请参阅 `docs/` 目录。

**最后更新**: 2026-01-22

---

## 项目概述

**土地物业资产管理系统** - 全栈资产管理平台，支持RBAC权限管理、合同生命周期管理。

| 层 | 技术栈 |
|---|-------|
| **前端** | React 19 + TypeScript + Vite 6 + Ant Design 6 + pnpm |
| **后端** | FastAPI + Python 3.12 + SQLAlchemy 2.0 + Pydantic v2 |
| **数据库** | SQLite (dev) / PostgreSQL (prod) |
| **缓存** | Redis |

---

## 快速命令

```bash
# 开发启动
cd frontend && pnpm dev          # 前端 :5173
cd backend && python run_dev.py  # 后端 :8002

# 测试
cd frontend && pnpm test
cd backend && pytest -m unit     # 可选: integration, api, e2e

# 代码质量
cd frontend && pnpm lint && pnpm type-check
cd backend && ruff check . && mypy src

# 数据库迁移
cd backend && alembic upgrade head
```

---

## 核心架构

```
React UI → ApiClient → FastAPI (/api/v1/*) → Service → CRUD → SQLAlchemy
```

**关键规则**:
- 业务逻辑 **必须** 放在 `services/` 层，不要放在 `api/v1/` 端点
- 新增 API 使用 `route_registry.register_router()` 注册
- 前端导入使用 `@/api/client` 和 `@/components/Forms`

---

## 目录导航

> 使用渐进式披露：需要时再查看具体目录

| 需求 | 查看位置 |
|-----|---------|
| API 端点定义 | `backend/src/api/v1/` (65+个文件，含子模块) |
| 业务逻辑实现 | `backend/src/services/` (19个子目录) |
| 数据库模型 | `backend/src/models/` (17个文件) |
| 前端组件 | `frontend/src/components/` (247个.tsx组件) |
| 页面路由 | `frontend/src/pages/` (目录结构) |
| 类型定义 | `frontend/src/types/` (127个.ts文件) |

---

## ⚠️ 关键警告

> [!DANGER]
> **SECRET_KEY 必须配置**
> - 生产环境必须设置 32+ 字符的强随机密钥
> - 生成方法: `python -c "import secrets; print(secrets.token_urlsafe(32))"`
> - 不得使用示例密钥或弱密钥（如包含 "secret-key", "changeme" 等）
> - 开发环境首次启动时，系统会自动检测并提示配置

> [!WARNING]
> **Alembic 迁移失败**: 运行 `alembic stamp head` 后再 `alembic upgrade head`

> [!WARNING]
> **环境变量配置**: 复制 `backend/.env.example` 为 `backend/.env` 并配置所需变量

---

## 开发规范速查

### 新增 API 端点

```python
# backend/src/api/v1/my_feature.py
from src.core.router_registry import route_registry

router = APIRouter(prefix="/my-feature", tags=["My Feature"])

@router.get("/items")
async def get_items(): ...

route_registry.register_router(router, prefix="/api/v1", tags=["My Feature"], version="v1")
```

### Service 层模式

```python
# ✅ 正确 - 业务逻辑在 Service
class AssetService:
    def process(self, data): ...

# ❌ 错误 - 业务逻辑在 API 端点
@router.post("/process")
async def process(data):
    # 不要在这里放业务逻辑!
```

### 前端状态管理

| 状态类型 | 使用 |
|---------|------|
| 全局 UI | Zustand (`store/`) |
| 服务器数据 | React Query |
| 表单 | React Hook Form |

---

## 环境配置

```bash
# backend/.env
ENVIRONMENT=development          # production, testing, staging
DEPENDENCY_POLICY=strict         # graceful, optional
```

详见 `backend/src/core/environment.py`

---

## Git 工作流

- **分支**: main (生产) ← develop ← feature/* / hotfix/*
- **提交格式**: `type(scope): description` (如 `feat(auth): add JWT refresh`)

---

# Python
When working with Python, invoke the relevant /astral:<skill> for uv, ty, and ruff to ensure best practices are followed.