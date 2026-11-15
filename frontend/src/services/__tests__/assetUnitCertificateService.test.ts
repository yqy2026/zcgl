import { expect, it, vi } from 'vitest';
import { AxiosError, AxiosHeaders } from 'axios';
import { apiClient } from '@/api/client';
import { ApiErrorHandler } from '@/utils/responseExtractor';
import { assetOperationsService } from '@/services/assetOperationsService';

vi.mock('@/api/client', () => ({ apiClient: { get: vi.fn() } }));

it.each(['listAssetUnitCertificates', 'getAssetUnit'] as const)(
  '%s preserves scope codes after the shared interceptor enhances an Axios rejection',
  async method => {
    const original = new AxiosError('Forbidden', 'ERR_BAD_REQUEST', undefined, undefined, {
      status: 403,
      statusText: 'Forbidden',
      headers: {},
      config: { headers: new AxiosHeaders() },
      data: { success: false, error: { code: 'PARTY_SCOPE_MISSING', message: '范围缺失' } },
    });
    vi.mocked(apiClient.get).mockRejectedValueOnce(ApiErrorHandler.handleError(original));
    await expect(assetOperationsService[method]('unit-1')).rejects.toMatchObject({
      code: 'PARTY_SCOPE_MISSING',
    });
  }
);
