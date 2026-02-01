# 后端失败测试修复指南

**日期**: 2026-02-01
**状态**: 196 个失败测试待修复

---

## 🔍 关键问题分析

### 问题 1: `get_whitelist_for_model` 不存在

**错误信息**:
```
AttributeError: <module 'src.security.security' from '...'> does not have the attribute 'get_whitelist_for_model'
```

**根本原因**:
- `get_whitelist_for_model` 函数存在于 `src.crud.field_whitelist`
- `src.security.security` 模块中没有导入此函数
- `test_request_security.py` 中的 Mock 路径错误：`@patch("src.security.security.get_whitelist_for_model")`

**受影响的测试文件**:
- `tests/unit/security/test_request_security.py` (~20 个测试用例)

**修复方案**:

**方案 A**: 修复测试文件的 Mock 路径
```python
# 修改前
@patch("src.security.security.get_whitelist_for_model")

# 修改后
@patch("src.crud.field_whitelist.get_whitelist_for_model")
```

**方案 B**: 在 `src.security.security` 中添加导入（推荐）
```python
# src/security/security.py
from src.crud.field_whitelist import get_whitelist_for_model
```

---

### 问题 2: `model_to_dict` 不存在

**错误信息**:
```
AttributeError: <module 'src.services.rent_contract.service' from '...'> does not have the attribute 'model_to_dict'
```

**根本原因**:
- `test_rent_contract_service_coverage.py` 中使用了 `model_to_dict` 函数
- `src.services.rent_contract.service` 模块中没有此函数

**修复方案**:

**方案 A**: 添加 `model_to_dict` 辅助函数
```python
# src/services/rent_contract/service.py
def model_to_dict(model: Any) -> dict:
    """将 SQLAlchemy 模型转换为字典"""
    if model is None:
        return {}
    return {c.name: getattr(model, c.name) for c in model.__table__.columns}
```

**方案 B**: 使用 Pydantic 的 `model_dump()`（推荐）
```python
# 修改测试代码
from_model = RentContractRead.model_validate(db_contract)
result = from_model.model_dump()
```

---

### 问题 3: `rent_contract` 和 `rent_ledger` 模块不存在

**错误信息**:
```
AttributeError: <module 'src.services.rent_contract.service' from '...'> does not have the attribute 'rent_contract'
AttributeError: <module 'src.services.rent_contract.service' from '...'> does not have the attribute 'rent_ledger'
```

**根本原因**:
- 测试代码期望 `service.py` 直接导入模型
- 但模型可能应该从 `src.models.rent_contract` 导入

**修复方案**:
```python
# 修改测试代码
# 修改前
from src.services.rent_contract.service import rent_contract, rent_ledger

# 修改后
from src.models.rent_contract import RentContract, RentLedger
rent_contract = RentContract
rent_ledger = RentLedger
```

---

## 📋 修复优先级和时间估算

### P0 - 高优先级（大量失败）

| 文件 | 失败数 | 修复重点 | 预估时间 |
|------|--------|---------|---------|
| `test_request_security.py` | ~20 | Mock 路径修复 | 1h |
| `test_rent_contract_service_coverage.py` | ~11 | 导入修复 + 添加辅助函数 | 2h |
| `test_pdf_analyzer.py` | 6 | Mock 配置 | 1h |
| `test_pdf_batch_routes.py` | ~15 | API Mock | 1.5h |

### P1 - 中优先级

| 文件 | 失败数 | 修复重点 | 预估时间 |
|------|--------|---------|---------|
| `test_rent_contract_service_impl.py` | 4 | Ledger 生成逻辑 | 1h |
| `test_notification_scheduler.py` | 3 | 定时任务 Mock | 0.5h |
| `test_project.py` | 1 | 权限检查 | 0.5h |
| `test_asset_encryption.py` | ~10 | 加密解密测试 | 1h |

### P2 - 低优先级（分散失败）

| 文件 | 失败数 | 修复重点 | 预估时间 |
|------|--------|---------|---------|
| 其他分散失败测试 | ~144 | 各类问题 | 8h |

**总计预估时间**: ~16.5 小时

---

## 🛠️ 快速修复步骤

### 步骤 1: 修复 `get_whitelist_for_model` 导入（1h）

```bash
# 1. 在 src/security/security.py 中添加导入
echo "from src.crud.field_whitelist import get_whitelist_for_model" >> src/security/security.py

# 2. 运行相关测试
pytest tests/unit/security/test_request_security.py -v

# 3. 验证修复
pytest tests/unit/security/test_request_security.py -v | grep -E "PASSED|FAILED"
```

### 步骤 2: 修复 `model_to_dict` 问题（2h）

```python
# 在 src/services/rent_contract/service.py 中添加辅助函数

def model_to_dict(model: Any, exclude: Optional[Set[str]] = None) -> dict:
    """
    将 SQLAlchemy 模型转换为字典

    Args:
        model: SQLAlchemy 模型实例
        exclude: 要排除的字段集合

    Returns:
        dict: 模型数据的字典表示
    """
    if model is None:
        return {}

    if hasattr(model, 'model_dump'):
        # Pydantic v2 模型
        return model.model_dump(exclude=exclude)

    # SQLAlchemy 模型
    columns = model.__table__.columns.keys()
    return {
        col: getattr(model, col)
        for col in columns
        if exclude is None or col not in exclude
    }
```

### 步骤 3: 修复模块导入（1h）

```python
# 修改测试文件中的导入
# 测试文件: tests/unit/services/rent_contract/test_rent_contract_service_coverage.py

# 修改前
from src.services.rent_contract.service import service, rent_contract, rent_ledger, model_to_dict

# 修改后
from src.services.rent_contract.service import service
from src.models.rent_contract import RentContract, RentLedger
from src.services.rent_contract.service import model_to_dict  # 在步骤2中添加的函数

# 兼容性修复
rent_contract = RentContract
rent_ledger = RentLedger
```

### 步骤 4: 批量运行测试验证（0.5h）

```bash
# 运行所有失败的测试
pytest tests/unit/services/document/test_pdf_analyzer.py -v
pytest tests/unit/services/rent_contract/test_rent_contract_service_coverage.py -v
pytest tests/unit/services/rent_contract/test_rent_contract_service_impl.py -v
pytest tests/unit/api/v1/test_pdf_batch_routes.py -v

# 生成覆盖率报告
pytest --cov=src --cov-report=html --cov-report=term
```

---

## 🚀 自动化修复脚本

创建 `scripts/fix_tests.sh` 自动化常见修复：

```bash
#!/bin/bash
# scripts/fix_tests.sh

echo "开始自动修复失败测试..."

# 1. 修复 get_whitelist_for_model 导入
echo "修复 security 模块导入..."
sed -i '1a from src.crud.field_whitelist import get_whitelist_for_model' src/security/security.py

# 2. 修复测试文件中的 Mock 路径
echo "修复测试 Mock 路径..."
find tests -name "*.py" -exec sed -i 's/src\.security\.security\.get_whitelist_for_model/src.crud.field_whitelist.get_whitelist_for_model/g' {} \;

# 3. 运行测试验证
echo "运行测试验证..."
pytest tests/unit/security/test_request_security.py -v

echo "修复完成！"
```

---

## ✅ 验收标准

- [ ] 所有 P0 优先级测试已修复（4 个文件，~47 个测试）
- [ ] 所有 P1 优先级测试已修复（4 个文件，~18 个测试）
- [ ] 剩余 P2 测试已评估并制定修复计划
- [ ] 测试通过率从 95.4% 提升到 98%+
- [ ] 运行 `pytest --cov=src` 确认覆盖率未下降

---

## 📝 注意事项

1. **不要直接修改核心业务逻辑**
   - 只修复测试代码，不要为了测试而修改实现

2. **保持测试独立性**
   - 每个测试应该独立运行，不依赖其他测试

3. **Mock 的正确使用**
   - Mock 外部依赖，不要 Mock 被测试的模块

4. **渐进式修复**
   - 优先修复 P0 和 P1，确保关键测试通过
   - P2 可以分批处理

---

## 🔗 相关文件

- `backend/tests/factories/mock_factory.py` - Mock 工厂（已创建）
- `backend/tests/fixtures/test_data_generator.py` - 测试数据生成器（已创建）
- `backend/src/crud/field_whitelist.py` - 白名单功能实现
- `backend/src/security/request_security.py` - 请求安全实现

---

**下一步**: 修复 P0 优先级测试，预计 4.5 小时完成。
