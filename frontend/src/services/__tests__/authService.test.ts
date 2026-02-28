import { describe, it, expect, beforeEach, vi } from 'vitest';
import { AuthService } from '../authService';
import { AuthStorage } from '@/utils/AuthStorage';

// Mock API client
vi.mock('@/api/client', () => ({
  apiClient: {
    post: vi.fn(),
    get: vi.fn(),
    put: vi.fn(),
  },
}));

import { apiClient } from '@/api/client';

describe('AuthService - Login with Permissions', () => {
  beforeEach(() => {
    localStorage.clear();
    sessionStorage.clear();
    AuthStorage.clearAuthData();
    vi.clearAllMocks();
  });

  it('should store permissions from login response', async () => {
    const mockResponse = {
      data: {
        user: {
          id: '1',
          username: 'testuser',
          email: 'test@example.com',
          full_name: 'Test User',
          role_id: 'role-admin-id',
          role_name: 'admin',
          default_organization_id: 'org-123',
        },
        permissions: [
          { resource: 'assets', action: 'read', description: 'Read assets' },
          { resource: 'users', action: 'write', description: 'Write users' },
        ],
      },
    };

    vi.mocked(apiClient.post).mockResolvedValue({
      success: true,
      data: mockResponse.data,
    });

    const result = await AuthService.login({ identifier: 'testuser', password: 'password' });

    expect(result.success).toBe(true);
    expect(result.data?.permissions).toEqual([
      { resource: 'assets', action: 'read', description: 'Read assets' },
      { resource: 'users', action: 'write', description: 'Write users' },
    ]);

    // Verify AuthStorage was called with permissions
    const authData = AuthStorage.getAuthData();
    expect(authData?.permissions).toEqual([
      { resource: 'assets', action: 'read', description: 'Read assets' },
      { resource: 'users', action: 'write', description: 'Write users' },
    ]);
  });

  it('should handle empty permissions array', async () => {
    const mockResponse = {
      data: {
        user: {
          id: '1',
          username: 'testuser',
          email: 'test@example.com',
        },
        permissions: [],
      },
    };

    vi.mocked(apiClient.post).mockResolvedValue({
      success: true,
      data: mockResponse.data,
    });

    const result = await AuthService.login({ identifier: 'testuser', password: 'password' });

    expect(result.success).toBe(true);
    expect(result.data?.permissions).toEqual([]);

    const authData = AuthStorage.getAuthData();
    expect(authData?.permissions).toEqual([]);
  });

  it('should handle logout successfully', async () => {
    vi.mocked(apiClient.post).mockResolvedValue({
      success: true,
      message: 'Logged out successfully',
    });

    await AuthService.logout();

    const authData = AuthStorage.getAuthData();
    expect(authData).toBeNull();
    expect(apiClient.post).toHaveBeenCalledWith('/auth/logout', undefined, { retry: false });
  });

  it('should refresh token successfully', async () => {
    // Setup initial state
    // AuthStorage.setToken('old-token');
    // AuthStorage.setRefreshToken('old-refresh-token');

    const mockResponse = {
      success: true,
      data: {
        message: '令牌刷新成功',
        auth_mode: 'cookie',
      },
    };

    vi.mocked(apiClient.post).mockResolvedValue({
      success: true,
      data: mockResponse.data,
    });

    const result = await AuthService.refreshToken();

    expect(result.success).toBe(true);
  });

  it('should get current user successfully', async () => {
    const mockUser = {
      id: '1',
      username: 'testuser',
      email: 'test@example.com',
    };

    vi.mocked(apiClient.get).mockResolvedValue({
      success: true,
      data: mockUser,
    });

    const result = await AuthService.getCurrentUser();

    expect(result).toEqual(mockUser);
    expect(apiClient.get).toHaveBeenCalledWith(
      '/auth/me',
      expect.objectContaining({
        cache: false,
        skipAuthRefresh: false,
        suppressAuthRedirect: false,
      })
    );
  });

  it('should bypass auth refresh handling when requested for bootstrap probe', async () => {
    const mockUser = {
      id: '1',
      username: 'testuser',
      email: 'test@example.com',
    };

    vi.mocked(apiClient.get).mockResolvedValue({
      success: true,
      data: mockUser,
    });

    const result = await AuthService.getCurrentUser({ skipAuthRefresh: true });

    expect(result).toEqual(mockUser);
    expect(apiClient.get).toHaveBeenCalledWith(
      '/auth/me',
      expect.objectContaining({
        cache: false,
        skipAuthRefresh: true,
        suppressAuthRedirect: false,
      })
    );
  });

  it('should suppress hard redirect during bootstrap auth probe when requested', async () => {
    const mockUser = {
      id: '1',
      username: 'testuser',
      email: 'test@example.com',
    };

    vi.mocked(apiClient.get).mockResolvedValue({
      success: true,
      data: mockUser,
    });

    const result = await AuthService.getCurrentUser({ suppressAuthRedirect: true });

    expect(result).toEqual(mockUser);
    expect(apiClient.get).toHaveBeenCalledWith(
      '/auth/me',
      expect.objectContaining({
        cache: false,
        skipAuthRefresh: false,
        suppressAuthRedirect: true,
      })
    );
  });

  it('should get and normalize current user permission summary', async () => {
    vi.mocked(apiClient.get).mockResolvedValue({
      success: true,
      data: {
        permissions: [
          { resource: 'assets', action: 'read', description: 'Read assets' },
          { resource: 'users', action: 'write' },
          { resource: '', action: 'invalid' },
          { resource: 'reports' },
        ],
      },
    });

    const permissions = await AuthService.getCurrentUserPermissions('user-1');

    expect(permissions).toEqual([
      { resource: 'assets', action: 'read', description: 'Read assets' },
      { resource: 'users', action: 'write', description: undefined },
    ]);
    expect(apiClient.get).toHaveBeenCalledWith('/roles/users/user-1/permissions/summary', {
      cache: false,
      retry: false,
    });
  });

  it('should return empty permission summary when response has no permissions', async () => {
    vi.mocked(apiClient.get).mockResolvedValue({
      success: true,
      data: {},
    });

    const permissions = await AuthService.getCurrentUserPermissions('user-1');
    expect(permissions).toEqual([]);
  });

  it('should handle missing permissions field (defaults to empty array)', async () => {
    const mockResponse = {
      data: {
        user: {
          id: '1',
          username: 'testuser',
          email: 'test@example.com',
        },
        // permissions field missing
      },
    };

    vi.mocked(apiClient.post).mockResolvedValue({
      success: true,
      data: mockResponse.data,
    });

    const result = await AuthService.login({ identifier: 'testuser', password: 'password' });

    expect(result.success).toBe(true);
    expect(result.data?.permissions).toEqual([]);

    const authData = AuthStorage.getAuthData();
    expect(authData?.permissions).toEqual([]);
  });

  it('should store auth metadata in sessionStorage when remember is false', async () => {
    const mockResponse = {
      data: {
        user: {
          id: '1',
          username: 'testuser',
          email: 'test@example.com',
        },
        permissions: [],
      },
    };

    vi.mocked(apiClient.post).mockResolvedValue({
      success: true,
      data: mockResponse.data,
    });

    const result = await AuthService.login({
      identifier: 'testuser',
      password: 'password',
      remember: false,
    });

    expect(result.success).toBe(true);
    expect(sessionStorage.getItem('authData')).not.toBeNull();
    expect(localStorage.getItem('authData')).toBeNull();
  });

  it('should store auth metadata in localStorage when remember is true', async () => {
    const mockResponse = {
      data: {
        user: {
          id: '1',
          username: 'testuser',
          email: 'test@example.com',
        },
        permissions: [],
      },
    };

    vi.mocked(apiClient.post).mockResolvedValue({
      success: true,
      data: mockResponse.data,
    });

    const result = await AuthService.login({
      identifier: 'testuser',
      password: 'password',
      remember: true,
    });

    expect(result.success).toBe(true);
    expect(localStorage.getItem('authData')).not.toBeNull();
    expect(sessionStorage.getItem('authData')).toBeNull();
  });

  it('should preserve capability snapshot when updating profile metadata', async () => {
    AuthStorage.setAuthData(
      {
        user: {
          id: '1',
          username: 'testuser',
          full_name: 'Old Name',
          phone: '123',
          is_active: true,
          created_at: '2026-01-01T00:00:00Z',
          updated_at: '2026-01-01T00:00:00Z',
        },
        permissions: [{ resource: 'asset', action: 'read' }],
        capabilities: [
          {
            resource: 'asset',
            actions: ['read'],
            perspectives: [],
            data_scope: { owner_party_ids: ['party-1'], manager_party_ids: [] },
          },
        ],
        capabilities_cached_at: '2026-02-27T00:00:00Z',
        capabilities_version: 'v1',
        capabilities_generated_at: '2026-02-27T00:00:00Z',
      },
      { persistence: 'local' }
    );

    vi.mocked(apiClient.put).mockResolvedValue({
      success: true,
      data: {
        id: '1',
        username: 'testuser',
        full_name: 'New Name',
        phone: '123',
        is_active: true,
        created_at: '2026-01-01T00:00:00Z',
        updated_at: '2026-02-27T00:00:00Z',
      },
    });

    await AuthService.updateProfile({ fullName: 'New Name' });

    const updated = AuthStorage.getAuthData();
    expect(updated?.capabilities).toEqual([
      {
        resource: 'asset',
        actions: ['read'],
        perspectives: [],
        data_scope: { owner_party_ids: ['party-1'], manager_party_ids: [] },
      },
    ]);
    expect(updated?.capabilities_cached_at).toBe('2026-02-27T00:00:00Z');
    expect(updated?.capabilities_version).toBe('v1');
    expect(updated?.capabilities_generated_at).toBe('2026-02-27T00:00:00Z');
  });
});
