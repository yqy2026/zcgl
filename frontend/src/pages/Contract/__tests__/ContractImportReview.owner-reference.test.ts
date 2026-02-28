import { describe, expect, it } from 'vitest';

import { resolveOwnerReferences } from '../ContractImportReview';

describe('resolveOwnerReferences', () => {
  it('keeps owner_party_id from stored values when validateFields result does not include it', () => {
    const result = resolveOwnerReferences(
      {
        ownership_id: 'legacy-owner-001',
      },
      {
        owner_party_id: 'party-001',
        ownership_id: 'legacy-owner-001',
      }
    );

    expect(result.ownerPartyId).toBe('party-001');
    expect(result.ownershipId).toBe('legacy-owner-001');
  });

  it('prefers validated owner_party_id when field is explicitly present', () => {
    const result = resolveOwnerReferences(
      {
        owner_party_id: 'party-validated',
      },
      {
        owner_party_id: 'party-stored',
      }
    );

    expect(result.ownerPartyId).toBe('party-validated');
  });

  it('normalizes blank owner and ownership ids to undefined', () => {
    const result = resolveOwnerReferences(
      {
        owner_party_id: '   ',
      },
      {
        ownership_id: '   ',
      }
    );

    expect(result.ownerPartyId).toBeUndefined();
    expect(result.ownershipId).toBeUndefined();
  });
});
