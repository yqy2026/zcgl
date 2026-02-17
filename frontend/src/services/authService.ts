import { AUTH_API } from '@/constants/api';
import { apiClient } from '@/api/client';
import { ApiErrorHandler } from '@/utils/responseExtractor';
import type { AuthResponse, StandardApiResponse } from '@/types/apiResponse';

import type { LoginCredentials, User, UserActivity } from '@/types/auth';
import { createLogger } from '@/utils/logger';
import { AuthStorage } from '@/utils/AuthStorage';

const logger = createLogger('AuthService');

// 权限接口
interface Permission {
  id?: string;
  name?: string;
  resource: string;
  action: string;
  description?: string;
  conditions?: Record<string, unknown>;
}

export class AuthService {
  // 用户登录
  static async login(credentials: LoginCredentials): Promise<StandardApiResponse<AuthResponse>> {
    try {
      logger.debug('开始登录流程', { identifier: credentials.identifier });

      // 使用API客户端，自动处理响应提取和错误
      const result = await apiClient.post(AUTH_API.LOGIN, credentials, {
        retry: {
          maxAttempts: 3,
          delay: 1000,
          backoffMultiplier: 2,
          retryCondition: (error: unknown) => {
            // 只对网络错误和5xx错误重试
            const axiosError = error as { response?: { status: number } };
            return (
              !axiosError.response ||
              (axiosError.response.status >= 500 && axiosError.response.status < 600)
            );
          },
        },
      });

      if (!result.success) {
        throw new Error(`登录失败: ${result.error}`);
      }

      const responseData = result.data as Record<string, unknown> & {
        user?: User;
        permissions?: AuthResponse['permissions'];
        message?: string;
        data?: {
          permissions?: Array<{
            resource: string;
            action: string;
            description?: string;
          }>;
        };
      };

      logger.debug('API响应数据', { responseData });

      // 验证响应数据结构
      if (responseData.user === undefined) {
        logger.error('登录响应数据格式不正确', undefined, { responseData });
        throw new Error('登录响应数据格式不正确');
      }

      const { user } = responseData;

      if (user === undefined) {
        throw new Error('未找到用户信息');
      }

      logger.debug('用户数据解析成功', { user });

      const permissions = Array.isArray(responseData.permissions)
        ? responseData.permissions
        : Array.isArray(responseData.data?.permissions)
          ? responseData.data?.permissions
          : [];

      // Keep metadata persistence aligned with cookie lifetime.
      const authPersistence = credentials.remember === true ? 'local' : 'session';
      AuthStorage.setAuthData({ user, permissions }, { persistence: authPersistence });

      return {
        success: true,
        data: {
          user,
          permissions,
        },
        message: (responseData.message as string) || '登录成功',
      };
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
      await apiClient.post(AUTH_API.LOGOUT, undefined, {
        retry: false, // 登出不重试
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
  static async refreshToken(): Promise<
    StandardApiResponse<{ message?: string; auth_mode?: string }>
  > {
    try {
      const result = await apiClient.post(AUTH_API.REFRESH, undefined, {
        retry: {
          maxAttempts: 2,
          delay: 500,
          backoffMultiplier: 1.5,
          retryCondition: (error: unknown) => {
            // 刷新令牌失败一般不重试，除非是网络问题
            const axiosError = error as { response?: unknown };
            return axiosError.response === undefined;
          },
        },
      });

      if (!result.success) {
        throw new Error(`令牌刷新失败: ${result.error}`);
      }

      const responseData =
        (result.data as { message?: string; auth_mode?: string } | undefined) ?? {};

      // Tokens are rotated in httpOnly cookies by backend
      // No need to update localStorage

      return {
        success: true,
        data: responseData, // 这里responseData已经转换过类型了
        message: '令牌刷新成功',
      };
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  // 获取当前用户信息
  static async getCurrentUser(options?: {
    skipAuthRefresh?: boolean;
    suppressAuthRedirect?: boolean;
  }): Promise<User> {
    try {
      const result = await apiClient.get(AUTH_API.PROFILE, {
        cache: false, // 用户信息不缓存
        skipAuthRefresh: options?.skipAuthRefresh === true,
        suppressAuthRedirect: options?.suppressAuthRedirect === true,
        retry: {
          maxAttempts: 2,
          delay: 500,
          backoffMultiplier: 2,
        },
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

  // 获取当前用户权限摘要（用于会话恢复）
  static async getCurrentUserPermissions(
    userId: string
  ): Promise<Array<{ resource: string; action: string; description?: string }>> {
    try {
      const result = await apiClient.get(`/roles/users/${userId}/permissions/summary`, {
        cache: false,
        retry: false,
      });

      if (!result.success) {
        throw new Error(`获取用户权限失败: ${result.error}`);
      }

      const responseData = result.data as
        | {
            permissions?: Array<{
              resource?: string;
              action?: string;
              description?: string;
            }>;
          }
        | undefined;

      if (!Array.isArray(responseData?.permissions)) {
        return [];
      }

      return responseData.permissions
        .filter(
          (
            permission
          ): permission is {
            resource: string;
            action: string;
            description?: string;
          } =>
            typeof permission.resource === 'string' &&
            permission.resource.trim() !== '' &&
            typeof permission.action === 'string' &&
            permission.action.trim() !== ''
        )
        .map(permission => ({
          resource: permission.resource,
          action: permission.action,
          description: permission.description,
        }));
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  // 检查认证状态 - 验证cookie是否有效
  static isAuthenticated(): boolean {
    // 检查本地存储的用户信息作为快速检查
    const user = AuthStorage.getCurrentUser();
    return user != null;
  }

  // 验证认证状态 - 通过API调用验证cookie有效性
  static async verifyAuth(): Promise<boolean> {
    try {
      // 调用/me端点验证cookie是否有效
      await apiClient.get(AUTH_API.PROFILE, {
        cache: false, // 不使用缓存
        retry: false, // 验证失败不重试
      });
      return true;
    } catch {
      return false;
    }
  }

  // 获取本地存储的用户信息
  static getLocalUser(): User | null {
    return AuthStorage.getCurrentUser();
  }

  // 获取本地存储的权限信息
  static getLocalPermissions(): Permission[] {
    return AuthStorage.getPermissions() as Permission[];
  }

  // 检查用户是否有特定权限
  static hasPermission(resource: string, action: string): boolean {
    const permissions = this.getLocalPermissions();

    return permissions.some(
      permission => permission.resource === resource && permission.action === action
    );
  }

  // 检查用户是否有任一权限（用于权限检查）
  static hasAnyPermission(permissions: Array<{ resource: string; action: string }>): boolean {
    const userPermissions = this.getLocalPermissions();

    return permissions.some(requiredPermission =>
      userPermissions.some(
        permission =>
          permission.resource === requiredPermission.resource &&
          permission.action === requiredPermission.action
      )
    );
  }

  // 清除认证数据
  private static clearAuthData(): void {
    // Tokens are in httpOnly cookies, cleared by backend logout endpoint
    // Only clear local auth metadata
    AuthStorage.clearAuthData();
    // Note: auth_token and refreshToken keys removed - tokens are now in cookies
  }

  // 修改密码
  static async changePassword(oldPassword: string, newPassword: string): Promise<void> {
    try {
      const result = await apiClient.post(
        AUTH_API.CHANGE_PASSWORD,
        {
          oldPassword,
          newPassword,
        },
        {
          retry: false, // 密码修改不重试
        }
      );

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
      const result = await apiClient.put(AUTH_API.PROFILE, profileData, {
        retry: {
          maxAttempts: 2,
          delay: 500,
          backoffMultiplier: 2,
        },
      });

      if (!result.success) {
        throw new Error(`更新个人资料失败: ${result.error}`);
      }

      // 更新本地存储的用户信息
      const updatedUser = result.data as User;
      const existing = AuthStorage.getAuthData();
      const existingPersistence = AuthStorage.getAuthPersistence();
      AuthStorage.setAuthData({
        user: updatedUser,
        permissions: existing?.permissions ?? [],
      }, {
        persistence: existingPersistence ?? 'local',
      });
      return updatedUser;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  // 获取用户活动记录
  static async getUserActivity(pageSize: number = 20): Promise<UserActivity[]> {
    try {
      const result = await apiClient.get(AUTH_API.SESSIONS, {
        params: { page_size: pageSize },
        cache: true,
      });

      if (!result.success) {
        throw new Error(`获取活动记录失败: ${result.error}`);
      }

      return (result.data as UserActivity[]) ?? [];
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }
}
