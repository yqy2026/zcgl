import { api } from './index'
import type { LoginCredentials, AuthResponse, User } from '../types/auth'

export class AuthService {
  // 用户登录
  static async login(credentials: LoginCredentials): Promise<AuthResponse> {
    try {
      const response = await api.post('/auth/login', credentials)

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
    } catch (error: any) {
      throw new Error(error.response?.data?.error?.message || error.message || '网络错误，请稍后重试')
    }
  }

  // 用户登出
  static async logout(): Promise<void> {
    try {
      await api.post('/auth/logout')
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

      const response = await api.post('/auth/refresh', {
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
    } catch (error: any) {
      throw new Error(error.response?.data?.error?.message || error.message || '网络错误')
    }
  }

  // 获取当前用户信息
  static async getCurrentUser(): Promise<User> {
    try {
      const response = await api.get('/auth/me')

      if (response.data.success) {
        return response.data.data  // 修复：me端点直接返回用户数据，不是嵌套在user字段中
      } else {
        throw new Error('获取用户信息失败')
      }
    } catch (error: any) {
      throw new Error(error.response?.data?.error?.message || error.message || '网络错误')
    }
  }

  // 检查本地认证状态
  static isAuthenticated(): boolean {
    const token = localStorage.getItem('auth_token')
    const user = localStorage.getItem('user')

    if (!token || !user) {
      return false
    }

    try {
      // 检查token是否过期（简单检查，实际应该解析JWT）
      const tokenData = JSON.parse(atob(token.split('.')[1] || '{}'))
      const currentTime = Date.now() / 1000

      return tokenData.exp > currentTime
    } catch {
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
  static getLocalPermissions(): any[] {
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
      await api.post('/auth/change-password', {
        oldPassword,
        newPassword
      })
    } catch (error: any) {
      throw new Error(error.response?.data?.error?.message || error.message || '密码修改失败')
    }
  }

  // 更新个人资料
  static async updateProfile(profileData: any): Promise<User> {
    try {
      const response = await api.put('/auth/profile', profileData)

      if (response.data.success) {
        // 更新本地存储的用户信息
        const updatedUser = response.data.data
        localStorage.setItem('user', JSON.stringify(updatedUser))
        return updatedUser
      } else {
        throw new Error('更新个人资料失败')
      }
    } catch (error: any) {
      throw new Error(error.response?.data?.error?.message || error.message || '更新个人资料失败')
    }
  }

  // 获取用户活动记录
  static async getUserActivity(limit: number = 20): Promise<any[]> {
    try {
      const response = await api.get(`/auth/activity?limit=${limit}`)

      if (response.data.success) {
        return response.data.data
      } else {
        throw new Error('获取活动记录失败')
      }
    } catch (error: any) {
      throw new Error(error.response?.data?.error?.message || error.message || '获取活动记录失败')
    }
  }
}