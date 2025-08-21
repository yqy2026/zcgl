// API配置文件

export const API_CONFIG = {
  // 基础配置
  BASE_URL: import.meta.env.VITE_API_BASE_URL || '/api/v1',
  TIMEOUT: parseInt(import.meta.env.VITE_API_TIMEOUT || '30000'),
  
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
  
  // 端点配置
  ENDPOINTS: {
    // 资产管理
    ASSETS: '/assets',
    ASSET_DETAIL: (id: string) => `/assets/${id}`,
    ASSET_HISTORY: (id: string) => `/assets/${id}/history`,
    ASSET_VALIDATE: '/assets/validate',
    ASSET_BATCH_DELETE: '/assets/batch-delete',
    
    // 统计分析
    STATISTICS: '/statistics',
    DASHBOARD: '/statistics/dashboard',
    BASIC_STATS: '/statistics/basic',
    TREND_DATA: (metric: string) => `/statistics/trend/${metric}`,
    COMPARISON: (metric: string) => `/statistics/comparison/${metric}`,
    
    // Excel导入导出
    EXCEL_IMPORT: '/excel/import',
    EXCEL_EXPORT: '/excel/export',
    EXCEL_TEMPLATE: '/excel/import/template',
    EXCEL_DOWNLOAD: (filename: string) => `/excel/download/${filename}`,
    EXCEL_VALIDATE: '/excel/validate',
    
    // 数据备份
    BACKUP_CREATE: '/backup/create',
    BACKUP_LIST: '/backup/list',
    BACKUP_INFO: (filename: string) => `/backup/info/${filename}`,
    BACKUP_RESTORE: '/backup/restore',
    BACKUP_DELETE: (filename: string) => `/backup/${filename}`,
    BACKUP_CLEANUP: '/backup/cleanup',
    BACKUP_SCHEDULER: '/backup/scheduler/status',
    
    // 历史记录
    HISTORY_DETAIL: (id: string) => `/history/${id}`,
    HISTORY_COMPARE: (id1: string, id2: string) => `/history/compare/${id1}/${id2}`,
    FIELD_HISTORY: (assetId: string, field: string) => `/assets/${assetId}/field-history/${field}`,
    
    // 系统信息
    HEALTH: '/health',
    INFO: '/info',
    VERSION: '/version',
  },
  
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
  ENDPOINTS,
  ERROR_CODES,
  HTTP_STATUS,
  HEADERS,
  ENV,
} = API_CONFIG

// 工具函数
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