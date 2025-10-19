import React, { useState } from 'react'
import { Card, Row, Col, Spin, Alert, Empty, Typography, Space, Tag, Button, Statistic, message, Switch, Radio } from 'antd'
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

const { Title, Text } = Typography

// 分析维度类型
type AnalysisDimension = 'count' | 'area'

const AssetAnalyticsPage: React.FC = () => {
  const [filters, setFilters] = useState<AssetSearchParams>({})
  const [showAdvancedFilters, setShowAdvancedFilters] = useState(false)
  const [dimension, setDimension] = useState<AnalysisDimension>('area')

  // 获取分析数据
  const { data: analyticsResponse, isLoading, error, refetch } = useQuery({
    queryKey: ['asset-analytics', filters],
    queryFn: async () => {
      const result = await analyticsService.getComprehensiveAnalytics(filters)
      return result
    },
    staleTime: 5 * 60 * 1000, // 5分钟缓存
    refetchOnWindowFocus: false
  })

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

  
  // 处理筛选条件变化
  const handleFilterChange = (newFilters: AssetSearchParams) => {
    setFilters(newFilters)
  }

  // 处理筛选条件重置
  const handleFilterReset = () => {
    setFilters({})
  }

  // 处理维度切换
  const handleDimensionChange = (newDimension: AnalysisDimension) => {
    setDimension(newDimension)
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
        occupancy_trend: analytics.occupancy_trend,
        // 面积维度数据
        property_nature_area_distribution: analytics.property_nature_area_distribution,
        ownership_status_area_distribution: analytics.ownership_status_area_distribution,
        usage_status_area_distribution: analytics.usage_status_area_distribution,
        business_category_area_distribution: analytics.business_category_area_distribution
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
        <Spin size="large" />
        <div style={{ marginTop: '16px' }}>加载分析数据中...</div>
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

      {/* 维度切换 */}
      <Card style={{ marginBottom: '24px' }}>
        <Space align="center">
          <Text strong>分析维度：</Text>
          <Radio.Group
            value={dimension}
            onChange={(e) => handleDimensionChange(e.target.value)}
            buttonStyle="solid"
          >
            <Radio.Button value="count">数量维度</Radio.Button>
            <Radio.Button value="area">面积维度</Radio.Button>
          </Radio.Group>
          <Text type="secondary">
            {dimension === 'count' ? '基于资产个数进行分析' : '基于资产面积进行分析'}
          </Text>
        </Space>
      </Card>

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
                title={`物业性质分布 (${dimension === 'count' ? '数量' : '面积'})`}
                data={dimension === 'count'
                  ? chartDataUtils.toPieData(analytics.property_nature_distribution)
                  : chartDataUtils.toAreaData(analytics.property_nature_area_distribution)
                }
                loading={isLoading}
                height={280}
              />
            </Col>

            {/* 确权状态分布饼图 */}
            <Col xs={24} sm={12} xl={6}>
              <AnalyticsPieChart
                title={`确权状态分布 (${dimension === 'count' ? '数量' : '面积'})`}
                data={dimension === 'count'
                  ? chartDataUtils.toPieData(analytics.ownership_status_distribution.map(item => ({
                      name: item.status,
                      count: item.count,
                      percentage: item.percentage
                    })))
                  : chartDataUtils.toAreaData(analytics.ownership_status_area_distribution.map(item => ({
                      name: item.status,
                      total_area: item.total_area,
                      area_percentage: item.area_percentage,
                      average_area: item.average_area
                    })))
                }
                loading={isLoading}
                height={280}
              />
            </Col>

            {/* 使用状态分布柱状图 */}
            <Col xs={24} sm={12} xl={6}>
              <AnalyticsBarChart
                title={`使用状态分布 (${dimension === 'count' ? '数量' : '面积'})`}
                data={dimension === 'count'
                  ? analytics.usage_status_distribution.map(item => ({
                      name: item.status,
                      value: item.count
                    }))
                  : chartDataUtils.toAreaBarData(analytics.usage_status_area_distribution.map(item => ({
                      name: item.status,
                      total_area: item.total_area,
                      count: item.count,
                      average_area: item.average_area
                    })))
                }
                xAxisKey="name"
                barKey="value"
                loading={isLoading}
                height={280}
              />
            </Col>

            {/* 业态类别分布柱状图 */}
            <Col xs={24} sm={12} xl={6}>
              <AnalyticsBarChart
                title={`业态类别分布 (${dimension === 'count' ? '数量' : '面积'})`}
                data={dimension === 'count'
                  ? chartDataUtils.toBusinessCategoryData(analytics.business_category_distribution)
                  : chartDataUtils.toBusinessCategoryAreaData(analytics.business_category_area_distribution)
                }
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
                    <Typography.Title level={5}>
                      物业性质分布 ({dimension === 'count' ? '数量' : '面积'})
                    </Typography.Title>
                    <div className={styles.distributionList}>
                      {(dimension === 'count'
                        ? analytics.property_nature_distribution
                        : analytics.property_nature_area_distribution
                      )?.map((item, index) => (
                        <div key={index} className={styles.distributionItem}>
                          <span className={styles.itemName}>
                            {dimension === 'count' ? item.name : item.name}
                          </span>
                          <span className={styles.itemStats}>
                            {dimension === 'count'
                              ? `${item.count} (${item.percentage}%)`
                              : `${item.total_area?.toFixed(0)}㎡ (${item.area_percentage}%)`
                            }
                          </span>
                        </div>
                      ))}
                    </div>
                  </Col>

                  <Col xs={24} sm={12} lg={6}>
                    <Typography.Title level={5}>
                      确权状态分布 ({dimension === 'count' ? '数量' : '面积'})
                    </Typography.Title>
                    <div className={styles.distributionList}>
                      {(dimension === 'count'
                        ? analytics.ownership_status_distribution
                        : analytics.ownership_status_area_distribution
                      )?.map((item, index) => (
                        <div key={index} className={styles.distributionItem}>
                          <span className={styles.itemName}>
                            {dimension === 'count' ? item.status : item.status}
                          </span>
                          <span className={styles.itemStats}>
                            {dimension === 'count'
                              ? `${item.count} (${item.percentage}%)`
                              : `${item.total_area?.toFixed(0)}㎡ (${item.area_percentage}%)`
                            }
                          </span>
                        </div>
                      ))}
                    </div>
                  </Col>

                  <Col xs={24} sm={12} lg={6}>
                    <Typography.Title level={5}>
                      使用状态分布 ({dimension === 'count' ? '数量' : '面积'})
                    </Typography.Title>
                    <div className={styles.distributionList}>
                      {(dimension === 'count'
                        ? analytics.usage_status_distribution
                        : analytics.usage_status_area_distribution
                      )?.map((item, index) => (
                        <div key={index} className={styles.distributionItem}>
                          <span className={styles.itemName}>
                            {dimension === 'count' ? item.status : item.status}
                          </span>
                          <span className={styles.itemStats}>
                            {dimension === 'count'
                              ? `${item.count} (${item.percentage}%)`
                              : `${item.total_area?.toFixed(0)}㎡ (${item.area_percentage}%)`
                            }
                          </span>
                        </div>
                      ))}
                    </div>
                  </Col>

                  <Col xs={24} sm={12} lg={6}>
                    <Typography.Title level={5}>
                      业态类别分布 ({dimension === 'count' ? '数量' : '面积'})
                    </Typography.Title>
                    <div className={styles.distributionList}>
                      {(dimension === 'count'
                        ? analytics.business_category_distribution
                        : analytics.business_category_area_distribution
                      )?.map((item, index) => (
                        <div key={index} className={styles.distributionItem}>
                          <span className={styles.itemName}>
                            {dimension === 'count' ? item.category : item.category}
                          </span>
                          <span className={styles.itemStats}>
                            {dimension === 'count'
                              ? `${item.count}个 (占比${item.percentage}%)`
                              : `${item.total_area?.toFixed(0)}㎡ (占比${item.area_percentage}%)`
                            }
                            {dimension === 'count' && Number(item.occupancy_rate) > 0 && (
                              <span className={styles.occupancyRate}>
                                ，出租率{Number(item.occupancy_rate).toFixed(2)}%
                              </span>
                            )}
                            {dimension === 'area' && item.occupancy_rate && Number(item.occupancy_rate) > 0 && (
                              <span className={styles.occupancyRate}>
                                ，出租率{Number(item.occupancy_rate).toFixed(2)}%
                              </span>
                            )}
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