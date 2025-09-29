import React from 'react'
import { Card, Row, Col, Typography, Statistic, Spin, Alert } from 'antd'
import { useQuery } from '@tanstack/react-query'
import { apiClient } from '../../services/api'

const { Title } = Typography

interface AreaSummary {
  total_assets: number
  total_area: number
  total_usable_area: number
  total_rentable_area: number
  total_rented_area: number
  total_unrented_area: number
}

const DashboardPage: React.FC = () => {
  const { data: areaSummary, isLoading, error } = useQuery({
    queryKey: ['statistics', 'area-summary'],
    queryFn: async () => {
      try {
        const response = await apiClient.get('/statistics/area-summary')
        console.log('API Response:', response)
        return response.data
      } catch (err) {
        console.error('API Error:', err)
        throw err
      }
    },
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
        />
      </div>
    )
  }

  const occupancyRate = areaSummary?.total_rentable_area 
    ? (areaSummary.total_rented_area / areaSummary.total_rentable_area * 100).toFixed(2)
    : '0.00'

  return (
    <div style={{ padding: '24px' }}>
      <Title level={2}>工作台</Title>
      
      <Row gutter={[16, 16]} style={{ marginBottom: '24px' }}>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="资产总数"
              value={areaSummary?.total_assets || 0}
              suffix="个"
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="总面积"
              value={areaSummary?.total_area || 0}
              precision={2}
              suffix="㎡"
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="可租面积"
              value={areaSummary?.total_rentable_area || 0}
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
                  value={areaSummary?.total_rented_area || 0}
                  precision={2}
                  suffix="㎡"
                />
              </Col>
              <Col span={12}>
                <Statistic
                  title="空置面积"
                  value={areaSummary?.total_unrented_area || 0}
                  precision={2}
                  suffix="㎡"
                />
              </Col>
            </Row>
          </Card>
        </Col>
        <Col xs={24} lg={12}>
          <Card title="使用情况">
            <Row gutter={16}>
              <Col span={12}>
                <Statistic
                  title="可用面积"
                  value={areaSummary?.total_usable_area || 0}
                  precision={2}
                  suffix="㎡"
                />
              </Col>
              <Col span={12}>
                <Statistic
                  title="可租面积"
                  value={areaSummary?.total_rentable_area || 0}
                  precision={2}
                  suffix="㎡"
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