import { describe, expect, it } from 'vitest';
import { assetFormSchema } from '@/assetFormSchema';

describe('assetFormSchema', () => {
  const basePayload = {
    asset_name: '测试物业',
    address: '测试地址',
    ownership_status: '已确权' as const,
    property_nature: '经营类' as const,
    usage_status: '出租' as const,
  };

  it('requires owner_party_id', () => {
    const result = assetFormSchema.safeParse(basePayload);

    expect(result.success).toBe(false);
    if (result.success) {
      return;
    }
    expect(result.error.issues.some(issue => issue.path.join('.') === 'owner_party_id')).toBe(true);
  });

  it('accepts payload when owner_party_id is provided', () => {
    const result = assetFormSchema.safeParse({
      ...basePayload,
      owner_party_id: 'party-001',
    });

    expect(result.success).toBe(true);
  });
});
