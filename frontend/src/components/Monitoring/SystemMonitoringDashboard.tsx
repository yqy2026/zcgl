/**
 * 系统监控仪表板组件
 *
 * 功能特性:
 * - 实时系统性能监控
 * - 应用性能指标展示
 * - 健康状态检查
 * - 告警管理
 * - 性能趋势分析
 *
 * @author Claude Code
 * @created 2025-11-01
 */

import React, { useState, useCallback, useMemo } from 'react'
import { Card, Row, Col, Statistic, Progress, Alert, Tag, Button, Space, Tooltip, List, Badge } from 'antd'
import {
  MonitorOutlined,
  AlertOutlined,
  ReloadOutlined,
  SettingOutlined,
  RiseOutlined,
  FallOutlined,
  MinusOutlined
} from '@ant-design/icons'
import { Line, Gauge } from '@ant-design/plots'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'

import { monitoringService } from '@/services/monitoringService'

// 类型定义
interface SystemMetrics {
  timestamp: string
  cpu_percent: number
  memory_percent: number
  memory_available_gb: number
  disk_usage_percent: number
  disk_free_gb: number
  network_io: Record<string, number>
  process_count: number
  load_average?: number[]
}

interface ApplicationMetrics {
  timestamp: string
  active_connections: number
  total_requests: number
  average_response_time: number
  error_rate: number
  cache_hit_rate: number
  database_connections: number
}

interface HealthStatus {
  status: 'healthy' | 'degraded' | 'unhealthy'
  timestamp: string
  components: Record<string, unknown>
  overall_score: number
}

interface PerformanceAlert {
  id: string
  level: 'info' | 'warning' | 'critical'
  message: string
  metric_name: string
  current_value: number
  threshold: number
  timestamp: string
  resolved: boolean
}

// 图表数据点接口
interface ChartDataPoint {
  time: string
  value: number
  category?: string
}

interface DashboardData {
  current_system: SystemMetrics
  current_application: ApplicationMetrics
  health_status: HealthStatus
  active_alerts: PerformanceAlert[]
  trends: {
    system_metrics: SystemMetrics[]
    application_metrics: ApplicationMetrics[]
  }
  summary: {
    total_alerts: number
    critical_alerts: number
    warning_alerts: number
    health_score: number
    last_updated: string
  }
}

const SystemMonitoringDashboard: React.FC = () => {
  const [refreshInterval, _setRefreshInterval] = useState(30000) // 30秒刷新
  const [autoRefresh, setAutoRefresh] = useState(true)
  const [_selectedTimeRange, _setSelectedTimeRange] = useState(24) // 小时

  const queryClient = useQueryClient()

  // 获取仪表板数据
  const {
    data: dashboardData,
    isLoading,
    error,
    refetch
  } = useQuery<DashboardData>({
    queryKey: ['monitoring-dashboard'],
    queryFn: () => monitoringService.getDashboardData(),
    refetchInterval: autoRefresh ? refreshInterval : false,
    retry: 3,
    retryDelay: 1000
  })

  // 手动刷新
  const handleRefresh = useCallback(() => {
    refetch()
  }, [refetch])

  // 解决告警
  const resolveAlertMutation = useMutation({
    mutationFn: (alertId: string) => monitoringService.resolveAlert(alertId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['monitoring-dashboard'] })
    }
  })

  // 获取状态颜色
  const getStatusColor = (status: string) => {
    const colors = {
      healthy: '#52c41a',
      degraded: '#faad14',
      unhealthy: '#ff4d4f',
      normal: '#52c41a',
      warning: '#faad14',
      critical: '#ff4d4f'
    }
    return colors[status as keyof typeof colors] || '#d9d9d9'
  }

  // 获取告警级别颜色
  const getAlertLevelColor = (level: string) => {
    const colors = {
      info: '#1890ff',
      warning: '#faad14',
      critical: '#ff4d4f'
    }
    return colors[level as keyof typeof colors] || '#d9d9d9'
  }

  // 获取趋势图标
  const _getTrendIcon = (trend: number) => {
    if (trend > 5) return <RiseOutlined style={{ color: '#ff4d4f' }} />
    if (trend < -5) return <FallOutlined style={{ color: '#52c41a' }} />
    return <MinusOutlined style={{ color: '#d9d9d9' }} />
  }

  // 格式化网络IO
  const _formatNetworkIO = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
    return `${(bytes / (1024 * 1024 * 1024)).toFixed(1)} GB`
  }

  // CPU使用率图表配置
  const cpuChartData = useMemo(() => {
    if (!dashboardData?.trends?.system_metrics) return []
    return dashboardData.trends.system_metrics.map(item => ({
      time: new Date(item.timestamp).toLocaleTimeString(),
      value: item.cpu_percent
    }))
  }, [dashboardData])

  const cpuChartConfig = {
    data: cpuChartData,
    xField: 'time',
    yField: 'value',
    smooth: true,
    color: '#1890ff',
    annotations: [
      {
        type: 'line',
        start: ['min', 80],
        end: ['max', 80],
        style: { stroke: '#ff4d4f', lineDash: [2, 2] }
      }
    ],
    tooltip: {
      formatter: (datum: ChartDataPoint) => ({
        name: 'CPU使用率',
        value: `${datum.value}%`
      })
    }
  }

  // 内存使用率图表配置
  const memoryChartData = useMemo(() => {
    if (!dashboardData?.trends?.system_metrics) return []
    return dashboardData.trends.system_metrics.map(item => ({
      time: new Date(item.timestamp).toLocaleTimeString(),
      value: item.memory_percent
    }))
  }, [dashboardData])

  const memoryChartConfig = {
    data: memoryChartData,
    xField: 'time',
    yField: 'value',
    smooth: true,
    color: '#52c41a',
    annotations: [
      {
        type: 'line',
        start: ['min', 85],
        end: ['max', 85],
        style: { stroke: '#ff4d4f', lineDash: [2, 2] }
      }
    ],
    tooltip: {
      formatter: (datum: ChartDataPoint) => ({
        name: '内存使用率',
        value: `${datum.value}%`
      })
    }
  }

  // 响应时间图表配置
  const responseTimeChartData = useMemo(() => {
    if (!dashboardData?.trends?.application_metrics) return []
    return dashboardData.trends.application_metrics.map(item => ({
      time: new Date(item.timestamp).toLocaleTimeString(),
      value: item.average_response_time
    }))
  }, [dashboardData])

  const responseTimeChartConfig = {
    data: responseTimeChartData,
    xField: 'time',
    yField: 'value',
    smooth: true,
    color: '#faad14',
    annotations: [
      {
        type: 'line',
        start: ['min', 1000],
        end: ['max', 1000],
        style: { stroke: '#ff4d4f', lineDash: [2, 2] }
      }
    ],
    tooltip: {
      formatter: (datum: ChartDataPoint) => ({
        name: '响应时间',
        value: `${datum.value}ms`
      })
    }
  }

  // 健康评分仪表盘配置
  const healthGaugeConfig = useMemo(() => ({
    percent: ((dashboardData?.health_status?.overall_score ?? 0) / 100),
    color: getStatusColor(dashboardData?.health_status?.status ?? 'unknown'),
    indicator: {
      pointer: { style: { stroke: '#D0D0D0' } },
      pin: { style: { stroke: '#D0D0D0' } }
    },
    statistic: {
      content: {
        style: { fontSize: '36px', lineHeight: '36px' },
        formatter: () => `${dashboardData?.health_status?.overall_score ?? 0}%`
      }
    }
  }), [dashboardData])

  if (error !== undefined && error !== null) {
    return (
      <Alert
        message="监控数据加载失败"
        description="无法获取系统监控数据，请检查网络连接或联系管理员"
        type="error"
        showIcon
        action={
          <Button size="small" onClick={handleRefresh}>
            重试
          </Button>
        }
      />
    )
  }

  return (
    <div className="system-monitoring-dashboard">
      {/* 头部工具栏 */}
      <Row justify="space-between" align="middle" style={{ marginBottom: 16 }}>
        <Col>
          <Space>
            <MonitorOutlined style={{ fontSize: 24, color: '#1890ff' }} />
            <h2 style={{ margin: 0 }}>系统监控仪表板</h2>
            {dashboardData?.summary && (
              <Tag color={getStatusColor(dashboardData.health_status.status)}>
                {dashboardData.health_status.status.toUpperCase()}
              </Tag>
            )}
          </Space>
        </Col>
        <Col>
          <Space>
            <Tooltip title="自动刷新">
              <Button
                type={autoRefresh ? 'primary' : 'default'}
                size="small"
                onClick={() => setAutoRefresh(!autoRefresh)}
              >
                自动刷新: {autoRefresh ? '开启' : '关闭'}
              </Button>
            </Tooltip>
            <Button
              icon={<ReloadOutlined />}
              size="small"
              onClick={handleRefresh}
              loading={isLoading}
            >
              刷新
            </Button>
            <Button
              icon={<SettingOutlined />}
              size="small"
              onClick={() => {/* 打开设置 */}}
            >
              设置
            </Button>
          </Space>
        </Col>
      </Row>

      {/* 系统概览 */}
      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col span={6}>
          <Card size="small">
            <Statistic
              title="CPU使用率"
              value={dashboardData?.current_system?.cpu_percent ?? 0}
              suffix="%"
              valueStyle={{ color: getStatusColor(
                (dashboardData?.current_system?.cpu_percent ?? 0) > 80 ? 'critical' : 'normal'
              )}}
            />
            <Progress
              percent={dashboardData?.current_system?.cpu_percent ?? 0}
              showInfo={false}
              strokeColor={getStatusColor(
                (dashboardData?.current_system?.cpu_percent ?? 0) > 80 ? 'critical' : 'normal'
              )}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small">
            <Statistic
              title="内存使用率"
              value={dashboardData?.current_system?.memory_percent ?? 0}
              suffix="%"
              valueStyle={{ color: getStatusColor(
                (dashboardData?.current_system?.memory_percent ?? 0) > 85 ? 'critical' : 'normal'
              )}}
            />
            <Progress
              percent={dashboardData?.current_system?.memory_percent ?? 0}
              showInfo={false}
              strokeColor={getStatusColor(
                (dashboardData?.current_system?.memory_percent ?? 0) > 85 ? 'critical' : 'normal'
              )}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small">
            <Statistic
              title="磁盘使用率"
              value={dashboardData?.current_system?.disk_usage_percent ?? 0}
              suffix="%"
              valueStyle={{ color: getStatusColor(
                (dashboardData?.current_system?.disk_usage_percent ?? 0) > 90 ? 'critical' : 'normal'
              )}}
            />
            <Progress
              percent={dashboardData?.current_system?.disk_usage_percent ?? 0}
              showInfo={false}
              strokeColor={getStatusColor(
                (dashboardData?.current_system?.disk_usage_percent ?? 0) > 90 ? 'critical' : 'normal'
              )}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small">
            <Statistic
              title="活跃连接"
              value={dashboardData?.current_application?.active_connections ?? 0}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
      </Row>

      {/* 健康状态和告警 */}
      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col span={8}>
          <Card title="系统健康状态" size="small">
            <div style={{ textAlign: 'center', padding: '20px 0' }}>
              <Gauge {...healthGaugeConfig} height={200} />
              <div style={{ marginTop: 16 }}>
                <Tag color={getStatusColor(dashboardData?.health_status?.status ?? 'unknown')}>
                  {(dashboardData?.health_status?.status ?? 'unknown').toUpperCase()}
                </Tag>
              </div>
            </div>
          </Card>
        </Col>
        <Col span={16}>
          <Card
            title={
              <Space>
                <AlertOutlined />
                活跃告警
                <Badge count={dashboardData?.summary?.total_alerts ?? 0} />
              </Space>
            }
            size="small"
          >
            <List
              size="small"
              dataSource={dashboardData?.active_alerts?.slice(0, 5) ?? []}
              renderItem={(alert: PerformanceAlert) => (
                <List.Item
                  actions={[
                    !alert.resolved && (
                      <Button
                        size="small"
                        type="text"
                        onClick={() => resolveAlertMutation.mutate(alert.id)}
                        loading={resolveAlertMutation.isPending}
                      >
                        解决
                      </Button>
                    )
                  ].filter(Boolean)}
                >
                  <List.Item.Meta
                    avatar={
                      <Badge
                        dot={!alert.resolved}
                        color={getAlertLevelColor(alert.level)}
                      />
                    }
                    title={
                      <Space>
                        <Tag color={getAlertLevelColor(alert.level)}>
                          {alert.level.toUpperCase()}
                        </Tag>
                        <span>{alert.metric_name}</span>
                      </Space>
                    }
                    description={alert.message}
                  />
                </List.Item>
              )}
              locale={{ emptyText: '暂无告警' }}
            />
          </Card>
        </Col>
      </Row>

      {/* 性能图表 */}
      <Row gutter={[16, 16]}>
        <Col span={8}>
          <Card title="CPU使用率趋势" size="small">
            <Line {...cpuChartConfig} height={200} />
          </Card>
        </Col>
        <Col span={8}>
          <Card title="内存使用率趋势" size="small">
            <Line {...memoryChartConfig} height={200} />
          </Card>
        </Col>
        <Col span={8}>
          <Card title="响应时间趋势" size="small">
            <Line {...responseTimeChartConfig} height={200} />
          </Card>
        </Col>
      </Row>

      {/* 详细信息 */}
      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col span={12}>
          <Card title="系统详细信息" size="small">
            <Row gutter={[16, 8]}>
              <Col span={12}>
                <Statistic
                  title="可用内存"
                  value={dashboardData?.current_system?.memory_available_gb ?? 0}
                  suffix="GB"
                  precision={1}
                />
              </Col>
              <Col span={12}>
                <Statistic
                  title="可用磁盘"
                  value={dashboardData?.current_system?.disk_free_gb ?? 0}
                  suffix="GB"
                  precision={1}
                />
              </Col>
              <Col span={12}>
                <Statistic
                  title="进程数"
                  value={dashboardData?.current_system?.process_count ?? 0}
                />
              </Col>
              <Col span={12}>
                <Statistic
                  title="系统负载"
                  value={dashboardData?.current_system?.load_average?.[0] ?? 0}
                  precision={2}
                />
              </Col>
            </Row>
          </Card>
        </Col>
        <Col span={12}>
          <Card title="应用详细信息" size="small">
            <Row gutter={[16, 8]}>
              <Col span={12}>
                <Statistic
                  title="总请求数"
                  value={dashboardData?.current_application?.total_requests ?? 0}
                />
              </Col>
              <Col span={12}>
                <Statistic
                  title="平均响应时间"
                  value={dashboardData?.current_application?.average_response_time ?? 0}
                  suffix="ms"
                  precision={1}
                />
              </Col>
              <Col span={12}>
                <Statistic
                  title="错误率"
                  value={dashboardData?.current_application?.error_rate ?? 0}
                  suffix="%"
                  precision={2}
                  valueStyle={{
                    color: getStatusColor(
                      (dashboardData?.current_application?.error_rate ?? 0) > 5 ? 'critical' : 'normal'
                    )
                  }}
                />
              </Col>
              <Col span={12}>
                <Statistic
                  title="缓存命中率"
                  value={dashboardData?.current_application?.cache_hit_rate ?? 0}
                  suffix="%"
                  precision={1}
                />
              </Col>
            </Row>
          </Card>
        </Col>
      </Row>
    </div>
  )
}

export default SystemMonitoringDashboard