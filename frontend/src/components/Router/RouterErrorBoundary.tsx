import React, { Component, ErrorInfo, ReactNode } from 'react'
import { Result, Button, Typography, Alert, Space } from 'antd'
import { useNavigate } from 'react-router-dom'

const { Title, Paragraph, Text } = Typography

interface RouterErrorBoundaryState {
  hasError: boolean
  error: Error | null
  errorInfo: ErrorInfo | null
  retryCount: number
}

interface RouterErrorBoundaryProps {
  children: ReactNode
  fallback?: ReactNode
  onError?: (error: Error, errorInfo: ErrorInfo) => void
  maxRetries?: number
  showErrorDetails?: boolean
}

interface ErrorReport {
  error: string
  stack: string
  componentStack: string
  timestamp: string
  userAgent: string
  url: string
  retryCount: number
}

class RouterErrorBoundaryComponent extends Component<RouterErrorBoundaryProps, RouterErrorBoundaryState> {
  private maxRetries: number

  constructor(props: RouterErrorBoundaryProps) {
    super(props)

    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
      retryCount: 0
    }

    this.maxRetries = props.maxRetries || 3
  }

  static getDerivedStateFromError(error: Error): Partial<RouterErrorBoundaryState> {
    return {
      hasError: true,
      error
    }
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    this.setState({
      error,
      errorInfo
    })

    // 报告错误
    this.reportError(error, errorInfo)

    // 调用错误回调
    if (this.props.onError) {
      this.props.onError(error, errorInfo)
    }

    console.error('路由错误边界捕获到错误:', error, errorInfo)
  }

  private reportError = (error: Error, errorInfo: ErrorInfo) => {
    const errorReport: ErrorReport = {
      error: error.message,
      stack: error.stack || '',
      componentStack: errorInfo.componentStack,
      timestamp: new Date().toISOString(),
      userAgent: navigator.userAgent,
      url: window.location.href,
      retryCount: this.state.retryCount
    }

    // 发送错误报告到监控服务
    this.sendErrorReport(errorReport)
  }

  private sendErrorReport = async (errorReport: ErrorReport) => {
    try {
      // 这里可以集成错误监控服务，如 Sentry
      if (process.env.NODE_ENV === 'production') {
        // 发送到错误监控服务
        await fetch('/api/errors/report', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify(errorReport)
        })
      } else {
        // 开发环境打印到控制台
        console.group('🚨 路由错误报告')
        console.error('错误:', errorReport)
        console.groupEnd()
      }
    } catch (reportingError) {
      console.warn('错误报告发送失败:', reportingError)
    }
  }

  private handleRetry = () => {
    if (this.state.retryCount < this.maxRetries) {
      this.setState(prevState => ({
        hasError: false,
        error: null,
        errorInfo: null,
        retryCount: prevState.retryCount + 1
      }))
    }
  }

  private handleGoHome = () => {
    // 重置状态并导航到首页
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null,
      retryCount: 0
    })
    window.location.href = '/dashboard'
  }

  private canRetry = () => {
    return this.state.retryCount < this.maxRetries
  }

  render() {
    if (this.state.hasError) {
      // 如果提供了自定义fallback，使用它
      if (this.props.fallback) {
        return this.props.fallback
      }

      return (
        <RouterErrorHandler
          error={this.state.error}
          errorInfo={this.state.errorInfo}
          onRetry={this.handleRetry}
          onGoHome={this.handleGoHome}
          canRetry={this.canRetry()}
          retryCount={this.state.retryCount}
          maxRetries={this.maxRetries}
          showErrorDetails={this.props.showErrorDetails}
        />
      )
    }

    return this.props.children
  }
}

interface RouterErrorHandlerProps {
  error: Error | null
  errorInfo: ErrorInfo | null
  onRetry: () => void
  onGoHome: () => void
  canRetry: boolean
  retryCount: number
  maxRetries: number
  showErrorDetails?: boolean
}

const RouterErrorHandler: React.FC<RouterErrorHandlerProps> = ({
  error,
  errorInfo,
  onRetry,
  onGoHome,
  canRetry,
  retryCount,
  maxRetries,
  showErrorDetails = process.env.NODE_ENV === 'development'
}) => {
  const navigate = useNavigate()

  const handleGoBack = () => {
    navigate(-1)
  }

  const getErrorType = (error: Error | null) => {
    if (!error) return 'unknown'

    if (error.name === 'ChunkLoadError') return 'chunk_load'
    if (error.name === 'TypeError') return 'type_error'
    if (error.name === 'NetworkError') return 'network'
    if (error.message.includes('Loading chunk')) return 'chunk_load'

    return 'runtime'
  }

  const errorType = getErrorType(error)
  const isChunkLoadError = errorType === 'chunk_load'

  const getErrorTitle = () => {
    if (isChunkLoadError) return '页面加载失败'
    if (errorType === 'network') return '网络连接错误'
    if (errorType === 'type_error') return '页面渲染错误'
    return '页面访问出错'
  }

  const getErrorDescription = () => {
    if (isChunkLoadError) {
      return '页面资源加载失败，可能是网络问题或应用版本更新。请尝试刷新页面。'
    }
    if (errorType === 'network') {
      return '网络连接异常，请检查网络连接后重试。'
    }
    if (errorType === 'type_error') {
      return '页面渲染时发生错误，这可能是临时的技术问题。'
    }
    return '访问页面时遇到了意外错误，我们正在努力修复。'
  }

  return (
    <div style={{
      padding: '50px',
      maxWidth: '800px',
      margin: '0 auto',
      minHeight: '60vh',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center'
    }}>
      <Result
        status="error"
        title={getErrorTitle()}
        subTitle={getErrorDescription()}
        extra={[
          <Space key="actions" direction="vertical" size="middle">
            <Space>
              {canRetry && (
                <Button type="primary" onClick={onRetry}>
                  重试 ({retryCount}/{maxRetries})
                </Button>
              )}
              <Button onClick={handleGoBack}>
                返回上一页
              </Button>
              <Button onClick={onGoHome}>
                返回首页
              </Button>
              {isChunkLoadError && (
                <Button onClick={() => window.location.reload()}>
                  刷新页面
                </Button>
              )}
            </Space>

            {isChunkLoadError && (
              <Alert
                message="提示"
                description="如果您经常遇到此错误，请尝试清除浏览器缓存或联系技术支持。"
                type="info"
                showIcon
              />
            )}
          </Space>
        ]}
      />

      {showErrorDetails && error && (
        <div style={{
          marginTop: '30px',
          padding: '20px',
          background: '#f5f5f5',
          borderRadius: '6px',
          fontSize: '12px',
          fontFamily: 'monospace'
        }}>
          <Title level={5}>错误详情 (开发模式)</Title>
          <Paragraph>
            <Text strong>错误类型:</Text> {errorType}<br/>
            <Text strong>错误消息:</Text> {error.message}<br/>
            <Text strong>重试次数:</Text> {retryCount}/{maxRetries}
          </Paragraph>

          {error.stack && (
            <details style={{ marginTop: '10px' }}>
              <summary>错误堆栈</summary>
              <pre style={{
                marginTop: '10px',
                fontSize: '11px',
                whiteSpace: 'pre-wrap',
                wordBreak: 'break-word'
              }}>
                {error.stack}
              </pre>
            </details>
          )}

          {errorInfo?.componentStack && (
            <details style={{ marginTop: '10px' }}>
              <summary>组件堆栈</summary>
              <pre style={{
                marginTop: '10px',
                fontSize: '11px',
                whiteSpace: 'pre-wrap',
                wordBreak: 'break-word'
              }}>
                {errorInfo.componentStack}
              </pre>
            </details>
          )}
        </div>
      )}
    </div>
  )
}

// Hook版本的错误边界
export const useRouterErrorBoundary = () => {
  const navigate = useNavigate()

  const handleError = useCallback((error: Error, fallbackPath: string = '/dashboard') => {
    console.error('路由错误:', error)

    // 根据错误类型决定处理方式
    if (error.name === 'ChunkLoadError') {
      // 资源加载错误，刷新页面
      window.location.reload()
    } else {
      // 其他错误，导航到安全页面
      navigate(fallbackPath)
    }
  }, [navigate])

  return { handleError }
}

// 预定义的错误边界组件
export const RouterErrorBoundary: React.FC<RouterErrorBoundaryProps> = (props) => {
  return <RouterErrorBoundaryComponent {...props} />
}

// 为特定模块定制的错误边界
export const AssetRouterErrorBoundary: React.FC<{ children: ReactNode }> = ({ children }) => {
  return (
    <RouterErrorBoundary
      maxRetries={2}
      onError={(error) => {
        console.error('资产管理模块错误:', error)
      }}
    >
      {children}
    </RouterErrorBoundary>
  )
}

export const SystemRouterErrorBoundary: React.FC<{ children: ReactNode }> = ({ children }) => {
  return (
    <RouterErrorBoundary
      maxRetries={1}
      onError={(error) => {
        console.error('系统管理模块错误:', error)
      }}
    >
      {children}
    </RouterErrorBoundary>
  )
}

export default RouterErrorBoundary