/**
 * Asset Service Types
 * 资产服务相关的接口定义
 */

import type { AreaStatistics } from '@/types/asset';

// Re-export types from asset.ts for convenience
export type {
  Asset,
  AssetSearchParams,
  AssetListResponse,
  AssetCreateRequest,
  AssetUpdateRequest,
  AssetHistory,
  SystemDictionary,
  AssetCustomField,
  CustomFieldValue,
  AreaStatistics,
} from '@/types/asset';

export type { StandardApiResponse, PaginatedApiResponse } from '@/types/apiResponse';

// ==================== 字段相关接口 ====================

/** 字段选项接口 */
export interface FieldOption {
  label: string;
  value: unknown;
}

/** 字段验证结果接口 */
export interface FieldValidationResult {
  valid: boolean;
  error?: string;
}

/** 字段历史记录接口 */
export interface FieldHistoryRecord {
  timestamp: string;
  value: unknown;
  changedBy: string;
  changeReason?: string;
}

// ==================== 历史记录接口 ====================

/** 历史比较结果接口 */
export interface HistoryComparisonResult {
  differences: Array<{
    field: string;
    oldValue: unknown;
    newValue: unknown;
    changeType: 'added' | 'modified' | 'deleted';
  }>;
  summary: {
    totalChanges: number;
    significantChanges: number;
  };
}

// ==================== 统计相关接口 ====================

/** 统计数据接口 */
export interface AssetStats {
  totalAssets: number;
  totalArea: number;
  occupiedArea: number;
  occupancyRate: number;
  byProject: Record<
    string,
    {
      count: number;
      area: number;
      occupancyRate: number;
    }
  >;
  byOwnership: Record<
    string,
    {
      count: number;
      area: number;
    }
  >;
}

/** 出租率统计接口 */
export interface OccupancyRateStats {
  overall: {
    totalArea: number;
    occupiedArea: number;
    occupancyRate: number;
  };
  byProject: Record<
    string,
    {
      totalArea: number;
      occupiedArea: number;
      occupancyRate: number;
    }
  >;
  byTimeRange: Array<{
    period: string;
    occupancyRate: number;
  }>;
  // 实际API返回的额外属性
  monthly_trend?: Array<{
    month: string;
    rate: number;
    total_area: number;
    rented_area: number;
  }>;
  by_property_nature?: Array<{
    property_nature: string;
    rate: number;
    total_area: number;
    rented_area: number;
  }>;
  by_ownership_entity?: Array<{
    ownership_entity: string;
    rate: number;
    asset_count: number;
  }>;
  total_assets?: number;
  summary?: {
    total_area: number;
    rented_area: number;
    occupancy_rate: number;
  };
  // OccupancyRateChart使用的额外属性
  overall_rate?: number;
  trend_percentage?: number;
  trend?: 'up' | 'down' | 'stable';
  top_performers?: Array<{
    property_name: string;
    occupancy_rate: number;
    total_area: number;
    rented_area: number;
    area?: number;
    rate?: number;
  }>;
  low_performers?: Array<{
    property_name: string;
    occupancy_rate: number;
    total_area: number;
    rented_area: number;
    area?: number;
    rate?: number;
  }>;
}

/** 资产分布统计接口 */
export interface AssetDistributionStats {
  byNature: Record<string, number>;
  byStatus: Record<string, number>;
  byUsage: Record<string, number>;
  byArea: Array<{
    range: string;
    count: number;
  }>;
  // 实际API返回的额外属性
  by_property_nature?: Array<{
    property_nature: string;
    land_area: number;
    property_area: number;
    rentable_area: number;
    rented_area: number;
    vacant_area: number;
    non_commercial_area: number;
    count?: number;
    total_area?: number;
    percentage?: number;
  }>;
  by_ownership_status?: Array<{
    ownership_status: string;
    total_area: number;
    rentable_area: number;
    rented_area: number;
    vacant_area: number;
    occupancy_rate: number;
    count?: number;
    percentage?: number;
  }>;
  by_usage_status?: Array<{
    usage_status: string;
    total_area: number;
    rentable_area: number;
    rented_area: number;
    vacant_area: number;
    occupancy_rate: number;
    count?: number;
    percentage?: number;
  }>;
  by_ownership_entity?: Array<{
    ownership_entity: string;
    total_area: number;
    rentable_area: number;
    rented_area: number;
    asset_count: number;
    occupancy_rate: number;
    count?: number;
    percentage?: number;
  }>;
  total_assets?: number;
  summary?: {
    total_area: number;
    total_assets: number;
    by_nature_count: Record<string, number>;
    commercial_area?: number;
  };
}

/** 综合统计接口 */
export interface ComprehensiveStats extends AssetStats {
  distribution: AssetDistributionStats;
  areaStats: AreaStatistics;
  occupancyTrend: Array<{
    period: string;
    rate: number;
  }>;
  recentActivity: Array<{
    type: string;
    count: number;
    timestamp: string;
  }>;
}

// ==================== 导入导出接口 ====================

/** 导出任务状态接口 */
export interface ExportTask {
  id: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  progress: number;
  downloadUrl?: string;
  createdAt: string;
  completedAt?: string;
  errorMessage?: string;
}

/** 导入预览结果接口 */
export interface ImportPreviewResult {
  headers: string[];
  data: Array<Record<string, unknown>>;
  totalCount: number;
  errors: Array<{
    row: number;
    field: string;
    message: string;
  }>;
}

/** 导入任务状态接口 */
export interface ImportTask {
  id: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  progress: number;
  processedCount: number;
  totalCount: number;
  errors: Array<{
    row: number;
    field: string;
    message: string;
  }>;
  createdAt: string;
  completedAt?: string;
}

/** 导出选项接口 */
export interface ExportOptions {
  format?: 'xlsx' | 'csv';
  includeHeaders?: boolean;
  selectedFields?: string[];
}

// ==================== 搜索过滤器接口 ====================

/** 搜索过滤器接口 */
export interface AssetSearchFilters {
  project_id?: string;
  ownership_id?: string;
  property_nature?: string;
  usage_status?: string;
  business_category?: string;
  [key: string]: unknown;
}
