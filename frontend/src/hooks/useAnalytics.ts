import { useQuery } from '@tanstack/react-query';
import { useView } from '@/contexts/ViewContext';
import { analyticsService } from '@/services/analyticsService';
import type { AssetSearchParams } from '@/types/asset';
import type { AnalyticsResponse } from '@/types/analytics';
import { buildQueryScopeKey } from '@/utils/queryScope';

export const useAnalytics = (filters?: AssetSearchParams) => {
  const { currentView } = useView();
  const queryScopeKey = buildQueryScopeKey(currentView);

  return useQuery<AnalyticsResponse>({
    queryKey: ['analytics', queryScopeKey, 'comprehensive', filters],
    queryFn: async (): Promise<AnalyticsResponse> => {
      const result = await analyticsService.getComprehensiveAnalytics(filters);
      return result;
    },
    staleTime: 5 * 60 * 1000, // 5分钟缓存
    gcTime: 10 * 60 * 1000, // 10分钟缓存
    retry: 2, // 失败时重试2次
    retryDelay: 1000,
    refetchOnWindowFocus: false, // 禁用自动刷新避免循环请求
    refetchOnMount: true,
    // 添加依赖项数组，确保filters变化时重新请求
    enabled: true,
  });
};

export const useBasicStatistics = (filters?: AssetSearchParams) => {
  const { currentView } = useView();
  const queryScopeKey = buildQueryScopeKey(currentView);

  return useQuery<AnalyticsResponse>({
    queryKey: ['analytics', queryScopeKey, 'basic-statistics', filters],
    queryFn: () => analyticsService.getBasicStatistics(filters),
    staleTime: 2 * 60 * 1000, // 2分钟缓存
    gcTime: 5 * 60 * 1000, // 5分钟缓存
  });
};

export const useAreaSummary = () => {
  const { currentView } = useView();
  const queryScopeKey = buildQueryScopeKey(currentView);

  return useQuery<AnalyticsResponse>({
    queryKey: ['analytics', queryScopeKey, 'area-summary'],
    queryFn: () => analyticsService.getAreaSummary(),
    staleTime: 3 * 60 * 1000, // 3分钟缓存
    gcTime: 6 * 60 * 1000, // 6分钟缓存
  });
};

export const useFinancialSummary = () => {
  const { currentView } = useView();
  const queryScopeKey = buildQueryScopeKey(currentView);

  return useQuery<AnalyticsResponse>({
    queryKey: ['analytics', queryScopeKey, 'financial-summary'],
    queryFn: () => analyticsService.getFinancialSummary(),
    staleTime: 3 * 60 * 1000, // 3分钟缓存
    gcTime: 6 * 60 * 1000, // 6分钟缓存
  });
};
