import React from 'react'
import { Card, Typography } from 'antd'

const { Title } = Typography

const UXDemoPage: React.FC = () => {
  return (
    <div style={{ padding: '24px' }}>
      <Title level={2}>UX演示</Title>
      <Card>
        <p>UX演示页面正在开发中...</p>
      </Card>
    </div>
  )
}

export default UXDemoPage