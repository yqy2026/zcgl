import React, { useState } from 'react'
import { Card, Typography, Space, Button, message, Divider } from 'antd'
import { PlayCircleOutlined, ReloadOutlined } from '@ant-design/icons'

import AssetForm from './AssetForm'
import type { AssetFormData } from '../../schemas/assetFormSchema'
import type { Asset, OwnershipStatus, UsageStatus, PropertyNature } from '../../types/asset'

const { Title, Paragraph } = Typography

// 模拟数据
const mockAssetData: Asset = {
  id: 'demo-asset-1',
  property_name: '示例商业大厦',
  ownership_entity: '示例集团有限公司',
  management_entity: '示例物业管理公司',
  address: '广东省广州市天河区珠江新城示例路123号',
  land_area: 5000,
  actual_property_area: 12000,
  rentable_area: 10000,
  rented_area: 8000,
  unrented_area: 2000,
  non_commercial_area: 2000,
  ownership_status: '已确权',
  certificated_usage: '商业',
  actual_usage: '办公、商业',
  business_category: '写字楼',
  usage_status: '出租',
  is_litigated: false,
  property_nature: '经营类',
  business_model: '整体出租',  // 接收模式
  include_in_occupancy_rate: true,
  occupancy_rate: '80.00%',
  lease_contract: 'HT-2024-001',
  current_contract_start_date: '2024-01-01',
  current_contract_end_date: '2026-12-31',
  tenant_name: '示例科技有限公司',
  ownership_category: '自有产权',
  current_lease_contract: 'ZL-2024-001',
  wuyang_project_name: '五羊新城项目',
  agreement_start_date: '2024-01-01',
  agreement_end_date: '2029-12-31',
  current_terminal_contract: 'ZD-2024-001',
  description: '位于珠江新城核心区域的高端商业大厦，交通便利，配套完善。',
  notes: '该物业为集团重点资产，需要重点关注出租情况和维护状态。',
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-15T10:30:00Z',
}

const AssetFormDemo: React.FC = () => {
  const [mode, setMode] = useState<'create' | 'edit'>('create')
  const [loading, setLoading] = useState(false)
  const [formKey, setFormKey] = useState(0) // 用于重置表单

  // 处理表单提交
  const handleSubmit = async (data: AssetFormData) => {
    setLoading(true)
    
    // 模拟API调用
    await new Promise(resolve => setTimeout(resolve, 2000))
    
    console.log('表单数据:', data)
    message.success(`${mode === 'create' ? '创建' : '更新'}成功！`)
    setLoading(false)
  }

  // 处理取消
  const handleCancel = () => {
    message.info('操作已取消')
  }

  // 重置演示
  const resetDemo = () => {
    setFormKey(prev => prev + 1)
    message.info('表单已重置')
  }

  return (
    <div style={{ padding: '24px', maxWidth: '1200px', margin: '0 auto' }}>
      {/* 演示说明 */}
      <Card style={{ marginBottom: '24px' }}>
        <Title level={2}>
          <PlayCircleOutlined style={{ color: '#1890ff', marginRight: '8px' }} />
          资产表单组件演示
        </Title>
        
        <Paragraph>
          这是一个功能完整的资产表单组件演示。该组件支持以下特性：
        </Paragraph>
        
        <ul>
          <li><strong>动态字段显示</strong>：根据物业性质和使用状态自动显示相关字段</li>
          <li><strong>智能计算</strong>：自动计算出租率和未出租面积</li>
          <li><strong>表单验证</strong>：使用Zod进行类型安全的数据验证</li>
          <li><strong>完成度跟踪</strong>：实时显示表单填写完成度</li>
          <li><strong>高级选项</strong>：可展开/收起高级字段</li>
          <li><strong>帮助系统</strong>：内置填写帮助和字段说明</li>
        </ul>

        <Divider />

        <Space>
          <Button 
            type={mode === 'create' ? 'primary' : 'default'}
            onClick={() => setMode('create')}
          >
            创建模式
          </Button>
          <Button 
            type={mode === 'edit' ? 'primary' : 'default'}
            onClick={() => setMode('edit')}
          >
            编辑模式
          </Button>
          <Button 
            icon={<ReloadOutlined />}
            onClick={resetDemo}
          >
            重置演示
          </Button>
        </Space>
      </Card>

      {/* 表单演示 */}
      <Card title={`${mode === 'create' ? '新增' : '编辑'}资产表单`}>
        <AssetForm
          key={formKey}
          initialData={mode === 'edit' ? mockAssetData : undefined}
          onSubmit={handleSubmit}
          onCancel={handleCancel}
          loading={loading}
          mode={mode}
        />
      </Card>

      {/* 功能说明 */}
      <Card title="功能说明" style={{ marginTop: '24px' }}>
        <Title level={4}>动态字段显示规则</Title>
        <ul>
          <li>选择"经营类"物业性质时，显示出租相关字段（可出租面积、已出租面积等）</li>
          <li>选择"非经营类"物业性质时，显示非经营物业面积字段</li>
          <li>选择"出租"使用状态时，显示租户和合同相关字段</li>
          <li>填写业态类别时，显示接收模式字段</li>
          <li>填写五羊项目名称时，显示接收协议日期字段</li>
        </ul>

        <Title level={4}>智能计算功能</Title>
        <ul>
          <li>根据已出租面积和可出租面积自动计算出租率</li>
          <li>根据可出租面积和已出租面积自动计算未出租面积</li>
          <li>实时更新表单完成度百分比</li>
        </ul>

        <Title level={4}>数据验证规则</Title>
        <ul>
          <li>必填字段：物业名称、权属方、所在地址、确权状态、物业性质、使用状态</li>
          <li>面积字段必须为非负数</li>
          <li>已出租面积不能大于可出租面积</li>
          <li>合同结束日期必须晚于开始日期</li>
          <li>接收协议结束日期必须晚于开始日期</li>
          <li>各字段都有相应的字符长度限制</li>
        </ul>
      </Card>
    </div>
  )
}

export default AssetFormDemo