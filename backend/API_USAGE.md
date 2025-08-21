# 资产管理API使用指南

## 基础信息

- **基础URL**: `http://localhost:8001`
- **API版本**: `v1`
- **API前缀**: `/api/v1`

## 认证

当前版本暂不需要认证，后续版本将添加JWT认证。

## 资产管理API端点

### 1. 创建资产

**POST** `/api/v1/assets/`

创建新的资产记录。

**请求体示例：**
```json
{
  "ownership_entity": "国资集团",
  "management_entity": "五羊公司",
  "property_name": "测试物业",
  "address": "广州市天河区测试路123号",
  "actual_property_area": 1000.0,
  "rentable_area": 800.0,
  "rented_area": 600.0,
  "unrented_area": 200.0,
  "non_commercial_area": 200.0,
  "ownership_status": "已确权",
  "actual_usage": "商业",
  "usage_status": "出租",
  "is_litigated": "否",
  "property_nature": "经营类",
  "occupancy_rate": "75%"
}
```

**响应示例：**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "ownership_entity": "国资集团",
  "management_entity": "五羊公司",
  "property_name": "测试物业",
  "address": "广州市天河区测试路123号",
  "actual_property_area": 1000.0,
  "rentable_area": 800.0,
  "rented_area": 600.0,
  "unrented_area": 200.0,
  "non_commercial_area": 200.0,
  "ownership_status": "已确权",
  "actual_usage": "商业",
  "usage_status": "出租",
  "is_litigated": "否",
  "property_nature": "经营类",
  "occupancy_rate": "75%",
  "version": 1,
  "created_at": "2024-01-01T10:00:00Z",
  "updated_at": "2024-01-01T10:00:00Z"
}
```

### 2. 获取资产列表

**GET** `/api/v1/assets/`

获取资产列表，支持分页、搜索和筛选。

**查询参数：**
- `page`: 页码（默认：1）
- `limit`: 每页记录数（默认：20，最大：100）
- `search`: 搜索关键词
- `ownership_status`: 确权状态筛选
- `property_nature`: 物业性质筛选
- `usage_status`: 使用状态筛选
- `ownership_entity`: 权属方筛选
- `sort_field`: 排序字段（默认：created_at）
- `sort_order`: 排序方向（asc/desc，默认：desc）

**请求示例：**
```
GET /api/v1/assets/?page=1&limit=10&search=测试&ownership_status=已确权
```

**响应示例：**
```json
{
  "data": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "property_name": "测试物业",
      "ownership_entity": "国资集团",
      "ownership_status": "已确权",
      "created_at": "2024-01-01T10:00:00Z"
    }
  ],
  "total": 1,
  "page": 1,
  "limit": 10,
  "has_next": false,
  "has_prev": false
}
```

### 3. 获取单个资产详情

**GET** `/api/v1/assets/{asset_id}`

根据ID获取单个资产的详细信息。

**请求示例：**
```
GET /api/v1/assets/550e8400-e29b-41d4-a716-446655440000
```

**响应示例：**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "ownership_entity": "国资集团",
  "property_name": "测试物业",
  "address": "广州市天河区测试路123号",
  "actual_property_area": 1000.0,
  "ownership_status": "已确权",
  "property_nature": "经营类",
  "created_at": "2024-01-01T10:00:00Z",
  "updated_at": "2024-01-01T10:00:00Z"
}
```

### 4. 更新资产信息

**PUT** `/api/v1/assets/{asset_id}`

更新资产信息，支持部分更新。

**请求体示例：**
```json
{
  "property_name": "更新后的物业名称",
  "actual_property_area": 1200.0,
  "occupancy_rate": "80%"
}
```

**响应示例：**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "property_name": "更新后的物业名称",
  "actual_property_area": 1200.0,
  "occupancy_rate": "80%",
  "version": 2,
  "updated_at": "2024-01-01T11:00:00Z"
}
```

### 5. 删除资产

**DELETE** `/api/v1/assets/{asset_id}`

删除指定的资产记录。

**请求示例：**
```
DELETE /api/v1/assets/550e8400-e29b-41d4-a716-446655440000
```

**响应：**
- 状态码：204 No Content
- 响应体：空

### 6. 获取资产变更历史

**GET** `/api/v1/assets/{asset_id}/history`

获取资产的变更历史记录。

**请求示例：**
```
GET /api/v1/assets/550e8400-e29b-41d4-a716-446655440000/history
```

**响应示例：**
```json
{
  "asset_id": "550e8400-e29b-41d4-a716-446655440000",
  "history": [
    {
      "id": "hist-001",
      "change_type": "create",
      "changed_fields": ["property_name", "ownership_entity"],
      "old_values": {},
      "new_values": {
        "property_name": "测试物业",
        "ownership_entity": "国资集团"
      },
      "changed_by": "system",
      "changed_at": "2024-01-01T10:00:00Z",
      "reason": "创建新资产"
    }
  ]
}
```

### 7. 获取资产统计摘要

**GET** `/api/v1/assets/stats/summary`

获取资产的统计摘要信息。

**请求示例：**
```
GET /api/v1/assets/stats/summary
```

**响应示例：**
```json
{
  "total_assets": 100,
  "ownership_status": {
    "confirmed": 80,
    "unconfirmed": 15,
    "partial": 5
  },
  "property_nature": {
    "commercial": 70,
    "non_commercial": 30
  },
  "usage_status": {
    "rented": 60,
    "vacant": 25
  }
}
```

## 错误响应

所有API端点在出错时都会返回统一格式的错误响应：

```json
{
  "error": "错误类型",
  "message": "错误描述信息",
  "timestamp": "2024-01-01T10:00:00Z"
}
```

### 常见错误码

- **400 Bad Request**: 请求参数错误或业务逻辑错误
- **404 Not Found**: 资产不存在
- **409 Conflict**: 资产名称重复
- **422 Unprocessable Entity**: 请求数据验证失败
- **500 Internal Server Error**: 服务器内部错误

## 数据验证

### 必填字段

创建资产时，以下字段为必填：
- `ownership_entity`: 权属方
- `property_name`: 物业名称
- `address`: 所在地址
- `actual_property_area`: 实际房产面积
- `rentable_area`: 经营性物业可出租面积
- `rented_area`: 经营性物业已出租面积
- `unrented_area`: 经营性物业未出租面积
- `non_commercial_area`: 非经营物业面积
- `ownership_status`: 确权状态
- `actual_usage`: 实际用途
- `usage_status`: 使用状态
- `is_litigated`: 是否涉诉
- `property_nature`: 物业性质
- `occupancy_rate`: 出租率

### 枚举值

- `ownership_status`: "已确权", "未确权", "部分确权"
- `usage_status`: "出租", "闲置", "自用", "公房", "其他"
- `property_nature`: "经营类", "非经营类"
- `is_litigated`: "是", "否"

### 数值验证

- 所有面积字段必须大于等于0
- `actual_property_area` 必须大于0
- `rented_area` 不能超过 `rentable_area`
- `unrented_area` 不能超过 `rentable_area`

## API文档

访问以下URL查看完整的API文档：

- **Swagger UI**: http://localhost:8001/docs
- **ReDoc**: http://localhost:8001/redoc
- **OpenAPI JSON**: http://localhost:8001/openapi.json