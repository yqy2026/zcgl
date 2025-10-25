import React, { Component, ErrorInfo, ReactNode } from 'react'
import { Result, Button, Collapse, Typography } from 'antd'
import { ExceptionOutlined } from '@ant-design/icons'

const { Panel } = Collapse
const { Paragraph, Text } = Typography

interface Props {
  children: ReactNode
}

interface State {
  hasError: boolean
  error?: Error
}

class SystemErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props)
    this.state = { hasError: false }
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('System Error Boundary caught an error:', error, errorInfo)
    // 将错误信息存储在window对象中，便于调试
    ;(window as any).__lastSystemError = {
      message: error.message,
      stack: error.stack,
      componentStack: errorInfo.componentStack
    }
  }

  handleReset = () => {
    this.setState({ hasError: false, error: undefined })
  }

  render() {
    if (this.state.hasError) {
      const error = this.state.error
      return (
        <div style={{ padding: '50px' }}>
          <Result
            status="error"
            icon={<ExceptionOutlined />}
            title="页面加载失败"
            subTitle="抱歉，系统管理页面出现了错误。"
            extra={[
              <Button type="primary" key="home" onClick={() => window.location.href = '/dashboard'}>
                返回首页
              </Button>,
              <Button key="retry" onClick={this.handleReset}>
                重试
              </Button>
            ]}
          />
          {error && (
            <Collapse style={{ marginTop: '20px' }}>
              <Panel header="错误详情" key="error-details">
                <Paragraph>
                  <Text strong>错误信息:</Text>
                  <Text code>{error.message}</Text>
                </Paragraph>
                {error.stack && (
                  <Paragraph>
                    <Text strong>堆栈跟踪:</Text>
                    <pre style={{ background: '#f5f5f5', padding: '10px', borderRadius: '4px', fontSize: '12px' }}>
                      {error.stack}
                    </pre>
                  </Paragraph>
                )}
              </Panel>
            </Collapse>
          )}
        </div>
      )
    }

    return this.props.children
  }
}

export default SystemErrorBoundary