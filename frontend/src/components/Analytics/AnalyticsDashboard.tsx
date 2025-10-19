import React, { useState, useMemo } from 'react'
import { Row, Col, Card, Typography, Button, Space, Dropdown, Menu } from 'antd'
import {
  ReloadOutlined,
  DownloadOutlined,
  SettingOutlined,
  FullscreenOutlined,
  FullscreenExitOutlined
} from '@ant-design/icons'
import { useAnalytics } from '../../hooks/useAnalytics'
import type { AssetSearchParams } from '../../types/asset'

import { AnalyticsFilters } from './AnalyticsFilters'
import { StatisticCard, FinancialStatisticCard } from './StatisticCard'
import { ChartCard } from './AnalyticsCard'
import {
  AnalyticsPieChart,
  AnalyticsBarChart,
  AnalyticsLineChart
} from './Charts'
import AdvancedAnalyticsCard from './AdvancedAnalyticsCard'
import { PerformanceMonitor } from './PerformanceMonitor'

const { Title } = Typography

interface AnalyticsDashboardProps {
  initialFilters?: AssetSearchParams
  className?: string
}

export const AnalyticsDashboard: React.FC<AnalyticsDashboardProps> = ({
  initialFilters = {},
  className = ''
}) => {
  const [filters, setFilters] = useState<AssetSearchParams>(initialFilters)
  const [showAdvanced, setShowAdvanced] = useState(false)
  const [fullscreen, setFullscreen] = useState(false)
  const [autoRefresh, setAutoRefresh] = useState(false)

  const { data: analyticsResponse, isLoading, error, refetch } = useAnalytics(filters)
  const analytics = analyticsResponse?.data

  const hasData = analytics?.area_summary?.total_assets && analytics.area_summary.total_assets > 0

  // 导出选项 - removed unused variable

  const handleExport = (format: 'excel' | 'pdf' | 'csv') => {
    // 实现导出逻辑
    console.log(`Exporting as ${format}`, { filters, analytics })
  }

  const handleRefresh = () => {
    refetch()
  }

  const handleFullscreenToggle = () => {
    setFullscreen(!fullscreen)
  }

  const toggleAutoRefresh = () => {
    setAutoRefresh(!autoRefresh)
  }

  const handleFiltersChange = (newFilters: AssetSearchParams) => {
    setFilters(newFilters)
  }

  const handleApplyFilters = () => {
    refetch()
  }

  const handleResetFilters = () => {
    setFilters({})
    refetch()
  }

  const toggleAdvancedFilters = () => {
    setShowAdvanced(!showAdvanced)
  }

  // 导出菜单
  const exportMenu = (
    <Menu
      items={[
        {
          key: 'excel',
          label: '导出为 Excel',
          onClick: () => handleExport('excel')
        },
        {
          key: 'pdf',
          label: '导出为 PDF',
          onClick: () => handleExport('pdf')
        },
        {
          key: 'csv',
          label: '导出为 CSV',
          onClick: () => handleExport('csv')
        }
      ]}
    />
  )

  // 关键指标数据
  const keyMetrics = useMemo(() => {
    if (!analytics) return []

    return [
      {
        title: '资产总数',
        value: analytics.area_summary.total_assets,
        suffix: '个',
        precision: 0
      },
      {
        title: '总面积',
        value: analytics.area_summary.total_area,
        suffix: '㎡',
        precision: 2
      },
      {
        title: '可租面积',
        value: analytics.area_summary.total_rentable_area,
        suffix: '㎡',
        precision: 2
      },
      {
        title: '整体出租率',
        value: analytics.area_summary.occupancy_rate,
        suffix: '%',
        precision: 2
      }
    ]
  }, [analytics])

  // 财务指标数据
  const financialMetrics = useMemo(() => {
    if (!analytics) return []

    return [
      {
        title: '年收入',
        value: analytics.financial_summary.total_annual_income,
        suffix: '元',
        precision: 2,
        isPositive: true
      },
      {
        title: '年支出',
        value: analytics.financial_summary.total_annual_expense,
        suffix: '元',
        precision: 2,
        isPositive: false
      },
      {
        title: '净收益',
        value: analytics.financial_summary.total_net_income,
        suffix: '元',
        precision: 2,
        isPositive: analytics.financial_summary.total_net_income >= 0
      },
      {
        title: '月租金',
        value: analytics.financial_summary.total_monthly_rent,
        suffix: '元',
        precision: 2,
        isPositive: true
      }
    ]
  }, [analytics])

  if (error) {
    return (
      <Card className={className}>
        <div style={{ textAlign: 'center', padding: '60px 0' }}>
          <Title level={4} type="danger">数据加载失败</Title>
          <p>请检查网络连接或联系管理员</p>
          <Button type="primary" onClick={handleRefresh}>
            重试
          </Button>
        </div>
      </Card>
    )
  }

  return (
    <div className={className} style={{
      padding: fullscreen ? '0' : '24px',
      background: fullscreen ? '#f0f2f5' : 'transparent'
    }}>
      {/* 性能监控 */}
      <PerformanceMonitor enabled={process.env.NODE_ENV === 'development'} />

      {/* 头部操作栏 */}
      <Row gutter={[16, 16]} style={{ marginBottom: '24px' }}>
        <Col xs={24} md={12}>
          <Title level={2}>资产分析</Title>
        </Col>
        <Col xs={24} md={12} style={{ textAlign: 'right' }}>
          <Space>
            <Button
              icon={<ReloadOutlined />}
              onClick={handleRefresh}
              loading={isLoading}
            >
              刷新
            </Button>
            <Dropdown overlay={exportMenu} placement="bottomRight">
              <Button icon={<DownloadOutlined />}>
                导出
              </Button>
            </Dropdown>
            <Button
              icon={fullscreen ? <FullscreenExitOutlined /> : <FullscreenOutlined />}
              onClick={handleFullscreenToggle}
            >
              {fullscreen ? '退出全屏' : '全屏'}
            </Button>
            <Button
              icon={<SettingOutlined />}
              onClick={toggleAutoRefresh}
              type={autoRefresh ? 'primary' : 'default'}
            >
              自动刷新
            </Button>
          </Space>
        </Col>
      </Row>

      {/* 筛选器 */}
      <AnalyticsFilters
        filters={filters}
        onFiltersChange={handleFiltersChange}
        onApplyFilters={handleApplyFilters}
        onResetFilters={handleResetFilters}
        loading={isLoading}
        showAdvanced={showAdvanced}
        onToggleAdvanced={toggleAdvancedFilters}
      />

      {!hasData ? (
        <Card>
          <div style={{ textAlign: 'center', padding: '60px 0' }}>
            <Title level={4}>暂无数据</Title>
            <p>数据库中还没有资产数据，请先录入资产信息</p>
          </div>
        </Card>
      ) : (
        <>
          {/* 关键指标概览 */}
          <Row gutter={[16, 16]} style={{ marginBottom: '24px' }}>
            {keyMetrics.map((metric, index) => (
              <Col xs={24} sm={6} key={index}>
                <StatisticCard
                  title={metric.title}
                  value={metric.value}
                  precision={metric.precision}
                  suffix={metric.suffix}
                  loading={isLoading}
                />
              </Col>
            ))}
          </Row>

          {/* 高级分析指标 */}
          {analytics?.performance_metrics && (
            <Row gutter={[16, 16]} style={{ marginBottom: '24px' }}>
              <Col xs={24}>
                <AdvancedAnalyticsCard
                  performanceMetrics={analytics.performance_metrics}
                  comparisonData={analytics.comparison_data}
                  loading={isLoading}
                />
              </Col>
            </Row>
          )}

          {/* 财务指标 */}
          <Row gutter={[16, 16]} style={{ marginBottom: '24px' }}>
            {financialMetrics.map((metric, index) => (
              <Col xs={24} sm={6} key={index}>
                <FinancialStatisticCard
                  title={metric.title}
                  value={metric.value}
                  precision={metric.precision}
                  suffix={metric.suffix}
                  isPositive={metric.isPositive}
                  loading={isLoading}
                />
              </Col>
            ))}
          </Row>

          {/* 图表区域 */}
          <Row gutter={[16, 16]}>
            {/* 物业性质分布 */}
            <Col xs={24} lg={12}>
              <ChartCard
                title="物业性质分布"
                hasData={analytics?.property_nature_distribution?.length > 0}
                loading={isLoading}
              >
                <AnalyticsPieChart
                  data={analytics?.property_nature_distribution?.map(item => ({ name: item.name, value: item.count, percentage: item.percentage })) || []}
                  dataKey="value"
                  labelKey="name"
                />
              </ChartCard>
            </Col>

            {/* 确权状态分布 */}
            <Col xs={24} lg={12}>
              <ChartCard
                title="确权状态分布"
                hasData={analytics?.ownership_status_distribution?.length > 0}
                loading={isLoading}
              >
                <AnalyticsBarChart
                  data={analytics?.ownership_status_distribution || []}
                  xDataKey="status"
                  yDataKey="count"
                  barName="资产数量"
                />
              </ChartCard>
            </Col>

            {/* 使用状态分布 */}
            <Col xs={24} lg={12}>
              <ChartCard
                title="使用状态分布"
                hasData={analytics?.usage_status_distribution?.length > 0}
                loading={isLoading}
              >
                <AnalyticsPieChart
                  data={analytics?.usage_status_distribution?.map(item => ({
                    name: item.status,
                    value: item.count,
                    percentage: item.percentage
                  })) || []}
                  dataKey="value"
                  labelKey="name"
                />
              </ChartCard>
            </Col>

            {/* 出租率分布 */}
            <Col xs={24} lg={12}>
              <ChartCard
                title="出租率区间分布"
                hasData={analytics?.occupancy_distribution?.length > 0}
                loading={isLoading}
              >
                <AnalyticsBarChart
                  data={analytics?.occupancy_distribution || []}
                  xDataKey="range"
                  yDataKey="count"
                  barName="资产数量"
                  isPercentage={false}
                />
              </ChartCard>
            </Col>

            {/* 业态类别分析 */}
            <Col xs={24} lg={12}>
              <ChartCard
                title="业态类别出租率"
                hasData={analytics?.business_category_distribution?.length > 0}
                loading={isLoading}
              >
                <AnalyticsBarChart
                  data={analytics?.business_category_distribution || []}
                  xDataKey="category"
                  yDataKey="occupancy_rate"
                  barName="出租率"
                  isPercentage={true}
                />
              </ChartCard>
            </Col>

            {/* 出租率趋势 */}
            <Col xs={24} lg={12}>
              <ChartCard
                title="出租率趋势"
                hasData={analytics?.occupancy_trend?.length > 0}
                loading={isLoading}
              >
                <AnalyticsLineChart
                  data={analytics?.occupancy_trend || []}
                  xDataKey="date"
                  yDataKey="occupancy_rate"
                  lineName="出租率"
                  isPercentage={true}
                />
              </ChartCard>
            </Col>
          </Row>
        </>
      )}
    </div>
  )
}

export default AnalyticsDashboard