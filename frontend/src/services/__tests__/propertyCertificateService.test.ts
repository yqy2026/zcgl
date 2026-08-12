import { beforeEach, describe, expect, it, vi } from 'vitest';
import { apiClient } from '@/api/client';
import { propertyCertificateService } from '@/services/propertyCertificateService';
import type { PropertyCertificateListParams } from '@/services/propertyCertificateService';

vi.mock('@/api/client', () => ({
  apiClient: {
    get: vi.fn(),
  },
}));

describe('propertyCertificateService', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('passes asset_id to the server-side certificate list filter', async () => {
    vi.mocked(apiClient.get).mockResolvedValue({ success: true, data: [] });
    const params = {
      skip: 10,
      limit: 20,
      asset_id: 'asset-1',
    } satisfies PropertyCertificateListParams;

    await propertyCertificateService.listCertificates(params);

    expect(apiClient.get).toHaveBeenCalledWith('/property-certificates', {
      params,
    });
    expect(vi.mocked(apiClient.get).mock.calls[0]?.[1]?.params).toBe(params);
  });
});
