/**
 * API配置文件
 * 注意: 端点配置已迁移至 constants/api.ts，请使用那里的配置
 * 此文件仅保留通用配置（超时、重试、缓存等）
 */

// 获取环境变量的辅助函数，兼容Vite环境
const getEnvVar = (key: string, defaultValue: string) => {
  // 在Vite环境中使用import.meta.env
  const envKey = key.replace('VITE_', '');
  return import.meta.env[key] || import.meta.env[`VITE_${envKey}`] || defaultValue;
};

export const API_CONFIG = {
  // 基础配置
  BASE_URL: '/api/v1', // 统一使用 /api/v1
  TIMEOUT: parseInt(getEnvVar('VITE_API_TIMEOUT', '30000')),

  // 重试配置
  RETRY: {
    ATTEMPTS: 3,
    DELAY: 1000,
    BACKOFF_FACTOR: 2,
  },

  // 缓存配置
  CACHE: {
    DEFAULT_TTL: 5 * 60 * 1000, // 5分钟
    LONG_TTL: 30 * 60 * 1000,   // 30分钟
    SHORT_TTL: 1 * 60 * 1000,   // 1分钟
  },

  // 文件上传配置
  UPLOAD: {
    MAX_SIZE: 50 * 1024 * 1024, // 50MB
    CHUNK_SIZE: 1024 * 1024,    // 1MB
    ALLOWED_TYPES: [
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      'application/vnd.ms-excel',
      'text/csv',
    ],
  },

  // 分页配置
  PAGINATION: {
    DEFAULT_PAGE_SIZE: 20,
    MAX_PAGE_SIZE: 100,
    PAGE_SIZE_OPTIONS: [10, 20, 50, 100],
  },

  /**
   * 端点配置已迁移至 constants/api.ts
   * 请使用 import { API_ENDPOINTS } from '@/constants/api'
   * @deprecated 使用 constants/api.ts 中的 API_ENDPOINTS
   */
  ENDPOINTS: {} as const,

  // 错误代码映射
  ERROR_CODES: {
    NETWORK_ERROR: 'NETWORK_ERROR',
    TIMEOUT_ERROR: 'TIMEOUT_ERROR',
    VALIDATION_ERROR: 'VALIDATION_ERROR',
    PERMISSION_ERROR: 'PERMISSION_ERROR',
    NOT_FOUND_ERROR: 'NOT_FOUND_ERROR',
    SERVER_ERROR: 'SERVER_ERROR',
  },

  // HTTP状态码映射
  HTTP_STATUS: {
    OK: 200,
    CREATED: 201,
    NO_CONTENT: 204,
    BAD_REQUEST: 400,
    UNAUTHORIZED: 401,
    FORBIDDEN: 403,
    NOT_FOUND: 404,
    CONFLICT: 409,
    UNPROCESSABLE_ENTITY: 422,
    INTERNAL_SERVER_ERROR: 500,
    BAD_GATEWAY: 502,
    SERVICE_UNAVAILABLE: 503,
  },

  // 请求头配置
  HEADERS: {
    CONTENT_TYPE: 'Content-Type',
    AUTHORIZATION: 'Authorization',
    REQUEST_ID: 'X-Request-ID',
    USER_AGENT: 'X-User-Agent',
    CLIENT_VERSION: 'X-Client-Version',
  },

  // 环境配置
  ENV: {
    DEVELOPMENT: import.meta.env.DEV,
    PRODUCTION: import.meta.env.PROD,
    API_URL: import.meta.env.VITE_API_BASE_URL,
    APP_VERSION: import.meta.env.VITE_APP_VERSION || '1.0.0',
  },
}

// 导出常用配置
export const {
  BASE_URL,
  TIMEOUT,
  RETRY,
  CACHE,
  UPLOAD,
  PAGINATION,
  ERROR_CODES,
  HTTP_STATUS,
  HEADERS,
  ENV,
} = API_CONFIG

// 导出工具函数
export const isProduction = () => ENV.PRODUCTION
export const isDevelopment = () => ENV.DEVELOPMENT

// 获取完整的API URL
export const getApiUrl = (endpoint: string) => {
  return `${BASE_URL}${endpoint}`
}

// 验证文件类型
export const isValidFileType = (file: File) => {
  return UPLOAD.ALLOWED_TYPES.includes(file.type)
}

// 验证文件大小
export const isValidFileSize = (file: File) => {
  return file.size <= UPLOAD.MAX_SIZE
}

// 格式化文件大小
export const formatFileSize = (bytes: number): string => {
  if (bytes === 0) return '0 B'

  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))

  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(2))} ${sizes[i]}`
}

// 生成请求ID
export const generateRequestId = (): string => {
  return `req_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
}

// 延迟函数
export const delay = (ms: number): Promise<void> => {
  return new Promise(resolve => setTimeout(resolve, ms))
}
