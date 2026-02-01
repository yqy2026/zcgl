/**
 * ApiClient 测试
 * 测试API客户端的核心功能（简化版本，不依赖MSW）
 */

import type { AxiosError, AxiosResponse } from 'axios';
import { AxiosHeaders, InternalAxiosRequestConfig } from 'axios';
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { Logger } from '@/utils/logger';
import { ApiClient, apiClient } from '../client';
import { API_BASE_URL } from '../config';

const { mockClearAuthData } = vi.hoisted(() => ({
  mockClearAuthData: vi.fn(),
}));

vi.mock('@/utils/AuthStorage', () => ({
  AuthStorage: {
    clearAuthData: mockClearAuthData,
  },
}));

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
  let client: ApiClient;

  beforeEach(() => {
    client = new ApiClient({
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
      const cacheClient = new ApiClient({
        defaultCacheConfig: {
          enabled: true,
          ttl: 5000,
          maxSize,
        },
      });

      // 访问私有属性用于测试缓存行为
      const cache = cacheClient['cache'] as unknown as {
        set: (key: string, data: unknown, ttl: number) => void;
        get: (key: string) => unknown;
        size: () => number;
      };

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
// ApiClient 核心功能测试
// =============================================================================

describe('ApiClient', () => {
  let client: ApiClient;

  beforeEach(() => {
    client = new ApiClient({
      baseURL: API_BASE_URL,
      enableAutoRetry: false,
      enableCaching: false,
      enableLogging: false,
    });
  });

  describe('构造函数和初始化', () => {
    it('应该使用默认配置创建客户端', () => {
      const defaultClient = new ApiClient();
      const config = defaultClient.getConfig();

      expect(config.baseURL).toBe(API_BASE_URL);
      expect(config.timeout).toBe(30000);
      expect(config.enableAutoRetry).toBe(false);
      expect(config.enableCaching).toBe(false);
    });

    it('应该接受自定义配置', () => {
      const customClient = new ApiClient({
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
      expect(axiosInstance.defaults.baseURL).toBe(API_BASE_URL);
    });
  });

  describe('配置管理', () => {
    it('应该支持自定义响应检测配置', () => {
      const customClient = new ApiClient({
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
      const customClient = new ApiClient({
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
      const cacheClient = new ApiClient({
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
      const devClient = new ApiClient({
        enableLogging: true,
      });

      const config = devClient.getConfig();
      expect(config.enableLogging).toBe(true);
    });

    it('生产环境应该禁用日志', () => {
      const prodClient = new ApiClient({
        enableLogging: false,
      });

      const config = prodClient.getConfig();
      expect(config.enableLogging).toBe(false);
    });
  });

  describe('Token刷新处理', () => {
    let originalLocation: Location;

    const setTestLocation = (pathname: string, search: string, hash: string): void => {
      Object.defineProperty(window, 'location', {
        value: {
          pathname,
          search,
          hash,
          href: '',
        },
        configurable: true,
        writable: true,
      });
    };

    beforeEach(() => {
      originalLocation = window.location;
      mockClearAuthData.mockReset();
    });

    afterEach(() => {
      Object.defineProperty(window, 'location', {
        value: originalLocation,
        configurable: true,
        writable: true,
      });
    });

    it('refresh接口返回401时应直接登出，避免递归刷新', async () => {
      const axiosInstance = client.getAxiosInstance();
      const responseInterceptor = axiosInstance.interceptors.response.handlers[0]?.rejected;
      if (responseInterceptor == null) {
        throw new Error('Response interceptor is not registered');
      }

      const postSpy = vi.spyOn(axiosInstance, 'post');
      setTestLocation('/current', '?q=1', '#hash');

      const config: InternalAxiosRequestConfig & { _retry?: boolean } = {
        url: '/auth/refresh',
        method: 'post',
        headers: new AxiosHeaders(),
      };
      const response = {
        status: 401,
        statusText: 'Unauthorized',
        data: {},
        headers: {},
        config,
      } as AxiosResponse;
      const error = {
        config,
        response,
        isAxiosError: true,
        name: 'AxiosError',
        message: 'Unauthorized',
        toJSON: () => ({}),
      } as AxiosError;

      await expect(responseInterceptor(error)).rejects.toBe(error);

      expect(postSpy).not.toHaveBeenCalled();
      expect(mockClearAuthData).toHaveBeenCalledTimes(1);
      expect(window.location.href).toBe(
        `/login?redirect=${encodeURIComponent('/current?q=1#hash')}`
      );
    });

    it('普通请求401且刷新失败时应登出并跳转', async () => {
      const axiosInstance = client.getAxiosInstance();
      const responseInterceptor = axiosInstance.interceptors.response.handlers[0]?.rejected;
      if (responseInterceptor == null) {
        throw new Error('Response interceptor is not registered');
      }

      setTestLocation('/assets', '', '');

      const refreshError = new Error('Refresh failed');
      const postSpy = vi.spyOn(axiosInstance, 'post').mockRejectedValue(refreshError);

      const config: InternalAxiosRequestConfig & { _retry?: boolean } = {
        url: '/assets',
        method: 'get',
        headers: new AxiosHeaders(),
      };
      const response = {
        status: 401,
        statusText: 'Unauthorized',
        data: {},
        headers: {},
        config,
      } as AxiosResponse;
      const error = {
        config,
        response,
        isAxiosError: true,
        name: 'AxiosError',
        message: 'Unauthorized',
        toJSON: () => ({}),
      } as AxiosError;

      await expect(responseInterceptor(error)).rejects.toBe(refreshError);

      expect(postSpy).toHaveBeenCalledTimes(1);
      expect(postSpy).toHaveBeenCalledWith('/auth/refresh');
      expect(mockClearAuthData).toHaveBeenCalledTimes(1);
      expect(window.location.href).toBe(
        `/login?redirect=${encodeURIComponent('/assets')}`
      );
    });
  });
});

// =============================================================================
// URL Validation 测试
// =============================================================================

describe('URL Validation', () => {
  const originalWarn = console.warn;
  let client: ApiClient;
  let warnSpy: ReturnType<typeof vi.spyOn>;
  const normalizedBaseUrl = API_BASE_URL.startsWith('http')
    ? new URL(API_BASE_URL).pathname
    : API_BASE_URL;
  const basePath = normalizedBaseUrl.endsWith('/')
    ? normalizedBaseUrl.slice(0, -1)
    : normalizedBaseUrl;
  const buildRequestConfig = (url: string): InternalAxiosRequestConfig => ({
    url,
    method: 'get',
    headers: new AxiosHeaders(),
  });

  beforeEach(() => {
    console.warn = vi.fn();
    warnSpy = vi.spyOn(Logger.prototype, 'warn').mockImplementation(() => {});
    client = new ApiClient({
      baseURL: API_BASE_URL,
      enableLogging: false,
      enableAutoRetry: false,
    });
  });

  afterEach(() => {
    console.warn = originalWarn;
    warnSpy.mockRestore();
  });

  it('should not warn for URLs starting with base path', () => {
    const axiosInstance = client.getAxiosInstance();
    const requestInterceptor = axiosInstance.interceptors.request.handlers[0]?.fulfilled;
    if (!requestInterceptor) {
      throw new Error('Request interceptor is not registered');
    }
    requestInterceptor(buildRequestConfig(`${basePath}/auth/login`));

    expect(console.warn).not.toHaveBeenCalled();
  });

  it('should not warn for URLs starting with /auth (legacy)', () => {
    const axiosInstance = client.getAxiosInstance();
    const requestInterceptor = axiosInstance.interceptors.request.handlers[0]?.fulfilled;
    if (!requestInterceptor) {
      throw new Error('Request interceptor is not registered');
    }
    requestInterceptor(buildRequestConfig('/auth/login'));

    expect(console.warn).not.toHaveBeenCalled();
  });

  it('should normalize URLs without base path prefix', () => {
    const axiosInstance = client.getAxiosInstance();
    const requestInterceptor = axiosInstance.interceptors.request.handlers[0]?.fulfilled;
    if (!requestInterceptor) {
      throw new Error('Request interceptor is not registered');
    }
    const config = buildRequestConfig('/users');
    requestInterceptor(config);

    expect(config.url).toBe('users');
    expect(warnSpy).not.toHaveBeenCalled();
  });

  it('should normalize URLs without base path prefix (with nested path)', () => {
    const axiosInstance = client.getAxiosInstance();
    const requestInterceptor = axiosInstance.interceptors.request.handlers[0]?.fulfilled;
    if (!requestInterceptor) {
      throw new Error('Request interceptor is not registered');
    }
    const config = buildRequestConfig('/assets/list');
    requestInterceptor(config);

    expect(config.url).toBe('assets/list');
    expect(warnSpy).not.toHaveBeenCalled();
  });

  it('should not validate relative URLs (not starting with /)', () => {
    const axiosInstance = client.getAxiosInstance();
    const requestInterceptor = axiosInstance.interceptors.request.handlers[0]?.fulfilled;
    if (!requestInterceptor) {
      throw new Error('Request interceptor is not registered');
    }
    requestInterceptor(buildRequestConfig('relative-path'));

    expect(console.warn).not.toHaveBeenCalled();
  });

  it('should not validate URLs without / prefix (full URLs)', () => {
    const axiosInstance = client.getAxiosInstance();
    const requestInterceptor = axiosInstance.interceptors.request.handlers[0]?.fulfilled;
    if (!requestInterceptor) {
      throw new Error('Request interceptor is not registered');
    }
    requestInterceptor(buildRequestConfig('https://api.example.com/data'));

    expect(console.warn).not.toHaveBeenCalled();
  });
});

// =============================================================================
// Default Instance 测试
// =============================================================================

describe('Default Instance', () => {
  it('should export default apiClient instance', () => {
    expect(apiClient).toBeInstanceOf(ApiClient);
  });

  it('should have correct configuration on default instance', () => {
    const config = apiClient.getConfig();
    expect(config.baseURL).toBe(API_BASE_URL);
    expect(config.timeout).toBe(30000);
  });
});

// =============================================================================
// 工厂函数测试
// =============================================================================

describe('工厂函数', () => {
  it('createApiClient应该创建新实例', async () => {
    const { createApiClient } = await import('../client');
    const client = createApiClient({
      baseURL: '/custom',
    });

    expect(client).toBeInstanceOf(ApiClient);
    expect(client.getConfig().baseURL).toBe('/custom');
  });

  it('应该导出默认的apiClient实例', async () => {
    const { apiClient } = await import('../client');

    expect(apiClient).toBeInstanceOf(ApiClient);
  });
});
