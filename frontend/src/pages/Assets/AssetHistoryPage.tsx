import React from 'react';
import { Button, Empty } from 'antd';
import { useNavigate, useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { assetService } from '@/services/assetService';
import AssetHistory from '@/components/Asset/AssetHistory';
import { PageContainer } from '@/components/Common';
import { ASSET_ROUTES } from '@/constants/routes';
import { buildQueryScopeKey } from '@/utils/queryScope';

/**
 * 资产变更历史页面
 * 由资产列表"查看历史记录"入口导航至 /assets/:id/history。
 * 复用自包含的 AssetHistory 组件（筛选/分页/详情模态）。
 */
const AssetHistoryPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryScopeKey = buildQueryScopeKey();
  const hasAssetId = id != null && id !== '';

  const { data: asset } = useQuery({
    queryKey: ['asset', queryScopeKey, id],
    queryFn: () => assetService.getAsset(id as string),
    enabled: hasAssetId,
  });

  return (
    <PageContainer
      title={asset?.asset_name != null ? `${asset.asset_name} - 变更历史` : '资产变更历史'}
      onBack={() => navigate(ASSET_ROUTES.LIST)}
      extra={
        asset ? (
          <Button type="primary" onClick={() => navigate(ASSET_ROUTES.DETAIL(id as string))}>
            返回资产详情
          </Button>
        ) : null
      }
    >
      {hasAssetId ? <AssetHistory assetId={id as string} /> : <Empty description="缺少资产 ID" />}
    </PageContainer>
  );
};

export default AssetHistoryPage;
