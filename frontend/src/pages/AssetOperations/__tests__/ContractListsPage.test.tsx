import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor, cleanup, fireEvent } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import userEvent from '@testing-library/user-event';

import { UpstreamContractsPage, TerminalContractsPage } from '../ContractListsPage';
import { assetOperationsService, AssetOperationsError } from '@/services/assetOperationsService';
import type {
  TerminalContractListItem,
  UpstreamContractListItem,
} from '@/services/assetOperationsService';

vi.mock(import('@/services/assetOperationsService'), async importOriginal => {
  const actual = await importOriginal<typeof import('@/services/assetOperationsService')>();
  return {
    ...actual,
    assetOperationsService: {
      ...actual.assetOperationsService,
      listUpstreamContracts: vi.fn(),
      getUpstreamContract: vi.fn(),
      listTerminalContracts: vi.fn(),
      getTerminalContract: vi.fn(),
    },
  };
});

const mockedService = vi.mocked(assetOperationsService);
vi.mock('@/services/assetDepositService', () => ({
  assetDepositService: {
    list: vi.fn().mockResolvedValue({ items: [], total: 0, page: 1, page_size: 20 }),
  },
}));
vi.mock('@/components/System/CapabilityGuard', () => ({
  default: ({ children }: { children: React.ReactNode }) => children,
}));
vi.mock('@/services/partyService', () => ({
  partyService: {
    getParties: vi.fn().mockResolvedValue({
      items: [
        { id: 'owner-1', name: '城投置业' },
        { id: 'owner-2', name: '产业集团' },
      ],
      total: 2,
      skip: 0,
      limit: 1000,
      isTruncated: false,
    }),
  },
}));
vi.mock('@/services/businessChangeService', () => ({
  businessChangeService: {
    list: vi.fn().mockResolvedValue({ items: [], total: 0, page: 1, page_size: 50 }),
  },
}));

function makeUpstream(overrides: Partial<UpstreamContractListItem> = {}): UpstreamContractListItem {
  return {
    rentSchedules: [],
    rentSummary: null,
    id: 'upstream-1',
    contractNumber: 'UP-001',
    contractType: 'lease',
    name: '一德路承租合同',
    ownerPartyId: 'owner-1',
    operatorPartyId: 'operator-1',
    startDate: '2026-01-01',
    endDate: '2026-12-31',
    paymentCycle: 'monthly',
    paymentDay: 15,
    depositAmount: 50000,
    renewedFromId: null,
    version: 1,
    status: 'expiring',
    warnings: [],
    terminalContractIds: ['terminal-1'],
    coverages: [
      {
        assetUnitId: 'unit-1',
        effectiveFrom: '2026-01-01',
        effectiveTo: '2026-12-31',
      },
    ],
    lifecycleEvents: [],
    renewalChain: [
      {
        contractId: 'upstream-1',
        contractNumber: 'UP-001',
        relation: 'current',
      },
    ],
    ...overrides,
  };
}

function makeTerminal(overrides: Partial<TerminalContractListItem> = {}): TerminalContractListItem {
  return {
    rentSchedules: [],
    rentSummary: null,
    id: 'terminal-1',
    contractNumber: 'TM-001',
    contractMode: 'sublease',
    tenantPartyId: 'tenant-1',
    lessorPartyId: 'operator-1',
    upstreamContractId: null,
    startDate: '2026-01-01',
    endDate: '2026-12-31',
    depositAmount: 20000,
    rentCollector: 'operator',
    version: 1,
    status: 'active',
    warnings: [
      {
        code: 'UPSTREAM_CONTRACT_MISSING',
        severity: 'warning',
        message: '尚未关联上游合同',
      },
    ],
    coverages: [],
    lifecycleEvents: [],
    renewalChain: [],
    ...overrides,
  };
}

function renderPage(element: React.ReactElement): void {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={['/asset-operations/contracts/upstream']}>
        {element}
      </MemoryRouter>
    </QueryClientProvider>
  );
}

beforeEach(() => {
  mockedService.listUpstreamContracts.mockReset();
  mockedService.getUpstreamContract.mockReset();
  mockedService.listTerminalContracts.mockReset();
  mockedService.getTerminalContract.mockReset();
});

afterEach(() => {
  cleanup();
});

describe('UpstreamContractsPage', () => {
  it('renders rows but keeps the detail hint until a row is selected', async () => {
    mockedService.listUpstreamContracts.mockResolvedValue({
      items: [makeUpstream()],
      total: 1,
    });
    mockedService.getUpstreamContract.mockResolvedValue(makeUpstream());

    renderPage(<UpstreamContractsPage />);

    await waitFor(() => {
      expect(screen.getByText('UP-001')).toBeTruthy();
    });
    await waitFor(() => {
      expect(screen.getByText('在左侧选择一份合同查看详情。')).toBeTruthy();
    });
    expect(mockedService.getUpstreamContract).not.toHaveBeenCalled();

    await userEvent.setup().click(screen.getByText('UP-001'));

    await waitFor(() => {
      expect(screen.getByText(/版本链|当前终端合同|覆盖单元/)).toBeTruthy();
      expect(screen.getByText('1 个')).toBeTruthy();
      expect(screen.getByText('付款周期（只读）')).toBeTruthy();
      expect(screen.getByText('付款日（只读）')).toBeTruthy();
      expect(screen.getByText('以租金阶段为准')).toBeTruthy();
    });
  });

  it('shows the scope warning instead of treating 403 as empty', async () => {
    mockedService.listUpstreamContracts.mockRejectedValue(
      new AssetOperationsError('获取上游合同列表失败', 'PARTY_SCOPE_MISSING')
    );

    renderPage(<UpstreamContractsPage />);

    await waitFor(() => {
      expect(screen.getByText('没有可访问的资产范围，请联系管理员配置数据范围。')).toBeTruthy();
    });
    expect(screen.queryByText('暂无上游合同')).toBeNull();
  });

  it('shows the empty state when the list is empty', async () => {
    mockedService.listUpstreamContracts.mockResolvedValue({
      items: [],
      total: 0,
    });

    renderPage(<UpstreamContractsPage />);

    await waitFor(() => {
      expect(screen.getByText('暂无上游合同，请先经录入会话登记已签合同。')).toBeTruthy();
    });
  });

  it('filters upstream contracts by owner party and resets pagination', async () => {
    mockedService.listUpstreamContracts.mockResolvedValue({ items: [], total: 0 });

    renderPage(<UpstreamContractsPage />);

    fireEvent.mouseDown(screen.getByRole('combobox', { name: '按产权方筛选' }));
    fireEvent.click(await screen.findByText('城投置业'));

    await waitFor(() =>
      expect(mockedService.listUpstreamContracts).toHaveBeenLastCalledWith(
        expect.objectContaining({ ownerPartyId: 'owner-1', offset: 0 })
      )
    );
  });
});

describe('TerminalContractsPage', () => {
  it('renders warning tags and loads detail only after selection', async () => {
    mockedService.listTerminalContracts.mockResolvedValue({
      items: [makeTerminal()],
      total: 1,
    });
    mockedService.getTerminalContract.mockResolvedValue(makeTerminal());

    renderPage(<TerminalContractsPage />);

    await waitFor(() => {
      expect(screen.getByText('TM-001')).toBeTruthy();
      expect(screen.getByText('暂无上游')).toBeTruthy();
    });
    await waitFor(() => {
      expect(screen.getByText('在左侧选择一份合同查看详情。')).toBeTruthy();
    });
    expect(mockedService.getTerminalContract).not.toHaveBeenCalled();

    await userEvent.setup().click(screen.getByText('TM-001'));

    await waitFor(() => {
      expect(screen.getByText(/上游合同/)).toBeTruthy();
    });
  });
});

it('filters unsettled deposits separately from unpaid rent and resets pagination', async () => {
  mockedService.listTerminalContracts.mockResolvedValue({ items: [], total: 0 });
  renderPage(<TerminalContractsPage />);
  const user = userEvent.setup();
  await user.click(screen.getByLabelText('押金未结清'));
  await waitFor(() =>
    expect(mockedService.listTerminalContracts).toHaveBeenLastCalledWith(
      expect.objectContaining({ filter: 'deposit_unsettled', offset: 0 })
    )
  );
  await user.click(screen.getByLabelText('租金未到账'));
  expect(screen.getByLabelText('押金未结清')).not.toBeChecked();
  await waitFor(() =>
    expect(mockedService.listTerminalContracts).toHaveBeenLastCalledWith(
      expect.objectContaining({ filter: 'rent_unpaid' })
    )
  );
});

it('filters terminal contracts by owner party through covered units', async () => {
  mockedService.listTerminalContracts.mockResolvedValue({ items: [], total: 0 });
  renderPage(<TerminalContractsPage />);

  fireEvent.mouseDown(screen.getByRole('combobox', { name: '按产权方筛选' }));
  fireEvent.click(await screen.findByText('产业集团'));

  await waitFor(() =>
    expect(mockedService.listTerminalContracts).toHaveBeenLastCalledWith(
      expect.objectContaining({ ownerPartyId: 'owner-2', offset: 0 })
    )
  );
});
