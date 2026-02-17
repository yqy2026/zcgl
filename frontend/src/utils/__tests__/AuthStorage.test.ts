import { describe, it, expect, beforeEach, vi } from 'vitest';
import { AuthStorage } from '../AuthStorage';

describe('AuthStorage', () => {
  beforeEach(() => {
    localStorage.clear();
    sessionStorage.clear();
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
        role_id: 'role-user-id',
        role_name: 'user',
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
        role_id: 'role-user-id',
        role_name: 'user',
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

  it('should store auth data in sessionStorage when persistence is session', () => {
    const authData = {
      user: {
        id: 'session-user',
        username: 'session-test',
        full_name: 'Session User',
        role_id: 'role-user-id',
        role_name: 'user',
        is_active: true,
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-01T00:00:00Z',
      },
      permissions: [{ resource: 'assets', action: 'read' }],
    };

    AuthStorage.setAuthData(authData, { persistence: 'session' });

    expect(sessionStorage.getItem('authData')).toBe(JSON.stringify(authData));
    expect(sessionStorage.getItem('user')).toBe(JSON.stringify(authData.user));
    expect(sessionStorage.getItem('permissions')).toBe(JSON.stringify(authData.permissions));
    expect(localStorage.getItem('authData')).toBeNull();
  });

  it('should persist metadata updated timestamp with auth data', () => {
    const authData = {
      user: {
        id: 'time-user',
        username: 'timestamp-test',
        full_name: 'Timestamp User',
        role_id: 'role-user-id',
        role_name: 'user',
        is_active: true,
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-01T00:00:00Z',
      },
      permissions: [{ resource: 'assets', action: 'read' }],
    };

    AuthStorage.setAuthData(authData, { persistence: 'session' });
    expect(sessionStorage.getItem('authDataUpdatedAt')).not.toBeNull();
  });

  it('should prefer fresher metadata when both storages contain auth data', () => {
    const localAuthData = {
      user: {
        id: 'local-user',
        username: 'local-test',
        full_name: 'Local User',
        role_id: 'role-user-id',
        role_name: 'user',
        is_active: true,
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-01T00:00:00Z',
      },
      permissions: [{ resource: 'local', action: 'read' }],
    };

    const sessionAuthData = {
      user: {
        id: 'session-user',
        username: 'session-test',
        full_name: 'Session User',
        role_id: 'role-user-id',
        role_name: 'user',
        is_active: true,
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-01T00:00:00Z',
      },
      permissions: [{ resource: 'session', action: 'read' }],
    };

    localStorage.setItem('authData', JSON.stringify(localAuthData));
    localStorage.setItem('authDataUpdatedAt', String(Date.now()));
    sessionStorage.setItem('authData', JSON.stringify(sessionAuthData));
    sessionStorage.setItem('authDataUpdatedAt', String(Date.now() - 5000));

    const retrieved = AuthStorage.getAuthData();
    expect(retrieved).toEqual(localAuthData);
  });

  it('should prefer localStorage on user conflict when recency metadata is missing', () => {
    const localAuthData = {
      user: {
        id: 'local-user',
        username: 'local-test',
        full_name: 'Local User',
        role_id: 'role-user-id',
        role_name: 'user',
        is_active: true,
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-01T00:00:00Z',
      },
      permissions: [{ resource: 'local', action: 'read' }],
    };

    const sessionAuthData = {
      user: {
        id: 'session-user',
        username: 'session-test',
        full_name: 'Session User',
        role_id: 'role-user-id',
        role_name: 'user',
        is_active: true,
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-01T00:00:00Z',
      },
      permissions: [{ resource: 'session', action: 'read' }],
    };

    localStorage.setItem('authData', JSON.stringify(localAuthData));
    sessionStorage.setItem('authData', JSON.stringify(sessionAuthData));

    const retrieved = AuthStorage.getAuthData();
    expect(retrieved).toEqual(localAuthData);
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
    localStorage.setItem('authDataUpdatedAt', String(Date.now()));
    localStorage.setItem('auth_token', 'legacy');
    localStorage.setItem('refreshToken', 'legacy-refresh');
    sessionStorage.setItem('authData', JSON.stringify({ user: { id: '2' }, permissions: [] }));
    sessionStorage.setItem('authDataUpdatedAt', String(Date.now()));
    sessionStorage.setItem('user', JSON.stringify({ id: '2' }));
    sessionStorage.setItem('permissions', JSON.stringify([]));

    AuthStorage.clearAuthData();

    expect(localStorage.getItem('token')).toBeNull();
    expect(localStorage.getItem('refresh_token')).toBeNull();
    expect(localStorage.getItem('auth_token')).toBeNull();
    expect(localStorage.getItem('refreshToken')).toBeNull();
    expect(localStorage.getItem('authData')).toBeNull();
    expect(localStorage.getItem('authDataUpdatedAt')).toBeNull();
    expect(localStorage.getItem('user')).toBeNull();
    expect(localStorage.getItem('permissions')).toBeNull();
    expect(sessionStorage.getItem('authData')).toBeNull();
    expect(sessionStorage.getItem('authDataUpdatedAt')).toBeNull();
    expect(sessionStorage.getItem('user')).toBeNull();
    expect(sessionStorage.getItem('permissions')).toBeNull();
  });

  it('should get current user from authData', () => {
    const authData = {
      user: {
        id: '1',
        username: 'test',
        full_name: 'Test User',
        role_id: 'role-user-id',
        role_name: 'user',
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
        role_id: 'role-user-id',
        role_name: 'user',
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
        role_id: 'role-user-id',
        role_name: 'user',
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
