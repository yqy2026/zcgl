import React from 'react'
import { useNavigate } from 'react-router-dom'
import { 
  Card, 
  Typography, 
  Button, 
  Space, 
  Row, 
  Col, 
  Statistic,
  Progress,
  Table,
  Tag
} from 'antd'
import {
  ArrowLeftOutlined,
  PieChartOutlined,
  BarChartOutlined,
  LineChartOutlined,
  TrendingUpOutlined,
} from '@ant-design/icons'

const { Title, Text } = Typography

const AssetAnalyticsPage: React.FC = () => {
  const navigate = useNavigate()

  const handleBack = () => {
    navigate('/assets/list')
  }

  // 模拟数据
  const summaryData = {
    totalAssets: 156,
    totalArea: 125000,
    rentedArea: 98000,
    occupancyRate: 78.4,
    monthlyRevenue: 2850000,
  }

  const propertyTypeData = [
    { type: '写字楼', count: 45, area: 65000, occupancyRate: 85.2 },
    { type: '商业', count: 32, area: 28000, occupancyRate: 92.1 },
    { type: '工业', count: 28, area: 25000, occupancyRate: 68.5 },
    { type: '住宅', count: 35, area: 15000, occupancyRate: 45.8 },
    { type: '其他', count: 16, area: 12000, occupancyRate: 72.3 },
  ]

  const columns = [
    {
      title: '物业类型',
      dataIndex: 'type',
      key: 'type',
    },
    {
      title: '数量',
      dataIndex: 'count',
      key: 'count',
      render: (count: number) => `${count} 个`,
    },
    {
      title: '总面积',
      dataIndex: 'area',
      key: 'area',
      render: (area: number) => `${area.toLocaleString()} ㎡`,
    },
    {
      title: '出租率',
      dataIndex: 'occupancyRate',
      key: 'occupancyRate',
      render: (rate: number) => (
        <Space>
          <Progress 
            percent={rate} 
            size="small" 
            style={{ width: '100px' }}
            strokeColor={rate > 80 ? '#52c41a' : rate > 60 ? '#faad14' : '#ff4d4f'}
          />
          <Text>{rate}%</Text>
        </Space>
      ),
    },
  ]

  return (
    <div style={{ padding: '24px' }}>
      {/* 页面头部 */}
      <div style={{ marginBottom: '24px' }}>
        <Space>
          <Button 
            icon={<ArrowLeftOutlined />} 
            onClick={handleBack}
          >
            返回列表
          </Button>
          <Title level={2} style={{ margin: 0 }}>
            资产分析
          </Title>
        </Space>
      </div>

      {/* 关键指标概览 */}
      <Row gutter={16} style={{ marginBottom: '24px' }}>
        <Col span={6}>
          <Card>
            <Statistic
              title="资产总数"
              value={summaryData.totalAssets}
              suffix="个"
              prefix={<PieChartOutlined />}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="总面积"
              value={summaryData.totalArea}
              suffix="㎡"
              prefix={<BarChartOutlined />}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="平均出租率"
              value={summaryData.occupancyRate}
              suffix="%"
              prefix={<LineChartOutlined />}
              precision={1}
              valueStyle={{ color: '#faad14' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="月度收入"
              value={summaryData.monthlyRevenue}
              prefix="¥"
              prefix={<TrendingUpOutlined />}
              valueStyle={{ color: '#722ed1' }}
            />
          </Card>
        </Col>
      </Row>

      {/* 物业类型分析 */}
      <Card title="物业类型分析" style={{ marginBottom: '24px' }}>
        <Table
          columns={columns}
          dataSource={propertyTypeData}
          pagination={false}
          rowKey="type"
        />
      </Card>

      {/* 出租率分布 */}
      <Row gutter={16}>
        <Col span={12}>
          <Card title="出租率分布">
            <div style={{ padding: '20px' }}>
              <div style={{ marginBottom: '16px' }}>
                <Text>高出租率 (>80%)</Text>
                <Progress 
                  percent={65} 
                  strokeColor="#52c41a"
                  format={() => '65%'}
                />
              </div>
              <div style={{ marginBottom: '16px' }}>
                <Text>中等出租率 (60-80%)</Text>
                <Progress 
                  percent={25} 
                  strokeColor="#faad14"
                  format={() => '25%'}
                />
              </div>
              <div>
                <Text>低出租率 (<60%)</Text>
                <Progress 
                  percent={10} 
                  strokeColor="#ff4d4f"
                  format={() => '10%'}
                />
              </div>
            </div>
          </Card>
        </Col>
        <Col span={12}>
          <Card title="确权状态分析">
            <div style={{ padding: '20px' }}>
              <div style={{ marginBottom: '16px' }}>
                <Text>已确权</Text>
                <Progress 
                  percent={78} 
                  strokeColor="#52c41a"
                  format={() => '78%'}
                />
              </div>
              <div style={{ marginBottom: '16px' }}>
                <Text>部分确权</Text>
                <Progress 
                  percent={15} 
                  strokeColor="#faad14"
                  format={() => '15%'}
                />
              </div>
              <div>
                <Text>未确权</Text>
                <Progress 
                  percent={7} 
                  strokeColor="#ff4d4f"
                  format={() => '7%'}
                />
              </div>
            </div>
          </Card>
        </Col>
      </Row>
    </div>
  )
}

export default AssetAnalyticsPage