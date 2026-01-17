# Field Validation Security Guide

**为开发者提供的字段验证安全指南**

**最后更新**: 2026-01-17
**版本**: 1.0

---

## 概述

字段验证框架（Field Validator）用于防止任意字段查询攻击，确保 API 端点只允许查询白名单字段。

**安全问题示例**:
```python
# ❌ 危险 - 允许用户查询任意字段
@router.get("/assets")
async def get_assets(group_by: str):
    # 攻击者可以: ?group_by=internal_notes
    # 或: ?group_by=manager_salary
    for asset in assets:
        value = getattr(asset, group_by)  # 泄露敏感数据!
```

**解决方案**: 使用字段验证框架

---

## 快速开始

### 1. 导入验证器

```python
from src.security.field_validator import FieldValidator
```

### 2. 验证字段

```python
# 验证单个 group_by 字段
@router.get("/asset-distribution")
async def get_asset_distribution(
    group_by: str = Query("ownership_status", description="分组字段")
):
    # 验证字段是否在白名单中
    FieldValidator.validate_group_by_field("Asset", group_by, raise_on_invalid=True)

    # 现在可以安全使用 group_by
    for asset in assets:
        value = getattr(asset, group_by)
```

### 3. 验证多个字段

```python
# 验证过滤字段列表
filter_fields = ["property_name", "ownership_status"]
valid_fields, invalid_fields = FieldValidator.validate_filter_fields(
    "Asset",
    filter_fields,
    raise_on_invalid=True
)
```

---

## API 参考

### `FieldValidator.validate_filter_fields()`

验证过滤字段是否在白名单中。

**参数**:
- `model_name` (str): 模型名称（如 "Asset", "RentContract"）
- `fields` (list[str]): 要验证的字段列表
- `raise_on_invalid` (bool): 发现无效字段时是否抛出异常（默认 True）

**返回**:
- `(valid_fields, invalid_fields)` 元组

**示例**:
```python
valid, invalid = FieldValidator.validate_filter_fields(
    "Asset",
    ["property_name", "manager_name"],  # manager_name 被阻止
    raise_on_invalid=False
)
# valid = ["property_name"]
# invalid = ["manager_name"]
```

---

### `FieldValidator.validate_group_by_field()`

验证 group_by 字段（使用 filter_fields 白名单）。

**参数**:
- `model_name` (str): 模型名称
- `field` (str): Group by 字段
- `raise_on_invalid` (bool): 是否抛出异常（默认 True）

**返回**:
- `bool`: 字段是否有效

**示例**:
```python
@router.get("/statistics")
async def get_stats(group_by: str):
    FieldValidator.validate_group_by_field("Asset", group_by)
    # 如果字段无效，会抛出 HTTPException 400
```

---

### `FieldValidator.validate_search_fields()`

验证搜索字段（文本搜索，ILIKE 操作）。

**参数**:
- `model_name` (str): 模型名称
- `fields` (list[str]): 搜索字段列表
- `raise_on_invalid` (bool): 是否抛出异常

**返回**:
- `(valid_fields, invalid_fields)` 元组

---

### `FieldValidator.validate_sort_field()`

验证排序字段。

**参数**:
- `model_name` (str): 模型名称
- `field` (str): 排序字段
- `raise_on_invalid` (bool): 是否抛出异常

**返回**:
- `bool`: 字段是否有效

---

### `FieldValidator.sanitize_filters()`

清理过滤器字典，移除不允许的字段。

**参数**:
- `model_name` (str): 模型名称
- `filters` (dict): 原始过滤器字典
- `strict` (bool): 严格模式 - 发现无效字段时抛出异常（默认 False）

**返回**:
- `dict`: 清理后的过滤器字典

**示例**:
```python
filters = {
    "property_name": "测试",
    "manager_name": "张三",  # 被阻止的字段
}

sanitized = FieldValidator.sanitize_filters("Asset", filters, strict=False)
# sanitized = {"property_name": "测试"}
```

---

### `FieldValidator.get_allowed_fields()`

获取模型允许的字段列表。

**参数**:
- `model_name` (str): 模型名称
- `operation` (str): 操作类型（"filter", "search", "sort"）

**返回**:
- `set[str]`: 允许的字段集合

**示例**:
```python
allowed = FieldValidator.get_allowed_fields("Asset", "filter")
# allowed = {"property_name", "ownership_status", "land_area", ...}
```

---

## 使用场景

### 场景 1: 动态 group_by 参数

```python
@router.get("/asset-distribution")
async def get_asset_distribution(
    group_by: str = Query("ownership_status", description="分组字段"),
    db: Session = Depends(get_db),
):
    # ✅ 验证 group_by 字段
    FieldValidator.validate_group_by_field("Asset", group_by, raise_on_invalid=True)

    assets = db.query(Asset).all()

    distribution = {}
    for asset in assets:
        # 现在安全使用 getattr
        value = getattr(asset, group_by, "未知")
        distribution[value] = distribution.get(value, 0) + 1

    return {"distribution": distribution}
```

---

### 场景 2: 动态过滤器

```python
@router.get("/assets")
async def get_assets(
    filters: dict[str, Any] = Body({}),
    db: Session = Depends(get_db),
):
    # ✅ 清理过滤器，移除不允许的字段
    safe_filters = FieldValidator.sanitize_filters(
        "Asset",
        filters,
        strict=True  # 严格模式：发现无效字段时抛出异常
    )

    # 使用清理后的过滤器
    query = db.query(Asset)
    for field, value in safe_filters.items():
        query = query.filter(getattr(Asset, field) == value)

    return query.all()
```

---

### 场景 3: 动态排序

```python
@router.get("/assets")
async def get_assets(
    sort_by: str = Query("created_at", description="排序字段"),
    db: Session = Depends(get_db),
):
    # ✅ 验证排序字段
    FieldValidator.validate_sort_field("Asset", sort_by, raise_on_invalid=True)

    # 安全使用排序字段
    query = db.query(Asset).order_by(getattr(Asset, sort_by))
    return query.all()
```

---

### 场景 4: 批量字段验证

```python
@router.post("/assets/search")
async def search_assets(
    search_fields: list[str] = Body(...),
    search_term: str = Body(...),
    db: Session = Depends(get_db),
):
    # ✅ 验证所有搜索字段
    valid_fields, invalid_fields = FieldValidator.validate_search_fields(
        "Asset",
        search_fields,
        raise_on_invalid=True
    )

    # 使用验证后的字段
    query = db.query(Asset)
    for field in valid_fields:
        query = query.filter(getattr(Asset, field).ilike(f"%{search_term}%"))

    return query.all()
```

---

## 错误处理

### 自动抛出的异常

当 `raise_on_invalid=True` 时，验证失败会抛出 `HTTPException`：

```python
try:
    FieldValidator.validate_group_by_field("Asset", "manager_salary")
except HTTPException as e:
    # e.status_code = 400
    # e.detail = {
    #     "error": "Invalid group_by field",
    #     "field": "manager_salary",
    #     "message": "不允许按字段分组: manager_salary。请检查 API 文档了解允许的分组字段。"
    # }
```

### 宽松模式

```python
# 不抛出异常，只返回结果
valid, invalid = FieldValidator.validate_filter_fields(
    "Asset",
    ["property_name", "manager_salary"],
    raise_on_invalid=False  # 宽松模式
)

if invalid:
    logger.warning(f"过滤掉无效字段: {invalid}")
    # 继续处理，只使用 valid 字段
```

---

## 字段白名单配置

字段白名单定义在 `backend/src/crud/field_whitelist.py`。

### 查看允许的字段

```python
from src.crud.field_whitelist import AssetWhitelist

# 查看 Asset 模型的白名单
print(AssetWhitelist.filter_fields)   # 允许过滤的字段
print(AssetWhitelist.search_fields)   # 允许搜索的字段
print(AssetWhitelist.sort_fields)     # 允许排序的字段
print(AssetWhitelist.blocked_fields)  # 明确阻止的字段
```

### 添加新字段到白名单

如果需要允许新字段，编辑 `field_whitelist.py`：

```python
class AssetWhitelist(ModelFieldWhitelist):
    filter_fields: ClassVar[set[str]] = {
        "property_name",
        "ownership_status",
        # 添加新字段
        "new_field_name",
    }

    # PII 字段必须在 blocked_fields 中
    blocked_fields: ClassVar[set[str]] = {
        "manager_name",     # PII
        "tenant_name",      # PII
        "project_phone",    # PII
    }
```

---

## 最佳实践

### ✅ DO - 推荐做法

1. **总是验证用户提供的字段名**
   ```python
   FieldValidator.validate_group_by_field("Asset", group_by)
   ```

2. **使用严格模式防止攻击**
   ```python
   FieldValidator.validate_filter_fields(
       "Asset", fields, raise_on_invalid=True
   )
   ```

3. **记录被阻止的尝试**
   ```python
   valid, invalid = FieldValidator.validate_filter_fields(
       "Asset", fields, raise_on_invalid=False
   )
   if invalid:
       logger.warning(f"Blocked unauthorized field access: {invalid}")
   ```

4. **在 API 端点早期验证**
   ```python
   @router.get("/assets")
   async def get_assets(group_by: str):
       # 第一步：验证字段
       FieldValidator.validate_group_by_field("Asset", group_by)

       # 第二步：执行业务逻辑
       ...
   ```

---

### ❌ DON'T - 避免做法

1. **不要跳过验证**
   ```python
   # ❌ 危险！
   for asset in assets:
       value = getattr(asset, user_provided_field)  # 未验证！
   ```

2. **不要信任前端验证**
   ```python
   # ❌ 前端验证不够
   # 攻击者可以绕过前端直接调用 API
   # 必须在后端验证
   ```

3. **不要硬编码字段列表**
   ```python
   # ❌ 不好 - 难以维护
   valid_fields = ["field1", "field2", ...]
   if field not in valid_fields:
       raise HTTPException(...)

   # ✅ 好 - 使用框架
   FieldValidator.validate_group_by_field("Asset", field)
   ```

4. **不要在白名单中包含 PII 字段**
   ```python
   # ❌ 错误！
   filter_fields = {
       "manager_name",  # PII - 不应该允许过滤
       ...
   }

   # ✅ 正确 - PII 字段应在 blocked_fields
   blocked_fields = {
       "manager_name",  # 明确阻止
       ...
   }
   ```

---

## 常见问题

### Q: 如何知道某个字段是否被允许？

```python
# 方法 1: 查看白名单配置
from src.crud.field_whitelist import AssetWhitelist
allowed = "property_name" in AssetWhitelist.filter_fields

# 方法 2: 使用 get_allowed_fields
allowed_fields = FieldValidator.get_allowed_fields("Asset", "filter")
```

### Q: 验证失败会发生什么？

当 `raise_on_invalid=True` 时，会抛出 `HTTPException` (status_code=400)，并返回清晰的错误消息给客户端。

### Q: 如何为新模型添加字段白名单？

1. 在 `crud/field_whitelist.py` 中创建新的 Whitelist 类
2. 在 `security/field_validator.py` 的 `MODEL_REGISTRY` 中注册模型
3. 定义允许的字段集合

### Q: 财务字段可以查询吗？

某些财务字段（如 `monthly_rent`, `deposit`）允许**排序**但不允许**过滤**。这样可以显示数据但防止基于金额的数据挖掘。

---

## 测试

运行字段验证测试：

```bash
cd backend
pytest tests/security/test_phase1_security.py::TestFieldFilteringValidation -v
```

---

## 相关文档

- `backend/src/crud/field_whitelist.py` - 字段白名单配置
- `backend/src/security/field_validator.py` - 验证器实现
- `tests/security/test_phase1_security.py` - 测试用例

---

## 更新日志

- **2026-01-17**: 初始版本，Phase 1 安全加固
