import { beforeEach, describe, expect, it } from 'vitest';
import type { CapabilitiesResponse } from '@/types/capability';
import { useDataScopeStore } from '../dataScopeStore';

const createResponse = (
  overrides?: Partial<CapabilitiesResponse['capabilities'][number]>[]
): CapabilitiesResponse => ({
  version: '2026-03-25.v1',
  generated_at: '2026-04-04T00:00:00Z',
  capabilities: (overrides ?? []).map((override, index) => ({
    resource: override?.resource ?? `resource-${index}`,
    actions: override?.actions ?? ['read'],
    perspectives: override?.perspectives ?? ['owner'],
    data_scope: {
      owner_party_ids: override?.data_scope?.owner_party_ids ?? [],
      manager_party_ids: override?.data_scope?.manager_party_ids ?? [],
    },
  })),
});

describe('dataScopeStore', () => {
  beforeEach(() => {
    useDataScopeStore.getState().reset();
  });

  it('initializes from capabilities response', () => {
    const response = createResponse([
      {
        resource: 'asset',
        data_scope: { owner_party_ids: ['owner-2', 'owner-1'], manager_party_ids: [] },
      },
      {
        resource: 'project',
        data_scope: { owner_party_ids: ['owner-1'], manager_party_ids: ['manager-1'] },
      },
    ]);

    useDataScopeStore.getState().initFromCapabilities(response, false);
    const state = useDataScopeStore.getState();

    expect(state.bindingTypes).toEqual(['owner', 'manager']);
    expect(state.ownerPartyIds).toEqual(['owner-1', 'owner-2']);
    expect(state.managerPartyIds).toEqual(['manager-1']);
    expect(state.initialized).toBe(true);
  });

  it('handles single owner binding', () => {
    const response = createResponse([
      {
        data_scope: { owner_party_ids: ['owner-1'], manager_party_ids: [] },
      },
    ]);

    useDataScopeStore.getState().initFromCapabilities(response, false);
    const state = useDataScopeStore.getState();

    expect(state.isSingleOwner).toBe(true);
    expect(state.getEffectivePerspective()).toBe('owner');
  });

  it('handles single manager binding', () => {
    const response = createResponse([
      {
        perspectives: ['manager'],
        data_scope: { owner_party_ids: [], manager_party_ids: ['manager-1'] },
      },
    ]);

    useDataScopeStore.getState().initFromCapabilities(response, false);
    const state = useDataScopeStore.getState();

    expect(state.isSingleManager).toBe(true);
    expect(state.getEffectivePerspective()).toBe('manager');
  });

  it('handles dual binding', () => {
    const response = createResponse([
      {
        perspectives: ['owner', 'manager'],
        data_scope: { owner_party_ids: ['owner-1'], manager_party_ids: ['manager-1'] },
      },
    ]);

    useDataScopeStore.getState().initFromCapabilities(response, false);
    const state = useDataScopeStore.getState();

    expect(state.isDualBinding).toBe(true);
    expect(state.getEffectivePerspective()).toBeNull();
  });

  it('stores admin flag', () => {
    const response = createResponse([]);

    useDataScopeStore.getState().initFromCapabilities(response, true);

    expect(useDataScopeStore.getState().isAdmin).toBe(true);
    expect(useDataScopeStore.getState().getEffectivePerspective()).toBeNull();
  });

  it('resets on logout', () => {
    const response = createResponse([
      {
        data_scope: { owner_party_ids: ['owner-1'], manager_party_ids: [] },
      },
    ]);
    useDataScopeStore.getState().initFromCapabilities(response, true);

    useDataScopeStore.getState().reset();
    const state = useDataScopeStore.getState();

    expect(state.bindingTypes).toEqual([]);
    expect(state.ownerPartyIds).toEqual([]);
    expect(state.managerPartyIds).toEqual([]);
    expect(state.isAdmin).toBe(false);
    expect(state.initialized).toBe(false);
  });
});
