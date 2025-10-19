import React, { useMemo } from 'react'
import { Card, Row, Col, Statistic, Progress, Tag, Tooltip } from 'antd'
import {
  ArrowUpOutlined,
  ArrowDownOutlined,
  InfoCircleOutlined
} from '@ant-design/icons'
import type { PerformanceMetrics, ComparisonData } from '../../types/analytics'
import { FinancialStatisticCard } from './StatisticCard'

interface AdvancedAnalyticsCardProps {
  performanceMetrics: PerformanceMetrics
  comparisonData?: ComparisonData
  loading?: boolean
}

const AdvancedAnalyticsCard: React.FC<AdvancedAnalyticsCardProps> = ({
  performanceMetrics,
  comparisonData,
  loading = false
}) => {
  // Helper functions removed (unused)

  const getPerformanceStatus = (value: number, thresholds: { good: number; average: number }) => {
    if (value >= thresholds.good) return { color: 'success', text: '优秀' }
    if (value >= thresholds.average) return { color: 'processing', text: '良好' }
    return { color: 'warning', text: '待改进' }
  }

  const performanceStatus = useMemo(() => ({
    utilization: getPerformanceStatus(performanceMetrics.asset_utilization * 100, { good: 80, average: 60 }),
    efficiency: getPerformanceStatus(performanceMetrics.income_efficiency * 100, { good: 70, average: 50 }),
    variance: getPerformanceStatus(100 - performanceMetrics.occupancy_variance * 100, { good: 90, average: 80 }),
    growth: getPerformanceStatus(performanceMetrics.growth_rate * 100, { good: 10, average: 5 })
  }), [performanceMetrics])

  return (
    <Card loading={loading} title="高级分析指标">
      <Row gutter={[16, 16]}>
        {/* 资产利用率 */}
        <Col xs={24} sm={12} lg={6}>
          <div style={{ textAlign: 'center' }}>
            <Statistic
              title="资产利用率"
              value={performanceMetrics.asset_utilization * 100}
              precision={1}
              suffix="%"
              valueStyle={{ color: performanceStatus.utilization.color === 'success' ? '#3f8600' :
                           performanceStatus.utilization.color === 'processing' ? '#1890ff' : '#fa8c16' }}
            />
            <Progress
              percent={performanceMetrics.asset_utilization * 100}
              size="small"
              strokeColor={performanceStatus.utilization.color === 'success' ? '#3f8600' :
                          performanceStatus.utilization.color === 'processing' ? '#1890ff' : '#fa8c16'}
              style={{ marginTop: 8 }}
            />
            <Tag color={performanceStatus.utilization.color} style={{ marginTop: 8 }}>
              {performanceStatus.utilization.text}
            </Tag>
          </div>
        </Col>

        {/* 收入效率 */}
        <Col xs={24} sm={12} lg={6}>
          <div style={{ textAlign: 'center' }}>
            <Statistic
              title="收入效率"
              value={performanceMetrics.income_efficiency * 100}
              precision={1}
              suffix="%"
              valueStyle={{ color: performanceStatus.efficiency.color === 'success' ? '#3f8600' :
                           performanceStatus.efficiency.color === 'processing' ? '#1890ff' : '#fa8c16' }}
            />
            <Progress
              percent={performanceMetrics.income_efficiency * 100}
              size="small"
              strokeColor={performanceStatus.efficiency.color === 'success' ? '#3f8600' :
                          performanceStatus.efficiency.color === 'processing' ? '#1890ff' : '#fa8c16'}
              style={{ marginTop: 8 }}
            />
            <Tag color={performanceStatus.efficiency.color} style={{ marginTop: 8 }}>
              {performanceStatus.efficiency.text}
            </Tag>
          </div>
        </Col>

        {/* 出租率稳定性 */}
        <Col xs={24} sm={12} lg={6}>
          <div style={{ textAlign: 'center' }}>
            <Statistic
              title="出租率稳定性"
              value={(1 - performanceMetrics.occupancy_variance) * 100}
              precision={1}
              suffix="%"
              valueStyle={{ color: performanceStatus.variance.color === 'success' ? '#3f8600' :
                           performanceStatus.variance.color === 'processing' ? '#1890ff' : '#fa8c16' }}
            />
            <Progress
              percent={(1 - performanceMetrics.occupancy_variance) * 100}
              size="small"
              strokeColor={performanceStatus.variance.color === 'success' ? '#3f8600' :
                          performanceStatus.variance.color === 'processing' ? '#1890ff' : '#fa8c16'}
              style={{ marginTop: 8 }}
            />
            <Tag color={performanceStatus.variance.color} style={{ marginTop: 8 }}>
              {performanceStatus.variance.text}
            </Tag>
          </div>
        </Col>

        {/* 增长率 */}
        <Col xs={24} sm={12} lg={6}>
          <div style={{ textAlign: 'center' }}>
            <Statistic
              title="增长率"
              value={performanceMetrics.growth_rate * 100}
              precision={1}
              suffix="%"
              prefix={performanceMetrics.growth_rate > 0 ? <ArrowUpOutlined /> :
                      performanceMetrics.growth_rate < 0 ? <ArrowDownOutlined /> : null}
              valueStyle={{ color: performanceStatus.growth.color === 'success' ? '#3f8600' :
                           performanceStatus.growth.color === 'processing' ? '#1890ff' : '#fa8c16' }}
            />
            <Progress
              percent={Math.abs(performanceMetrics.growth_rate * 100)}
              size="small"
              strokeColor={performanceStatus.growth.color === 'success' ? '#3f8600' :
                          performanceStatus.growth.color === 'processing' ? '#1890ff' : '#fa8c16'}
              style={{ marginTop: 8 }}
            />
            <Tag color={performanceStatus.growth.color} style={{ marginTop: 8 }}>
              {performanceStatus.growth.text}
            </Tag>
          </div>
        </Col>
      </Row>

      {/* 对比分析 */}
      {comparisonData && (
        <>
          <div style={{ marginTop: '24px', marginBottom: '16px' }}>
            <h4>
              同比分析
              <Tooltip title="与上一周期对比">
                <InfoCircleOutlined style={{ marginLeft: '8px', color: '#666' }} />
              </Tooltip>
            </h4>
          </div>
          <Row gutter={[16, 16]}>
            <Col xs={24} sm={6}>
              <FinancialStatisticCard
                title="资产总数变化"
                value={comparisonData.change_percentage.total_assets}
                precision={1}
                suffix="%"
                isPositive={comparisonData.change_percentage.total_assets >= 0}
              />
            </Col>
            <Col xs={24} sm={6}>
              <FinancialStatisticCard
                title="总面积变化"
                value={comparisonData.change_percentage.total_area}
                precision={1}
                suffix="%"
                isPositive={comparisonData.change_percentage.total_area >= 0}
              />
            </Col>
            <Col xs={24} sm={6}>
              <FinancialStatisticCard
                title="出租率变化"
                value={comparisonData.change_percentage.occupancy_rate}
                precision={1}
                suffix="%"
                isPositive={comparisonData.change_percentage.occupancy_rate >= 0}
              />
            </Col>
            <Col xs={24} sm={6}>
              <FinancialStatisticCard
                title="净收益变化"
                value={comparisonData.change_percentage.total_net_income}
                precision={1}
                suffix="%"
                isPositive={comparisonData.change_percentage.total_net_income >= 0}
              />
            </Col>
          </Row>
        </>
      )}
    </Card>
  )
}

export default AdvancedAnalyticsCard