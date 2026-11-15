import { isAxiosError } from 'axios';
import { apiClient } from '@/api/client';
import { ApiErrorHandler } from '@/utils/responseExtractor';
import { AssetOperationsError } from '@/services/assetOperationsService';
export type SupplementKind = 'upstream' | 'terminal';
export interface ContractSupplement {
  id: string;
  contract_kind: SupplementKind;
  contract_id: string;
  agreement_number: string;
  title: string;
  signed_on: string | null;
  version: number;
  withdrawn_at: string | null;
}
export interface SupplementRegistration {
  contract_kind: SupplementKind;
  contract_id: string;
  agreement_number: string;
  title: string;
  signed_on: string | null;
}
async function request<T>(
  action: () => Promise<{ success: boolean; data?: T | null }>
): Promise<T> {
  try {
    const result = await action();
    if (!result.success || result.data == null)
      throw new AssetOperationsError('补充协议操作失败，请重新加载。', 'SUPPLEMENT_REQUEST_FAILED');
    return result.data;
  } catch (error) {
    if (error instanceof AssetOperationsError) throw error;
    const enhanced = ApiErrorHandler.handleError(error);
    const original = isAxiosError(error) ? error : enhanced.originalError;
    const code = isAxiosError<{ error?: { code?: string } }>(original)
      ? original.response?.data?.error?.code
      : undefined;
    throw new AssetOperationsError('补充协议操作失败，请重试。', code ?? enhanced.code);
  }
}
export const contractSupplementService = {
  async list(kind: SupplementKind, contractId: string): Promise<ContractSupplement[]> {
    const result = await request(() =>
      apiClient.get<{ items: ContractSupplement[] }>('/api/v1/contract-supplements', {
        params: { contract_kind: kind, contract_id: contractId },
        cache: false,
      })
    );
    return result.items;
  },
  register: (data: SupplementRegistration) =>
    request(() =>
      apiClient.post<ContractSupplement>('/api/v1/contract-supplements', data, { retry: false })
    ),
  withdraw: (id: string, version: number, reason: string) =>
    request(() =>
      apiClient.post<ContractSupplement>(
        '/api/v1/contract-supplements/' + encodeURIComponent(id) + '/withdrawal',
        { expected_version: version, reason },
        { retry: false }
      )
    ),
};
