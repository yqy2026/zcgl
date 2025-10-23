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
  
  // 端点配置 - 统一命名规范
  ENDPOINTS: {
    // 资产管理
    ASSETS: '/assets',
    ASSET_DETAIL: (id: string) => `/assets/${id}`,
    ASSET_CREATE: '/assets',
    ASSET_UPDATE: (id: string) => `/assets/${id}`,
    ASSET_DELETE: (id: string) => `/assets/${id}`,
    ASSET_BATCH: '/assets/batch',
    ASSET_SEARCH: '/assets/search',
    ASSET_EXPORT: '/assets/export',
    ASSET_IMPORT: '/assets/import',
    ASSET_VALIDATE: '/assets/validate',
    ASSET_STATISTICS: '/assets/statistics',
    ASSET_HISTORY: (id: string) => `/assets/${id}/history`,
    ASSET_FIELD_HISTORY: (assetId: string, field: string) => `/assets/${assetId}/field-history/${field}`,

    // PDF智能导入 - 统一使用连字符
    PDF_IMPORT: {
      BASE: '/pdf-import',
      UPLOAD: '/pdf-import/upload',
      PROCESS: '/pdf-import/process',
      SESSION: (sessionId: string) => `/pdf-import/session/${sessionId}`,
      VALIDATE: '/pdf-import/validate',
      CONFIRM: '/pdf-import/confirm',
      PROGRESS: '/pdf-import/progress',
      CANCEL: '/pdf-import/cancel',
      RETRY: '/pdf-import/retry',
      ANALYSIS: '/pdf-import/analysis',
      CORRECTIONS: '/pdf-import/corrections',
      EXPORT: '/pdf-import/export',
    },

    // 认证管理
    AUTH: {
      LOGIN: '/auth/login',
      LOGOUT: '/auth/logout',
      REFRESH: '/auth/refresh',
      ME: '/auth/me',
      VERIFY: '/auth/verify',
      PASSWORD_CHANGE: '/auth/password/change',
      PASSWORD_RESET: '/auth/password/reset',
      PASSWORD_CONFIRM: '/auth/password/confirm',
    },

    // 用户管理
    USERS: {
      LIST: '/users',
      CREATE: '/users',
      DETAIL: (id: string) => `/users/${id}`,
      UPDATE: (id: string) => `/users/${id}`,
      DELETE: (id: string) => `/users/${id}`,
      LOCK: (id: string) => `/users/${id}/lock`,
      UNLOCK: (id: string) => `/users/${id}/unlock`,
      ROLES: (id: string) => `/users/${id}/roles`,
      PERMISSIONS: (id: string) => `/users/${id}/permissions`,
    },

    // 角色管理
    ROLES: {
      LIST: '/roles',
      CREATE: '/roles',
      DETAIL: (id: string) => `/roles/${id}`,
      UPDATE: (id: string) => `/roles/${id}`,
      DELETE: (id: string) => `/roles/${id}`,
      PERMISSIONS: (id: string) => `/roles/${id}/permissions`,
      USERS: (id: string) => `/roles/${id}/users`,
    },

    // 组织架构
    ORGANIZATIONS: {
      LIST: '/organizations',
      CREATE: '/organizations',
      DETAIL: (id: string) => `/organizations/${id}`,
      UPDATE: (id: string) => `/organizations/${id}`,
      DELETE: (id: string) => `/organizations/${id}`,
      TREE: '/organizations/tree',
      USERS: (id: string) => `/organizations/${id}/users`,
      CHILDREN: (id: string) => `/organizations/${id}/children`,
    },

    // 租赁管理 - 统一使用连字符
    RENTAL: {
      CONTRACTS: {
        LIST: '/rental-contracts',
        CREATE: '/rental-contracts',
        DETAIL: (id: string) => `/rental-contracts/${id}`,
        UPDATE: (id: string) => `/rental-contracts/${id}`,
        DELETE: (id: string) => `/rental-contracts/${id}`,
        TERMINATE: (id: string) => `/rental-contracts/${id}/terminate`,
        RENEW: (id: string) => `/rental-contracts/${id}/renew`,
      },
      LEDGER: {
        LIST: '/rental-ledger',
        CREATE: '/rental-ledger',
        DETAIL: (id: string) => `/rental-ledger/${id}`,
        UPDATE: (id: string) => `/rental-ledger/${id}`,
        DELETE: (id: string) => `/rental-ledger/${id}`,
      },
      STATISTICS: '/rental-statistics',
    },

    // 权属方管理
    OWNERSHIPS: {
      LIST: '/ownerships',
      CREATE: '/ownerships',
      DETAIL: (id: string) => `/ownerships/${id}`,
      UPDATE: (id: string) => `/ownerships/${id}`,
      DELETE: (id: string) => `/ownerships/${id}`,
      ASSETS: (id: string) => `/ownerships/${id}/assets`,
      STATISTICS: '/ownerships/statistics',
    },

    // 项目管理
    PROJECTS: {
      LIST: '/projects',
      CREATE: '/projects',
      DETAIL: (id: string) => `/projects/${id}`,
      UPDATE: (id: string) => `/projects/${id}`,
      DELETE: (id: string) => `/projects/${id}`,
      ASSETS: (id: string) => `/projects/${id}/assets`,
      STATISTICS: (id: string) => `/projects/${id}/statistics`,
    },

    // 数据分析
    ANALYTICS: {
      BASE: '/analytics',
      DASHBOARD: '/analytics/dashboard',
      ASSETS: '/analytics/assets',
      RENTAL: '/analytics/rental',
      FINANCIAL: '/analytics/financial',
      OCCUPANCY: '/analytics/occupancy',
      TRENDS: '/analytics/trends',
      COMPARISON: '/analytics/comparison',
      EXPORT: '/analytics/export',
    },

    // 统计信息
    STATISTICS: {
      BASE: '/statistics',
      DASHBOARD: '/statistics/dashboard',
      BASIC: '/statistics/basic',
      ASSETS: '/statistics/assets',
      RENTAL: '/statistics/rental',
      FINANCIAL: '/statistics/financial',
      TREND: (metric: string) => `/statistics/trend/${metric}`,
      COMPARISON: (metric: string) => `/statistics/comparison/${metric}`,
    },

    // Excel导入导出
    EXCEL: {
      IMPORT: '/excel/import',
      EXPORT: '/excel/export',
      TEMPLATE: '/excel/import/template',
      DOWNLOAD: (filename: string) => `/excel/download/${filename}`,
      VALIDATE: '/excel/validate',
      PREVIEW: '/excel/preview',
    },

    // 数据备份
    BACKUP: {
      CREATE: '/backup/create',
      LIST: '/backup/list',
      INFO: (filename: string) => `/backup/info/${filename}`,
      RESTORE: '/backup/restore',
      DELETE: (filename: string) => `/backup/${filename}`,
      CLEANUP: '/backup/cleanup',
      SCHEDULER: '/backup/scheduler/status',
    },

    // 系统管理
    SYSTEM: {
      BASE: '/system',
      INFO: '/system/info',
      SETTINGS: '/system/settings',
      DICTIONARIES: '/system/dictionaries',
      TEMPLATES: '/system/templates',
      LOGS: '/system/logs',
      MONITORING: '/system/monitoring',
      HEALTH: '/system/health',
    },

    // 历史记录
    HISTORY: {
      DETAIL: (id: string) => `/history/${id}`,
      COMPARE: (id1: string, id2: string) => `/history/compare/${id1}/${id2}`,
      ASSET_HISTORY: (assetId: string) => `/assets/${assetId}/history`,
      REVERT: (id: string) => `/history/revert/${id}`,
    },

    // 自定义字段
    CUSTOM_FIELDS: {
      LIST: '/asset-custom-fields',
      CREATE: '/asset-custom-fields',
      DETAIL: (id: string) => `/asset-custom-fields/${id}`,
      UPDATE: (id: string) => `/asset-custom-fields/${id}`,
      DELETE: (id: string) => `/asset-custom-fields/${id}`,
      BATCH_UPDATE: '/asset-custom-fields/batch-update',
    },

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