import React, { useEffect } from 'react'
import { ConfigProvider, App } from 'antd'
import zhCN from 'antd/locale/zh_CN'
import { ErrorBoundary } from '@/components/ErrorHandling'
import { uxManager } from '@/utils/uxManager'

interface UXProviderProps {
  children: React.ReactNode
  config?: {
    // 主题配置
    theme?: {
      primaryColor?: string
      borderRadius?: number
      fontSize?: number
    }
    // UX配置
    ux?: {
      enableErrorReporting?: boolean
      enablePerformanceMonitoring?: boolean
      enableUserFeedback?: boolean
      errorReportingEndpoint?: string
    }
    // 错误边界配置
    errorBoundary?: {
      fallback?: React.ReactNode
      onError?: (error: Error, errorInfo: React.ErrorInfo) => void
    }
  }
}

const UXProvider: React.FC<UXProviderProps> = ({ 
  children, 
  config = {} 
}) => {
  // 初始化UX管理器
  useEffect(() => {
    if (config.ux) {
      uxManager.updateConfig(config.ux)
    }

    // 设置全局错误处理
    const handleError = (error: Error, errorInfo?: Record<string, unknown>) => {
      uxManager.handleError(error, errorInfo)
      
      // 调用自定义错误处理函数
      if (config.errorBoundary?.onError) {
        config.errorBoundary.onError(error, errorInfo)
      }
    }

    // 监听未捕获的Promise拒绝
    const handleUnhandledRejection = (event: PromiseRejectionEvent) => {
      handleError(new Error(event.reason), { type: 'unhandledrejection' })
    }

    window.addEventListener('unhandledrejection', handleUnhandledRejection)

    return () => {
      window.removeEventListener('unhandledrejection', handleUnhandledRejection)
    }
  }, [config])

  // 主题配置
  const themeConfig = {
    token: {
      colorPrimary: config.theme?.primaryColor || '#1890ff',
      borderRadius: config.theme?.borderRadius || 6,
      fontSize: config.theme?.fontSize || 14,
    },
    components: {
      // 自定义组件样式
      Button: {
        borderRadius: config.theme?.borderRadius || 6,
      },
      Card: {
        borderRadius: config.theme?.borderRadius || 8,
      },
      Modal: {
        borderRadius: config.theme?.borderRadius || 8,
      },
      Notification: {
        borderRadius: config.theme?.borderRadius || 8,
      },
    },
  }

  return (
    <ConfigProvider 
      locale={zhCN}
      theme={themeConfig}
    >
      <App>
        <ErrorBoundary
          fallback={config.errorBoundary?.fallback}
          onError={config.errorBoundary?.onError}
        >
          {children}
        </ErrorBoundary>
      </App>
    </ConfigProvider>
  )
}

export default UXProvider