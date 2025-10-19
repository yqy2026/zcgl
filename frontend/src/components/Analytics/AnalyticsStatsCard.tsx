import React from 'react'
import { Card, Statistic, Row, Col } from 'antd'
import {
  ArrowUpOutlined,
  ArrowDownOutlined,
  ApartmentOutlined,
  ThunderboltOutlined,
  PieChartOutlined,
  MoneyCollectOutlined,
  TransactionOutlined,
  AreaChartOutlined
} from '@ant-design/icons'

interface StatCardProps {
  title: string
  value: number | string
  precision?: number
  suffix?: string
  prefix?: React.ReactNode
  valueStyle?: React.CSSProperties
  trend?: number
  trendType?: 'up' | 'down'
  icon?: React.ReactNode
  color?: string
  loading?: boolean
}

interface StatsGridProps {
  data: {
    total_assets: number
    total_area: number
    total_rentable_area: number
    occupancy_rate: number
    total_annual_income?: number
    total_net_income?: number
    total_monthly_rent?: number
  }
  loading?: boolean
}

// 单个统计卡片组件
const StatCard: React.FC<StatCardProps> = ({
  title,
  value,
  precision = 2,
  suffix,
  prefix,
  valueStyle,
  trend,
  trendType,
  icon,
  color = '#1890ff',
  loading = false
}) => {
  const getTrendIcon = () => {
    if (!trend && trend !== 0) return null

    const isPositive = trend > 0
    const color = trendType === 'up' ? (isPositive ? '#52c41a' : '#ff4d4f') : (isPositive ? '#ff4d4f' : '#52c41a')
    const Icon = isPositive ? ArrowUpOutlined : ArrowDownOutlined

    return (
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: '2px',
        color,
        fontSize: 12,
        fontWeight: 500
      }}>
        <Icon />
        <span>{Math.abs(trend)}%</span>
      </div>
    )
  }

  return (
    <Card
      loading={loading}
      size="small"
      styles={{
        body: { padding: '20px 24px' },
        header: { padding: '12px 24px', borderBottom: '1px solid #f0f0f0' }
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', marginBottom: 8 }}>
        {icon && (
          <div
            style={{
              width: 40,
              height: 40,
              borderRadius: 8,
              background: color,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              marginRight: 16,
              color: 'white',
              fontSize: 18
            }}
          >
            {icon}
          </div>
        )}
        <div style={{ flex: 1 }}>
          <div style={{ color: '#8c8c8c', fontSize: 14, marginBottom: 4 }}>{title}</div>
          <Statistic
            value={value}
            precision={precision}
            suffix={suffix}
            prefix={prefix}
            valueStyle={{
              fontSize: 24,
              fontWeight: 'bold',
              margin: 0,
              ...valueStyle
            }}
          />
        </div>
      </div>
      {getTrendIcon()}
    </Card>
  )
}

// 统计网格组件
export const AnalyticsStatsGrid: React.FC<StatsGridProps> = ({ data, loading = false }) => {
  // 注释：由于没有历史数据对比，暂时不显示趋势数据
  // 所有数据都是当前时间点的真实数据

  return (
    <Row gutter={[16, 16]}>
      <Col xs={24} sm={12} lg={6}>
        <StatCard
          title="资产总数"
          value={data.total_assets}
          suffix="个"
          icon={<ApartmentOutlined />}
          color="#2f54eb"
          loading={loading}
        />
      </Col>

      <Col xs={24} sm={12} lg={6}>
        <StatCard
          title="总面积"
          value={data.total_area}
          precision={2}
          suffix="㎡"
          icon={<AreaChartOutlined />}
          color="#13c2c2"
          loading={loading}
        />
      </Col>

      <Col xs={24} sm={12} lg={6}>
        <StatCard
          title="可租面积"
          value={data.total_rentable_area}
          precision={2}
          suffix="㎡"
          icon={<ThunderboltOutlined />}
          color="#722ed1"
          loading={loading}
        />
      </Col>

      <Col xs={24} sm={12} lg={6}>
        <StatCard
          title="整体出租率"
          value={data.occupancy_rate}
          precision={2}
          suffix="%"
          icon={<PieChartOutlined />}
          color="#fa8c16"
          valueStyle={{
            color: data.occupancy_rate >= 80 ? '#52c41a' :
                   data.occupancy_rate >= 60 ? '#faad14' : '#ff4d4f'
          }}
          loading={loading}
        />
      </Col>

      {/* 财务指标（如果有数据） */}
      {data.total_annual_income !== undefined && (
        <Col xs={24} sm={12} lg={6}>
          <StatCard
            title="年收入"
            value={data.total_annual_income}
            precision={2}
            suffix="元"
            icon={<MoneyCollectOutlined />}
            color="#52c41a"
            loading={loading}
          />
        </Col>
      )}

      {data.total_net_income !== undefined && (
        <Col xs={24} sm={12} lg={6}>
          <StatCard
            title="净收益"
            value={data.total_net_income}
            precision={2}
            suffix="元"
            icon={<MoneyCollectOutlined />}
            color={data.total_net_income >= 0 ? '#52c41a' : '#ff4d4f'}
            trendType={data.total_net_income >= 0 ? 'up' : 'down'}
            loading={loading}
          />
        </Col>
      )}

      {data.total_monthly_rent !== undefined && (
        <Col xs={24} sm={12} lg={6}>
          <StatCard
            title="月租金"
            value={data.total_monthly_rent}
            precision={2}
            suffix="元"
            icon={<TransactionOutlined />}
            color="#eb2f96"
            loading={loading}
          />
        </Col>
      )}
    </Row>
  )
}

// 财务指标网格组件
interface FinancialStatsGridProps {
  data: {
    total_annual_income: number
    total_annual_expense: number
    total_net_income: number
    total_monthly_rent: number
    total_deposit?: number
  }
  loading?: boolean
}

export const FinancialStatsGrid: React.FC<FinancialStatsGridProps> = ({ data, loading = false }) => {
  return (
    <Row gutter={[16, 16]}>
      <Col xs={24} sm={6}>
        <Card loading={loading} size="small">
          <Statistic
            title="年收入"
            value={data.total_annual_income}
            precision={2}
            suffix="元"
            valueStyle={{ color: '#3f8600' }}
          />
        </Card>
      </Col>

      <Col xs={24} sm={6}>
        <Card loading={loading} size="small">
          <Statistic
            title="年支出"
            value={data.total_annual_expense}
            precision={2}
            suffix="元"
            valueStyle={{ color: '#cf1322' }}
          />
        </Card>
      </Col>

      <Col xs={24} sm={6}>
        <Card loading={loading} size="small">
          <Statistic
            title="净收益"
            value={data.total_net_income}
            precision={2}
            suffix="元"
            valueStyle={{
              color: data.total_net_income >= 0 ? '#3f8600' : '#cf1322'
            }}
          />
        </Card>
      </Col>

      <Col xs={24} sm={6}>
        <Card loading={loading} size="small">
          <Statistic
            title="月租金"
            value={data.total_monthly_rent}
            precision={2}
            suffix="元"
            valueStyle={{ color: '#1890ff' }}
          />
        </Card>
      </Col>
    </Row>
  )
}