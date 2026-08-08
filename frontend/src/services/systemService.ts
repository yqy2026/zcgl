import dayjs from 'dayjs';
import { apiClient } from '@/api/client';
import { SYSTEM_API, BACKUP_API } from '@/constants/api';

// 使用增强型API客户端
const api = apiClient;

// 用户管理相关接口
export interface User {
  id: string;
  username: string;
  email: string;
  full_name: string;
  phone: string;
  status: 'active' | 'inactive' | 'locked';
  role_id?: string;
  roles?: string[];
  role_ids?: string[];
  account_type: 'human' | 'service' | 'system';
  organization_id: string | null;
  organization_name?: string | null;
  last_login: string | null;
  created_at: string;
  updated_at: string;
  is_locked: boolean;
  login_attempts: number;
}

export interface UserListResponse {
  items: User[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

interface UserApiResponse {
  id: string;
  username: string;
  email: string | null;
  full_name: string;
  phone: string;
  role_id?: string | null;
  roles?: string[];
  role_ids?: string[];
  is_active: boolean;
  is_locked: boolean;
  last_login_at: string | null;
  failed_login_attempts?: number;
  account_type: 'human' | 'service' | 'system';
  organization_id: string | null;
  created_at: string;
  updated_at: string;
}

interface UserListApiResponse {
  items: UserApiResponse[];
  total?: number;
  page?: number;
  page_size?: number;
  pages?: number;
  pagination?: {
    total: number;
    page: number;
    page_size: number;
    total_pages: number;
  };
}

export interface OrganizationOption {
  id: string;
  name: string;
}

export interface RoleOption {
  id: string;
  name: string;
}

export interface CreateUserData {
  username: string;
  email?: string;
  full_name: string;
  phone: string;
  password: string;
  status?: 'active' | 'inactive';
  role_id?: string;
  role_ids?: string[];
}

export interface UpdateUserData {
  email?: string;
  full_name?: string;
  phone?: string;
  status?: 'active' | 'inactive';
  role_id?: string;
  role_ids?: string[];
}

export type UserPartyRelationType = 'owner' | 'manager';

export interface UserPartyBinding {
  id: string;
  user_id: string;
  party_id: string;
  relation_type: UserPartyRelationType;
  valid_from: string;
  valid_to: string | null;
  created_at: string;
  updated_at: string;
}

export type UserPartyScopeOperation = 'create' | 'update' | 'close';

export interface UserPartyScopeProposal {
  operation: UserPartyScopeOperation;
  binding_id?: string;
  party_id?: string;
  relation_type?: UserPartyRelationType;
  valid_from?: string;
  valid_to?: string | null;
}

export interface UserPartyScopeIssue {
  code: string;
  node_type: 'organization' | 'party' | 'binding';
  safe_label: string;
  node_ref: string | null;
}

export interface UserPartyScopeState {
  source: 'explicit' | 'organization' | 'unrestricted' | 'none';
  scope_mode: 'owner' | 'manager' | 'all' | 'unrestricted' | 'none';
  owner_party_ids: string[];
  manager_party_ids: string[];
  organization_id: string | null;
  source_organization_id: string | null;
  next_transition_at: string | null;
  error_code: string | null;
  issues: UserPartyScopeIssue[];
}

export interface UserPartyScopeView extends UserPartyScopeState {
  user_id: string;
}

export interface UserPartyScopeImpact {
  before_current_binding_count: number;
  after_current_binding_count: number;
  scope_changed: boolean;
  uses_organization_default_after: boolean;
}

export interface UserPartyScopePreview {
  user_id: string;
  operation: UserPartyScopeOperation;
  before_scope: UserPartyScopeState;
  after_scope: UserPartyScopeState;
  impact: UserPartyScopeImpact;
  preview_token: string;
  expires_at: string;
}

export interface UserPartyScopeCommitRequest {
  preview_token: string;
  reason: string;
  idempotency_key: string;
}

export interface UserPartyScopeCommitResponse {
  binding: UserPartyBinding;
  operation: UserPartyScopeOperation;
  before_scope: UserPartyScopeState;
  after_scope: UserPartyScopeState;
  impact: UserPartyScopeImpact;
  committed_at: string;
  idempotent: boolean;
}

export interface UserPartyScopeBatchProposal extends UserPartyScopeProposal {
  user_id: string;
}

export interface UserPartyScopeBatchImpact {
  user_count: number;
  binding_change_count: number;
  scope_change_count: number;
  uses_organization_default_after_count: number;
}

export interface UserPartyScopeBatchPreviewItem {
  user: {
    id: string;
    username: string;
    full_name: string;
    account_type: 'human' | 'service' | 'system';
    organization_id: string | null;
  };
  operation: UserPartyScopeOperation;
  before_scope: UserPartyScopeState;
  after_scope: UserPartyScopeState;
  impact: UserPartyScopeImpact;
}

export interface UserPartyScopeBatchPreview {
  items: UserPartyScopeBatchPreviewItem[];
  impact: UserPartyScopeBatchImpact;
  preview_token: string;
  expires_at: string;
}

export interface UserPartyScopeBatchCommitRequest {
  preview_token: string;
  reason: string;
  idempotency_key: string;
}

export interface UserPartyScopeBatchCommitResponse {
  items: UserPartyScopeBatchPreviewItem[];
  impact: UserPartyScopeBatchImpact;
  committed_at: string;
  idempotent: boolean;
}

export interface UserOrganizationTransferProposal {
  organization_id: string;
}

export interface UserOrganizationTransferImpact {
  organization_changed: boolean;
  scope_changed: boolean;
  current_explicit_binding_count: number;
  uses_explicit_party_scope_after: boolean;
  cache_invalidation_required: boolean;
}

export interface UserOrganizationTransferPreview {
  user_id: string;
  before_scope: UserPartyScopeState;
  after_scope: UserPartyScopeState;
  impact: UserOrganizationTransferImpact;
  preview_token: string;
  expires_at: string;
}

export interface UserOrganizationTransferCommitRequest {
  preview_token: string;
  reason: string;
  idempotency_key: string;
}

export interface UserOrganizationTransferCommitResponse {
  user_id: string;
  organization_id: string;
  before_scope: UserPartyScopeState;
  after_scope: UserPartyScopeState;
  impact: UserOrganizationTransferImpact;
  committed_at: string;
  idempotent: boolean;
}
export const userService = {
  normalizeUserPayload(data: CreateUserData | UpdateUserData, includeStatus = true) {
    const { status, ...editableData } = data;
    const roleIds = Array.isArray(data.role_ids)
      ? data.role_ids.map(item => item.trim()).filter(item => item !== '')
      : undefined;
    const payload: Record<string, unknown> = { ...editableData };
    if (roleIds != null) {
      payload.role_ids = roleIds;
      payload.role_id = roleIds[0] ?? data.role_id;
    } else if (data.role_id !== undefined) {
      payload.role_id = data.role_id;
    }
    if (includeStatus && status != null) {
      payload.is_active = status === 'active';
    }
    return payload;
  },

  normalizeUserResponse(data: UserApiResponse): User {
    if (typeof data.is_active !== 'boolean' || typeof data.is_locked !== 'boolean') {
      throw new Error('用户接口响应缺少有效的账号状态字段');
    }
    return {
      id: data.id,
      username: data.username,
      email: data.email ?? '',
      full_name: data.full_name,
      phone: data.phone,
      status: data.is_locked ? 'locked' : data.is_active ? 'active' : 'inactive',
      role_id: data.role_id ?? undefined,
      roles: data.roles ?? [],
      role_ids: data.role_ids ?? [],
      account_type: data.account_type,
      organization_id: data.organization_id,
      organization_name: null,
      last_login: data.last_login_at,
      created_at: data.created_at,
      updated_at: data.updated_at,
      is_locked: data.is_locked,
      login_attempts: data.failed_login_attempts ?? 0,
    };
  },

  // 获取用户列表
  async getUsers(params?: {
    page?: number;
    page_size?: number;
    search?: string;
    status?: string;
    role_id?: string;
    organization_id?: string;
  }): Promise<UserListResponse> {
    const { status, ...baseParams } = params ?? {};
    const requestParams = {
      ...baseParams,
      ...(status === 'active' ? { is_active: true } : {}),
      ...(status === 'inactive' ? { is_active: false } : {}),
    };
    const response = await api.get<UserListApiResponse>(SYSTEM_API.USERS, {
      params: requestParams,
    });
    if (response.data == null) {
      return { items: [], total: 0, page: 1, page_size: 20, pages: 0 };
    }
    const pagination = response.data.pagination;
    return {
      items: response.data.items.map(userService.normalizeUserResponse),
      total: response.data.total ?? pagination?.total ?? 0,
      page: response.data.page ?? pagination?.page ?? 1,
      page_size: response.data.page_size ?? pagination?.page_size ?? 20,
      pages: response.data.pages ?? pagination?.total_pages ?? 0,
    };
  },

  // 获取用户详情
  async getUser(id: string) {
    const response = await api.get(SYSTEM_API.USER_DETAIL(id));
    return response.data;
  },

  // 获取用户主体绑定
  async getUserPartyBindings(userId: string, params?: { active_only?: boolean }) {
    const response = await api.get<UserPartyBinding[]>(`/users/${userId}/party-bindings`, {
      params,
    });
    return response.data ?? [];
  },

  // 预览用户主体范围变更
  async previewUserPartyScope(userId: string, proposal: UserPartyScopeProposal) {
    const response = await api.post<UserPartyScopePreview>(
      `/users/${userId}/party-bindings/preview`,
      proposal
    );
    return response.data;
  },

  // 提交已预览的用户主体范围变更
  async commitUserPartyScope(userId: string, request: UserPartyScopeCommitRequest) {
    const response = await api.post<UserPartyScopeCommitResponse>(
      `/users/${userId}/party-bindings/commit`,
      request
    );
    return response.data;
  },
  async previewUserPartyScopeBatch(proposals: UserPartyScopeBatchProposal[]) {
    const response = await api.post<UserPartyScopeBatchPreview>(
      '/users/party-bindings/batch/preview',
      { items: proposals }
    );
    return response.data;
  },

  async commitUserPartyScopeBatch(request: UserPartyScopeBatchCommitRequest) {
    const response = await api.post<UserPartyScopeBatchCommitResponse>(
      '/users/party-bindings/batch/commit',
      request
    );
    return response.data;
  },
  async getMyPartyScope(): Promise<UserPartyScopeView> {
    const response = await api.get<UserPartyScopeView>('/auth/me/party-scope');
    if (response.data == null) {
      throw new Error('获取当前用户有效主体范围失败');
    }
    return response.data;
  },

  async getUserPartyScope(userId: string): Promise<UserPartyScopeView> {
    const response = await api.get<UserPartyScopeView>(`/auth/users/${userId}/party-scope`);
    if (response.data == null) {
      throw new Error('获取用户有效主体范围失败');
    }
    return response.data;
  },
  async previewUserOrganizationTransfer(
    userId: string,
    proposal: UserOrganizationTransferProposal
  ) {
    const response = await api.post<UserOrganizationTransferPreview>(
      `${SYSTEM_API.USER_DETAIL(userId)}/organization/preview`,
      proposal
    );
    return response.data;
  },

  async commitUserOrganizationTransfer(
    userId: string,
    request: UserOrganizationTransferCommitRequest
  ) {
    const response = await api.put<UserOrganizationTransferCommitResponse>(
      `${SYSTEM_API.USER_DETAIL(userId)}/organization`,
      request
    );
    return response.data;
  },
  // 创建用户
  async createUser(data: CreateUserData) {
    const response = await api.post(
      SYSTEM_API.USERS,
      userService.normalizeUserPayload(data, false)
    );
    return response.data;
  },

  // 更新用户
  async updateUser(id: string, data: UpdateUserData) {
    const response = await api.put(
      SYSTEM_API.USER_DETAIL(id),
      userService.normalizeUserPayload(data)
    );
    return response.data;
  },

  // 删除用户
  async deleteUser(id: string) {
    const response = await api.delete(SYSTEM_API.USER_DETAIL(id));
    return response.data;
  },

  // 重置密码
  async resetPassword(id: string, password: string) {
    const response = await api.post(`${SYSTEM_API.USER_DETAIL(id)}/reset-password`, { password });
    return response.data;
  },

  // 锁定用户
  async lockUser(id: string) {
    const response = await api.post(`${SYSTEM_API.USER_DETAIL(id)}/lock`);
    return response.data;
  },

  // 解锁用户
  async unlockUser(id: string) {
    const response = await api.post(`${SYSTEM_API.USER_DETAIL(id)}/unlock`);
    return response.data;
  },

  // 获取用户统计
  async getUserStatistics() {
    const response = await api.get(SYSTEM_API.USER_STATISTICS);
    return response.data;
  },
};

// 角色管理相关接口
export interface Role {
  id: string;
  name: string;
  code: string;
  description: string;
  status: 'active' | 'inactive';
  permissions: string[];
  user_count: number;
  created_at: string;
  updated_at: string;
  is_system: boolean;
}

export interface CreateRoleData {
  name: string;
  display_name: string;
  description: string;
  is_active?: boolean;
  permission_ids?: string[];
}

export interface UpdateRoleData {
  display_name?: string;
  description?: string;
  is_active?: boolean;
  permission_ids?: string[];
}

export const roleService = {
  // 获取角色列表
  async getRoles(params?: {
    page?: number;
    page_size?: number;
    search?: string;
    is_active?: boolean;
  }) {
    const response = await api.get(SYSTEM_API.ROLES, { params });
    return response.data;
  },

  // 获取角色详情
  async getRole(id: string) {
    const response = await api.get(SYSTEM_API.ROLE_DETAIL(id));
    return response.data;
  },

  // 创建角色
  async createRole(data: CreateRoleData) {
    const response = await api.post(SYSTEM_API.ROLES, data, { retry: false });
    return response.data;
  },

  // 更新角色
  async updateRole(id: string, data: UpdateRoleData) {
    const response = await api.put(SYSTEM_API.ROLE_DETAIL(id), data);
    return response.data;
  },

  // 删除角色
  async deleteRole(id: string) {
    const response = await api.delete(SYSTEM_API.ROLE_DETAIL(id));
    return response.data;
  },

  // 获取权限列表
  async getPermissions() {
    const response = await api.get(SYSTEM_API.PERMISSIONS);
    return response.data;
  },

  // 更新角色权限
  async updateRolePermissions(id: string, permissions: string[]) {
    const response = await api.put(SYSTEM_API.ROLE_PERMISSIONS(id), {
      permission_ids: permissions,
    });
    return response.data;
  },

  // 获取角色统计
  async getRoleStatistics() {
    const response = await api.get(SYSTEM_API.ROLE_STATISTICS);
    return response.data;
  },
};

// 操作日志相关接口
export interface OperationLog {
  id: string;
  user_id: string;
  username?: string | null;
  user_name?: string | null;
  action: string;
  action_name?: string | null;
  module: string;
  module_name?: string | null;
  resource_type?: string | null;
  resource_id?: string | null;
  resource_name?: string | null;
  ip_address?: string | null;
  user_agent?: string | null;
  request_method?: string | null;
  request_url?: string | null;
  request_params?: string | Record<string, unknown> | unknown[] | null;
  request_body?: string | Record<string, unknown> | unknown[] | null;
  response_status?: number | null;
  response_time?: number | null;
  error_message?: string | null;
  details?: string | Record<string, unknown> | unknown[] | null;
  created_at: string;
}

export interface OperationLogListResult {
  items: OperationLog[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export interface LogStatistics {
  total: number;
  today: number;
  this_week: number;
  this_month: number;
  by_action: Record<string, number>;
  by_module: Record<string, number>;
  error_count: number;
  avg_response_time: number;
}

export const logService = {
  // 获取操作日志列表
  async getLogs(params?: {
    page?: number;
    page_size?: number;
    search?: string;
    user_id?: string;
    module?: string;
    action?: string;
    start_date?: string;
    end_date?: string;
    response_status?: string;
  }): Promise<OperationLogListResult> {
    const response = await api.get<OperationLogListResult>(SYSTEM_API.AUDIT_LOGS, { params });
    if (!response.success || response.data == null) {
      return {
        items: [],
        total: 0,
        page: params?.page ?? 1,
        page_size: params?.page_size ?? 20,
        pages: 0,
      };
    }

    return response.data;
  },

  // 获取操作日志详情
  async getLog(id: string) {
    const response = await api.get(SYSTEM_API.AUDIT_LOG_DETAIL(id));
    return response.data;
  },

  // 获取操作日志统计
  async getLogStatistics(params?: { start_date?: string; end_date?: string; days?: number }) {
    const derivedDays = (() => {
      if (typeof params?.days === 'number') {
        return params.days;
      }
      if (params?.start_date && params?.end_date) {
        const start = dayjs(params.start_date);
        const end = dayjs(params.end_date);
        if (start.isValid() && end.isValid()) {
          return Math.max(end.diff(start, 'day') + 1, 1);
        }
      }
      return 30;
    })();

    const result = await api.get<{
      total_logs?: number;
      daily_statistics?: Record<string, number>;
      error_statistics?: { total_errors?: number };
    }>(SYSTEM_API.AUDIT_LOG_STATISTICS, { params: { days: derivedDays } });

    if (!result.success || result.data == null) {
      return {
        total: 0,
        today: 0,
        this_week: 0,
        this_month: 0,
        by_action: {},
        by_module: {},
        error_count: 0,
        avg_response_time: 0,
      };
    }

    const dailyStats = result.data.daily_statistics ?? {};
    const todayKey = dayjs().format('YYYY-MM-DD');
    const today = dailyStats[todayKey] ?? 0;

    let thisWeek = 0;
    let thisMonth = 0;

    for (const [dateKey, count] of Object.entries(dailyStats)) {
      const date = dayjs(dateKey);
      if (date.isValid()) {
        if (date.isSame(dayjs(), 'week')) {
          thisWeek += count;
        }
        if (date.isSame(dayjs(), 'month')) {
          thisMonth += count;
        }
      }
    }

    return {
      total: result.data.total_logs ?? 0,
      today,
      this_week: thisWeek,
      this_month: thisMonth,
      by_action: {},
      by_module: {},
      error_count: result.data.error_statistics?.total_errors ?? 0,
      avg_response_time: 0,
    };
  },

  // 导出操作日志
  async exportLogs(params?: {
    search?: string;
    user_id?: string;
    module?: string;
    action?: string;
    start_date?: string;
    end_date?: string;
    format?: 'excel' | 'csv';
  }) {
    const response = await api.get(SYSTEM_API.AUDIT_LOGS, {
      params: { ...params, export: true },
      responseType: 'blob',
    });
    return response.data;
  },
};

// 组织管理相关接口（扩展已有功能）
export const organizationService = {
  // 获取组织统计信息
  async getOrganizationStatistics() {
    const response = await api.get<{
      total: number;
      active: number;
      inactive: number;
      by_type?: Record<string, number>;
      by_level?: Record<string, number>;
    }>(SYSTEM_API.ORGANIZATION_STATISTICS);

    if (!response.success || response.data == null) {
      return {
        total: 0,
        active: 0,
        inactive: 0,
        by_type: {},
        by_level: {},
      };
    }

    return response.data;
  },

  // 获取组织成员
  async getOrganizationMembers(organizationId: string) {
    const response = await api.get(`${SYSTEM_API.ORGANIZATIONS}/${organizationId}/members`);
    return response.data;
  },

  // 添加组织成员
  async addOrganizationMember(organizationId: string, userId: string) {
    const response = await api.post(`${SYSTEM_API.ORGANIZATIONS}/${organizationId}/members`, {
      user_id: userId,
    });
    return response.data;
  },

  // 移除组织成员
  async removeOrganizationMember(organizationId: string, userId: string) {
    const response = await api.delete(
      `${SYSTEM_API.ORGANIZATIONS}/${organizationId}/members/${userId}`
    );
    return response.data;
  },
};

// 系统设置相关接口
export interface SystemSettings {
  site_name: string;
  site_description: string;
  logo_url: string;
  allow_registration: boolean;
  default_role: string;
  session_timeout: number;
  password_policy: {
    min_length: number;
    require_uppercase: boolean;
    require_lowercase: boolean;
    require_numbers: boolean;
    require_special_chars: boolean;
  };
}

export interface SystemInfo {
  version: string;
  build_time: string;
  database_status: string;
  api_version: string;
  environment: string;
}

export const systemService = {
  // 获取系统设置
  async getSettings(): Promise<SystemSettings> {
    const result = await api.get<SystemSettings>(SYSTEM_API.SETTINGS);
    if (!result.success) {
      throw new Error(result.error ?? '获取系统设置失败');
    }
    return result.data!;
  },

  // 更新系统设置
  async updateSettings(data: Partial<SystemSettings>) {
    const response = await api.put(SYSTEM_API.SETTINGS, data);
    return response.data;
  },

  // 获取系统信息
  async getSystemInfo(): Promise<SystemInfo> {
    const result = await api.get<SystemInfo>(SYSTEM_API.HEALTH);
    if (!result.success) {
      throw new Error(result.error ?? '获取系统信息失败');
    }
    return result.data!;
  },

  // 备份系统数据
  async backupSystem() {
    const response = await api.post(BACKUP_API.CREATE);
    return response.data;
  },

  // 恢复系统数据
  async restoreSystem(backupFile: File) {
    const formData = new FormData();
    formData.append('backup_file', backupFile);
    const response = await api.post(BACKUP_API.RESTORE, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },
};
