import React, { createContext, useCallback, useContext, useState, useRef } from 'react'
import { Alert, Button, Modal, Typography, Space, Card, Collapse } from 'antd'
import {
  ExclamationCircleOutlined,
  ReloadOutlined,
  CloseOutlined,
  InfoCircleOutlined,
  WarningOutlined,
  CheckCircleOutlined
} from '@ant-design/icons'

const { Text, Title } = Typography
const { Panel } = Collapse

export type ErrorType = 'error' | 'warning' | 'info' | 'success'
export type ErrorSeverity = 'low' | 'medium' | 'high' | 'critical'

interface ErrorInfo {
  id: string
  type: ErrorType
  severity: ErrorSeverity
  title: string
  message: string
  details?: any
  timestamp: Date
  stack?: string
  action?: {
    text: string
    onClick: () => void
  }
  retryCount?: number
  resolved?: boolean
}

interface ErrorContextType {
  showError: (error: Omit<ErrorInfo, 'id' | 'timestamp'>) => void
  showWarning: (message: string, details?: any) => void
  showSuccess: (message: string, details?: any) => void
  showInfo: (message: string, details?: any) => void
  clearError: (id: string) => void
  clearAllErrors: () => void
  retryError: (id: string) => void
  getErrors: () => ErrorInfo[]
  getErrorStats: () => { total: number; byType: Record<string, number>; bySeverity: Record<string, number> }
}

const ErrorContext = createContext<ErrorContextType | null>(null)

export const useSmartError = () => {
  const context = useContext(ErrorContext)
  if (!context) {
    throw new Error('useSmartError must be used within SmartErrorProvider')
  }
  return context
}

interface SmartErrorHandlerProps {
  children: React.ReactNode
  maxErrors?: number
  autoHideDuration?: number
  enableRetry?: boolean
  maxRetryAttempts?: number
}

export const SmartErrorHandler: React.FC<SmartErrorHandlerProps> = ({
  children,
  maxErrors = 50,
  autoHideDuration = 5000,
  enableRetry = true,
  maxRetryAttempts = 3
}) => {
  const [errors, setErrors] = useState<ErrorInfo[]>([])
  const [selectedError, setSelectedError] = useState<ErrorInfo | null>(null)
  const retryAttempts = useRef<Record<string, number>>({})
  const autoHideTimeouts = useRef<Record<string, NodeJS.Timeout>>({})

  const generateErrorId = useCallback(() => {
    return `error_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
  }, [])

  const showError = useCallback((error: Omit<ErrorInfo, 'id' | 'timestamp'>) => {
    const errorInfo: ErrorInfo = {
      id: generateErrorId(),
      timestamp: new Date(),
      retryCount: 0,
      resolved: false,
      ...error
    }

    setErrors(prev => {
      const newErrors = [errorInfo, ...prev.slice(0, maxErrors - 1)]
      return newErrors.sort((a, b) => b.timestamp.getTime() - a.timestamp.getTime())
    })

    // 自动隐藏（5秒后）
    if (autoHideDuration > 0) {
      autoHideTimeouts.current[errorInfo.id] = setTimeout(() => {
        setErrors(prev => prev.filter(e => e.id !== errorInfo.id))
        delete autoHideTimeouts.current[errorInfo.id]
      }, autoHideDuration)
    }

    return errorInfo.id
  }, [maxErrors, autoHideDuration])

  const showWarning = useCallback((message: string, details?: any) => {
    showError({
      type: 'warning',
      severity: 'medium',
      title: '警告',
      message,
      details
    })
  }, [showError])

  const showSuccess = useCallback((message: string, details?: any) => {
    showError({
      type: 'success',
      severity: 'low',
      title: '成功',
      message,
      details
    })
  }, [showError])

  const showInfo = useCallback((message: string, details?: any) => {
    showError({
      type: 'info',
      severity: 'low',
      title: '信息',
      message,
      details
    })
  }, [showError])

  const clearError = useCallback((id: string) => {
    setErrors(prev => prev.filter(e => e.id !== id))
    if (autoHideTimeouts.current[id]) {
      clearTimeout(autoHideTimeouts.current[id])
      delete autoHideTimeouts.current[id]
    }
    if (selectedError?.id === id) {
      setSelectedError(null)
    }
  }, [])

  const clearAllErrors = useCallback(() => {
    setErrors([])
    setSelectedError(null)
    Object.keys(autoHideTimeouts.current).forEach(id => {
      clearTimeout(autoHideTimeouts.current[id])
    })
    autoHideTimeouts.current = {}
  }, [])

  const retryError = useCallback((id: string) => {
    if (!enableRetry) return

    const error = errors.find(e => e.id === id)
    if (!error) return

    const currentAttempts = retryAttempts.current[id] || 0
    if (currentAttempts >= maxRetryAttempts) {
      // 达到最大重试次数，显示错误信息
      showError({
        type: 'error',
        severity: 'high',
        title: '重试失败',
        message: `已达到最大重试次数 (${maxRetryAttempts}次)，请检查网络连接或联系管理员`
      })
      return
    }

    // 增加重试次数
    retryAttempts.current[id] = currentAttempts + 1

    // 执行重试操作
    if (error.action) {
      error.action.onClick()
    }
  }, [errors, enableRetry, maxRetryAttempts])

  const getErrors = useCallback(() => errors, [errors])

  const getErrorStats = useCallback(() => {
    const stats = {
      total: errors.length,
      byType: {} as Record<string, number>,
      bySeverity: {} as Record<string, number>
    }

    errors.forEach(error => {
      stats.byType[error.type] = (stats.byType[error.type] || 0) + 1
      stats.bySeverity[error.severity] = (stats.bySeverity[error.severity] || 0) + 1
    })

    return stats
  }, [errors])

  const contextValue: ErrorContextType = {
    showError,
    showWarning,
    showSuccess,
    showInfo,
    clearError,
    clearAllErrors,
    retryError,
    getErrors,
    getErrorStats
  }

  const getErrorIcon = (type: ErrorType, severity: ErrorSeverity) => {
    switch (type) {
      case 'error':
        return severity === 'critical' ? <ExclamationCircleOutlined style={{ color: '#ff4d4f' }} /> :
               severity === 'high' ? <ExclamationCircleOutlined style={{ color: '#ff7a45' }} /> :
               <ExclamationCircleOutlined style={{ color: '#fa8c16' }} />
      case 'warning':
        return <WarningOutlined style={{ color: '#faad14' }} />
      case 'success':
        return <CheckCircleOutlined style={{ color: '#52c41a' }} />
      case 'info':
        return <InfoCircleOutlined style={{ color: '#1890ff' }} />
      default:
        return <ExclamationCircleOutlined />
    }
  }

  const getErrorColor = (type: ErrorType, severity: ErrorSeverity) => {
    switch (type) {
      case 'error':
        return severity === 'critical' ? '#ff4d4f' :
               severity === 'high' ? '#ff7a45' :
               severity === 'medium' ? '#fa8c16' : '#ffc53d'
      case 'warning':
        return '#faad14'
      case 'success':
        return '#52c41a'
      case 'info':
        return '#1890ff'
      default:
        return '#d9d9d9'
    }
  }

  return (
    <ErrorContext.Provider value={contextValue}>
      {children}
      <ErrorNotificationContainer errors={errors} />
      <ErrorModal
        error={selectedError}
        onClose={() => setSelectedError(null)}
        onRetry={retryError}
        enableRetry={enableRetry}
        maxRetryAttempts={maxRetryAttempts}
      />
    </ErrorContext.Provider>
  )
}

interface ErrorNotificationContainerProps {
  errors: ErrorInfo[]
}

const ErrorNotificationContainer: React.FC<ErrorNotificationContainerProps> = ({ errors }) => {
  if (errors.length === 0) return null

  const latestErrors = errors.slice(0, 3).reverse() // 显示最近3个错误

  return (
    <div style={{
      position: 'fixed',
      top: '20px',
      right: '20px',
      zIndex: 9999,
      maxWidth: '400px'
    }}>
      {latestErrors.map((error, index) => (
        <div
          key={error.id}
          style={{
            marginBottom: index === 0 ? '0px' : '8px',
            backgroundColor: 'white',
            borderRadius: '6px',
            boxShadow: '0 4px 12px rgba(0, 0, 0, 0.15)',
            borderLeft: `4px solid ${getErrorColor(error.type, error.severity)}`
          }}
        >
          <div style={{ padding: '12px 16px 12px 16px' }}>
            <div style={{
              display: 'flex',
              alignItems: 'center',
              marginBottom: '8px'
            }}>
              {getErrorIcon(error.type, error.severity)}
              <div style={{ marginLeft: '8px', flex: 1 }}>
                <div style={{
                  fontWeight: 'bold',
                  color: getErrorColor(error.type, error.severity),
                  fontSize: '14px'
                }}>
                  {error.title}
                </div>
                {error.retryCount && error.retryCount > 1 && (
                  <div style={{
                    fontSize: '12px',
                    color: '#666',
                    marginTop: '2px'
                  }}>
                    重试 {error.retryCount} 次
                  </div>
                )}
              </div>
              <Button
                type="text"
                size="small"
                icon={<CloseOutlined />}
                onClick={() => {
                  // 这个函数会通过context提供
                }}
              />
            </div>
            <Text style={{ fontSize: '13px', color: '#333' }}>
              {error.message}
            </Text>
          </div>
          <div style={{
            borderTop: '1px solid #f0f0f0',
            padding: '8px 16px'
          }}>
            <Space>
              <Button
                type="primary"
                size="small"
                onClick={() => {
                  // 查看详情会在父组件中处理
                }}
              >
                查看详情
              </Button>
              {enableRetry && error.action && (
                <Button
                  type="default"
                  size="small"
                  onClick={() => {
                    // 重试会在父组件中处理
                  }}
                >
                  重试
                </Button>
              )}
            </Space>
          </div>
        </div>
      ))}
    </div>
  )
}

interface ErrorModalProps {
  error: ErrorInfo | null
  onClose: () => void
  onRetry: (id: string) => void
  enableRetry: boolean
  maxRetryAttempts: number
}

const ErrorModal: React.FC<ErrorModalProps> = ({ error, onClose, onRetry, enableRetry, maxRetryAttempts }) => {
  if (!error) return null

  return (
    <Modal
      title={
        <div style={{ display: 'flex', alignItems: 'center' }}>
          {getErrorIcon(error.type, error.severity)}
          <span style={{ marginLeft: '8px' }}>{error.title}</span>
        </div>
      }
      open={true}
      onCancel={onClose}
      width={600}
      footer={
        <Space>
          <Button onClick={onClose}>关闭</Button>
          {enableRetry && error.action && (
            <Button type="primary" onClick={() => onRetry(error.id)}>
              重试 ({Math.min((error.retryCount || 0) + 1, maxRetryAttempts)}/{maxRetryAttempts})
            </Button>
          )}
        </Space>
      }
    >
      <div style={{ padding: '16px 0px' }}>
        <div style={{ marginBottom: '16px' }}>
          <Text strong>错误时间：</Text>
          <Text style={{ marginLeft: '8px' }}>
            {error.timestamp.toLocaleString()}
          </Text>
        </div>

        <div style={{ marginBottom: '16px' }}>
          <Text strong>错误信息：</Text>
        </div>
        <div style={{
          backgroundColor: '#f8f9fa',
          padding: '12px',
          borderRadius: '4px',
          border: '1px solid #e9ecef',
          fontSize: '14px',
          color: '#333'
        }}>
          {error.message}
        </div>

        {error.details && (
          <div style={{ marginTop: '16px' }}>
            <Text strong>详细信息：</Text>
            <Collapse ghost style={{ marginTop: '8px' }}>
              <Panel header="查看详细信息" key="details">
                <pre style={{
                  backgroundColor: '#f8f9fa',
                  padding: '12px',
                  borderRadius: '4px',
                  overflow: 'auto',
                  maxHeight: '200px',
                  fontSize: '12px'
                }}>
                  {typeof error.details === 'object'
                    ? JSON.stringify(error.details, null, 2)
                    : String(error.details)
                  }
                </pre>
              </Panel>
            </Collapse>
          </div>
        )}

        {error.stack && (
          <div style={{ marginTop: '16px' }}>
            <Text strong>堆栈信息：</Text>
            <Collapse ghost style={{ marginTop: '8px' }}>
              <Panel header="查看堆栈信息" key="stack">
                <pre style={{
                  backgroundColor: '#fff2f0',
                  padding: '12px',
                  borderRadius: '4px',
                  overflow: 'auto',
                  maxHeight: '200px',
                  fontSize: '11px',
                  color: '#d63384'
                }}>
                  {error.stack}
                </pre>
              </Panel>
            </Collapse>
          </div>
        )}

        {error.action && (
          <div style={{ marginTop: '16px' }}>
            <Text strong>建议操作：</Text>
            <div style={{ marginTop: '8px' }}>
              <Alert
                message={error.action.text}
                type="info"
                action={
                  <Button type="primary" size="small" onClick={() => onRetry(error.id)}>
                    执行操作
                  </Button>
                }
              />
            </div>
          </div>
        )}
      </div>
    </Modal>
  )
}