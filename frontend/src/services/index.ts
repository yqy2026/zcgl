// 统一导出所有服务

// export { apiClient, ApiClient } from './api' // 已弃用，迁移到 api/client
// export { api } from './api' // 已弃用，迁移到 api/client

// 现代化API客户端 - Re-exported from new api/ location
export { apiClient, ApiClient, createApiClient } from '../api/client';
export { assetService, AssetService } from './assetService';
export { statisticsService, StatisticsService } from './statisticsService';
export { excelService, ExcelService } from './excelService';
export { backupService, BackupService } from './backupService';

// 导出工具和管理器
export {
  errorHandler,
  handleApiError,
  ApiErrorHandler,
  withErrorHandling,
  createErrorHandler,
} from './errorHandler';
export { cacheManager, ApiCacheManager, cached, invalidateCache } from './cacheManager';
// API_CONFIG now exported from api/ location
export { API_CONFIG, HTTP_STATUS, ERROR_CODES } from '../api/config';

// 导出类型
export type {
  BackupRequest,
  RestoreRequest,
  BackupResponse,
  RestoreResponse,
} from './backupService';

export type { ErrorHandlerOptions } from './errorHandler';

export type { CacheItem, CacheOptions } from './cacheManager';
