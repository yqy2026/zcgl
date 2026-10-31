import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, cleanup, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import dayjs from 'dayjs';

import { OccupancyReportsPage } from '../OccupancyReportsPage';
import {
  occupancyReportService,
  AssetOperationsError,
} from '@/services/occupancyReportService';
import type {
  OccupancyReportDraft,
  OccupancyReportLine,
} from '@/services/occupancyReportService';

vi.mock(import('@/services/occupancyReportService'), async importOriginal => {
  const actual = await importOriginal<typeof import('@/services/occupancyReportService')>();
  return {
    ...actual,
    occupancyReportService: {
      listOperatorParties: vi.fn(),
      getAssessmentScope: vi.fn(),
      createAssessmentScopeDraft: vi.fn(),
      getAssessmentScopeDraft: vi.fn(),
      updateAssessmentScopeDraft: vi.fn(),
      previewAssessmentScopeDraft: vi.fn(),
      commitAssessmentScopeDraft: vi.fn(),
      getOccupancyReportDraft: vi.fn(),
      saveOccupancyReportNote: vi.fn(),
      previewOccupancyReportSubmission: vi.fn(),
      submitOccupancyReport: vi.fn(),
      getOccupancyReportSnapshot: vi.fn(),
      previewOccupancyReportWithdrawal: vi.fn(),
      withdrawOccupancyReport: vi.fn(),
      exportOccupancyReport: vi.fn(),
      getExportTaskResult: vi.fn(),
    },
  };
});

// 与 LedgersPage.test 一致：页面测试跳过能力守卫的登录上下文。
vi.mock('@/components/System/CapabilityGuard', () => ({
  default: ({ children }: { children: React.ReactNode }) => children,
}));

const mockedService = vi.mocked(occupancyReportService);

function makeLine(overrides: Partial<OccupancyReportLine> = {}): OccupancyReportLine {
  return {
    assetUnitId: 'unit-1',
    ownerNameSnapshot: '业主甲',
    usageTypeSnapshot: 'commercial',
    projectNameSnapshot: '项目一',
    addressSnapshot: '地址 1 号',
    landArea: 300,
    buildingArea: 200,
    rentableArea: 150,
    rentedArea: 150,
    unitCount: 1,
    rentedUnitCount: 1,
    rentalStatus: 'rented',
    terminalContractIds: ['tc-1'],
    ...overrides,
  };
}

function makeDraft(overrides: Partial<OccupancyReportDraft> = {}): OccupancyReportDraft {
  return {
    operatorPartyId: 'op-1',
    period: dayjs().startOf('month').subtract(1, 'month').format('YYYY-MM'),
    firstReport: false,
    scopeVersion: {
      versionId: 'sv-1',
      versionNumber: 1,
      status: 'active',
      effectiveFromPeriod: '2026-01',
      activatedAt: null,
      version: 1,
    },
    totals: {
      unitCount: 1,
      rentedUnitCount: 1,
      occupancyRate: 0.85,
      landArea: 1000,
      buildingArea: 800,
      rentableArea: 500,
      rentedArea: 425,
    },
    lines: [makeLine()],
    pending: [],
    changes: [],
    changeNote: null,
    canSubmit: true,
    gateReasons: [],
    ...overrides,
  };
}

function renderPage(): void {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={['/asset-operations/occupancy-reports']}>
        <OccupancyReportsPage />
      </MemoryRouter>
    </QueryClientProvider>
  );
}

beforeEach(() => {
  Object.values(mockedService).forEach(mock => vi.mocked(mock).mockReset());
  mockedService.listOperatorParties.mockResolvedValue([{ id: 'op-1', name: '城投公司' }]);
  mockedService.getAssessmentScope.mockResolvedValue({
    operatorPartyId: 'op-1',
    year: dayjs().year(),
    scope: null,
    items: [],
    pending: [],
    occupancy: null,
  });
});

afterEach(() => {
  cleanup();
});

describe('OccupancyReportsPage', () => {
  it('renders the monthly draft totals and line rows after loading', async () => {
    mockedService.getOccupancyReportDraft.mockResolvedValue(makeDraft());

    renderPage();

    expect(await screen.findByText('地址 1 号')).toBeTruthy();
    expect(screen.getByText('85.0%')).toBeTruthy();
    expect(screen.getByText('业主甲')).toBeTruthy();
    expect(screen.getByRole('button', { name: '提交报送' })).toBeEnabled();
    expect(mockedService.getOccupancyReportDraft).toHaveBeenCalledWith(
      dayjs().startOf('month').subtract(1, 'month').format('YYYY-MM'),
      'op-1'
    );
  });

  it('shows the forbidden alert instead of swallowing 403 into an empty state', async () => {
    mockedService.getOccupancyReportDraft.mockRejectedValue(
      new AssetOperationsError('无有效范围', 'PARTY_SCOPE_MISSING')
    );

    renderPage();

    expect(
      await screen.findByText('当前账号没有相关数据范围或权限，请联系管理员。')
    ).toBeTruthy();
    expect(screen.queryByText('当月暂无纳入考核范围的宗地明细。')).toBeNull();
  });

  it('disables submission when the draft reports canSubmit=false', async () => {
    mockedService.getOccupancyReportDraft.mockResolvedValue(
      makeDraft({ canSubmit: false, gateReasons: ['存在待确认宗地'] })
    );

    renderPage();

    expect(await screen.findByText('地址 1 号')).toBeTruthy();
    expect(screen.getByText('暂不满足提交条件：存在待确认宗地')).toBeTruthy();
    expect(screen.getByRole('button', { name: '提交报送' })).toBeDisabled();
  });

  it('shows the explicit empty state when the draft has no lines or pending units', async () => {
    mockedService.getOccupancyReportDraft.mockResolvedValue(
      makeDraft({ lines: [], pending: [] })
    );

    renderPage();

    expect(await screen.findByText('当月暂无纳入考核范围的宗地明细。')).toBeTruthy();
  });

  it('recovers the operator selection from the operator_party_id deep link', async () => {
    mockedService.getOccupancyReportDraft.mockResolvedValue(makeDraft());
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });

    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter
          initialEntries={['/asset-operations/occupancy-reports?operator_party_id=op-1']}
        >
          <OccupancyReportsPage />
        </MemoryRouter>
      </QueryClientProvider>
    );

    await waitFor(() => {
      expect(mockedService.getOccupancyReportDraft).toHaveBeenCalledWith(
        expect.any(String),
        'op-1'
      );
    });
    expect(mockedService.listOperatorParties).toHaveBeenCalled();
  });
});
