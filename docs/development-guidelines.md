# 土地物业管理资产系统 - 开发规范

## 概述

本文档定义了土地物业管理资产系统的开发规范和最佳实践，确保代码质量、API一致性和系统可维护性。

## 目录

1. [项目结构](#项目结构)
2. [代码规范](#代码规范)
3. [API设计规范](#api设计规范)
4. [数据库规范](#数据库规范)
5. [前端开发规范](#前端开发规范)
6. [测试规范](#测试规范)
7. [部署规范](#部署规范)
8. [工具和自动化](#工具和自动化)

## 项目结构

### 后端项目结构

```
backend/
├── src/
│   ├── api/v1/              # API路由层
│   │   ├── assets.py       # 资产管理API
│   │   ├── projects.py     # 项目管理API
│   │   ├── excel.py        # Excel导入导出API
│   │   └── ...
│   ├── models/             # 数据模型层
│   │   ├── asset.py        # 资产模型
│   │   ├── task.py         # 任务模型
│   │   └── ...
│   ├── schemas/            # Pydantic数据验证
│   │   ├── asset.py        # 资产数据模式
│   │   ├── task.py         # 任务数据模式
│   │   └── ...
│   ├── crud/               # 数据库操作层
│   │   ├── asset.py        # 资产CRUD操作
│   │   └── ...
│   ├── services/           # 业务逻辑层
│   │   ├── excel_import.py # Excel导入服务
│   │   └── ...
│   ├── middleware/         # 中间件
│   │   └── api_versioning.py
│   ├── validation/         # 数据验证框架
│   │   └── framework.py
│   ├── utils/              # 工具类
│   │   ├── api_doc_generator.py
│   │   └── api_consistency_checker.py
│   └── cli/                # 命令行工具
│       └── api_tools.py
├── tests/                  # 测试文件
├── migrations/             # 数据库迁移
├── docs/                   # 文档
├── pyproject.toml          # 项目配置
└── run_dev.py             # 开发服务器
```

### 前端项目结构

```
frontend/
├── src/
│   ├── components/         # 通用组件
│   │   ├── common/         # 基础组件
│   │   ├── forms/          # 表单组件
│   │   └── ...
│   ├── pages/              # 页面组件
│   │   ├── assets/         # 资产页面
│   │   ├── dashboard/      # 仪表板
│   │   └── ...
│   ├── services/           # API服务层
│   │   ├── api.ts          # API配置
│   │   ├── assetService.ts # 资产服务
│   │   └── ...
│   ├── types/              # TypeScript类型定义
│   │   ├── asset.ts        # 资产类型
│   │   └── ...
│   ├── utils/              # 工具函数
│   ├── hooks/              # React Hooks
│   └── stores/             # 状态管理
├── public/                 # 静态资源
├── tests/                  # 测试文件
├── package.json            # 项目配置
└── vite.config.ts          # Vite配置
```

## 代码规范

### Python代码规范

#### 1. 命名规范

- **类名**: PascalCase (如 `AssetCRUD`, `TaskService`)
- **函数名**: snake_case (如 `get_asset_by_id`, `process_excel_import`)
- **变量名**: snake_case (如 `asset_data`, `user_id`)
- **常量**: UPPER_SNAKE_CASE (如 `MAX_FILE_SIZE`, `DEFAULT_PAGE_SIZE`)
- **文件名**: snake_case (如 `asset_service.py`, `excel_import.py`)

#### 2. 代码格式

```python
# 导入顺序：标准库 -> 第三方库 -> 本地模块
import os
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.asset import Asset
from ..schemas.asset import AssetCreate

# 函数定义：使用类型注解
async def create_asset(
    asset_in: AssetCreate,
    db: Session = Depends(get_db)
) -> Asset:
    """创建新资产

    Args:
        asset_in: 资产创建数据
        db: 数据库会话

    Returns:
        创建的资产对象

    Raises:
        HTTPException: 创建失败时抛出
    """
    try:
        asset = asset_crud.create(db=db, obj_in=asset_in)
        return asset
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建资产失败: {str(e)}")
```

#### 3. 文档字符串

使用Google风格的文档字符串：

```python
def calculate_occupancy_rate(rented_area: float, rentable_area: float) -> float:
    """计算出租率

    Args:
        rented_area: 已出租面积
        rentable_area: 可出租面积

    Returns:
        出租率百分比 (0-100)

    Raises:
        ValueError: 当面积为负数时

    Example:
        >>> calculate_occupancy_rate(80, 100)
        80.0
    """
    if rentable_area <= 0:
        raise ValueError("可出租面积必须大于0")

    return (rented_area / rentable_area) * 100
```

### TypeScript代码规范

#### 1. 命名规范

- **接口名**: PascalCase (如 `Asset`, `AssetSearchParams`)
- **类型名**: PascalCase (如 `OwnershipStatus`, `TaskStatus`)
- **函数名**: camelCase (如 `getAssets`, `createTask`)
- **变量名**: camelCase (如 `assetData`, `userId`)
- **常量**: UPPER_SNAKE_CASE (如 `API_BASE_URL`, `MAX_FILE_SIZE`)

#### 2. 代码格式

```typescript
// 接口定义
interface Asset {
  id: string
  property_name: string
  address: string
  ownership_status: OwnershipStatus
  created_at?: string
  updated_at?: string
}

// 服务函数
export const assetService = {
  async getAssets(params: AssetSearchParams): Promise<AssetListResponse> {
    try {
      const response = await api.get<AssetListResponse>('/assets', { params })
      return response.data
    } catch (error) {
      console.error('获取资产列表失败:', error)
      throw error
    }
  }
}

// React组件
interface AssetListProps {
  assets: Asset[]
  onAssetSelect: (asset: Asset) => void
}

export const AssetList: React.FC<AssetListProps> = ({ assets, onAssetSelect }) => {
  return (
    <div className="asset-list">
      {assets.map(asset => (
        <AssetItem
          key={asset.id}
          asset={asset}
          onSelect={onAssetSelect}
        />
      ))}
    </div>
  )
}
```

## API设计规范

### 1. RESTful API设计

#### URL命名规范

```
# 资源命名使用复数形式
GET    /api/v1/assets           # 获取资产列表
POST   /api/v1/assets           # 创建新资产
GET    /api/v1/assets/{id}      # 获取单个资产
PUT    /api/v1/assets/{id}      # 更新资产
DELETE /api/v1/assets/{id}      # 删除资产

# 嵌套资源
GET    /api/v1/assets/{id}/documents     # 获取资产文档
POST   /api/v1/assets/{id}/documents     # 为资产添加文档

# 操作类接口使用动词
POST   /api/v1/assets/batch-update      # 批量更新资产
POST   /api/v1/assets/export            # 导出资产数据
POST   /api/v1/excel/import             # Excel导入
```

#### HTTP状态码规范

```
200 OK                  # 请求成功
201 Created             # 资源创建成功
204 No Content          # 删除成功
400 Bad Request         # 请求参数错误
401 Unauthorized        # 未授权
403 Forbidden          # 权限不足
404 Not Found           # 资源不存在
409 Conflict            # 资源冲突
422 Unprocessable Entity  # 数据验证失败
500 Internal Server Error  # 服务器错误
```

#### 响应格式规范

```typescript
// 成功响应
interface SuccessResponse<T> {
  success: true
  message: string
  data: T
}

// 分页响应
interface PaginatedResponse<T> {
  success: true
  message: string
  data: {
    items: T[]
    total: number
    page: number
    limit: number
    pages: number
  }
}

// 错误响应
interface ErrorResponse {
  success: false
  message: string
  error?: {
    code: string
    details?: any
  }
}
```

### 2. API版本控制

#### 版本策略

- 使用URL路径版本控制: `/api/v1/`, `/api/v2/`
- 向后兼容原则：新版本保持对旧版本的兼容
- 弃用通知：提前3个月通知版本弃用

#### 版本实现

```python
# 版本中间件配置
from src.middleware.api_versioning import APIVersionMiddleware

app.add_middleware(
    APIVersionMiddleware,
    default_version="v1",
    supported_versions=["v1", "v2"],
    deprecated_versions={"v1": datetime(2024, 12, 31)}
)
```

## 数据库规范

### 1. 表设计规范

#### 命名规范

- **表名**: snake_case，使用复数形式 (如 `assets`, `task_configs`)
- **字段名**: snake_case (如 `property_name`, `created_at`)
- **索引名**: `idx_表名_字段名` (如 `idx_assets_property_name`)
- **外键名**: `fk_表名_字段名` (如 `fk_assets_project_id`)

#### 字段规范

```sql
-- 主键统一使用字符串类型的UUID
id VARCHAR(36) PRIMARY KEY DEFAULT (UUID())

-- 时间字段统一使用UTC时间
created_at DATETIME DEFAULT CURRENT_TIMESTAMP
updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP

-- 软删除字段
is_active BOOLEAN DEFAULT TRUE
deleted_at DATETIME NULL

-- 审计字段
created_by VARCHAR(100)
updated_by VARCHAR(100)

-- 金额字段使用DECIMAL类型
monthly_rent DECIMAL(15, 2)
annual_income DECIMAL(15, 2)

-- 状态字段使用VARCHAR，配合CHECK约束
status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'inactive', 'deleted'))
```

### 2. 模型定义规范

```python
class Asset(Base):
    """资产模型"""
    __tablename__ = "assets"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # 基本字段
    property_name = Column(String(200), nullable=False, comment="物业名称")
    address = Column(String(500), nullable=False, comment="物业地址")

    # 审计字段
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")
    created_by = Column(String(100), comment="创建人")
    updated_by = Column(String(100), comment="更新人")

    # 关联关系
    project_id = Column(String(36), ForeignKey("projects.id"), comment="项目ID")
    project = relationship("Project", back_populates="assets")

    def __repr__(self):
        return f"<Asset(id={self.id}, name={self.property_name})>"

    @property
    def occupancy_rate(self) -> float:
        """计算出租率"""
        if self.rentable_area and self.rentable_area > 0:
            return (self.rented_area / self.rentable_area) * 100
        return 0.0
```

## 前端开发规范

### 1. 组件开发规范

#### 组件结构

```typescript
// 组件文件结构
ComponentName/
├── index.tsx          # 组件入口
├── ComponentName.tsx  # 主组件
├── ComponentName.test.tsx  # 测试文件
├── styles.module.css  # 样式文件
└── types.ts           # 类型定义
```

#### 组件模板

```typescript
import React, { useState, useEffect } from 'react'
import { Button, Table, message } from 'antd'
import type { Asset } from '@/types/asset'
import { assetService } from '@/services/assetService'
import styles from './styles.module.css'

interface AssetListProps {
  onAssetSelect?: (asset: Asset) => void
  readonly?: boolean
}

export const AssetList: React.FC<AssetListProps> = ({
  onAssetSelect,
  readonly = false
}) => {
  const [assets, setAssets] = useState<Asset[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    loadAssets()
  }, [])

  const loadAssets = async () => {
    setLoading(true)
    setError(null)

    try {
      const response = await assetService.getAssets({})
      setAssets(response.data.items)
    } catch (err) {
      const errorMsg = '加载资产列表失败'
      setError(errorMsg)
      message.error(errorMsg)
    } finally {
      setLoading(false)
    }
  }

  const handleAssetSelect = (asset: Asset) => {
    onAssetSelect?.(asset)
  }

  return (
    <div className={styles.container}>
      <Table
        dataSource={assets}
        loading={loading}
        rowKey="id"
        onRow={(record) => ({
          onClick: () => handleAssetSelect(record),
          className: styles.row
        })}
        columns={[
          {
            title: '物业名称',
            dataIndex: 'property_name',
            key: 'property_name'
          },
          {
            title: '地址',
            dataIndex: 'address',
            key: 'address'
          }
        ]}
      />
    </div>
  )
}
```

### 2. 状态管理规范

#### Zustand Store

```typescript
import { create } from 'zustand'
import { devtools } from 'zustand/middleware'
import type { Asset, AssetSearchParams } from '@/types/asset'
import { assetService } from '@/services/assetService'

interface AssetStore {
  // 状态
  assets: Asset[]
  loading: boolean
  error: string | null
  total: number
  filters: AssetSearchParams

  // 动作
  loadAssets: (params?: AssetSearchParams) => Promise<void>
  createAsset: (asset: Partial<Asset>) => Promise<void>
  updateAsset: (id: string, asset: Partial<Asset>) => Promise<void>
  deleteAsset: (id: string) => Promise<void>
  setFilters: (filters: Partial<AssetSearchParams>) => void
  clearError: () => void
}

export const useAssetStore = create<AssetStore>()(
  devtools(
    (set, get) => ({
      // 初始状态
      assets: [],
      loading: false,
      error: null,
      total: 0,
      filters: {},

      // 动作实现
      loadAssets: async (params) => {
        const { filters } = get()
        const searchParams = { ...filters, ...params }

        set({ loading: true, error: null })

        try {
          const response = await assetService.getAssets(searchParams)
          set({
            assets: response.data.items,
            total: response.data.total,
            loading: false
          })
        } catch (error) {
          set({
            error: error.message,
            loading: false
          })
        }
      },

      createAsset: async (assetData) => {
        try {
          const newAsset = await assetService.createAsset(assetData)
          set(state => ({
            assets: [newAsset.data, ...state.assets]
          }))
        } catch (error) {
          set({ error: error.message })
        }
      },

      // ... 其他动作
    }),
    { name: 'asset-store' }
  )
)
```

## 测试规范

### 1. 后端测试

#### 单元测试

```python
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.main import app
from src.database import get_db
from src.crud.asset import asset_crud
from src.schemas.asset import AssetCreate

client = TestClient(app)

class TestAssetAPI:
    """资产API测试类"""

    def test_create_asset_success(self, db_session: Session):
        """测试成功创建资产"""
        asset_data = {
            "property_name": "测试物业",
            "address": "测试地址",
            "ownership_status": "已确权",
            "property_nature": "经营性"
        }

        response = client.post("/api/v1/assets", json=asset_data)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["property_name"] == asset_data["property_name"]

    def test_create_asset_invalid_data(self):
        """测试创建资产时数据无效"""
        invalid_data = {
            "property_name": "",  # 空名称
            "address": "测试地址"
        }

        response = client.post("/api/v1/assets", json=invalid_data)

        assert response.status_code == 422

    def test_get_asset_by_id_not_found(self):
        """测试获取不存在的资产"""
        fake_id = "550e8400-e29b-41d4-a716-446655440000"
        response = client.get(f"/api/v1/assets/{fake_id}")

        assert response.status_code == 404
```

#### 集成测试

```python
import pytest
from httpx import AsyncClient

from src.main import app

@pytest.mark.asyncio
async def test_excel_import_flow():
    """测试Excel导入完整流程"""

    # 1. 上传文件
    with open("test_data.xlsx", "rb") as f:
        response = await client.post(
            "/api/v1/excel/import",
            files={"file": ("test.xlsx", f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
        )

    assert response.status_code == 200

    # 2. 检查导入结果
    result = response.json()
    assert result["success"] is True
    assert result["total"] > 0

    # 3. 验证数据已导入数据库
    assets_response = await client.get("/api/v1/assets")
    assert len(assets_response.json()["data"]["items"]) > 0
```

### 2. 前端测试

#### 组件测试

```typescript
import React from 'react'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { AssetList } from '@/components/assets/AssetList'
import { assetService } from '@/services/assetService'

// Mock API服务
jest.mock('@/services/assetService')
const mockAssetService = assetService as jest.Mocked<typeof assetService>

describe('AssetList', () => {
  const mockAssets = [
    {
      id: '1',
      property_name: '测试物业1',
      address: '测试地址1',
      ownership_status: '已确权' as const
    },
    {
      id: '2',
      property_name: '测试物业2',
      address: '测试地址2',
      ownership_status: '未确权' as const
    }
  ]

  beforeEach(() => {
    jest.clearAllMocks()
  })

  test('renders asset list correctly', async () => {
    mockAssetService.getAssets.mockResolvedValue({
      data: { items: mockAssets, total: 2 }
    })

    render(<AssetList />)

    await waitFor(() => {
      expect(screen.getByText('测试物业1')).toBeInTheDocument()
      expect(screen.getByText('测试物业2')).toBeInTheDocument()
    })
  })

  test('calls onAssetSelect when asset is clicked', async () => {
    const mockOnAssetSelect = jest.fn()
    mockAssetService.getAssets.mockResolvedValue({
      data: { items: mockAssets, total: 2 }
    })

    render(<AssetList onAssetSelect={mockOnAssetSelect} />)

    await waitFor(() => {
      expect(screen.getByText('测试物业1')).toBeInTheDocument()
    })

    await userEvent.click(screen.getByText('测试物业1'))
    expect(mockOnAssetSelect).toHaveBeenCalledWith(mockAssets[0])
  })

  test('displays error message when API call fails', async () => {
    mockAssetService.getAssets.mockRejectedValue(new Error('API错误'))

    render(<AssetList />)

    await waitFor(() => {
      expect(screen.getByText(/加载资产列表失败/)).toBeInTheDocument()
    })
  })
})
```

#### E2E测试

```typescript
import { test, expect } from '@playwright/test'

test.describe('Asset Management', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/assets')
  })

  test('should create new asset', async ({ page }) => {
    // 点击创建按钮
    await page.click('[data-testid="create-asset-button"]')

    // 填写表单
    await page.fill('[data-testid="property-name-input"]', '测试物业')
    await page.fill('[data-testid="address-input"]', '测试地址')
    await page.selectOption('[data-testid="ownership-status-select"]', '已确权')

    // 提交表单
    await page.click('[data-testid="submit-button"]')

    // 验证成功消息
    await expect(page.locator('[data-testid="success-message"]')).toBeVisible()

    // 验证新资产出现在列表中
    await expect(page.locator('text=测试物业')).toBeVisible()
  })

  test('should search assets', async ({ page }) => {
    // 输入搜索关键词
    await page.fill('[data-testid="search-input"]', '测试')
    await page.click('[data-testid="search-button"]')

    // 验证搜索结果
    await expect(page.locator('[data-testid="asset-row"]')).toHaveCount(2)
  })
})
```

## 部署规范

### 1. 环境配置

#### 开发环境

```bash
# 后端环境变量
DEV_MODE=true
DATABASE_URL=sqlite:///./data/land_property.db
LOG_LEVEL=debug
CORS_ORIGINS=["http://localhost:5173"]

# 前端环境变量
VITE_API_BASE_URL=http://localhost:8002/api/v1
VITE_API_TIMEOUT=30000
```

#### 生产环境

```bash
# 后端环境变量
DATABASE_URL=postgresql://user:password@localhost:5432/zcgl
REDIS_URL=redis://localhost:6379/0
LOG_LEVEL=info
CORS_ORIGINS=["https://zcgl.example.com"]
SECRET_KEY=your-secret-key

# 前端环境变量
VITE_API_BASE_URL=https://api.zcgl.example.com/api/v1
```

### 2. Docker部署

#### Dockerfile (后端)

```dockerfile
FROM python:3.12-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# 安装Python依赖
COPY pyproject.toml ./
RUN pip install --no-cache-dir -e .

# 复制应用代码
COPY src/ ./src/

# 创建非root用户
RUN useradd --create-home --shell /bin/bash app
USER app

# 健康检查
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8002/health || exit 1

EXPOSE 8002

CMD ["uv", "run", "python", "run_prod.py"]
```

#### Docker Compose

```yaml
version: '3.8'

services:
  backend:
    build: ./backend
    ports:
      - "8002:8002"
    environment:
      - DATABASE_URL=postgresql://zcgl:password@db:5432/zcgl
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - db
      - redis
    volumes:
      - ./backend/data:/app/data

  frontend:
    build: ./frontend
    ports:
      - "80:80"
    depends_on:
      - backend

  db:
    image: postgres:15
    environment:
      - POSTGRES_DB=zcgl
      - POSTGRES_USER=zcgl
      - POSTGRES_PASSWORD=password
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data

volumes:
  postgres_data:
  redis_data:
```

## 工具和自动化

### 1. API工具

```bash
# 生成API文档
python -m src.cli.api_tools docs

# 检查API一致性
python -m src.cli.api_tools check --severity high

# 分析API质量
python -m src.cli.api_tools analyze
```

### 2. 代码质量检查

```bash
# 后端代码检查
uv run ruff check src/
uv run mypy src/
uv run python -m pytest tests/ -v --cov=src

# 前端代码检查
npm run lint
npm run type-check
npm test
```

### 3. CI/CD Pipeline

```yaml
name: CI/CD Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  test-backend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.12'
      - name: Install dependencies
        run: |
          cd backend
          uv sync
      - name: Run tests
        run: |
          cd backend
          uv run python -m pytest tests/ -v --cov=src
      - name: Check API consistency
        run: |
          cd backend
          python -m src.cli.api_tools check --severity high

  test-frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Node.js
        uses: actions/setup-node@v3
        with:
          node-version: '18'
      - name: Install dependencies
        run: |
          cd frontend
          npm ci
      - name: Run tests
        run: |
          cd frontend
          npm test
      - name: Build
        run: |
          cd frontend
          npm run build

  deploy:
    needs: [test-backend, test-frontend]
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    steps:
      - name: Deploy to production
        run: |
          echo "Deploy to production"
```

## 最佳实践

### 1. 性能优化

- **数据库查询**: 使用适当的索引，避免N+1查询
- **API响应**: 实现分页和字段筛选
- **前端渲染**: 使用虚拟滚动和懒加载
- **缓存策略**: 合理使用Redis缓存

### 2. 安全实践

- **输入验证**: 严格验证所有用户输入
- **SQL注入防护**: 使用ORM参数化查询
- **XSS防护**: 转义用户输入内容
- **CSRF防护**: 使用CSRF令牌
- **权限控制**: 实现细粒度的权限管理

### 3. 错误处理

- **统一错误格式**: 标准化错误响应结构
- **详细日志记录**: 记录关键操作和错误信息
- **用户友好提示**: 提供清晰的错误消息
- **优雅降级**: 处理服务不可用情况

### 4. 监控和日志

- **应用监控**: 监控API响应时间和错误率
- **日志聚合**: 集中管理和分析日志
- **性能指标**: 跟踪关键业务指标
- **告警机制**: 及时发现和响应问题

---

本规范文档将根据项目发展持续更新和完善。所有开发人员应严格遵守这些规范，以确保代码质量和系统的可维护性。