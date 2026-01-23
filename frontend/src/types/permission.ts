/**
 * 权限相关类型定义
 * 与后端 models/dynamic_permission.py 保持一致
 */

// ==================== 权限范围枚举 ====================

export type PermissionScope = 'global' | 'organization' | 'project' | 'asset' | 'custom';

export type PermissionType = 'role_based' | 'user_specific' | 'temporary' | 'conditional' | 'template_based';

export type PermissionRequestStatus = 'pending' | 'approved' | 'rejected';

export type PermissionAuditAction = 'ASSIGN' | 'REVOKE' | 'ASSIGN_TEMPORARY' | 'ASSIGN_CONDITIONAL';

// ==================== 动态权限 ====================

export interface DynamicPermission {
  id: string;
  user_id: string;
  permission_id: string;
  permission_type: PermissionType;
  scope: PermissionScope;
  scope_id?: string;
  conditions?: Record<string, unknown>;
  expires_at?: string;
  assigned_by: string;
  assigned_at: string;
  revoked_by?: string;
  revoked_at?: string;
  is_active: boolean;
}

export interface DynamicPermissionCreate {
  user_id: string;
  permission_id: string;
  permission_type: PermissionType;
  scope: PermissionScope;
  scope_id?: string;
  conditions?: Record<string, unknown>;
  expires_at?: string;
}

// ==================== 临时权限 ====================

export interface TemporaryPermission {
  id: string;
  user_id: string;
  permission_id: string;
  scope: PermissionScope;
  scope_id?: string;
  expires_at: string;
  assigned_by: string;
  assigned_at: string;
  is_active: boolean;
}

export interface TemporaryPermissionCreate {
  user_id: string;
  permission_id: string;
  scope: PermissionScope;
  scope_id?: string;
  expires_at: string;
}

// ==================== 条件权限 ====================

export interface ConditionalPermission {
  id: string;
  user_id: string;
  permission_id: string;
  scope: PermissionScope;
  scope_id?: string;
  conditions: Record<string, unknown>;
  assigned_by: string;
  assigned_at: string;
  is_active: boolean;
}

export interface ConditionalPermissionCreate {
  user_id: string;
  permission_id: string;
  scope: PermissionScope;
  scope_id?: string;
  conditions: Record<string, unknown>;
}

// ==================== 权限模板 ====================

export interface PermissionTemplate {
  id: string;
  name: string;
  description?: string;
  permission_ids: string[];
  scope: PermissionScope;
  conditions?: Record<string, unknown>;
  created_by: string;
  created_at: string;
  is_active: boolean;
}

export interface PermissionTemplateCreate {
  name: string;
  description?: string;
  permission_ids: string[];
  scope: PermissionScope;
  conditions?: Record<string, unknown>;
}

export interface PermissionTemplateUpdate {
  name?: string;
  description?: string;
  permission_ids?: string[];
  scope?: PermissionScope;
  conditions?: Record<string, unknown>;
  is_active?: boolean;
}

// ==================== 权限申请 ====================

export interface PermissionRequest {
  id: string;
  user_id: string;
  permission_ids: string[];
  scope: PermissionScope;
  scope_id?: string;
  reason: string;
  requested_duration_hours?: string;
  requested_conditions?: Record<string, unknown>;
  status: PermissionRequestStatus;
  approved_by?: string;
  approved_at?: string;
  approval_comment?: string;
  created_at: string;
  updated_at: string;
}

export interface PermissionRequestCreate {
  permission_ids: string[];
  scope: PermissionScope;
  scope_id?: string;
  reason: string;
  requested_duration_hours?: string;
  requested_conditions?: Record<string, unknown>;
}

export interface PermissionRequestApproval {
  status: 'approved' | 'rejected';
  approval_comment?: string;
}

// ==================== 权限委托 ====================

export interface PermissionDelegation {
  id: string;
  delegator_id: string;
  delegatee_id: string;
  permission_ids: string[];
  scope: PermissionScope;
  scope_id?: string;
  starts_at: string;
  ends_at: string;
  conditions?: Record<string, unknown>;
  reason?: string;
  is_active: boolean;
  created_at: string;
}

export interface PermissionDelegationCreate {
  delegatee_id: string;
  permission_ids: string[];
  scope: PermissionScope;
  scope_id?: string;
  starts_at?: string;
  ends_at: string;
  conditions?: Record<string, unknown>;
  reason?: string;
}

// ==================== 权限审计日志 ====================

export interface DynamicPermissionAudit {
  id: string;
  user_id: string;
  permission_id: string;
  action: PermissionAuditAction;
  permission_type: PermissionType;
  scope: PermissionScope;
  scope_id?: string;
  assigned_by: string;
  reason?: string;
  conditions?: Record<string, unknown>;
  created_at: string;
}

// ==================== 列表响应类型 ====================

export interface PermissionRequestListResponse {
  items: PermissionRequest[];
  total: number;
  page: number;
  pageSize: number;
  pages: number;
}

export interface PermissionDelegationListResponse {
  items: PermissionDelegation[];
  total: number;
  page: number;
  pageSize: number;
  pages: number;
}

export interface PermissionTemplateListResponse {
  items: PermissionTemplate[];
  total: number;
  page: number;
  pageSize: number;
  pages: number;
}

export interface DynamicPermissionAuditListResponse {
  items: DynamicPermissionAudit[];
  total: number;
  page: number;
  pageSize: number;
  pages: number;
}
