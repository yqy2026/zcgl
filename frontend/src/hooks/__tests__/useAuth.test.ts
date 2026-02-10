/**
 * useAuth Hook 测试
 * 对齐 AuthContext 作为唯一认证状态源
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, act, waitFor } from '@testing-library/react';
import React from 'react';
import { useAuth } from '../useAuth';
import { AuthProvider } from '@/contexts/AuthContext';
import { AuthService } from '@/services/authService';
import { AuthStorage } from '@/utils/AuthStorage';
import { MessageManager } from '@/utils/messageManager';

vi.mock('@/services/authService', () => ({
  AuthService: {
    getLocalPermissions: vi.fn(),
    login: vi.fn(),
    logout: vi.fn(),
    getCurrentUser: vi.fn(),
    refreshToken: vi.fn(),
    hasPermission: vi.fn(),
    hasAnyPermission: vi.fn(),
    isAuthenticated: vi.fn(),
    verifyAuth: vi.fn(),
  },
}));

vi.mock('@/utils/AuthStorage', () => ({
  AuthStorage: {
    getAuthData: vi.fn(),
    clearAuthData: vi.fn(),
  },
}));

vi.mock('@/utils/logger', () => ({
  createLogger: () => ({
    info: vi.fn(),
    warn: vi.fn(),
    error: vi.fn(),
    debug: vi.fn(),
  }),
}));

vi.mock('@/utils/messageManager', () => ({
  MessageManager: {
    success: vi.fn(),
    error: vi.fn(),
    warning: vi.fn(),
    info: vi.fn(),
  },
}));

const wrapper = ({ children }: { children: React.ReactNode }) =>
  React.createElement(AuthProvider, null, children);

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
    vi.mocked(AuthStorage.getAuthData).mockReturnValue(null);
    vi.mocked(AuthService.verifyAuth).mockResolvedValue(true);
    vi.mocked(AuthService.getLocalPermissions).mockReturnValue([]);
    vi.mocked(AuthService.hasPermission).mockReturnValue(false);
    vi.mocked(AuthService.hasAnyPermission).mockReturnValue(false);
    vi.mocked(AuthService.isAuthenticated).mockReturnValue(false);
    vi.mocked(AuthService.logout).mockResolvedValue(undefined);
  });

  describe('初始化', () => {
    it('如果未认证，应该初始化为空用户', () => {
      const { result } = renderHook(() => useAuth(), { wrapper });

      expect(result.current.user).toBeNull();
      expect(result.current.loading).toBe(false);
    });

    it('如果本地存在认证信息，应该恢复用户状态', async () => {
      vi.mocked(AuthStorage.getAuthData).mockReturnValue({
        user: mockUser,
        permissions: [],
      });
      vi.mocked(AuthService.verifyAuth).mockResolvedValue(true);

      const { result } = renderHook(() => useAuth(), { wrapper });

      await waitFor(() => {
        expect(result.current.user).toEqual(mockUser);
      });
    });
  });

  describe('login', () => {
    it('应该处理登录成功', async () => {
      vi.mocked(AuthService.login).mockResolvedValue({
        success: true,
        data: {
          user: mockUser,
          permissions: [],
        },
        message: '登录成功',
      });

      const { result } = renderHook(() => useAuth(), { wrapper });

      await act(async () => {
        await result.current.login({ username: 'testuser', password: 'password' });
      });

      expect(result.current.user).toEqual(mockUser);
      expect(result.current.error).toBeNull();
      expect(MessageManager.success).toHaveBeenCalledWith('登录成功');
    });

    it('应该处理登录失败', async () => {
      vi.mocked(AuthService.login).mockRejectedValue(new Error('用户名或密码错误'));

      const { result } = renderHook(() => useAuth(), { wrapper });

      await act(async () => {
        await expect(
          result.current.login({ username: 'testuser', password: 'wrong' })
        ).rejects.toThrow('用户名或密码错误');
      });

      expect(result.current.user).toBeNull();
      expect(result.current.error).toBe('用户名或密码错误');
      expect(MessageManager.error).toHaveBeenCalledWith('用户名或密码错误');
    });

    it('应该处理登录异常', async () => {
      vi.mocked(AuthService.login).mockRejectedValue(new Error('Network error'));

      const { result } = renderHook(() => useAuth(), { wrapper });

      await act(async () => {
        await expect(
          result.current.login({ username: 'testuser', password: 'password' })
        ).rejects.toThrow('Network error');
      });

      expect(result.current.user).toBeNull();
      expect(result.current.error).toBe('Network error');
      expect(MessageManager.error).toHaveBeenCalledWith('Network error');
    });
  });

  describe('logout', () => {
    it('应该处理登出', async () => {
      vi.mocked(AuthStorage.getAuthData).mockReturnValue({
        user: mockUser,
        permissions: [],
      });
      vi.mocked(AuthService.verifyAuth).mockResolvedValue(true);

      const { result } = renderHook(() => useAuth(), { wrapper });

      await waitFor(() => {
        expect(result.current.user).toEqual(mockUser);
      });

      await act(async () => {
        await result.current.logout();
      });

      expect(result.current.user).toBeNull();
      expect(AuthStorage.clearAuthData).toHaveBeenCalled();
      expect(MessageManager.success).toHaveBeenCalledWith('已退出登录');
    });
  });
});
