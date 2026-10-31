/**
 * Occupancy Report Service
 * 资产运营 v5 报送纵向切片：年度考核范围 + 月度出租率报送 + 历史快照
 *
 * 后端 JSON 为 snake_case，金额/面积为 Decimal 字符串；本服务经
 * convertBackendToFrontend 归一为 camelCase + number，坏数据直接抛错不补 0。
 * 错误统一抛带稳定 code 的 AssetOperationsError，页面只用 code 选择恢复动作。
 */

import { isAxiosError } from 'axios';
import { apiClient } from '@/api/client';
import { ApiErrorHandler } from '@/utils/responseExtractor';
import { convertBackendToFrontend, convertFrontendToBackend } from '@/utils/dataConversion';
import { AssetOperationsError } from '@/services/assetOperationsService';

export { AssetOperationsError };

type RawRecord = Record<string, unknown>;

interface RawErrorPayload {
  code?: unknown;
  message?: unknown;
  details?: unknown;
}

interface Envelope {
  success: boolean;
  data?: unknown;
  error?: unknown;
  rawResponse?: { data?: { error?: RawErrorPayload } };
}

function requireDecimal(record: RawRecord, field: string): number {
  const value = record[field];
  if (typeof value !== 'number' || !Number.isFinite(value)) {
    throw new Error(`Invalid Decimal field: ${field}`);
  }
  return value;
}

function requireNullableDecimal(record: RawRecord, field: string): number | null {
  // 仅字段缺失或显式 null 才视为空。注意 convertBackendToFrontend 对非法
  // Decimal 串（parseDecimal 返回 undefined）仍保留键、值变 undefined，
  // 此时必须抛错而不是静默归 null（与 requireDecimal 同策略）。
  if (!(field in record) || record[field] === null) {
    return null;
  }
  return requireDecimal(record, field);
}

/**
 * 兼容不在共享 DECIMAL_FIELDS 清单里、未经 convertBackendToFrontend
 * 转 number 的 Decimal 字段（如 occupancy_rate_current/new），坏数据照样抛错。
 */
function requireDecimalFromAny(value: unknown, field: string): number | null {
  if (value == null) {
    return null;
  }
  if (typeof value === 'number') {
    if (!Number.isFinite(value)) {
      throw new Error(`Invalid Decimal field: ${field}`);
    }
    return value;
  }
  if (typeof value === 'string' && value.trim() !== '') {
    const parsed = Number(value);
    if (Number.isFinite(parsed)) {
      return parsed;
    }
  }
  throw new Error(`Invalid Decimal field: ${field}`);
}

function requireString(record: RawRecord, field: string): string {
  const value = record[field];
  if (typeof value !== 'string' || value === '') {
    throw new Error(`Invalid string field: ${field}`);
  }
  return value;
}

function optionalString(record: RawRecord, field: string): string | null {
  const value = record[field];
  return value == null ? null : String(value);
}

function requireInt(record: RawRecord, field: string): number {
  const value = record[field];
  if (typeof value !== 'number' || !Number.isInteger(value)) {
    throw new Error(`Invalid integer field: ${field}`);
  }
  return value;
}

function requireBoolean(record: RawRecord, field: string): boolean {
  const value = record[field];
  if (typeof value !== 'boolean') {
    throw new Error(`Invalid boolean field: ${field}`);
  }
  return value;
}

function requireStringArray(record: RawRecord, field: string): string[] {
  const value = record[field];
  if (!Array.isArray(value)) {
    throw new Error(`Invalid array field: ${field}`);
  }
  return value.map(item => String(item));
}

// ==================== 错误构造 ====================

/**
 * 409 ASSESSMENT_SCOPE_DRAFT_EXISTS：后端 details.draft_id 指向已有草稿，
 * 页面用它直接引导进入该草稿继续编辑。
 */
export class AssessmentScopeDraftExistsError extends AssetOperationsError {
  readonly draftId: string;

  constructor(message: string, draftId: string) {
    super(message, 'ASSESSMENT_SCOPE_DRAFT_EXISTS');
    this.name = 'AssessmentScopeDraftExistsError';
    this.draftId = draftId;
  }
}

function toErrorPayloadError(
  payload: RawErrorPayload | undefined,
  fallbackCode: string,
  fallbackMessage: string
): AssetOperationsError {
  const code =
    typeof payload?.code === 'string' && payload.code !== '' ? payload.code : fallbackCode;
  const message =
    typeof payload?.message === 'string' && payload.message !== ''
      ? payload.message
      : fallbackMessage;
  if (code === 'ASSESSMENT_SCOPE_DRAFT_EXISTS') {
    const details =
      payload?.details != null && typeof payload.details === 'object' && !Array.isArray(payload.details)
        ? (payload.details as RawRecord)
        : null;
    const draftId = details?.draft_id;
    return new AssessmentScopeDraftExistsError(
      message,
      typeof draftId === 'string' ? draftId : ''
    );
  }
  return new AssetOperationsError(message, code);
}

function toServiceError(error: unknown): AssetOperationsError {
  if (error instanceof AssetOperationsError) {
    return error;
  }
  const enhanced = ApiErrorHandler.handleError(error);
  if (isAxiosError<{ error?: RawErrorPayload }>(error)) {
    const fallbackCode = error.response?.status === 403 ? 'FORBIDDEN' : enhanced.code;
    return toErrorPayloadError(
      error.response?.data?.error,
      fallbackCode,
      enhanced.message
    );
  }
  return new AssetOperationsError(enhanced.message, enhanced.code);
}

function unwrap<T>(result: Envelope): T {
  if (!result.success) {
    throw toErrorPayloadError(
      result.rawResponse?.data?.error,
      'UNKNOWN_ERROR',
      typeof result.error === 'string' ? result.error : '报送操作失败，请重试'
    );
  }
  if (result.data == null) {
    throw new AssetOperationsError('报送响应缺少数据，请重试', 'INVALID_RESPONSE_DATA');
  }
  return convertBackendToFrontend<T>(result.data);
}

async function get<T>(path: string, params?: Record<string, string | number>): Promise<T> {
  try {
    return unwrap<T>(await apiClient.get(`/api/v1${path}`, { cache: false, params }));
  } catch (error) {
    throw toServiceError(error);
  }
}

async function post<T>(
  path: string,
  payload?: unknown,
  options?: { key?: string; params?: Record<string, string> }
): Promise<T> {
  try {
    return unwrap<T>(
      await apiClient.post(
        `/api/v1${path}`,
        payload == null ? undefined : convertFrontendToBackend(payload),
        {
          retry: false,
          ...(options?.key != null ? { headers: { 'Idempotency-Key': options.key } } : {}),
          ...(options?.params != null ? { params: options.params } : {}),
        }
      )
    );
  } catch (error) {
    throw toServiceError(error);
  }
}

async function put<T>(path: string, payload: unknown): Promise<T> {
  try {
    return unwrap<T>(
      await apiClient.put(`/api/v1${path}`, convertFrontendToBackend(payload), { retry: false })
    );
  } catch (error) {
    throw toServiceError(error);
  }
}

/**
 * 幂等键由调用方生成（crypto.randomUUID），与台账服务 commandKey 同一风格。
 */
export function commandKey(): string {
  return crypto.randomUUID();
}

/**
 * 403 语义判断：范围缺失/权限不足/主体越权都按「无权」提示，不吞成空态。
 */
export function isOccupancyForbidden(error: unknown): boolean {
  return (
    error instanceof AssetOperationsError &&
    (error.code.startsWith('PARTY_SCOPE_') ||
      error.code === 'ASSET_OPS_PERMISSION_DENIED' ||
      error.code === 'ASSESSMENT_SCOPE_OPERATOR_FORBIDDEN' ||
      error.code === 'FORBIDDEN')
  );
}

// ==================== 归一化 ====================

export interface OperatorParty {
  id: string;
  name: string;
}

function normalizeOperatorParty(raw: RawRecord): OperatorParty {
  return {
    id: String(raw.id ?? ''),
    name: String(raw.name ?? ''),
  };
}

export interface AssessmentScopeUnitSnapshot {
  unitCode: string;
  name: string;
  projectId: string;
  usageType: string;
  isOperating: boolean;
  landArea: number;
  buildingArea: number;
  rentableArea: number;
  managedFrom: string;
  predecessorUnitIds: string[];
}

function normalizeUnitSnapshot(raw: RawRecord): AssessmentScopeUnitSnapshot {
  return {
    unitCode: String(raw.unit_code ?? ''),
    name: String(raw.name ?? ''),
    projectId: String(raw.project_id ?? ''),
    usageType: String(raw.usage_type ?? ''),
    isOperating: Boolean(raw.is_operating),
    landArea: requireDecimal(raw, 'land_area'),
    buildingArea: requireDecimal(raw, 'building_area'),
    rentableArea: requireDecimal(raw, 'rentable_area'),
    managedFrom: String(raw.managed_from ?? ''),
    predecessorUnitIds: Array.isArray(raw.predecessor_unit_ids)
      ? raw.predecessor_unit_ids.map(String)
      : [],
  };
}

export interface AssessmentScopeItem {
  assetUnitId: string;
  included: boolean;
  exclusionReason: string | null;
  unitSnapshot: AssessmentScopeUnitSnapshot;
}

function normalizeScopeItem(raw: RawRecord): AssessmentScopeItem {
  return {
    assetUnitId: requireString(raw, 'asset_unit_id'),
    included: requireBoolean(raw, 'included'),
    exclusionReason: optionalString(raw, 'exclusion_reason'),
    unitSnapshot: normalizeUnitSnapshot(
      requireRecord(raw.unit_snapshot, 'unit_snapshot')
    ),
  };
}

function requireRecord(value: unknown, field: string): RawRecord {
  if (value == null || typeof value !== 'object' || Array.isArray(value)) {
    throw new Error(`Invalid object field: ${field}`);
  }
  return value as RawRecord;
}

export interface AssessmentScopePendingItem {
  assetUnitId: string;
  reason: 'new_takeover' | 'boundary_uncertain';
  unitSnapshot: AssessmentScopeUnitSnapshot;
}

function normalizePendingItem(raw: RawRecord): AssessmentScopePendingItem {
  return {
    assetUnitId: requireString(raw, 'asset_unit_id'),
    reason: raw.reason === 'boundary_uncertain' ? 'boundary_uncertain' : 'new_takeover',
    unitSnapshot: normalizeUnitSnapshot(requireRecord(raw.unit_snapshot, 'unit_snapshot')),
  };
}

export interface AssessmentScopeVersionSummary {
  versionId: string;
  versionNumber: number | null;
  status: string;
  effectiveFromPeriod: string;
  activatedAt: string | null;
  version: number;
}

function normalizeVersionSummary(raw: RawRecord): AssessmentScopeVersionSummary {
  return {
    versionId: requireString(raw, 'version_id'),
    versionNumber: raw.version_number == null ? null : requireInt(raw, 'version_number'),
    status: String(raw.status ?? ''),
    effectiveFromPeriod: String(raw.effective_from_period ?? ''),
    activatedAt: optionalString(raw, 'activated_at'),
    version: requireInt(raw, 'version'),
  };
}

export interface OccupancySnapshotSummary {
  period: string;
  unitCount: number;
  rentedUnitCount: number;
  occupancyRate: number | null;
  rentableArea: number;
  rentedArea: number;
}

function normalizeOccupancySnapshot(raw: RawRecord): OccupancySnapshotSummary {
  return {
    period: String(raw.period ?? ''),
    unitCount: requireInt(raw, 'unit_count'),
    rentedUnitCount: requireInt(raw, 'rented_unit_count'),
    occupancyRate: requireNullableDecimal(raw, 'occupancy_rate'),
    rentableArea: requireDecimal(raw, 'rentable_area'),
    rentedArea: requireDecimal(raw, 'rented_area'),
  };
}

export interface AssessmentScopeOverview {
  operatorPartyId: string;
  year: number;
  scope: AssessmentScopeVersionSummary | null;
  items: AssessmentScopeItem[];
  pending: AssessmentScopePendingItem[];
  occupancy: OccupancySnapshotSummary | null;
}

function normalizeScopeOverview(raw: RawRecord): AssessmentScopeOverview {
  return {
    operatorPartyId: String(raw.operator_party_id ?? ''),
    year: requireInt(raw, 'year'),
    scope:
      raw.scope == null
        ? null
        : normalizeVersionSummary(requireRecord(raw.scope, 'scope')),
    items: requireRecordArray(raw, 'items').map(normalizeScopeItem),
    pending: requireRecordArray(raw, 'pending').map(normalizePendingItem),
    occupancy:
      raw.occupancy == null
        ? null
        : normalizeOccupancySnapshot(requireRecord(raw.occupancy, 'occupancy')),
  };
}

function requireRecordArray(record: RawRecord, field: string): RawRecord[] {
  const value = record[field];
  if (!Array.isArray(value)) {
    throw new Error(`Invalid array field: ${field}`);
  }
  return value.map(item => requireRecord(item, field));
}

export interface AssessmentScopeDraft {
  draftId: string;
  operatorPartyId: string;
  year: number;
  status: 'draft';
  effectiveFromPeriod: string;
  version: number;
  items: AssessmentScopeItem[];
  pending: AssessmentScopePendingItem[];
}

function normalizeScopeDraft(raw: RawRecord): AssessmentScopeDraft {
  return {
    draftId: requireString(raw, 'draft_id'),
    operatorPartyId: String(raw.operator_party_id ?? ''),
    year: requireInt(raw, 'year'),
    status: 'draft',
    effectiveFromPeriod: String(raw.effective_from_period ?? ''),
    version: requireInt(raw, 'version'),
    items: requireRecordArray(raw, 'items').map(normalizeScopeItem),
    pending: requireRecordArray(raw, 'pending').map(normalizePendingItem),
  };
}

export interface AssessmentScopePreview {
  previewToken: string;
  expiresAt: string;
  currentVersionNumber: number | null;
  currentIncludedCount: number;
  currentExcludedCount: number;
  newIncludedCount: number;
  newExcludedCount: number;
  pendingCount: number;
  occupancyPeriod: string;
  occupancyRateCurrent: number | null;
  occupancyRateNew: number | null;
  affectedPeriods: string[];
}

function normalizeScopePreview(raw: RawRecord): AssessmentScopePreview {
  return {
    previewToken: requireString(raw, 'preview_token'),
    expiresAt: String(raw.expires_at ?? ''),
    currentVersionNumber:
      raw.current_version_number == null ? null : requireInt(raw, 'current_version_number'),
    currentIncludedCount: requireInt(raw, 'current_included_count'),
    currentExcludedCount: requireInt(raw, 'current_excluded_count'),
    newIncludedCount: requireInt(raw, 'new_included_count'),
    newExcludedCount: requireInt(raw, 'new_excluded_count'),
    pendingCount: requireInt(raw, 'pending_count'),
    occupancyPeriod: String(raw.occupancy_period ?? ''),
    occupancyRateCurrent: requireDecimalFromAny(raw.occupancy_rate_current, 'occupancy_rate_current'),
    occupancyRateNew: requireDecimalFromAny(raw.occupancy_rate_new, 'occupancy_rate_new'),
    affectedPeriods: requireStringArray(raw, 'affected_periods'),
  };
}

export interface AssessmentScopeCommitResult {
  versionId: string;
  versionNumber: number;
  effectiveFromPeriod: string;
  activatedAt: string;
  idempotent: boolean;
}

function normalizeScopeCommitResult(raw: RawRecord): AssessmentScopeCommitResult {
  return {
    versionId: requireString(raw, 'version_id'),
    versionNumber: requireInt(raw, 'version_number'),
    effectiveFromPeriod: String(raw.effective_from_period ?? ''),
    activatedAt: String(raw.activated_at ?? ''),
    idempotent: requireBoolean(raw, 'idempotent'),
  };
}

export interface OccupancyReportTotals {
  unitCount: number;
  rentedUnitCount: number;
  occupancyRate: number | null;
  landArea: number;
  buildingArea: number;
  rentableArea: number;
  rentedArea: number;
}

function normalizeTotals(raw: RawRecord): OccupancyReportTotals {
  return {
    unitCount: requireInt(raw, 'unit_count'),
    rentedUnitCount: requireInt(raw, 'rented_unit_count'),
    occupancyRate: requireNullableDecimal(raw, 'occupancy_rate'),
    landArea: requireDecimal(raw, 'land_area'),
    buildingArea: requireDecimal(raw, 'building_area'),
    rentableArea: requireDecimal(raw, 'rentable_area'),
    rentedArea: requireDecimal(raw, 'rented_area'),
  };
}

export interface OccupancyReportLine {
  assetUnitId: string;
  ownerNameSnapshot: string;
  usageTypeSnapshot: string;
  projectNameSnapshot: string;
  addressSnapshot: string;
  landArea: number;
  buildingArea: number;
  rentableArea: number;
  rentedArea: number;
  unitCount: number;
  rentedUnitCount: number;
  rentalStatus: 'rented' | 'vacant' | 'non_rentable';
  terminalContractIds: string[];
}

function normalizeReportLine(raw: RawRecord): OccupancyReportLine {
  return {
    assetUnitId: requireString(raw, 'asset_unit_id'),
    ownerNameSnapshot: String(raw.owner_name_snapshot ?? ''),
    usageTypeSnapshot: String(raw.usage_type_snapshot ?? ''),
    projectNameSnapshot: String(raw.project_name_snapshot ?? ''),
    addressSnapshot: String(raw.address_snapshot ?? ''),
    landArea: requireDecimal(raw, 'land_area'),
    buildingArea: requireDecimal(raw, 'building_area'),
    rentableArea: requireDecimal(raw, 'rentable_area'),
    rentedArea: requireDecimal(raw, 'rented_area'),
    unitCount: requireInt(raw, 'unit_count'),
    rentedUnitCount: requireInt(raw, 'rented_unit_count'),
    rentalStatus:
      raw.rental_status === 'rented'
        ? 'rented'
        : raw.rental_status === 'non_rentable'
          ? 'non_rentable'
          : 'vacant',
    terminalContractIds: Array.isArray(raw.terminal_contract_ids)
      ? raw.terminal_contract_ids.map(String)
      : [],
  };
}

export interface OccupancyReportFieldChange {
  fieldName: string;
  previous: string | null;
  current: string | null;
}

function normalizeFieldChange(raw: RawRecord): OccupancyReportFieldChange {
  return {
    fieldName: String(raw.field_name ?? ''),
    previous: optionalString(raw, 'previous'),
    current: optionalString(raw, 'current'),
  };
}

export interface OccupancyReportPendingUnit {
  assetUnitId: string;
  reason: 'new_takeover' | 'boundary_uncertain';
}

function normalizePendingUnit(raw: RawRecord): OccupancyReportPendingUnit {
  return {
    assetUnitId: requireString(raw, 'asset_unit_id'),
    reason: raw.reason === 'boundary_uncertain' ? 'boundary_uncertain' : 'new_takeover',
  };
}

export interface OccupancyReportDraft {
  operatorPartyId: string;
  period: string;
  firstReport: boolean;
  scopeVersion: AssessmentScopeVersionSummary | null;
  totals: OccupancyReportTotals;
  lines: OccupancyReportLine[];
  pending: OccupancyReportPendingUnit[];
  changes: OccupancyReportFieldChange[];
  changeNote: string | null;
  canSubmit: boolean;
  gateReasons: string[];
}

function normalizeReportDraft(raw: RawRecord): OccupancyReportDraft {
  return {
    operatorPartyId: String(raw.operator_party_id ?? ''),
    period: String(raw.period ?? ''),
    firstReport: requireBoolean(raw, 'first_report'),
    scopeVersion:
      raw.scope_version == null
        ? null
        : normalizeVersionSummary(requireRecord(raw.scope_version, 'scope_version')),
    totals: normalizeTotals(requireRecord(raw.totals, 'totals')),
    lines: requireRecordArray(raw, 'lines').map(normalizeReportLine),
    pending: requireRecordArray(raw, 'pending').map(normalizePendingUnit),
    changes: requireRecordArray(raw, 'changes').map(normalizeFieldChange),
    changeNote: optionalString(raw, 'change_note'),
    canSubmit: requireBoolean(raw, 'can_submit'),
    gateReasons: requireStringArray(raw, 'gate_reasons'),
  };
}

export interface OccupancyReportNoteResult {
  operatorPartyId: string;
  period: string;
  changeNote: string | null;
  draftId: string;
  version: number;
}

function normalizeNoteResult(raw: RawRecord): OccupancyReportNoteResult {
  return {
    operatorPartyId: String(raw.operator_party_id ?? ''),
    period: String(raw.period ?? ''),
    changeNote: optionalString(raw, 'change_note'),
    draftId: requireString(raw, 'draft_id'),
    version: requireInt(raw, 'version'),
  };
}

export interface OccupancyReportSubmissionPreview {
  operatorPartyId: string;
  period: string;
  canSubmit: boolean;
  gateReasons: string[];
  mustHandle: OccupancyReportPendingUnit[];
  suggested: string[];
  normalizedNote: string | null;
  totals: OccupancyReportTotals;
  changes: OccupancyReportFieldChange[];
  firstReport: boolean;
  scopeVersion: AssessmentScopeVersionSummary;
  previewToken: string | null;
  expiresAt: string | null;
}

function normalizeSubmissionPreview(raw: RawRecord): OccupancyReportSubmissionPreview {
  return {
    operatorPartyId: String(raw.operator_party_id ?? ''),
    period: String(raw.period ?? ''),
    canSubmit: requireBoolean(raw, 'can_submit'),
    gateReasons: requireStringArray(raw, 'gate_reasons'),
    mustHandle: requireRecordArray(raw, 'must_handle').map(normalizePendingUnit),
    suggested: requireStringArray(raw, 'suggested'),
    normalizedNote: optionalString(raw, 'normalized_note'),
    totals: normalizeTotals(requireRecord(raw.totals, 'totals')),
    changes: requireRecordArray(raw, 'changes').map(normalizeFieldChange),
    firstReport: requireBoolean(raw, 'first_report'),
    scopeVersion: normalizeVersionSummary(requireRecord(raw.scope_version, 'scope_version')),
    previewToken: optionalString(raw, 'preview_token'),
    expiresAt: optionalString(raw, 'expires_at'),
  };
}

export interface OccupancyReportSubmitResult {
  reportId: string;
  status: 'submitted';
  totals: OccupancyReportTotals;
  lineCount: number;
  idempotent: boolean;
}

function normalizeSubmitResult(raw: RawRecord): OccupancyReportSubmitResult {
  return {
    reportId: requireString(raw, 'report_id'),
    status: 'submitted',
    totals: normalizeTotals(requireRecord(raw.totals, 'totals')),
    lineCount: requireInt(raw, 'line_count'),
    idempotent: requireBoolean(raw, 'idempotent'),
  };
}

export interface OccupancyReportProjectCounts {
  projectCount: number;
  operatingProjectCount: number;
  nonOperatingProjectCount: number;
}

function normalizeProjectCounts(raw: RawRecord): OccupancyReportProjectCounts {
  return {
    projectCount: requireInt(raw, 'project_count'),
    operatingProjectCount: requireInt(raw, 'operating_project_count'),
    nonOperatingProjectCount: requireInt(raw, 'non_operating_project_count'),
  };
}

export type OccupancyReportDiffKind = 'changed' | 'unit_left_scope' | 'unit_entered_scope';

export interface OccupancyReportUnitDiff {
  assetUnitId: string;
  kind: OccupancyReportDiffKind;
  changes: OccupancyReportFieldChange[];
}

function normalizeUnitDiff(raw: RawRecord): OccupancyReportUnitDiff {
  return {
    assetUnitId: requireString(raw, 'asset_unit_id'),
    kind:
      raw.kind === 'unit_left_scope'
        ? 'unit_left_scope'
        : raw.kind === 'unit_entered_scope'
          ? 'unit_entered_scope'
          : 'changed',
    changes: requireRecordArray(raw, 'changes').map(normalizeFieldChange),
  };
}

export interface OccupancyReportSnapshot {
  reportId: string;
  operatorPartyId: string;
  period: string;
  status: 'submitted' | 'withdrawn';
  scopeVersion: AssessmentScopeVersionSummary;
  changeNote: string | null;
  submittedAt: string;
  withdrawnAt: string | null;
  withdrawReason: string | null;
  predecessorReportId: string | null;
  totals: OccupancyReportTotals;
  projectCounts: OccupancyReportProjectCounts;
  lines: OccupancyReportLine[];
  differences: OccupancyReportUnitDiff[];
}

function normalizeSnapshot(raw: RawRecord): OccupancyReportSnapshot {
  return {
    reportId: requireString(raw, 'report_id'),
    operatorPartyId: String(raw.operator_party_id ?? ''),
    period: String(raw.period ?? ''),
    status: raw.status === 'withdrawn' ? 'withdrawn' : 'submitted',
    scopeVersion: normalizeVersionSummary(requireRecord(raw.scope_version, 'scope_version')),
    changeNote: optionalString(raw, 'change_note'),
    submittedAt: String(raw.submitted_at ?? ''),
    withdrawnAt: optionalString(raw, 'withdrawn_at'),
    withdrawReason: optionalString(raw, 'withdraw_reason'),
    predecessorReportId: optionalString(raw, 'predecessor_report_id'),
    totals: normalizeTotals(requireRecord(raw.totals, 'totals')),
    projectCounts: normalizeProjectCounts(requireRecord(raw.project_counts, 'project_counts')),
    lines: requireRecordArray(raw, 'lines').map(normalizeReportLine),
    differences: requireRecordArray(raw, 'differences').map(normalizeUnitDiff),
  };
}

export interface OccupancyReportWithdrawalPreview {
  reportId: string;
  period: string;
  submittedAt: string;
  successorDraftRule: string;
  previewToken: string;
  expiresAt: string;
  reportVersion: number;
}

function normalizeWithdrawalPreview(raw: RawRecord): OccupancyReportWithdrawalPreview {
  return {
    reportId: requireString(raw, 'report_id'),
    period: String(raw.period ?? ''),
    submittedAt: String(raw.submitted_at ?? ''),
    successorDraftRule: String(raw.successor_draft_rule ?? ''),
    previewToken: requireString(raw, 'preview_token'),
    expiresAt: String(raw.expires_at ?? ''),
    reportVersion: requireInt(raw, 'report_version'),
  };
}

export interface OccupancyReportWithdrawResult {
  reportId: string;
  status: 'withdrawn';
  withdrawnAt: string;
  successorDraftId: string;
  idempotent: boolean;
}

function normalizeWithdrawResult(raw: RawRecord): OccupancyReportWithdrawResult {
  return {
    reportId: requireString(raw, 'report_id'),
    status: 'withdrawn',
    withdrawnAt: String(raw.withdrawn_at ?? ''),
    successorDraftId: requireString(raw, 'successor_draft_id'),
    idempotent: requireBoolean(raw, 'idempotent'),
  };
}

export interface OccupancyReportExportStart {
  taskId: string;
  status: string;
}

function normalizeExportStart(raw: RawRecord): OccupancyReportExportStart {
  return {
    taskId: requireString(raw, 'task_id'),
    status: String(raw.status ?? ''),
  };
}

export interface OccupancyReportExportFile {
  fileName: string;
  contentBase64: string;
}

function normalizeExportFile(raw: RawRecord): OccupancyReportExportFile {
  const resultData = requireRecord(raw.result_data, 'result_data');
  return {
    fileName: String(resultData.file_name ?? ''),
    contentBase64: String(resultData.content_base64 ?? ''),
  };
}

// ==================== 服务入口 ====================

export interface ScopeDecisionInput {
  assetUnitId: string;
  included: boolean;
  exclusionReason?: string | null;
}

export const occupancyReportService = {
  /** 运营主体选择器数据源：仅 legal_entity 且 active。 */
  listOperatorParties: async (): Promise<OperatorParty[]> => {
    try {
      const result = await apiClient.get<unknown>('/api/v1/parties', {
        cache: false,
        params: { party_type: 'legal_entity', status: 'active' },
      });
      if (!result.success || result.data == null) {
        throw new AssetOperationsError(
          typeof result.error === 'string' ? result.error : '获取运营主体列表失败，请重试',
          'UNKNOWN_ERROR'
        );
      }
      const normalized = convertBackendToFrontend<unknown>(result.data);
      const items = Array.isArray(normalized)
        ? normalized
        : ((normalized as RawRecord).items as unknown[] | undefined);
      if (!Array.isArray(items)) {
        throw new AssetOperationsError('运营主体响应格式异常，请重试', 'INVALID_RESPONSE_DATA');
      }
      return items.map(item => normalizeOperatorParty(requireRecord(item, 'items')));
    } catch (error) {
      throw toServiceError(error);
    }
  },

  getAssessmentScope: async (year: number, operatorPartyId: string): Promise<AssessmentScopeOverview> =>
    normalizeScopeOverview(
      await get<RawRecord>(`/assessment-scopes/${year}`, {
        operator_party_id: operatorPartyId,
      })
    ),

  createAssessmentScopeDraft: async (
    year: number,
    payload: { operatorPartyId: string; source: 'current' | 'previous_year' }
  ): Promise<AssessmentScopeDraft> =>
    normalizeScopeDraft(
      await post<RawRecord>(`/assessment-scopes/${year}/drafts`, {
        operator_party_id: payload.operatorPartyId,
        source: payload.source,
      })
    ),

  getAssessmentScopeDraft: async (draftId: string): Promise<AssessmentScopeDraft> =>
    normalizeScopeDraft(
      await get<RawRecord>(`/assessment-scope-drafts/${encodeURIComponent(draftId)}`)
    ),

  updateAssessmentScopeDraft: async (
    draftId: string,
    decisions: ScopeDecisionInput[],
    expectedVersion: number
  ): Promise<AssessmentScopeDraft> =>
    normalizeScopeDraft(
      await put<RawRecord>(`/assessment-scope-drafts/${encodeURIComponent(draftId)}`, {
        expected_version: expectedVersion,
        decisions: decisions.map(decision => ({
          asset_unit_id: decision.assetUnitId,
          included: decision.included,
          ...(decision.included ? {} : { exclusion_reason: decision.exclusionReason ?? '' }),
        })),
      })
    ),

  previewAssessmentScopeDraft: async (draftId: string): Promise<AssessmentScopePreview> =>
    normalizeScopePreview(
      await post<RawRecord>(`/assessment-scope-drafts/${encodeURIComponent(draftId)}/preview`)
    ),

  commitAssessmentScopeDraft: async (
    draftId: string,
    payload: { previewToken: string; expectedVersion: number; effectiveFromPeriod: string },
    key: string
  ): Promise<AssessmentScopeCommitResult> =>
    normalizeScopeCommitResult(
      await post<RawRecord>(
        `/assessment-scope-drafts/${encodeURIComponent(draftId)}/commit`,
        {
          preview_token: payload.previewToken,
          expected_version: payload.expectedVersion,
          effective_from_period: payload.effectiveFromPeriod,
        },
        { key }
      )
    ),

  getOccupancyReportDraft: async (
    period: string,
    operatorPartyId: string
  ): Promise<OccupancyReportDraft> =>
    normalizeReportDraft(
      await get<RawRecord>(`/occupancy-reports/${encodeURIComponent(period)}/draft`, {
        operator_party_id: operatorPartyId,
      })
    ),

  saveOccupancyReportNote: async (
    period: string,
    payload: { operatorPartyId: string; changeNote: string | null }
  ): Promise<OccupancyReportNoteResult> =>
    normalizeNoteResult(
      await put<RawRecord>(`/occupancy-reports/${encodeURIComponent(period)}/draft-note`, {
        operator_party_id: payload.operatorPartyId,
        change_note: payload.changeNote,
      })
    ),

  previewOccupancyReportSubmission: async (
    period: string,
    operatorPartyId: string
  ): Promise<OccupancyReportSubmissionPreview> =>
    normalizeSubmissionPreview(
      await post<RawRecord>(
        `/occupancy-reports/${encodeURIComponent(period)}/submission-preview`,
        undefined,
        { params: { operator_party_id: operatorPartyId } }
      )
    ),

  submitOccupancyReport: async (
    period: string,
    operatorPartyId: string,
    payload: { previewToken: string; expectedScopeVersionId: string; expectedScopeVersion: number },
    key: string
  ): Promise<OccupancyReportSubmitResult> =>
    normalizeSubmitResult(
      await post<RawRecord>(
        `/occupancy-reports/${encodeURIComponent(period)}/submissions`,
        {
          preview_token: payload.previewToken,
          expected_scope_version_id: payload.expectedScopeVersionId,
          expected_scope_version: payload.expectedScopeVersion,
        },
        { key, params: { operator_party_id: operatorPartyId } }
      )
    ),

  getOccupancyReportSnapshot: async (reportId: string): Promise<OccupancyReportSnapshot> =>
    normalizeSnapshot(
      await get<RawRecord>(`/occupancy-reports/${encodeURIComponent(reportId)}`)
    ),

  previewOccupancyReportWithdrawal: async (
    reportId: string
  ): Promise<OccupancyReportWithdrawalPreview> =>
    normalizeWithdrawalPreview(
      await post<RawRecord>(`/occupancy-reports/${encodeURIComponent(reportId)}/withdrawal-preview`)
    ),

  withdrawOccupancyReport: async (
    reportId: string,
    payload: { previewToken: string; expectedVersion: number; withdrawReason: string },
    key: string
  ): Promise<OccupancyReportWithdrawResult> =>
    normalizeWithdrawResult(
      await post<RawRecord>(
        `/occupancy-reports/${encodeURIComponent(reportId)}/withdrawal`,
        {
          preview_token: payload.previewToken,
          expected_version: payload.expectedVersion,
          withdraw_reason: payload.withdrawReason,
        },
        { key }
      )
    ),

  exportOccupancyReport: async (reportId: string): Promise<OccupancyReportExportStart> =>
    normalizeExportStart(
      await post<RawRecord>(`/occupancy-reports/${encodeURIComponent(reportId)}/exports`)
    ),

  /** 导出任务结果：经既有 tasks 端点取 base64 CSV。 */
  getExportTaskResult: async (taskId: string): Promise<OccupancyReportExportFile> => {
    const task = await get<RawRecord>(`/tasks/${encodeURIComponent(taskId)}`);
    return normalizeExportFile(task);
  },
};
