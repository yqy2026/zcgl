/**
 * API路径常量管理
 * 统一管理所有API路径，避免硬编码
 *
 * 最佳实践：
 * 1. 集中管理所有API路径
 * 2. 支持多环境配置
 * 3. 类型安全的路径构建
 * 4. 版本控制友好
 */

// ==================== API环境配置 ====================

// 环境类型定义
export type EnvironmentType = 'development' | 'production' | 'test';

// API版本配置
export const API_VERSIONS = {
  V1: 'v1',
  V2: 'v2',
} as const;

// 当前使用的版本
export const CURRENT_API_VERSION = API_VERSIONS.V1; // 版本化API

// 获取当前环境
const getCurrentEnvironment = (): EnvironmentType => {
  if (process.env.NODE_ENV === 'production') {
    return 'production';
  }
  if (process.env.NODE_ENV === 'test') {
    return 'test';
  }
  return 'development';
};

// API基础路径配置
export const API_CONFIG = {
  // 当前环境
  ENVIRONMENT: getCurrentEnvironment(),

  // API版本
  VERSION: API_VERSIONS.V1,

  // 基础路径配置
  BASE_PATH: '',
  BASE_URL: '/api/v1', // 统一使用版本化路径，与后端路由匹配
  PROXY_PREFIX: '/api',

  // 超时配置（毫秒）
  TIMEOUTS: {
    DEFAULT: 30000,
    UPLOAD: 120000,
    DOWNLOAD: 60000,
  },

  // 重试配置
  RETRY: {
    ATTEMPTS: 3,
    DELAY: 1000,
    BACKOFF_FACTOR: 2,
  },
} as const;

// 构建完整API路径的工具函数
export const buildApiPath = (path: string): string => {
  // 统一使用版本化路径，与后端 /api/v1/{module}/{action} 模式匹配
  return `${API_CONFIG.BASE_URL}${path}`;
};

// 构建不带版本的API路径（用于兼容旧API）
export const buildLegacyApiPath = (path: string): string => {
  return `${API_CONFIG.BASE_URL}${path}`;
};

// ==================== API模块路径 ====================

// 认证相关API
export const AUTH_API = {
  // 基础认证 (后端使用 /api/v1/auth/ 前缀)
  LOGIN: '/auth/login',
  LOGOUT: '/auth/logout',
  REGISTER: '/auth/register',
  REFRESH: '/auth/refresh',

  // 用户管理
  PROFILE: '/auth/me',
  CHANGE_PASSWORD: '/auth/change-password',
  RESET_PASSWORD: '/auth/reset-password',

  // 会话管理
  SESSIONS: '/auth/sessions',
  SESSION_INFO: (sessionId: string) => `/auth/sessions/${sessionId}`,

  // 用户列表管理
  USERS: '/auth/users',
  USER_DETAIL: (id: string) => `/auth/users/${id}`,
  USER_CREATE: '/auth/users',
  USER_UPDATE: (id: string) => `/auth/users/${id}`,
  USER_DELETE: (id: string) => `/auth/users/${id}`,
  USER_STATISTICS: '/auth/users/statistics/summary',
  USER_LOCK: (id: string) => `/auth/users/${id}/lock`,
  USER_UNLOCK: (id: string) => `/auth/users/${id}/unlock`,
  USER_RESET_PASSWORD: (id: string) => `/auth/users/${id}/reset-password`,
} as const;

// 资产管理API
export const ASSET_API = {
  // 基础CRUD
  LIST: '/assets',
  DETAIL: (id: string) => `/assets/${id}`,
  CREATE: '/assets',
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

  // 权属方和业态数据
  OWNERSHIP_ENTITIES: '/assets/ownership-entities',
  BUSINESS_CATEGORIES: '/assets/business-categories',
  USAGE_STATUSES: '/assets/usage-statuses',
  PROPERTY_NATURES: '/assets/property-natures',
  OWNERSHIP_STATUSES: '/assets/ownership-statuses',
} as const;

// 组织架构API
export const ORGANIZATION_API = {
  // 组织管理
  LIST: '/organizations',
  DETAIL: (id: string) => `/organizations/${id}`,
  CREATE: '/organizations',
  UPDATE: (id: string) => `/organizations/${id}`,
  DELETE: (id: string) => `/organizations/${id}`,

  // 员工管理
  EMPLOYEES: '/organizations/employees',
  EMPLOYEE_DETAIL: (id: string) => `/organizations/employees/${id}`,

  // 权限管理
  PERMISSIONS: '/organizations/permissions',
  ROLES: '/roles',
} as const;

// 权属方管理API
export const OWNERSHIP_API = {
  LIST: '/ownerships',
  DETAIL: (id: string) => `/ownerships/${id}`,
  CREATE: '/ownerships',
  UPDATE: (id: string) => `/ownerships/${id}`,
  DELETE: (id: string) => `/ownerships/${id}`,
  SEARCH: '/ownerships/search',
} as const;

// 项目管理API
export const PROJECT_API = {
  LIST: '/projects',
  DETAIL: (id: string) => `/projects/${id}`,
  CREATE: '/projects',
  UPDATE: (id: string) => `/projects/${id}`,
  DELETE: (id: string) => `/projects/${id}`,
  SEARCH: '/projects/search',
  DROPDOWN_OPTIONS: '/projects/dropdown-options',
} as const;

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
  PAYMENT_HISTORY: (contractId: string) => `/rental-contracts/contracts/${contractId}/payments`,

  // 合同状态
  ACTIVATE: (id: string) => `/rental-contracts/contracts/${id}/activate`,
  TERMINATE: (id: string) => `/rental-contracts/contracts/${id}/terminate`,
  RENEW: (id: string) => `/rental-contracts/contracts/${id}/renew`,
  CONTRACTS_EXPORT: '/rental-contracts/contracts/export',

  // 租赁统计
  STATISTICS_OVERVIEW: '/rental-contracts/statistics/overview',
  STATISTICS_OWNERSHIP: '/rental-contracts/statistics/ownership',
  STATISTICS_ASSET: '/rental-contracts/statistics/asset',
  STATISTICS_MONTHLY: '/rental-contracts/statistics/monthly',
  STATISTICS_EXPORT: '/rental-contracts/statistics/export',
} as const;

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
} as const;

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
} as const;

// PDF导入API
export const PDF_API = {
  // PDF处理
  UPLOAD: buildApiPath('/pdf-import/upload'),
  PROCESS: buildApiPath('/pdf-import/process'),
  PREVIEW: buildApiPath('/pdf-import/preview'),

  // 系统信息
  INFO: buildApiPath('/pdf-import/info'),
  SESSIONS: buildApiPath('/pdf-import/sessions'),
  SESSION_PROGRESS: (sessionId: string) => buildApiPath(`/pdf-import/progress/${sessionId}`),

  // 批量处理
  BATCH_UPLOAD: buildApiPath('/pdf-import/batch'),
  BATCH_PROCESS: buildApiPath('/pdf-import/batch/process'),

  // 处理状态
  STATUS: (taskId: string) => buildApiPath(`/pdf-import/status/${taskId}`),
  RESULT: (taskId: string) => buildApiPath(`/pdf-import/result/${taskId}`),

  // 质量评估
  QUALITY_ASSESSMENT: (sessionId: string) =>
    buildApiPath(`/pdf-import/quality/assessment/${sessionId}`),
  QUALITY_ANALYZE: buildApiPath('/pdf-import/quality/analyze'),

  // 导入确认
  CONFIRM_IMPORT: buildApiPath('/pdf-import/confirm_import'),
  CANCEL_SESSION: (sessionId: string) => buildApiPath(`/pdf-import/session/${sessionId}`),

  // 历史记录
  HISTORY: buildApiPath('/pdf-import/history'),
  HISTORY_DETAIL: (id: string) => buildApiPath(`/pdf-import/history/${id}`),

  // 性能监控
  PERFORMANCE_REALTIME: buildApiPath('/pdf-import/performance/realtime'),
  PERFORMANCE_REPORT: buildApiPath('/pdf-import/performance/report'),
  PERFORMANCE_HEALTH: buildApiPath('/pdf-import/performance/health'),

  // 测试端点
  TEST_SYSTEM: buildApiPath('/pdf-import/test_system'),
  TEST_DETAILED: buildApiPath('/pdf-import/test_detailed'),
  HEALTH_CHECK: buildApiPath('/pdf-import/health'),
} as const;

// 系统管理API
export const SYSTEM_API = {
  // 系统设置
  SETTINGS: buildApiPath('/system/settings'),
  CONFIG: buildApiPath('/system/config'),

  // 字典管理
  DICTIONARIES: buildApiPath('/system/dictionaries'),
  DICTIONARY_DETAIL: (id: string) => buildApiPath(`/system/dictionaries/${id}`),

  // 用户管理 (引用AUTH_API中的定义)
  USERS: AUTH_API.USERS,
  USER_DETAIL: AUTH_API.USER_DETAIL,
  USER_STATISTICS: AUTH_API.USER_STATISTICS,

  // 日志管理
  LOGS: buildApiPath('/logs'),
  LOG_DETAIL: (id: string) => buildApiPath(`/logs/${id}`),

  // 系统监控
  HEALTH: buildApiPath('/system/health'),
  PERFORMANCE: buildApiPath('/system/performance'),
  STATUS: buildApiPath('/system/status'),

  // 组织管理
  ORGANIZATIONS: buildApiPath('/organizations'),
  ORGANIZATION_DETAIL: (id: string) => buildApiPath(`/organizations/${id}`),

  // 角色管理
  ROLES: buildApiPath('/roles'),
  ROLE_DETAIL: (id: string) => buildApiPath(`/roles/${id}`),

  // 权限管理
  PERMISSIONS: buildApiPath('/permissions'),
  PERMISSION_CHECK: buildApiPath('/permissions/check'),

  // 审计日志
  AUDIT_LOGS: buildApiPath('/logs'),
  AUDIT_LOG_DETAIL: (id: string) => buildApiPath(`/logs/${id}`),
} as const;

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
} as const;

// 测试覆盖率API
export const TEST_COVERAGE_API = {
  REPORT: buildApiPath('/test-coverage/report'),
  TREND: (days: number) => buildApiPath(`/test-coverage/trend?days=${days}`),
  THRESHOLDS: buildApiPath('/test-coverage/thresholds'),
  THRESHOLDS_UPDATE: buildApiPath('/test-coverage/thresholds'),
  QUALITY_GATE: buildApiPath('/test-coverage/quality-gate'),
} as const;

// 监控API
export const MONITORING_API = {
  ROUTE_PERFORMANCE: buildApiPath('/monitoring/route-performance'),
  SYSTEM_HEALTH: buildApiPath('/monitoring/health'), // 迁移到 /api/v1/monitoring/health
  PERFORMANCE_METRICS: buildApiPath('/monitoring/performance'),
} as const;

// 错误报告API
export const ERROR_REPORTING_API = {
  REPORT: buildApiPath('/errors/report'),
  LIST: buildApiPath('/errors'),
  ANALYTICS: buildApiPath('/errors/analytics'),
} as const;

// 通知管理API
export const NOTIFICATION_API = {
  LIST: buildApiPath('/notifications'),
  UNREAD_COUNT: buildApiPath('/notifications/unread-count'),
  MARK_READ: (id: string) => buildApiPath(`/notifications/${id}/read`),
  MARK_ALL_READ: buildApiPath('/notifications/read-all'),
  DELETE: (id: string) => buildApiPath(`/notifications/${id}`),
} as const;

// A/B测试API
export const AB_TESTING_API = {
  EVENTS: buildApiPath('/analytics/abtest-events'),
  CONVERSIONS: buildApiPath('/analytics/abtest-conversions'),
  CONFIGURATIONS: buildApiPath('/analytics/abtest-config'),
} as const;

// ==================== API路径构建工具 ====================

/**
 * 构建完整的API URL
 * @param path API路径
 * @param params 路径参数对象
 * @returns 完整的API URL
 */
export const buildApiUrl = (path: string, params?: Record<string, string | number>): string => {
  let url = `${API_CONFIG.BASE_PATH}${path}`;

  if (params) {
    const searchParams = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => {
      searchParams.append(key, String(value));
    });
    url += `?${searchParams.toString()}`;
  }

  return url;
};

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
  let url = `${API_CONFIG.BASE_PATH}${pathTemplate}`;

  // 替换路径参数
  Object.entries(pathParams).forEach(([key, value]) => {
    url = url.replace(`{${key}}`, String(value));
  });

  // 添加查询参数
  if (queryParams) {
    const searchParams = new URLSearchParams();
    Object.entries(queryParams).forEach(([key, value]) => {
      searchParams.append(key, String(value));
    });
    url += `?${searchParams.toString()}`;
  }

  return url;
};

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
  TEST_COVERAGE: TEST_COVERAGE_API,
  MONITORING: MONITORING_API,
  ERROR_REPORTING: ERROR_REPORTING_API,
  AB_TESTING: AB_TESTING_API,
  NOTIFICATION: NOTIFICATION_API,
} as const;
