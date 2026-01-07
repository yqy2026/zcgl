/**
 * 组织架构相关类型定义
 */

export interface Organization {
  id: string;
  name: string;
  code: string;
  level: number;
  sort_order: number;
  parent_id?: string;
  path?: string;

  // 组织基本信息
  type: 'company' | 'department' | 'group' | 'division' | 'team' | 'branch' | 'office';
  status: 'active' | 'inactive' | 'suspended';

  // 联系信息
  phone?: string;
  email?: string;
  address?: string;

  // 负责人信息
  leader_name?: string;
  leader_phone?: string;
  leader_email?: string;

  // 其他信息
  description?: string;
  functions?: string;

  // 系统字段
  is_deleted: boolean;
  created_at: string;
  updated_at: string;
  created_by?: string;
  updated_by?: string;

  children?: Organization[];
}

export interface OrganizationCreate {
  name: string;
  code: string;
  level?: number;
  sort_order?: number;
  parent_id?: string;
  type: 'company' | 'department' | 'group' | 'division' | 'team' | 'branch' | 'office';
  status: 'active' | 'inactive' | 'suspended';

  // 联系信息
  phone?: string;
  email?: string;
  address?: string;

  // 负责人信息
  leader_name?: string;
  leader_phone?: string;
  leader_email?: string;

  // 其他信息
  description?: string;
  functions?: string;

  created_by?: string;
}

export interface OrganizationUpdate {
  name?: string;
  code?: string;
  level?: number;
  sort_order?: number;
  parent_id?: string;
  type?: 'company' | 'department' | 'group' | 'division' | 'team' | 'branch' | 'office';
  status?: 'active' | 'inactive' | 'suspended';

  // 联系信息
  phone?: string;
  email?: string;
  address?: string;

  // 负责人信息
  leader_name?: string;
  leader_phone?: string;
  leader_email?: string;

  // 其他信息
  description?: string;
  functions?: string;

  updated_by?: string;
}

export interface OrganizationTree {
  id: string;
  name: string;
  code: string;
  level: number;
  sort_order: number;
  type: 'company' | 'department' | 'group' | 'division' | 'team' | 'branch' | 'office';
  status: 'active' | 'inactive' | 'suspended';
  children: OrganizationTree[];
}

export interface OrganizationHistory {
  id: string;
  organization_id: string;
  action: 'create' | 'update' | 'delete';
  field_name?: string;
  old_value?: string;
  new_value?: string;
  change_reason?: string;
  created_at: string;
  created_by?: string;
}

export interface OrganizationStatistics {
  total: number;
  active: number;
  inactive: number;
  by_level: Record<string, number>;
  by_type: Record<string, number>;
}

export interface OrganizationMoveRequest {
  target_parent_id?: string;
  sort_order?: number;
  updated_by?: string;
}

export interface OrganizationBatchRequest {
  organization_ids: string[];
  action: 'delete' | 'move';
  updated_by?: string;
}

export interface OrganizationSearchRequest {
  keyword?: string;
  level?: number;
  parent_id?: string;
  skip?: number;
  limit?: number;
}

export interface OrganizationBatchResult {
  message: string;
  results: Array<{
    id: string;
    status: 'success' | 'error';
    message: string;
  }>;
  errors: Array<{
    id: string;
    error: string;
  }>;
}

// API响应类型
export interface OrganizationListResponse {
  data: Organization[];
  total: number;
  page: number;
  page_size: number;
}

export interface OrganizationResponse {
  data: Organization;
  message?: string;
}

export interface OrganizationTreeResponse {
  data: OrganizationTree[];
}

export interface OrganizationStatisticsResponse {
  data: OrganizationStatistics;
}

export interface OrganizationHistoryResponse {
  data: OrganizationHistory[];
  total: number;
  page: number;
  page_size: number;
}

// 表单验证规则
export interface OrganizationFormRules {
  name: Array<{ required: boolean; message: string; min?: number; max?: number }>;
}

// 树形选择器数据节点
export interface OrganizationTreeNode {
  key: string;
  title: React.ReactNode;
  value: string;
  children?: OrganizationTreeNode[];
  disabled?: boolean;
}

// 组织路径信息
export interface OrganizationPath {
  organizations: Organization[];
  path_string: string;
}

// 组织移动操作结果
export interface OrganizationMoveResult {
  message: string;
  organization: Organization;
}

// 高级搜索条件
export interface OrganizationAdvancedSearch extends OrganizationSearchRequest {
  date_range?: [string, string];
  created_by?: string;
  updated_by?: string;
}

// 组织导出配置
export interface OrganizationExportConfig {
  format: 'excel' | 'csv' | 'pdf';
  fields: string[];
  include_children: boolean;
  filter?: OrganizationSearchRequest;
}

// 组织导入配置
export interface OrganizationImportConfig {
  file: File;
  update_existing: boolean;
  skip_errors: boolean;
  dry_run: boolean;
}

// 组织导入结果
export interface OrganizationImportResult {
  success_count: number;
  error_count: number;
  errors: Array<{
    row: number;
    field: string;
    message: string;
  }>;
  preview?: Organization[];
}
