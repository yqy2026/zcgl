import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';

import { assetService } from '@/services/assetService';
import { MessageManager } from '@/utils/messageManager';
import type { AssetSearchParams, AssetCreateRequest, AssetUpdateRequest } from '@/types/asset';
import type { AssetSearchFilters } from '@/services/asset/types';

/**
 * 资产列表查询 Hook
 *
 * 注意: 服务器数据由 React Query 管理缓存，不再复制到 Zustand。
 * Zustand 仅用于 UI 状态（selectedAsset、searchParams 等）。
 */
export const useAssets = (params?: AssetSearchParams) => {
  return useQuery({
    queryKey: ['assets', params],
    queryFn: () => assetService.getAssets(params),
    placeholderData: previousData => previousData,
    staleTime: 30 * 1000, // 30秒内不重新请求
  });
};

/**
 * 单个资产查询 Hook
 */
export const useAsset = (id: string) => {
  return useQuery({
    queryKey: ['asset', id],
    queryFn: () => assetService.getAsset(id),
    enabled: !!id,
  });
};

/**
 * 创建资产 Hook
 */
export const useCreateAsset = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: AssetCreateRequest) => assetService.createAsset(data),
    onSuccess: () => {
      // 使响应缓存失效，触发重新查询
      queryClient.invalidateQueries({ queryKey: ['assets'] });
      MessageManager.success('资产创建成功');
    },
    onError: (error: { message: string }) => {
      MessageManager.error(`创建失败: ${error.message}`);
    },
  });
};

/**
 * 更新资产 Hook
 */
export const useUpdateAsset = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: AssetUpdateRequest }) =>
      assetService.updateAsset(id, data),
    onSuccess: asset => {
      // 使响应缓存失效，触发重新查询
      queryClient.invalidateQueries({ queryKey: ['assets'] });
      queryClient.invalidateQueries({ queryKey: ['asset', asset.id] });
      MessageManager.success('资产更新成功');
    },
    onError: (error: { message: string }) => {
      MessageManager.error(`更新失败: ${error.message}`);
    },
  });
};

/**
 * 删除资产 Hook
 */
export const useDeleteAsset = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => assetService.deleteAsset(id),
    onSuccess: () => {
      // 使响应缓存失效，触发重新查询
      queryClient.invalidateQueries({ queryKey: ['assets'] });
      MessageManager.success('资产删除成功');
    },
    onError: (error: { message: string }) => {
      MessageManager.error(`删除失败: ${error.message}`);
    },
  });
};

/**
 * 批量删除资产 Hook
 */
export const useBatchDeleteAssets = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (ids: string[]) => assetService.deleteAssets(ids),
    onSuccess: (_, ids) => {
      // 更新缓存
      queryClient.invalidateQueries({ queryKey: ['assets'] });

      MessageManager.success(`成功删除 ${ids.length} 个资产`);
    },
    onError: (error: { message: string }) => {
      MessageManager.error(`批量删除失败: ${error.message}`);
    },
  });
};

/**
 * 资产历史查询 Hook
 */
export const useAssetHistory = (assetId: string, page = 1, pageSize = 20, changeType?: string) => {
  return useQuery({
    queryKey: ['asset-history', assetId, page, pageSize, changeType],
    queryFn: () => assetService.getAssetHistory(assetId, page, pageSize, changeType),
    enabled: !!assetId,
  });
};

/**
 * 资产统计 Hook
 */
export const useAssetStats = (filters?: AssetSearchParams) => {
  return useQuery({
    queryKey: ['asset-stats', filters],
    queryFn: () => assetService.getAssetStats(filters),
    staleTime: 5 * 60 * 1000, // 5分钟缓存
  });
};

/**
 * 权属方列表 Hook
 */
export const useOwnershipEntities = () => {
  return useQuery({
    queryKey: ['ownership-entities'],
    queryFn: () => assetService.getOwnershipEntities(),
    staleTime: 10 * 60 * 1000, // 10分钟缓存
  });
};

/**
 * 管理方列表 Hook
 */
export const useManagementEntities = () => {
  return useQuery({
    queryKey: ['management-entities'],
    queryFn: () => assetService.getManagementEntities(),
    staleTime: 10 * 60 * 1000, // 10分钟缓存
  });
};

/**
 * 业态类别列表 Hook
 */
export const useBusinessCategories = () => {
  return useQuery({
    queryKey: ['business-categories'],
    queryFn: () => assetService.getBusinessCategories(),
    staleTime: 10 * 60 * 1000, // 10分钟缓存
  });
};

/**
 * 资产搜索 Hook
 */
export const useAssetSearch = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ query, filters }: { query: string; filters?: AssetSearchFilters }) =>
      assetService.searchAssets(query, filters),
    onSuccess: result => {
      // 可以选择性地更新缓存
      queryClient.setQueryData(['assets', { search: result }], result);
    },
  });
};

/**
 * 资产验证 Hook
 */
export const useValidateAsset = () => {
  return useMutation({
    mutationFn: (data: AssetCreateRequest | AssetUpdateRequest) => assetService.validateAsset(data),
  });
};
