# 布尔值命名规范修复计划

## Summary
一次性修复项目中所有不符合命名规范的布尔值字段，统一使用 `is_`/`has_`/`can_`/`should_` 前缀。

## Steps

### 1. **修复后端 API 响应字段** - 核心 Schema 修复
修改以下 Pydantic Schema 中的布尔字段：

| 文件 | 当前字段 | 修改为 |
|------|---------|--------|
| `schemas/common.py` | `success` | `is_success` |
| `schemas/excel.py` | `valid` | `is_valid` |
| `schemas/backup.py` | `restored` | `is_restored` |
| `schemas/backup.py` | `compress` | `should_compress` |
| `schemas/backup.py` | `confirm` | `should_confirm` |
| `schemas/pdf_import.py` | `success` | `is_success` |
| `schemas/property_certificate.py` | `verified` | `is_verified` |
| `schemas/asset.py` | `update_all` | `should_update_all` |
| `schemas/excel_advanced.py` | `validate_data` | `should_validate_data` |
| `schemas/excel_advanced.py` | `skip_errors` | `should_skip_errors` |
| `schemas/excel_advanced.py` | `include_headers` | `should_include_headers` |
| `schemas/processing_result.py` | `success` | `is_success` |

### 2. **修复后端 API 端点参数** - 函数参数修复
修改 API 端点中的布尔参数名：

| 文件 | 当前参数 | 修改为 |
|------|---------|--------|
| `api/v1/analytics.py` | `include_deleted` | `should_include_deleted` |
| `api/v1/analytics.py` | `use_cache` | `should_use_cache` |
| `api/v1/backup.py` | `confirm` | `should_confirm` |

### 3. **修复后端 Service 层** - 内部变量修复
修改 Service 层中的布尔变量：

| 文件 | 当前变量 | 修改为 |
|------|---------|--------|
| `services/analytics/analytics_service.py` | `use_cache` | `should_use_cache` |
| `services/excel/excel_import_service.py` | `validate_data` | `should_validate_data` |
| `services/excel/excel_import_service.py` | `create_assets` | `should_create_assets` |
| `services/excel/excel_import_service.py` | `update_existing` | `should_update_existing` |
| `services/excel/excel_import_service.py` | `skip_errors` | `should_skip_errors` |

### 4. **修复前端类型定义** - TypeScript Types 修复
修改前端类型定义中的布尔字段：

| 文件 | 当前字段 | 修改为 |
|------|---------|--------|
| `types/apiResponse.ts` | `success` | `isSuccess` |
| `types/auth.ts` | `remember` | `shouldRemember` |

### 5. **修复前端 Hooks** - 状态变量修复
修改 React Hooks 中的布尔状态：

| 文件 | 当前变量 | 修改为 |
|------|---------|--------|
| `hooks/useDictionary.ts` | `loading` | `isLoading` |
| `utils/logger.ts` | `enabled` | `isEnabled` |

### 6. **修复前端组件** - 组件 Props 修复
修改组件中的布尔 props 和状态：

| 文件 | 当前字段 | 修改为 |
|------|---------|--------|
| `components/Forms/AssetForm.tsx` | `loading` | `isLoading` |

### 7. **全局搜索验证** - 确保无遗漏
执行全局搜索验证所有修复完成：
```bash
# 后端验证
cd backend && ruff check . && mypy src

# 前端验证
cd frontend && pnpm type-check && pnpm lint
```

### 8. **更新单元测试** - 测试用例同步
更新所有相关测试文件中的字段名引用。

### 9. **运行完整测试套件** - 验证修复
```bash
cd backend && pytest -m unit
cd frontend && pnpm test
```

## 预计影响

| 层 | 文件数 | 修改点数 |
|----|--------|---------|
| 后端 Schema | ~10 | ~15 |
| 后端 API | ~5 | ~8 |
| 后端 Service | ~5 | ~10 |
| 前端 Types | ~5 | ~8 |
| 前端 Hooks/Utils | ~5 | ~5 |
| 前端 Components | ~10 | ~15 |
| 测试文件 | ~20 | ~50 |
| **总计** | **~60** | **~111** |

## 注意事项

1. **不修改框架参数**: SQLAlchemy、Pydantic 内置参数保持原样
2. **前后端同步**: 每个 API 字段修改需同步更新前端调用
3. **测试覆盖**: 确保所有修改都有对应的测试更新
