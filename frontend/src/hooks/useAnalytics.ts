import { useQuery } from '@tanstack/react-query';
import { analyticsService } from '@/services/analyticsService';
import type { AssetSearchParams } from '@/types/asset';
import type { AnalyticsResponse } from '@/types/analytics';
import { buildQueryScopeKey } from '@/utils/queryScope';
import { useDataScopeStore } from '@/stores/dataScopeStore';

export const useAnalytics = (filters?: AssetSearchParams) => {
  const initialized = useDataScopeStore(state => state.initialized);
  const currentViewMode = useDataScopeStore(state => state.getEffectiveViewMode());
  const queryScopeKey = buildQueryScopeKey();

  return useQuery<AnalyticsResponse>({
    queryKey: ['analytics', queryScopeKey, currentViewMode, 'comprehensive', filters],
    queryFn: async (): Promise<AnalyticsResponse> => {
      const result = await analyticsService.getComprehensiveAnalytics(filters, currentViewMode);
      return result;
    },
    staleTime: 5 * 60 * 1000, // 5分钟缓存
    gcTime: 10 * 60 * 1000, // 10分钟缓存
    retry: 2, // 失败时重试2次
    retryDelay: 1000,
    refetchOnWindowFocus: false, // 禁用自动刷新避免循环请求
    refetchOnMount: true,
    enabled: initialized,
    // 添加依赖项数组，确保filters变化时重新请求
  });
};

export const useBasicStatistics = (filters?: AssetSearchParams) => {
  const currentViewMode = useDataScopeStore(state => state.getEffectiveViewMode());
  const queryScopeKey = buildQueryScopeKey();

  return useQuery<AnalyticsResponse>({
    queryKey: ['analytics', queryScopeKey, currentViewMode, 'basic-statistics', filters],
    queryFn: () => analyticsService.getBasicStatistics(filters, currentViewMode),
    staleTime: 2 * 60 * 1000, // 2分钟缓存
    gcTime: 5 * 60 * 1000, // 5分钟缓存
  });
};

export const useAreaSummary = () => {
  const currentViewMode = useDataScopeStore(state => state.getEffectiveViewMode());
  const queryScopeKey = buildQueryScopeKey();

  return useQuery<AnalyticsResponse>({
    queryKey: ['analytics', queryScopeKey, currentViewMode, 'area-summary'],
    queryFn: () => analyticsService.getAreaSummary(currentViewMode),
    staleTime: 3 * 60 * 1000, // 3分钟缓存
    gcTime: 6 * 60 * 1000, // 6分钟缓存
  });
};

export const useFinancialSummary = () => {
  const currentViewMode = useDataScopeStore(state => state.getEffectiveViewMode());
  const queryScopeKey = buildQueryScopeKey();

  return useQuery<AnalyticsResponse>({
    queryKey: ['analytics', queryScopeKey, currentViewMode, 'financial-summary'],
    queryFn: () => analyticsService.getFinancialSummary(currentViewMode),
    staleTime: 3 * 60 * 1000, // 3分钟缓存
    gcTime: 6 * 60 * 1000, // 6分钟缓存
  });
};
