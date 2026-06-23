import { describe, expect, it } from 'vitest';

import {
  evaluateCapability,
  getAvailablePerspectives,
  hasPartyScopeAccess,
} from '@/utils/authz/capabilityEvaluator';
import type { CapabilityItem } from '@/types/capability';

const assetCapability = (overrides: Partial<CapabilityItem> = {}): CapabilityItem => ({
  resource: 'asset',
  actions: ['read', 'update'],
  perspectives: ['owner'],
  data_scope: {
    owner_party_ids: ['owner-1'],
    manager_party_ids: ['manager-1'],
  },
  ...overrides,
});

describe('capabilityEvaluator', () => {
  it('allows admin users without requiring a matching capability', () => {
    expect(
      evaluateCapability({
        capabilities: [],
        isAdmin: true,
        action: 'delete',
        resourceType: 'asset',
        perspective: 'manager',
      })
    ).toBe(true);
  });

  it('allows matching actions and rejects missing actions', () => {
    const capability = assetCapability({ actions: ['read'] });

    expect(
      evaluateCapability({
        capabilities: [capability],
        isAdmin: false,
        action: 'read',
        resourceType: 'asset',
      })
    ).toBe(true);

    expect(
      evaluateCapability({
        capabilities: [capability],
        isAdmin: false,
        action: 'delete',
        resourceType: 'asset',
      })
    ).toBe(false);
  });

  it('enforces backend-provided perspective lists when present', () => {
    const capability = assetCapability({
      actions: ['read'],
      perspectives: ['owner'],
    });

    expect(
      evaluateCapability({
        capabilities: [capability],
        isAdmin: false,
        action: 'read',
        resourceType: 'asset',
        perspective: 'owner',
      })
    ).toBe(true);

    expect(
      evaluateCapability({
        capabilities: [capability],
        isAdmin: false,
        action: 'read',
        resourceType: 'asset',
        perspective: 'manager',
      })
    ).toBe(false);
  });

  it('treats empty perspective lists as action-only capabilities', () => {
    const capability = assetCapability({
      actions: ['read'],
      perspectives: [],
    });

    expect(
      evaluateCapability({
        capabilities: [capability],
        isAdmin: false,
        action: 'read',
        resourceType: 'asset',
        perspective: 'manager',
      })
    ).toBe(true);
  });

  it('rejects missing resource capabilities', () => {
    expect(
      evaluateCapability({
        capabilities: [assetCapability()],
        isAdmin: false,
        action: 'read',
        resourceType: 'project',
      })
    ).toBe(false);
  });

  it('allows owner and manager party scope matches and rejects mismatches', () => {
    const capability = assetCapability();

    expect(
      hasPartyScopeAccess({
        capabilities: [capability],
        isAdmin: false,
        partyId: 'owner-1',
        relationType: 'owner',
        resourceType: 'asset',
      })
    ).toBe(true);

    expect(
      hasPartyScopeAccess({
        capabilities: [capability],
        isAdmin: false,
        partyId: 'manager-1',
        relationType: 'manager',
        resourceType: 'asset',
      })
    ).toBe(true);

    expect(
      hasPartyScopeAccess({
        capabilities: [capability],
        isAdmin: false,
        partyId: 'manager-1',
        relationType: 'owner',
        resourceType: 'asset',
      })
    ).toBe(false);
  });

  it('rejects party scope access when the resource capability is missing', () => {
    expect(
      hasPartyScopeAccess({
        capabilities: [assetCapability()],
        isAdmin: false,
        partyId: 'owner-1',
        relationType: 'owner',
        resourceType: 'project',
      })
    ).toBe(false);
  });

  it('allows admin party scope access without scope ids', () => {
    expect(
      hasPartyScopeAccess({
        capabilities: [],
        isAdmin: true,
        partyId: 'party-any',
        relationType: 'owner',
        resourceType: 'asset',
      })
    ).toBe(true);
  });

  it('uses backend-provided project perspectives instead of local override tables', () => {
    const capability = {
      resource: 'project',
      actions: ['read', 'update'],
      perspectives: ['owner'],
      data_scope: {
        owner_party_ids: ['owner-project'],
        manager_party_ids: [],
      },
    } as const;

    expect(getAvailablePerspectives('project', capability)).toEqual(['owner']);
    expect(
      evaluateCapability({
        capabilities: [capability],
        isAdmin: false,
        action: 'update',
        resourceType: 'project',
        perspective: 'owner',
      })
    ).toBe(true);
  });

  it('uses backend party scope data without project-specific owner blocking', () => {
    const capability = {
      resource: 'project',
      actions: ['read'],
      perspectives: ['owner'],
      data_scope: {
        owner_party_ids: ['owner-project'],
        manager_party_ids: [],
      },
    } as const;

    expect(
      hasPartyScopeAccess({
        capabilities: [capability],
        isAdmin: false,
        partyId: 'owner-project',
        relationType: 'owner',
        resourceType: 'project',
      })
    ).toBe(true);
  });
});
