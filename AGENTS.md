# AGENTS.md

本文件为 AI Coding Agents 提供项目上下文与执行约束，确保修改一致、可验证。
每次修改后请更新CHANGELOG.md

**Last Updated**: 2026-02-05

---

## 项目概述

**土地物业资产管理系统**（Land Property Asset Management System）- 一个用于管理土地和物业资产的综合管理平台。

### 核心功能
- 🏢 资产管理（58字段资产信息管理）
- 📋 租赁合同管理（PDF智能识别+数据提取）
- 👥 用户权限管理（RBAC权限控制）
- 📊 数据分析报表（可视化图表+统计分析）
- 🏗️ 组织架构管理（层级结构管理）
- 📄 产权证管理（Property Certificate管理）
- 📑 PDF文档智能提取（LLM Vision API）

### 技术栈

| 层级 | 技术栈 |
|------|--------|
| 前端 | React 19.2 + TypeScript 5.9 + Vite 6 + Ant Design 6 + pnpm |
| 后端 | FastAPI 0.104+ + Uvicorn 0.38+ + Python 3.12 + SQLAlchemy 2.0 + Pydantic v2 + Alembic |
| 数据库 | PostgreSQL 16+（开发/测试/生产统一；SQLite已移除）|
| 缓存 | Redis 7 |
| 文档AI | Qwen-VL / GLM-4V / Hunyuan Vision / DeepSeek-VL |

---

## 快速命令

```bash
# 一键启动开发环境（前后端）
make dev

# 进程监控启动（异常退出记录日志）
pwsh -File scripts/dev_watch.ps1

# 单独启动
make dev-backend      # 后端 :8002
make dev-frontend     # 前端 :5173

# 代码质量检查
make lint             # 前后端 lint
make type-check       # TypeScript 类型检查

# 测试
make test             # 前后端测试
make test-backend     # 仅后端单元测试 (pytest -m unit)
make test-frontend    # 仅前端测试 (vitest)

## ⚠️ 测试环境提示（重要）
- 后端测试请使用项目虚拟环境 `backend/.venv`，避免使用系统 Python 或 Anaconda 导致 `.env` 不生效
- 示例：
  - `cd backend && .\\.venv\\Scripts\\pytest.exe tests/unit/services/core/test_security_service_removed.py -q`
  - 或先 `cd backend` 后执行 `.\.venv\Scripts\activate` 再运行 `pytest`

# 其他常用命令
make secrets          # 生成 SECRET_KEY / DATA_ENCRYPTION_KEY
make migrate          # alembic upgrade head
make build-frontend   # 构建前端生产包
make check            # 完整检查（lint + test + build + import）

# 手动开发
# 前端
cd frontend && pnpm dev
cd frontend && pnpm lint && pnpm type-check

# 后端
cd backend && python run_dev.py
cd backend && ruff check . && ruff format . && mypy src
cd backend && pytest -m unit
```

---

## 项目结构

### 根目录布局
```
.
├── backend/           # FastAPI 后端
├── frontend/          # React 前端
├── docs/              # 项目文档
├── scripts/           # 辅助脚本
├── database/          # 数据库相关文件
├── docker-compose.yml # Docker 编排配置
├── Dockerfile         # 主 Dockerfile
└── Makefile           # 常用命令
```

### 后端结构 (`backend/`)
```
src/
├── api/v1/            # API 路由层（FastAPI Routers）
├── services/          # 业务逻辑层（核心业务规则）
├── crud/              # 数据访问层（CRUD 操作）
├── models/            # SQLAlchemy ORM 模型
├── schemas/           # Pydantic 数据验证模型
├── core/              # 核心配置、安全、工具
├── security/          # 认证、授权、加密
├── middleware/        # FastAPI 中间件
├── utils/             # 工具函数
├── database.py        # 数据库连接管理
├── main.py            # 应用入口
└── exceptions.py      # 自定义异常

tests/
├── unit/              # 单元测试（快速、隔离）
├── integration/       # 集成测试（模块协作）
├── e2e/               # 端到端测试（完整工作流）
├── security/          # 安全测试
├── load/              # 性能/负载测试
└── conftest.py        # pytest 配置和 fixtures
```

### 前端结构 (`frontend/src/`)
```
src/
├── api/               # API 客户端配置
├── components/        # 可复用组件
│   ├── Forms/         # 统一表单组件
│   ├── Asset/         # 资产相关组件
│   ├── Rental/        # 租赁相关组件
│   ├── Charts/        # 图表组件
│   └── Layout/        # 布局组件
├── pages/             # 页面组件（路由对应）
├── services/          # API 服务封装
├── hooks/             # 自定义 React Hooks
├── store/             # Zustand 状态管理
├── types/             # TypeScript 类型定义
├── utils/             # 工具函数
├── routes/            # 路由配置
└── styles/            # 全局样式
```

---

## 架构原则

### 后端分层架构
```
请求 → api/v1/ → services/ → crud/ → models/ → PostgreSQL
              ↑              ↑
         业务逻辑       数据访问
```

**核心规则**：
1. 业务逻辑 **必须** 放在 `services/`，不要放在 API 端点中
2. CRUD 为纯数据访问层；不要绕过 CRUD 直接操作数据库
3. 新增 API 需使用 `route_registry.register_router()` 注册
4. API 路径统一按 `/api/v1/*` 版本化

### 前端状态管理策略

| 状态类型 | 使用工具 | 适用场景 |
|---------|---------|---------|
| 全局 UI / 偏好 / 通知 | Zustand | 主题、侧边栏、语言、用户偏好、通知等全局 UI 状态（`useAppStore`） |
| 资产相关 UI 状态 | Zustand | 资产选中/多选、筛选参数、视图模式等（`useAssetStore`） |
| 认证状态 | React Context | 当前登录用户、登录/登出流程（`AuthContext`） |
| 服务器数据 | React Query | API 数据获取、缓存、同步 |
| 表单状态 | React Hook Form | 表单验证、提交 |
| 局部 UI | useState | 模态框开关、loading 状态 |

说明：`frontend/src/store/` 目录实际存在，当前包含 `useAppStore` 与 `useAssetStore`；认证状态不在 Zustand，而在 `frontend/src/contexts/AuthContext.tsx`。

---

## 后端开发要点

### 1. Pydantic v2
- 使用 `model_validate()` / `model_dump()`
- 响应模型启用 `from_attributes`
- 推荐配置：`model_config = ConfigDict(from_attributes=True)`

### 2. SQLAlchemy 2.0
- 优先使用 ORM + QueryBuilder
- 列表接口注意 N+1 问题，集合关系优先 `selectinload`
- 避免在 schema validator 中触发懒加载

### 3. PII 数据加密
Asset/Organization/RentContract/Contact/PropertyCertificate 等 CRUD 使用 `SensitiveDataHandler` 进行敏感字段加密：

| 字段类型 | 加密方式 | 说明 |
|---------|---------|------|
| 身份证号 | AES-256-CBC (确定性) | 支持搜索 |
| 手机号 | AES-256-CBC (确定性) | 支持搜索 |

- 不要绕过 CRUD 直接写库
- `DATA_ENCRYPTION_KEY` 缺失会降级为明文存储
- 生成密钥：`python -m src.core.encryption`

### 4. 计算字段
- `unrented_area`、`occupancy_rate` 等由 `AssetCalculator` 计算
- API/Service 层处理，不要从 API 直接写入
- `version` 字段由 ORM 自动维护（乐观锁）

### 5. 新增功能流程
```python
# 1. Schema (schemas/my_feature.py)
class MyFeatureCreate(BaseModel):
    name: str

# 2. Model (models/my_feature.py)
class MyFeature(Base):
    __tablename__ = "my_features"
    id = Column(Integer, primary_key=True)

# 3. CRUD (crud/my_feature.py)
class CRUDMyFeature(CRUDBase[...]): pass
my_feature_crud = CRUDMyFeature(MyFeature)

# 4. Service (services/my_feature/my_feature_service.py)
class MyFeatureService:
    def create(self, data: dict): ...

# 5. API (api/v1/my_feature.py)
router = APIRouter(prefix="/my-feature", tags=["My Feature"])
@router.get("/")
async def get_all(service: MyFeatureService = Depends(get_service)): ...

# 6. 注册路由
route_registry.register_router(router, prefix="/api/v1", tags=["My Feature"], version="v1")
```

---

## 前端开发要点

### 1. 严格布尔表达式（重要！）
本项目启用 `@typescript-eslint/strict-boolean-expressions` 规则，必须使用显式空值检查：

| 场景 | ❌ 错误 | ✅ 正确 |
|------|--------|--------|
| 默认值 | `\|\|` | `??` |
| 空值检查 | `if (value)` | `if (value != null)` |
| 字符串检查 | `if (str)` | `if (str?.trim() !== '')` |
| 布尔比较 | `if (bool)` | `if (bool === true)` |
| 数组长度 | `arr.length` | `arr?.length ?? 0` |

### 2. 导入路径规范
```typescript
// ✅ 正确 - 使用 @/ 别名
import { apiClient } from '@/api/client';
import { AssetForm } from '@/components/Forms';

// ❌ 已废弃 - 相对路径深层导入
import { apiClient } from '../../../api/client';
```

### 3. API 调用模式
```typescript
// ✅ 正确 - 使用 React Query 管理服务器数据
const { data: assets, isLoading } = useQuery({
  queryKey: ['assets'],
  queryFn: () => apiClient.get('/assets'),
  staleTime: 5 * 60 * 1000,
});

// ❌ 错误 - 不要用 useState + useEffect 管理服务器数据
```

---

## 测试策略

### 后端测试 (pytest)

**测试标记**（用于分类运行）：
- `unit` - 单元测试（快速、隔离）
- `integration` - 集成测试（模块协作）
- `e2e` - 端到端测试（完整工作流）
- `api` - API 端点测试
- `database` - 数据库测试
- `security` - 安全测试
- `performance` - 性能测试
- `slow` - 慢测试（>10s）

**常用命令**：
```bash
cd backend
pytest -m unit                    # 仅单元测试
pytest -m "not slow"              # 排除慢测试
pytest -m integration             # 集成测试
pytest --cov=src --cov-report=html # 覆盖率报告
```

### 低内存测试建议（避免卡死）

```bash
# 单文件或单用例（优先）
cd backend
pytest tests/unit/services/asset/test_asset_service.py
pytest tests/unit/services/asset/test_asset_service.py::TestCreateAsset::test_create_asset_success

# 关闭覆盖率（显著降低内存）
pytest --no-cov <path>
pytest -p no:cov <path>

# 失败即停 / 只跑上次失败
pytest -x --maxfail=1 <path>
pytest -lf

# 降低并发（若启用了 xdist）
pytest -n 0 <path>

# 找出最慢/最吃内存用例
pytest --durations=10 <path>
```

**测试目录**：
- `tests/unit/` - 模型、服务、CRUD、工具函数测试
- `tests/integration/` - API、数据库集成测试
- `tests/e2e/` - 完整业务流程测试
- `tests/security/` - 安全相关测试

### 前端测试 (Vitest)

**测试位置**：
- 组件测试：`src/components/**/__tests__/*.test.tsx`
- Hook 测试：`src/hooks/__tests__/*.test.ts`
- 服务测试：`src/services/__tests__/*.test.ts`
- 工具测试：`src/utils/__tests__/*.test.ts`

**常用命令**：
```bash
cd frontend
pnpm test              # 运行测试
pnpm test:ui           # UI 模式
pnpm test:coverage     # 覆盖率报告
```

### 覆盖率目标
- 后端：≥70%（目标 85%）
- 前端：≥50%（目标 75%）

---

## 环境与配置

### 必需环境变量

**后端** (`backend/.env`):
```bash
# 数据库（PostgreSQL 必需）
DATABASE_URL=postgresql+psycopg://user:pass@localhost:5432/zcgl
TEST_DATABASE_URL=postgresql+psycopg://user:pass@localhost:5432/zcgl_test

# 安全密钥（生产环境必须修改！）
SECRET_KEY="your-secret-key-here"
DATA_ENCRYPTION_KEY="your-encryption-key-here"

# 环境类型
ENVIRONMENT=development  # production, development, testing, staging

# LLM/Vision API（PDF智能提取）
LLM_PROVIDER="hunyuan"  # qwen | glm | deepseek | hunyuan
DASHSCOPE_API_KEY="your-api-key"
```

**前端** (`frontend/.env`):
```bash
VITE_API_BASE_URL=http://127.0.0.1:8002/api/v1
VITE_API_TIMEOUT=30000
```

### 生成密钥
```bash
make secrets
# 或
python -c "import secrets; print('SECRET_KEY=\"%s\"' % secrets.token_urlsafe(32))"
# DATA_ENCRYPTION_KEY 需要标准 Base64 + 版本号（避免 Incorrect padding）:
# cd backend && python -m src.core.encryption
```

---

## 代码质量工具

### 后端
- **Ruff**: 代码检查与格式化（替代 flake8/black）
- **MyPy**: 静态类型检查（渐进式严格策略）
- **Bandit**: 安全漏洞扫描
- **pytest**: 测试框架

### 前端
- **ESLint**: TypeScript/React 代码检查
- **Prettier**: 代码格式化
- **Vitest**: 测试框架
- **stylelint**: CSS/SCSS 检查

### Pre-commit Hooks
项目配置了 pre-commit 钩子，在提交前自动运行：
- Ruff 检查与格式化
- MyPy 类型检查
- Bandit 安全扫描
- 基础文件检查（YAML/JSON格式、行尾空格等）

安装：
```bash
pip install pre-commit
pre-commit install
```

---

## Git 工作流

采用 **Git Flow** 分支策略：

```
main (生产)
  ↑
  ├── merge (release)
  ↑
develop (开发)
  ↑
  ├── merge (feature)
  ↑
feature/* (功能分支)
hotfix/* (紧急修复)
release/* (发布准备)
```

### 提交规范 (Conventional Commits)
```
<type>(<scope>): <subject>

<body>

<footer>
```

| 类型 | 说明 | 示例 |
|------|------|------|
| `feat` | 新功能 | `feat(auth): 添加 OAuth2 登录` |
| `fix` | Bug 修复 | `fix(api): 修复查询参数解析错误` |
| `docs` | 文档更新 | `docs: 更新 API 文档` |
| `refactor` | 重构 | `refactor(database): 优化查询性能` |
| `test` | 测试相关 | `test: 添加单元测试` |
| `chore` | 构建/工具 | `chore: 更新依赖版本` |

---

## 部署

### Docker Compose（推荐）
```bash
docker-compose up -d
```

包含服务：
- `frontend` - React 应用 (port 3000)
- `backend` - FastAPI 服务 (port 8002)
- `postgres` - PostgreSQL 数据库 (port 5432)
- `redis` - Redis 缓存 (port 6379)
- `nginx` - 反向代理 (port 80/443)

### 生产部署要点
1. 修改所有默认密钥（SECRET_KEY, DATA_ENCRYPTION_KEY）
2. 配置 PostgreSQL 强密码
3. 启用 HTTPS（配置 SSL 证书）
4. 配置防火墙规则
5. 设置日志收集和监控

---

## 安全注意事项

### 敏感数据加密
- 身份证号、手机号等 PII 字段自动加密存储
- 加密密钥必须安全保管，勿提交到版本控制
- 生产环境使用 AWS KMS / HashiCorp Vault 等密钥管理服务

### 认证与授权
- JWT Token 认证
- RBAC 权限控制
- CSRF 保护
- IP 黑名单和自动封禁

### 安全扫描
- Bandit：Python 安全漏洞扫描
- 依赖安全检查：`safety check`

---

## 常见问题

| 问题 | 解决方案 |
|------|---------|
| 后端 Import 错误 | `cd backend && pip install -e .` |
| 数据库连接失败 | 检查 PostgreSQL 服务和连接配置 |
| Alembic 迁移失败 | `alembic stamp head && alembic upgrade head` |
| 前端端口被占用 | 修改 `vite.config.ts` |
| 加密未生效 | 检查 `DATA_ENCRYPTION_KEY` 是否设置 |
| 搜索加密字段失败 | 确保使用确定性加密 |
| TypeScript 严格布尔错误 | 使用 `??` 和显式空值检查 |

---

## 启动与排查经验

- 后端开发请使用项目虚拟环境 `backend/.venv`（避免系统/Anaconda 导致 `.env` 不生效或 CORS/依赖异常）
- 后端启动建议：`cd backend && .\\.venv\\Scripts\\python.exe run_dev.py`
- 若 8002 被占用可临时切换端口（例如 8003），需要同步调整前端代理或 API_BASE_URL
- 前端推荐保持 `VITE_API_BASE_URL=/api/v1` + Vite 代理，避免跨域
- `/system/users` 报错常见原因：
- CORS 预检未允许 `Authorization` 头，需在后端 CORS 允许头中加入 `Authorization`
- CORS 中间件需包裹错误响应（放在中间件链最外层）
- `/api/v1/roles` 的 `MissingGreenlet` 多由角色权限懒加载触发，需在 role CRUD 用 `selectinload(Role.permissions)` 预加载
- `/api/v1/auth/users` 若使用 `DISTINCT` 包含 JSON 列会触发 Postgres “json 无等号”错误，应改为 `distinct(User.id)` 并独立 count
- RBAC 初始化脚本：`backend/scripts/setup/init_rbac_data.py` 可反复执行并补齐权限（包含 `property_certificate`）
- 若数据库仍存在遗留列 `users.role` 或 `assets.ownership_entity`，先执行 `alembic upgrade head` 移除后再初始化 RBAC
- Playwright 调试建议使用 `npx --yes @playwright/cli`，产物统一放在 `output/playwright/`

---

## 文档参考

- [环境配置指南](docs/guides/environment-setup.md)
- [数据库指南](docs/guides/database.md)
- [前端开发指南](docs/guides/frontend.md)
- [后端开发指南](docs/guides/backend.md)
- [API 总览](docs/integrations/api-overview.md)
- [测试标准](docs/TESTING_STANDARDS.md)
- [命名规范](docs/guides/NAMING_CONVENTIONS.md)

---

## 变更记录
每次修改后请更新CHANGELOG.md

**注意**：本文档应与代码同步更新。任何架构变更、新工具引入或流程调整都应同步更新此文档。
