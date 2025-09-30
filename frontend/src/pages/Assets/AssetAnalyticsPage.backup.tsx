import React, { useState } from 'react'
import {
  Card,
  Row,
  Col,
  Spin,
  Alert,
  Empty,
  Typography,
  Space,
  Tag,
  Button,
  Statistic,
  message
} from 'antd'
import styles from './AssetAnalyticsPage.module.css'
import { useQuery } from '@tanstack/react-query'
import {
  ReloadOutlined,
  DownloadOutlined,
  FullscreenOutlined,
  SettingOutlined
} from '@ant-design/icons'
import { analyticsService, type AnalyticsData } from '@/services/analyticsService'
import { exportAnalyticsData } from '@/services/analyticsExportService'
import { AnalyticsStatsGrid, FinancialStatsGrid } from '@/components/Analytics/AnalyticsStatsCard'
import {
  AnalyticsPieChart,
  AnalyticsBarChart,
  AnalyticsLineChart,
  chartDataUtils
} from '@/components/Analytics/AnalyticsChart'
import AnalyticsFilters from '@/components/Analytics/AnalyticsFilters'
import type { AssetSearchParams } from '@/types/asset'

const AssetAnalyticsPage: React.FC = () => {
  const [filters, setFilters] = useState<AssetSearchParams>({})
  const [showAdvancedFilters, setShowAdvancedFilters] = useState(false)

  // 获取分析数据
  const { data: analyticsResponse, isLoading, error, refetch } = useQuery({
    queryKey: ['asset-analytics', filters],
    queryFn: async () => {
      const result = await analyticsService.getComprehensiveAnalytics(filters)
      console.log('API Result from service:', result)
      return result
    },
    staleTime: 5 * 60 * 1000, // 5分钟缓存
    refetchOnWindowFocus: false
  })
  console.log('UseQuery return structure:', { analyticsResponse, isLoading, error })

  // React Query 可能直接返回解析后的数据，也可能是包装在响应对象中
  // 我们需要检查两种可能性
  let analytics
  if (analyticsResponse && analyticsResponse.data) {
    // 标准情况：analyticsResponse 是 AnalyticsResponse 类型
    analytics = analyticsResponse.data
  } else if (analyticsResponse && analyticsResponse.area_summary) {
    // React Query 直接返回了 AnalyticsData
    analytics = analyticsResponse
  } else {
    // 没有数据
    analytics = null
  }

  console.log('Processed analytics data:', analytics)

  // 简化的调试日志 - 显示关键数据结构信息
  console.log('=== Analytics Data Processing ===')
  console.log('Data processing result:', {
    hasAnalytics: !!analytics,
    totalAssets: analytics?.area_summary?.total_assets
  })

  // 处理筛选条件变化
  const handleFilterChange = (newFilters: AssetSearchParams) => {
    setFilters(newFilters)
  }

  // 处理筛选条件重置
  const handleFilterReset = () => {
    setFilters({})
  }

  // 处理导出数据
  const handleExport = async () => {
    if (!analytics) return

    try {
      message.loading('正在导出数据...', 0)

      const exportData = {
        summary: {
          total_assets: analytics.area_summary.total_assets,
          total_area: analytics.area_summary.total_area,
          total_rentable_area: analytics.area_summary.total_rentable_area,
          occupancy_rate: analytics.area_summary.occupancy_rate,
          total_annual_income: analytics.financial_summary.total_annual_income,
          total_annual_expense: analytics.financial_summary.total_annual_expense,
          total_net_income: analytics.financial_summary.total_net_income,
          total_monthly_rent: analytics.financial_summary.total_monthly_rent
        },
        property_nature_distribution: analytics.property_nature_distribution,
        ownership_status_distribution: analytics.ownership_status_distribution,
        usage_status_distribution: analytics.usage_status_distribution,
        business_category_distribution: analytics.business_category_distribution,
        occupancy_trend: analytics.occupancy_trend
      }

      await exportAnalyticsData(exportData, 'excel')
      message.success('数据导出成功！')
    } catch (error) {
      console.error('导出失败:', error)
      message.error('导出失败，请重试')
    } finally {
      message.destroy()
    }
  }

  if (isLoading) {
    return (
      <div style={{ padding: '24px', textAlign: 'center' }}>
        <Spin size="large" tip="加载分析数据中..." />
      </div>
    )
  }

  if (error) {
    // 调试 - 显示错误详情
    console.error('Analytics Error:', error)
    return (
      <div style={{ padding: '24px' }}>
        <Alert
          message="数据加载失败"
          description={`错误详情: ${error instanceof Error ? error.message : '未知错误'}`}
          type="error"
          showIcon
        />
      </div>
    )
  }

  const hasData = analytics && analytics.area_summary && Number(analytics.area_summary.total_assets) > 0

  // 调试 - 显示数据检查结果
  console.log('Has Data Result:', hasData)
  console.log('Will show empty state:', !hasData)

  return (
    <div className={styles.analyticsContainer}>
      {/* 页面标题和操作栏 */}
      <Card style={{ marginBottom: '24px' }}>
        <Row justify="space-between" align={['middle', 'stretch']} gutter={[16, 16]}>
          <Col xs={24} sm={12}>
            <Typography.Title level={3} style={{ margin: 0 }}>
              资产分析
            </Typography.Title>
          </Col>
          <Col xs={24} sm={12}>
            <Space wrap className={styles.headerActions}>
              <Button
                icon={<ReloadOutlined />}
                onClick={() => refetch()}
                loading={isLoading}
                size="small"
                className="no-print"
              >
                <span className={styles.btnText}>刷新</span>
              </Button>
              <Button
                icon={<DownloadOutlined />}
                onClick={handleExport}
                disabled={!hasData}
                size="small"
                className="no-print"
              >
                <span className={styles.btnText}>导出</span>
              </Button>
              <Button
                icon={<FullscreenOutlined />}
                onClick={() => {
                  // TODO: 实现全屏功能
                }}
                size="small"
                className="no-print"
              >
                <span className={styles.btnText}>全屏</span>
              </Button>
            </Space>
          </Col>
        </Row>
      </Card>

      {/* 筛选条件 */}
      <AnalyticsFilters
        filters={filters}
        onFiltersChange={handleFilterChange}
        onResetFilters={handleFilterReset}
        loading={isLoading}
      />

      {!hasData ? (
        <Card>
          <Empty
            description="暂无数据"
            style={{ padding: '60px 0' }}
          >
            <p>数据库中还没有资产数据，请先录入资产信息</p>
          </Empty>
        </Card>
      ) : (
        <>
          {/* 概览统计卡片 */}
          <Card title="概览统计" style={{ marginBottom: '24px' }}>
            <AnalyticsStatsGrid
              data={{
                total_assets: analytics.area_summary.total_assets,
                total_area: analytics.area_summary.total_area,
                total_rentable_area: analytics.area_summary.total_rentable_area,
                occupancy_rate: analytics.area_summary.occupancy_rate,
                total_annual_income: analytics.financial_summary.total_annual_income,
                total_net_income: analytics.financial_summary.total_net_income,
                total_monthly_rent: analytics.financial_summary.total_monthly_rent
              }}
              loading={isLoading}
            />
          </Card>

          {/* 分布图表 */}
          <Row gutter={[16, 16]} style={{ marginBottom: '24px' }}>
            {/* 物业性质分布饼图 */}
            <Col xs={24} sm={12} xl={6}>
              <AnalyticsPieChart
                title="物业性质分布"
                data={chartDataUtils.toPieData(analytics.property_nature_distribution)}
                loading={isLoading}
                height={280}
              />
            </Col>

            {/* 确权状态分布饼图 */}
            <Col xs={24} sm={12} xl={6}>
              <AnalyticsPieChart
                title="确权状态分布"
                data={chartDataUtils.toPieData(analytics.ownership_status_distribution.map(item => ({
                  name: item.status,
                  count: item.count,
                  percentage: item.percentage
                })))}
                loading={isLoading}
                height={280}
              />
            </Col>

            {/* 使用状态分布柱状图 */}
            <Col xs={24} sm={12} xl={6}>
              <AnalyticsBarChart
                title="使用状态分布"
                data={analytics.usage_status_distribution.map(item => ({
                  name: item.status,
                  value: item.count
                }))}
                xAxisKey="name"
                barKey="value"
                loading={isLoading}
                height={280}
              />
            </Col>

            {/* 业态类别分布柱状图 */}
            <Col xs={24} sm={12} xl={6}>
              <AnalyticsBarChart
                title="业态类别分布"
                data={chartDataUtils.toBusinessCategoryData(analytics.business_category_distribution)}
                xAxisKey="name"
                barKey="value"
                loading={isLoading}
                height={280}
              />
            </Col>
          </Row>

          {/* 财务指标 */}
          <Card title="财务指标" style={{ marginBottom: '24px' }}>
            <FinancialStatsGrid
              data={analytics.financial_summary}
              loading={isLoading}
            />
          </Card>

          {/* 出租率趋势 */}
          {analytics.occupancy_trend && analytics.occupancy_trend.length > 0 && (
            <Card title="出租率趋势" style={{ marginBottom: '24px' }}>
              <AnalyticsLineChart
                title="出租率趋势"
                data={chartDataUtils.toTrendData(analytics.occupancy_trend)}
                lines={[
                  {
                    key: 'occupancy_rate',
                    name: '出租率 (%)',
                    color: '#1890ff'
                  }
                ]}
                xAxisKey="date"
                loading={isLoading}
                height={400}
              />
            </Card>
          )}

          {/* 详细数据表格 */}
          <Row gutter={[16, 16]}>
            <Col xs={24}>
              <Card title="分布详情">
                <Row gutter={[16, 16]}>
                  <Col xs={24} sm={12} lg={6}>
                    <Typography.Title level={5}>物业性质分布</Typography.Title>
                    <div className={styles.distributionList}>
                      {analytics.property_nature_distribution?.map((item, index) => (
                        <div key={index} className={styles.distributionItem}>
                          <span className={styles.itemName}>{item.name}</span>
                          <span className={styles.itemStats}>
                            {item.count} ({item.percentage}%)
                          </span>
                        </div>
                      ))}
                    </div>
                  </Col>

                  <Col xs={24} sm={12} lg={6}>
                    <Typography.Title level={5}>确权状态分布</Typography.Title>
                    <div className={styles.distributionList}>
                      {analytics.ownership_status_distribution?.map((item, index) => (
                        <div key={index} className={styles.distributionItem}>
                          <span className={styles.itemName}>{item.status}</span>
                          <span className={styles.itemStats}>
                            {item.count} ({item.percentage}%)
                          </span>
                        </div>
                      ))}
                    </div>
                  </Col>

                  <Col xs={24} sm={12} lg={6}>
                    <Typography.Title level={5}>使用状态分布</Typography.Title>
                    <div className={styles.distributionList}>
                      {analytics.usage_status_distribution?.map((item, index) => (
                        <div key={index} className={styles.distributionItem}>
                          <span className={styles.itemName}>{item.status}</span>
                          <span className={styles.itemStats}>
                            {item.count} ({item.percentage}%)
                          </span>
                        </div>
                      ))}
                    </div>
                  </Col>

                  <Col xs={24} sm={12} lg={6}>
                    <Typography.Title level={5}>业态类别分布</Typography.Title>
                    <div className={styles.distributionList}>
                      {analytics.business_category_distribution?.map((item, index) => (
                        <div key={index} className={styles.distributionItem}>
                          <span className={styles.itemName}>{item.category}</span>
                          <span className={styles.itemStats}>
                            {item.count} <span className={styles.occupancyRate}>(出租率: {item.occupancy_rate}%)</span>
                          </span>
                        </div>
                      ))}
                    </div>
                  </Col>
                </Row>
              </Card>
            </Col>
          </Row>
        </>
      )}
    </div>
  )
}

export default AssetAnalyticsPage

// 触发热重载 - 修复接口类型匹配问题