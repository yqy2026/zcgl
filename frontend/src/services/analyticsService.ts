import { apiClient } from '@/api/client';
import { STATISTICS_API } from '@/constants/api';
import { useDataScopeStore, type BindingType } from '@/stores/dataScopeStore';
import type { AssetSearchParams } from '@/types/asset';
import type { AnalyticsData, AnalyticsResponse } from '@/types/analytics';
import { convertBackendToFrontend } from '@/utils/dataConversion';
import { createLogger } from '@/utils/logger';

const serviceLogger = createLogger('analyticsService');

// Re-export the types for compatibility
export type { AnalyticsData, AnalyticsResponse };

// ==================== 类型定义 ====================

/**
 * 原始API响应数据结构
 */
interface RawApiData {
  area_summary?: RawAreaSummary;
  financial_summary?: RawFinancialSummary;
  total_income?: number;
  self_operated_rent_income?: number;
  agency_service_income?: number;
  actual_receipts?: number | null;
  collection_rate?: number | null;
  customer_entity_count?: number;
  customer_contract_count?: number;
  customer_entity_breakdown?: Record<string, number>;
  customer_contract_breakdown?: Record<string, number>;
  metrics_version?: string;
  property_nature_distribution?: unknown[];
  ownership_status_distribution?: unknown[];
  usage_status_distribution?: unknown[];
  business_category_distribution?: RawBusinessCategoryItem[];
  occupancy_trend?: unknown[];
  property_nature_area_distribution?: unknown[];
  ownership_status_area_distribution?: unknown[];
  usage_status_area_distribution?: unknown[];
  business_category_area_distribution?: unknown[];
  occupancy_distribution?: unknown[];
}

/**
 * 原始区域摘要
 */
interface RawAreaSummary {
  total_assets?: number;
  total_land_area?: number;
  total_area?: number;
  total_rentable_area?: number;
  total_rented_area?: number;
  total_unrented_area?: number;
  assets_with_area_data?: number;
  overall_occupancy_rate?: number;
  occupancy_rate?: number;
  total_non_commercial_area?: number;
}

/**
 * 原始财务摘要
 */
interface RawFinancialSummary {
  estimated_annual_income?: number;
  total_annual_income?: number;
  total_annual_expense?: number;
  total_net_income?: number;
  total_monthly_rent?: number;
  total_deposit?: number;
  assets_with_income_data?: number;
  assets_with_rent_data?: number;
  profit_margin?: number;
}

/**
 * 业务分类项
 */
interface RawBusinessCategoryItem {
  percentage?: number;
  [key: string]: unknown;
}

const toNumber = (value: unknown): number => {
  if (typeof value === 'number' && Number.isFinite(value)) {
    return value;
  }
  if (typeof value === 'string') {
    const parsed = Number(value);
    if (Number.isFinite(parsed)) {
      return parsed;
    }
  }
  return 0;
};

const toNullableNumber = (value: unknown): number | null => {
  if (value === null || value === undefined) {
    return null;
  }
  if (typeof value === 'number' && Number.isFinite(value)) {
    return value;
  }
  if (typeof value === 'string') {
    const parsed = Number(value);
    if (Number.isFinite(parsed)) {
      return parsed;
    }
  }
  return null;
};

export class AnalyticsService {
  private api = apiClient;

  private appendViewMode<T extends Record<string, unknown> | undefined>(
    params: T,
    viewMode?: BindingType | null
  ): (T & { view_mode?: BindingType }) | { view_mode?: BindingType } | undefined {
    const resolvedViewMode =
      viewMode === undefined ? useDataScopeStore.getState().getEffectiveViewMode() : viewMode;
    if (resolvedViewMode == null) {
      return params;
    }

    return {
      ...(params ?? {}),
      view_mode: resolvedViewMode,
    };
  }

  private buildExportFilename(format: 'excel' | 'pdf' | 'csv'): string {
    const timestamp = new Date().toISOString().slice(0, 19).replace(/[:-]/g, '');
    const extension = format === 'excel' ? 'xlsx' : format;
    return `analytics_${timestamp}.${extension}`;
  }

  private triggerBlobDownload(blob: Blob, filename: string): void {
    const url = window.URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = filename;
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    window.URL.revokeObjectURL(url);
  }

  async getComprehensiveAnalytics(
    filters?: AssetSearchParams,
    viewMode?: BindingType | null
  ): Promise<AnalyticsResponse> {
    try {
      const response = await this.api.get<AnalyticsResponse>('/analytics/comprehensive', {
        params: this.appendViewMode(filters, viewMode),
      });

      if (!response.success) {
        throw new Error(response.error ?? '获取综合分析数据失败');
      }

      if (!response.data) {
        throw new Error('综合分析接口返回为空');
      }

      const apiData = response.data as AnalyticsResponse | RawApiData;

      if ('success' in apiData && 'data' in apiData) {
        return apiData;
      }

      const adaptedData = this.adaptApiDataToAnalyticsData(apiData);
      return {
        success: true,
        message: '数据获取成功',
        data: adaptedData,
        cache_stats: { cache_size: 0, hits: 0, misses: 0, hit_rate: 0 },
        performance_info: {
          calculation_time: 0,
          asset_count: adaptedData.area_summary?.total_assets ?? 0,
          cache_enabled: true,
        },
      };
    } catch (error) {
      serviceLogger.error('Analytics API Error:', error as Error);
      throw error;
    }
  }

  /**
   * 将后端API返回的数据适配为前端期望的 AnalyticsData 格式
   */
  private adaptApiDataToAnalyticsData(apiData: RawApiData): AnalyticsData {
    serviceLogger.debug(
      'Adapting API data to AnalyticsData format:',
      apiData as Record<string, unknown>
    );

    // 从 API 数据中提取 area_summary
    const rawAreaSummary = convertBackendToFrontend<RawAreaSummary>(apiData.area_summary ?? {});

    // 适配 area_summary
    const area_summary: AnalyticsData['area_summary'] = {
      total_assets: rawAreaSummary.total_assets ?? 0,
      total_area: rawAreaSummary.total_land_area ?? rawAreaSummary.total_area ?? 0,
      total_rentable_area: rawAreaSummary.total_rentable_area ?? 0,
      total_rented_area: rawAreaSummary.total_rented_area ?? 0,
      total_unrented_area: rawAreaSummary.total_unrented_area ?? 0,
      assets_with_area_data: rawAreaSummary.assets_with_area_data ?? 0,
      occupancy_rate: rawAreaSummary.overall_occupancy_rate ?? rawAreaSummary.occupancy_rate ?? 0,
      total_non_commercial_area: rawAreaSummary.total_non_commercial_area ?? 0,
    };

    // 提取或生成 financial_summary（如果后端没有返回，使用空值）
    const rawFinancialSummary = convertBackendToFrontend<RawFinancialSummary>(
      apiData.financial_summary ?? {}
    );
    const financial_summary: AnalyticsData['financial_summary'] = {
      estimated_annual_income: rawFinancialSummary.estimated_annual_income ?? 0,
      total_annual_income: rawFinancialSummary.total_annual_income ?? 0,
      total_annual_expense: rawFinancialSummary.total_annual_expense ?? 0,
      total_net_income: rawFinancialSummary.total_net_income ?? 0,
      total_monthly_rent: rawFinancialSummary.total_monthly_rent ?? 0,
      total_deposit: rawFinancialSummary.total_deposit ?? 0,
      assets_with_income_data: rawFinancialSummary.assets_with_income_data ?? 0,
      assets_with_rent_data: rawFinancialSummary.assets_with_rent_data ?? 0,
      profit_margin: rawFinancialSummary.profit_margin ?? 0,
    };

    // 提取分布数据（如果不存在则使用空数组）
    const property_nature_distribution = (apiData.property_nature_distribution ??
      []) as AnalyticsData['property_nature_distribution'];
    const ownership_status_distribution = (apiData.ownership_status_distribution ??
      []) as AnalyticsData['ownership_status_distribution'];
    const usage_status_distribution = (apiData.usage_status_distribution ??
      []) as AnalyticsData['usage_status_distribution'];

    // BusinessCategoryDistribution 需要 percentage 字段
    const rawBusinessCategories = apiData.business_category_distribution ?? [];
    const business_category_distribution: AnalyticsData['business_category_distribution'] =
      rawBusinessCategories.map((item: RawBusinessCategoryItem) => ({
        category: typeof item.category === 'string' ? item.category : '未分类',
        count: toNumber(item.count),
        occupancy_rate: toNumber(item.occupancy_rate),
        avg_annual_income: toNumber(item.avg_annual_income),
      }));

    // 提取趋势数据
    const occupancy_trend = (apiData.occupancy_trend ?? []) as AnalyticsData['occupancy_trend'];

    // 提取面积分布数据
    const property_nature_area_distribution = (apiData.property_nature_area_distribution ??
      []) as AnalyticsData['property_nature_area_distribution'];
    const ownership_status_area_distribution = (apiData.ownership_status_area_distribution ??
      []) as AnalyticsData['ownership_status_area_distribution'];
    const usage_status_area_distribution = (apiData.usage_status_area_distribution ??
      []) as AnalyticsData['usage_status_area_distribution'];
    const business_category_area_distribution = (apiData.business_category_area_distribution ??
      []) as AnalyticsData['business_category_area_distribution'];

    // 提取出租率分布
    const occupancy_distribution = (apiData.occupancy_distribution ??
      []) as AnalyticsData['occupancy_distribution'];

    const adaptedData: AnalyticsData = {
      area_summary,
      financial_summary,
      total_income: toNumber(apiData.total_income),
      self_operated_rent_income: toNumber(apiData.self_operated_rent_income),
      agency_service_income: toNumber(apiData.agency_service_income),
      actual_receipts: toNumber(apiData.actual_receipts),
      collection_rate: toNullableNumber(apiData.collection_rate),
      customer_entity_count: toNumber(apiData.customer_entity_count),
      customer_contract_count: toNumber(apiData.customer_contract_count),
      customer_entity_breakdown:
        apiData.customer_entity_breakdown != null ? apiData.customer_entity_breakdown : undefined,
      customer_contract_breakdown:
        apiData.customer_contract_breakdown != null
          ? apiData.customer_contract_breakdown
          : undefined,
      metrics_version:
        typeof apiData.metrics_version === 'string' ? apiData.metrics_version : undefined,
      property_nature_distribution,
      ownership_status_distribution,
      usage_status_distribution,
      business_category_distribution,
      occupancy_trend,
      property_nature_area_distribution,
      ownership_status_area_distribution,
      usage_status_area_distribution,
      business_category_area_distribution,
      occupancy_distribution,
    };

    serviceLogger.debug('Adapted AnalyticsData:', { data: adaptedData });
    return adaptedData;
  }

  async getBasicStatistics(
    filters?: AssetSearchParams,
    viewMode?: BindingType | null
  ): Promise<AnalyticsResponse> {
    try {
      const response = await this.api.get<AnalyticsResponse>(STATISTICS_API.OVERVIEW, {
        params: this.appendViewMode(filters, viewMode),
      });

      if (response.success && response.data) {
        return response.data;
      }
      throw new Error(response.error ?? 'Failed to fetch basic statistics');
    } catch (error) {
      serviceLogger.error('Basic statistics API Error:', error as Error);
      throw error;
    }
  }

  async getAreaSummary(viewMode?: BindingType | null): Promise<AnalyticsResponse> {
    try {
      const response = await this.api.get<AnalyticsResponse>(STATISTICS_API.ASSET_SUMMARY, {
        params: this.appendViewMode(undefined, viewMode),
      });

      if (response.success && response.data) {
        return response.data;
      }
      throw new Error(response.error ?? 'Failed to fetch area summary');
    } catch (error) {
      serviceLogger.error('Area summary API Error:', error as Error);
      throw error;
    }
  }

  async getFinancialSummary(viewMode?: BindingType | null): Promise<AnalyticsResponse> {
    try {
      const response = await this.api.get<AnalyticsResponse>(STATISTICS_API.FINANCIAL_SUMMARY, {
        params: this.appendViewMode(undefined, viewMode),
      });

      if (response.success && response.data) {
        return response.data;
      }
      throw new Error(response.error ?? 'Failed to fetch financial summary');
    } catch (error) {
      serviceLogger.error('Financial summary API Error:', error as Error);
      throw error;
    }
  }

  async exportAnalyticsReport(
    format: 'excel' | 'pdf' | 'csv',
    filters?: Pick<AssetSearchParams, 'start_date' | 'end_date' | 'include_deleted'>,
    viewMode?: BindingType | null
  ): Promise<Blob> {
    try {
      const params: Record<string, string | boolean> = {
        export_format: format,
      };

      if (filters?.start_date != null && filters.start_date !== '') {
        params.date_from = filters.start_date;
      }
      if (filters?.end_date != null && filters.end_date !== '') {
        params.date_to = filters.end_date;
      }
      if (typeof filters?.include_deleted === 'boolean') {
        params.include_deleted = filters.include_deleted;
      }

      const response = await this.api.post<Blob>('/analytics/export', undefined, {
        params: this.appendViewMode(params, viewMode),
        responseType: 'blob',
        retry: false,
        smartExtract: false,
      });

      if (!response.success || response.data == null) {
        throw new Error(response.error ?? '导出失败');
      }

      return response.data;
    } catch (error) {
      serviceLogger.error('Analytics export API Error:', error as Error);
      throw error;
    }
  }

  async downloadAnalyticsReport(
    format: 'excel' | 'pdf' | 'csv',
    filters?: Pick<AssetSearchParams, 'start_date' | 'end_date' | 'include_deleted'>,
    viewMode?: BindingType | null
  ): Promise<void> {
    const blob = await this.exportAnalyticsReport(format, filters, viewMode);
    this.triggerBlobDownload(blob, this.buildExportFilename(format));
  }
}

export const analyticsService = new AnalyticsService();
