import type { Role } from '@/services/systemService';

export interface Permission {
  id: string;
  name: string;
  code: string;
  module: string;
  description: string;
  type: 'menu' | 'action' | 'data';
}

export interface RoleApiPermission {
  id: string;
}

export interface RoleApiItem {
  id: string;
  name: string;
  display_name?: string;
  description?: string;
  is_active?: boolean;
  permissions?: RoleApiPermission[];
  user_count?: number;
  created_at: string;
  updated_at: string;
  is_system_role?: boolean;
}

export type RoleListResponse = { items?: RoleApiItem[]; total?: number } | RoleApiItem[];

export interface PermissionApiItem {
  id: string;
  name?: string;
  display_name?: string;
  resource?: string;
  action?: string;
  description?: string;
}

export interface PermissionListResponse {
  data?: Record<string, PermissionApiItem[]>;
}

export interface RoleStatisticsApiResponse {
  data?: {
    total_roles?: number;
    active_roles?: number;
    system_roles?: number;
    custom_roles?: number;
  };
  total_roles?: number;
  active_roles?: number;
  system_roles?: number;
  custom_roles?: number;
}

export interface RoleStatistics {
  total: number;
  active: number;
  inactive: number;
  system: number;
  custom: number;
  avg_permissions: number;
}

export interface RoleFilters {
  keyword: string;
  status: string;
}

export interface RoleListQueryResult {
  items: Role[];
  total: number;
}

export interface RolePaginationState {
  current: number;
  pageSize: number;
}

export type Tone = 'primary' | 'success' | 'warning' | 'error' | 'neutral';
export type PermissionTagTone = 'primary' | 'success' | 'warning';
export type StatusTone = 'success' | 'error' | 'neutral';
