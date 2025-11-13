/**
 * API配置文件
 */

// API基础URL配置 - 统一使用版本化路径
export const API_BASE_URL = process.env.VITE_API_BASE_URL || '/api/v1'

// API端点配置 - 使用版本化路径，与后端API标准化保持一致
export const API_ENDPOINTS = {
  // 认证管理
  auth: {
    login: '/auth/login',
    logout: '/auth/logout',
    me: '/auth/me',
    refresh: '/auth/refresh',
  },

  // 资产管理
  assets: '/assets/',
  assetDetail: (id: string) => `/assets/${id}`,

  // 数据分析
  analytics: {
    comprehensive: '/analytics/comprehensive',
    dashboard: '/analytics/dashboard',
    assets: '/analytics/assets',
  },

  // 统计数据
  statistics: {
    basic: '/statistics/basic',
    dashboard: '/statistics/dashboard',
    summary: '/statistics/summary',
  },

  // 组织架构
  organizations: {
    list: '/organizations',
    tree: '/organizations/tree',
  },

  // Excel导入导出
  excel: {
    export: '/excel/export',
    import: '/excel/import',
    template: '/excel/template',
  },

  // 备份恢复
  backup: {
    create: '/backup/create',
    restore: '/backup/restore',
    list: '/backup/list',
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
    public response?: unknown
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