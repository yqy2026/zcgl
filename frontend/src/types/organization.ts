/**
 * 组织架构相关类型定义
 * @deprecated Phase 3 兼容保留，待 Phase 4 完成 Party 全量迁移后移除。
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
  type: string;
  status: string;
  represented_party_id?: string | null;
  represented_party_perspective?: OrganizationPartyPerspective | null;

  // 其他信息
  description?: string;

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
  type: string;
  status: string;

  // 其他信息
  description?: string;

  created_by?: string;
}

export interface OrganizationUpdate {
  name?: string;
  code?: string;
  level?: number;
  sort_order?: number;
  parent_id?: string;
  type?: string;
  status?: string;

  // 其他信息
  description?: string;

  updated_by?: string;
}

export type OrganizationPartyPerspective = 'owner' | 'manager';

export interface OrganizationPartyScopeProposal {
  represented_party_id: string | null;
  represented_party_perspective: OrganizationPartyPerspective | null;
}

export interface OrganizationPartyScopeState {
  represented_party_id?: string | null;
  represented_party_perspective?: OrganizationPartyPerspective | null;
  effective_party_id?: string | null;
  effective_party_perspective?: OrganizationPartyPerspective | null;
  source_organization_id?: string | null;
}

export interface OrganizationPartyScopeImpact {
  organization_count: number;
  organization_scope_change_count: number;
  user_count: number;
  user_scope_change_count: number;
}

export interface OrganizationPartyScopePreview {
  organization_id: string;
  before_scope: OrganizationPartyScopeState;
  after_scope: OrganizationPartyScopeState;
  impact: OrganizationPartyScopeImpact;
  preview_token: string;
  expires_at: string;
}

export interface OrganizationPartyScopeCommitRequest {
  preview_token: string;
  reason: string;
  idempotency_key: string;
}

export interface OrganizationPartyScopeCommitResponse {
  organization: Organization;
  before_scope: OrganizationPartyScopeState;
  after_scope: OrganizationPartyScopeState;
  impact: OrganizationPartyScopeImpact;
  committed_at: string;
  idempotent: boolean;
}

export interface OrganizationPartyScopeBatchProposal extends OrganizationPartyScopeProposal {
  organization_id: string;
}

export interface OrganizationPartyScopeBatchPreviewItem {
  organization: Organization;
  before_scope: OrganizationPartyScopeState;
  after_scope: OrganizationPartyScopeState;
  impact: OrganizationPartyScopeImpact;
}

export interface OrganizationPartyScopeBatchPreviewRequest {
  items: OrganizationPartyScopeBatchProposal[];
}

export interface OrganizationPartyScopeBatchPreview {
  items: OrganizationPartyScopeBatchPreviewItem[];
  impact: OrganizationPartyScopeImpact;
  preview_token: string;
  expires_at: string;
}

export interface OrganizationPartyScopeBatchCommitRequest {
  preview_token: string;
  reason: string;
  idempotency_key: string;
}

export interface OrganizationPartyScopeBatchCommitResponse {
  items: OrganizationPartyScopeBatchPreviewItem[];
  impact: OrganizationPartyScopeImpact;
  committed_at: string;
  idempotent: boolean;
}

export interface OrganizationTree {
  id: string;
  name: string;
  code: string;
  level: number;
  sort_order: number;
  type: string;
  status: string;
  children: OrganizationTree[];
}

export interface OrganizationHistory {
  id: string;
  organization_id: string;
  action: 'create' | 'update' | 'delete' | 'move' | 'party_scope_update';
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

export interface OrganizationMoveProposal {
  target_parent_id: string | null;
}

export interface OrganizationMoveScopeState {
  parent_id: string | null;
  effective_party_id: string | null;
  effective_party_perspective: 'owner' | 'manager' | null;
  source_organization_id: string | null;
}

export interface OrganizationMoveImpact {
  organization_count: number;
  organization_scope_change_count: number;
  organization_path_change_count: number;
  user_count: number;
  user_scope_change_count: number;
}

export interface OrganizationMovePreview {
  organization_id: string;
  before_scope: OrganizationMoveScopeState;
  after_scope: OrganizationMoveScopeState;
  impact: OrganizationMoveImpact;
  preview_token: string;
  expires_at: string;
}

export interface OrganizationMoveCommitRequest {
  preview_token: string;
  reason: string;
  idempotency_key: string;
}

export interface OrganizationMoveCommitResponse {
  organization: Organization;
  before_scope: OrganizationMoveScopeState;
  after_scope: OrganizationMoveScopeState;
  impact: OrganizationMoveImpact;
  committed_at: string;
  idempotent: boolean;
}

export interface OrganizationSearchRequest {
  keyword?: string;
  level?: number;
  parent_id?: string;
  page?: number;
  page_size?: number;
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

// 高级搜索条件
export interface OrganizationSearchCriteria extends OrganizationSearchRequest {
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
