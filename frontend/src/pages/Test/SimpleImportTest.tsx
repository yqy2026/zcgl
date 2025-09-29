import React, { useState } from 'react'
import { Card, Typography, Upload, Button, message, Alert, Space } from 'antd'
import { UploadOutlined } from '@ant-design/icons'
import type { UploadProps, UploadFile } from 'antd'
import { api } from '../../services/api'
import { STANDARD_SHEET_NAME } from '../../config/excelConfig'

const { Title, Text } = Typography

const SimpleImportTest: React.FC = () => {
  const [fileList, setFileList] = useState<UploadFile[]>([])
  const [uploading, setUploading] = useState(false)
  const [result, setResult] = useState<any>(null)

  const uploadProps: UploadProps = {
    fileList,
    beforeUpload: (file) => {
      const isExcel = file.type === 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' ||
                     file.type === 'application/vnd.ms-excel'

      if (!isExcel) {
        message.error('只能上传Excel文件(.xlsx, .xls)')
        return false
      }

      setFileList([file])
      return false // 阻止自动上传
    },
    onRemove: () => {
      setFileList([])
      setResult(null)
    },
    maxCount: 1,
  }

  const handleTestImport = async () => {
    if (fileList.length === 0) {
      message.error('请先选择要导入的文件')
      return
    }

    setUploading(true)

    try {
      const formData = new FormData()
      formData.append('file', fileList[0] as any)

      console.log('=== 简化导入测试 ===')
      console.log('文件名:', fileList[0].name)
      console.log('工作簿名称:', STANDARD_SHEET_NAME)

      const response = await api.post('/excel/import', formData, {
        params: {
          sheet_name: STANDARD_SHEET_NAME,
          skip_errors: true
        },
        timeout: 300000,
      })

      console.log('响应结果:', response.data)
      setResult(response.data)
      message.success(`导入完成！成功: ${response.data.success}, 失败: ${response.data.failed}`)

    } catch (error: any) {
      console.error('导入错误:', error)
      console.error('错误响应:', error.response?.data)
      setResult(error.response?.data || { message: '导入失败' })
      message.error(`导入失败: ${error.response?.data?.message || '未知错误'}`)
    } finally {
      setUploading(false)
    }
  }

  return (
    <div style={{ padding: '24px' }}>
      <Title level={2}>简化导入测试</Title>

      <Card style={{ marginBottom: '16px' }}>
        <Space direction="vertical" style={{ width: '100%' }}>
          <Text>选择要测试的Excel文件：</Text>
          <Upload.Dragger {...uploadProps}>
            <p className="ant-upload-drag-icon">
              <UploadOutlined style={{ fontSize: '48px', color: '#1890ff' }} />
            </p>
            <p className="ant-upload-text">点击或拖拽文件到此区域上传</p>
            <p className="ant-upload-hint">
              支持单个文件上传，仅支持.xlsx和.xls格式
            </p>
          </Upload.Dragger>

          <Button
            type="primary"
            onClick={handleTestImport}
            loading={uploading}
            disabled={fileList.length === 0}
            size="large"
            block
          >
            {uploading ? '导入中...' : '开始导入测试'}
          </Button>
        </Space>
      </Card>

      {result && (
        <Card title="导入结果" style={{ marginBottom: '16px' }}>
          <Alert
            message="API响应"
            description={<pre style={{ whiteSpace: 'pre-wrap' }}>{JSON.stringify(result, null, 2)}</pre>}
            type={result.success > 0 ? 'success' : 'info'}
            showIcon
          />
        </Card>
      )}

      <Card title="调试说明">
        <Text>
          这个页面用于测试Web端导入功能。如果这里导入成功，但正式导入页面失败，
          说明问题可能在于正式导入页面的逻辑上。
        </Text>
      </Card>
    </div>
  )
}

export default SimpleImportTest