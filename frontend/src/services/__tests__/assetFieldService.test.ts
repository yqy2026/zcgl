import { beforeEach, describe, expect, it, vi } from 'vitest';

import { AssetFieldService } from '../asset/assetFieldService';

vi.mock('@/api/client', () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  },
}));

vi.mock('@/utils/responseExtractor', () => ({
  ApiErrorHandler: {
    handleError: vi.fn((error: unknown) => ({
      message: error instanceof Error ? error.message : 'Unknown error',
      code: 'UNKNOWN',
    })),
  },
}));

import { apiClient } from '@/api/client';

describe('AssetFieldService', () => {
  let service: AssetFieldService;

  beforeEach(() => {
    service = new AssetFieldService();
    vi.clearAllMocks();
  });

  it('getAssetCustomFieldValues should call backend values endpoint', async () => {
    vi.mocked(apiClient.get).mockResolvedValue({
      success: true,
      data: { values: [{ field_name: 'f1', field_value: 'v1' }] },
    });

    const result = await service.getAssetCustomFieldValues('asset-1');

    expect(result).toHaveLength(1);
    expect(apiClient.get).toHaveBeenCalledWith(
      '/asset-custom-fields/assets/asset-1/values',
      expect.any(Object)
    );
  });

  it('updateAssetCustomFieldValues should call backend values endpoint', async () => {
    const values = [{ field_name: 'f1', field_value: 'v1' }];
    vi.mocked(apiClient.put).mockResolvedValue({
      success: true,
      data: { values },
    });

    const result = await service.updateAssetCustomFieldValues('asset-1', values);

    expect(result).toEqual(values);
    expect(apiClient.put).toHaveBeenCalledWith(
      '/asset-custom-fields/assets/asset-1/values',
      { values },
      expect.any(Object)
    );
  });

  it('batchSetCustomFieldValues should send snake_case payload to batch-values endpoint', async () => {
    vi.mocked(apiClient.post).mockResolvedValue({ success: true });

    await expect(
      service.batchSetCustomFieldValues([
        { assetId: 'asset-1', values: [{ field_name: 'f1', field_value: 'v1' }] },
        { assetId: 'asset-2', values: [{ field_name: 'f2', field_value: 'v2' }] },
      ])
    ).resolves.toBeUndefined();

    expect(apiClient.post).toHaveBeenCalledWith(
      '/asset-custom-fields/assets/batch-values',
      [
        { asset_id: 'asset-1', values: [{ field_name: 'f1', field_value: 'v1' }] },
        { asset_id: 'asset-2', values: [{ field_name: 'f2', field_value: 'v2' }] },
      ],
      expect.any(Object)
    );
  });

  it('validateCustomFieldValue should call validate endpoint with query params', async () => {
    vi.mocked(apiClient.post).mockResolvedValue({
      success: true,
      data: { valid: true },
    });

    const result = await service.validateCustomFieldValue('field-1', 123);

    expect(result).toEqual({ valid: true });
    expect(apiClient.post).toHaveBeenCalledWith(
      '/asset-custom-fields/validate',
      {},
      expect.objectContaining({
        params: { field_id: 'field-1', value: '123' },
      })
    );
  });

  it('getFieldOptions should map backend field_types and filter by fieldType', async () => {
    vi.mocked(apiClient.get).mockResolvedValue({
      success: true,
      data: {
        field_types: [
          { value: 'text', label: '文本' },
          { value: 'number', label: '数字' },
        ],
      },
    });

    const result = await service.getFieldOptions('number');

    expect(result).toEqual([{ value: 'number', label: '数字' }]);
    expect(apiClient.get).toHaveBeenCalledWith(
      '/asset-custom-fields/types/list',
      expect.any(Object)
    );
  });
});
