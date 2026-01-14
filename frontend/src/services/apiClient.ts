/**
 * 统一的API客户端
 * 提供标准化的API调用方法，包含错误处理、重试机制等
 */

import axios, { AxiosInstance, AxiosRequestConfig, AxiosResponse, AxiosError } from 'axios'
import { API_CONFIG } from '../constants/api'

// API响应类型定义
export interface ApiResponse<T = unknown> {
  success: boolean
  data: T
  message?: string
  code?: string
  timestamp?: string
}

export interface PaginatedResponse<T = unknown> {
  success: boolean
  data: T[]
  pagination: {
    page: number
    pageSize: number
    total: number
    totalPages: number
  }
  message?: string
}

export interface ApiError {
  success: false
  error: {
    code: string
    message: string
    details?: unknown
    timestamp?: string
  }
}

/**
 * 统一的API客户端类
 */
export class ApiClient {
  private instance: AxiosInstance

  constructor() {
    this.instance = axios.create({
      baseURL: API_CONFIG.BASE_URL,
      timeout: API_CONFIG.TIMEOUTS.DEFAULT,
      headers: {
        'Content-Type': 'application/json',
      },
    })

    this.setupInterceptors()
  }

  /**
   * 设置请求和响应拦截器
   */
  private setupInterceptors(): void {
    // 请求拦截器
    this.instance.interceptors.request.use(
      (config) => {
        // 添加认证token
        const token = localStorage.getItem('token')
        if (token != null) {
          config.headers.Authorization = `Bearer ${token}`
        }

        // 开发模式特殊处理
        if (API_CONFIG.ENVIRONMENT === 'development') {
          const mockToken = localStorage.getItem('mock_token')
          if (mockToken != null) {
            config.headers['X-Development-Auth'] = 'mock-token'
          }
        }

        // 添加请求ID用于追踪
        config.headers['X-Request-ID'] = this.generateRequestId()

        return config
      },
      (error) => {
        return Promise.reject(error)
      }
    )

    // 响应拦截器
    this.instance.interceptors.response.use(
      (response: AxiosResponse) => {
        return response
      },
      async (error) => {
        const originalRequest = error.config as any
        const errorResp = error as { response?: { status?: number } }

        // 处理401未授权错误
        if (errorResp.response?.status === 401 && !((originalRequest != null) && (originalRequest._retry === true))) {
          if (originalRequest != null) {
            originalRequest._retry = true
          }

          // 开发模式处理
          if (API_CONFIG.ENVIRONMENT === 'development') {
            console.warn('开发模式：收到401响应，但使用mock token，跳过重定向')
            return Promise.reject(error)
          }

          // 尝试刷新token
          try {
            await this.refreshToken()
            // 重新发送原请求
            return this.instance(originalRequest)
          } catch (refreshError) {
            // 刷新失败，重定向到登录页
            this.handleAuthFailure()
            return Promise.reject(refreshError)
          }
        }

        return Promise.reject(error)
      }
    )
  }

  /**
   * 生成请求ID
   */
  private generateRequestId(): string {
    return `req_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
  }

  /**
   * 刷新token
   */
  private async refreshToken(): Promise<void> {
    const refreshToken = localStorage.getItem('refresh_token')
    if (refreshToken == null) {
      throw new Error('No refresh token available')
    }

    try {
      const response = await axios.post('/api/auth/refresh', {
        refresh_token: refreshToken,
      })

      const { access_token } = response.data
      localStorage.setItem('token', access_token)
    } catch {
      throw new Error('Token refresh failed')
    }
  }

  /**
   * 处理认证失败
   */
  private handleAuthFailure(): void {
    localStorage.removeItem('token')
    localStorage.removeItem('refresh_token')
    window.location.href = '/login'
  }

  /**
   * 通用GET请求
   */
  async get<T = unknown>(
    url: string,
    config?: AxiosRequestConfig
  ): Promise<ApiResponse<T>> {
    const response = await this.instance.get<ApiResponse<T>>(url, config)
    return response.data
  }

  /**
   * 通用POST请求
   */
  async post<T = unknown>(
    url: string,
    data?: unknown,
    config?: AxiosRequestConfig
  ): Promise<ApiResponse<T>> {
    const response = await this.instance.post<ApiResponse<T>>(url, data, config)
    return response.data
  }

  /**
   * 通用PUT请求
   */
  async put<T = unknown>(
    url: string,
    data?: unknown,
    config?: AxiosRequestConfig
  ): Promise<ApiResponse<T>> {
    const response = await this.instance.put<ApiResponse<T>>(url, data, config)
    return response.data
  }

  /**
   * 通用DELETE请求
   */
  async delete<T = unknown>(
    url: string,
    config?: AxiosRequestConfig
  ): Promise<ApiResponse<T>> {
    const response = await this.instance.delete<ApiResponse<T>>(url, config)
    return response.data
  }

  /**
   * 文件上传
   */
  async upload<T = unknown>(
    url: string,
    formData: FormData,
    onProgress?: (progress: number) => void,
    config?: AxiosRequestConfig
  ): Promise<ApiResponse<T>> {
    const response = await this.instance.post<ApiResponse<T>>(url, formData, {
      ...config,
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      timeout: API_CONFIG.TIMEOUTS.UPLOAD,
      onUploadProgress: (progressEvent) => {
        if (onProgress != null && progressEvent.total != null) {
          const progress = (progressEvent.loaded / progressEvent.total) * 100
          onProgress(Math.round(progress))
        }
      },
    })
    return response.data
  }

  /**
   * 文件下载
   */
  async download(
    url: string,
    filename?: string,
    config?: AxiosRequestConfig
  ): Promise<void> {
    const response = await this.instance.get(url, {
      ...config,
      responseType: 'blob',
      timeout: API_CONFIG.TIMEOUTS.DOWNLOAD,
    })

    // 创建下载链接
    const blob = new Blob([response.data])
    const downloadUrl = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = downloadUrl
    link.download = filename ?? 'download'
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(downloadUrl)
  }

  /**
   * 带重试的请求方法
   */
  async requestWithRetry<T = unknown>(
    requestFn: () => Promise<ApiResponse<T>>,
    maxRetries: number = API_CONFIG.RETRY.ATTEMPTS
  ): Promise<ApiResponse<T>> {
    let lastError: Error | AxiosError | unknown

    for (let attempt = 1; attempt <= maxRetries; attempt++) {
      try {
        return await requestFn()
      } catch (error) {
        lastError = error

        // 如果是最后一次尝试，直接抛出错误
        if (attempt === maxRetries) {
          break
        }

        // 计算延迟时间
        const delay = API_CONFIG.RETRY.DELAY * Math.pow(API_CONFIG.RETRY.BACKOFF_FACTOR, attempt - 1)
        await new Promise(resolve => setTimeout(resolve, delay))
      }
    }

    throw lastError
  }
}

// 创建单例实例
export const apiClient = new ApiClient()

// 便捷的API调用方法
export const api = {
  get: <T = unknown>(url: string, config?: AxiosRequestConfig) => apiClient.get<T>(url, config),
  post: <T = unknown>(url: string, data?: unknown, config?: AxiosRequestConfig) => apiClient.post<T>(url, data, config),
  put: <T = unknown>(url: string, data?: unknown, config?: AxiosRequestConfig) => apiClient.put<T>(url, data, config),
  delete: <T = unknown>(url: string, config?: AxiosRequestConfig) => apiClient.delete<T>(url, config),
  upload: <T = unknown>(
    url: string,
    formData: FormData,
    onProgress?: (progress: number) => void,
    config?: AxiosRequestConfig
  ) => apiClient.upload<T>(url, formData, onProgress, config),
  download: (url: string, filename?: string, config?: AxiosRequestConfig) =>
    apiClient.download(url, filename, config),
  withRetry: <T = unknown>(requestFn: () => Promise<ApiResponse<T>>, maxRetries?: number) =>
    apiClient.requestWithRetry<T>(requestFn, maxRetries),
}

export default apiClient
