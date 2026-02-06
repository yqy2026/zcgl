import { renderHook } from '@/test/utils/test-helpers';
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
      roles: ['user'],
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
      user: {
        id: '1',
        username: 'admin',
        full_name: 'Admin User',
        role_id: 'role-admin-id',
        role_name: 'admin',
        roles: ['admin'],
        is_active: true,
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-01T00:00:00Z',
      },
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
      user: {
        id: '1',
        username: 'manager',
        full_name: 'Manager User',
        role_id: 'role-manager-id',
        role_name: 'manager',
        is_active: true,
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-01T00:00:00Z',
      },
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
      user: {
        id: '1',
        username: 'test',
        full_name: 'Test User',
        role_id: 'role-user-id',
        role_name: 'user',
        is_active: true,
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-01T00:00:00Z',
        default_organization_id: 'org-123',
      },
      permissions: []
    };

    AuthStorage.setAuthData(mockAuthData);

    const { result } = renderHook(() => usePermission());

    expect(result.current.userPermissions?.organizationId).toBe('org-123');
    expect(result.current.canAccessOrganization('org-123')).toBe(true);
    expect(result.current.canAccessOrganization('org-456')).toBe(false);
  });
});
