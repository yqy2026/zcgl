import { apiClient } from './api'
import type { AssetSearchParams } from '../types/asset'

export interface AnalyticsData {
  area_summary: {
    total_assets: number
    total_land_area: number
    total_actual_property_area: number
    total_area: number
    total_rentable_area: number
    total_rented_area: number
    total_unrented_area: number
    assets_with_area_data: number
    occupancy_rate: number
  }
  financial_summary: {
    total_annual_income: number
    total_annual_expense: number
    total_net_income: number
    total_monthly_rent: number
    total_deposit: number
    assets_with_income_data: number
    assets_with_rent_data: number
  }
  occupancy_distribution: Array<{
    range: string
    count: number
    percentage: number
  }>
  property_nature_distribution: Array<{
    name: string
    count: number
    percentage: number
  }>
  ownership_status_distribution: Array<{
    status: string
    count: number
    percentage: number
  }>
  usage_status_distribution: Array<{
    status: string
    count: number
    percentage: number
  }>
  business_category_distribution: Array<{
    category: string
    count: number
    occupancy_rate: number
  }>
  occupancy_trend: Array<{
    date: string
    occupancy_rate: number
    total_rented_area: number
    total_rentable_area: number
  }>
  // 面积维度分布数据
  property_nature_area_distribution: Array<{
    name: string
    count: number
    total_area: number
    percentage: number
    area_percentage: number
    average_area: number
  }>
  ownership_status_area_distribution: Array<{
    status: string
    count: number
    total_area: number
    percentage: number
    area_percentage: number
    average_area: number
  }>
  usage_status_area_distribution: Array<{
    status: string
    count: number
    total_area: number
    percentage: number
    area_percentage: number
    average_area: number
  }>
  business_category_area_distribution: Array<{
    category: string
    count: number
    total_area: number
    percentage: number
    area_percentage: number
    average_area: number
    occupancy_rate: number
  }>
}

export interface AnalyticsResponse {
  success: boolean
  message: string
  data: AnalyticsData
}

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