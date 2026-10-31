import { beforeEach, expect, it, vi } from 'vitest';
import { AxiosError, AxiosHeaders } from 'axios';
import { apiClient } from '@/api/client';
import {
  occupancyReportService,
  isOccupancyForbidden,
  AssetOperationsError,
  AssessmentScopeDraftExistsError,
} from '../occupancyReportService';

vi.mock('@/api/client', () => ({ apiClient: { get: vi.fn(), post: vi.fn(), put: vi.fn() } }));

beforeEach(() => vi.clearAllMocks());

function axiosRejection(status: number, payload: Record<string, unknown>) {
  return new AxiosError('Request failed', 'ERR_BAD_REQUEST', undefined, undefined, {
    status,
    statusText: status === 403 ? 'Forbidden' : 'Conflict',
    headers: {},
    config: { headers: new AxiosHeaders() },
    data: { success: false, error: payload },
  });
}

it('converts Decimal strings into numbers for the draft totals and lines', async () => {
  vi.mocked(apiClient.get).mockResolvedValueOnce({
    success: true,
    data: {
      operator_party_id: 'op-1',
      period: '2026-10',
      first_report: false,
      scope_version: null,
      totals: {
        unit_count: 2,
        rented_unit_count: 1,
        occupancy_rate: '0.85',
        land_area: '1000.50',
        building_area: '800.25',
        rentable_area: '500.10',
        rented_area: '425.00',
      },
      lines: [
        {
          asset_unit_id: 'unit-1',
          owner_name_snapshot: '业主甲',
          usage_type_snapshot: 'commercial',
          project_name_snapshot: '项目一',
          address_snapshot: '地址 1 号',
          land_area: '300.00',
          building_area: '200.00',
          rentable_area: '150.00',
          rented_area: '150.00',
          unit_count: 1,
          rented_unit_count: 1,
          rental_status: 'rented',
          terminal_contract_ids: ['tc-1'],
        },
      ],
      pending: [],
      changes: [{ field_name: 'rented_area', previous: '100.00', current: '150.00' }],
      change_note: null,
      can_submit: true,
      gate_reasons: [],
    },
  });

  const draft = await occupancyReportService.getOccupancyReportDraft('2026-10', 'op-1');

  expect(draft.totals.occupancyRate).toBe(0.85);
  expect(draft.totals.landArea).toBe(1000.5);
  expect(draft.totals.rentableArea).toBe(500.1);
  expect(draft.lines[0]?.rentedArea).toBe(150);
  expect(draft.lines[0]?.rentalStatus).toBe('rented');
  expect(draft.changes[0]?.previous).toBe('100.00');
  expect(draft.canSubmit).toBe(true);
  expect(apiClient.get).toHaveBeenCalledWith(
    '/api/v1/occupancy-reports/2026-10/draft',
    expect.objectContaining({ cache: false, params: { operator_party_id: 'op-1' } })
  );
});

it('treats an explicitly null occupancy rate as null but throws on an unparseable one', async () => {
  vi.mocked(apiClient.get).mockResolvedValueOnce({
    success: true,
    data: {
      operator_party_id: 'op-1',
      period: '2026-10',
      first_report: true,
      scope_version: null,
      totals: {
        unit_count: 1,
        rented_unit_count: 0,
        occupancy_rate: null,
        land_area: '0',
        building_area: '0',
        rentable_area: '0',
        rented_area: '0',
      },
      lines: [],
      pending: [],
      changes: [],
      change_note: null,
      can_submit: false,
      gate_reasons: [],
    },
  });

  const draft = await occupancyReportService.getOccupancyReportDraft('2026-10', 'op-1');
  expect(draft.totals.occupancyRate).toBeNull();

  vi.mocked(apiClient.get).mockResolvedValueOnce({
    success: true,
    data: {
      operator_party_id: 'op-1',
      period: '2026-10',
      first_report: true,
      scope_version: null,
      totals: {
        unit_count: 1,
        rented_unit_count: 0,
        occupancy_rate: 'not-a-number',
        land_area: '0',
        building_area: '0',
        rentable_area: '0',
        rented_area: '0',
      },
      lines: [],
      pending: [],
      changes: [],
      change_note: null,
      can_submit: false,
      gate_reasons: [],
    },
  });

  await expect(
    occupancyReportService.getOccupancyReportDraft('2026-10', 'op-1')
  ).rejects.toThrow('Invalid Decimal field: occupancy_rate');
});

it('normalizes preview occupancy rates that bypass the shared decimal list', async () => {
  vi.mocked(apiClient.post).mockResolvedValueOnce({
    success: true,
    data: {
      preview_token: 'tok-1',
      expires_at: '2026-11-01T00:00:00Z',
      current_version_number: null,
      current_included_count: 3,
      current_excluded_count: 1,
      new_included_count: 4,
      new_excluded_count: 0,
      pending_count: 0,
      occupancy_period: '2026-10',
      occupancy_rate_current: '0.80',
      occupancy_rate_new: '0.90',
      affected_periods: ['2026-10', '2026-11'],
    },
  });

  const preview = await occupancyReportService.previewAssessmentScopeDraft('draft-1');

  expect(preview.occupancyRateCurrent).toBe(0.8);
  expect(preview.occupancyRateNew).toBe(0.9);
  expect(preview.currentVersionNumber).toBeNull();
  expect(preview.affectedPeriods).toEqual(['2026-10', '2026-11']);
});

it('passes the Idempotency-Key header and snake_case body on submit', async () => {
  vi.mocked(apiClient.post).mockResolvedValueOnce({
    success: true,
    data: {
      report_id: 'report-1',
      operator_party_id: 'op-1',
      period: '2026-10',
      status: 'submitted',
      scope_version_id: 'sv-1',
      submitted_at: '2026-11-01T00:00:00Z',
      totals: {
        unit_count: 1,
        rented_unit_count: 1,
        occupancy_rate: null,
        land_area: '0',
        building_area: '0',
        rentable_area: '0',
        rented_area: '0',
      },
      line_count: 1,
      idempotent: false,
    },
  });

  const result = await occupancyReportService.submitOccupancyReport(
    '2026-10',
    'op-1',
    {
      previewToken: 'tok-1',
      expectedScopeVersionId: 'sv-1',
      expectedScopeVersion: 2,
    },
    'request-1'
  );

  expect(result.reportId).toBe('report-1');
  expect(apiClient.post).toHaveBeenCalledWith(
    '/api/v1/occupancy-reports/2026-10/submissions',
    {
      preview_token: 'tok-1',
      expected_scope_version_id: 'sv-1',
      expected_scope_version: 2,
    },
    expect.objectContaining({
      headers: { 'Idempotency-Key': 'request-1' },
      retry: false,
      params: { operator_party_id: 'op-1' },
    })
  );
});

it('maps a rejected HTTP 403 into a forbidden AssetOperationsError', async () => {
  vi.mocked(apiClient.get).mockRejectedValueOnce(
    axiosRejection(403, { code: 'PARTY_SCOPE_MISSING', message: '无有效范围' })
  );

  const error: unknown = await occupancyReportService
    .getOccupancyReportDraft('2026-10', 'op-1')
    .catch(value => value);

  expect(error).toBeInstanceOf(AssetOperationsError);
  expect(error).toMatchObject({ code: 'PARTY_SCOPE_MISSING' });
  expect(isOccupancyForbidden(error)).toBe(true);
});

it('passes backend business error codes through the failure envelope untouched', async () => {
  vi.mocked(apiClient.post).mockResolvedValueOnce({
    success: false,
    error: '该统计月已报送',
    rawResponse: {
      data: { error: { code: 'OCCUPANCY_REPORT_ALREADY_SUBMITTED', message: '该统计月已报送' } },
    },
  });

  await expect(
    occupancyReportService.previewOccupancyReportSubmission('2026-10', 'op-1')
  ).rejects.toMatchObject({ code: 'OCCUPANCY_REPORT_ALREADY_SUBMITTED' });
});

it('surfaces the existing draft id on ASSESSMENT_SCOPE_DRAFT_EXISTS', async () => {
  vi.mocked(apiClient.post).mockRejectedValueOnce(
    axiosRejection(409, {
      code: 'ASSESSMENT_SCOPE_DRAFT_EXISTS',
      message: '该年度已存在未保存的考核范围草稿',
      details: { draft_id: 'draft-9' },
    })
  );

  const error: unknown = await occupancyReportService
    .createAssessmentScopeDraft(2026, { operatorPartyId: 'op-1', source: 'current' })
    .catch(value => value);

  expect(error).toBeInstanceOf(AssessmentScopeDraftExistsError);
  expect(error).toMatchObject({ code: 'ASSESSMENT_SCOPE_DRAFT_EXISTS', draftId: 'draft-9' });
  expect(isOccupancyForbidden(error)).toBe(false);
});

it('lists active legal-entity operator parties from the parties endpoint', async () => {
  vi.mocked(apiClient.get).mockResolvedValueOnce({
    success: true,
    data: [
      { id: 'op-1', name: '城投公司', party_type: 'legal_entity', status: 'active' },
      { id: 'op-2', name: '文旅集团' },
    ],
  });

  const parties = await occupancyReportService.listOperatorParties();

  expect(parties).toEqual([
    { id: 'op-1', name: '城投公司' },
    { id: 'op-2', name: '文旅集团' },
  ]);
  expect(apiClient.get).toHaveBeenCalledWith(
    '/api/v1/parties',
    expect.objectContaining({ params: { party_type: 'legal_entity', status: 'active' } })
  );
});

it('serializes scope decisions without exclusion reasons for included units', async () => {
  vi.mocked(apiClient.put).mockResolvedValueOnce({
    success: true,
    data: {
      draft_id: 'draft-1',
      operator_party_id: 'op-1',
      year: 2026,
      status: 'draft',
      effective_from_period: '2026-10',
      version: 2,
      items: [],
      pending: [],
    },
  });

  await occupancyReportService.updateAssessmentScopeDraft(
    'draft-1',
    [
      { assetUnitId: 'unit-1', included: true },
      { assetUnitId: 'unit-2', included: false, exclusionReason: ' 非经营 ' },
    ],
    1
  );

  expect(apiClient.put).toHaveBeenCalledWith(
    '/api/v1/assessment-scope-drafts/draft-1',
    {
      expected_version: 1,
      decisions: [
        { asset_unit_id: 'unit-1', included: true },
        { asset_unit_id: 'unit-2', included: false, exclusion_reason: ' 非经营 ' },
      ],
    },
    expect.objectContaining({ retry: false })
  );
});

it('reads the export csv payload from the task result', async () => {
  vi.mocked(apiClient.get).mockResolvedValueOnce({
    success: true,
    data: {
      id: 'task-1',
      status: 'completed',
      result_data: {
        file_name: 'occupancy-report-2026-10.csv',
        content_base64: 'Y29sdW1uMQ==',
      },
    },
  });

  const file = await occupancyReportService.getExportTaskResult('task-1');

  expect(file.fileName).toBe('occupancy-report-2026-10.csv');
  expect(file.contentBase64).toBe('Y29sdW1uMQ==');
});
