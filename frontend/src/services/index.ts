// 统一导出所有服务

// export { apiClient, ApiClient } from './api' // 已弃用，迁移到enhancedApiClient
// export { api } from './api' // 已弃用，迁移到enhancedApiClient

// 现代化API客户端
export { enhancedApiClient, EnhancedApiClient } from './enhancedApiClient'
export { createEnhancedApiClient } from './enhancedApiClient'
export { assetService, AssetService } from './assetService'
export { statisticsService, StatisticsService } from './statisticsService'
export { excelService, ExcelService } from './excelService'
export { backupService, BackupService } from './backupService'

// 导出工具和管理器
export { errorHandler, handleApiError, ApiErrorHandler } from './errorHandler'
export { cacheManager, ApiCacheManager, cached, invalidateCache } from './cacheManager'
export { API_CONFIG, HTTP_STATUS, ERROR_CODES } from './config'

// 导出类型
export type {
  BackupRequest,
  RestoreRequest,
  BackupResponse,
  RestoreResponse,
} from './backupService'

export type {
  ErrorHandlerOptions,
} from './errorHandler'

export type {
  CacheItem,
  CacheOptions,
} from './cacheManager'