import React from 'react'
import { Card, Row, Col, Statistic, Spin, Alert, Typography, Space, Tag } from 'antd'
import {
  PieChartOutlined,
  HomeOutlined,
  EnvironmentOutlined,
  UserOutlined,
} from '@ant-design/icons'
import { useQuery } from '@tanstack/react-query'
import {
  Chart as ChartJS,
  ArcElement,
  Tooltip,
  Legend,
  CategoryScale,
  LinearScale,
  BarElement,
} from 'chart.js'
import { Pie, Doughnut, Bar } from 'react-chartjs-2'

import { assetService } from '@/services/assetService'
import type { AssetSearchParams } from '@/types/asset'

// 注册Chart.js组件
ChartJS.register(ArcElement, Tooltip, Legend, CategoryScale, LinearScale, BarElement)

const { Title, Text } = Typography

interface AssetDistributionData {
  total_assets: number
  by_property_nature: Array<{
    property_nature: string
    count: number
    percentage: number
    total_area: number
  }>
  by_ownership_status: Array<{
    ownership_status: string
    count: number
    percentage: number
  }>
  by_usage_status: Array<{
    usage_status: string
    count: number
    percentage: number
  }>
  by_ownership_entity: Array<{
    ownership_entity: string
    count: number
    percentage: number
    total_area: number
  }>
  by_region: Array<{
    region: string
    count: number
    percentage: number
  }>
  summary: {
    total_area: number
    commercial_area: number
    non_commercial_area: number
    rented_area: number
    vacant_area: number
  }
}

interface AssetDistributionChartProps {
  filters?: AssetSearchParams
  height?: number
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
  })

  // 物业性质分布图表配置
  const propertyNatureChartData = {
    labels: data?.by_property_nature?.map(item => item.property_nature) || [],
    datasets: [
      {
        data: data?.by_property_nature?.map(item => item.count) || [],
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
        position: 'bottom' as const,
      },
      tooltip: {
        callbacks: {
          label: (context: { dataIndex: number; parsed: number; label: string }) => {
            const item = data?.by_property_nature?.[context.dataIndex]
            return [
              `${context.label}: ${context.parsed} 个`,
              `占比: ${item?.percentage?.toFixed(1)}%`,
              `总面积: ${item?.total_area?.toLocaleString()} ㎡`,
            ]
          },
        },
      },
    },
  }

  // 确权状态分布图表配置
  const ownershipStatusChartData = {
    labels: data?.by_ownership_status?.map(item => item.ownership_status) || [],
    datasets: [
      {
        data: data?.by_ownership_status?.map(item => item.count) || [],
        backgroundColor: [
          '#52c41a',
          '#ff4d4f',
          '#faad14',
          '#1890ff',
        ],
        borderWidth: 2,
        borderColor: '#ffffff',
      },
    ],
  }

  const ownershipStatusChartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'bottom' as const,
      },
      tooltip: {
        callbacks: {
          label: (context: { dataIndex: number; parsed: number; label: string }) => {
            const item = data?.by_ownership_status?.[context.dataIndex]
            return [
              `${context.label}: ${context.parsed} 个`,
              `占比: ${item?.percentage?.toFixed(1)}%`,
            ]
          },
        },
      },
    },
  }

  // 使用状态分布图表配置
  const usageStatusChartData = {
    labels: data?.by_usage_status?.map(item => item.usage_status) || [],
    datasets: [
      {
        data: data?.by_usage_status?.map(item => item.count) || [],
        backgroundColor: [
          '#52c41a',
          '#ff4d4f',
          '#1890ff',
          '#722ed1',
          '#faad14',
        ],
        borderWidth: 2,
        borderColor: '#ffffff',
      },
    ],
  }

  const usageStatusChartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'bottom' as const,
      },
      tooltip: {
        callbacks: {
          label: (context: { dataIndex: number; parsed: number; label: string }) => {
            const item = data?.by_usage_status?.[context.dataIndex]
            return [
              `${context.label}: ${context.parsed} 个`,
              `占比: ${item?.percentage?.toFixed(1)}%`,
            ]
          },
        },
      },
    },
  }

  // 权属方分布柱状图配置
  const ownershipEntityChartData = {
    labels: data?.by_ownership_entity?.slice(0, 10).map(item => 
      item.ownership_entity.length > 8 
        ? item.ownership_entity.substring(0, 8) + '...'
        : item.ownership_entity
    ) || [],
    datasets: [
      {
        label: '资产数量',
        data: data?.by_ownership_entity?.slice(0, 10).map(item => item.count) || [],
        backgroundColor: 'rgba(24, 144, 255, 0.6)',
        borderColor: '#1890ff',
        borderWidth: 1,
      },
    ],
  }

  const ownershipEntityChartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        display: false,
      },
      tooltip: {
        callbacks: {
          label: (context: { dataIndex: number; parsed: { y: number } }) => {
            const item = data?.by_ownership_entity?.[context.dataIndex]
            return [
              `资产数量: ${context.parsed.y} 个`,
              `占比: ${item?.percentage?.toFixed(1)}%`,
              `总面积: ${item?.total_area?.toLocaleString()} ㎡`,
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
        description="无法加载资产分布统计数据，请稍后重试"
        type="error"
        showIcon
      />
    )
  }

  return (
    <div>
      {/* 总体统计 */}
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col xs={12} sm={6}>
          <Card>
            <Statistic
              title="资产总数"
              value={data?.total_assets || 0}
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
              value={data?.summary?.total_area || 0}
              suffix="㎡"
              formatter={(value) => `${Number(value).toLocaleString()}`}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        
        <Col xs={12} sm={6}>
          <Card>
            <Statistic
              title="权属方数量"
              value={data?.by_ownership_entity?.length || 0}
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
              value={data?.summary?.commercial_area || 0}
              suffix="㎡"
              formatter={(value) => `${Number(value).toLocaleString()}`}
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
              <div style={{ height: height }}>
                <Pie data={propertyNatureChartData} options={propertyNatureChartOptions} />
              </div>
            </Spin>
          </Card>
        </Col>

        {/* 确权状态分布 */}
        <Col xs={24} md={12} lg={8}>
          <Card title="确权状态分布" style={{ marginBottom: 16 }}>
            <Spin spinning={isLoading}>
              <div style={{ height: height }}>
                <Doughnut data={ownershipStatusChartData} options={ownershipStatusChartOptions} />
              </div>
            </Spin>
          </Card>
        </Col>

        {/* 使用状态分布 */}
        <Col xs={24} md={12} lg={8}>
          <Card title="使用状态分布" style={{ marginBottom: 16 }}>
            <Spin spinning={isLoading}>
              <div style={{ height: height }}>
                <Pie data={usageStatusChartData} options={usageStatusChartOptions} />
              </div>
            </Spin>
          </Card>
        </Col>

        {/* 权属方分布 */}
        <Col xs={24}>
          <Card title="主要权属方资产分布（前10名）">
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
        <Col xs={24} md={12}>
          <Card title="物业性质详情" size="small">
            <div style={{ maxHeight: 300, overflowY: 'auto' }}>
              {data?.by_property_nature?.map((item, index) => (
                <div key={index} style={{ 
                  display: 'flex', 
                  justifyContent: 'space-between', 
                  alignItems: 'center',
                  padding: '8px 0',
                  borderBottom: index < (data.by_property_nature?.length || 0) - 1 ? '1px solid #f0f0f0' : 'none'
                }}>
                  <div>
                    <Space>
                      <Tag color={index === 0 ? 'blue' : 'green'}>
                        {item.property_nature}
                      </Tag>
                      <Text>{item.count} 个</Text>
                    </Space>
                    <br />
                    <Text type="secondary" style={{ fontSize: '12px' }}>
                      面积: {item.total_area?.toLocaleString()} ㎡
                    </Text>
                  </div>
                  <div style={{ textAlign: 'right' }}>
                    <Text style={{ fontWeight: 'bold' }}>
                      {item.percentage?.toFixed(1)}%
                    </Text>
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
                <div key={index} style={{ 
                  display: 'flex', 
                  justifyContent: 'space-between', 
                  alignItems: 'center',
                  padding: '8px 0',
                  borderBottom: index < (data.by_usage_status?.length || 0) - 1 ? '1px solid #f0f0f0' : 'none'
                }}>
                  <div>
                    <Space>
                      <Tag color={
                        item.usage_status === '出租' ? 'green' :
                        item.usage_status === '闲置' ? 'red' :
                        item.usage_status === '自用' ? 'blue' : 'default'
                      }>
                        {item.usage_status}
                      </Tag>
                      <Text>{item.count} 个</Text>
                    </Space>
                  </div>
                  <div style={{ textAlign: 'right' }}>
                    <Text style={{ fontWeight: 'bold' }}>
                      {item.percentage?.toFixed(1)}%
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

export default AssetDistributionChart