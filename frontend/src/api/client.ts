/**
 * 增强型API客户端
 * 提供统一的响应处理、错误处理、重试和缓存功能
 */

import axios, {
  AxiosInstance,
  AxiosRequestConfig,
  AxiosResponse,
  InternalAxiosRequestConfig,
  AxiosError
} from 'axios';
import { ResponseExtractor, ApiErrorHandler } from '../utils/responseExtractor';
import {
  EnhancedApiClientConfig,
  RetryConfig,
  ExtractResult
} from '../types/apiResponse';
import { createLogger } from '../utils/logger';

const apiLogger = createLogger('API');

// ==================== 类型定义 ====================

/**
 * 扩展的请求配置，包含重试标记
 */
interface ExtendedAxiosRequestConfig extends InternalAxiosRequestConfig {
  _retry?: boolean;
}

// ==================== 缓存管理器 ====================

/**
 * 简单的内存缓存实现
 */
class MemoryCache {
  private cache = new Map<string, { data: unknown; timestamp: number; ttl: number }>();
  private maxSize: number;

  constructor(maxSize: number = 100) {
    this.maxSize = maxSize;
  }

  set(key: string, data: unknown, ttl: number): void {
    // 如果缓存已满，删除最旧的条目
    if (this.cache.size >= this.maxSize) {
      const firstKey = this.cache.keys().next().value;
      if (firstKey !== undefined) {
        this.cache.delete(firstKey);
      }
    }

    this.cache.set(key, {
      data,
      timestamp: Date.now(),
      ttl
    });
  }

  get(key: string): unknown | null {
    const item = this.cache.get(key);
    if (!item) {
      return null;
    }

    // 检查是否过期
    if (Date.now() - item.timestamp > item.ttl) {
      this.cache.delete(key);
      return null;
    }

    return item.data;
  }

  clear(): void {
    this.cache.clear();
  }

  delete(key: string): void {
    this.cache.delete(key);
  }

  size(): number {
    return this.cache.size;
  }
}

// ==================== 重试管理器 ====================

/**
 * 重试管理器
 */
class RetryManager {
  /**
   * 执行带重试的请求
   */
  static async executeWithRetry<T>(
    requestFn: () => Promise<T>,
    config: RetryConfig,
    attempt: number = 1
  ): Promise<T> {
    try {
      return await requestFn();
    } catch (error) {
      // 检查是否应该重试
      if (attempt < config.maxAttempts && (!config.retryCondition || config.retryCondition(error))) {
        // 计算延迟时间（指数退避）
        const delay = config.delay * Math.pow(config.backoffMultiplier, attempt - 1);
        await new Promise(resolve => setTimeout(resolve, delay));

        apiLogger.warn(`请求失败，第 ${attempt} 次重试...`, { error, attempt });
        return this.executeWithRetry(requestFn, config, attempt + 1);
      }

      throw error;
    }
  }
}

// ==================== 主要客户端类 ====================

/**
 * 增强型API客户端
 */
export class EnhancedApiClient {
  private instance: AxiosInstance;
  private cache: MemoryCache;
  private config: EnhancedApiClientConfig;

  constructor(config: EnhancedApiClientConfig = {}) {
    this.config = {
      // 默认配置
      baseURL: config.baseURL ?? '/api/v1',
      timeout: config.timeout ?? 30000,
      responseDetection: {
        successField: 'success',
        dataField: 'data',
        errorFields: ['error', 'message'],
        strict: false,
        ...config.responseDetection
      },
      defaultRetryConfig: {
        maxAttempts: 3,
        delay: 1000,
        backoffMultiplier: 2,
        ...config.defaultRetryConfig
      },
      defaultCacheConfig: {
        enabled: false,
        ttl: 5 * 60 * 1000, // 5分钟
        maxSize: 100,
        ...config.defaultCacheConfig
      },
      enableAutoRetry: config.enableAutoRetry ?? false,
      enableCaching: config.enableCaching ?? false,
      enableLogging: config.enableLogging ?? process.env.NODE_ENV === 'development',
      enableTypeValidation: config.enableTypeValidation ?? false,
      globalErrorHandler: config.globalErrorHandler,
      requestInterceptors: config.requestInterceptors || [],
      responseInterceptors: config.responseInterceptors || [],
      ...config
    };

    // 初始化axios实例
    this.instance = axios.create({
      baseURL: this.config.baseURL,
      timeout: this.config.timeout,
      headers: {
        'Content-Type': 'application/json'
      }
    });

    // 初始化缓存
    this.cache = new MemoryCache(this.config.defaultCacheConfig!.maxSize);

    // 设置拦截器
    this.setupInterceptors();
  }

  // ==================== 拦截器设置 ====================

  /**
   * 设置请求和响应拦截器
   */
  private setupInterceptors(): void {
    // 请求拦截器
    this.instance.interceptors.request.use(
      (config: InternalAxiosRequestConfig) => {
        // 添加认证token
        const token = localStorage.getItem('auth_token')
        if (token != null && config.headers != null) {
          config.headers.set('Authorization', `Bearer ${token}`)
        }

        // 添加请求ID
        if (config.headers != null) {
          config.headers.set('X-Request-ID', this.generateRequestId())
        }

        // 添加时间戳防止缓存
        if (config.method === 'get') {
          // eslint-disable-next-line @typescript-eslint/strict-boolean-expressions
          const params = ((config.params as unknown) || {}) as Record<string, unknown>
          config.params = {
            ...params,
            _t: Date.now()
          }
        }

        // 执行自定义请求拦截器
        if (this.config.requestInterceptors) {
          for (const interceptor of this.config.requestInterceptors) {
            config = interceptor(config)
          }
        }

        if (this.config.enableLogging === true) {
          apiLogger.debug(`🚀 API Request: ${config.method?.toUpperCase()} ${config.url}`, {
            params: config.params,
            data: config.data
          })
        }

        return config
      },
      (error) => {
        apiLogger.error('❌ Request Error:', error)
        return Promise.reject(error)
      }
    )

    // 响应拦截器
    this.instance.interceptors.response.use(
      (response: AxiosResponse) => {
        if (this.config.enableLogging === true) {
          apiLogger.debug(`✅ API Response: ${response.config.method?.toUpperCase()} ${response.config.url}`, {
            status: response.status,
            data: response.data
          })
        }

        // 执行自定义响应拦截器
        if (this.config.responseInterceptors) {
          let finalResponse = response
          for (const interceptor of this.config.responseInterceptors) {
            finalResponse = interceptor(finalResponse)
          }
          return finalResponse
        }

        return response
      },
      async (error: unknown) => {
        const axiosError = error as AxiosError<unknown, ExtendedAxiosRequestConfig>
        const originalRequest = axiosError.config as ExtendedAxiosRequestConfig | undefined

        // 处理401错误 - 自动刷新token
        if (axiosError.response?.status === 401 && originalRequest != null && originalRequest._retry !== true) {
          apiLogger.warn('🔑 Token过期，尝试刷新...')

          try {
            // 动态导入AuthService避免循环依赖
            const { AuthService } = await import('../services/authService')

            // 尝试刷新token
            await AuthService.refreshToken()

            apiLogger.info('✅ Token刷新成功，重试原始请求')

            // 标记请求已重试过，避免无限循环
            originalRequest._retry = true

            // 更新请求头中的token
            const newToken = localStorage.getItem('auth_token')
            if (newToken != null && originalRequest.headers != null) {
              originalRequest.headers.set('Authorization', `Bearer ${newToken}`)
            }

            // 重试原始请求
            return await this.instance(originalRequest)
          } catch (refreshError) {
            apiLogger.error('❌ Token刷新失败，执行登出', { refreshError })

            // 刷新失败，清除认证数据
            localStorage.removeItem('auth_token')
            localStorage.removeItem('refreshToken')
            localStorage.removeItem('user')

            // 跳转到登录页
            if (typeof window !== 'undefined') {
              window.location.href = '/login'
            }

            return Promise.reject(refreshError)
          }
        }

        const enhancedError = ApiErrorHandler.handleError(error)

        if (this.config.enableLogging === true) {
          apiLogger.error(`❌ API Error: ${enhancedError.type} - ${enhancedError.message}`, undefined, {
            config: axiosError.config,
            response: axiosError.response
          })
        }

        // 执行全局错误处理器
        if (this.config.globalErrorHandler) {
          this.config.globalErrorHandler(enhancedError)
        }

        return Promise.reject(enhancedError)
      }
    )
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
      smartExtract?: boolean;
    }
  ): Promise<ExtractResult<T>> {
    const {
      cache = this.config.defaultCacheConfig?.enabled,
      retry = this.config.enableAutoRetry,
      smartExtract = true,
      ...axiosConfig
    } = config || {};

    // 检查缓存
    if (cache === true) {
      const cacheKey = this.generateCacheKey('GET', url, axiosConfig.params)
      const cachedData = this.cache.get(cacheKey)
      if (cachedData !== null && cachedData !== undefined) {
        if (this.config.enableLogging === true) {
          apiLogger.debug(`📦 Cache Hit: ${url}`)
        }
        return {
          success: true,
          data: cachedData as T,
          rawResponse: {} as AxiosResponse
        }
      }
    }

    // 执行请求
    const executeRequest = async (): Promise<AxiosResponse> => {
      const response = await this.instance.get(url, axiosConfig)

      // 存储到缓存
      if (cache === true && response.data !== undefined && response.data !== null) {
        const cacheKey = this.generateCacheKey('GET', url, axiosConfig.params)
        this.cache.set(cacheKey, response.data, this.config.defaultCacheConfig!.ttl)
      }

      return response
    }

    // 处理重试
    let response: AxiosResponse
    if (retry === true) {
      response = await RetryManager.executeWithRetry(executeRequest, this.config.defaultRetryConfig!)
    } else if (retry !== undefined && retry !== null && typeof retry === 'object') {
      response = await RetryManager.executeWithRetry(executeRequest, retry)
    } else {
      response = await executeRequest()
    }

    // 智能提取数据
    if (smartExtract) {
      return ResponseExtractor.smartExtract<T>(response, {
        detection: this.config.responseDetection,
        enableTypeValidation: this.config.enableTypeValidation
      })
    }

    return {
      success: true,
      data: response.data as T,
      rawResponse: response
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
    let response: AxiosResponse
    if (retry === true) {
      response = await RetryManager.executeWithRetry(executeRequest, this.config.defaultRetryConfig!)
    } else if (retry !== undefined && retry !== null && typeof retry === 'object') {
      response = await RetryManager.executeWithRetry(executeRequest, retry)
    } else {
      response = await executeRequest()
    }

    // 智能提取数据
    if (smartExtract) {
      return ResponseExtractor.smartExtract<T>(response, {
        detection: this.config.responseDetection,
        enableTypeValidation: this.config.enableTypeValidation
      });
    }

    return {
      success: true,
      data: response.data as T,
      rawResponse: response
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
    let response: AxiosResponse
    if (retry === true) {
      response = await RetryManager.executeWithRetry(executeRequest, this.config.defaultRetryConfig!)
    } else if (retry !== undefined && retry !== null && typeof retry === 'object') {
      response = await RetryManager.executeWithRetry(executeRequest, retry)
    } else {
      response = await executeRequest()
    }

    // 智能提取数据
    if (smartExtract) {
      return ResponseExtractor.smartExtract<T>(response, {
        detection: this.config.responseDetection,
        enableTypeValidation: this.config.enableTypeValidation
      });
    }

    return {
      success: true,
      data: response.data as T,
      rawResponse: response
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
    let response: AxiosResponse
    if (retry === true) {
      response = await RetryManager.executeWithRetry(executeRequest, this.config.defaultRetryConfig!)
    } else if (retry !== undefined && retry !== null && typeof retry === 'object') {
      response = await RetryManager.executeWithRetry(executeRequest, retry)
    } else {
      response = await executeRequest()
    }

    // 智能提取数据
    if (smartExtract) {
      return ResponseExtractor.smartExtract<T>(response, {
        detection: this.config.responseDetection,
        enableTypeValidation: this.config.enableTypeValidation
      });
    }

    return {
      success: true,
      data: response.data as T,
      rawResponse: response
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
    const promises = requests.map(async (request) => {
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

    return await Promise.all(promises);
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
    const paramsStr = params ? JSON.stringify(params) : '';
    return `${method}:${url}:${paramsStr}`;
  }

  /**
   * 清除缓存
   */
  clearCache(): void {
    this.cache.clear();
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
  updateConfig(newConfig: Partial<EnhancedApiClientConfig>): void {
    this.config = { ...this.config, ...newConfig };
  }

  /**
   * 获取当前配置
   */
  getConfig(): EnhancedApiClientConfig {
    return { ...this.config };
  }
}

// ==================== 默认实例 ====================

/**
 * 创建默认的增强API客户端实例
 */
export const createEnhancedApiClient = (config?: EnhancedApiClientConfig): EnhancedApiClient => {
  return new EnhancedApiClient(config);
};

/**
 * 默认实例
 */
export const enhancedApiClient = new EnhancedApiClient({
  baseURL: '/api/v1',
  enableAutoRetry: true,
  enableLogging: process.env.NODE_ENV === 'development',
  defaultRetryConfig: {
    maxAttempts: 3,
    delay: 1000,
    backoffMultiplier: 2
  }
});

export default EnhancedApiClient;
