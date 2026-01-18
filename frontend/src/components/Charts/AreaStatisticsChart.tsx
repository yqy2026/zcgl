import React from 'react';
import { Card, Row, Col, Statistic, Spin, Alert, Typography, Space, Progress, Tag } from 'antd';
import { BuildOutlined, HomeOutlined, ShopOutlined } from '@ant-design/icons';
import { useQuery } from '@tanstack/react-query';
import { Column, DualAxes } from '@ant-design/plots';

import { assetService } from '@/services/assetService';
import type { AssetSearchParams } from '@/types/asset';
import type {
  ChartDataPoint,
  DualAxesDataPoint,
  AreaRangeDataPoint,
  TooltipFormatterResult,
  TooltipCustomContentProps,
  ChartColorFunction,
} from '@/types/charts';

// Local interface matching the actual API response structure
interface AreaStatisticsData {
  total_statistics: {
    total_land_area: number;
    total_property_area: number;
    total_rentable_area: number;
    total_rented_area: number;
    total_vacant_area: number;
    total_non_commercial_area: number;
  };
  by_property_nature: Array<{
    property_nature: string;
    land_area: number;
    property_area: number;
    rentable_area: number;
    rented_area: number;
    vacant_area: number;
    non_commercial_area: number;
  }>;
  by_ownership_entity: Array<{
    ownership_entity: string;
    total_area: number;
    rentable_area: number;
    rented_area: number;
    occupancy_rate: number;
  }>;
  by_usage_status: Array<{
    usage_status: string;
    total_area: number;
    asset_count: number;
    average_area: number;
  }>;
  area_ranges: Array<{
    range: string;
    count: number;
    total_area: number;
    percentage: number;
  }>;
  top_assets_by_area: Array<{
    property_name: string;
    property_area: number;
    rentable_area: number;
    rented_area: number;
    occupancy_rate: number;
  }>;
}

const { Text } = Typography;

interface AreaStatisticsChartProps {
  filters?: AssetSearchParams;
  height?: number;
}

const AreaStatisticsChart: React.FC<AreaStatisticsChartProps> = ({ filters, height = 400 }) => {
  // 获取面积统计数据
  const { data, isLoading, error } = useQuery<AreaStatisticsData>({
    queryKey: ['area-statistics', filters],
    queryFn: async (): Promise<AreaStatisticsData> => {
      const result = await assetService.getAreaStatistics(filters);
      return result as unknown as AreaStatisticsData;
    },
    refetchInterval: 5 * 60 * 1000, // 5分钟刷新一次
  });

  // 物业性质面积对比图表配置 - 为@ant-design/plots转换数据格式
  const propertyNatureChartData =
    data?.by_property_nature?.flatMap(item => [
      { property_nature: item.property_nature, type: '土地面积', value: item.land_area },
      { property_nature: item.property_nature, type: '房产面积', value: item.property_area },
      { property_nature: item.property_nature, type: '可租面积', value: item.rentable_area },
      { property_nature: item.property_nature, type: '已租面积', value: item.rented_area },
    ]) ?? [];

  const propertyNatureChartConfig = {
    data: propertyNatureChartData,
    xField: 'property_nature' as const,
    yField: 'value' as const,
    seriesField: 'type' as const,
    color: (({ type }: ChartDataPoint): string => {
      const typeStr = type as string;
      if (typeStr === '土地面积') return '#1890ff';
      if (typeStr === '房产面积') return '#52c41a';
      if (typeStr === '可租面积') return '#faad14';
      if (typeStr === '已租面积') return '#722ed1';
      return '#1890ff';
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
  };

  // 权属方面积对比图表配置 - DualAxes for area + occupancy rate
  const ownershipEntityData =
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
    ) ?? [];

  const ownershipEntityChartConfig = {
    data: [ownershipEntityData, ownershipEntityData],
    xField: 'entity' as const,
    yField: ['total_area', 'occupancy_rate'] as const,
    geometryOptions: [
      {
        geometry: 'column' as const,
        color: '#1890ff',
        columnStyle: {
          fillOpacity: 0.6,
        },
      },
      {
        geometry: 'line' as const,
        color: '#f5222d',
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
      customContent: (_title: string, data: TooltipCustomContentProps['data']) => {
        const datum = data?.[0]?.data as DualAxesDataPoint | undefined;
        if (datum == null) return null;
        return (
          <div style={{ padding: '8px' }}>
            <div style={{ fontWeight: 'bold', marginBottom: '4px' }}>
              {(datum.full_name as string | undefined) ?? (datum.entity as string)}
            </div>
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
  };

  // 面积区间分布图表配置
  const areaRangeChartConfig = {
    data:
      data?.area_ranges?.map(
        (item): AreaRangeDataPoint => ({
          range: item.range,
          count: item.count,
          total_area: item.total_area,
          percentage: item.percentage,
        })
      ) ?? [],
    xField: 'range' as const,
    yField: 'count' as const,
    color: '#52c41a',
    columnStyle: {
      fillOpacity: 0.6,
      stroke: '#52c41a',
      lineWidth: 1,
    },
    label: {
      position: 'top' as const,
      formatter: (datum: ChartDataPoint): string => `${datum.count as number} 个`,
      style: {
        fill: '#333',
        fontSize: 12,
      },
    },
    tooltip: {
      formatter: (datum: ChartDataPoint): TooltipFormatterResult => ({
        name: (datum.range as string) ?? '',
        value: `${datum.count as number} 个`,
      }),
      customContent: (_title: string, data: TooltipCustomContentProps['data']) => {
        const datum = data?.[0]?.data as AreaRangeDataPoint | undefined;
        if (datum == null) return null;
        return (
          <div style={{ padding: '8px' }}>
            <div style={{ fontWeight: 'bold', marginBottom: '4px' }}>{datum.range}</div>
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
  };

  if (error !== undefined && error !== null) {
    return (
      <Alert
        message="数据加载失败"
        description="无法加载面积统计数据，请稍后重试"
        type="error"
        showIcon
      />
    );
  }

  return (
    <div>
      {/* 总体统计 */}
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col xs={12} sm={6} md={4}>
          <Card>
            <Statistic
              title="总土地面积"
              value={data?.total_statistics?.total_land_area ?? 0}
              suffix="㎡"
              formatter={value => `${Number(value).toLocaleString()}`}
              prefix={<BuildOutlined />}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>

        <Col xs={12} sm={6} md={4}>
          <Card>
            <Statistic
              title="总房产面积"
              value={data?.total_statistics?.total_property_area ?? 0}
              suffix="㎡"
              formatter={value => `${Number(value).toLocaleString()}`}
              prefix={<HomeOutlined />}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>

        <Col xs={12} sm={6} md={4}>
          <Card>
            <Statistic
              title="可租面积"
              value={data?.total_statistics?.total_rentable_area ?? 0}
              suffix="㎡"
              formatter={value => `${Number(value).toLocaleString()}`}
              prefix={<ShopOutlined />}
              valueStyle={{ color: '#faad14' }}
            />
          </Card>
        </Col>

        <Col xs={12} sm={6} md={4}>
          <Card>
            <Statistic
              title="已租面积"
              value={data?.total_statistics?.total_rented_area ?? 0}
              suffix="㎡"
              formatter={value => `${Number(value).toLocaleString()}`}
              valueStyle={{ color: '#722ed1' }}
            />
          </Card>
        </Col>

        <Col xs={12} sm={6} md={4}>
          <Card>
            <Statistic
              title="空置面积"
              value={data?.total_statistics?.total_vacant_area ?? 0}
              suffix="㎡"
              formatter={value => `${Number(value).toLocaleString()}`}
              valueStyle={{ color: '#ff4d4f' }}
            />
          </Card>
        </Col>

        <Col xs={12} sm={6} md={4}>
          <Card>
            <Statistic
              title="非经营面积"
              value={data?.total_statistics?.total_non_commercial_area ?? 0}
              suffix="㎡"
              formatter={value => `${Number(value).toLocaleString()}`}
              valueStyle={{ color: '#8c8c8c' }}
            />
          </Card>
        </Col>
      </Row>

      {/* 图表区域 */}
      <Row gutter={16}>
        {/* 物业性质面积分布 */}
        <Col xs={24} lg={12}>
          <Card title="物业性质面积分布" style={{ marginBottom: 16 }}>
            <Spin spinning={isLoading}>
              <Column {...propertyNatureChartConfig} height={height} />
            </Spin>
          </Card>
        </Col>

        {/* 面积区间分布 */}
        <Col xs={24} lg={12}>
          <Card title="面积区间分布" style={{ marginBottom: 16 }}>
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
      <Row gutter={16} style={{ marginTop: 16 }}>
        <Col xs={24} lg={12}>
          <Card title="使用状态面积统计" size="small">
            <div style={{ maxHeight: 300, overflowY: 'auto' }}>
              {data?.by_usage_status?.map((item, index) => (
                <div
                  key={index}
                  style={{
                    padding: '12px 0',
                    borderBottom:
                      index < (data.by_usage_status?.length ?? 0) - 1
                        ? '1px solid #f0f0f0'
                        : 'none',
                  }}
                >
                  <div
                    style={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                      marginBottom: 8,
                    }}
                  >
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
                    <Text style={{ fontWeight: 'bold' }}>
                      {item.total_area?.toLocaleString()} ㎡
                    </Text>
                  </div>
                  <div>
                    <Text type="secondary" style={{ fontSize: '12px' }}>
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
            <div style={{ maxHeight: 300, overflowY: 'auto' }}>
              {data?.top_assets_by_area?.map((asset, index) => (
                <div
                  key={index}
                  style={{
                    padding: '12px 0',
                    borderBottom:
                      index < (data.top_assets_by_area?.length ?? 0) - 1
                        ? '1px solid #f0f0f0'
                        : 'none',
                  }}
                >
                  <div
                    style={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'flex-start',
                      marginBottom: 8,
                    }}
                  >
                    <div style={{ flex: 1 }}>
                      <Text strong>{asset.property_name}</Text>
                      <br />
                      <Text type="secondary" style={{ fontSize: '12px' }}>
                        房产面积: {asset.property_area?.toLocaleString()} ㎡
                      </Text>
                    </div>
                    <div style={{ textAlign: 'right' }}>
                      <Text style={{ fontWeight: 'bold', color: '#1890ff' }}>
                        {asset.rentable_area?.toLocaleString()} ㎡
                      </Text>
                      <br />
                      <Text style={{ fontSize: '12px', color: '#52c41a' }}>
                        出租率: {asset.occupancy_rate?.toFixed(1)}%
                      </Text>
                    </div>
                  </div>

                  {asset.rentable_area && asset.rentable_area > 0 && (
                    <Progress
                      percent={asset.occupancy_rate ?? 0}
                      size="small"
                      strokeColor={
                        (asset.occupancy_rate ?? 0) >= 80
                          ? '#52c41a'
                          : (asset.occupancy_rate ?? 0) >= 60
                            ? '#faad14'
                            : '#ff4d4f'
                      }
                      format={percent => `${percent?.toFixed(1)}%`}
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

export default AreaStatisticsChart;
