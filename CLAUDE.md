# CLAUDE.md
每次回复我都叫我【yellowUp】
本文件为 Claude Code 提供项目上下文与执行约束。详细文档请参阅 `docs/` 目录。

**最后更新**: 2026-02-07

---

## 项目概述

**土地物业资产管理系统**（Land Property Asset Management System）- 一个用于管理土地和物业资产的综合管理平台。

| 层 | 技术栈 |
|---|-------|
| **前端** | React 19.2 + TypeScript 5.9 + Vite 6 + Ant Design 6 + pnpm |
| **后端** | FastAPI 0.104+ + Uvicorn 0.38+ + Python 3.12 + SQLAlchemy 2.0 + Pydantic v2 + Alembic |
| **数据库** | PostgreSQL 16+（开发/测试/生产统一；SQLite 已移除） |
| **缓存** | Redis 7 |
| **文档AI** | Qwen-VL / GLM-4V / Hunyuan Vision / DeepSeek-VL |

---

## 快速命令

```bash
# 一键启动（前后端）
make dev

# 进程监控启动（异常退出会记录日志）
pwsh -File scripts/dev_watch.ps1

# 单独启动
make dev-backend      # 后端 :8002
make dev-frontend     # 前端 :5173

# 代码质量
make lint
make type-check

# 测试
make test
make test-backend
make test-frontend

# 迁移/构建
make migrate
make build-frontend
```

---

## 核心架构

```
React UI → ApiClient → FastAPI (/api/v1/*) → Service → CRUD → SQLAlchemy
```

**关键规则**:
- 业务逻辑 **必须** 放在 `services/` 层，不要放在 `api/v1/` 端点
- CRUD 为纯数据访问层；不要绕过 CRUD 直接操作数据库
- 新增 API 使用 `route_registry.register_router()` 注册
- API 路径统一按 `/api/v1/*` 版本化
- PII 字段统一由 `SensitiveDataHandler` 处理；`DATA_ENCRYPTION_KEY` 缺失会降级为明文存储

---

## 前端开发要点

- 严格布尔表达式：使用显式空值检查与 `??` 默认值
- 导入路径统一使用 `@/` 别名，避免深层相对路径
- 服务器数据使用 React Query 管理（不要用 `useState + useEffect`）

---

## 目录导航

> 使用渐进式披露：需要时再查看具体目录

| 需求 | 查看位置 |
|-----|---------|
| API 端点定义 | `backend/src/api/v1/` |
| 业务逻辑实现 | `backend/src/services/` |
| 数据库模型 | `backend/src/models/` |
| 前端组件 | `frontend/src/components/` |
| 页面路由 | `frontend/src/pages/` |
| 类型定义 | `frontend/src/types/` |

---

## ⚠️ 关键警告

> [!DANGER]
> **SECRET_KEY 必须配置**
> - 生产环境必须设置 32+ 字符的强随机密钥
> - 生成方法: `make secrets` 或 `python -c "import secrets; print(secrets.token_urlsafe(32))"`
> - 不得使用示例密钥或弱密钥（如包含 "secret-key", "changeme" 等）

> [!WARNING]
> **DATA_ENCRYPTION_KEY**: 运行 `cd backend && python -m src.core.encryption` 生成标准 Base64 密钥

> [!WARNING]
> **环境变量配置**: 复制 `backend/.env.example` 为 `backend/.env` 并配置所需变量

> [!WARNING]
> **Alembic 迁移失败**: 运行 `alembic stamp head` 后再 `alembic upgrade head`

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

## 测试策略

**测试标记**：`unit` / `integration` / `e2e` / `api` / `database` / `security` / `performance` / `slow`

**常用命令**：
```bash
cd backend
pytest -m unit
pytest -m "not slow"

cd frontend
pnpm test
```

---

## 环境配置

```bash
# backend/.env（示例）
DATABASE_URL=postgresql+psycopg://user:pass@localhost:5432/zcgl
TEST_DATABASE_URL=postgresql+psycopg://user:pass@localhost:5432/zcgl_test
ENVIRONMENT=development  # production, development, testing, staging
LLM_PROVIDER="hunyuan"   # qwen | glm | deepseek | hunyuan
```

详见 `backend/.env.example` 与 `backend/src/core/environment.py`

---

## Git 工作流

- **分支**: main (生产) ← develop ← feature/* / hotfix/*
- **提交格式**: `type(scope): description` (如 `feat(auth): add JWT refresh`)

### 冲突处理经验（2026-02）

- 禁止在大量冲突时直接依赖 `-X theirs/ours` 后推送，必须逐文件人工复核
- `modify/delete` 冲突先查历史（`git log -- <file>`），确认删除是否为架构收口，避免误恢复旧文件
- 模型与聚合导入文件是高风险区域：重点检查 `models/*.py`、`models/__init__.py`、`crud/*.py`
- 冲突解决后至少执行：
  - 无冲突标记检查：`rg -n "^(<<<<<<<|=======|>>>>>>>)"`
  - 关键导入烟测（models/crud）
  - `ruff check` 与受影响测试最小集
- 推送前给出“冲突清单 + 处理决策 + 未覆盖风险”，必要时先人工核准

---

## Python

- 代码质量: `ruff check .`, `ruff format .`, `mypy src`
- 测试: `pytest -m unit`

---

## 维护文档

每次修改后请更新 CHANGELOG.md
