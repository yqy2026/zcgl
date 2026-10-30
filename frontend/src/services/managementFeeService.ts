import { apiClient } from '@/api/client';
import { isAxiosError } from 'axios';
import { ApiErrorHandler } from '@/utils/responseExtractor';
import { convertBackendToFrontend, convertFrontendToBackend } from '@/utils/dataConversion';
import { AssetOperationsError } from '@/services/assetOperationsService';

export interface ManagementFeeLine {
  id: string | null;
  line_kind: 'current' | 'carried';
  upstream_contract_id: string;
  terminal_contract_id: string;
  rent_ledger_entry_id: string;
  asset_unit_ids: string[];
  tenant_name_snapshot: string;
  rent_period: string;
  scheduled_rent: number;
  owner_received_amount: number;
  counted_record_ids: string[];
  received_on: string | null;
  fee_rate: number;
  fee_amount: number;
  deferred_amount: number;
  deferral_reason: string | null;
  carried_from_statement_id: string | null;
  processed: boolean;
}

export interface ManagementFeeStatement {
  id: string;
  owner_party_id: string;
  period: string;
  statement_number: string;
  version: number;
  status: 'collecting' | 'pending_stamp' | 'confirmed' | 'superseded';
  deadline: string;
  upstream_contract_ids: string[];
  base_amount: number;
  fee_amount: number;
  stamped_document_id: string | null;
  confirmed_at: string | null;
  confirmed_by: string | null;
  predecessor_statement_id: string | null;
  successor_statement_id: string | null;
  lines: ManagementFeeLine[];
  carried_waiting_hint: boolean;
  upstream_missing_entry_ids: string[];
  upstream_missing_warning: string | null;
}

export interface ManagementFeeCommandResult {
  statement_id: string;
  version: number;
  idempotent: boolean;
}

export interface ManagementFeeMatrix {
  ledger_type: 'management_fee';
  year: number;
  current_month: number;
  rows: {
    owner_party_id: string;
    owner_name: string;
    months: {
      month: number;
      statement_id: string | null;
      status: ManagementFeeStatement['status'] | 'upcoming' | 'missing';
      fee_amount: number | null;
    }[];
    total_confirmed_amount: number;
  }[];
  total_confirmed_amount: number;
}
export interface ManagementFeeReceiptInput {
  rent_ledger_entry_id: string;
  amount: number;
  occurred_on: string;
  document_id?: string | null;
  // 到账命令使用租金义务版本，其余命令使用对账单版本。
  expected_version: number;
}
export interface ManagementFeeReceiptResult {
  id: string;
  ledger_entry_id: string;
  record_type: string;
  amount: number;
  occurred_on: string;
  reverses_record_id: string | null;
  reason: string | null;
  version: number;
  idempotent: boolean;
}
export interface ManagementFeeStampResult extends ManagementFeeCommandResult {
  document_id: string;
  fee_amount: number;
}
export interface ManagementFeeSuccessorResult extends ManagementFeeCommandResult {
  successor_statement_id: string;
}

const base = '/api/v1/management-fee-statements';
const statementPath = (id: string) => `${base}/${encodeURIComponent(id)}`;

function serviceError(error: unknown): AssetOperationsError {
  if (error instanceof AssetOperationsError) return error;
  if (isAxiosError<{ error?: { code?: string; message?: string } }>(error)) {
    return new AssetOperationsError(
      error.response?.data.error?.message ?? '管理费请求失败',
      error.response?.data.error?.code ??
        (error.response?.status === 403 ? 'FORBIDDEN' : 'UNKNOWN_ERROR')
    );
  }
  const detail = ApiErrorHandler.handleError(error);
  return new AssetOperationsError(detail.message, detail.code);
}

async function response<T>(request: ReturnType<typeof apiClient.get>): Promise<T> {
  try {
    const result = await request;
    if (!result.success) {
      const raw = result.rawResponse?.data as
        | { error?: { code?: string; message?: string } }
        | undefined;
      throw new AssetOperationsError(
        raw?.error?.message ?? result.error ?? '管理费请求失败',
        raw?.error?.code ?? 'UNKNOWN_ERROR'
      );
    }
    if (result.data == null)
      throw new AssetOperationsError('管理费响应缺少数据', 'INVALID_RESPONSE_DATA');
    return convertBackendToFrontend<T>(result.data);
  } catch (error) {
    throw serviceError(error);
  }
}

function command<T>(id: string, action: string, payload: unknown, key: string): Promise<T> {
  return response<T>(
    apiClient.post(`${statementPath(id)}/${action}`, convertFrontendToBackend(payload), {
      retry: false,
      headers: { 'Idempotency-Key': key },
    })
  );
}

export const managementFeeService = {
  matrix: (year: number) =>
    response<ManagementFeeMatrix>(
      apiClient.get('/rent-ledgers', {
        cache: false,
        params: { ledger_type: 'management_fee', year },
      })
    ),
  list: (period: string) =>
    response<{ items: ManagementFeeStatement[]; total: number }>(
      apiClient.get(base, { cache: false, params: { period } })
    ),
  get: (id: string) =>
    response<ManagementFeeStatement>(apiClient.get(statementPath(id), { cache: false })),
  record: (id: string, payload: ManagementFeeReceiptInput, key: string) =>
    command<ManagementFeeReceiptResult>(id, 'owner-receipts', payload, key),
  defer: (
    id: string,
    payload: { rent_ledger_entry_id: string; reason: string; expected_version: number },
    key: string
  ) => command<ManagementFeeCommandResult>(id, 'deferrals', payload, key),
  confirm: (id: string, payload: { expected_version: number }, key: string) =>
    command<ManagementFeeCommandResult>(id, 'confirmation', payload, key),
  supersede: (id: string, payload: { expected_version: number; reason: string }, key: string) =>
    command<ManagementFeeSuccessorResult>(id, 'successor', payload, key),
  upload: (id: string, file: File, expectedVersion: number) => {
    const form = new FormData();
    form.append('file', file);
    form.append('expected_version', String(expectedVersion));
    return response<ManagementFeeStampResult>(
      apiClient.post(`${statementPath(id)}/stamped-document`, form, { retry: false })
    );
  },
};
