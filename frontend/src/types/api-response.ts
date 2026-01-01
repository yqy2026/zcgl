/**
 * 统一API响应类型定义
 * 为整个前端应用提供类型安全的API响应处理基础
 */

import { AxiosResponse } from 'axios';

// ==================== 基础响应类型 ====================

/**
 * 标准API响应格式
 * 适用于大部分后端API接口
 */
export interface StandardApiResponse<T = any> {
  success: boolean;
  data: T;
  message?: string;
  code?: string;
  timestamp?: string;
}

/**
 * 分页响应格式
 * 适用于列表类API接口
 */
export interface PaginatedApiResponse<T = any> {
  success: boolean;
  data: {
    items: T[];
    pagination: {
      page: number;
      pageSize: number;
      total: number;
      totalPages: number;
    };
  };
  message?: string;
}

/**
 * 简化响应格式
 * 直接返回数据，无包装结构
 */
export interface DirectResponse<T = any> {
  [key: string]: T;
}

/**
 * 错误响应格式
 */
export interface ErrorResponse {
  success: false;
  error: {
    code: string;
    message: string;
    details?: any;
    timestamp?: string;
  };
}

// ==================== 业务响应类型 ====================

/**
 * 用户认证响应
 */
export interface AuthResponse {
  user: {
    id: string;
    username: string;
    email?: string;
    full_name: string;
    role: string;
    is_active: boolean;
  };
  tokens: {
    access_token: string;
    refresh_token: string;
    token_type: string;
    expires_in: number;
  };
  permissions: string[];
}

/**
 * 资产列表响应
 */
export interface AssetListResponse {
  items: unknown[];
  total: number;
  page: number;
  limit: number;
  pages: number;
}

// ==================== 响应提取器类型 ====================

/**
 * 响应数据提取结果
 */
export interface ExtractResult<T> {
  success: boolean;
  data?: T;
  error?: string;
  rawResponse: AxiosResponse;
}

/**
 * 响应检测配置
 */
export interface ResponseDetectionConfig {
  // 成功检测字段
  successField?: string;
  // 数据字段
  dataField?: string;
  // 错误检测
  errorFields?: string[];
  // 是否启用严格模式
  strict?: boolean;
}

/**
 * 智能响应提取选项
 */
export interface SmartExtractOptions<T = any> {
  // 期望的数据类型
  expectedType?: new (...args: any[]) => T;
  // 自定义检测配置
  detection?: ResponseDetectionConfig;
  // 是否启用类型验证
  enableTypeValidation?: boolean;
  // 默认值
  defaultValue?: T;
}

// ==================== 错误处理类型 ====================

/**
 * API错误分类
 */
export enum ApiErrorType {
  NETWORK_ERROR = 'NETWORK_ERROR',
  SERVER_ERROR = 'SERVER_ERROR',
  CLIENT_ERROR = 'CLIENT_ERROR',
  AUTH_ERROR = 'AUTH_ERROR',
  VALIDATION_ERROR = 'VALIDATION_ERROR',
  BUSINESS_ERROR = 'BUSINESS_ERROR',
  UNKNOWN_ERROR = 'UNKNOWN_ERROR'
}

/**
 * 增强的API错误信息
 */
export interface EnhancedApiError {
  type: ApiErrorType;
  code: string;
  message: string;
  details?: any;
  timestamp: string;
  requestId?: string;
  statusCode?: number;
  originalError?: any;
}

// ==================== 重试和缓存类型 ====================

/**
 * 重试配置
 */
export interface RetryConfig {
  maxAttempts: number;
  delay: number;
  backoffMultiplier: number;
  retryCondition?: (error: any) => boolean;
}

/**
 * 缓存配置
 */
export interface CacheConfig {
  enabled: boolean;
  ttl: number; // 生存时间（毫秒）
  keyGenerator?: (config: any) => string;
  maxSize?: number;
}

// ==================== 统一API客户端配置 ====================

/**
 * 增强API客户端配置
 */
export interface EnhancedApiClientConfig {
  // 基础配置
  baseURL?: string;
  timeout?: number;

  // 响应处理配置
  responseDetection?: ResponseDetectionConfig;
  defaultRetryConfig?: RetryConfig;
  defaultCacheConfig?: CacheConfig;

  // 功能开关
  enableAutoRetry?: boolean;
  enableCaching?: boolean;
  enableLogging?: boolean;
  enableTypeValidation?: boolean;

  // 错误处理
  globalErrorHandler?: (error: EnhancedApiError) => void;

  // 拦截器
  requestInterceptors?: Array<(config: any) => any>;
  responseInterceptors?: Array<(response: AxiosResponse) => AxiosResponse>;
}

// ==================== 类型守卫和工具函数 ====================

/**
 * 检查是否为标准API响应
 */
export function isStandardApiResponse(response: any): response is StandardApiResponse {
  return response &&
    typeof response === 'object' &&
    'success' in response &&
    typeof response.success === 'boolean';
}

/**
 * 检查是否为分页响应
 */
export function isPaginatedResponse(response: any): response is PaginatedApiResponse {
  return isStandardApiResponse(response) &&
    response.data &&
    typeof response.data === 'object' &&
    'items' in response.data &&
    'pagination' in response.data;
}

/**
 * 检查是否为错误响应
 */
export function isErrorResponse(response: any): response is ErrorResponse {
  return response &&
    typeof response === 'object' &&
    response.success === false &&
    'error' in response;
}

/**
 * 检查是否为直接数据响应
 */
export function isDirectResponse<T>(response: any): response is DirectResponse<T> {
  return response &&
    typeof response === 'object' &&
    !('success' in response);
}

// ==================== 导出外部类型 ====================

export type { AxiosResponse } from 'axios';