import React from 'react';
import { Card, Statistic, Row, Col } from 'antd';
import {
  ArrowUpOutlined,
  ArrowDownOutlined,
  ApartmentOutlined,
  ThunderboltOutlined,
  PieChartOutlined,
  MoneyCollectOutlined,
  TransactionOutlined,
  AreaChartOutlined,
} from '@ant-design/icons';
import { getTrendColor, getOccupancyRateColor, COLORS } from '@/styles/colorMap';

interface StatCardProps {
  title: string;
  value: number | string;
  precision?: number;
  suffix?: string;
  prefix?: React.ReactNode;
  valueStyle?: React.CSSProperties;
  trend?: number;
  trendType?: 'up' | 'down';
  icon?: React.ReactNode;
  color?: string;
  loading?: boolean;
}

interface StatsGridProps {
  data: {
    total_assets: number;
    total_area: number;
    total_rentable_area: number;
    occupancy_rate: number;
    total_annual_income?: number;
    total_net_income?: number;
    total_monthly_rent?: number;
  };
  loading?: boolean;
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
  color = COLORS.primary,
  loading = false,
}) => {
  const getTrendIcon = () => {
    if (trend === null || trend === undefined) {
      return null;
    }

    const isPositive = trend > 0;
    const color = getTrendColor(trend, trendType);
    const Icon = isPositive ? ArrowUpOutlined : ArrowDownOutlined;

    return (
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '2px',
          color,
          fontSize: 12,
          fontWeight: 500,
        }}
      >
        <Icon />
        <span>{Math.abs(trend)}%</span>
      </div>
    );
  };

  return (
    <Card
      loading={loading}
      size="small"
      styles={{
        body: { padding: '20px 24px' },
        header: { padding: '12px 24px', borderBottom: '1px solid #f0f0f0' },
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', marginBottom: 8 }}>
        {icon != null && (
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
              fontSize: 18,
            }}
          >
            {icon}
          </div>
        )}
        <div style={{ flex: 1 }}>
          <div style={{ color: COLORS.textTertiary, fontSize: 14, marginBottom: 4 }}>{title}</div>
          <Statistic
            value={value}
            precision={precision}
            suffix={suffix}
            prefix={prefix}
            styles={{ content: {
              fontSize: 24,
              fontWeight: 'bold',
              margin: 0,
              ...valueStyle,
            } }}
          />
        </div>
      </div>
      {getTrendIcon()}
    </Card>
  );
};

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
          color={COLORS.primary}
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
          color={COLORS.success}
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
          color={COLORS.primary}
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
          color={COLORS.warning}
          valueStyle={{
            color: getOccupancyRateColor(data.occupancy_rate),
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
            color={COLORS.success}
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
            color={data.total_net_income >= 0 ? COLORS.success : COLORS.error}
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
            color={COLORS.primary}
            loading={loading}
          />
        </Col>
      )}
    </Row>
  );
};

// 财务指标网格组件
interface FinancialStatsGridProps {
  data: {
    total_annual_income: number;
    total_annual_expense: number;
    total_net_income: number;
    total_monthly_rent: number;
    total_deposit?: number;
  };
  loading?: boolean;
}

export const FinancialStatsGrid: React.FC<FinancialStatsGridProps> = ({
  data,
  loading = false,
}) => {
  return (
    <Row gutter={[16, 16]}>
      <Col xs={24} sm={6}>
        <Card loading={loading} size="small">
          <Statistic
            title="年收入"
            value={data.total_annual_income}
            precision={2}
            suffix="元"
            styles={{ content: { color: COLORS.success } }}
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
            styles={{ content: { color: COLORS.error } }}
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
            styles={{ content: {
              color: data.total_net_income >= 0 ? COLORS.success : COLORS.error,
            } }}
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
            styles={{ content: { color: COLORS.primary } }}
          />
        </Card>
      </Col>
    </Row>
  );
};
