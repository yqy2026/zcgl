import { expect, it, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom';
import MonthlyPage from '@/pages/AssetOperations/MonthlyPage';
import { monthlyWorkbenchService } from '@/services/monthlyWorkbenchService';
import { occupancyReportService } from '@/services/occupancyReportService';
import { AssetOperationsError } from '@/services/assetOperationsService';

vi.mock('@/services/monthlyWorkbenchService', () => ({
  monthlyWorkbenchService: { overview: vi.fn() },
}));
vi.mock('@/services/occupancyReportService', () => ({
  occupancyReportService: { listOperatorParties: vi.fn() },
}));

const partiesQuery = vi.mocked(occupancyReportService.listOperatorParties);
const overviewQuery = vi.mocked(monthlyWorkbenchService.overview);

function view() {
  return {
    month: '2026-11',
    today: '2026-11-17',
    daysLeftInMonth: 13,
    progress: { total: 5, done: 1 },
    rentPayments: {
      period: '2026-11',
      subtitle: '月付 25 日前 · 季付 15 日前',
      pendingCount: 2,
      pendingAmount: 120000,
      doneCount: 1,
      doneAmount: 60000,
      items: [
        {
          contractKind: 'upstream' as const,
          contractId: 'u1',
          contractNumber: 'CZ-2026-001',
          contractName: '一德路后座',
          counterpartyName: '国资物业',
          unitLabel: null,
          period: '2026-10',
          ledgerEntryId: 'e2',
          dueAmount: 60000,
          paidAmount: 0,
          remainingAmount: 60000,
          dueDate: '2026-10-25',
          daysOverdue: 23,
          status: 'overdue' as const,
          recordTypeHint: 'payment' as const,
        },
      ],
    },
    rentCollections: {
      period: '2026-11',
      subtitle: '转租单元 · 本公司收取',
      pendingCount: 1,
      pendingAmount: 5000,
      doneCount: 0,
      doneAmount: 0,
      items: [],
    },
    managementFees: {
      period: '2026-10',
      items: [
        {
          ownerPartyId: 'owner-2',
          ownerPartyName: '城投资产',
          statementId: 'st-1',
          statementNumber: 'DF-2026-10-01',
          status: 'collecting' as const,
          baseAmount: 50000,
          feeAmount: 3000,
          receivedLineCount: 1,
          lineCount: 2,
        },
      ],
    },
    occupancyReport: {
      operatorPartyId: 'op-1',
      period: '2026-11',
      status: 'draft' as const,
      unavailableReason: null,
      unitCount: 10,
      rentedUnitCount: 7,
      occupancyRate: 0.7,
      rateDelta: 0.05,
      gateReasons: ['change_note_required'],
      canSubmit: false,
    },
    expiredUpstream: [
      {
        contractId: 'u3',
        contractNumber: 'CZ-2025-003',
        name: '江南苑车位',
        contractType: 'lease' as const,
        endDate: '2026-10-31',
        daysPast: 17,
        unitCount: 12,
        activeTerminalCount: 6,
        hasPendingRenewal: false,
      },
    ],
    expiringUpstream: [
      {
        contractId: 'u4',
        contractNumber: 'CZ-2026-009',
        name: '北京路249号',
        contractType: 'lease' as const,
        ownerPartyName: '越秀城建',
        endDate: '2027-01-15',
        daysLeft: 59,
        overrunTerminalCount: 1,
      },
    ],
    archiveGaps: [
      { documentType: 'terminal_contract', label: '终端合同', missing: 3 },
    ],
    unlinkedUnitCount: 2,
    depositsPending: [
      {
        depositId: 'd1',
        contractKind: 'terminal' as const,
        contractId: 't1',
        contractNumber: 'ZZ-1',
        counterpartyName: '凤凰创意',
        collector: 'operator' as const,
        status: 'refundable_unreturned',
        direction: 'refundable',
        agreedAmount: 16000,
        heldAmount: 16000,
        outstandingAmount: 16000,
      },
    ],
    pendingScopeUnits: [
      {
        assetUnitId: 'unit-9',
        unitCode: 'A39',
        unitName: '海珠工业园 A39 栋',
        reason: 'new_takeover' as const,
      },
    ],
  };
}

beforeEach(() => {
  vi.clearAllMocks();
  partiesQuery.mockResolvedValue([{ id: 'op-1', name: '运营主体' }]);
});

function LocationProbe(): React.ReactElement {
  const location = useLocation();
  return (
    <div data-testid="location">
      {location.pathname}
      {location.search}
    </div>
  );
}

function show(initialEntry = '/asset-operations/monthly') {
  return render(
    <MemoryRouter initialEntries={[initialEntry]}>
      <QueryClientProvider
        client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}
      >
        <Routes>
          <Route path="/asset-operations/monthly" element={<MonthlyPage />} />
          <Route path="/asset-operations/ledgers" element={<LocationProbe />} />
        </Routes>
      </QueryClientProvider>
    </MemoryRouter>
  );
}

it('renders headline, four cards and anytime sections from the overview', async () => {
  overviewQuery.mockResolvedValue(view());
  show();
  expect(await screen.findByText('本月还有 4 件没做完')).toBeTruthy();
  // 支付卡：逾期行排前并显示逾期天数
  expect(screen.getByText(/已逾期 23 天/)).toBeTruthy();
  // 收租卡空态
  expect(screen.getByText('本月终端租金已全部到账')).toBeTruthy();
  // 管理费卡：收租中 + 户数
  expect(screen.getByText('产权方已收 1/2 户 · 月底仍未收的顺延下月')).toBeTruthy();
  // 报送卡：出租率与门槛
  expect(screen.getByText('70.0%')).toBeTruthy();
  expect(screen.getByText(/较上月 \+5\.0 个百分点/)).toBeTruthy();
  expect(screen.getByText(/变动说明未填/)).toBeTruthy();
  // 随时处理
  expect(screen.getByText('上游合同已到期，尚未续签或退出')).toBeTruthy();
  expect(screen.getByText(/已过 17 天/)).toBeTruthy();
  expect(screen.getByText(/1 份终端合同租期超出到期日/)).toBeTruthy();
  expect(screen.getByText('档案缺漏 · 共 3 份')).toBeTruthy();
  expect(screen.getByText(/未关联任何产权证的物业/)).toBeTruthy();
  expect(screen.getByText(/欠 ¥16,000 \/ 共 ¥16,000/)).toBeTruthy();
  expect(screen.getByText(/是否纳入 2026 考核/)).toBeTruthy();
  expect(overviewQuery).toHaveBeenCalledWith({ operatorPartyId: 'op-1' });
});

it('navigates to the ledger entry when a payment row is clicked', async () => {
  overviewQuery.mockResolvedValue(view());
  show();
  const row = await screen.findByText('一德路后座 · 10 月未付');
  fireEvent.click(row.closest('button') as HTMLElement);
  expect(await screen.findByTestId('location')).toHaveTextContent(
    'ledger_type=upstream_rent&entry_id=e2&period=2026-10',
  );
});

it('shows scope recovery instead of cards when the request is forbidden', async () => {
  overviewQuery.mockRejectedValue(
    new AssetOperationsError('拒绝', 'PARTY_SCOPE_MISSING'),
  );
  show();
  expect(await screen.findByText('没有可访问的资产范围')).toBeTruthy();
  expect(screen.queryByText(/本月还有/)).toBeNull();
});

it('shows submitted state for the report card', async () => {
  const data = view();
  data.occupancyReport = {
    ...data.occupancyReport,
    status: 'submitted',
    gateReasons: [],
    rateDelta: null,
  };
  overviewQuery.mockResolvedValue(data);
  show();
  expect(await screen.findByText('已报送')).toBeTruthy();
  expect(screen.queryByText(/变动说明未填/)).toBeNull();
});

it('prompts to register operators when none exist', async () => {
  partiesQuery.mockResolvedValue([]);
  show();
  expect(
    await screen.findByText('尚无可用的运营主体，请先在主体管理中登记法人主体。'),
  ).toBeTruthy();
  expect(overviewQuery).not.toHaveBeenCalled();
});
