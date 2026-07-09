import { apiClient } from '@/api/client';
import { API_ENDPOINTS } from '@/constants/api';
import { ApiErrorHandler } from '@/utils/responseExtractor';
import type {
  LedgerBatchUpdatePayload,
  LedgerEntry,
  LedgerFollowUpUpdatePayload,
  LedgerListParams,
  LedgerListResponse,
  LedgerRecalculateResult,
  OperationalPaymentFlow,
  OperationalPaymentFlowCreate,
  PaymentAllocation,
  PaymentAllocationCreate,
  ServiceFeeGeneratePayload,
  ServiceFeeGenerateResult,
} from '@/types/ledger';

type LedgerExportParams = LedgerListParams & {
  export_format?: 'excel' | 'csv';
};

const buildLedgerParams = (
  params: LedgerExportParams
): Record<string, string | number | boolean> => {
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
        throw new Error(`获取经营台账失败: ${result.error}`);
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
        throw new Error(`导出经营台账失败: ${result.error}`);
      }

      return result.data;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  async updateContractLedgerStatus(
    contractId: string,
    payload: LedgerBatchUpdatePayload
  ): Promise<LedgerEntry[]> {
    try {
      const result = await apiClient.patch<LedgerEntry[]>(
        API_ENDPOINTS.LEDGER.CONTRACT_BATCH_UPDATE_STATUS(contractId),
        payload,
        {
          retry: false,
        }
      );

      if (!result.success) {
        throw new Error(`登记台账实收失败: ${result.error}`);
      }

      return result.data!;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  async createPaymentFlow(payload: OperationalPaymentFlowCreate): Promise<OperationalPaymentFlow> {
    try {
      const result = await apiClient.post<OperationalPaymentFlow>(
        API_ENDPOINTS.LEDGER.PAYMENT_FLOWS,
        payload,
        {
          retry: false,
          smartExtract: true,
        }
      );

      if (!result.success || result.data == null) {
        throw new Error(`创建经营收付流水失败: ${result.error}`);
      }

      return result.data;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  async savePaymentFlowAllocations(
    flowId: string,
    allocations: PaymentAllocationCreate[]
  ): Promise<PaymentAllocation[]> {
    try {
      const result = await apiClient.post<PaymentAllocation[]>(
        API_ENDPOINTS.LEDGER.PAYMENT_FLOW_ALLOCATIONS(flowId),
        { allocations },
        {
          retry: false,
          smartExtract: true,
        }
      );

      if (!result.success || result.data == null) {
        throw new Error(`保存经营收付流水分摊失败: ${result.error}`);
      }

      return result.data;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  async generateServiceFees(payload: ServiceFeeGeneratePayload): Promise<ServiceFeeGenerateResult> {
    try {
      const result = await apiClient.post<ServiceFeeGenerateResult>(
        API_ENDPOINTS.LEDGER.SERVICE_FEES_GENERATE,
        payload,
        {
          retry: false,
          smartExtract: true,
        }
      );

      if (!result.success || result.data == null) {
        throw new Error(`生成服务费台账失败: ${result.error}`);
      }

      return result.data;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  async updateLedgerEntryFollowUp(
    entryId: string,
    payload: LedgerFollowUpUpdatePayload
  ): Promise<LedgerEntry> {
    try {
      const result = await apiClient.patch<LedgerEntry>(
        API_ENDPOINTS.LEDGER.ENTRY_FOLLOW_UP(entryId),
        payload,
        {
          retry: false,
          smartExtract: true,
        }
      );

      if (!result.success || result.data == null) {
        throw new Error(`维护台账跟进状态失败: ${result.error}`);
      }

      return result.data;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  async recalculateContractLedger(contractId: string): Promise<LedgerRecalculateResult> {
    try {
      const result = await apiClient.post<LedgerRecalculateResult>(
        API_ENDPOINTS.LEDGER.CONTRACT_RECALCULATE(contractId),
        {},
        {
          retry: false,
          smartExtract: true,
        }
      );

      if (!result.success || result.data == null) {
        throw new Error(`重算合同台账失败: ${result.error}`);
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
    link.download = `operations-ledger.${extension}`;
    link.style.display = 'none';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  }
}

export const ledgerService = new LedgerService();
