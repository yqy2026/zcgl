import { apiClient } from './api'
import type { AssetSearchParams } from '../types/asset'
import type { AnalyticsData, AnalyticsResponse } from '../types/analytics'

// Re-export the types for compatibility
export type { AnalyticsData, AnalyticsResponse }

export class AnalyticsService {
  private api = apiClient

  async getComprehensiveAnalytics(filters?: AssetSearchParams): Promise<AnalyticsResponse> {
    try {
      const response = await this.api.get<AnalyticsResponse>('/analytics/comprehensive', {
        params: filters
      })
      // The ApiClient already returns response.data, so we don't need to access .data again
      return response
    } catch (error) {
      console.error('Analytics API Error:', error)
      throw error
    }
  }

  async getBasicStatistics(filters?: AssetSearchParams): Promise<AnalyticsResponse> {
    try {
      const response = await this.api.get<AnalyticsResponse>('/statistics/basic', {
        params: filters
      })
      // The ApiClient already returns response.data, so we don't need to access .data again
      return response
    } catch (error) {
      console.error('Basic statistics API Error:', error)
      throw error
    }
  }

  async getAreaSummary(): Promise<AnalyticsResponse> {
    try {
      const response = await this.api.get<AnalyticsResponse>('/statistics/area-summary')
      // The ApiClient already returns response.data, so we don't need to access .data again
      return response
    } catch (error) {
      console.error('Area summary API Error:', error)
      throw error
    }
  }

  async getFinancialSummary(): Promise<AnalyticsResponse> {
    try {
      const response = await this.api.get<AnalyticsResponse>('/statistics/financial-summary')
      // The ApiClient already returns response.data, so we don't need to access .data again
      return response
    } catch (error) {
      console.error('Financial summary API Error:', error)
      throw error
    }
  }
}

export const analyticsService = new AnalyticsService()