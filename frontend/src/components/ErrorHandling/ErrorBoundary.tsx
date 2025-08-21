import React, { Component, ErrorInfo, ReactNode } from 'react'
import { Result, Button, Typography, Card } from 'antd'
import { BugOutlined, ReloadOutlined, HomeOutlined } from '@ant-design/icons'
import { uxManager } from '../../utils/uxManager'

const { Paragraph, Text } = Typography

interface Props {
  children: ReactNode
}

interface State {
  hasError: boolean
  error?: Error
  errorInfo?: ErrorInfo
}

class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props)
    this.state = { hasError: false }
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    this.setState({ errorInfo })
    
    // 记录错误到UX管理器
    uxManager.handleError(error, {
      componentStack: errorInfo.componentStack,
      errorBoundary: true,
    })
    
    console.error('ErrorBoundary caught an error:', error, errorInfo)
  }

  handleReload = () => {
    window.location.reload()
  }

  handleGoHome = () => {
    window.location.href = '/dashboard'
  }

  handleReset = () => {
    this.setState({ hasError: false, error: undefined, errorInfo: undefined })
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={{ padding: '50px', minHeight: '100vh', backgroundColor: '#f5f5f5' }}>
          <Card style={{ maxWidth: '800px', margin: '0 auto' }}>
            <Result
              status="error"
              icon={<BugOutlined style={{ color: '#ff4d4f' }} />}
              title="页面出现错误"
              subTitle="抱歉，页面遇到了一个意外错误。我们已经记录了这个问题，请尝试刷新页面或返回首页。"
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
                  type="link"
                  onClick={this.handleReset}
                >
                  重试
                </Button>,
              ]}
            >
              {process.env.NODE_ENV === 'development' && this.state.error && (
                <div style={{ textAlign: 'left', marginTop: '20px' }}>
                  <Typography.Title level={5}>错误详情（开发模式）：</Typography.Title>
                  <Paragraph>
                    <Text code>{this.state.error.message}</Text>
                  </Paragraph>
                  {this.state.error.stack && (
                    <Paragraph>
                      <pre style={{ 
                        fontSize: '12px', 
                        backgroundColor: '#f6f8fa', 
                        padding: '10px',
                        borderRadius: '4px',
                        overflow: 'auto',
                        maxHeight: '200px'
                      }}>
                        {this.state.error.stack}
                      </pre>
                    </Paragraph>
                  )}
                </div>
              )}
            </Result>
          </Card>
        </div>
      )
    }

    return this.props.children
  }
}

export default ErrorBoundary