# 异常处理最佳实践指南

**版本**: 1.0
**最后更新**: 2026-01-16
**状态**: 已实施

---

## 概述

本文档定义了土地物业资产管理系统的异常处理最佳实践，确保系统的安全性、可维护性和用户体验。

---

## 核心原则

### 1. API层：不捕获通用Exception

**❌ 错误示例** - 暴露内部错误：
```python
@router.get("/assets/{asset_id}")
async def get_asset(asset_id: str, db: Session = Depends(get_db)):
    try:
        asset = asset_service.get_asset(asset_id)
        return asset
    except Exception as e:
        # ❌ 暴露内部错误给客户端
        raise HTTPException(status_code=500, detail=f"获取资产失败: {str(e)}")
```

**✅ 正确示例** - 让全局处理器处理：
```python
@router.get("/assets/{asset_id}")
async def get_asset(asset_id: str, db: Session = Depends(get_db)):
    # ✅ 直接调用，让异常自然传播
    asset = asset_service.get_asset(asset_id)
    return asset
```

**为什么**：
- 全局异常处理器会安全地记录日志并返回标准化的错误响应
- 开发环境显示详细错误，生产环境隐藏敏感信息
- 避免向客户端泄露数据库错误、SQL语句、堆栈跟踪等

### 2. Service层：将技术异常转换为业务异常

**❌ 错误示例** - 返回None掩盖错误：
```python
class AssetService:
    def get_asset(self, asset_id: str):
        try:
            asset = self.db.query(Asset).filter(Asset.id == asset_id).first()
            if not asset:
                return None  # ❌ 掩盖了"资源未找到"的业务错误
            return asset
        except Exception as e:
            logger.error(f"获取资产失败: {e}")
            return None  # ❌ 吞噬了异常
```

**✅ 正确示例** - 使用辅助函数：
```python
from src.core.exception_helpers import handle_service_exception
from src.core.exception_handler import ResourceNotFoundError

class AssetService:
    def get_asset(self, asset_id: str):
        try:
            asset = self.db.query(Asset).filter(Asset.id == asset_id).first()
            if not asset:
                raise ResourceNotFoundError("资产", asset_id)
            return asset
        except Exception as e:
            # ✅ 使用辅助函数统一处理
            handle_service_exception(e, "AssetService", "get_asset")
```

**为什么**：
- 技术异常（如数据库连接失败）不应该传播到API层
- 业务异常（如资源未找到）应该明确定义并抛出
- 统一的异常处理模式降低了认知负担

### 3. 降级策略：明确记录并优雅降级

**✅ 正确示例** - 合理的降级策略：
```python
class AnalyticsService:
    def calculate_occupancy_rate(self, filters: dict):
        try:
            # 尝试使用数据库聚合查询（高性能）
            result = self._calculate_via_db_aggregation(filters)
            return result
        except Exception as e:
            logger.warning(f"数据库聚合失败，降级到内存计算: {e}")
            # ✅ 降级到内存计算（性能较低但可用）
            return self._calculate_in_memory(filters)
```

**为什么**：
- 当主要方法失败时，有明确的备用方案
- 记录了降级原因，便于问题排查
- 提升了系统的可用性和弹性

### 4. 优雅降级：返回安全的默认值

**✅ 正确示例** - 返回空列表：
```python
class EnumValidationService:
    def get_enum_values(self, enum_type: str) -> list[str]:
        try:
            values = self.db.query(EnumValue).filter(
                EnumValue.type == enum_type
            ).all()
            return [v.value for v in values]
        except Exception as e:
            logger.error(f"获取枚举值失败: {e}")
            # ✅ 返回空列表而不是崩溃
            return []
```

**为什么**：
- 当配置数据缺失时，系统仍能继续运行
- 调用方可以处理空列表（如显示"无可用选项"）
- 避免因非关键功能失败导致整个系统不可用

---

## 全局异常处理器

系统已实现全局异常处理器，位置：`backend/src/core/exception_handler.py`

### 功能

1. **统一错误响应格式**
   ```json
   {
     "success": false,
     "error": {
       "code": "INTERNAL_SERVER_ERROR",
       "message": "内部服务器错误",
       "timestamp": "2026-01-16T10:00:00Z",
       "details": {}
     }
   }
   ```

2. **环境感知的错误详情**
   - **开发环境**: 包含详细错误信息、异常类型
   - **生产环境**: 隐藏敏感信息，只显示通用错误消息

3. **自动日志记录**
   - 记录完整的错误堆栈
   - 包含请求上下文信息（路径、方法、参数）

### 使用方法

全局处理器已在 `backend/src/main.py:265` 注册，自动处理所有未捕获的异常。

---

## 辅助工具

### 1. 异常处理辅助函数

位置：`backend/src/core/exception_helpers.py`

```python
from src.core.exception_helpers import handle_service_exception

try:
    # 业务逻辑
    result = some_operation()
except Exception as e:
    handle_service_exception(e, "MyService", "my_operation")
```

**功能**：
- 自动记录错误日志
- 将IntegrityError转换为DuplicateResourceError
- 将ValueError/TypeError转换为BusinessValidationError
- 重新抛出其他异常让全局处理器处理

### 2. 自动化检查脚本

位置：`backend/scripts/check_exception_handling.py`

```bash
cd backend
python scripts/check_exception_handling.py
```

**功能**：
- 检测API层的安全问题（暴露内部错误）
- 检测Service层的异常处理模式
- 生成详细的问题报告

---

## 已修复的文件

| 文件 | 修复数量 | 状态 | 提交 |
|------|---------|------|------|
| `backend/src/api/v1/assets.py` | 11处 | ✅ 完成 | f2d9835 |
| `backend/src/api/v1/excel.py` | 18处 | ✅ 完成 | 3b2325a |
| `backend/src/api/v1/statistics.py` | 17处 | ✅ 完成 | 4751df8 |
| **总计** | **46处** | ✅ **完成** | - |

**验证结果**：
```bash
$ python scripts/check_exception_handling.py
[OK] 未发现安全问题
[WARNING] 发现 62 处代码质量问题  # 均为Service层的合理降级策略
```

---

## 常见场景

### 场景1: 资源未找到

**❌ 错误**：
```python
try:
    asset = db.query(Asset).filter(Asset.id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail=f"资产 {asset_id} 不存在")
except Exception as e:
    raise HTTPException(status_code=500, detail=str(e))
```

**✅ 正确**：
```python
asset = db.query(Asset).filter(Asset.id == asset_id).first()
if not asset:
    raise ResourceNotFoundError("资产", asset_id)
return asset
```

### 场景2: 数据验证失败

**❌ 错误**：
```python
try:
    if not email or "@" not in email:
        raise ValueError(f"无效的邮箱: {email}")
except ValueError as e:
    raise HTTPException(status_code=400, detail=str(e))
```

**✅ 正确**：
```python
if not email or "@" not in email:
    raise BusinessValidationError("邮箱格式不正确")
```

### 场景3: 数据库唯一约束冲突

**❌ 错误**：
```python
try:
    db.add(new_asset)
    db.commit()
except IntegrityError as e:
    raise HTTPException(status_code=500, detail=f"数据库错误: {str(e)}")
```

**✅ 正确**：
```python
try:
    db.add(new_asset)
    db.commit()
except IntegrityError:
    raise DuplicateResourceError("资产", "物业名称", new_asset.property_name)
```

### 场景4: 后台任务错误处理

**✅ 正确** - 后台任务需要记录错误状态：
```python
async def process_task(task_id: str, db_session: Session):
    try:
        # 执行任务
        result = await do_work()
        # 更新任务为成功状态
        task_crud.update(db_session, task_id, {"status": "completed"})
    except Exception as e:
        # ✅ 合理：更新任务失败状态，但不向客户端暴露
        task_crud.update(db_session, task_id, {
            "status": "failed",
            "error_message": str(e)  # 存储在数据库中供管理员查看
        })
```

---

## 检查清单

在提交代码前，请确认：

### API层检查清单
- [ ] 不存在 `except Exception as e: raise HTTPException(status_code=500, detail=f"...{str(e)}")`
- [ ] 不存在 `except Exception:` 捕获后返回通用错误消息
- [ ] 让业务异常自然传播到全局处理器
- [ ] 使用自定义业务异常（ResourceNotFoundError, BusinessValidationError等）

### Service层检查清单
- [ ] 将技术异常转换为业务异常
- [ ] 使用 `handle_service_exception` 辅助函数
- [ ] 降级策略有明确的日志记录
- [ ] 优雅降级返回安全的默认值

### 测试检查清单
- [ ] 测试错误场景不暴露内部信息
- [ ] 验证全局异常处理器正常工作
- [ ] 确认日志记录包含完整的错误信息

---

## 参考资料

- 全局异常处理器：`backend/src/core/exception_handler.py`
- 业务异常定义：`backend/src/core/exception_handler.py:19-180`
- 异常处理辅助函数：`backend/src/core/exception_helpers.py`
- 自动检查脚本：`backend/scripts/check_exception_handling.py`
- 单元测试：`backend/tests/unit/core/test_exception_handling.py`

---

## 更新日志

| 日期 | 版本 | 变更内容 | 作者 |
|------|------|---------|------|
| 2026-01-16 | 1.0 | 初始版本，基于异常处理改进项目 | Claude Sonnet 4.5 |

---

**注意**: 本文档是活跃文档，随着系统演进会持续更新。如发现需要补充或修正的内容，请及时更新。
