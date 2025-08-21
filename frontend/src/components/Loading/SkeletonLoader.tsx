import React from 'react'
import { Skeleton, Card, Row, Col } from 'antd'

interface SkeletonLoaderProps {
  type?: 'list' | 'card' | 'form' | 'table' | 'chart' | 'detail'
  rows?: number
  loading?: boolean
  children?: React.ReactNode
}

const SkeletonLoader: React.FC<SkeletonLoaderProps> = ({
  type = 'list',
  rows = 3,
  loading = true,
  children,
}) => {
  if (!loading && children) {
    return <>{children}</>
  }

  const renderSkeleton = () => {
    switch (type) {
      case 'list':
        return (
          <div>
            {Array.from({ length: rows }).map((_, index) => (
              <Card key={index} style={{ marginBottom: 16 }}>
                <Skeleton
                  avatar
                  paragraph={{ rows: 2 }}
                  active
                />
              </Card>
            ))}
          </div>
        )

      case 'card':
        return (
          <Row gutter={16}>
            {Array.from({ length: rows }).map((_, index) => (
              <Col xs={24} sm={12} md={8} lg={6} key={index}>
                <Card style={{ marginBottom: 16 }}>
                  <Skeleton
                    paragraph={{ rows: 3 }}
                    active
                  />
                </Card>
              </Col>
            ))}
          </Row>
        )

      case 'form':
        return (
          <Card>
            <div style={{ marginBottom: 24 }}>
              <Skeleton.Input style={{ width: 200, height: 32 }} active />
            </div>
            {Array.from({ length: rows }).map((_, index) => (
              <Row key={index} gutter={16} style={{ marginBottom: 24 }}>
                <Col span={6}>
                  <Skeleton.Input style={{ width: '100%', height: 32 }} active />
                </Col>
                <Col span={6}>
                  <Skeleton.Input style={{ width: '100%', height: 32 }} active />
                </Col>
                <Col span={6}>
                  <Skeleton.Input style={{ width: '100%', height: 32 }} active />
                </Col>
                <Col span={6}>
                  <Skeleton.Input style={{ width: '100%', height: 32 }} active />
                </Col>
              </Row>
            ))}
            <div style={{ marginTop: 24 }}>
              <Skeleton.Button style={{ width: 100, height: 32 }} active />
              <Skeleton.Button style={{ width: 80, height: 32, marginLeft: 16 }} active />
            </div>
          </Card>
        )

      case 'table':
        return (
          <Card>
            <div style={{ marginBottom: 16 }}>
              <Row gutter={16}>
                <Col span={6}>
                  <Skeleton.Input style={{ width: '100%', height: 32 }} active />
                </Col>
                <Col span={6}>
                  <Skeleton.Input style={{ width: '100%', height: 32 }} active />
                </Col>
                <Col span={6}>
                  <Skeleton.Input style={{ width: '100%', height: 32 }} active />
                </Col>
                <Col span={6}>
                  <Skeleton.Button style={{ width: 80, height: 32 }} active />
                </Col>
              </Row>
            </div>
            
            {/* 表头 */}
            <Row gutter={16} style={{ marginBottom: 16, padding: '12px 0', background: '#fafafa' }}>
              {Array.from({ length: 6 }).map((_, index) => (
                <Col span={4} key={index}>
                  <Skeleton.Input style={{ width: '80%', height: 20 }} active />
                </Col>
              ))}
            </Row>
            
            {/* 表格行 */}
            {Array.from({ length: rows }).map((_, rowIndex) => (
              <Row key={rowIndex} gutter={16} style={{ marginBottom: 12, padding: '8px 0' }}>
                {Array.from({ length: 6 }).map((_, colIndex) => (
                  <Col span={4} key={colIndex}>
                    <Skeleton.Input 
                      style={{ 
                        width: colIndex === 0 ? '60%' : '80%', 
                        height: 16 
                      }} 
                      active 
                    />
                  </Col>
                ))}
              </Row>
            ))}
            
            {/* 分页 */}
            <div style={{ marginTop: 24, textAlign: 'right' }}>
              <Skeleton.Button style={{ width: 200, height: 32 }} active />
            </div>
          </Card>
        )

      case 'chart':
        return (
          <Card>
            <div style={{ marginBottom: 16 }}>
              <Skeleton.Input style={{ width: 200, height: 24 }} active />
            </div>
            
            {/* 统计卡片 */}
            <Row gutter={16} style={{ marginBottom: 24 }}>
              {Array.from({ length: 4 }).map((_, index) => (
                <Col span={6} key={index}>
                  <Card size="small">
                    <Skeleton
                      paragraph={{ rows: 1 }}
                      title={{ width: '60%' }}
                      active
                    />
                  </Card>
                </Col>
              ))}
            </Row>
            
            {/* 图表区域 */}
            <div style={{ 
              height: 300, 
              background: '#fafafa', 
              borderRadius: 6,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center'
            }}>
              <Skeleton.Node style={{ width: 200, height: 200 }} active>
                <div style={{ 
                  width: 200, 
                  height: 200, 
                  background: '#f0f0f0',
                  borderRadius: '50%'
                }} />
              </Skeleton.Node>
            </div>
          </Card>
        )

      case 'detail':
        return (
          <div>
            {/* 头部信息 */}
            <Card style={{ marginBottom: 16 }}>
              <div style={{ display: 'flex', alignItems: 'center', marginBottom: 16 }}>
                <Skeleton.Avatar size={64} active />
                <div style={{ marginLeft: 16, flex: 1 }}>
                  <Skeleton.Input style={{ width: 300, height: 24, marginBottom: 8 }} active />
                  <Skeleton.Input style={{ width: 200, height: 16 }} active />
                </div>
                <div>
                  <Skeleton.Button style={{ width: 80, height: 32, marginRight: 8 }} active />
                  <Skeleton.Button style={{ width: 80, height: 32 }} active />
                </div>
              </div>
            </Card>
            
            {/* 详细信息 */}
            <Row gutter={16}>
              <Col span={16}>
                <Card title={<Skeleton.Input style={{ width: 120, height: 20 }} active />}>
                  {Array.from({ length: rows }).map((_, index) => (
                    <Row key={index} gutter={16} style={{ marginBottom: 16 }}>
                      <Col span={8}>
                        <Skeleton.Input style={{ width: '100%', height: 16 }} active />
                      </Col>
                      <Col span={16}>
                        <Skeleton.Input style={{ width: '80%', height: 16 }} active />
                      </Col>
                    </Row>
                  ))}
                </Card>
              </Col>
              
              <Col span={8}>
                <Card title={<Skeleton.Input style={{ width: 100, height: 20 }} active />}>
                  {Array.from({ length: 3 }).map((_, index) => (
                    <div key={index} style={{ marginBottom: 16 }}>
                      <Skeleton
                        paragraph={{ rows: 1 }}
                        title={{ width: '70%' }}
                        active
                      />
                    </div>
                  ))}
                </Card>
              </Col>
            </Row>
          </div>
        )

      default:
        return (
          <Skeleton
            paragraph={{ rows }}
            active
          />
        )
    }
  }

  return <div>{renderSkeleton()}</div>
}

export default SkeletonLoader