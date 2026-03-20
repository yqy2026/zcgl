import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useView } from '@/contexts/ViewContext';
import { analyticsService } from '@/services/analyticsService';
import { exportAnalyticsData } from '@/services/analyticsExportService';
import { MessageManager } from '@/utils/messageManager';
import { createLogger } from '@/utils/logger';
import type { AssetSearchParams } from '@/types/asset';
import type { AnalyticsData } from '@/types/analytics';
import { buildQueryScopeKey } from '@/utils/queryScope';

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
  const { currentView } = useView();
  const [filters, setFilters] = useState<AssetSearchParams>({});
  const [dimension, setDimension] = useState<AnalysisDimension>('area');
  const queryScopeKey = buildQueryScopeKey(currentView);

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

      const exportData = {
        summary: {
          total_assets: analyticsData.area_summary.total_assets,
          total_area: analyticsData.area_summary.total_area,
          total_rentable_area: analyticsData.area_summary.total_rentable_area,
          occupancy_rate: analyticsData.area_summary.occupancy_rate,
          total_annual_income: analyticsData.financial_summary.total_annual_income,
          total_annual_expense: analyticsData.financial_summary.total_annual_expense,
          total_net_income: analyticsData.financial_summary.total_net_income,
          total_monthly_rent: analyticsData.financial_summary.total_monthly_rent,
          total_income: analyticsData.total_income ?? 0,
          self_operated_rent_income: analyticsData.self_operated_rent_income ?? 0,
          agency_service_income: analyticsData.agency_service_income ?? 0,
          customer_entity_count: analyticsData.customer_entity_count ?? 0,
          customer_contract_count: analyticsData.customer_contract_count ?? 0,
          metrics_version: analyticsData.metrics_version ?? '',
        },
        property_nature_distribution: analyticsData.property_nature_distribution ?? [],
        ownership_status_distribution: analyticsData.ownership_status_distribution ?? [],
        usage_status_distribution: analyticsData.usage_status_distribution ?? [],
        business_category_distribution: (analyticsData.business_category_distribution ?? []).map(
          item => ({
            category: item.category,
            count: item.count,
            occupancy_rate: item.occupancy_rate ?? 0,
          })
        ),
        occupancy_trend: (analyticsData.occupancy_trend ?? []).map(item => ({
          date: item.date,
          occupancy_rate: item.occupancy_rate,
          total_rented_area: 0,
          total_rentable_area: 0,
        })),
        property_nature_area_distribution: analyticsData.property_nature_area_distribution,
        ownership_status_area_distribution: analyticsData.ownership_status_area_distribution,
        usage_status_area_distribution: analyticsData.usage_status_area_distribution,
        business_category_area_distribution: analyticsData.business_category_area_distribution,
      };

      await exportAnalyticsData(exportData, 'excel');
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
