# 代码风格与约定

## Python 后端

### 架构分层
- **API 层** (`api/v1/`): 路由编排，不承载业务逻辑
- **Service 层** (`services/`): 业务逻辑实现
- **CRUD 层** (`crud/`): 纯数据访问
- **Models 层** (`models/`): 数据库模型定义

### 新增 API 端点模式
```python
# backend/src/api/v1/my_feature.py
from src.core.router_registry import route_registry

router = APIRouter(prefix="/my-feature", tags=["My Feature"])

@router.get("/items")
async def get_items(): ...

route_registry.register_router(router, prefix="/api/v1", tags=["My Feature"], version="v1")
```

### 关键规则
- 路由层不得直接操作 CRUD 与事务提交
- 枚举非法时返回 422
- PII 字段由 `SensitiveDataHandler` 处理
- 软删除使用 `data_status` 字段

## TypeScript 前端

### 导入约定
- 统一使用 `@/` 别名
- 避免深层相对路径

### 状态管理
| 状态类型 | 使用 |
|---------|------|
| 全局 UI | Zustand (`store/`) |
| 服务器数据 | React Query |
| 表单 | React Hook Form |

### 严格布尔表达式
- 使用显式空值检查与 `??` 默认值

## 提交格式
```
type(scope): description

# 示例
feat(auth): add JWT refresh
fix(assets): resolve soft delete constraint
```
