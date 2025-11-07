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
  details?: unknown
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
export function getErrorType(error: unknown): ErrorType {
  if (!error) return ErrorType.UNKNOWN_ERROR

  const err = error as Record<string, unknown>

  // 网络错误
  if (err.name === 'NetworkError' || err.code === 'NETWORK_ERROR') {
    return ErrorType.NETWORK_ERROR
  }

  // 超时错误
  if (err.name === 'TimeoutError' || err.code === 'ECONNABORTED') {
    return ErrorType.TIMEOUT_ERROR
  }

  // 404 错误
  if (err.status === 404 || (err.response as Record<string, unknown>)?.status === 404) {
    return ErrorType.NOT_FOUND_ERROR
  }

  // 403 错误
  if (err.status === 403 || (err.response as Record<string, unknown>)?.status === 403) {
    return ErrorType.PERMISSION_ERROR
  }

  // 422 错误（验证错误）
  if (err.status === 422 || (err.response as Record<string, unknown>)?.status === 422) {
    return ErrorType.VALIDATION_ERROR
  }

  // API 错误
  if ((err.response as Record<string, unknown>)?.status && (err.response as Record<string, unknown>).status as number >= 400) {
    return ErrorType.API_ERROR
  }

  return ErrorType.UNKNOWN_ERROR
}

/**
 * 提取错误消息
 */
export function extractErrorMessage(error: unknown): string {
  if (!error) return ERROR_MESSAGES[ErrorType.UNKNOWN_ERROR]

  // 直接的错误消息
  if (typeof error === 'string') return error

  const err = error as Record<string, unknown>

  // 对象中的错误消息
  if (err.message && typeof err.message === 'string') return err.message

  // API 响应错误
  const responseData = err.response as Record<string, unknown>
  if (responseData?.data) {
    const data = responseData.data as Record<string, unknown>
    if (data.detail && typeof data.detail === 'string') return data.detail
    if (data.message && typeof data.message === 'string') return data.message
    if (data.error && typeof data.error === 'string') return data.error
  }

  // 验证错误
  if (responseData?.data) {
    const data = responseData.data as Record<string, unknown>
    if (data.errors) {
      const errors = data.errors
      if (Array.isArray(errors)) {
        return errors.filter(e => typeof e === 'string').join(', ')
      }
      if (typeof errors === 'object' && errors !== null) {
        return Object.values(errors).flat().filter(e => typeof e === 'string').join(', ')
      }
    }
  }

  // 默认消息
  const errorType = getErrorType(error)
  return ERROR_MESSAGES[errorType]
}

/**
 * 标准化错误对象
 */
export function normalizeError(error: unknown): StandardError {
  const errorType = getErrorType(error)
  const message = extractErrorMessage(error)
  const err = error as Record<string, unknown>

  return {
    type: errorType,
    code: (err.code as string) || (err.status as number)?.toString() || 'UNKNOWN',
    message,
    details: err.details || (err.response as Record<string, unknown>)?.data || null,
    timestamp: new Date().toISOString(),
    stack: err.stack as string
  }
}

/**
 * 统一错误处理函数
 */
export function handleError(
  error: unknown,
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
  } catch (error: unknown) {
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
  return (error: unknown) => {
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