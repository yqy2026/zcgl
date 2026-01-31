# AGENTS.md
本文件为 Codex（coding agent）提供项目上下文与执行约束，确保修改一致、可验证。
更多细节参见 `docs/` 目录（此处只给最关键、可执行的信息）。

**Last Updated**: 2026-01-31

---

## 项目概述

**土地物业资产管理系统**（Land Property Asset Management System）

| 层 | 技术栈 |
|---|---|
| 前端 | React 19.2 + TypeScript 5.9 + Vite 6 + Ant Design 6 + pnpm + Vitest |
| 后端 | FastAPI 0.104+ + Uvicorn 0.38+ + Python 3.12 + SQLAlchemy 2.0 + Pydantic v2 + Alembic |
| 数据库 | PostgreSQL 16+（开发/测试/生产统一；SQLite 已移除） |
| 缓存 | Redis 7 |

---

## 快速命令

```bash
# 一键（Makefile）
make dev              # 前端+后端
make dev-frontend     # 前端 :5173
make dev-backend      # 后端 :8002
make lint             # 前后端 lint
make test             # 前后端测试
make secrets          # 生成 SECRET_KEY / DATA_ENCRYPTION_KEY
make migrate          # alembic upgrade head

# 手动（常用）
cd frontend && pnpm dev
cd backend && python run_dev.py

# 测试
cd frontend && pnpm test
cd backend && pytest -m unit     # 可选: integration, api, e2e, slow...

# 代码质量
cd frontend && pnpm lint && pnpm type-check
cd backend && ruff check . && ruff format . && mypy src

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
- CRUD 为纯数据访问层；不要绕过 CRUD 直接写库（包含加密/审计/缓存逻辑）。
- 新增 API 需用 `route_registry.register_router()` 注册，并按 `/api/v1/*` 版本化。
- 前端 API 客户端使用 `@/api/client` / `@/api/config`；服务层使用 `@/services/*`；表单组件使用 `@/components/Forms`。

**目录速查**:
- API: `backend/src/api/v1/`
- Service: `backend/src/services/`
- CRUD: `backend/src/crud/`
- Models: `backend/src/models/`
- Schemas: `backend/src/schemas/`
- 前端 API: `frontend/src/api/`
- 前端服务: `frontend/src/services/`
- 前端组件: `frontend/src/components/`
- 页面路由: `frontend/src/pages/`

---

## 后端开发要点（高频约束）

1) **Pydantic v2**: 使用 `model_validate()` / `model_dump()`；响应模型启用 `from_attributes`（建议 `model_config = ConfigDict(from_attributes=True)`）。  
2) **SQLAlchemy 2.0**: 优先 ORM + QueryBuilder；列表接口注意 N+1，集合关系优先 `selectinload`；避免在 schema validator 中触发懒加载。  
3) **PII 加密**: Asset/Organization/RentContract/Contact/PropertyCertificate 等 CRUD 使用 `SensitiveDataHandler`；不要绕过 CRUD；`DATA_ENCRYPTION_KEY` 缺失会降级为明文。  
4) **计算字段**: `unrented_area` / `occupancy_rate` 等由 `AssetCalculator` 计算，API/Service 层处理；不要从 API 写入；`version` 由 ORM 维护。  
5) **异常与审计**: 重要写操作优先 `*_with_history`，保持历史记录与审计字段一致。  

---

## 前端开发要点（高频约束）

- React Query 用于服务端数据；Zustand 管理全局 UI；表单用 React Hook Form。
- TypeScript **严格布尔表达式**：避免 `if (value)`；使用 `??`、`!= null`、`?.`、`.trim()` 等显式判断。
- Ant Design 组件优先，保持既有 UI 语言一致。

---

## 环境与配置

- **后端必须**配置 `backend/.env`：`DATABASE_URL`（PostgreSQL）、`SECRET_KEY`（32+）、建议设置 `DATA_ENCRYPTION_KEY`。
- `ENVIRONMENT` / `DEPENDENCY_POLICY` 见 `backend/src/core/environment.py`；完整配置见 `backend/src/core/config.py`。
- PDF/LLM 文档提取需配置对应 Provider API Key（见 `backend/.env.example`）。
- 迁移失败时：先 `alembic stamp head` 再 `alembic upgrade head`。
- 前端 `.env` 参考 `frontend/.env.example`（`VITE_API_BASE_URL` 默认指向 `/api/v1`）。

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
- `docs/guides/frontend.md` / `docs/guides/backend.md`
- `frontend/CLAUDE.md` / `backend/CLAUDE.md`
