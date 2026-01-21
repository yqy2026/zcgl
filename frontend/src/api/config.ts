/**
 * API配置文件 - 统一配置中心
 *
 * 合并说明:
 * - 原 services/config.ts 的内容已合并至此
 * - 保留原有的 apiRequest 函数
 * - 新增完整的错误代码、HTTP状态码、工具函数等
 * @lastModified 2025-12-24
 */

// ==================== 环境配置 ====================

// 获取环境变量的辅助函数，兼容Vite环境
const getEnvVar = (key: string, defaultValue: string): string => {
  const envKey = key.replace('VITE_', '');
  const rawValue = import.meta.env[key] as unknown;
  const rawViteValue = import.meta.env[`VITE_${envKey}`] as unknown;

  if (typeof rawValue === 'string' && rawValue !== '') return rawValue;
  if (typeof rawViteValue === 'string' && rawViteValue !== '') return rawViteValue;
  return defaultValue;
};

// API基础URL配置 - 统一使用版本化路径
export const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL as string) || '/api/v1';

// ==================== API配置 ====================

export const API_CONFIG = {
  // 基础配置
  BASE_URL: API_BASE_URL,
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
    LONG_TTL: 30 * 60 * 1000, // 30分钟
    SHORT_TTL: 1 * 60 * 1000, // 1分钟
  },

  // 文件上传配置
  UPLOAD: {
    MAX_SIZE: 50 * 1024 * 1024, // 50MB
    CHUNK_SIZE: 1024 * 1024, // 1MB
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

  // 请求头配置
  headers: {
    'Content-Type': 'application/json',
  },
} as const;

// ==================== 错误代码映射 ====================

export const ERROR_CODES = {
  NETWORK_ERROR: 'NETWORK_ERROR',
  TIMEOUT_ERROR: 'TIMEOUT_ERROR',
  VALIDATION_ERROR: 'VALIDATION_ERROR',
  PERMISSION_ERROR: 'PERMISSION_ERROR',
  NOT_FOUND_ERROR: 'NOT_FOUND_ERROR',
  SERVER_ERROR: 'SERVER_ERROR',
} as const;

// ==================== HTTP状态码映射 ====================

export const HTTP_STATUS = {
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
} as const;

// ==================== 请求头常量 ====================

export const HEADERS = {
  CONTENT_TYPE: 'Content-Type',
  AUTHORIZATION: 'Authorization',
  REQUEST_ID: 'X-Request-ID',
  USER_AGENT: 'X-User-Agent',
  CLIENT_VERSION: 'X-Client-Version',
} as const;

// ==================== 环境配置 ====================

export const ENV = {
  DEVELOPMENT: import.meta.env.DEV,
  PRODUCTION: import.meta.env.PROD,
  API_URL: import.meta.env.VITE_API_BASE_URL,
  APP_VERSION: import.meta.env.VITE_APP_VERSION || '1.0.0',
} as const;

// ==================== 工具函数 ====================

/**
 * 创建完整的API URL
 */
export const createApiUrl = (endpoint: string): string => {
  return `${API_BASE_URL}${endpoint}`;
};

/**
 * 获取完整的API URL (别名，兼容旧代码)
 */
export const getApiUrl = (endpoint: string) => {
  return `${API_BASE_URL}${endpoint}`;
};

/**
 * 生成请求ID
 */
export const generateRequestId = (): string => {
  return `req_${Date.now()}_${Math.random().toString(36).slice(2, 11)}`;
};

/**
 * 延迟函数
 */
export const delay = (ms: number): Promise<void> => {
  return new Promise(resolve => setTimeout(resolve, ms));
};

/**
 * 检查是否为生产环境
 */
export const isProduction = () => ENV.PRODUCTION;

/**
 * 检查是否为开发环境
 */
export const isDevelopment = () => ENV.DEVELOPMENT;

/**
 * 验证文件类型
 */
export const isValidFileType = (file: File) => {
  return API_CONFIG.UPLOAD.ALLOWED_TYPES.includes(
    file.type as (typeof API_CONFIG.UPLOAD.ALLOWED_TYPES)[number]
  );
};

/**
 * 验证文件大小
 */
export const isValidFileSize = (file: File) => {
  return file.size <= API_CONFIG.UPLOAD.MAX_SIZE;
};

/**
 * 格式化文件大小
 */
export const formatFileSize = (bytes: number): string => {
  if (bytes === 0) return '0 B';

  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));

  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(2))} ${sizes[i]}`;
};

// ==================== 错误处理 ====================

/**
 * API错误类
 */
export class ApiError extends Error {
  constructor(
    message: string,
    public status?: number,
    public response?: unknown
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

// ==================== 通用API请求函数 ====================

/**
 * 通用API请求函数
 */
export const apiRequest = async <T>(endpoint: string, options: RequestInit = {}): Promise<T> => {
  const url = createApiUrl(endpoint);

  // 创建AbortController实现超时
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), API_CONFIG.TIMEOUT);

  const config: RequestInit = {
    ...options,
    headers: {
      ...API_CONFIG.headers,
      ...options.headers,
    },
    signal: controller.signal,
  };

  try {
    const response = await fetch(url, config);
    clearTimeout(timeoutId);

    if (!response.ok) {
      let errorMessage = `HTTP ${response.status}: ${response.statusText}`;

      try {
        const errorData = (await response.json()) as unknown as Record<string, unknown>;

        const rawMessage = errorData.message as unknown;
        const rawDetail = errorData.detail as unknown;

        if (typeof rawMessage === 'string' && rawMessage !== '') {
          errorMessage = rawMessage;
        } else if (typeof rawDetail === 'string' && rawDetail !== '') {
          errorMessage = rawDetail;
        }
      } catch {
        // 如果无法解析错误响应，使用默认错误消息
      }

      throw new ApiError(errorMessage, response.status, response);
    }

    const data = (await response.json()) as unknown as T;
    return data;
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }

    // 网络错误或其他错误
    throw new ApiError(error instanceof Error ? error.message : '网络请求失败', 0, error);
  }
};

// ==================== 导出便捷访问 ====================

export const { BASE_URL, TIMEOUT, RETRY, CACHE, UPLOAD, PAGINATION } = API_CONFIG;
