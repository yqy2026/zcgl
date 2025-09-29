import React, { useState } from 'react'
import { Card, Button, message, Typography, Space } from 'antd'
import { DownloadOutlined, FileExcelOutlined } from '@ant-design/icons'
import { assetService } from '@/services/assetService'

const { Title, Text } = Typography

const TemplateTestPage: React.FC = () => {
  const [loading, setLoading] = useState(false)

  const handleDownloadAssetTemplate = async () => {
    setLoading(true)
    try {
      await assetService.downloadImportTemplate()
      message.success('资产导入模板下载成功')
    } catch (error: any) {
      console.error('下载模板失败:', error)
      message.error(`下载模板失败: ${error.message || '网络错误'}`)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{ padding: '24px' }}>
      <Title level={2}>模板测试页面</Title>
      <Text type="secondary">测试数据模板下载功能</Text>

      <Card style={{ marginTop: '24px' }}>
        <Space direction="vertical" size="large" style={{ width: '100%' }}>
          <div>
            <Title level={4}>
              <FileExcelOutlined style={{ marginRight: '8px' }} />
              资产导入模板
            </Title>
            <Text type="secondary">
              用于批量导入资产数据的Excel模板，包含所有必要字段
            </Text>
          </div>

          <Button
            type="primary"
            size="large"
            icon={<DownloadOutlined />}
            onClick={handleDownloadAssetTemplate}
            loading={loading}
          >
            下载资产导入模板
          </Button>
        </Space>
      </Card>
    </div>
  )
}

export default TemplateTestPage