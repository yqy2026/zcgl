/**
 * @deprecated 请直接从 '@/types/apiResponse' 或 '@/types' 导入标准响应类型
 * 此文件保留以向后兼容，将在未来版本中移除
 *
 * @module types/api
 * @description
 * 旧的 API 响应类型定义。新代码应使用 `@/types/apiResponse` 中定义的标准化类型。
 *
 * @example
 * ```typescript
 * // ✅ 推荐：使用标准类型
 * import type { StandardApiResponse, PaginatedApiResponse } from '@/types';
 *
 * // ❌ 已废弃：从此文件导入
 * import type { ApiResponse } from '@/types/api';
 * ```
 */

// ==================== 重新导出标准类型（向后兼容） ====================

/**
 * @deprecated 使用 StandardApiResponse 代替
 */
export type ApiResponse<T = unknown> =
  | {
      success?: boolean;
      message?: string;
      data?: T;
      error?: string;
      timestamp?: string;
    }
  | {
      success: true;
      data: T;
      message?: string;
      timestamp?: string;
    }
  | {
      success: false;
      error: string;
      message?: string;
      timestamp?: string;
    };

/**
 * @deprecated 使用 PaginatedApiResponse 代替
 */
export interface PaginatedResponse<T> {
  data: T[];
  total: number;
  page: number;
  pageSize: number;
  has_next: boolean;
  has_prev: boolean;
}

/**
 * @deprecated 使用 apiResponse.ts 中的 ErrorResponse 代替
 */
export interface ErrorResponse {
  error: string;
  message: string;
  details?: unknown[];
  timestamp: string;
}

// 统计相关类型
export interface DashboardData {
  key_metrics: {
    total_assets: number;
    total_area: number;
    total_rentable_area: number;
    overall_occupancy_rate: number;
    total_rented_area: number;
    total_unrented_area: number;
  };
  charts: {
    ownership_distribution: ChartDataItem[];
    property_nature_distribution: ChartDataItem[];
    usage_status_distribution: ChartDataItem[];
    occupancy_ranges: ChartDataItem[];
  };
  generated_at: string;
  data_count: number;
}

export interface ChartDataItem {
  name: string;
  value?: number;
  count?: number;
  percentage: number;
  area?: number;
  area_percentage?: number;
}

// Excel导入导出类型
export interface ExcelImportResponse {
  success: number;
  failed: number;
  total: number;
  errors: string[];
  message: string;
}

export interface ExcelExportRequest {
  filters?: Record<string, unknown>;
  columns?: string[];
  format?: 'xlsx' | 'xls' | 'csv';
  include_headers?: boolean;
}

export interface ExcelExportResponse {
  file_url: string;
  file_name: string;
  file_size: number;
  total_records: number;
  created_at: string;
  expires_at: string;
}

// 备份相关类型
export interface BackupInfo {
  filename: string;
  file_path: string;
  file_size: number;
  timestamp: string;
  created_at: string;
  description: string;
  is_compressed: boolean;
  backup_type: string;
}

export interface BackupListResponse {
  success: boolean;
  message: string;
  backups: BackupInfo[];
  total_count: number;
}
