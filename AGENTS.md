# AGENTS.md

本文件为 AI Coding Agents 提供项目上下文与执行约束（Single Source of Truth）。
每次修改后请更新 `CHANGELOG.md`。
项目目前在从0到1阶段的开发中，不要做兼容保留操作，充分的暴露问题，要打牢系统基础。
1、写代码之前，先说清楚你打算怎么做，等我确认了再动手。
2、如果我给的需求不够明确，先问清楚再写代码，别自己猜。
3、每次写完代码之后，把你能想到的边界情况列出来，再建议几个测试用例覆盖它们。
4、如果一个任务需要改三个以上的文件，先停下来，把它拆成更小的任务再做。
5、遇到 bug 的时候，先写一个能复现这个 bug 的测试，然后修到测试通过为止。
6、每次我纠正你的时候，想想自己哪里做错了，拿出一个方案确保以后不再犯同样的错。

**Last Updated**: 2026-03-04

---

## 项目概述

**土地物业资产运营管理系统**（Real Estate Asset Management & Operations System）

### 核心功能
- 资产管理| 租赁合同管理（PDF 智能提取）
- 数据分析报表 | 组织架构管理 | 产权证管理

### 技术栈

| 层级 | 技术栈 |
|------|--------|
| 前端 | React 19.x + TypeScript 5.x + Vite 6.x + Ant Design 6.x + pnpm |
| 后端 | FastAPI 0.104+ + Python 3.12+ + SQLAlchemy 2.0+ + Pydantic v2 + Alembic |
| 数据库 | PostgreSQL 18.x+（开发/测试/生产统一） |
| 缓存 | Redis 8.x+ |
| 文档AI | Qwen-VL / GLM-4V / Hunyuan Vision / DeepSeek-VL |

---

## 快速命令

```bash
# 一键启动（推荐）
make dev                # 前后端同时启动
make dev-backend        # 后端 :8002
make dev-frontend       # 前端 :5173

# 代码质量
make lint               # 前后端 lint
make type-check         # TypeScript 类型检查

# 测试
make test               # 前后端测试
make test-backend       # 后端 (pytest -m unit)
make test-frontend      # 前端 (vitest)

# 其他
make migrate            # alembic upgrade head
make secrets            # 生成 SECRET_KEY / DATA_ENCRYPTION_KEY
make check              # lint + test + build 完整检查
```

### 后端 Python 环境（强制使用 UV）

```bash
cd backend
uv sync --frozen                  # 按 uv.lock 同步依赖到 backend/.venv
uv run pytest -m unit             # 在 UV 环境中运行测试
uv run alembic upgrade head       # 执行迁移
uv run python -m src.core.encryption
```

> ⚠️ 后端开发/测试统一使用 `uv`（`uv sync` / `uv run`），不要直接使用系统 `python/pip` 或 Anaconda。

---

## 项目结构

```
.
├── backend/           # FastAPI 后端
│   └── src/
│       ├── api/v1/          # API 路由层（子目录按模块划分）
│       │   ├── analytics/   # 分析报表
│       │   ├── assets/      # 资产管理
│       │   ├── auth/        # 认证授权
│       │   ├── documents/   # 文档/PDF 处理
│       │   ├── rent_contracts/ # 租赁合同
│       │   └── system/      # 系统管理
│       ├── services/        # 业务逻辑层
│       ├── crud/            # 数据访问层
│       ├── models/          # SQLAlchemy ORM 模型
│       ├── schemas/         # Pydantic 数据验证
│       ├── core/            # 核心配置 / 安全 / 事件
│       ├── security/        # 认证 / 授权 / 加密（JWT/AES）
│       ├── middleware/      # FastAPI 中间件
│       ├── config/          # 配置管理
│       ├── constants/       # 常量定义
│       ├── enums/           # 枚举类型
│       └── utils/           # 工具函数
├── frontend/          # React 前端
│   └── src/
│       ├── api/             # API 客户端
│       ├── components/      # 可复用组件 (Forms/Asset/Charts/Layout)
│       ├── pages/           # 页面（路由对应）
│       ├── services/        # API 服务封装
│       ├── hooks/           # 自定义 Hooks
│       ├── store/           # Zustand 状态管理
│       ├── contexts/        # React Context（AuthContext 等）
│       ├── types/           # TypeScript 类型定义
│       ├── routes/          # 路由配置
│       ├── styles/          # 全局样式
│       └── utils/           # 工具函数
├── docs/              # 项目文档
├── scripts/           # 辅助脚本
└── Makefile           # 常用命令
```

---

## 架构原则

### 后端分层

```
请求 → api/v1/ → services/ → crud/ → models/ → PostgreSQL
              ↑              ↑
         业务逻辑       数据访问
```

**DO / DO NOT：**
- ✅ 业务逻辑 **必须** 放在 `services/`
- ❌ **不要** 在 API 端点中放业务逻辑
- ✅ 数据访问通过 `crud/` 层
- ❌ **不要** 绕过 CRUD 直接操作数据库
- ✅ 新 API 使用 `route_registry.register_router()` 注册
- ✅ API 路径统一 `/api/v1/*`

### 前端状态管理

| 状态类型 | 使用工具 | 说明 |
|---------|---------|----|
| 全局 UI / 偏好 | Zustand | `useAppStore` / `useAssetStore` |
| 认证状态 | React Context | `AuthContext` |
| 服务器数据 | React Query | API 缓存与同步 |
| 表单 | React Hook Form | 验证 / 提交 |
| 局部 UI | useState | 模态框 / loading |

---

## 后端开发要点

### Pydantic v2
- 使用 `model_validate()` / `model_dump()`
- 配置：`model_config = ConfigDict(from_attributes=True)`

### SQLAlchemy 2.0
- ORM + QueryBuilder
- 集合关系用 `selectinload` 避免 N+1
- ❌ 不要在 schema validator 中触发懒加载

### PII 数据加密
- `SensitiveDataHandler` 对身份证号/手机号做 AES-256-CBC 确定性加密
- ❌ 不要绕过 CRUD 直接写库
- `DATA_ENCRYPTION_KEY` 缺失会降级为明文存储

### 计算字段
- `unrented_area`、`occupancy_rate` 等由 `AssetCalculator` 计算
- ❌ 不要从 API 直接写入计算字段
- `version` 字段由 ORM 自动维护（乐观锁）

### 新增功能流程
```
Schema (schemas/) → Model (models/) → CRUD (crud/) → Service (services/) → API (api/v1/)
→ 注册: route_registry.register_router(router, prefix="/api/v1", tags=[...], version="v1")
```

---

## 前端开发要点

### 严格布尔表达式

| 场景 | ❌ 错误 | ✅ 正确 |
|------|--------|--------|
| 默认值 | `\|\|` | `??` |
| 空值检查 | `if (value)` | `if (value != null)` |
| 字符串检查 | `if (str)` | `if (str?.trim() !== '')` |
| 数组长度 | `arr.length` | `arr?.length ?? 0` |

### 导入路径
- ✅ 使用 `@/` 别名：`import { X } from '@/components'`
- ❌ 不要用深层相对路径 `../../../`

### API 数据
- ✅ 使用 React Query 管理服务器数据
- ❌ 不要用 `useState + useEffect` 做数据获取

---

## 测试策略

### 后端 (pytest + UV)

**标记**：`unit` / `integration` / `e2e` / `api` / `database` / `security` / `performance` / `slow`

```bash
cd backend
uv run pytest -m unit               # 单元测试
uv run pytest -m "not slow"         # 快速测试
uv run pytest --no-cov <path>       # 关闭覆盖率（降低内存）
uv run pytest -x --maxfail=1 <path> # 失败即停
```

### 前端 (Vitest)

```bash
cd frontend
pnpm test              # 运行测试
pnpm test:coverage     # 覆盖率
```

### 覆盖率目标
- 后端：≥70%（目标 85%）
- 前端：≥50%（目标 75%）

---

## 环境配置

**后端** (`backend/.env`)：
```bash
DATABASE_URL=postgresql+psycopg://user:pass@localhost:5432/zcgl
TEST_DATABASE_URL=postgresql+psycopg://user:pass@localhost:5432/zcgl_test
SECRET_KEY="<32+ 字符随机密钥>"           # 必须配置
DATA_ENCRYPTION_KEY="<Base64 密钥>"       # cd backend && uv run python -m src.core.encryption 生成
ENVIRONMENT=development
LLM_PROVIDER="hunyuan"
```

**前端** (`frontend/.env`)：
```bash
VITE_API_BASE_URL=http://127.0.0.1:8002/api/v1
```

---

## 代码质量工具

| 工具 | 用途 |
|------|------|
| Ruff | Python lint + 格式化 |
| MyPy | Python 类型检查 |
| Bandit | Python 安全扫描 |
| UV | Python 虚拟环境与依赖管理（统一入口） |
| Tsgo | TypeScript 类型检查 (native) |
| Oxlint / Oxfmt | TS/React lint + 格式化 |
| Vitest | 前端测试 |
| pre-commit | 提交前自动检查 |

---

## Git 工作流

- **分支**：`main`（生产）← `develop`（开发）← `feature/*` / `hotfix/*`
- **提交格式**：`type(scope): description`（如 `feat(auth): 添加 OAuth2 登录`）

### 冲突处理规则

- ❌ **禁止** 大量冲突时直接 `-X theirs/ours` 后推送，必须逐文件人工复核
- ✅ `modify/delete` 冲突先查 `git log -- <file>` 确认是否架构收口
- ✅ 冲突解决后检查：无冲突标记 + 关键导入烟测 + `ruff check` + 受影响测试
- ✅ 涉及 `models/` / `crud/` 的冲突需重点复核，防止重复定义

> 📖 详细复盘与标准化流程见 [Git 冲突处理复盘](docs/incidents/2026-02-git-conflict-postmortem.md)

---

## 排障速查

| 问题 | 解决方案 |
|------|---------| 
| 后端 Import 错误 | `cd backend && uv sync --frozen` |
| 数据库连接失败 | 检查 PostgreSQL 服务和 `DATABASE_URL` |
| Alembic 迁移失败 | `cd backend && uv run alembic stamp head && uv run alembic upgrade head` |
| 前端端口被占用 | 修改 `vite.config.ts` 或 kill 进程 |
| 加密未生效 | 检查 `DATA_ENCRYPTION_KEY` |
| TypeScript 严格布尔错误 | 使用 `??` 和显式空值检查 |
| CORS 错误 | 检查后端 `CORS_ORIGINS` |
| 403 权限错误 | 执行 `init_rbac_data.py` 补齐 RBAC |

> 📖 更多启动排查经验见 [Git 冲突处理复盘](docs/incidents/2026-02-git-conflict-postmortem.md#启动排查经验)

---

## ⚠️ 安全警告

> [!DANGER]
> - `SECRET_KEY` 必须为强随机密钥，不得使用默认值
> - **永远不要** 提交 `.env` 文件
> - 生产环境必须修改所有默认密码

> [!WARNING]
> - 拉取代码后始终运行 `cd backend && uv run alembic upgrade head`
> - API 返回 403 时检查 RBAC 权限（`init_rbac_data.py`）

---

## 文档索引

- [快速开始](docs/guides/getting-started.md) | [环境配置](docs/guides/environment-setup.md)
- [后端开发](docs/guides/backend.md) | [前端开发](docs/guides/frontend.md)
- [数据库指南](docs/guides/database.md) | [测试标准](docs/guides/testing-standards.md)
- [API 总览](docs/integrations/api-overview.md) | [命名规范](docs/guides/naming-conventions.md)
- [Git 冲突复盘](docs/incidents/2026-02-git-conflict-postmortem.md)
