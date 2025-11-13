# 测试文件组织说明

## 测试结构

### 统一测试文件
- `test_api_unified.py` - 统一的API测试（整合simple和enhanced测试）
- `test_database_unified.py` - 统一的数据库测试（整合simple和enhanced测试）

### 测试标记（pytest markers）

使用pytest标记来组织和管理测试：

#### 测试级别标记
- `@pytest.mark.unit` - 单元测试：测试单个函数或类
- `@pytest.mark.integration` - 集成测试：测试模块间协作
- `@pytest.mark.e2e` - 端到端测试：测试完整流程

#### 功能领域标记
- `@pytest.mark.api` - API测试
- `@pytest.mark.database` - 数据库测试
- `@pytest.mark.ocr` - OCR测试
- `@pytest.mark.pdf` - PDF处理测试
- `@pytest.mark.rbac` - 权限测试
- `@pytest.mark.performance` - 性能测试
- `@pytest.mark.core` - 核心功能测试

#### 其他标记
- `@pytest.mark.slow` - 慢速测试：需要较长时间运行

## 运行测试

### 运行所有测试
```bash
pytest
```

### 运行特定级别的测试
```bash
# 只运行单元测试
pytest -m unit

# 只运行集成测试
pytest -m integration

# 只运行端到端测试
pytest -m e2e
```

### 运行特定领域的测试
```bash
# 只运行API测试
pytest -m api

# 只运行数据库测试
pytest -m database

# 只运行OCR测试
pytest -m ocr
```

### 运行组合标记的测试
```bash
# 运行API的单元测试
pytest -m "unit and api"

# 运行数据库的集成测试
pytest -m "integration and database"

# 排除慢速测试
pytest -m "not slow"
```

### 运行特定测试文件
```bash
# 运行统一的API测试
pytest tests/test_api_unified.py

# 运行统一的数据库测试
pytest tests/test_database_unified.py
```

## 测试覆盖率

### 生成覆盖率报告
```bash
# 生成终端报告
pytest --cov=src --cov-report=term-missing

# 生成HTML报告
pytest --cov=src --cov-report=html

# 生成XML报告
pytest --cov=src --cov-report=xml
```

## 废弃的测试文件

以下测试文件已被统一测试文件替代，将在下一个版本中删除：

### API测试
- `test_api_simple.py` → `test_api_unified.py`
- `test_enhanced_api_coverage.py` → `test_api_unified.py`
- `test_api_simple_fixed.py` → `test_api_unified.py`
- `test_api_simple_fixed_v2.py` → `test_api_unified.py`

### 数据库测试
- `test_database_simple.py` → `test_database_unified.py`
- `test_db_simple.py` → `test_database_unified.py`
- `test_enhanced_database_coverage.py` → `test_database_unified.py`

### OCR测试
- `simple_ocr_test.py` - 保留作为基础OCR测试
- `ocr_basic_test.py` - 保留作为基础OCR测试
- `final_ocr_test.py` - 保留作为完整OCR测试

## 迁移指南

### 从simple/enhanced测试迁移到统一测试

1. **更新测试导入**：
   - 从 `test_api_simple.py` 迁移到 `test_api_unified.py`
   - 从 `test_enhanced_api_coverage.py` 迁移到 `test_api_unified.py`

2. **添加测试标记**：
   - 为测试添加适当的pytest标记
   - 使用 `@pytest.mark.unit`, `@pytest.mark.integration` 等

3. **更新测试运行命令**：
   - 使用新的标记来运行特定测试
   - 使用统一的测试文件

## 最佳实践

1. **测试命名**：
   - 使用清晰的测试名称
   - 遵循 `test_功能_场景` 的命名模式

2. **测试组织**：
   - 使用测试类来组织相关测试
   - 使用pytest标记来分类测试

3. **测试独立性**：
   - 确保测试之间相互独立
   - 使用fixtures来设置测试数据

4. **测试覆盖**：
   - 确保核心功能有充分的测试覆盖
   - 定期检查测试覆盖率

5. **测试性能**：
   - 标记慢速测试
   - 优化测试执行时间

