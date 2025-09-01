/**
 * API配置文件
 */

// API基础URL配置
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8001'

// API端点配置
export const API_ENDPOINTS = {
  // 资产管理
  assets: '/api/v1/assets',
  assetDetail: (id: string) => `/api/v1/assets/${id}`,
  
  // 统计数据
  statistics: {
    basic: '/api/v1/statistics/basic',
    dashboard: '/api/v1/statistics/dashboard',
    summary: '/api/v1/statistics/summary',
  },
  
  // Excel导入导出
  excel: {
    export: '/api/v1/excel/export',
    import: '/api/v1/excel/import',
    template: '/api/v1/excel/template',
  },
  
  // 备份恢复
  backup: {
    create: '/api/v1/backup/create',
    restore: '/api/v1/backup/restore',
    list: '/api/v1/backup/list',
  },
} as const

// 创建完整的API URL
export const createApiUrl = (endpoint: string): string => {
  return `${API_BASE_URL}${endpoint}`
}

// API请求配置
export const API_CONFIG = {
  timeout: 30000, // 30秒超时
  headers: {
    'Content-Type': 'application/json',
  },
} as const

// 错误处理
export class ApiError extends Error {
  constructor(
    message: string,
    public status?: number,
    public response?: any
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

// 通用API请求函数
export const apiRequest = async <T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> => {
  const url = createApiUrl(endpoint)
  
  const config: RequestInit = {
    ...API_CONFIG,
    ...options,
    headers: {
      ...API_CONFIG.headers,
      ...options.headers,
    },
  }

  try {
    const response = await fetch(url, config)
    
    if (!response.ok) {
      let errorMessage = `HTTP ${response.status}: ${response.statusText}`
      
      try {
        const errorData = await response.json()
        errorMessage = errorData.message || errorData.detail || errorMessage
      } catch {
        // 如果无法解析错误响应，使用默认错误消息
      }
      
      throw new ApiError(errorMessage, response.status, response)
    }

    const data = await response.json()
    return data
  } catch (error) {
    if (error instanceof ApiError) {
      throw error
    }
    
    // 网络错误或其他错误
    throw new ApiError(
      error instanceof Error ? error.message : '网络请求失败',
      0,
      error
    )
  }
}