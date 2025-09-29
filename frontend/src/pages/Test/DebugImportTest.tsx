import React, { useState } from 'react'
import { Card, Typography, Upload, Button, message, Alert, Space, Descriptions, Tag } from 'antd'
import { UploadOutlined } from '@ant-design/icons'
import type { UploadProps, UploadFile } from 'antd'
import { api } from '../../services/api'
import { STANDARD_SHEET_NAME } from '../../config/excelConfig'

const { Title, Text } = Typography

const DebugImportTest: React.FC = () => {
  const [fileList, setFileList] = useState<UploadFile[]>([])
  const [uploading, setUploading] = useState(false)
  const [result, setResult] = useState<any>(null)
  const [rawResponse, setRawResponse] = useState<any>(null)

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
      setRawResponse(null)
    },
    maxCount: 1,
  }

  const handleDebugImport = async () => {
    if (fileList.length === 0) {
      message.error('请先选择要导入的文件')
      return
    }

    setUploading(true)

    try {
      const formData = new FormData()
      formData.append('file', fileList[0] as any)

      console.log('=== 调试导入测试 ===')
      console.log('文件名:', fileList[0].name)
      console.log('工作簿名称:', STANDARD_SHEET_NAME)

      const response = await api.post('/excel/import', formData, {
        params: {
          sheet_name: STANDARD_SHEET_NAME,
          skip_errors: true  // 布尔值格式
        },
        timeout: 300000,
      })

      console.log('=== 原始响应对象 ===')
      console.log('Response:', response)
      console.log('Response.data:', response.data)
      console.log('Response.status:', response.status)
      console.log('Response.headers:', response.headers)

      // 保存原始响应
      setRawResponse(response)

      // 处理响应数据
      const result = response.data
      console.log('=== 处理后的结果 ===')
      console.log('Result:', result)
      console.log('Result.success:', result.success)
      console.log('Result.failed:', result.failed)
      console.log('Result.total:', result.total)

      setResult(result)

      // 检查数据完整性
      if (result.success !== undefined && result.failed !== undefined && result.total !== undefined) {
        message.success(`导入完成！成功: ${result.success}, 失败: ${result.failed}`)
      } else {
        message.error('响应数据格式不正确')
      }

    } catch (error: any) {
      console.error('导入错误:', error)
      console.error('错误响应:', error.response)

      setResult(error.response?.data || { message: '导入失败' })
      setRawResponse(error.response)
      message.error(`导入失败: ${error.response?.data?.message || '未知错误'}`)
    } finally {
      setUploading(false)
    }
  }

  const checkDatabaseCount = async () => {
    try {
      const response = await api.get('/assets')
      console.log('数据库资产数量:', response.data.data?.length || 0)
      message.success(`当前数据库共有 ${response.data.data?.length || 0} 条资产记录`)
    } catch (error: any) {
      message.error('查询失败: ' + (error.response?.data?.message || '未知错误'))
    }
  }

  return (
    <div style={{ padding: '24px' }}>
      <Title level={2}>调试导入测试</Title>

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

          <Space>
            <Button
              type="primary"
              onClick={handleDebugImport}
              loading={uploading}
              disabled={fileList.length === 0}
              size="large"
            >
              {uploading ? '导入中...' : '开始调试导入'}
            </Button>

            <Button
              onClick={checkDatabaseCount}
              size="large"
            >
              查询数据库记录数
            </Button>
          </Space>
        </Space>
      </Card>

      {rawResponse && (
        <Card title="原始响应信息" style={{ marginBottom: '16px' }}>
          <Descriptions bordered>
            <Descriptions.Item label="状态码">{rawResponse.status}</Descriptions.Item>
            <Descriptions.Item label="状态文本">{rawResponse.statusText}</Descriptions.Item>
            <Descriptions.Item label="Content-Type">{rawResponse.headers?.['content-type']}</Descriptions.Item>
          </Descriptions>
        </Card>
      )}

      {result && (
        <Card title="导入结果" style={{ marginBottom: '16px' }}>
          <Space direction="vertical" style={{ width: '100%' }}>
            <Descriptions bordered>
              <Descriptions.Item label="消息">{result.message || '无'}</Descriptions.Item>
              <Descriptions.Item label="总数">
                <Tag color="blue">{result.total || 0}</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="成功">
                <Tag color="green">{result.success || 0}</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="失败">
                <Tag color="red">{result.failed || 0}</Tag>
              </Descriptions.Item>
            </Descriptions>

            {result.errors && result.errors.length > 0 && (
              <Alert
                message="错误列表"
                description={
                  <ul>
                    {result.errors.map((error: string, index: number) => (
                      <li key={index}>{error}</li>
                    ))}
                  </ul>
                }
                type="error"
                showIcon
              />
            )}

            <Alert
              message="原始响应数据"
              description={<pre style={{ whiteSpace: 'pre-wrap', fontSize: '12px' }}>{JSON.stringify(result, null, 2)}</pre>}
              type="info"
              showIcon
            />
          </Space>
        </Card>
      )}

      <Card title="调试说明">
        <Text>
          这个页面用于深度调试导入功能。它会显示完整的响应信息和处理过程，
          帮助定位前端导入结果显示问题的根本原因。
        </Text>
      </Card>
    </div>
  )
}

export default DebugImportTest