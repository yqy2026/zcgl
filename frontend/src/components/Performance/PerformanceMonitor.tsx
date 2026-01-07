/**
 * 性能监控组件
 * 监控应用性能指标并提供优化建议
 */

import React, { useEffect, useState, useCallback } from 'react'
import { Card, Statistic, Progress, Alert, Button, Modal, Table, Tag } from 'antd'
import {
  DashboardOutlined,
  ThunderboltOutlined,
  ClockCircleOutlined,
  WarningOutlined
} from '@ant-design/icons'
// import { getComponentLoadMetrics, SmartPreloader } from '@/utils/advancedLazyLoad'

interface PerformanceMetrics {
  // Web Vitals
  fcp?: number // First Contentful Paint
  lcp?: number // Largest Contentful Paint
  fid?: number // First Input Delay
  cls?: number // Cumulative Layout Shift
  
  // 自定义指标
  pageLoadTime?: number
  apiResponseTime?: number
  componentLoadTime?: number
  memoryUsage?: number
  
  // 网络信息
  connectionType?: string
  effectiveType?: string
  downlink?: number
  rtt?: number
}

interface ComponentMetrics {
  name: string
  loadTime: number
  status: 'success' | 'failed' | 'loading'
  retries: number
}

const PerformanceMonitor: React.FC = () => {
  const [metrics, setMetrics] = useState<PerformanceMetrics>({})
  const [componentMetrics, setComponentMetrics] = useState<ComponentMetrics[]>([])
  const [isVisible, setIsVisible] = useState(false)
  const [isMonitoring, setIsMonitoring] = useState(false)

  // 收集Web Vitals
  const collectWebVitals = useCallback(() => {
    // FCP - First Contentful Paint
    const fcpEntry = performance.getEntriesByName('first-contentful-paint')[0] as PerformanceEntry
    if (fcpEntry) {
      setMetrics(prev => ({ ...prev, fcp: fcpEntry.startTime }))
    }

    // 使用Performance Observer收集其他指标
    if ('PerformanceObserver' in window) {
      // LCP - Largest Contentful Paint
      const lcpObserver = new PerformanceObserver((list) => {
        const entries = list.getEntries()
        const lastEntry = entries[entries.length - 1] as PerformanceEntry
        setMetrics(prev => ({ ...prev, lcp: lastEntry.startTime }))
      })
      lcpObserver.observe({ entryTypes: ['largest-contentful-paint'] })

      // FID - First Input Delay
      const fidObserver = new PerformanceObserver((list) => {
        const entries = list.getEntries()
        entries.forEach((entry) => {
          const inputEntry = entry as PerformanceEventTiming
          setMetrics(prev => ({ ...prev, fid: inputEntry.processingStart - inputEntry.startTime }))
        })
      })
      fidObserver.observe({ entryTypes: ['first-input'] })

      // CLS - Cumulative Layout Shift
      let clsValue = 0
      const clsObserver = new PerformanceObserver((list) => {
        const entries = list.getEntries()
        entries.forEach((entry) => {
          const layoutShiftEntry = entry as PerformanceEntry & { value: number; hadRecentInput: boolean }
          if (!layoutShiftEntry.hadRecentInput) {
            clsValue += layoutShiftEntry.value
          }
        })
        setMetrics(prev => ({ ...prev, cls: clsValue }))
      })
      clsObserver.observe({ entryTypes: ['layout-shift'] })
    }
  }, [])

  // 网络连接接口
interface NetworkConnection {
  type: string;
  effectiveType: string;
  downlink: number;
  rtt: number;
}

// 内存信息接口
interface MemoryInfo {
  usedJSHeapSize: number;
  jsHeapSizeLimit: number;
}

// 收集网络信息
  const collectNetworkInfo = useCallback(() => {
    if ('connection' in navigator) {
      const connection = (navigator as unknown as { connection?: NetworkConnection }).connection
      if (connection) {
        setMetrics(prev => ({
          ...prev,
          connectionType: connection.type,
          effectiveType: connection.effectiveType,
          downlink: connection.downlink,
          rtt: connection.rtt
        }))
      }
    }
  }, [])

  // 收集内存使用情况
  const collectMemoryInfo = useCallback(() => {
    if ('memory' in performance) {
      const memory = (performance as unknown as { memory: MemoryInfo }).memory
      setMetrics(prev => ({
        ...prev,
        memoryUsage: memory.usedJSHeapSize / memory.jsHeapSizeLimit * 100
      }))
    }
  }, [])

  // 收集组件加载指标
  const collectComponentMetrics = useCallback(() => {
    // const report = getComponentLoadMetrics()
    // 这里需要根据实际的报告格式调整
    const mockComponentMetrics: ComponentMetrics[] = [
      { name: 'DashboardPage', loadTime: 1200, status: 'success', retries: 0 },
      { name: 'AssetListPage', loadTime: 800, status: 'success', retries: 1 },
      { name: 'AssetDetailPage', loadTime: 600, status: 'success', retries: 0 },
    ]
    setComponentMetrics(mockComponentMetrics)
  }, [])

  // 开始监控
  const startMonitoring = useCallback(() => {
    setIsMonitoring(true)
    collectWebVitals()
    collectNetworkInfo()
    collectMemoryInfo()
    collectComponentMetrics()

    // 定期更新指标
    const interval = setInterval(() => {
      collectMemoryInfo()
      collectComponentMetrics()
    }, 5000)

    return () => clearInterval(interval)
  }, [collectWebVitals, collectNetworkInfo, collectMemoryInfo, collectComponentMetrics])

  useEffect(() => {
    if (isMonitoring) {
      const cleanup = startMonitoring()
      return cleanup
    }
  }, [isMonitoring, startMonitoring])

  // 获取性能评分
  const getPerformanceScore = (metric: number, thresholds: [number, number]) => {
    if (metric <= thresholds[0]) return { score: 'good', color: 'green' }
    if (metric <= thresholds[1]) return { score: 'needs-improvement', color: 'orange' }
    return { score: 'poor', color: 'red' }
  }

  // 性能建议
  const getPerformanceAdvice = () => {
    const advice = []
    
    if (metrics.lcp && metrics.lcp > 2500) {
      advice.push('LCP过高，建议优化图片加载和关键资源')
    }
    
    if (metrics.fid && metrics.fid > 100) {
      advice.push('FID过高，建议减少JavaScript执行时间')
    }
    
    if (metrics.cls && metrics.cls > 0.1) {
      advice.push('CLS过高，建议为图片和广告预留空间')
    }
    
    if (metrics.memoryUsage && metrics.memoryUsage > 80) {
      advice.push('内存使用率过高，建议检查内存泄漏')
    }

    return advice
  }

  const componentColumns = [
    {
      title: '组件名称',
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: '加载时间',
      dataIndex: 'loadTime',
      key: 'loadTime',
      render: (time: number) => `${time}ms`,
      sorter: (a: ComponentMetrics, b: ComponentMetrics) => a.loadTime - b.loadTime,
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => {
        const colorMap = {
          success: 'green',
          failed: 'red',
          loading: 'blue'
        }
        return <Tag color={colorMap[status as keyof typeof colorMap]}>{status}</Tag>
      },
    },
    {
      title: '重试次数',
      dataIndex: 'retries',
      key: 'retries',
    },
  ]

  return (
    <>
      {/* 性能监控触发按钮 */}
      <Button
        type="primary"
        icon={<DashboardOutlined />}
        onClick={() => setIsVisible(true)}
        style={{ position: 'fixed', bottom: 20, right: 20, zIndex: 1000 }}
      >
        性能监控
      </Button>

      {/* 性能监控面板 */}
      <Modal
        title="性能监控面板"
        open={isVisible}
        onCancel={() => setIsVisible(false)}
        width={1000}
        footer={[
          <Button key="start" type="primary" onClick={() => setIsMonitoring(!isMonitoring)}>
            {isMonitoring ? '停止监控' : '开始监控'}
          </Button>,
          <Button key="close" onClick={() => setIsVisible(false)}>
            关闭
          </Button>
        ]}
      >
        {!isMonitoring ? (
          <Alert
            message="点击开始监控按钮开始收集性能数据"
            type="info"
            showIcon
          />
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            {/* Web Vitals 指标 */}
            <Card title="Web Vitals 指标" size="small">
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 16 }}>
                <Statistic
                  title="FCP (ms)"
                  value={metrics.fcp || 0}
                  precision={0}
                  valueStyle={{ 
                    color: metrics.fcp ? getPerformanceScore(metrics.fcp, [1800, 3000]).color : 'inherit' 
                  }}
                  prefix={<ThunderboltOutlined />}
                />
                <Statistic
                  title="LCP (ms)"
                  value={metrics.lcp || 0}
                  precision={0}
                  valueStyle={{ 
                    color: metrics.lcp ? getPerformanceScore(metrics.lcp, [2500, 4000]).color : 'inherit' 
                  }}
                  prefix={<ClockCircleOutlined />}
                />
                <Statistic
                  title="FID (ms)"
                  value={metrics.fid || 0}
                  precision={0}
                  valueStyle={{ 
                    color: metrics.fid ? getPerformanceScore(metrics.fid, [100, 300]).color : 'inherit' 
                  }}
                  prefix={<ThunderboltOutlined />}
                />
                <Statistic
                  title="CLS"
                  value={metrics.cls || 0}
                  precision={3}
                  valueStyle={{ 
                    color: metrics.cls ? getPerformanceScore(metrics.cls, [0.1, 0.25]).color : 'inherit' 
                  }}
                  prefix={<WarningOutlined />}
                />
              </div>
            </Card>

            {/* 系统资源使用 */}
            <Card title="系统资源" size="small">
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 16 }}>
                <div>
                  <div style={{ marginBottom: 8 }}>内存使用率</div>
                  <Progress
                    percent={metrics.memoryUsage || 0}
                    status={metrics.memoryUsage && metrics.memoryUsage > 80 ? 'exception' : 'normal'}
                    format={(percent) => `${percent?.toFixed(1)}%`}
                  />
                </div>
                <div>
                  <Statistic
                    title="网络类型"
                    value={metrics.effectiveType || '未知'}
                    prefix={<ThunderboltOutlined />}
                  />
                  {metrics.downlink && (
                    <div style={{ fontSize: 12, color: '#666', marginTop: 4 }}>
                      下行速度: {metrics.downlink} Mbps | RTT: {metrics.rtt}ms
                    </div>
                  )}
                </div>
              </div>
            </Card>

            {/* 组件加载性能 */}
            <Card title="组件加载性能" size="small">
              <Table
                dataSource={componentMetrics}
                columns={componentColumns}
                size="small"
                pagination={false}
                rowKey="name"
              />
            </Card>

            {/* 性能建议 */}
            {getPerformanceAdvice().length > 0 && (
              <Card title="性能优化建议" size="small">
                {getPerformanceAdvice().map((advice, index) => (
                  <Alert
                    key={index}
                    message={advice}
                    type="warning"
                    showIcon
                    style={{ marginBottom: 8 }}
                  />
                ))}
              </Card>
            )}
          </div>
        )}
      </Modal>
    </>
  )
}

export default PerformanceMonitor