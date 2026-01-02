import { useState, useEffect, useCallback } from 'react'
import { message } from 'antd'
import { AuthService } from '../services/authService'
import type { User, LoginCredentials } from '../types/auth'

export const useAuth = () => {
  const [user, setUser] = useState<User | null>(AuthService.getLocalUser())
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // 初始化认证状态
  useEffect(() => {
    const initAuth = async () => {
      try {
        if (AuthService.isAuthenticated()) {
          const currentUser = AuthService.getLocalUser()
          const _permissions = AuthService.getLocalPermissions()

          setUser(currentUser)
          // 设置API请求头
          const token = localStorage.getItem('auth_token')
          if (token) {
            // 这里可以设置API默认的Authorization header
          }
        }
      } catch (error) {
        console.error('初始化认证状态失败:', error)
        // 清除可能损坏的本地存储
        AuthService.logout()
      }
    }

    initAuth()
  }, [])

  const login = useCallback(async (credentials: LoginCredentials) => {
    setLoading(true)
    setError(null)

    try {
      const response = await AuthService.login(credentials) as any

      if (response.success) {
        setUser(response.data.user)
        message.success('登录成功')
      } else {
        setError('用户名或密码错误')
      }
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : '登录失败，请稍后重试'
      setError(errorMessage)
      message.error(errorMessage)
    } finally {
      setLoading(false)
    }
  }, [])

  const logout = useCallback(async () => {
    setLoading(true)

    try {
      await AuthService.logout()
      setUser(null)
      setError(null)
      message.success('已安全登出')
    } catch (err: unknown) {
      console.error('登出失败:', err)
      // 即使API失败，也要清除本地状态
      setUser(null)
      setError(null)
    } finally {
      setLoading(false)
    }
  }, [])

  const refreshUser = useCallback(async () => {
    try {
      if (AuthService.isAuthenticated()) {
        const currentUser = await AuthService.getCurrentUser()
        setUser(currentUser)
      }
    } catch (error) {
      console.error('刷新用户信息失败:', error)
      // 如果刷新失败，尝试刷新token
      try {
        await AuthService.refreshToken()
        const currentUser = await AuthService.getCurrentUser()
        setUser(currentUser)
      } catch (refreshError) {
        console.error('刷新token失败:', refreshError)
        // 彻底登出
        await logout()
      }
    }
  }, [logout])

  const hasPermission = useCallback((resource: string, action: string): boolean => {
    return AuthService.hasPermission(resource, action)
  }, [])

  const hasAnyPermission = useCallback((permissions: Array<{ resource: string; action: string }>): boolean => {
    return AuthService.hasAnyPermission(permissions)
  }, [])

  const clearError = useCallback(() => {
    setError(null)
  }, [])

  return {
    user,
    loading,
    error,
    isAuthenticated: !!user,
    permissions: AuthService.getLocalPermissions(),
    login,
    logout,
    refreshUser,
    hasPermission,
    hasAnyPermission,
    clearError
  }
}