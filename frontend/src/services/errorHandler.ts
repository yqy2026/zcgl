// API错误处理工具

import { message, notification } from 'antd'
import type { ErrorResponse } from '@/types/api'
import { HTTP_STATUS, ERROR_CODES } from '../api/config'

// 日志数据接口
export interface LogData {
  timestamp: string
  level: 'error' | 'warning' | 'info'
  message: string
  error?: {
    message?: string
    stack?: string
    name?: string
  }
  context?: Record<string, unknown>
  userAgent?: string
  url?: string
}

export interface ErrorHandlerOptions {
  showMessage?: boolean
  showNotification?: boolean
  logError?: boolean
  customHandler?: (error: ErrorResponse) => void
}

export class ApiErrorHandler {
  private static instance: ApiErrorHandler
  
  private constructor() {}
  
  static getInstance(): ApiErrorHandler {
    if (!ApiErrorHandler.instance) {
      ApiErrorHandler.instance = new ApiErrorHandler()
    }
    return ApiErrorHandler.instance
  }
  
  // 处理API错误
  handle(error: ErrorResponse, options: ErrorHandlerOptions = {}): void {
    const {
      showMessage = true,
      showNotification = false,
      logError = true,
      customHandler,
    } = options
    
    // 记录错误日志
    if (logError) {
      this.logError(error)
    }
    
    // 自定义错误处理
    if (customHandler) {
      customHandler(error)
      return
    }
    
    // 根据错误类型显示不同的提示
    if (showMessage) {
      this.showErrorMessage(error)
    }
    
    if (showNotification) {
      this.showErrorNotification(error)
    }
    
    // 特殊错误处理
    this.handleSpecialErrors(error)
  }
  
  // 显示错误消息
  private showErrorMessage(error: ErrorResponse): void {
    const errorMessage = this.getErrorMessage(error)
    
    switch (this.getErrorType(error)) {
      case 'validation':
        message.warning(errorMessage)
        break
      case 'permission':
        message.error(errorMessage)
        break
      case 'network':
        message.error(errorMessage)
        break
      default:
        message.error(errorMessage)
    }
  }
  
  // 显示错误通知
  private showErrorNotification(error: ErrorResponse): void {
    const errorMessage = this.getErrorMessage(error)
    const errorType = this.getErrorType(error)
    
    notification.error({
      message: this.getErrorTitle(errorType),
      description: errorMessage,
      duration: 4.5,
      placement: 'topRight',
    })
  }
  
  // 获取错误消息
  private getErrorMessage(error: ErrorResponse): string {
    // 优先使用服务器返回的错误消息
    if (error.message) {
      return error.message
    }
    
    // 根据错误代码返回默认消息
    switch (error.error) {
      case ERROR_CODES.NETWORK_ERROR:
        return '网络连接失败，请检查网络设置'
      case ERROR_CODES.TIMEOUT_ERROR:
        return '请求超时，请稍后重试'
      case ERROR_CODES.VALIDATION_ERROR:
        return '请求参数验证失败'
      case ERROR_CODES.PERMISSION_ERROR:
        return '权限不足，无法执行此操作'
      case ERROR_CODES.NOT_FOUND_ERROR:
        return '请求的资源不存在'
      case ERROR_CODES.SERVER_ERROR:
        return '服务器内部错误，请稍后重试'
      default:
        return '操作失败，请稍后重试'
    }
  }
  
  // 获取错误类型
  private getErrorType(error: ErrorResponse): string {
    if (error.error === ERROR_CODES.NETWORK_ERROR) {
      return 'network'
    }
    
    if (error.error === ERROR_CODES.VALIDATION_ERROR) {
      return 'validation'
    }
    
    if (error.error === ERROR_CODES.PERMISSION_ERROR) {
      return 'permission'
    }
    
    return 'general'
  }
  
  // 获取错误标题
  private getErrorTitle(errorType: string): string {
    switch (errorType) {
      case 'network':
        return '网络错误'
      case 'validation':
        return '参数错误'
      case 'permission':
        return '权限错误'
      default:
        return '操作失败'
    }
  }
  
  // 处理特殊错误
  private handleSpecialErrors(error: ErrorResponse): void {
    // 处理认证错误
    if (error.error === ERROR_CODES.PERMISSION_ERROR) {
      this.handleAuthError()
    }
    
    // 处理服务器错误
    if (error.error === ERROR_CODES.SERVER_ERROR) {
      this.handleServerError(error)
    }
  }
  
  // 处理认证错误
  private handleAuthError(): void {
    // 清除本地存储的认证信息
    localStorage.removeItem('auth_token')
    localStorage.removeItem('user_info')
    
    // 延迟跳转到登录页面
    setTimeout(() => {
      if (window.location.pathname !== '/login') {
        window.location.href = '/login'
      }
    }, 1000)
  }
  
  // 处理服务器错误
  private handleServerError(error: ErrorResponse): void {
    // 可以在这里添加错误上报逻辑
    console.error('Server Error:', error)
    
    // 如果是开发环境，显示详细错误信息
    if (process.env.NODE_ENV === 'development' && error.details) {
      console.error('Error Details:', error.details)
    }
  }
  
  // 记录错误日志
  private logError(error: ErrorResponse): void {
    const logData: LogData = {
      timestamp: new Date().toISOString(),
      level: 'error',
      message: error.message,
      error: {
        message: error.error,
        name: error.error,
      },
      context: error.details ? { details: error.details } : undefined,
      url: window.location.href,
      userAgent: navigator.userAgent,
    }

    console.error('API Error:', logData)

    // 在生产环境中，可以将错误发送到日志服务
    if (process.env.NODE_ENV === 'production') {
      this.sendErrorToLogService(logData)
    }
  }
  
  // 发送错误到日志服务
  private sendErrorToLogService(_logData: LogData): void {
    // 这里可以集成第三方日志服务，如 Sentry、LogRocket 等
    // 示例：
    // Sentry.captureException(new Error(logData.message), {
    //   extra: logData,
    // })
  }
  
  // 创建用户友好的错误消息
  static createUserFriendlyError(
    originalError: unknown,
    context?: string
  ): ErrorResponse {
    let message = '操作失败，请稍后重试'
    let error: string = ERROR_CODES.SERVER_ERROR

    const err = originalError as any

    if (err.response) {
      const status = err.response.status
      switch (status) {
        case HTTP_STATUS.BAD_REQUEST:
          message = '请求参数错误'
          error = ERROR_CODES.VALIDATION_ERROR as any
          break
        case HTTP_STATUS.UNAUTHORIZED:
          message = '未授权访问，请重新登录'
          error = ERROR_CODES.PERMISSION_ERROR as any
          break
        case HTTP_STATUS.FORBIDDEN:
          message = '权限不足，无法执行此操作'
          error = ERROR_CODES.PERMISSION_ERROR as any
          break
        case HTTP_STATUS.NOT_FOUND:
          message = context ? `${context}不存在` : '请求的资源不存在'
          error = ERROR_CODES.NOT_FOUND_ERROR as any
          break
        case HTTP_STATUS.UNPROCESSABLE_ENTITY:
          message = '数据验证失败'
          error = ERROR_CODES.VALIDATION_ERROR as any
          break
        case HTTP_STATUS.INTERNAL_SERVER_ERROR:
          message = '服务器内部错误'
          error = ERROR_CODES.SERVER_ERROR
          break
      }
    } else if (err.code === 'NETWORK_ERROR') {
      message = '网络连接失败，请检查网络设置'
      error = ERROR_CODES.NETWORK_ERROR as any
    } else if (err.code === 'ECONNABORTED') {
      message = '请求超时，请稍后重试'
      error = ERROR_CODES.TIMEOUT_ERROR as any
    }

    return {
      error,
      message,
      timestamp: new Date().toISOString(),
      details: err.response?.data?.details,
    }
  }
}

// 导出单例实例
export const errorHandler = ApiErrorHandler.getInstance()

// 导出便捷方法
export const handleApiError = (
  error: unknown,
  options?: ErrorHandlerOptions,
  context?: string
) => {
  const errorResponse = ApiErrorHandler.createUserFriendlyError(error, context)
  errorHandler.handle(errorResponse, options)
}

// ============================================================
// 增强工具函数 (从 utils/errorHandler.ts 合并)
// ============================================================

/**
 * 异步操作包装器
 * 自动处理错误并返回标准化结果
 */
export async function withErrorHandling<T>(
  operation: () => Promise<T>,
  options: ErrorHandlerOptions & {
    errorMessage?: string
    successMessage?: string
  } = {}
): Promise<{ success: boolean; data?: T; error?: ErrorResponse }> {
  try {
    const data = await operation()

    // 显示成功消息（如果配置）
    if (options.successMessage) {
      message.success({
        content: options.successMessage,
        duration: 2
      })
    }

    return { success: true, data }
  } catch (error: unknown) {
    const errorResponse = ApiErrorHandler.createUserFriendlyError(error, options.errorMessage)

    // 记录错误日志
    if (options.logError !== false) {
      (errorHandler as any).logError(errorResponse)
    }

    // 显示错误消息
    if (options.showMessage !== false) {
      message.error(errorResponse.message || '操作失败')
    }

    return { success: false, error: errorResponse }
  }
}

/**
 * 创建上下文错误处理器
 * 为特定上下文创建带上下文信息的错误处理器
 */
export function createErrorHandler(
  context: string,
  baseOptions: ErrorHandlerOptions = {}
) {
  return (error: unknown, options?: ErrorHandlerOptions) => {
    const errorResponse = ApiErrorHandler.createUserFriendlyError(error, `${context}操作失败`)

    errorHandler.handle(errorResponse, {
      ...baseOptions,
      ...options,
      logError: baseOptions.logError !== false && options?.logError !== false
    })

    return errorResponse
  }
}