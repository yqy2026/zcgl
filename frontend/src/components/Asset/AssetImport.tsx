import React, { useState } from 'react'
import {
  Card,
  Upload,
  Button,
  Progress,
  Alert,
  Steps,
  Table,
  Typography,
  Space,
  Divider,
  Tag,
  Modal,
  List,
  Tooltip,
  message,
} from 'antd'
import {
  InboxOutlined,
  UploadOutlined,
  DownloadOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined,
  CloseCircleOutlined,
  FileExcelOutlined,
  EyeOutlined,
  DeleteOutlined,
} from '@ant-design/icons'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import type { UploadProps, UploadFile } from 'antd'

import { assetService } from '@/services/assetService'

const { Dragger } = Upload
const { Step } = Steps
const { Title, Text, Paragraph } = Typography

interface ImportResult {
  id: string
  filename: string
  status: 'processing' | 'completed' | 'failed'
  total_rows: number
  success_count: number
  error_count: number
  errors: Array<{
    row: number
    field: string
    message: string
    value: any
  }>
  created_at: string
  completed_at?: string
}

interface AssetImportProps {
  onImportComplete?: (result: ImportResult) => void
}

const AssetImport: React.FC<AssetImportProps> = ({ onImportComplete }) => {
  const [currentStep, setCurrentStep] = useState(0)
  const [uploadedFile, setUploadedFile] = useState<UploadFile | null>(null)
  const [importResult, setImportResult] = useState<ImportResult | null>(null)
  const [previewVisible, setPreviewVisible] = useState(false)
  const [previewData, setPreviewData] = useState<any[]>([])
  const [errorDetailVisible, setErrorDetailVisible] = useState(false)
  
  const queryClient = useQueryClient()

  // 获取导入历史
  const { data: importHistory, refetch: refetchHistory } = useQuery({
    queryKey: ['import-history'],
    queryFn: () => assetService.getImportHistory(),
    refetchInterval: 5000, // 每5秒刷新一次
  })

  // 文件上传变更
  const uploadMutation = useMutation({
    mutationFn: (file: File) => assetService.uploadImportFile(file),
    onSuccess: (result) => {
      setImportResult(result)
      setCurrentStep(1)
      message.success('文件上传成功，开始处理...')
      
      // 开始轮询导入状态
      pollImportStatus(result.id)
    },
    onError: (error: any) => {
      message.error(error.message || '文件上传失败')
    },
  })

  // 轮询导入状态
  const pollImportStatus = (importId: string) => {
    const interval = setInterval(async () => {
      try {
        const result = await assetService.getImportStatus(importId)
        setImportResult(result)
        
        if (result.status === 'completed' || result.status === 'failed') {
          clearInterval(interval)
          setCurrentStep(2)
          refetchHistory()
          
          if (result.status === 'completed') {
            message.success(`导入完成！成功导入 ${result.success_count} 条记录`)
            onImportComplete?.(result)
          } else {
            message.error('导入失败，请查看错误详情')
          }
        }
      } catch (error) {
        clearInterval(interval)
        message.error('获取导入状态失败')
      }
    }, 2000)
  }

  // 文件上传配置
  const uploadProps: UploadProps = {
    name: 'file',
    multiple: false,
    accept: '.xlsx,.xls',
    beforeUpload: (file) => {
      // 检查文件类型
      const isExcel = file.type === 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' ||
                     file.type === 'application/vnd.ms-excel'
      
      if (!isExcel) {
        message.error('只能上传 Excel 文件！')
        return false
      }

      // 检查文件大小（限制为10MB）
      const isLt10M = file.size / 1024 / 1024 < 10
      if (!isLt10M) {
        message.error('文件大小不能超过 10MB！')
        return false
      }

      setUploadedFile(file as UploadFile)
      return false // 阻止自动上传
    },
    onRemove: () => {
      setUploadedFile(null)
      setCurrentStep(0)
      setImportResult(null)
    },
  }

  // 开始导入
  const handleStartImport = () => {
    if (!uploadedFile?.originFileObj) {
      message.error('请先选择文件')
      return
    }

    uploadMutation.mutate(uploadedFile.originFileObj)
  }

  // 预览数据
  const handlePreviewData = async () => {
    if (!uploadedFile?.originFileObj) return
    
    try {
      const data = await assetService.previewImportFile(uploadedFile.originFileObj)
      setPreviewData(data)
      setPreviewVisible(true)
    } catch (error: any) {
      message.error(error.message || '预览失败')
    }
  }

  // 下载模板
  const handleDownloadTemplate = async () => {
    try {
      await assetService.downloadImportTemplate()
      message.success('模板下载成功')
    } catch (error: any) {
      message.error(error.message || '模板下载失败')
    }
  }

  // 重新开始
  const handleRestart = () => {
    setCurrentStep(0)
    setUploadedFile(null)
    setImportResult(null)
    setPreviewData([])
  }

  // 删除导入记录
  const handleDeleteImportRecord = async (id: string) => {
    try {
      await assetService.deleteImportRecord(id)
      message.success('删除成功')
      refetchHistory()
    } catch (error: any) {
      message.error(error.message || '删除失败')
    }
  }

  // 预览表格列配置
  const previewColumns = [
    { title: '行号', dataIndex: 'rowIndex', width: 60 },
    { title: '物业名称', dataIndex: 'property_name', width: 150 },
    { title: '权属方', dataIndex: 'ownership_entity', width: 120 },
    { title: '地址', dataIndex: 'address', width: 200 },
    { title: '确权状态', dataIndex: 'ownership_status', width: 100 },
    { title: '物业性质', dataIndex: 'property_nature', width: 100 },
    { title: '使用状态', dataIndex: 'usage_status', width: 100 },
  ]

  // 错误详情表格列配置
  const errorColumns = [
    { title: '行号', dataIndex: 'row', width: 60 },
    { title: '字段', dataIndex: 'field', width: 100 },
    { title: '错误信息', dataIndex: 'message', width: 200 },
    { title: '原始值', dataIndex: 'value', width: 150 },
  ]

  return (
    <div>
      {/* 导入步骤 */}
      <Card title="Excel 数据导入" style={{ marginBottom: 16 }}>
        <Steps current={currentStep} style={{ marginBottom: 24 }}>
          <Step title="选择文件" description="上传 Excel 文件" />
          <Step title="处理中" description="解析和验证数据" />
          <Step title="完成" description="查看导入结果" />
        </Steps>

        {/* 步骤1：文件上传 */}
        {currentStep === 0 && (
          <div>
            <Space direction="vertical" style={{ width: '100%' }}>
              <Alert
                message="导入说明"
                description={
                  <div>
                    <p>1. 请使用标准的 Excel 模板文件进行数据导入</p>
                    <p>2. 支持 .xlsx 和 .xls 格式，文件大小不超过 10MB</p>
                    <p>3. 必填字段：物业名称、权属方、地址、确权状态、物业性质、使用状态</p>
                    <p>4. 导入前请确保数据格式正确，避免导入失败</p>
                  </div>
                }
                type="info"
                showIcon
                style={{ marginBottom: 16 }}
              />

              <div style={{ textAlign: 'center', marginBottom: 16 }}>
                <Button
                  type="primary"
                  icon={<DownloadOutlined />}
                  onClick={handleDownloadTemplate}
                >
                  下载导入模板
                </Button>
              </div>

              <Dragger {...uploadProps} style={{ marginBottom: 16 }}>
                <p className="ant-upload-drag-icon">
                  <InboxOutlined />
                </p>
                <p className="ant-upload-text">点击或拖拽文件到此区域上传</p>
                <p className="ant-upload-hint">
                  支持 Excel 文件格式（.xlsx, .xls），单个文件不超过 10MB
                </p>
              </Dragger>

              {uploadedFile && (
                <div>
                  <Alert
                    message={`已选择文件: ${uploadedFile.name}`}
                    type="success"
                    showIcon
                    style={{ marginBottom: 16 }}
                  />
                  
                  <Space>
                    <Button
                      type="primary"
                      icon={<UploadOutlined />}
                      onClick={handleStartImport}
                      loading={uploadMutation.isPending}
                    >
                      开始导入
                    </Button>
                    <Button
                      icon={<EyeOutlined />}
                      onClick={handlePreviewData}
                    >
                      预览数据
                    </Button>
                  </Space>
                </div>
              )}
            </Space>
          </div>
        )}

        {/* 步骤2：处理中 */}
        {currentStep === 1 && importResult && (
          <div style={{ textAlign: 'center' }}>
            <div style={{ marginBottom: 24 }}>
              <FileExcelOutlined style={{ fontSize: 48, color: '#1890ff' }} />
            </div>
            <Title level={4}>正在处理文件...</Title>
            <Paragraph type="secondary">
              文件名: {importResult.filename}
            </Paragraph>
            <Progress
              type="circle"
              percent={75}
              status="active"
              style={{ marginBottom: 16 }}
            />
            <div>
              <Text type="secondary">请稍候，正在解析和验证数据...</Text>
            </div>
          </div>
        )}

        {/* 步骤3：完成 */}
        {currentStep === 2 && importResult && (
          <div>
            <div style={{ textAlign: 'center', marginBottom: 24 }}>
              {importResult.status === 'completed' ? (
                <CheckCircleOutlined style={{ fontSize: 48, color: '#52c41a' }} />
              ) : (
                <CloseCircleOutlined style={{ fontSize: 48, color: '#ff4d4f' }} />
              )}
            </div>

            <div style={{ marginBottom: 24 }}>
              <Title level={4} style={{ textAlign: 'center' }}>
                {importResult.status === 'completed' ? '导入完成' : '导入失败'}
              </Title>
              
              <Space direction="vertical" style={{ width: '100%' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <Text>文件名:</Text>
                  <Text strong>{importResult.filename}</Text>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <Text>总行数:</Text>
                  <Text strong>{importResult.total_rows}</Text>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <Text>成功导入:</Text>
                  <Text strong style={{ color: '#52c41a' }}>
                    {importResult.success_count}
                  </Text>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <Text>失败记录:</Text>
                  <Text strong style={{ color: '#ff4d4f' }}>
                    {importResult.error_count}
                  </Text>
                </div>
              </Space>
            </div>

            {importResult.error_count > 0 && (
              <Alert
                message="部分数据导入失败"
                description={
                  <div>
                    <p>有 {importResult.error_count} 条记录导入失败，请查看错误详情并修正后重新导入。</p>
                    <Button
                      type="link"
                      onClick={() => setErrorDetailVisible(true)}
                    >
                      查看错误详情
                    </Button>
                  </div>
                }
                type="warning"
                showIcon
                style={{ marginBottom: 16 }}
              />
            )}

            <div style={{ textAlign: 'center' }}>
              <Space>
                <Button type="primary" onClick={handleRestart}>
                  重新导入
                </Button>
                <Button onClick={() => queryClient.invalidateQueries({ queryKey: ['assets'] })}>
                  刷新资产列表
                </Button>
              </Space>
            </div>
          </div>
        )}
      </Card>

      {/* 导入历史 */}
      <Card title="导入历史" size="small">
        <List
          dataSource={importHistory}
          renderItem={(item: ImportResult) => (
            <List.Item
              actions={[
                <Tooltip title="查看详情">
                  <Button
                    type="text"
                    icon={<EyeOutlined />}
                    onClick={() => {
                      setImportResult(item)
                      setErrorDetailVisible(true)
                    }}
                  />
                </Tooltip>,
                <Tooltip title="删除记录">
                  <Button
                    type="text"
                    danger
                    icon={<DeleteOutlined />}
                    onClick={() => {
                      Modal.confirm({
                        title: '确认删除',
                        content: '确定要删除这条导入记录吗？',
                        onOk: () => handleDeleteImportRecord(item.id),
                      })
                    }}
                  />
                </Tooltip>,
              ]}
            >
              <List.Item.Meta
                title={
                  <Space>
                    <Text strong>{item.filename}</Text>
                    <Tag color={
                      item.status === 'completed' ? 'green' :
                      item.status === 'failed' ? 'red' : 'blue'
                    }>
                      {item.status === 'completed' ? '完成' :
                       item.status === 'failed' ? '失败' : '处理中'}
                    </Tag>
                  </Space>
                }
                description={
                  <div>
                    <div>
                      导入时间: {new Date(item.created_at).toLocaleString()}
                    </div>
                    <div>
                      成功: {item.success_count} / 失败: {item.error_count} / 总计: {item.total_rows}
                    </div>
                  </div>
                }
              />
            </List.Item>
          )}
        />
      </Card>

      {/* 数据预览模态框 */}
      <Modal
        title="数据预览"
        open={previewVisible}
        onCancel={() => setPreviewVisible(false)}
        footer={[
          <Button key="close" onClick={() => setPreviewVisible(false)}>
            关闭
          </Button>,
        ]}
        width={1000}
      >
        <Table
          dataSource={previewData}
          columns={previewColumns}
          scroll={{ x: 800, y: 400 }}
          pagination={{ pageSize: 10 }}
          size="small"
        />
      </Modal>

      {/* 错误详情模态框 */}
      <Modal
        title="错误详情"
        open={errorDetailVisible}
        onCancel={() => setErrorDetailVisible(false)}
        footer={[
          <Button key="close" onClick={() => setErrorDetailVisible(false)}>
            关闭
          </Button>,
        ]}
        width={800}
      >
        {importResult?.errors && (
          <Table
            dataSource={importResult.errors}
            columns={errorColumns}
            scroll={{ y: 400 }}
            pagination={{ pageSize: 10 }}
            size="small"
          />
        )}
      </Modal>
    </div>
  )
}

export default AssetImport