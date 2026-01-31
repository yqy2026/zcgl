import { describe, it, expect, beforeEach, vi } from 'vitest';
import { AuthStorage } from '../AuthStorage';

describe('AuthStorage', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.spyOn(Storage.prototype, 'getItem');
    vi.spyOn(Storage.prototype, 'setItem');
    vi.spyOn(Storage.prototype, 'removeItem');
  });

  it('should store auth data with correct structure', () => {
    const authData = {
      user: {
        id: '1',
        username: 'test',
        full_name: 'Test User',
        role: 'user',
        is_active: true,
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-01T00:00:00Z',
      },
      permissions: [{ resource: 'assets', action: 'read' }],
    };

    AuthStorage.setAuthData(authData);

    const stored = localStorage.getItem('authData');
    expect(stored).toBeDefined();
    expect(JSON.parse(stored!)).toEqual(authData);
    expect(localStorage.getItem('user')).toBe(JSON.stringify(authData.user));
    expect(localStorage.getItem('permissions')).toBe(JSON.stringify(authData.permissions));
  });

  it('should retrieve auth data correctly', () => {
    const authData = {
      user: {
        id: '1',
        username: 'test',
        full_name: 'Test User',
        role: 'user',
        is_active: true,
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-01T00:00:00Z',
      },
      permissions: [{ resource: 'assets', action: 'read' }],
    };

    AuthStorage.setAuthData(authData);
    const retrieved = AuthStorage.getAuthData();

    expect(retrieved).toEqual(authData);
  });

  it('should return null when no auth data exists', () => {
    const retrieved = AuthStorage.getAuthData();
    expect(retrieved).toBeNull();
  });

  it('should clear all auth-related data', () => {
    // Set multiple auth-related keys
    localStorage.setItem('token', 'test');
    localStorage.setItem('refresh_token', 'test');
    localStorage.setItem('authData', JSON.stringify({ user: { id: '1' }, permissions: [] }));
    localStorage.setItem('auth_token', 'legacy');
    localStorage.setItem('refreshToken', 'legacy-refresh');

    AuthStorage.clearAuthData();

    expect(localStorage.getItem('token')).toBeNull();
    expect(localStorage.getItem('refresh_token')).toBeNull();
    expect(localStorage.getItem('auth_token')).toBeNull();
    expect(localStorage.getItem('refreshToken')).toBeNull();
    expect(localStorage.getItem('authData')).toBeNull();
    expect(localStorage.getItem('user')).toBeNull();
    expect(localStorage.getItem('permissions')).toBeNull();
  });

  it('should get current user from authData', () => {
    const authData = {
      user: {
        id: '1',
        username: 'test',
        full_name: 'Test User',
        role: 'user',
        is_active: true,
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-01T00:00:00Z',
      },
      permissions: [],
    };

    AuthStorage.setAuthData(authData);
    const user = AuthStorage.getCurrentUser();

    expect(user).toEqual(authData.user);
  });

  it('should get permissions from authData', () => {
    const authData = {
      user: {
        id: '1',
        username: 'test',
        full_name: 'Test User',
        role: 'user',
        is_active: true,
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-01T00:00:00Z',
      },
      permissions: [{ resource: 'assets', action: 'read' }],
    };

    AuthStorage.setAuthData(authData);
    const permissions = AuthStorage.getPermissions();

    expect(permissions).toEqual([{ resource: 'assets', action: 'read' }]);
  });

  it('should check authentication status', () => {
    // Test when not authenticated
    expect(AuthStorage.isAuthenticated()).toBe(false);

    // Test when authenticated
    const authData = {
      user: {
        id: '1',
        username: 'test',
        full_name: 'Test User',
        role: 'user',
        is_active: true,
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-01T00:00:00Z',
      },
      permissions: [],
    };

    AuthStorage.setAuthData(authData);
    expect(AuthStorage.isAuthenticated()).toBe(true);
  });
});
