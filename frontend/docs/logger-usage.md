# Logger 使用文档

## 概述

`logger.ts` 是项目的统一日志工具，用于替代原生的 `console` 语句，提供环境感知、级别控制和统一格式化的日志输出。

## 为什么使用 Logger？

1. **符合 ESLint 规范** - 绕过 `no-console` 规则
2. **环境感知** - 开发环境显示详细日志，生产环境仅显示错误
3. **统一格式** - 所有日志采用一致的格式输出
4. **模块化** - 通过前缀区分不同模块的日志
5. **级别控制** - 支持 debug, info, warn, error 四个级别

## 快速开始

### 基础使用

```typescript
import { createLogger } from '@/utils/logger';

const logger = createLogger('MyModule');

// 调试信息（仅开发环境）
logger.debug('用户登录成功', { userId: 123, username: 'john' });

// 普通信息
logger.info('API 请求完成');

// 警告信息  
logger.warn('缓存未命中', { key: 'user:123' });

// 错误信息（开发和生产环境都显示）
logger.error('数据库连接失败', error);
```

### 输出格式

```
// 开发环境
19:30:45 [DEBUG] [MyModule] 用户登录成功 { userId: 123, username: 'john' }
19:30:46 [WARN] [MyModule] 缓存未命中 { key: 'user:123' }
19:30:47 [ERROR] [MyModule] 数据库连接失败 { error: '...', stack: '...' }

// 生产环境（仅显示 error 级别）
[ERROR] [MyModule] 数据库连接失败 { error: '...', stack: '...' }
```

## API 参考

### createLogger(prefix: string): Logger

创建带前缀的 logger 实例。

```typescript
const logger = createLogger('AuthService');
logger.debug('开始登录流程'); 
// 输出: 19:30:45 [DEBUG] [AuthService] 开始登录流程
```

### logger.debug(message: string, meta?: Record<string, unknown>): void

记录调试信息，仅在开发环境显示。

```typescript
logger.debug('API 响应数据', { data: responseData });
```

### logger.info(message: string, meta?: Record<string, unknown>): void

记录普通信息。

```typescript
logger.info('用户注册成功');
```

### logger.warn(message: string, meta?: Record<string, unknown>): void

记录警告信息。

```typescript
logger.warn('配置项缺失', { key: 'API_KEY' });
```

### logger.error(message: string, error?: Error | unknown, meta?: Record<string, unknown>): void

记录错误信息，自动提取错误堆栈。

```typescript
try {
  await someOperation();
} catch (error) {
  logger.error('操作失败', error);
  // 或者
  logger.error('操作失败', error, { context: 'additional info' });
}
```

### logger.child(prefix: string): Logger

创建子 logger，会自动添加层级前缀。

```typescript
const parentLogger = createLogger('Service');
const childLogger = parentLogger.child('Database');

childLogger.debug('查询开始');
// 输出: 19:30:45 [DEBUG] [Service:Database] 查询开始
```

### logger.setEnabled(enabled: boolean): void

临时启用/禁用日志。

```typescript
logger.setEnabled(false); // 临时禁用
logger.debug('这条不会显示');
logger.setEnabled(true); // 重新启用
```

### logger.setLevel(level: LogLevel): void

设置日志级别。

```typescript
logger.setLevel('warn'); // 只显示 warn 和 error
logger.debug('这条不会显示');
logger.warn('这条会显示');
```

## 使用场景

### 1. Service 层

```typescript
import { createLogger } from '@/utils/logger';

const logger = createLogger('UserService');

export class UserService {
  async getUser(id: string) {
    try {
      logger.debug('获取用户信息', { userId: id });
      const user = await api.get(`/users/${id}`);
      logger.debug('用户信息获取成功', { user });
      return user;
    } catch (error) {
      logger.error('获取用户信息失败', error, { userId: id });
      throw error;
    }
  }
}
```

### 2. Hook 层

```typescript
import { createLogger } from '@/utils/logger';

const logger = createLogger('useAuth');

export function useAuth() {
  const login = async (credentials) => {
    logger.debug('开始登录', { username: credentials.username });
    try {
      const result = await authService.login(credentials);
      logger.debug('登录成功', { user: result.user });
      return result;
    } catch (error) {
      logger.error('登录失败', error);
      throw error;
    }
  };

  return { login };
}
```

### 3. 组件层

```typescript
import { createLogger } from '@/utils/logger';

const logger = createLogger('LoginForm');

export const LoginForm: React.FC = () => {
  const handleSubmit = async (values) => {
    logger.debug('提交登录表单', { username: values.username });
    try {
      await login(values);
      logger.info('登录成功');
    } catch (error) {
      logger.error('登录失败', error);
    }
  };

  return <Form onFinish={handleSubmit}>{/* ... */}</Form>;
};
```

## 替换指南

### 替换 console.log

```typescript
// ❌ 旧代码
console.log('数据加载完成:', data);

// ✅ 新代码
logger.debug('数据加载完成', { data });
```

### 替换 console.warn

```typescript
// ❌ 旧代码
console.warn('API 请求失败:', error.message);

// ✅ 新代码
logger.warn('API 请求失败', { error: error.message });
```

### 替换 console.error

```typescript
// ❌ 旧代码
console.error('处理失败:', error);

// ✅ 新代码
logger.error('处理失败', error);
```

## 最佳实践

### 1. 使用有意义的模块名

```typescript
// ✅ 好
const logger = createLogger('AuthService');
const logger = createLogger('UserProfile');

// ❌ 不好
const logger = createLogger('Service');
const logger = createLogger('Component');
```

### 2. 提供结构化的meta数据

```typescript
// ✅ 好
logger.debug('创建订单', { orderId: 123, userId: 456, amount: 100 });

// ❌ 不好
logger.debug(`创建订单 ID=${123} User=${456}`);
```

### 3. Error参数使用error字段

```typescript
// ✅ 好
logger.error('数据库查询失败', error, { query: 'SELECT ...' });

// ❌ 不好  
logger.error('数据库查询失败', undefined, { error, query: 'SELECT ...' });
```

### 4. 移除表情符号

```typescript
// ❌ 旧代码
console.log('🚀 开始加载...');
console.log('✅ 加载成功');

// ✅ 新代码
logger.debug('开始加载');
logger.info('加载成功');
```

### 5. 测试代码可以继续使用 console

测试文件（`**/*.test.ts`, `**/*.test.tsx`, `src/test/**`）已在 ESLint 配置中豁免，可以继续使用原生 console。

## 配置

Logger 会根据环境自动配置：

| 环境 | enabled | level | useTimestamp |
|------|---------|-------|--------------|
| Development | true | debug | true |
| Production | true | error | false |
| Test | false | error | false |

## 注意事项

1. **不要在循环中频繁打印** - 会影响性能
2. **不要打印敏感信息** - 如密码、token
3. **保持日志简洁** - 避免打印大对象
4. **使用合适的级别** - debug 用于调试，warn 用于潜在问题，error 用于错误

## 与 ESLint 集成

Logger 内部使用 `// eslint-disable-next-line no-console` 绕过规则检查，外部代码无需添加此注释。

```typescript
// ✅ 正确 - 无需注释
logger.debug('message');

// ❌ 错误 - 会被 ESLint 检测
console.log('message');
```

## 故障排查

### Q: 开发环境看不到日志？

A: 检查logger是否被禁用：
```typescript
logger.setEnabled(true);
```

### Q: 想在生产环境也看到 debug 日志？

A: 临时设置日志级别：
```typescript
logger.setLevel('debug');
```

### Q: 如何在浏览器控制台过滤日志？

A: 使用模块名作为过滤条件：
```
// 只看 AuthService 的日志
[AuthService]

// 只看 ERROR 级别
[ERROR]
```

## 总结

Logger 工具提供了比原生 console 更强大和灵活的日志功能。在新代码中始终使用 logger，逐步替换旧代码中的 console 语句，保持代码库的一致性和可维护性。
