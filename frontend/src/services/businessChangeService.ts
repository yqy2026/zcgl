import { isAxiosError } from 'axios';
import { apiClient } from '@/api/client';
import { ApiErrorHandler } from '@/utils/responseExtractor';
import { AssetOperationsError } from '@/services/assetOperationsService';

/** 变更记录查询目标（api-contract §5.14 支持的合同/单元轴）。 */
export type BusinessChangeTargetType =
  | 'upstream_contract'
  | 'terminal_contract'
  | 'management_fee_statement'
  | 'asset_unit'
  | 'asset_unit_boundary_change';

export interface BusinessChangeEvent {
  id: string;
  target_type: string;
  target_id: string;
  action: string;
  before: Record<string, unknown>;
  after: Record<string, unknown>;
  reason: string | null;
  actor_id: string;
  occurred_at: string;
  correlation_id: string;
  summary: string;
  related_objects: Array<Record<string, string>>;
}

export interface BusinessChangeEventList {
  items: BusinessChangeEvent[];
  total: number;
  page: number;
  page_size: number;
}

export const businessChangeService = {
  async list(
    targetType: BusinessChangeTargetType,
    targetId: string,
    page = 1
  ): Promise<BusinessChangeEventList> {
    try {
      const result = await apiClient.get<BusinessChangeEventList>(
        '/api/v1/business-change-events',
        {
          params: { target_type: targetType, target_id: targetId, page },
          cache: false,
        }
      );
      if (!result.success || result.data == null || !Array.isArray(result.data.items)) {
        throw new AssetOperationsError('变更记录加载失败，请重新加载。', 'CHANGE_EVENT_READ_FAILED');
      }
      return result.data;
    } catch (error) {
      if (error instanceof AssetOperationsError) throw error;
      const enhanced = ApiErrorHandler.handleError(error);
      const original = isAxiosError(error) ? error : enhanced.originalError;
      const code = isAxiosError<{ error?: { code?: string } }>(original)
        ? original.response?.data.error?.code
        : undefined;
      throw new AssetOperationsError('变更记录加载失败，请重新加载。', code ?? enhanced.code);
    }
  },
};
