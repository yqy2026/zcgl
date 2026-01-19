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
      token: 'test-token',
      refreshToken: 'test-refresh',
      user: { id: '1', username: 'test' },
      permissions: [{ resource: 'assets', action: 'read' }]
    };

    AuthStorage.setAuthData(authData);

    const stored = localStorage.getItem('authData');
    expect(stored).toBeDefined();
    expect(JSON.parse(stored!)).toEqual(authData);
  });

  it('should retrieve auth data correctly', () => {
    const authData = {
      token: 'test-token',
      refreshToken: 'test-refresh',
      user: { id: '1', username: 'test' },
      permissions: [{ resource: 'assets', action: 'read' }]
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
    localStorage.setItem('authData', JSON.stringify({ token: 'test' }));

    AuthStorage.clearAuthData();

    expect(localStorage.getItem('token')).toBeNull();
    expect(localStorage.getItem('refresh_token')).toBeNull();
    expect(localStorage.getItem('authData')).toBeNull();
  });

  it('should get token from authData', () => {
    const authData = {
      token: 'test-token',
      refreshToken: 'test-refresh',
      user: { id: '1' },
      permissions: []
    };

    AuthStorage.setAuthData(authData);
    const token = AuthStorage.getToken();

    expect(token).toBe('test-token');
  });
});
