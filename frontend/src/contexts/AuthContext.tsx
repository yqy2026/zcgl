import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react'
import { message } from 'antd'
import { User, LoginCredentials } from '../types/auth'
import { AuthService } from '../services/authService'
import { AUTH_API } from '../constants/api'

interface AuthContextType {
  user: User | null
  isAuthenticated: boolean
  login: (credentials: LoginCredentials) => Promise<void>
  logout: () => Promise<void>
  loading: boolean
  error: string | null
}

interface AuthProviderProps {
  children: ReactNode
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

// Hook for components to use the auth context
export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}

const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // 检查本地存储的认证状态
  useEffect(() => {
    // 优先读取真正的JWT token，其次是auth_token
    const token = localStorage.getItem('token') || localStorage.getItem('auth_token')
    const storedUser = localStorage.getItem('user') || localStorage.getItem('user_info')

    if (token && storedUser) {
      try {
        const parsedUser = JSON.parse(storedUser)
        setUser(parsedUser)
        console.log('认证状态已从本地存储恢复')
      } catch (e) {
        console.error('Failed to parse stored user:', e)
        // 清除所有可能的认证相关存储
        localStorage.removeItem('user')
        localStorage.removeItem('user_info')
        localStorage.removeItem('token')
        localStorage.removeItem('auth_token')
      }
    }
  }, [])

  const login = async (credentials: LoginCredentials) => {
    try {
      console.log('🔐 AuthContext.login 开始登录', credentials);
      setLoading(true)
      setError(null)

      // 调用 AuthService 的登录方法
      const response = await AuthService.login(credentials) as any

      console.log('📤 AuthContext收到登录响应:', response);

      if (response.success && response.data) {
        setUser(response.data.user)
        console.log('✅ 用户状态已更新:', response.data.user);
        message.success(response.message || '登录成功')
      } else {
        throw new Error('登录响应格式错误')
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : '登录失败'
      setError(errorMessage)
      message.error(errorMessage)
      throw err
    } finally {
      setLoading(false)
    }
  }

  const logout = async () => {
    try {
      setLoading(true)

      // 直接清除本地存储的认证信息（避免循环调用）
      localStorage.removeItem('user')
      localStorage.removeItem('user_info')
      localStorage.removeItem('token')
      localStorage.removeItem('auth_token')
      localStorage.removeItem('refresh_token')
      localStorage.removeItem('refreshToken')
      localStorage.removeItem('permissions')

      setUser(null)
      message.success('已退出登录')
    } catch (err) {
      console.error('Logout error:', err)
      // 即使出错也要确保清除状态
      localStorage.removeItem('user')
      localStorage.removeItem('user_info')
      localStorage.removeItem('token')
      localStorage.removeItem('auth_token')
      localStorage.removeItem('refresh_token')
      localStorage.removeItem('refreshToken')
      localStorage.removeItem('permissions')
      setUser(null)
    } finally {
      setLoading(false)
    }
  }

  // Token自动刷新机制
  useEffect(() => {
    if (!user) return

    const token = localStorage.getItem('token') || localStorage.getItem('auth_token')
    if (!token) {
      console.log('没有访问令牌，需要重新登录')
      return
    }

    const refreshToken = async () => {
      try {
        const refresh_token = localStorage.getItem('refresh_token') || localStorage.getItem('refreshToken')
        if (!refresh_token) {
          console.log('没有刷新令牌，需要重新登录')
          await logout()
          return
        }

        // 调用刷新令牌API
        const response = await fetch(AUTH_API.REFRESH, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ refresh_token }),
        })

        if (response.ok) {
          const data = await response.json()
          if (data.access_token) {
            localStorage.setItem('token', data.access_token)
            if (data.refresh_token) {
              localStorage.setItem('refresh_token', data.refresh_token)
            }
            console.log('令牌已自动刷新')
          }
        } else {
          console.log('刷新令牌失败，需要重新登录')
          await logout()
        }
      } catch (error) {
        console.error('自动刷新令牌失败:', error)
        await logout()
      }
    }

    // 设置定时器，在令牌过期前5分钟刷新
    const setupTokenRefresh = () => {
      // 解析当前JWT token的过期时间
      const currentToken = localStorage.getItem('token') || localStorage.getItem('auth_token')
      if (!currentToken) {
        return
      }

      try {
        // 健壮的JWT token解析
        const tokenParts = currentToken.split('.')
        if (tokenParts.length !== 3) {
          console.warn('Token格式不正确，清理无效token')
          localStorage.removeItem('token')
          localStorage.removeItem('auth_token')
          return
        }

        let payload
        try {
          payload = JSON.parse(atob(tokenParts[1]))
        } catch (parseError) {
          console.warn('Token payload解析失败，清理无效token:', parseError)
          localStorage.removeItem('token')
          localStorage.removeItem('auth_token')
          return
        }

        if (!payload.exp) {
          console.warn('Token缺少过期时间，清理无效token')
          localStorage.removeItem('token')
          localStorage.removeItem('auth_token')
          return
        }

        const exp = payload.exp * 1000 // 转换为毫秒
        const now = Date.now()

        // 检查token是否已过期
        if (exp <= now) {
          console.log('Token已过期，清理无效token')
          localStorage.removeItem('token')
          localStorage.removeItem('auth_token')
          return
        }

        const timeUntilExpiry = exp - now

        // 在过期前5分钟刷新
        const refreshTime = Math.max(timeUntilExpiry - 5 * 60 * 1000, 60000) // 最少1分钟后刷新

        console.log(`令牌将在${Math.round(refreshTime/1000/60)}分钟后自动刷新`)

        const timer = setTimeout(refreshToken, refreshTime)
        return () => clearTimeout(timer)
      } catch (error) {
        console.error('解析token失败:', error)
        return
      }
    }

    const cleanup = setupTokenRefresh()

    return cleanup
  }, [user])

  const value: AuthContextType = {
    user,
    isAuthenticated: !!user,
    login,
    logout,
    loading,
    error,
  }

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  )
}

export { AuthProvider }
export default AuthContext

// 导出TypeScript类型供其他模块使用
export type { AuthContextType, AuthProviderProps }