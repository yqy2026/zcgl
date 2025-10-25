// API错误处理工具

import { message, notification } from 'antd'
import type { ErrorResponse } from '@/types/api'
import { HTTP_STATUS, ERROR_CODES } from './config'

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
    if (import.meta.env.DEV && error.details) {
      console.error('Error Details:', error.details)
    }
  }
  
  // 记录错误日志
  private logError(error: ErrorResponse): void {
    const logData = {
      timestamp: new Date().toISOString(),
      error: error.error,
      message: error.message,
      details: error.details,
      url: window.location.href,
      userAgent: navigator.userAgent,
    }
    
    console.error('API Error:', logData)
    
    // 在生产环境中，可以将错误发送到日志服务
    if (import.meta.env.PROD) {
      this.sendErrorToLogService(logData)
    }
  }
  
  // 发送错误到日志服务
  private sendErrorToLogService(_logData: any): void {
    // 这里可以集成第三方日志服务，如 Sentry、LogRocket 等
    // 示例：
    // Sentry.captureException(new Error(logData.message), {
    //   extra: logData,
    // })
  }
  
  // 创建用户友好的错误消息
  static createUserFriendlyError(
    originalError: any,
    context?: string
  ): ErrorResponse {
    let message = '操作失败，请稍后重试'
    let error = ERROR_CODES.SERVER_ERROR
    
    if (originalError.response) {
      const status = originalError.response.status
      switch (status) {
        case HTTP_STATUS.BAD_REQUEST:
          message = '请求参数错误'
          error = ERROR_CODES.VALIDATION_ERROR
          break
        case HTTP_STATUS.UNAUTHORIZED:
          message = '未授权访问，请重新登录'
          error = ERROR_CODES.PERMISSION_ERROR
          break
        case HTTP_STATUS.FORBIDDEN:
          message = '权限不足，无法执行此操作'
          error = ERROR_CODES.PERMISSION_ERROR
          break
        case HTTP_STATUS.NOT_FOUND:
          message = context ? `${context}不存在` : '请求的资源不存在'
          error = ERROR_CODES.NOT_FOUND_ERROR
          break
        case HTTP_STATUS.UNPROCESSABLE_ENTITY:
          message = '数据验证失败'
          error = ERROR_CODES.VALIDATION_ERROR
          break
        case HTTP_STATUS.INTERNAL_SERVER_ERROR:
          message = '服务器内部错误'
          error = ERROR_CODES.SERVER_ERROR
          break
      }
    } else if (originalError.code === 'NETWORK_ERROR') {
      message = '网络连接失败，请检查网络设置'
      error = ERROR_CODES.NETWORK_ERROR
    } else if (originalError.code === 'ECONNABORTED') {
      message = '请求超时，请稍后重试'
      error = ERROR_CODES.TIMEOUT_ERROR
    }
    
    return {
      error,
      message,
      timestamp: new Date().toISOString(),
      details: originalError.response?.data?.details,
    }
  }
}

// 导出单例实例
export const errorHandler = ApiErrorHandler.getInstance()

// 导出便捷方法
export const handleApiError = (
  error: any,
  options?: ErrorHandlerOptions,
  context?: string
) => {
  const errorResponse = ApiErrorHandler.createUserFriendlyError(error, context)
  errorHandler.handle(errorResponse, options)
}