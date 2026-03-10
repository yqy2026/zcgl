import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, expect, it } from 'vitest';
import { API_ENDPOINTS } from '@/constants/api';

const readApiConstantsSource = (): string => {
  return readFileSync(resolve(process.cwd(), 'src/constants/api.ts'), 'utf8');
};

describe('api constants rental retirement', () => {
  it('stops exposing legacy rent contract API constants', () => {
    const source = readApiConstantsSource();

    expect('RENT_CONTRACT' in API_ENDPOINTS).toBe(false);
    expect(source).not.toContain('export const RENT_CONTRACT_API');
    expect(source).not.toContain('/rental-contracts/');
  });

  it('exposes contract group API constants for the new workflow entry', () => {
    expect(API_ENDPOINTS).toHaveProperty('CONTRACT_GROUP');
    expect(API_ENDPOINTS.CONTRACT_GROUP.LIST).toBe('/contract-groups');
    expect(API_ENDPOINTS.CONTRACT_GROUP.DETAIL('group-1')).toBe('/contract-groups/group-1');
    expect(API_ENDPOINTS.CONTRACT_GROUP.CREATE).toBe('/contract-groups');
    expect(API_ENDPOINTS.CONTRACT_GROUP.UPDATE('group-1')).toBe('/contract-groups/group-1');
  });
});
