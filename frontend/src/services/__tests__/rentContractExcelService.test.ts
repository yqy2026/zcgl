import { beforeEach, describe, expect, it, vi } from 'vitest';
import { rentContractExcelService } from '../rentContractExcelService';

vi.mock('@/api/client', () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
  },
}));

vi.mock('@/utils/logger', () => ({
  createLogger: () => ({
    info: vi.fn(),
    warn: vi.fn(),
    error: vi.fn(),
    debug: vi.fn(),
  }),
}));

import { apiClient } from '@/api/client';

describe('rentContractExcelService', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('downloads excel template from /rental-contracts path', async () => {
    const blob = new Blob(['template']);
    vi.mocked(apiClient.get).mockResolvedValue({ data: blob });

    const result = await rentContractExcelService.downloadTemplate();

    expect(result).toBe(blob);
    expect(apiClient.get).toHaveBeenCalledWith('/rental-contracts/excel/template', {
      responseType: 'blob',
    });
  });

  it('imports excel file through /rental-contracts endpoint', async () => {
    const file = new File(['excel-content'], 'contracts.xlsx', {
      type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    });
    vi.mocked(apiClient.post).mockResolvedValue({
      data: {
        success: true,
        message: 'ok',
        imported_contracts: 1,
        imported_terms: 0,
        imported_ledgers: 0,
        errors: [],
        warnings: [],
      },
    });

    const result = await rentContractExcelService.importFromFile(file, {
      import_terms: true,
      import_ledger: false,
      overwrite_existing: false,
    });

    expect(result.success).toBe(true);
    expect(apiClient.post).toHaveBeenCalledWith(
      '/rental-contracts/excel/import',
      expect.any(FormData),
      expect.objectContaining({
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      })
    );
  });

  it('exports excel file through /rental-contracts endpoint', async () => {
    const blob = new Blob(['export']);
    vi.mocked(apiClient.get).mockResolvedValue({ data: blob });

    const result = await rentContractExcelService.exportToFile({
      contract_ids: ['c-1', 'c-2'],
      include_terms: true,
      include_ledger: false,
      start_date: '2026-01-01',
      end_date: '2026-02-01',
    });

    expect(result).toBe(blob);
    expect(apiClient.get).toHaveBeenCalledWith(
      '/rental-contracts/excel/export',
      expect.objectContaining({
        responseType: 'blob',
      })
    );

    const requestOptions = vi.mocked(apiClient.get).mock.calls[0]?.[1];
    expect(requestOptions?.params).toBeInstanceOf(URLSearchParams);
    const params = requestOptions?.params as URLSearchParams | undefined;
    expect(params).toBeDefined();
    expect(params?.toString()).toContain('contract_ids=c-1');
    expect(params?.toString()).toContain('contract_ids=c-2');
  });

  it('throws upgrade hint when import fails due to legacy template fields', async () => {
    const file = new File(['excel-content'], 'contracts.xlsx', {
      type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    });
    vi.mocked(apiClient.post).mockRejectedValue(new Error('第 2 行缺少字段: 权属方ID'));

    await expect(rentContractExcelService.importFromFile(file)).rejects.toThrow(
      '系统已升级，请下载最新模板后重试'
    );
  });
});
