# API设计指南

## 概述

本指南定义了土地物业管理资产系统的API设计原则和规范，确保API的一致性、可维护性和易用性。

## 设计原则

### 1. RESTful设计

- 使用标准HTTP方法 (GET, POST, PUT, DELETE)
- 使用名词而非动词作为资源名
- 使用复数形式表示资源集合
- 使用HTTP状态码表示操作结果
- 支持HATEOAS (Hypermedia as the Engine of Application State)

### 2. 一致性原则

- 统一的命名规范
- 一致的响应格式
- 标准化的错误处理
- 一致的分页机制

### 3. 可扩展性原则

- 版本控制支持
- 灵活的查询参数
- 可扩展的响应结构
- 向后兼容保证

## URL设计规范

### 1. 基本结构

```
https://api.zcgl.com/api/v1/{resource}/{id}/{sub-resource}/{sub-id}
```

### 2. 资源命名

```typescript
// ✅ 正确示例
GET    /api/v1/assets              // 获取资产列表
POST   /api/v1/assets              // 创建资产
GET    /api/v1/assets/{id}         // 获取单个资产
PUT    /api/v1/assets/{id}         // 更新资产
DELETE /api/v1/assets/{id}         // 删除资产

// ❌ 错误示例
GET    /api/v1/getAssets           // 使用动词
GET    /api/v1/asset               // 使用单数
POST   /api/v1/assets/create       // 冗余路径
```

### 3. 嵌套资源

```typescript
// ✅ 正确示例
GET    /api/v1/assets/{id}/documents        // 获取资产文档
POST   /api/v1/assets/{id}/documents        // 为资产添加文档
PUT    /api/v1/assets/{id}/documents/{doc_id}  // 更新资产文档

// ✅ 合理的嵌套深度（不超过2层）
GET    /api/v1/projects/{id}/assets/{asset_id}/contracts

// ❌ 过深的嵌套
GET    /api/v1/projects/{id}/assets/{asset_id}/contracts/{contract_id}/payments/{payment_id}
```

### 4. 查询参数

```typescript
// 分页参数
GET /api/v1/assets?page=1&limit=20

// 排序参数
GET /api/v1/assets?sort_by=created_at&order=desc

// 筛选参数
GET /api/v1/assets?ownership_status=已确权&property_nature=经营性

// 字段选择
GET /api/v1/assets?fields=id,property_name,address

// 搜索参数
GET /api/v1/assets?search=关键词

// 复杂筛选
GET /api/v1/assets?filters[ownership_status]=已确权&filters[property_nature]=经营性
```

## HTTP方法使用

### 1. 标准方法

| 方法 | 用途 | 幂等性 | 安全性 |
|------|------|--------|--------|
| GET | 获取资源 | ✅ | ✅ |
| POST | 创建资源 | ❌ | ❌ |
| PUT | 完整更新资源 | ✅ | ❌ |
| PATCH | 部分更新资源 | ❌ | ❌ |
| DELETE | 删除资源 | ✅ | ❌ |

### 2. 使用示例

```typescript
// GET - 获取资源
GET /api/v1/assets                    // 获取资产列表
GET /api/v1/assets/{id}               // 获取单个资产

// POST - 创建资源
POST /api/v1/assets                   // 创建资产
POST /api/v1/assets/batch-update      // 批量操作

// PUT - 完整更新
PUT /api/v1/assets/{id}               // 完整更新资产信息

// PATCH - 部分更新
PATCH /api/v1/assets/{id}             // 更新资产的特定字段

// DELETE - 删除资源
DELETE /api/v1/assets/{id}            // 删除资产
```

## 请求格式

### 1. Content-Type

```typescript
// JSON请求
Content-Type: application/json

// 文件上传
Content-Type: multipart/form-data

// 表单提交
Content-Type: application/x-www-form-urlencoded
```

### 2. 请求体结构

```typescript
// 创建资源请求
interface CreateAssetRequest {
  property_name: string        // 必填字段
  address: string              // 必填字段
  ownership_status?: string    // 可选字段
  property_nature?: string
  // ... 其他字段
}

// 更新资源请求
interface UpdateAssetRequest {
  property_name?: string       // 部分更新
  address?: string
  ownership_status?: string
}

// 批量操作请求
interface BatchUpdateRequest {
  asset_ids: string[]          // 目标资源ID列表
  updates: {                   // 更新数据
    ownership_status?: string
    property_nature?: string
  }
}

// 查询请求
interface SearchRequest {
  search?: string              // 搜索关键词
  filters?: {                  // 筛选条件
    ownership_status?: string
    property_nature?: string
    usage_status?: string
  }
  sort_by?: string             // 排序字段
  order?: 'asc' | 'desc'       // 排序方向
  page?: number                // 页码
  limit?: number               // 每页数量
}
```

## 响应格式

### 1. 成功响应

```typescript
// 单个资源响应
interface SuccessResponse<T> {
  success: true
  message: string
  data: T                       // 资源数据
  timestamp: string             // 响应时间
}

// 列表响应
interface ListResponse<T> {
  success: true
  message: string
  data: {
    items: T[]                 // 数据列表
    total: number              // 总数量
    page: number               // 当前页码
    limit: number              // 每页数量
    pages: number              // 总页数
  }
  timestamp: string
}

// 创建/更新响应
interface CreateResponse<T> {
  success: true
  message: string
  data: T                       // 创建/后的资源
  timestamp: string
}

// 操作响应（无返回数据）
interface ActionResponse {
  success: true
  message: string
  timestamp: string
}
```

### 2. 错误响应

```typescript
// 标准错误响应
interface ErrorResponse {
  success: false
  message: string               // 错误描述
  error?: {
    code: string               // 错误代码
    details?: any              // 详细错误信息
    field?: string             // 错误字段（验证错误）
  }
  timestamp: string
}

// 验证错误响应
interface ValidationErrorResponse extends ErrorResponse {
  error: {
    code: "VALIDATION_ERROR"
    details: {                 // 字段级错误
      [field: string]: string[]
    }
  }
}

// 业务逻辑错误响应
interface BusinessErrorResponse extends ErrorResponse {
  error: {
    code: string               // 业务错误代码
    details: {
      reason: string           // 错误原因
      suggestion?: string      // 处理建议
    }
  }
}
```

### 3. 响应示例

```typescript
// GET /api/v1/assets/{id}
{
  "success": true,
  "message": "获取资产成功",
  "data": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "property_name": "示例物业",
    "address": "示例地址",
    "ownership_status": "已确权",
    "created_at": "2024-01-01T00:00:00Z"
  },
  "timestamp": "2024-01-01T12:00:00Z"
}

// GET /api/v1/assets
{
  "success": true,
  "message": "获取资产列表成功",
  "data": {
    "items": [...],
    "total": 100,
    "page": 1,
    "limit": 20,
    "pages": 5
  },
  "timestamp": "2024-01-01T12:00:00Z"
}

// 错误响应示例
{
  "success": false,
  "message": "请求参数验证失败",
  "error": {
    "code": "VALIDATION_ERROR",
    "details": {
      "property_name": ["物业名称不能为空"],
      "address": ["地址长度不能超过500个字符"]
    }
  },
  "timestamp": "2024-01-01T12:00:00Z"
}
```

## 状态码规范

### 1. 成功状态码

| 状态码 | 含义 | 使用场景 |
|--------|------|----------|
| 200 | OK | 请求成功，返回数据 |
| 201 | Created | 资源创建成功 |
| 202 | Accepted | 请求已接受，正在处理 |
| 204 | No Content | 请求成功，无返回内容 |

### 2. 客户端错误状态码

| 状态码 | 含义 | 使用场景 |
|--------|------|----------|
| 400 | Bad Request | 请求参数错误 |
| 401 | Unauthorized | 未认证或认证失败 |
| 403 | Forbidden | 权限不足 |
| 404 | Not Found | 资源不存在 |
| 409 | Conflict | 资源冲突 |
| 422 | Unprocessable Entity | 数据验证失败 |
| 429 | Too Many Requests | 请求频率限制 |

### 3. 服务器错误状态码

| 状态码 | 含义 | 使用场景 |
|--------|------|----------|
| 500 | Internal Server Error | 服务器内部错误 |
| 502 | Bad Gateway | 网关错误 |
| 503 | Service Unavailable | 服务不可用 |

## 分页规范

### 1. 分页参数

```typescript
interface PaginationParams {
  page?: number      // 页码，从1开始，默认1
  limit?: number     // 每页数量，默认20，最大100
}
```

### 2. 分页响应

```typescript
interface PaginatedData<T> {
  items: T[]         // 当前页数据
  total: number      // 总记录数
  page: number       // 当前页码
  limit: number      // 每页数量
  pages: number      // 总页数
}
```

### 3. 分页实现示例

```typescript
// 请求
GET /api/v1/assets?page=2&limit=10

// 响应
{
  "success": true,
  "message": "获取成功",
  "data": {
    "items": [...],
    "total": 100,
    "page": 2,
    "limit": 10,
    "pages": 10
  }
}
```

## 搜索和筛选

### 1. 搜索参数

```typescript
interface SearchParams {
  search?: string           // 通用搜索关键词
  search_keyword?: string   // 特定字段搜索
  search_fields?: string[]  // 搜索字段列表
}
```

### 2. 筛选参数

```typescript
interface FilterParams {
  // 简单筛选
  ownership_status?: string
  property_nature?: string
  usage_status?: string

  // 范围筛选
  created_at_start?: string
  created_at_end?: string
  area_min?: number
  area_max?: number

  // 复杂筛选（JSON格式）
  filters?: {
    ownership_status?: string[]
    property_nature?: string[]
    created_at?: {
      gte?: string
      lte?: string
    }
  }
}
```

### 3. 排序参数

```typescript
interface SortParams {
  sort_by?: string          // 排序字段
  order?: 'asc' | 'desc'   // 排序方向
  sort?: string[]           // 多字段排序 ['created_at:desc', 'name:asc']
}
```

## 文件上传

### 1. 文件上传请求

```typescript
// 单文件上传
POST /api/v1/files/upload
Content-Type: multipart/form-data

FormData:
- file: File
- category: string
- description?: string
```

### 2. 文件上传响应

```typescript
interface FileUploadResponse {
  success: true
  message: string
  data: {
    file_id: string
    filename: string
    file_size: number
    file_type: string
    upload_time: string
    download_url: string
  }
}
```

## 批量操作

### 1. 批量操作请求

```typescript
// 批量更新
POST /api/v1/assets/batch-update
{
  "asset_ids": ["id1", "id2", "id3"],
  "updates": {
    "ownership_status": "已确权",
    "property_nature": "经营性"
  }
}

// 批量删除
DELETE /api/v1/assets/batch-delete
{
  "asset_ids": ["id1", "id2", "id3"]
}
```

### 2. 批量操作响应

```typescript
interface BatchOperationResponse {
  success: true
  message: string
  data: {
    total: number           // 总处理数量
    success: number         // 成功数量
    failed: number          // 失败数量
    errors?: Array<{        // 错误详情
      id: string
      error: string
    }>
  }
}
```

## 异步任务

### 1. 任务创建请求

```typescript
POST /api/v1/tasks
{
  "task_type": "excel_import",
  "title": "Excel导入任务",
  "parameters": {
    "file_id": "file123",
    "sheet_name": "Sheet1"
  }
}
```

### 2. 任务创建响应

```typescript
interface TaskCreateResponse {
  success: true
  message: string
  data: {
    task_id: string
    status: "pending" | "running" | "completed" | "failed"
    estimated_time: string
  }
}
```

### 3. 任务状态查询

```typescript
// 请求
GET /api/v1/tasks/{task_id}/status

// 响应
{
  "success": true,
  "message": "获取任务状态成功",
  "data": {
    "task_id": "task123",
    "status": "running",
    "progress": 45,
    "total_items": 1000,
    "processed_items": 450,
    "created_at": "2024-01-01T12:00:00Z",
    "started_at": "2024-01-01T12:00:05Z"
  }
}
```

## 版本控制

### 1. 版本策略

- 使用URL路径版本控制: `/api/v1/`, `/api/v2/`
- 向后兼容原则：新版本保持对旧版本的兼容
- 弃用通知：提前3个月通知版本弃用

### 2. 版本头信息

```typescript
// 请求头
X-API-Version: v1

// 响应头
X-API-Version: v1
X-API-Supported-Versions: v1,v2
X-API-Default-Version: v2
```

### 3. 版本弃用处理

```typescript
// 弃用版本响应头
Deprecation: true
Sunset: 2024-12-31T00:00:00Z
Link: </api/v2/assets>; rel="successor-version"
```

## 错误处理

### 1. 错误分类

```typescript
// 验证错误 (422)
{
  "success": false,
  "message": "数据验证失败",
  "error": {
    "code": "VALIDATION_ERROR",
    "details": {
      "field_name": ["错误消息1", "错误消息2"]
    }
  }
}

// 业务逻辑错误 (400)
{
  "success": false,
  "message": "业务规则校验失败",
  "error": {
    "code": "BUSINESS_ERROR",
    "details": {
      "reason": "资产已存在合同，无法删除",
      "suggestion": "请先删除相关合同"
    }
  }
}

// 权限错误 (403)
{
  "success": false,
  "message": "权限不足",
  "error": {
    "code": "PERMISSION_DENIED",
    "details": {
      "required_permission": "asset:delete",
      "current_permissions": ["asset:read", "asset:update"]
    }
  }
}
```

### 2. 错误代码规范

```typescript
enum ErrorCodes {
  // 通用错误
  VALIDATION_ERROR = "VALIDATION_ERROR",
  BUSINESS_ERROR = "BUSINESS_ERROR",
  PERMISSION_DENIED = "PERMISSION_DENIED",
  RESOURCE_NOT_FOUND = "RESOURCE_NOT_FOUND",
  INTERNAL_ERROR = "INTERNAL_ERROR",

  // 业务特定错误
  ASSET_NOT_FOUND = "ASSET_NOT_FOUND",
  ASSET_ALREADY_EXISTS = "ASSET_ALREADY_EXISTS",
  CONTRACT_ACTIVE = "CONTRACT_ACTIVE",
  EXCEL_IMPORT_FAILED = "EXCEL_IMPORT_FAILED"
}
```

## 安全规范

### 1. 认证和授权

```typescript
// 认证头
Authorization: Bearer <token>

// API密钥
X-API-Key: <api_key>
```

### 2. 输入验证

- 严格验证所有输入参数
- 使用白名单而非黑名单
- 防止SQL注入和XSS攻击
- 限制文件上传大小和类型

### 3. 输出过滤

- 过滤敏感信息
- 控制返回字段
- 使用数据脱敏

## 性能优化

### 1. 缓存策略

```typescript
// 缓存控制头
Cache-Control: public, max-age=3600
ETag: "abc123"
Last-Modified: Wed, 01 Jan 2024 00:00:00 GMT
```

### 2. 分页和限制

- 默认分页大小：20
- 最大分页大小：100
- 查询结果限制：1000

### 3. 字段选择

```typescript
// 请求特定字段
GET /api/v1/assets?fields=id,property_name,address

// 排除字段
GET /api/v1/assets?exclude=created_at,updated_at
```

## 文档和测试

### 1. API文档

- 使用OpenAPI/Swagger规范
- 提供详细的接口说明
- 包含请求/响应示例
- 提供错误码说明

### 2. 测试要求

- 单元测试覆盖率 > 80%
- 集成测试覆盖主要业务流程
- 性能测试验证响应时间
- 安全测试检查漏洞

## 监控和日志

### 1. 请求日志

```typescript
// 请求日志格式
{
  "timestamp": "2024-01-01T12:00:00Z",
  "method": "GET",
  "path": "/api/v1/assets",
  "status_code": 200,
  "response_time": 150,
  "user_id": "user123",
  "ip_address": "192.168.1.1"
}
```

### 2. 错误日志

```typescript
// 错误日志格式
{
  "timestamp": "2024-01-01T12:00:00Z",
  "error_code": "VALIDATION_ERROR",
  "error_message": "数据验证失败",
  "request_data": {...},
  "stack_trace": "...",
  "user_id": "user123"
}
```

### 3. 性能监控

- API响应时间监控
- 错误率监控
- 并发量监控
- 资源使用监控

---

本API设计指南为系统开发提供了统一的设计标准，所有API接口都应严格遵守这些规范，确保系统的一致性和可维护性。