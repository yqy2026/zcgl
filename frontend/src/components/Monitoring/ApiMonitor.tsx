/**
 * API监控组件
 * 显示API健康状态和实时监控信息
 */

import React, { useState, useEffect } from 'react'
import { Card, Row, Col, Statistic, Alert, Table, Tag, Progress, Button } from 'antd'
import { CloudServerOutlined, CheckCircleOutlined, ExclamationCircleOutlined, ReloadOutlined } from '@ant-design/icons'
import { createLogger } from '../../utils/logger'
// TODO: Create apiHealthCheck service or remove this component
// import { apiHealthCheck } from '../services/apiHealthCheck'

const componentLogger = createLogger('ApiMonitor')

interface ApiStatus {
  endpoint: string
  status: 'healthy' | 'unhealthy' | 'unknown'
  responseTime?: number
  error?: string
  lastChecked: Date
}

const ApiMonitor: React.FC = () => {
  const [loading, setLoading] = useState(false)
  const [apiStatus, setApiStatus] = useState<ApiStatus[]>([])
  const [summary, setSummary] = useState({
    total: 0,
    healthy: 0,
    unhealthy: 0,
    unknown: 0,
    healthPercentage: 0
  })

  const loadApiStatus = async () => {
    setLoading(true)
    try {
      // TODO: Implement apiHealthCheck service
      // const results = await apiHealthCheck.checkCriticalEndpoints()
      // const statusArray = Array.from(apiHealthCheck.getResults().values())

      // Mock data for now
      const mockResults: ApiStatus[] = []
      const results: ApiStatus[] = []

      setApiStatus(mockResults)
      setSummary({
        total: results.length,
        healthy: results.filter((r: ApiStatus) => r.status === 'healthy').length,
        unhealthy: results.filter((r: ApiStatus) => r.status === 'unhealthy').length,
        unknown: results.filter((r: ApiStatus) => r.status === 'unknown').length,
        healthPercentage: results.length > 0 ? (results.filter((r: ApiStatus) => r.status === 'healthy').length / results.length) * 100 : 0
      })
    } catch (error) {
      componentLogger.error('Failed to load API status:', error as Error)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadApiStatus()
    // 每30秒自动刷新一次
    const interval = setInterval(loadApiStatus, 30000)
    return () => clearInterval(interval)
  }, [])

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'healthy': return 'green'
      case 'unhealthy': return 'red'
      case 'unknown': return 'orange'
      default: return 'default'
    }
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'healthy': return <CheckCircleOutlined style={{ color: '#52c41a' }} />
      case 'unhealthy': return <ExclamationCircleOutlined style={{ color: '#ff4d4f' }} />
      case 'unknown': return <CloudServerOutlined style={{ color: '#fa8c16' }} />
      default: return <CloudServerOutlined />
    }
  }

  const formatResponseTime = (time?: number) => {
    if (time == null) return '-'
    if (time < 1000) return `${time}ms`
    return `${(time / 1000).toFixed(2)}s`
  }

  const columns = [
    {
      title: '端点',
      dataIndex: 'endpoint',
      key: 'endpoint',
      width: 200,
      render: (text: string) => <code style={{ fontSize: '12px' }}>{text}</code>
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: string) => (
        <Tag color={getStatusColor(status)} icon={getStatusIcon(status)}>
          {status.toUpperCase()}
        </Tag>
      )
    },
    {
      title: '响应时间',
      dataIndex: 'responseTime',
      key: 'responseTime',
      width: 120,
      render: (time?: number) => (
        <span style={{ color: (time ?? 0) > 3000 ? '#ff4d4f' : (time ?? 0) > 1000 ? '#fa8c16' : '#52c41a' }}>
          {formatResponseTime(time)}
        </span>
      )
    },
    {
      title: '错误信息',
      dataIndex: 'error',
      key: 'error',
      ellipsis: true,
      render: (error?: string) => (error != null && error !== '') ? <span style={{ color: '#ff4d4f' }}>{error}</span> : '-'
    },
    {
      title: '最后检查',
      dataIndex: 'lastChecked',
      key: 'lastChecked',
      width: 150,
      render: (date: Date) => new Date(date).toLocaleTimeString()
    }
  ]

  const getHealthStatusColor = (percentage: number) => {
    if (percentage >= 80) return '#52c41a'
    if (percentage >= 60) return '#fa8c16'
    return '#ff4d4f'
  }

  return (
    <div style={{ padding: '24px' }}>
      <div style={{ marginBottom: '24px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h2>API健康监控</h2>
        <Button
          type="primary"
          icon={<ReloadOutlined />}
          loading={loading}
          onClick={loadApiStatus}
        >
          刷新状态
        </Button>
      </div>

      {/* 总体状态概览 */}
      <Row gutter={16} style={{ marginBottom: '24px' }}>
        <Col span={6}>
          <Card>
            <Statistic
              title="总体健康度"
              value={summary.healthPercentage}
              precision={1}
              suffix="%"
              valueStyle={{ color: getHealthStatusColor(summary.healthPercentage) }}
              prefix={<CloudServerOutlined />}
            />
            <Progress
              percent={summary.healthPercentage}
              strokeColor={getHealthStatusColor(summary.healthPercentage)}
              showInfo={false}
              size="small"
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="健康端点"
              value={summary.healthy}
              valueStyle={{ color: '#52c41a' }}
              prefix={<CheckCircleOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="异常端点"
              value={summary.unhealthy}
              valueStyle={{ color: '#ff4d4f' }}
              prefix={<ExclamationCircleOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="未知状态"
              value={summary.unknown}
              valueStyle={{ color: '#fa8c16' }}
              prefix={<CloudServerOutlined />}
            />
          </Card>
        </Col>
      </Row>

      {/* 健康状态警告 */}
      {summary.healthPercentage < 80 && (
        <Alert
          message="API健康状况需要关注"
          description={`当前API健康度为${summary.healthPercentage.toFixed(1)}%，低于80%的健康阈值。建议检查异常端点并采取相应措施。`}
          type="warning"
          showIcon
          style={{ marginBottom: '24px' }}
        />
      )}

      {summary.healthPercentage < 60 && (
        <Alert
          message="API健康状况严重"
          description={`当前API健康度仅为${summary.healthPercentage.toFixed(1)}%，系统可能存在严重问题。建议立即检查所有API端点状态。`}
          type="error"
          showIcon
          style={{ marginBottom: '24px' }}
        />
      )}

      {/* 详细状态表格 */}
      <Card title="端点详细状态" size="small">
        <Table
          columns={columns}
          dataSource={apiStatus}
          rowKey="endpoint"
          loading={loading}
          pagination={{
            pageSize: 10,
            showSizeChanger: true,
            showQuickJumper: true,
            showTotal: (total: number) => `共 ${total} 个端点`
          }}
          size="small"
        />
      </Card>

      {/* 监控说明 */}
      <Card title="监控说明" size="small" style={{ marginTop: '24px' }}>
        <div style={{ fontSize: '14px', color: '#666' }}>
          <p><strong>监控范围：</strong>系统关键API端点</p>
          <p><strong>检查频率：</strong>每30秒自动刷新一次</p>
          <p><strong>健康标准：</strong></p>
          <ul style={{ marginLeft: '20px', marginTop: '8px' }}>
            <li><span style={{ color: '#52c41a' }}>绿色</span>：响应正常（2xx状态码，响应时间&lt;3秒）</li>
            <li><span style={{ color: '#ff4d4f' }}>红色</span>：端点不可用（404、500等错误）</li>
            <li><span style={{ color: '#fa8c16' }}>橙色</span>：状态未知（检查失败或超时）</li>
          </ul>
          <p><strong>建议：</strong>当健康度低于80%时需要关注，低于60%时需要立即处理。</p>
        </div>
      </Card>
    </div>
  )
}

export default ApiMonitor
