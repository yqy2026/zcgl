# API响应处理代码审查Checklist

## 📋 概述

本文档提供API响应处理代码审查的标准检查清单，确保代码质量和一致性。

## 🔍 审查清单

### 1. API调用检查

#### ✅ 必须检查项

- [ ] **使用正确的API客户端**
  ```typescript
  // ✅ 使用增强型客户端
  import { enhancedApiClient } from '../services/enhancedApiClient';
  const result = await enhancedApiClient.get('/api/users');

  // ❌ 避免直接使用axios
  import axios from 'axios';
  const response = await axios.get('/api/users');
  ```

- [ ] **导入路径正确**
  ```typescript
  // ✅ 正确的导入路径
  import { ResponseExtractor } from '../utils/responseExtractor';
  import { enhancedApiClient } from '../services/enhancedApiClient';

  // ❌ 错误的相对路径
  import { ResponseExtractor } from '../../utils/responseExtractor';
  ```

- [ ] **方法类型定义**
  ```typescript
  // ✅ 明确的返回类型
  static async getUser(id: string): Promise<User>

  // ❌ 缺少返回类型
  static async getUser(id: string) // any类型
  ```

#### ⚠️ 建议检查项

- [ ] **重试配置合理性**
  ```typescript
  // ✅ 合理的重试配置
  retry: {
    maxAttempts: 3,
    delay: 1000,
    retryCondition: (error) => !error.response || error.response.status >= 500
  }

  // ⚠️ 检查：是否为敏感操作设置了重试？
  // ⚠️ 检查：重试次数是否过多？
  ```

- [ ] **缓存配置合理性**
  ```typescript
  // ✅ 合理的缓存配置
  cache: {
    enabled: true,
    ttl: 5 * 60 * 1000 // 5分钟
  }

  // ⚠️ 检查：静态数据缓存时间是否足够长？
  // ⚠️ 检查：动态数据是否不应该缓存？
  ```

### 2. 响应处理检查

#### ✅ 必须检查项

- [ ] **使用统一的响应提取**
  ```typescript
  // ✅ 使用ResponseExtractor
  const result = ResponseExtractor.smartExtract<User>(response);
  if (result.success) {
    return result.data;
  }

  // ❌ 直接访问response
  const user = response.data.user; // 应该使用提取器
  ```

- [ ] **检查响应结果**
  ```typescript
  // ✅ 检查成功状态
  const result = ResponseExtractor.smartExtract(response);
  if (!result.success) {
    throw new Error(result.error);
  }

  // ❌ 未检查响应状态
  const data = ResponseExtractor.extractData(response); // 可能返回undefined
  ```

- [ ] **适当的错误处理**
  ```typescript
  // ✅ 统一错误处理
  } catch (error) {
    const enhancedError = ApiErrorHandler.handleError(error);
    throw new Error(enhancedError.message);
  }

  // ❌ 不一致的错误处理
  } catch (error) {
    if (error.response?.data?.message) {
      throw error.response.data.message;
    } else {
      throw error.message || '未知错误';
    }
  }
  ```

#### ⚠️ 建议检查项

- [ ] **避免重复的响应处理逻辑**
  ```typescript
  // ❌ 重复逻辑
  if (response.data && response.data.user) {
    return response.data.user;
  } else if (response.data && response.data.success && response.data.data.user) {
    return response.data.data.user;
  }

  // ✅ 统一处理
  const result = ResponseExtractor.smartExtract(response);
  ```

- [ ] **类型验证**
  ```typescript
  // ✅ 启用类型验证
  const result = ResponseExtractor.smartExtract<User>(response, {
    enableTypeValidation: true,
    expectedType: User
  });
  ```

### 3. 类型定义检查

#### ✅ 必须检查项

- [ ] **导入统一类型**
  ```typescript
  // ✅ 导入标准类型
  import { StandardApiResponse, PaginatedApiResponse } from '../types/api-response';
  ```

- [ ] **定义明确的接口**
  ```typescript
  // ✅ 明确的接口定义
  interface User {
    id: string;
    username: string;
    email?: string;
  }

  type UserResponse = StandardApiResponse<User>;
  ```

- [ ] **避免使用any**
  ```typescript
  // ❌ 避免any
  const result: any = await apiCall();

  // ✅ 使用具体类型
  const result: StandardApiResponse<User> = await apiCall();
  ```

### 4. 错误处理检查

#### ✅ 必须检查项

- [ ] **使用统一错误处理器**
  ```typescript
  // ✅ 使用ApiErrorHandler
  const enhancedError = ApiErrorHandler.handleError(error);
  console.error('错误类型:', enhancedError.type);
  ```

- [ **重新抛出错误**
  ```typescript
  // ✅ 重新抛出错误
  } catch (error) {
    const enhancedError = ApiErrorHandler.handleError(error);
    throw new Error(enhancedError.message);
  }

  // ❌ 静默错误
  } catch (error) {
    console.error(error); // 错误被忽略
  }
  ```

#### ⚠️ 建议检查项

- [ ] **用户友好的错误消息**
  ```typescript
  // ✅ 用户友好的消息
  throw new Error(`登录失败: ${enhancedError.message}`);

  // ⚠️ 技术性错误消息
  throw new Error(`API_ERROR_${enhancedError.code}`);
  ```

- [ **适当的日志记录**
  ```typescript
  // ✅ 记录错误详情
  console.error('API调用失败:', {
    url: config.url,
    method: config.method,
    error: enhancedError
  });
  ```

### 5. 代码质量检查

#### ✅ 必须检查项

- [ ] **函数单一职责**
  ```typescript
  // ✅ 单一职责
  static async getUser(id: string): Promise<User>

  // ❌ 职责过多
  static async getUserAndProcess(id: string): Promise<User> // 同时获取和处理
  ```

- [ **合理的函数长度**
  ```typescript
  // ✅ 适度长度（建议 < 50行）
  static async login(credentials: LoginCredentials): Promise<AuthResponse> {
    // 主要逻辑
  }

  // ⚠️ 过长的函数（建议拆分）
  static async complexOperation(params: any): Promise<any> // > 100行
  ```

#### ⚠️ 建议检查项

- [ ] **去除调试代码**
  ```typescript
  // ❌ 移除调试代码
  console.log('debug:', response);
  console.log('test:', data);

  // ✅ 使用适当的日志级别
  if (process.env.NODE_ENV === 'development') {
    console.log('开发模式调试:', response);
  }
  ```

- [ ] **代码复用**
  ```typescript
  // ❌ 重复逻辑
  class Service1 {
    static handleResponse(response: AxiosResponse) {
      // 重复的响应处理逻辑
    }
  }

  // ✅ 提取公共逻辑
  const commonResponseHandler = (response: AxiosResponse) => {
    return ResponseExtractor.smartExtract(response);
  };
  ```

## 🔧 常见问题和解决方案

### 问题1: 直接访问response属性

```typescript
// ❌ 问题代码
const user = response.user;

// ✅ 解决方案
const result = ResponseExtractor.smartExtract(response);
if (result.success) {
  const user = result.data;
}
```

### 问题2: 不一致的错误处理

```typescript
// ❌ 问题代码
catch (error) {
  if (error.response?.data?.message) {
    throw error.response.data.message;
  }
  throw error.message;
}

// ✅ 解决方案
catch (error) {
  const enhancedError = ApiErrorHandler.handleError(error);
  throw new Error(enhancedError.message);
}
```

### 问题3: 缺少类型定义

```typescript
// ❌ 问题代码
const result = await apiCall();
return result.data;

// ✅ 解决方案
const result: StandardApiResponse<User> = await apiCall();
return result.data;
```

## 📊 审查工具

### 自动化检查

1. **ESLint规则**
   ```bash
   npm run lint -- --ext .ts,.tsx src/
   ```

2. **API响应分析工具**
   ```bash
   node scripts/api-response-analyzer.js --path src/services
   ```

3. **类型检查**
   ```bash
   npm run type-check
   ```

### 手动检查

1. **代码走查**
   - 检查API调用模式
   - 验证响应处理逻辑
   - 确认错误处理完整性

2. **单元测试审查**
   - 检查测试覆盖率
   - 验证错误场景测试
   - 确认类型正确性

## 📝 审查报告模板

```markdown
# 代码审查报告

## 基本信息
- **审查者**: [姓名]
- **被审查者**: [姓名]
- **审查日期**: [日期]
- **文件路径**: [文件路径]

## 检查结果

### ✅ 通过的检查项
- [ ] 使用enhancedApiClient
- [ ] 正确的响应提取
- [ ] 统一的错误处理
- [ ] 明确的类型定义

### ⚠️ 需要改进的检查项
- [ ] 需要添加重试配置
- [ ] 建议添加缓存策略
- [ ] 函数长度过长建议拆分

### ❌ 未通过的检查项
- [ ] 直接访问response属性
- [ ] 缺少错误处理
- [ ] 使用any类型

## 建议和行动项
1. [ ] 修复直接访问response属性的问题
2. [ ] 添加适当的重试配置
3. [ ] 完善错误处理逻辑
4. [ ] 补充类型定义

## 总结
- **总体评分**: [评分]
- **主要问题**: [主要问题]
- **改进建议**: [改进建议]
```

## 🔄 持续改进

### 定期检查
- 每周进行代码质量扫描
- 每月更新检查清单
- 定期培训和分享

### 工具优化
- 完善ESLint自定义规则
- 改进自动化分析工具
- 集成到CI/CD流程

---

**维护团队**: 前端开发团队
**最后更新**: 2025-11-10