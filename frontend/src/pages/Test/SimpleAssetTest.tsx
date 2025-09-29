import React from 'react'
import { Card, Typography } from 'antd'

const { Title } = Typography

const SimpleAssetTest: React.FC = () => {
  return (
    <div style={{ padding: '24px' }}>
      <Title level={2}>简单资产测试</Title>
      <Card>
        <p>简单资产测试页面正在开发中...</p>
      </Card>
    </div>
  )
}

export default SimpleAssetTest