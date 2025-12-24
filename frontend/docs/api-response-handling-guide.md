# API响应处理编码规范

## 📋 概述

本文档定义了土地物业资产管理系统中API响应处理的最佳实践和编码规范，旨在提高代码质量、类型安全性和维护性。

## 🎯 目标

- **统一性**: 确保所有API调用使用一致的响应处理模式
- **类型安全**: 利用TypeScript提供编译时类型检查
- **错误处理**: 统一的错误处理和用户反馈机制
- **可维护性**: 减少重复代码，提高代码复用性

## 🔧 核心工具

### ResponseExtractor
智能响应数据提取器，自动识别和提取不同格式的API响应。

```typescript
import { ResponseExtractor } from '../utils/responseExtractor';

// 智能提取响应数据
const result = ResponseExtractor.smartExtract<User>(response);
if (result.success) {
  const user = result.data;
} else {
  console.error('提取失败:', result.error);
}

// 快速获取数据（带默认值）
const user = ResponseExtractor.extractData<User>(response, null);
```

### EnhancedApiClient
增强型API客户端，提供统一的响应处理、重试和缓存功能。

```typescript
import { enhancedApiClient } from '../services/enhancedApiClient';

// 基础用法（自动响应提取）
const result = await enhancedApiClient.get<User>('/api/users/1');

// 高级用法（自定义配置）
const result = await enhancedApiClient.post('/api/users', userData, {
  retry: { maxAttempts: 3, delay: 1000 },
  cache: { enabled: true, ttl: 5 * 60 * 1000 },
  smartExtract: true
});
```

### ApiErrorHandler
统一的错误处理器，提供分类和格式化的错误信息。

```typescript
import { ApiErrorHandler } from '../utils/responseExtractor';

try {
  // API调用
} catch (error) {
  const enhancedError = ApiErrorHandler.handleError(error);
  console.error('错误类型:', enhancedError.type);
  console.error('错误消息:', enhancedError.message);
}
```

## 📝 编码规范

### 1. API调用规范

#### ✅ 推荐做法

**使用EnhancedApiClient进行所有API调用：**
```typescript
// ✅ 正确：使用增强型客户端
import { enhancedApiClient } from '../services/enhancedApiClient';

class UserService {
  static async getUser(id: string): Promise<User> {
    const result = await enhancedApiClient.get<User>(`/api/users/${id}`, {
      cache: { enabled: true, ttl: 5 * 60 * 1000 },
      retry: { maxAttempts: 2 }
    });

    if (!result.success) {
      throw new Error(`获取用户失败: ${result.error}`);
    }

    return result.data;
  }
}
```

**使用统一的响应处理：**
```typescript
// ✅ 正确：使用ResponseExtractor
import { ResponseExtractor } from '../utils/responseExtractor';

const result = ResponseExtractor.smartExtract<User[]>(response);
if (result.success) {
  return result.data;
} else {
  throw new Error(result.error);
}
```

**适当的错误处理：**
```typescript
// ✅ 正确：使用统一的错误处理
try {
  const result = await apiCall();
  return result;
} catch (error) {
  const enhancedError = ApiErrorHandler.handleError(error);
  throw new Error(enhancedError.message);
}
```

#### ❌ 避免的做法

**直接访问response对象属性：**
```typescript
// ❌ 错误：直接访问response属性
const response = await axios.get('/api/users');
const user = response.user; // 应该使用response.data
```

**重复的响应处理逻辑：**
```typescript
// ❌ 错误：重复的逻辑
if (response.data && response.data.user) {
  return response.data.user;
} else if (response.data && response.data.success && response.data.data.user) {
  return response.data.data.user;
} else {
  throw new Error('获取用户失败');
}
```

**不统一的错误处理：**
```typescript
// ❌ 错误：不统一的错误处理
catch (error) {
  if (error.response?.data?.message) {
    throw new Error(error.response.data.message);
  } else if (error.message) {
    throw new Error(error.message);
  } else {
    throw new Error('未知错误');
  }
}
```

### 2. 类型定义规范

#### ✅ 推荐做法

**使用统一的响应类型：**
```typescript
import { StandardApiResponse, PaginatedApiResponse } from '../types/api-response';

interface User {
  id: string;
  username: string;
  email?: string;
}

// 标准响应
type UserResponse = StandardApiResponse<User>;

// 分页响应
type UserListResponse = PaginatedApiResponse<User>;
```

**定义服务特定的类型：**
```typescript
interface LoginRequest {
  username: string;
  password: string;
}

interface LoginResponse {
  user: User;
  tokens: {
    access_token: string;
    refresh_token: string;
  };
}

class AuthService {
  static async login(credentials: LoginRequest): Promise<StandardApiResponse<LoginResponse>> {
    // 实现
  }
}
```

### 3. 重试策略规范

#### ✅ 推荐做法

**根据操作类型配置重试：**
```typescript
// ✅ 正确：敏感操作不重试
await enhancedApiClient.post('/api/transfer', transferData, {
  retry: false // 转账操作不重试
});

// ✅ 正确：查询操作可以重试
await enhancedApiClient.get('/api/users', {
  retry: {
    maxAttempts: 3,
    delay: 1000,
    backoffMultiplier: 2,
    retryCondition: (error) => {
      // 只对网络错误和5xx服务器错误重试
      return !error.response || (error.response.status >= 500 && error.response.status < 600);
    }
  }
});
```

### 4. 缓存策略规范

#### ✅ 推荐做法

**合理配置缓存：**
```typescript
// ✅ 正确：静态数据缓存
await enhancedApiClient.get('/api/dictionaries', {
  cache: {
    enabled: true,
    ttl: 30 * 60 * 1000 // 30分钟
  }
});

// ✅ 正确：用户数据不缓存
await enhancedApiClient.get('/api/user/profile', {
  cache: false
});

// ✅ 正确：短时间缓存
await enhancedApiClient.get('/api/statistics', {
  cache: {
    enabled: true,
    ttl: 2 * 60 * 1000 // 2分钟
  }
});
```

## 🧪 测试规范

### 单元测试

```typescript
import { ResponseExtractor } from '../utils/responseExtractor';

describe('UserService', () => {
  it('should extract user data correctly', () => {
    const mockResponse = {
      data: {
        success: true,
        data: { id: '1', username: 'test' }
      }
    };

    const result = ResponseExtractor.smartExtract(mockResponse);

    expect(result.success).toBe(true);
    expect(result.data).toEqual({ id: '1', username: 'test' });
  });

  it('should handle error response', () => {
    const mockResponse = {
      data: {
        success: false,
        error: { message: '用户不存在' }
      }
    };

    const result = ResponseExtractor.smartExtract(mockResponse);

    expect(result.success).toBe(false);
    expect(result.error).toBe('用户不存在');
  });
});
```

### 集成测试

```typescript
import { enhancedApiClient } from '../services/enhancedApiClient';

describe('API Integration', () => {
  it('should handle API call with retry', async () => {
    // 模拟网络失败然后成功
    const result = await enhancedApiClient.get('/api/test', {
      retry: {
        maxAttempts: 3,
        delay: 100
      }
    });

    expect(result.success).toBe(true);
  });
});
```

## 🔍 代码审查检查清单

### API调用检查

- [ ] 是否使用 `enhancedApiClient` 而不是直接使用 `axios`？
- [ ] 是否有适当的重试配置？
- [ ] 是否有合理的缓存配置？
- [ ] 是否使用了统一的响应提取？

### 响应处理检查

- [ ] 是否使用 `ResponseExtractor.smartExtract()` 而不是直接访问 `response`？
- [ ] 是否检查 `result.success` 状态？
- [ ] 是否有适当的错误处理？
- [ ] 是否避免重复的响应处理逻辑？

### 错误处理检查

- [ ] 是否使用 `ApiErrorHandler.handleError()`？
- [ ] 错误消息是否用户友好？
- [ ] 是否重新抛出错误而不是静默处理？
- [ ] 是否记录适当的日志信息？

### 类型安全检查

- [ ] 是否定义了正确的响应类型？
- [ ] 是否避免使用 `any` 类型？
- [ ] 是否有运行时类型验证（如果需要）？

## 🚀 迁移指南

### 从现有代码迁移

#### 步骤1：替换API客户端

```typescript
// 旧代码
import { api } from './index';
const response = await api.get('/api/users');

// 新代码
import { enhancedApiClient } from './enhancedApiClient';
const result = await enhancedApiClient.get('/api/users');
```

#### 步骤2：更新响应处理

```typescript
// 旧代码
if (response.data.success) {
  return response.data.data;
} else {
  throw new Error(response.data.message);
}

// 新代码
const result = ResponseExtractor.smartExtract(response);
if (result.success) {
  return result.data;
} else {
  throw new Error(result.error);
}
```

#### 步骤3：添加重试和缓存配置

```typescript
const result = await enhancedApiClient.get('/api/users', {
  retry: {
    maxAttempts: 2,
    delay: 500
  },
  cache: {
    enabled: true,
    ttl: 5 * 60 * 1000
  }
});
```

## 📊 性能优化建议

### 1. 缓存策略
- **静态数据**: 长时间缓存（30分钟以上）
- **用户数据**: 不缓存或短时间缓存（1-2分钟）
- **统计数据**: 中等时间缓存（5-10分钟）

### 2. 重试策略
- **GET请求**: 可以重试（网络错误、5xx错误）
- **POST/PUT/DELETE**: 谨慎重试（幂等操作）
- **敏感操作**: 不重试（转账、删除等）

### 3. 批量操作
- 使用 `enhancedApiClient.batch()` 进行批量请求
- 合并相似的API调用减少请求数量

## 📚 相关文档

- [API响应处理工具文档](./api-response-tools.md)
- [类型定义文档](./type-definitions.md)
- [错误处理指南](./error-handling.md)

## 🔄 版本历史

- **v1.0** - 初始版本，基础规范
- **v1.1** - 添加缓存和重试策略
- **v1.2** - 完善类型安全和测试规范

---

**维护团队**: 前端开发团队
**最后更新**: 2025-11-10
**版本**: v1.2