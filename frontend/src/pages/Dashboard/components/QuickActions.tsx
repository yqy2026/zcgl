import React from 'react'
import { Row, Col, Card, Space } from 'antd'
import {
  PlusOutlined,
  ImportOutlined,
  ExportOutlined,
  BarChartOutlined,
  FileTextOutlined,
  SettingOutlined,
} from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import { COLORS } from '@/styles/colorMap'

const QuickActions: React.FC = () => {
  const navigate = useNavigate()

  const actions = [
    {
      title: '新增资产',
      description: '添加新的物业资产',
      icon: <PlusOutlined style={{ fontSize: '24px', color: COLORS.primary }} />,
      onClick: () => navigate('/assets/new'),
    },
    {
      title: '批量导入',
      description: '从Excel导入资产数据',
      icon: <ImportOutlined style={{ fontSize: '24px', color: COLORS.success }} />,
      onClick: () => navigate('/assets/import'),
    },
    {
      title: '数据导出',
      description: '导出资产清单',
      icon: <ExportOutlined style={{ fontSize: '24px', color: COLORS.warning }} />,
      onClick: () => navigate('/assets/list'),
    },
    {
      title: '资产分析',
      description: '查看详细分析报告',
      icon: <BarChartOutlined style={{ fontSize: '24px', color: COLORS.info }} />,
      onClick: () => navigate('/assets/analytics'),
    },
    {
      title: '生成报表',
      description: '生成管理报表',
      icon: <FileTextOutlined style={{ fontSize: '24px', color: COLORS.secondary }} />,
      onClick: () => navigate('/reports'),
    },
    {
      title: '系统设置',
      description: '配置系统参数',
      icon: <SettingOutlined style={{ fontSize: '24px', color: COLORS.textTertiary }} />,
      onClick: () => navigate('/settings'),
    },
  ]

  return (
    <Row gutter={[16, 16]}>
      {actions.map((action, index) => (
        <Col xs={24} sm={12} md={8} lg={6} xl={4} key={index}>
          <Card
            hoverable
            style={{ textAlign: 'center', height: '120px' }}
            bodyStyle={{ padding: '16px' }}
            onClick={action.onClick}
          >
            <Space direction="vertical" size="small">
              {action.icon}
              <div>
                <div style={{ fontWeight: 'bold', fontSize: '14px' }}>
                  {action.title}
                </div>
                <div style={{ fontSize: '12px', color: COLORS.textSecondary }}>
                  {action.description}
                </div>
              </div>
            </Space>
          </Card>
        </Col>
      ))}
    </Row>
  )
}

export default QuickActions