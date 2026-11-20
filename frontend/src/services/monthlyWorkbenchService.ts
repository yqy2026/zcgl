/**
 * Monthly Workbench Service
 * 资产运营 v5「本月」工作台：四张截止日任务卡 + 随时处理区的无状态聚合读。
 *
 * 后端按当前事实逐次派生（不落任务表），往月未清项天然带逾期天数。
 * 字段解析沿用 occupancyReportService 的严格策略：坏数据抛错，不静默补 0。
 */

import { isAxiosError } from 'axios';
import { apiClient } from '@/api/client';
import { ApiErrorHandler } from '@/utils/responseExtractor';
import { convertBackendToFrontend } from '@/utils/dataConversion';
import { AssetOperationsError } from '@/services/assetOperationsService';

export { AssetOperationsError };

interface RawErrorPayload {
  code?: unknown;
  message?: unknown;
}

interface Envelope {
  success: boolean;
  data?: unknown;
  error?: unknown;
  rawResponse?: { data?: { error?: RawErrorPayload } };
}

function toServiceError(error: unknown): AssetOperationsError {
  if (error instanceof AssetOperationsError) {
    return error;
  }
  const enhanced = ApiErrorHandler.handleError(error);
  const originalError = isAxiosError(error) ? error : enhanced.originalError;
  if (isAxiosError<{ error?: RawErrorPayload }>(originalError)) {
    const payload = originalError.response?.data?.error;
    const code =
      typeof payload?.code === 'string' && payload.code !== ''
        ? payload.code
        : originalError.response?.status === 403
          ? 'FORBIDDEN'
          : enhanced.code;
    const message =
      typeof payload?.message === 'string' && payload.message !== ''
        ? payload.message
        : enhanced.message;
    return new AssetOperationsError(message, code);
  }
  return new AssetOperationsError(enhanced.message, enhanced.code);
}

type RawRecord = Record<string, unknown>;

const API_BASE = '/api/v1';

// 后端 Decimal 字段经 JSON 序列化为字符串（如 "0"），数字与数字串都接受；
// 缺失/null → null，坏数据抛错不静默补 0（与 occupancyReportService 同策略）。
function num(record: RawRecord, field: string): number {
  const value = record[field];
  if (typeof value === 'number') {
    if (!Number.isFinite(value)) {
      throw new Error(`Invalid number field: ${field}`);
    }
    return value;
  }
  if (typeof value === 'string' && value.trim() !== '') {
    const parsed = Number(value);
    if (Number.isFinite(parsed)) {
      return parsed;
    }
  }
  throw new Error(`Invalid number field: ${field}`);
}

function nullableNum(record: RawRecord, field: string): number | null {
  if (!(field in record) || record[field] === null) {
    return null;
  }
  return num(record, field);
}

function str(record: RawRecord, field: string): string {
  const value = record[field];
  return value == null ? '' : String(value);
}

function nullableStr(record: RawRecord, field: string): string | null {
  const value = record[field];
  return value == null ? null : String(value);
}

export interface MonthlyMoneyTask {
  contractKind: 'upstream' | 'terminal';
  contractId: string;
  contractNumber: string;
  contractName: string;
  counterpartyName: string;
  unitLabel: string | null;
  period: string;
  ledgerEntryId: string;
  dueAmount: number;
  paidAmount: number;
  remainingAmount: number;
  dueDate: string;
  daysOverdue: number;
  status: 'overdue' | 'partial' | 'unpaid' | 'upcoming';
  recordTypeHint: 'payment' | 'receipt';
}

export interface MonthlyMoneyCard {
  period: string;
  subtitle: string;
  pendingCount: number;
  pendingAmount: number;
  doneCount: number;
  doneAmount: number;
  items: MonthlyMoneyTask[];
}

export interface MonthlyManagementFeeItem {
  ownerPartyId: string;
  ownerPartyName: string;
  statementId: string | null;
  statementNumber: string | null;
  status: 'collecting' | 'pending_stamp' | 'confirmed' | 'missing';
  baseAmount: number | null;
  feeAmount: number | null;
  receivedLineCount: number;
  lineCount: number;
}

export interface MonthlyManagementFeeCard {
  period: string;
  items: MonthlyManagementFeeItem[];
}

export interface MonthlyOccupancyReportCard {
  operatorPartyId: string;
  period: string;
  status: 'draft' | 'submitted' | 'missing_scope';
  unavailableReason: string | null;
  unitCount: number | null;
  rentedUnitCount: number | null;
  occupancyRate: number | null;
  rateDelta: number | null;
  gateReasons: string[];
  canSubmit: boolean;
}

export interface MonthlyExpiredUpstreamItem {
  contractId: string;
  contractNumber: string;
  name: string;
  contractType: 'lease' | 'management_agreement';
  endDate: string;
  daysPast: number;
  unitCount: number;
  activeTerminalCount: number;
  hasPendingRenewal: boolean;
}

export interface MonthlyExpiringUpstreamItem {
  contractId: string;
  contractNumber: string;
  name: string;
  contractType: 'lease' | 'management_agreement';
  ownerPartyName: string;
  endDate: string;
  daysLeft: number;
  overrunTerminalCount: number;
}

export interface MonthlyArchiveGapItem {
  documentType: string;
  label: string;
  missing: number;
}

export interface MonthlyDepositItem {
  depositId: string;
  contractKind: 'upstream' | 'terminal';
  contractId: string;
  contractNumber: string;
  counterpartyName: string;
  collector: 'operator' | 'owner';
  status: string;
  direction: string;
  agreedAmount: number;
  heldAmount: number;
  outstandingAmount: number;
}

export interface MonthlyPendingScopeUnit {
  assetUnitId: string;
  unitCode: string;
  unitName: string;
  reason: 'new_takeover' | 'boundary_uncertain';
}

export interface MonthlyWorkbenchView {
  month: string;
  today: string;
  daysLeftInMonth: number;
  progress: { total: number; done: number };
  rentPayments: MonthlyMoneyCard;
  rentCollections: MonthlyMoneyCard;
  managementFees: MonthlyManagementFeeCard;
  occupancyReport: MonthlyOccupancyReportCard;
  expiredUpstream: MonthlyExpiredUpstreamItem[];
  expiringUpstream: MonthlyExpiringUpstreamItem[];
  archiveGaps: MonthlyArchiveGapItem[];
  unlinkedUnitCount: number;
  depositsPending: MonthlyDepositItem[];
  pendingScopeUnits: MonthlyPendingScopeUnit[];
}

function parseMoneyTask(record: RawRecord): MonthlyMoneyTask {
  return {
    contractKind: str(record, 'contract_kind') as MonthlyMoneyTask['contractKind'],
    contractId: str(record, 'contract_id'),
    contractNumber: str(record, 'contract_number'),
    contractName: str(record, 'contract_name'),
    counterpartyName: str(record, 'counterparty_name'),
    unitLabel: nullableStr(record, 'unit_label'),
    period: str(record, 'period'),
    ledgerEntryId: str(record, 'ledger_entry_id'),
    dueAmount: num(record, 'due_amount'),
    paidAmount: num(record, 'paid_amount'),
    remainingAmount: num(record, 'remaining_amount'),
    dueDate: str(record, 'due_date'),
    daysOverdue: num(record, 'days_overdue'),
    status: str(record, 'status') as MonthlyMoneyTask['status'],
    recordTypeHint: str(record, 'record_type_hint') as MonthlyMoneyTask['recordTypeHint'],
  };
}

function parseMoneyCard(record: RawRecord): MonthlyMoneyCard {
  return {
    period: str(record, 'period'),
    subtitle: str(record, 'subtitle'),
    pendingCount: num(record, 'pending_count'),
    pendingAmount: num(record, 'pending_amount'),
    doneCount: num(record, 'done_count'),
    doneAmount: num(record, 'done_amount'),
    items: ((record.items as RawRecord[] | undefined) ?? []).map(parseMoneyTask),
  };
}

function parseView(record: RawRecord): MonthlyWorkbenchView {
  return {
    month: str(record, 'month'),
    today: str(record, 'today'),
    daysLeftInMonth: num(record, 'days_left_in_month'),
    progress: {
      total: num(record.progress as RawRecord, 'total'),
      done: num(record.progress as RawRecord, 'done'),
    },
    rentPayments: parseMoneyCard(record.rent_payments as RawRecord),
    rentCollections: parseMoneyCard(record.rent_collections as RawRecord),
    managementFees: {
      period: str(record.management_fees as RawRecord, 'period'),
      items: (((record.management_fees as RawRecord).items as RawRecord[] | undefined) ?? []).map(
        item => ({
          ownerPartyId: str(item, 'owner_party_id'),
          ownerPartyName: str(item, 'owner_party_name'),
          statementId: nullableStr(item, 'statement_id'),
          statementNumber: nullableStr(item, 'statement_number'),
          status: str(item, 'status') as MonthlyManagementFeeItem['status'],
          baseAmount: nullableNum(item, 'base_amount'),
          feeAmount: nullableNum(item, 'fee_amount'),
          receivedLineCount: num(item, 'received_line_count'),
          lineCount: num(item, 'line_count'),
        })
      ),
    },
    occupancyReport: {
      operatorPartyId: str(record.occupancy_report as RawRecord, 'operator_party_id'),
      period: str(record.occupancy_report as RawRecord, 'period'),
      status: str(
        record.occupancy_report as RawRecord,
        'status'
      ) as MonthlyOccupancyReportCard['status'],
      unavailableReason: nullableStr(record.occupancy_report as RawRecord, 'unavailable_reason'),
      unitCount: nullableNum(record.occupancy_report as RawRecord, 'unit_count'),
      rentedUnitCount: nullableNum(record.occupancy_report as RawRecord, 'rented_unit_count'),
      occupancyRate: nullableNum(record.occupancy_report as RawRecord, 'occupancy_rate'),
      rateDelta: nullableNum(record.occupancy_report as RawRecord, 'rate_delta'),
      gateReasons: (
        ((record.occupancy_report as RawRecord).gate_reasons as string[] | undefined) ?? []
      ).map(item => String(item)),
      canSubmit: (record.occupancy_report as RawRecord).can_submit === true,
    },
    expiredUpstream: ((record.expired_upstream as RawRecord[] | undefined) ?? []).map(item => ({
      contractId: str(item, 'contract_id'),
      contractNumber: str(item, 'contract_number'),
      name: str(item, 'name'),
      contractType: str(item, 'contract_type') as MonthlyExpiredUpstreamItem['contractType'],
      endDate: str(item, 'end_date'),
      daysPast: num(item, 'days_past'),
      unitCount: num(item, 'unit_count'),
      activeTerminalCount: num(item, 'active_terminal_count'),
      hasPendingRenewal: item.has_pending_renewal === true,
    })),
    expiringUpstream: ((record.expiring_upstream as RawRecord[] | undefined) ?? []).map(item => ({
      contractId: str(item, 'contract_id'),
      contractNumber: str(item, 'contract_number'),
      name: str(item, 'name'),
      contractType: str(item, 'contract_type') as MonthlyExpiringUpstreamItem['contractType'],
      ownerPartyName: str(item, 'owner_party_name'),
      endDate: str(item, 'end_date'),
      daysLeft: num(item, 'days_left'),
      overrunTerminalCount: num(item, 'overrun_terminal_count'),
    })),
    archiveGaps: ((record.archive_gaps as RawRecord[] | undefined) ?? []).map(item => ({
      documentType: str(item, 'document_type'),
      label: str(item, 'label'),
      missing: num(item, 'missing'),
    })),
    unlinkedUnitCount: num(record, 'unlinked_unit_count'),
    depositsPending: ((record.deposits_pending as RawRecord[] | undefined) ?? []).map(item => ({
      depositId: str(item, 'deposit_id'),
      contractKind: str(item, 'contract_kind') as MonthlyDepositItem['contractKind'],
      contractId: str(item, 'contract_id'),
      contractNumber: str(item, 'contract_number'),
      counterpartyName: str(item, 'counterparty_name'),
      collector: str(item, 'collector') as MonthlyDepositItem['collector'],
      status: str(item, 'status'),
      direction: str(item, 'direction'),
      agreedAmount: num(item, 'agreed_amount'),
      heldAmount: num(item, 'held_amount'),
      outstandingAmount: num(item, 'outstanding_amount'),
    })),
    pendingScopeUnits: ((record.pending_scope_units as RawRecord[] | undefined) ?? []).map(
      item => ({
        assetUnitId: str(item, 'asset_unit_id'),
        unitCode: str(item, 'unit_code'),
        unitName: str(item, 'unit_name'),
        reason: str(item, 'reason') as MonthlyPendingScopeUnit['reason'],
      })
    ),
  };
}

export class MonthlyWorkbenchService {
  async overview(params: {
    operatorPartyId: string;
    month?: string;
  }): Promise<MonthlyWorkbenchView> {
    try {
      const result: Envelope = await apiClient.get(`${API_BASE}/monthly-workbench`, {
        cache: false,
        params: {
          operator_party_id: params.operatorPartyId,
          ...(params.month != null ? { month: params.month } : {}),
        },
      });
      if (!result.success || result.data == null) {
        throw new AssetOperationsError('本月工作台响应缺少数据，请重试', 'INVALID_RESPONSE_DATA');
      }
      return parseView(convertBackendToFrontend(result.data) as RawRecord);
    } catch (error) {
      throw toServiceError(error);
    }
  }
}

export const monthlyWorkbenchService = new MonthlyWorkbenchService();
