import React, { createContext, useContext, useCallback, useRef, useState } from 'react'
import { Spin, Skeleton, Progress, Typography, Card } from 'antd'
import { LoadingOutlined } from '@ant-design/icons'

const { Text } = Typography

interface LoadingState {
  isLoading: boolean
  message?: string
  progress?: number
  type?: 'default' | 'upload' | 'processing' | 'data'
  delay?: number
  timestamp?: number
}

interface LoadingContextType {
  showLoading: (state: LoadingState) => void
  hideLoading: () => void
  updateProgress: (progress: number) => void
  getLoadingState: () => LoadingState | null
}

const LoadingContext = createContext<LoadingContextType | null>(null)

export const useSmartLoading = () => {
  const context = useContext(LoadingContext)
  if (!context) {
    throw new Error('useSmartLoading must be used within SmartLoadingProvider')
  }
  return context
}

interface SmartLoadingManagerProps {
  children: React.ReactNode
  defaultDelay?: number
  maxQueueSize?: number
}

export const SmartLoadingManager: React.FC<SmartLoadingManagerProps> = ({
  children,
  defaultDelay = 300,
  maxQueueSize = 10
}) => {
  const [loadingState, setLoadingState] = useState<LoadingState | null>(null)
  const loadingQueue = useRef<LoadingState[]>([])
  const loadingTimeoutRef = useRef<NodeJS.Timeout>()

  const showLoading = useCallback((state: LoadingState) => {
    // 添加到队列
    loadingQueue.current.push({ ...state, timestamp: Date.now() })

    // 限制队列大小
    if (loadingQueue.current.length > maxQueueSize) {
      loadingQueue.current.shift() // 移除最旧的请求
    }

    // 延迟显示，避免闪烁
    const delay = state.delay !== undefined ? state.delay : defaultDelay
    const timestamp = state.timestamp || Date.now()
    const timeSinceRequest = Date.now() - timestamp

    const showLoadingState = () => {
      // 只显示最新状态
      const latestState = loadingQueue.current[loadingQueue.current.length - 1]
      if (latestState) {
        setLoadingState(latestState)
      }
    }

    if (timeSinceRequest >= delay) {
      showLoadingState()
    } else {
      // 清除之前的定时器
      if (loadingTimeoutRef.current) {
        clearTimeout(loadingTimeoutRef.current)
      }

      // 设置新的定时器
      const remainingDelay = delay - timeSinceRequest
      loadingTimeoutRef.current = setTimeout(showLoadingState, remainingDelay)
    }
  }, [defaultDelay, maxQueueSize])

  const hideLoading = useCallback(() => {
    // 清除定时器
    if (loadingTimeoutRef.current) {
      clearTimeout(loadingTimeoutRef.current)
    }

    // 移除当前状态
    if (loadingQueue.current.length > 0) {
      loadingQueue.current.pop()
    }

    // 显示前一个状态（如果存在）
    if (loadingQueue.current.length > 0) {
      const previousState = loadingQueue.current[loadingQueue.current.length - 1]
      setLoadingState(previousState)
    } else {
      setLoadingState(null)
    }
  }, [])

  const updateProgress = useCallback((progress: number) => {
    if (loadingState) {
      setLoadingState({ ...loadingState, progress })
    }
  }, [loadingState])

  const getLoadingState = useCallback(() => {
    return loadingState
  }, [loadingState])

  const contextValue: LoadingContextType = {
    showLoading,
    hideLoading,
    updateProgress,
    getLoadingState
  }

  return (
    <LoadingContext.Provider value={contextValue}>
      {children}
      <SmartLoadingOverlay state={loadingState} />
    </LoadingContext.Provider>
  )
}

interface SmartLoadingOverlayProps {
  state: LoadingState | null
}

const SmartLoadingOverlay: React.FC<SmartLoadingOverlayProps> = ({ state }) => {
  if (!state) {
    return null
  }

  const renderLoadingContent = () => {
    switch (state.type) {
      case 'upload':
        return (
          <Card style={{ width: 300, textAlign: 'center' }}>
            <Spin
              indicator={<LoadingOutlined style={{ fontSize: 24 }} />}
              tip={state.message}
            />
            <div style={{ marginTop: 16 }}>
              <Progress
                percent={state.progress || 0}
                status="active"
                strokeColor={{
                  '0%': '#108ee9',
                  '100%': '#52c41a',
                }}
              strokeWidth={8}
                size="small"
              />
              <div style={{ marginTop: 8 }}>
                <Text type="secondary">{state.message}</Text>
              </div>
            </div>
          </Card>
        )

      case 'processing':
        return (
          <Card style={{ width: 320, textAlign: 'center', padding: '20px' }}>
            <Spin size="large" tip={state.message} />
            <div style={{ marginTop: 16 }}>
              <Progress
                percent={state.progress || 0}
                status="active"
                strokeColor={{
                  '0%': '#1890ff',
                  '100%': '#52c41a',
                }}
                strokeWidth={6}
                format={() => state.message}
              />
            </div>
          </Card>
        )

      case 'data':
        return (
          <div style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: 'rgba(255, 255, 255, 0.9)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 9999
          }}>
            <Card style={{ width: 200, textAlign: 'center' }}>
              <Spin indicator={<LoadingOutlined style={{ fontSize: 20 }} />} tip="数据处理中" />
              <div style={{ marginTop: 12 }}>
                <Progress
                  percent={state.progress || 0}
                  status="active"
                  size="small"
                  strokeWidth={4}
                />
              </div>
            </Card>
          </div>
        )

      default:
        return (
          <div style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: 'rgba(0, 0, 0, 0.45)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 9999
          }}>
            <Spin
              size="large"
              tip={state.message}
              indicator={<LoadingOutlined style={{ fontSize: 32 }} />}
            />
            <div style={{ marginTop: 16, marginLeft: 16 }}>
              <Text style={{ color: 'white', fontSize: 16 }}>
                {state.message || '加载中...'}
              </Text>
            </div>
          </div>
        )
    }
  }

  return renderLoadingContent()
}

// 智能骨架屏组件
interface SmartSkeletonProps {
  loading: boolean
  children: React.ReactNode
  type?: 'default' | 'list' | 'card' | 'table'
  rows?: number
  avatar?: boolean
  paragraph?: boolean
  title?: boolean
  active?: boolean
}

export const SmartSkeleton: React.FC<SmartSkeletonProps> = ({
  loading,
  children,
  type = 'default',
  rows = 3,
  avatar = false,
  paragraph = true,
  title = true,
  active = true
}) => {
  if (!loading) {
    return <>{children}</>
  }

  const renderSkeleton = () => {
    switch (type) {
      case 'list':
        return (
          <div style={{ padding: '16px' }}>
            {Array.from({ length: rows }).map((_, index) => (
              <div key={index} style={{ marginBottom: 16 }}>
                <Skeleton
                  avatar={avatar}
                  paragraph={{ rows: 1 }}
                  title={title}
                  active={active}
                />
                <Skeleton
                  paragraph={{ rows: paragraph ? 2 : 1 }}
                  active={active}
                />
              </div>
            ))}
          </div>
        )

      case 'card':
        return (
          <div style={{ padding: '16px' }}>
            {Array.from({ length: rows }).map((_, index) => (
              <Card key={index} style={{ marginBottom: 16 }}>
                <Skeleton
                  avatar={avatar}
                  paragraph={{ rows: 2 }}
                  title={title}
                  active={active}
                />
              </Card>
            ))}
          </div>
        )

      case 'table':
        return (
          <div style={{ padding: '16px' }}>
            <Skeleton
              paragraph={{ rows: 1 }}
              title={title}
              active={active}
              style={{ marginBottom: 16 }}
            />
            <Skeleton
              paragraph={{ rows: rows }}
              active={active}
            />
          </div>
        )

      default:
        return (
          <div style={{ padding: '24px' }}>
            <Skeleton
              avatar={avatar}
              paragraph={{ rows: rows }}
              title={title}
              active={active}
            />
          </div>
        )
    }
  }

  return (
    <div style={{ minHeight: '200px' }}>
      {renderSkeleton()}
    </div>
  )
}

// 预加载组件
interface PreloaderProps {
  resource: string
  onPreloadComplete?: () => void
  fallback?: React.ReactNode
}

export const SmartPreloader: React.FC<PreloaderProps> = ({
  resource,
  onPreloadComplete,
  fallback = null
}) => {
  const [isPreloaded, setIsPreloaded] = useState(false)
  const [isPreloading, setIsPreloading] = useState(false)

  React.useEffect(() => {
    if (resource && !isPreloaded && !isPreloading) {
      setIsPreloading(true)

      // 创建预加载链接
      const link = document.createElement('link')
      link.rel = 'preload'
      link.href = resource
      link.as = 'script'

      link.onload = () => {
        setIsPreloaded(true)
        setIsPreloading(false)
        onPreloadComplete?.()
        document.head.removeChild(link)
      }

      link.onerror = () => {
        setIsPreloading(false)
        console.warn(`预加载失败: ${resource}`)
        document.head.removeChild(link)
      }

      document.head.appendChild(link)
    }
  }, [resource, isPreloaded, isPreloading])

  if (fallback && !isPreloaded) {
    return <>{fallback}</>
  }

  return null
}

// 智能进度跟踪器
interface ProgressTrackerProps {
  steps: Array<{
    title: string
    description?: string
    status: 'wait' | 'process' | 'finish' | 'error'
    icon?: React.ReactNode
  }>
  current: number
  size?: 'small' | 'default'
  direction?: 'horizontal' | 'vertical'
  showDetails?: boolean
}

export const SmartProgressTracker: React.FC<ProgressTrackerProps> = ({
  steps,
  current,
  size = 'default',
  direction = 'horizontal',
  showDetails = true
}) => {
  return (
    <div style={{ padding: '16px' }}>
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: showDetails ? '16px' : '0'
      }}>
        <Text strong>
          总进度: {steps.filter(s => s.status === 'finish').length}/{steps.length}
        </Text>
        <Text type="secondary">
          ({Math.round((steps.filter(s => s.status === 'finish').length / steps.length) * 100)}%)
        </Text>
      </div>

      <Progress
        percent={(steps.filter(s => s.status === 'finish').length / steps.length) * 100}
        strokeColor={{
          '0%': '#108ee9',
          '100%': '#52c41a',
        }}
        strokeWidth={8}
        size="small"
        format={(percent) => `${Math.round(percent || 0)}%`}
      />

      <div style={{ marginTop: '16px' }}>
        {steps.map((step, index) => (
          <div key={index} style={{
            display: 'flex',
            alignItems: 'center',
            marginBottom: '12px',
            opacity: step.status === 'wait' ? 0.6 : 1
          }}>
            <div style={{
              width: '20px',
              height: '20px',
              borderRadius: '50%',
              backgroundColor: step.status === 'finish' ? '#52c41a' :
                               step.status === 'process' ? '#1890ff' :
                               step.status === 'error' ? '#ff4d4f' : '#d9d9d9',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: step.status === 'finish' ? 'white' : '#666',
              fontSize: '12px',
              fontWeight: 'bold'
            }}>
              {step.status === 'finish' ? '✓' :
               step.status === 'error' ? '!' :
               step.status === 'process' ? '⟳' : index + 1}
            </div>
            <div style={{ marginLeft: '12px' }}>
              <div style={{ fontWeight: index === current ? 'bold' : 'normal' }}>
                {step.title}
              </div>
              {showDetails && step.description && (
                <div style={{
                  fontSize: '12px',
                  color: '#666',
                  marginTop: '4px'
                }}>
                  {step.description}
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}