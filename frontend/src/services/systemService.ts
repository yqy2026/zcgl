import { enhancedApiClient } from '@/api/client'
import { SYSTEM_API, BACKUP_API } from '../constants/api'

// 使用增强型API客户端
const api = enhancedApiClient

// 用户管理相关接口
export interface User {
  id: string
  username: string
  email: string
  full_name: string
  phone: string
  status: 'active' | 'inactive' | 'locked'
  role: string
  role_name: string
  organization_id: string
  organization_name: string
  last_login: string | null
  created_at: string
  updated_at: string
  is_locked: boolean
  login_attempts: number
}

export interface CreateUserData {
  username: string
  email: string
  full_name: string
  phone?: string
  password: string
  status: 'active' | 'inactive'
  role: string
  organization_id: string
}

export interface UpdateUserData {
  email?: string
  full_name?: string
  phone?: string
  status?: 'active' | 'inactive'
  role?: string
  organization_id?: string
}

export const userService = {
  // 获取用户列表
  async getUsers(params?: {
    page?: number
    limit?: number
    search?: string
    status?: string
    role?: string
    organization_id?: string
  }) {
    const response = await api.get(SYSTEM_API.USERS, { params })
    return response.data
  },

  // 获取用户详情
  async getUser(id: string) {
    const response = await api.get(SYSTEM_API.USER_DETAIL(id))
    return response.data
  },

  // 创建用户
  async createUser(data: CreateUserData) {
    const response = await api.post(SYSTEM_API.USERS, data)
    return response.data
  },

  // 更新用户
  async updateUser(id: string, data: UpdateUserData) {
    const response = await api.put(SYSTEM_API.USER_DETAIL(id), data)
    return response.data
  },

  // 删除用户
  async deleteUser(id: string) {
    const response = await api.delete(SYSTEM_API.USER_DETAIL(id))
    return response.data
  },

  // 重置密码
  async resetPassword(id: string, password: string) {
    const response = await api.post(`${SYSTEM_API.USER_DETAIL(id)}/reset-password`, { password })
    return response.data
  },

  // 锁定用户
  async lockUser(id: string) {
    const response = await api.post(`${SYSTEM_API.USER_DETAIL(id)}/lock`)
    return response.data
  },

  // 解锁用户
  async unlockUser(id: string) {
    const response = await api.post(`${SYSTEM_API.USER_DETAIL(id)}/unlock`)
    return response.data
  },

  // 获取用户统计
  async getUserStatistics() {
    const response = await api.get(SYSTEM_API.USER_STATISTICS)
    return response.data
  }
}

// 角色管理相关接口
export interface Role {
  id: string
  name: string
  code: string
  description: string
  status: 'active' | 'inactive'
  permissions: string[]
  user_count: number
  created_at: string
  updated_at: string
  is_system: boolean
}

export interface CreateRoleData {
  name: string
  code: string
  description: string
  status: 'active' | 'inactive'
  permissions?: string[]
}

export interface UpdateRoleData {
  name?: string
  code?: string
  description?: string
  status?: 'active' | 'inactive'
  permissions?: string[]
}

export const roleService = {
  // 获取角色列表
  async getRoles(params?: {
    page?: number
    limit?: number
    search?: string
    status?: string
  }) {
    const response = await api.get(SYSTEM_API.ROLES, { params })
    return response.data
  },

  // 获取角色详情
  async getRole(id: string) {
    const response = await api.get(SYSTEM_API.ROLE_DETAIL(id))
    return response.data
  },

  // 创建角色
  async createRole(data: CreateRoleData) {
    const response = await api.post(SYSTEM_API.ROLES, data)
    return response.data
  },

  // 更新角色
  async updateRole(id: string, data: UpdateRoleData) {
    const response = await api.put(SYSTEM_API.ROLE_DETAIL(id), data)
    return response.data
  },

  // 删除角色
  async deleteRole(id: string) {
    const response = await api.delete(SYSTEM_API.ROLE_DETAIL(id))
    return response.data
  },

  // 获取权限列表
  async getPermissions() {
    const response = await api.get(SYSTEM_API.PERMISSIONS)
    return response.data
  },

  // 更新角色权限
  async updateRolePermissions(id: string, permissions: string[]) {
    const response = await api.put(SYSTEM_API.ROLE_DETAIL(id), { permissions })
    return response.data
  },

  // 获取角色统计
  async getRoleStatistics() {
    // 暂时注释，后端可能没有这个端点
    // const response = await api.get('/roles/statistics')
    // return response.data
    return { total: 0, active: 0, inactive: 0 }
  }
}

// 操作日志相关接口
export interface OperationLog {
  id: string
  user_id: string
  username: string
  user_name: string
  action: string
  action_name: string
  module: string
  module_name: string
  resource_type: string
  resource_id: string | null
  resource_name: string | null
  ip_address: string
  user_agent: string
  request_method: string
  request_url: string
  response_status: number
  response_time: number
  error_message: string | null
  details: Record<string, unknown> | null
  created_at: string
}

export const logService = {
  // 获取操作日志列表
  async getLogs(params?: {
    page?: number
    limit?: number
    search?: string
    user_id?: string
    module?: string
    action?: string
    start_date?: string
    end_date?: string
    response_status?: string
  }) {
    const response = await api.get(SYSTEM_API.AUDIT_LOGS, { params })
    return response.data
  },

  // 获取操作日志详情
  async getLog(id: string) {
    const response = await api.get(SYSTEM_API.AUDIT_LOG_DETAIL(id))
    return response.data
  },

  // 获取操作日志统计
  async getLogStatistics(params?: {
    start_date?: string
    end_date?: string
  }) {
    // 暂时注释，后端可能没有这个端点
    // const response = await api.get('/logs/statistics', { params })
    // return response.data
    return { total: 0, today: 0, thisWeek: 0, thisMonth: 0 }
  },

  // 导出操作日志
  async exportLogs(params?: {
    search?: string
    user_id?: string
    module?: string
    action?: string
    start_date?: string
    end_date?: string
    format?: 'excel' | 'csv'
  }) {
    const response = await api.get(SYSTEM_API.AUDIT_LOGS, {
      params: { ...params, export: true },
      responseType: 'blob'
    })
    return response.data
  }
}

// 组织管理相关接口（扩展已有功能）
export const organizationService = {
  // 获取组织统计信息
  async getOrganizationStatistics() {
    // 暂时返回模拟数据，因为后端可能没有这个端点
    return { total: 0, active: 0, inactive: 0 }
  },

  // 获取组织成员
  async getOrganizationMembers(organizationId: string) {
    const response = await api.get(`${SYSTEM_API.ORGANIZATIONS}/${organizationId}/members`)
    return response.data
  },

  // 添加组织成员
  async addOrganizationMember(organizationId: string, userId: string) {
    const response = await api.post(`${SYSTEM_API.ORGANIZATIONS}/${organizationId}/members`, { user_id: userId })
    return response.data
  },

  // 移除组织成员
  async removeOrganizationMember(organizationId: string, userId: string) {
    const response = await api.delete(`${SYSTEM_API.ORGANIZATIONS}/${organizationId}/members/${userId}`)
    return response.data
  }
}

// 系统设置相关接口
export interface SystemSettings {
  site_name: string
  site_description: string
  logo_url: string
  allow_registration: boolean
  default_role: string
  session_timeout: number
  password_policy: {
    min_length: number
    require_uppercase: boolean
    require_lowercase: boolean
    require_numbers: boolean
    require_special_chars: boolean
  }
}

export const systemService = {
  // 获取系统设置
  async getSettings() {
    const response = await api.get(SYSTEM_API.SETTINGS)
    return response.data
  },

  // 更新系统设置
  async updateSettings(data: Partial<SystemSettings>) {
    const response = await api.put(SYSTEM_API.SETTINGS, data)
    return response.data
  },

  // 获取系统信息
  async getSystemInfo() {
    const response = await api.get(SYSTEM_API.HEALTH)
    return response.data
  },

  // 备份系统数据
  async backupSystem() {
    const response = await api.post(BACKUP_API.CREATE)
    return response.data
  },

  // 恢复系统数据
  async restoreSystem(backupFile: File) {
    const formData = new FormData()
    formData.append('backup_file', backupFile)
    const response = await api.post(BACKUP_API.RESTORE, formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    })
    return response.data
  }
}
