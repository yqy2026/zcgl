import React from 'react';
import { Card, Row, Col, Statistic, Spin, Alert, Typography, Space, Tag } from 'antd';
import { HomeOutlined, UserOutlined } from '@ant-design/icons';
import { useQuery } from '@tanstack/react-query';
import { Pie, Column } from '@ant-design/plots';

import { assetService } from '@/services/assetService';
import type { AssetSearchParams } from '@/types/asset';
import type {
  ChartDataPoint,
  DistributionDataPoint,
  ColumnDataPoint,
  TooltipFormatterResult,
  TooltipCustomContentProps,
} from '@/types/charts';

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
  by_ownership_entity: Array<{
    ownership_entity: string;
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
  const propertyNatureChartConfig = {
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
    color: ['#1890ff', '#52c41a', '#faad14', '#f5222d', '#722ed1', '#fa8c16'],
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
      customContent: (_title: string, data: TooltipCustomContentProps['data']) => {
        const datum = data?.[0]?.data as DistributionDataPoint | undefined;
        if (datum == null) return null;
        return (
          <div style={{ padding: '8px' }}>
            <div style={{ fontWeight: 'bold', marginBottom: '4px' }}>{datum.type}</div>
            <div>数量: {datum.value} 个</div>
            <div>占比: {datum.percentage?.toFixed(1)}%</div>
            <div>总面积: {datum.total_area?.toLocaleString()} ㎡</div>
          </div>
        );
      },
    },
  };

  // 确权状态分布图表配置
  const ownershipStatusChartConfig = {
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
    color: ['#52c41a', '#ff4d4f', '#faad14', '#1890ff'],
    radius: 0.8,
    innerRadius: 0.6,
    label: {
      type: 'inner' as const,
      offset: '-50%',
      content: '{percentage}%',
      style: {
        textAlign: 'center' as const,
        fontSize: 14,
        fill: '#fff',
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
  };

  // 使用状态分布图表配置
  const usageStatusChartConfig = {
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
    color: ['#52c41a', '#ff4d4f', '#1890ff', '#722ed1', '#faad14'],
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
  };

  // 权属方分布柱状图配置
  const ownershipEntityChartConfig = {
    data:
      data?.by_ownership_entity?.slice(0, 10).map(
        (item): ColumnDataPoint => ({
          entity:
            item.ownership_entity.length > 8
              ? item.ownership_entity.substring(0, 8) + '...'
              : item.ownership_entity,
          count: item.count ?? 0,
          percentage: item.percentage,
          total_area: item.total_area,
          full_name: item.ownership_entity,
          value: item.count ?? 0,
        })
      ) ?? [],
    xField: 'entity' as const,
    yField: 'count' as const,
    color: '#1890ff',
    columnStyle: {
      fillOpacity: 0.6,
      stroke: '#1890ff',
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
        name: (datum.full_name as string | undefined) ?? (datum.entity as string) ?? '',
        value: `${datum.count as number} 个`,
      }),
      customContent: (_title: string, data: TooltipCustomContentProps['data']) => {
        const datum = data?.[0]?.data as ColumnDataPoint | undefined;
        if (datum == null) return null;
        return (
          <div style={{ padding: '8px' }}>
            <div style={{ fontWeight: 'bold', marginBottom: '4px' }}>
              {(datum.full_name as string | undefined) ?? (datum.entity as string)}
            </div>
            <div>资产数量: {datum.count as number} 个</div>
            <div>占比: {(datum.percentage as number | undefined)?.toFixed(1) ?? 0}%</div>
            <div>总面积: {(datum.total_area as number | undefined)?.toLocaleString()} ㎡</div>
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
        description="无法加载资产分布统计数据，请稍后重试"
        type="error"
        showIcon
      />
    );
  }

  return (
    <div>
      {/* 总体统计 */}
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col xs={12} sm={6}>
          <Card>
            <Statistic
              title="资产总数"
              value={data?.total_assets ?? 0}
              suffix="个"
              prefix={<HomeOutlined />}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>

        <Col xs={12} sm={6}>
          <Card>
            <Statistic
              title="总面积"
              value={data?.summary?.total_area ?? 0}
              suffix="㎡"
              formatter={value => `${Number(value).toLocaleString()}`}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>

        <Col xs={12} sm={6}>
          <Card>
            <Statistic
              title="权属方数量"
              value={data?.by_ownership_entity?.length ?? 0}
              suffix="个"
              prefix={<UserOutlined />}
              valueStyle={{ color: '#722ed1' }}
            />
          </Card>
        </Col>

        <Col xs={12} sm={6}>
          <Card>
            <Statistic
              title="经营类面积"
              value={data?.summary?.commercial_area ?? 0}
              suffix="㎡"
              formatter={value => `${Number(value).toLocaleString()}`}
              valueStyle={{ color: '#faad14' }}
            />
          </Card>
        </Col>
      </Row>

      {/* 分布图表 */}
      <Row gutter={16}>
        {/* 物业性质分布 */}
        <Col xs={24} md={12} lg={8}>
          <Card title="物业性质分布" style={{ marginBottom: 16 }}>
            <Spin spinning={isLoading}>
              <Pie {...propertyNatureChartConfig} height={height} />
            </Spin>
          </Card>
        </Col>

        {/* 确权状态分布 */}
        <Col xs={24} md={12} lg={8}>
          <Card title="确权状态分布" style={{ marginBottom: 16 }}>
            <Spin spinning={isLoading}>
              <Pie {...ownershipStatusChartConfig} height={height} />
            </Spin>
          </Card>
        </Col>

        {/* 使用状态分布 */}
        <Col xs={24} md={12} lg={8}>
          <Card title="使用状态分布" style={{ marginBottom: 16 }}>
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
      <Row gutter={16} style={{ marginTop: 16 }}>
        <Col xs={24} md={12}>
          <Card title="物业性质详情" size="small">
            <div style={{ maxHeight: 300, overflowY: 'auto' }}>
              {data?.by_property_nature?.map((item, index) => (
                <div
                  key={index}
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    padding: '8px 0',
                    borderBottom:
                      index < (data.by_property_nature?.length ?? 0) - 1
                        ? '1px solid #f0f0f0'
                        : 'none',
                  }}
                >
                  <div>
                    <Space>
                      <Tag color={index === 0 ? 'blue' : 'green'}>{item.property_nature}</Tag>
                      <Text>{item.count} 个</Text>
                    </Space>
                    <br />
                    <Text type="secondary" style={{ fontSize: '12px' }}>
                      面积: {item.total_area?.toLocaleString()} ㎡
                    </Text>
                  </div>
                  <div style={{ textAlign: 'right' }}>
                    <Text style={{ fontWeight: 'bold' }}>{item.percentage?.toFixed(1)}%</Text>
                  </div>
                </div>
              ))}
            </div>
          </Card>
        </Col>

        <Col xs={24} md={12}>
          <Card title="使用状态详情" size="small">
            <div style={{ maxHeight: 300, overflowY: 'auto' }}>
              {data?.by_usage_status?.map((item, index) => (
                <div
                  key={index}
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    padding: '8px 0',
                    borderBottom:
                      index < (data.by_usage_status?.length ?? 0) - 1
                        ? '1px solid #f0f0f0'
                        : 'none',
                  }}
                >
                  <div>
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
                      <Text>{item.count} 个</Text>
                    </Space>
                  </div>
                  <div style={{ textAlign: 'right' }}>
                    <Text style={{ fontWeight: 'bold' }}>{item.percentage?.toFixed(1)}%</Text>
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

export default AssetDistributionChart;
