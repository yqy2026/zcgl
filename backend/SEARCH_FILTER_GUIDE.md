# 搜索和筛选功能指南

## 概述

土地物业资产管理系统提供了强大的搜索和筛选功能，帮助用户快速找到所需的资产信息。

## 搜索功能

### 全文搜索

使用 `search` 参数进行全文搜索，系统会在以下字段中查找匹配的内容：

- 物业名称 (`property_name`)
- 所在地址 (`address`)
- 权属方 (`ownership_entity`)
- 经营管理方 (`management_entity`)
- 实际用途 (`actual_usage`)
- 业态类别 (`business_category`)
- 租户名称 (`tenant_name`)
- 五羊运营项目名称 (`wuyang_project_name`)
- 说明 (`description`)

**示例：**
```
GET /api/v1/assets/?search=广州
GET /api/v1/assets/?search=商业
GET /api/v1/assets/?search=国资集团
```

### 搜索特性

- **模糊匹配**：支持部分关键词匹配
- **大小写不敏感**：搜索时忽略大小写
- **多字段搜索**：一次搜索覆盖多个字段
- **中文支持**：完全支持中文搜索

## 筛选功能

### 基础筛选条件

#### 1. 确权状态筛选 (`ownership_status`)
- `已确权`：已完成确权登记的资产
- `未确权`：尚未完成确权登记的资产
- `部分确权`：部分完成确权登记的资产

**示例：**
```
GET /api/v1/assets/?ownership_status=已确权
```

#### 2. 物业性质筛选 (`property_nature`)
- `经营类`：用于经营活动的物业
- `非经营类`：非经营用途的物业

**示例：**
```
GET /api/v1/assets/?property_nature=经营类
```

#### 3. 使用状态筛选 (`usage_status`)
- `出租`：已出租的物业
- `闲置`：空置未使用的物业
- `自用`：自己使用的物业
- `公房`：公共用房
- `其他`：其他使用状态

**示例：**
```
GET /api/v1/assets/?usage_status=出租
```

#### 4. 权属方筛选 (`ownership_entity`)
按具体的权属方名称筛选资产。

**示例：**
```
GET /api/v1/assets/?ownership_entity=国资集团
```

#### 5. 经营管理方筛选 (`management_entity`)
按具体的经营管理方名称筛选资产。

**示例：**
```
GET /api/v1/assets/?management_entity=五羊公司
```

#### 6. 业态类别筛选 (`business_category`)
按业态类别筛选资产。

**示例：**
```
GET /api/v1/assets/?business_category=商业
```

### 高级筛选条件

#### 7. 面积范围筛选
- `min_area`：最小面积（平方米）
- `max_area`：最大面积（平方米）

**示例：**
```
GET /api/v1/assets/?min_area=100&max_area=1000
```

#### 8. 涉诉状态筛选 (`is_litigated`)
- `是`：涉及诉讼的资产
- `否`：未涉及诉讼的资产

**示例：**
```
GET /api/v1/assets/?is_litigated=否
```

## 组合筛选

可以同时使用多个筛选条件进行组合查询：

**示例：**
```
GET /api/v1/assets/?ownership_status=已确权&property_nature=经营类&usage_status=出租&min_area=500
```

这个查询会返回：已确权、经营类、已出租、面积大于500平方米的资产。

## 排序功能

### 排序参数

- `sort_field`：排序字段
- `sort_order`：排序方向（`asc` 升序，`desc` 降序）

### 支持的排序字段

- `created_at`：创建时间（默认）
- `updated_at`：更新时间
- `property_name`：物业名称
- `ownership_entity`：权属方
- `actual_property_area`：实际房产面积
- `rentable_area`：可出租面积
- `rented_area`：已出租面积
- `occupancy_rate`：出租率

**示例：**
```
GET /api/v1/assets/?sort_field=actual_property_area&sort_order=desc
GET /api/v1/assets/?sort_field=property_name&sort_order=asc
```

## 分页功能

### 分页参数

- `page`：页码（从1开始，默认：1）
- `limit`：每页记录数（默认：20，最大：100）

**示例：**
```
GET /api/v1/assets/?page=2&limit=50
```

### 分页响应信息

响应中包含分页相关信息：

```json
{
  "data": [...],
  "total": 150,
  "page": 2,
  "limit": 50,
  "has_next": true,
  "has_prev": true
}
```

## 复杂查询示例

### 示例1：查找广州地区的已确权商业物业
```
GET /api/v1/assets/?search=广州&ownership_status=已确权&business_category=商业
```

### 示例2：查找面积在500-2000平方米之间的出租物业，按面积降序排列
```
GET /api/v1/assets/?usage_status=出租&min_area=500&max_area=2000&sort_field=actual_property_area&sort_order=desc
```

### 示例3：查找国资集团的经营类物业，每页显示30条
```
GET /api/v1/assets/?ownership_entity=国资集团&property_nature=经营类&limit=30
```

### 示例4：搜索包含"五羊"的项目，筛选已确权且未涉诉的资产
```
GET /api/v1/assets/?search=五羊&ownership_status=已确权&is_litigated=否
```

## 性能优化

### 索引优化

系统已为以下字段创建了数据库索引以提高查询性能：

- `ownership_entity`（权属方）
- `property_nature`（物业性质）
- `usage_status`（使用状态）
- `ownership_status`（确权状态）
- `created_at`（创建时间）
- `actual_property_area`（实际房产面积）

### 查询建议

1. **使用具体的筛选条件**：避免只使用搜索而不使用筛选条件
2. **合理设置分页大小**：建议每页不超过50条记录
3. **优先使用索引字段**：使用已建立索引的字段进行筛选和排序
4. **避免过于宽泛的搜索**：使用更具体的搜索关键词

## 错误处理

### 常见错误

1. **无效的排序字段**
   ```json
   {
     "error": "Invalid sort field",
     "message": "排序字段不存在"
   }
   ```

2. **无效的筛选值**
   ```json
   {
     "error": "Invalid filter value",
     "message": "筛选条件值无效"
   }
   ```

3. **分页参数错误**
   ```json
   {
     "error": "Invalid pagination",
     "message": "页码必须大于0"
   }
   ```

## API响应格式

### 成功响应

```json
{
  "data": [
    {
      "id": "asset-id-1",
      "property_name": "测试物业",
      "ownership_entity": "国资集团",
      "ownership_status": "已确权",
      "property_nature": "经营类",
      "actual_property_area": 1000.0,
      "created_at": "2024-01-01T10:00:00Z"
    }
  ],
  "total": 1,
  "page": 1,
  "limit": 20,
  "has_next": false,
  "has_prev": false
}
```

### 空结果响应

```json
{
  "data": [],
  "total": 0,
  "page": 1,
  "limit": 20,
  "has_next": false,
  "has_prev": false
}
```

## 使用技巧

1. **渐进式筛选**：先使用大类筛选，再逐步细化条件
2. **保存常用查询**：将常用的筛选条件组合保存为书签
3. **结合统计功能**：使用统计API了解数据分布，指导筛选策略
4. **监控查询性能**：关注查询响应时间，适时调整查询策略