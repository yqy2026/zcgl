import React, { useMemo } from 'react';
import { Card, Row, Col, Statistic, Spin, Alert, Typography, Space, Progress, Tag } from 'antd';
import { BuildOutlined, HomeOutlined, ShopOutlined } from '@ant-design/icons';
import { useQuery } from '@tanstack/react-query';
import { Column, DualAxes } from '@ant-design/plots';

import { assetService } from '@/services/assetService';
import type { AssetSearchParams, AreaStatistics } from '@/types/asset';
import { CHART_COLORS, CHART_LABEL_COLORS, COLORS } from '@/styles/colorMap';
import type {
  ChartDataPoint,
  DualAxesDataPoint,
  AreaRangeDataPoint,
  TooltipFormatterResult,
  TooltipCustomContentProps,
  ChartColorFunction,
} from '@/types/charts';
import styles from './AreaStatisticsChart.module.css';

const { Text } = Typography;

interface AreaStatisticsChartProps {
  filters?: AssetSearchParams;
  height?: number;
}

const AreaStatisticsChart: React.FC<AreaStatisticsChartProps> = ({ filters, height = 400 }) => {
  const getOccupancyProgressColor = (occupancyRate: number): string => {
    if (occupancyRate >= 80) return COLORS.success;
    if (occupancyRate >= 60) return COLORS.warning;
    return COLORS.error;
  };

  // 获取面积统计数据
  const { data, isLoading, error } = useQuery<AreaStatistics>({
    queryKey: ['area-statistics', filters],
    queryFn: async (): Promise<AreaStatistics> => assetService.getAreaStatistics(filters),
    refetchInterval: 5 * 60 * 1000, // 5分钟刷新一次
  });

  // 物业性质面积对比图表配置 - 为@ant-design/plots转换数据格式
  const propertyNatureChartData = useMemo(
    () =>
      data?.by_property_nature?.flatMap(item => [
        { property_nature: item.property_nature, type: '土地面积', value: item.land_area },
        { property_nature: item.property_nature, type: '房产面积', value: item.property_area },
        { property_nature: item.property_nature, type: '可租面积', value: item.rentable_area },
        { property_nature: item.property_nature, type: '已租面积', value: item.rented_area },
      ]) ?? [],
    [data]
  );

  const propertyNatureChartConfig = useMemo(
    () => ({
      data: propertyNatureChartData,
      xField: 'property_nature' as const,
      yField: 'value' as const,
      seriesField: 'type' as const,
      color: (({ type }: ChartDataPoint): string => {
        const typeStr = type as string;
        if (typeStr === '土地面积') return CHART_COLORS[0];
        if (typeStr === '房产面积') return CHART_COLORS[1];
        if (typeStr === '可租面积') return CHART_COLORS[2];
        if (typeStr === '已租面积') return CHART_COLORS[4];
        return CHART_COLORS[0];
      }) as ChartColorFunction,
      columnStyle: {
        fillOpacity: 0.6,
        lineWidth: 1,
      },
      legend: {
        position: 'top' as const,
      },
      tooltip: {
        formatter: (datum: ChartDataPoint): TooltipFormatterResult => ({
          name: (datum.type as string) ?? '',
          value: `${(datum.value as number | undefined)?.toLocaleString()} ㎡`,
        }),
      },
      yAxis: {
        min: 0,
        label: {
          formatter: (value: number) => `${Number(value).toLocaleString()} ㎡`,
        },
      },
      animation: {
        appear: {
          animation: 'scale-in-y' as const,
          duration: 1000,
        },
      },
    }),
    [propertyNatureChartData]
  );

  // 权属方面积对比图表配置 - DualAxes for area + occupancy rate
  const ownershipEntityData = useMemo(
    () =>
      data?.by_ownership_entity?.slice(0, 10).map(
        (item): DualAxesDataPoint => ({
          entity:
            item.ownership_entity.length > 8
              ? item.ownership_entity.substring(0, 8) + '...'
              : item.ownership_entity,
          total_area: item.total_area,
          occupancy_rate: item.occupancy_rate,
          full_name: item.ownership_entity,
        })
      ) ?? [],
    [data]
  );

  const ownershipEntityChartConfig = useMemo(
    () => ({
      data: [ownershipEntityData, ownershipEntityData],
      xField: 'entity' as const,
      yField: ['total_area', 'occupancy_rate'] as const,
      geometryOptions: [
        {
          geometry: 'column' as const,
          color: CHART_COLORS[0],
          columnStyle: {
            fillOpacity: 0.6,
          },
        },
        {
          geometry: 'line' as const,
          color: CHART_COLORS[3],
          lineStyle: {
            lineWidth: 2,
          },
          point: {
            size: 4,
          },
        },
      ],
      yAxis: {
        total_area: {
          min: 0,
          label: {
            formatter: (value: number) => `${Number(value).toLocaleString()} ㎡`,
          },
        },
        occupancy_rate: {
          min: 0,
          max: 100,
          label: {
            formatter: (value: number) => `${value}%`,
          },
        },
      },
      tooltip: {
        formatter: (datum: ChartDataPoint, type: string): TooltipFormatterResult => {
          if (type === 'total_area') {
            return {
              name: '总面积',
              value: `${(datum.total_area as number | undefined)?.toLocaleString()} ㎡`,
            };
          }
          return {
            name: '出租率',
            value: `${(datum.occupancy_rate as number | undefined)?.toFixed(2)}%`,
          };
        },
        customContent: (_title: string, tooltipData: TooltipCustomContentProps['data']) => {
          const datum = tooltipData?.[0]?.data as DualAxesDataPoint | undefined;
          if (datum == null) return null;
          return (
            <div className={styles.chartTooltip}>
              <div className={styles.tooltipTitle}>{datum.full_name ?? datum.entity}</div>
              <div>总面积: {datum.total_area?.toLocaleString()} ㎡</div>
              <div>出租率: {datum.occupancy_rate?.toFixed(2)}%</div>
            </div>
          );
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
    }),
    [ownershipEntityData]
  );

  // 面积区间分布图表配置
  const areaRangeChartData = useMemo(
    () =>
      data?.area_ranges?.map(
        (item): AreaRangeDataPoint => ({
          range: item.range,
          count: item.count,
          total_area: item.total_area ?? 0,
          percentage: item.percentage ?? 0,
        })
      ) ?? [],
    [data]
  );

  const areaRangeChartConfig = useMemo(
    () => ({
      data: areaRangeChartData,
      xField: 'range' as const,
      yField: 'count' as const,
      color: CHART_COLORS[1],
      columnStyle: {
        fillOpacity: 0.6,
        stroke: CHART_COLORS[1],
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
          name: (datum.range as string) ?? '',
          value: `${datum.count as number} 个`,
        }),
        customContent: (_title: string, tooltipData: TooltipCustomContentProps['data']) => {
          const datum = tooltipData?.[0]?.data as AreaRangeDataPoint | undefined;
          if (datum == null) return null;
          return (
            <div className={styles.chartTooltip}>
              <div className={styles.tooltipTitle}>{datum.range}</div>
              <div>资产数量: {datum.count} 个</div>
              <div>总面积: {datum.total_area?.toLocaleString()} ㎡</div>
              <div>占比: {datum.percentage?.toFixed(1)}%</div>
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
    [areaRangeChartData]
  );

  if (error !== undefined && error !== null) {
    return (
      <Alert
        title="数据加载失败"
        description="无法加载面积统计数据，请稍后重试"
        type="error"
        showIcon
      />
    );
  }

  return (
    <div className={styles.areaStatisticsChart}>
      {/* 总体统计 */}
      <Row gutter={16} className={styles.summaryRow}>
        <Col xs={12} sm={6} md={4}>
          <Card className={styles.summaryCard}>
            <Statistic
              title="总土地面积"
              value={data?.total_statistics?.total_land_area ?? 0}
              suffix="㎡"
              formatter={value => `${Number(value).toLocaleString()}`}
              prefix={<BuildOutlined />}
              className={styles.statisticLand}
            />
          </Card>
        </Col>

        <Col xs={12} sm={6} md={4}>
          <Card className={styles.summaryCard}>
            <Statistic
              title="总房产面积"
              value={data?.total_statistics?.total_property_area ?? 0}
              suffix="㎡"
              formatter={value => `${Number(value).toLocaleString()}`}
              prefix={<HomeOutlined />}
              className={styles.statisticProperty}
            />
          </Card>
        </Col>

        <Col xs={12} sm={6} md={4}>
          <Card className={styles.summaryCard}>
            <Statistic
              title="可租面积"
              value={data?.total_statistics?.total_rentable_area ?? 0}
              suffix="㎡"
              formatter={value => `${Number(value).toLocaleString()}`}
              prefix={<ShopOutlined />}
              className={styles.statisticRentable}
            />
          </Card>
        </Col>

        <Col xs={12} sm={6} md={4}>
          <Card className={styles.summaryCard}>
            <Statistic
              title="已租面积"
              value={data?.total_statistics?.total_rented_area ?? 0}
              suffix="㎡"
              formatter={value => `${Number(value).toLocaleString()}`}
              className={styles.statisticRented}
            />
          </Card>
        </Col>

        <Col xs={12} sm={6} md={4}>
          <Card className={styles.summaryCard}>
            <Statistic
              title="空置面积"
              value={data?.total_statistics?.total_vacant_area ?? 0}
              suffix="㎡"
              formatter={value => `${Number(value).toLocaleString()}`}
              className={styles.statisticVacant}
            />
          </Card>
        </Col>

        <Col xs={12} sm={6} md={4}>
          <Card className={styles.summaryCard}>
            <Statistic
              title="非经营面积"
              value={data?.total_statistics?.total_non_commercial_area ?? 0}
              suffix="㎡"
              formatter={value => `${Number(value).toLocaleString()}`}
              className={styles.statisticNonCommercial}
            />
          </Card>
        </Col>
      </Row>

      {/* 图表区域 */}
      <Row gutter={16}>
        {/* 物业性质面积分布 */}
        <Col xs={24} lg={12}>
          <Card title="物业性质面积分布" className={styles.chartCard}>
            <Spin spinning={isLoading}>
              <Column {...propertyNatureChartConfig} height={height} />
            </Spin>
          </Card>
        </Col>

        {/* 面积区间分布 */}
        <Col xs={24} lg={12}>
          <Card title="面积区间分布" className={styles.chartCard}>
            <Spin spinning={isLoading}>
              <Column {...areaRangeChartConfig} height={height} />
            </Spin>
          </Card>
        </Col>

        {/* 权属方面积与出租率对比 */}
        <Col xs={24}>
          <Card title="权属方面积与出租率对比">
            <Spin spinning={isLoading}>
              <DualAxes {...ownershipEntityChartConfig} height={height} />
            </Spin>
          </Card>
        </Col>
      </Row>

      {/* 详细统计 */}
      <Row gutter={16} className={styles.detailsRow}>
        <Col xs={24} lg={12}>
          <Card title="使用状态面积统计" size="small">
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
                  <div className={styles.detailItemHeader}>
                    <Space>
                      <Tag
                        color={
                          item.usage_status === '出租'
                            ? 'green'
                            : item.usage_status === '闲置'
                              ? 'red'
                              : item.usage_status === '自用'
                                ? 'blue'
                                : 'default'
                        }
                      >
                        {item.usage_status}
                      </Tag>
                      <Text strong>{item.asset_count} 个资产</Text>
                    </Space>
                    <Text className={styles.detailAreaValue}>
                      {item.total_area?.toLocaleString()} ㎡
                    </Text>
                  </div>
                  <div>
                    <Text type="secondary" className={styles.detailMeta}>
                      平均面积: {item.average_area?.toLocaleString()} ㎡
                    </Text>
                  </div>
                </div>
              ))}
            </div>
          </Card>
        </Col>

        <Col xs={24} lg={12}>
          <Card title="面积最大资产（前10名）" size="small">
            <div className={styles.detailList}>
              {data?.top_assets_by_area?.map((asset, index) => (
                <div
                  key={asset.property_name}
                  className={
                    index < (data.top_assets_by_area?.length ?? 0) - 1
                      ? styles.detailItem
                      : `${styles.detailItem} ${styles.detailItemLast}`
                  }
                >
                  <div className={styles.topAssetHeader}>
                    <div className={styles.topAssetLeft}>
                      <Text strong>{asset.property_name}</Text>
                      <br />
                      <Text type="secondary" className={styles.detailMeta}>
                        房产面积: {asset.property_area?.toLocaleString()} ㎡
                      </Text>
                    </div>
                    <div className={styles.topAssetRight}>
                      <Text className={styles.topAssetArea}>
                        {asset.rentable_area?.toLocaleString()} ㎡
                      </Text>
                      <br />
                      <Text className={styles.topAssetOccupancy}>
                        出租率: {asset.occupancy_rate?.toFixed(1)}%
                      </Text>
                    </div>
                  </div>

                  {asset.rentable_area != null && asset.rentable_area > 0 && (
                    <Progress
                      percent={asset.occupancy_rate ?? 0}
                      size="small"
                      strokeColor={getOccupancyProgressColor(asset.occupancy_rate ?? 0)}
                      format={percent => `${percent?.toFixed(1)}%`}
                      className={styles.topAssetProgress}
                    />
                  )}
                </div>
              ))}
            </div>
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default React.memo(AreaStatisticsChart);
