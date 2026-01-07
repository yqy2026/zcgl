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
import { assetService } from '../../services/assetService'
import { AssetForm } from '../../components/Forms'
import type { AssetCreateRequest, AssetUpdateRequest } from '../../types/asset'

// 错误类型接口
interface ApiError {
  response?: {
    data?: {
      message?: string
      detail?: string
    }
  }
  message?: string
}

const { Title } = Typography

// AssetFormData interface removed, using AssetCreateRequest from types/asset

const AssetCreatePage: React.FC = () => {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const _form = Form.useForm()

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
      navigate('/assets/list')
    },
    onError: (error: unknown) => {
      const apiError = error as ApiError
      message.error(apiError.response?.data?.detail || apiError.message || '创建失败')
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
    onError: (error: unknown) => {
      const apiError = error as ApiError
      message.error(apiError.response?.data?.detail || apiError.message || '更新失败')
    },
  })

  // 提交表单
  const handleSubmit = async (data: AssetCreateRequest) => {
    if (isEdit) {
      updateMutation.mutate(data as AssetUpdateRequest)
    } else {
      createMutation.mutate(data as AssetCreateRequest)
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
