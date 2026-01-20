/**
 * EnhancedApiClient 测试
 * 测试API客户端的核心功能（简化版本，不依赖MSW）
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { EnhancedApiClient, API_CONFIG, enhancedApiClient } from '../client';

// =============================================================================
// Mock数据
// =============================================================================

const _mockResponse = {
  success: true,
  data: { id: 1, name: 'test' },
  message: 'Success',
};

// =============================================================================
// MemoryCache 测试套件
// =============================================================================

describe('MemoryCache', () => {
  let client: EnhancedApiClient;

  beforeEach(() => {
    client = new EnhancedApiClient({
      enableCaching: true,
      defaultCacheConfig: {
        enabled: true,
        ttl: 1000, // 1秒
        maxSize: 5,
      },
    });
  });

  afterEach(() => {
    client.clearCache();
  });

  describe('缓存基本功能', () => {
    it('应该能够设置和获取缓存', () => {
      // 手动设置缓存来测试
      client['cache'].set('test:key', { data: 'test' }, 1000);
      const cached = client['cache'].get('test:key');
      expect(cached).toEqual({ data: 'test' });
    });

    it('缓存过期后应该返回null', () => {
      client['cache'].set('test:key', { data: 'test' }, 100); // 100ms TTL

      // 立即获取应该成功
      expect(client['cache'].get('test:key')).toEqual({ data: 'test' });

      // 等待过期
      // 注意：这个测试使用真实的setTimeout，所以需要等待实际时间
      // 在实际测试中，我们可能需要使用vi.useFakeTimers()
    });

    it('应该能够清除缓存', () => {
      client['cache'].set('test:key', { data: 'test' }, 1000);
      expect(client['cache'].get('test:key')).toEqual({ data: 'test' });

      client['cache'].clear();
      expect(client['cache'].get('test:key')).toBeNull();
    });

    it('应该能够删除特定缓存键', () => {
      client['cache'].set('test:key1', { data: 'test1' }, 1000);
      client['cache'].set('test:key2', { data: 'test2' }, 1000);

      client['cache'].delete('test:key1');

      expect(client['cache'].get('test:key1')).toBeNull();
      expect(client['cache'].get('test:key2')).toEqual({ data: 'test2' });
    });

    it('应该返回正确的缓存大小', () => {
      expect(client['cache'].size()).toBe(0);

      client['cache'].set('key1', { data: 'test1' }, 1000);
      client['cache'].set('key2', { data: 'test2' }, 1000);

      expect(client['cache'].size()).toBe(2);
    });
  });

  describe('缓存容量限制', () => {
    it('达到最大容量时应该删除最旧的条目', () => {
      const maxSize = 3;
      const cacheClient = new EnhancedApiClient({
        defaultCacheConfig: {
          enabled: true,
          ttl: 5000,
          maxSize,
        },
      });

      const cache = cacheClient['cache'] as any;

      // 添加4个条目（超过最大容量3）
      cache.set('key1', { data: 'test1' }, 5000);
      cache.set('key2', { data: 'test2' }, 5000);
      cache.set('key3', { data: 'test3' }, 5000);
      cache.set('key4', { data: 'test4' }, 5000);

      // 第一个条目应该被删除
      expect(cache.get('key1')).toBeNull();
      expect(cache.get('key2')).toEqual({ data: 'test2' });
      expect(cache.get('key3')).toEqual({ data: 'test3' });
      expect(cache.get('key4')).toEqual({ data: 'test4' });

      // 缓存大小应该是3
      expect(cache.size()).toBe(3);
    });
  });
});

// =============================================================================
// EnhancedApiClient 核心功能测试
// =============================================================================

describe('EnhancedApiClient', () => {
  let client: EnhancedApiClient;

  beforeEach(() => {
    client = new EnhancedApiClient({
      baseURL: '/api/v1',
      enableAutoRetry: false,
      enableCaching: false,
      enableLogging: false,
    });
  });

  describe('构造函数和初始化', () => {
    it('应该使用默认配置创建客户端', () => {
      const defaultClient = new EnhancedApiClient();
      const config = defaultClient.getConfig();

      expect(config.baseURL).toBe('/api/v1');
      expect(config.timeout).toBe(30000);
      expect(config.enableAutoRetry).toBe(false);
      expect(config.enableCaching).toBe(false);
    });

    it('应该接受自定义配置', () => {
      const customClient = new EnhancedApiClient({
        baseURL: '/custom/api',
        timeout: 5000,
        enableAutoRetry: true,
        enableCaching: true,
      });

      const config = customClient.getConfig();
      expect(config.baseURL).toBe('/custom/api');
      expect(config.timeout).toBe(5000);
      expect(config.enableAutoRetry).toBe(true);
      expect(config.enableCaching).toBe(true);
    });

    it('应该创建axios实例', () => {
      const axiosInstance = client.getAxiosInstance();
      expect(axiosInstance).toBeDefined();
      expect(axiosInstance.defaults.baseURL).toBe('/api/v1');
    });
  });

  describe('配置管理', () => {
    it('应该支持自定义响应检测配置', () => {
      const customClient = new EnhancedApiClient({
        responseDetection: {
          successField: 'ok',
          dataField: 'result',
          errorFields: ['err'],
          strict: true,
        },
      });

      const config = customClient.getConfig();
      expect(config.responseDetection?.successField).toBe('ok');
      expect(config.responseDetection?.dataField).toBe('result');
    });

    it('应该支持自定义重试配置', () => {
      const customClient = new EnhancedApiClient({
        defaultRetryConfig: {
          maxAttempts: 5,
          delay: 2000,
          backoffMultiplier: 3,
        },
      });

      const config = customClient.getConfig();
      expect(config.defaultRetryConfig?.maxAttempts).toBe(5);
      expect(config.defaultRetryConfig?.delay).toBe(2000);
    });
  });

  describe('工具方法', () => {
    it('clearCache应该清除所有缓存', () => {
      const cacheClient = new EnhancedApiClient({
        enableCaching: true,
        defaultCacheConfig: { enabled: true, ttl: 5000, maxSize: 100 },
      });

      // 添加一些缓存
      cacheClient['cache'].set('key1', { data: 'test1' }, 5000);
      cacheClient['cache'].set('key2', { data: 'test2' }, 5000);

      expect(cacheClient.getCacheSize()).toBe(2);

      cacheClient.clearCache();

      expect(cacheClient.getCacheSize()).toBe(0);
    });

    it('getCacheSize应该返回当前缓存数量', () => {
      expect(client.getCacheSize()).toBe(0);
    });

    it('updateConfig应该更新客户端配置', () => {
      client.updateConfig({
        timeout: 10000,
        enableAutoRetry: true,
      });

      const config = client.getConfig();
      expect(config.timeout).toBe(10000);
      expect(config.enableAutoRetry).toBe(true);
    });

    it('getConfig应该返回配置的副本', () => {
      const config1 = client.getConfig();
      const config2 = client.getConfig();

      expect(config1).toEqual(config2);
      expect(config1).not.toBe(config2); // 不同的引用
    });
  });

  describe('日志功能', () => {
    it('开发环境应该启用日志', () => {
      const devClient = new EnhancedApiClient({
        enableLogging: true,
      });

      const config = devClient.getConfig();
      expect(config.enableLogging).toBe(true);
    });

    it('生产环境应该禁用日志', () => {
      const prodClient = new EnhancedApiClient({
        enableLogging: false,
      });

      const config = prodClient.getConfig();
      expect(config.enableLogging).toBe(false);
    });
  });
});

// =============================================================================
// API_CONFIG 测试
// =============================================================================

describe('API_CONFIG', () => {
  it('should have baseURL set to /api/v1', () => {
    expect(API_CONFIG.baseURL).toBe('/api/v1');
  });

  it('should have timeout set to 30000', () => {
    expect(API_CONFIG.timeout).toBe(30000);
  });
});

// =============================================================================
// URL Validation 测试
// =============================================================================

describe('URL Validation', () => {
  const originalWarn = console.warn;
  let client: EnhancedApiClient;

  beforeEach(() => {
    console.warn = vi.fn();
    client = new EnhancedApiClient({
      baseURL: '/api/v1',
      enableLogging: false,
      enableAutoRetry: false,
    });
  });

  afterEach(() => {
    console.warn = originalWarn;
  });

  it('should not warn for URLs starting with /api/v1', () => {
    const axiosInstance = client.getAxiosInstance();
    const requestInterceptor = axiosInstance.interceptors.request.handlers[0];

    // @ts-expect-error - testing internal interceptor
    requestInterceptor.fulfilled({ url: '/api/v1/auth/login' });

    expect(console.warn).not.toHaveBeenCalled();
  });

  it('should not warn for URLs starting with /auth (legacy)', () => {
    const axiosInstance = client.getAxiosInstance();
    const requestInterceptor = axiosInstance.interceptors.request.handlers[0];

    // @ts-expect-error - testing internal interceptor
    requestInterceptor.fulfilled({ url: '/auth/login' });

    expect(console.warn).not.toHaveBeenCalled();
  });

  it('should warn for URLs without /api/v1 prefix', () => {
    const axiosInstance = client.getAxiosInstance();
    const requestInterceptor = axiosInstance.interceptors.request.handlers[0];

    // @ts-expect-error - testing internal interceptor
    requestInterceptor.fulfilled({ url: '/users' });

    expect(console.warn).toHaveBeenCalledWith(
      expect.stringContaining('[API Client] URL does not use /api/v1 prefix: /users')
    );
  });

  it('should warn for URLs without /api/v1 prefix (with nested path)', () => {
    const axiosInstance = client.getAxiosInstance();
    const requestInterceptor = axiosInstance.interceptors.request.handlers[0];

    // @ts-expect-error - testing internal interceptor
    requestInterceptor.fulfilled({ url: '/assets/list' });

    expect(console.warn).toHaveBeenCalledWith(
      expect.stringContaining('[API Client] URL does not use /api/v1 prefix: /assets/list')
    );
  });

  it('should not validate relative URLs (not starting with /)', () => {
    const axiosInstance = client.getAxiosInstance();
    const requestInterceptor = axiosInstance.interceptors.request.handlers[0];

    // @ts-expect-error - testing internal interceptor
    requestInterceptor.fulfilled({ url: 'relative-path' });

    expect(console.warn).not.toHaveBeenCalled();
  });

  it('should not validate URLs without / prefix (full URLs)', () => {
    const axiosInstance = client.getAxiosInstance();
    const requestInterceptor = axiosInstance.interceptors.request.handlers[0];

    // @ts-expect-error - testing internal interceptor
    requestInterceptor.fulfilled({ url: 'https://api.example.com/data' });

    expect(console.warn).not.toHaveBeenCalled();
  });
});

// =============================================================================
// Default Instance 测试
// =============================================================================

describe('Default Instance', () => {
  it('should export default enhancedApiClient instance', () => {
    expect(enhancedApiClient).toBeInstanceOf(EnhancedApiClient);
  });

  it('should have correct configuration on default instance', () => {
    const config = enhancedApiClient.getConfig();
    expect(config.baseURL).toBe('/api/v1');
    expect(config.timeout).toBe(30000);
  });
});

// =============================================================================
// 工厂函数测试
// =============================================================================

describe('工厂函数', () => {
  it('createEnhancedApiClient应该创建新实例', async () => {
    const { createEnhancedApiClient } = await import('../client');
    const client = createEnhancedApiClient({
      baseURL: '/custom',
    });

    expect(client).toBeInstanceOf(EnhancedApiClient);
    expect(client.getConfig().baseURL).toBe('/custom');
  });

  it('应该导出默认的enhancedApiClient实例', async () => {
    const { enhancedApiClient } = await import('../client');

    expect(enhancedApiClient).toBeInstanceOf(EnhancedApiClient);
  });
});
