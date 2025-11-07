/**
 * API路径常量管理
 * 统一管理所有API路径，避免硬编码
 */

// ==================== API基础路径配置 ====================

// API版本和基础路径
export const API_CONFIG = {
  // 开发环境通过Vite代理转发到后端
  BASE_PATH: '/v1',
  // 基础URL - 统一路径配置
  BASE_URL: process.env.NODE_ENV === 'development'
    ? '/api/v1'
    : '/api/v1',
  // 完整的基础URL（用于直接请求）
  FULL_BASE_URL: process.env.NODE_ENV === 'development'
    ? '/api/v1'
    : '/api/v1',
  // 代理路径前缀（Vite配置）
  PROXY_PREFIX: '/api',
} as const

// ==================== API模块路径 ====================

// 认证相关API
export const AUTH_API = {
  // 基础认证
  LOGIN: '/auth/login',
  LOGOUT: '/auth/logout',
  REGISTER: '/auth/register',
  REFRESH: '/auth/refresh',

  // 用户管理
  PROFILE: '/auth/profile',
  CHANGE_PASSWORD: '/auth/change-password',
  RESET_PASSWORD: '/auth/reset-password',

  // 会话管理
  SESSIONS: '/auth/sessions',
  SESSION_INFO: (sessionId: string) => `/auth/sessions/${sessionId}`,
} as const

// 资产管理API
export const ASSET_API = {
  // 基础CRUD
  LIST: '/assets/',
  DETAIL: (id: string) => `/assets/${id}`,
  CREATE: '/assets/',
  UPDATE: (id: string) => `/assets/${id}`,
  DELETE: (id: string) => `/assets/${id}`,

  // 批量操作
  BATCH_CREATE: '/assets/batch',
  BATCH_UPDATE: '/assets/batch',
  BATCH_DELETE: '/assets/batch',

  // 搜索和过滤
  SEARCH: '/assets/search',
  FILTER: '/assets/filter',

  // 统计数据
  STATISTICS: '/assets/statistics',
  SUMMARY: '/assets/summary',

  // 文件操作
  UPLOAD_IMAGE: '/assets/upload/image',
  UPLOAD_DOCUMENT: '/assets/upload/document',
  EXPORT: '/assets/export',
} as const

// 组织架构API
export const ORGANIZATION_API = {
  // 组织管理
  LIST: '/organizations/',
  DETAIL: (id: string) => `/organizations/${id}`,
  CREATE: '/organizations/',
  UPDATE: (id: string) => `/organizations/${id}`,
  DELETE: (id: string) => `/organizations/${id}`,

  // 员工管理
  EMPLOYEES: '/organizations/employees',
  EMPLOYEE_DETAIL: (id: string) => `/organizations/employees/${id}`,

  // 权限管理
  PERMISSIONS: '/organizations/permissions',
  ROLES: '/organizations/roles',
} as const

// 权属方管理API
export const OWNERSHIP_API = {
  LIST: '/ownerships/',
  DETAIL: (id: string) => `/ownerships/${id}`,
  CREATE: '/ownerships/',
  UPDATE: (id: string) => `/ownerships/${id}`,
  DELETE: (id: string) => `/ownerships/${id}`,
  SEARCH: '/ownerships/search',
} as const

// 项目管理API
export const PROJECT_API = {
  LIST: '/projects/',
  DETAIL: (id: string) => `/projects/${id}`,
  CREATE: '/projects/',
  UPDATE: (id: string) => `/projects/${id}`,
  DELETE: (id: string) => `/projects/${id}`,
  SEARCH: '/projects/search',
} as const

// 租赁合同API
export const RENT_CONTRACT_API = {
  LIST: '/rental-contracts/contracts',
  DETAIL: (id: string) => `/rental-contracts/contracts/${id}`,
  CREATE: '/rental-contracts/contracts',
  UPDATE: (id: string) => `/rental-contracts/contracts/${id}`,
  DELETE: (id: string) => `/rental-contracts/contracts/${id}`,

  // 租金条款
  TERMS: (id: string) => `/rental-contracts/contracts/${id}/terms`,
  ADD_TERM: (id: string) => `/rental-contracts/contracts/${id}/terms`,

  // 租金台账
  LEDGER: (id: string) => `/rental-contracts/contracts/${id}/ledger`,
  LEDGER_LIST: '/rental-contracts/ledger',
  LEDGER_DETAIL: (id: string) => `/rental-contracts/ledger/${id}`,
  LEDGER_UPDATE: (id: string) => `/rental-contracts/ledger/${id}`,
  LEDGER_BATCH_UPDATE: '/rental-contracts/ledger/batch',
  LEDGER_GENERATE: '/rental-contracts/ledger/generate',
  LEDGER_EXPORT: '/rental-contracts/ledger/export',

  // 租金管理
  PAYMENTS: '/rental-contracts/payments',
  PAYMENT_HISTORY: (contractId: string) => `/rental-contracts/${contractId}/payments`,

  // 合同状态
  ACTIVATE: (id: string) => `/rental-contracts/${id}/activate`,
  TERMINATE: (id: string) => `/rental-contracts/${id}/terminate`,
  RENEW: (id: string) => `/rental-contracts/${id}/renew`,
  CONTRACTS_EXPORT: '/rental-contracts/export',

  // 租赁统计
  STATISTICS_OVERVIEW: '/rental-contracts/statistics/overview',
  STATISTICS_OWNERSHIP: '/rental-contracts/statistics/ownership',
  STATISTICS_ASSET: '/rental-contracts/statistics/asset',
  STATISTICS_MONTHLY: '/rental-contracts/statistics/monthly',
  STATISTICS_EXPORT: '/rental-contracts/statistics/export',
} as const

// 数据统计API
export const STATISTICS_API = {
  // 基础统计
  OVERVIEW: '/statistics/overview',
  ASSET_SUMMARY: '/statistics/asset-summary',
  FINANCIAL_SUMMARY: '/statistics/financial-summary',

  // 图表数据
  ASSET_TYPE_CHART: '/statistics/charts/asset-types',
  OCCUPANCY_TREND: '/statistics/charts/occupancy-trend',
  REVENUE_TREND: '/statistics/charts/revenue-trend',

  // 报表
  MONTHLY_REPORT: '/statistics/reports/monthly',
  ANNUAL_REPORT: '/statistics/reports/annual',
  CUSTOM_REPORT: '/statistics/reports/custom',
} as const

// Excel导入导出API
export const EXCEL_API = {
  // 导入操作
  IMPORT_ASSETS: '/excel/import/assets',
  IMPORT_CONTRACTS: '/excel/import/contracts',
  IMPORT_OWNERSHIPS: '/excel/import/ownerships',

  // 导出操作
  EXPORT_ASSETS: '/excel/export/assets',
  EXPORT_CONTRACTS: '/excel/export/contracts',
  EXPORT_TEMPLATES: '/excel/export/templates',

  // 模板下载
  ASSET_TEMPLATE: '/excel/templates/asset',
  CONTRACT_TEMPLATE: '/excel/templates/contract',
  OWNERSHIP_TEMPLATE: '/excel/templates/ownership',
} as const

// PDF导入API
export const PDF_API = {
  // PDF处理
  UPLOAD: '/pdf-import/upload',
  PROCESS: '/pdf-import/process',
  PREVIEW: '/pdf-import/preview',

  // 批量处理
  BATCH_UPLOAD: '/pdf-import/batch',
  BATCH_PROCESS: '/pdf-import/batch/process',

  // 处理状态
  STATUS: (taskId: string) => `/pdf-import/status/${taskId}`,
  RESULT: (taskId: string) => `/pdf-import/result/${taskId}`,

  // 历史记录
  HISTORY: '/pdf-import/history',
  HISTORY_DETAIL: (id: string) => `/pdf-import/history/${id}`,
} as const

// 系统管理API
export const SYSTEM_API = {
  // 系统设置
  SETTINGS: '/system/settings',
  CONFIG: '/system/config',

  // 字典管理
  DICTIONARIES: '/system/dictionaries',
  DICTIONARY_DETAIL: (id: string) => `/system/dictionaries/${id}`,

  // 用户管理
  USERS: '/system/users',
  USER_DETAIL: (id: string) => `/system/users/${id}`,

  // 日志管理
  LOGS: '/system/logs',
  LOG_DETAIL: (id: string) => `/system/logs/${id}`,

  // 系统监控
  HEALTH: '/system/health',
  PERFORMANCE: '/system/performance',
  STATUS: '/system/status',
} as const

// 数据备份API
export const BACKUP_API = {
  // 备份操作
  CREATE: '/backup/create',
  LIST: '/backup/list',
  DETAIL: (id: string) => `/backup/${id}`,
  DELETE: (id: string) => `/backup/${id}`,

  // 恢复操作
  RESTORE: '/backup/restore',
  RESTORE_STATUS: (taskId: string) => `/backup/restore/status/${taskId}`,

  // 备份配置
  CONFIG: '/backup/config',
  SCHEDULE: '/backup/schedule',
} as const

// ==================== API路径构建工具 ====================

/**
 * 构建完整的API URL
 * @param path API路径
 * @param params 路径参数对象
 * @returns 完整的API URL
 */
export const buildApiUrl = (
  path: string,
  params?: Record<string, string | number>
): string => {
  let url = `${API_CONFIG.BASE_PATH}${path}`

  if (params) {
    const searchParams = new URLSearchParams()
    Object.entries(params).forEach(([key, value]) => {
      searchParams.append(key, String(value))
    })
    url += `?${searchParams.toString()}`
  }

  return url
}

/**
 * 构建带路径参数的API URL
 * @param pathTemplate 路径模板，如 '/users/{id}'
 * @param pathParams 路径参数
 * @param queryParams 查询参数
 * @returns 完整的API URL
 */
export const buildApiUrlWithPathParams = (
  pathTemplate: string,
  pathParams: Record<string, string | number>,
  queryParams?: Record<string, string | number>
): string => {
  let url = `${API_CONFIG.BASE_PATH}${pathTemplate}`

  // 替换路径参数
  Object.entries(pathParams).forEach(([key, value]) => {
    url = url.replace(`{${key}}`, String(value))
  })

  // 添加查询参数
  if (queryParams) {
    const searchParams = new URLSearchParams()
    Object.entries(queryParams).forEach(([key, value]) => {
      searchParams.append(key, String(value))
    })
    url += `?${searchParams.toString()}`
  }

  return url
}

// ==================== API路径常量导出 ====================

export const API_ENDPOINTS = {
  AUTH: AUTH_API,
  ASSET: ASSET_API,
  ORGANIZATION: ORGANIZATION_API,
  OWNERSHIP: OWNERSHIP_API,
  PROJECT: PROJECT_API,
  RENT_CONTRACT: RENT_CONTRACT_API,
  STATISTICS: STATISTICS_API,
  EXCEL: EXCEL_API,
  PDF: PDF_API,
  SYSTEM: SYSTEM_API,
  BACKUP: BACKUP_API,
} as const
