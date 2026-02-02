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
  id: string;
  name: string;
  resource: string;
  action: string;
  conditions?: Record<string, unknown>;
}

export class AuthService {
  // 用户登录
  static async login(credentials: LoginCredentials): Promise<StandardApiResponse<AuthResponse>> {
    try {
      logger.debug('开始登录流程', { username: credentials.username });

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
        tokens?: AuthResponse['tokens'];
        token?: string;
        message?: string;
        data?: {
          access_token?: string;
          refresh_token?: string;
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

      const tokenPayload =
        (responseData.tokens ?? responseData.data) as
          | (AuthResponse['tokens'] & { permissions?: AuthResponse['permissions'] })
          | undefined;

      const accessToken =
        tokenPayload?.access_token ??
        (typeof responseData.token === 'string' && responseData.token !== ''
          ? responseData.token
          : undefined);
      const refreshToken = tokenPayload?.refresh_token;
      const permissions = (Array.isArray(responseData.permissions)
        ? responseData.permissions
        : Array.isArray(tokenPayload?.permissions)
          ? tokenPayload?.permissions
          : []) as AuthResponse['permissions'];
      const hasAccessToken =
        accessToken != null && typeof accessToken === 'string' && accessToken !== '';
      const hasRefreshToken =
        refreshToken != null && typeof refreshToken === 'string' && refreshToken !== '';

      // Store user/permissions locally (tokens stay in httpOnly cookies)
      AuthStorage.setAuthData({ user, permissions });

      return {
        success: true,
        data: {
          user,
          tokens:
            hasAccessToken && hasRefreshToken
              ? {
                  access_token: accessToken,
                  refresh_token: refreshToken,
                  token_type: tokenPayload?.token_type ?? 'Bearer',
                  expires_in: tokenPayload?.expires_in ?? 3600,
                }
              : undefined,
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
      const result = await apiClient.post(
        AUTH_API.REFRESH,
        undefined,
        {
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
        }
      );

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
  static async getCurrentUser(): Promise<User> {
    try {
      const result = await apiClient.get(AUTH_API.PROFILE, {
        cache: false, // 用户信息不缓存
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
      AuthStorage.setAuthData({
        user: updatedUser,
        permissions: existing?.permissions ?? [],
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
