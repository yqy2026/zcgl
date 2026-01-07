/**
 * 权属方类型定义
 */

export interface Ownership {
  id: string;
  name: string;
  code: string;
  short_name?: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  asset_count?: number;
  project_count?: number;
  related_projects?: Array<{
    id: string;
    name: string;
    code: string;
    relation_type: string;
    start_date?: string;
    end_date?: string;
  }>;
}

export interface OwnershipCreate {
  name: string;
  code: string;
  short_name?: string;
}

export interface OwnershipUpdate {
  name?: string;
  code?: string;
  short_name?: string;
  is_active?: boolean;
}

export interface OwnershipListResponse {
  items: Ownership[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

export interface OwnershipSearchRequest {
  keyword?: string;
  is_active?: boolean;
  page: number;
  size: number;
}

export interface OwnershipStatisticsResponse {
  total_count: number;
  active_count: number;
  inactive_count: number;
  recent_created: Ownership[];
}

export interface OwnershipDeleteResponse {
  message: string;
  id: string;
  affected_assets?: number;
}

export interface OwnershipFormData {
  name: string;
  code: string;
  short_name?: string;
}

export interface OwnershipSearchParams {
  keyword?: string;
  is_active?: boolean;
  page?: number;
  size?: number;
}
