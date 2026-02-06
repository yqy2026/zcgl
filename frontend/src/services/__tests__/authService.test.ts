import { describe, it, expect, beforeEach, vi } from 'vitest';
import { AuthService } from '../authService';
import { AuthStorage } from '@/utils/AuthStorage';

// Mock API client
vi.mock('@/api/client', () => ({
  apiClient: {
    post: vi.fn(),
    get: vi.fn(),
  },
}));

import { apiClient } from '@/api/client';

describe('AuthService - Login with Permissions', () => {
  beforeEach(() => {
    localStorage.clear();
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

    const result = await AuthService.login({ username: 'testuser', password: 'password' });

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

    const result = await AuthService.login({ username: 'testuser', password: 'password' });

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
    expect(apiClient.get).toHaveBeenCalledWith('/auth/me', expect.objectContaining({
      cache: false,
    }));
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

    const result = await AuthService.login({ username: 'testuser', password: 'password' });

    expect(result.success).toBe(true);
    expect(result.data?.permissions).toEqual([]);

    const authData = AuthStorage.getAuthData();
    expect(authData?.permissions).toEqual([]);
  });
});
