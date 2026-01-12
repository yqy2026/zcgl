# MyPy类型错误修复计划

**生成时间**: 2026-01-12
**错误总数**: 2353个错误，分布在175个文件
**目标**: 分批修复所有类型注解错误，达到85%+类型安全覆盖率

---

## 📊 错误类型分布

| 排名 | 错误类型 | 数量 | 优先级 | 预计工作量 |
|-----|---------|------|-------|-----------|
| 1 | 缺少返回类型注解 `no-untyped-def` | 560 | 🔴 高 | 4小时 |
| 2 | 缺少参数类型注解 | 171 | 🔴 高 | 2小时 |
| 3 | 缺少部分参数类型注解 | 93 | 🟡 中 | 1.5小时 |
| 4 | `dict`缺少类型参数 | 88 | 🟡 中 | 1小时 |
| 5 | Base类无法被Any继承 | 45 | 🟢 低 | 30分钟 |
| 6 | `Callable`缺少类型参数 | 42 | 🟡 中 | 45分钟 |
| 7 | `list`缺少类型参数 | 21 | 🟡 中 | 30分钟 |
| 8 | 类型不匹配赋值 | 80+ | 🟡 中 | 2小时 |

---

## 🎯 修复策略

### 阶段1: 高优先级错误 (预计6.5小时)
**目标**: 修复824个最常见的类型注解错误（35%）

#### 1.1 缺少返回类型注解 (560个错误)
```python
# ❌ Before
def get_contracts(db, skip, limit):
    ...

# ✅ After
def get_contracts(db: Session, skip: int, limit: int) -> list[Contract]:
    ...
```

**优先文件**:
- `src/api/v1/analytics.py` (12个错误)
- `src/api/v1/assets.py` (10个错误)
- `src/api/v1/monitoring.py` (8个错误)

#### 1.2 缺少参数类型注解 (171个错误)
```python
# ❌ Before
def update_status(id, status):
    ...

# ✅ After
def update_status(id: int, status: str) -> bool:
    ...
```

**优先文件**:
- `src/api/v1/assets.py` (8个错误)
- `src/api/v1/collection.py` (6个错误)

---

### 阶段2: 中优先级错误 (预计5小时)
**目标**: 修复泛型和类型参数错误（约350个错误，15%）

#### 2.1 泛型类型参数 (233个错误)
```python
# ❌ Before
def process_items(items: dict):
    ...

def filter_items(items: list):
    ...

# ✅ After
def process_items(items: dict[str, Any]):
    ...

def filter_items(items: list[Asset]):
    ...
```

#### 2.2 Callable类型参数 (42个错误)
```python
# ❌ Before
def register_callback(callback: Callable):
    ...

# ✅ After
def register_callback(callback: Callable[[str], None]):
    ...
```

---

### 阶段3: 低优先级错误 (预计4小时)
**目标**: 修复类型不匹配和其他错误（约1179个错误，50%）

#### 3.1 类型不匹配 (80+个错误)
```python
# ❌ Before
status: str = True
name: str = column_value  # Column[str]

# ✅ After
status: bool = True
name: str = str(column_value)
```

#### 3.2 CRUDBase继承问题 (45个错误)
```python
# ❌ Before
class MyCRUD(CRUDBase[Model, CreateSchema, UpdateSchema], Any):

# ✅ After
class MyCRUD(CRUDBase[Model, CreateSchema, UpdateSchema]):
```

---

## 📋 修复执行计划

### Week 1: 高优先级错误
- [ ] Day 1-2: 修复API路由的返回类型 (560个)
- [ ] Day 3-4: 修复API路由的参数类型 (171个)
- [ ] Day 5: 修复Service层函数类型 (93个)

### Week 2: 中优先级错误
- [ ] Day 1: 修复泛型类型参数 (233个)
- [ ] Day 2: 修复Callable类型 (42个)
- [ ] Day 3: 修复其他类型参数 (88个)

### Week 3: 低优先级错误
- [ ] Day 1-2: 修复类型不匹配 (80+个)
- [ ] Day 3-4: 修复继承和其他问题 (150+个)
- [ ] Day 5: 全量回归测试

---

## 🔧 修复工具和脚本

### 自动化脚本
创建 `backend/scripts/fix_mypy.sh`:
```bash
#!/bin/bash
# 批量添加返回类型注解
find src/api/v1 -name "*.py" -exec sed -i 's/def \([^(]*\)(\([^)]*\)):/def \1(\2) -> None:/g' {} +
```

### MyPy配置优化
```toml
[tool.mypy]
# 分阶段启用严格检查
strict_optional = True
warn_return_any = True
warn_unused_ignores = True
# 暂时禁用的检查（后续启用）
disallow_untyped_defs = False  # Week 1后启用
```

---

## ✅ 验证清单

每个阶段完成后：
- [ ] 本地运行 `uv run mypy src/` - 确认错误数减少
- [ ] 运行 `pytest -m unit` - 确保功能正常
- [ ] 运行 `pytest -m integration` - 确保集成测试通过
- [ ] 提交PR并检查CI状态

---

## 📈 进度跟踪

| 阶段 | 开始时间 | 目标错误数 | 实际修复 | 状态 |
|-----|---------|-----------|---------|------|
| 阶段1 | Week 1 Day 1 | 824 | - | ⏳ 待开始 |
| 阶段2 | Week 2 Day 1 | 350 | - | ⏳ 待开始 |
| 阶段3 | Week 3 Day 1 | 1179 | - | ⏳ 待开始 |

---

## 🎓 最佳实践

### 类型注解规范
1. **公共API必须有完整类型注解**
   ```python
   def create_asset(asset: AssetCreate) -> AssetResponse:  # ✅
   ```

2. **私有函数可以简化**
   ```python
   def _helper(data: dict) -> Any:  # 可接受
   ```

3. **使用类型别名减少重复**
   ```python
   AssetId = int
   ContractList = list[Contract]
   ```

4. **优先使用类型别名而非字符串**
   ```python
   # ❌ 避免
   def process(data: "list[dict]") -> None:

   # ✅ 推荐
   def process(data: list[dict[str, Any]]) -> None:
   ```

---

## 🚀 立即行动

从错误最多的文件开始修复：
1. `src/api/v1/analytics.py` - 50+个错误
2. `src/api/v1/assets.py` - 40+个错误
3. `src/core/router_registry.py` - 30+个错误
