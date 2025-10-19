# API优化指南

本文档详细说明了土地物业资产管理系统的API优化策略和最佳实践。

## 目录

- [API设计原则](#api设计原则)
- [缓存策略](#缓存策略)
- [响应优化](#响应优化)
- [数据库优化](#数据库优化)
- [错误处理](#错误处理)
- [安全优化](#安全优化)
- [监控与日志](#监控与日志)

## API设计原则

### RESTful设计

#### 资源命名规范
```
GET    /api/v1/assets              # 获取资产列表
POST   /api/v1/assets              # 创建资产
GET    /api/v1/assets/{id}         # 获取特定资产
PUT    /api/v1/assets/{id}         # 更新资产
DELETE /api/v1/assets/{id}         # 删除资产
```

#### HTTP状态码使用
```python
# 成功响应
200 OK          # 请求成功
201 Created     # 资源创建成功
204 No Content  # 删除成功

# 客户端错误
400 Bad Request      # 请求参数错误
401 Unauthorized     # 未授权
403 Forbidden        # 禁止访问
404 Not Found        # 资源不存在
409 Conflict         # 资源冲突
422 Unprocessable Entity  # 验证失败

# 服务器错误
500 Internal Server Error  # 服务器内部错误
503 Service Unavailable    # 服务不可用
```

### 版本控制

#### URL版本控制
```python
# 推荐：URL版本控制
/api/v1/assets
/api/v2/assets

# 可选：Header版本控制
Accept: application/vnd.api+json;version=1
```

## 缓存策略

### Redis缓存实现

#### 缓存装饰器
```python
from src.utils.cache_manager import cache_statistics, cache_assets

@cache_statistics(expire=1800)  # 30分钟缓存
async def get_statistics_summary():
    """统计数据缓存"""
    # 复杂计算逻辑
    return calculated_data

@cache_assets(expire=3600)  # 1小时缓存
async def get_asset_list(filters: dict):
    """资产列表缓存"""
    return await fetch_assets(filters)
```

#### 缓存键管理
```python
def cache_key_builder(func_name: str, **kwargs) -> str:
    """构建缓存键"""
    # 过滤敏感参数
    filtered_kwargs = {k: v for k, v in kwargs.items()
                      if k not in ['db', 'current_user']}

    # 生成唯一键
    key_parts = [func_name]
    for k, v in sorted(filtered_kwargs.items()):
        key_parts.append(f"{k}={v}")

    return ":".join(key_parts)
```

### 缓存失效策略

#### 主动失效
```python
async def update_asset(asset_id: str, data: dict):
    """更新资产时清除相关缓存"""
    # 更新数据库
    await asset_service.update(asset_id, data)

    # 清除相关缓存
    cache_mgr = await get_cache_manager()
    await cache_mgr.clear_pattern("assets:*")
    await cache_mgr.clear_pattern("statistics:*")
```

#### 定时刷新
```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler

async def refresh_statistics_cache():
    """定时刷新统计缓存"""
    cache_mgr = await get_cache_manager()
    await cache_mgr.clear_pattern("statistics:*")

scheduler = AsyncIOScheduler()
scheduler.add_job(refresh_statistics_cache, 'interval', hours=1)
scheduler.start()
```

## 响应优化

### 分页优化

#### 游标分页
```python
@router.get("/assets")
async def get_assets(
    cursor: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100)
):
    """游标分页实现"""
    if cursor:
        # 解码游标
        decoded_cursor = decode_cursor(cursor)
        query = query.filter(Asset.id > decoded_cursor)

    assets = await query.limit(limit + 1).all()

    has_next = len(assets) > limit
    if has_next:
        assets.pop()  # 移除多查询的一条
        next_cursor = encode_cursor(assets[-1].id)
    else:
        next_cursor = None

    return {
        "items": assets,
        "next_cursor": next_cursor,
        "has_next": has_next
    }
```

#### 字段选择
```python
@router.get("/assets")
async def get_assets(
    fields: Optional[str] = Query(None, description="选择返回字段")
):
    """字段选择器"""
    if fields:
        selected_fields = fields.split(',')
        assets = await query.with_entities(*selected_fields).all()
    else:
        assets = await query.all()

    return {"items": assets}
```

### 数据压缩

#### 响应压缩
```python
from fastapi.middleware.gzip import GZipMiddleware

# 启用Gzip压缩
app.add_middleware(GZipMiddleware, minimum_size=1000)

# 自定义压缩中间件
@app.middleware("http")
async def compression_middleware(request: Request, call_next):
    response = await call_next(request)

    # 检查响应大小和类型
    if (should_compress(response) and
        "gzip" in request.headers.get("accept-encoding", "")):

        # 压缩响应
        compressed_data = gzip.compress(response.body)
        response.body = compressed_data
        response.headers["Content-Encoding"] = "gzip"
        response.headers["Content-Length"] = str(len(compressed_data))

    return response
```

#### 数据序列化优化
```python
from pydantic import BaseModel, Field

class AssetResponse(BaseModel):
    """优化的资产响应模型"""
    id: str
    name: str = Field(alias="property_name")

    class Config:
        # 启用JSON序列化优化
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            Decimal: lambda v: float(v)
        }

        # 减少序列化开销
        orm_mode = True
        allow_population_by_field_name = True
```

## 数据库优化

### 查询优化

#### 批量操作
```python
async def bulk_create_assets(assets_data: List[dict]):
    """批量创建资产"""
    try:
        await db.execute(
            insert(Asset).values(assets_data)
        )
        await db.commit()
    except Exception as e:
        await db.rollback()
        raise e

async def bulk_update_assets(updates: List[dict]):
    """批量更新资产"""
    try:
        await db.execute(
            update(Asset).where(
                Asset.id.in_([u['id'] for u in updates])
            ).values(updates)
        )
        await db.commit()
    except Exception as e:
        await db.rollback()
        raise e
```

#### 查询优化
```python
async def get_assets_with_optimization(filters: dict):
    """优化的资产查询"""
    query = select(Asset).where(Asset.data_status == 'NORMAL')

    # 使用索引字段
    if filters.get('ownership_status'):
        query = query.where(Asset.ownership_status == filters['ownership_status'])

    # 限制查询字段
    query = query.options(
        load_only(Asset.id, Asset.property_name, Asset.address)
    )

    # 使用预加载避免N+1问题
    query = query.options(
        joinedload(Asset.ownership_entity),
        joinedload(Asset.project)
    )

    return await query.execute()
```

### 连接池优化

```python
from sqlalchemy.pool import QueuePool

# 创建优化的数据库引擎
engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=20,
    max_overflow=30,
    pool_pre_ping=True,
    pool_recycle=3600,
    echo=False  # 生产环境关闭SQL日志
)

# 使用异步连接池
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

async_engine = create_async_engine(
    ASYNC_DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    pool_recycle=3600
)

async def get_async_session():
    async with AsyncSession(async_engine) as session:
        yield session
```

## 错误处理

### 统一错误响应

```python
from fastapi import HTTPException
from fastapi.responses import JSONResponse

class APIError(Exception):
    """自定义API错误"""
    def __init__(self, message: str, code: str = None, details: dict = None):
        self.message = message
        self.code = code
        self.details = details

@app.exception_handler(APIError)
async def api_error_handler(request: Request, exc: APIError):
    """API错误处理器"""
    return JSONResponse(
        status_code=400,
        content={
            "error": "API Error",
            "message": exc.message,
            "code": exc.code,
            "details": exc.details,
            "timestamp": datetime.now().isoformat()
        }
    )

# 使用示例
@router.post("/assets")
async def create_asset(asset_data: AssetCreate):
    try:
        return await asset_service.create(asset_data)
    except DuplicateAssetError as e:
        raise APIError(
            message="资产名称已存在",
            code="DUPLICATE_ASSET",
            details={"property_name": asset_data.property_name}
        )
```

### 请求验证优化

```python
from pydantic import BaseModel, validator
from typing import Optional

class AssetCreate(BaseModel):
    property_name: str = Field(..., min_length=1, max_length=200)
    address: Optional[str] = Field(None, max_length=500)

    @validator('property_name')
    def validate_property_name(cls, v):
        if not v.strip():
            raise ValueError('物业名称不能为空')
        return v.strip()

    class Config:
        # 严格验证模式
        strict = True
        # 额外字段验证
        extra = "forbid"

@router.post("/assets")
async def create_asset(asset_data: AssetCreate):
    # Pydantic自动验证
    return await asset_service.create(asset_data.dict())
```

## 安全优化

### 认证与授权

```python
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """获取当前用户"""
    try:
        token = credentials.credentials
        payload = decode_jwt_token(token)
        user_id = payload.get("sub")

        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )

        return await get_user(user_id)
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )

@router.get("/assets")
async def get_assets(
    current_user: User = Depends(get_current_user)
):
    """需要认证的资产查询"""
    return await asset_service.get_user_assets(current_user.id)
```

### 请求限制

```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

@app.exception_handler(429)
def rate_limit_exceeded_handler(request, exc):
    """限流错误处理"""
    return JSONResponse(
        status_code=429,
        content={
            "error": "Rate Limit Exceeded",
            "message": "请求过于频繁，请稍后再试",
            "retry_after": exc.detail
        }
    )

@router.get("/assets")
@limiter.limit("100/minute")
async def get_assets(request: Request):
    """限流的资产查询"""
    return await asset_service.get_all()
```

## 监控与日志

### 性能监控

```python
import time
from fastapi import Request, Response

@app.middleware("http")
async def monitoring_middleware(request: Request, call_next):
    """监控中间件"""
    start_time = time.time()

    # 记录请求开始
    logger.info(f"Request started: {request.method} {request.url}")

    try:
        response = await call_next(request)

        # 计算响应时间
        process_time = time.time() - start_time

        # 添加响应头
        response.headers["X-Process-Time"] = str(process_time)

        # 记录请求完成
        logger.info(
            f"Request completed: {request.method} {request.url} "
            f"status={response.status_code} time={process_time:.3f}s"
        )

        # 慢查询警告
        if process_time > 1.0:
            logger.warning(
                f"Slow request: {request.method} {request.url} "
                f"took {process_time:.3f}s"
            )

        return response

    except Exception as e:
        process_time = time.time() - start_time
        logger.error(
            f"Request failed: {request.method} {request.url} "
            f"error={str(e)} time={process_time:.3f}s"
        )
        raise
```

### 结构化日志

```python
import structlog

# 配置结构化日志
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

@router.get("/assets/{asset_id}")
async def get_asset(asset_id: str):
    logger.info("Getting asset", asset_id=asset_id)

    try:
        asset = await asset_service.get_by_id(asset_id)
        logger.info("Asset retrieved successfully", asset_id=asset_id)
        return asset

    except AssetNotFoundError:
        logger.warning("Asset not found", asset_id=asset_id)
        raise
```

## 测试优化

### 性能测试

```python
import asyncio
import aiohttp
from concurrent.futures import ThreadPoolExecutor

async def performance_test():
    """API性能测试"""
    base_url = "http://localhost:8002"

    async with aiohttp.ClientSession() as session:
        tasks = []

        # 并发请求测试
        for i in range(100):
            task = asyncio.create_task(
                session.get(f"{base_url}/api/v1/assets")
            )
            tasks.append(task)

        # 测量响应时间
        start_time = time.time()
        responses = await asyncio.gather(*tasks)
        end_time = time.time()

        # 统计结果
        success_count = sum(1 for r in responses if r.status == 200)
        avg_time = (end_time - start_time) / len(tasks)

        print(f"并发测试结果:")
        print(f"成功请求: {success_count}/{len(tasks)}")
        print(f"平均响应时间: {avg_time:.3f}s")
        print(f"总耗时: {end_time - start_time:.3f}s")

if __name__ == "__main__":
    asyncio.run(performance_test())
```

## 最佳实践总结

### 开发规范
1. **统一响应格式**: 使用一致的API响应结构
2. **错误处理**: 完善的错误处理和日志记录
3. **性能监控**: 实时监控API性能指标
4. **版本管理**: 合理的API版本控制策略

### 部署优化
1. **负载均衡**: 使用Nginx等反向代理
2. **缓存策略**: 多层缓存架构
3. **数据库优化**: 索引优化和查询优化
4. **监控告警**: 完善的监控和告警机制

通过以上优化措施，API性能和可靠性得到显著提升，为用户提供更好的服务体验。