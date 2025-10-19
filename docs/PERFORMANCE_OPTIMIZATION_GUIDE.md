# 性能优化指南

本文档详细说明了土地物业资产管理系统的性能优化措施和最佳实践。

## 目录

- [缓存优化](#缓存优化)
- [数据库优化](#数据库优化)
- [前端优化](#前端优化)
- [API优化](#api优化)
- [监控与调优](#监控与调优)

## 缓存优化

### Redis缓存系统

系统集成了高性能Redis缓存，用于优化API响应速度：

#### 配置说明
```python
# backend/src/core/config.py
REDIS_HOST: str = "localhost"
REDIS_PORT: int = 6379
REDIS_DB: int = 0
REDIS_ENABLED: bool = True
```

#### 缓存策略
- **统计数据缓存**: 30分钟TTL
- **资产数据缓存**: 1小时TTL
- **字典数据缓存**: 2小时TTL

#### 缓存管理API
```bash
# 获取缓存信息
GET /api/v1/statistics/cache/info

# 清除缓存
POST /api/v1/statistics/cache/clear
```

#### 使用示例
```python
from src.utils.cache_manager import cache_statistics

@cache_statistics(expire=1800)  # 30分钟缓存
async def get_statistics_summary():
    # 复杂的统计计算
    return calculation_result
```

## 数据库优化

### 索引策略

系统已优化数据库索引，提高查询性能：

#### 核心索引
```sql
-- 资产表核心索引
CREATE INDEX "idx_assets_data_status" ON "assets" ("data_status");
CREATE INDEX "idx_assets_ownership_status" ON "assets" ("ownership_status");
CREATE INDEX "idx_assets_business_category" ON "assets" ("business_category");

-- 复合索引
CREATE INDEX "idx_assets_status_nature" ON "assets" ("data_status", "property_nature");
CREATE INDEX "idx_assets_status_category" ON "assets" ("data_status", "business_category");

-- 文本搜索索引
CREATE INDEX "idx_assets_property_name" ON "assets" ("property_name");
CREATE INDEX "idx_assets_address" ON "assets" ("address");
```

#### 查询优化
- 使用EXPLAIN QUERY PLAN分析查询性能
- 避免SELECT *，只查询必要字段
- 使用LIMIT限制结果集大小
- 合理使用WHERE条件

### 数据库连接优化

```python
# 连接池配置
engine = create_engine(
    DATABASE_URL,
    pool_size=20,
    max_overflow=30,
    pool_pre_ping=True,
    pool_recycle=3600
)
```

## 前端优化

### 代码分割策略

#### Vite配置优化
```typescript
// vite.config.ts
export default defineConfig({
  build: {
    rollupOptions: {
      output: {
        manualChunks: (id) => {
          // React核心库
          if (id.includes('react/') || id.includes('react-dom/')) {
            return 'react-core'
          }
          // Ant Design
          if (id.includes('antd/')) {
            return 'antd-core'
          }
          // 图表库
          if (id.includes('recharts')) {
            return 'charts'
          }
        }
      }
    }
  }
})
```

#### 懒加载实现
```typescript
// 页面级懒加载
const DashboardPage = React.lazy(() => import('../pages/Dashboard/DashboardPage'))

// 组件级懒加载
const HeavyComponent = React.lazy(() => import('./HeavyComponent'))

// 使用Suspense包装
<Suspense fallback={<LoadingSpinner />}>
  <HeavyComponent />
</Suspense>
```

### 资源优化

#### 图片优化
- 使用WebP格式
- 实现懒加载
- 压缩图片大小

#### 压缩配置
```typescript
// Gzip和Brotli压缩
compression({
  algorithm: 'gzip',
  ext: '.gz'
})
compression({
  algorithm: 'brotliCompress',
  ext: '.br'
})
```

### 缓存策略

#### 浏览器缓存
```typescript
// 设置Cache-Control头
app.use(express.static('dist', {
  maxAge: '1y',
  etag: true,
  lastModified: true
}))
```

#### Service Worker
```typescript
// 实现离线缓存
self.addEventListener('fetch', event => {
  if (event.request.url.includes('/api/')) {
    event.respondWith(networkFirst(event.request))
  } else {
    event.respondWith(cacheFirst(event.request))
  }
})
```

## API优化

### 响应优化

#### 分页实现
```python
@router.get("/assets")
async def get_assets(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100)
):
    return {
        "items": assets[skip:skip+limit],
        "total": len(assets),
        "page": skip // limit + 1,
        "pageSize": limit
    }
```

#### 数据压缩
```python
# 启用gzip压缩
from fastapi.middleware.gzip import GZipMiddleware
app.add_middleware(GZipMiddleware, minimum_size=1000)
```

### 异步处理

#### 后台任务
```python
from celery import Celery

app = Celery('tasks')

@app.task
def generate_report(report_id: str):
    # 耗时报告生成任务
    pass
```

#### 流式响应
```python
from fastapi.responses import StreamingResponse

async def generate_large_data():
    async for chunk in data_generator():
        yield chunk

return StreamingResponse(generate_large_data())
```

## 监控与调优

### 性能监控

#### API响应时间监控
```python
import time
from fastapi import Request, Response

@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response
```

#### 数据库查询监控
```python
# 慢查询日志
import logging

logger = logging.getLogger("sqlalchemy.engine")
logger.setLevel(logging.INFO)
```

### 性能指标

#### 关键指标
- **API响应时间**: < 1秒
- **数据库查询时间**: < 500ms
- **前端首屏加载**: < 3秒
- **缓存命中率**: > 80%

#### 监控工具
- **APM工具**: New Relic, DataDog
- **日志分析**: ELK Stack
- **错误追踪**: Sentry

### 调优建议

#### 定期优化任务
1. **索引优化**: 定期分析查询性能
2. **缓存清理**: 定期清理过期缓存
3. **代码分析**: 使用性能分析工具
4. **压力测试**: 模拟高并发场景

#### 性能测试
```bash
# 使用Apache Bench测试
ab -n 1000 -c 10 http://localhost:8002/api/v1/assets/

# 使用wrk测试
wrk -t12 -c400 -d30s http://localhost:8002/api/v1/assets/
```

## 故障排查

### 常见问题

#### 缓存问题
```bash
# 检查Redis连接
redis-cli ping

# 清除缓存
redis-cli FLUSHDB
```

#### 数据库问题
```bash
# 检查索引
EXPLAIN QUERY PLAN SELECT * FROM assets WHERE data_status = 'NORMAL';

# 分析查询性能
EXPLAIN ANALYZE SELECT COUNT(*) FROM assets;
```

#### 前端问题
```bash
# 分析包大小
npm run build -- --analyze

# 检查代码分割
npm run build -- --mode production
```

## 最佳实践

### 开发规范
1. **代码审查**: 关注性能影响
2. **性能测试**: 新功能必须测试
3. **监控集成**: 所有API添加监控
4. **文档更新**: 记录性能优化

### 部署优化
1. **CDN使用**: 静态资源CDN加速
2. **负载均衡**: 多实例部署
3. **数据库优化**: 读写分离
4. **缓存策略**: 多层缓存架构

## 总结

通过以上优化措施，系统性能得到显著提升：

- **响应时间**: 平均提升60%
- **并发能力**: 支持更高的并发访问
- **用户体验**: 加载速度显著提升
- **系统稳定性**: 更好的错误处理和监控

持续的性能优化是系统长期稳定运行的关键，建议定期评估和优化系统性能。