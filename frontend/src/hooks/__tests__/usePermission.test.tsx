import { renderHook } from '@/test/utils/test-helpers';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import usePermission from '../usePermission';

const mockUseAuth = vi.hoisted(() => vi.fn());
const mockUseCapabilities = vi.hoisted(() => vi.fn());

vi.mock('@/contexts/AuthContext', () => ({
  useAuth: mockUseAuth,
}));

vi.mock('@/hooks/useCapabilities', () => ({
  useCapabilities: mockUseCapabilities,
}));

describe('usePermission (compat shell)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('returns null userPermissions when user is missing', () => {
    mockUseAuth.mockReturnValue({
      user: null,
      permissions: [],
    });
    mockUseCapabilities.mockReturnValue({
      canPerform: vi.fn(() => false),
      hasPartyAccess: vi.fn(() => false),
      loading: false,
    });

    const { result } = renderHook(() => usePermission());
    expect(result.current.userPermissions).toBeNull();
  });

  it('maps legacy permission vocabulary to capability checks', () => {
    const canPerform = vi.fn(() => true);

    mockUseAuth.mockReturnValue({
      user: {
        id: 'u-1',
        username: 'tester',
        is_admin: false,
        roles: ['user'],
      },
      permissions: [],
    });
    mockUseCapabilities.mockReturnValue({
      canPerform,
      hasPartyAccess: vi.fn(() => false),
      loading: false,
    });

    const { result } = renderHook(() => usePermission());
    expect(result.current.hasPermission('rental', 'view')).toBe(true);
    expect(canPerform).toHaveBeenCalledWith('read', 'rent_contract');
  });

  it('uses user.is_admin as admin source', () => {
    mockUseAuth.mockReturnValue({
      user: {
        id: 'u-1',
        username: 'admin',
        is_admin: true,
        roles: ['admin'],
      },
      permissions: [],
    });
    mockUseCapabilities.mockReturnValue({
      canPerform: vi.fn(() => true),
      hasPartyAccess: vi.fn(() => true),
      loading: false,
    });

    const { result } = renderHook(() => usePermission());
    expect(result.current.isAdmin()).toBe(true);
  });

  it('checks organization access via party scope helper', () => {
    const hasPartyAccess = vi.fn(() => true);

    mockUseAuth.mockReturnValue({
      user: {
        id: 'u-1',
        username: 'user',
        is_admin: false,
        roles: ['user'],
      },
      permissions: [],
    });
    mockUseCapabilities.mockReturnValue({
      canPerform: vi.fn(() => false),
      hasPartyAccess,
      loading: false,
    });

    const { result } = renderHook(() => usePermission());
    expect(result.current.canAccessOrganization('party-1')).toBe(true);
    expect(hasPartyAccess).toHaveBeenCalledWith('party-1', 'owner', 'party');
  });
});
