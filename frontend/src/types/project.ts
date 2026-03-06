/**
 * 项目类型定义
 */

import type { Asset } from '@/types/asset';

export interface ProjectPartyRelation {
  id?: string;
  project_id?: string;
  party_id: string;
  party_name?: string;
  relation_type: string;
  is_primary?: boolean;
  is_active?: boolean;
}

export interface Project {
  id: string;
  project_name: string;
  project_code: string;
  status: string;
  manager_party_id?: string;
  data_status: string;
  review_status: string;
  review_by?: string;
  reviewed_at?: string;
  review_reason?: string;
  created_at: string;
  updated_at: string;
  created_by?: string;
  updated_by?: string;
  asset_count?: number;
  party_relations?: ProjectPartyRelation[];
}

export interface ProjectCreate {
  project_name: string;
  project_code?: string;
  status?: string;
  manager_party_id?: string;
  party_relations?: ProjectPartyRelation[];
}

export interface ProjectUpdate {
  project_name?: string;
  project_code?: string;
  status?: string;
  manager_party_id?: string;
  data_status?: string;
  party_relations?: ProjectPartyRelation[];
}

export type ProjectResponse = Project;

export interface ProjectListResponse {
  items: ProjectResponse[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export interface ProjectDeleteResponse {
  message: string;
  deleted_id: string;
  affected_assets?: number;
}

export interface ProjectSearchRequest {
  keyword?: string;
  status?: string;
  owner_party_id?: string;
  page?: number;
  page_size?: number;
}

export interface ProjectStatisticsResponse {
  total_projects: number;
  active_projects: number;
}

export interface ProjectAssetSummary {
  total_assets: number;
  total_rentable_area: number;
  total_rented_area: number;
  occupancy_rate: number;
}

export interface ProjectActiveAssetsResponse {
  items: Asset[];
  total: number;
  summary: ProjectAssetSummary;
}

// 项目搜索参数类型
export interface ProjectSearchParams {
  keyword?: string;
  status?: string;
  owner_party_id?: string;
  page?: number;
  page_size?: number;
}

// 项目选项类型（用于下拉选择）
export interface ProjectOption {
  value: string;
  label: string;
  disabled?: boolean;
}

// 项目统计类型
export interface ProjectStats {
  total: number;
  active: number;
}

// 项目下拉选项类型
export interface ProjectDropdownOption {
  id: string;
  project_name: string;
  project_code: string;
  status?: string;
}
