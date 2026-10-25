/**
 * Asset Operations Service
 * 资产运营 v5 纵向切片：资产单元与合同链
 *
 * 后端金额/面积字段是 Decimal 字符串；本服务统一转成 number 后再交给页面。
 */

import { apiClient } from '@/api/client';
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

const NUMBER_FIELDS = [
  'land_area',
  'building_area',
  'rentable_area',
  'rented_area',
  'occupancy_rate',
] as const;

type RawUnitRecord = Record<string, unknown>;

function toNumber(value: unknown): number {
  if (typeof value === 'number') {
    return value;
  }
  if (typeof value === 'string' && value.trim() !== '') {
    const parsed = Number(value);
    return Number.isNaN(parsed) ? 0 : parsed;
  }
  return 0;
}

function normalizeUnit(raw: RawUnitRecord): AssetUnitListItem {
  const normalized: RawUnitRecord = { ...raw };
  for (const field of NUMBER_FIELDS) {
    if (field in normalized) {
      normalized[field] = toNumber(normalized[field]);
    }
  }
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
    landArea: toNumber(normalized.land_area),
    buildingArea: toNumber(normalized.building_area),
    rentableArea: toNumber(normalized.rentable_area),
    managedFrom: String(normalized.managed_from ?? ''),
    managedTo:
      normalized.managed_to == null ? null : String(normalized.managed_to),
    vacancyReason:
      normalized.vacancy_reason == null
        ? null
        : String(normalized.vacancy_reason),
    expectedLeaseStart:
      normalized.expected_lease_start == null
        ? null
        : String(normalized.expected_lease_start),
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
    rentedArea: toNumber(normalized.rented_area),
    occupancyRate: toNumber(normalized.occupancy_rate),
    warnings: Array.isArray(normalized.warnings)
      ? normalized.warnings.map((item) => {
          const warning = item as RawUnitRecord;
          return {
            code: String(warning.code ?? ''),
            severity: String(warning.severity ?? 'warning'),
            message:
              warning.message == null ? null : String(warning.message),
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
  status:
    | 'scheduled'
    | 'active'
    | 'expiring'
    | 'expired_pending_action'
    | 'exited'
    | 'historical';
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

function normalizeWarnings(raw: unknown): {
  code: string;
  severity: string;
  message: string | null;
}[] {
  if (!Array.isArray(raw)) {
    return [];
  }
  return raw.map((item) => {
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
  return raw.map((item) => {
    const coverage = item as RawUnitRecord;
    return {
      assetUnitId: String(coverage.asset_unit_id ?? ''),
      effectiveFrom: String(coverage.effective_from ?? ''),
      effectiveTo:
        coverage.effective_to == null ? null : String(coverage.effective_to),
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
  return raw.map((item) => {
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
  return raw.map((item) => {
    const node = item as RawUnitRecord;
    return {
      contractId: String(node.contract_id ?? ''),
      contractNumber: String(node.contract_number ?? ''),
      relation: String(node.relation ?? ''),
    };
  });
}

function normalizeUpstream(raw: RawUnitRecord): UpstreamContractListItem {
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
    contractType:
      raw.contract_type === 'management_agreement'
        ? 'management_agreement'
        : 'lease',
    name: String(raw.name ?? ''),
    ownerPartyId: String(raw.owner_party_id ?? ''),
    operatorPartyId: String(raw.operator_party_id ?? ''),
    startDate: String(raw.start_date ?? ''),
    endDate: String(raw.end_date ?? ''),
    paymentCycle: raw.payment_cycle == null ? null : String(raw.payment_cycle),
    paymentDay: raw.payment_day == null ? null : Number(raw.payment_day),
    depositAmount: toNumber(raw.deposit_amount),
    renewedFromId:
      raw.renewed_from_id == null ? null : String(raw.renewed_from_id),
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
  const allowedTerminalStatus = [
    'scheduled',
    'active',
    'expiring',
    'ended',
    'historical',
  ] as const;
  const statusValue = String(raw.status ?? '');
  return {
    id: String(raw.id ?? ''),
    contractNumber: String(raw.contract_number ?? ''),
    contractMode:
      raw.contract_mode === 'direct_lease' ? 'direct_lease' : 'sublease',
    tenantPartyId: String(raw.tenant_party_id ?? ''),
    lessorPartyId: String(raw.lessor_party_id ?? ''),
    upstreamContractId:
      raw.upstream_contract_id == null ? null : String(raw.upstream_contract_id),
    startDate: String(raw.start_date ?? ''),
    endDate: String(raw.end_date ?? ''),
    depositAmount: toNumber(raw.deposit_amount),
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

export class AssetOperationsService {
  async listAssetUnits(
    params: AssetUnitListParams = {},
  ): Promise<AssetUnitListResult> {
    try {
      const result = await apiClient.get<{ items: RawUnitRecord[]; total: number }>(
        `${API_BASE}/asset-units`,
        {
          params: {
            ...(params.projectId != null ? { project_id: params.projectId } : {}),
            ...(params.ownerPartyId != null
              ? { owner_party_id: params.ownerPartyId }
              : {}),
            ...(params.usageType != null ? { usage_type: params.usageType } : {}),
            ...(params.q != null && params.q.trim() !== '' ? { q: params.q } : {}),
            ...(params.filter != null ? { filter: params.filter } : {}),
            offset: params.offset ?? 0,
            limit: params.limit ?? 50,
          },
          cache: false,
        },
      );
      if (!result.success) {
        throw new AssetOperationsError(`获取资产单元列表失败: ${result.error}`, extractErrorCode(result));
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
      const result = await apiClient.get<RawUnitRecord>(
        `${API_BASE}/asset-units/${unitId}`,
        { cache: false },
      );
      if (!result.success) {
        throw new AssetOperationsError(`获取资产单元详情失败: ${result.error}`, extractErrorCode(result));
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
    request: { expectedVersion: number; name?: string; address?: string },
  ): Promise<AssetUnitListItem> {
    try {
      const result = await apiClient.patch<RawUnitRecord>(
        `${API_BASE}/asset-units/${unitId}`,
        {
          expected_version: request.expectedVersion,
          ...(request.name != null ? { name: request.name } : {}),
          ...(request.address != null ? { address: request.address } : {}),
        },
      );
      if (!result.success) {
        throw new AssetOperationsError(`更新资产单元失败: ${result.error}`, extractErrorCode(result));
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
    } = {},
  ): Promise<ContractListResult<UpstreamContractListItem>> {
    try {
      const result = await apiClient.get<{
        items: RawUnitRecord[];
        total: number;
      }>(`${API_BASE}/upstream-contracts`, {
        params: {
          ...(params.contractType != null
            ? { contract_type: params.contractType }
            : {}),
          ...(params.ownerPartyId != null
            ? { owner_party_id: params.ownerPartyId }
            : {}),
          ...(params.q != null && params.q.trim() !== ''
            ? { q: params.q }
            : {}),
          offset: params.offset ?? 0,
          limit: params.limit ?? 50,
        },
        cache: false,
      });
      if (!result.success) {
        throw new AssetOperationsError(
          `获取上游合同列表失败: ${result.error}`,
          extractErrorCode(result),
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

  async getUpstreamContract(
    contractId: string,
  ): Promise<UpstreamContractDetail> {
    try {
      const result = await apiClient.get<RawUnitRecord>(
        `${API_BASE}/upstream-contracts/${contractId}`,
        { cache: false },
      );
      if (!result.success) {
        throw new AssetOperationsError(
          `获取上游合同详情失败: ${result.error}`,
          extractErrorCode(result),
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
    } = {},
  ): Promise<ContractListResult<TerminalContractListItem>> {
    try {
      const result = await apiClient.get<{
        items: RawUnitRecord[];
        total: number;
      }>(`${API_BASE}/terminal-contracts`, {
        params: {
          ...(params.contractMode != null
            ? { contract_mode: params.contractMode }
            : {}),
          ...(params.upstreamContractId != null
            ? { upstream_contract_id: params.upstreamContractId }
            : {}),
          ...(params.q != null && params.q.trim() !== ''
            ? { q: params.q }
            : {}),
          offset: params.offset ?? 0,
          limit: params.limit ?? 50,
        },
        cache: false,
      });
      if (!result.success) {
        throw new AssetOperationsError(
          `获取终端合同列表失败: ${result.error}`,
          extractErrorCode(result),
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

  async getTerminalContract(
    contractId: string,
  ): Promise<TerminalContractDetail> {
    try {
      const result = await apiClient.get<RawUnitRecord>(
        `${API_BASE}/terminal-contracts/${contractId}`,
        { cache: false },
      );
      if (!result.success) {
        throw new AssetOperationsError(
          `获取终端合同详情失败: ${result.error}`,
          extractErrorCode(result),
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

  async updateVacancyNote(
    unitId: string,
    request: {
      expectedVersion: number;
      vacancyReason?: string;
      expectedLeaseStart?: string;
    },
  ): Promise<AssetUnitListItem> {
    try {
      const result = await apiClient.put<RawUnitRecord>(
        `${API_BASE}/asset-units/${unitId}/vacancy-note`,
        {
          expected_version: request.expectedVersion,
          ...(request.vacancyReason != null
            ? { vacancy_reason: request.vacancyReason }
            : {}),
          ...(request.expectedLeaseStart != null
            ? { expected_lease_start: request.expectedLeaseStart }
            : {}),
        },
      );
      if (!result.success) {
        throw new AssetOperationsError(`更新空置备注失败: ${result.error}`, extractErrorCode(result));
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
