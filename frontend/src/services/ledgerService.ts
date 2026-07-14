import { apiClient } from '@/api/client';
import { API_ENDPOINTS } from '@/constants/api';
import { ApiErrorHandler } from '@/utils/responseExtractor';
import type {
  LedgerEntry,
  LedgerFollowUpUpdatePayload,
  LedgerListParams,
  LedgerListResponse,
  LedgerRecalculateResult,
  OperationalPaymentFlow,
  OperationalPaymentFlowCreate,
  OperationalPaymentFlowDetail,
  PaymentAllocation,
  PaymentAllocationCreate,
  PaymentFlowCorrectionPayload,
  PaymentFlowVoidPayload,
  PaymentFlowTargetQuery,
  PaymentVoucherAttachment,
  PaymentVoucherDownloadAudit,
  ServiceFeeGeneratePayload,
  ServiceFeeGenerateResult,
  ServiceFeeLedger,
  ServiceFeeLedgerQuery,
  ServiceFeeSourceReconcilePayload,
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

  async listPaymentFlows(params: PaymentFlowTargetQuery): Promise<OperationalPaymentFlowDetail[]> {
    try {
      const result = await apiClient.get<OperationalPaymentFlowDetail[]>(
        API_ENDPOINTS.LEDGER.PAYMENT_FLOWS,
        {
          params,
          cache: false,
          retry: { maxAttempts: 2, delay: 500, backoffMultiplier: 2 },
          smartExtract: true,
        }
      );

      if (!result.success || result.data == null) {
        throw new Error(`查询经营收付流水失败: ${result.error}`);
      }

      return result.data;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  async voidPaymentFlow(
    flowId: string,
    payload: PaymentFlowVoidPayload
  ): Promise<OperationalPaymentFlow> {
    try {
      const result = await apiClient.post<OperationalPaymentFlow>(
        API_ENDPOINTS.LEDGER.PAYMENT_FLOW_VOID(flowId),
        payload,
        { retry: false, smartExtract: true }
      );

      if (!result.success || result.data == null) {
        throw new Error(`作废经营收付流水失败: ${result.error}`);
      }

      return result.data;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  async correctPaymentFlow(
    flowId: string,
    payload: PaymentFlowCorrectionPayload
  ): Promise<OperationalPaymentFlow> {
    try {
      const result = await apiClient.post<OperationalPaymentFlow>(
        API_ENDPOINTS.LEDGER.PAYMENT_FLOW_CORRECT(flowId),
        payload,
        { retry: false, smartExtract: true }
      );

      if (!result.success || result.data == null) {
        throw new Error(`更正经营收付流水失败: ${result.error}`);
      }

      return result.data;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  async downloadPaymentFlowVoucher(flowId: string, attachmentId: string): Promise<Blob> {
    try {
      const result = await apiClient.get<Blob>(
        API_ENDPOINTS.LEDGER.PAYMENT_FLOW_VOUCHER_DOWNLOAD(flowId, attachmentId),
        {
          cache: false,
          retry: false,
          responseType: 'blob',
          smartExtract: false,
        }
      );

      if (!result.success || result.data == null) {
        throw new Error(`下载收付流水凭证失败: ${result.error}`);
      }

      return result.data;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  async uploadPaymentFlowVoucher(flowId: string, file: File): Promise<PaymentVoucherAttachment> {
    try {
      const formData = new FormData();
      formData.append('file', file);
      const result = await apiClient.post<PaymentVoucherAttachment>(
        API_ENDPOINTS.LEDGER.PAYMENT_FLOW_VOUCHERS(flowId),
        formData,
        {
          headers: { 'Content-Type': 'multipart/form-data' },
          retry: false,
          smartExtract: true,
        }
      );

      if (!result.success || result.data == null) {
        throw new Error(`上传收付流水凭证失败: ${result.error}`);
      }

      return result.data;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  async listPaymentFlowVoucherDownloadAudits(
    flowId: string
  ): Promise<PaymentVoucherDownloadAudit[]> {
    try {
      const result = await apiClient.get<PaymentVoucherDownloadAudit[]>(
        API_ENDPOINTS.LEDGER.PAYMENT_FLOW_VOUCHER_DOWNLOAD_AUDITS(flowId),
        {
          cache: false,
          retry: { maxAttempts: 2, delay: 500, backoffMultiplier: 2 },
          smartExtract: true,
        }
      );

      if (!result.success || result.data == null) {
        throw new Error(`查询收付流水凭证下载审计失败: ${result.error}`);
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

  async listServiceFees(params: ServiceFeeLedgerQuery): Promise<ServiceFeeLedger[]> {
    try {
      const result = await apiClient.get<ServiceFeeLedger[]>(API_ENDPOINTS.LEDGER.SERVICE_FEES, {
        params,
        cache: false,
        retry: { maxAttempts: 2, delay: 500, backoffMultiplier: 2 },
        smartExtract: true,
      });

      if (!result.success || result.data == null) {
        throw new Error(`查询服务费台账失败: ${result.error}`);
      }

      return result.data;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  async reconcileServiceFeeSource(
    entryId: string,
    payload: ServiceFeeSourceReconcilePayload
  ): Promise<ServiceFeeLedger> {
    try {
      const result = await apiClient.post<ServiceFeeLedger>(
        API_ENDPOINTS.LEDGER.SERVICE_FEE_RECONCILE(entryId),
        payload,
        {
          retry: false,
          smartExtract: true,
        }
      );

      if (!result.success || result.data == null) {
        throw new Error(`校准服务费台账来源失败: ${result.error}`);
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

  triggerPaymentFlowVoucherDownload(blob: Blob, fileName: string): void {
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = fileName;
    link.style.display = 'none';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  }
}

export const ledgerService = new LedgerService();
