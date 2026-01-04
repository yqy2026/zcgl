/**
 * 版本管理和兼容性配置
 * 统一管理版本号、兼容性标志和功能开关
 */

export const VERSION_CONFIG = {
  // 应用版本
  APP_VERSION: '1.0.0',

  // API版本
  API_VERSION: 'v1',

  // 数据库版本（用于迁移）
  DATABASE_VERSION: '1.0.0',

  // 缓存版本（用于清除旧缓存）
  CACHE_VERSION: '1.0.0',

  // 功能开关
  FEATURES: {
    // PDF处理功能
    PDF_PROCESSING: true,
    OCR_SUPPORT: false, // OCR服务可能不可用

    // 高级功能
    ADVANCED_ANALYTICS: true,
    REAL_TIME_UPDATES: true,
    OFFLINE_SUPPORT: false,

    // 开发功能
    DEVELOPMENT_MODE: true,
    DEBUG_MODE: true,
    MOCK_DATA: true,

    // 实验性功能
    BETA_FEATURES: false,
    EXPERIMENTAL_UI: false,
  },

  // 浏览器兼容性
  BROWSER_SUPPORT: {
    CHROME_MIN_VERSION: 90,
    FIREFOX_MIN_VERSION: 88,
    SAFARI_MIN_VERSION: 14,
    EDGE_MIN_VERSION: 90,

    // 必需的API支持
    REQUIRED_APIS: [
      'fetch',
      'Promise',
      'URLSearchParams',
      'IntersectionObserver',
      'ResizeObserver',
      'LocalStorage',
      'SessionStorage',
    ],

    // 可选的API（有降级方案）
    OPTIONAL_APIS: [
      'WebWorkers',
      'ServiceWorker',
      'Notification',
      'Geolocation',
      'Camera',
    ],
  },

  // 依赖版本要求
  DEPENDENCIES: {
    REACT: { MIN: '18.0.0', MAX: '19.0.0' },
    REACT_DOM: { MIN: '18.0.0', MAX: '19.0.0' },
    REACT_ROUTER: { MIN: '6.8.0', MAX: '7.0.0' },
    ANTD: { MIN: '5.0.0', MAX: '6.0.0' },
    TYPESCRIPT: { MIN: '5.0.0', MAX: '6.0.0' },
  },

  // 环境配置
  ENVIRONMENT: {
    DEVELOPMENT: 'development',
    PRODUCTION: 'production',
    TEST: 'test',
  },

  // 兼容性模式
  COMPATIBILITY_MODES: {
    LEGACY: 'legacy',      // 旧版浏览器兼容模式
    MODERN: 'modern',        // 现代浏览器模式
    PROGRESSIVE: 'progressive', // 渐进增强模式
  },

  // 废弃警告
  DEPRECATION_WARNINGS: {
    OLD_API: true,
    LEGACY_FEATURES: true,
    BREAKING_CHANGES: true,
  },
} as const

// 版本比较工具
export const versionCompare = (version1: string, version2: string): number => {
  const v1parts = version1.split('.').map(Number)
  const v2parts = version2.split('.').map(Number)

  for (let i = 0; i < Math.max(v1parts.length, v2parts.length); i++) {
    const v1part = v1parts[i] || 0
    const v2part = v2parts[i] || 0

    if (v1part > v2part) return 1
    if (v1part < v2part) return -1
  }

  return 0
}

// 检查版本兼容性
export const isVersionCompatible = (
  currentVersion: string,
  minVersion: string,
  maxVersion?: string
): boolean => {
  if (versionCompare(currentVersion, minVersion) < 0) {
    return false
  }

  if ((maxVersion !== null && maxVersion !== undefined && maxVersion !== '') && versionCompare(currentVersion, maxVersion) > 0) {
    return false
  }

  return true
}

// 获取当前环境
export const getCurrentEnvironment = (): string => {
  const nodeEnv = process.env.NODE_ENV;
  return (nodeEnv !== null && nodeEnv !== undefined && nodeEnv !== '') ? nodeEnv : VERSION_CONFIG.ENVIRONMENT.DEVELOPMENT
}

// 检查是否为开发环境
export const isDevelopment = (): boolean => {
  return getCurrentEnvironment() === VERSION_CONFIG.ENVIRONMENT.DEVELOPMENT
}

// 检查是否为生产环境
export const isProduction = (): boolean => {
  return getCurrentEnvironment() === VERSION_CONFIG.ENVIRONMENT.PRODUCTION
}

// 功能开关检查
export const isFeatureEnabled = (feature: keyof typeof VERSION_CONFIG.FEATURES): boolean => {
  return VERSION_CONFIG.FEATURES[feature]
}

// 条件性功能渲染
export const renderIf = (
  condition: boolean,
  component: React.ReactElement
): React.ReactElement | null => {
  return condition ? component : null
}

// 调试日志
export const debugLog = (...args: any[]): void => {
  if (VERSION_CONFIG.FEATURES.DEBUG_MODE) {
    // eslint-disable-next-line no-console
    console.log('[DEBUG]', ...args)
  }
}

// 错误日志（始终显示）
export const errorLog = (...args: any[]): void => {
  // eslint-disable-next-line no-console
  console.error('[ERROR]', ...args)
}

// 警告日志
export const warnLog = (...args: any[]): void => {
  if (VERSION_CONFIG.FEATURES.DEBUG_MODE || VERSION_CONFIG.DEPRECATION_WARNINGS.BREAKING_CHANGES) {
    // eslint-disable-next-line no-console
    console.warn('[WARN]', ...args)
  }
}

export default VERSION_CONFIG