import { apiClient } from "./api";
import type { DashboardData, ChartDataItem } from "@/types/api";
import type { Filters } from "@/types/common";

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
  status: "queued" | "processing" | "completed" | "failed";
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
  async getDashboardData(): Promise<DashboardData> {
    const response = await apiClient.get<DashboardData>("/statistics/dashboard");
    return response.data || (response as DashboardData);
  }

  async getBasicStatistics(filters?: Filters): Promise<BasicStatistics> {
    try {
      const response = await apiClient.get<BasicStatistics>("/statistics/basic", {
        params: filters,
      });
      return response.data || response;
    } catch (error) {
      console.error("操作失败:", error);
      throw new Error(error instanceof Error ? error.message : "操作失败");
    }
  }

  async getOwnershipDistribution(filters?: Filters): Promise<ChartDataItem[]> {
    const response = await apiClient.get<ChartDataItem[]>("/statistics/ownership-distribution", {
      params: filters,
    });
    return response.data || [];
  }

  async getPropertyNatureDistribution(filters?: Filters): Promise<ChartDataItem[]> {
    const response = await apiClient.get<ChartDataItem[]>(
      "/statistics/property-nature-distribution",
      {
        params: filters,
      },
    );
    return response.data || [];
  }

  async getUsageStatusDistribution(filters?: Filters): Promise<ChartDataItem[]> {
    const response = await apiClient.get<ChartDataItem[]>("/statistics/usage-status-distribution", {
      params: filters,
    });
    return response.data || [];
  }

  async getOccupancyRateDistribution(filters?: Filters): Promise<ChartDataItem[]> {
    const response = await apiClient.get<{ data: { categories: ChartDataItem[] } }>(
      "/statistics/occupancy-rate/by-category",
      {
        params: { category_field: "business_category", ...filters },
      },
    );
    return response.data?.data?.categories || [];
  }

  async getAreaStatistics(filters?: Filters): Promise<AreaStatistics> {
    const response = await apiClient.get<{ data: AreaStatistics }>("/assets/statistics/summary", {
      params: filters,
    });
    return response.data?.data || response.data;
  }

  async getTrendData(
    metric: string,
    period: "daily" | "weekly" | "monthly" | "yearly" = "monthly",
    filters?: Filters,
  ): Promise<TrendDataItem[]> {
    const response = await apiClient.get<TrendDataItem[]>(`/statistics/trend/${metric}`, {
      params: { period, ...filters },
    });
    return response.data || [];
  }

  async generateReport(
    reportType: string,
    filters?: Filters,
    format: "json" | "excel" | "pdf" = "json",
  ): Promise<ReportGenerationResponse> {
    const response = await apiClient.post<ReportGenerationResponse>(
      `/statistics/report/${reportType}`,
      {
        filters,
        format,
      },
    );
    return response.data || response;
  }

  async getComparisonData(
    metric: string,
    compareType: "period" | "category",
    filters?: Filters,
  ): Promise<ComparisonData> {
    const response = await apiClient.get<ComparisonData>(`/statistics/comparison/${metric}`, {
      params: { compare_type: compareType, ...filters },
    });
    return response.data || response;
  }
}

export const statisticsService = new StatisticsService();
