import { isAxiosError } from 'axios';
import { apiClient } from '@/api/client';
import { ApiErrorHandler } from '@/utils/responseExtractor';
import { AssetOperationsError } from '@/services/assetOperationsService';
export interface HandoverTarget {
  event_id: string;
  event_type: 'terminated' | 'exited';
  effective_date: string;
  handover_status: 'pending' | 'completed' | 'not_applicable' | null;
  can_write: boolean;
  unavailable_reason:
    | 'HANDOVER_EVENT_REVERSED'
    | 'HANDOVER_NOT_EFFECTIVE'
    | 'HANDOVER_NOT_REQUIRED'
    | null;
}
export const handoverArchiveService = {
  async list(kind: 'upstream' | 'terminal', contractId: string): Promise<HandoverTarget[]> {
    try {
      const result = await apiClient.get<{ items: HandoverTarget[] }>(
        '/api/v1/archive/handover-targets',
        {
          params: { contract_kind: kind, contract_id: contractId },
          cache: false,
        }
      );
      if (!result.success || result.data == null || !Array.isArray(result.data.items))
        throw new AssetOperationsError('交接事项加载失败，请重新加载。', 'HANDOVER_READ_FAILED');
      return result.data.items;
    } catch (error) {
      if (error instanceof AssetOperationsError) throw error;
      const enhanced = ApiErrorHandler.handleError(error);
      const original = isAxiosError(error) ? error : enhanced.originalError;
      const code = isAxiosError<{ error?: { code?: string } }>(original)
        ? original.response?.data?.error?.code
        : undefined;
      throw new AssetOperationsError('交接事项加载失败，请重新加载。', code ?? enhanced.code);
    }
  },
};
