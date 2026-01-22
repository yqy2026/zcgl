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
        token: 'legacy-token',
        user: {
          id: '1',
          username: 'testuser',
          email: 'test@example.com',
          full_name: 'Test User',
          role: 'admin',
          organization_id: 'org-123',
        },
        data: {
          access_token: 'test-access-token',
          refresh_token: 'test-refresh-token',
          permissions: [
            { resource: 'assets', action: 'read', description: 'Read assets' },
            { resource: 'users', action: 'write', description: 'Write users' },
          ],
        },
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
        token: 'legacy-token',
        user: {
          id: '1',
          username: 'testuser',
          email: 'test@example.com',
        },
        data: {
          access_token: 'test-access-token',
          refresh_token: 'test-refresh-token',
          permissions: [],
        },
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

  it('should handle missing permissions field (defaults to empty array)', async () => {
    const mockResponse = {
      data: {
        token: 'legacy-token',
        user: {
          id: '1',
          username: 'testuser',
          email: 'test@example.com',
        },
        data: {
          access_token: 'test-access-token',
          refresh_token: 'test-refresh-token',
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
