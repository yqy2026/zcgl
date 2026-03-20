import React from 'react';
import { renderHook, waitFor, act } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { ViewProvider, useView } from '../ViewContext';

const mockUseAuth = vi.fn();
const mockGetPartyById = vi.fn();

vi.mock('@/contexts/AuthContext', () => ({
  useAuth: () => mockUseAuth(),
}));

vi.mock('@/services/partyService', () => ({
  partyService: {
    getPartyById: (...args: unknown[]) => mockGetPartyById(...args),
  },
}));

const wrapper = ({ children }: { children: React.ReactNode }) => (
  <ViewProvider>{children}</ViewProvider>
);

const buildParty = (id: string, name: string) => ({
  id,
  name,
  code: `${name}-CODE`,
  party_type: 'organization' as const,
  status: 'active',
  created_at: '2026-03-16T00:00:00Z',
  updated_at: '2026-03-16T00:00:00Z',
});

describe('ViewContext', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
    sessionStorage.clear();
    mockUseAuth.mockReturnValue({
      user: {
        id: 'user-1',
        username: 'test-user',
      },
      capabilities: [],
      capabilitiesLoading: false,
      isAuthenticated: true,
    });
  });

  it('auto-selects the only available view option', async () => {
    mockUseAuth.mockReturnValue({
      user: {
        id: 'user-1',
        username: 'test-user',
      },
      capabilities: [
        {
          resource: 'asset',
          actions: ['read'],
          perspectives: ['owner'],
          data_scope: {
            owner_party_ids: ['party-1'],
            manager_party_ids: [],
          },
        },
      ],
      capabilitiesLoading: false,
      isAuthenticated: true,
    });
    mockGetPartyById.mockResolvedValue(buildParty('party-1', '主体A'));

    const { result } = renderHook(() => useView(), { wrapper });

    await waitFor(() => {
      expect(result.current.currentView?.key).toBe('owner:party-1');
    });

    expect(result.current.selectionRequired).toBe(false);
    expect(result.current.availableViews).toHaveLength(1);
    expect(result.current.currentView?.partyName).toBe('主体A');
  });

  it('clears stale selection and requires reselection when multiple options remain', async () => {
    localStorage.setItem(
      'view-selection:user-1',
      JSON.stringify({
        key: 'owner:party-1',
        perspective: 'owner',
        partyId: 'party-1',
      })
    );

    mockUseAuth.mockReturnValue({
      user: {
        id: 'user-1',
        username: 'test-user',
      },
      capabilities: [
        {
          resource: 'asset',
          actions: ['read'],
          perspectives: ['owner', 'manager'],
          data_scope: {
            owner_party_ids: ['party-1'],
            manager_party_ids: ['party-2'],
          },
        },
      ],
      capabilitiesLoading: false,
      isAuthenticated: true,
    });
    mockGetPartyById.mockImplementation(async (partyId: string) => {
      if (partyId === 'party-1') {
        return buildParty('party-1', '主体A');
      }
      return buildParty('party-2', '主体B');
    });

    const { result } = renderHook(() => useView(), { wrapper });

    await waitFor(() => {
      expect(result.current.currentView?.key).toBe('owner:party-1');
    });

    act(() => {
      window.dispatchEvent(new CustomEvent('authz-stale'));
    });

    await waitFor(() => {
      expect(result.current.selectionRequired).toBe(true);
    });

    expect(result.current.currentView).toBeNull();
    expect(result.current.availableViews).toHaveLength(2);
    expect(result.current.selectorOpen).toBe(true);
  });
});
