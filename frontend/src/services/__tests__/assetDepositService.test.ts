import { expect, it, vi } from 'vitest';
import { apiClient } from '@/api/client';
import { assetDepositService } from '../assetDepositService';

vi.mock('@/api/client', () => ({ apiClient: { get: vi.fn(), post: vi.fn() } }));
it('converts deposit amounts and preserves a denied scope', async () => {
  vi.mocked(apiClient.get).mockResolvedValueOnce({
    success: true,
    data: { id: 'd', held_amount: '12.50', agreed_amount: '20.00' },
  });
  expect(await assetDepositService.detail('d')).toMatchObject({
    held_amount: 12.5,
    agreed_amount: 20,
  });
  vi.mocked(apiClient.get).mockResolvedValueOnce({
    success: false,
    error: '无权',
    rawResponse: { data: { error: { code: 'PARTY_SCOPE_MISSING' } } },
  });
  await expect(assetDepositService.list('terminal', 'c')).rejects.toMatchObject({
    code: 'PARTY_SCOPE_MISSING',
  });
});
