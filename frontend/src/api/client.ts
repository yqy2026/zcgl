/**
 * API客户端
 * 提供统一的响应处理、错误处理、重试和缓存功能
 *
 * 此文件是 API 客户端的主入口，同时作为 re-export hub 保持向后兼容。
 * 实现细节拆分至:
 *   - ./clientHelpers  (辅助函数、常量、缓存/重试管理器)
 *   - ./interceptors   (请求/响应拦截器)
 */

import axios, {
  AxiosInstance,
  AxiosRequestConfig,
  AxiosResponse,
} from 'axios';
import { ResponseExtractor, ApiErrorHandler } from '@/utils/responseExtractor';
import { ApiClientConfig, RetryConfig, ExtractResult } from '@/types/apiResponse';
import { isDevelopmentMode } from '@/utils/runtimeEnv';
import { API_BASE_URL } from './config';
import {
  apiLogger,
  ExtendedAxiosRequestConfig,
  MemoryCache,
  RetryManager,
} from './clientHelpers';
import { setupInterceptors } from './interceptors';

// ==================== 主要客户端类 ====================

/**
 * API客户端
 */
export class ApiClient {
  private instance: AxiosInstance;
  private cache: MemoryCache;
  private config: ApiClientConfig;

  constructor(config: ApiClientConfig = {}) {
    this.config = {
      // 默认配置
      baseURL: config.baseURL ?? API_BASE_URL,
      timeout: config.timeout ?? 30000,
      responseDetection: {
        successField: 'success',
        dataField: 'data',
        errorFields: ['error', 'message'],
        strict: false,
        ...config.responseDetection,
      },
      defaultRetryConfig: {
        maxAttempts: 3,
        delay: 1000,
        backoffMultiplier: 2,
        ...config.defaultRetryConfig,
      },
      defaultCacheConfig: {
        enabled: false,
        ttl: 5 * 60 * 1000, // 5分钟
        maxSize: 100,
        ...config.defaultCacheConfig,
      },
      enableAutoRetry: config.enableAutoRetry ?? false,
      enableCaching: config.enableCaching ?? false,
      enableLogging: config.enableLogging ?? isDevelopmentMode(),
      enableTypeValidation: config.enableTypeValidation ?? false,
      globalErrorHandler: config.globalErrorHandler,
      requestInterceptors: config.requestInterceptors || [],
      responseInterceptors: config.responseInterceptors || [],
      ...config,
    };

    // 初始化axios实例
    this.instance = axios.create({
      baseURL: this.config.baseURL,
      timeout: this.config.timeout,
      withCredentials: true, // Include cookies in requests for httpOnly cookie auth
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // 初始化缓存
    this.cache = new MemoryCache(this.config.defaultCacheConfig!.maxSize);

    // 设置拦截器
    setupInterceptors(this.instance, this.config, () => this.generateRequestId());
  }

  // ==================== 核心HTTP方法 ====================

  /**
   * GET请求
   */
  async get<T = unknown>(
    url: string,
    config?: AxiosRequestConfig & {
      cache?: boolean;
      retry?: boolean | RetryConfig;
      skipAuthRefresh?: boolean;
      suppressAuthRedirect?: boolean;
      smartExtract?: boolean;
    }
  ): Promise<ExtractResult<T>> {
    const {
      cache = this.config.defaultCacheConfig?.enabled,
      retry = this.config.enableAutoRetry,
      skipAuthRefresh = false,
      suppressAuthRedirect = false,
      smartExtract = true,
      ...axiosConfig
    } = config || {};

    // 检查缓存
    if (cache === true) {
      const cacheKey = this.generateCacheKey('GET', url, axiosConfig.params);
      const cachedData = this.cache.get(cacheKey);
      if (cachedData !== null && cachedData !== undefined) {
        if (this.config.enableLogging === true) {
          apiLogger.debug(`📦 Cache Hit: ${url}`);
        }
        if (smartExtract) {
          const cachedResponse = {
            data: cachedData,
            config: {
              url,
              method: 'get',
            },
            status: 200,
            statusText: 'OK',
            headers: {},
          } as AxiosResponse;
          return ResponseExtractor.smartExtract<T>(cachedResponse, {
            detection: this.config.responseDetection,
            enableTypeValidation: this.config.enableTypeValidation,
          });
        }
        return {
          success: true,
          data: cachedData as T,
          rawResponse: {} as AxiosResponse,
        };
      }
    }

    // 执行请求
    const executeRequest = async (): Promise<AxiosResponse> => {
      const requestConfig: AxiosRequestConfig = {
        ...axiosConfig,
      };

      if (skipAuthRefresh === true) {
        (requestConfig as ExtendedAxiosRequestConfig)._skipAuthRefresh = true;
      }
      if (suppressAuthRedirect === true) {
        (requestConfig as ExtendedAxiosRequestConfig)._suppressAuthRedirect = true;
      }

      const response = await this.instance.get(url, requestConfig);

      // 存储到缓存
      if (cache === true && response.data !== undefined && response.data !== null) {
        const cacheKey = this.generateCacheKey('GET', url, axiosConfig.params);
        this.cache.set(cacheKey, response.data, this.config.defaultCacheConfig!.ttl);
      }

      return response;
    };

    // 处理重试
    let response: AxiosResponse;
    if (retry === true) {
      response = await RetryManager.executeWithRetry(
        executeRequest,
        this.config.defaultRetryConfig!
      );
    } else if (retry !== undefined && retry !== null && typeof retry === 'object') {
      response = await RetryManager.executeWithRetry(executeRequest, retry);
    } else {
      response = await executeRequest();
    }

    // 智能提取数据
    if (smartExtract) {
      return ResponseExtractor.smartExtract<T>(response, {
        detection: this.config.responseDetection,
        enableTypeValidation: this.config.enableTypeValidation,
      });
    }

    return {
      success: true,
      data: response.data as T,
      rawResponse: response,
    };
  }

  /**
   * POST请求
   */
  async post<T = unknown>(
    url: string,
    data?: unknown,
    config?: AxiosRequestConfig & {
      retry?: boolean | RetryConfig;
      smartExtract?: boolean;
    }
  ): Promise<ExtractResult<T>> {
    const {
      retry = this.config.enableAutoRetry,
      smartExtract = true,
      ...axiosConfig
    } = config || {};

    const executeRequest = async (): Promise<AxiosResponse> => {
      return await this.instance.post(url, data, axiosConfig);
    };

    // 处理重试
    let response: AxiosResponse;
    if (retry === true) {
      response = await RetryManager.executeWithRetry(
        executeRequest,
        this.config.defaultRetryConfig!
      );
    } else if (retry !== undefined && retry !== null && typeof retry === 'object') {
      response = await RetryManager.executeWithRetry(executeRequest, retry);
    } else {
      response = await executeRequest();
    }

    // 智能提取数据
    if (smartExtract) {
      return ResponseExtractor.smartExtract<T>(response, {
        detection: this.config.responseDetection,
        enableTypeValidation: this.config.enableTypeValidation,
      });
    }

    return {
      success: true,
      data: response.data as T,
      rawResponse: response,
    };
  }

  /**
   * PUT请求
   */
  async put<T = unknown>(
    url: string,
    data?: unknown,
    config?: AxiosRequestConfig & {
      retry?: boolean | RetryConfig;
      smartExtract?: boolean;
    }
  ): Promise<ExtractResult<T>> {
    const {
      retry = this.config.enableAutoRetry,
      smartExtract = true,
      ...axiosConfig
    } = config || {};

    const executeRequest = async (): Promise<AxiosResponse> => {
      return await this.instance.put(url, data, axiosConfig);
    };

    // 处理重试
    let response: AxiosResponse;
    if (retry === true) {
      response = await RetryManager.executeWithRetry(
        executeRequest,
        this.config.defaultRetryConfig!
      );
    } else if (retry !== undefined && retry !== null && typeof retry === 'object') {
      response = await RetryManager.executeWithRetry(executeRequest, retry);
    } else {
      response = await executeRequest();
    }

    // 智能提取数据
    if (smartExtract) {
      return ResponseExtractor.smartExtract<T>(response, {
        detection: this.config.responseDetection,
        enableTypeValidation: this.config.enableTypeValidation,
      });
    }

    return {
      success: true,
      data: response.data as T,
      rawResponse: response,
    };
  }

  /**
   * DELETE请求
   */
  async delete<T = unknown>(
    url: string,
    config?: AxiosRequestConfig & {
      retry?: boolean | RetryConfig;
      smartExtract?: boolean;
    }
  ): Promise<ExtractResult<T>> {
    const {
      retry = this.config.enableAutoRetry,
      smartExtract = true,
      ...axiosConfig
    } = config || {};

    const executeRequest = async (): Promise<AxiosResponse> => {
      return await this.instance.delete(url, axiosConfig);
    };

    // 处理重试
    let response: AxiosResponse;
    if (retry === true) {
      response = await RetryManager.executeWithRetry(
        executeRequest,
        this.config.defaultRetryConfig!
      );
    } else if (retry !== undefined && retry !== null && typeof retry === 'object') {
      response = await RetryManager.executeWithRetry(executeRequest, retry);
    } else {
      response = await executeRequest();
    }

    // 智能提取数据
    if (smartExtract) {
      return ResponseExtractor.smartExtract<T>(response, {
        detection: this.config.responseDetection,
        enableTypeValidation: this.config.enableTypeValidation,
      });
    }

    return {
      success: true,
      data: response.data as T,
      rawResponse: response,
    };
  }

  // ==================== 便捷方法 ====================

  /**
   * 快速获取数据（忽略提取结果检查）
   */
  async getData<T = unknown>(
    url: string,
    defaultValue?: T,
    config?: AxiosRequestConfig
  ): Promise<T> {
    const result = await this.get<T>(url, { ...config, smartExtract: true });

    if (!result.success) {
      apiLogger.warn(`数据获取失败: ${result.error}`);
      return defaultValue as T;
    }

    return result.data!;
  }

  /**
   * 批量请求
   */
  async batch<T = unknown>(
    requests: Array<{
      method: 'GET' | 'POST' | 'PUT' | 'DELETE';
      url: string;
      data?: unknown;
      config?: AxiosRequestConfig;
    }>
  ): Promise<ExtractResult<T>[]> {
    const promises = requests.map(async request => {
      switch (request.method) {
        case 'GET':
          return await this.get<T>(request.url, request.config);
        case 'POST':
          return await this.post<T>(request.url, request.data, request.config);
        case 'PUT':
          return await this.put<T>(request.url, request.data, request.config);
        case 'DELETE':
          return await this.delete<T>(request.url, request.config);
        default:
          throw new Error(`不支持的请求方法: ${request.method}`);
      }
    });

    const results = await Promise.allSettled(promises);
    return results.map(result => {
      if (result.status === 'fulfilled') {
        return result.value;
      }

      const enhancedError = ApiErrorHandler.handleError(result.reason);
      if (this.config.enableLogging === true) {
        apiLogger.error('Batch request failed', enhancedError);
      }

      return {
        success: false,
        error: enhancedError.message,
        rawResponse: {} as AxiosResponse,
      };
    });
  }

  // ==================== 工具方法 ====================

  /**
   * 生成请求ID
   */
  private generateRequestId(): string {
    return `req_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  /**
   * 生成缓存键
   */
  private generateCacheKey(method: string, url: string, params?: Record<string, unknown>): string {
    const paramsStr = params ? JSON.stringify(this.normalizeParams(params)) : '';
    return `${method}:${url}:${paramsStr}`;
  }

  private normalizeParams(value: unknown): unknown {
    if (Array.isArray(value)) {
      return value.map(item => this.normalizeParams(item));
    }

    if (value && typeof value === 'object') {
      if (value instanceof Date) {
        return value.toISOString();
      }

      // 检查是否为普通对象
      if (Object.prototype.toString.call(value) === '[object Object]') {
        const entries = Object.entries(value as Record<string, unknown>).sort(([a], [b]) =>
          a.localeCompare(b)
        );
        return entries.reduce<Record<string, unknown>>((acc, [key, val]) => {
          acc[key] = this.normalizeParams(val);
          return acc;
        }, {});
      }

      // 如果是其他类型的对象（如Map, Set等），转换为字符串
      return value.toString();
    }

    return value;
  }

  /**
   * 失效指定缓存
   */
  invalidateCache(method: string, url: string, params?: Record<string, unknown>): void {
    const normalizedMethod = method.toUpperCase();
    const cacheKey = this.generateCacheKey(normalizedMethod, url, params);
    this.cache.delete(cacheKey);
  }

  /**
   * 按前缀失效缓存
   */
  invalidateCacheByPrefix(prefix: string): void {
    this.cache.deleteByPrefix(prefix);
  }

  /**
   * 清除缓存
   */
  clearCache(): void {
    this.cache.clear();
  }

  /**
   * 释放资源（清理缓存与定时器）
   */
  dispose(): void {
    this.cache.dispose();
  }

  /**
   * 获取缓存大小
   */
  getCacheSize(): number {
    return this.cache.size();
  }

  /**
   * 获取axios实例（用于高级用法）
   */
  getAxiosInstance(): AxiosInstance {
    return this.instance;
  }

  /**
   * 更新配置
   */
  updateConfig(newConfig: Partial<ApiClientConfig>): void {
    this.config = { ...this.config, ...newConfig };
  }

  /**
   * 获取当前配置
   */
  getConfig(): ApiClientConfig {
    return { ...this.config };
  }
}

// ==================== 默认实例 ====================

/**
 * 创建默认的API客户端实例
 */
export const createApiClient = (config?: ApiClientConfig): ApiClient => {
  return new ApiClient(config);
};

/**
 * 默认实例
 */
export const apiClient = new ApiClient({
  baseURL: API_BASE_URL,
  enableAutoRetry: true,
  enableLogging: isDevelopmentMode(),
  defaultRetryConfig: {
    maxAttempts: 3,
    delay: 1000,
    backoffMultiplier: 2,
  },
});

export default ApiClient;
