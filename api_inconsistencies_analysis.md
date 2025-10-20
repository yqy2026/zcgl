# API前后端不一致问题分析报告

## 1. 路径不一致问题

### 1.1 严重不匹配 - 后端不存在的端点
以下前端调用的API端点在后端中不存在：

#### 统计模块严重不匹配
- ❌ `GET /statistics/dashboard` - 前端调用，后端不存在
- ❌ `GET /statistics/ownership-distribution` - 前端调用，后端不存在
- ❌ `GET /statistics/property-nature-distribution` - 前端调用，后端不存在
- ❌ `GET /statistics/usage-status-distribution` - 前端调用，后端不存在
- ❌ `GET /statistics/asset-distribution` - 前端调用，后端不存在
- ❌ `GET /statistics/area-statistics` - 前端调用，后端不存在
- ❌ `GET /statistics/trend/{metric}` - 前端调用，后端不存在
- ❌ `POST /statistics/report/{reportType}` - 前端调用，后端不存在
- ❌ `GET /statistics/comparison/{metric}` - 前端调用，后端不存在

#### 字典管理模块路径不匹配
- ❌ `GET /system-dictionaries` - 前端调用，后端是 `/system-dictionaries` (但实际应该是 `/dictionaries`)
- ❌ `POST /system-dictionaries` - 前端调用，后端是 `/system-dictionaries` (但实际应该是 `/dictionaries`)
- ❌ `PUT /system-dictionaries/{id}` - 前端调用，后端是 `/system-dictionaries` (但实际应该是 `/dictionaries`)
- ❌ `DELETE /system-dictionaries/{id}` - 前端调用，后端是 `/system-dictionaries` (但实际应该是 `/dictionaries`)
- ❌ `POST /system-dictionaries/batch-update` - 前端调用，后端不存在
- ❌ `GET /system-dictionaries/types/list` - 前端调用，后端不存在

#### 资产模块不匹配
- ❌ `POST /assets/import` - 前端调用，后端不存在
- ❌ `POST /assets/batch-update` - 前端调用，后端不存在
- ❌ `POST /assets/validate` - 前端调用，后端不存在
- ❌ `POST /assets/batch-custom-fields` - 前端调用，后端不存在

#### Excel扩展功能不匹配
- ❌ `GET /excel/export-status/{taskId}` - 前端调用，后端不存在
- ❌ `GET /excel/export-history` - 前端调用，后端不存在
- ❌ `DELETE /excel/export-history/{id}` - 前端调用，后端不存在
- ❌ `GET /excel/import-status/{importId}` - 前端调用，后端不存在
- ❌ `GET /excel/import-history` - 前端调用，后端不存在
- ❌ `DELETE /excel/import-history/{id}` - 前端调用，后端不存在
- ❌ `POST /excel/import/cancel/{taskId}` - 前端调用，后端不存在
- ❌ `POST /excel/export/cancel/{taskId}` - 前端调用，后端不存在
- ❌ `POST /excel/validate` - 前端调用，后端不存在
- ❌ `GET /excel/formats` - 前端调用，后端不存在
- ❌ `GET /excel/field-mapping` - 前端调用，后端不存在
- ❌ `POST /excel/field-mapping` - 前端调用，后端不存在

#### 备份模块不匹配
- ❌ 所有 `/backup/*` 端点 - 前端调用，但后端在 `/api/v1/backup/*`

#### 自定义字段模块不匹配
- ❌ `POST /asset-custom-fields/validate` - 前端调用，后端存在
- ❌ `GET /assets/{assetId}/custom-fields` - 前端调用，后端存在
- ❌ `PUT /assets/{assetId}/custom-fields` - 前端调用，后端存在
- ❌ `POST /assets/batch-custom-fields` - 前端调用，后端不存在

#### 路径格式错误
- ❌ `POST /ownershipssearch` - 应该是 `/ownerships/search`
- ❌ `POST /projectssearch` - 应该是 `/projects/search`
- ❌ `GET /ownershipsstatistics/summary` - 应该是 `/ownerships/statistics/summary`
- ❌ `GET /ownershipsdropdown-options` - 应该是 `/ownerships/dropdown-options`
- ❌ `GET /projectsstatistics/summary` - 应该是 `/projects/statistics/summary`
- ❌ `GET /projectsdropdown-options` - 应该是 `/projects/dropdown-options`

### 1.2 已修复的问题
- ✅ `GET /statistics/occupancy-rate` - 已修复为 `/statistics/occupancy-rate/overall`

## 2. 影响评估

### 2.1 高优先级问题
1. **统计模块功能几乎完全不可用** - 9个关键统计端点缺失
2. **字典管理功能混乱** - 路径命名不一致
3. **Excel高级功能缺失** - 状态跟踪、历史记录等功能不可用

### 2.2 中优先级问题
1. **资产批量操作功能** - 批量更新、验证等功能缺失
2. **自定义字段批量操作** - 部分功能缺失

### 2.3 低优先级问题
1. **路径格式错误** - 容易修复的路径问题

## 3. 修复建议

### 3.1 立即修复
1. 修复所有路径格式错误（缺少斜杠的问题）
2. 统一字典管理API路径
3. 实现缺失的基础统计端点

### 3.2 中期修复
1. 实现Excel高级功能端点
2. 实现资产批量操作端点
3. 完善自定义字段功能

### 3.3 长期优化
1. 重新设计统计API架构
2. 完善API文档和测试
3. 建立API一致性检查机制