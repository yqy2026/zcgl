import React from 'react';
import { Form } from 'antd';
import { MessageManager } from '@/utils/messageManager';
import { useParams, useNavigate } from 'react-router-dom';
import { PageContainer } from '@/components/Common';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { assetService } from '@/services/assetService';
import { AssetForm } from '@/components/Forms';
import type { AssetCreateRequest, AssetUpdateRequest } from '@/types/asset';

// 错误类型接口
interface ApiError {
  response?: {
    data?: {
      message?: string;
      detail?: string;
    };
  };
  message?: string;
}

// AssetFormData interface removed, using AssetCreateRequest from types/asset

const AssetCreatePage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const _form = Form.useForm();

  const isEdit = id != null;

  // 获取资产详情（编辑模式）
  const { data: asset, isLoading } = useQuery({
    queryKey: ['asset', id],
    queryFn: () => assetService.getAsset(id!),
    enabled: isEdit,
  });

  // 创建资产
  const createMutation = useMutation({
    mutationFn: (data: AssetCreateRequest) => assetService.createAsset(data),
    onSuccess: () => {
      MessageManager.success('资产创建成功');
      queryClient.invalidateQueries({ queryKey: ['assets'] });
      navigate('/assets/list');
    },
    onError: (error: unknown) => {
      const apiError = error as ApiError;
      MessageManager.error(apiError.response?.data?.detail ?? apiError.message ?? '创建失败');
    },
  });

  // 更新资产
  const updateMutation = useMutation({
    mutationFn: (data: AssetUpdateRequest) => assetService.updateAsset(id!, data),
    onSuccess: () => {
      MessageManager.success('资产更新成功');
      queryClient.invalidateQueries({ queryKey: ['assets'] });
      queryClient.invalidateQueries({ queryKey: ['asset', id] });
      navigate(`/assets/${id}`);
    },
    onError: (error: unknown) => {
      const apiError = error as ApiError;
      MessageManager.error(apiError.response?.data?.detail ?? apiError.message ?? '更新失败');
    },
  });

  // 提交表单
  const handleSubmit = async (data: AssetCreateRequest) => {
    if (isEdit) {
      updateMutation.mutate(data as AssetUpdateRequest);
    } else {
      createMutation.mutate(data);
    }
  };

  // 取消操作
  const handleCancel = () => {
    navigate(isEdit ? `/assets/${id}` : '/assets');
  };

  return (
    <PageContainer
      title={isEdit ? '编辑资产' : '新增资产'}
      loading={isEdit && isLoading}
      onBack={() => navigate(isEdit ? `/assets/${id}` : '/assets')}
    >
      <AssetForm
        initialData={asset}
        onSubmit={handleSubmit}
        onCancel={handleCancel}
        isLoading={createMutation.isPending || updateMutation.isPending}
        mode={isEdit ? 'edit' : 'create'}
      />
    </PageContainer>
  );
};

export default AssetCreatePage;
