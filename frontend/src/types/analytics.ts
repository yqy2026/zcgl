import type { AssetSearchParams } from './asset'

export interface AreaSummary {
  total_assets: number
  total_area: number
  total_rentable_area: number
  total_rented_area: number
  total_unrented_area: number
  assets_with_area_data: number
  occupancy_rate: number
}

export interface FinancialSummary {
  estimated_annual_income: number
  total_annual_income: number
  total_annual_expense: number
  total_net_income: number
  total_monthly_rent: number
  total_deposit: number
  assets_with_income_data: number
  assets_with_rent_data: number
  profit_margin: number
}

export interface OccupancyDistribution {
  range: string
  count: number
  percentage: number
}

export interface PropertyNatureDistribution {
  name: string
  count: number
  percentage: number
}

export interface OwnershipStatusDistribution {
  status: string
  count: number
  percentage: number
}

export interface UsageStatusDistribution {
  status: string
  count: number
  percentage: number
}

export interface BusinessCategoryDistribution {
  category: string
  count: number
  occupancy_rate: number
  avg_annual_income: number
}

export interface OccupancyTrend {
  date: string
  occupancy_rate: number
  total_rented_area: number
  total_rentable_area: number
}

export interface PerformanceMetrics {
  asset_utilization: number
  income_efficiency: number
  occupancy_variance: number
  growth_rate: number
}

export interface ComparisonData {
  current_period: AreaSummary & FinancialSummary
  previous_period: AreaSummary & FinancialSummary
  change_percentage: {
    total_assets: number
    total_area: number
    occupancy_rate: number
    total_annual_income: number
    total_net_income: number
  }
}

export interface AnalyticsData {
  area_summary: AreaSummary
  financial_summary: FinancialSummary
  occupancy_distribution: OccupancyDistribution[]
  property_nature_distribution: PropertyNatureDistribution[]
  ownership_status_distribution: OwnershipStatusDistribution[]
  usage_status_distribution: UsageStatusDistribution[]
  business_category_distribution: BusinessCategoryDistribution[]
  occupancy_trend: OccupancyTrend[]
  property_nature_area_distribution?: PropertyNatureDistribution[]
  ownership_status_area_distribution?: OwnershipStatusDistribution[]
  usage_status_area_distribution?: UsageStatusDistribution[]
  business_category_area_distribution?: BusinessCategoryDistribution[]
  // performance_metrics: PerformanceMetrics  // 暂时注释，等待后端API支持
  // comparison_data?: ComparisonData  // 暂时注释，等待后端API支持
}

export interface AnalyticsResponse {
  success: boolean
  message: string
  data: AnalyticsData
  // Flat structure for direct access (compatible with AnalyticsData)
  area_summary?: AreaSummary
  financial_summary?: FinancialSummary
  occupancy_distribution?: OccupancyDistribution[]
  property_nature_distribution?: PropertyNatureDistribution[]
  ownership_status_distribution?: OwnershipStatusDistribution[]
  usage_status_distribution?: UsageStatusDistribution[]
  business_category_distribution?: BusinessCategoryDistribution[]
  occupancy_trend?: OccupancyTrend[]
  property_nature_area_distribution?: PropertyNatureDistribution[]
  ownership_status_area_distribution?: OwnershipStatusDistribution[]
  usage_status_area_distribution?: UsageStatusDistribution[]
  business_category_area_distribution?: BusinessCategoryDistribution[]
}

export interface ChartDataPoint {
  name: string
  value: number
  percentage?: number
  [key: string]: unknown
}

export interface FilterPreset {
  key: string
  label: string
  filters: AssetSearchParams
  description?: string
}

export interface AnalyticsViewConfig {
  showCharts: boolean
  showTables: boolean
  showTrends: boolean
  showComparison: boolean
  chartType: 'pie' | 'bar' | 'line' | 'area'
  timeRange: 'day' | 'week' | 'month' | 'quarter' | 'year'
}

export interface ExportOptions {
  format: 'excel' | 'pdf' | 'csv'
  includeCharts: boolean
  includeRawData: boolean
  dateRange?: [string, string]
}

export interface DashboardWidget {
  id: string
  title: string
  type: 'statistic' | 'chart' | 'table'
  size: 'small' | 'medium' | 'large'
  position: { x: number; y: number; width: number; height: number }
  config: Record<string, any>
}

export interface AnalyticsSettings {
  refreshInterval: number
  defaultFilters: AssetSearchParams
  viewConfig: AnalyticsViewConfig
  widgets: DashboardWidget[]
  exportDefaults: ExportOptions
}