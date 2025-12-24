/**
 * @deprecated 此文件已废弃，配置已迁移至 config/api.ts
 *
 * 迁移指南:
 * - 旧: import { API_CONFIG, ERROR_CODES } from '@/services/config'
 * - 新: import { API_CONFIG, ERROR_CODES } from '@/config/api'
 *
 * 所有配置现在统一在 config/api.ts 中管理
 * 最后更新: 2025-12-24
 */

// 重新导出所有内容以保持向后兼容
export {
  API_CONFIG,
  API_ENDPOINTS,
  API_BASE_URL,
  ERROR_CODES,
  HTTP_STATUS,
  HEADERS,
  ENV,
  createApiUrl,
  getApiUrl,
  generateRequestId,
  delay,
  isProduction,
  isDevelopment,
  isValidFileType,
  isValidFileSize,
  formatFileSize,
  ApiError,
  apiRequest,
  BASE_URL,
  TIMEOUT,
  RETRY,
  CACHE,
  UPLOAD,
  PAGINATION,
} from '../config/api';
