import React from 'react'
import { Button, Card, Typography } from 'antd'

const { Title, Paragraph } = Typography

const TestApp: React.FC = () => {
  return (
    <div style={{ padding: '24px', maxWidth: '800px', margin: '0 auto' }}>
      <Card>
        <Title level={2}>🎉 前端测试页面</Title>
        <Paragraph>
          如果你能看到这个页面，说明前端基本配置正常！
        </Paragraph>
        
        <div style={{ marginTop: '24px' }}>
          <Button type="primary" size="large">
            测试按钮
          </Button>
        </div>
        
        <div style={{ marginTop: '24px', padding: '16px', background: '#f5f5f5', borderRadius: '8px' }}>
          <Title level={4}>系统信息</Title>
          <ul>
            <li>React: 正常运行 ✅</li>
            <li>Ant Design: 正常运行 ✅</li>
            <li>TypeScript: 正常运行 ✅</li>
            <li>Vite: 正常运行 ✅</li>
          </ul>
        </div>
      </Card>
    </div>
  )
}

export default TestApp