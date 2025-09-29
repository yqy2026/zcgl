import React from 'react'
import {
  Card,
  Row,
  Col,
  Statistic,
  Spin,
  Alert,
  Progress,
  Table,
  Empty
} from 'antd'
import { useQuery } from '@tanstack/react-query'
import {
  PieChart,
  Pie,
  Cell,
  BarChart,
  Bar,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer
} from 'recharts'
import { api } from '../../services/api'

interface AnalyticsData {
  area_summary: {
    total_assets: number
    total_area: number
    total_rentable_area: number
    total_rented_area: number
    total_unrented_area: number
    assets_with_area_data: number
    occupancy_rate: number
  }
  financial_summary: {
    total_annual_income: number
    total_annual_expense: number
    total_net_income: number
    total_monthly_rent: number
    total_deposit: number
    assets_with_income_data: number
    assets_with_rent_data: number
  }
  occupancy_distribution: Array<{
    range: string
    count: number
    percentage: number
  }>
  property_nature_distribution: Array<{
    name: string
    count: number
    percentage: number
  }>
  ownership_status_distribution: Array<{
    status: string
    count: number
    percentage: number
  }>
  usage_status_distribution: Array<{
    status: string
    count: number
    percentage: number
  }>
  business_category_distribution: Array<{
    category: string
    count: number
    occupancy_rate: number
  }>
  occupancy_trend: Array<{
    date: string
    occupancy_rate: number
    total_rented_area: number
    total_rentable_area: number
  }>
}

const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884d8', '#82ca9d']

const AssetAnalyticsPage: React.FC = () => {
  const { data: analyticsData, isLoading, error } = useQuery({
    queryKey: ['asset-analytics'],
    queryFn: async () => {
      const response = await api.get('/analytics/comprehensive')
      return response.data.data
    }
  })

  const analytics = analyticsData

  if (isLoading) {
    return (
      <div style={{ padding: '24px', textAlign: 'center' }}>
        <Spin size="large" tip="加载分析数据中..." />
      </div>
    )
  }

  if (error) {
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

  const hasData = analytics?.area_summary?.total_assets > 0

  return (
    <div style={{ padding: '24px' }}>
      <Card title="资产分析" style={{ marginBottom: '24px' }}>
        {/* 概览统计 */}
        <Row gutter={[16, 16]} style={{ marginBottom: '24px' }}>
          <Col xs={24} sm={6}>
            <Card>
              <Statistic
                title="资产总数"
                value={analytics?.area_summary?.total_assets || 0}
                suffix="个"
              />
            </Card>
          </Col>
          <Col xs={24} sm={6}>
            <Card>
              <Statistic
                title="总面积"
                value={analytics?.area_summary?.total_area || 0}
                precision={2}
                suffix="㎡"
              />
            </Card>
          </Col>
          <Col xs={24} sm={6}>
            <Card>
              <Statistic
                title="可租面积"
                value={analytics?.area_summary?.total_rentable_area || 0}
                precision={2}
                suffix="㎡"
              />
            </Card>
          </Col>
          <Col xs={24} sm={6}>
            <Card>
              <Statistic
                title="整体出租率"
                value={analytics?.area_summary?.occupancy_rate || 0}
                precision={2}
                suffix="%"
              />
            </Card>
          </Col>
        </Row>
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
        <Row gutter={[16, 16]}>
          {/* 物业性质分布 */}
          <Col xs={24} lg={12}>
            <Card title="物业性质分布">
              {analytics?.property_nature_distribution?.map((item, index) => (
                <div key={index} style={{ marginBottom: '8px' }}>
                  <strong>{item.name}:</strong> {item.count} ({item.percentage}%)
                </div>
              ))}
            </Card>
          </Col>

          {/* 确权状态分布 */}
          <Col xs={24} lg={12}>
            <Card title="确权状态分布">
              {analytics?.ownership_status_distribution?.map((item, index) => (
                <div key={index} style={{ marginBottom: '8px' }}>
                  <strong>{item.status}:</strong> {item.count} ({item.percentage}%)
                </div>
              ))}
            </Card>
          </Col>

          {/* 使用状态分布 */}
          <Col xs={24} lg={12}>
            <Card title="使用状态分布">
              {analytics?.usage_status_distribution?.map((item, index) => (
                <div key={index} style={{ marginBottom: '8px' }}>
                  <strong>{item.status}:</strong> {item.count} ({item.percentage}%)
                </div>
              ))}
            </Card>
          </Col>

          {/* 业态类别分布 */}
          <Col xs={24} lg={12}>
            <Card title="业态类别分布">
              {analytics?.business_category_distribution?.map((item, index) => (
                <div key={index} style={{ marginBottom: '8px' }}>
                  <strong>{item.category}:</strong> {item.count} (出租率: {item.occupancy_rate}%)
                </div>
              ))}
            </Card>
          </Col>

          {/* 财务指标 */}
          <Col xs={24}>
            <Card title="财务指标">
              <Row gutter={[16, 16]}>
                <Col xs={24} sm={6}>
                  <Statistic
                    title="年收入"
                    value={analytics?.financial_summary?.total_annual_income || 0}
                    precision={2}
                    suffix="元"
                  />
                </Col>
                <Col xs={24} sm={6}>
                  <Statistic
                    title="年支出"
                    value={analytics?.financial_summary?.total_annual_expense || 0}
                    precision={2}
                    suffix="元"
                  />
                </Col>
                <Col xs={24} sm={6}>
                  <Statistic
                    title="净收益"
                    value={analytics?.financial_summary?.total_net_income || 0}
                    precision={2}
                    suffix="元"
                    valueStyle={{ color: (analytics?.financial_summary?.total_net_income || 0) >= 0 ? '#3f8600' : '#cf1322' }}
                  />
                </Col>
                <Col xs={24} sm={6}>
                  <Statistic
                    title="月租金"
                    value={analytics?.financial_summary?.total_monthly_rent || 0}
                    precision={2}
                    suffix="元"
                  />
                </Col>
              </Row>
            </Card>
          </Col>
        </Row>
      )}
    </div>
  )
}

export default AssetAnalyticsPage

// 触发热重载 - 修复接口类型匹配问题