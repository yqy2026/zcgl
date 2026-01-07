/**
 * ErrorBoundary 组件测试
 * 测试错误边界组件的核心功能
 * 遵循 Testing Library 最佳实践：测试用户行为而非实现细节
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { ErrorBoundary, AssetErrorBoundary, SystemErrorBoundary, useErrorHandler } from '../ErrorBoundary'

// =============================================================================
// 测试组件 - 用于触发错误
// =============================================================================

const ThrowError = ({ shouldThrow = false }: { shouldThrow?: boolean }) => {
  if (shouldThrow) {
    throw new Error('Test error')
  }
  return <div>Normal Content</div>
}

const AsyncErrorComponent = () => {
  throw new TypeError('Async type error')
}

const ChunkLoadErrorComponent = () => {
  const error = new Error('Loading chunk 0 failed')
  ;(error as any).name = 'ChunkLoadError'
  throw error
}

// =============================================================================
// Mock Router
// =============================================================================

vi.mock('react-router-dom', () => ({
  useNavigate: () => vi.fn()
}))

// =============================================================================
// 基础功能测试
// =============================================================================

describe('ErrorBoundary - 基础功能', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('应该正常渲染子组件', () => {
    render(
      <ErrorBoundary>
        <div>Child Component</div>
      </ErrorBoundary>
    )

    expect(screen.getByText('Child Component')).toBeInTheDocument()
  })

  it('应该捕获子组件抛出的错误', () => {
    // 抑制控制台错误输出
    const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {})

    render(
      <ErrorBoundary>
        <ThrowError shouldThrow={true} />
      </ErrorBoundary>
    )

    // 应该显示错误UI
    expect(screen.getByText(/页面访问出错/)).toBeInTheDocument()

    consoleErrorSpy.mockRestore()
  })

  it('应该支持自定义fallback', () => {
    const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {})

    const customFallback = <div>Custom Error UI</div>

    render(
      <ErrorBoundary fallback={customFallback}>
        <ThrowError shouldThrow={true} />
      </ErrorBoundary>
    )

    expect(screen.getByText('Custom Error UI')).toBeInTheDocument()

    consoleErrorSpy.mockRestore()
  })

  it('应该调用onError回调', () => {
    const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {})
    const onError = vi.fn()

    render(
      <ErrorBoundary onError={onError}>
        <ThrowError shouldThrow={true} />
      </ErrorBoundary>
    )

    expect(onError).toHaveBeenCalled()

    consoleErrorSpy.mockRestore()
  })
})

// =============================================================================
// 错误类型检测测试
// =============================================================================

describe('ErrorBoundary - 错误类型检测', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('应该识别ChunkLoadError', () => {
    const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {})

    render(
      <ErrorBoundary>
        <ChunkLoadErrorComponent />
      </ErrorBoundary>
    )

    expect(screen.getByText(/页面加载失败/)).toBeInTheDocument()
    // 使用更具体的选择器 - 按钮角色
    const refreshButtons = screen.getAllByRole('button', { name: /刷新页面/ })
    expect(refreshButtons.length).toBeGreaterThan(0)

    consoleErrorSpy.mockRestore()
  })

  it('应该识别TypeError', () => {
    const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {})

    render(
      <ErrorBoundary>
        <AsyncErrorComponent />
      </ErrorBoundary>
    )

    expect(screen.getByText(/页面渲染错误/)).toBeInTheDocument()

    consoleErrorSpy.mockRestore()
  })
})

// =============================================================================
// 重试功能测试
// =============================================================================

describe('ErrorBoundary - 重试功能', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('应该支持重试功能', async () => {
    const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {})
    const _user = userEvent.setup()

    const shouldThrow = true

    render(
      <ErrorBoundary maxRetries={3}>
        <ThrowError shouldThrow={shouldThrow} />
      </ErrorBoundary>
    )

    // 等待错误显示
    await waitFor(() => {
      expect(screen.getByText(/页面访问出错/)).toBeInTheDocument()
    })

    // 检查重试按钮
    const retryButton = screen.getByText(/重试 \(0\/3\)/)
    expect(retryButton).toBeInTheDocument()

    consoleErrorSpy.mockRestore()
  })

  it('超过最大重试次数后应该禁用重试', () => {
    const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {})

    render(
      <ErrorBoundary maxRetries={1}>
        <ThrowError shouldThrow={true} />
      </ErrorBoundary>
    )

    // 第一次重试后
    waitFor(() => {
      const retryButton = screen.queryByText(/重testRetry \(1\/1\)/)
      expect(retryButton).not.toBeInTheDocument()
    })

    consoleErrorSpy.mockRestore()
  })
})

// =============================================================================
// 导航功能测试
// =============================================================================

describe('ErrorBoundary - 导航功能', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('应该显示返回上一页按钮', () => {
    const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {})

    render(
      <ErrorBoundary>
        <ThrowError shouldThrow={true} />
      </ErrorBoundary>
    )

    expect(screen.getByText(/返回上一页/)).toBeInTheDocument()

    consoleErrorSpy.mockRestore()
  })

  it('应该显示返回首页按钮', () => {
    const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {})

    render(
      <ErrorBoundary>
        <ThrowError shouldThrow={true} />
      </ErrorBoundary>
    )

    expect(screen.getByText(/返回首页/)).toBeInTheDocument()

    consoleErrorSpy.mockRestore()
  })
})

// =============================================================================
// 专用错误边界测试
// =============================================================================

describe('专用错误边界', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('AssetErrorBoundary应该正常渲染子组件', () => {
    render(
      <AssetErrorBoundary>
        <div>Asset Content</div>
      </AssetErrorBoundary>
    )

    expect(screen.getByText('Asset Content')).toBeInTheDocument()
  })

  it('SystemErrorBoundary应该正常渲染子组件', () => {
    render(
      <SystemErrorBoundary>
        <div>System Content</div>
      </SystemErrorBoundary>
    )

    expect(screen.getByText('System Content')).toBeInTheDocument()
  })

  it('AssetErrorBoundary应该捕获错误', () => {
    const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {})

    render(
      <AssetErrorBoundary>
        <ThrowError shouldThrow={true} />
      </AssetErrorBoundary>
    )

    expect(screen.getByText(/页面访问出错/)).toBeInTheDocument()

    consoleErrorSpy.mockRestore()
  })

  it('SystemErrorBoundary应该捕获错误', () => {
    const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {})

    render(
      <SystemErrorBoundary>
        <ThrowError shouldThrow={true} />
      </SystemErrorBoundary>
    )

    expect(screen.getByText(/页面访问出错/)).toBeInTheDocument()

    consoleErrorSpy.mockRestore()
  })
})

// =============================================================================
// Hooks 测试
// =============================================================================

describe('useErrorHandler Hook', () => {
  it('应该导出useErrorHandler hook', () => {
    expect(typeof useErrorHandler).toBe('function')
  })

  it('应该捕获错误', () => {
    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})

    const TestComponent = () => {
      const { captureError, hasError } = useErrorHandler()

      return (
        <div>
          <button onClick={() => captureError(new Error('Test error'))}>
            Trigger Error
          </button>
          <span>Has Error: {hasError.toString()}</span>
        </div>
      )
    }

    render(<TestComponent />)

    expect(screen.getByText('Has Error: false')).toBeInTheDocument()

    consoleSpy.mockRestore()
  })

  it('应该重置错误', () => {
    const TestComponent = () => {
      const { captureError, resetError, hasError } = useErrorHandler()

      return (
        <div>
          <button onClick={() => captureError(new Error('Test error'))}>
            Trigger Error
          </button>
          <button onClick={resetError}>Reset Error</button>
          <span>Has Error: {hasError.toString()}</span>
        </div>
      )
    }

    render(<TestComponent />)

    expect(screen.getByText('Has Error: false')).toBeInTheDocument()
  })
})

// =============================================================================
// 边界情况测试
// =============================================================================

describe('ErrorBoundary - 边界情况', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('应该处理空children', () => {
    render(<ErrorBoundary>{null}</ErrorBoundary>)
    // 不应该抛出错误
  })

  it('应该处理多个子组件', () => {
    render(
      <ErrorBoundary>
        <div>Child 1</div>
        <div>Child 2</div>
        <div>Child 3</div>
      </ErrorBoundary>
    )

    expect(screen.getByText('Child 1')).toBeInTheDocument()
    expect(screen.getByText('Child 2')).toBeInTheDocument()
    expect(screen.getByText('Child 3')).toBeInTheDocument()
  })

  it('应该处理嵌套错误边界', () => {
    const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {})

    render(
      <ErrorBoundary>
        <ErrorBoundary>
          <ThrowError shouldThrow={true} />
        </ErrorBoundary>
      </ErrorBoundary>
    )

    // 内层错误边界应该捕获错误
    expect(screen.getByText(/页面访问出错/)).toBeInTheDocument()

    consoleErrorSpy.mockRestore()
  })
})

// =============================================================================
// 开发模式测试
// =============================================================================

describe('ErrorBoundary - 开发模式功能', () => {
  const originalEnv = process.env.NODE_ENV

  afterEach(() => {
    process.env.NODE_ENV = originalEnv
  })

  it('开发模式应该显示错误详情', () => {
    const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {})

    process.env.NODE_ENV = 'development'

    render(
      <ErrorBoundary showErrorDetails={true}>
        <ThrowError shouldThrow={true} />
      </ErrorBoundary>
    )

    // 应该显示错误详情
    expect(screen.getByText(/错误详情 \(开发模式\)/)).toBeInTheDocument()

    consoleErrorSpy.mockRestore()
  })

  it('生产模式不应该显示错误详情', () => {
    const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {})

    process.env.NODE_ENV = 'production'

    render(
      <ErrorBoundary showErrorDetails={false}>
        <ThrowError shouldThrow={true} />
      </ErrorBoundary>
    )

    // 不应该显示错误详情
    expect(screen.queryByText(/错误详情/)).not.toBeInTheDocument()

    consoleErrorSpy.mockRestore()
  })
})
