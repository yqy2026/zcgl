import React, { Component, ErrorInfo, ReactNode } from 'react'
import { Result, Button } from 'antd'
import { ExceptionOutlined } from '@ant-design/icons'

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
  }

  handleReset = () => {
    this.setState({ hasError: false, error: undefined })
  }

  render() {
    if (this.state.hasError) {
      return (
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
      )
    }

    return this.props.children
  }
}

export default SystemErrorBoundary