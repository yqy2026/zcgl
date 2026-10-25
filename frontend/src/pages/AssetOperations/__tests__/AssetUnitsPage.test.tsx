import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor, cleanup } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';

import { AssetUnitsPage } from '../AssetUnitsPage';
import {
  assetOperationsService,
  AssetOperationsError,
} from '@/services/assetOperationsService';
import type { AssetUnitListItem } from '@/services/assetOperationsService';

vi.mock(import('@/services/assetOperationsService'), async (importOriginal) => {
  const actual = await importOriginal<
    typeof import('@/services/assetOperationsService')
  >();
  return {
    ...actual,
    assetOperationsService: {
      listAssetUnits: vi.fn(),
      getAssetUnit: vi.fn(),
      updateAssetUnit: vi.fn(),
      updateVacancyNote: vi.fn(),
    },
  };
});

const mockedService = vi.mocked(assetOperationsService);

function makeUnit(overrides: Partial<AssetUnitListItem> = {}): AssetUnitListItem {
  return {
    id: 'unit-1',
    unitCode: 'U-001',
    name: '一号商铺',
    projectId: 'project-1',
    ownerPartyId: 'owner-1',
    address: '地址 1 号',
    usageType: 'commercial',
    acquisitionMode: 'leased',
    isOperating: true,
    landArea: 0,
    buildingArea: 100,
    rentableArea: 80,
    managedFrom: '2026-01-01',
    managedTo: null,
    vacancyReason: null,
    expectedLeaseStart: null,
    predecessorUnitIds: [],
    version: 2,
    rentalStatus: 'rented',
    rentedArea: 80,
    occupancyRate: 1,
    warnings: [],
    terminalContractIds: ['terminal-1'],
    ...overrides,
  };
}

function renderPage(): void {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={['/asset-operations/units']}>
        <AssetUnitsPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  mockedService.listAssetUnits.mockReset();
  mockedService.getAssetUnit.mockReset();
  mockedService.updateAssetUnit.mockReset();
});

afterEach(() => {
  cleanup();
});

describe('AssetUnitsPage', () => {
  it('renders units and derives the detail pane after loading', async () => {
    mockedService.listAssetUnits.mockResolvedValue({
      items: [makeUnit()],
      total: 1,
    });
    mockedService.getAssetUnit.mockResolvedValue(makeUnit());

    renderPage();

    await waitFor(() => {
      expect(screen.getByText('U-001')).toBeTruthy();
    });
    await waitFor(() => {
      expect(screen.getByText(/当前终端合同/)).toBeTruthy();
      expect(screen.getByText('terminal-1')).toBeTruthy();
    });
  });

  it('shows the scope warning instead of treating 403 as empty', async () => {
    mockedService.listAssetUnits.mockRejectedValue(
      new AssetOperationsError('获取资产单元列表失败', 'PARTY_SCOPE_MISSING'),
    );

    renderPage();

    await waitFor(() => {
      expect(
        screen.getByText('没有可访问的资产范围，请联系管理员配置数据范围。'),
      ).toBeTruthy();
    });
    expect(screen.queryByText('暂无资产单元')).toBeNull();
  });

  it('shows the error state for non-scope failures', async () => {
    mockedService.listAssetUnits.mockRejectedValue(new Error('网络错误'));

    renderPage();

    await waitFor(() => {
      expect(screen.getByText('网络错误')).toBeTruthy();
    });
  });

  it('shows the empty state when the list is empty', async () => {
    mockedService.listAssetUnits.mockResolvedValue({ items: [], total: 0 });

    renderPage();

    await waitFor(() => {
      expect(screen.getByText('暂无资产单元，请先完成录入或导入。')).toBeTruthy();
    });
    expect(screen.getByText(/在左侧选择一个资产单元/)).toBeTruthy();
  });

  it('saves a renamed unit with its current version', async () => {
    mockedService.listAssetUnits.mockResolvedValue({
      items: [makeUnit()],
      total: 1,
    });
    mockedService.getAssetUnit.mockResolvedValue(makeUnit());
    mockedService.updateAssetUnit.mockResolvedValue(
      makeUnit({ name: '改名后的商铺', version: 3 }),
    );
    const user = userEvent.setup();

    renderPage();

    const input = await screen.findByLabelText('单元名称');
    await user.clear(input);
    await user.type(input, '改名后的商铺');
    await user.click(screen.getByRole('button', { name: '保存名称' }));

    await waitFor(() => {
      expect(mockedService.updateAssetUnit).toHaveBeenCalledWith('unit-1', {
        expectedVersion: 2,
        name: '改名后的商铺',
      });
    });
  });
});
