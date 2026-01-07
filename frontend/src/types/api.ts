// API响应类型定义

export interface ApiResponse<T = unknown> {
  success?: boolean;
  message?: string;
  data?: T;
  error?: string;
  timestamp?: string;
}

export interface PaginatedResponse<T> {
  data: T[];
  total: number;
  page: number;
  limit: number;
  has_next: boolean;
  has_prev: boolean;
}

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
