import React from 'react'
import { Card, Typography, Statistic, Row, Col, Spin, Alert } from 'antd'
import {
  PercentageOutlined,
  RiseOutlined,
  FallOutlined,
  MinusOutlined,
} from '@ant-design/icons'
import { useQuery } from '@tanstack/react-query'
import { Line, Column, Pie } from '@ant-design/plots'

import { assetService } from '@/services/assetService'
import type { AssetSearchParams } from '@/types/asset'
import type {
  ChartDataPoint,
  TrendDataPoint,
  DistributionDataPoint,
  ColumnDataPoint,
  TooltipFormatterResult,
  TooltipCustomContentProps,
} from '@/types/charts'

const { Text } = Typography

interface _OccupancyRateData {
  overall_rate: number
  trend: 'up' | 'down' | 'stable'
  trend_percentage: number
  by_property_nature: Array<{
    property_nature: string
    rate: number
    total_area: number
    rented_area: number
  }>
  by_ownership_entity: Array<{
    ownership_entity: string
    rate: number
    asset_count: number
  }>
  monthly_trend: Array<{
    month: string
    rate: number
    total_area: number
    rented_area: number
  }>
  top_performers: Array<{
    property_name: string
    rate: number
    area: number
  }>
  low_performers: Array<{
    property_name: string
    rate: number
    area: number
  }>
}

interface OccupancyRateChartProps {
  filters?: AssetSearchParams
  height?: number
}

const OccupancyRateChart: React.FC<OccupancyRateChartProps> = ({
  filters,
  height = 400,
}) => {
  // 获取出租率数据
  const { data, isLoading, error } = useQuery({
    queryKey: ['occupancy-rate-stats', filters],
    queryFn: () => assetService.getOccupancyRateStats(filters),
    refetchInterval: 5 * 60 * 1000, // 5分钟刷新一次
  })

  // 趋势图表配置
  const trendChartConfig = {
    data: data?.monthly_trend?.map((item): TrendDataPoint => ({
      month: item.month,
      rate: item.rate,
      total_area: item.total_area,
      rented_area: item.rented_area,
    })) ?? [],
    xField: 'month' as const,
    yField: 'rate' as const,
    smooth: true,
    color: '#1890ff',
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
      customContent: (_title: string, data: TooltipCustomContentProps['data']) => {
        const datum = data?.[0]?.data as TrendDataPoint | undefined
        if (datum == null) return null
        return (
          <div style={{ padding: '8px' }}>
            <div style={{ fontWeight: 'bold', marginBottom: '4px' }}>{datum.month}</div>
            <div>出租率: {datum.rate.toFixed(2)}%</div>
            <div>总面积: {datum.total_area?.toLocaleString()} ㎡</div>
            <div>已租面积: {datum.rented_area?.toLocaleString()} ㎡</div>
          </div>
        )
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
  }

  // 物业性质分布图表配置
  const propertyNatureChartConfig = {
    data: data?.by_property_nature?.map((item): DistributionDataPoint => ({
      type: item.property_nature,
      value: item.rate,
      total_area: item.total_area,
      rented_area: item.rented_area,
    })) ?? [],
    angleField: 'value' as const,
    colorField: 'type' as const,
    color: ['#1890ff', '#52c41a', '#faad14', '#f5222d', '#722ed1', '#fa8c16'],
    radius: 0.8,
    innerRadius: 0.6,
    label: {
      type: 'inner' as const,
      offset: '-50%',
      content: '{value}%',
      style: {
        textAlign: 'center' as const,
        fontSize: 14,
        fill: '#fff',
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
      customContent: (_title: string, data: TooltipCustomContentProps['data']) => {
        const datum = data?.[0]?.data as DistributionDataPoint | undefined
        if (datum == null) return null
        return (
          <div style={{ padding: '8px' }}>
            <div style={{ fontWeight: 'bold', marginBottom: '4px' }}>{datum.type}</div>
            <div>出租率: {datum.value.toFixed(2)}%</div>
            <div>总面积: {datum.total_area?.toLocaleString()} ㎡</div>
            <div>已租面积: {datum.rented_area?.toLocaleString()} ㎡</div>
          </div>
        )
      },
    },
    statistic: {
      title: {
        offsetY: -8,
        content: '总体出租率',
        style: {
          fontSize: '14px',
        },
      },
      content: {
        offsetY: 4,
        style: {
          fontSize: '20px',
          fontWeight: 'bold' as const,
        },
        content: `${data?.overall_rate?.toFixed(2) ?? 0}%`,
      },
    },
  }

  // 权属方出租率柱状图配置
  const ownershipChartConfig = {
    data: data?.by_ownership_entity?.map((item): ColumnDataPoint => ({
      ownership: item.ownership_entity.length > 10
        ? item.ownership_entity.substring(0, 10) + '...'
        : item.ownership_entity,
      rate: item.rate,
      asset_count: item.asset_count,
      full_name: item.ownership_entity,
    })) ?? [],
    xField: 'ownership' as const,
    yField: 'rate' as const,
    color: '#1890ff',
    columnStyle: {
      fillOpacity: 0.6,
      stroke: '#1890ff',
      lineWidth: 1,
    },
    label: {
      position: 'top' as const,
      formatter: (datum: ChartDataPoint): string => `${(datum.rate as number).toFixed(1)}%`,
      style: {
        fill: '#333',
        fontSize: 12,
      },
    },
    tooltip: {
      formatter: (datum: ChartDataPoint): TooltipFormatterResult => ({
        name: ((datum.full_name as string | undefined) ?? (datum.ownership as string)) ?? '',
        value: `${(datum.rate as number).toFixed(2)}%`,
      }),
      customContent: (_title: string, data: TooltipCustomContentProps['data']) => {
        const datum = data?.[0]?.data as ColumnDataPoint | undefined
        if (datum == null) return null
        return (
          <div style={{ padding: '8px' }}>
            <div style={{ fontWeight: 'bold', marginBottom: '4px' }}>
              {(datum.full_name as string | undefined) ?? (datum.ownership as string)}
            </div>
            <div>出租率: {(datum.rate as number).toFixed(2)}%</div>
            <div>资产数量: {datum.asset_count as number} 个</div>
          </div>
        )
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
  }

  // 获取趋势图标
  const getTrendIcon = (trend: string, _percentage: number) => {
    if (trend === 'up') {
      return <RiseOutlined style={{ color: '#52c41a' }} />
    } else if (trend === 'down') {
      return <FallOutlined style={{ color: '#ff4d4f' }} />
    } else {
      return <MinusOutlined style={{ color: '#8c8c8c' }} />
    }
  }

  // 获取趋势颜色
  const getTrendColor = (trend: string) => {
    if (trend === 'up') return '#52c41a'
    if (trend === 'down') return '#ff4d4f'
    return '#8c8c8c'
  }

  if (error !== undefined && error !== null) {
    return (
      <Alert
        message="数据加载失败"
        description="无法加载出租率统计数据，请稍后重试"
        type="error"
        showIcon
      />
    )
  }

  return (
    <div>
      {/* 总体统计 */}
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="总体出租率"
              value={data?.overall_rate ?? 0}
              precision={2}
              suffix="%"
              prefix={<PercentageOutlined />}
              valueStyle={{
                color: (data?.overall_rate ?? 0) >= 80 ? '#52c41a' :
                       (data?.overall_rate ?? 0) >= 60 ? '#faad14' : '#ff4d4f'
              }}
            />
          </Card>
        </Col>
        
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="趋势变化"
              value={data?.trend_percentage ?? 0}
              precision={2}
              suffix="%"
              prefix={getTrendIcon(data?.trend ?? 'stable', data?.trend_percentage ?? 0)}
              valueStyle={{ color: getTrendColor(data?.trend ?? 'stable') }}
            />
          </Card>
        </Col>
        
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="经营类物业出租率"
              value={data?.by_property_nature?.find(item => item.property_nature === '经营类')?.rate ?? 0}
              precision={2}
              suffix="%"
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="权属方数量"
              value={data?.by_ownership_entity?.length ?? 0}
              suffix="个"
              valueStyle={{ color: '#722ed1' }}
            />
          </Card>
        </Col>
      </Row>

      {/* 图表区域 */}
      <Row gutter={16}>
        {/* 趋势图 */}
        <Col xs={24} lg={12}>
          <Card title="出租率趋势分析" style={{ marginBottom: 16 }}>
            <Spin spinning={isLoading}>
              <Line {...trendChartConfig} height={height} />
            </Spin>
          </Card>
        </Col>

        {/* 物业性质分布 */}
        <Col xs={24} lg={12}>
          <Card title="物业性质出租率分布" style={{ marginBottom: 16 }}>
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
      <Row gutter={16} style={{ marginTop: 16 }}>
        <Col xs={24} md={12}>
          <Card title="出租率最高资产" size="small">
            <div style={{ maxHeight: 300, overflowY: 'auto' }}>
              {data?.top_performers?.map((asset, index) => (
                <div key={index} style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  padding: '8px 0',
                  borderBottom: index < (data.top_performers?.length ?? 0) - 1 ? '1px solid #f0f0f0' : 'none'
                }}>
                  <div>
                    <Text strong>{asset.property_name}</Text>
                    <br />
                    <Text type="secondary" style={{ fontSize: '12px' }}>
                      面积: {asset.area?.toLocaleString()} ㎡
                    </Text>
                  </div>
                  <div style={{ textAlign: 'right' }}>
                    <Text style={{ color: '#52c41a', fontWeight: 'bold' }}>
                      {(asset.rate ?? 0).toFixed(2)}%
                    </Text>
                  </div>
                </div>
              ))}
            </div>
          </Card>
        </Col>

        <Col xs={24} md={12}>
          <Card title="出租率最低资产" size="small">
            <div style={{ maxHeight: 300, overflowY: 'auto' }}>
              {data?.low_performers?.map((asset, index) => (
                <div key={index} style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  padding: '8px 0',
                  borderBottom: index < (data.low_performers?.length ?? 0) - 1 ? '1px solid #f0f0f0' : 'none'
                }}>
                  <div>
                    <Text strong>{asset.property_name}</Text>
                    <br />
                    <Text type="secondary" style={{ fontSize: '12px' }}>
                      面积: {asset.area?.toLocaleString()} ㎡
                    </Text>
                  </div>
                  <div style={{ textAlign: 'right' }}>
                    <Text style={{ color: '#ff4d4f', fontWeight: 'bold' }}>
                      {(asset.rate ?? 0).toFixed(2)}%
                    </Text>
                  </div>
                </div>
              ))}
            </div>
          </Card>
        </Col>
      </Row>
    </div>
  )
}

export default OccupancyRateChart