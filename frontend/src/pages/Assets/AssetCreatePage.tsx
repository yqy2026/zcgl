import React from 'react'
import { 
  Typography, 
  Button,
  Space,
  message,
  Spin,
  Form
} from 'antd'
import { ArrowLeftOutlined } from '@ant-design/icons'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { assetService } from '@/services/assetService'
import AssetForm from '@/components/Asset/AssetForm'
import type { AssetCreateRequest, AssetUpdateRequest } from '@/types/asset'

const { Title } = Typography

interface AssetFormData {
  property_name: string
  address: string
  ownership_status: string
  property_nature: string
  usage_status: string
  ownership_entity: string
  management_entity?: string
  business_category?: string
  
  // 面积相关字段
  total_area?: number
  usable_area?: number
  land_area?: number
  total_building_area?: number
  actual_property_area?: number
  rentable_area?: number
  rented_area?: number
  unrented_area?: number
  non_commercial_area?: number
  occupancy_rate?: number
  include_in_occupancy_rate?: boolean
  
  // 用途相关字段
  certificated_usage?: string
  actual_usage?: string
  
  // 租户相关字段
  tenant_name?: string
  tenant_contact?: string
  tenant_type?: string
  
  // 合同相关字段
  lease_contract_number?: string
  contract_start_date?: string
  contract_end_date?: string
  contract_status?: string
  monthly_rent?: number
  deposit?: number
  is_sublease?: boolean
  sublease_notes?: string
  
  // 管理相关字段
  manager_name?: string
  business_model?: string
  operation_status?: string
  
  // 财务相关字段
  annual_income?: number
  annual_expense?: number
  net_income?: number
  
  // 协议相关字段
  operation_agreement_start_date?: string
  operation_agreement_end_date?: string
  operation_agreement_attachments?: string
  
  // 项目相关字段
  project_name?: string
  project_short_name?: string
  ownership_category?: string
  
  // 系统字段
  data_status?: string
  created_by?: string
  updated_by?: string
  version?: number
  tags?: string
  
  // 审核相关字段
  last_audit_date?: string
  audit_status?: string
  auditor?: string
  audit_notes?: string
  
  // 其他字段
  is_litigated?: boolean
  notes?: string
  
  // 多租户支持
  tenant_id?: string
}

const AssetCreatePage: React.FC = () => {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [form] = Form.useForm()
  
  const isEdit = !!id

  // 获取资产详情（编辑模式）
  const { data: asset, isLoading } = useQuery({
    queryKey: ['asset', id],
    queryFn: () => assetService.getAsset(id!),
    enabled: isEdit,
  })

  // 创建资产
  const createMutation = useMutation({
    mutationFn: (data: AssetCreateRequest) => assetService.createAsset(data),
    onSuccess: () => {
      message.success('资产创建成功')
      queryClient.invalidateQueries({ queryKey: ['assets'] })
      navigate('/assets')
    },
    onError: (error: any) => {
      message.error(error.message || '创建失败')
    },
  })

  // 更新资产
  const updateMutation = useMutation({
    mutationFn: (data: AssetUpdateRequest) => assetService.updateAsset(id!, data),
    onSuccess: () => {
      message.success('资产更新成功')
      queryClient.invalidateQueries({ queryKey: ['assets'] })
      queryClient.invalidateQueries({ queryKey: ['asset', id] })
      navigate(`/assets/${id}`)
    },
    onError: (error: any) => {
      message.error(error.message || '更新失败')
    },
  })

  // 提交表单
  const handleSubmit = async (data: AssetFormData) => {
    try {
      if (isEdit) {
        updateMutation.mutate(data as AssetUpdateRequest)
      } else {
        createMutation.mutate(data as AssetCreateRequest)
      }
    } catch (error) {
      console.error('Submit error:', error)
    }
  }

  // 取消操作
  const handleCancel = () => {
    navigate(isEdit ? `/assets/${id}` : '/assets')
  }

  if (isEdit && isLoading) {
    return (
      <div style={{ padding: '24px', textAlign: 'center' }}>
        <Spin size="large" />
        <div style={{ marginTop: '16px' }}>加载资产信息中...</div>
      </div>
    )
  }

  return (
    <div style={{ padding: '24px' }}>
      <div style={{ marginBottom: '24px' }}>
        <Space>
          <Button 
            icon={<ArrowLeftOutlined />} 
            onClick={() => navigate(isEdit ? `/assets/${id}` : '/assets')}
          >
            返回
          </Button>
          <Title level={2} style={{ margin: 0 }}>
            {isEdit ? '编辑资产' : '新增资产'}
          </Title>
        </Space>
      </div>

      <AssetForm
        initialData={asset}
        onSubmit={handleSubmit}
        onCancel={handleCancel}
        loading={createMutation.isPending || updateMutation.isPending}
        mode={isEdit ? 'edit' : 'create'}
      />
    </div>
  )
}

export default AssetCreatePage