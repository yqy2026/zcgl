import { apiClient } from './api'
import type { DashboardData, ChartDataItem } from '@/types/api'

export class StatisticsService {
  // 获取仪表板数据
  async getDashboardData(): Promise<DashboardData> {
    const response = await apiClient.get<DashboardData>('/statistics/dashboard')
    return response.data || response as DashboardData
  }

  // 获取基础统计信息
  async getBasicStatistics(filters?: Record<string, any>): Promise<any> {
  try {
      const response = await apiClient.get('/statistics/basic', {
        params: filters,
      })
      return response.data || response
  } catch (error) {
    console.error('操作失败:', error)
    throw new Error(error instanceof Error ? error.message : '操作失败')
  }

  // 获取权属分布统计
  async getOwnershipDistribution(filters?: Record<string, any>): Promise<ChartDataItem[]> {
    const response = await apiClient.get<ChartDataItem[]>('/statistics/ownership-distribution', {
      params: filters,
    })
    return response.data || []
  }

  // 获取物业性质分布
  async getPropertyNatureDistribution(filters?: Record<string, any>): Promise<ChartDataItem[]> {
    const response = await apiClient.get<ChartDataItem[]>('/statistics/property-nature-distribution', {
      params: filters,
    })
    return response.data || []
  }

  // 获取使用状态分布
  async getUsageStatusDistribution(filters?: Record<string, any>): Promise<ChartDataItem[]> {
    const response = await apiClient.get<ChartDataItem[]>('/statistics/usage-status-distribution', {
      params: filters,
    })
    return response.data || []
  }

  // 获取出租率分布
  async getOccupancyRateDistribution(filters?: Record<string, any>): Promise<ChartDataItem[]> {
    const response = await apiClient.get<{data: {categories: ChartDataItem[]}}>('/statistics/occupancy-rate/by-category', {
      params: { category_field: 'business_category', ...filters },
    })
    return response.data?.data?.categories || []
  }

  // 获取面积统计
  async getAreaStatistics(filters?: Record<string, any>): Promise<any> {
    const response = await apiClient.get('/assets/statistics/summary', {
      params: filters,
    })
    return response.data?.data || response.data
  }

  // 获取趋势数据
  async getTrendData(
    metric: string,
    period: 'daily' | 'weekly' | 'monthly' | 'yearly' = 'monthly',
    filters?: Record<string, any>
  ): Promise<any[]> {
    const response = await apiClient.get(`/statistics/trend/${metric}`, {
      params: { period, ...filters },
    })
    return response.data || []
  }

  // 生成报表
  async generateReport(
    reportType: string,
    filters?: Record<string, any>,
    format: 'json' | 'excel' | 'pdf' = 'json'
  ): Promise<any> {
    const response = await apiClient.post(`/statistics/report/${reportType}`, {
      filters,
      format,
    })
    return response.data || response
  }

  // 获取对比数据
  async getComparisonData(
    metric: string,
    compareType: 'period' | 'category',
    filters?: Record<string, any>
  ): Promise<any> {
    const response = await apiClient.get(`/statistics/comparison/${metric}`, {
      params: { compare_type: compareType, ...filters },
    })
    return response.data || response
  }
}

// 导出服务实例
export const statisticsService = new StatisticsService()