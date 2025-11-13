/**
 * 通用错误边界组件
 * 捕获React组件树中的错误并显示友好的错误页面
 */

import React, { Component, ReactNode, ErrorInfo } from 'react'
import { Result, Button } from 'antd'

interface Props {
  children: ReactNode
  fallback?: ReactNode
  onError?: (error: Error, errorInfo: ErrorInfo) => void
  showErrorDetails?: boolean
}

interface State {
  hasError: boolean
  error: Error | null
  errorInfo: ErrorInfo | null
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props)
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
    }
  }

  static getDerivedStateFromError(error: Error): Partial<State> {
    return {
      hasError: true,
      error,
    }
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    this.setState({
      error,
      errorInfo,
    })

    // 调用错误处理回调
    if (this.props.onError) {
      this.props.onError(error, errorInfo)
    }

    // 开发环境下打印错误详情
    if (process.env.NODE_ENV === 'development') {
      console.error('ErrorBoundary caught an error:', error, errorInfo)
    }

    // 生产环境下上报错误
    if (process.env.NODE_ENV === 'production') {
      this.reportError(error, errorInfo)
    }
  }

  /**
   * 上报错误到监控系统
   */
  private reportError(error: Error, errorInfo: ErrorInfo): void {
    try {
      const errorData = {
        message: error.message,
        stack: error.stack,
        componentStack: errorInfo.componentStack,
        timestamp: new Date().toISOString(),
        userAgent: navigator.userAgent,
        url: window.location.href,
      }

      // 这里可以集成错误监控服务，如Sentry、LogRocket等
      // errorMonitoringService.captureException(error, { extra: errorData })

      console.warn('Error reported:', errorData)
    } catch (reportError) {
      console.error('Failed to report error:', reportError)
    }
  }

  /**
   * 重置错误状态
   */
  private handleReset = (): void => {
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null,
    })
  }

  /**
   * 重新加载页面
   */
  private handleReload = (): void => {
    window.location.reload()
  }

  render(): ReactNode {
    if (this.state.hasError) {
      // 如果有自定义fallback，使用它
      if (this.props.fallback) {
        return this.props.fallback
      }

      // 默认错误页面
      return (
        <div style={{ padding: '50px', textAlign: 'center' }}>
          <Result
            status="500"
            title="500"
            subTitle="抱歉，页面出现了错误。"
            extra={[
              <Button type="primary" key="retry" onClick={this.handleReset}>
                重试
              </Button>,
              <Button key="reload" onClick={this.handleReload}>
                刷新页面
              </Button>,
            ]}
          >

            {/* 开发环境显示错误详情 */}
            {process.env.NODE_ENV === 'development' && this.props.showErrorDetails && (
              <details style={{
                marginTop: '20px',
                textAlign: 'left',
                whiteSpace: 'pre-wrap',
                background: '#f5f5f5',
                padding: '16px',
                borderRadius: '4px',
                border: '1px solid #d9d9d9'
              }}>
                <summary>错误详情（仅开发环境可见）</summary>
                <h4>错误信息:</h4>
                <p>{this.state.error?.toString()}</p>

                <h4>组件堆栈:</h4>
                <pre>{this.state.errorInfo?.componentStack}</pre>

                <h4>错误堆栈:</h4>
                <pre>{this.state.error?.stack}</pre>
              </details>
            )}
          </Result>
        </div>
      )
    }

    return this.props.children
  }
}

// 便捷的错误边界Hook
export const useErrorHandler = () => {
  const [error, setError] = React.useState<Error | null>(null)

  const resetError = React.useCallback(() => {
    setError(null)
  }, [])

  const captureError = React.useCallback((error: Error) => {
    console.error('Error captured by useErrorHandler:', error)
    setError(error)

    // 生产环境下上报错误
    if (process.env.NODE_ENV === 'production') {
      // errorMonitoringService.captureException(error)
    }
  }, [])

  return {
    error,
    captureError,
    resetError,
    hasError: !!error,
  }
}

export default ErrorBoundary