import { apiClient } from '@/api/client';
import { convertBackendToFrontend, convertFrontendToBackend } from '@/utils/dataConversion';
import { AssetOperationsError } from '@/services/assetOperationsService';

export type ContractKind = 'upstream' | 'terminal';
export type LedgerType = 'upstream_rent' | 'terminal_rent';
export interface RentScheduleInput {
  stage_start: string;
  stage_end: string;
  base_monthly_rent: number | string;
  actual_monthly_rent: number | string;
  increase_rate?: number | string;
  free_rent_months?: number | string;
  discount_amount?: number | string;
  payment_cycle: 'monthly' | 'quarterly' | 'yearly' | 'custom';
  due_day: number;
}
export interface RentRecord {
  id: string;
  ledger_entry_id: string;
  record_type: string;
  amount: number;
  occurred_on: string;
  reason: string | null;
  reverses_record_id: string | null;
  document_id: string | null;
  created_by: string;
  created_at: string;
}
export interface RentEntry {
  id: string;
  entry_type: 'upstream_payable' | 'terminal_receivable' | 'owner_receipt_expected';
  contract_kind: ContractKind;
  contract_id: string;
  period: string;
  period_start: string;
  period_end: string;
  due_date: string;
  due_amount: number;
  currency: string;
  origin: 'generated' | 'manual' | 'clawback';
  basis_note: string | null;
  locked_source: Record<string, unknown>;
  voided_at: string | null;
  version: number;
  effective_paid_amount: number;
  remaining_amount: number;
  status: 'upcoming' | 'unpaid' | 'partial' | 'overdue' | 'paid' | 'void';
  warnings: string[];
  records: RentRecord[];
}
export interface LedgerMonth {
  month: number;
  entries: RentEntry[];
  due_amount: number;
  paid_amount: number;
  remaining_amount: number;
  label: string;
}
export interface LedgerRow {
  contract_kind: ContractKind;
  contract_id: string;
  contract_number: string;
  contract_name: string;
  months: LedgerMonth[];
  total_due_amount: number;
  total_paid_amount: number;
  total_remaining_amount: number;
}
export interface LedgerMatrix {
  ledger_type: LedgerType;
  year: number;
  current_month: number;
  rows: LedgerRow[];
  total_due_amount: number;
  total_paid_amount: number;
  total_remaining_amount: number;
}
export interface RentSummary {
  current_period: string;
  due_amount_this_month: number;
  paid_amount_this_month: number;
  remaining_amount_this_month: number;
  total_remaining_amount: number;
  paid_period_count: number;
  period_count: number;
  next_due_date: string | null;
  warnings: string[];
  entries: RentEntry[];
}
export interface RentImpact {
  created_count: number;
  updated_count: number;
  voided_count: number;
  restored_count: number;
  mismatched_entry_ids: string[];
  warnings: string[];
}
export interface CorrectionPreview {
  contract_id: string;
  contract_version: number;
  rent_schedules: RentScheduleInput[];
  impact: RentImpact;
  preview_token: string;
  expires_at: string;
}
interface EntryResult {
  entry_id: string;
  version: number;
  idempotent: boolean;
}
interface RecordResult {
  id: string;
  ledger_entry_id: string;
  version: number;
  idempotent: boolean;
}
interface Envelope {
  success: boolean;
  data?: unknown;
  error?: unknown;
  rawResponse?: { data?: { error?: { code?: unknown } } };
}

function unwrap<T>(result: Envelope): T {
  if (!result.success) {
    const code = result.rawResponse?.data?.error?.code;
    throw new AssetOperationsError(
      typeof result.error === 'string' ? result.error : '台账操作失败，请重试',
      typeof code === 'string' ? code : 'UNKNOWN_ERROR'
    );
  }
  if (result.data == null)
    throw new AssetOperationsError('台账响应缺少数据，请重试', 'INVALID_RESPONSE_DATA');
  return convertBackendToFrontend<T>(result.data);
}
async function get<T>(path: string, params?: Record<string, string | number>): Promise<T> {
  return unwrap<T>(await apiClient.get(`/api/v1${path}`, { cache: false, params }));
}
async function post<T>(path: string, payload: unknown, key?: string): Promise<T> {
  return unwrap<T>(
    await apiClient.post(`/api/v1${path}`, convertFrontendToBackend(payload), {
      retry: false,
      ...(key != null ? { headers: { 'Idempotency-Key': key } } : {}),
    })
  );
}
export function businessToday(): string {
  return new Intl.DateTimeFormat('en-CA', {
    timeZone: 'Asia/Shanghai',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).format(new Date());
}
export function commandKey(): string {
  return crypto.randomUUID();
}
export function isLedgerForbidden(error: unknown): boolean {
  return (
    error instanceof AssetOperationsError &&
    (error.code.startsWith('PARTY_SCOPE_') ||
      error.code === 'ASSET_OPS_PERMISSION_DENIED' ||
      error.code === 'FORBIDDEN')
  );
}
export const assetLedgerService = {
  getMatrix: (ledgerType: LedgerType, year: number) =>
    get<LedgerMatrix>('/rent-ledgers', { ledger_type: ledgerType, year }),
  getEntry: (id: string) => get<RentEntry>(`/rent-ledger-entries/${encodeURIComponent(id)}`),
  record: (
    id: string,
    payload: {
      record_type: 'payment' | 'receipt' | 'owner_reported_receipt';
      amount: number | string;
      occurred_on: string;
      document_id?: string;
      expected_version: number;
    },
    key: string
  ) => post<RecordResult>(`/rent-ledger-entries/${encodeURIComponent(id)}/records`, payload, key),
  reverse: (id: string, payload: { reason: string; expected_version: number }, key: string) =>
    post<RecordResult>(`/rent-payment-records/${encodeURIComponent(id)}/reversal`, payload, key),
  createManual: (
    payload: {
      contract_kind: ContractKind;
      contract_id: string;
      origin: 'manual' | 'clawback';
      period_start?: string;
      period_end?: string;
      due_date?: string;
      amount: number | string;
      basis_note: string;
    },
    key: string
  ) => post<EntryResult>('/rent-ledger-entries', payload, key),
  voidEntry: (id: string, payload: { reason: string; expected_version: number }, key: string) =>
    post<EntryResult>(`/rent-ledger-entries/${encodeURIComponent(id)}/void`, payload, key),
  previewCorrection: (
    kind: ContractKind,
    id: string,
    payload: { rent_schedules: RentScheduleInput[]; reason: string }
  ) =>
    post<CorrectionPreview>(
      `/${kind === 'upstream' ? 'upstream' : 'terminal'}-contracts/${encodeURIComponent(id)}/rent-schedule-correction/preview`,
      payload
    ),
  commitCorrection: (
    kind: ContractKind,
    id: string,
    payload: { preview_token: string; expected_version: number },
    key: string
  ) =>
    post<{ contract_id: string; version: number; impact: RentImpact; idempotent: boolean }>(
      `/${kind === 'upstream' ? 'upstream' : 'terminal'}-contracts/${encodeURIComponent(id)}/rent-schedule-correction`,
      payload,
      key
    ),
};
