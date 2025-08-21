import React from 'react'
import { Row, Col, Card, Statistic, List, Button, Space, Typography, Progress } from 'antd'
import {
  HomeOutlined,
  BarChartOutlined,
  CalendarOutlined,
  AlertOutlined,
} from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import { useDashboardData } from './hooks/useDashboardData'
import MetricsCards from './components/MetricsCards'
import TodoList from './components/TodoList'
import AssetChart from './components/AssetChart'
import QuickActions from './components/QuickActions'

const { Title, Text } = Typography

const DashboardPage: React.FC = () => {
  const navigate = useNavigate()
  const { 
    metrics, 
    todoItems, 
    chartData, 
    recentActivities,
    isLoading 
  } = useDashboardData()

  return (
    <div style={{ padding: '24px' }}>
      {/* 页面标题 */}
      <div style={{ marginBottom: '24px' }}>
        <Title level={2}>
          <HomeOutlined style={{ marginRight: '8px', color: '#1890ff' }} />
          工作台
        </Title>
        <Text type="secondary">
          欢迎回来！这里是您的资产管理工作概览
        </Text>
      </div>

      {/* 关键指标卡片 */}
      <MetricsCards metrics={metrics} loading={isLoading} />

      {/* 主要内容区域 */}
      <Row gutter={24} style={{ marginTop: '24px' }}>
        {/* 左侧：待办事项 */}
        <Col xs={24} lg={12}>
          <Card 
            title={
              <Space>
                <AlertOutlined style={{ color: '#faad14' }} />
                <span>今日待办</span>
              </Space>
            }
            extra={
              <Button 
                type="link" 
                onClick={() => navigate('/tasks')}
              >
                查看全部
              </Button>
            }
            style={{ height: '400px' }}
          >
            <TodoList items={todoItems} loading={isLoading} />
          </Card>
        </Col>

        {/* 右侧：资产状态图表 */}
        <Col xs={24} lg={12}>
          <Card 
            title={
              <Space>
                <BarChartOutlined style={{ color: '#52c41a' }} />
                <span>资产概览</span>
              </Space>
            }
            extra={
              <Button 
                type="link" 
                onClick={() => navigate('/assets/analytics')}
              >
                详细分析
              </Button>
            }
            style={{ height: '400px' }}
          >
            <AssetChart data={chartData} loading={isLoading} />
          </Card>
        </Col>
      </Row>

      {/* 快速操作区域 */}
      <Row gutter={24} style={{ marginTop: '24px' }}>
        <Col span={24}>
          <Card title="快速操作">
            <QuickActions />
          </Card>
        </Col>
      </Row>

      {/* 最近活动 */}
      <Row gutter={24} style={{ marginTop: '24px' }}>
        <Col span={24}>
          <Card 
            title={
              <Space>
                <CalendarOutlined style={{ color: '#722ed1' }} />
                <span>最近活动</span>
              </Space>
            }
          >
            <List
              dataSource={recentActivities}
              loading={isLoading}
              renderItem={(item: any) => (
                <List.Item>
                  <List.Item.Meta
                    avatar={item.icon}
                    title={item.title}
                    description={
                      <Space>
                        <Text type="secondary">{item.description}</Text>
                        <Text type="secondary">·</Text>
                        <Text type="secondary">{item.time}</Text>
                      </Space>
                    }
                  />
                </List.Item>
              )}
            />
          </Card>
        </Col>
      </Row>
    </div>
  )
}

export default DashboardPage