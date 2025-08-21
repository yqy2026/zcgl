# 设计文档

## 概述

土地物业资产管理应用是一个基于Web的单页应用（SPA），采用现代前端技术栈构建。应用采用分阶段开发策略，第一阶段专注于资产信息管理的核心功能，为后续功能扩展奠定坚实基础。

## 技术架构

### 前端架构
- **框架**: React 18 + TypeScript
- **状态管理**: Zustand（轻量级状态管理）
- **UI组件库**: Ant Design（提供丰富的企业级组件）
- **路由**: React Router v7
- **表单处理**: React Hook Form + Zod（类型安全的表单验证）
- **数据获取**: TanStack Query（React Query v4）
- **样式**: Tailwind CSS + Ant Design

### 后端架构
- **语言**: CPython 3.12+
- **包管理**: uv（超快的Python包管理器）
- **框架**: FastAPI（现代、快速的Web框架）
- **数据库**: SQLite（开发阶段）/ PostgreSQL（生产环境）
- **ORM**: SQLAlchemy + Alembic（数据库迁移）
- **API设计**: RESTful API + 自动生成OpenAPI文档
- **数据验证**: Pydantic（类型安全的数据验证）
- **数据处理**: Polars（高性能数据处理，替代pandas）
- **Excel处理**: openpyxl + Polars（高性能Excel读写）
- **类型检查**: mypy（静态类型检查）
- **代码格式化**: Ruff（极快的Python linter和formatter）
- **文件存储**: 本地文件系统（开发阶段）

### 部署架构
- **开发环境**: Vite开发服务器 + FastAPI后端（uvicorn）
- **生产环境**: Docker容器化部署
- **数据备份**: 定期数据库备份机制

### 开发工具链配置
```toml
# pyproject.toml
[project]
name = "land-property-management"
version = "0.1.0"
description = "土地物业资产管理系统"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.104.0",
    "uvicorn[standard]>=0.24.0",
    "sqlalchemy>=2.0.0",
    "alembic>=1.12.0",
    "pydantic>=2.5.0",
    "polars>=0.20.0",
    "openpyxl>=3.1.0",
    "python-multipart>=0.0.6",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.4.0",
    "pytest-asyncio>=0.21.0",
    "httpx>=0.25.0",
    "mypy>=1.7.0",
    "ruff>=0.1.6",
]

[tool.ruff]
target-version = "py312"
line-length = 88
select = ["E", "F", "I", "N", "W", "UP"]
ignore = ["E501"]

[tool.ruff.format]
quote-style = "double"
indent-style = "space"

[tool.mypy]
python_version = "3.12"
strict = true
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

## 核心组件和接口

### 1. 资产信息管理模块

#### 数据模型
```typescript
interface Asset {
  id: string;
  
  // 权属信息
  ownershipEntity: string; // 权属方
  managementEntity: string; // 经营管理方
  ownershipCategory?: string; // 权属类别
  
  // 基本信息
  propertyName: string; // 物业名称
  address: string; // 所在地址
  
  // 面积信息（平方米）
  landArea?: number; // 土地面积
  actualPropertyArea: number; // 实际房产面积
  rentableArea: number; // 经营性物业可出租面积
  rentedArea: number; // 经营性物业已出租面积
  unrentedArea: number; // 经营性物业未出租面积
  nonCommercialArea: number; // 非经营物业面积
  
  // 确权和用途信息
  ownershipStatus: '已确权' | '未确权' | '部分确权'; // 是否确权
  certificatedUsage?: string; // 证载用途（商业、住宅、办公、厂房、车位等）
  actualUsage: string; // 实际用途
  businessCategory?: string; // 业态类别
  
  // 使用状态
  usageStatus: '出租' | '闲置' | '自用' | '公房' | '其他'; // 物业使用状态
  isLitigated: boolean; // 是否涉诉
  propertyNature: '经营类' | '非经营类'; // 物业性质
  
  // 经营信息
  businessModel?: string; // 经营模式
  includeInOccupancyRate?: boolean; // 是否计入出租率
  occupancyRate: string; // 出租率
  
  // 合同信息
  leaseContract?: string; // 承租合同/代理协议
  currentContractStartDate?: Date; // 现合同开始日期
  currentContractEndDate?: Date; // 现合同结束日期
  tenantName?: string; // 租户名称
  currentLeaseContract?: string; // 现租赁合同
  currentTerminalContract?: string; // 现终端出租合同
  
  // 项目信息
  wuyangProjectName?: string; // 五羊运营项目名称
  agreementStartDate?: Date; // 协议开始日期
  agreementEndDate?: Date; // 协议结束日期
  
  // 备注和说明
  description?: string; // 说明
  notes?: string; // 其他备注
  
  // 系统字段
  createdAt: Date;
  updatedAt: Date;
  version: number; // 用于变更历史跟踪
}

interface AssetHistory {
  id: string;
  assetId: string;
  changeType: 'create' | 'update' | 'delete';
  changedFields: string[];
  oldValues: Record<string, any>;
  newValues: Record<string, any>;
  changedBy: string;
  changedAt: Date;
  reason?: string;
}
```

#### API接口设计
```typescript
// 资产管理API
interface AssetAPI {
  // 获取资产列表（支持分页、搜索、筛选）
  getAssets(params: {
    page?: number;
    limit?: number;
    search?: string;
    filters?: {
      status?: string;
      usage?: string;
      location?: string;
      dateRange?: [Date, Date];
    };
    sort?: {
      field: string;
      order: 'asc' | 'desc';
    };
  }): Promise<{
    data: Asset[];
    total: number;
    page: number;
    limit: number;
  }>;

  // 获取单个资产详情
  getAsset(id: string): Promise<Asset>;

  // 创建新资产
  createAsset(asset: Omit<Asset, 'id' | 'createdAt' | 'updatedAt' | 'version'>): Promise<Asset>;

  // 更新资产信息
  updateAsset(id: string, updates: Partial<Asset>): Promise<Asset>;

  // 删除资产
  deleteAsset(id: string): Promise<void>;

  // 获取资产变更历史
  getAssetHistory(id: string): Promise<AssetHistory[]>;

  // 批量导入资产
  importAssets(file: File): Promise<{
    success: number;
    failed: number;
    errors: string[];
  }>;

  // 导出资产数据
  exportAssets(filters?: any): Promise<Blob>;
}
```

#### 前端组件结构
```
src/
├── components/
│   ├── assets/
│   │   ├── AssetList.tsx          # 资产列表组件
│   │   ├── AssetCard.tsx          # 资产卡片组件
│   │   ├── AssetForm.tsx          # 资产表单组件
│   │   ├── AssetDetail.tsx        # 资产详情组件
│   │   ├── AssetSearch.tsx        # 搜索筛选组件
│   │   ├── AssetImport.tsx        # 批量导入组件
│   │   └── AssetHistory.tsx       # 变更历史组件
│   ├── common/
│   │   ├── Layout.tsx             # 应用布局
│   │   ├── Header.tsx             # 页面头部
│   │   ├── Sidebar.tsx            # 侧边栏导航
│   │   └── LoadingSpinner.tsx     # 加载组件
│   └── ui/
│       ├── Button.tsx             # 自定义按钮
│       ├── Modal.tsx              # 模态框
│       └── Table.tsx              # 数据表格
├── pages/
│   ├── AssetListPage.tsx          # 资产列表页面
│   ├── AssetDetailPage.tsx        # 资产详情页面
│   └── AssetCreatePage.tsx        # 创建资产页面
├── hooks/
│   ├── useAssets.ts               # 资产数据钩子
│   ├── useAssetForm.ts            # 表单处理钩子
│   └── useAssetSearch.ts          # 搜索功能钩子
├── stores/
│   ├── assetStore.ts              # 资产状态管理
│   └── uiStore.ts                 # UI状态管理
├── services/
│   ├── assetService.ts            # 资产API服务
│   └── fileService.ts             # 文件处理服务
└── utils/
    ├── validation.ts              # 数据验证
    ├── formatting.ts              # 数据格式化
    └── constants.ts               # 常量定义
```

## 数据模型设计

### 数据库表结构（SQLAlchemy Models）
```python
from sqlalchemy import Column, String, Float, DateTime, Integer, Text, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

Base = declarative_base()

class Asset(Base):
    __tablename__ = "assets"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # 权属信息
    ownership_entity = Column(String, nullable=False)  # 权属方
    management_entity = Column(String)  # 经营管理方
    ownership_category = Column(String)  # 权属类别
    
    # 基本信息
    property_name = Column(String, nullable=False)  # 物业名称
    address = Column(String, nullable=False)  # 所在地址
    
    # 面积信息（平方米）
    land_area = Column(Float)  # 土地面积
    actual_property_area = Column(Float, nullable=False)  # 实际房产面积
    rentable_area = Column(Float, nullable=False)  # 经营性物业可出租面积
    rented_area = Column(Float, nullable=False)  # 经营性物业已出租面积
    unrented_area = Column(Float, nullable=False)  # 经营性物业未出租面积
    non_commercial_area = Column(Float, nullable=False)  # 非经营物业面积
    
    # 确权和用途信息
    ownership_status = Column(String, nullable=False)  # 是否确权（已确权、未确权、部分确权）
    certificated_usage = Column(String)  # 证载用途
    actual_usage = Column(String, nullable=False)  # 实际用途
    business_category = Column(String)  # 业态类别
    
    # 使用状态
    usage_status = Column(String, nullable=False)  # 物业使用状态（出租、闲置、自用、公房、其他）
    is_litigated = Column(String, nullable=False)  # 是否涉诉
    property_nature = Column(String, nullable=False)  # 物业性质（经营类、非经营类）
    
    # 经营信息
    business_model = Column(String)  # 经营模式
    include_in_occupancy_rate = Column(String)  # 是否计入出租率
    occupancy_rate = Column(String, nullable=False)  # 出租率
    
    # 合同信息
    lease_contract = Column(String)  # 承租合同/代理协议
    current_contract_start_date = Column(DateTime)  # 现合同开始日期
    current_contract_end_date = Column(DateTime)  # 现合同结束日期
    tenant_name = Column(String)  # 租户名称
    current_lease_contract = Column(String)  # 现租赁合同
    current_terminal_contract = Column(String)  # 现终端出租合同
    
    # 项目信息
    wuyang_project_name = Column(String)  # 五羊运营项目名称
    agreement_start_date = Column(DateTime)  # 协议开始日期
    agreement_end_date = Column(DateTime)  # 协议结束日期
    
    # 备注和说明
    description = Column(Text)  # 说明
    notes = Column(Text)  # 其他备注
    
    # 系统字段
    version = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关联关系
    history = relationship("AssetHistory", back_populates="asset", cascade="all, delete-orphan")
    documents = relationship("AssetDocument", back_populates="asset", cascade="all, delete-orphan")

class AssetHistory(Base):
    __tablename__ = "asset_history"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    asset_id = Column(String, ForeignKey("assets.id"), nullable=False)
    change_type = Column(String, nullable=False)
    changed_fields = Column(JSON)
    old_values = Column(JSON)
    new_values = Column(JSON)
    changed_by = Column(String, default="system")
    changed_at = Column(DateTime, default=datetime.utcnow)
    reason = Column(String)
    
    asset = relationship("Asset", back_populates="history")

class AssetDocument(Base):
    __tablename__ = "asset_documents"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    asset_id = Column(String, ForeignKey("assets.id"), nullable=False)
    file_name = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    file_size = Column(Integer, nullable=False)
    mime_type = Column(String, nullable=False)
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    
    asset = relationship("Asset", back_populates="documents")
```

### Pydantic数据模型
```python
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum

class OwnershipStatus(str, Enum):
    CONFIRMED = "已确权"
    UNCONFIRMED = "未确权"
    PARTIAL = "部分确权"

class UsageStatus(str, Enum):
    RENTED = "出租"
    VACANT = "闲置"
    SELF_USE = "自用"
    PUBLIC = "公房"
    OTHER = "其他"

class PropertyNature(str, Enum):
    COMMERCIAL = "经营类"
    NON_COMMERCIAL = "非经营类"

class AssetBase(BaseModel):
    # 权属信息
    ownership_entity: str = Field(..., description="权属方")
    management_entity: Optional[str] = Field(None, description="经营管理方")
    ownership_category: Optional[str] = Field(None, description="权属类别")
    
    # 基本信息
    property_name: str = Field(..., description="物业名称")
    address: str = Field(..., description="所在地址")
    
    # 面积信息（平方米）
    land_area: Optional[float] = Field(None, description="土地面积")
    actual_property_area: float = Field(..., description="实际房产面积")
    rentable_area: float = Field(..., description="经营性物业可出租面积")
    rented_area: float = Field(..., description="经营性物业已出租面积")
    unrented_area: float = Field(..., description="经营性物业未出租面积")
    non_commercial_area: float = Field(..., description="非经营物业面积")
    
    # 确权和用途信息
    ownership_status: OwnershipStatus = Field(..., description="是否确权")
    certificated_usage: Optional[str] = Field(None, description="证载用途")
    actual_usage: str = Field(..., description="实际用途")
    business_category: Optional[str] = Field(None, description="业态类别")
    
    # 使用状态
    usage_status: UsageStatus = Field(..., description="物业使用状态")
    is_litigated: str = Field(..., description="是否涉诉")
    property_nature: PropertyNature = Field(..., description="物业性质")
    
    # 经营信息
    business_model: Optional[str] = Field(None, description="经营模式")
    include_in_occupancy_rate: Optional[str] = Field(None, description="是否计入出租率")
    occupancy_rate: str = Field(..., description="出租率")
    
    # 合同信息
    lease_contract: Optional[str] = Field(None, description="承租合同/代理协议")
    current_contract_start_date: Optional[datetime] = Field(None, description="现合同开始日期")
    current_contract_end_date: Optional[datetime] = Field(None, description="现合同结束日期")
    tenant_name: Optional[str] = Field(None, description="租户名称")
    current_lease_contract: Optional[str] = Field(None, description="现租赁合同")
    current_terminal_contract: Optional[str] = Field(None, description="现终端出租合同")
    
    # 项目信息
    wuyang_project_name: Optional[str] = Field(None, description="五羊运营项目名称")
    agreement_start_date: Optional[datetime] = Field(None, description="协议开始日期")
    agreement_end_date: Optional[datetime] = Field(None, description="协议结束日期")
    
    # 备注和说明
    description: Optional[str] = Field(None, description="说明")
    notes: Optional[str] = Field(None, description="其他备注")

class AssetCreate(AssetBase):
    pass

class AssetUpdate(BaseModel):
    # 所有字段都是可选的，用于部分更新
    ownership_entity: Optional[str] = None
    management_entity: Optional[str] = None
    property_name: Optional[str] = None
    address: Optional[str] = None
    # ... 其他字段

class AssetResponse(AssetBase):
    id: str
    version: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
```

## 错误处理

### 前端错误处理策略
```typescript
// 全局错误边界
class ErrorBoundary extends React.Component {
  // 捕获组件渲染错误
}

// API错误处理
const handleApiError = (error: any) => {
  if (error.response?.status === 401) {
    // 处理认证错误
    redirectToLogin();
  } else if (error.response?.status === 403) {
    // 处理权限错误
    showPermissionError();
  } else if (error.response?.status >= 500) {
    // 处理服务器错误
    showServerError();
  } else {
    // 处理其他错误
    showGenericError(error.message);
  }
};

// 表单验证错误
const assetValidationSchema = z.object({
  ownershipEntity: z.string().min(1, "权属方不能为空"),
  propertyName: z.string().min(1, "物业名称不能为空"),
  address: z.string().min(1, "所在地址不能为空"),
  actualPropertyArea: z.number().positive("实际房产面积必须大于0"),
  rentableArea: z.number().min(0, "可出租面积不能为负数"),
  rentedArea: z.number().min(0, "已出租面积不能为负数"),
  unrentedArea: z.number().min(0, "未出租面积不能为负数"),
  nonCommercialArea: z.number().min(0, "非经营物业面积不能为负数"),
  ownershipStatus: z.enum(['已确权', '未确权', '部分确权']),
  actualUsage: z.string().min(1, "实际用途不能为空"),
  usageStatus: z.enum(['出租', '闲置', '自用', '公房', '其他']),
  propertyNature: z.enum(['经营类', '非经营类']),
  occupancyRate: z.string(),
  // ... 其他验证规则
});
```

### 后端错误处理
```python
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError
import logging

logger = logging.getLogger(__name__)

# 自定义异常类
class AssetNotFoundError(Exception):
    def __init__(self, asset_id: str):
        self.asset_id = asset_id
        super().__init__(f"Asset with id {asset_id} not found")

class DuplicateAssetError(Exception):
    def __init__(self, property_name: str):
        self.property_name = property_name
        super().__init__(f"Asset with name {property_name} already exists")

# 全局异常处理器
@app.exception_handler(ValidationError)
async def validation_exception_handler(request: Request, exc: ValidationError):
    return JSONResponse(
        status_code=400,
        content={
            "error": "Validation Error",
            "details": exc.errors()
        }
    )

@app.exception_handler(AssetNotFoundError)
async def asset_not_found_handler(request: Request, exc: AssetNotFoundError):
    return JSONResponse(
        status_code=404,
        content={
            "error": "Asset Not Found",
            "message": str(exc)
        }
    )

@app.exception_handler(DuplicateAssetError)
async def duplicate_asset_handler(request: Request, exc: DuplicateAssetError):
    return JSONResponse(
        status_code=409,
        content={
            "error": "Duplicate Asset",
            "message": str(exc)
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unexpected error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "message": "An unexpected error occurred"
        }
    )
```

## 测试策略

### 前端测试
- **单元测试**: Jest + React Testing Library
  - 组件渲染测试
  - 用户交互测试
  - 工具函数测试
- **集成测试**: 
  - API集成测试
  - 表单提交流程测试
- **E2E测试**: Playwright
  - 关键用户流程测试

### 后端测试
- **单元测试**: pytest + pytest-asyncio
  - API路由测试
  - 数据库操作测试
  - 业务逻辑测试
  - Pydantic模型验证测试
- **集成测试**: 
  - 数据库集成测试
  - Excel文件导入导出测试
  - FastAPI TestClient集成测试

### 测试覆盖率目标
- 单元测试覆盖率: ≥80%
- 集成测试覆盖率: ≥70%
- E2E测试覆盖关键业务流程

## 性能优化

### 前端性能优化
- **代码分割**: React.lazy + Suspense
- **虚拟滚动**: 大数据列表优化
- **缓存策略**: React Query缓存配置
- **图片优化**: 懒加载 + WebP格式
- **Bundle优化**: Tree shaking + 代码压缩

### 后端性能优化
- **数据库优化**: 
  - 索引优化
  - 查询优化
  - 连接池配置
- **缓存策略**: Redis缓存热点数据
- **分页优化**: 游标分页替代偏移分页
- **文件处理**: 流式处理大文件

### 高性能数据处理（Polars）
```python
import polars as pl
from typing import List, Dict, Any

class AssetDataProcessor:
    """使用Polars进行高性能数据处理"""
    
    @staticmethod
    def import_excel_data(file_path: str) -> pl.DataFrame:
        """从Excel文件导入数据"""
        # 使用Polars读取Excel文件
        df = pl.read_excel(
            file_path,
            sheet_name="物业总表",
            infer_schema_length=1000  # 推断更多行的数据类型
        )
        
        # 数据清洗和标准化
        df = df.with_columns([
            # 处理空值
            pl.col("权属方").fill_null("未知"),
            pl.col("经营管理方").fill_null(""),
            
            # 数据类型转换
            pl.col("土地面积\n(平方米)").cast(pl.Float64, strict=False).alias("land_area"),
            pl.col("实际房产面积\n(平方米)").cast(pl.Float64, strict=False).alias("actual_property_area"),
            
            # 日期处理
            pl.col("现合同开始日期").str.to_datetime("%Y年%m月%d日", strict=False),
            pl.col("现合同结束日期").str.to_datetime("%Y年%m月%d日", strict=False),
        ])
        
        return df
    
    @staticmethod
    def calculate_occupancy_rates(df: pl.DataFrame) -> pl.DataFrame:
        """计算出租率"""
        return df.with_columns([
            # 计算出租率
            (pl.col("rented_area") / pl.col("rentable_area") * 100)
            .round(2)
            .alias("calculated_occupancy_rate"),
            
            # 标记是否应计入出租率统计
            pl.when(pl.col("property_nature") == "经营类")
            .then(True)
            .otherwise(False)
            .alias("should_include_in_stats")
        ])
    
    @staticmethod
    def export_to_excel(df: pl.DataFrame, file_path: str) -> None:
        """导出数据到Excel"""
        df.write_excel(file_path, worksheet="资产清单")

# Excel导入导出服务
class ExcelService:
    def __init__(self):
        self.processor = AssetDataProcessor()
    
    async def import_assets_from_excel(self, file_path: str) -> Dict[str, Any]:
        """从Excel导入资产数据"""
        try:
            # 使用Polars读取和处理数据
            df = self.processor.import_excel_data(file_path)
            
            # 数据验证
            validation_errors = self._validate_data(df)
            if validation_errors:
                return {
                    "success": 0,
                    "failed": len(df),
                    "errors": validation_errors
                }
            
            # 转换为数据库模型并保存
            assets = self._convert_to_assets(df)
            success_count = await self._save_assets(assets)
            
            return {
                "success": success_count,
                "failed": len(df) - success_count,
                "errors": []
            }
            
        except Exception as e:
            return {
                "success": 0,
                "failed": 0,
                "errors": [str(e)]
            }
```

## 开发工作流

### 代码质量保证
```bash
# 使用uv管理依赖
uv add fastapi uvicorn sqlalchemy

# 类型检查
uv run mypy src/

# 代码格式化和检查
uv run ruff check src/
uv run ruff format src/

# 运行测试
uv run pytest tests/ -v --cov=src/

# 启动开发服务器
uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Git Hooks配置
```bash
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.1.6
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format
  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.7.0
    hooks:
      - id: mypy
        additional_dependencies: [types-all]
```

## 安全考虑

### 数据安全
- **输入验证**: 所有用户输入进行严格验证（Pydantic + mypy）
- **SQL注入防护**: 使用SQLAlchemy ORM参数化查询
- **XSS防护**: 输出转义和CSP策略
- **文件上传安全**: 文件类型检查和大小限制

### 访问控制
- **认证**: JWT令牌认证
- **授权**: 基于角色的访问控制（RBAC）
- **会话管理**: 安全的会话处理

### 数据备份
- **定期备份**: 每日自动数据库备份
- **备份验证**: 定期恢复测试
- **灾难恢复**: 备份恢复流程文档