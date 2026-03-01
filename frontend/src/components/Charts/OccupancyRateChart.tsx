import React, { useMemo } from 'react';
import { Card, Typography, Statistic, Row, Col, Spin, Alert } from 'antd';
import { PercentageOutlined, RiseOutlined, FallOutlined, MinusOutlined } from '@ant-design/icons';
import { useQuery } from '@tanstack/react-query';
import { Line, Column, Pie } from '@ant-design/plots';

import { assetService } from '@/services/assetService';
import type { AssetSearchParams } from '@/types/asset';
import { CHART_COLORS, CHART_LABEL_COLORS } from '@/styles/colorMap';
import type {
  ChartDataPoint,
  TrendDataPoint,
  DistributionDataPoint,
  ColumnDataPoint,
  TooltipFormatterResult,
  TooltipCustomContentProps,
} from '@/types/charts';
import styles from './OccupancyRateChart.module.css';

const { Text } = Typography;

interface _OccupancyRateData {
  overall_rate: number;
  trend: 'up' | 'down' | 'stable';
  trend_percentage: number;
  by_property_nature: Array<{
    property_nature: string;
    rate: number;
    total_area: number;
    rented_area: number;
  }>;
  by_owner_party: Array<{
    owner_party_name: string;
    rate: number;
    asset_count: number;
  }>;
  monthly_trend: Array<{
    month: string;
    rate: number;
    total_area: number;
    rented_area: number;
  }>;
  top_performers: Array<{
    property_name: string;
    rate: number;
    area: number;
  }>;
  low_performers: Array<{
    property_name: string;
    rate: number;
    area: number;
  }>;
}

interface OccupancyRateChartProps {
  filters?: AssetSearchParams;
  height?: number;
}

type TrendDirection = 'up' | 'down' | 'stable';

const OccupancyRateChart: React.FC<OccupancyRateChartProps> = ({ filters, height = 400 }) => {
  // 获取出租率数据
  const { data, isLoading, error } = useQuery({
    queryKey: ['occupancy-rate-stats', filters],
    queryFn: () => assetService.getOccupancyRateStats(filters),
    refetchInterval: 5 * 60 * 1000, // 5分钟刷新一次
  });

  // 趋势图表配置
  const trendChartConfig = useMemo(
    () => ({
      data:
        data?.monthly_trend?.map(
          (item): TrendDataPoint => ({
            month: item.month,
            rate: item.rate,
            total_area: item.total_area,
            rented_area: item.rented_area,
          })
        ) ?? [],
      xField: 'month' as const,
      yField: 'rate' as const,
      smooth: true,
      color: CHART_COLORS[0],
      areaStyle: {
        fillOpacity: 0.1,
      },
      point: {
        size: 4,
        shape: 'circle' as const,
      },
      tooltip: {
        formatter: (datum: ChartDataPoint): TooltipFormatterResult => ({
          name: '出租率',
          value: `${(datum.rate as number).toFixed(2)}%`,
        }),
        customContent: (_title: string, tooltipData: TooltipCustomContentProps['data']) => {
          const datum = tooltipData?.[0]?.data as TrendDataPoint | undefined;
          if (datum == null) return null;
          return (
            <div className={styles.chartTooltip}>
              <div className={styles.tooltipTitle}>{datum.month}</div>
              <div>出租率: {datum.rate.toFixed(2)}%</div>
              <div>总面积: {datum.total_area?.toLocaleString()} ㎡</div>
              <div>已租面积: {datum.rented_area?.toLocaleString()} ㎡</div>
            </div>
          );
        },
      },
      yAxis: {
        min: 0,
        max: 100,
        label: {
          formatter: (value: number) => `${value}%`,
        },
      },
      animation: {
        appear: {
          animation: 'path-in' as const,
          duration: 1000,
        },
      },
    }),
    [data]
  );

  // 物业性质分布图表配置
  const propertyNatureChartConfig = useMemo(
    () => ({
      data:
        data?.by_property_nature?.map(
          (item): DistributionDataPoint => ({
            type: item.property_nature,
            value: item.rate,
            total_area: item.total_area,
            rented_area: item.rented_area,
          })
        ) ?? [],
      angleField: 'value' as const,
      colorField: 'type' as const,
      color: CHART_COLORS,
      radius: 0.8,
      innerRadius: 0.6,
      label: {
        type: 'inner' as const,
        offset: '-50%',
        content: '{value}%',
        style: {
          textAlign: 'center' as const,
          fontSize: 14,
          fill: CHART_LABEL_COLORS.light,
        },
      },
      legend: {
        layout: 'vertical' as const,
        position: 'right' as const,
      },
      tooltip: {
        formatter: (datum: ChartDataPoint): TooltipFormatterResult => ({
          name: (datum.type as string) ?? '',
          value: `${(datum.value as number).toFixed(2)}%`,
        }),
        customContent: (_title: string, tooltipData: TooltipCustomContentProps['data']) => {
          const datum = tooltipData?.[0]?.data as DistributionDataPoint | undefined;
          if (datum == null) return null;
          return (
            <div className={styles.chartTooltip}>
              <div className={styles.tooltipTitle}>{datum.type}</div>
              <div>出租率: {datum.value.toFixed(2)}%</div>
              <div>总面积: {datum.total_area?.toLocaleString()} ㎡</div>
              <div>已租面积: {datum.rented_area?.toLocaleString()} ㎡</div>
            </div>
          );
        },
      },
      statistic: {
        title: {
          offsetY: -8,
          content: '总体出租率',
          style: {
            fontSize: 14,
          },
        },
        content: {
          offsetY: 4,
          style: {
            fontSize: 20,
            fontWeight: 'bold' as const,
          },
          content: `${data?.overall_rate?.toFixed(2) ?? 0}%`,
        },
      },
    }),
    [data]
  );

  // 权属方出租率柱状图配置
  const ownershipChartConfig = useMemo(
    () => ({
      data:
        data?.by_owner_party?.map(
          (item): ColumnDataPoint => ({
            ownership:
              item.owner_party_name.length > 10
                ? item.owner_party_name.substring(0, 10) + '...'
                : item.owner_party_name,
            rate: item.rate,
            asset_count: item.asset_count,
            full_name: item.owner_party_name,
            value: item.rate,
          })
        ) ?? [],
      xField: 'ownership' as const,
      yField: 'rate' as const,
      color: CHART_COLORS[0],
      columnStyle: {
        fillOpacity: 0.6,
        stroke: CHART_COLORS[0],
        lineWidth: 1,
      },
      label: {
        position: 'top' as const,
        formatter: (datum: ChartDataPoint): string => `${(datum.rate as number).toFixed(1)}%`,
        style: {
          fill: CHART_LABEL_COLORS.dark,
          fontSize: 12,
        },
      },
      tooltip: {
        formatter: (datum: ChartDataPoint): TooltipFormatterResult => ({
          name: (datum.full_name as string | undefined) ?? (datum.ownership as string) ?? '',
          value: `${(datum.rate as number).toFixed(2)}%`,
        }),
        customContent: (_title: string, tooltipData: TooltipCustomContentProps['data']) => {
          const datum = tooltipData?.[0]?.data as ColumnDataPoint | undefined;
          if (datum == null) return null;
          return (
            <div className={styles.chartTooltip}>
              <div className={styles.tooltipTitle}>
                {datum.full_name ?? (datum.ownership as string)}
              </div>
              <div>出租率: {(datum.rate as number).toFixed(2)}%</div>
              <div>资产数量: {datum.asset_count as number} 个</div>
            </div>
          );
        },
      },
      yAxis: {
        min: 0,
        max: 100,
        label: {
          formatter: (value: number) => `${value}%`,
        },
      },
      xAxis: {
        label: {
          autoRotate: true,
          autoHide: true,
          maxRotation: 45,
          minRotation: 0,
        },
      },
      animation: {
        appear: {
          animation: 'scale-in-y' as const,
          duration: 1000,
        },
      },
    }),
    [data]
  );

  const getTrendDirection = (trend?: string): TrendDirection => {
    if (trend === 'up') return 'up';
    if (trend === 'down') return 'down';
    return 'stable';
  };

  const getOverallRateClassName = (overallRate: number): string => {
    if (overallRate >= 80) return styles.statisticSuccess;
    if (overallRate >= 60) return styles.statisticWarning;
    return styles.statisticError;
  };

  // 获取趋势图标
  const getTrendIcon = (trend: TrendDirection) => {
    if (trend === 'up') {
      return <RiseOutlined className={`${styles.trendIcon} ${styles.trendIconUp}`} aria-hidden />;
    } else if (trend === 'down') {
      return <FallOutlined className={`${styles.trendIcon} ${styles.trendIconDown}`} aria-hidden />;
    } else {
      return (
        <MinusOutlined className={`${styles.trendIcon} ${styles.trendIconStable}`} aria-hidden />
      );
    }
  };

  const trendDirection = getTrendDirection(data?.trend);

  if (error !== undefined && error !== null) {
    return (
      <Alert
        title="数据加载失败"
        description="无法加载出租率统计数据，请稍后重试"
        type="error"
        showIcon
      />
    );
  }

  return (
    <div className={styles.occupancyRateChart}>
      {/* 总体统计 */}
      <Row gutter={16} className={styles.summaryRow}>
        <Col xs={24} sm={12} md={6}>
          <Card className={styles.summaryCard}>
            <Statistic
              title="总体出租率"
              value={data?.overall_rate ?? 0}
              precision={2}
              suffix="%"
              prefix={<PercentageOutlined />}
              className={getOverallRateClassName(data?.overall_rate ?? 0)}
            />
          </Card>
        </Col>

        <Col xs={24} sm={12} md={6}>
          <Card className={styles.summaryCard}>
            <Statistic
              title="趋势变化"
              value={data?.trend_percentage ?? 0}
              precision={2}
              suffix="%"
              prefix={getTrendIcon(trendDirection)}
              className={
                trendDirection === 'up'
                  ? styles.statisticSuccess
                  : trendDirection === 'down'
                    ? styles.statisticError
                    : styles.statisticMuted
              }
            />
          </Card>
        </Col>

        <Col xs={24} sm={12} md={6}>
          <Card className={styles.summaryCard}>
            <Statistic
              title="经营类物业出租率"
              value={
                data?.by_property_nature?.find(item => item.property_nature === '经营类')?.rate ?? 0
              }
              precision={2}
              suffix="%"
              className={styles.statisticPrimary}
            />
          </Card>
        </Col>

        <Col xs={24} sm={12} md={6}>
          <Card className={styles.summaryCard}>
            <Statistic
              title="权属方数量"
              value={data?.by_owner_party?.length ?? 0}
              suffix="个"
              className={styles.statisticAccent}
            />
          </Card>
        </Col>
      </Row>

      {/* 图表区域 */}
      <Row gutter={16}>
        {/* 趋势图 */}
        <Col xs={24} lg={12}>
          <Card title="出租率趋势分析" className={styles.chartCard}>
            <Spin spinning={isLoading}>
              <Line {...trendChartConfig} height={height} />
            </Spin>
          </Card>
        </Col>

        {/* 物业性质分布 */}
        <Col xs={24} lg={12}>
          <Card title="物业性质出租率分布" className={styles.chartCard}>
            <Spin spinning={isLoading}>
              <Pie {...propertyNatureChartConfig} height={height} />
            </Spin>
          </Card>
        </Col>

        {/* 权属方对比 */}
        <Col xs={24}>
          <Card title="权属方出租率对比">
            <Spin spinning={isLoading}>
              <Column {...ownershipChartConfig} height={height} />
            </Spin>
          </Card>
        </Col>
      </Row>

      {/* 表现排行 */}
      <Row gutter={16} className={styles.rankingRow}>
        <Col xs={24} md={12}>
          <Card title="出租率最高资产" size="small">
            <div className={styles.rankingList}>
              {data?.top_performers?.map((asset, index) => (
                <div
                  key={asset.property_name}
                  className={
                    index < (data.top_performers?.length ?? 0) - 1
                      ? styles.rankingItem
                      : `${styles.rankingItem} ${styles.rankingItemLast}`
                  }
                >
                  <div className={styles.rankingInfo}>
                    <Text strong>{asset.property_name}</Text>
                    <br />
                    <Text type="secondary" className={styles.rankingMeta}>
                      面积: {asset.area?.toLocaleString()} ㎡
                    </Text>
                  </div>
                  <div className={styles.rankingValue}>
                    <Text className={styles.rankingRateHigh}>{(asset.rate ?? 0).toFixed(2)}%</Text>
                    <div className={styles.rankingLabel}>高位</div>
                  </div>
                </div>
              ))}
            </div>
          </Card>
        </Col>

        <Col xs={24} md={12}>
          <Card title="出租率最低资产" size="small">
            <div className={styles.rankingList}>
              {data?.low_performers?.map((asset, index) => (
                <div
                  key={asset.property_name}
                  className={
                    index < (data.low_performers?.length ?? 0) - 1
                      ? styles.rankingItem
                      : `${styles.rankingItem} ${styles.rankingItemLast}`
                  }
                >
                  <div className={styles.rankingInfo}>
                    <Text strong>{asset.property_name}</Text>
                    <br />
                    <Text type="secondary" className={styles.rankingMeta}>
                      面积: {asset.area?.toLocaleString()} ㎡
                    </Text>
                  </div>
                  <div className={styles.rankingValue}>
                    <Text className={styles.rankingRateLow}>{(asset.rate ?? 0).toFixed(2)}%</Text>
                    <div className={styles.rankingLabel}>低位</div>
                  </div>
                </div>
              ))}
            </div>
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default React.memo(OccupancyRateChart);
