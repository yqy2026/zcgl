import React, { createContext, useCallback, useContext, useState, useRef, useEffect } from 'react'
import { Progress, Steps, Card, Typography, Tag, Button } from 'antd'
import {
  CheckCircleOutlined,
  ClockCircleOutlined,
  LoadingOutlined,
  PauseCircleOutlined,
  ExclamationCircleOutlined,
  SyncOutlined
} from '@ant-design/icons'

const { Text, Title } = Typography

export type StepStatus = 'wait' | 'process' | 'finish' | 'error' | 'paused'
export type ProgressType = 'upload' | 'processing' | 'download' | 'api_call' | 'data_sync'

interface ProgressStep {
  id: string
  title: string
  description?: string
  status: StepStatus
  progress?: number
  startTime?: Date
  endTime?: Date
  duration?: number
  icon?: React.ReactNode
  error?: string
  action?: {
    text: string
    onClick: () => void
  }
  substeps?: ProgressStep[]
}

interface ProgressTracker {
  id: string
  type: ProgressType
  title: string
  steps: ProgressStep[]
  currentStep: number
  totalProgress?: number
  startTime?: Date
  estimatedEndTime?: Date
  status: 'active' | 'completed' | 'paused' | 'error'
  canCancel?: boolean
  canPause?: boolean
  error?: string
  onRetry?: () => void
  onStepClick?: (stepId: string) => void
  onCancel?: () => void
  onPause?: () => void
  onResume?: () => void
}

interface ProgressContextType {
  createTracker: (tracker: Omit<ProgressTracker, 'id' | 'startTime'>) => string
  updateStep: (trackerId: string, stepId: string, updates: Partial<ProgressStep>) => void
  updateTracker: (trackerId: string, updates: Partial<ProgressTracker>) => void
  cancelTracker: (trackerId: string) => void
  completeTracker: (trackerId: string) => void
  pauseTracker: (trackerId: string) => void
  resumeTracker: (trackerId: string) => void
  getTracker: (trackerId: string) => ProgressTracker | null
  getActiveTrackers: () => ProgressTracker[]
}

const ProgressContext = createContext<ProgressContextType | null>(null)

export const useSmartProgress = () => {
  const context = useContext(ProgressContext)
  if (!context) {
    throw new Error('useSmartProgress must be used within SmartProgressProvider')
  }
  return context
}

interface SmartProgressProviderProps {
  children: React.ReactNode
  maxActiveTrackers?: number
}

export const SmartProgressProvider: React.FC<SmartProgressProviderProps> = ({
  children,
  maxActiveTrackers = 5
}) => {
  const [trackers, setTrackers] = useState<ProgressTracker[]>([])
  const intervals = useRef<Record<string, NodeJS.Timeout>>({})

  const createTracker = useCallback((tracker: Omit<ProgressTracker, 'id' | 'startTime'>) => {
    const trackerId = `tracker_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
    const newTracker: ProgressTracker = {
      id: trackerId,
      startTime: new Date(),
      ...tracker,
      status: tracker.status || 'active'
    }

    setTrackers(prev => {
      const newTrackers = [newTracker, ...prev.slice(0, maxActiveTrackers - 1)]
      return newTrackers
    })

    // 启动时间更新
    intervals.current[trackerId] = setInterval(() => {
      updateTracker(trackerId, { estimatedEndTime: calculateEstimatedEndTime(newTracker) })
    }, 1000)

    return trackerId
  }, [maxActiveTrackers])

  const updateStep = useCallback((trackerId: string, stepId: string, updates: Partial<ProgressStep>) => {
    setTrackers(prev => prev.map(tracker => {
      if (tracker.id === trackerId) {
        const updatedSteps = tracker.steps.map(step => {
          if (step.id === stepId) {
            const now = new Date()
            const startTime = step.startTime || now

            // 如果状态改为完成，记录结束时间
            if (updates.status === 'finish' && step.status !== 'finish') {
              return {
                ...step,
                ...updates,
                endTime: now,
                duration: now.getTime() - startTime.getTime(),
                progress: 100
              }
            }

            return { ...step, ...updates }
          }
          return step
        })

        // 更新当前步骤
        const currentStepIndex = updatedSteps.findIndex(s => s.status === 'finish')
        const nextStepIndex = updatedSteps.findIndex(s => s.status === 'process')

        return {
          ...tracker,
          steps: updatedSteps,
          currentStep: Math.max(currentStepIndex, nextStepIndex),
          totalProgress: calculateTotalProgress(updatedSteps)
        }
      }
      return tracker
    }))
  }, [])

  const updateTracker = useCallback((trackerId: string, updates: Partial<ProgressTracker>) => {
    setTrackers(prev => prev.map(tracker => {
      if (tracker.id === trackerId) {
        if (updates.status === 'completed') {
          // 清除定时器
          if (intervals.current[trackerId]) {
            clearInterval(intervals.current[trackerId])
            delete intervals.current[trackerId]
          }
        }

        return { ...tracker, ...updates }
      }
      return tracker
    }))
  }, [])

  const cancelTracker = useCallback((trackerId: string) => {
    updateTracker(trackerId, {
      status: 'error',
      estimatedEndTime: new Date()
    })

    if (intervals.current[trackerId]) {
      clearInterval(intervals.current[trackerId])
      delete intervals.current[trackerId]
    }
  }, [])

  const completeTracker = useCallback((trackerId: string) => {
    setTrackers(prev => prev.map(tracker => {
      if (tracker.id === trackerId) {
        return {
          ...tracker,
          status: 'completed',
          estimatedEndTime: new Date()
        }
      }
      return tracker
    }))

    // 清除定时器
    if (intervals.current[trackerId]) {
      clearInterval(intervals.current[trackerId])
      delete intervals.current[trackerId]
    }
  }, [])

  const pauseTracker = useCallback((trackerId: string) => {
    updateTracker(trackerId, {
      status: 'paused',
      estimatedEndTime: undefined
    })

    if (intervals.current[trackerId]) {
      clearInterval(intervals.current[trackerId])
      delete intervals.current[trackerId]
    }
  }, [])

  const resumeTracker = useCallback((trackerId: string) => {
    updateTracker(trackerId, {
      status: 'active'
    })

    // 重新启动定时器
    const tracker = getTracker(trackerId)
    if (tracker) {
      intervals.current[trackerId] = setInterval(() => {
        updateTracker(trackerId, { estimatedEndTime: calculateEstimatedEndTime(tracker) })
      }, 1000)
    }
  }, [])

  const getTracker = useCallback((trackerId: string) => {
    return trackers.find(t => t.id === trackerId) || null
  }, [trackers])

  const getActiveTrackers = useCallback(() => {
    return trackers.filter(t => t.status === 'active')
  }, [trackers])

  const contextValue: ProgressContextType = {
    createTracker,
    updateStep,
    updateTracker,
    cancelTracker,
    completeTracker,
    pauseTracker,
    resumeTracker,
    getTracker,
    getActiveTrackers
  }

  const calculateTotalProgress = (steps: ProgressStep[]): number => {
    const totalWeight = steps.length * 100
    const completedWeight = steps
      .filter(step => step.status === 'finish')
      .reduce((sum, step) => {
        const weight = step.progress || 100
        return sum + weight
      }, 0)

    return totalWeight > 0 ? Math.round((completedWeight / totalWeight) * 100) : 0
  }

  const calculateEstimatedEndTime = (tracker: ProgressTracker): Date => {
    if (!tracker.startTime) return new Date()

    const elapsed = new Date().getTime() - tracker.startTime.getTime()
    const progress = tracker.totalProgress || 0

    if (progress <= 0) return new Date()

    // 基于当前进度估算剩余时间
    const estimatedTotalTime = elapsed * 100 / progress
    const remainingTime = estimatedTotalTime - elapsed

    return new Date(Date.now() + remainingTime)
  }

  useEffect(() => {
    return () => {
      Object.values(intervals.current).forEach(interval => {
        clearInterval(interval)
      })
    }
  }, [])

  return (
    <ProgressContext.Provider value={contextValue}>
      {children}
      <ProgressTrackersList trackers={trackers} />
    </ProgressContext.Provider>
  )
}

interface ProgressTrackersListProps {
  trackers: ProgressTracker[]
}

const ProgressTrackersList: React.FC<ProgressTrackersListProps> = ({ trackers }) => {
  const { cancelTracker, pauseTracker, resumeTracker } = useSmartProgress()

  if (trackers.length === 0) return null

  const getProgressTypeIcon = (type: ProgressType) => {
    switch (type) {
      case 'upload':
        return <SyncOutlined style={{ color: '#1890ff' }} />
      case 'processing':
        return <LoadingOutlined style={{ color: '#52c41a' }} />
      case 'download':
        return <LoadingOutlined style={{ color: '#722ed1' }} />
      case 'api_call':
        return <LoadingOutlined style={{ color: '#13c2c2' }} />
      case 'data_sync':
        return <SyncOutlined spin style={{ color: '#fa8c16' }} />
      default:
        return <LoadingOutlined />
    }
  }

  const getStatusIcon = (status: StepStatus) => {
    switch (status) {
      case 'wait':
        return <ClockCircleOutlined style={{ color: '#d9d9d9' }} />
      case 'process':
        return <LoadingOutlined spin style={{ color: '#1890ff' }} />
      case 'finish':
        return <CheckCircleOutlined style={{ color: '#52c41a' }} />
      case 'error':
        return <ExclamationCircleOutlined style={{ color: '#ff4d4f' }} />
      case 'paused':
        return <PauseCircleOutlined style={{ color: '#faad14' }} />
      default:
        return null
    }
  }

  const getStepIcon = (step: ProgressStep) => {
    return step.icon || getStatusIcon(step.status)
  }

  const formatDuration = (duration: number): string => {
    if (duration < 1000) return `${Math.round(duration)}ms`
    if (duration < 60000) return `${Math.round(duration / 1000)}s`
    return `${Math.round(duration / 60000)}m ${Math.round((duration % 60000) / 1000)}s`
  }

  return (
    <div style={{
      position: 'fixed',
      bottom: '20px',
      right: '20px',
      width: '400px',
      maxHeight: '60vh',
      zIndex: 9999,
      backgroundColor: 'white',
      borderRadius: '8px',
      boxShadow: '0 4px 12px rgba(0, 0, 0, 0.15)',
      border: '1px solid #d9d9d9'
    }}>
      <div style={{
        padding: '16px',
        borderBottom: '1px solid #f0f0f0',
        marginBottom: '12px'
      }}>
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center'
        }}>
          <Title level={5}>进行中的任务 ({trackers.length})</Title>
          <Button type="text" size="small">
            全部展开
          </Button>
        </div>
      </div>

      <div style={{
        maxHeight: '45vh',
        overflowY: 'auto'
      }}>
        {trackers.map(tracker => (
          <Card
            key={tracker.id}
            size="small"
            style={{ marginBottom: '12px' }}
            title={
              <div style={{ display: 'flex', alignItems: 'center' }}>
                {getProgressTypeIcon(tracker.type)}
                <span style={{ marginLeft: '8px' }}>{tracker.title}</span>
                <Tag
                  color={tracker.status === 'completed' ? 'green' :
                         tracker.status === 'error' ? 'red' :
                         tracker.status === 'paused' ? 'orange' : 'blue'}
                  style={{ marginLeft: 'auto' }}
                >
                  {tracker.status === 'completed' ? '已完成' :
                   tracker.status === 'error' ? '失败' :
                   tracker.status === 'paused' ? '已暂停' : '进行中'}
                </Tag>
              </div>
            }
            >
            <div style={{ marginBottom: '8px' }}>
              <Progress
                percent={tracker.totalProgress || 0}
                size="small"
                status={tracker.status === 'error' ? 'exception' :
                       tracker.status === 'completed' ? 'success' : 'normal'}
                strokeColor={{
                  '0%': '#52c41a',
                  '100%': '#52c41a'
                }}
              />
            </div>

            <Steps
              direction="vertical"
              size="small"
              current={tracker.currentStep}
              items={tracker.steps.map(step => ({
                title: (
                  <div style={{ display: 'flex', alignItems: 'center' }}>
                    {getStepIcon(step)}
                    <span style={{ marginLeft: '8px', fontSize: '12px' }}>
                      {step.title}
                    </span>
                    {step.duration && (
                      <span style={{ marginLeft: '8px', fontSize: '11px', color: '#666' }}>
                        ({formatDuration(step.duration)})
                      </span>
                    )}
                  </div>
                ),
                description: step.description,
                status: step.status === 'paused' ? 'wait' : step.status as any
              })) as any}
            />

            {tracker.error && (
              <div style={{
                marginTop: '8px',
                padding: '8px',
                backgroundColor: '#fff2f0',
                borderRadius: '4px',
                fontSize: '12px'
              }}>
                <Text type="danger" style={{ display: 'flex', alignItems: 'center' }}>
                  <ExclamationCircleOutlined style={{ marginRight: '8px' }} />
                  {tracker.error}
                </Text>
              </div>
            )}

            <div style={{
              marginTop: '12px',
              display: 'flex',
              justifyContent: 'flex-end',
              gap: '8px'
            }}>
              {tracker.canCancel && (
                <Button size="small" danger onClick={() => cancelTracker(tracker.id)}>
                  取消
                </Button>
              )}
              {tracker.canPause && (
                <Button size="small" onClick={() => {
                  if (tracker.status === 'paused') {
                    resumeTracker(tracker.id)
                  } else {
                    pauseTracker(tracker.id)
                  }
                }}>
                  {tracker.status === 'paused' ? '恢复' : '暂停'}
                </Button>
              )}
              {tracker.status === 'error' && (
                <Button size="small" type="primary" onClick={() => {
                  if (tracker.onRetry) {
                    tracker.onRetry()
                  }
                }}>
                  重试
                </Button>
              )}
            </div>
          </Card>
        ))}
      </div>
    </div>
  )
}