import React from 'react'
import { Card, Row, Col, Typography, Statistic, Spin, Alert } from 'antd'
import { useQuery } from '@tanstack/react-query'
import { apiClient } from '../../services/api'

const { Title } = Typography

interface AreaSummary {
  total_assets: number
  total_land_area: number
  total_rentable_area: number
  total_rented_area: number
  total_unrented_area: number
  total_non_commercial_area: number
  assets_with_area_data: number
  overall_occupancy_rate: number
}

const DashboardPage: React.FC = () => {
  const { data: areaSummary, isLoading, error, refetch } = useQuery({
    queryKey: ['statistics', 'area-summary'],
    queryFn: async () => {
      try {
        console.log('🔄 Starting API request for area summary...')
        const response = await apiClient.get('/statistics/area-summary')
        console.log('✅ API Response received:', response)
        return response
      } catch (err) {
        console.error('❌ API Error:', err)
        throw err
      }
    },
    retry: 2,
    retryDelay: 1000,
    staleTime: 0, // 总是重新获取数据
    cacheTime: 0, // 不缓存数据
  })

  if (isLoading) {
    return (
      <div style={{ padding: '24px', textAlign: 'center' }}>
        <Spin size="large" tip="加载数据中..." />
      </div>
    )
  }

  if (error) {
    console.error('Dashboard Error:', error)
    return (
      <div style={{ padding: '24px' }}>
        <Alert
          message="数据加载失败"
          description={`错误详情: ${error instanceof Error ? error.message : '未知错误'}`}
          type="error"
          showIcon
          action={
            <button onClick={() => window.location.reload()}>
              重试
            </button>
          }
        />
      </div>
    )
  }

  const occupancyRate = areaSummary?.data?.overall_occupancy_rate?.toFixed(2) || '0.00'

  // 添加调试日志
  console.log('Dashboard Data:', {
    areaSummary,
    totalAssets: areaSummary?.data?.total_assets,
    occupancyRate
  })

  return (
    <div style={{ padding: '24px' }}>
      <Title level={2}>工作台</Title>
      
      <Row gutter={[16, 16]} style={{ marginBottom: '24px' }}>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="资产总数"
              value={areaSummary?.data?.total_assets || 0}
              suffix="个"
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="土地面积"
              value={areaSummary?.data?.total_land_area || 0}
              precision={2}
              suffix="㎡"
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="可租面积"
              value={areaSummary?.data?.total_rentable_area || 0}
              precision={2}
              suffix="㎡"
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="出租率"
              value={occupancyRate}
              precision={2}
              suffix="%"
            />
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]}>
        <Col xs={24} lg={12}>
          <Card title="面积统计">
            <Row gutter={16}>
              <Col span={12}>
                <Statistic
                  title="已租面积"
                  value={areaSummary?.data?.total_rented_area || 0}
                  precision={2}
                  suffix="㎡"
                />
              </Col>
              <Col span={12}>
                <Statistic
                  title="空置面积"
                  value={areaSummary?.data?.total_unrented_area || 0}
                  precision={2}
                  suffix="㎡"
                />
              </Col>
            </Row>
          </Card>
        </Col>
        <Col xs={24} lg={12}>
          <Card title="面积详情">
            <Row gutter={16}>
              <Col span={12}>
                <Statistic
                  title="非商业面积"
                  value={areaSummary?.data?.total_non_commercial_area || 0}
                  precision={2}
                  suffix="㎡"
                />
              </Col>
              <Col span={12}>
                <Statistic
                  title="有数据资产数"
                  value={areaSummary?.data?.assets_with_area_data || 0}
                  suffix="个"
                />
              </Col>
            </Row>
          </Card>
        </Col>
      </Row>
    </div>
  )
}

export default DashboardPage