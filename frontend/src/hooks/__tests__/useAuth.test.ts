/**
 * useAuth Hook 测试
 * 测试认证相关的自定义Hooks（简化版本）
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useAuth } from '../useAuth';
import { AuthService } from '@/services/authService';
import { MessageManager } from '@/utils/messageManager';

// Mock AuthService
vi.mock('@/services/authService', () => ({
  AuthService: {
    getLocalUser: vi.fn(),
    isAuthenticated: vi.fn(),
    getLocalPermissions: vi.fn(),
    login: vi.fn(),
    logout: vi.fn(),
    getCurrentUser: vi.fn(),
    refreshToken: vi.fn(),
    hasPermission: vi.fn(),
    hasAnyPermission: vi.fn(),
  },
}));

// Mock logger
vi.mock('@/utils/logger', () => ({
  createLogger: () => ({
    info: vi.fn(),
    warn: vi.fn(),
    error: vi.fn(),
    debug: vi.fn(),
  }),
}));

// Mock MessageManager
vi.mock('@/utils/messageManager', () => ({
  MessageManager: {
    success: vi.fn(),
    error: vi.fn(),
    warning: vi.fn(),
    info: vi.fn(),
  },
}));

describe('useAuth Hook', () => {
  const mockUser = {
    id: '1',
    username: 'testuser',
    email: 'test@example.com',
    full_name: 'Test User',
    role_id: 'role-admin-id',
    role_name: 'admin',
    default_organization_id: 'org-1',
  };

  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(AuthService.getLocalUser).mockReturnValue(null);
    vi.mocked(AuthService.isAuthenticated).mockReturnValue(false);
  });

  describe('初始化', () => {
    it('如果未认证，应该初始化为空用户', () => {
      vi.mocked(AuthService.isAuthenticated).mockReturnValue(false);
      vi.mocked(AuthService.getLocalUser).mockReturnValue(null);

      const { result } = renderHook(() => useAuth());

      expect(result.current.user).toBeNull();
      expect(result.current.loading).toBe(false);
    });

    it('如果已认证，应该初始化为本地用户', () => {
      vi.mocked(AuthService.isAuthenticated).mockReturnValue(true);
      vi.mocked(AuthService.getLocalUser).mockReturnValue(mockUser);
      vi.mocked(AuthService.getLocalPermissions).mockReturnValue([]);

      const { result } = renderHook(() => useAuth());

      expect(result.current.user).toEqual(mockUser);
    });
  });

  describe('login', () => {
    it('应该处理登录成功', async () => {
      vi.mocked(AuthService.login).mockResolvedValue({
        success: true,
        data: {
          user: mockUser,
          access_token: 'token',
          refresh_token: 'refresh',
          expires_in: 3600,
          token_type: 'bearer',
          permissions: [],
        },
      });

      const { result } = renderHook(() => useAuth());

      await act(async () => {
        await result.current.login({ username: 'testuser', password: 'password' });
      });

      expect(result.current.user).toEqual(mockUser);
      expect(result.current.error).toBeNull();
      expect(MessageManager.success).toHaveBeenCalledWith('登录成功');
    });

    it('应该处理登录失败', async () => {
      vi.mocked(AuthService.login).mockResolvedValue({
        success: false,
        message: 'Invalid credentials',
      });

      const { result } = renderHook(() => useAuth());

      await act(async () => {
        await result.current.login({ username: 'testuser', password: 'wrong' });
      });

      expect(result.current.user).toBeNull();
      expect(result.current.error).toBe('用户名或密码错误');
    });

    it('应该处理登录异常', async () => {
      vi.mocked(AuthService.login).mockRejectedValue(new Error('Network error'));

      const { result } = renderHook(() => useAuth());

      await act(async () => {
        await result.current.login({ username: 'testuser', password: 'password' });
      });

      expect(result.current.user).toBeNull();
      expect(result.current.error).toBe('Network error');
      expect(MessageManager.error).toHaveBeenCalledWith('Network error');
    });
  });

  describe('logout', () => {
    it('应该处理登出', async () => {
      vi.mocked(AuthService.logout).mockResolvedValue(undefined);

      // Setup initial state
      vi.mocked(AuthService.isAuthenticated).mockReturnValue(true);
      vi.mocked(AuthService.getLocalUser).mockReturnValue(mockUser);

      const { result } = renderHook(() => useAuth());

      await act(async () => {
        await result.current.logout();
      });

      expect(result.current.user).toBeNull();
      expect(MessageManager.success).toHaveBeenCalledWith('已安全登出');
    });
  });
});
