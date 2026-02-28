import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react';
import { User, LoginCredentials, Permission } from '@/types/auth';
import type { CapabilityItem } from '@/types/capability';
import { AuthService } from '@/services/authService';
import { AuthStorage } from '@/utils/AuthStorage';
import { createLogger } from '@/utils/logger';
import { MessageManager } from '@/utils/messageManager';
import { CSRF_CONFIG } from '@/api/config';

const logger = createLogger('AuthContext');

interface AuthContextType {
  user: User | null;
  permissions: Permission[];
  capabilities: CapabilityItem[];
  capabilitiesLoading: boolean;
  isAuthenticated: boolean;
  isAdmin: boolean;
  initializing: boolean;
  login: (credentials: LoginCredentials) => Promise<void>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
  refreshCapabilities: (options?: { forceRefresh?: boolean }) => Promise<void>;
  /** @deprecated Phase 3 迁移期兼容导出，后续统一改为 canPerform/useCapabilities。 */
  hasPermission: (resource: string, action: string) => boolean;
  /** @deprecated Phase 3 迁移期兼容导出，后续统一改为 canPerform/useCapabilities。 */
  hasAnyPermission: (permissions: Array<{ resource: string; action: string }>) => boolean;
  clearError: () => void;
  loading: boolean;
  error: string | null;
}

interface AuthProviderProps {
  children: React.ReactNode;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

const hasCookieValue = (cookieName: string): boolean => {
  if (typeof document === 'undefined') {
    return false;
  }

  const cookies = document.cookie.split(';');
  const encodedCookieName = `${encodeURIComponent(cookieName)}=`;

  for (const cookie of cookies) {
    const trimmed = cookie.trim();
    if (trimmed === '') {
      continue;
    }

    if (trimmed.startsWith(encodedCookieName)) {
      return true;
    }
  }

  return false;
};

// Hook for components to use the auth context
export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}

const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [permissions, setPermissions] = useState<Permission[]>(() => {
    return AuthStorage.getPermissions() as Permission[];
  });
  const [capabilities, setCapabilities] = useState<CapabilityItem[]>(() => {
    return AuthStorage.getCapabilities();
  });
  const [capabilitiesLoading, setCapabilitiesLoading] = useState<boolean>(() => {
    const hasStoredUser = AuthStorage.getCurrentUser() != null;
    return hasStoredUser || hasCookieValue(CSRF_CONFIG.COOKIE_NAME);
  });
  const [loading, setLoading] = useState(false);
  const [initializing, setInitializing] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const currentUserIdRef = useRef<string | null>(AuthStorage.getCurrentUser()?.id ?? null);
  const capabilityRequestVersionRef = useRef(0);

  const persistAuthDataSafely = useCallback(
    (
      nextUser: User,
      nextPermissions: Array<{ resource: string; action: string; description?: string }>,
      persistence: 'local' | 'session'
    ) => {
      try {
        AuthStorage.setAuthData(
          {
            user: nextUser,
            permissions: nextPermissions,
          },
          { persistence }
        );
      } catch (storageError) {
        logger.warn('写入本地认证元数据失败，不影响当前会话', {
          userId: nextUser.id,
          error: storageError instanceof Error ? storageError.message : String(storageError),
        });
      }
    },
    []
  );

  const invalidateCapabilityRequests = useCallback(() => {
    capabilityRequestVersionRef.current += 1;
  }, []);

  const refreshCapabilitiesByUser = useCallback(
    async (userId: string, options?: { forceRefresh?: boolean }) => {
      const requestVersion = capabilityRequestVersionRef.current + 1;
      capabilityRequestVersionRef.current = requestVersion;
      setCapabilitiesLoading(true);

      try {
        const snapshot = await AuthService.getCurrentUserCapabilities({
          forceRefresh: options?.forceRefresh === true,
        });

        const isCurrentRequest = capabilityRequestVersionRef.current === requestVersion;
        const isSameUser = currentUserIdRef.current === userId;
        if (isCurrentRequest !== true || isSameUser !== true) {
          return;
        }

        AuthStorage.setCapabilitiesSnapshot(snapshot);
        setCapabilities(snapshot.capabilities);
      } catch (capabilityError) {
        const isCurrentRequest = capabilityRequestVersionRef.current === requestVersion;
        const isSameUser = currentUserIdRef.current === userId;
        if (isCurrentRequest !== true || isSameUser !== true) {
          return;
        }

        logger.warn('拉取 capabilities 失败，降级为空能力集', {
          error:
            capabilityError instanceof Error ? capabilityError.message : String(capabilityError),
        });
        AuthStorage.clearCapabilitiesSnapshot();
        setCapabilities([]);
      } finally {
        if (capabilityRequestVersionRef.current === requestVersion) {
          setCapabilitiesLoading(false);
        }
      }
    },
    []
  );

  const refreshCapabilities = useCallback(
    async (options?: { forceRefresh?: boolean }) => {
      const userId = currentUserIdRef.current;
      if (userId == null || userId === '') {
        invalidateCapabilityRequests();
        AuthStorage.clearCapabilitiesSnapshot();
        setCapabilities([]);
        setCapabilitiesLoading(false);
        return;
      }
      await refreshCapabilitiesByUser(userId, options);
    },
    [invalidateCapabilityRequests, refreshCapabilitiesByUser]
  );

  const triggerCapabilitiesRefresh = useCallback(
    (userId: string, options?: { forceRefresh?: boolean }) => {
      void refreshCapabilitiesByUser(userId, options).catch(capabilityError => {
        logger.error(
          '后台刷新 capabilities 发生未处理异常',
          capabilityError instanceof Error ? capabilityError : new Error(String(capabilityError))
        );
      });
    },
    [refreshCapabilitiesByUser]
  );

  // 检查本地存储的认证状态
  useEffect(() => {
    let isMounted = true;

    const resolvePermissionsWithFallback = async (
      userId: string,
      fallbackPermissions: Array<{ resource: string; action: string; description?: string }>
    ) => {
      try {
        return await AuthService.getCurrentUserPermissions(userId);
      } catch (permissionError) {
        logger.warn('获取权限摘要失败，使用兜底权限', {
          userId,
          error:
            permissionError instanceof Error ? permissionError.message : String(permissionError),
        });
        return fallbackPermissions;
      }
    };

    const restoreAuth = async () => {
      const authData = AuthStorage.getAuthData();
      const storedUser = authData?.user ?? null;
      const storedPermissions = authData?.permissions ?? [];
      const authPersistence = AuthStorage.getAuthPersistence() ?? 'session';

      try {
        if (storedUser != null) {
          if (isMounted) {
            setUser(storedUser);
            setPermissions(storedPermissions as Permission[]);
            setError(null);
          }
          currentUserIdRef.current = storedUser.id;
          logger.debug('认证状态已从本地存储恢复', { userId: storedUser.id });

          // 清理旧的 localStorage 键
          localStorage.removeItem('user');
          localStorage.removeItem('user_info');

          // 以当前Cookie会话为准，避免跨标签账号切换后展示旧用户
          logger.debug('开始校验并同步当前登录会话');
          const currentUser = await AuthService.getCurrentUser();
          const isCrossUserSwitch = currentUser.id !== storedUser.id;
          const fallbackPermissions = currentUser.id === storedUser.id ? storedPermissions : [];
          const permissions = await resolvePermissionsWithFallback(
            currentUser.id,
            fallbackPermissions
          );
          persistAuthDataSafely(currentUser, permissions, authPersistence);

          if (isCrossUserSwitch) {
            // 跨用户切换时先失效旧能力快照，避免新用户短暂继承旧能力集。
            invalidateCapabilityRequests();
            AuthStorage.clearCapabilitiesSnapshot();
            if (isMounted) {
              setCapabilities([]);
            }
          }

          if (isMounted) {
            setUser(currentUser);
            setPermissions(permissions as Permission[]);
            setError(null);
          }
          currentUserIdRef.current = currentUser.id;
          triggerCapabilitiesRefresh(currentUser.id, { forceRefresh: true });

          if (currentUser.id !== storedUser.id) {
            logger.info('检测到跨标签账号切换，已同步当前会话用户', {
              fromUserId: storedUser.id,
              toUserId: currentUser.id,
            });
          }
          logger.debug('登录会话校验并同步完成', { userId: currentUser.id });
          return;
        }

        // 无本地元数据时，只有检测到会话Cookie提示才进行恢复探测。
        // 这样可避免匿名访客无Cookie时触发不必要的/auth/me与重定向链路。
        const hasSessionCookieHint = hasCookieValue(CSRF_CONFIG.COOKIE_NAME);
        if (hasSessionCookieHint !== true) {
          logger.debug('未发现会话Cookie提示，跳过登录会话恢复探测');
          currentUserIdRef.current = null;
          invalidateCapabilityRequests();
          AuthStorage.clearCapabilitiesSnapshot();
          if (isMounted) {
            setUser(null);
            setPermissions([]);
            setCapabilities([]);
            setCapabilitiesLoading(false);
            setError(null);
          }
          return;
        }

        logger.debug('检测到会话Cookie提示，尝试通过Cookie恢复登录会话');
        const currentUser = await AuthService.getCurrentUser({
          suppressAuthRedirect: true,
        });
        const permissions = await resolvePermissionsWithFallback(currentUser.id, []);
        persistAuthDataSafely(currentUser, permissions, 'session');
        if (isMounted) {
          setUser(currentUser);
          setPermissions(permissions as Permission[]);
          setError(null);
        }
        currentUserIdRef.current = currentUser.id;
        triggerCapabilitiesRefresh(currentUser.id, { forceRefresh: true });
        logger.debug('通过Cookie恢复登录会话成功', { userId: currentUser.id });
      } catch {
        currentUserIdRef.current = null;
        invalidateCapabilityRequests();
        AuthStorage.clearCapabilitiesSnapshot();
        if (storedUser != null) {
          // 本地有认证元数据但Cookie会话已失效
          AuthStorage.clearAuthData();
          if (isMounted) {
            setUser(null);
            setPermissions([]);
            setCapabilities([]);
            setCapabilitiesLoading(false);
            setError('登录状态已失效，请重新登录');
          }
        } else {
          // 无本地元数据时，恢复失败保持未登录且不弹错误
          if (isMounted) {
            setUser(null);
            setPermissions([]);
            setCapabilities([]);
            setCapabilitiesLoading(false);
          }
        }
      } finally {
        if (isMounted) {
          setInitializing(false);
        }
      }
    };

    void restoreAuth();

    return () => {
      isMounted = false;
    };
  }, [invalidateCapabilityRequests, persistAuthDataSafely, triggerCapabilitiesRefresh]);

  const login = async (credentials: LoginCredentials) => {
    try {
      logger.debug('开始登录', { identifier: credentials.identifier });
      setLoading(true);
      setError(null);

      // 调用 AuthService 的登录方法
      const response = await AuthService.login(credentials);

      logger.debug('AuthContext收到登录响应', {
        success: response.success,
        hasData: Boolean(response.data),
      });

      if (Boolean(response.success) && Boolean(response.data)) {
        currentUserIdRef.current = response.data.user.id;
        invalidateCapabilityRequests();
        AuthStorage.clearCapabilitiesSnapshot();
        setCapabilities([]);
        setUser(response.data.user);
        setPermissions(response.data.permissions as Permission[]);
        logger.debug('用户状态已更新', { user: response.data.user } as Record<string, unknown>);
        triggerCapabilitiesRefresh(response.data.user.id, { forceRefresh: true });
        const successLog =
          typeof response.message === 'string' && response.message !== ''
            ? response.message
            : '登录成功';
        MessageManager.success(successLog);
      } else {
        throw new Error('登录响应格式错误');
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : '登录失败';
      setError(errorMessage);
      MessageManager.error(errorMessage);
      throw error;
    } finally {
      setLoading(false);
    }
  };

  const logout = async () => {
    try {
      setLoading(true);
      currentUserIdRef.current = null;
      invalidateCapabilityRequests();
      AuthStorage.clearCapabilitiesSnapshot();
      setCapabilities([]);
      setCapabilitiesLoading(false);

      // Call backend logout to clear httpOnly cookies
      await AuthService.logout();

      // Clear local authentication data using AuthStorage
      AuthStorage.clearAuthData();

      setUser(null);
      setPermissions([]);
      MessageManager.success('已退出登录');
    } catch (error) {
      logger.error('登出错误', error instanceof Error ? error : new Error(String(error)));
      // 即使出错也要确保清除状态
      AuthStorage.clearAuthData();
      setUser(null);
      setPermissions([]);
      setCapabilities([]);
      setCapabilitiesLoading(false);
    } finally {
      setLoading(false);
    }
  };

  const refreshUser = async () => {
    try {
      if (AuthService.isAuthenticated()) {
        const currentUser = await AuthService.getCurrentUser();
        const refreshedPermissions = await AuthService.getCurrentUserPermissions(currentUser.id);
        const authPersistence = AuthStorage.getAuthPersistence() ?? 'session';
        persistAuthDataSafely(currentUser, refreshedPermissions, authPersistence);
        currentUserIdRef.current = currentUser.id;
        setUser(currentUser);
        setPermissions(refreshedPermissions as Permission[]);
        setError(null);
        await refreshCapabilitiesByUser(currentUser.id, { forceRefresh: true });
      }
    } catch (refreshError) {
      logger.error(
        '刷新用户信息失败',
        refreshError instanceof Error ? refreshError : new Error(String(refreshError))
      );
      try {
        await AuthService.refreshToken();
        const currentUser = await AuthService.getCurrentUser();
        const refreshedPermissions = await AuthService.getCurrentUserPermissions(currentUser.id);
        const authPersistence = AuthStorage.getAuthPersistence() ?? 'session';
        persistAuthDataSafely(currentUser, refreshedPermissions, authPersistence);
        currentUserIdRef.current = currentUser.id;
        setUser(currentUser);
        setPermissions(refreshedPermissions as Permission[]);
        setError(null);
        await refreshCapabilitiesByUser(currentUser.id, { forceRefresh: true });
      } catch (tokenRefreshError) {
        logger.error(
          '刷新令牌失败，清理本地认证信息',
          tokenRefreshError instanceof Error
            ? tokenRefreshError
            : new Error(String(tokenRefreshError))
        );
        AuthStorage.clearAuthData();
        currentUserIdRef.current = null;
        invalidateCapabilityRequests();
        AuthStorage.clearCapabilitiesSnapshot();
        setUser(null);
        setPermissions([]);
        setCapabilities([]);
        setCapabilitiesLoading(false);
        setError('登录状态已失效，请重新登录');
      }
    }
  };

  const hasPermission = useCallback(
    (resource: string, action: string): boolean => {
      if (user?.is_admin === true) {
        return true;
      }

      const hasCapability = capabilities.some(capability => {
        return (
          capability.resource === resource &&
          capability.actions.some(capabilityAction => capabilityAction === action)
        );
      });

      if (hasCapability) {
        return true;
      }

      // Phase 3 兼容路径：在守卫主链完全切换前，保留旧权限摘要兜底。
      return permissions.some(
        permission => permission.resource === resource && permission.action === action
      );
    },
    [capabilities, permissions, user?.is_admin]
  );

  const hasAnyPermission = useCallback(
    (nextPermissions: Array<{ resource: string; action: string }>): boolean => {
      return nextPermissions.some(permission =>
        hasPermission(permission.resource, permission.action)
      );
    },
    [hasPermission]
  );

  const clearError = useCallback(() => {
    setError(null);
  }, []);

  // Token自动刷新机制 - Now handled by httpOnly cookies and API client interceptor
  // The API client automatically handles 401 errors and refreshes tokens via cookies
  // No need for manual token refresh logic here

  const isAdmin = user?.is_admin ?? false;

  const value: AuthContextType = useMemo(
    () => ({
      user,
      permissions,
      capabilities,
      capabilitiesLoading,
      isAuthenticated: user != null,
      isAdmin,
      initializing,
      login,
      logout,
      refreshUser,
      refreshCapabilities,
      hasPermission,
      hasAnyPermission,
      clearError,
      loading,
      error,
    }),
    [
      user,
      permissions,
      capabilities,
      capabilitiesLoading,
      isAdmin,
      initializing,
      loading,
      error,
      refreshCapabilities,
      hasPermission,
      hasAnyPermission,
      clearError,
    ]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export { AuthProvider };
export default AuthContext;

// 导出TypeScript类型供其他模块使用
export type { AuthContextType, AuthProviderProps };
