import { apiClient } from '@/api/client';
import { isAxiosError } from 'axios';
import { ApiErrorHandler } from '@/utils/responseExtractor';
import { convertBackendToFrontend, convertFrontendToBackend } from '@/utils/dataConversion';
import { AssetOperationsError } from '@/services/assetOperationsService';

export interface DepositRecord {
  id: string;
  deposit_entry_id: string;
  record_type: string;
  amount: number;
  occurred_on: string;
  document_id: string | null;
  offset_ledger_entry_id: string | null;
  lifecycle_event_id: string | null;
  reverses_record_id: string | null;
  reason: string | null;
  created_by: string;
  created_at: string;
}
export interface DepositDetail {
  id: string;
  contract_kind: 'upstream' | 'terminal';
  contract_id: string;
  collector: 'operator' | 'owner';
  agreed_amount: number;
  held_amount: number;
  carried_in_amount: number;
  carried_out_amount: number;
  direction: string;
  outstanding_amount: number;
  status: string;
  version: number;
  ended: boolean;
  read_only: boolean;
  records: DepositRecord[];
  offset_candidates: {
    id: string;
    contract_id: string;
    period_start: string;
    period_end: string;
    due_date: string;
    remaining_amount: number;
  }[];
}
interface DepositList {
  items: DepositDetail[];
  total: number;
  page: number;
  page_size: number;
}
export interface DepositWrite {
  record_type: string;
  amount: number;
  occurred_on: string;
  expected_version: number;
  reason?: string;
  document_id?: string;
  offset_ledger_entry_id?: string;
}
function serviceError(error: unknown): AssetOperationsError {
  if (error instanceof AssetOperationsError) return error;
  if (isAxiosError<{ error?: { code?: string; message?: string } }>(error)) {
    return new AssetOperationsError(
      error.response?.data.error?.message ?? '押金请求失败',
      error.response?.data.error?.code ??
        (error.response?.status === 403 ? 'FORBIDDEN' : 'UNKNOWN_ERROR')
    );
  }
  const detail = ApiErrorHandler.handleError(error);
  return new AssetOperationsError(detail.message, detail.code);
}
async function read<T>(path: string, params?: Record<string, string>): Promise<T> {
  try {
    const result = await apiClient.get(`/api/v1${path}`, { cache: false, params });
    if (!result.success) {
      const raw = result.rawResponse?.data as { error?: { code?: string } } | undefined;
      throw new AssetOperationsError('押金读取失败', raw?.error?.code ?? 'UNKNOWN_ERROR');
    }
    if (result.data == null)
      throw new AssetOperationsError('押金响应缺少数据', 'INVALID_RESPONSE_DATA');
    return convertBackendToFrontend<T>(result.data);
  } catch (error) {
    throw serviceError(error);
  }
}
async function write(path: string, payload: unknown, key: string): Promise<void> {
  try {
    const result = await apiClient.post(`/api/v1${path}`, convertFrontendToBackend(payload), {
      retry: false,
      headers: { 'Idempotency-Key': key },
    });
    if (!result.success) {
      const raw = result.rawResponse?.data as
        | { error?: { code?: string; message?: string } }
        | undefined;
      throw new AssetOperationsError(
        raw?.error?.message ?? '押金登记失败',
        raw?.error?.code ?? 'UNKNOWN_ERROR'
      );
    }
  } catch (error) {
    throw serviceError(error);
  }
}
export const assetDepositService = {
  list: (kind: 'upstream' | 'terminal', id: string, status?: string) =>
    read<DepositList>('/deposits', {
      contract_kind: kind,
      contract_id: id,
      ...(status != null ? { status } : {}),
    }),
  detail: (id: string) => read<DepositDetail>(`/deposits/${encodeURIComponent(id)}`),
  record: (id: string, payload: DepositWrite, key: string) =>
    write(`/deposits/${encodeURIComponent(id)}/records`, payload, key),
  reverse: (id: string, payload: { reason: string; expected_version: number }, key: string) =>
    write(`/deposit-records/${encodeURIComponent(id)}/reversal`, payload, key),
};
