import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor, cleanup, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';

import { AssetUnitsPage } from '../AssetUnitsPage';
import { ASSET_OPERATIONS_V5_ROUTES } from '@/constants/routes';
import { assetOperationsService, AssetOperationsError } from '@/services/assetOperationsService';
import type { AssetUnitListItem } from '@/services/assetOperationsService';
vi.mock('@/components/System/CapabilityGuard', () => ({ default: () => null }));

vi.mock(import('@/services/assetOperationsService'), async importOriginal => {
  const actual = await importOriginal<typeof import('@/services/assetOperationsService')>();
  return {
    ...actual,
    assetOperationsService: {
      listAssetUnits: vi.fn(),
      listAssetUnitUsageTypes: vi.fn(),
      getAssetUnit: vi.fn(),
      listAssetUnitCertificates: vi.fn(),
      updateAssetUnit: vi.fn(),
      updateVacancyNote: vi.fn(),
    },
  };
});

const mockedService = vi.mocked(assetOperationsService);
vi.mock('@/services/partyService', () => ({
  partyService: {
    getParties: vi.fn().mockResolvedValue({
      items: [{ id: 'owner-1', name: '城投置业' }],
      total: 1,
      skip: 0,
      limit: 1000,
      isTruncated: false,
    }),
  },
}));
vi.mock('@/services/businessChangeService', () => ({
  businessChangeService: {
    list: vi
      .fn()
      .mockResolvedValue({ items: [], total: 0, page: 1, page_size: 50 }),
  },
}));

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
    </QueryClientProvider>
  );
}

beforeEach(() => {
  mockedService.listAssetUnitCertificates.mockReset().mockResolvedValue([]);
  mockedService.listAssetUnits.mockReset();
  mockedService.getAssetUnit.mockReset();
  mockedService.updateAssetUnit.mockReset();
  mockedService.listAssetUnitUsageTypes.mockReset().mockResolvedValue(['办公', '商业']);
});

afterEach(() => {
  cleanup();
});

describe('AssetUnitsPage', () => {
  it('removes the previous certificates while the next unit loads', async () => {
    const second = makeUnit({ id: 'unit-2', unitCode: 'U-002', name: '二号商铺' });
    mockedService.listAssetUnits.mockResolvedValue({ items: [makeUnit(), second], total: 2 });
    mockedService.getAssetUnit.mockImplementation(async id =>
      id === second.id ? second : makeUnit()
    );
    mockedService.listAssetUnitCertificates
      .mockResolvedValueOnce([
        {
          id: 'c1',
          certificate_number: '上一单元证',
          certificate_type: 'real_estate',
          property_address: null,
          registration_date: null,
          building_area: null,
          land_area: null,
          land_use_term_start: null,
          land_use_term_end: null,
        },
      ])
      .mockReturnValueOnce(new Promise(() => {}));
    renderPage();
    expect(await screen.findByText('上一单元证')).toBeTruthy();
    await userEvent.click(screen.getByText('二号商铺'));
    expect(await screen.findByText('产权证加载中…')).toBeTruthy();
    expect(screen.queryByText('上一单元证')).toBeNull();
  });
  it('shows certificate loading only after the unit detail is available', async () => {
    mockedService.listAssetUnits.mockResolvedValue({ items: [makeUnit()], total: 1 });
    mockedService.getAssetUnit.mockResolvedValue(makeUnit());
    mockedService.listAssetUnitCertificates.mockReturnValue(new Promise(() => {}));
    renderPage();
    expect(await screen.findByText('产权证加载中…')).toBeTruthy();
    expect(screen.queryByText('当前单元尚未关联产权证。')).toBeNull();
  });

  it.each([
    'PARTY_SCOPE_MISSING',
    'PARTY_SCOPE_INVALID_ORGANIZATION',
    'PARTY_SCOPE_INVALID_PARTY',
    'PARTY_SCOPE_INVALID_BINDING',
    'ASSET_OPS_PERMISSION_DENIED',
  ])('shows certificate permission failure %s without displaying an empty result', async code => {
    mockedService.listAssetUnits.mockResolvedValue({ items: [makeUnit()], total: 1 });
    mockedService.getAssetUnit.mockResolvedValue(makeUnit());
    mockedService.listAssetUnitCertificates.mockRejectedValue(
      new AssetOperationsError('范围缺失', code)
    );
    renderPage();
    expect(await screen.findByText('没有可访问的产权证范围，请联系管理员。')).toBeTruthy();
    expect(screen.queryByText('当前单元尚未关联产权证。')).toBeNull();
  });
  it('shows certificate source text without exposing old certificate links', async () => {
    mockedService.listAssetUnits.mockResolvedValue({ items: [makeUnit()], total: 1 });
    mockedService.getAssetUnit.mockResolvedValue(makeUnit());
    mockedService.listAssetUnitCertificates.mockResolvedValue([
      {
        id: 'c1',
        certificate_number: '粤证001',
        certificate_type: 'real_estate',
        property_address: '证载地址',
        registration_date: null,
        building_area: '100（共有）',
        land_area: null,
        land_use_term_start: null,
        land_use_term_end: null,
      },
    ]);
    renderPage();
    expect(await screen.findByText('粤证001')).toBeTruthy();
    expect(screen.getByText('100（共有）')).toBeTruthy();
    expect(screen.queryByRole('link', { name: '粤证001' })).toBeNull();
  });

  it('distinguishes an unlinked certificate from a missing scan', async () => {
    mockedService.listAssetUnits.mockResolvedValue({ items: [makeUnit()], total: 1 });
    mockedService.getAssetUnit.mockResolvedValue(makeUnit());
    renderPage();
    expect(await screen.findByText('当前单元尚未关联产权证。')).toBeTruthy();
    expect(screen.queryByText('缺少扫描件')).toBeNull();
  });

  it('offers a retry for certificate failures and preserves the selected unit', async () => {
    mockedService.listAssetUnits.mockResolvedValue({ items: [makeUnit()], total: 1 });
    mockedService.getAssetUnit.mockResolvedValue(makeUnit());
    mockedService.listAssetUnitCertificates
      .mockRejectedValueOnce(new AssetOperationsError('失败', 'SERVER_ERROR'))
      .mockResolvedValue([]);
    renderPage();
    await userEvent.click(await screen.findByText('重新加载产权证'));
    expect(await screen.findByText('当前单元尚未关联产权证。')).toBeTruthy();
  });
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
      new AssetOperationsError('获取资产单元列表失败', 'PARTY_SCOPE_MISSING')
    );

    renderPage();

    await waitFor(() => {
      expect(screen.getByText('没有可访问的资产范围，请联系管理员配置数据范围。')).toBeTruthy();
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
    mockedService.updateAssetUnit.mockResolvedValue(makeUnit({ name: '改名后的商铺', version: 3 }));
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

  it('resets the rename form when the selected unit changes', async () => {
    const first = makeUnit();
    const second = makeUnit({ id: 'unit-2', unitCode: 'U-002', name: '二号商铺' });
    mockedService.listAssetUnits.mockResolvedValue({ items: [first, second], total: 2 });
    mockedService.getAssetUnit.mockImplementation(async unitId =>
      unitId === second.id ? second : first
    );
    const user = userEvent.setup();

    renderPage();

    const input = (await screen.findByLabelText('单元名称')) as HTMLInputElement;
    await user.clear(input);
    await user.type(input, '未保存名称');
    await user.click(screen.getByText('二号商铺'));

    await waitFor(() => {
      expect(mockedService.getAssetUnit).toHaveBeenCalledWith('unit-2');
      expect((screen.getByLabelText('单元名称') as HTMLInputElement).value).toBe('二号商铺');
    });
  });

  it('links the unit detail to the assessment-scope reporting page by year', async () => {
    mockedService.listAssetUnits.mockResolvedValue({
      items: [makeUnit()],
      total: 1,
    });
    mockedService.getAssetUnit.mockResolvedValue(makeUnit());

    renderPage();

    const link = await screen.findByRole('link', { name: '查看考核范围' });
    expect(link.getAttribute('href')).toBe(
      `${ASSET_OPERATIONS_V5_ROUTES.OCCUPANCY_REPORTS}?year=${new Date().getFullYear()}`
    );
  });

  it('filters units by owner party with pagination reset', async () => {
    mockedService.listAssetUnits.mockResolvedValue({ items: [makeUnit()], total: 1 });
    mockedService.getAssetUnit.mockResolvedValue(makeUnit());

    renderPage();

    fireEvent.mouseDown(screen.getByRole('combobox', { name: '按产权方筛选' }));
    fireEvent.click(await screen.findByText('城投置业'));

    await waitFor(() =>
      expect(mockedService.listAssetUnits).toHaveBeenLastCalledWith(
        expect.objectContaining({ ownerPartyId: 'owner-1', offset: 0 })
      )
    );
  });

  it('filters units by usage type', async () => {
    mockedService.listAssetUnits.mockResolvedValue({ items: [makeUnit()], total: 1 });
    mockedService.getAssetUnit.mockResolvedValue(makeUnit());

    renderPage();

    fireEvent.mouseDown(screen.getByRole('combobox', { name: '按业态筛选' }));
    fireEvent.click(await screen.findByText('商业'));

    await waitFor(() =>
      expect(mockedService.listAssetUnits).toHaveBeenLastCalledWith(
        expect.objectContaining({ usageType: '商业', offset: 0 })
      )
    );
  });
});
