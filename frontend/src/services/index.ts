// 统一导出所有服务

export { apiClient, ApiClient } from './api'
export { api } from './api'
export { assetService, AssetService } from './assetService'
export { statisticsService, StatisticsService } from './statisticsService'
export { excelService, ExcelService } from './excelService'
export { backupService, BackupService } from './backupService'

// 导出工具和管理器
export { errorHandler, handleApiError, ApiErrorHandler } from './errorHandler'
export { cacheManager, ApiCacheManager, cached, invalidateCache } from './cacheManager'
export { API_CONFIG, ENDPOINTS, HTTP_STATUS, ERROR_CODES } from './config'

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