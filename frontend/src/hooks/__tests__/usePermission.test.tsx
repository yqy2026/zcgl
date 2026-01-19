import { renderHook, act } from '@testing-library/react';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import usePermission from '../usePermission';
import { AuthStorage } from '@/utils/AuthStorage';

// Mock MessageManager to avoid console output
vi.mock('@/utils/messageManager', () => ({
  MessageManager: {
    error: vi.fn(),
  },
}));

describe('usePermission', () => {
  beforeEach(() => {
    localStorage.clear();
    AuthStorage.clearAuthData();
    vi.clearAllMocks();
  });

  it('should load permissions from AuthStorage', () => {
    const mockAuthData = {
      token: 'test-token',
      refreshToken: 'test-refresh',
      user: { id: '1', username: 'test' },
      permissions: [
        { resource: 'assets', action: 'read' },
        { resource: 'users', action: 'write' }
      ]
    };

    AuthStorage.setAuthData(mockAuthData);

    const { result } = renderHook(() => usePermission());

    // Wait for the hook to complete loading
    expect(result.current.userPermissions).toEqual({
      userId: '1',
      username: 'test',
      roles: [],
      permissions: [
        { resource: 'assets', action: 'read' },
        { resource: 'users', action: 'write' }
      ],
      organizationId: undefined
    });
    expect(result.current.loading).toBe(false);
  });

  it('should return null permissions when not authenticated', () => {
    const { result } = renderHook(() => usePermission());

    expect(result.current.userPermissions).toBeNull();
    expect(result.current.loading).toBe(false);
  });

  it('should check permissions correctly', () => {
    const mockAuthData = {
      token: 'test-token',
      refreshToken: 'test-refresh',
      user: { id: '1', username: 'test' },
      permissions: [
        { resource: 'assets', action: 'read' }
      ]
    };

    AuthStorage.setAuthData(mockAuthData);

    const { result } = renderHook(() => usePermission());

    expect(result.current.hasPermission('assets', 'read')).toBe(true);
    expect(result.current.hasPermission('assets', 'write')).toBe(false);
  });

  it('should check admin role correctly', () => {
    const mockAuthData = {
      token: 'test-token',
      refreshToken: 'test-refresh',
      user: { id: '1', username: 'admin', role: 'admin' },
      permissions: []
    };

    AuthStorage.setAuthData(mockAuthData);

    const { result } = renderHook(() => usePermission());

    expect(result.current.isAdmin()).toBe(true);
    expect(result.current.hasRole('admin')).toBe(true);
    // Admin should have all permissions
    expect(result.current.hasPermission('any-resource', 'any-action')).toBe(true);
  });

  it('should handle role from auth data', () => {
    const mockAuthData = {
      token: 'test-token',
      refreshToken: 'test-refresh',
      user: { id: '1', username: 'manager', role: 'manager' },
      permissions: [
        { resource: 'assets', action: 'read' }
      ]
    };

    AuthStorage.setAuthData(mockAuthData);

    const { result } = renderHook(() => usePermission());

    expect(result.current.userPermissions?.roles).toEqual(['manager']);
    expect(result.current.hasRole('manager')).toBe(true);
    expect(result.current.hasRole('admin')).toBe(false);
  });

  it('should handle organizationId', () => {
    const mockAuthData = {
      token: 'test-token',
      refreshToken: 'test-refresh',
      user: { id: '1', username: 'test', organization_id: 'org-123' },
      permissions: []
    };

    AuthStorage.setAuthData(mockAuthData);

    const { result } = renderHook(() => usePermission());

    expect(result.current.userPermissions?.organizationId).toBe('org-123');
    expect(result.current.canAccessOrganization('org-123')).toBe(true);
    expect(result.current.canAccessOrganization('org-456')).toBe(false);
  });
});
