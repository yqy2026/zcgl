import React, { useMemo } from 'react';
import { Card, Row, Col, Statistic, Spin, Alert, Typography, Space, Tag } from 'antd';
import { HomeOutlined, UserOutlined } from '@ant-design/icons';
import { useQuery } from '@tanstack/react-query';
import { Pie, Column } from '@ant-design/plots';

import { assetService } from '@/services/assetService';
import type { AssetSearchParams } from '@/types/asset';
import { CHART_COLORS, CHART_LABEL_COLORS } from '@/styles/colorMap';
import type {
  ChartDataPoint,
  DistributionDataPoint,
  ColumnDataPoint,
  TooltipFormatterResult,
  TooltipCustomContentProps,
} from '@/types/charts';
import styles from './AssetDistributionChart.module.css';

const { Text } = Typography;

interface _AssetDistributionData {
  total_assets: number;
  by_property_nature: Array<{
    property_nature: string;
    count: number;
    percentage: number;
    total_area: number;
  }>;
  by_ownership_status: Array<{
    ownership_status: string;
    count: number;
    percentage: number;
  }>;
  by_usage_status: Array<{
    usage_status: string;
    count: number;
    percentage: number;
  }>;
  by_owner_party: Array<{
    owner_party_name: string;
    count: number;
    percentage: number;
    total_area: number;
  }>;
  by_region: Array<{
    region: string;
    count: number;
    percentage: number;
  }>;
  summary: {
    total_area: number;
    commercial_area: number;
    non_commercial_area: number;
    rented_area: number;
    vacant_area: number;
  };
}

interface AssetDistributionChartProps {
  filters?: AssetSearchParams;
  height?: number;
}

const AssetDistributionChart: React.FC<AssetDistributionChartProps> = ({
  filters,
  height = 300,
}) => {
  // 获取资产分布数据
  const { data, isLoading, error } = useQuery({
    queryKey: ['asset-distribution-stats', filters],
    queryFn: () => assetService.getAssetDistributionStats(filters),
    refetchInterval: 5 * 60 * 1000, // 5分钟刷新一次
  });

  // 物业性质分布图表配置
  const propertyNatureChartConfig = useMemo(
    () => ({
      data:
        data?.by_property_nature?.map(
          (item): DistributionDataPoint => ({
            type: item.property_nature,
            value: item.count ?? 0,
            percentage: item.percentage,
            total_area: item.total_area,
          })
        ) ?? [],
      angleField: 'value' as const,
      colorField: 'type' as const,
      color: CHART_COLORS,
      radius: 0.8,
      innerRadius: 0.4,
      label: {
        type: 'outer' as const,
        content: '{percentage}%',
      },
      legend: {
        layout: 'horizontal' as const,
        position: 'bottom' as const,
      },
      tooltip: {
        formatter: (datum: ChartDataPoint): TooltipFormatterResult => ({
          name: (datum.type as string) ?? '',
          value: `${datum.value as number} 个`,
        }),
        customContent: (_title: string, tooltipData: TooltipCustomContentProps['data']) => {
          const datum = tooltipData?.[0]?.data as DistributionDataPoint | undefined;
          if (datum == null) return null;
          return (
            <div className={styles.chartTooltip}>
              <div className={styles.tooltipTitle}>{datum.type}</div>
              <div>数量: {datum.value} 个</div>
              <div>占比: {datum.percentage?.toFixed(1)}%</div>
              <div>总面积: {datum.total_area?.toLocaleString()} ㎡</div>
            </div>
          );
        },
      },
    }),
    [data]
  );

  // 确权状态分布图表配置
  const ownershipStatusChartConfig = useMemo(
    () => ({
      data:
        data?.by_ownership_status?.map(
          (item): DistributionDataPoint => ({
            type: item.ownership_status,
            value: item.count ?? 0,
            percentage: item.percentage,
          })
        ) ?? [],
      angleField: 'value' as const,
      colorField: 'type' as const,
      color: [CHART_COLORS[1], CHART_COLORS[3], CHART_COLORS[2], CHART_COLORS[0]],
      radius: 0.8,
      innerRadius: 0.6,
      label: {
        type: 'inner' as const,
        offset: '-50%',
        content: '{percentage}%',
        style: {
          textAlign: 'center' as const,
          fontSize: 14,
          fill: CHART_LABEL_COLORS.light,
        },
      },
      legend: {
        layout: 'horizontal' as const,
        position: 'bottom' as const,
      },
      tooltip: {
        formatter: (datum: ChartDataPoint): TooltipFormatterResult => ({
          name: (datum.type as string) ?? '',
          value: `${datum.value as number} 个 (${(datum.percentage as number | undefined)?.toFixed(1) ?? 0}%)`,
        }),
      },
    }),
    [data]
  );

  // 使用状态分布图表配置
  const usageStatusChartConfig = useMemo(
    () => ({
      data:
        data?.by_usage_status?.map(
          (item): DistributionDataPoint => ({
            type: item.usage_status,
            value: item.count ?? 0,
            percentage: item.percentage,
          })
        ) ?? [],
      angleField: 'value' as const,
      colorField: 'type' as const,
      color: [CHART_COLORS[1], CHART_COLORS[3], CHART_COLORS[0], CHART_COLORS[4], CHART_COLORS[2]],
      radius: 0.8,
      innerRadius: 0.4,
      label: {
        type: 'outer' as const,
        content: '{percentage}%',
      },
      legend: {
        layout: 'horizontal' as const,
        position: 'bottom' as const,
      },
      tooltip: {
        formatter: (datum: ChartDataPoint): TooltipFormatterResult => ({
          name: (datum.type as string) ?? '',
          value: `${datum.value as number} 个 (${(datum.percentage as number | undefined)?.toFixed(1) ?? 0}%)`,
        }),
      },
    }),
    [data]
  );

  // 权属方分布柱状图配置
  const ownershipEntityChartConfig = useMemo(
    () => ({
      data:
        data?.by_owner_party?.slice(0, 10).map(
          (item): ColumnDataPoint => ({
            entity:
              item.owner_party_name.length > 8
                ? item.owner_party_name.substring(0, 8) + '...'
                : item.owner_party_name,
            count: item.count ?? 0,
            percentage: item.percentage,
            total_area: item.total_area,
            full_name: item.owner_party_name,
            value: item.count ?? 0,
          })
        ) ?? [],
      xField: 'entity' as const,
      yField: 'count' as const,
      color: CHART_COLORS[0],
      columnStyle: {
        fillOpacity: 0.6,
        stroke: CHART_COLORS[0],
        lineWidth: 1,
      },
      label: {
        position: 'top' as const,
        formatter: (datum: ChartDataPoint): string => `${datum.count as number} 个`,
        style: {
          fill: CHART_LABEL_COLORS.dark,
          fontSize: 12,
        },
      },
      tooltip: {
        formatter: (datum: ChartDataPoint): TooltipFormatterResult => ({
          name: (datum.full_name as string | undefined) ?? (datum.entity as string) ?? '',
          value: `${datum.count as number} 个`,
        }),
        customContent: (_title: string, tooltipData: TooltipCustomContentProps['data']) => {
          const datum = tooltipData?.[0]?.data as ColumnDataPoint | undefined;
          if (datum == null) return null;
          return (
            <div className={styles.chartTooltip}>
              <div className={styles.tooltipTitle}>
                {datum.full_name ?? (datum.entity as string)}
              </div>
              <div>资产数量: {datum.count as number} 个</div>
              <div>占比: {datum.percentage?.toFixed(1) ?? 0}%</div>
              <div>总面积: {datum.total_area?.toLocaleString()} ㎡</div>
            </div>
          );
        },
      },
      yAxis: {
        min: 0,
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

  const getUsageStatusTone = (usageStatus: string): 'green' | 'red' | 'blue' | 'default' => {
    if (usageStatus === '出租') return 'green';
    if (usageStatus === '闲置') return 'red';
    if (usageStatus === '自用') return 'blue';
    return 'default';
  };

  if (error !== undefined && error !== null) {
    return (
      <Alert
        title="数据加载失败"
        description="无法加载资产分布统计数据，请稍后重试"
        type="error"
        showIcon
      />
    );
  }

  return (
    <div className={styles.assetDistributionChart}>
      {/* 总体统计 */}
      <Row gutter={16} className={styles.summaryRow}>
        <Col xs={12} sm={6}>
          <Card className={styles.summaryCard}>
            <Statistic
              title="资产总数"
              value={data?.total_assets ?? 0}
              suffix="个"
              prefix={<HomeOutlined />}
              className={styles.statisticPrimary}
            />
          </Card>
        </Col>

        <Col xs={12} sm={6}>
          <Card className={styles.summaryCard}>
            <Statistic
              title="总面积"
              value={data?.summary?.total_area ?? 0}
              suffix="㎡"
              formatter={value => `${Number(value).toLocaleString()}`}
              className={styles.statisticSuccess}
            />
          </Card>
        </Col>

        <Col xs={12} sm={6}>
          <Card className={styles.summaryCard}>
            <Statistic
              title="权属方数量"
              value={data?.by_owner_party?.length ?? 0}
              suffix="个"
              prefix={<UserOutlined />}
              className={styles.statisticAccent}
            />
          </Card>
        </Col>

        <Col xs={12} sm={6}>
          <Card className={styles.summaryCard}>
            <Statistic
              title="经营类面积"
              value={data?.summary?.commercial_area ?? 0}
              suffix="㎡"
              formatter={value => `${Number(value).toLocaleString()}`}
              className={styles.statisticWarning}
            />
          </Card>
        </Col>
      </Row>

      {/* 分布图表 */}
      <Row gutter={16}>
        {/* 物业性质分布 */}
        <Col xs={24} md={12} lg={8}>
          <Card title="物业性质分布" className={styles.chartCard}>
            <Spin spinning={isLoading}>
              <Pie {...propertyNatureChartConfig} height={height} />
            </Spin>
          </Card>
        </Col>

        {/* 确权状态分布 */}
        <Col xs={24} md={12} lg={8}>
          <Card title="确权状态分布" className={styles.chartCard}>
            <Spin spinning={isLoading}>
              <Pie {...ownershipStatusChartConfig} height={height} />
            </Spin>
          </Card>
        </Col>

        {/* 使用状态分布 */}
        <Col xs={24} md={12} lg={8}>
          <Card title="使用状态分布" className={styles.chartCard}>
            <Spin spinning={isLoading}>
              <Pie {...usageStatusChartConfig} height={height} />
            </Spin>
          </Card>
        </Col>

        {/* 权属方分布 */}
        <Col xs={24}>
          <Card title="主要权属方资产分布（前10名）">
            <Spin spinning={isLoading}>
              <Column {...ownershipEntityChartConfig} height={height} />
            </Spin>
          </Card>
        </Col>
      </Row>

      {/* 详细统计 */}
      <Row gutter={16} className={styles.detailsRow}>
        <Col xs={24} md={12}>
          <Card title="物业性质详情" size="small">
            <div className={styles.detailList}>
              {data?.by_property_nature?.map((item, index) => (
                <div
                  key={item.property_nature}
                  className={
                    index < (data.by_property_nature?.length ?? 0) - 1
                      ? styles.detailItem
                      : `${styles.detailItem} ${styles.detailItemLast}`
                  }
                >
                  <div>
                    <Space>
                      <Tag color={index === 0 ? 'blue' : 'green'}>{item.property_nature}</Tag>
                      <Text>{item.count} 个</Text>
                    </Space>
                    <br />
                    <Text type="secondary" className={styles.detailMeta}>
                      面积: {item.total_area?.toLocaleString()} ㎡
                    </Text>
                  </div>
                  <div className={styles.detailValue}>
                    <Text className={styles.detailPercentage}>{item.percentage?.toFixed(1)}%</Text>
                    <div className={styles.detailLabel}>占比</div>
                  </div>
                </div>
              ))}
            </div>
          </Card>
        </Col>

        <Col xs={24} md={12}>
          <Card title="使用状态详情" size="small">
            <div className={styles.detailList}>
              {data?.by_usage_status?.map((item, index) => (
                <div
                  key={item.usage_status}
                  className={
                    index < (data.by_usage_status?.length ?? 0) - 1
                      ? styles.detailItem
                      : `${styles.detailItem} ${styles.detailItemLast}`
                  }
                >
                  <div>
                    <Space>
                      <Tag color={getUsageStatusTone(item.usage_status)}>{item.usage_status}</Tag>
                      <Text>{item.count} 个</Text>
                    </Space>
                  </div>
                  <div className={styles.detailValue}>
                    <Text className={styles.detailPercentage}>{item.percentage?.toFixed(1)}%</Text>
                    <div className={styles.detailLabel}>占比</div>
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

export default React.memo(AssetDistributionChart);
