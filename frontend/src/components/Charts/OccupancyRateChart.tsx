import React, { useEffect, useRef } from 'react'
import { Card, Typography, Space, Statistic, Row, Col, Spin, Alert } from 'antd'
import {
  PercentageOutlined,
  RiseOutlined,
  FallOutlined,
  MinusOutlined,
} from '@ant-design/icons'
import { useQuery } from '@tanstack/react-query'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend,
  ArcElement,
} from 'chart.js'
import { Line, Bar, Doughnut } from 'react-chartjs-2'

import { assetService } from '@/services/assetService'
import type { AssetSearchParams } from '@/types/asset'

// 注册Chart.js组件
ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend,
  ArcElement
)

const { Title: AntTitle, Text } = Typography

interface OccupancyRateData {
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
  const trendChartData = {
    labels: data?.monthly_trend?.map(item => item.month) || [],
    datasets: [
      {
        label: '出租率 (%)',
        data: data?.monthly_trend?.map(item => item.rate) || [],
        borderColor: '#1890ff',
        backgroundColor: 'rgba(24, 144, 255, 0.1)',
        borderWidth: 2,
        fill: true,
        tension: 0.4,
      },
    ],
  }

  const trendChartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'top' as const,
      },
      title: {
        display: true,
        text: '出租率月度趋势',
        font: {
          size: 16,
          weight: 'bold' as const,
        },
      },
      tooltip: {
        callbacks: {
          label: (context: { dataIndex: number; parsed: { y: number }; label: string }) => {
            const monthData = data?.monthly_trend?.[context.dataIndex]
            return [
              `出租率: ${context.parsed.y.toFixed(2)}%`,
              `总面积: ${monthData?.total_area?.toLocaleString() || 0} ㎡`,
              `已租面积: ${monthData?.rented_area?.toLocaleString() || 0} ㎡`,
            ]
          },
        },
      },
    },
    scales: {
      y: {
        beginAtZero: true,
        max: 100,
        ticks: {
          callback: (value: number) => `${value}%`,
        },
      },
    },
  }

  // 物业性质分布图表配置
  const propertyNatureChartData = {
    labels: data?.by_property_nature?.map(item => item.property_nature) || [],
    datasets: [
      {
        data: data?.by_property_nature?.map(item => item.rate) || [],
        backgroundColor: [
          '#1890ff',
          '#52c41a',
          '#faad14',
          '#f5222d',
          '#722ed1',
          '#fa8c16',
        ],
        borderWidth: 2,
        borderColor: '#ffffff',
      },
    ],
  }

  const propertyNatureChartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'right' as const,
      },
      title: {
        display: true,
        text: '按物业性质分布',
        font: {
          size: 16,
          weight: 'bold' as const,
        },
      },
      tooltip: {
        callbacks: {
          label: (context: { dataIndex: number; parsed: number; label: string }) => {
            const item = data?.by_property_nature?.[context.dataIndex]
            return [
              `${context.label}: ${context.parsed.toFixed(2)}%`,
              `总面积: ${item?.total_area?.toLocaleString() || 0} ㎡`,
              `已租面积: ${item?.rented_area?.toLocaleString() || 0} ㎡`,
            ]
          },
        },
      },
    },
  }

  // 权属方出租率柱状图配置
  const ownershipChartData = {
    labels: data?.by_ownership_entity?.map(item => 
      item.ownership_entity.length > 10 
        ? item.ownership_entity.substring(0, 10) + '...'
        : item.ownership_entity
    ) || [],
    datasets: [
      {
        label: '出租率 (%)',
        data: data?.by_ownership_entity?.map(item => item.rate) || [],
        backgroundColor: 'rgba(24, 144, 255, 0.6)',
        borderColor: '#1890ff',
        borderWidth: 1,
      },
    ],
  }

  const ownershipChartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        display: false,
      },
      title: {
        display: true,
        text: '各权属方出租率对比',
        font: {
          size: 16,
          weight: 'bold' as const,
        },
      },
      tooltip: {
        callbacks: {
          label: (context: { dataIndex: number; parsed: { y: number } }) => {
            const item = data?.by_ownership_entity?.[context.dataIndex]
            return [
              `出租率: ${context.parsed.y.toFixed(2)}%`,
              `资产数量: ${item?.asset_count || 0} 个`,
            ]
          },
        },
      },
    },
    scales: {
      y: {
        beginAtZero: true,
        max: 100,
        ticks: {
          callback: (value: number) => `${value}%`,
        },
      },
      x: {
        ticks: {
          maxRotation: 45,
          minRotation: 0,
        },
      },
    },
  }

  // 获取趋势图标
  const getTrendIcon = (trend: string, percentage: number) => {
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

  if (error) {
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
              value={data?.overall_rate || 0}
              precision={2}
              suffix="%"
              prefix={<PercentageOutlined />}
              valueStyle={{ 
                color: data?.overall_rate && data.overall_rate >= 80 ? '#52c41a' : 
                       data?.overall_rate && data.overall_rate >= 60 ? '#faad14' : '#ff4d4f'
              }}
            />
          </Card>
        </Col>
        
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="趋势变化"
              value={data?.trend_percentage || 0}
              precision={2}
              suffix="%"
              prefix={getTrendIcon(data?.trend || 'stable', data?.trend_percentage || 0)}
              valueStyle={{ color: getTrendColor(data?.trend || 'stable') }}
            />
          </Card>
        </Col>
        
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="经营类物业出租率"
              value={data?.by_property_nature?.find(item => item.property_nature === '经营类')?.rate || 0}
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
              value={data?.by_ownership_entity?.length || 0}
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
              <div style={{ height: height }}>
                <Line data={trendChartData} options={trendChartOptions as any} />
              </div>
            </Spin>
          </Card>
        </Col>

        {/* 物业性质分布 */}
        <Col xs={24} lg={12}>
          <Card title="物业性质出租率分布" style={{ marginBottom: 16 }}>
            <Spin spinning={isLoading}>
              <div style={{ height: height }}>
                <Doughnut data={propertyNatureChartData} options={propertyNatureChartOptions} />
              </div>
            </Spin>
          </Card>
        </Col>

        {/* 权属方对比 */}
        <Col xs={24}>
          <Card title="权属方出租率对比">
            <Spin spinning={isLoading}>
              <div style={{ height: height }}>
                <Bar data={ownershipChartData} options={ownershipChartOptions as any} />
              </div>
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
                  borderBottom: index < (data.top_performers?.length || 0) - 1 ? '1px solid #f0f0f0' : 'none'
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
                  borderBottom: index < (data.low_performers?.length || 0) - 1 ? '1px solid #f0f0f0' : 'none'
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