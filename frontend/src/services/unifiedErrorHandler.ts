/**
 * 统一错误处理系统
 * 整合所有错误处理机制，提供一致的错误处理体验
 */

import { message, notification } from 'antd'
import { AxiosError } from 'axios'

// 错误类型枚举
export enum ErrorType {
  NETWORK_ERROR = 'NETWORK_ERROR',
  API_ERROR = 'API_ERROR',
  VALIDATION_ERROR = 'VALIDATION_ERROR',
  AUTHENTICATION_ERROR = 'AUTHENTICATION_ERROR',
  AUTHORIZATION_ERROR = 'AUTHORIZATION_ERROR',
  BUSINESS_ERROR = 'BUSINESS_ERROR',
  INTERNAL_SERVER_ERROR = 'INTERNAL_SERVER_ERROR',
  UNKNOWN_ERROR = 'UNKNOWN_ERROR'
}

// 错误严重程度
export enum ErrorSeverity {
  LOW = 'low',
  MEDIUM = 'medium',
  HIGH = 'high',
  CRITICAL = 'critical'
}

// 统一错误接口
export interface UnifiedError {
  code: string
  message: string
  type: ErrorType
  severity: ErrorSeverity
  timestamp: string
  requestId?: string
  details?: {
    field?: string
    message?: string
    code?: string
  }[] | string
  extraData?: Record<string, unknown>
}

// 错误处理选项
export interface ErrorHandlerOptions {
  showMessage?: boolean
  showNotification?: boolean
  logToConsole?: boolean
  customMessage?: string
  onError?: (error: UnifiedError) => void
}

// 错误码映射
const ERROR_CODE_MAP: Record<string, { type: ErrorType; severity: ErrorSeverity; defaultMessage: string }> = {
  // 通用错误 (1000-1999)
  'E1000': { type: ErrorType.INTERNAL_SERVER_ERROR, severity: ErrorSeverity.CRITICAL, defaultMessage: '服务器内部错误' },
  'E1001': { type: ErrorType.API_ERROR, severity: ErrorSeverity.MEDIUM, defaultMessage: '无效请求' },
  'E1002': { type: ErrorType.VALIDATION_ERROR, severity: ErrorSeverity.MEDIUM, defaultMessage: '数据验证失败' },
  'E1003': { type: ErrorType.AUTHENTICATION_ERROR, severity: ErrorSeverity.HIGH, defaultMessage: '未授权访问' },
  'E1004': { type: ErrorType.AUTHORIZATION_ERROR, severity: ErrorSeverity.HIGH, defaultMessage: '权限不足' },
  'E1005': { type: ErrorType.API_ERROR, severity: ErrorSeverity.LOW, defaultMessage: '资源未找到' },

  // 业务错误 (2000-2999)
  'E2000': { type: ErrorType.BUSINESS_ERROR, severity: ErrorSeverity.MEDIUM, defaultMessage: '业务逻辑错误' },
  'E2001': { type: ErrorType.API_ERROR, severity: ErrorSeverity.LOW, defaultMessage: '资源未找到' },
  'E2002': { type: ErrorType.BUSINESS_ERROR, severity: ErrorSeverity.MEDIUM, defaultMessage: '资源已存在' },
  'E2003': { type: ErrorType.BUSINESS_ERROR, severity: ErrorSeverity.MEDIUM, defaultMessage: '资源冲突' },
  'E2004': { type: ErrorType.AUTHORIZATION_ERROR, severity: ErrorSeverity.HIGH, defaultMessage: '操作不被允许' },

  // 数据验证错误 (3000-3999)
  'E3000': { type: ErrorType.VALIDATION_ERROR, severity: ErrorSeverity.MEDIUM, defaultMessage: '数据验证失败' },
  'E3001': { type: ErrorType.VALIDATION_ERROR, severity: ErrorSeverity.MEDIUM, defaultMessage: '必填字段缺失' },
  'E3002': { type: ErrorType.VALIDATION_ERROR, severity: ErrorSeverity.MEDIUM, defaultMessage: '字段格式无效' },
  'E3003': { type: ErrorType.VALIDATION_ERROR, severity: ErrorSeverity.MEDIUM, defaultMessage: '字段值超出范围' },

  // 权限和认证错误 (4000-4999)
  'E4000': { type: ErrorType.AUTHENTICATION_ERROR, severity: ErrorSeverity.HIGH, defaultMessage: '认证失败' },
  'E4001': { type: ErrorType.AUTHENTICATION_ERROR, severity: ErrorSeverity.HIGH, defaultMessage: '登录已过期' },
  'E4002': { type: ErrorType.AUTHENTICATION_ERROR, severity: ErrorSeverity.HIGH, defaultMessage: '令牌无效' },
  'E4003': { type: ErrorType.AUTHORIZATION_ERROR, severity: ErrorSeverity.HIGH, defaultMessage: '权限不足' },

  // 外部服务错误 (5000-5999)
  'E5000': { type: ErrorType.INTERNAL_SERVER_ERROR, severity: ErrorSeverity.HIGH, defaultMessage: '外部服务错误' },
  'E5001': { type: ErrorType.INTERNAL_SERVER_ERROR, severity: ErrorSeverity.CRITICAL, defaultMessage: '数据库错误' },
  'E5002': { type: ErrorType.INTERNAL_SERVER_ERROR, severity: ErrorSeverity.MEDIUM, defaultMessage: '文件上传失败' },
  'E5004': { type: ErrorType.INTERNAL_SERVER_ERROR, severity: ErrorSeverity.MEDIUM, defaultMessage: 'PDF处理失败' }
}

/**
 * 统一错误处理器类
 */
export class UnifiedErrorHandler {
  private static instance: UnifiedErrorHandler
  private errorQueue: UnifiedError[] = []
  private maxQueueSize = 100

  private constructor() {
    // 设置全局错误监听
    this.setupGlobalErrorHandlers()
  }

  static getInstance(): UnifiedErrorHandler {
    if (!UnifiedErrorHandler.instance) {
      UnifiedErrorHandler.instance = new UnifiedErrorHandler()
    }
    return UnifiedErrorHandler.instance
  }

  /**
   * 处理错误
   */
  handleError(error: unknown, options: ErrorHandlerOptions = {}): UnifiedError {
    const unifiedError = this.parseError(error)

    // 添加到错误队列
    this.addToErrorQueue(unifiedError)

    // 日志记录
    if (options.logToConsole !== false) {
      this.logError(unifiedError)
    }

    // 显示错误消息
    if (options.showMessage !== false) {
      this.showErrorMessage(unifiedError, options)
    }

    // 调用自定义回调
    if (options.onError) {
      options.onError(unifiedError)
    }

    return unifiedError
  }

  /**
   * 解析各种类型的错误为统一错误格式
   */
  private parseError(error: unknown): UnifiedError {
    // Axios错误
    if (this.isAxiosError(error)) {
      return this.parseAxiosError(error)
    }

    // 统一错误格式
    if (this.isUnifiedError(error)) {
      return error
    }

    // 标准Error对象
    if (error instanceof Error) {
      return this.parseStandardError(error)
    }

    // 字符串错误
    if (typeof error === 'string') {
      return this.parseStringError(error)
    }

    // 未知错误
    return this.parseUnknownError(error)
  }

  /**
   * 解析Axios错误
   */
  private parseAxiosError(error: AxiosError): UnifiedError {
    const response = error.response
    const request = error.request

    // 网络错误
    if (!response && request) {
      return {
        code: 'NETWORK_ERROR',
        message: '网络连接失败，请检查网络设置',
        type: ErrorType.NETWORK_ERROR,
        severity: ErrorSeverity.MEDIUM,
        timestamp: new Date().toISOString(),
        details: error.message
      }
    }

    // 服务器响应错误
    if (response?.data) {
      const data = response.data as any

      // 后端统一错误格式
      if (data.error && data.error.code) {
        const errorInfo = ERROR_CODE_MAP[data.error.code] || {
          type: ErrorType.UNKNOWN_ERROR,
          severity: ErrorSeverity.MEDIUM,
          defaultMessage: '未知错误'
        }

        return {
          code: data.error.code,
          message: data.error.message || errorInfo.defaultMessage,
          type: errorInfo.type,
          severity: errorInfo.severity,
          timestamp: data.error.timestamp || new Date().toISOString(),
          requestId: data.request_id,
          details: data.error.details,
          extraData: {
            status: response.status,
            statusText: response.statusText,
            url: response.config.url
          }
        }
      }

      // 其他格式的错误响应
      return {
        code: `HTTP_${response.status}`,
        message: data.message || data.error?.message || `请求失败 (${response.status})`,
        type: response.status >= 500 ? ErrorType.INTERNAL_SERVER_ERROR : ErrorType.API_ERROR,
        severity: response.status >= 500 ? ErrorSeverity.HIGH : ErrorSeverity.MEDIUM,
        timestamp: new Date().toISOString(),
        extraData: {
          status: response.status,
          statusText: response.statusText,
          url: response.config.url,
          responseData: data
        }
      }
    }

    // 其他Axios错误
    return {
      code: 'AXIOS_ERROR',
      message: error.message || '请求失败',
      type: ErrorType.API_ERROR,
      severity: ErrorSeverity.MEDIUM,
      timestamp: new Date().toISOString(),
      details: error.message
    }
  }

  /**
   * 解析标准Error对象
   */
  private parseStandardError(error: Error): UnifiedError {
    return {
      code: 'STANDARD_ERROR',
      message: error.message,
      type: ErrorType.UNKNOWN_ERROR,
      severity: ErrorSeverity.MEDIUM,
      timestamp: new Date().toISOString(),
      details: error.stack
    }
  }

  /**
   * 解析字符串错误
   */
  private parseStringError(error: string): UnifiedError {
    return {
      code: 'STRING_ERROR',
      message: error,
      type: ErrorType.UNKNOWN_ERROR,
      severity: ErrorSeverity.MEDIUM,
      timestamp: new Date().toISOString()
    }
  }

  /**
   * 解析未知错误
   */
  private parseUnknownError(error: unknown): UnifiedError {
    return {
      code: 'UNKNOWN_ERROR',
      message: '未知错误',
      type: ErrorType.UNKNOWN_ERROR,
      severity: ErrorSeverity.MEDIUM,
      timestamp: new Date().toISOString(),
      details: typeof error === 'object' ? JSON.stringify(error) : String(error)
    }
  }

  /**
   * 显示错误消息
   */
  private showErrorMessage(error: UnifiedError, options: ErrorHandlerOptions): void {
    const displayMessage = options.customMessage || error.message

    // CRITICAL错误使用通知
    if (error.severity === ErrorSeverity.CRITICAL) {
      notification.error({
        message: '严重错误',
        description: displayMessage,
        duration: 0, // 不自动关闭
        key: error.code
      })
      return
    }

    // HIGH错误使用持久通知
    if (error.severity === ErrorSeverity.HIGH) {
      if (options.showNotification !== false) {
        notification.error({
          message: '错误',
          description: displayMessage,
          duration: 8,
          key: error.code
        })
      }
      return
    }

    // MEDIUM和LOW错误使用message
    if (options.showMessage !== false) {
      message.error(displayMessage)
    }
  }

  /**
   * 记录错误日志
   */
  private logError(error: UnifiedError): void {
    const logData = {
      ...error,
      userAgent: navigator.userAgent,
      url: window.location.href,
      timestamp: new Date().toISOString()
    }

    switch (error.severity) {
      case ErrorSeverity.CRITICAL:
        console.error('🚨 Critical Error:', logData)
        break
      case ErrorSeverity.HIGH:
        console.error('🔴 High Severity Error:', logData)
        break
      case ErrorSeverity.MEDIUM:
        console.warn('🟡 Medium Severity Error:', logData)
        break
      case ErrorSeverity.LOW:
        console.info('🟢 Low Severity Error:', logData)
        break
    }
  }

  /**
   * 添加到错误队列
   */
  private addToErrorQueue(error: UnifiedError): void {
    this.errorQueue.push(error)
    if (this.errorQueue.length > this.maxQueueSize) {
      this.errorQueue.shift()
    }
  }

  /**
   * 获取错误队列
   */
  getErrorQueue(): UnifiedError[] {
    return [...this.errorQueue]
  }

  /**
   * 清空错误队列
   */
  clearErrorQueue(): void {
    this.errorQueue = []
  }

  /**
   * 设置全局错误监听
   */
  private setupGlobalErrorHandlers(): void {
    // 全局未捕获的错误
    window.addEventListener('error', (event) => {
      this.handleError(event.error || new Error(event.message), {
        showMessage: true,
        logToConsole: true
      })
    })

    // 全局未捕获的Promise错误
    window.addEventListener('unhandledrejection', (event) => {
      this.handleError(event.reason, {
        showMessage: true,
        logToConsole: true
      })
    })
  }

  /**
   * 类型检查方法
   */
  private isAxiosError(error: unknown): error is AxiosError {
    return error !== null && typeof error === 'object' && 'isAxiosError' in error
  }

  private isUnifiedError(error: unknown): error is UnifiedError {
    return error !== null && typeof error === 'object' &&
           'code' in error && 'message' in error && 'type' in error && 'severity' in error
  }
}

// 创建全局实例
export const unifiedErrorHandler = UnifiedErrorHandler.getInstance()

// 便捷的错误处理函数
export const handleError = (error: unknown, options?: ErrorHandlerOptions) => {
  return unifiedErrorHandler.handleError(error, options)
}

// 特定类型的错误处理函数
export const handleNetworkError = (error: unknown, options?: ErrorHandlerOptions) => {
  return handleError(error, {
    customMessage: '网络连接失败，请检查网络设置后重试',
    ...options
  })
}

export const handleAuthError = (error: unknown, onRedirect?: () => void) => {
  const unifiedError = handleError(error, {
    customMessage: '登录已过期，请重新登录',
    showMessage: true
  })

  // 如果是认证错误，执行重定向
  if (unifiedError.type === ErrorType.AUTHENTICATION_ERROR && onRedirect) {
    setTimeout(onRedirect, 2000)
  }

  return unifiedError
}

export const handleValidationError = (error: unknown, options?: ErrorHandlerOptions) => {
  return handleError(error, {
    customMessage: '数据验证失败，请检查输入内容',
    ...options
  })
}

export const handleBusinessError = (error: unknown, options?: ErrorHandlerOptions) => {
  return handleError(error, options)
}

export default unifiedErrorHandler
