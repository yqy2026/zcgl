import React from 'react'
import { Card, Row, Col, Statistic, Spin, Alert, Typography, Space, Progress, Tag } from 'antd'
import {
  AreaChartOutlined,
  BuildOutlined,
  HomeOutlined,
  ShopOutlined,
} from '@ant-design/icons'
import { useQuery } from '@tanstack/react-query'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend,
} from 'chart.js'
import { Bar } from 'react-chartjs-2'

import { assetService } from '@/services/assetService'
import type { AssetSearchParams } from '@/types/asset'
import { getChartYValue, getChartDatasetLabel } from '@/types/chart-types'

// Local interface matching the actual API response structure
interface AreaStatisticsData {
  total_statistics: {
    total_land_area: number
    total_property_area: number
    total_rentable_area: number
    total_rented_area: number
    total_vacant_area: number
    total_non_commercial_area: number
  }
  by_property_nature: Array<{
    property_nature: string
    land_area: number
    property_area: number
    rentable_area: number
    rented_area: number
    vacant_area: number
    non_commercial_area: number
  }>
  by_ownership_entity: Array<{
    ownership_entity: string
    total_area: number
    rentable_area: number
    rented_area: number
    occupancy_rate: number
  }>
  by_usage_status: Array<{
    usage_status: string
    total_area: number
    asset_count: number
    average_area: number
  }>
  area_ranges: Array<{
    range: string
    count: number
    total_area: number
    percentage: number
  }>
  top_assets_by_area: Array<{
    property_name: string
    property_area: number
    rentable_area: number
    rented_area: number
    occupancy_rate: number
  }>
}

// 注册Chart.js组件
ChartJS.register(CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend)

const { Title: AntTitle, Text } = Typography

interface AreaStatisticsChartProps {
  filters?: AssetSearchParams
  height?: number
}

const AreaStatisticsChart: React.FC<AreaStatisticsChartProps> = ({
  filters,
  height = 400,
}) => {
  // 获取面积统计数据
  const { data, isLoading, error } = useQuery<AreaStatisticsData>({
    queryKey: ['area-statistics', filters],
    queryFn: async (): Promise<AreaStatisticsData> => {
      const result = await assetService.getAreaStatistics(filters);
      return result as unknown as AreaStatisticsData;
    },
    refetchInterval: 5 * 60 * 1000, // 5分钟刷新一次
  })

  // 物业性质面积对比图表配置
  const propertyNatureChartData = {
    labels: data?.by_property_nature?.map(item => item.property_nature) || [],
    datasets: [
      {
        label: '土地面积 (㎡)',
        data: data?.by_property_nature?.map(item => item.land_area) || [],
        backgroundColor: 'rgba(24, 144, 255, 0.6)',
        borderColor: '#1890ff',
        borderWidth: 1,
      },
      {
        label: '房产面积 (㎡)',
        data: data?.by_property_nature?.map(item => item.property_area) || [],
        backgroundColor: 'rgba(82, 196, 26, 0.6)',
        borderColor: '#52c41a',
        borderWidth: 1,
      },
      {
        label: '可租面积 (㎡)',
        data: data?.by_property_nature?.map(item => item.rentable_area) || [],
        backgroundColor: 'rgba(250, 173, 20, 0.6)',
        borderColor: '#faad14',
        borderWidth: 1,
      },
      {
        label: '已租面积 (㎡)',
        data: data?.by_property_nature?.map(item => item.rented_area) || [],
        backgroundColor: 'rgba(114, 46, 209, 0.6)',
        borderColor: '#722ed1',
        borderWidth: 1,
      },
    ],
  }

  const propertyNatureChartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'top' as const,
      },
      title: {
        display: true,
        text: '按物业性质面积分布',
        font: {
          size: 16,
          weight: 'bold' as const,
        },
      },
      tooltip: {
        callbacks: {
          label: (context: unknown) => {
            const label = getChartDatasetLabel(context);
            const value = getChartYValue(context);
            return `${label}: ${value.toLocaleString()} ㎡`;
          },
        },
      },
    },
    scales: {
      y: {
        beginAtZero: true,
        ticks: {
          callback: (value: number) => `${Number(value).toLocaleString()} ㎡`,
        },
      },
    },
  }

  // 权属方面积对比图表配置
  const ownershipEntityChartData = {
    labels: data?.by_ownership_entity?.slice(0, 10).map(item => 
      item.ownership_entity.length > 8 
        ? item.ownership_entity.substring(0, 8) + '...'
        : item.ownership_entity
    ) || [],
    datasets: [
      {
        label: '总面积 (㎡)',
        data: data?.by_ownership_entity?.slice(0, 10).map(item => item.total_area) || [],
        backgroundColor: 'rgba(24, 144, 255, 0.6)',
        borderColor: '#1890ff',
        borderWidth: 1,
        yAxisID: 'y',
      },
      {
        label: '出租率 (%)',
        data: data?.by_ownership_entity?.slice(0, 10).map(item => item.occupancy_rate) || [],
        backgroundColor: 'rgba(245, 34, 45, 0.6)',
        borderColor: '#f5222d',
        borderWidth: 1,
        yAxisID: 'y1',
        type: 'line' as const,
      },
    ],
  }

  const ownershipEntityChartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'top' as const,
      },
      title: {
        display: true,
        text: '主要权属方面积与出租率对比',
        font: {
          size: 16,
          weight: 'bold' as const,
        },
      },
      tooltip: {
        callbacks: {
          label: (context: unknown) => {
            const label = getChartDatasetLabel(context);
            const value = getChartYValue(context);
            if (label?.includes('出租率')) {
              return `${label}: ${value.toFixed(2)}%`;
            }
            return `${label}: ${value.toLocaleString()} ㎡`;
          },
        },
      },
    },
    scales: {
      x: {
        ticks: {
          maxRotation: 45,
          minRotation: 0,
        },
      },
      y: {
        type: 'linear' as const,
        display: true,
        position: 'left' as const,
        beginAtZero: true,
        ticks: {
          callback: (value: number) => `${Number(value).toLocaleString()} ㎡`,
        },
      },
      y1: {
        type: 'linear' as const,
        display: true,
        position: 'right' as const,
        beginAtZero: true,
        max: 100,
        ticks: {
          callback: (value: number) => `${value}%`,
        },
        grid: {
          drawOnChartArea: false,
        },
      },
    },
  }

  // 面积区间分布图表配置
  const areaRangeChartData = {
    labels: data?.area_ranges?.map(item => item.range) || [],
    datasets: [
      {
        label: '资产数量',
        data: data?.area_ranges?.map(item => item.count) || [],
        backgroundColor: 'rgba(82, 196, 26, 0.6)',
        borderColor: '#52c41a',
        borderWidth: 1,
      },
    ],
  }

  const areaRangeChartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        display: false,
      },
      title: {
        display: true,
        text: '资产面积区间分布',
        font: {
          size: 16,
          weight: 'bold' as const,
        },
      },
      tooltip: {
        callbacks: {
          label: (context: unknown) => {
            const ctx = context as { dataIndex?: number; parsed?: number | { y: number } };
            const dataIndex = ctx.dataIndex ?? 0;
            const item = data?.area_ranges?.[dataIndex];
            const yValue = typeof ctx.parsed === 'number' ? ctx.parsed : (ctx.parsed as { y: number })?.y ?? 0;
            return [
              `资产数量: ${yValue} 个`,
              `总面积: ${item?.total_area?.toLocaleString()} ㎡`,
              `占比: ${item?.percentage?.toFixed(1)}%`,
            ]
          },
        },
      },
    },
    scales: {
      y: {
        beginAtZero: true,
        ticks: {
          stepSize: 1,
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

  if (error) {
    return (
      <Alert
        message="数据加载失败"
        description="无法加载面积统计数据，请稍后重试"
        type="error"
        showIcon
      />
    )
  }

  return (
    <div>
      {/* 总体统计 */}
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col xs={12} sm={6} md={4}>
          <Card>
            <Statistic
              title="总土地面积"
              value={data?.total_statistics?.total_land_area || 0}
              suffix="㎡"
              formatter={(value) => `${Number(value).toLocaleString()}`}
              prefix={<BuildOutlined />}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        
        <Col xs={12} sm={6} md={4}>
          <Card>
            <Statistic
              title="总房产面积"
              value={data?.total_statistics?.total_property_area || 0}
              suffix="㎡"
              formatter={(value) => `${Number(value).toLocaleString()}`}
              prefix={<HomeOutlined />}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        
        <Col xs={12} sm={6} md={4}>
          <Card>
            <Statistic
              title="可租面积"
              value={data?.total_statistics?.total_rentable_area || 0}
              suffix="㎡"
              formatter={(value) => `${Number(value).toLocaleString()}`}
              prefix={<ShopOutlined />}
              valueStyle={{ color: '#faad14' }}
            />
          </Card>
        </Col>
        
        <Col xs={12} sm={6} md={4}>
          <Card>
            <Statistic
              title="已租面积"
              value={data?.total_statistics?.total_rented_area || 0}
              suffix="㎡"
              formatter={(value) => `${Number(value).toLocaleString()}`}
              valueStyle={{ color: '#722ed1' }}
            />
          </Card>
        </Col>
        
        <Col xs={12} sm={6} md={4}>
          <Card>
            <Statistic
              title="空置面积"
              value={data?.total_statistics?.total_vacant_area || 0}
              suffix="㎡"
              formatter={(value) => `${Number(value).toLocaleString()}`}
              valueStyle={{ color: '#ff4d4f' }}
            />
          </Card>
        </Col>
        
        <Col xs={12} sm={6} md={4}>
          <Card>
            <Statistic
              title="非经营面积"
              value={data?.total_statistics?.total_non_commercial_area || 0}
              suffix="㎡"
              formatter={(value) => `${Number(value).toLocaleString()}`}
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
              <div style={{ height: height }}>
                <Bar data={propertyNatureChartData} options={propertyNatureChartOptions} />
              </div>
            </Spin>
          </Card>
        </Col>

        {/* 面积区间分布 */}
        <Col xs={24} lg={12}>
          <Card title="面积区间分布" style={{ marginBottom: 16 }}>
            <Spin spinning={isLoading}>
              <div style={{ height: height }}>
                <Bar data={areaRangeChartData} options={areaRangeChartOptions} />
              </div>
            </Spin>
          </Card>
        </Col>

        {/* 权属方面积与出租率对比 */}
        <Col xs={24}>
          <Card title="权属方面积与出租率对比">
            <Spin spinning={isLoading}>
              <div style={{ height: height }}>
                <Bar data={ownershipEntityChartData} options={ownershipEntityChartOptions} />
              </div>
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
                <div key={index} style={{ 
                  padding: '12px 0',
                  borderBottom: index < (data.by_usage_status?.length || 0) - 1 ? '1px solid #f0f0f0' : 'none'
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                    <Space>
                      <Tag color={
                        item.usage_status === '出租' ? 'green' :
                        item.usage_status === '闲置' ? 'red' :
                        item.usage_status === '自用' ? 'blue' : 'default'
                      }>
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
                <div key={index} style={{ 
                  padding: '12px 0',
                  borderBottom: index < (data.top_assets_by_area?.length || 0) - 1 ? '1px solid #f0f0f0' : 'none'
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 8 }}>
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
                      percent={asset.occupancy_rate || 0}
                      size="small"
                      strokeColor={
                        (asset.occupancy_rate || 0) >= 80 ? '#52c41a' :
                        (asset.occupancy_rate || 0) >= 60 ? '#faad14' : '#ff4d4f'
                      }
                      format={(percent) => `${percent?.toFixed(1)}%`}
                    />
                  )}
                </div>
              ))}
            </div>
          </Card>
        </Col>
      </Row>
    </div>
  )
}

export default AreaStatisticsChart