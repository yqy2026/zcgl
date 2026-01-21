/**
 * 统计服务 - 统一响应处理版本
 *
 * @description 数据统计和分析核心服务，提供仪表板、图表数据、趋势分析等功能
 * @author Claude Code
 */

import { apiClient } from '@/api/client';
import { ApiErrorHandler } from '../utils/responseExtractor';
import { createLogger } from '../utils/logger';
import type { DashboardData, ChartDataItem } from '@/types/api';
import type { Filters } from '@/types/common';

const logger = createLogger('StatisticsService');

// 基础统计信息接口
export interface BasicStatistics {
  totalAssets: number;
  totalArea: number;
  totalRentableArea: number;
  totalRentedArea: number;
  averageOccupancyRate: number;
  categoryCount: Record<string, number>;
  regionCount: Record<string, number>;
}

// 面积统计接口
export interface AreaStatistics {
  landArea: number;
  totalPropertyArea: number;
  totalRentableArea: number;
  totalRentedArea: number;
  vacantArea: number;
  averageUnitPrice: number;
  regionStats: Record<
    string,
    {
      area: number;
      rentableArea: number;
      rentedArea: number;
    }
  >;
}

// 趋势数据接口
export interface TrendDataItem {
  date: string;
  value: number;
  label?: string;
  category?: string;
}

// 报表生成响应接口
export interface ReportGenerationResponse {
  reportId: string;
  status: 'queued' | 'processing' | 'completed' | 'failed';
  downloadUrl?: string;
  message?: string;
}

// 对比数据接口
export interface ComparisonData {
  categories: string[];
  series: Array<{
    name: string;
    data: number[];
  }>;
  summary?: Record<string, unknown>;
}

export class StatisticsService {
  // ==================== 仪表板数�?====================

  /**
   * 获取仪表板数�?   */
  async getDashboardData(): Promise<DashboardData> {
    try {
      const result = await apiClient.get<DashboardData>('/statistics/dashboard', {
        cache: true,
        retry: { maxAttempts: 3, delay: 1000, backoffMultiplier: 2 },
        smartExtract: true,
      });

      if (!result.success) {
        throw new Error(`获取仪表板数据失�? ${result.error}`);
      }

      return result.data!;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  // ==================== 基础统计 ====================

  /**
   * 获取基础统计信息
   */
  async getBasicStatistics(filters?: Filters): Promise<BasicStatistics> {
    try {
      const result = await apiClient.get<BasicStatistics>('/statistics/basic', {
        params: filters,
        cache: true,
        retry: { maxAttempts: 3, delay: 1000, backoffMultiplier: 2 },
        smartExtract: true,
      });

      if (!result.success) {
        throw new Error(`获取基础统计信息失败: ${result.error}`);
      }

      return result.data!;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  /**
   * 获取面积统计信息
   */
  async getAreaStatistics(filters?: Filters): Promise<AreaStatistics> {
    try {
      const result = await apiClient.get<AreaStatistics>('/assets/statistics/summary', {
        params: filters,
        cache: true,
        retry: { maxAttempts: 3, delay: 1000, backoffMultiplier: 2 },
        smartExtract: true,
      });

      if (!result.success) {
        throw new Error(`获取面积统计信息失败: ${result.error}`);
      }

      return result.data!;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  // ==================== 分布数据 ====================

  /**
   * 获取权属方分布数�?   */
  async getOwnershipDistribution(filters?: Filters): Promise<ChartDataItem[]> {
    try {
      const result = await apiClient.get<ChartDataItem[]>(
        '/statistics/ownership-distribution',
        {
          params: filters,
          cache: true,
          retry: { maxAttempts: 3, delay: 1000, backoffMultiplier: 2 },
          smartExtract: true,
        }
      );

      if (!result.success) {
        throw new Error(`获取权属方分布数据失败: ${result.error}`);
      }

      return result.data!;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      logger.warn('获取权属方分布数据失败', { error: enhancedError.message });
      return [];
    }
  }

  /**
   * 获取物业性质分布数据
   */
  async getPropertyNatureDistribution(filters?: Filters): Promise<ChartDataItem[]> {
    try {
      const result = await apiClient.get<ChartDataItem[]>(
        '/statistics/property-nature-distribution',
        {
          params: filters,
          cache: true,
          retry: { maxAttempts: 3, delay: 1000, backoffMultiplier: 2 },
          smartExtract: true,
        }
      );

      if (!result.success) {
        throw new Error(`获取物业性质分布数据失败: ${result.error}`);
      }

      return result.data!;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      logger.warn('获取物业性质分布数据失败', { error: enhancedError.message });
      return [];
    }
  }

  /**
   * 获取使用状态分布数�?   */
  async getUsageStatusDistribution(filters?: Filters): Promise<ChartDataItem[]> {
    try {
      const result = await apiClient.get<ChartDataItem[]>(
        '/statistics/usage-status-distribution',
        {
          params: filters,
          cache: true,
          retry: { maxAttempts: 3, delay: 1000, backoffMultiplier: 2 },
          smartExtract: true,
        }
      );

      if (!result.success) {
        throw new Error(`获取使用状态分布数据失败: ${result.error}`);
      }

      return result.data!;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      logger.warn('获取使用状态分布数据失败', { error: enhancedError.message });
      return [];
    }
  }

  /**
   * 获取出租率分布数据
   */
  async getOccupancyRateDistribution(filters?: Filters): Promise<ChartDataItem[]> {
    try {
      const result = await apiClient.get<{ categories: ChartDataItem[] }>(
        '/statistics/occupancy-rate/by-category',
        {
          params: { category_field: 'business_category', ...filters },
          cache: true,
          retry: { maxAttempts: 3, delay: 1000, backoffMultiplier: 2 },
          smartExtract: true,
        }
      );

      if (!result.success) {
        throw new Error(`获取出租率分布数据失败: ${result.error}`);
      }

      return result.data?.categories ?? [];
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      logger.warn('获取出租率分布数据失败', { error: enhancedError.message });
      return [];
    }
  }

  // ==================== 趋势数据 ====================

  /**
   * 获取趋势数据
   */
  async getTrendData(
    metric: string,
    period: 'daily' | 'weekly' | 'monthly' | 'yearly' = 'monthly',
    filters?: Filters
  ): Promise<TrendDataItem[]> {
    try {
      const result = await apiClient.get<TrendDataItem[]>(`/statistics/trend/${metric}`, {
        params: { period, ...filters },
        cache: true,
        retry: { maxAttempts: 3, delay: 1000, backoffMultiplier: 2 },
        smartExtract: true,
      });

      if (!result.success) {
        throw new Error(`获取趋势数据失败: ${result.error}`);
      }

      return result.data!;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      logger.warn(`获取趋势数据失败 (${metric})`, { error: enhancedError.message });
      return [];
    }
  }

  /**
   * 获取多个指标的趋势数�?   */
  async getMultipleTrends(
    metrics: string[],
    period: 'daily' | 'weekly' | 'monthly' | 'yearly' = 'monthly',
    filters?: Filters
  ): Promise<Record<string, TrendDataItem[]>> {
    const results: Record<string, TrendDataItem[]> = {};
    const errors: string[] = [];

    for (const metric of metrics) {
      try {
        results[metric] = await this.getTrendData(metric, period, filters);
      } catch (error) {
        const enhancedError = ApiErrorHandler.handleError(error);
        errors.push(`${metric}: ${enhancedError.message}`);
        results[metric] = [];
      }
    }

    if (errors.length > 0) {
      logger.warn('部分趋势数据获取失败', { errors });
    }

    return results;
  }

  // ==================== 对比分析 ====================

  /**
   * 获取对比数据
   */
  async getComparisonData(
    metric: string,
    compareType: 'period' | 'category',
    filters?: Filters
  ): Promise<ComparisonData> {
    try {
      const result = await apiClient.get<ComparisonData>(
        `/statistics/comparison/${metric}`,
        {
          params: { compare_type: compareType, ...filters },
          cache: true,
          retry: { maxAttempts: 3, delay: 1000, backoffMultiplier: 2 },
          smartExtract: true,
        }
      );

      if (!result.success) {
        throw new Error(`获取对比数据失败: ${result.error}`);
      }

      return result.data!;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  /**
   * 获取同期对比数据
   */
  async getPeriodComparison(
    metric: string,
    currentPeriod: string,
    previousPeriod: string,
    filters?: Filters
  ): Promise<{
    current: TrendDataItem[];
    previous: TrendDataItem[];
    growth: number;
  }> {
    try {
      const [currentResult, previousResult] = await Promise.all([
        this.getTrendData(metric, 'monthly', { ...filters, period: currentPeriod }),
        this.getTrendData(metric, 'monthly', { ...filters, period: previousPeriod }),
      ]);

      // 计算增长率
      const currentSum = currentResult.reduce((sum, item) => sum + item.value, 0);
      const previousSum = previousResult.reduce((sum, item) => sum + item.value, 0);
      const growth = previousSum === 0 ? 0 : ((currentSum - previousSum) / previousSum) * 100;

      return {
        current: currentResult,
        previous: previousResult,
        growth,
      };
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(`获取同期对比数据失败: ${enhancedError.message}`);
    }
  }

  // ==================== 报表生成 ====================

  /**
   * 生成报表
   */
  async generateReport(
    reportType: string,
    filters?: Filters,
    format: 'json' | 'excel' | 'pdf' = 'json'
  ): Promise<ReportGenerationResponse> {
    try {
      const result = await apiClient.post<ReportGenerationResponse>(
        `/statistics/report/${reportType}`,
        {
          filters,
          format,
        },
        {
          retry: { maxAttempts: 3, delay: 1000, backoffMultiplier: 2 },
          smartExtract: true,
        }
      );

      if (!result.success) {
        throw new Error(`生成报表失败: ${result.error}`);
      }

      return result.data!;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  /**
   * 获取报表状�?   */
  async getReportStatus(reportId: string): Promise<ReportGenerationResponse> {
    try {
      const result = await apiClient.get<ReportGenerationResponse>(
        `/statistics/report/status/${reportId}`,
        {
          retry: { maxAttempts: 3, delay: 1000, backoffMultiplier: 2 },
          smartExtract: true,
        }
      );

      if (!result.success) {
        throw new Error(`获取报表状态失�? ${result.error}`);
      }

      return result.data!;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  /**
   * 下载报表
   */
  async downloadReport(reportId: string): Promise<Blob> {
    try {
      const result = await apiClient.get<Blob>(`/statistics/report/download/${reportId}`, {
        responseType: 'blob',
        retry: { maxAttempts: 3, delay: 1000, backoffMultiplier: 2 },
      });

      if (!result.success) {
        throw new Error(`下载报表失败: ${result.error}`);
      }

      return result.data!;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  // ==================== 高级统计功能 ====================

  /**
   * 获取资产排名统计
   */
  async getAssetRankings(
    metric: 'area' | 'rent' | 'occupancy_rate',
    limit: number = 10,
    filters?: Filters
  ): Promise<Array<{ name: string; value: number; rank: number }>> {
    try {
      const result = await apiClient.get<
        Array<{ name: string; value: number; rank: number }>
      >(`/statistics/rankings/asset/${metric}`, {
        params: { limit, ...filters },
        cache: true,
        retry: { maxAttempts: 3, delay: 1000, backoffMultiplier: 2 },
        smartExtract: true,
      });

      if (!result.success) {
        throw new Error(`获取资产排名失败: ${result.error}`);
      }

      return result.data!;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      logger.warn(`获取资产排名失败 (${metric})`, { error: enhancedError.message });
      return [];
    }
  }

  /**
   * 获取区域统计对比
   */
  async getRegionalComparison(filters?: Filters): Promise<{
    regions: string[];
    metrics: Record<string, number[]>;
  }> {
    try {
      const result = await apiClient.get<{
        regions: string[];
        metrics: Record<string, number[]>;
      }>('/statistics/regional-comparison', {
        params: filters,
        cache: true,
        retry: { maxAttempts: 3, delay: 1000, backoffMultiplier: 2 },
        smartExtract: true,
      });

      if (!result.success) {
        throw new Error(`获取区域对比数据失败: ${result.error}`);
      }

      return result.data!;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  /**
   * 获取性能指标摘要
   */
  async getPerformanceSummary(filters?: Filters): Promise<{
    totalAssets: number;
    totalArea: number;
    averageOccupancyRate: number;
    averageRent: number;
    revenueGrowth: number;
    efficiency: number;
  }> {
    try {
      const result = await apiClient.get<{
        totalAssets: number;
        totalArea: number;
        averageOccupancyRate: number;
        averageRent: number;
        revenueGrowth: number;
        efficiency: number;
      }>('/statistics/performance-summary', {
        params: filters,
        cache: true,
        retry: { maxAttempts: 3, delay: 1000, backoffMultiplier: 2 },
        smartExtract: true,
      });

      if (!result.success) {
        throw new Error(`获取性能指标摘要失败: ${result.error}`);
      }

      return result.data!;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  /**
   * 批量获取统计数据
   */
  async batchGetStatistics(filters?: Filters): Promise<{
    dashboard: DashboardData;
    basic: BasicStatistics;
    area: AreaStatistics;
    distributions: {
      ownership: ChartDataItem[];
      propertyNature: ChartDataItem[];
      usageStatus: ChartDataItem[];
      occupancyRate: ChartDataItem[];
    };
  }> {
    try {
      const [dashboard, basic, area, ownership, propertyNature, usageStatus, occupancyRate] =
        await Promise.allSettled([
          this.getDashboardData(),
          this.getBasicStatistics(filters),
          this.getAreaStatistics(filters),
          this.getOwnershipDistribution(filters),
          this.getPropertyNatureDistribution(filters),
          this.getUsageStatusDistribution(filters),
          this.getOccupancyRateDistribution(filters),
        ]);

      return {
        dashboard: dashboard.status === 'fulfilled' ? dashboard.value : ({} as DashboardData),
        basic: basic.status === 'fulfilled' ? basic.value : ({} as BasicStatistics),
        area: area.status === 'fulfilled' ? area.value : ({} as AreaStatistics),
        distributions: {
          ownership: ownership.status === 'fulfilled' ? ownership.value : [],
          propertyNature: propertyNature.status === 'fulfilled' ? propertyNature.value : [],
          usageStatus: usageStatus.status === 'fulfilled' ? usageStatus.value : [],
          occupancyRate: occupancyRate.status === 'fulfilled' ? occupancyRate.value : [],
        },
      };
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(`批量获取统计数据失败: ${enhancedError.message}`);
    }
  }
}

export const statisticsService = new StatisticsService();
