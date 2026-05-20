import { apiClient } from '@/api/client';
import { API_ENDPOINTS } from '@/constants/api';
import { ApiErrorHandler } from '@/utils/responseExtractor';
import type { LedgerListParams, LedgerListResponse } from '@/types/ledger';

type LedgerExportParams = LedgerListParams & {
  export_format?: 'excel' | 'csv';
};

const buildLedgerParams = (params: LedgerExportParams): Record<string, string | number | boolean> => {
  const normalized: Record<string, string | number | boolean> = {};

  Object.entries(params).forEach(([key, value]) => {
    if (value == null || value === '') {
      return;
    }
    normalized[key] = value;
  });

  return normalized;
};

export class LedgerService {
  async getLedgerEntries(params: LedgerListParams): Promise<LedgerListResponse> {
    try {
      const result = await apiClient.get<LedgerListResponse>(API_ENDPOINTS.LEDGER.ENTRIES, {
        params: buildLedgerParams(params),
        cache: false,
        retry: { maxAttempts: 2, delay: 500, backoffMultiplier: 2 },
        smartExtract: true,
      });

      if (!result.success) {
        throw new Error(`获取财务台账失败: ${result.error}`);
      }

      return result.data!;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  async exportLedgerEntries(
    params: LedgerListParams,
    format: 'excel' | 'csv' = 'excel'
  ): Promise<Blob> {
    try {
      const result = await apiClient.get<Blob>(API_ENDPOINTS.LEDGER.EXPORT, {
        params: buildLedgerParams({ ...params, export_format: format }),
        cache: false,
        retry: false,
        responseType: 'blob',
        smartExtract: false,
      });

      if (!result.success || result.data == null) {
        throw new Error(`导出财务台账失败: ${result.error}`);
      }

      return result.data;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  triggerLedgerDownload(blob: Blob, format: 'excel' | 'csv' = 'excel'): void {
    const extension = format === 'csv' ? 'csv' : 'xlsx';
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `financial-ledger.${extension}`;
    link.style.display = 'none';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  }
}

export const ledgerService = new LedgerService();
