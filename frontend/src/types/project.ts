/**
 * 项目类型定义
 */

export interface Project {
  id: string;
  name: string;
  code: string;
  description?: string;
  is_active: boolean;
  data_status: string;
  created_at: string;
  updated_at: string;
  created_by?: string;
  updated_by?: string;
  asset_count?: number;

  // 权属方关联
  ownership_relations?: Array<{
    id: string;
    ownership_id: string;
    ownership_name: string;
    relation_type: string;
    is_active: boolean;
  }>;
}

export interface ProjectCreate {
  name: string;
  description?: string;
  ownership_relations?: Array<{
    ownership_id: string;
    relation_type: string;
  }>;
}

export interface ProjectUpdate {
  name?: string;
  description?: string;
  ownership_relations?: Array<{
    ownership_id: string;
    relation_type: string;
  }>;
}

export type ProjectResponse = Project;

export interface ProjectListResponse {
  items: ProjectResponse[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

export interface ProjectDeleteResponse {
  message: string;
  deleted_id: string;
}

export interface ProjectSearchRequest {
  keyword?: string;
  is_active?: boolean;
  page?: number;
  size?: number;
}

export interface ProjectStatisticsResponse {
  total_count: number;
  active_count: number;
  inactive_count: number;
}

// 项目搜索参数类型
export interface ProjectSearchParams {
  keyword?: string;
  is_active?: boolean;
  ownership_id?: string;
  page?: number;
  size?: number;
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
  inactive: number;
}

// 项目下拉选项类型
export interface ProjectDropdownOption {
  id: string;
  name: string;
  code: string;
  is_active: boolean;
}
