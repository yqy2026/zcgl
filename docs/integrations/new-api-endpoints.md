# 新增API端点文档

## 概述

本文档描述了为解决前后端不一致问题而新增的API端点，包括详细的请求/响应格式和使用示例。

## 新增端点

### 1. 获取所有资产（不分页）

**端点**: `GET /api/v1/assets/all`

**描述**: 获取所有资产列表，不分页，用于数据导出等场景。支持搜索、过滤和排序。

**请求参数**:
| 参数名 | 类型 | 必填 | 默认值 | 描述 |
|---------|------|------|---------|------|
| search | string | 否 | - | 搜索关键字（物业名称、地址等） |
| ownership_status | string | 否 | - | 确权状态过滤 |
| usage_status | string | 否 | - | 使用状态过滤 |
| property_nature | string | 否 | - | 物业性质过滤 |
| business_category | string | 否 | - | 业态类别过滤 |
| sort_by | string | 否 | created_at | 排序字段 |
| sort_order | string | 否 | desc | 排序顺序（asc/desc） |
| limit | integer | 否 | 10000 | 最大返回数量（1-50000） |

**响应格式**:
```json
{
  "success": true,
  "data": [
    {
      "id": "asset-id-1",
      "ownership_id": "ownership-id-1",
      "ownership_entity": "权属方名称",
      "property_name": "物业名称",
      "address": "物业地址",
      "rentable_area": 100.0,
      "rented_area": 80.0,
      "unrented_area": 20.0,  // 计算字段，不存储在数据库
      "occupancy_rate": 80.00,  // 计算字段，不存储在数据库
      "created_at": "2025-10-23T12:00:00Z",
      "updated_at": "2025-10-23T12:00:00Z"
    }
  ],
  "message": "成功获取X个资产"
}
```

**使用示例**:
```bash
# 获取所有资产
GET /api/v1/assets/all

# 带搜索条件
GET /api/v1/assets/all?search=商业广场&ownership_status=已确权

# 带排序
GET /api/v1/assets/all?sort_by=property_name&sort_order=asc

# 限制返回数量
GET /api/v1/assets/all?limit=1000
```

### 2. 根据ID列表获取资产

**端点**: `POST /api/v1/assets/by-ids`

**描述**: 根据资产ID列表批量获取资产信息。

**请求体**:
```json
{
  "ids": ["asset-id-1", "asset-id-2", "asset-id-3"]
}
```

**响应格式**:
```json
{
  "success": true,
  "data": [
    {
      "id": "asset-id-1",
      "ownership_id": "ownership-id-1",
      "ownership_entity": "权属方名称",
      "property_name": "物业名称",
      "unrented_area": 20.0,  // 计算字段
      "occupancy_rate": 80.00   // 计算字段
    }
  ],
  "message": "成功获取X个资产"
}
```

**使用示例**:
```bash
# 根据ID列表获取资产
POST /api/v1/assets/by-ids
Content-Type: application/json

{
  "ids": ["asset-1", "asset-2"]
}
```

**特殊情况**:
- 空ID列表: 返回空数组
- 不存在的ID: 只返回存在的资产信息
- 部分ID不存在: 返回能找到的资产信息

## 计算字段说明

### unrented_area（未出租面积）
- **类型**: decimal(12, 2)
- **计算公式**: `rentable_area - rented_area`
- **最小值**: 0（不会出现负数）
- **描述**: 可出租面积减去已出租面积

### occupancy_rate（出租率）
- **类型**: decimal(5, 2)
- **计算公式**: `(rented_area / rentable_area) * 100`
- **范围**: 0-100.00
- **特殊处理**:
  - 当 `include_in_occupancy_rate = false` 时，返回 0
  - 当 `rentable_area = 0` 时，返回 0
  - 当 `rentable_area` 为空时，返回 0

## 错误处理

### HTTP状态码
- **200**: 成功
- **400**: 请求参数错误（如limit超出范围）
- **500**: 服务器内部错误

### 错误响应格式
```json
{
  "detail": "错误描述信息"
}
```

## 参数验证规则

### limit参数
- 类型: integer
- 范围: 1-50000
- 默认值: 10000

### sort_order参数
- 类型: string
- 枚举值: asc, desc
- 默认值: desc

### search参数
- 类型: string
- 最大长度: 500
- 搜索字段: property_name, address, ownership_entity(通过权属表名称), business_category

## 性能考虑

1. **分页建议**: 对于大量数据，建议使用分页端点 `/api/v1/assets` 而不是此端点
2. **索引优化**: 搜索字段已建立索引以提高查询性能
3. **缓存策略**: 建议对频繁查询的结果实施缓存
4. **内存使用**: 大量数据查询可能消耗较多内存，建议合理设置limit参数

## 版本信息

- **API版本**: v1
- **添加版本**: 2025-10-23
- **兼容性**: 向后兼容
- **变更类型**: 新增功能

## 测试覆盖

已创建以下测试用例：
- 获取所有资产成功场景
- 带过滤条件查询
- 空结果处理
- 根据ID列表查询
- 参数验证
- 错误处理
- 计算字段正确性
- 响应格式一致性
