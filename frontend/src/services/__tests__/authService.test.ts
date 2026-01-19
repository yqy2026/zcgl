import { describe, it, expect, beforeEach, vi } from 'vitest';
import { AuthService } from '../authService';
import { AuthStorage } from '@/utils/AuthStorage';

// Mock API client
vi.mock('@/api/client', () => ({
  enhancedApiClient: {
    post: vi.fn(),
    get: vi.fn(),
  },
}));

import { enhancedApiClient } from '@/api/client';

describe('AuthService - Login with Permissions', () => {
  beforeEach(() => {
    localStorage.clear();
    AuthStorage.clearAuthData();
    vi.clearAllMocks();
  });

  it('should store permissions from login response', async () => {
    const mockResponse = {
      data: {
        access_token: 'test-access-token',
        refresh_token: 'test-refresh-token',
        token_type: 'Bearer',
        expires_in: 3600,
        user: {
          id: '1',
          username: 'testuser',
          email: 'test@example.com',
          full_name: 'Test User',
          role: 'admin',
          organization_id: 'org-123',
        },
        permissions: [
          { resource: 'assets', action: 'read', description: 'Read assets' },
          { resource: 'users', action: 'write', description: 'Write users' },
        ],
      },
    };

    vi.mocked(enhancedApiClient.post).mockResolvedValue({
      success: true,
      data: mockResponse.data,
    });

    const result = await AuthService.login('testuser', 'password');

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
        access_token: 'test-access-token',
        refresh_token: 'test-refresh-token',
        token_type: 'Bearer',
        expires_in: 3600,
        user: {
          id: '1',
          username: 'testuser',
          email: 'test@example.com',
        },
        permissions: [],
      },
    };

    vi.mocked(enhancedApiClient.post).mockResolvedValue({
      success: true,
      data: mockResponse.data,
    });

    const result = await AuthService.login('testuser', 'password');

    expect(result.success).toBe(true);
    expect(result.data?.permissions).toEqual([]);

    const authData = AuthStorage.getAuthData();
    expect(authData?.permissions).toEqual([]);
  });

  it('should handle missing permissions field (defaults to empty array)', async () => {
    const mockResponse = {
      data: {
        access_token: 'test-access-token',
        refresh_token: 'test-refresh-token',
        token_type: 'Bearer',
        expires_in: 3600,
        user: {
          id: '1',
          username: 'testuser',
          email: 'test@example.com',
        },
        // permissions field missing
      },
    };

    vi.mocked(enhancedApiClient.post).mockResolvedValue({
      success: true,
      data: mockResponse.data,
    });

    const result = await AuthService.login('testuser', 'password');

    expect(result.success).toBe(true);
    expect(result.data?.permissions).toEqual([]);

    const authData = AuthStorage.getAuthData();
    expect(authData?.permissions).toEqual([]);
  });
});
