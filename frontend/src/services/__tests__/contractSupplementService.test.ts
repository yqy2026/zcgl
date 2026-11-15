import { expect, it, vi, beforeEach } from 'vitest';
import { apiClient } from '@/api/client';
import { contractSupplementService } from '@/services/contractSupplementService';
vi.mock('@/api/client', () => ({ apiClient: { get: vi.fn(), post: vi.fn() } }));
beforeEach(() => vi.clearAllMocks());
it('reads the precise parent without a local cache', async () => {
  vi.mocked(apiClient.get).mockResolvedValue({ success: true, data: { items: [] } });
  expect(await contractSupplementService.list('terminal', 'p')).toEqual([]);
  expect(apiClient.get).toHaveBeenCalledWith('/api/v1/contract-supplements', {
    params: { contract_kind: 'terminal', contract_id: 'p' },
    cache: false,
  });
});
it('does not retry registrations or withdrawals and retains the version', async () => {
  vi.mocked(apiClient.post).mockResolvedValue({ success: true, data: { id: 's' } });
  await contractSupplementService.register({
    contract_kind: 'upstream',
    contract_id: 'p',
    agreement_number: '1',
    title: '补充协议',
    signed_on: null,
  });
  expect(apiClient.post).toHaveBeenLastCalledWith(
    '/api/v1/contract-supplements',
    expect.objectContaining({ contract_id: 'p' }),
    { retry: false }
  );
  await contractSupplementService.withdraw('a/b', 3, '误登记');
  expect(apiClient.post).toHaveBeenLastCalledWith(
    '/api/v1/contract-supplements/a%2Fb/withdrawal',
    { expected_version: 3, reason: '误登记' },
    { retry: false }
  );
});
it('rejects empty responses', async () => {
  vi.mocked(apiClient.get).mockResolvedValue({ success: false });
  await expect(contractSupplementService.list('upstream', 'p')).rejects.toThrow();
});
