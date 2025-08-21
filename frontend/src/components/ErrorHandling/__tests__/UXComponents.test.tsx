import React from 'react'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi, beforeEach } from 'vitest'

import { GlobalErrorBoundary, ErrorPage, UXProvider } from '@/components/ErrorHandling'
import { LoadingSpinner, SkeletonLoader } from '@/components/Loading'
import { 
  EmptyState, 
  ConfirmDialog, 
  ProgressIndicator, 
  ActionFeedback 
} from '@/components/Feedback'

// Mock console.error to avoid noise in tests
const originalError = console.error
beforeEach(() => {
  console.error = vi.fn()
})

afterEach(() => {
  console.error = originalError
})

// Test component that throws an error
const ErrorThrowingComponent: React.FC<{ shouldThrow: boolean }> = ({ shouldThrow }) => {
  if (shouldThrow) {
    throw new Error('Test error')
  }
  return <div>No error</div>
}

describe('UX Components', () => {
  describe('GlobalErrorBoundary', () => {
    it('renders children when there is no error', () => {
      render(
        <GlobalErrorBoundary>
          <div>Test content</div>
        </GlobalErrorBoundary>
      )

      expect(screen.getByText('Test content')).toBeInTheDocument()
    })

    it('renders error UI when child component throws', () => {
      render(
        <GlobalErrorBoundary>
          <ErrorThrowingComponent shouldThrow={true} />
        </GlobalErrorBoundary>
      )

      expect(screen.getByText('页面出现错误')).toBeInTheDocument()
      expect(screen.getByText('刷新页面')).toBeInTheDocument()
    })

    it('calls onError callback when error occurs', () => {
      const onError = vi.fn()
      
      render(
        <GlobalErrorBoundary onError={onError}>
          <ErrorThrowingComponent shouldThrow={true} />
        </GlobalErrorBoundary>
      )

      expect(onError).toHaveBeenCalledWith(
        expect.any(Error),
        expect.objectContaining({
          componentStack: expect.any(String)
        })
      )
    })

    it('renders custom fallback when provided', () => {
      const customFallback = <div>Custom error message</div>
      
      render(
        <GlobalErrorBoundary fallback={customFallback}>
          <ErrorThrowingComponent shouldThrow={true} />
        </GlobalErrorBoundary>
      )

      expect(screen.getByText('Custom error message')).toBeInTheDocument()
    })
  })

  describe('ErrorPage', () => {
    it('renders 404 error page correctly', () => {
      render(<ErrorPage type="404" />)

      expect(screen.getByText('页面不存在')).toBeInTheDocument()
      expect(screen.getByText('抱歉，您访问的页面不存在或已被删除。')).toBeInTheDocument()
    })

    it('renders 403 error page correctly', () => {
      render(<ErrorPage type="403" />)

      expect(screen.getByText('访问被拒绝')).toBeInTheDocument()
      expect(screen.getByText('抱歉，您没有权限访问此页面。')).toBeInTheDocument()
    })

    it('renders 500 error page correctly', () => {
      render(<ErrorPage type="500" />)

      expect(screen.getByText('服务器错误')).toBeInTheDocument()
      expect(screen.getByText('抱歉，服务器出现了一些问题，请稍后重试。')).toBeInTheDocument()
    })

    it('renders network error page correctly', () => {
      render(<ErrorPage type="network" />)

      expect(screen.getByText('网络连接失败')).toBeInTheDocument()
      expect(screen.getByText('请检查您的网络连接，然后重试。')).toBeInTheDocument()
    })

    it('calls action callbacks when buttons are clicked', async () => {
      const user = userEvent.setup()
      const onBack = vi.fn()
      const onHome = vi.fn()
      const onReload = vi.fn()

      render(
        <ErrorPage 
          type="404" 
          onBack={onBack}
          onHome={onHome}
          onReload={onReload}
          showReloadButton={true}
        />
      )

      await user.click(screen.getByText('返回上页'))
      expect(onBack).toHaveBeenCalled()

      await user.click(screen.getByText('返回首页'))
      expect(onHome).toHaveBeenCalled()

      await user.click(screen.getByText('重新加载'))
      expect(onReload).toHaveBeenCalled()
    })
  })

  describe('LoadingSpinner', () => {
    it('renders loading spinner when spinning is true', () => {
      render(<LoadingSpinner spinning={true} tip="Loading..." />)

      expect(screen.getByText('Loading...')).toBeInTheDocument()
    })

    it('renders children when spinning is false', () => {
      render(
        <LoadingSpinner spinning={false}>
          <div>Content loaded</div>
        </LoadingSpinner>
      )

      expect(screen.getByText('Content loaded')).toBeInTheDocument()
    })

    it('shows loading tip with different sizes', () => {
      const { rerender } = render(<LoadingSpinner size="small" tip="Small loading" />)
      expect(screen.getByText('Small loading')).toBeInTheDocument()

      rerender(<LoadingSpinner size="large" tip="Large loading" />)
      expect(screen.getByText('Large loading')).toBeInTheDocument()
    })
  })

  describe('SkeletonLoader', () => {
    it('renders skeleton when loading is true', () => {
      render(<SkeletonLoader type="list" loading={true} />)
      
      // Skeleton should be present (Ant Design skeleton components)
      expect(document.querySelector('.ant-skeleton')).toBeInTheDocument()
    })

    it('renders children when loading is false', () => {
      render(
        <SkeletonLoader type="list" loading={false}>
          <div>Actual content</div>
        </SkeletonLoader>
      )

      expect(screen.getByText('Actual content')).toBeInTheDocument()
    })

    it('renders different skeleton types', () => {
      const { rerender } = render(<SkeletonLoader type="card" loading={true} />)
      expect(document.querySelector('.ant-skeleton')).toBeInTheDocument()

      rerender(<SkeletonLoader type="form" loading={true} />)
      expect(document.querySelector('.ant-skeleton')).toBeInTheDocument()

      rerender(<SkeletonLoader type="table" loading={true} />)
      expect(document.querySelector('.ant-skeleton')).toBeInTheDocument()
    })
  })

  describe('EmptyState', () => {
    it('renders no-data state correctly', () => {
      render(<EmptyState type="no-data" />)

      expect(screen.getByText('暂无数据')).toBeInTheDocument()
      expect(screen.getByText('还没有任何数据，点击下方按钮开始添加')).toBeInTheDocument()
    })

    it('renders no-search-results state correctly', () => {
      render(<EmptyState type="no-search-results" />)

      expect(screen.getByText('无搜索结果')).toBeInTheDocument()
      expect(screen.getByText('没有找到符合条件的数据，请尝试其他关键词')).toBeInTheDocument()
    })

    it('calls action callbacks when buttons are clicked', async () => {
      const user = userEvent.setup()
      const onCreate = vi.fn()
      const onRefresh = vi.fn()

      render(
        <EmptyState 
          type="no-data"
          showCreateButton={true}
          showRefreshButton={true}
          onCreateClick={onCreate}
          onRefreshClick={onRefresh}
        />
      )

      await user.click(screen.getByText('新增数据'))
      expect(onCreate).toHaveBeenCalled()

      await user.click(screen.getByText('刷新'))
      expect(onRefresh).toHaveBeenCalled()
    })
  })

  describe('ConfirmDialog', () => {
    it('renders delete confirmation dialog', () => {
      render(
        <ConfirmDialog 
          type="delete"
          visible={true}
          itemName="测试项目"
        />
      )

      expect(screen.getByText('确认删除')).toBeInTheDocument()
      expect(screen.getByText(/确定要删除"测试项目"吗？/)).toBeInTheDocument()
    })

    it('calls confirm and cancel callbacks', async () => {
      const user = userEvent.setup()
      const onConfirm = vi.fn()
      const onCancel = vi.fn()

      render(
        <ConfirmDialog 
          type="delete"
          visible={true}
          onConfirm={onConfirm}
          onCancel={onCancel}
        />
      )

      await user.click(screen.getByText('删除'))
      expect(onConfirm).toHaveBeenCalled()

      // Re-render to test cancel
      render(
        <ConfirmDialog 
          type="delete"
          visible={true}
          onConfirm={onConfirm}
          onCancel={onCancel}
        />
      )

      await user.click(screen.getByText('取消'))
      expect(onCancel).toHaveBeenCalled()
    })
  })

  describe('ProgressIndicator', () => {
    it('renders line progress correctly', () => {
      render(
        <ProgressIndicator 
          type="line"
          percent={50}
          title="Test Progress"
          description="50% complete"
        />
      )

      expect(screen.getByText('Test Progress')).toBeInTheDocument()
      expect(screen.getByText('50% complete')).toBeInTheDocument()
    })

    it('renders circle progress correctly', () => {
      render(
        <ProgressIndicator 
          type="circle"
          percent={75}
          status="success"
        />
      )

      // Circle progress should be rendered
      expect(document.querySelector('.ant-progress-circle')).toBeInTheDocument()
    })

    it('renders steps progress correctly', () => {
      const steps = [
        { title: 'Step 1', status: 'finish' as const },
        { title: 'Step 2', status: 'process' as const },
        { title: 'Step 3', status: 'wait' as const },
      ]

      render(
        <ProgressIndicator 
          type="steps"
          steps={steps}
          current={1}
        />
      )

      expect(screen.getByText('Step 1')).toBeInTheDocument()
      expect(screen.getByText('Step 2')).toBeInTheDocument()
      expect(screen.getByText('Step 3')).toBeInTheDocument()
    })
  })

  describe('ActionFeedback', () => {
    it('renders loading feedback correctly', () => {
      render(
        <ActionFeedback 
          result={{
            status: 'loading',
            message: 'Processing...'
          }}
        />
      )

      expect(screen.getByText('处理中...')).toBeInTheDocument()
      expect(screen.getByText('Processing...')).toBeInTheDocument()
    })

    it('renders success feedback correctly', () => {
      render(
        <ActionFeedback 
          result={{
            status: 'success',
            message: 'Operation completed successfully'
          }}
        />
      )

      expect(screen.getByText('操作成功')).toBeInTheDocument()
      expect(screen.getByText('Operation completed successfully')).toBeInTheDocument()
    })

    it('renders error feedback with retry button', async () => {
      const user = userEvent.setup()
      const onRetry = vi.fn()

      render(
        <ActionFeedback 
          result={{
            status: 'error',
            message: 'Operation failed'
          }}
          onRetry={onRetry}
        />
      )

      expect(screen.getByText('操作失败')).toBeInTheDocument()
      expect(screen.getByText('Operation failed')).toBeInTheDocument()

      await user.click(screen.getByText('重试'))
      expect(onRetry).toHaveBeenCalled()
    })

    it('auto-hides success feedback after delay', async () => {
      const onClose = vi.fn()

      render(
        <ActionFeedback 
          result={{
            status: 'success',
            message: 'Success message'
          }}
          autoHide={true}
          autoHideDelay={100}
          onClose={onClose}
        />
      )

      expect(screen.getByText('Success message')).toBeInTheDocument()

      await waitFor(() => {
        expect(onClose).toHaveBeenCalled()
      }, { timeout: 200 })
    })
  })

  describe('UXProvider', () => {
    it('renders children with error boundary protection', () => {
      render(
        <UXProvider>
          <div>Test app content</div>
        </UXProvider>
      )

      expect(screen.getByText('Test app content')).toBeInTheDocument()
    })

    it('catches errors in child components', () => {
      render(
        <UXProvider>
          <ErrorThrowingComponent shouldThrow={true} />
        </UXProvider>
      )

      expect(screen.getByText('页面出现错误')).toBeInTheDocument()
    })

    it('applies custom theme configuration', () => {
      const config = {
        theme: {
          primaryColor: '#ff0000',
          borderRadius: 10,
        }
      }

      render(
        <UXProvider config={config}>
          <div>Themed content</div>
        </UXProvider>
      )

      expect(screen.getByText('Themed content')).toBeInTheDocument()
    })
  })
})