# 后端开发指南

## 📋 Purpose
本文档详细说明土地物业管理系统的后端开发技术栈、架构设计、开发规范和最佳实践。

## 🎯 Scope
- 后端技术栈和项目结构
- API 开发规范
- 数据库模型和 CRUD 操作
- 服务层设计
- 认证和权限控制
- 异步编程和性能优化
- 测试和调试
- 常见问题解决

## ✅ Status
**当前状态**: Active (2026-02-04 更新)
**适用版本**: v2.0.0
**技术栈**: FastAPI + Python 3.12 + SQLAlchemy 2.0 + Pydantic v2 + PostgreSQL

---

## 🏗️ 技术架构概述

### 技术栈

| 类别 | 技术 | 版本 | 用途 |
|------|------|------|------|
| **框架** | FastAPI | 0.104+ | Web 框架 |
| **语言** | Python | 3.12+ | 编程语言 |
| **ASGI 服务器** | Uvicorn | 0.38+ | 运行服务器 |
| **ORM** | SQLAlchemy | 2.0+ | 数据库 ORM |
| **数据库驱动 (sync)** | psycopg | 3.2+ | PostgreSQL 同步驱动 |
| **数据库驱动 (async)** | asyncpg | 0.31+ | AsyncSession 异步驱动 |
| **数据验证** | Pydantic | 2.12+ | 数据验证 |
| **数据库迁移** | Alembic | 1.17+ | 数据库迁移 |
| **认证** | Python-JOSE | 3.5+ | JWT 认证 |
| **密码哈希** | Passlib | 1.7+ | 密码加密 |
| **缓存** | Redis | 7.0+ | 缓存层 |
| **PDF 处理** | LLM Vision API（Qwen/DeepSeek/GLM）, PyMuPDF（优先）, pdf2image（回退） | - , 1.24+ | 文档处理 |
| **数据处理** | Pandas | 2.0+ | 数据分析 |

**证据来源**: `backend/pyproject.toml`

### 项目结构

```
backend/
├── src/
│   ├── api/                # API 路由
│   │   └── v1/            # API v1 版本
│   │       ├── auth.py    # 认证接口
│   │       ├── assets.py # 资产接口
│   │       ├── analytics.py # 分析接口
│   │       └── ...
│   ├── core/              # 核心功能
│   │   ├── config.py     # 配置管理
│   │   ├── security.py   # 安全相关
│   │   ├── router_registry.py # 路由注册
│   │   └── ...
│   ├── crud/              # CRUD 操作
│   │   ├── base.py       # 基础 CRUD 类
│   │   ├── user.py       # 用户 CRUD
│   │   ├── asset.py      # 资产 CRUD
│   │   └── ...
│   ├── models/            # 数据库模型
│   │   ├── user.py       # 用户模型
│   │   ├── asset.py      # 资产模型
│   │   └── ...
│   ├── schemas/           # Pydantic 模型
│   │   ├── auth.py       # 认证 Schema
│   │   ├── asset.py      # 资产 Schema
│   │   └── ...
│   ├── services/          # 业务逻辑
│   │   ├── auth_service.py # 认证服务
│   │   ├── asset_service.py # 资产服务
│   │   ├── document/      # PDF 处理
│   │   └── ...
│   ├── middleware/        # 中间件
│   │   ├── auth.py       # 认证中间件
│   │   ├── cors.py       # CORS 中间件
│   │   └── ...
│   ├── utils/             # 工具函数
│   ├── constants/         # 常量定义
│   ├── database.py        # 数据库配置
│   ├── exceptions.py      # 自定义异常
│   └── main.py           # 应用入口
├── tests/                 # 测试文件
├── alembic/              # 数据库迁移
├── scripts/              # 工具脚本
├── pyproject.toml        # 项目配置
└── run_dev.py           # 开发服务器
```

**证据来源**: `backend/src/` 目录结构

---

## 🚀 快速开始

### 开发环境设置

```bash
# 1. 进入后端目录
cd backend

# 2. 创建虚拟环境
python -m venv venv

# 3. 激活虚拟环境
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# 4. 安装依赖
pip install -e .

# 5. 安装开发依赖
pip install -e ".[dev]"

# 可选：PDF 处理基础依赖（如需 PDF 解析/分析）
pip install -e ".[pdf-basic]"

# 6. 配置数据库并启动开发服务器
alembic upgrade head
python run_dev.py
```

> 提示：确保 `python` 来自虚拟环境（如 `.venv` / `venv`），可用 `python -c "import sys; print(sys.executable)"` 检查，避免系统 Python 缺失依赖。

### PDF 渲染后端策略

- `backend/src/services/document/pdf_to_images.py` 采用 **PyMuPDF 优先** 的 PDF 渲染路径。
- 当 PyMuPDF 不可用时，自动回退到 `pdf2image`。
- 若两者均不可用，将抛出明确错误：`No PDF rendering backend available. Install pymupdf or pdf2image.`。
- 建议在测试/生产环境至少安装一种渲染后端，避免文档提取流程在预处理阶段失败。

### 开发命令

```bash
# 启动开发服务器
python run_dev.py              # 端口 8002，热重载

# 完整功能服务器
python start_complete_backend.py

# 代码质量
ruff check .                    # 代码检查
ruff format .                   # 代码格式化
mypy src                        # 类型检查
bandit -r src                   # 安全扫描

# 测试
pytest                          # 运行所有测试
pytest --cov=src               # 带覆盖率
pytest -m unit                 # 单元测试
pytest -m integration          # 集成测试
pytest -m slow                 # 慢速测试

# 数据库迁移
alembic revision --autogenerate -m "描述"
alembic upgrade head
```

---

## 📡 API 开发规范

### API 端点结构

```python
# src/api/v1/assets.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from ...database import get_async_db
from ...schemas.asset import AssetResponse, AssetCreate, AssetUpdate
from ...services.asset_service import AssetService
from ...middleware.auth import get_current_user
from ...models.user import User

router = APIRouter(prefix="/assets", tags=["资产管理"])

@router.get("", response_model=List[AssetResponse])
async def get_assets(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取资产列表

    - **skip**: 跳过的记录数
    - **limit**: 返回的最大记录数
    - **返回**: 资产列表
    """
    service = AssetService(db)
    assets = await service.get_assets(skip=skip, limit=limit)
    return assets

@router.post("", response_model=AssetResponse, status_code=status.HTTP_201_CREATED)
async def create_asset(
    data: AssetCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """
    创建新资产

    - **data**: 资产数据
    - **返回**: 创建的资产
    """
    service = AssetService(db)
    try:
        asset = await service.create_asset(data, current_user.id)
        return asset
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.get("/{asset_id}", response_model=AssetResponse)
async def get_asset(
    asset_id: str,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """获取单个资产详情"""
    service = AssetService(db)
    asset = await service.get_asset(asset_id)
    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="资产不存在"
        )
    return asset
```

### 请求/响应 Schema

```python
# src/schemas/asset.py
from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import datetime

class AssetBase(BaseModel):
    """资产基础 Schema"""
    property_name: str = Field(..., min_length=1, max_length=200, description="资产名称")
    address: str = Field(..., min_length=1, description="资产地址")
    ownership_status: str = Field(..., description="权属状态")
    property_nature: str = Field(..., description="资产性质")
    usage_status: str = Field(..., description="使用状态")

    @field_validator('ownership_status')
    @classmethod
    def validate_ownership_status(cls, v):
        valid_statuses = ['自持', '租赁', '合作', '其他']
        if v not in valid_statuses:
            raise ValueError(f'权属状态必须是: {", ".join(valid_statuses)}')
        return v

class AssetCreate(AssetBase):
    """创建资产 Schema"""
    land_area: Optional[float] = Field(None, ge=0, description="土地面积")
    building_area: Optional[float] = Field(None, ge=0, description="建筑面积")

class AssetUpdate(BaseModel):
    """更新资产 Schema（所有字段可选）"""
    property_name: Optional[str] = Field(None, min_length=1, max_length=200)
    address: Optional[str] = None
    ownership_status: Optional[str] = None
    version: Optional[int] = Field(None, description="版本号(乐观锁)")
    # ... 其他字段

class AssetResponse(AssetBase):
    """资产响应 Schema"""
    id: str
    created_at: datetime
    updated_at: datetime
    created_by: Optional[str] = None

    class Config:
        from_attributes = True  # Pydantic v2
```

### 统一响应格式

```python
# src/core/response_handler.py
from fastapi import status
from typing import Any, Optional

def success_response(
    data: Any = None,
    message: str = "操作成功",
    code: str = "SUCCESS"
):
    """成功响应"""
    return {
        "success": True,
        "data": data,
        "message": message,
        "code": code
    }

def error_response(
    detail: str,
    code: str = "ERROR",
    status_code: int = status.HTTP_400_BAD_REQUEST
):
    """错误响应"""
    raise HTTPException(
        status_code=status_code,
        detail={
            "success": False,
            "error": {
                "code": code,
                "message": detail
            }
        }
    )
```

**证据来源**: `backend/src/api/v1/`, `backend/src/schemas/`

---

## 🗄️ 数据库模型和 CRUD

### 数据库模型定义

```python
# src/models/asset.py
from sqlalchemy import Column, String, Float, DateTime, Text, Enum as SQLEnum
from sqlalchemy.orm import relationship
from datetime import datetime

from ...database import Base

class Asset(Base):
    """资产模型"""
    __tablename__ = "assets"

    # 主键
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    # 基本信息（58字段中的核心字段）
    property_name = Column(String(200), nullable=False, index=True, comment="资产名称")
    address = Column(String(500), nullable=False, comment="资产地址")
    ownership_status = Column(SQLEnum('自持', '租赁', '合作', '其他'), nullable=False, comment="权属状态")
    property_nature = Column(String(50), comment="资产性质")
    usage_status = Column(String(50), comment="使用状态")

    # 面积信息
    land_area = Column(Float, comment="土地面积(㎡)")
    building_area = Column(Float, comment="建筑面积(㎡)")
    rentable_area = Column(Float, comment="可租面积(㎡)")
    rented_area = Column(Float, comment="已租面积(㎡)")
    occupancy_rate = Column(Float, comment="出租率(%)")

    # 财务信息
    annual_income = Column(Float, comment="年收入")
    annual_expense = Column(Float, comment="年支出")
    net_income = Column(Float, comment="净收入")

    # 元数据
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(String, comment="创建人ID")

    # 关系
    ownerships = relationship("Ownership", back_populates="asset")
    contracts = relationship("RentContract", back_populates="asset")

    def __repr__(self):
        return f"<Asset(id={self.id}, name={self.property_name})>"
```

### CRUD 基类

```python
# src/crud/base.py
from typing import Generic, TypeVar, Type, Optional, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import Base

ModelType = TypeVar("ModelType", bound=Base)
CreateSchemaType = TypeVar("CreateSchemaType")
UpdateSchemaType = TypeVar("UpdateSchemaType")

class CRUDBase(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    """CRUD 基类（异步）"""

    def __init__(self, model: Type[ModelType]):
        self.model = model

    async def get_async(self, db: AsyncSession, id: str) -> Optional[ModelType]:
        """通过 ID 获取单个记录"""
        result = await db.execute(select(self.model).where(self.model.id == id))
        return result.scalars().first()

    async def get_multi_async(
        self, db: AsyncSession, skip: int = 0, limit: int = 100
    ) -> List[ModelType]:
        """获取多条记录（分页）"""
        result = await db.execute(select(self.model).offset(skip).limit(limit))
        return list(result.scalars().all())

    async def create_async(
        self, db: AsyncSession, obj_in: CreateSchemaType
    ) -> ModelType:
        """创建新记录"""
        obj_in_data = obj_in.model_dump() if hasattr(obj_in, 'model_dump') else obj_in.dict()
        db_obj = self.model(**obj_in_data)
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def update_async(
        self,
        db: AsyncSession,
        db_obj: ModelType,
        obj_in: UpdateSchemaType
    ) -> ModelType:
        """更新记录"""
        obj_data = obj_in.model_dump(exclude_unset=True) if hasattr(obj_in, 'model_dump') else obj_in.dict(exclude_unset=True)
        for field, value in obj_data.items():
            setattr(db_obj, field, value)
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def delete_async(self, db: AsyncSession, id: str) -> ModelType:
        """删除记录"""
        obj = await self.get_async(db, id)
        await db.delete(obj)
        await db.commit()
        return obj
```

### 具体 CRUD 实现

```python
# src/crud/asset.py
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.asset import Asset
from ..schemas.asset import AssetCreate, AssetUpdate
from .base import CRUDBase

class AssetCRUD(CRUDBase[Asset, AssetCreate, AssetUpdate]):
    """资产 CRUD 操作"""

    async def search_async(
        self,
        db: AsyncSession,
        keyword: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[Asset]:
        """搜索资产"""
        stmt = (
            select(Asset)
            .where(Asset.property_name.contains(keyword))
            .offset(skip)
            .limit(limit)
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def get_by_ownership_status_async(
        self,
        db: AsyncSession,
        status: str
    ) -> List[Asset]:
        """按权属状态获取资产"""
        stmt = select(Asset).where(Asset.ownership_status == status)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def calculate_occupancy_rate_async(
        self, db: AsyncSession, asset_id: str
    ) -> Optional[float]:
        """计算出租率"""
        asset = await self.get_async(db, asset_id)
        if asset and asset.rentable_area and asset.rented_area:
            return (asset.rented_area / asset.rentable_area) * 100
        return None

# 创建单例实例
asset_crud = AssetCRUD(Asset)
```

**证据来源**: `backend/src/crud/`, `backend/src/models/`

---

## 🔐 认证和权限控制

> 注意：历史遗留 `SecurityService` 已移除，不再提供或导出。  
> 如需密码哈希与强度校验，请使用 `backend/src/services/core/password_service.py`；  
> 如需认证与令牌逻辑，请使用 `backend/src/services/core/authentication_service.py`。

### JWT 认证实现

```python
# src/services/auth_service.py
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.config import settings

# 密码哈希上下文
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class AuthService:
    """认证服务"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.secret_key = settings.SECRET_KEY
        self.algorithm = settings.ALGORITHM

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """验证密码"""
        return pwd_context.verify(plain_password, hashed_password)

    def get_password_hash(self, password: str) -> str:
        """哈希密码"""
        return pwd_context.hash(password)

    def create_access_token(self, data: Dict, expires_delta: Optional[timedelta] = None) -> str:
        """创建访问令牌"""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.now(UTC).replace(tzinfo=None) + expires_delta
        else:
            expire = datetime.now(UTC).replace(tzinfo=None) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

        to_encode.update({"exp": expire, "sub": "access"})
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt

    def create_refresh_token(self, data: Dict) -> str:
        """创建刷新令牌"""
        to_encode = data.copy()
        expire = datetime.now(UTC).replace(tzinfo=None) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        to_encode.update({"exp": expire, "sub": "refresh"})
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt

    def decode_token(self, token: str) -> Optional[Dict[str, Any]]:
        """解码令牌"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except JWTError:
            return None
```

### 依赖注入认证

```python
# src/middleware/auth.py
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_async_db
from ..models.user import User
from ..crud.user import user_crud

security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_async_db)
) -> User:
    """获取当前认证用户"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无效的认证凭据",
        headers={"WWW-Authenticate": "Bearer"},
    )

    token = credentials.credentials
    auth_service = AuthService(db)
    payload = auth_service.decode_token(token)

    if payload is None or payload.get("sub") != "access":
        raise credentials_exception

    user_id: str = payload.get("sub")
    user = await user_crud.get_async(db, user_id)

    if user is None:
        raise credentials_exception

    return user

async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """获取当前活跃用户"""
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="用户未激活")
    return current_user

async def require_admin(
    current_user: User = Depends(get_current_active_user)
) -> User:
    """要求管理员权限"""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理员权限"
        )
    return current_user
```

### 权限检查装饰器

```python
# src/decorators/permissions.py
from functools import wraps
from typing import Callable
from fastapi import HTTPException, status

def require_permission(resource: str, action: str):
    """权限检查装饰器"""
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, current_user: User, **kwargs):
            # 检查用户是否有相应权限
            has_permission = any(
                p.resource == resource and p.action == action
                for p in current_user.permissions
            )

            if not has_permission:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"缺少权限: {resource}.{action}"
                )

            return await func(*args, current_user=current_user, **kwargs)
        return wrapper
    return decorator

# 使用示例
@router.delete("/{asset_id}")
@require_permission("assets", "delete")
async def delete_asset(
    asset_id: str,
    current_user: User = Depends(get_current_user)
):
    # ... 删除逻辑
    pass
```

**证据来源**: `backend/src/middleware/auth.py`, `backend/src/services/auth_service.py`

---

## ⚡ 异步编程和性能

### 异步端点

```python
# 使用 async/await
@router.get("/assets")
async def get_assets_async(db: AsyncSession = Depends(get_async_db)):
    """异步获取资产列表"""
    # SQLAlchemy 2.0 支持异步
    result = await db.execute(select(Asset).limit(100))
    assets = result.scalars().all()
    return assets
```

### Redis 缓存

```python
# src/services/cache_service.py
from typing import Optional, Any
import json
import redis.asyncio as redis
from ..core.config import settings

class CacheService:
    """Redis 缓存服务"""

    def __init__(self):
        self.redis = redis.Redis(
            host=settings.REDIS_HOST or "localhost",
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            password=settings.REDIS_PASSWORD,
            encoding="utf-8",
            decode_responses=True,
        )

    async def get(self, key: str) -> Optional[Any]:
        """获取缓存"""
        value = await self.redis.get(key)
        if value:
            return json.loads(value)
        return None

    async def set(
        self,
        key: str,
        value: Any,
        expire: int = 3600
    ) -> None:
        """设置缓存"""
        await self.redis.setex(
            key,
            expire,
            json.dumps(value, ensure_ascii=False)
        )

    async def delete(self, key: str) -> None:
        """删除缓存"""
        await self.redis.delete(key)

    async def invalidate_pattern(self, pattern: str) -> None:
        """批量删除缓存"""
        keys = await self.redis.keys(f"{pattern}*")
        if keys:
            await self.redis.delete(*keys)

# 使用缓存
cache_service = CacheService()

@router.get("/assets/{asset_id}")
async def get_asset_cached(asset_id: str, db: AsyncSession = Depends(get_async_db)):
    # 先查缓存
    cache_key = f"asset:{asset_id}"
    cached = await cache_service.get(cache_key)

    if cached:
        return cached

    # 缓存未命中，查数据库
    asset = await asset_crud.get_async(db, asset_id)

    if asset:
        # 写入缓存
        await cache_service.set(cache_key, asset.__dict__, expire=300)

    return asset
```

**证据来源**: `backend/src/core/config.py`, `backend/src/services/`

---

## 🧪 测试

### 测试结构

```
tests/
├── __init__.py
├── conftest.py              # pytest 配置
├── test_api/                # API 测试
│   ├── test_auth.py
│   ├── test_assets.py
│   └── ...
├── test_services/            # 服务测试
├── test_crud/                # CRUD 测试
└── test_utils/               # 工具测试
```

### API 测试示例

```python
# tests/test_api/test_assets.py
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.main import app
from src.database import get_async_db
from src.models.base import Base

# 测试数据库
SQLALCHEMY_TEST_DATABASE_URL = "postgresql+psycopg://user:password@localhost:5432/zcgl_test"
# SQLite 已移除，测试环境请使用 PostgreSQL
engine = create_async_engine(SQLALCHEMY_TEST_DATABASE_URL, pool_pre_ping=True)
TestingSessionLocal = async_sessionmaker(
    autocommit=False, autoflush=False, bind=engine, expire_on_commit=False
)

@pytest.fixture(scope="session", autouse=True)
async def prepare_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest.fixture
async def db_session() -> AsyncSession:
    """测试数据库 fixture"""
    async with TestingSessionLocal() as session:
        yield session

@pytest.fixture
async def client(db_session: AsyncSession):
    """测试客户端 fixture"""
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_async_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://127.0.0.1") as client:
        yield client
    app.dependency_overrides.clear()

class TestAssetsAPI:
    """资产 API 测试"""

    @pytest.mark.asyncio
    async def test_create_asset(self, client: AsyncClient):
        """测试创建资产"""
        response = await client.post(
            "/api/v1/assets",
            json={
                "property_name": "测试资产",
                "address": "测试地址",
                "ownership_status": "自持",
                "property_nature": "办公楼",
                "usage_status": "在用"
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert data["data"]["property_name"] == "测试资产"

    @pytest.mark.asyncio
    async def test_get_assets(self, client: AsyncClient):
        """测试获取资产列表"""
        response = await client.get("/api/v1/assets")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data["data"], list)

    @pytest.mark.asyncio
    async def test_get_asset_not_found(self, client: AsyncClient):
        """测试获取不存在的资产"""
        response = await client.get("/api/v1/assets/nonexistent")
        assert response.status_code == 404
```

### 运行测试

```bash
# 运行所有测试
pytest

# 运行特定测试文件
pytest tests/test_api/test_assets.py

# 运行带覆盖率
pytest --cov=src --cov-report=html

# 运行特定标记的测试
pytest -m unit          # 单元测试
pytest -m integration   # 集成测试
pytest -m slow          # 慢速测试
```

**证据来源**: `backend/pyproject.toml`

---

## 🐛 调试技巧

### 日志配置

```python
# src/core/logging.py
import logging
import sys
from pathlib import Path

def setup_logging():
    """配置日志"""
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    # 配置格式
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # 文件处理器
    file_handler = logging.FileHandler(log_dir / "app.log")
    file_handler.setFormatter(formatter)

    # 控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)

    # 配置根日志记录器
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    return root_logger
```

### 调试端点

```python
# src/api/v1/debug.py (仅开发环境)
from fastapi import APIRouter
from ..core.config import settings

router = APIRouter(prefix="/debug", tags=["调试"])

@router.get("/config")
async def get_debug_config():
    """获取配置信息（仅开发环境）"""
    if not settings.DEBUG:
        raise HTTPException(status_code=404, detail="仅在开发环境可用")

    return {
        "database_url": settings.DATABASE_URL,
        "redis": {
            "enabled": settings.REDIS_ENABLED,
            "host": settings.REDIS_HOST,
            "port": settings.REDIS_PORT,
            "db": settings.REDIS_DB,
        },
        "cors_origins": settings.CORS_ORIGINS,
        # ... 其他配置
    }
```

---

## 🚨 常见问题

### Q1: 数据库连接失败
**问题**: `sqlalchemy.exc.OperationalError: could not connect to server`
**解决**:
```bash
# 检查 DATABASE_URL 配置
echo $DATABASE_URL

# 确认 PostgreSQL 服务运行
pg_isready -h localhost -p 5432

# 检查账号和密码
psql "$DATABASE_URL" -c "SELECT 1;"
```

### Q2: 导入错误
**问题**: `ModuleNotFoundError: No module named 'xxx'`
**解决**:
```bash
# 重新安装依赖
pip install -e .

# 检查虚拟环境
python -c "import sys; print(sys.executable)"

# Windows:
where python
# macOS/Linux:
which python

# 检查 Python 路径
python -c "import sys; print(sys.path)"
```

### Q3: 类型检查错误
**问题**: `mypy` 报错
**解决**:
```bash
# 更新类型存根
pip install types-requests

# 配置 mypy.ini
# 或使用 pyright (VS Code 默认)
pip install pyright
```

### Q4: Alembic 迁移失败
**问题**: `alembic.util.exc.CommandError: Target database is not up to date`
**解决**:
```bash
# 查看当前版本
alembic current

# 查看迁移历史
alembic history

# 标记为最新版本
alembic stamp head

# 重新运行迁移
alembic upgrade head
```

### Q5: asyncpg 导入失败 / AsyncSession 运行时报错
**问题**: `ModuleNotFoundError: No module named 'asyncpg'` 或 `ImportError: asyncpg`
**解决**:
```bash
# 确认使用虚拟环境
python -c "import sys; print(sys.executable)"

# 安装后端依赖（包含 asyncpg）
pip install -e .
```

### Q6: 时间戳写入报错 (asyncpg DataError)
**问题**: `asyncpg.exceptions.DataError` 或 `can't subtract offset-naive and offset-aware datetimes`
**解决**:
```python
from datetime import datetime, timezone

# 写库字段使用 naive UTC
naive_utc = datetime.now(UTC).replace(tzinfo=None)

# 如果已有带时区时间
naive_utc = aware_dt.astimezone(timezone.utc).replace(tzinfo=None)
```

---

## 📋 开发检查清单

### 开发前
- [ ] 虚拟环境已激活
- [ ] 依赖已安装
- [ ] 数据库已初始化
- [ ] 环境变量已配置

### 开发中
- [ ] 遵循代码规范 (Ruff)
- [ ] 添加类型注解
- [ ] 编写文档字符串
- [ ] 添加错误处理
- [ ] 考虑异步操作

### 提交前
- [ ] 代码通过 Ruff 检查
- [ ] 类型检查通过
- [ ] 测试通过
- [ ] 更新文档
- [ ] 运行数据库迁移

---

## 🔗 相关链接

### 文档
- [环境配置指南](environment-setup.md)
- [数据库指南](database.md)
- [认证 API](../integrations/auth-api.md)
- [开发工作流程](development-workflow.md)

### 外部资源
- [FastAPI 文档](https://fastapi.tiangolo.com/)
- [SQLAlchemy 文档](https://docs.sqlalchemy.org/)
- [Pydantic 文档](https://docs.pydantic.dev/)
- [Pytest 文档](https://docs.pytest.org/)

### 代码位置
- [后端源码](../../backend/src/)
- [API 路由](../../backend/src/api/v1/)
- [数据模型](../../backend/src/models/)
- [服务层](../../backend/src/services/)

## 📋 Changelog

### 2025-12-23 v1.0.0 - 初始版本
- ✨ 新增：后端开发完整指南
- 🏗️ 新增：技术架构和项目结构说明
- 📡 新增：API 开发规范和示例
- 🗄️ 新增：数据库模型和 CRUD 操作详解
- 🔐 新增：认证和权限控制实现
- ⚡ 新增：异步编程和性能优化
- 🧪 新增：测试和调试指南
- 🚨 新增：常见问题解决

## 🔍 Evidence Sources
- **项目配置**: `backend/pyproject.toml`
- **应用入口**: `backend/src/main.py`
- **API 路由**: `backend/src/api/v1/`
- **数据模型**: `backend/src/models/`
- **CRUD 层**: `backend/src/crud/`
- **服务层**: `backend/src/services/`
- **中间件**: `backend/src/middleware/`
