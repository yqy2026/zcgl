import { renderHook } from '@/test/utils/test-helpers';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { useCapabilities } from '@/hooks/useCapabilities';

const mockUseAuth = vi.hoisted(() => vi.fn());

vi.mock('@/contexts/AuthContext', () => ({
  useAuth: mockUseAuth,
}));

describe('useCapabilities', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('merges capabilities by resource and unions actions/data scope', () => {
    mockUseAuth.mockReturnValue({
      isAdmin: false,
      capabilitiesLoading: false,
      capabilities: [
        {
          resource: 'asset',
          actions: ['read'],
          perspectives: ['owner'],
          data_scope: {
            owner_party_ids: ['owner-1'],
            manager_party_ids: [],
          },
        },
        {
          resource: 'asset',
          actions: ['update'],
          perspectives: ['manager'],
          data_scope: {
            owner_party_ids: ['owner-1', 'owner-2'],
            manager_party_ids: ['manager-1'],
          },
        },
      ],
    });

    const { result } = renderHook(() => useCapabilities());

    expect(result.current.canPerform('read', 'asset')).toBe(true);
    expect(result.current.canPerform('update', 'asset')).toBe(true);
    expect(result.current.getAvailableActions('asset').sort()).toEqual(['read', 'update']);
    expect(result.current.hasPartyAccess('owner-2', 'owner', 'asset')).toBe(true);
    expect(result.current.hasPartyAccess('manager-1', 'manager', 'asset')).toBe(true);
  });

  it('applies project perspective override and blocks owner perspective', () => {
    mockUseAuth.mockReturnValue({
      isAdmin: false,
      capabilitiesLoading: false,
      capabilities: [
        {
          resource: 'project',
          actions: ['read', 'update'],
          perspectives: ['owner', 'manager'],
          data_scope: {
            owner_party_ids: ['owner-project'],
            manager_party_ids: ['manager-project'],
          },
        },
      ],
    });

    const { result } = renderHook(() => useCapabilities());

    expect(result.current.getAvailablePerspectives('project')).toEqual(['manager']);
    expect(result.current.canPerform('update', 'project', 'owner')).toBe(false);
    expect(result.current.canPerform('update', 'project', 'manager')).toBe(true);
  });

  it('supports temporary admin-only backup action', () => {
    mockUseAuth.mockReturnValue({
      isAdmin: true,
      capabilitiesLoading: false,
      capabilities: [],
    });

    const { result } = renderHook(() => useCapabilities());
    expect(result.current.canPerform('backup', 'system')).toBe(true);

    mockUseAuth.mockReturnValue({
      isAdmin: false,
      capabilitiesLoading: false,
      capabilities: [],
    });
    const nonAdminResult = renderHook(() => useCapabilities());
    expect(nonAdminResult.result.current.canPerform('backup', 'system')).toBe(false);
  });
});
