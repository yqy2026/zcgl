import { message } from 'antd'

/**
 * 统一错误处理工具
 * 提供一致的错误处理模式和用户友好的错误消息
 */

export interface ErrorHandlerOptions {
  fallbackMessage?: string
  showDetails?: boolean
  duration?: number
  logToConsole?: boolean
}

/**
 * 错误类型枚举
 */
export enum ErrorType {
  NETWORK_ERROR = 'NETWORK_ERROR',
  API_ERROR = 'API_ERROR',
  VALIDATION_ERROR = 'VALIDATION_ERROR',
  PERMISSION_ERROR = 'PERMISSION_ERROR',
  NOT_FOUND_ERROR = 'NOT_FOUND_ERROR',
  TIMEOUT_ERROR = 'TIMEOUT_ERROR',
  UNKNOWN_ERROR = 'UNKNOWN_ERROR'
}

/**
 * 标准化错误接口
 */
export interface StandardError {
  type: ErrorType
  code: string
  message: string
  details?: any
  timestamp: string
  stack?: string
}

/**
 * 错误消息映射表
 */
const ERROR_MESSAGES: Record<ErrorType, string> = {
  [ErrorType.NETWORK_ERROR]: '网络连接失败，请检查网络设置',
  [ErrorType.API_ERROR]: '服务器处理请求时发生错误',
  [ErrorType.VALIDATION_ERROR]: '数据验证失败，请检查输入内容',
  [ErrorType.PERMISSION_ERROR]: '权限不足，无法执行此操作',
  [ErrorType.NOT_FOUND_ERROR]: '请求的资源不存在',
  [ErrorType.TIMEOUT_ERROR]: '请求超时，请稍后重试',
  [ErrorType.UNKNOWN_ERROR]: '发生未知错误，请稍后重试'
}

/**
 * 判断错误类型
 */
export function getErrorType(error: any): ErrorType {
  if (!error) return ErrorType.UNKNOWN_ERROR

  // 网络错误
  if (error.name === 'NetworkError' || error.code === 'NETWORK_ERROR') {
    return ErrorType.NETWORK_ERROR
  }

  // 超时错误
  if (error.name === 'TimeoutError' || error.code === 'ECONNABORTED') {
    return ErrorType.TIMEOUT_ERROR
  }

  // 404 错误
  if (error.status === 404 || error.response?.status === 404) {
    return ErrorType.NOT_FOUND_ERROR
  }

  // 403 错误
  if (error.status === 403 || error.response?.status === 403) {
    return ErrorType.PERMISSION_ERROR
  }

  // 422 错误（验证错误）
  if (error.status === 422 || error.response?.status === 422) {
    return ErrorType.VALIDATION_ERROR
  }

  // API 错误
  if (error.response?.status >= 400) {
    return ErrorType.API_ERROR
  }

  return ErrorType.UNKNOWN_ERROR
}

/**
 * 提取错误消息
 */
export function extractErrorMessage(error: any): string {
  if (!error) return ERROR_MESSAGES[ErrorType.UNKNOWN_ERROR]

  // 直接的错误消息
  if (typeof error === 'string') return error

  // 对象中的错误消息
  if (error.message) return error.message

  // API 响应错误
  if (error.response?.data?.detail) return error.response.data.detail
  if (error.response?.data?.message) return error.response.data.message
  if (error.response?.data?.error) return error.response.data.error

  // 验证错误
  if (error.response?.data?.errors) {
    const errors = error.response.data.errors
    if (Array.isArray(errors)) {
      return errors.join(', ')
    }
    if (typeof errors === 'object') {
      return Object.values(errors).flat().join(', ')
    }
  }

  // 默认消息
  const errorType = getErrorType(error)
  return ERROR_MESSAGES[errorType]
}

/**
 * 标准化错误对象
 */
export function normalizeError(error: any): StandardError {
  const errorType = getErrorType(error)
  const message = extractErrorMessage(error)

  return {
    type: errorType,
    code: error.code || error.status?.toString() || 'UNKNOWN',
    message,
    details: error.details || error.response?.data || null,
    timestamp: new Date().toISOString(),
    stack: error.stack
  }
}

/**
 * 统一错误处理函数
 */
export function handleError(
  error: any,
  options: ErrorHandlerOptions = {}
): StandardError {
  const {
    fallbackMessage = '操作失败，请稍后重试',
    showDetails = false,
    duration = 3,
    logToConsole = true
  } = options

  // 标准化错误
  const standardError = normalizeError(error)

  // 控制台日志
  if (logToConsole) {
    console.group(`🚨 Error [${standardError.type}]`)
    console.error('Error:', error)
    console.error('Standardized:', standardError)
    console.groupEnd()
  }

  // 显示用户友好的错误消息
  let displayMessage = standardError.message

  // 如果消息太技术化，使用默认消息
  if (displayMessage.includes('Internal Server Error') ||
      displayMessage.includes('SyntaxError') ||
      displayMessage.includes('TypeError')) {
    displayMessage = fallbackMessage
  }

  // 添加详细信息（如果需要）
  if (showDetails && standardError.details) {
    displayMessage += ` (${JSON.stringify(standardError.details)})`
  }

  // 显示消息
  message.error({
    content: displayMessage,
    duration
  })

  return standardError
}

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
): Promise<{ success: boolean; data?: T; error?: StandardError }> {
  try {
    const data = await operation()

    // 显示成功消息（如果配置）
    if (options.successMessage) {
      message.success({
        content: options.successMessage,
        duration: options.duration || 2
      })
    }

    return { success: true, data }
  } catch (error: any) {
    const standardError = handleError(error, {
      fallbackMessage: options.errorMessage,
      ...options
    })

    return { success: false, error: standardError }
  }
}

/**
 * 创建错误边界友好的错误处理
 */
export function createErrorHandler(
  context: string,
  options: ErrorHandlerOptions = {}
) {
  return (error: any) => {
    console.error(`Error in ${context}:`, error)
    return handleError(error, {
      fallbackMessage: `${context}操作失败`,
      ...options
    })
  }
}

/**
 * 导出默认配置
 */
export const defaultErrorHandler = handleError