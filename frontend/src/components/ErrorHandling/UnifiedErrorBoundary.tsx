/**
 * 统一错误边界组件
 * 整合React错误边界与统一错误处理系统
 */

import React, { Component, ErrorInfo, ReactNode } from 'react'
import { Result, Button } from 'antd'
import { ExclamationCircleOutlined, ReloadOutlined } from '@ant-design/icons'

import { unifiedErrorHandler, UnifiedError } from '@/services/unifiedErrorHandler'

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
  errorId: string | null
}

/**
 * 统一错误边界组件
 */
export class UnifiedErrorBoundary extends Component<Props, State> {
  private retryCount = 0
  private maxRetries = 3

  constructor(props: Props) {
    super(props)
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
      errorId: null
    }
  }

  static getDerivedStateFromError(error: Error): Partial<State> {
    return {
      hasError: true,
      error
    }
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    this.setState({
      errorInfo,
      errorId: this.generateErrorId()
    })

    // 使用统一错误处理器处理错误
    const unifiedError = unifiedErrorHandler.handleError(error, {
      showMessage: true,
      showNotification: true,
      customMessage: '页面渲染出错，请刷新页面重试',
      onError: (handledError) => {
        console.error('React Error Boundary caught an error:', {
          error,
          errorInfo,
          handledError,
          errorId: this.state.errorId
        })
      }
    })

    // 调用自定义错误处理回调
    if (this.props.onError) {
      this.props.onError(error, errorInfo)
    }

    // 上报错误到监控系统
    this.reportError(error, errorInfo)
  }

  private generateErrorId(): string {
    return `error_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
  }

  private reportError = (error: Error, errorInfo: ErrorInfo) => {
    // 这里可以集成错误监控系统
    try {
      // 示例：发送到错误监控服务
      const errorData = {
        errorId: this.state.errorId,
        message: error.message,
        stack: error.stack,
        componentStack: errorInfo.componentStack,
        timestamp: new Date().toISOString(),
        userAgent: navigator.userAgent,
        url: window.location.href,
        retryCount: this.retryCount
      }

      // 可以发送到Sentry、LogRocket等监控服务
      console.log('Error reported:', errorData)
    } catch (reportingError) {
      console.error('Failed to report error:', reportingError)
    }
  }

  private handleRetry = () => {
    if (this.retryCount < this.maxRetries) {
      this.retryCount++
      this.setState({
        hasError: false,
        error: null,
        errorInfo: null,
        errorId: null
      })
    } else {
      // 超过最大重试次数，刷新页面
      window.location.reload()
    }
  }

  private handleReload = () => {
    window.location.reload()
  }

  private handleGoHome = () => {
    window.location.href = '/'
  }

  render() {
    if (this.state.hasError) {
      // 如果提供了自定义fallback，使用它
      if (this.props.fallback) {
        return this.props.fallback
      }

      // 默认错误UI
      return (
        <div style={{
          padding: '50px',
          textAlign: 'center',
          minHeight: '100vh',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center',
          alignItems: 'center'
        }}>
          <Result
            status="error"
            icon={<ExclamationCircleOutlined />}
            title="页面渲染出错"
            subTitle={
              <div>
                <p>很抱歉，页面遇到了一些问题。</p>
                {this.state.errorId && (
                  <p style={{ fontSize: '12px', color: '#999' }}>
                    错误ID: {this.state.errorId}
                  </p>
                )}
                {this.props.showErrorDetails && this.state.error && (
                  <details style={{
                    marginTop: '20px',
                    textAlign: 'left',
                    background: '#f5f5f5',
                    padding: '10px',
                    borderRadius: '4px',
                    fontSize: '12px'
                  }}>
                    <summary>错误详情</summary>
                    <pre style={{ marginTop: '10px', whiteSpace: 'pre-wrap' }}>
                      {this.state.error.stack}
                    </pre>
                  </details>
                )}
              </div>
            }
            extra={[
              <Button
                key="retry"
                type="primary"
                icon={<ReloadOutlined />}
                onClick={this.handleRetry}
                disabled={this.retryCount >= this.maxRetries}
              >
                {this.retryCount < this.maxRetries ? '重试' : '重试次数已用完'}
              </Button>,
              <Button
                key="reload"
                onClick={this.handleReload}
              >
                刷新页面
              </Button>,
              <Button
                key="home"
                onClick={this.handleGoHome}
              >
                返回首页
              </Button>
            ]}
          />
        </div>
      )
    }

    return this.props.children
  }
}

/**
 * 高阶组件：为组件添加错误边界
 */
export function withErrorBoundary<P extends object>(
  Component: React.ComponentType<P>,
  errorBoundaryProps?: Omit<Props, 'children'>
) {
  const WrappedComponent = (props: P) => (
    <UnifiedErrorBoundary {...errorBoundaryProps}>
      <Component {...props} />
    </UnifiedErrorBoundary>
  )

  WrappedComponent.displayName = `withErrorBoundary(${Component.displayName || Component.name})`

  return WrappedComponent
}

/**
 * Hook: 使用错误边界
 */
export function useErrorBoundary() {
  const handleError = (error: Error, errorInfo?: ErrorInfo) => {
    unifiedErrorHandler.handleError(error, {
      showMessage: true,
      showNotification: true,
      onError: (handledError) => {
        console.error('Error caught by error boundary hook:', {
          error,
          errorInfo,
          handledError
        })
      }
    })
  }

  return { handleError }
}

/**
 * 错误恢复组件
 */
interface ErrorRecoveryProps {
  error: UnifiedError
  onRetry?: () => void
  onDismiss?: () => void
}

export function ErrorRecovery({ error, onRetry, onDismiss }: ErrorRecoveryProps) {
  const handleRetry = () => {
    if (onRetry) {
      onRetry()
    }
  }

  const handleDismiss = () => {
    if (onDismiss) {
      onDismiss()
    }
  }

  const getRecoveryActions = () => {
    switch (error.type) {
      case 'NETWORK_ERROR':
        return (
          <>
            <Button type="primary" onClick={handleRetry}>
              重新连接
            </Button>
            <Button onClick={() => window.location.reload()}>
              刷新页面
            </Button>
          </>
        )

      case 'AUTHENTICATION_ERROR':
        return (
          <>
            <Button type="primary" onClick={() => window.location.href = '/login'}>
              重新登录
            </Button>
            <Button onClick={handleDismiss}>
              稍后重试
            </Button>
          </>
        )

      case 'VALIDATION_ERROR':
        return (
          <Button type="primary" onClick={handleDismiss}>
            检查输入
          </Button>
        )

      default:
        return (
          <>
            <Button type="primary" onClick={handleRetry}>
              重试
            </Button>
            <Button onClick={() => window.location.reload()}>
              刷新页面
            </Button>
          </>
        )
    }
  }

  return (
    <div style={{
      padding: '20px',
      border: '1px solid #ff4d4f',
      borderRadius: '6px',
      backgroundColor: '#fff2f0',
      margin: '10px 0'
    }}>
      <div style={{ marginBottom: '15px' }}>
        <strong>错误提示:</strong> {error.message}
      </div>

      {error.details && (
        <div style={{ marginBottom: '15px', fontSize: '12px', color: '#666' }}>
          {typeof error.details === 'string' ? error.details : JSON.stringify(error.details)}
        </div>
      )}

      <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end' }}>
        {getRecoveryActions()}
      </div>
    </div>
  )
}

export default UnifiedErrorBoundary
