/**
 * Asset Operations Service
 * 资产运营 v5 纵向切片：资产单元与合同链
 *
 * 后端金额/面积字段是 Decimal 字符串；本服务统一转成 number 后再交给页面。
 */

import { isAxiosError } from 'axios';
import { apiClient } from '@/api/client';
import { convertBackendToFrontend, convertFrontendToBackend } from '@/utils/dataConversion';
import { ApiErrorHandler } from '@/utils/responseExtractor';

/**
 * 带稳定 code 的服务调用错误；页面只用 code 选择恢复动作，不解析 message。
 */
export class AssetOperationsError extends Error {
  readonly code: string;

  constructor(message: string, code: string) {
    super(message);
    this.name = 'AssetOperationsError';
    this.code = code;
  }
}

function toServiceError(error: unknown): AssetOperationsError {
  const enhanced = ApiErrorHandler.handleError(error);
  const original = isAxiosError(error) ? error : enhanced.originalError;
  if (isAxiosError<{ error?: { code?: unknown } }>(original)) {
    const code = original.response?.data?.error?.code;
    if (typeof code === 'string' && code !== '') {
      return new AssetOperationsError(enhanced.message, code);
    }
  }
  return new AssetOperationsError(enhanced.message, enhanced.code);
}

type FailedResult = {
  rawResponse?: { data?: { error?: { code?: unknown } } };
};

function extractErrorCode(result: FailedResult): string {
  const code = result.rawResponse?.data?.error?.code;
  return typeof code === 'string' && code !== '' ? code : 'UNKNOWN_ERROR';
}

const API_BASE = '/api/v1';

/** Certificate areas retain the registered source text, including qualifications. */
export interface AssetUnitCertificate {
  id: string;
  certificate_number: string;
  certificate_type: string;
  property_address: string | null;
  registration_date: string | null;
  building_area: string | null;
  land_area: string | null;
  land_use_term_start: string | null;
  land_use_term_end: string | null;
}

export interface AssetUnitListItem {
  id: string;
  unitCode: string;
  name: string;
  projectId: string;
  ownerPartyId: string;
  address: string;
  usageType: string;
  acquisitionMode: string;
  isOperating: boolean;
  landArea: number;
  buildingArea: number;
  rentableArea: number;
  managedFrom: string;
  managedTo: string | null;
  vacancyReason: string | null;
  expectedLeaseStart: string | null;
  predecessorUnitIds: string[];
  version: number;
  rentalStatus: 'rented' | 'vacant' | 'non_rentable';
  rentedArea: number;
  occupancyRate: number;
  warnings: { code: string; severity: string; message: string | null }[];
  terminalContractIds: string[];
  /** 列表富化字段（WP2 物业页对齐原型） */
  ownerPartyName: string;
  projectName: string;
  assessment: 'included' | 'excluded' | 'pending' | null;
  currentTenantName: string | null;
  currentContractNumber: string | null;
  currentContractEndDate: string | null;
  certificateCount: number;
}

export interface AssetUnitFilterCounts {
  all: number;
  inAssessment: number;
  vacant: number;
  nonRentable: number;
  missingCertificate: number;
}

export interface AssetUnitListResult {
  items: AssetUnitListItem[];
  total: number;
  counts: AssetUnitFilterCounts | null;
}

export interface AssetUnitListParams {
  projectId?: string;
  ownerPartyId?: string;
  usageType?: string;
  q?: string;
  filter?: 'all' | 'in_assessment' | 'vacant' | 'non_rentable' | 'missing_certificate';
  assessmentOperatorPartyId?: string;
  assessmentYear?: number;
  offset?: number;
  limit?: number;
}

type RawUnitRecord = Record<string, unknown>;

function requireDecimal(record: RawUnitRecord, field: string): number {
  const value = record[field];
  if (typeof value !== 'number' || !Number.isFinite(value)) {
    throw new Error(`Invalid Decimal field: ${field}`);
  }
  return value;
}

function normalizeUnit(raw: RawUnitRecord): AssetUnitListItem {
  const normalized = convertBackendToFrontend<RawUnitRecord>(raw);
  return {
    id: String(normalized.id ?? ''),
    unitCode: String(normalized.unit_code ?? ''),
    name: String(normalized.name ?? ''),
    projectId: String(normalized.project_id ?? ''),
    ownerPartyId: String(normalized.owner_party_id ?? ''),
    address: String(normalized.address ?? ''),
    usageType: String(normalized.usage_type ?? ''),
    acquisitionMode: String(normalized.acquisition_mode ?? ''),
    isOperating: Boolean(normalized.is_operating),
    landArea: requireDecimal(normalized, 'land_area'),
    buildingArea: requireDecimal(normalized, 'building_area'),
    rentableArea: requireDecimal(normalized, 'rentable_area'),
    managedFrom: String(normalized.managed_from ?? ''),
    managedTo: normalized.managed_to == null ? null : String(normalized.managed_to),
    vacancyReason: normalized.vacancy_reason == null ? null : String(normalized.vacancy_reason),
    expectedLeaseStart:
      normalized.expected_lease_start == null ? null : String(normalized.expected_lease_start),
    predecessorUnitIds: Array.isArray(normalized.predecessor_unit_ids)
      ? normalized.predecessor_unit_ids.map(String)
      : [],
    version: Number(normalized.version ?? 1),
    rentalStatus:
      normalized.rental_status === 'rented'
        ? 'rented'
        : normalized.rental_status === 'non_rentable'
          ? 'non_rentable'
          : 'vacant',
    rentedArea: requireDecimal(normalized, 'rented_area'),
    occupancyRate: requireDecimal(normalized, 'occupancy_rate'),
    warnings: Array.isArray(normalized.warnings)
      ? normalized.warnings.map(item => {
          const warning = item as RawUnitRecord;
          return {
            code: String(warning.code ?? ''),
            severity: String(warning.severity ?? 'warning'),
            message: warning.message == null ? null : String(warning.message),
          };
        })
      : [],
    terminalContractIds: Array.isArray(normalized.terminal_contract_ids)
      ? normalized.terminal_contract_ids.map(String)
      : [],
    ownerPartyName: String(normalized.owner_party_name ?? ''),
    projectName: String(normalized.project_name ?? ''),
    assessment:
      normalized.assessment === 'included' ||
      normalized.assessment === 'excluded' ||
      normalized.assessment === 'pending'
        ? normalized.assessment
        : null,
    currentTenantName:
      normalized.current_tenant_name == null ? null : String(normalized.current_tenant_name),
    currentContractNumber:
      normalized.current_contract_number == null
        ? null
        : String(normalized.current_contract_number),
    currentContractEndDate:
      normalized.current_contract_end_date == null
        ? null
        : String(normalized.current_contract_end_date),
    certificateCount: Number(normalized.certificate_count ?? 0),
  };
}

export interface UpstreamContractListItem {
  rentSummary: import('@/services/assetLedgerService').RentSummary | null;
  rentSchedules: import('@/services/assetLedgerService').RentScheduleInput[];
  id: string;
  contractNumber: string;
  contractType: 'lease' | 'management_agreement';
  name: string;
  ownerPartyId: string;
  operatorPartyId: string;
  startDate: string;
  endDate: string;
  readonly paymentCycle: string | null;
  readonly paymentDay: number | null;
  depositAmount: number;
  renewedFromId: string | null;
  version: number;
  status: 'scheduled' | 'active' | 'expiring' | 'expired_pending_action' | 'exited' | 'historical';
  warnings: { code: string; severity: string; message: string | null }[];
  terminalContractIds: string[];
  /** 详情富化（WP4）：到期剩余天数、付款计划、单元×终端矩阵 */
  daysToExpiry: number | null;
  paymentPlan: {
    stageStart: string;
    stageEnd: string;
    monthlyRent: number;
    periodCount: number;
    paidCount: number;
    nextDueDate: string | null;
    totalAmount: number;
    note: string;
  }[];
  unitsMatrix: {
    assetUnitId: string;
    unitCode: string;
    unitName: string;
    rentableArea: number;
    tenantPartyName: string | null;
    terminalContractNumber: string | null;
    terminalEndDate: string | null;
    monthlyRent: number | null;
    hasScan: boolean | null;
  }[];
  coverages: {
    assetUnitId: string;
    effectiveFrom: string;
    effectiveTo: string | null;
  }[];
  lifecycleEvents: {
    id: string;
    eventType: string;
    effectiveDate: string;
    reason: string | null;
  }[];
  renewalChain: { contractId: string; contractNumber: string; relation: string }[];
}

export interface TerminalContractListItem {
  rentSummary: import('@/services/assetLedgerService').RentSummary | null;
  rentSchedules: import('@/services/assetLedgerService').RentScheduleInput[];
  id: string;
  contractNumber: string;
  contractMode: 'sublease' | 'direct_lease';
  tenantPartyId: string;
  lessorPartyId: string;
  upstreamContractId: string | null;
  startDate: string;
  endDate: string;
  depositAmount: number;
  rentCollector: string;
  version: number;
  status: 'scheduled' | 'active' | 'expiring' | 'ended' | 'historical';
  warnings: { code: string; severity: string; message: string | null }[];
  coverages: {
    assetUnitId: string;
    effectiveFrom: string;
    effectiveTo: string | null;
  }[];
  lifecycleEvents: {
    id: string;
    eventType: string;
    effectiveDate: string;
    reason: string | null;
  }[];
  renewalChain: { contractId: string; contractNumber: string; relation: string }[];
  /** 列表富化字段（WP3 终端合同页对齐原型） */
  tenantPartyName: string;
  upstreamContractNumber: string | null;
  unitLabels: string[];
  currentMonthlyRent: number | null;
  currentMonthCollectionStatus: 'paid' | 'partial' | 'unpaid' | 'none' | null;
  currentMonthRemaining: number | null;
  hasScan: boolean;
}

export interface TerminalContractFilterCounts {
  active: number;
  expiring180: number;
  rentUnpaid: number;
  depositUnsettled: number;
  missingScan: number;
  ended: number;
}

export interface ContractListResult<T> {
  items: T[];
  total: number;
  counts?: unknown;
}

export interface TerminalContractListResult extends ContractListResult<TerminalContractListItem> {
  counts: TerminalContractFilterCounts | null;
}

function normalizeSession(raw: RawUnitRecord): ContractIntakeSession {
  const allowedStatus = [
    'uploaded',
    'extracting',
    'ready_for_review',
    'confirming',
    'confirmed',
    'cancelling',
    'cancelled',
    'failed',
  ] as const;
  const statusValue = String(raw.status ?? 'uploaded');
  return {
    id: String(raw.id ?? ''),
    documentId: String(raw.document_id ?? ''),
    contractType: ((): ContractIntakeType => {
      const value = String(raw.contract_type ?? 'terminal');
      return (['upstream_lease', 'management_agreement', 'terminal'] as const).includes(
        value as ContractIntakeType
      )
        ? (value as ContractIntakeType)
        : 'terminal';
    })(),
    status: (allowedStatus as readonly string[]).includes(statusValue)
      ? (statusValue as ContractIntakeSession['status'])
      : 'uploaded',
    candidateFields:
      raw.candidate_fields != null && typeof raw.candidate_fields === 'object'
        ? (raw.candidate_fields as Record<string, unknown>)
        : {},
    warnings: normalizeWarnings(raw.warnings),
    expiresAt: String(raw.expires_at ?? ''),
  };
}

function normalizeWarnings(raw: unknown): {
  code: string;
  severity: string;
  message: string | null;
}[] {
  if (!Array.isArray(raw)) {
    return [];
  }
  return raw.map(item => {
    const warning = item as RawUnitRecord;
    return {
      code: String(warning.code ?? ''),
      severity: String(warning.severity ?? 'warning'),
      message: warning.message == null ? null : String(warning.message),
    };
  });
}

function normalizeCoverages(raw: unknown): {
  assetUnitId: string;
  effectiveFrom: string;
  effectiveTo: string | null;
}[] {
  if (!Array.isArray(raw)) {
    return [];
  }
  return raw.map(item => {
    const coverage = item as RawUnitRecord;
    return {
      assetUnitId: String(coverage.asset_unit_id ?? ''),
      effectiveFrom: String(coverage.effective_from ?? ''),
      effectiveTo: coverage.effective_to == null ? null : String(coverage.effective_to),
    };
  });
}

function normalizeEvents(raw: unknown): {
  id: string;
  eventType: string;
  effectiveDate: string;
  reason: string | null;
}[] {
  if (!Array.isArray(raw)) {
    return [];
  }
  return raw.map(item => {
    const event = item as RawUnitRecord;
    return {
      id: String(event.id ?? ''),
      eventType: String(event.event_type ?? ''),
      effectiveDate: String(event.effective_date ?? ''),
      reason: event.reason == null ? null : String(event.reason),
    };
  });
}

function normalizeChain(raw: unknown): {
  contractId: string;
  contractNumber: string;
  relation: string;
}[] {
  if (!Array.isArray(raw)) {
    return [];
  }
  return raw.map(item => {
    const node = item as RawUnitRecord;
    return {
      contractId: String(node.contract_id ?? ''),
      contractNumber: String(node.contract_number ?? ''),
      relation: String(node.relation ?? ''),
    };
  });
}

function normalizeUpstream(raw: RawUnitRecord): UpstreamContractListItem {
  const normalized = convertBackendToFrontend<RawUnitRecord>(raw);
  const allowedUpstreamStatus = [
    'scheduled',
    'active',
    'expiring',
    'expired_pending_action',
    'exited',
    'historical',
  ] as const;
  const statusValue = String(raw.status ?? '');
  return {
    rentSummary: raw.rent_summary == null ? null : convertBackendToFrontend(raw.rent_summary),
    rentSchedules: convertBackendToFrontend(
      Array.isArray(raw.rent_schedules) ? raw.rent_schedules : []
    ),
    id: String(raw.id ?? ''),
    contractNumber: String(raw.contract_number ?? ''),
    contractType: raw.contract_type === 'management_agreement' ? 'management_agreement' : 'lease',
    name: String(raw.name ?? ''),
    ownerPartyId: String(raw.owner_party_id ?? ''),
    operatorPartyId: String(raw.operator_party_id ?? ''),
    startDate: String(raw.start_date ?? ''),
    endDate: String(raw.end_date ?? ''),
    paymentCycle: raw.payment_cycle == null ? null : String(raw.payment_cycle),
    paymentDay: raw.payment_day == null ? null : Number(raw.payment_day),
    depositAmount: requireDecimal(normalized, 'deposit_amount'),
    renewedFromId: raw.renewed_from_id == null ? null : String(raw.renewed_from_id),
    version: Number(raw.version ?? 1),
    status: (allowedUpstreamStatus as readonly string[]).includes(statusValue)
      ? (statusValue as UpstreamContractListItem['status'])
      : 'active',
    warnings: normalizeWarnings(raw.warnings),
    terminalContractIds: Array.isArray(raw.terminal_contract_ids)
      ? raw.terminal_contract_ids.map(String)
      : [],
    coverages: normalizeCoverages(raw.coverages),
    lifecycleEvents: normalizeEvents(raw.lifecycle_events),
    renewalChain: normalizeChain(raw.renewal_chain),
    daysToExpiry: normalized.days_to_expiry == null ? null : Number(normalized.days_to_expiry),
    paymentPlan: Array.isArray(normalized.payment_plan)
      ? normalized.payment_plan.map((item: RawUnitRecord) => ({
          stageStart: String(item.stage_start ?? ''),
          stageEnd: String(item.stage_end ?? ''),
          monthlyRent: Number(item.monthly_rent ?? 0),
          periodCount: Number(item.period_count ?? 0),
          paidCount: Number(item.paid_count ?? 0),
          nextDueDate: item.next_due_date == null ? null : String(item.next_due_date),
          totalAmount: Number(item.total_amount ?? 0),
          note: String(item.note ?? ''),
        }))
      : [],
    unitsMatrix: Array.isArray(normalized.units_matrix)
      ? normalized.units_matrix.map((item: RawUnitRecord) => ({
          assetUnitId: String(item.asset_unit_id ?? ''),
          unitCode: String(item.unit_code ?? ''),
          unitName: String(item.unit_name ?? ''),
          rentableArea: Number(item.rentable_area ?? 0),
          tenantPartyName: item.tenant_party_name == null ? null : String(item.tenant_party_name),
          terminalContractNumber:
            item.terminal_contract_number == null ? null : String(item.terminal_contract_number),
          terminalEndDate: item.terminal_end_date == null ? null : String(item.terminal_end_date),
          monthlyRent: item.monthly_rent == null ? null : Number(item.monthly_rent),
          hasScan: item.has_scan == null ? null : item.has_scan === true,
        }))
      : [],
  };
}

function normalizeTerminal(raw: RawUnitRecord): TerminalContractListItem {
  const normalized = convertBackendToFrontend<RawUnitRecord>(raw);
  const allowedTerminalStatus = ['scheduled', 'active', 'expiring', 'ended', 'historical'] as const;
  const statusValue = String(raw.status ?? '');
  return {
    rentSummary: raw.rent_summary == null ? null : convertBackendToFrontend(raw.rent_summary),
    rentSchedules: convertBackendToFrontend(
      Array.isArray(raw.rent_schedules) ? raw.rent_schedules : []
    ),
    id: String(raw.id ?? ''),
    contractNumber: String(raw.contract_number ?? ''),
    contractMode: raw.contract_mode === 'direct_lease' ? 'direct_lease' : 'sublease',
    tenantPartyId: String(raw.tenant_party_id ?? ''),
    lessorPartyId: String(raw.lessor_party_id ?? ''),
    upstreamContractId: raw.upstream_contract_id == null ? null : String(raw.upstream_contract_id),
    startDate: String(raw.start_date ?? ''),
    endDate: String(raw.end_date ?? ''),
    depositAmount: requireDecimal(normalized, 'deposit_amount'),
    rentCollector: String(raw.rent_collector ?? ''),
    version: Number(raw.version ?? 1),
    status: (allowedTerminalStatus as readonly string[]).includes(statusValue)
      ? (statusValue as TerminalContractListItem['status'])
      : 'active',
    warnings: normalizeWarnings(raw.warnings),
    coverages: normalizeCoverages(raw.coverages),
    lifecycleEvents: normalizeEvents(raw.lifecycle_events),
    renewalChain: normalizeChain(raw.renewal_chain),
    tenantPartyName: String(normalized.tenant_party_name ?? ''),
    upstreamContractNumber:
      normalized.upstream_contract_number == null
        ? null
        : String(normalized.upstream_contract_number),
    unitLabels: Array.isArray(normalized.unit_labels) ? normalized.unit_labels.map(String) : [],
    currentMonthlyRent:
      normalized.current_monthly_rent == null ? null : Number(normalized.current_monthly_rent),
    currentMonthCollectionStatus: (['paid', 'partial', 'unpaid', 'none'] as const).includes(
      normalized.current_month_collection_status as never
    )
      ? (normalized.current_month_collection_status as TerminalContractListItem['currentMonthCollectionStatus'])
      : null,
    currentMonthRemaining:
      normalized.current_month_remaining == null
        ? null
        : Number(normalized.current_month_remaining),
    hasScan: raw.has_scan !== false,
  };
}

export type UpstreamContractDetail = UpstreamContractListItem;
export type TerminalContractDetail = TerminalContractListItem;

export type ContractIntakeType = 'upstream_lease' | 'management_agreement' | 'terminal';

export interface ContractIntakeSession {
  id: string;
  documentId: string;
  contractType: ContractIntakeType;
  status:
    | 'uploaded'
    | 'extracting'
    | 'ready_for_review'
    | 'confirming'
    | 'confirmed'
    | 'cancelling'
    | 'cancelled'
    | 'failed';
  candidateFields: Record<string, unknown>;
  warnings: { code: string; severity: string; message: string | null }[];
  expiresAt: string;
}

export interface RentSchedulePayload {
  stage_start: string;
  stage_end: string;
  base_monthly_rent: string | number;
  increase_rate?: string | number;
  free_rent_months?: string | number;
  discount_amount?: string | number;
  actual_monthly_rent: string | number;
  payment_cycle: string;
  due_day: number;
}

export interface ConfirmUpstreamPayload {
  contract_number: string;
  name: string;
  owner_party_id: string;
  operator_party_id: string;
  start_date: string;
  end_date: string;
  payment_cycle?: string;
  payment_day?: number;
  management_fee_rate?: string | number;
  deposit_amount?: string | number;
  oa_reference?: string;
  asset_unit_ids: string[];
  rent_schedules: RentSchedulePayload[];
}

export interface ConfirmTerminalPayload {
  contract_number: string;
  tenant_party_id: string;
  lessor_party_id: string;
  upstream_contract_id?: string;
  start_date: string;
  end_date: string;
  deposit_months?: string | number;
  deposit_amount?: string | number;
  asset_unit_ids: string[];
  rent_schedules: RentSchedulePayload[];
}

export interface CreatedContractResult {
  id: string;
  contractNumber: string;
  idempotent: boolean;
}

export interface TerminationCoverageImpact {
  assetUnitId: string;
  effectiveFrom: string;
  currentEffectiveTo: string | null;
  newEffectiveTo: string;
}

export interface TerminationPreview {
  depositSettlement?: DepositSettlementPreview;
  rentImpact?: import('@/services/assetLedgerService').RentImpact;
  contractId: string;
  contractVersion: number;
  effectiveDate: string;
  lastValidDay: string;
  coverageImpact: TerminationCoverageImpact[];
  warnings: string[];
  previewToken: string;
  expiresAt: string;
}

export interface DepositSettlementPreview {
  entry_id: string;
  version: number;
  held_amount: number;
  offsets: { ledger_entry_id: string; amount: number }[];
  candidates: {
    ledger_entry_id: string;
    remaining: number;
    period_start: string;
    period_end: string;
    contract_id: string;
  }[];
  clawback_amount: number;
  clawback_basis: string;
  refundable_amount: number;
  additional_due_amount: number;
  recoverable_amount: number;
}

export interface LifecycleEventRecord {
  id: string;
  contractKind: string;
  contractId: string;
  eventType: string;
  effectiveDate: string;
  reason: string | null;
  idempotent?: boolean;
}

export interface ExitPreview {
  depositSettlement?: { applicable?: boolean; recoverable_amount?: number };
  rentImpact?: import('@/services/assetLedgerService').RentImpact;
  contractId: string;
  contractVersion: number;
  depositAmount: number;
  effectiveDate: string;
  lastValidDay: string;
  coverageImpact: TerminationCoverageImpact[];
  previewToken: string;
  expiresAt: string;
}

export interface RenewalResult {
  id: string;
  contractNumber: string;
  idempotent: boolean;
}

export class AssetOperationsService {
  async listAssetUnits(params: AssetUnitListParams = {}): Promise<AssetUnitListResult> {
    try {
      const result = await apiClient.get<{
        items: RawUnitRecord[];
        total: number;
        counts?: RawUnitRecord | null;
      }>(`${API_BASE}/asset-units`, {
        params: {
          ...(params.projectId != null ? { project_id: params.projectId } : {}),
          ...(params.ownerPartyId != null ? { owner_party_id: params.ownerPartyId } : {}),
          ...(params.usageType != null ? { usage_type: params.usageType } : {}),
          ...(params.q != null && params.q.trim() !== '' ? { q: params.q } : {}),
          ...(params.filter != null ? { filter: params.filter } : {}),
          ...(params.assessmentOperatorPartyId != null
            ? { assessment_operator_party_id: params.assessmentOperatorPartyId }
            : {}),
          ...(params.assessmentYear != null ? { assessment_year: params.assessmentYear } : {}),
          offset: params.offset ?? 0,
          limit: params.limit ?? 50,
        },
        cache: false,
      });
      if (!result.success) {
        throw new AssetOperationsError(
          `获取资产单元列表失败: ${result.error}`,
          extractErrorCode(result)
        );
      }
      const payload = result.data ?? { items: [], total: 0 };
      const countsRaw = payload.counts ?? null;
      return {
        items: (payload.items ?? []).map(normalizeUnit),
        total: Number(payload.total ?? 0),
        counts:
          countsRaw == null
            ? null
            : {
                all: Number(countsRaw.all ?? 0),
                inAssessment: Number(countsRaw.in_assessment ?? 0),
                vacant: Number(countsRaw.vacant ?? 0),
                nonRentable: Number(countsRaw.non_rentable ?? 0),
                missingCertificate: Number(countsRaw.missing_certificate ?? 0),
              },
      };
    } catch (error) {
      if (error instanceof AssetOperationsError) {
        throw error;
      }
      throw toServiceError(error);
    }
  }

  async listAssetUnitUsageTypes(): Promise<string[]> {
    try {
      const result = await apiClient.get<string[]>(`${API_BASE}/asset-units/usage-types`, {
        cache: false,
      });
      if (!result.success) {
        throw new AssetOperationsError(
          `获取资产单元业态选项失败: ${result.error}`,
          extractErrorCode(result)
        );
      }
      return Array.isArray(result.data) ? result.data : [];
    } catch (error) {
      if (error instanceof AssetOperationsError) {
        throw error;
      }
      throw toServiceError(error);
    }
  }

  async getAssetUnit(unitId: string): Promise<AssetUnitListItem> {
    try {
      const result = await apiClient.get<RawUnitRecord>(`${API_BASE}/asset-units/${unitId}`, {
        cache: false,
      });
      if (!result.success) {
        throw new AssetOperationsError(
          `获取资产单元详情失败: ${result.error}`,
          extractErrorCode(result)
        );
      }
      return normalizeUnit(result.data ?? {});
    } catch (error) {
      if (error instanceof AssetOperationsError) {
        throw error;
      }
      throw toServiceError(error);
    }
  }

  async listAssetUnitCertificates(unitId: string): Promise<AssetUnitCertificate[]> {
    try {
      const result = await apiClient.get<{ items: AssetUnitCertificate[] }>(
        `${API_BASE}/asset-units/${encodeURIComponent(unitId)}/property-certificates`,
        { cache: false }
      );
      if (!result.success) {
        throw new AssetOperationsError('产权证加载失败，请重新加载。', extractErrorCode(result));
      }
      if (result.data == null || !Array.isArray(result.data.items)) {
        throw new AssetOperationsError('产权证数据格式错误，请重新加载。', 'INVALID_RESPONSE_DATA');
      }
      return result.data.items;
    } catch (error) {
      if (error instanceof AssetOperationsError) throw error;
      throw toServiceError(error);
    }
  }

  async listCertificateOptions(
    unitId: string,
    q: string,
    offset = 0
  ): Promise<{ items: AssetUnitCertificate[]; total: number }> {
    try {
      const result = await apiClient.get<{ items: AssetUnitCertificate[]; total: number }>(
        `${API_BASE}/asset-units/${encodeURIComponent(unitId)}/property-certificate-options`,
        { params: { q, offset, limit: 20 }, cache: false }
      );
      if (!result.success || result.data == null)
        throw new AssetOperationsError('候选证照加载失败，请重试。', extractErrorCode(result));
      return result.data;
    } catch (error) {
      if (error instanceof AssetOperationsError) throw error;
      throw toServiceError(error);
    }
  }

  async linkCertificate(
    unitId: string,
    input: { certificate_id: string; effective_from: string; effective_to?: string }
  ): Promise<void> {
    try {
      const result = await apiClient.post(
        `${API_BASE}/asset-units/${encodeURIComponent(unitId)}/property-certificates`,
        input
      );
      if (!result.success)
        throw new AssetOperationsError(
          '关联保存失败，请刷新候选后重试。',
          extractErrorCode(result)
        );
    } catch (error) {
      if (error instanceof AssetOperationsError) throw error;
      throw toServiceError(error);
    }
  }

  async unlinkCertificate(
    unitId: string,
    certificateId: string,
    effectiveFrom: string
  ): Promise<void> {
    try {
      const result = await apiClient.post(
        `${API_BASE}/asset-units/${encodeURIComponent(unitId)}/property-certificates/${encodeURIComponent(certificateId)}/unlink`,
        { effective_from: effectiveFrom }
      );
      if (!result.success)
        throw new AssetOperationsError('解除安排保存失败，请重试。', extractErrorCode(result));
    } catch (error) {
      if (error instanceof AssetOperationsError) throw error;
      throw toServiceError(error);
    }
  }

  async updateAssetUnit(
    unitId: string,
    request: { expectedVersion: number; name?: string; address?: string }
  ): Promise<AssetUnitListItem> {
    try {
      const result = await apiClient.patch<RawUnitRecord>(`${API_BASE}/asset-units/${unitId}`, {
        expected_version: request.expectedVersion,
        ...(request.name != null ? { name: request.name } : {}),
        ...(request.address != null ? { address: request.address } : {}),
      });
      if (!result.success) {
        throw new AssetOperationsError(
          `更新资产单元失败: ${result.error}`,
          extractErrorCode(result)
        );
      }
      return normalizeUnit(result.data ?? {});
    } catch (error) {
      if (error instanceof AssetOperationsError) {
        throw error;
      }
      throw toServiceError(error);
    }
  }

  async listUpstreamContracts(
    params: {
      contractType?: string;
      ownerPartyId?: string;
      q?: string;
      offset?: number;
      limit?: number;
    } = {}
  ): Promise<ContractListResult<UpstreamContractListItem>> {
    try {
      const result = await apiClient.get<{
        items: RawUnitRecord[];
        total: number;
      }>(`${API_BASE}/upstream-contracts`, {
        params: {
          ...(params.contractType != null ? { contract_type: params.contractType } : {}),
          ...(params.ownerPartyId != null ? { owner_party_id: params.ownerPartyId } : {}),
          ...(params.q != null && params.q.trim() !== '' ? { q: params.q } : {}),
          offset: params.offset ?? 0,
          limit: params.limit ?? 50,
        },
        cache: false,
      });
      if (!result.success) {
        throw new AssetOperationsError(
          `获取上游合同列表失败: ${result.error}`,
          extractErrorCode(result)
        );
      }
      const payload = result.data ?? { items: [], total: 0 };
      return {
        items: (payload.items ?? []).map(normalizeUpstream),
        total: Number(payload.total ?? 0),
      };
    } catch (error) {
      if (error instanceof AssetOperationsError) {
        throw error;
      }
      throw toServiceError(error);
    }
  }

  async getUpstreamContract(contractId: string): Promise<UpstreamContractDetail> {
    try {
      const result = await apiClient.get<RawUnitRecord>(
        `${API_BASE}/upstream-contracts/${contractId}`,
        { cache: false }
      );
      if (!result.success) {
        throw new AssetOperationsError(
          `获取上游合同详情失败: ${result.error}`,
          extractErrorCode(result)
        );
      }
      return normalizeUpstream(result.data ?? {});
    } catch (error) {
      if (error instanceof AssetOperationsError) {
        throw error;
      }
      throw toServiceError(error);
    }
  }

  async listTerminalContracts(
    params: {
      filter?:
        | 'active'
        | 'expiring_180'
        | 'rent_unpaid'
        | 'deposit_unsettled'
        | 'missing_scan'
        | 'ended';
      contractMode?: string;
      upstreamContractId?: string;
      ownerPartyId?: string;
      q?: string;
      offset?: number;
      limit?: number;
    } = {}
  ): Promise<TerminalContractListResult> {
    try {
      const result = await apiClient.get<{
        items: RawUnitRecord[];
        total: number;
        counts?: RawUnitRecord | null;
      }>(`${API_BASE}/terminal-contracts`, {
        params: {
          ...(params.filter != null ? { filter: params.filter } : {}),
          ...(params.contractMode != null ? { contract_mode: params.contractMode } : {}),
          ...(params.upstreamContractId != null
            ? { upstream_contract_id: params.upstreamContractId }
            : {}),
          ...(params.ownerPartyId != null ? { owner_party_id: params.ownerPartyId } : {}),
          ...(params.q != null && params.q.trim() !== '' ? { q: params.q } : {}),
          offset: params.offset ?? 0,
          limit: params.limit ?? 50,
        },
        cache: false,
      });
      if (!result.success) {
        throw new AssetOperationsError(
          `获取终端合同列表失败: ${result.error}`,
          extractErrorCode(result)
        );
      }
      const payload = result.data ?? { items: [], total: 0 };
      const countsRaw = payload.counts ?? null;
      return {
        items: (payload.items ?? []).map(normalizeTerminal),
        total: Number(payload.total ?? 0),
        counts:
          countsRaw == null
            ? null
            : {
                active: Number(countsRaw.active ?? 0),
                expiring180: Number(countsRaw.expiring_180 ?? 0),
                rentUnpaid: Number(countsRaw.rent_unpaid ?? 0),
                depositUnsettled: Number(countsRaw.deposit_unsettled ?? 0),
                missingScan: Number(countsRaw.missing_scan ?? 0),
                ended: Number(countsRaw.ended ?? 0),
              },
      };
    } catch (error) {
      if (error instanceof AssetOperationsError) {
        throw error;
      }
      throw toServiceError(error);
    }
  }

  async getTerminalContract(contractId: string): Promise<TerminalContractDetail> {
    try {
      const result = await apiClient.get<RawUnitRecord>(
        `${API_BASE}/terminal-contracts/${contractId}`,
        { cache: false }
      );
      if (!result.success) {
        throw new AssetOperationsError(
          `获取终端合同详情失败: ${result.error}`,
          extractErrorCode(result)
        );
      }
      return normalizeTerminal(result.data ?? {});
    } catch (error) {
      if (error instanceof AssetOperationsError) {
        throw error;
      }
      throw toServiceError(error);
    }
  }

  async createIntakeSession(
    contractType: ContractIntakeType,
    file: File
  ): Promise<ContractIntakeSession> {
    try {
      const formData = new FormData();
      formData.append('contract_type', contractType);
      formData.append('file', file);
      const result = await apiClient.post<RawUnitRecord>(
        `${API_BASE}/contract-intake-sessions`,
        formData,
        {
          headers: { 'Content-Type': 'multipart/form-data' },
          retry: false,
          smartExtract: true,
        }
      );
      if (!result.success) {
        throw new AssetOperationsError(
          `创建录入会话失败: ${result.error}`,
          extractErrorCode(result)
        );
      }
      return normalizeSession(result.data ?? {});
    } catch (error) {
      if (error instanceof AssetOperationsError) {
        throw error;
      }
      throw toServiceError(error);
    }
  }

  async getIntakeSession(sessionId: string): Promise<ContractIntakeSession> {
    try {
      const result = await apiClient.get<RawUnitRecord>(
        `${API_BASE}/contract-intake-sessions/${sessionId}`,
        { cache: false }
      );
      if (!result.success) {
        throw new AssetOperationsError(
          `读取录入会话失败: ${result.error}`,
          extractErrorCode(result)
        );
      }
      return normalizeSession(result.data ?? {});
    } catch (error) {
      if (error instanceof AssetOperationsError) {
        throw error;
      }
      throw toServiceError(error);
    }
  }

  async confirmUpstreamIntake(
    sessionId: string,
    payload: ConfirmUpstreamPayload,
    idempotencyKey: string
  ): Promise<CreatedContractResult> {
    try {
      const result = await apiClient.post<RawUnitRecord>(
        `${API_BASE}/contract-intake-sessions/${sessionId}/confirm-upstream`,
        convertFrontendToBackend(payload),
        {
          headers: { 'Idempotency-Key': idempotencyKey },
          retry: false,
          smartExtract: true,
        }
      );
      if (!result.success) {
        throw new AssetOperationsError(
          `确认上游合同失败: ${result.error}`,
          extractErrorCode(result)
        );
      }
      const data = convertBackendToFrontend<RawUnitRecord>(result.data ?? {});
      return {
        id: String(data.id ?? ''),
        contractNumber: String(data.contract_number ?? ''),
        idempotent: Boolean(data.idempotent),
      };
    } catch (error) {
      if (error instanceof AssetOperationsError) {
        throw error;
      }
      throw toServiceError(error);
    }
  }

  async confirmTerminalIntake(
    sessionId: string,
    payload: ConfirmTerminalPayload,
    idempotencyKey: string
  ): Promise<CreatedContractResult> {
    try {
      const result = await apiClient.post<RawUnitRecord>(
        `${API_BASE}/contract-intake-sessions/${sessionId}/confirm-terminal`,
        convertFrontendToBackend(payload),
        {
          headers: { 'Idempotency-Key': idempotencyKey },
          retry: false,
          smartExtract: true,
        }
      );
      if (!result.success) {
        throw new AssetOperationsError(
          `确认终端合同失败: ${result.error}`,
          extractErrorCode(result)
        );
      }
      const data = convertBackendToFrontend<RawUnitRecord>(result.data ?? {});
      return {
        id: String(data.id ?? ''),
        contractNumber: String(data.contract_number ?? ''),
        idempotent: Boolean(data.idempotent),
      };
    } catch (error) {
      if (error instanceof AssetOperationsError) {
        throw error;
      }
      throw toServiceError(error);
    }
  }

  async cancelIntakeSession(sessionId: string): Promise<void> {
    try {
      const result = await apiClient.post<RawUnitRecord>(
        `${API_BASE}/contract-intake-sessions/${sessionId}/cancel`,
        {},
        { retry: false, smartExtract: true }
      );
      if (!result.success) {
        throw new AssetOperationsError(
          `取消录入会话失败: ${result.error}`,
          extractErrorCode(result)
        );
      }
    } catch (error) {
      if (error instanceof AssetOperationsError) {
        throw error;
      }
      throw toServiceError(error);
    }
  }

  private static toLifecycleEvent(raw: RawUnitRecord): LifecycleEventRecord {
    return {
      id: String(raw.id ?? ''),
      contractKind: String(raw.contract_kind ?? ''),
      contractId: String(raw.contract_id ?? ''),
      eventType: String(raw.event_type ?? ''),
      effectiveDate: String(raw.effective_date ?? ''),
      reason: raw.reason == null ? null : String(raw.reason),
    };
  }

  async previewTerminalTermination(
    contractId: string,
    proposal: {
      effective_date: string;
      termination_type: string;
      handover_status: string;
      deposit_settlement_status: string;
      deposit_offset_mode?: 'auto' | 'none' | 'manual';
      deposit_offsets?: { ledger_entry_id: string; amount: number | string }[];
      clawback_amount?: number | string;
      clawback_basis?: string;
      reason: string;
    }
  ): Promise<TerminationPreview> {
    try {
      const result = await apiClient.post<RawUnitRecord>(
        `${API_BASE}/terminal-contracts/${contractId}/termination/preview`,
        proposal,
        { retry: false, smartExtract: true }
      );
      if (!result.success) {
        throw new AssetOperationsError(`终止预览失败: ${result.error}`, extractErrorCode(result));
      }
      const data = result.data ?? {};
      const impacts = Array.isArray(data.coverage_impact) ? data.coverage_impact : [];
      return {
        contractId: String(data.contract_id ?? contractId),
        contractVersion: Number(data.contract_version ?? 1),
        effectiveDate: String(data.effective_date ?? ''),
        lastValidDay: String(data.last_valid_day ?? ''),
        ...(data.deposit_settlement != null
          ? {
              depositSettlement: convertBackendToFrontend<DepositSettlementPreview>(
                data.deposit_settlement
              ),
            }
          : {}),
        coverageImpact: impacts.map(item => {
          const impact = item as RawUnitRecord;
          return {
            assetUnitId: String(impact.asset_unit_id ?? ''),
            effectiveFrom: String(impact.effective_from ?? ''),
            currentEffectiveTo:
              impact.current_effective_to == null ? null : String(impact.current_effective_to),
            newEffectiveTo: String(impact.new_effective_to ?? ''),
          };
        }),
        warnings: Array.isArray(data.warnings) ? data.warnings.map(String) : [],
        ...(data.rent_impact != null
          ? {
              rentImpact: convertBackendToFrontend<
                import('@/services/assetLedgerService').RentImpact
              >(data.rent_impact),
            }
          : {}),
        previewToken: String(data.preview_token ?? ''),
        expiresAt: String(data.expires_at ?? ''),
      };
    } catch (error) {
      if (error instanceof AssetOperationsError) {
        throw error;
      }
      throw toServiceError(error);
    }
  }

  async commitTerminalTermination(
    contractId: string,
    request: { preview_token: string; expected_version: number },
    idempotencyKey: string
  ): Promise<LifecycleEventRecord> {
    try {
      const result = await apiClient.post<RawUnitRecord>(
        `${API_BASE}/terminal-contracts/${contractId}/termination`,
        request,
        {
          headers: { 'Idempotency-Key': idempotencyKey },
          retry: false,
          smartExtract: true,
        }
      );
      if (!result.success) {
        throw new AssetOperationsError(`终止提交失败: ${result.error}`, extractErrorCode(result));
      }
      return AssetOperationsService.toLifecycleEvent(result.data ?? {});
    } catch (error) {
      if (error instanceof AssetOperationsError) {
        throw error;
      }
      throw toServiceError(error);
    }
  }

  async reverseTerminalTermination(
    contractId: string,
    proposal: {
      target_event_id: string;
      effective_date: string;
      reason: string;
    },
    idempotencyKey: string
  ): Promise<LifecycleEventRecord> {
    try {
      const result = await apiClient.post<RawUnitRecord>(
        `${API_BASE}/terminal-contracts/${contractId}/termination-reversal`,
        proposal,
        {
          headers: { 'Idempotency-Key': idempotencyKey },
          retry: false,
          smartExtract: true,
        }
      );
      if (!result.success) {
        throw new AssetOperationsError(`撤销终止失败: ${result.error}`, extractErrorCode(result));
      }
      return AssetOperationsService.toLifecycleEvent(result.data ?? {});
    } catch (error) {
      if (error instanceof AssetOperationsError) {
        throw error;
      }
      throw toServiceError(error);
    }
  }

  async previewUpstreamExit(
    contractId: string,
    proposal: { effective_date: string; reason: string }
  ): Promise<ExitPreview> {
    try {
      const result = await apiClient.post<RawUnitRecord>(
        `${API_BASE}/upstream-contracts/${contractId}/exit/preview`,
        proposal,
        { retry: false, smartExtract: true }
      );
      if (!result.success) {
        throw new AssetOperationsError(`退出预览失败: ${result.error}`, extractErrorCode(result));
      }
      const data = convertBackendToFrontend<RawUnitRecord>(result.data ?? {});
      const impacts = Array.isArray(data.coverage_impact) ? data.coverage_impact : [];
      return {
        contractId: String(data.contract_id ?? contractId),
        contractVersion: Number(data.contract_version ?? 1),
        depositAmount: requireDecimal(data, 'deposit_amount'),
        ...(data.deposit_settlement != null
          ? {
              depositSettlement: convertBackendToFrontend<{
                applicable?: boolean;
                recoverable_amount?: number;
              }>(data.deposit_settlement),
            }
          : {}),
        effectiveDate: String(data.effective_date ?? ''),
        lastValidDay: String(data.last_valid_day ?? ''),
        coverageImpact: impacts.map(item => {
          const impact = item as RawUnitRecord;
          return {
            assetUnitId: String(impact.asset_unit_id ?? ''),
            effectiveFrom: String(impact.effective_from ?? ''),
            currentEffectiveTo:
              impact.current_effective_to == null ? null : String(impact.current_effective_to),
            newEffectiveTo: String(impact.new_effective_to ?? ''),
          };
        }),
        ...(data.rent_impact != null
          ? {
              rentImpact: convertBackendToFrontend<
                import('@/services/assetLedgerService').RentImpact
              >(data.rent_impact),
            }
          : {}),
        previewToken: String(data.preview_token ?? ''),
        expiresAt: String(data.expires_at ?? ''),
      };
    } catch (error) {
      if (error instanceof AssetOperationsError) {
        throw error;
      }
      throw toServiceError(error);
    }
  }

  async commitUpstreamExit(
    contractId: string,
    request: { preview_token: string; expected_version: number },
    idempotencyKey: string
  ): Promise<LifecycleEventRecord> {
    try {
      const result = await apiClient.post<RawUnitRecord>(
        `${API_BASE}/upstream-contracts/${contractId}/exit`,
        request,
        {
          headers: { 'Idempotency-Key': idempotencyKey },
          retry: false,
          smartExtract: true,
        }
      );
      if (!result.success) {
        throw new AssetOperationsError(`退出提交失败: ${result.error}`, extractErrorCode(result));
      }
      return AssetOperationsService.toLifecycleEvent(result.data ?? {});
    } catch (error) {
      if (error instanceof AssetOperationsError) {
        throw error;
      }
      throw toServiceError(error);
    }
  }

  async reverseUpstreamExit(
    contractId: string,
    proposal: {
      target_event_id: string;
      effective_date: string;
      reason: string;
    },
    idempotencyKey: string
  ): Promise<LifecycleEventRecord> {
    try {
      const result = await apiClient.post<RawUnitRecord>(
        `${API_BASE}/upstream-contracts/${contractId}/exit-reversal`,
        proposal,
        {
          headers: { 'Idempotency-Key': idempotencyKey },
          retry: false,
          smartExtract: true,
        }
      );
      if (!result.success) {
        throw new AssetOperationsError(`撤销退出失败: ${result.error}`, extractErrorCode(result));
      }
      return AssetOperationsService.toLifecycleEvent(result.data ?? {});
    } catch (error) {
      if (error instanceof AssetOperationsError) {
        throw error;
      }
      throw toServiceError(error);
    }
  }

  async renewTerminal(
    contractId: string,
    payload: ConfirmTerminalPayload & {
      scan_document_id: string;
      scan_owner_id: string;
    },
    idempotencyKey: string
  ): Promise<RenewalResult> {
    try {
      const result = await apiClient.post<RawUnitRecord>(
        `${API_BASE}/terminal-contracts/${contractId}/renewals`,
        convertFrontendToBackend(payload),
        {
          headers: { 'Idempotency-Key': idempotencyKey },
          retry: false,
          smartExtract: true,
        }
      );
      if (!result.success) {
        throw new AssetOperationsError(`登记续签失败: ${result.error}`, extractErrorCode(result));
      }
      const data = result.data ?? {};
      return {
        id: String(data.id ?? ''),
        contractNumber: String(data.contract_number ?? ''),
        idempotent: Boolean(data.idempotent),
      };
    } catch (error) {
      if (error instanceof AssetOperationsError) {
        throw error;
      }
      throw toServiceError(error);
    }
  }

  async renewUpstream(
    contractId: string,
    payload: ConfirmUpstreamPayload & {
      scan_document_id: string;
      scan_owner_id: string;
    },
    idempotencyKey: string
  ): Promise<RenewalResult> {
    try {
      const result = await apiClient.post<RawUnitRecord>(
        `${API_BASE}/upstream-contracts/${contractId}/renewals`,
        convertFrontendToBackend(payload),
        {
          headers: { 'Idempotency-Key': idempotencyKey },
          retry: false,
          smartExtract: true,
        }
      );
      if (!result.success) {
        throw new AssetOperationsError(`登记续签失败: ${result.error}`, extractErrorCode(result));
      }
      const data = result.data ?? {};
      return {
        id: String(data.id ?? ''),
        contractNumber: String(data.contract_number ?? ''),
        idempotent: Boolean(data.idempotent),
      };
    } catch (error) {
      if (error instanceof AssetOperationsError) {
        throw error;
      }
      throw toServiceError(error);
    }
  }

  async updateVacancyNote(
    unitId: string,
    request: {
      expectedVersion: number;
      vacancyReason?: string;
      expectedLeaseStart?: string;
    }
  ): Promise<AssetUnitListItem> {
    try {
      const result = await apiClient.put<RawUnitRecord>(
        `${API_BASE}/asset-units/${unitId}/vacancy-note`,
        {
          expected_version: request.expectedVersion,
          ...(request.vacancyReason != null ? { vacancy_reason: request.vacancyReason } : {}),
          ...(request.expectedLeaseStart != null
            ? { expected_lease_start: request.expectedLeaseStart }
            : {}),
        }
      );
      if (!result.success) {
        throw new AssetOperationsError(
          `更新空置备注失败: ${result.error}`,
          extractErrorCode(result)
        );
      }
      return normalizeUnit(result.data ?? {});
    } catch (error) {
      if (error instanceof AssetOperationsError) {
        throw error;
      }
      throw toServiceError(error);
    }
  }

  /** 调整资产单元（原型：拆分/合并弹窗）——预览与提交两步命令。 */
  async previewAssetUnitSplit(
    unitId: string,
    request: {
      effectiveDate: string;
      parts: {
        unitCode: string;
        name: string;
        landArea: number;
        buildingArea: number;
        rentableArea: number;
      }[];
    }
  ): Promise<RawUnitRecord> {
    return this._boundaryPreview(`${API_BASE}/asset-units/${unitId}/split/preview`, {
      effective_date: request.effectiveDate,
      parts: request.parts.map(part => ({
        unit_code: part.unitCode,
        name: part.name,
        land_area: part.landArea,
        building_area: part.buildingArea,
        rentable_area: part.rentableArea,
      })),
    });
  }

  async previewAssetUnitMerge(request: {
    sourceUnitIds: string[];
    effectiveDate: string;
    resultUnitCode: string;
    resultName: string;
  }): Promise<RawUnitRecord> {
    return this._boundaryPreview(`${API_BASE}/asset-units/merge/preview`, {
      source_unit_ids: request.sourceUnitIds,
      effective_date: request.effectiveDate,
      result: { unit_code: request.resultUnitCode, name: request.resultName },
    });
  }

  async _boundaryPreview(path: string, payload: unknown): Promise<RawUnitRecord> {
    try {
      const result = await apiClient.post<RawUnitRecord>(path, payload, {
        retry: false,
      });
      if (!result.success) {
        throw new AssetOperationsError(`预览失败: ${result.error}`, extractErrorCode(result));
      }
      return result.data ?? {};
    } catch (error) {
      if (error instanceof AssetOperationsError) {
        throw error;
      }
      throw toServiceError(error);
    }
  }

  async commitAssetUnitSplit(
    unitId: string,
    request: { previewToken: string; reason: string; expectedVersion: number }
  ): Promise<RawUnitRecord> {
    return this._boundaryCommit(`${API_BASE}/asset-units/${unitId}/split`, {
      preview_token: request.previewToken,
      reason: request.reason,
      expected_version: request.expectedVersion,
    });
  }

  async commitAssetUnitMerge(request: {
    previewToken: string;
    reason: string;
    expectedVersions: Record<string, number>;
  }): Promise<RawUnitRecord> {
    return this._boundaryCommit(`${API_BASE}/asset-units/merge`, {
      preview_token: request.previewToken,
      reason: request.reason,
      expected_versions: request.expectedVersions,
    });
  }

  async _boundaryCommit(path: string, payload: unknown): Promise<RawUnitRecord> {
    try {
      const result = await apiClient.post<RawUnitRecord>(path, payload, {
        retry: false,
        headers: {
          'Idempotency-Key':
            typeof crypto !== 'undefined' && 'randomUUID' in crypto
              ? crypto.randomUUID()
              : `boundary-${Date.now()}`,
        },
      });
      if (!result.success) {
        throw new AssetOperationsError(`提交失败: ${result.error}`, extractErrorCode(result));
      }
      return result.data ?? {};
    } catch (error) {
      if (error instanceof AssetOperationsError) {
        throw error;
      }
      throw toServiceError(error);
    }
  }

  /** 单元租赁时间轴：覆盖过该单元的终端/上游合同区间（终止已回放）。 */
  async getCoverageHistory(unitId: string): Promise<
    {
      contractKind: 'terminal' | 'upstream';
      contractId: string;
      contractNumber: string;
      startDate: string;
      endDate: string;
    }[]
  > {
    try {
      const result = await apiClient.get<{
        items: {
          contract_kind?: unknown;
          contract_id?: unknown;
          contract_number?: unknown;
          start_date?: unknown;
          end_date?: unknown;
        }[];
      }>(`${API_BASE}/asset-units/${unitId}/coverage-history`, { cache: false });
      if (!result.success) {
        throw new AssetOperationsError(
          `获取租赁时间轴失败: ${result.error}`,
          extractErrorCode(result)
        );
      }
      return (result.data?.items ?? []).map(item => ({
        contractKind: item.contract_kind === 'upstream' ? 'upstream' : 'terminal',
        contractId: String(item.contract_id ?? ''),
        contractNumber: String(item.contract_number ?? ''),
        startDate: String(item.start_date ?? ''),
        endDate: String(item.end_date ?? ''),
      }));
    } catch (error) {
      if (error instanceof AssetOperationsError) {
        throw error;
      }
      throw toServiceError(error);
    }
  }

  /** 物业台账导出（xlsx blob），参数与列表筛选一致。 */
  async exportAssetUnits(params: AssetUnitListParams): Promise<Blob> {
    try {
      const result = await apiClient
        .getAxiosInstance()
        .get<Blob>(`${API_BASE}/asset-units/export`, {
          params: {
            ...(params.projectId != null ? { project_id: params.projectId } : {}),
            ...(params.ownerPartyId != null ? { owner_party_id: params.ownerPartyId } : {}),
            ...(params.usageType != null ? { usage_type: params.usageType } : {}),
            ...(params.q != null && params.q.trim() !== '' ? { q: params.q } : {}),
            ...(params.filter != null ? { filter: params.filter } : {}),
            ...(params.assessmentOperatorPartyId != null
              ? { assessment_operator_party_id: params.assessmentOperatorPartyId }
              : {}),
            ...(params.assessmentYear != null ? { assessment_year: params.assessmentYear } : {}),
          },
          responseType: 'blob',
        });
      return result.data;
    } catch (error) {
      throw toServiceError(error);
    }
  }
}

export const assetOperationsService = new AssetOperationsService();
