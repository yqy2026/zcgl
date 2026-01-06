# CLAUDE.md

本文件为 Claude Code 提供项目上下文。详细文档请参阅 `docs/` 目录。

---

## 项目概述

**土地物业资产管理系统** (Land Property Asset Management System)

| 层 | 技术栈 |
|---|-------|
| **前端** | React 18 + TypeScript + Vite + Ant Design 5 |
| **后端** | FastAPI + Python 3.12 + SQLAlchemy 2.0 + Pydantic v2 |
| **数据库** | SQLite (dev) / PostgreSQL (prod) |
| **缓存** | Redis |

---

## 服务端口

| 服务 | 端口 | 文档 |
|-----|------|------|
| 前端 (dev) | 5173 | http://localhost:5173 |
| 后端 API | 8002 | **Swagger**: http://localhost:8002/docs |
| Redis | 6379 | - |

---

## 常用命令速查

### 开发

| 操作 | 前端 (`frontend/`) | 后端 (`backend/`) |
|------|-------------------|------------------|
| 启动 | `npm run dev` | `python run_dev.py` |
| 测试 | `npm test` | `pytest` |
| Lint | `npm run lint` | `ruff check .` |
| 类型检查 | `npm run type-check` | `mypy src` |
| 格式化 | `npm run lint:fix` | `ruff format .` |

### 数据库迁移

```bash
alembic upgrade head                    # 应用迁移
alembic revision --autogenerate -m "msg" # 创建迁移
```

### Docker

```bash
docker-compose up -d    # 启动所有服务
docker-compose down     # 停止所有服务
```

---

## 核心架构

### 请求流程

```
React UI → EnhancedApiClient → FastAPI (/api/v1/*) → Service → CRUD → SQLAlchemy
```

### 后端分层

```
请求 → api/v1/ (端点定义) → services/ (业务逻辑) → crud/ (数据库操作) → models/ (ORM)
                              ↑ 必须放这里!
```

**Service层目录结构** (2026-01-04 更新):
```
backend/src/services/
├── analytics/         # 分析服务 (出租率、面积汇总)
│   ├── occupancy_service.py
│   └── area_service.py
├── asset/            # 资产服务
│   ├── asset_service.py
│   ├── batch_service.py      # 批量操作（事务管理）
│   └── validators.py         # 数据验证
├── backup/           # 备份服务
│   └── backup_service.py
├── excel/            # Excel服务
│   ├── excel_import_service.py
│   ├── excel_export_service.py
│   └── excel_template_service.py
├── core/             # 核心服务 (认证、用户管理)
├── custom_field/     # 自定义字段服务
├── document/         # 文档处理服务
└── [其他服务目录...]
```

### 前端状态管理

| 状态类型 | 使用 | 示例 |
|---------|------|------|
| 全局 UI | Zustand | 主题、用户、权限 |
| 服务器数据 | React Query | API 数据缓存 |
| 表单 | React Hook Form | 表单验证 |
| 组件局部 | useState | 模态框开关 |

---

## 关键开发规范

### API 导入路径 (2025-12-24 更新)

```typescript
// ✅ 正确
import { enhancedApiClient } from '@/api/client';
import { AssetForm } from '@/components/Forms';

// ❌ 已废弃 (仍可用但不推荐)
import { enhancedApiClient } from '@/services';
import { AssetForm } from '@/components/Asset';
```

### 业务逻辑位置

```python
# ✅ 正确 - 业务逻辑在 Service 层
# backend/src/services/asset/asset_service.py
class AssetService:
    def process(self, data): ...

# ❌ 错误 - 业务逻辑在 API 端点
@router.post("/process")
async def process(data):
    # 不要在这里放业务逻辑!
```

### 新增 API 端点

```python
# backend/src/api/v1/my_feature.py
from src.core.router_registry import route_registry

router = APIRouter(prefix="/my-feature", tags=["My Feature"])

@router.get("/items")
async def get_items(): ...

# 注册路由
route_registry.register_router(router, prefix="/api/v1", tags=["My Feature"], version="v1")
```

---

## ⚠️ 关键陷阱警告

> [!CAUTION]
> **OCR 服务已禁用** - PaddleOCR 存在编码问题，请勿尝试使用

```python
from src.core.import_utils import safe_import
ocr = safe_import("services.ocr", fallback=None)
if ocr is None:
    # 必须提供回退方案
```

> [!WARNING]
> **JWT Secret**: 生产环境必须 32+ 字符，否则启动失败

> [!WARNING]
> **Alembic 迁移失败**: 运行 `alembic stamp head` 重置后再 `alembic upgrade head`

---

## 目录结构 (核心)

```
zcgl/
├── frontend/src/
│   ├── api/            # API 客户端 (client.ts, config.ts)
│   ├── components/     # 159 个 React 组件
│   ├── pages/          # 42 个页面
│   ├── services/       # 35 个 API 服务
│   ├── hooks/          # 19 个自定义 Hook
│   ├── store/          # Zustand 状态
│   └── types/          # TypeScript 类型
├── backend/
│   ├── src/
│   │   ├── api/v1/     # 33+ 个 API 端点
│   │   ├── services/   # 模块化服务层 (核心业务逻辑)
│   │   ├── crud/       # 16 个 CRUD 文件
│   │   ├── models/     # 11 个 ORM 模型
│   │   ├── schemas/    # 16 个 Pydantic 模型
│   │   └── utils/      # 运行时工具
│   ├── scripts/
│   │   └── devtools/   # 开发工具脚本
│   └── tests/
│       ├── unit/       # 单元测试 (97个通过 ✅)
│       ├── integration/ # 集成测试
│       └── api/        # API 测试
└── docs/               # 详细文档
```

---

## 测试

```bash
# 后端 (按类型)
pytest -m unit          # 单元测试
pytest -m integration   # 集成测试
pytest -m api           # API 测试

# 前端
npm test                # 运行测试
npm run test:coverage   # 覆盖率报告
```

**覆盖率要求**: > 95%

---

## 环境配置

```bash
# backend/.env
ENVIRONMENT=development  # production, testing, staging
DEPENDENCY_POLICY=strict # graceful, optional
```

详见 `backend/src/core/environment.py`

---

## 详细文档

| 主题 | 文件 |
|------|------|
| 环境配置 | `docs/guides/environment-setup.md` |
| 数据库 | `docs/guides/database.md` |
| 前端开发 | `docs/guides/frontend.md` |
| 后端开发 | `docs/guides/backend.md` |
| 部署 | `docs/guides/deployment.md` |
| API 概览 | `docs/integrations/api-overview.md` |
| 测试标准 | `docs/TESTING_STANDARDS.md` |

---

## Git 工作流

- **main**: 生产分支
- **develop**: 集成分支
- **feature/***: 功能分支
- **hotfix/***: 热修复

**提交格式**: `type(scope): description` (如 `feat(auth): add JWT refresh`)
