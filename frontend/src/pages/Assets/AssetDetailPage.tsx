import React from 'react';
import { Button, Alert } from 'antd';
import { EditOutlined } from '@ant-design/icons';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { assetService } from '@/services/assetService';
import AssetDetailInfo from '@/components/Asset/AssetDetailInfo';
import { PageContainer } from '@/components/Common';

const AssetDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const {
    data: asset,
    isLoading,
    error,
  } = useQuery({
    queryKey: ['asset', id],
    queryFn: () => assetService.getAsset(id as string),
    enabled: id !== null && id !== undefined && id !== '',
  });

  if (error) {
    return (
      <PageContainer title="资产详情" onBack={() => navigate('/assets')}>
        <Alert
          title="数据加载失败"
          description={`错误详情: ${error instanceof Error ? error.message : '未知错误'}`}
          type="error"
          showIcon
        />
      </PageContainer>
    );
  }

  if (!isLoading && !asset) {
    return (
      <PageContainer title="资产详情" onBack={() => navigate('/assets')}>
        <Alert title="资产不存在" description="未找到指定的资产信息" type="warning" showIcon />
      </PageContainer>
    );
  }

  return (
    <PageContainer
      title={asset?.property_name ?? '资产详情'}
      loading={isLoading}
      onBack={() => navigate('/assets')}
      extra={
        <Button
          type="primary"
          icon={<EditOutlined />}
          onClick={() => navigate(`/assets/${id}/edit`)}
          disabled={isLoading}
        >
          编辑资产
        </Button>
      }
    >
      {asset && <AssetDetailInfo asset={asset} />}
    </PageContainer>
  );
};

export default AssetDetailPage;
