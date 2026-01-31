import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { User, LoginCredentials } from '@/types/auth';
import { AuthService } from '@/services/authService';
import { AuthStorage } from '@/utils/AuthStorage';
import { createLogger } from '@/utils/logger';
import { MessageManager } from '@/utils/messageManager';

const logger = createLogger('AuthContext');

interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  login: (credentials: LoginCredentials) => Promise<void>;
  logout: () => Promise<void>;
  loading: boolean;
  error: string | null;
}

interface AuthProviderProps {
  children: ReactNode;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

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
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // 检查本地存储的认证状态
  useEffect(() => {
    let isMounted = true;
    const restoreAuth = async () => {
      // 从 AuthStorage 获取用户数据（统一的存储方式）
      const authData = AuthStorage.getAuthData();
      const storedUser = authData?.user;

      if (storedUser != null) {
        if (isMounted) {
          setUser(storedUser);
        }
        logger.debug('认证状态已从本地存储恢复', { userId: storedUser.id });

        // 清理旧的 localStorage 键
        localStorage.removeItem('user');
        localStorage.removeItem('user_info');
      }

      // 验证登录会话
      if (storedUser != null) {
        logger.debug('开始校验登录会话');
        const verified = await AuthService.verifyAuth();
        if (!verified) {
          logger.warn('登录会话校验失败，清理本地认证信息');
          AuthStorage.clearAuthData();
          if (isMounted) {
            setUser(null);
          }
        } else {
          logger.debug('登录会话校验通过');
        }
      }
    };

    restoreAuth();

    return () => {
      isMounted = false;
    };
  }, []);

  const login = async (credentials: LoginCredentials) => {
    try {
      logger.debug('开始登录', { username: credentials.username });
      setLoading(true);
      setError(null);

      // 调用 AuthService 的登录方法
      const response = await AuthService.login(credentials);

      logger.debug('AuthContext收到登录响应', {
        success: response.success,
        hasData: Boolean(response.data),
      });

      if (Boolean(response.success) && Boolean(response.data)) {
        setUser(response.data.user);
        logger.debug('用户状态已更新', { user: response.data.user } as Record<string, unknown>);
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

      // Call backend logout to clear httpOnly cookies
      await AuthService.logout();

      // Clear local authentication data using AuthStorage
      AuthStorage.clearAuthData();

      setUser(null);
      MessageManager.success('已退出登录');
    } catch (error) {
      logger.error('登出错误', error instanceof Error ? error : new Error(String(error)));
      // 即使出错也要确保清除状态
      AuthStorage.clearAuthData();
      setUser(null);
    } finally {
      setLoading(false);
    }
  };

  // Token自动刷新机制 - Now handled by httpOnly cookies and API client interceptor
  // The API client automatically handles 401 errors and refreshes tokens via cookies
  // No need for manual token refresh logic here

  const value: AuthContextType = {
    user,
    isAuthenticated: !!user,
    login,
    logout,
    loading,
    error,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export { AuthProvider };
export default AuthContext;

// 导出TypeScript类型供其他模块使用
export type { AuthContextType, AuthProviderProps };
