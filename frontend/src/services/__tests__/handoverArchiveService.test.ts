import { expect, it, vi } from 'vitest';
import { apiClient } from '@/api/client';
import { handoverArchiveService } from '@/services/handoverArchiveService';
vi.mock('@/api/client', () => ({ apiClient: { get: vi.fn() } }));
it('queries the precise parent without cached facts', async () => {
  vi.mocked(apiClient.get).mockResolvedValue({ success: true, data: { items: [] } });
  expect(await handoverArchiveService.list('terminal', 'parent')).toEqual([]);
  expect(apiClient.get).toHaveBeenCalledWith('/api/v1/archive/handover-targets', {
    params: { contract_kind: 'terminal', contract_id: 'parent' },
    cache: false,
  });
});
it('rejects a missing response rather than inventing an empty list', async () => {
  vi.mocked(apiClient.get).mockResolvedValue({ success: true, data: null });
  await expect(handoverArchiveService.list('upstream', 'p')).rejects.toMatchObject({
    code: 'HANDOVER_READ_FAILED',
  });
});
