import React from 'react'
import { Card, Typography } from 'antd'

const { Title } = Typography

const ApiTest: React.FC = () => {
  return (
    <div style={{ padding: '24px' }}>
      <Title level={2}>API测试</Title>
      <Card>
        <p>API测试页面正在开发中...</p>
      </Card>
    </div>
  )
}

export default ApiTest