import { renderHook, act } from '@testing-library/react'
import { describe, it, expect, beforeEach, jest } from '@jest/globals'
import { useNavigate } from 'react-router-dom'

import { useErrorHandler } from '../useErrorHandler'

// Mock react-router-dom
jest.mock('react-router-dom', () => ({
  useNavigate: jest.fn(),
}))

// Mock SuccessNotification
jest.mock('@/components/Feedback/SuccessNotification', () => ({
  default: {
    notify: jest.fn(),
    warning: {
      permission: jest.fn(),
    },
    error: {
      network: jest.fn(),
      server: jest.fn(),
      validation: jest.fn(),
      upload: jest.fn(),
    },
  },
}))

describe('useErrorHandler', () => {
  const mockNavigate = jest.fn()

  beforeEach(() => {
    jest.clearAllMocks()
    ;(useNavigate as jest.MockedFunction<typeof useNavigate>).mockReturnValue(mockNavigate)
  })

  it('handles API errors correctly', () => {
    const { result } = renderHook(() => useErrorHandler())

    const apiError = {
      response: {
        status: 400,
        data: {
          message: 'Bad request',
        },
      },
    }

    act(() => {
      const errorInfo = result.current.handleApiError(apiError)
      
      expect(errorInfo).toEqual({
        code: 400,
        message: 'Bad request',
        details: { message: 'Bad request' },
        timestamp: expect.any(String),
      })
    })
  })

  it('handles 401 errors and redirects to login', () => {
    const { result } = renderHook(() => 
      useErrorHandler({ redirectOnError: true })
    )

    const unauthorizedError = {
      response: {
        status: 401,
        data: {},
      },
    }

    act(() => {
      result.current.handleApiError(unauthorizedError)
      expect(mockNavigate).toHaveBeenCalledWith('/login')
    })
  })

  it('handles network errors', () => {
    const { result } = renderHook(() => useErrorHandler())

    const networkError = {
      request: {},
      message: 'Network Error',
    }

    act(() => {
      const errorInfo = result.current.handleApiError(networkError)
      
      expect(errorInfo).toEqual({
        code: 'NETWORK_ERROR',
        message: '网络连接失败，请检查网络设置',
        details: {},
        timestamp: expect.any(String),
      })
    })
  })

  it('handles validation errors', () => {
    const { result } = renderHook(() => useErrorHandler())

    const validationErrors = {
      name: ['名称不能为空'],
      email: ['邮箱格式不正确'],
    }

    act(() => {
      const errors = result.current.handleValidationError(validationErrors)
      expect(errors).toEqual(validationErrors)
    })
  })

  it('handles business errors', () => {
    const { result } = renderHook(() => useErrorHandler())

    act(() => {
      const errorInfo = result.current.handleBusinessError('业务逻辑错误', 'BIZ_001')
      
      expect(errorInfo).toEqual({
        code: 'BIZ_001',
        message: '业务逻辑错误',
        timestamp: expect.any(String),
      })
    })
  })

  it('handles upload errors', () => {
    const { result } = renderHook(() => useErrorHandler())

    const uploadError = {
      response: {
        status: 413,
      },
    }

    act(() => {
      const errorInfo = result.current.handleUploadError(uploadError)
      
      expect(errorInfo).toEqual({
        code: 'UPLOAD_ERROR',
        message: '文件大小超出限制',
        details: uploadError,
        timestamp: expect.any(String),
      })
    })
  })

  it('implements retry mechanism', async () => {
    const { result } = renderHook(() => useErrorHandler())

    let attemptCount = 0
    const failingOperation = jest.fn().mockImplementation(() => {
      attemptCount++
      if (attemptCount < 3) {
        throw new Error('Operation failed')
      }
      return 'success'
    })

    const resultValue = await act(async () => {
      return result.current.withRetry(failingOperation, 3, 100)
    })

    expect(resultValue).toBe('success')
    expect(failingOperation).toHaveBeenCalledTimes(3)
  })

  it('fails after max retries', async () => {
    const { result } = renderHook(() => useErrorHandler())

    const alwaysFailingOperation = jest.fn().mockRejectedValue(new Error('Always fails'))

    await act(async () => {
      await expect(
        result.current.withRetry(alwaysFailingOperation, 2, 100)
      ).rejects.toThrow('Always fails')
    })

    expect(alwaysFailingOperation).toHaveBeenCalledTimes(2)
  })

  it('disables notifications when configured', () => {
    const { result } = renderHook(() => 
      useErrorHandler({ showNotification: false })
    )

    const apiError = {
      response: {
        status: 500,
        data: { message: 'Server error' },
      },
    }

    act(() => {
      result.current.handleApiError(apiError)
    })

    // Should not show notification
    const SuccessNotification = require('@/components/Feedback/SuccessNotification').default
    expect(SuccessNotification.notify).not.toHaveBeenCalled()
  })

  it('handles different HTTP status codes correctly', () => {
    const { result } = renderHook(() => useErrorHandler())

    const testCases = [
      { status: 403, expectedMessage: '权限不足，无法访问' },
      { status: 404, expectedMessage: '请求的资源不存在' },
      { status: 422, expectedMessage: '数据验证失败' },
      { status: 429, expectedMessage: '请求过于频繁，请稍后重试' },
      { status: 500, expectedMessage: '服务器内部错误' },
      { status: 502, expectedMessage: '网关错误' },
      { status: 503, expectedMessage: '服务暂时不可用' },
      { status: 504, expectedMessage: '请求超时' },
    ]

    testCases.forEach(({ status, expectedMessage }) => {
      const error = {
        response: {
          status,
          data: {},
        },
      }

      act(() => {
        const errorInfo = result.current.handleApiError(error)
        expect(errorInfo.message).toBe(expectedMessage)
      })
    })
  })

  it('handles JavaScript errors', () => {
    const { result } = renderHook(() => useErrorHandler())

    const jsError = new Error('JavaScript error')

    act(() => {
      const errorInfo = result.current.handleApiError(jsError)
      
      expect(errorInfo).toEqual({
        code: 'CLIENT_ERROR',
        message: 'JavaScript error',
        details: jsError,
        timestamp: expect.any(String),
      })
    })
  })
})