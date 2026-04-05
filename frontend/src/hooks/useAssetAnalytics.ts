import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { analyticsService } from '@/services/analyticsService';
import { MessageManager } from '@/utils/messageManager';
import { createLogger } from '@/utils/logger';
import type { AssetSearchParams } from '@/types/asset';
import type { AnalyticsData } from '@/types/analytics';
import { buildQueryScopeKey } from '@/utils/queryScope';
import { useDataScopeStore } from '@/stores/dataScopeStore';

const logger = createLogger('useAssetAnalytics');

export type AnalysisDimension = 'count' | 'area';

const isAnalyticsResponse = (
  value: unknown
): value is { success: boolean; data: AnalyticsData } => {
  return value != null && typeof value === 'object' && 'success' in value && 'data' in value;
};

const isAnalyticsData = (value: unknown): value is AnalyticsData => {
  return value != null && typeof value === 'object' && 'area_summary' in value;
};

export const useAssetAnalytics = () => {
  const initialized = useDataScopeStore(state => state.initialized);
  const [filters, setFilters] = useState<AssetSearchParams>({});
  const [dimension, setDimension] = useState<AnalysisDimension>('area');
  const queryScopeKey = buildQueryScopeKey();

  // 获取分析数据
  const {
    data: analyticsResponse,
    isLoading,
    error,
    refetch,
  } = useQuery({
    queryKey: ['analytics', queryScopeKey, 'comprehensive', filters],
    queryFn: async () => {
      const result = await analyticsService.getComprehensiveAnalytics(filters);
      logger.debug('Analytics API Result:', { result });
      return result;
    },
    staleTime: 5 * 60 * 1000, // 5分钟缓存
    refetchOnWindowFocus: false,
    enabled: initialized,
  });

  // 解析数据
  let analyticsData: AnalyticsData | null = null;
  if (analyticsResponse) {
    if (isAnalyticsResponse(analyticsResponse)) {
      analyticsData = analyticsResponse.data;
    } else if (isAnalyticsData(analyticsResponse)) {
      analyticsData = analyticsResponse;
    } else {
      logger.warn('Unexpected analytics response format:', analyticsResponse);
    }
  }

  const handleFilterChange = (newFilters: AssetSearchParams) => {
    setFilters(newFilters);
  };

  const handleFilterReset = () => {
    setFilters({});
  };

  const handleDimensionChange = (newDimension: AnalysisDimension) => {
    setDimension(newDimension);
  };

  const handleExport = async () => {
    if (!analyticsData) return;

    try {
      MessageManager.loading('正在导出数据...', 0);
      await analyticsService.downloadAnalyticsReport('excel', {
        start_date: filters.start_date,
        end_date: filters.end_date,
        include_deleted: filters.include_deleted,
      });
      MessageManager.success('数据导出成功！');
    } catch (err) {
      logger.error('导出失败:', err as Error);
      MessageManager.error('导出失败，请重试');
    } finally {
      MessageManager.destroy();
    }
  };

  const hasData =
    analyticsData != null &&
    analyticsData.area_summary != null &&
    Number(analyticsData.area_summary.total_assets) > 0;

  return {
    analyticsData,
    loading: isLoading,
    error,
    refetch,
    filters,
    dimension,
    hasData,
    handleFilterChange,
    handleFilterReset,
    handleDimensionChange,
    handleExport,
  };
};
