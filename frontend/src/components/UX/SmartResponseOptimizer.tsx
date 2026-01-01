import React, { createContext, useCallback, useContext, useState, useRef } from 'react'
import { message, Statistic, Card, Row, Col, Switch, Button, Space, Typography } from 'antd'
import {
  ThunderboltOutlined
} from '@ant-design/icons'

const { Text } = Typography

export type OptimizationType = 'loading' | 'rendering' | 'compression' | 'caching' | 'network' | 'database'
export type ResponseLevel = 'excellent' | 'good' | 'acceptable' | 'poor'

interface PerformanceMetrics {
  responseTime: number
  renderTime: number
  networkTime: number
  cacheHit: boolean
  compressionRatio: number
  requestSize: number
  responseSize: number
  timestamp: Date
}

interface SmartResponseConfig {
  enableOptimization: boolean
  autoCompression: boolean
  smartCaching: boolean
  prefetchResources: boolean
  lazyLoading: boolean
  imageOptimization: boolean
  minResponseTime: number
  maxResponseTime: number
}

interface ResponseOptimizationContextType {
  getMetrics: () => PerformanceMetrics[]
  optimizeResponse: (config: SmartResponseConfig) => void
  getPerformanceLevel: (responseTime: number) => ResponseLevel
  generateReport: () => {
    summary: {
      total: number
      average: any
      byType: any
      byLevel: any
    }
  }
  clearMetrics: () => void
  toggleOptimization: (type: OptimizationType) => void
  resetConfig: () => void
}

const OptimizationContext = createContext<ResponseOptimizationContextType | null>(null)

export const useSmartResponse = () => {
  const context = useContext(OptimizationContext)
  if (!context) {
    throw new Error('useSmartResponse must be used within SmartResponseProvider')
  }
  return context
}

const SmartResponseProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [config, setConfig] = useState<SmartResponseConfig>({
    enableOptimization: true,
    autoCompression: true,
    smartCaching: true,
    prefetchResources: true,
    lazyLoading: true,
    imageOptimization: true,
    minResponseTime: 100,
    maxResponseTime: 5000
  })

  const [metrics, setMetrics] = useState<PerformanceMetrics[]>([])
  const [optimizationStates, setOptimizationStates] = useState<Record<OptimizationType, boolean>>({
    loading: true,
    rendering: true,
    compression: true,
    caching: true,
    network: true,
    database: false
  })

  const metricsRef = useRef<PerformanceMetrics[]>([])

  // 获取性能等级
  const getPerformanceLevel = useCallback((responseTime: number): ResponseLevel => {
    if (responseTime < 200) return 'excellent'
    if (responseTime < 500) return 'good'
    if (responseTime < 1000) return 'acceptable'
    return 'poor'
  }, [])

  // 优化响应
  const optimizeResponse = useCallback((newConfig: SmartResponseConfig) => {
    setConfig(prev => ({ ...prev, ...newConfig }))
    message.info('响应优化配置已更新')
  }, [])

  // 获取响应类型
  const getResponseType = useCallback((metric: PerformanceMetrics): OptimizationType => {
    // 根据时间分配类型
    if (metric.responseTime < 100) return 'loading'
    if (metric.renderTime > metric.responseTime * 2) return 'rendering'
    if (metric.compressionRatio > 0.8) return 'compression'
    if (metric.cacheHit) return 'caching'
    if (metric.networkTime > metric.responseTime * 0.5) return 'network'
    return 'database'
  }, [])

  // 生成性能报告
  const generateReport = useCallback(() => {
    if (metrics.length === 0) {
      return {
        summary: {
          total: 0,
          average: 0,
          byType: {},
          byLevel: {}
        }
      }
    }

    const totalMetrics = metrics
    const averageResponseTime = totalMetrics.reduce((sum, m) => sum + m.responseTime, 0) / totalMetrics.length
    const averageRenderTime = totalMetrics.reduce((sum, m) => sum + m.renderTime, 0) / totalMetrics.length
    const averageNetworkTime = totalMetrics.reduce((sum, m) => sum + m.networkTime, 0) / totalMetrics.length
    const cacheHitRate = totalMetrics.filter(m => m.cacheHit).length / totalMetrics.length * 100
    const averageCompressionRatio = totalMetrics.reduce((sum, m) => sum + m.compressionRatio, 0) / totalMetrics.length

    const byType = totalMetrics.reduce((acc, m) => {
      const type = getResponseType(m)
      acc[type] = (acc[type] || 0) + 1
      return acc
    }, {} as Record<string, number>)

    const byLevel = {
      excellent: totalMetrics.filter(m => getPerformanceLevel(m.responseTime) === 'excellent').length,
      good: totalMetrics.filter(m => getPerformanceLevel(m.responseTime) === 'good').length,
      acceptable: totalMetrics.filter(m => getPerformanceLevel(m.responseTime) === 'acceptable').length,
      poor: totalMetrics.filter(m => getPerformanceLevel(m.responseTime) === 'poor').length
    }

    return {
      summary: {
        total: totalMetrics.length,
        average: {
          responseTime: averageResponseTime,
          renderTime: averageRenderTime,
          networkTime: averageNetworkTime,
          cacheHitRate: cacheHitRate,
          compressionRatio: averageCompressionRatio
        },
        byType,
        byLevel
      }
    }
  }, [metrics, getResponseType, getPerformanceLevel])

  // 清除指标
  const clearMetrics = useCallback(() => {
    setMetrics([])
    metricsRef.current = []

    setOptimizationStates({
      loading: true,
      rendering: true,
      compression: true,
      caching: true,
      network: true,
      database: true
    })
  }, [])

  // 添加性能指标
  const _addMetrics = useCallback((metric: PerformanceMetrics) => {
    const newMetrics = [metric, ...metricsRef.current.slice(0, 49)] // 只保留最近50个
    metricsRef.current = newMetrics
    setMetrics(newMetrics)
  }, [])

  // 切换优化状态
  const toggleOptimization = useCallback((type: OptimizationType) => {
    setOptimizationStates(prev => ({
      ...prev,
      [type]: !prev[type]
    }))
    message.info(`${type}优化已${optimizationStates[type] ? '启用' : '禁用'}`)
  }, [optimizationStates])

  // 重置配置
  const resetConfig = useCallback(() => {
    setConfig({
      enableOptimization: true,
      autoCompression: true,
      smartCaching: true,
      prefetchResources: true,
      lazyLoading: true,
      imageOptimization: true,
      minResponseTime: 100,
      maxResponseTime: 5000
    })
  }, [])

  const contextValue: ResponseOptimizationContextType = {
    getMetrics: () => metrics,
    optimizeResponse,
    getPerformanceLevel,
    generateReport,
    clearMetrics,
    toggleOptimization,
    resetConfig
  }

  return (
    <OptimizationContext.Provider value={contextValue}>
      {children}
      <ResponseOptimizationDashboard config={config} metrics={metrics} />
    </OptimizationContext.Provider>
  )
}

// 响应优化仪表板组件
const ResponseOptimizationDashboard: React.FC<{ config: SmartResponseConfig; metrics: PerformanceMetrics[] }> = ({ config, metrics }) => {
  const [showDetails, setShowDetails] = useState(false)
  const { generateReport, optimizeResponse, resetConfig } = useSmartResponse()

  // 获取响应类型（本地定义，因为不在context中）
  const _getResponseType = (metric: PerformanceMetrics): OptimizationType => {
    if (metric.responseTime < 100) return 'loading'
    if (metric.renderTime > metric.responseTime * 2) return 'rendering'
    if (metric.compressionRatio > 0.8) return 'compression'
    if (metric.cacheHit) return 'caching'
    if (metric.networkTime > metric.responseTime * 0.5) return 'network'
    return 'database'
  }

  if (metrics.length === 0) {
    return (
      <Card title="响应优化仪表板" style={{ margin: '24px' }}>
        <div style={{ textAlign: 'center', padding: '40px' }}>
          <Text type="secondary">暂无性能数据</Text>
        </div>
      </Card>
    )
  }

  const summary = generateReport()
  const { byType, byLevel } = summary.summary

  return (
    <Card title="智能响应优化" style={{ margin: '24px' }}>
      <Row gutter={[16, 16]}>
        <Col span={8}>
          <Card title="配置状态" size="small">
            <Space direction="vertical">
              <div>
                <Text>智能优化:</Text>
                <Switch
                  checked={config.enableOptimization}
                  onChange={(checked) => optimizeResponse({ ...config, enableOptimization: checked } as SmartResponseConfig)}
                />
              </div>
              <div>
                <Text>自动压缩:</Text>
                <Switch
                  checked={config.autoCompression}
                  disabled={!config.enableOptimization}
                />
              </div>
              <div>
                <Text>智能缓存:</Text>
                <Switch
                  checked={config.smartCaching}
                  disabled={!config.enableOptimization}
                />
              </div>
            </Space>

            <div style={{ marginTop: '16px' }}>
              <Button type="primary" onClick={resetConfig}>
                重置配置
              </Button>
              <Button onClick={() => setShowDetails(!showDetails)}>
                {showDetails ? '收起详情' : '展开详情'}
              </Button>
            </div>
          </Card>
        </Col>

        <Col span={16}>
          <Card title="性能统计" size="small">
            <Row gutter={[8, 8]}>
              <Col span={12}>
                <Statistic
                  title="总请求数"
                  value={metrics.length}
                  prefix={<ThunderboltOutlined />}
                />
              </Col>
              <Col span={12}>
                <Statistic
                  title="平均响应时间"
                  value={`${summary.summary.average.responseTime.toFixed(0)}ms`}
                  precision={0}
                  suffix="ms"
                  valueStyle={{
                    color: summary.summary.average.responseTime < 300 ? '#3f8600' : '#cf1322'
                  }}
                />
              </Col>
            </Row>

            <Row gutter={[8, 8]}>
              <Col span={8}>
                <Statistic
                  title="缓存命中率"
                  value={summary.summary.average.cacheHitRate}
                  precision={1}
                  suffix="%"
                  valueStyle={{
                    color: summary.summary.average.cacheHitRate > 80 ? '#52c41a' : '#faad14'
                  }}
                />
              </Col>
              <Col span={8}>
                <Statistic
                  title="压缩比"
                  value={summary.summary.average.compressionRatio}
                  precision={2}
                  suffix=""
                  formatter={(value) => `${value}%`}
                  valueStyle={{
                    color: summary.summary.average.compressionRatio > 30 ? '#52c41a' : '#fa8c16'
                  }}
                />
              </Col>
            </Row>
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginTop: '16px' }}>
        <Col span={12}>
          <Card title="性能等级分布" size="small">
            <Row gutter={[8, 8]}>
              {Object.entries(byLevel).map(([level, count]) => (
                <Col span={6} key={level}>
                  <div style={{
                    textAlign: 'center',
                    padding: '12px',
                    borderRadius: '4px',
                    backgroundColor: level === 'excellent' ? '#f6ffed' :
                                 level === 'good' ? '#b7eb8c' :
                                 level === 'acceptable' ? '#fff7e6' : '#ffcccc'
                  }}>
                    <Text style={{ color: level === 'excellent' || level === 'good' ? '#fff' : '#000' }}>
                      {level === 'excellent' ? '优秀' : level === 'good' ? '良好' : level === 'acceptable' ? '可接受' : '较差'}
                    </Text>
                  </div>
                  <div style={{ marginTop: '8px', fontSize: '18px', fontWeight: 'bold' }}>
                    {(count as number)}
                  </div>
                  <div style={{ marginTop: '4px', fontSize: '12px' }}>
                      {level === 'excellent' ? '优秀性能' :
                       level === 'good' ? '良好性能' :
                       level === 'acceptable' ? '可接受性能' : '需要优化'}
                  </div>
                </Col>
              ))}
            </Row>
          </Card>
        </Col>

        <Col span={12}>
          <Card title="优化类型分布" size="small">
            <Row gutter={[8, 8]}>
              {Object.entries(byType).map(([type, count]) => (
                <Col span={6} key={type}>
                  <div style={{
                    textAlign: 'center',
                    padding: '8px',
                    border: '1px solid #d9d9d9',
                    borderRadius: '4px',
                    cursor: 'pointer'
                  }}>
                    <Text style={{ fontWeight: 'bold' }}>
                      {type === 'loading' ? '加载' :
                       type === 'rendering' ? '渲染' :
                       type === 'compression' ? '压缩' :
                       type === 'caching' ? '缓存' :
                       type === 'network' ? '网络' : '数据库'}
                    </Text>
                  </div>
                  <div style={{ marginTop: '4px', fontSize: '20px' }}>
                    {(count as number)}
                  </div>
                </Col>
              ))}
            </Row>

            <div style={{ marginTop: '16px' }}>
              <Text type="secondary">
                点击性能类型可以查看详细优化建议
              </Text>
            </div>
          </Card>
        </Col>
      </Row>

      {showDetails && (
        <div style={{ marginTop: '16px' }}>
          <Card title="详细性能数据" size="small">
            <Space direction="vertical" style={{ width: '100%' }}>
              {metrics.slice(0, 10).map((metric, index) => (
                <div key={index} style={{
                  padding: '8px',
                  border: '1px solid #f0f0f0',
                  borderRadius: '4px',
                  marginBottom: '8px'
                }}>
                  <Row>
                    <Col span={8}>
                      <Text strong>请求时间:</Text>
                    </Col>
                    <Col span={4}>
                      <Text>{metric.responseTime.toFixed(2)}ms</Text>
                    </Col>
                    <Col span={4}>
                      <Text>
                        状态: {getResponseType(metric) === 'loading' ? '⏳' :
                             getResponseType(metric) === 'rendering' ? '🎨' :
                             getResponseType(metric) === 'compression' ? '📦' :
                             getResponseType(metric) === 'caching' ? '💾' :
                             '🌐'} {metric.cacheHit ? '✅' : '❌'}
                      </Text>
                    </Col>
                    <Col span={4}>
                      <Button size="small" onClick={() => {}}>
                        <EyeOutlined />
                      </Button>
                    </Col>
                  </Row>
                </div>
              ))}
            </Space>
          </Card>
        </div>
      )}
    </Card>
  )
}

export default SmartResponseProvider
export { ResponseOptimizationDashboard }