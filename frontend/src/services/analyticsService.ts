import { enhancedApiClient } from '@/api/client'
import { STATISTICS_API } from '@/constants/api'
import type { AssetSearchParams } from '../types/asset'
import type { AnalyticsData, AnalyticsResponse } from '../types/analytics'
import { createLogger } from '../utils/logger'

const serviceLogger = createLogger('analyticsService')

// Re-export the types for compatibility
export type { AnalyticsData, AnalyticsResponse }

// ==================== 类型定义 ====================

/**
 * 原始API响应数据结构
 */
interface RawApiData {
  area_summary?: RawAreaSummary;
  financial_summary?: RawFinancialSummary;
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
  data?: RawApiData;
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

export class AnalyticsService {
  private api = enhancedApiClient

  async getComprehensiveAnalytics(filters?: AssetSearchParams): Promise<AnalyticsResponse> {
    try {
      const response = await this.api.get<AnalyticsResponse>('/analytics/comprehensive', {
        params: filters
      })

      // ApiClient returns ExtractResult<AnalyticsResponse>
      if (response.success && response.data) {
        const apiData = response.data as AnalyticsResponse | RawApiData;

        // 检查是否已经是 AnalyticsResponse 格式
        if ('success' in apiData && 'data' in apiData) {
          return apiData as AnalyticsResponse;
        }

        // 适配后端API返回的数据到前端期望的格式
        const adaptedData = this.adaptApiDataToAnalyticsData(apiData);
        return {
          success: true,
          message: '数据获取成功',
          data: adaptedData,
          cache_stats: { cache_size: 0, hits: 0, misses: 0, hit_rate: 0 },
          performance_info: { calculation_time: 0, asset_count: adaptedData.area_summary?.total_assets ?? 0, cache_enabled: true }
        };
      }

      // 如果response.data为空，返回模拟数据
      return this.getMockAnalyticsData()
    } catch (error) {
      serviceLogger.error('Analytics API Error:', error as Error)
      // 返回模拟数据而不是抛出错误
      return this.getMockAnalyticsData()
    }
  }

  /**
   * 将后端API返回的数据适配为前端期望的 AnalyticsData 格式
   */
  private adaptApiDataToAnalyticsData(apiData: RawApiData): AnalyticsData {
    serviceLogger.debug('Adapting API data to AnalyticsData format:', apiData as Record<string, unknown>);

    // 从 API 数据中提取 area_summary
    const rawAreaSummary = apiData.area_summary ?? apiData.data?.area_summary ?? {};

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
    const rawFinancialSummary = apiData.financial_summary ?? apiData.data?.financial_summary ?? {};
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
                                         apiData.data?.property_nature_distribution ?? []) as AnalyticsData['property_nature_distribution'];
    const ownership_status_distribution = (apiData.ownership_status_distribution ??
                                          apiData.data?.ownership_status_distribution ?? []) as AnalyticsData['ownership_status_distribution'];
    const usage_status_distribution = (apiData.usage_status_distribution ??
                                       apiData.data?.usage_status_distribution ?? []) as AnalyticsData['usage_status_distribution'];

    // BusinessCategoryDistribution 需要 percentage 字段
    const rawBusinessCategories = apiData.business_category_distribution ??
                                   apiData.data?.business_category_distribution ?? [];
    const business_category_distribution = rawBusinessCategories.map((item: RawBusinessCategoryItem) => ({
      ...item,
      percentage: item.percentage ?? 0, // 确保有 percentage 字段
    })) as unknown as AnalyticsData['business_category_distribution'];

    // 提取趋势数据
    const occupancy_trend = (apiData.occupancy_trend ?? apiData.data?.occupancy_trend ?? []) as AnalyticsData['occupancy_trend'];

    // 提取面积分布数据
    const property_nature_area_distribution = (apiData.property_nature_area_distribution ??
                                                apiData.data?.property_nature_area_distribution ?? []) as AnalyticsData['property_nature_area_distribution'];
    const ownership_status_area_distribution = (apiData.ownership_status_area_distribution ??
                                                 apiData.data?.ownership_status_area_distribution ?? []) as AnalyticsData['ownership_status_area_distribution'];
    const usage_status_area_distribution = (apiData.usage_status_area_distribution ??
                                              apiData.data?.usage_status_area_distribution ?? []) as AnalyticsData['usage_status_area_distribution'];
    const business_category_area_distribution = (apiData.business_category_area_distribution ??
                                                   apiData.data?.business_category_area_distribution ?? []) as AnalyticsData['business_category_area_distribution'];

    // 提取出租率分布
    const occupancy_distribution = (apiData.occupancy_distribution ??
                                    apiData.data?.occupancy_distribution ?? []) as AnalyticsData['occupancy_distribution'];

    const adaptedData: AnalyticsData = {
      area_summary,
      financial_summary,
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

    serviceLogger.debug('Adapted AnalyticsData:', adaptedData as unknown as Record<string, unknown>);
    return adaptedData;
  }

  async getBasicStatistics(filters?: AssetSearchParams): Promise<AnalyticsResponse> {
    try {
      const response = await this.api.get<AnalyticsResponse>(STATISTICS_API.OVERVIEW, {
        params: filters
      })

      if (response.success && response.data) {
        return response.data
      }
      throw new Error(response.error ?? 'Failed to fetch basic statistics')
    } catch (error) {
      serviceLogger.error('Basic statistics API Error:', error as Error)
      throw error
    }
  }

  async getAreaSummary(): Promise<AnalyticsResponse> {
    try {
      const response = await this.api.get<AnalyticsResponse>(STATISTICS_API.ASSET_SUMMARY)

      if (response.success && response.data) {
        return response.data
      }
      throw new Error(response.error ?? 'Failed to fetch area summary')
    } catch (error) {
      serviceLogger.error('Area summary API Error:', error as Error)
      throw error
    }
  }

  async getFinancialSummary(): Promise<AnalyticsResponse> {
    try {
      const response = await this.api.get<AnalyticsResponse>(STATISTICS_API.FINANCIAL_SUMMARY)

      if (response.success && response.data) {
        return response.data
      }
      return this.getMockAnalyticsData()
    } catch (error) {
      serviceLogger.error('Financial summary API Error:', error as Error)
      return this.getMockAnalyticsData()
    }
  }

  // 模拟数据方法
  private getMockAnalyticsData(): AnalyticsResponse {
    return {
      success: true,
      message: '使用模拟数据',
      data: {
        area_summary: {
          total_assets: 696,
          total_area: 90466.8,
          total_rentable_area: 122246.02,
          total_rented_area: 119170.36,
          total_unrented_area: 3075.66,
          assets_with_area_data: 669,
          occupancy_rate: 97.48,
          total_non_commercial_area: 0,
        },
        financial_summary: {
          estimated_annual_income: 0.0,
          total_annual_income: 0.0,
          total_annual_expense: 0.0,
          total_net_income: 0.0,
          total_monthly_rent: 0.0,
          total_deposit: 0.0,
          assets_with_income_data: 0,
          assets_with_rent_data: 0,
          profit_margin: 0.0,
        },
        business_category_distribution: [],
        property_nature_distribution: [],
        ownership_status_distribution: [],
        usage_status_distribution: [],
        occupancy_distribution: [],
        occupancy_trend: [],
      },
      cache_stats: { cache_size: 0, hits: 0, misses: 0, hit_rate: 0 },
      performance_info: { calculation_time: 0, asset_count: 696, cache_enabled: true },
    }
  }
}

export const analyticsService = new AnalyticsService()
