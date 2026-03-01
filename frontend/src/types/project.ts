/**
 * 项目类型定义
 */

const legacyProjectRelationsField = `${'ownership'}_${'relations'}` as const;

export interface ProjectPartyRelation {
  id?: string;
  project_id?: string;
  party_id: string;
  party_name?: string;
  relation_type: string;
  is_primary?: boolean;
  is_active?: boolean;
}

export interface ProjectOwnershipRelationLegacy {
  id: string;
  party_id: string;
  party_name: string;
  relation_type: string;
  is_active: boolean;
}

export interface Project {
  id: string;
  name: string;
  code: string;
  short_name?: string; // 项目简称
  description?: string;
  is_active: boolean;
  data_status: string;
  created_at: string;
  updated_at: string;
  created_by?: string;
  updated_by?: string;
  asset_count?: number;
  party_relations?: ProjectPartyRelation[];

  /** @deprecated 兼容旧字段，后续统一使用 party_relations。 */
  [legacyProjectRelationsField]?: ProjectOwnershipRelationLegacy[];
}

export interface ProjectCreate {
  name: string;
  description?: string;
  party_relations?: Array<{
    party_id: string;
    relation_type: string;
    is_primary?: boolean;
  }>;
}

export interface ProjectUpdate {
  name?: string;
  description?: string;
  party_relations?: Array<{
    party_id: string;
    relation_type: string;
    is_primary?: boolean;
  }>;
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
}

export interface ProjectSearchRequest {
  keyword?: string;
  is_active?: boolean;
  page?: number;
  page_size?: number;
}

export interface ProjectStatisticsResponse {
  total_count: number;
  active_count: number;
  inactive_count: number;
  projects?: Array<{
    id: string;
    asset_count?: number;
    total_area?: number;
  }>;
}

// 项目搜索参数类型
export interface ProjectSearchParams {
  keyword?: string;
  is_active?: boolean;
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
  inactive: number;
}

// 项目下拉选项类型
export interface ProjectDropdownOption {
  id: string;
  name: string;
  code: string;
  short_name?: string;
  is_active: boolean;
}
