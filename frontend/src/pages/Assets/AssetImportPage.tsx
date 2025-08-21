import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { 
  Card, 
  Typography, 
  Button, 
  Space, 
  Upload, 
  Progress, 
  Alert, 
  Table, 
  Divider,
  Steps,
  Result
} from 'antd'
import {
  ArrowLeftOutlined,
  UploadOutlined,
  DownloadOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined,
} from '@ant-design/icons'
import type { UploadProps } from 'antd'

const { Title, Paragraph, Text } = Typography
const { Step } = Steps

interface ImportResult {
  success: number
  failed: number
  errors: string[]
}

const AssetImportPage: React.FC = () => {
  const navigate = useNavigate()
  const [currentStep, setCurrentStep] = useState(0)
  const [uploading, setUploading] = useState(false)
  const [progress, setProgress] = useState(0)
  const [importResult, setImportResult] = useState<ImportResult | null>(null)

  const handleBack = () => {
    navigate('/assets/list')
  }

  const handleDownloadTemplate = () => {
    // 模拟下载模板
    const link = document.createElement('a')
    link.href = '/templates/asset-import-template.xlsx'
    link.download = '资产导入模板.xlsx'
    link.click()
  }

  const uploadProps: UploadProps = {
    name: 'file',
    action: '/api/assets/import',
    accept: '.xlsx,.xls',
    showUploadList: false,
    beforeUpload: (file) => {
      const isExcel = file.type === 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' ||
                     file.type === 'application/vnd.ms-excel'
      if (!isExcel) {
        alert('只能上传Excel文件！')
        return false
      }
      return true
    },
    onChange: (info) => {
      if (info.file.status === 'uploading') {
        setUploading(true)
        setCurrentStep(1)
        // 模拟进度
        const timer = setInterval(() => {
          setProgress(prev => {
            if (prev >= 100) {
              clearInterval(timer)
              setUploading(false)
              setCurrentStep(2)
              // 模拟导入结果
              setImportResult({
                success: 45,
                failed: 5,
                errors: [
                  '第3行：物业名称不能为空',
                  '第7行：权属方不能为空',
                  '第12行：面积数据格式错误',
                  '第18行：确权状态值无效',
                  '第25行：地址信息不完整',
                ]
              })
              return 100
            }
            return prev + 10
          })
        }, 200)
      }
    },
  }

  const errorColumns = [
    {
      title: '行号',
      dataIndex: 'row',
      key: 'row',
      width: 80,
    },
    {
      title: '错误信息',
      dataIndex: 'error',
      key: 'error',
    },
  ]

  const errorData = importResult?.errors.map((error, index) => ({
    key: index,
    row: error.match(/第(\d+)行/)?.[1] || '-',
    error: error.replace(/第\d+行：/, ''),
  })) || []

  return (
    <div style={{ padding: '24px' }}>
      {/* 页面头部 */}
      <div style={{ marginBottom: '24px' }}>
        <Space>
          <Button 
            icon={<ArrowLeftOutlined />} 
            onClick={handleBack}
          >
            返回列表
          </Button>
          <Title level={2} style={{ margin: 0 }}>
            批量导入资产
          </Title>
        </Space>
      </div>

      {/* 导入步骤 */}
      <Card style={{ marginBottom: '24px' }}>
        <Steps current={currentStep}>
          <Step title="准备文件" description="下载模板并填写数据" />
          <Step title="上传文件" description="上传Excel文件" />
          <Step title="导入完成" description="查看导入结果" />
        </Steps>
      </Card>

      {/* 步骤内容 */}
      {currentStep === 0 && (
        <Card title="第一步：准备导入文件">
          <Alert
            message="导入说明"
            description={
              <div>
                <Paragraph>
                  1. 请先下载Excel模板文件，按照模板格式填写资产数据
                </Paragraph>
                <Paragraph>
                  2. 必填字段：物业名称、权属方、所在地址、物业性质、使用状态、确权状态
                </Paragraph>
                <Paragraph>
                  3. 面积字段请填写数字，单位为平方米
                </Paragraph>
                <Paragraph>
                  4. 日期字段请使用YYYY-MM-DD格式
                </Paragraph>
              </div>
            }
            type="info"
            showIcon
            style={{ marginBottom: '24px' }}
          />

          <Space>
            <Button 
              type="primary" 
              icon={<DownloadOutlined />}
              onClick={handleDownloadTemplate}
            >
              下载导入模板
            </Button>
            <Upload {...uploadProps}>
              <Button icon={<UploadOutlined />}>
                选择文件上传
              </Button>
            </Upload>
          </Space>
        </Card>
      )}

      {currentStep === 1 && (
        <Card title="第二步：正在处理文件">
          <div style={{ textAlign: 'center', padding: '40px' }}>
            <Progress 
              type="circle" 
              percent={progress} 
              status={uploading ? 'active' : 'success'}
            />
            <div style={{ marginTop: '16px' }}>
              <Text>{uploading ? '正在上传和处理文件...' : '文件处理完成'}</Text>
            </div>
          </div>
        </Card>
      )}

      {currentStep === 2 && importResult && (
        <div>
          <Card title="第三步：导入结果" style={{ marginBottom: '24px' }}>
            <Result
              status={importResult.failed === 0 ? 'success' : 'warning'}
              title={`导入完成！成功 ${importResult.success} 条，失败 ${importResult.failed} 条`}
              subTitle={
                importResult.failed > 0 
                  ? '部分数据导入失败，请查看下方错误详情并修正后重新导入'
                  : '所有数据已成功导入系统'
              }
              extra={[
                <Button 
                  type="primary" 
                  key="list"
                  onClick={() => navigate('/assets/list')}
                >
                  查看资产列表
                </Button>,
                <Button 
                  key="retry"
                  onClick={() => {
                    setCurrentStep(0)
                    setImportResult(null)
                    setProgress(0)
                  }}
                >
                  重新导入
                </Button>,
              ]}
            />
          </Card>

          {importResult.failed > 0 && (
            <Card title="错误详情">
              <Alert
                message="导入错误"
                description={`共有 ${importResult.failed} 条记录导入失败，请修正以下错误后重新导入：`}
                type="error"
                showIcon
                style={{ marginBottom: '16px' }}
              />
              
              <Table
                columns={errorColumns}
                dataSource={errorData}
                pagination={false}
                size="small"
              />
            </Card>
          )}
        </div>
      )}
    </div>
  )
}

export default AssetImportPage