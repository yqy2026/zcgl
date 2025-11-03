# API文档分析报告

**生成时间**: 2025-11-03 13:16:11
**分析范围**: 33 个模块，30 个端点

## 概览统计
- **总模块数**: 33
- **总端点数**: 30
- **平均每模块端点数**: 0.9
- **模块文档覆盖率**: 100.0%
- **端点文档覆盖率**: 100.0%

## HTTP方法分布
- **DELETE**: 1 个端点
- **GET**: 20 个端点
- **POST**: 6 个端点
- **PUT**: 3 个端点

## 模块详情

### rent_contract
**文件**: `src\api\v1\rent_contract.py`
**端点数**: 22
**有文档**: 是
**端点列表**:
- `POST /contracts` 是 - 创建租金合同
- `GET /contracts/{contract_id}` 是 - 获取租金合同详情
- `GET /contracts` 是 - 获取租金合同列表
- `PUT /contracts/{contract_id}` 是 - 更新租金合同
- `DELETE /contracts/{contract_id}` 是 - 删除租金合同
- `GET /contracts/{contract_id}/terms` 是 - 获取合同租金条款
- `POST /contracts/{contract_id}/terms` 是 - 添加租金条款
- `POST /ledger/generate` 是 - 生成月度台账
- `GET /ledger` 是 - 获取租金台账列表
- `GET /ledger/{ledger_id}` 是 - 获取租金台账详情
- `PUT /ledger/{ledger_id}` 是 - 更新租金台账
- `PUT /ledger/batch` 是 - 批量更新租金台账
- `GET /statistics/overview` 是 - 获取租金统计概览
- `GET /statistics/ownership` 是 - 权属方租金统计
- `GET /statistics/asset` 是 - 资产租金统计
- `GET /statistics/monthly` 是 - 月度租金统计
- `GET /statistics/export` 是 - 导出统计数据
- `GET /contracts/{contract_id}/ledger` 是 - 获取合同台账
- `GET /assets/{asset_id}/contracts` 是 - 获取资产合同
- `GET /excel/template` 是 - 下载Excel导入模板
- `POST /excel/import` 是 - Excel导入合同数据
- `GET /excel/export` 是 - Excel导出合同数据

### performance
**文件**: `src\api\v1\performance.py`
**端点数**: 4
**有文档**: 是
**端点列表**:
- `GET /analyze` 是 - 分析数据库性能
- `POST /optimize` 是 - 优化数据库性能
- `GET /statistics` 是 - 获取性能统计信息
- `POST /indexes` 是 - 创建性能优化索引

### statistics
**文件**: `src\api\v1\statistics.py`
**端点数**: 4
**有文档**: 是
**端点列表**:
- `GET /occupancy-rate/overall` 是 - 获取整体出租率统计
- `GET /occupancy-rate/by-category` 是 - 按类别获取出租率统计
- `GET /area-summary` 是 - 获取面积汇总统计
- `GET /financial-summary` 是 - 获取财务汇总统计

### admin
**文件**: `src\api\v1\admin.py`
**端点数**: 0
**有文档**: 是

### analytics
**文件**: `src\api\v1\analytics.py`
**端点数**: 0
**有文档**: 是

### assets
**文件**: `src\api\v1\assets.py`
**端点数**: 0
**有文档**: 是

### auth
**文件**: `src\api\v1\auth.py`
**端点数**: 0
**有文档**: 是

### auth_clean
**文件**: `src\api\v1\auth_clean.py`
**端点数**: 0
**有文档**: 是

### backup
**文件**: `src\api\v1\backup.py`
**端点数**: 0
**有文档**: 是

### chinese_ocr
**文件**: `src\api\v1\chinese_ocr.py`
**端点数**: 0
**有文档**: 是

### custom_fields
**文件**: `src\api\v1\custom_fields.py`
**端点数**: 0
**有文档**: 是

### defect_tracking
**文件**: `src\api\v1\defect_tracking.py`
**端点数**: 0
**有文档**: 是

### dictionaries
**文件**: `src\api\v1\dictionaries.py`
**端点数**: 0
**有文档**: 是

### enum_field
**文件**: `src\api\v1\enum_field.py`
**端点数**: 0
**有文档**: 是

### error_recovery
**文件**: `src\api\v1\error_recovery.py`
**端点数**: 0
**有文档**: 是

### excel
**文件**: `src\api\v1\excel.py`
**端点数**: 0
**有文档**: 是

### export
**文件**: `src\api\v1\export.py`
**端点数**: 0
**有文档**: 是

### fast_response_optimized
**文件**: `src\api\v1\fast_response_optimized.py`
**端点数**: 0
**有文档**: 是

### history
**文件**: `src\api\v1\history.py`
**端点数**: 0
**有文档**: 是

### monitoring
**文件**: `src\api\v1\monitoring.py`
**端点数**: 0
**有文档**: 是

### occupancy
**文件**: `src\api\v1\occupancy.py`
**端点数**: 0
**有文档**: 是

### optimized_endpoints
**文件**: `src\api\v1\optimized_endpoints.py`
**端点数**: 0
**有文档**: 是

### organization
**文件**: `src\api\v1\organization.py`
**端点数**: 0
**有文档**: 是

### ownership
**文件**: `src\api\v1\ownership.py`
**端点数**: 0
**有文档**: 是

### pdf_import_unified
**文件**: `src\api\v1\pdf_import_unified.py`
**端点数**: 0
**有文档**: 是

### pdf_monitoring
**文件**: `src\api\v1\pdf_monitoring.py`
**端点数**: 0
**有文档**: 是

### project
**文件**: `src\api\v1\project.py`
**端点数**: 0
**有文档**: 是

### system_dictionaries
**文件**: `src\api\v1\system_dictionaries.py`
**端点数**: 0
**有文档**: 是

### system_monitoring
**文件**: `src\api\v1\system_monitoring.py`
**端点数**: 0
**有文档**: 是

### system_settings
**文件**: `src\api\v1\system_settings.py`
**端点数**: 0
**有文档**: 是

### tasks
**文件**: `src\api\v1\tasks.py`
**端点数**: 0
**有文档**: 是

### test_coverage
**文件**: `src\api\v1\test_coverage.py`
**端点数**: 0
**有文档**: 是

### test_performance
**文件**: `src\api\v1\test_performance.py`
**端点数**: 0
**有文档**: 是

## 文档缺失问题

### 中优先级问题
- **src\api\v1\performance.py**: 端点 GET /analyze 缺少summary描述
- **src\api\v1\performance.py**: 端点 POST /optimize 缺少summary描述
- **src\api\v1\performance.py**: 端点 GET /statistics 缺少summary描述
- **src\api\v1\performance.py**: 端点 POST /indexes 缺少summary描述
- **src\api\v1\statistics.py**: 端点 GET /occupancy-rate/overall 缺少summary描述
- **src\api\v1\statistics.py**: 端点 GET /occupancy-rate/by-category 缺少summary描述
- **src\api\v1\statistics.py**: 端点 GET /area-summary 缺少summary描述
- **src\api\v1\statistics.py**: 端点 GET /financial-summary 缺少summary描述

## 改进建议
1. **优先为缺失文档的端点添加docstring**
2. **统一API文档格式，使用OpenAPI规范**
3. **为复杂端点添加参数和响应示例**
4. **建立自动化文档检查工具**
5. **定期审查和更新文档内容**