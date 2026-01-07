# API服务层文档

本目录包含了前端应用的所有API服务层代码，提供了类型安全、错误处理、缓存管理等完整的API交互功能。

## 文件结构

```
services/
├── api.ts                  # 核心API客户端
├── assetService.ts         # 资产管理服务
├── statisticsService.ts    # 统计分析服务
├── excelService.ts         # Excel导入导出服务
├── pdfService.ts           # PDF处理服务
├── rbacService.ts          # 权限管理服务
├── organizationService.ts  # 组织架构服务
├── dictionary/             # 字典服务
├── config.ts               # API配置文件
├── errorHandler.ts         # 错误处理工具
├── cacheManager.ts         # 缓存管理器
├── index.ts                # 统一导出文件
└── README.md               # 本文档
```

## 核心功能

### 1. API客户端 (api.ts)

提供了基础的HTTP请求功能，包括：

- **请求拦截器**: 自动添加认证token、请求ID等
- **响应拦截器**: 统一处理响应和错误
- **请求重试**: 自动重试失败的请求
- **文件上传**: 支持进度回调的文件上传
- **文件下载**: 自动处理文件下载

```typescript
import { apiClient } from '@/services';

// GET请求
const data = await apiClient.get('/assets');

// POST请求
const result = await apiClient.post('/assets', assetData);

// 文件上传
const uploadResult = await apiClient.upload('/excel/import', file, progress => {
  console.log(`上传进度: ${progress}%`);
});

// 文件下载
await apiClient.download('/excel/export/file.xlsx', '资产数据.xlsx');
```

### 2. 资产服务 (assetService.ts)

提供完整的资产管理API：

```typescript
import { assetService } from '@/services';

// 获取资产列表
const assets = await assetService.getAssets({
  page: 1,
  limit: 20,
  search: '写字楼',
});

// 创建资产
const newAsset = await assetService.createAsset({
  property_name: '新写字楼',
  ownership_entity: '某公司',
  // ... 其他字段
});

// 获取变更历史
const history = await assetService.getAssetHistory(assetId);
```

### 3. 统计服务 (statisticsService.ts)

提供数据统计和分析功能：

```typescript
import { statisticsService } from '@/services';

// 获取仪表板数据
const dashboard = await statisticsService.getDashboardData();

// 获取权属分布
const distribution = await statisticsService.getOwnershipDistribution();

// 生成报表
const report = await statisticsService.generateReport('monthly', filters);
```

### 4. Excel服务 (excelService.ts)

处理Excel文件的导入导出：

```typescript
import { excelService } from '@/services';

// 导入Excel
const importResult = await excelService.importExcel(file, '物业总表', progress => {
  console.log(`导入进度: ${progress}%`);
});

// 导出Excel
const exportResult = await excelService.exportExcel({
  filters: { property_nature: '经营类' },
  format: 'xlsx',
});

// 下载模板
await excelService.downloadTemplate();
```

### 5. PDF服务 (pdfService.ts)

处理PDF文件的导入和信息提取：

```typescript
import { pdfService } from '@/services';

// 上传PDF文件
const uploadResult = await pdfService.uploadPdf(file);

// 提取合同信息
const contractData = await pdfService.extractContract(sessionId);

// 验证合同数据
const validation = await pdfService.validateContract(contractData);
```

### 6. 权限管理服务 (rbacService.ts)

处理用户认证和权限管理：

```typescript
import { rbacService } from '@/services';

// 用户登录
const loginResult = await rbacService.login(username, password);

// 获取用户权限
const permissions = await rbacService.getUserPermissions(userId);

// 创建角色
const role = await rbacService.createRole(roleData);
```

### 7. 组织架构服务 (organizationService.ts)

处理组织架构管理：

```typescript
import { organizationService } from '@/services';

// 获取组织架构
const orgTree = await organizationService.getOrganizationTree();

// 创建组织
const org = await organizationService.createOrganization(orgData);
```

## 字典服务 (dictionary/)

专门的字典数据服务，请参考 [dictionary/README.md](dictionary/README.md) 获取详细信息。

## 高级功能

### 1. 错误处理

自动处理API错误并显示用户友好的提示：

```typescript
import { handleApiError } from '@/services';

try {
  const result = await assetService.createAsset(data);
} catch (error) {
  // 自动显示错误消息
  handleApiError(
    error,
    {
      showMessage: true,
      showNotification: false,
    },
    '创建资产'
  );
}
```

### 2. 缓存管理

智能缓存API响应以提高性能：

```typescript
import { cacheManager, cached } from '@/services';

// 使用装饰器缓存方法结果
class MyService {
  @cached({ ttl: 5 * 60 * 1000, tags: ['assets'] })
  async getAssets() {
    return await apiClient.get('/assets');
  }
}

// 手动管理缓存
cacheManager.set('/assets', data, { ttl: 300000 });
const cachedData = cacheManager.get('/assets');
```

### 3. 请求配置

灵活的配置选项：

```typescript
import { API_CONFIG, ENDPOINTS } from '@/services';

// 使用预定义的端点
const url = ENDPOINTS.ASSET_DETAIL('123');

// 检查环境
if (API_CONFIG.ENV.DEVELOPMENT) {
  console.log('开发环境');
}

// 验证文件
const isValid = API_CONFIG.isValidFileType(file);
```

## 类型安全

所有服务都提供完整的TypeScript类型支持：

```typescript
import type { Asset, AssetCreateRequest, AssetListResponse } from '@/types/asset';
import type { ApiResponse, ErrorResponse } from '@/types/api';

// 类型安全的API调用
const createAsset = async (data: AssetCreateRequest): Promise<Asset> => {
  const response = await assetService.createAsset(data);
  return response;
};
```

## 配置选项

### 环境变量

在 `.env.local` 文件中配置：

```env
# API基础URL
VITE_API_BASE_URL=http://localhost:8002/api

# 请求超时时间（毫秒）
VITE_API_TIMEOUT=30000

# 应用版本
VITE_APP_VERSION=1.0.0
```

### 运行时配置

```typescript
import { API_CONFIG } from '@/services';

// 修改配置
API_CONFIG.TIMEOUT = 60000;
API_CONFIG.RETRY.ATTEMPTS = 5;
```

## 最佳实践

### 1. 错误处理

```typescript
// ✅ 推荐：使用统一的错误处理
try {
  const result = await assetService.createAsset(data);
  message.success('创建成功');
  return result;
} catch (error) {
  handleApiError(error, { showMessage: true }, '创建资产');
  throw error;
}

// ❌ 不推荐：手动处理每个错误
try {
  const result = await assetService.createAsset(data);
} catch (error) {
  if (error.status === 400) {
    message.error('参数错误');
  } else if (error.status === 500) {
    message.error('服务器错误');
  }
}
```

### 2. 缓存使用

```typescript
// ✅ 推荐：为只读数据使用缓存
@cached({ ttl: 10 * 60 * 1000, tags: ['reference-data'] })
async getOwnershipEntities() {
  return await assetService.getOwnershipEntities()
}

// ❌ 不推荐：为频繁变化的数据使用长期缓存
@cached({ ttl: 60 * 60 * 1000 }) // 1小时缓存太长
async getAssetList() {
  return await assetService.getAssets()
}
```

### 3. 类型使用

```typescript
// ✅ 推荐：使用具体的类型
const createAsset = async (data: AssetCreateRequest): Promise<Asset> => {
  return await assetService.createAsset(data);
};

// ❌ 不推荐：使用any类型
const createAsset = async (data: any): Promise<any> => {
  return await assetService.createAsset(data);
};
```

## 调试和监控

### 1. 开发环境调试

在开发环境中，所有API请求都会在控制台输出详细日志：

```
🚀 API Request: GET /api/assets
✅ API Response [req_1234567890_abc123]: GET /api/assets
```

### 2. 错误监控

在生产环境中，错误会自动上报到日志服务：

```typescript
// 在errorHandler.ts中配置
private sendErrorToLogService(logData: any): void {
  // 集成Sentry、LogRocket等服务
  Sentry.captureException(new Error(logData.message), {
    extra: logData,
  })
}
```

### 3. 性能监控

```typescript
// 监控API响应时间
const startTime = performance.now();
const result = await assetService.getAssets();
const endTime = performance.now();
console.log(`API调用耗时: ${endTime - startTime}ms`);
```

## 扩展指南

### 1. 添加新服务

```typescript
// 1. 创建服务类
export class NewService {
  async getData(): Promise<any> {
    return await apiClient.get('/new-endpoint');
  }
}

// 2. 导出服务实例
export const newService = new NewService();

// 3. 在index.ts中导出
export { newService, NewService } from './newService';
```

### 2. 添加新的错误类型

```typescript
// 在config.ts中添加
export const ERROR_CODES = {
  // ... 现有错误码
  NEW_ERROR: 'NEW_ERROR',
}

// 在errorHandler.ts中处理
private getErrorMessage(error: ErrorResponse): string {
  switch (error.error) {
    // ... 现有处理
    case ERROR_CODES.NEW_ERROR:
      return '新的错误类型'
  }
}
```

### 3. 自定义缓存策略

```typescript
// 创建自定义缓存装饰器
export function customCached(strategy: 'memory' | 'localStorage') {
  return function (target: any, propertyKey: string, descriptor: PropertyDescriptor) {
    // 实现自定义缓存逻辑
  };
}
```

这个API服务层为前端应用提供了完整、类型安全、高性能的API交互能力，支持错误处理、缓存管理、请求重试等高级功能。
