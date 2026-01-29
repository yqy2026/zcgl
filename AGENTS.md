# AGENTS.md
本文件为 Codex（coding agent）提供项目上下文与执行约束，确保修改一致、可验证。
更多细节参见 `docs/` 目录（此处只给最关键、可执行的信息）。

**Last Updated**: 2026-01-29

---

## 项目概述

**土地物业资产管理系统**（Land Property Asset Management System）

| 层 | 技术栈 |
|---|---|
| 前端 | React 19 + TypeScript + Vite 6 + Ant Design 6 + pnpm |
| 后端 | FastAPI + Python 3.12 + SQLAlchemy 2.0 + Pydantic v2 |
| 数据库 | SQLite (dev) / PostgreSQL (prod) |
| 缓存 | Redis |

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

## 代码结构与职责

```
React UI → ApiClient → FastAPI (/api/v1/*) → Service → CRUD → SQLAlchemy
```

**必须遵循的规则**:
- 业务逻辑必须放在 `backend/src/services/`，不要放在 `backend/src/api/v1/`。
- 新增 API 需用 `route_registry.register_router()` 注册。
- 前端导入使用 `@/api/client` 与 `@/components/Forms`。

**目录速查**:
- API: `backend/src/api/v1/`
- Service: `backend/src/services/`
- CRUD: `backend/src/crud/`
- Models: `backend/src/models/`
- Schemas: `backend/src/schemas/`
- 前端组件: `frontend/src/components/`
- 页面路由: `frontend/src/pages/`

---

## 后端开发要点（高频约束）

1) **Pydantic v2**: schema 使用 `model_validate()` / `model_dump()`；响应模型开启 `from_attributes`。  
2) **SQLAlchemy 2.0**: 优先使用 ORM + QueryBuilder；列表接口注意 N+1，集合关系优先 `selectinload`。  
3) **PII 加密**: Asset 等实体的敏感字段通过 `AssetCRUD` 加解密；不要绕过 CRUD 层直接写库。  
4) **计算字段**: 例如 `unrented_area` / `occupancy_rate` 为计算属性，不应从 API 写入数据库。  
5) **性能**: 列表接口避免在 schema validator 中触发懒加载；必要时预加载关系或使用“轻量响应模型”。  
6) **异常与审计**: 重要写操作需保持历史记录与审计字段一致（参见 `*_with_history`）。

---

## 前端开发要点（高频约束）

- React Query 用于服务端数据；Zustand 管理全局 UI；表单用 React Hook Form。
- 新页面或大型组件先查 `frontend/src/pages/` 与 `frontend/src/components/` 现有模式。
- Ant Design 组件优先，保持既有 UI 语言一致。

---

## 环境与配置

- `backend/.env` 必须配置 `SECRET_KEY`（32+ 字符），并保持不提交到 git。
- 迁移失败时：先 `alembic stamp head` 再 `alembic upgrade head`。
- 环境变量与检测逻辑：`backend/src/core/environment.py`。

---

## 变更要求（Codex 执行准则）

- 变更尽量小、可回滚；不要触碰与任务无关的文件。
- 重要逻辑变更需同步更新文档（参见 `README.md` 文档贡献指南）。
- 如修改模型/字段/接口，优先补充或更新测试。
- 任何不确定结论用【待确认】标注，并给出验证路径。

---

## 常见新增流程

**新增 API 端点**
```python
from src.core.router_registry import route_registry

router = APIRouter(prefix="/my-feature", tags=["My Feature"])

@router.get("/items")
async def get_items(): ...

route_registry.register_router(router, prefix="/api/v1", tags=["My Feature"], version="v1")
```

**Service 层示例**
```python
class AssetService:
    def process(self, data): ...
```

---

## 参考文档

- `docs/`（系统架构、开发规范、接口说明、部署指南等）
- `CLAUDE.md` / `GEMINI.md`（快速上下文与命令）
