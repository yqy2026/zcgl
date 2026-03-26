import { describe, expect, it } from 'vitest';

import {
  evaluateCapability,
  getAvailablePerspectives,
  hasPartyScopeAccess,
} from '@/utils/authz/capabilityEvaluator';

describe('capabilityEvaluator', () => {
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
