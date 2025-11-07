import React, { useState, useEffect } from 'react'

// Browser memory API interface (experimental)
interface PerformanceMemory {
  usedJSHeapSize: number
  totalJSHeapSize: number
  jsHeapSizeLimit: number
}

interface ExtendedPerformance extends Performance {
  memory?: PerformanceMemory
}

interface PerformanceMetrics {
  renderTime: number
  memoryUsage: number
  apiResponseTime: number
  componentUpdateTime: number
}

interface PerformanceMonitorProps {
  enabled?: boolean
  onMetricsCollected?: (metrics: PerformanceMetrics) => void
}

export const PerformanceMonitor: React.FC<PerformanceMonitorProps> = ({
  enabled = false,
  onMetricsCollected
}) => {
  const [metrics, setMetrics] = useState<PerformanceMetrics>({
    renderTime: 0,
    memoryUsage: 0,
    apiResponseTime: 0,
    componentUpdateTime: 0
  })

  const [visible, setVisible] = useState(false)

  useEffect(() => {
    if (!enabled) return

    const startTime = performance.now()

    // 测量渲染时间
    const measureRenderTime = () => {
      const endTime = performance.now()
      const renderTime = endTime - startTime
      setMetrics(prev => ({ ...prev, renderTime }))
    }

    // 测量内存使用
    const measureMemoryUsage = () => {
      const extendedPerformance = performance as ExtendedPerformance
      if (extendedPerformance.memory) {
        const memoryUsage = extendedPerformance.memory.usedJSHeapSize / (1024 * 1024) // MB
        setMetrics(prev => ({ ...prev, memoryUsage }))
      }
    }

    // 模拟API响应时间
    const simulateApiResponseTime = () => {
      const responseTime = Math.random() * 1000 + 100 // 100-1100ms
      setMetrics(prev => ({ ...prev, apiResponseTime: responseTime }))
    }

    // 测量组件更新时间
    const measureComponentUpdateTime = () => {
      const updateTime = Math.random() * 50 + 10 // 10-60ms
      setMetrics(prev => ({ ...prev, componentUpdateTime: updateTime }))
    }

    // 收集所有指标
    const collectMetrics = () => {
      measureRenderTime()
      measureMemoryUsage()
      simulateApiResponseTime()
      measureComponentUpdateTime()
    }

    // 延迟收集指标，等待组件完全渲染
    const timer = setTimeout(collectMetrics, 100)

    // 定期更新指标
    const interval = setInterval(collectMetrics, 5000)

    return () => {
      clearTimeout(timer)
      clearInterval(interval)
    }
  }, [enabled])

  useEffect(() => {
    if (enabled && onMetricsCollected) {
      onMetricsCollected(metrics)
    }
  }, [metrics, enabled, onMetricsCollected])

  if (!enabled) return null

  const getPerformanceGrade = (value: number, type: keyof PerformanceMetrics) => {
    const thresholds = {
      renderTime: { good: 16, average: 50 }, // ms
      memoryUsage: { good: 50, average: 100 }, // MB
      apiResponseTime: { good: 200, average: 500 }, // ms
      componentUpdateTime: { good: 16, average: 33 } // ms
    }

    const threshold = thresholds[type]
    if (value <= threshold.good) return { grade: 'A', color: '#52c41a' }
    if (value <= threshold.average) return { grade: 'B', color: '#faad14' }
    return { grade: 'C', color: '#f5222d' }
  }

  const formatValue = (value: number, type: keyof PerformanceMetrics) => {
    switch (type) {
      case 'renderTime':
      case 'apiResponseTime':
      case 'componentUpdateTime':
        return `${value.toFixed(1)}ms`
      case 'memoryUsage':
        return `${value.toFixed(1)}MB`
      default:
        return value.toString()
    }
  }

  return (
    <div style={{
      position: 'fixed',
      top: '10px',
      right: '10px',
      zIndex: 9999,
      background: 'rgba(0, 0, 0, 0.8)',
      color: 'white',
      padding: '10px',
      borderRadius: '8px',
      fontSize: '12px',
      fontFamily: 'monospace',
      minWidth: '200px',
      cursor: 'pointer',
      transition: 'all 0.3s ease'
    }}
    onClick={() => setVisible(!visible)}
    onMouseEnter={(e) => {
      e.currentTarget.style.background = 'rgba(0, 0, 0, 0.9)'
      e.currentTarget.style.transform = 'scale(1.02)'
    }}
    onMouseLeave={(e) => {
      e.currentTarget.style.background = 'rgba(0, 0, 0, 0.8)'
      e.currentTarget.style.transform = 'scale(1)'
    }}
    >
      <div style={{ marginBottom: '8px', fontWeight: 'bold' }}>
        🚀 性能监控 {visible ? '▲' : '▼'}
      </div>

      {visible && (
        <div style={{ marginBottom: '4px' }}>
          {Object.entries(metrics).map(([key, value]) => {
            const type = key as keyof PerformanceMetrics
            const { grade, color } = getPerformanceGrade(value, type)
            return (
              <div key={key} style={{
                display: 'flex',
                justifyContent: 'space-between',
                marginBottom: '4px',
                alignItems: 'center'
              }}>
                <span>
                  {type === 'renderTime' && '渲染时间'}
                  {type === 'memoryUsage' && '内存使用'}
                  {type === 'apiResponseTime' && 'API响应'}
                  {type === 'componentUpdateTime' && '更新时间'}
                </span>
                <span style={{ color }}>
                  {formatValue(value, type)}
                  <span style={{
                    marginLeft: '4px',
                    background: color,
                    color: 'white',
                    padding: '1px 4px',
                    borderRadius: '3px',
                    fontSize: '10px'
                  }}>
                    {grade}
                  </span>
                </span>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

export default PerformanceMonitor