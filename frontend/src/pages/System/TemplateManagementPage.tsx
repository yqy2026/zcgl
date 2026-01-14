import React, { useState } from 'react'
import { Card, Button, Table, Tag, Space, Typography, Row, Col, Modal, Tooltip } from 'antd'
import {
  DownloadOutlined,
  EyeOutlined,
  FileExcelOutlined,
  InfoCircleOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined
} from '@ant-design/icons'
import { MessageManager } from '@/utils/messageManager'
import { assetService } from '@/services/assetService'
import { rentContractExcelService } from '@/services/rentContractExcelService'
import type { ColumnsType } from 'antd/es/table'
import { createLogger } from '@/utils/logger'
import { COLORS } from '@/styles/colorMap'

const _pageLogger = createLogger('TemplateManagement')

const { Title, Text } = Typography

interface TemplateInfo {
  key: string
  name: string
  description: string
  type: 'asset' | 'rent-contract'
  version: string
  updateDate: string
  fileSize: string
  fields: string[]
  status: 'active' | 'draft' | 'deprecated'
}

const TemplateManagementPage: React.FC = () => {
  const [loading, setLoading] = useState(false)
  const [previewVisible, setPreviewVisible] = useState(false)
  const [previewTemplate, setPreviewTemplate] = useState<TemplateInfo | null>(null)

  // 模板数据
  const templates: TemplateInfo[] = [
    {
      key: 'asset-import',
      name: '资产导入模板',
      description: '用于批量导入资产数据的Excel模板，包含所有必要字段',
      type: 'asset',
      version: 'v2.0',
      updateDate: '2025-09-24',
      fileSize: '25KB',
      fields: ['权属方', '权属类别', '项目名称', '物业名称', '物业地址', '土地面积', '实际房产面积', '非经营物业面积', '可出租面积', '已出租面积', '确权状态', '证载用途', '实际用途', '业态类别', '使用状态', '是否涉诉', '物业性质', '是否计入出租率', '接收模式', '接收协议开始日期', '接收协议结束日期'],
      status: 'active'
    },
    {
      key: 'rent-contract-import',
      name: '租赁合同导入模板',
      description: '用于批量导入租赁合同信息的Excel模板',
      type: 'rent-contract',
      version: 'v1.0',
      updateDate: '2025-09-20',
      fileSize: '18KB',
      fields: ['合同编号', '资产名称', '承租方', '合同开始日期', '合同结束日期', '月租金', '押金', '付款方式', '合同状态'],
      status: 'active'
    }
  ]

  // 下载模板
  const handleDownloadTemplate = async (template: TemplateInfo) => {
    setLoading(true)
    try {
      if (template.type === 'asset') {
        await assetService.downloadImportTemplate()
        MessageManager.success('资产导入模板下载成功')
      } else if (template.type === 'rent-contract') {
        await rentContractExcelService.downloadTemplateFile()
        MessageManager.success('租赁合同导入模板下载成功')
      }
    } catch (error: unknown) {
      _pageLogger.error('下载模板失败:', error as Error)
      MessageManager.error(`下载模板失败: ${(error as Error).message || '网络错误'}`)
    } finally {
      setLoading(false)
    }
  }

  // 预览模板
  const handlePreviewTemplate = (template: TemplateInfo) => {
    setPreviewTemplate(template)
    setPreviewVisible(true)
  }

  // 获取状态标签
  const getStatusTag = (status: string) => {
    switch (status) {
      case 'active':
        return <Tag icon={<CheckCircleOutlined />} color="success">使用中</Tag>
      case 'draft':
        return <Tag icon={<ClockCircleOutlined />} color="warning">草稿</Tag>
      case 'deprecated':
        return <Tag color="error">已废弃</Tag>
      default:
        return <Tag>未知</Tag>
    }
  }

  // 表格列定义
  const columns: ColumnsType<TemplateInfo> = [
    {
      title: '模板名称',
      dataIndex: 'name',
      key: 'name',
      render: (text: string, record: TemplateInfo) => (
        <Space>
          <FileExcelOutlined style={{ color: COLORS.success }} />
          <span>
            {text}
            <Text type="secondary" style={{ marginLeft: 8, fontSize: '12px' }}>
              v{record.version}
            </Text>
          </span>
        </Space>
      )
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true
    },
    {
      title: '类型',
      dataIndex: 'type',
      key: 'type',
      render: (type: string) => (
        <Tag color={type === 'asset' ? 'blue' : 'purple'}>
          {type === 'asset' ? '资产导入' : '租赁合同'}
        </Tag>
      )
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => getStatusTag(status)
    },
    {
      title: '更新时间',
      dataIndex: 'updateDate',
      key: 'updateDate'
    },
    {
      title: '文件大小',
      dataIndex: 'fileSize',
      key: 'fileSize'
    },
    {
      title: '操作',
      key: 'action',
      render: (_, record: TemplateInfo) => (
        <Space>
          <Tooltip title="下载模板">
            <Button
              type="primary"
              size="small"
              icon={<DownloadOutlined />}
              onClick={() => handleDownloadTemplate(record)}
              loading={loading}
            >
              下载
            </Button>
          </Tooltip>
          <Tooltip title="查看详情">
            <Button
              size="small"
              icon={<EyeOutlined />}
              onClick={() => handlePreviewTemplate(record)}
            >
              预览
            </Button>
          </Tooltip>
        </Space>
      )
    }
  ]

  return (
    <div style={{ padding: '24px' }}>
      {/* 页面标题 */}
      <div style={{ marginBottom: '24px' }}>
        <Title level={2} style={{ margin: 0 }}>
          数据模板管理
        </Title>
        <Text type="secondary">
          管理和下载各种数据导入模板，确保数据导入的准确性和一致性
        </Text>
      </div>

      {/* 统计信息 */}
      <Row gutter={[16, 16]} style={{ marginBottom: '24px' }}>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="可用模板"
              value={templates.filter(t => t.status === 'active').length}
              suffix="个"
              valueStyle={{ color: COLORS.success }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="资产模板"
              value={templates.filter(t => t.type === 'asset').length}
              suffix="个"
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="合同模板"
              value={templates.filter(t => t.type === 'rent-contract').length}
              suffix="个"
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="总下载量"
              value={0}
              suffix="次"
            />
          </Card>
        </Col>
      </Row>

      {/* 使用说明 */}
      <Card
        title={
          <Space>
            <InfoCircleOutlined />
            使用说明
          </Space>
        }
        style={{ marginBottom: '24px' }}
      >
        <Row gutter={[16, 16]}>
          <Col xs={24} md={8}>
            <Card size="small" title="1. 下载模板">
              <Text>
                点击&quot;下载&quot;按钮获取对应的数据导入模板文件
              </Text>
            </Card>
          </Col>
          <Col xs={24} md={8}>
            <Card size="small" title="2. 填写数据">
              <Text>
                按照模板格式和字段要求填写您的数据
              </Text>
            </Card>
          </Col>
          <Col xs={24} md={8}>
            <Card size="small" title="3. 导入数据">
              <Text>
                在对应的导入页面上传填写完成的Excel文件
              </Text>
            </Card>
          </Col>
        </Row>
      </Card>

      {/* 模板列表 */}
      <Card>
        <Table
          columns={columns}
          dataSource={templates}
          rowKey="key"
          pagination={{
            showSizeChanger: true,
            showQuickJumper: true,
            showTotal: (total, range) =>
              `第 ${range[0]}-${range[1]} 条，共 ${total} 条`,
          }}
        />
      </Card>

      {/* 模板预览弹窗 */}
      <Modal
        title="模板详情"
        open={previewVisible}
        onCancel={() => setPreviewVisible(false)}
        footer={null}
        width={800}
      >
        {previewTemplate && (
          <div>
            <Row gutter={[16, 16]}>
              <Col span={12}>
                <Text strong>模板名称：</Text>
                <Text style={{ marginLeft: 8 }}>{previewTemplate.name}</Text>
              </Col>
              <Col span={12}>
                <Text strong>版本：</Text>
                <Text style={{ marginLeft: 8 }}>{previewTemplate.version}</Text>
              </Col>
              <Col span={12}>
                <Text strong>类型：</Text>
                <Tag color={previewTemplate.type === 'asset' ? 'blue' : 'purple'}>
                  {previewTemplate.type === 'asset' ? '资产导入' : '租赁合同'}
                </Tag>
              </Col>
              <Col span={12}>
                <Text strong>状态：</Text>
                {getStatusTag(previewTemplate.status)}
              </Col>
              <Col span={24}>
                <Text strong>描述：</Text>
                <Text style={{ marginLeft: 8 }}>{previewTemplate.description}</Text>
              </Col>
              <Col span={24}>
                <Text strong>包含字段：</Text>
                <div style={{ marginTop: 8, maxHeight: '200px', overflowY: 'auto' }}>
                  {previewTemplate.fields.map((field, index) => (
                    <Tag key={index} style={{ marginBottom: 4 }}>
                      {field}
                    </Tag>
                  ))}
                </div>
              </Col>
            </Row>
            <div style={{ marginTop: '16px', textAlign: 'center' }}>
              <Space>
                <Button
                  type="primary"
                  icon={<DownloadOutlined />}
                  onClick={() => {
                    handleDownloadTemplate(previewTemplate)
                    setPreviewVisible(false)
                  }}
                >
                  下载模板
                </Button>
                <Button onClick={() => setPreviewVisible(false)}>
                  关闭
                </Button>
              </Space>
            </div>
          </div>
        )}
      </Modal>
    </div>
  )
}

// 导入Statistic组件
const Statistic: React.FC<{
  title: string
  value: number
  suffix?: string
  valueStyle?: React.CSSProperties
}> = ({ title, value, suffix, valueStyle }) => (
  <div>
    <div style={{ color: COLORS.textSecondary, fontSize: '14px', marginBottom: '4px' }}>
      {title}
    </div>
    <div style={{
      fontSize: '24px',
      fontWeight: 'bold',
      color: COLORS.textPrimary,
      ...valueStyle
    }}>
      {value}
      {suffix != null && <span style={{ fontSize: '14px', marginLeft: '4px' }}>{suffix}</span>}
    </div>
  </div>
)

export default TemplateManagementPage
