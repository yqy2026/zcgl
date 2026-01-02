// import { api } from './index' // 已迁移到enhancedApiClient
import { AUTH_API } from '@/constants/api'
import { enhancedApiClient } from '@/api/client'
import { ApiErrorHandler } from '../utils/responseExtractor'
import type { AuthResponse } from '../types/api-response'
import type { LoginCredentials, User } from '../types/auth'
import { createLogger } from '../utils/logger'

const logger = createLogger('AuthService')

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
      logger.debug('开始登录流程', { username: credentials.username });

      // 使用增强型API客户端，自动处理响应提取和错误
      const result = await enhancedApiClient.post(AUTH_API.LOGIN, credentials, {
        retry: {
          maxAttempts: 3,
          delay: 1000,
          backoffMultiplier: 2,
          retryCondition: (error: unknown) => {
            // 只对网络错误和5xx错误重试
            const axiosError = error as { response?: { status: number } };
            return !axiosError.response || (axiosError.response.status >= 500 && axiosError.response.status < 600)
          }
        }
      });

      if (!result.success) {
        throw new Error(`登录失败: ${result.error}`);
      }

      const responseData = result.data as any;

      logger.debug('API响应数据', { responseData });

      // 验证响应数据结构
      if (!responseData.user || (!responseData.tokens && !responseData.token)) {
        logger.error('登录响应数据格式不正确', undefined, { responseData });
        throw new Error('登录响应数据格式不正确');
      }

      const { user } = responseData;

      logger.debug('用户数据解析成功', { user });

      // 处理tokens（新格式）或token（旧格式）
      let accessToken: string;
      let refreshToken: string;

      if (responseData.tokens) {
        // 新格式：嵌套的tokens对象
        accessToken = responseData.tokens.access_token;
        refreshToken = responseData.tokens.refresh_token;

        // 存储到多个键以确保兼容性
        localStorage.setItem('auth_token', accessToken);
        localStorage.setItem('token', accessToken); // 前端常用的键
        localStorage.setItem('refreshToken', refreshToken);
      } else if (responseData.token) {
        // 旧格式：单个token字段
        accessToken = responseData.token;
        refreshToken = responseData.token;

        localStorage.setItem('auth_token', accessToken);
        localStorage.setItem('token', accessToken);
        localStorage.setItem('refreshToken', refreshToken);
      } else {
        throw new Error('未找到访问令牌');
      }

      localStorage.setItem('user', JSON.stringify(user));
      // 权限信息暂时为空数组，后续可以从用户信息中获取
      localStorage.setItem('permissions', JSON.stringify([]));

      return {
        success: true,
        data: {
          user,
          token: accessToken,
          refreshToken: refreshToken,
          permissions: []
        },
        message: responseData.message || '登录成功'
      } as any;

    } catch (error) {
      // 使用统一的错误处理器
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  // 用户登出
  static async logout(): Promise<void> {
    try {
      // 使用增强型API客户端，即使失败也会清除本地存储
      await enhancedApiClient.post(AUTH_API.LOGOUT, undefined, {
        retry: false // 登出不重试
      });
    } catch (error) {
      // 即使登出API调用失败，也要清除本地存储
      logger.warn('登出API调用失败', { error: ApiErrorHandler.handleError(error).message });
    } finally {
      // 清除本地存储的认证信息
      this.clearAuthData();
    }
  }

  // 刷新令牌
  static async refreshToken(): Promise<AuthResponse> {
    try {
      const refreshToken = localStorage.getItem('refreshToken');
      if (!refreshToken) {
        throw new Error('没有刷新令牌');
      }

      const result = await enhancedApiClient.post(AUTH_API.REFRESH, {
        refreshToken
      }, {
        retry: {
          maxAttempts: 2,
          delay: 500,
          backoffMultiplier: 1.5,
          retryCondition: (error: unknown) => {
            // 刷新令牌失败一般不重试，除非是网络问题
            const axiosError = error as { response?: unknown };
            return !axiosError.response;
          }
        }
      });

      if (!result.success) {
        throw new Error(`令牌刷新失败: ${result.error}`);
      }

      const { token, permissions } = result.data as any;

      localStorage.setItem('auth_token', token);
      localStorage.setItem('permissions', JSON.stringify(permissions));

      return {
        success: true,
        data: result.data,
        message: '令牌刷新成功'
      } as any;

    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  // 获取当前用户信息
  static async getCurrentUser(): Promise<User> {
    try {
      const result = await enhancedApiClient.get(AUTH_API.PROFILE, {
        cache: false, // 用户信息不缓存
        retry: {
          maxAttempts: 2,
          delay: 500,
          backoffMultiplier: 2
        }
      });

      if (!result.success) {
        throw new Error(`获取用户信息失败: ${result.error}`);
      }

      // me端点直接返回用户数据，不是嵌套在user字段中
      return result.data as User;

    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
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
      // 验证JWT Token
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
      logger.error('Token验证失败', error instanceof Error ? error : new Error(String(error)))
      return false
    }
  }

  // 获取本地存储的用户信息
  static getLocalUser(): User | null {
    const userStr = localStorage.getItem('user')
    try {
      return userStr ? JSON.parse(userStr) : null
    } catch (error) {
      return null
    }
  }

  // 获取本地存储的权限信息
  static getLocalPermissions(): Permission[] {
    const permissionsStr = localStorage.getItem('permissions')
    try {
      return permissionsStr ? JSON.parse(permissionsStr) : []
    } catch (error) {
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

  // 清除认证数据
  private static clearAuthData(): void {
    localStorage.removeItem('auth_token');
    localStorage.removeItem('refreshToken');
    localStorage.removeItem('user');
    localStorage.removeItem('permissions');
  }

  // 修改密码
  static async changePassword(oldPassword: string, newPassword: string): Promise<void> {
    try {
      const result = await enhancedApiClient.post(AUTH_API.CHANGE_PASSWORD, {
        oldPassword,
        newPassword
      }, {
        retry: false // 密码修改不重试
      });

      if (!result.success) {
        throw new Error(`密码修改失败: ${result.error}`);
      }

    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
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
      const result = await enhancedApiClient.put(AUTH_API.CHANGE_PASSWORD, profileData, {
        retry: {
          maxAttempts: 2,
          delay: 500,
          backoffMultiplier: 2
        }
      });

      if (!result.success) {
        throw new Error(`更新个人资料失败: ${result.error}`);
      }

      // 更新本地存储的用户信息
      const updatedUser = result.data as User;
      localStorage.setItem('user', JSON.stringify(updatedUser));
      return updatedUser;

    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  // 获取用户活动记录
  static async getUserActivity(limit: number = 20): Promise<any[]> {
    try {
      const result = await enhancedApiClient.get(AUTH_API.SESSIONS, {
        params: { limit },
        cache: true
      });

      if (!result.success) {
        throw new Error(`获取活动记录失败: ${result.error}`);
      }

      return result.data as any;

    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }
}
