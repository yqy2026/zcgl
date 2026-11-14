import { expect, it, vi } from 'vitest';
import { apiClient } from '@/api/client';
import { assetOperationsService } from '@/services/assetOperationsService';
vi.mock('@/api/client', () => ({ apiClient: { get: vi.fn(), post: vi.fn() } }));
it('encodes both identities and keeps effective-date semantics', async () => {
  vi.mocked(apiClient.post).mockResolvedValue({ success: true, data: { items: [] } });
  await assetOperationsService.linkCertificate('unit/a', {
    certificate_id: 'cert/b',
    effective_from: '2027-01-01',
  });
  expect(apiClient.post).toHaveBeenCalledWith(
    '/api/v1/asset-units/unit%2Fa/property-certificates',
    { certificate_id: 'cert/b', effective_from: '2027-01-01' }
  );
  await assetOperationsService.unlinkCertificate('unit/a', 'cert/b', '2027-02-01');
  expect(apiClient.post).toHaveBeenLastCalledWith(
    '/api/v1/asset-units/unit%2Fa/property-certificates/cert%2Fb/unlink',
    { effective_from: '2027-02-01' }
  );
});
it('keeps the conflict code on a failed write', async () => {
  vi.mocked(apiClient.post).mockResolvedValue({
    success: false,
    error: 'conflict',
    rawResponse: { data: { error: { code: 'CERTIFICATE_LINK_HISTORY_PROTECTED' } } },
  });
  await expect(
    assetOperationsService.linkCertificate('u', {
      certificate_id: 'c',
      effective_from: '2027-01-01',
    })
  ).rejects.toMatchObject({ code: 'CERTIFICATE_LINK_HISTORY_PROTECTED' });
});
