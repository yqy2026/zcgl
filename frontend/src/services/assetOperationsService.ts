/**
 * Asset Operations Service
 * 资产运营 v5 纵向切片：资产单元与合同链
 *
 * 后端金额/面积字段是 Decimal 字符串；本服务统一转成 number 后再交给页面。
 */

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
}

export interface AssetUnitListResult {
  items: AssetUnitListItem[];
  total: number;
}

export interface AssetUnitListParams {
  projectId?: string;
  ownerPartyId?: string;
  usageType?: string;
  q?: string;
  filter?: 'all' | 'non_rentable';
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
  };
}

export interface UpstreamContractListItem {
  id: string;
  contractNumber: string;
  contractType: 'lease' | 'management_agreement';
  name: string;
  ownerPartyId: string;
  operatorPartyId: string;
  startDate: string;
  endDate: string;
  paymentCycle: string | null;
  paymentDay: number | null;
  depositAmount: number;
  renewedFromId: string | null;
  version: number;
  status: 'scheduled' | 'active' | 'expiring' | 'expired_pending_action' | 'exited' | 'historical';
  warnings: { code: string; severity: string; message: string | null }[];
  terminalContractIds: string[];
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
}

export interface ContractListResult<T> {
  items: T[];
  total: number;
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
  };
}

function normalizeTerminal(raw: RawUnitRecord): TerminalContractListItem {
  const normalized = convertBackendToFrontend<RawUnitRecord>(raw);
  const allowedTerminalStatus = ['scheduled', 'active', 'expiring', 'ended', 'historical'] as const;
  const statusValue = String(raw.status ?? '');
  return {
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
  contractId: string;
  contractVersion: number;
  effectiveDate: string;
  lastValidDay: string;
  coverageImpact: TerminationCoverageImpact[];
  warnings: string[];
  previewToken: string;
  expiresAt: string;
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
      const result = await apiClient.get<{ items: RawUnitRecord[]; total: number }>(
        `${API_BASE}/asset-units`,
        {
          params: {
            ...(params.projectId != null ? { project_id: params.projectId } : {}),
            ...(params.ownerPartyId != null ? { owner_party_id: params.ownerPartyId } : {}),
            ...(params.usageType != null ? { usage_type: params.usageType } : {}),
            ...(params.q != null && params.q.trim() !== '' ? { q: params.q } : {}),
            ...(params.filter != null ? { filter: params.filter } : {}),
            offset: params.offset ?? 0,
            limit: params.limit ?? 50,
          },
          cache: false,
        }
      );
      if (!result.success) {
        throw new AssetOperationsError(
          `获取资产单元列表失败: ${result.error}`,
          extractErrorCode(result)
        );
      }
      const payload = result.data ?? { items: [], total: 0 };
      return {
        items: (payload.items ?? []).map(normalizeUnit),
        total: Number(payload.total ?? 0),
      };
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
      contractMode?: string;
      upstreamContractId?: string;
      q?: string;
      offset?: number;
      limit?: number;
    } = {}
  ): Promise<ContractListResult<TerminalContractListItem>> {
    try {
      const result = await apiClient.get<{
        items: RawUnitRecord[];
        total: number;
      }>(`${API_BASE}/terminal-contracts`, {
        params: {
          ...(params.contractMode != null ? { contract_mode: params.contractMode } : {}),
          ...(params.upstreamContractId != null
            ? { upstream_contract_id: params.upstreamContractId }
            : {}),
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
      return {
        items: (payload.items ?? []).map(normalizeTerminal),
        total: Number(payload.total ?? 0),
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
}

export const assetOperationsService = new AssetOperationsService();
