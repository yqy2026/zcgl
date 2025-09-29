import React, { useEffect, useState } from 'react'
import { Card, Typography, Spin, Alert, Button } from 'antd'
import { dictionaryService } from '../../services/dictionary'

const { Title, Paragraph } = Typography

const DictionaryTestPage: React.FC = () => {
  const [results, setResults] = useState<Record<string, any>>({})
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const testDictionaries = async () => {
    setLoading(true)
    setError(null)
    const testResults: Record<string, any> = {}

    const dictTypes = [
      'property_nature',
      'usage_status',
      'ownership_status',
      'ownership_category',
      'business_category',
      'certificated_usage',
      'actual_usage',
      'tenant_type',
      'contract_status',
      'business_model',
      'operation_status'
    ]

    try {
      for (const dictType of dictTypes) {
        try {
          console.log(`🧪 测试字典类型: ${dictType}`)
          const result = await dictionaryService.getOptions(dictType, {
            useCache: true,
            useFallback: true
          })

          if (result.success) {
            testResults[dictType] = {
              success: true,
              data: result.data,
              count: result.data.length,
              source: result.source
            }
            console.log(`✅ 字典类型 ${dictType} 测试成功 (${result.source}):`, result.data)
          } else {
            testResults[dictType] = {
              success: false,
              error: result.error || '未知错误'
            }
            console.error(`❌ 字典类型 ${dictType} 测试失败:`, result.error)
          }
        } catch (err) {
          console.error(`❌ 字典类型 ${dictType} 测试失败:`, err)
          testResults[dictType] = {
            success: false,
            error: err instanceof Error ? err.message : '未知错误'
          }
        }
      }

      setResults(testResults)
    } catch (err) {
      console.error('❌ 批量测试失败:', err)
      setError(err instanceof Error ? err.message : '测试失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    testDictionaries()
  }, [])

  return (
    <div style={{ padding: '24px' }}>
      <Title level={2}>字典数据测试页面</Title>
      <Paragraph>
        此页面用于测试字典数据的加载情况，帮助诊断新增资产页面的字典问题。
      </Paragraph>

      {loading && (
        <div style={{ textAlign: 'center', margin: '24px 0' }}>
          <Spin size="large" />
          <p style={{ marginTop: '16px' }}>正在测试字典数据加载...</p>
        </div>
      )}

      {error && (
        <Alert
          message="测试失败"
          description={error}
          type="error"
          style={{ marginBottom: '24px' }}
        />
      )}

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '16px' }}>
        {Object.entries(results).map(([dictType, result]: [string, any]) => (
          <Card
            key={dictType}
            title={`字典类型: ${dictType}`}
            style={{
              borderLeft: `4px solid ${result.success ? '#52c41a' : '#ff4d4f'}`
            }}
          >
            {result.success ? (
              <div>
                <p><strong>状态:</strong> ✅ 成功</p>
                <p><strong>数据来源:</strong> {result.source || 'api'}</p>
                <p><strong>数据条数:</strong> {result.count}</p>
                <p><strong>数据预览:</strong></p>
                <pre style={{
                  background: '#f5f5f5',
                  padding: '8px',
                  borderRadius: '4px',
                  fontSize: '12px',
                  maxHeight: '150px',
                  overflow: 'auto'
                }}>
                  {JSON.stringify(result.data, null, 2)}
                </pre>
              </div>
            ) : (
              <div>
                <p><strong>状态:</strong> ❌ 失败</p>
                <p><strong>错误信息:</strong> {result.error}</p>
              </div>
            )}
          </Card>
        ))}
      </div>

      <div style={{ marginTop: '24px' }}>
        <Button type="primary" onClick={testDictionaries} loading={loading}>
          重新测试
        </Button>
      </div>
    </div>
  )
}

export default DictionaryTestPage