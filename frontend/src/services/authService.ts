import { api } from './index'
import { AUTH_API } from '@/constants/api'
import type { LoginCredentials, AuthResponse, User } from '../types/auth'

// API 错误接口
interface ApiError {
  response?: {
    data?: {
      error?: {
        message?: string
      }
      message?: string
    }
  }
  message?: string
}

// 权限接口
interface Permission {
  id: string
  name: string
  resource: string
  action: string
  conditions?: Record<string, unknown>
}

export class AuthService {
  // 用户登录
  static async login(credentials: LoginCredentials): Promise<AuthResponse> {
    try {
      const response = await api.post(AUTH_API.LOGIN, credentials)

      // 后端返回的数据结构：{user, tokens: {access_token, refresh_token, ...}, message}
      if (response.data.user && response.data.tokens) {
        const { user, tokens } = response.data

        // 存储认证信息到localStorage
        localStorage.setItem('auth_token', tokens.access_token)
        localStorage.setItem('refreshToken', tokens.refresh_token)
        localStorage.setItem('user', JSON.stringify(user))
        // 权限信息暂时为空数组，后续可以从用户信息中获取
        localStorage.setItem('permissions', JSON.stringify([]))

        // 返回符合前端期望的数据结构
        return {
          success: true,
          data: {
            user,
            token: tokens.access_token,
            refreshToken: tokens.refresh_token,
            permissions: []
          },
          message: response.data.message || '登录成功'
        }
      } else {
        throw new Error(response.data.error?.message || '登录失败')
      }
    } catch (error: unknown) {
      const apiError = error as ApiError
      throw new Error(apiError.response?.data?.error?.message || apiError.message || '网络错误，请稍后重试')
    }
  }

  // 用户登出
  static async logout(): Promise<void> {
    try {
      await api.post(AUTH_API.LOGOUT)
    } catch (error) {
      // 即使登出API调用失败，也要清除本地存储
      console.error('登出API调用失败:', error)
    } finally {
      // 清除本地存储的认证信息
      localStorage.removeItem('auth_token')
      localStorage.removeItem('refreshToken')
      localStorage.removeItem('user')
      localStorage.removeItem('permissions')
    }
  }

  // 刷新令牌
  static async refreshToken(): Promise<AuthResponse> {
    try {
      const refreshToken = localStorage.getItem('refreshToken')
      if (!refreshToken) {
        throw new Error('没有刷新令牌')
      }

      const response = await api.post(AUTH_API.REFRESH, {
        refreshToken
      })

      if (response.data.success) {
        const { token, permissions } = response.data.data

        localStorage.setItem('auth_token', token)
        localStorage.setItem('permissions', JSON.stringify(permissions))

        return response.data
      } else {
        throw new Error('令牌刷新失败')
      }
    } catch (error: unknown) {
      const apiError = error as ApiError
      throw new Error(apiError.response?.data?.error?.message || apiError.message || '网络错误')
    }
  }

  // 获取当前用户信息
  static async getCurrentUser(): Promise<User> {
    try {
      const response = await api.get(AUTH_API.PROFILE)

      if (response.data.success) {
        return response.data.data  // 修复：me端点直接返回用户数据，不是嵌套在user字段中
      } else {
        throw new Error('获取用户信息失败')
      }
    } catch (error: unknown) {
      const apiError = error as ApiError
      throw new Error(apiError.response?.data?.error?.message || apiError.message || '网络错误')
    }
  }

  // 开发环境模拟登录
  static mockLogin(username: string = 'admin'): void {
    // 仅在开发环境启用Mock登录
    if (import.meta.env.DEV) {
      const mockUser = {
        id: '1',
        username: username,
        email: `${username}@example.com`,
        full_name: username === 'admin' ? '系统管理员' : '测试用户',
        roles: ['admin'],
        organization: {
          id: '1',
          name: '默认组织'
        }
      }

      const mockToken = 'mock_token_' + Date.now()

      localStorage.setItem('auth_token', mockToken)
      localStorage.setItem('user', JSON.stringify(mockUser))
      localStorage.setItem('permissions', JSON.stringify([
        { resource: 'assets', action: 'view' },
        { resource: 'assets', action: 'create' },
        { resource: 'assets', action: 'edit' },
        { resource: 'contracts', action: 'view' },
        { resource: 'contracts', action: 'create' },
        { resource: 'dashboard', action: 'view' },
        { resource: 'system', action: 'view' }
      ]))

    } else {
      throw new Error('⚠️ Mock登录仅在开发环境可用')
    }
  }

  // 检查本地认证状态
  static isAuthenticated(): boolean {
    const token = localStorage.getItem('auth_token')
    const user = localStorage.getItem('user')

    // 必须同时存在token和user信息
    if (!token || !user) {
      return false
    }

    try {
      // Mock token仅在开发环境有效
      if (token.startsWith('mock_token_')) {
        return import.meta.env.DEV // 仅开发环境返回true
      }

      // 生产环境验证JWT Token
      const tokenParts = token.split('.')
      if (tokenParts.length !== 3) {
        return false
      }

      const tokenData = JSON.parse(atob(tokenParts[1]))
      const currentTime = Date.now() / 1000

      // 检查token是否过期
      if (!tokenData.exp || tokenData.exp <= currentTime) {
        // Token已过期,清除本地存储
        this.logout()
        return false
      }

      return true
    } catch (error) {
      console.error('Token验证失败:', error)
      return false
    }
  }

  // 获取本地存储的用户信息
  static getLocalUser(): User | null {
    const userStr = localStorage.getItem('user')
    try {
      return userStr ? JSON.parse(userStr) : null
    } catch {
      return null
    }
  }

  // 获取本地存储的权限信息
  static getLocalPermissions(): Permission[] {
    const permissionsStr = localStorage.getItem('permissions')
    try {
      return permissionsStr ? JSON.parse(permissionsStr) : []
    } catch {
      return []
    }
  }

  // 检查用户是否有特定权限
  static hasPermission(resource: string, action: string): boolean {
    const permissions = this.getLocalPermissions()

    return permissions.some(permission =>
      permission.resource === resource &&
      permission.action === action
    )
  }

  // 检查用户是否有任一权限（用于权限检查）
  static hasAnyPermission(permissions: Array<{ resource: string; action: string }>): boolean {
    const userPermissions = this.getLocalPermissions()

    return permissions.some(requiredPermission =>
      userPermissions.some(permission =>
        permission.resource === requiredPermission.resource &&
        permission.action === requiredPermission.action
      )
    )
  }

  // 修改密码
  static async changePassword(oldPassword: string, newPassword: string): Promise<void> {
    try {
      await api.post(AUTH_API.CHANGE_PASSWORD, {
        oldPassword,
        newPassword
      })
    } catch (error: unknown) {
      const apiError = error as ApiError
      throw new Error(apiError.response?.data?.error?.message || apiError.message || '密码修改失败')
    }
  }

  // 更新个人资料
  static async updateProfile(profileData: {
    fullName?: string;
    email?: string;
    phone?: string;
    avatar?: string;
  }): Promise<User> {
    try {
      const response = await api.put(AUTH_API.PROFILE, profileData)

      if (response.data.success) {
        // 更新本地存储的用户信息
        const updatedUser = response.data.data
        localStorage.setItem('user', JSON.stringify(updatedUser))
        return updatedUser
      } else {
        throw new Error('更新个人资料失败')
      }
    } catch (error: unknown) {
      const apiError = error as ApiError
      throw new Error(apiError.response?.data?.error?.message || apiError.message || '更新个人资料失败')
    }
  }

  // 获取用户活动记录
  static async getUserActivity(limit: number = 20): Promise<any[]> {
    try {
      const response = await api.get(`${AUTH_API.SESSIONS}?limit=${limit}`)

      if (response.data.success) {
        return response.data.data
      } else {
        throw new Error('获取活动记录失败')
      }
    } catch (error: unknown) {
      const apiError = error as ApiError
      throw new Error(apiError.response?.data?.error?.message || apiError.message || '获取活动记录失败')
    }
  }
}
