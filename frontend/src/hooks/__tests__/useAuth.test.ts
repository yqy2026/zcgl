/**
 * useAuth Hook 测试
 * 对齐 AuthContext 作为唯一认证状态源
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, act, waitFor } from '@testing-library/react';
import React from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useAuth } from '../useAuth';
import { AuthProvider } from '@/contexts/AuthContext';
import { apiClient } from '@/api/client';
import { AuthService } from '@/services/authService';
import { AuthStorage } from '@/utils/AuthStorage';
import { MessageManager } from '@/utils/messageManager';

vi.mock('@/api/client', () => ({
  apiClient: {
    clearCache: vi.fn(),
  },
}));

vi.mock('@/services/authService', () => ({
  AuthService: {
    getLocalPermissions: vi.fn(),
    login: vi.fn(),
    logout: vi.fn(),
    getCurrentUser: vi.fn(),
    getCurrentUserPermissions: vi.fn(),
    getCurrentUserCapabilities: vi.fn(),
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
    getAuthPersistence: vi.fn(),
    getCurrentUser: vi.fn(),
    getPermissions: vi.fn(),
    getCapabilities: vi.fn(),
    setAuthData: vi.fn(),
    setCapabilitiesSnapshot: vi.fn(),
    clearCapabilitiesSnapshot: vi.fn(),
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

const createTestQueryClient = () =>
  new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        gcTime: Infinity,
      },
      mutations: {
        retry: false,
      },
    },
  });

let queryClient: QueryClient;

const wrapper = ({ children }: { children: React.ReactNode }) =>
  React.createElement(
    QueryClientProvider,
    { client: queryClient },
    React.createElement(AuthProvider, null, children)
  );

const clearDocumentCookies = () => {
  const cookieEntries = document.cookie.split(';');
  for (const cookieEntry of cookieEntries) {
    const trimmed = cookieEntry.trim();
    if (trimmed === '') {
      continue;
    }
    const separatorIndex = trimmed.indexOf('=');
    const cookieName = separatorIndex >= 0 ? trimmed.slice(0, separatorIndex) : trimmed;
    document.cookie = `${cookieName}=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/`;
  }
};

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

  const anotherUser = {
    id: '2',
    username: 'another-user',
    email: 'another@example.com',
    full_name: 'Another User',
    role_id: 'role-user-id',
    role_name: 'user',
    default_organization_id: 'org-2',
  };

  beforeEach(() => {
    vi.clearAllMocks();
    queryClient = createTestQueryClient();
    clearDocumentCookies();
    vi.mocked(AuthStorage.getAuthData).mockReturnValue(null);
    vi.mocked(AuthStorage.getAuthPersistence).mockReturnValue('session');
    vi.mocked(AuthStorage.getCurrentUser).mockReturnValue(null);
    vi.mocked(AuthStorage.getPermissions).mockReturnValue([]);
    vi.mocked(AuthStorage.getCapabilities).mockReturnValue([]);
    vi.mocked(AuthService.verifyAuth).mockResolvedValue(true);
    vi.mocked(AuthService.getCurrentUser).mockRejectedValue(new Error('Unauthorized'));
    vi.mocked(AuthService.getCurrentUserPermissions).mockResolvedValue([]);
    vi.mocked(AuthService.getCurrentUserCapabilities).mockResolvedValue({
      version: 'v1',
      generated_at: '2026-02-27T00:00:00Z',
      capabilities: [],
    });
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
      vi.mocked(AuthService.getCurrentUser).mockResolvedValue(mockUser);
      vi.mocked(AuthService.getCurrentUserPermissions).mockResolvedValue([]);

      const { result } = renderHook(() => useAuth(), { wrapper });

      await waitFor(() => {
        expect(result.current.user).toEqual(mockUser);
      });
    });

    it('本地用户与当前Cookie用户不一致时，应该按当前会话覆盖本地用户', async () => {
      vi.mocked(AuthStorage.getAuthData).mockReturnValue({
        user: mockUser,
        permissions: [{ resource: 'legacy', action: 'read' }],
      });
      vi.mocked(AuthStorage.getAuthPersistence).mockReturnValue('local');
      vi.mocked(AuthService.getCurrentUser).mockResolvedValue(anotherUser);
      vi.mocked(AuthService.getCurrentUserPermissions).mockResolvedValue([
        { resource: 'assets', action: 'read' },
      ]);

      const { result } = renderHook(() => useAuth(), { wrapper });

      await waitFor(() => {
        expect(result.current.user).toEqual(anotherUser);
      });

      expect(AuthStorage.setAuthData).toHaveBeenCalledWith(
        {
          user: anotherUser,
          permissions: [{ resource: 'assets', action: 'read' }],
        },
        { persistence: 'local' }
      );
    });

    it('本地用户与当前Cookie用户不一致时，应立即清空旧 capabilities', async () => {
      vi.mocked(AuthStorage.getAuthData).mockReturnValue({
        user: mockUser,
        permissions: [{ resource: 'legacy', action: 'read' }],
      });
      vi.mocked(AuthStorage.getCapabilities).mockReturnValue([
        {
          resource: 'legacy',
          actions: ['delete'],
          perspectives: [],
          data_scope: { owner_party_ids: [], manager_party_ids: [] },
        },
      ]);
      vi.mocked(AuthService.getCurrentUser).mockResolvedValue(anotherUser);
      vi.mocked(AuthService.getCurrentUserPermissions).mockResolvedValue([]);
      vi.mocked(AuthService.getCurrentUserCapabilities).mockImplementation(
        () =>
          new Promise(() => undefined) as ReturnType<typeof AuthService.getCurrentUserCapabilities>
      );

      const { result } = renderHook(() => useAuth(), { wrapper });

      await waitFor(() => {
        expect(result.current.user).toEqual(anotherUser);
      });

      expect(result.current.capabilities).toEqual([]);
      expect(result.current.hasPermission('legacy', 'delete')).toBe(false);
      expect(result.current.capabilitiesLoading).toBe(true);
    });

    it('本地无认证信息且无会话Cookie提示时，不应探测用户会话', async () => {
      vi.mocked(AuthStorage.getAuthData).mockReturnValue(null);

      const { result } = renderHook(() => useAuth(), { wrapper });

      await waitFor(() => {
        expect(result.current.initializing).toBe(false);
      });

      expect(result.current.user).toBeNull();
      expect(AuthService.getCurrentUser).not.toHaveBeenCalled();
    });

    it('本地无认证信息但Cookie有效时，应该恢复用户并写入会话存储', async () => {
      vi.mocked(AuthStorage.getAuthData).mockReturnValue(null);
      document.cookie = 'csrf_token=test-csrf-token; path=/';
      vi.mocked(AuthService.getCurrentUser).mockResolvedValue(mockUser);
      vi.mocked(AuthService.getCurrentUserPermissions).mockResolvedValue([
        { resource: 'assets', action: 'read', description: 'Read assets' },
      ]);

      const { result } = renderHook(() => useAuth(), { wrapper });

      await waitFor(() => {
        expect(result.current.user).toEqual(mockUser);
      });

      expect(AuthService.getCurrentUser).toHaveBeenCalledTimes(1);
      expect(AuthService.getCurrentUser).toHaveBeenCalledWith({
        suppressAuthRedirect: true,
      });
      expect(AuthStorage.setAuthData).toHaveBeenCalledWith(
        {
          user: mockUser,
          permissions: [{ resource: 'assets', action: 'read', description: 'Read assets' }],
        },
        { persistence: 'session' }
      );
    });

    it('权限摘要接口失败时，仍应保留通过Cookie验证的登录用户', async () => {
      vi.mocked(AuthStorage.getAuthData).mockReturnValue(null);
      document.cookie = 'csrf_token=test-csrf-token; path=/';
      vi.mocked(AuthService.getCurrentUser).mockResolvedValue(mockUser);
      vi.mocked(AuthService.getCurrentUserPermissions).mockRejectedValue(
        new Error('permissions unavailable')
      );

      const { result } = renderHook(() => useAuth(), { wrapper });

      await waitFor(() => {
        expect(result.current.user).toEqual(mockUser);
      });

      expect(AuthService.getCurrentUser).toHaveBeenCalledTimes(1);
      expect(AuthService.getCurrentUser).toHaveBeenCalledWith({
        suppressAuthRedirect: true,
      });
      expect(AuthStorage.setAuthData).toHaveBeenCalledWith(
        {
          user: mockUser,
          permissions: [],
        },
        { persistence: 'session' }
      );
    });

    it('capabilities 接口挂起时，不应阻塞初始化完成', async () => {
      vi.mocked(AuthStorage.getAuthData).mockReturnValue({
        user: mockUser,
        permissions: [],
      });
      vi.mocked(AuthService.getCurrentUser).mockResolvedValue(mockUser);
      vi.mocked(AuthService.getCurrentUserPermissions).mockResolvedValue([]);
      vi.mocked(AuthService.getCurrentUserCapabilities).mockImplementation(
        () =>
          new Promise(() => undefined) as ReturnType<typeof AuthService.getCurrentUserCapabilities>
      );

      const { result } = renderHook(() => useAuth(), { wrapper });

      await waitFor(() => {
        expect(result.current.initializing).toBe(false);
      });

      expect(result.current.user).toEqual(mockUser);
      expect(result.current.capabilitiesLoading).toBe(true);
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
        await result.current.login({ identifier: 'testuser', password: 'password' });
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
          result.current.login({ identifier: 'testuser', password: 'wrong' })
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
          result.current.login({ identifier: 'testuser', password: 'password' })
        ).rejects.toThrow('Network error');
      });

      expect(result.current.user).toBeNull();
      expect(result.current.error).toBe('Network error');
      expect(MessageManager.error).toHaveBeenCalledWith('Network error');
    });

    it('capabilities 刷新挂起时，不应阻塞登录流程完成', async () => {
      vi.mocked(AuthService.login).mockResolvedValue({
        success: true,
        data: {
          user: mockUser,
          permissions: [],
        },
        message: '登录成功',
      });
      vi.mocked(AuthService.getCurrentUserCapabilities).mockImplementation(
        () =>
          new Promise(() => undefined) as ReturnType<typeof AuthService.getCurrentUserCapabilities>
      );

      const { result } = renderHook(() => useAuth(), { wrapper });

      let loginPromise: Promise<void> | null = null;
      act(() => {
        loginPromise = result.current.login({ identifier: 'testuser', password: 'password' });
      });

      await waitFor(() => {
        expect(result.current.user).toEqual(mockUser);
      });
      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });

      expect(loginPromise).not.toBeNull();
      if (loginPromise != null) {
        await expect(loginPromise).resolves.toBeUndefined();
      }
      expect(MessageManager.success).toHaveBeenCalledWith('登录成功');
    });
  });

  describe('logout', () => {
    it('同标签登出后重新登录时，应该清空 React Query 缓存避免复用旧会话数据', async () => {
      const staleQueryKey = ['asset', 'user:1|view:owner:party-1', 'asset_123'];
      const staleAsset = {
        id: 'asset_123',
        asset_name: '旧会话资产',
      };

      vi.mocked(AuthStorage.getAuthData).mockReturnValue({
        user: mockUser,
        permissions: [],
      });
      vi.mocked(AuthService.getCurrentUser).mockResolvedValue(mockUser);
      vi.mocked(AuthService.getCurrentUserPermissions).mockResolvedValue([]);
      vi.mocked(AuthService.login).mockResolvedValue({
        success: true,
        data: {
          user: mockUser,
          permissions: [],
        },
        message: '登录成功',
      });

      queryClient.setQueryData(staleQueryKey, staleAsset);

      const { result } = renderHook(() => useAuth(), { wrapper });

      await waitFor(() => {
        expect(result.current.user).toEqual(mockUser);
      });

      expect(queryClient.getQueryData(staleQueryKey)).toEqual(staleAsset);

      await act(async () => {
        await result.current.logout();
      });

      await act(async () => {
        await result.current.login({ identifier: 'testuser', password: 'password' });
      });

      expect(queryClient.getQueryData(staleQueryKey)).toBeUndefined();
    });

    it('应该在登出时清空 API 内存缓存', async () => {
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

      expect(apiClient.clearCache).toHaveBeenCalledTimes(1);
    });

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

    it('should ignore stale capability response when logout happens during in-flight login refresh', async () => {
      let resolveCapabilities: ((value: unknown) => void) | null = null;

      vi.mocked(AuthService.login).mockResolvedValue({
        success: true,
        data: {
          user: mockUser,
          permissions: [],
        },
        message: '登录成功',
      });
      vi.mocked(AuthService.getCurrentUserCapabilities).mockImplementation(
        () =>
          new Promise(resolve => {
            resolveCapabilities = resolve;
          }) as ReturnType<typeof AuthService.getCurrentUserCapabilities>
      );

      const { result } = renderHook(() => useAuth(), { wrapper });

      let loginPromise: Promise<void> | null = null;
      act(() => {
        loginPromise = result.current.login({ identifier: 'testuser', password: 'password' });
      });

      await waitFor(() => {
        expect(result.current.user?.id).toBe(mockUser.id);
      });

      await act(async () => {
        await result.current.logout();
      });

      resolveCapabilities?.({
        version: 'v1',
        generated_at: '2026-02-27T00:00:00Z',
        capabilities: [
          {
            resource: 'asset',
            actions: ['read'],
            perspectives: [],
            data_scope: { owner_party_ids: [], manager_party_ids: [] },
          },
        ],
      });

      if (loginPromise != null) {
        await act(async () => {
          await loginPromise;
        });
      }

      expect(result.current.user).toBeNull();
      expect(result.current.capabilities).toEqual([]);
    });
  });

  describe('authz stale event', () => {
    it('should refresh permissions and capabilities when authz-stale is dispatched', async () => {
      vi.mocked(AuthStorage.getAuthData).mockReturnValue({
        user: mockUser,
        permissions: [],
      });
      vi.mocked(AuthService.getCurrentUser).mockResolvedValue(mockUser);
      vi.mocked(AuthService.getCurrentUserPermissions).mockResolvedValue([
        { resource: 'contacts', action: 'read' },
      ]);
      vi.mocked(AuthService.getCurrentUserCapabilities).mockResolvedValue({
        version: 'v2',
        generated_at: '2026-03-16T00:00:00Z',
        capabilities: [
          {
            resource: 'contact',
            actions: ['read'],
            perspectives: [],
            data_scope: { owner_party_ids: ['party-1'], manager_party_ids: [] },
          },
        ],
      });
      vi.mocked(AuthService.isAuthenticated).mockReturnValue(true);

      const { result } = renderHook(() => useAuth(), { wrapper });

      await waitFor(() => {
        expect(result.current.user).toEqual(mockUser);
      });

      vi.mocked(AuthService.getCurrentUser).mockClear();
      vi.mocked(AuthService.getCurrentUserPermissions).mockClear();
      vi.mocked(AuthService.getCurrentUserCapabilities).mockClear();
      vi.mocked(AuthStorage.clearCapabilitiesSnapshot).mockClear();
      vi.mocked(AuthStorage.setCapabilitiesSnapshot).mockClear();
      vi.mocked(MessageManager.warning).mockClear();

      await act(async () => {
        window.dispatchEvent(new CustomEvent('authz-stale'));
      });

      await waitFor(() => {
        expect(MessageManager.warning).toHaveBeenCalledWith('当前权限视角已更新，正在刷新访问权限');
      });

      expect(AuthStorage.clearCapabilitiesSnapshot).toHaveBeenCalled();
      expect(AuthService.getCurrentUser).toHaveBeenCalledTimes(1);
      expect(AuthService.getCurrentUserPermissions).toHaveBeenCalledTimes(1);
      expect(AuthService.getCurrentUserCapabilities).toHaveBeenCalledTimes(1);
      expect(AuthStorage.setCapabilitiesSnapshot).toHaveBeenCalledWith({
        version: 'v2',
        generated_at: '2026-03-16T00:00:00Z',
        capabilities: [
          {
            resource: 'contact',
            actions: ['read'],
            perspectives: [],
            data_scope: { owner_party_ids: ['party-1'], manager_party_ids: [] },
          },
        ],
      });
    });

    it('should coalesce repeated authz-stale events into a single refresh wave', async () => {
      vi.mocked(AuthStorage.getAuthData).mockReturnValue({
        user: mockUser,
        permissions: [],
      });
      vi.mocked(AuthService.getCurrentUser).mockResolvedValue(mockUser);
      vi.mocked(AuthService.getCurrentUserPermissions).mockResolvedValue([
        { resource: 'contacts', action: 'read' },
      ]);
      vi.mocked(AuthService.getCurrentUserCapabilities).mockResolvedValue({
        version: 'v2',
        generated_at: '2026-03-16T00:00:00Z',
        capabilities: [
          {
            resource: 'contact',
            actions: ['read'],
            perspectives: [],
            data_scope: { owner_party_ids: ['party-1'], manager_party_ids: [] },
          },
        ],
      });
      vi.mocked(AuthService.isAuthenticated).mockReturnValue(true);

      const { result } = renderHook(() => useAuth(), { wrapper });

      await waitFor(() => {
        expect(result.current.user).toEqual(mockUser);
      });

      let resolveRefreshUser: ((user: typeof mockUser) => void) | null = null;
      const refreshUserPromise = new Promise<typeof mockUser>(resolve => {
        resolveRefreshUser = resolve;
      });
      vi.mocked(AuthService.getCurrentUser).mockClear();
      vi.mocked(AuthService.getCurrentUser).mockReturnValue(
        refreshUserPromise as ReturnType<typeof AuthService.getCurrentUser>
      );
      vi.mocked(AuthService.getCurrentUserPermissions).mockClear();
      vi.mocked(AuthService.getCurrentUserCapabilities).mockClear();
      vi.mocked(AuthStorage.clearCapabilitiesSnapshot).mockClear();
      vi.mocked(AuthStorage.setCapabilitiesSnapshot).mockClear();
      vi.mocked(MessageManager.warning).mockClear();

      await act(async () => {
        window.dispatchEvent(new CustomEvent('authz-stale'));
        window.dispatchEvent(new CustomEvent('authz-stale'));
        window.dispatchEvent(new CustomEvent('authz-stale'));
      });

      expect(MessageManager.warning).toHaveBeenCalledTimes(1);
      expect(AuthStorage.clearCapabilitiesSnapshot).toHaveBeenCalledTimes(1);
      expect(AuthService.getCurrentUser).toHaveBeenCalledTimes(1);
      expect(AuthService.getCurrentUserPermissions).not.toHaveBeenCalled();
      expect(AuthService.getCurrentUserCapabilities).not.toHaveBeenCalled();

      resolveRefreshUser?.(mockUser);

      await waitFor(() => {
        expect(AuthService.getCurrentUserPermissions).toHaveBeenCalledTimes(1);
      });
      expect(AuthService.getCurrentUserCapabilities).toHaveBeenCalledTimes(1);
    });
  });
});
