import { apiClient } from '@/api/client';
import { SYSTEM_API, BACKUP_API } from '../constants/api';

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
  role: string;
  role_name: string;
  organization_id: string;
  organization_name: string;
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
  email: string;
  full_name: string;
  phone?: string;
  password: string;
  status: 'active' | 'inactive';
  role: string;
  organization_id: string;
}

export interface UpdateUserData {
  email?: string;
  full_name?: string;
  phone?: string;
  status?: 'active' | 'inactive';
  role?: string;
  organization_id?: string;
}

export const userService = {
  // 获取用户列表
  async getUsers(params?: {
    page?: number;
    page_size?: number;
    search?: string;
    status?: string;
    role?: string;
    organization_id?: string;
  }): Promise<UserListResponse> {
    const response = await api.get<unknown>(SYSTEM_API.USERS, { params });

    // 智能提取可能返回 items 或 UserListResponse
    const data = response.data;

    // 如果直接是 UserListResponse 格式（包含 items、total 等）
    if (
      data != null &&
      typeof data === 'object' &&
      'items' in data &&
      'total' in data &&
      'page' in data &&
      'page_size' in data
    ) {
      return data as UserListResponse;
    }

    // 如果只是 items 数组，包装成 UserListResponse
    if (Array.isArray(data)) {
      return {
        items: data as User[],
        total: data.length,
        page: 1,
        page_size: data.length,
        pages: 1,
      };
    }

    // 其他情况，返回空结构
    return {
      items: [],
      total: 0,
      page: 1,
      page_size: 20,
      pages: 0,
    };
  },

  // 获取用户详情
  async getUser(id: string) {
    const response = await api.get(SYSTEM_API.USER_DETAIL(id));
    return response.data;
  },

  // 创建用户
  async createUser(data: CreateUserData) {
    const response = await api.post(SYSTEM_API.USERS, data);
    return response.data;
  },

  // 更新用户
  async updateUser(id: string, data: UpdateUserData) {
    const response = await api.put(SYSTEM_API.USER_DETAIL(id), data);
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
  code: string;
  description: string;
  status: 'active' | 'inactive';
  permissions?: string[];
}

export interface UpdateRoleData {
  name?: string;
  code?: string;
  description?: string;
  status?: 'active' | 'inactive';
  permissions?: string[];
}

export const roleService = {
  // 获取角色列表
  async getRoles(params?: { page?: number; page_size?: number; search?: string; status?: string }) {
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
    const response = await api.post(SYSTEM_API.ROLES, data);
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
    const response = await api.put(SYSTEM_API.ROLE_DETAIL(id), { permissions });
    return response.data;
  },

  // 获取角色统计
  async getRoleStatistics() {
    // 暂时注释，后端可能没有这个端点
    // const response = await api.get('/roles/statistics')
    // return response.data
    return { total: 0, active: 0, inactive: 0 };
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
    return response.data as OperationLogListResult;
  },

  // 获取操作日志详情
  async getLog(id: string) {
    const response = await api.get(SYSTEM_API.AUDIT_LOG_DETAIL(id));
    return response.data;
  },

  // 获取操作日志统计
  async getLogStatistics(_params?: { start_date?: string; end_date?: string }) {
    // 暂时注释，后端可能没有这个端点
    // const response = await api.get('/logs/statistics', { params })
    // return response.data
    return { total: 0, today: 0, thisWeek: 0, thisMonth: 0 };
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
    // 暂时返回模拟数据，因为后端可能没有这个端点
    return { total: 0, active: 0, inactive: 0 };
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
