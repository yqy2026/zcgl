import React from 'react'
import { Row, Col, Progress, Typography, Space } from 'antd'

const { Text, Title } = Typography

interface ChartData {
  propertyTypes?: Array<{
    name: string
    value: number
    color: string
  }>
  occupancyTrend?: Array<{
    month: string
    rate: number
  }>
}

interface AssetChartProps {
  data?: ChartData
  loading?: boolean
}

const AssetChart: React.FC<AssetChartProps> = ({ data, loading }) => {
  if (loading) {
    return <div>加载中...</div>
  }

  const propertyTypes = data?.propertyTypes || []
  const total = propertyTypes.reduce((sum, item) => sum + item.value, 0)

  return (
    <div>
      {/* 物业类型分布 */}
      <Title level={5} style={{ marginBottom: '16px' }}>
        物业类型分布
      </Title>
      
      <div style={{ marginBottom: '24px' }}>
        {propertyTypes.map((item, index) => {
          const percentage = total > 0 ? (item.value / total) * 100 : 0
          return (
            <div key={index} style={{ marginBottom: '12px' }}>
              <Row justify="space-between" align="middle" style={{ marginBottom: '4px' }}>
                <Col>
                  <Space>
                    <div 
                      style={{ 
                        width: '12px', 
                        height: '12px', 
                        backgroundColor: item.color,
                        borderRadius: '2px'
                      }} 
                    />
                    <Text>{item.name}</Text>
                  </Space>
                </Col>
                <Col>
                  <Text strong>{item.value}个</Text>
                </Col>
              </Row>
              <Progress
                percent={percentage}
                strokeColor={item.color}
                showInfo={false}
                size="small"
              />
            </div>
          )
        })}
      </div>

      {/* 出租率趋势 */}
      <Title level={5} style={{ marginBottom: '16px' }}>
        出租率趋势
      </Title>
      
      <div>
        {data?.occupancyTrend?.map((item, index) => (
          <div key={index} style={{ marginBottom: '8px' }}>
            <Row justify="space-between" align="middle">
              <Col>
                <Text>{item.month}</Text>
              </Col>
              <Col>
                <Text strong>{item.rate}%</Text>
              </Col>
            </Row>
          </div>
        ))}
      </div>
    </div>
  )
}

export default AssetChart