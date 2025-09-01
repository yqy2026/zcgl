import React, { useState } from 'react'
import { Button, Card, Typography, Space, Spin, Alert } from 'antd'
import { apiRequest, API_ENDPOINTS } from '../../config/api'

const { Title, Paragraph, Text } = Typography

const ApiTest: React.FC = () => {
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<any>(null)
  const [error, setError] = useState<string | null>(null)

  const testApi = async (endpoint: string, description: string) => {
    setLoading(true)
    setError(null)
    setResult(null)

    try {
      const data = await apiRequest(endpoint)
      setResult({ description, data })
    } catch (err: any) {
      setError(`${description} 失败: ${err.message}`)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{ padding: '24px' }}>
      <Title level={2}>API 连接测试</Title>
      
      <Space direction="vertical" size="large" style={{ width: '100%' }}>
        <Card title="测试选项">
          <Space wrap>
            <Button 
              type="primary" 
              onClick={() => testApi(API_ENDPOINTS.statistics.basic, '基础统计数据')}
              loading={loading}
            >
              测试统计API
            </Button>
            
            <Button 
              onClick={() => testApi(`${API_ENDPOINTS.assets}?page=1&limit=5`, '资产列表')}
              loading={loading}
            >
              测试资产列表API
            </Button>
            
            <Button 
              onClick={() => testApi('/health', '健康检查')}
              loading={loading}
            >
              测试健康检查
            </Button>
          </Space>
        </Card>

        {loading && (
          <Card>
            <Spin size="large" />
            <Text style={{ marginLeft: 16 }}>正在请求API...</Text>
          </Card>
        )}

        {error && (
          <Alert
            message="API 请求失败"
            description={error}
            type="error"
            showIcon
          />
        )}

        {result && (
          <Card title={`测试结果: ${result.description}`}>
            <Paragraph>
              <Text strong>响应数据:</Text>
            </Paragraph>
            <pre style={{ 
              background: '#f5f5f5', 
              padding: '16px', 
              borderRadius: '4px',
              overflow: 'auto',
              maxHeight: '400px'
            }}>
              {JSON.stringify(result.data, null, 2)}
            </pre>
          </Card>
        )}
      </Space>
    </div>
  )
}

export default ApiTest