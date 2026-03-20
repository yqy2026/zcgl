/**
 * API客户端辅助工具
 * 包含常量、类型定义、辅助函数、缓存管理器和重试管理器
 */

import {
  InternalAxiosRequestConfig,
  AxiosResponse,
  AxiosError,
} from 'axios';
import { RetryConfig } from '@/types/apiResponse';
import { createLogger } from '@/utils/logger';
import { AuthStorage } from '@/utils/AuthStorage';
import { viewSelectionStorage } from '@/utils/viewSelectionStorage';
import { API_BASE_URL } from './config';

// ==================== Logger ====================

export const apiLogger = createLogger('API');

// ==================== 常量 ====================

export const AUTHZ_STALE_HEADER_NAME = 'x-authz-stale';
export const AUTHZ_STALE_EVENT_NAME = 'authz-stale';
export const VIEW_PERSPECTIVE_HEADER_NAME = 'X-View-Perspective';
export const VIEW_PARTY_ID_HEADER_NAME = 'X-View-Party-Id';

// ==================== 类型定义 ====================

/**
 * 扩展的请求配置，包含重试标记
 */
export interface ExtendedAxiosRequestConfig extends InternalAxiosRequestConfig {
  _retry?: boolean;
  _skipAuthRefresh?: boolean;
  _suppressAuthRedirect?: boolean;
}

// ==================== 辅助函数 ====================

export const getCookieValue = (name: string): string | null => {
  if (typeof document === 'undefined') {
    return null;
  }

  const cookieString = document.cookie;
  if (cookieString === '') {
    return null;
  }

  const cookies = cookieString.split(';');
  for (const cookie of cookies) {
    const trimmed = cookie.trim();
    if (trimmed === '') {
      continue;
    }
    const separatorIndex = trimmed.indexOf('=');
    if (separatorIndex < 0) {
      continue;
    }
    const key = decodeURIComponent(trimmed.slice(0, separatorIndex));
    if (key === name) {
      return decodeURIComponent(trimmed.slice(separatorIndex + 1));
    }
  }

  return null;
};

export const setHeaderIfMissing = (
  headers: InternalAxiosRequestConfig['headers'],
  name: string,
  value: string
): void => {
  if (headers == null) {
    return;
  }

  const hasFn = (headers as { has?: (headerName: string) => boolean }).has;
  if (typeof hasFn === 'function' && hasFn.call(headers, name)) {
    return;
  }

  const setFn = (headers as { set?: (headerName: string, val: string) => void }).set;
  if (typeof setFn === 'function') {
    setFn.call(headers, name, value);
    return;
  }

  const record = headers as Record<string, string>;
  if (record[name] == null) {
    record[name] = value;
  }
};

export const getHeaderValue = (
  headers:
    | InternalAxiosRequestConfig['headers']
    | AxiosResponse['headers']
    | Record<string, unknown>
    | undefined,
  name: string
): string | undefined => {
  if (headers == null) {
    return undefined;
  }

  const normalizedName = name.toLowerCase();
  const getFn = (headers as { get?: (headerName: string) => unknown }).get;
  if (typeof getFn === 'function') {
    const value = getFn.call(headers, name) ?? getFn.call(headers, normalizedName);
    if (typeof value === 'string') {
      return value;
    }
    if (Array.isArray(value)) {
      return value.join(',');
    }
    if (value != null) {
      return String(value);
    }
  }

  for (const [key, value] of Object.entries(headers as Record<string, unknown>)) {
    if (key.toLowerCase() !== normalizedName) {
      continue;
    }
    if (typeof value === 'string') {
      return value;
    }
    if (Array.isArray(value)) {
      return value.join(',');
    }
    if (value != null) {
      return String(value);
    }
  }

  return undefined;
};

export const shouldDispatchAuthzStaleEvent = (
  axiosError: AxiosError<unknown, ExtendedAxiosRequestConfig>,
  originalRequest: ExtendedAxiosRequestConfig | undefined
): boolean => {
  const responseStatus = axiosError.response?.status;
  if (responseStatus !== 403 && responseStatus !== 404) {
    return false;
  }

  const authzStaleHeader = getHeaderValue(
    axiosError.response?.headers as AxiosResponse['headers'] | undefined,
    AUTHZ_STALE_HEADER_NAME
  );
  if (typeof authzStaleHeader !== 'string' || authzStaleHeader.toLowerCase() !== 'true') {
    return false;
  }

  const currentUser = AuthStorage.getCurrentUser();
  const currentUserId =
    currentUser != null && typeof currentUser.id === 'string' ? currentUser.id : '';
  if (currentUserId.trim() === '') {
    return false;
  }

  const currentView = viewSelectionStorage.get(currentUserId);
  if (currentView == null) {
    return false;
  }

  const requestPerspective = getHeaderValue(originalRequest?.headers, VIEW_PERSPECTIVE_HEADER_NAME);
  const requestPartyId = getHeaderValue(originalRequest?.headers, VIEW_PARTY_ID_HEADER_NAME);
  if (requestPerspective == null || requestPartyId == null) {
    return false;
  }

  return (
    requestPerspective === currentView.perspective && requestPartyId === currentView.partyId
  );
};

// ==================== URL验证 ====================

/**
 * 验证API路径是否使用正确的基础前缀
 * @param url API URL
 */
export const validateApiPath = (url: string): void => {
  if (url.startsWith('/')) {
    const normalizedBaseUrl = API_BASE_URL.startsWith('http')
      ? new URL(API_BASE_URL).pathname
      : API_BASE_URL;
    const basePath = normalizedBaseUrl.endsWith('/')
      ? normalizedBaseUrl.slice(0, -1)
      : normalizedBaseUrl;
    if (!url.startsWith(basePath) && !url.startsWith('/auth')) {
      apiLogger.warn(
        `URL does not use ${basePath} prefix: ${url}. All API calls should use the centralized API client with correct prefix.`,
        { url, basePath }
      );
    }
  }
};

// ==================== 缓存管理器 ====================

/**
 * 简单的内存缓存实现
 */
export class MemoryCache {
  private cache = new Map<string, { data: unknown; timestamp: number; ttl: number }>();
  private maxSize: number;
  private cleanupInterval: ReturnType<typeof setInterval> | null = null;

  constructor(maxSize: number = 100) {
    this.maxSize = maxSize;
  }

  set(key: string, data: unknown, ttl: number): void {
    if (!this.cleanupInterval) {
      this.cleanupInterval = setInterval(() => {
        this.cleanup();
      }, 60000);
    }

    if (this.cache.has(key)) {
      this.cache.delete(key);
    } else if (this.cache.size >= this.maxSize) {
      const firstKey = this.cache.keys().next().value;
      if (firstKey !== undefined) {
        this.cache.delete(firstKey);
      }
    }

    this.cache.set(key, {
      data,
      timestamp: Date.now(),
      ttl,
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

    this.cache.delete(key);
    this.cache.set(key, {
      data: item.data,
      timestamp: item.timestamp,
      ttl: item.ttl,
    });

    return item.data;
  }

  private cleanup(): void {
    const now = Date.now();
    for (const [key, item] of this.cache.entries()) {
      if (now - item.timestamp > item.ttl) {
        this.cache.delete(key);
      }
    }
  }

  clear(): void {
    this.cache.clear();
    if (this.cleanupInterval) {
      clearInterval(this.cleanupInterval);
      this.cleanupInterval = null;
    }
  }

  dispose(): void {
    this.clear();
  }

  delete(key: string): void {
    this.cache.delete(key);
  }

  deleteByPrefix(prefix: string): void {
    if (prefix.trim() === '') {
      return;
    }

    for (const key of this.cache.keys()) {
      if (key.startsWith(prefix)) {
        this.cache.delete(key);
      }
    }
  }

  size(): number {
    return this.cache.size;
  }
}

// ==================== 重试管理器 ====================

/**
 * 重试管理器
 */
export class RetryManager {
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
      if (
        attempt < config.maxAttempts &&
        (!config.retryCondition || config.retryCondition(error))
      ) {
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
