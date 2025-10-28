import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react'
import { message } from 'antd'
import { User, LoginResponse, TokenResponse } from '../types/auth'
import { api } from '../services/api'
import { AUTH_API } from '../constants/api'

interface AuthContextType {
  user: User | null
  isAuthenticated: boolean
  login: (username: string, password: string) => Promise<void>
  logout: () => Promise<void>
  loading: boolean
  error: string | null
}

interface AuthProviderProps {
  children: ReactNode
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export const useAuth = () => {
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
    const token = localStorage.getItem('auth_token')
    const storedUser = localStorage.getItem('user')

    if (token && storedUser) {
      try {
        const parsedUser = JSON.parse(storedUser)
        setUser(parsedUser)
      } catch (e) {
        console.error('Failed to parse stored user:', e)
        localStorage.removeItem('user')
        localStorage.removeItem('auth_token')
      }
    }
  }, [])

  const login = async (username: string, password: string) => {
    try {
      setLoading(true)
      setError(null)

      // 使用统一的API路径常量进行登录
      const response = await api.post(AUTH_API.LOGIN, {
        username,
        password,
      })

      const data = response.data

      if (data && data.user && data.tokens) {
        setUser(data.user)
        localStorage.setItem('auth_token', data.tokens.access_token)
        localStorage.setItem('user', JSON.stringify(data.user))
      } else {
        throw new Error('登录响应格式错误')
      }

      message.success('登录成功')
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : '登录失败'
      setError(errorMessage)
      message.error(errorMessage)
    } finally {
      setLoading(false)
    }
  }

  const logout = async () => {
    try {
      setLoading(true)

      // 使用统一的API路径常量进行登出
      try {
        await api.post(AUTH_API.LOGOUT)
      } catch (err) {
        console.warn('Logout API call failed:', err)
      }

      localStorage.removeItem('auth_token')
      localStorage.removeItem('user')
      setUser(null)

      message.success('已退出登录')
    } catch (err) {
      console.error('Logout error:', err)
    } finally {
      setLoading(false)
    }
  }

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