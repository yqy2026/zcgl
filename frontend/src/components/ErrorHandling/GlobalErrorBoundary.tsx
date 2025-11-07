import React, { Component, ErrorInfo, ReactNode } from 'react'
import { Result, Button, Typography, Card, Space, Alert } from 'antd'
import {
  ExclamationCircleOutlined,
  ReloadOutlined,
  HomeOutlined,
  BugOutlined,
} from '@ant-design/icons'

const { Paragraph, Text } = Typography

interface Props {
  children: ReactNode
  fallback?: ReactNode
  onError?: (error: Error, errorInfo: ErrorInfo) => void
}

interface State {
  hasError: boolean
  error?: Error
  errorInfo?: ErrorInfo
  errorId?: string
}

class GlobalErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
  }

  public static getDerivedStateFromError(error: Error): State {
    // 生成错误ID用于追踪
    const errorId = `ERR_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
    
    return {
      hasError: true,
      error,
      errorId,
    }
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('GlobalErrorBoundary caught an error:', error, errorInfo)
    
    this.setState({
      errorInfo,
    })

    // 调用外部错误处理函数
    if (this.props.onError) {
      this.props.onError(error, errorInfo)
    }

    // 发送错误报告到监控服务
    this.reportError(error, errorInfo)
  }

  private reportError = (error: Error, errorInfo: ErrorInfo) => {
    // 这里可以集成错误监控服务，如 Sentry
    const errorReport = {
      message: error.message,
      stack: error.stack,
      componentStack: errorInfo.componentStack,
      timestamp: new Date().toISOString(),
      userAgent: navigator.userAgent,
      url: window.location.href,
      errorId: this.state.errorId,
    }

    // 发送到错误监控服务
    // Log error report for debugging
    
    // 示例：发送到后端API
    // fetch('/api/errors', {
    //   method: 'POST',
    //   headers: { 'Content-Type': 'application/json' },
    //   body: JSON.stringify(errorReport),
    // }).catch(console.error)
  }

  private handleReload = () => {
    window.location.reload()
  }

  private handleGoHome = () => {
    window.location.href = '/'
  }

  private handleReset = () => {
    this.setState({
      hasError: false,
      error: undefined,
      errorInfo: undefined,
      errorId: undefined,
    })
  }

  private handleReportBug = () => {
    const subject = encodeURIComponent(`Bug Report - ${this.state.errorId}`)
    const body = encodeURIComponent(`
错误ID: ${this.state.errorId}
错误信息: ${this.state.error?.message}
发生时间: ${new Date().toLocaleString()}
页面地址: ${window.location.href}
浏览器: ${navigator.userAgent}

请描述您在遇到此错误前的操作步骤：
1. 
2. 
3. 

其他信息：

    `)
    
    window.open(`mailto:support@example.com?subject=${subject}&body=${body}`)
  }

  public render() {
    if (this.state.hasError) {
      // 如果提供了自定义fallback，使用它
      if (this.props.fallback) {
        return this.props.fallback
      }

      const isDevelopment = process.env.NODE_ENV === 'development'

      return (
        <div style={{ 
          padding: '50px 20px', 
          minHeight: '100vh', 
          background: '#f5f5f5',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center'
        }}>
          <Card style={{ maxWidth: 600, width: '100%' }}>
            <Result
              status="error"
              icon={<ExclamationCircleOutlined style={{ color: '#ff4d4f' }} />}
              title="页面出现错误"
              subTitle={
                <div>
                  <Paragraph>
                    抱歉，页面遇到了一些问题。我们已经记录了这个错误，技术团队会尽快修复。
                  </Paragraph>
                  {this.state.errorId && (
                    <Alert
                      message={
                        <Space>
                          <Text type="secondary">错误ID:</Text>
                          <Text code copyable>{this.state.errorId}</Text>
                        </Space>
                      }
                      type="info"
                      showIcon={false}
                      style={{ marginBottom: 16 }}
                    />
                  )}
                </div>
              }
              extra={[
                <Button 
                  type="primary" 
                  key="reload" 
                  icon={<ReloadOutlined />}
                  onClick={this.handleReload}
                >
                  刷新页面
                </Button>,
                <Button 
                  key="home" 
                  icon={<HomeOutlined />}
                  onClick={this.handleGoHome}
                >
                  返回首页
                </Button>,
                <Button 
                  key="reset" 
                  onClick={this.handleReset}
                >
                  重试
                </Button>,
                <Button 
                  key="report" 
                  icon={<BugOutlined />}
                  onClick={this.handleReportBug}
                >
                  报告问题
                </Button>,
              ]}
            />

            {/* 开发环境下显示详细错误信息 */}
            {isDevelopment && this.state.error && (
              <Card 
                title="开发调试信息" 
                size="small" 
                style={{ marginTop: 16 }}
                type="inner"
              >
                <div style={{ marginBottom: 16 }}>
                  <Text strong>错误信息:</Text>
                  <Paragraph 
                    code 
                    style={{ 
                      background: '#fff2f0', 
                      padding: 8, 
                      marginTop: 8,
                      whiteSpace: 'pre-wrap',
                      fontSize: '12px'
                    }}
                  >
                    {this.state.error.message}
                  </Paragraph>
                </div>

                {this.state.error.stack && (
                  <div style={{ marginBottom: 16 }}>
                    <Text strong>错误堆栈:</Text>
                    <Paragraph 
                      code 
                      style={{ 
                        background: '#f6f6f6', 
                        padding: 8, 
                        marginTop: 8,
                        whiteSpace: 'pre-wrap',
                        fontSize: '11px',
                        maxHeight: 200,
                        overflow: 'auto'
                      }}
                    >
                      {this.state.error.stack}
                    </Paragraph>
                  </div>
                )}

                {this.state.errorInfo?.componentStack && (
                  <div>
                    <Text strong>组件堆栈:</Text>
                    <Paragraph 
                      code 
                      style={{ 
                        background: '#f6f6f6', 
                        padding: 8, 
                        marginTop: 8,
                        whiteSpace: 'pre-wrap',
                        fontSize: '11px',
                        maxHeight: 200,
                        overflow: 'auto'
                      }}
                    >
                      {this.state.errorInfo.componentStack}
                    </Paragraph>
                  </div>
                )}
              </Card>
            )}
          </Card>
        </div>
      )
    }

    return this.props.children
  }
}

export default GlobalErrorBoundary