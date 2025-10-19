import axios, { AxiosInstance, AxiosRequestConfig, AxiosResponse } from 'axios'
import type { ApiResponse, ErrorResponse } from '@/types/api'

// 环境配置 - 开发环境使用相对路径利用Vite代理，生产环境使用完整URL
const API_BASE_URL = import.meta.env.DEV
  ? '/api/v1'  // 开发环境使用相对路径，通过Vite代理转发
  : (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8001/api/v1')  // 生产环境使用完整URL
const API_TIMEOUT = import.meta.env.VITE_API_TIMEOUT || 30000

// 请求重试配置
const RETRY_CONFIG = {
  retries: 3,
  retryDelay: 1000,
  retryCondition: (error: any) => {
    return error.code === 'NETWORK_ERROR' || 
           (error.response && error.response.status >= 500)
  },
}

// 创建axios实例
const createApiInstance = (): AxiosInstance => {
  const instance = axios.create({
    baseURL: API_BASE_URL,
    timeout: 600000, // 10分钟超时，给导入操作足够时间
    // 不设置默认的Content-Type，让axios根据请求数据自动设置
  })

  // 请求拦截器
  instance.interceptors.request.use(
    (config) => {
      // 对于文件上传请求，不添加认证token和请求ID，避免干扰multipart/form-data
      const isFileUpload = config.data instanceof FormData

      if (!isFileUpload) {
        // 添加认证token
        const token = localStorage.getItem('auth_token')
        if (token) {
          config.headers.Authorization = `Bearer ${token}`
        }

        // 添加请求ID用于追踪
        config.headers['X-Request-ID'] = generateRequestId()
      }

      console.log(`🚀 API Request: ${config.method?.toUpperCase()} ${config.url}`)
      return config
    },
    (error) => {
      console.error('❌ Request Error:', error)
      return Promise.reject(error)
    }
  )

  // 响应拦截器
  instance.interceptors.response.use(
    (response: AxiosResponse) => {
      const requestId = response.config.headers['X-Request-ID']
      console.log(`✅ API Response [${requestId}]: ${response.config.method?.toUpperCase()} ${response.config.url}`, response.data)
      
      // 处理业务逻辑错误
      if (response.data && response.data.success === false) {
        console.warn('⚠️ Business Logic Error:', response.data.message)
      }
      
      return response
    },
    async (error) => {
      const requestId = error.config?.headers['X-Request-ID']
      console.error(`❌ Response Error [${requestId}]:`, error)
      
      // 处理网络错误
      if (!error.response) {
        // 尝试重试网络错误
        if (error.config && !error.config.__isRetryRequest) {
          try {
            error.config.__isRetryRequest = true
            return await retryRequest(instance, error.config)
          } catch (retryError) {
            // 重试失败，返回网络错误
          }
        }

        console.warn('网络连接失败，可能后端服务未启动或网络问题')
        return Promise.reject({
          error: 'Network Error',
          message: '网络连接失败，请检查网络设置',
          timestamp: new Date().toISOString(),
        } as ErrorResponse)
      }

      // 处理认证错误
      const { status } = error.response
      handleAuthError(status)

      // 处理HTTP错误
      const { data } = error.response
      const errorResponse: ErrorResponse = {
        error: data?.error || `HTTP ${status}`,
        message: data?.message || getDefaultErrorMessage(status),
        details: data?.details,
        timestamp: data?.timestamp || new Date().toISOString(),
      }

      return Promise.reject(errorResponse)
    }
  )

  return instance
}

// 生成请求ID
const generateRequestId = (): string => {
  return `req_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
}

// 请求重试函数
const retryRequest = async (
  instance: AxiosInstance,
  config: AxiosRequestConfig,
  retryCount = 0
): Promise<AxiosResponse> => {
  try {
    return await instance(config)
  } catch (error: any) {
    if (retryCount < RETRY_CONFIG.retries && RETRY_CONFIG.retryCondition(error)) {
      console.log(`🔄 Retrying request (${retryCount + 1}/${RETRY_CONFIG.retries}): ${config.url}`)
      
      // 等待重试延迟
      await new Promise(resolve => 
        setTimeout(resolve, RETRY_CONFIG.retryDelay * Math.pow(2, retryCount))
      )
      
      return retryRequest(instance, config, retryCount + 1)
    }
    throw error
  }
}

// 获取默认错误消息
const getDefaultErrorMessage = (status: number): string => {
  switch (status) {
    case 400:
      return '请求参数错误'
    case 401:
      return '未授权访问'
    case 403:
      return '禁止访问'
    case 404:
      return '资源不存在'
    case 409:
      return '资源冲突'
    case 422:
      return '请求参数验证失败'
    case 500:
      return '服务器内部错误'
    case 502:
      return '网关错误'
    case 503:
      return '服务不可用'
    default:
      return `请求失败 (${status})`
  }
}

// 处理认证错误
const handleAuthError = (status: number) => {
  if (status === 401) {
    // 清除本地存储的认证信息
    localStorage.removeItem('auth_token')
    localStorage.removeItem('user_info')

    // 临时注释掉重定向到登录页面的逻辑
    // if (window.location.pathname !== '/login') {
    //   window.location.href = '/login'
    // }

    console.warn('认证错误已发生，但重定向被临时禁用用于调试')
  }
}

// 创建API实例
export const api = createApiInstance()

// API请求封装类
export class ApiClient {
  private instance: AxiosInstance

  constructor(instance: AxiosInstance) {
    this.instance = instance
  }

  // GET请求
  async get<T = any>(
    url: string,
    config?: AxiosRequestConfig
  ): Promise<ApiResponse<T>> {
    const response = await this.instance.get<ApiResponse<T>>(url, config)
    return response.data
  }

  // POST请求
  async post<T = any>(
    url: string,
    data?: any,
    config?: AxiosRequestConfig
  ): Promise<ApiResponse<T>> {
    const response = await this.instance.post<ApiResponse<T>>(url, data, config)
    return response.data
  }

  // PUT请求
  async put<T = any>(
    url: string,
    data?: any,
    config?: AxiosRequestConfig
  ): Promise<ApiResponse<T>> {
    const response = await this.instance.put<ApiResponse<T>>(url, data, config)
    return response.data
  }

  // DELETE请求
  async delete<T = any>(
    url: string,
    config?: AxiosRequestConfig
  ): Promise<ApiResponse<T>> {
    const response = await this.instance.delete<ApiResponse<T>>(url, config)
    return response.data
  }

  // 文件上传
  async upload<T = any>(
    url: string,
    file: File,
    onProgress?: (progress: number) => void,
    additionalData?: Record<string, any>
  ): Promise<ApiResponse<T>> {
    const formData = new FormData()
    formData.append('file', file)
    
    if (additionalData) {
      Object.entries(additionalData).forEach(([key, value]) => {
        formData.append(key, value)
      })
    }

    const response = await this.instance.post<ApiResponse<T>>(url, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      onUploadProgress: (progressEvent) => {
        if (onProgress && progressEvent.total) {
          const progress = Math.round(
            (progressEvent.loaded * 100) / progressEvent.total
          )
          onProgress(progress)
        }
      },
    })

    return response.data
  }

  // 文件下载
  async download(
    url: string,
    filename?: string,
    config?: AxiosRequestConfig
  ): Promise<void> {
    const response = await this.instance.get(url, {
      ...config,
      responseType: 'blob',
    })

    // 从响应头获取文件名
    const contentDisposition = response.headers['content-disposition']
    let downloadFilename = filename
    
    if (!downloadFilename && contentDisposition) {
      const filenameMatch = contentDisposition.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/)
      if (filenameMatch && filenameMatch[1]) {
        downloadFilename = filenameMatch[1].replace(/['"]/g, '')
      }
    }

    // 创建下载链接
    const blob = new Blob([response.data])
    const downloadUrl = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = downloadUrl
    link.download = downloadFilename || 'download'
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(downloadUrl)
  }

  // PATCH请求
  async patch<T = any>(
    url: string,
    data?: any,
    config?: AxiosRequestConfig
  ): Promise<ApiResponse<T>> {
    const response = await this.instance.patch<ApiResponse<T>>(url, data, config)
    return response.data
  }

  // HEAD请求
  async head(
    url: string,
    config?: AxiosRequestConfig
  ): Promise<AxiosResponse> {
    return await this.instance.head(url, config)
  }

  // OPTIONS请求
  async options(
    url: string,
    config?: AxiosRequestConfig
  ): Promise<AxiosResponse> {
    return await this.instance.options(url, config)
  }

  // 批量请求
  async batch<T = any>(
    requests: Array<{
      method: 'get' | 'post' | 'put' | 'delete' | 'patch'
      url: string
      data?: any
      config?: AxiosRequestConfig
    }>
  ): Promise<ApiResponse<T>[]> {
    const promises = requests.map(req => {
      switch (req.method) {
        case 'get':
          return this.get(req.url, req.config)
        case 'post':
          return this.post(req.url, req.data, req.config)
        case 'put':
          return this.put(req.url, req.data, req.config)
        case 'delete':
          return this.delete(req.url, req.config)
        case 'patch':
          return this.patch(req.url, req.data, req.config)
        default:
          throw new Error(`Unsupported method: ${req.method}`)
      }
    })

    return Promise.all(promises)
  }

  // 取消请求
  createCancelToken() {
    return axios.CancelToken.source()
  }

  // 检查请求是否被取消
  isCancel(error: any): boolean {
    return axios.isCancel(error)
  }
}

// 导出API客户端实例
export const apiClient = new ApiClient(api)