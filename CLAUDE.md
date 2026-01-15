# CLAUDE.md

本文件为 Claude Code 提供项目上下文。详细文档请参阅 `README.md` 和 `docs/` 目录。

**最后更新**: 2026-01-15

---

## 项目概述

**土地物业资产管理系统** (Land Property Asset Management System)

| 层 | 技术栈 |
|---|-------|
| **前端** | React 18 + TypeScript + Vite + Ant Design 5 |
| **后端** | FastAPI + Python 3.12 + SQLAlchemy 2.0 + Pydantic v2 |
| **数据库** | PostgreSQL |
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

**Service层目录结构** (2026-01-11 更新):
```
backend/src/services/        # 19 个子目录
├── analytics/         # 分析服务 (出租率、面积汇总)
├── asset/            # 资产服务 (核心业务、批量操作、验证)
├── backup/           # 备份服务
├── core/             # 核心服务 (认证、用户管理)
├── custom_field/     # 自定义字段服务
├── document/         # 文档处理服务 (OCR、PDF解析、LLM提取)
├── excel/            # Excel 导入/导出服务
├── notification/     # 通知服务 (站内消息、企业微信推送)
├── organization/     # 组织管理服务
├── ownership/        # 权属管理服务
├── permission/       # 权限服务
├── project/          # 项目管理服务
├── rbac/             # 角色权限服务
├── rent_contract/    # 租赁合同服务 (V2生命周期管理)
├── system_dictionary/ # 系统字典服务
└── task/             # 任务管理服务
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

### 环境感知依赖加载

后端使用独特的依赖管理策略，支持三种模式：

```bash
# backend/.env
DEPENDENCY_POLICY=strict     # 严格模式: 关键依赖必须存在
DEPENDENCY_POLICY=graceful   # 优雅模式: 可选依赖降级处理
DEPENDENCY_POLICY=optional   # 可选模式: 依赖缺失时禁用功能
```

详见 `backend/src/core/environment.py` 和 `backend/src/core/import_utils.py`

### 前端 Code Splitting 策略

```typescript
// Vite 配置实现代码分割
// - React 核心库单独打包
// - Ant Design 组件按需加载
// - 页面级别懒加载
// - 功能模块分割
```

---

## ⚠️ 关键陷阱警告

> [!NOTE]
> **OCR 服务已升级** - PaddleOCR 3.3 已可用，使用 `paddleocr_service.py` 进行文档处理。
> 安装 OCR 依赖：`uv sync --extra pdf-ocr`

```python
from src.services.document.paddleocr_service import get_paddleocr_service
service = get_paddleocr_service()
if service.is_available:
    result = service.to_markdown("contract.pdf")
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
│   ├── components/     # 136 个 React 组件
│   │   ├── Forms/      # 统一表单组件
│   │   ├── Asset/      # 资产相关组件
│   │   ├── Charts/     # 数据可视化
│   │   ├── Layout/     # 布局组件
│   │   └── Router/     # 动态路由加载
│   ├── pages/          # 41 个页面
│   ├── services/       # 35 个 API 服务
│   ├── hooks/          # 17 个自定义 Hook
│   ├── store/          # Zustand 状态
│   ├── types/          # 18 个 TypeScript 类型定义
│   └── utils/          # 19 个工具函数
├── backend/
│   ├── src/
│   │   ├── api/v1/     # 41 个 API 端点
│   │   ├── services/   # 19 个服务子目录 (核心业务逻辑)
│   │   ├── crud/       # 18 个 CRUD 文件
│   │   ├── models/     # 16 个 ORM 模型
│   │   ├── schemas/    # 18 个 Pydantic 模型
│   │   └── utils/      # 运行时工具
│   ├── scripts/
│   │   └── devtools/   # 开发工具脚本
│   └── tests/
│       ├── unit/       # 单元测试
│       ├── integration/ # 集成测试
│       └── api/        # API 测试
└── docs/               # 详细文档
```

---

## 测试

```bash
# 后端 (按标记)
pytest -m unit          # 单元测试
pytest -m integration   # 集成测试
pytest -m api           # API 测试
pytest -m e2e           # 端到端测试
pytest -m security      # 安全测试
pytest -m performance   # 性能测试

# 前端
npm test                # 运行测试
npm run test:coverage   # 覆盖率报告
```

**覆盖率要求**: 后端 > 85%, 前端 > 75%

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

| 开发工作流 | `docs/guides/development-workflow.md` |

---

## Git 工作流

- **main**: 生产分支
- **develop**: 集成分支
- **feature/***: 功能分支
- **hotfix/***: 热修复

**提交格式**: `type(scope): description` (如 `feat(auth): add JWT refresh`)

---

## V2.0 新功能

- **通知中心**: 站内消息、合同到期提醒、企业微信推送
- **项目/权属详情页**: 独立详情页、关联资产/合同列表
- **合同智能提取**: PDF OCR + LLM 多模型混合提取

详见 `docs/v2-release-notes.md`
