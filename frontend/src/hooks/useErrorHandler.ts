import { useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import SuccessNotification from '@/components/Feedback/SuccessNotification'

interface ErrorInfo {
  code?: string | number
  message: string
  details?: Record<string, unknown>
  timestamp?: string
}

interface UseErrorHandlerOptions {
  showNotification?: boolean
  redirectOnError?: boolean
  logErrors?: boolean
}

interface ApiError {
  response?: { status: number; data?: Record<string, unknown> }
  request?: unknown
  message?: string
}

export const useErrorHandler = (options: UseErrorHandlerOptions = {}) => {
  const {
    showNotification = true,
    redirectOnError = false,
    logErrors = true,
  } = options

  const navigate = useNavigate()

  // 处理API错误
  const handleApiError = useCallback((error: ApiError) => {
    let errorInfo: ErrorInfo = {
      message: '未知错误',
      timestamp: new Date().toISOString(),
    }

    // 解析不同类型的错误
    if (error?.response) {
      // HTTP错误响应
      const { status, data } = error.response
      errorInfo = {
        code: status,
        message: (data?.message as string) || (data?.error as string) || `HTTP ${status} 错误`,
        details: data,
        timestamp: new Date().toISOString(),
      }

      // 根据状态码处理
      switch (status) {
        case 400:
          errorInfo.message = (data?.message as string) || '请求参数错误'
          break
        case 401:
          errorInfo.message = '登录已过期，请重新登录'
          if (redirectOnError) {
            navigate('/login')
          }
          break
        case 403:
          errorInfo.message = '权限不足，无法访问'
          break
        case 404:
          errorInfo.message = '请求的资源不存在'
          break
        case 422:
          errorInfo.message = (data?.message as string) || '数据验证失败'
          break
        case 429:
          errorInfo.message = '请求过于频繁，请稍后重试'
          break
        case 500:
          errorInfo.message = '服务器内部错误'
          break
        case 502:
          errorInfo.message = '网关错误'
          break
        case 503:
          errorInfo.message = '服务暂时不可用'
          break
        case 504:
          errorInfo.message = '请求超时'
          break
        default:
          errorInfo.message = (data?.message as string) || `服务器错误 (${status})`
      }
    } else if ((error as any)?.request) {
      // 网络错误
      errorInfo = {
        code: 'NETWORK_ERROR',
        message: '网络连接失败，请检查网络设置',
        details: error as any,
        timestamp: new Date().toISOString(),
      }
    } else if (error?.message) {
      // JavaScript错误
      errorInfo = {
        code: 'CLIENT_ERROR',
        message: error.message,
        details: error as any,
        timestamp: new Date().toISOString(),
      }
    }

    // 记录错误日志
    if (logErrors) {
      console.error('Error handled:', errorInfo)

      // 发送错误报告到监控服务
      reportError(errorInfo)
    }

    // 显示错误通知
    if (showNotification) {
      if (errorInfo.code === 401) {
        SuccessNotification.warning.permission()
      } else if (errorInfo.code === 'NETWORK_ERROR') {
        SuccessNotification.error.network()
      } else if (typeof errorInfo.code === 'number' && errorInfo.code >= 500) {
        SuccessNotification.error.server()
      } else {
        SuccessNotification.notify({
          type: 'error',
          title: '操作失败',
          description: errorInfo.message,
        })
      }
    }

    return errorInfo
  }, [navigate, showNotification, redirectOnError, logErrors])

  // 处理表单验证错误
  const handleValidationError = useCallback((errors: Record<string, string[]>) => {
    const errorMessages = Object.entries(errors)
      .map(([field, messages]) => `${field}: ${messages.join(', ')}`)
      .join('\n')

    if (showNotification) {
      SuccessNotification.error.validation(errorMessages)
    }

    if (logErrors) {
      console.error('Validation errors:', errors)
    }

    return errors
  }, [showNotification, logErrors])

  // 处理业务逻辑错误
  const handleBusinessError = useCallback((message: string, code?: string) => {
    const errorInfo: ErrorInfo = {
      code: code || 'BUSINESS_ERROR',
      message,
      timestamp: new Date().toISOString(),
    }

    if (logErrors) {
      console.error('Business error:', errorInfo)
    }

    if (showNotification) {
      SuccessNotification.notify({
        type: 'warning',
        title: '操作提示',
        description: message,
      })
    }

    return errorInfo
  }, [showNotification, logErrors])

  // 处理文件上传错误
  const handleUploadError = useCallback((error: { response?: { status: number }; message?: string }) => {
    let message = '文件上传失败'

    if (error?.response?.status === 413) {
      message = '文件大小超出限制'
    } else if (error?.response?.status === 415) {
      message = '不支持的文件格式'
    } else if (error?.message?.includes('timeout')) {
      message = '上传超时，请重试'
    }

    const errorInfo: ErrorInfo = {
      code: 'UPLOAD_ERROR',
      message,
      details: error,
      timestamp: new Date().toISOString(),
    }

    if (logErrors) {
      console.error('Upload error:', errorInfo)
    }

    if (showNotification) {
      SuccessNotification.notify({
        type: 'error',
        title: '上传失败',
        description: message,
      })
    }

    return errorInfo
  }, [showNotification, logErrors])

  // 重试机制
  const withRetry = useCallback(async <T>(
    operation: () => Promise<T>,
    maxRetries: number = 3,
    delay: number = 1000
  ): Promise<T> => {
    let lastError: unknown

    for (let attempt = 1; attempt <= maxRetries; attempt++) {
      try {
        return await operation()
      } catch (error) {
        lastError = error

        if (attempt === maxRetries) {
          break
        }

        // 指数退避延迟
        const waitTime = delay * Math.pow(2, attempt - 1)
        await new Promise(resolve => setTimeout(resolve, waitTime))
      }
    }

    throw lastError
  }, [])

  return {
    handleApiError,
    handleValidationError,
    handleBusinessError,
    handleUploadError,
    withRetry,
  }
}

// 错误报告函数
const reportError = (_errorInfo: ErrorInfo) => {
  // 这里可以集成错误监控服务
  try {
    // 示例：发送到后端API
    // fetch('/api/errors', {
    //   method: 'POST',
    //   headers: { 'Content-Type': 'application/json' },
    //   body: JSON.stringify({
    //     ...errorInfo,
    //     userAgent: navigator.userAgent,
    //     url: window.location.href,
    //     userId: getCurrentUserId(), // 如果有用户信息
    //   }),
    // }).catch(console.error)

    // 示例：发送到第三方监控服务
    // if (window.Sentry) {
    //   window.Sentry.captureException(new Error(errorInfo.message), {
    //     extra: errorInfo,
    //   })
    // }
  } catch (error) {
    console.error('Failed to report error:', error)
  }
}

export default useErrorHandler