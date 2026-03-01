import { describe, it, expect } from 'vitest';
import { resolveOwnerPartyName } from '../AssetList';

describe('resolveOwnerPartyName', () => {
  it('prefers owner_party_name when present', () => {
    expect(
      resolveOwnerPartyName({
        owner_party_name: '新字段权属方',
        ownership_entity: '旧字段权属方',
      })
    ).toBe('新字段权属方');
  });

  it('falls back to legacy ownership_entity when owner_party_name is missing', () => {
    expect(
      resolveOwnerPartyName({
        ownership_entity: '旧字段权属方',
      })
    ).toBe('旧字段权属方');
  });

  it('returns undefined when both fields are blank', () => {
    expect(
      resolveOwnerPartyName({
        owner_party_name: '   ',
        ownership_entity: '',
      })
    ).toBeUndefined();
  });
});
