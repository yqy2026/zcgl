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
import styles from './AnalyticsStatsCard.module.css';

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
  const hasTrend = trend !== null && trend !== undefined;
  const trendIsPositive = hasTrend ? trend > 0 : false;
  const TrendIcon = trendIsPositive ? ArrowUpOutlined : ArrowDownOutlined;
  const trendStyle = hasTrend
    ? ({
        ['--stats-card-trend-color' as string]: getTrendColor(trend, trendType),
      } as React.CSSProperties)
    : undefined;
  const statisticStyle = valueStyle !== undefined ? { ...valueStyle } : undefined;
  const cardStyle = {
    ['--stats-card-icon-bg' as string]: color,
    ...(valueStyle?.color !== undefined
      ? { ['--stats-card-value-color' as string]: valueStyle.color }
      : {}),
  } as React.CSSProperties;

  return (
    <Card loading={loading} size="small" className={styles.statCard} style={cardStyle}>
      <div className={styles.statHeader}>
        {icon != null && (
          <div className={styles.iconBadge}>
            {icon}
          </div>
        )}
        <div className={styles.statMain}>
          <div className={styles.statTitle}>{title}</div>
          <Statistic
            value={value}
            precision={precision}
            suffix={suffix}
            prefix={prefix}
            className={styles.statistic}
            styles={statisticStyle ? { content: statisticStyle } : undefined}
          />
        </div>
      </div>
      {hasTrend && (
        <div className={styles.trend} style={trendStyle}>
          <TrendIcon />
          <span>{Math.abs(trend)}%</span>
        </div>
      )}
    </Card>
  );
};

// 统计网格组件
export const AnalyticsStatsGrid: React.FC<StatsGridProps> = ({ data, loading = false }) => {
  // 注释：由于没有历史数据对比，暂时不显示趋势数据
  // 所有数据都是当前时间点的真实数据

  return (
    <Row gutter={[16, 16]} className={styles.statsGrid}>
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
    <Row gutter={[16, 16]} className={styles.financialGrid}>
      <Col xs={24} sm={6}>
        <Card loading={loading} size="small" className={styles.financialCard}>
          <Statistic
            title="年收入"
            value={data.total_annual_income}
            precision={2}
            suffix="元"
            className={`${styles.financialMetric} ${styles.financialIncome}`}
          />
        </Card>
      </Col>

      <Col xs={24} sm={6}>
        <Card loading={loading} size="small" className={styles.financialCard}>
          <Statistic
            title="年支出"
            value={data.total_annual_expense}
            precision={2}
            suffix="元"
            className={`${styles.financialMetric} ${styles.financialExpense}`}
          />
        </Card>
      </Col>

      <Col xs={24} sm={6}>
        <Card loading={loading} size="small" className={styles.financialCard}>
          <Statistic
            title="净收益"
            value={data.total_net_income}
            precision={2}
            suffix="元"
            className={`${styles.financialMetric} ${
              data.total_net_income >= 0
                ? styles.financialNetIncomePositive
                : styles.financialNetIncomeNegative
            }`}
          />
        </Card>
      </Col>

      <Col xs={24} sm={6}>
        <Card loading={loading} size="small" className={styles.financialCard}>
          <Statistic
            title="月租金"
            value={data.total_monthly_rent}
            precision={2}
            suffix="元"
            className={`${styles.financialMetric} ${styles.financialRent}`}
          />
        </Card>
      </Col>
    </Row>
  );
};
