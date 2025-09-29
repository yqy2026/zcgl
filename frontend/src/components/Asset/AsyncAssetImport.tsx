import React, { useState, useEffect } from 'react'
import {
  Card,
  Typography,
  Upload,
  Button,
  Progress,
  Space,
  Alert,
  Steps,
  Table,
  Tag,
  message,
  Modal,
  Statistic,
  Row,
  Col,
  Divider
} from 'antd'
import {
  UploadOutlined,
  DownloadOutlined,
  FileExcelOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined,
  SyncOutlined,
  ClockCircleOutlined,
  DeleteOutlined
} from '@ant-design/icons'
import type { UploadProps, UploadFile } from 'antd'
import { api } from '../../services/api'
import { STANDARD_SHEET_NAME, IMPORT_INSTRUCTIONS } from '../../config/excelConfig'

const { Title, Text } = Typography
const { Step } = Steps

interface ImportTask {
  task_id: string
  filename: string
  status: 'pending' | 'processing' | 'completed' | 'failed'
  progress: number
  created_at: number
  completed_at?: number
  result?: {
    success: number
    failed: number
    total: number
    errors: string[]
    message: string
  }
  error?: string
}

const AsyncAssetImport: React.FC = () => {
  const [currentStep, setCurrentStep] = useState(0)
  const [fileList, setFileList] = useState<UploadFile[]>([])
  const [currentTask, setCurrentTask] = useState<ImportTask | null>(null)
  const [pollingInterval, setPollingInterval] = useState<NodeJS.Timeout | null>(null)
  const [showTaskModal, setShowTaskModal] = useState(false)
  const [allTasks, setAllTasks] = useState<ImportTask[]>([])

  // 清理轮询
  useEffect(() => {
    return () => {
      if (pollingInterval) {
        clearInterval(pollingInterval)
      }
    }
  }, [pollingInterval])

  // 下载模板
  const handleDownloadTemplate = async () => {
    try {
      const response = await api.get('/excel/template', {
        responseType: 'blob'
      })

      const blob = new Blob([response.data])
      const url = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = 'land_property_asset_template.xlsx'
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      window.URL.revokeObjectURL(url)

      message.success('模板下载成功')
    } catch (error) {
      message.error('模板下载失败')
    }
  }

  // 文件上传配置
  const uploadProps: UploadProps = {
    fileList,
    beforeUpload: (file) => {
      const isExcel = file.type === 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' ||
                     file.type === 'application/vnd.ms-excel'

      if (!isExcel) {
        message.error('只能上传Excel文件(.xlsx, .xls)')
        return false
      }

      const isLt10M = file.size / 1024 / 1024 < 10
      if (!isLt10M) {
        message.error('文件大小不能超过10MB')
        return false
      }

      setFileList([file])
      setCurrentStep(1)
      return false
    },
    onRemove: () => {
      setFileList([])
      setCurrentStep(0)
      setCurrentTask(null)
    },
    maxCount: 1,
  }

  // 开始异步导入
  const handleAsyncImport = async () => {
    if (fileList.length === 0) {
      message.error('请先选择要导入的文件')
      return
    }

    try {
      const formData = new FormData()
      formData.append('file', fileList[0] as any)

      console.log('=== 异步导入开始 ===')
      console.log('文件名:', fileList[0].name)

      const response = await api.post('/excel/import/async', formData, {
        params: {
          sheet_name: STANDARD_SHEET_NAME,
          skip_errors: true
        }
      })

      const { task_id } = response.data
      console.log('任务ID:', task_id)

      setCurrentStep(2)
      message.success('导入任务已提交，正在后台处理')

      // 开始轮询任务状态
      startPolling(task_id)

    } catch (error: any) {
      console.error('提交导入任务失败:', error)
      message.error(`提交失败: ${error.response?.data?.detail || '未知错误'}`)
    }
  }

  // 开始轮询任务状态
  const startPolling = (taskId: string) => {
    if (pollingInterval) {
      clearInterval(pollingInterval)
    }

    const interval = setInterval(async () => {
      try {
        const response = await api.get(`/excel/import/status/${taskId}`)
        const task: ImportTask = response.data

        setCurrentTask(task)

        if (task.status === 'completed' || task.status === 'failed') {
          clearInterval(interval)
          setPollingInterval(null)

          if (task.status === 'completed') {
            message.success(`🎉 导入完成！成功导入 ${task.result?.success || 0} 条记录`)
          } else {
            message.error(`❌ 导入失败: ${task.error}`)
          }
        }
      } catch (error) {
        console.error('查询任务状态失败:', error)
        clearInterval(interval)
        setPollingInterval(null)
      }
    }, 2000) // 每2秒查询一次

    setPollingInterval(interval)
  }

  // 查看所有任务
  const handleViewTasks = async () => {
    try {
      const response = await api.get('/excel/import/tasks')
      setAllTasks(response.data.tasks)
      setShowTaskModal(true)
    } catch (error) {
      message.error('获取任务列表失败')
    }
  }

  // 删除任务
  const handleDeleteTask = async (taskId: string) => {
    try {
      await api.delete(`/excel/import/tasks/${taskId}`)
      message.success('任务已删除')

      // 刷新任务列表
      const response = await api.get('/excel/import/tasks')
      setAllTasks(response.data.tasks)
    } catch (error) {
      message.error('删除任务失败')
    }
  }

  // 重新开始
  const handleReset = () => {
    setCurrentStep(0)
    setFileList([])
    setCurrentTask(null)
    if (pollingInterval) {
      clearInterval(pollingInterval)
      setPollingInterval(null)
    }
  }

  // 任务状态标签
  const getStatusTag = (status: string) => {
    switch (status) {
      case 'pending':
        return <Tag color="default"><ClockCircleOutlined /> 等待中</Tag>
      case 'processing':
        return <Tag color="processing"><SyncOutlined spin /> 处理中</Tag>
      case 'completed':
        return <Tag color="success"><CheckCircleOutlined /> 已完成</Tag>
      case 'failed':
        return <Tag color="error"><ExclamationCircleOutlined /> 失败</Tag>
      default:
        return <Tag>{status}</Tag>
    }
  }

  // 任务表格列
  const taskColumns = [
    {
      title: '文件名',
      dataIndex: 'filename',
      key: 'filename',
      ellipsis: true,
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => getStatusTag(status),
    },
    {
      title: '进度',
      dataIndex: 'progress',
      key: 'progress',
      render: (progress: number) => <Progress percent={progress} size="small" />,
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (timestamp: number) => new Date(timestamp * 1000).toLocaleString(),
    },
    {
      title: '操作',
      key: 'actions',
      render: (_, record: ImportTask) => (
        <Space>
          {record.status === 'completed' && record.result && (
            <Button type="link" size="small">
              查看结果
            </Button>
          )}
          {(record.status === 'completed' || record.status === 'failed') && (
            <Button
              type="link"
              size="small"
              danger
              icon={<DeleteOutlined />}
              onClick={() => handleDeleteTask(record.task_id)}
            />
          )}
        </Space>
      ),
    },
  ]

  return (
    <div style={{ padding: '24px' }}>
      <Title level={2}>异步数据导入</Title>

      <Card>
        <Steps current={currentStep} style={{ marginBottom: '32px' }}>
          <Step title="选择文件" description="上传Excel文件" />
          <Step title="提交任务" description="后台处理" />
          <Step title="查看结果" description="导入完成" />
        </Steps>

        {/* 步骤0: 选择文件 */}
        {currentStep === 0 && (
          <div>
            <Alert
              message="异步导入说明"
              description={
                <div>
                  <p>• 异步导入支持大文件长时间处理，避免浏览器超时</p>
                  <p>• 提交导入任务后，可以在后台查看处理进度</p>
                  <p>• 导入完成后会自动显示结果</p>
                  {IMPORT_INSTRUCTIONS.map((instruction, index) => (
                    <p key={index}>{index + 1}. {instruction}</p>
                  ))}
                </div>
              }
              type="info"
              showIcon
              style={{ marginBottom: '24px' }}
            />

            <Row gutter={[16, 16]}>
              <Col xs={24} sm={12}>
                <Card size="small" title="第一步：下载模板">
                  <Space direction="vertical" style={{ width: '100%' }}>
                    <Text>下载标准的Excel导入模板</Text>
                    <Button
                      type="primary"
                      icon={<DownloadOutlined />}
                      onClick={handleDownloadTemplate}
                      block
                    >
                      下载Excel模板
                    </Button>
                  </Space>
                </Card>
              </Col>

              <Col xs={24} sm={12}>
                <Card size="small" title="第二步：上传文件">
                  <Space direction="vertical" style={{ width: '100%' }}>
                    <Text>选择填写好的Excel文件</Text>
                    <Upload.Dragger {...uploadProps}>
                      <p className="ant-upload-drag-icon">
                        <FileExcelOutlined style={{ fontSize: '48px', color: '#1890ff' }} />
                      </p>
                      <p className="ant-upload-text">点击或拖拽文件到此区域上传</p>
                      <p className="ant-upload-hint">
                        支持单个文件上传，仅支持.xlsx和.xls格式
                      </p>
                    </Upload.Dragger>
                  </Space>
                </Card>
              </Col>
            </Row>

            <div style={{ textAlign: 'center', marginTop: '24px' }}>
              <Button onClick={handleViewTasks}>
                查看历史任务
              </Button>
            </div>
          </div>
        )}

        {/* 步骤1: 提交任务 */}
        {currentStep === 1 && (
          <div style={{ textAlign: 'center' }}>
            <FileExcelOutlined style={{ fontSize: '64px', color: '#52c41a', marginBottom: '16px' }} />
            <Title level={4}>文件已选择</Title>
            <Text>文件名：{fileList[0]?.name}</Text>
            <br />
            <Text type="secondary">文件大小：{((fileList[0]?.size || 0) / 1024 / 1024).toFixed(2)} MB</Text>

            <Divider />

            <Space size="large">
              <Button onClick={() => setCurrentStep(0)}>
                重新选择
              </Button>
              <Button
                type="primary"
                icon={<UploadOutlined />}
                onClick={handleAsyncImport}
                size="large"
              >
                提交导入任务
              </Button>
            </Space>
          </div>
        )}

        {/* 步骤2: 查看进度和结果 */}
        {currentStep === 2 && currentTask && (
          <div>
            {/* 任务状态概览 */}
            <Card
              size="small"
              style={{
                marginBottom: '24px',
                backgroundColor: currentTask.status === 'completed' ? '#f6ffed' :
                               currentTask.status === 'failed' ? '#fff2f0' : '#f0f9ff',
                border: currentTask.status === 'completed' ? '1px solid #b7eb8f' :
                         currentTask.status === 'failed' ? '1px solid #ffccc7' : '1px solid #91d5ff'
              }}
            >
              <div style={{ textAlign: 'center', padding: '16px' }}>
                {getStatusTag(currentTask.status)}
                <Title level={4} style={{ marginTop: '8px' }}>
                  {currentTask.filename}
                </Title>

                {currentTask.status === 'processing' && (
                  <Progress
                    percent={currentTask.progress}
                    status="active"
                    style={{ marginTop: '16px' }}
                  />
                )}
              </div>
            </Card>

            {/* 任务结果 */}
            {currentTask.result && (
              <div>
                <Row gutter={[16, 16]} style={{ marginBottom: '24px' }}>
                  <Col xs={24} sm={8}>
                    <Card size="small" bordered={false}>
                      <Statistic
                        title="成功记录"
                        value={currentTask.result.success}
                        valueStyle={{ color: '#3f8600' }}
                      />
                    </Card>
                  </Col>
                  <Col xs={24} sm={8}>
                    <Card size="small" bordered={false}>
                      <Statistic
                        title="失败记录"
                        value={currentTask.result.failed}
                        valueStyle={{ color: '#cf1322' }}
                      />
                    </Card>
                  </Col>
                  <Col xs={24} sm={8}>
                    <Card size="small" bordered={false}>
                      <Statistic
                        title="总计"
                        value={currentTask.result.total}
                        valueStyle={{ color: '#1890ff' }}
                      />
                    </Card>
                  </Col>
                </Row>

                {currentTask.result.errors.length > 0 && (
                  <Alert
                    message="导入错误"
                    description={
                      <ul>
                        {currentTask.result.errors.map((error, index) => (
                          <li key={index}>{error}</li>
                        ))}
                      </ul>
                    }
                    type="error"
                    showIcon
                    style={{ marginBottom: '16px' }}
                  />
                )}
              </div>
            )}

            {currentTask.error && (
              <Alert
                message="导入失败"
                description={currentTask.error}
                type="error"
                showIcon
                style={{ marginBottom: '16px' }}
              />
            )}

            <div style={{ textAlign: 'center', marginTop: '24px' }}>
              <Space size="large">
                <Button onClick={handleReset}>
                  重新导入
                </Button>
                <Button type="primary" onClick={() => window.location.href = '/assets'}>
                  查看资产列表
                </Button>
              </Space>
            </div>
          </div>
        )}
      </Card>

      {/* 任务列表模态框 */}
      <Modal
        title="导入任务列表"
        open={showTaskModal}
        onCancel={() => setShowTaskModal(false)}
        footer={null}
        width={800}
      >
        <Table
          columns={taskColumns}
          dataSource={allTasks}
          rowKey="task_id"
          pagination={{ pageSize: 10 }}
          size="small"
        />
      </Modal>
    </div>
  )
}

export default AsyncAssetImport