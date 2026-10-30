import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import Page, { capitalMoney } from '../ManagementFeeStatementPage';
import { managementFeeService, type ManagementFeeStatement } from '@/services/managementFeeService';
import { AssetOperationsError } from '@/services/assetOperationsService';
import { assetLedgerService } from '@/services/assetLedgerService';
vi.mock('@/services/assetLedgerService', async original => ({
  ...(await original<typeof import('@/services/assetLedgerService')>()),
  assetLedgerService: { getEntry: vi.fn().mockResolvedValue({ version: 7 }) },
}));
vi.mock('@/services/managementFeeService', () => ({
  managementFeeService: {
    get: vi.fn(),
    upload: vi.fn(),
    confirm: vi.fn(),
    supersede: vi.fn(),
    defer: vi.fn(),
    record: vi.fn(),
  },
}));
vi.mock('@/components/System/CapabilityGuard', () => ({
  default: ({ children }: { children: React.ReactNode }) => children,
}));
beforeEach(() => {
  vi.mocked(assetLedgerService.getEntry).mockResolvedValue({ version: 7 } as Awaited<
    ReturnType<typeof assetLedgerService.getEntry>
  >);
});
afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});
const statement: ManagementFeeStatement = {
  id: 'st',
  owner_party_id: 'owner',
  period: '2026-10',
  statement_number: 'FEE-1',
  version: 2,
  status: 'pending_stamp',
  deadline: '2026-11-30',
  upstream_contract_ids: [],
  base_amount: 1000,
  fee_amount: 100,
  stamped_document_id: null,
  confirmed_at: null,
  confirmed_by: null,
  predecessor_statement_id: null,
  successor_statement_id: null,
  lines: [],
  carried_waiting_hint: false,
  upstream_missing_entry_ids: [],
  upstream_missing_warning: null,
};
function show() {
  render(
    <QueryClientProvider
      client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}
    >
      <MemoryRouter initialEntries={['/fees/st']}>
        <Routes>
          <Route path="/fees/:statement_id" element={<Page />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  );
}
it('shows the paper statement and prevents confirmation without a stamp', async () => {
  vi.mocked(managementFeeService.get).mockResolvedValue(statement);
  show();
  expect(await screen.findByText('FEE-1')).toBeVisible();
  expect(screen.getByText('壹佰元整')).toBeVisible();
  expect(screen.getByRole('button', { name: '确认对账单' })).toBeDisabled();
  expect(screen.getByLabelText('盖章文件')).toBeVisible();
});
it('keeps confirmed statements read-only while offering correction', async () => {
  vi.mocked(managementFeeService.get).mockResolvedValue({ ...statement, status: 'confirmed' });
  show();
  await screen.findByText('FEE-1');
  expect(screen.queryByLabelText('盖章文件')).toBeNull();
  expect(screen.getByRole('button', { name: '创建更正单' })).toBeDisabled();
});
it('shows denied scope without paper data', async () => {
  vi.mocked(managementFeeService.get).mockRejectedValue(
    new AssetOperationsError('无范围', 'PARTY_SCOPE_MISSING')
  );
  show();
  expect(await screen.findByText('暂无该对账单访问权限')).toBeVisible();
  expect(screen.queryByText('FEE-1')).toBeNull();
});

it('reuses the command key after an ambiguous confirmation failure', async () => {
  const user = (await import('@testing-library/user-event')).default.setup();
  vi.mocked(managementFeeService.get).mockResolvedValue({
    ...statement,
    stamped_document_id: 'doc',
  });
  vi.mocked(managementFeeService.confirm).mockRejectedValue(new Error('连接断开，请重试'));
  show();
  await user.click(await screen.findByRole('button', { name: '确认对账单' }));
  await screen.findByText('连接断开，请重试');
  await user.click(screen.getByRole('button', { name: '确认对账单' }));
  const calls = vi.mocked(managementFeeService.confirm).mock.calls;
  expect(calls).toHaveLength(2);
  expect(calls[0]).toEqual(calls[1]);
  expect(calls[0]?.[1]).toEqual({ expected_version: 2 });
});

it('hides previously readable paper after a write scope rejection', async () => {
  const user = (await import('@testing-library/user-event')).default.setup();
  vi.mocked(managementFeeService.get).mockResolvedValue({
    ...statement,
    stamped_document_id: 'doc',
  });
  vi.mocked(managementFeeService.confirm).mockRejectedValue(
    new AssetOperationsError('无权限', 'PARTY_SCOPE_MISSING')
  );
  show();
  await user.click(await screen.findByRole('button', { name: '确认对账单' }));
  expect(await screen.findByText('暂无该对账单访问权限')).toBeVisible();
  expect(screen.queryByText('FEE-1')).toBeNull();
});

it('uses the rent obligation version when registering owner receipts', async () => {
  const user = (await import('@testing-library/user-event')).default.setup();
  const { assetLedgerService } = await import('@/services/assetLedgerService');
  const entrySpy = vi
    .spyOn(assetLedgerService, 'getEntry')
    .mockResolvedValue({ version: 7 } as Awaited<ReturnType<typeof assetLedgerService.getEntry>>);
  vi.mocked(managementFeeService.get).mockResolvedValue({
    ...statement,
    lines: [
      {
        id: null,
        line_kind: 'current',
        upstream_contract_id: 'up',
        terminal_contract_id: 'term',
        rent_ledger_entry_id: 'rent',
        asset_unit_ids: [],
        tenant_name_snapshot: '租户甲',
        rent_period: '2026-10',
        scheduled_rent: 1000,
        owner_received_amount: 0,
        counted_record_ids: [],
        received_on: null,
        fee_rate: 0.1,
        fee_amount: 0,
        deferred_amount: 1000,
        deferral_reason: null,
        carried_from_statement_id: null,
        processed: false,
      },
    ],
  });
  vi.mocked(managementFeeService.record).mockResolvedValue({ id: 'r', version: 8 } as Awaited<
    ReturnType<typeof managementFeeService.record>
  >);
  show();
  await user.selectOptions(await screen.findByLabelText('租金账期'), 'rent');
  await user.type(screen.getByLabelText('到账金额'), '40');
  await user.click(screen.getByRole('button', { name: '登记产权方到账' }));
  const { waitFor } = await import('@testing-library/react');
  await waitFor(() =>
    expect(managementFeeService.record).toHaveBeenCalledWith(
      'st',
      expect.objectContaining({ rent_ledger_entry_id: 'rent', amount: 40, expected_version: 7 }),
      expect.any(String)
    )
  );
  entrySpy.mockRestore();
});

it.each(['confirm', 'upload', 'defer'] as const)(
  'invalidates the annual matrix after %s succeeds',
  async action => {
    const user = (await import('@testing-library/user-event')).default.setup();
    const { waitFor } = await import('@testing-library/react');
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    const invalidate = vi.spyOn(client, 'invalidateQueries');
    vi.mocked(managementFeeService.get).mockResolvedValue({
      ...statement,
      deadline: '2099-11-30',
      stamped_document_id: 'doc',
      lines: [
        {
          id: null,
          line_kind: 'current',
          upstream_contract_id: 'up',
          terminal_contract_id: 'term',
          rent_ledger_entry_id: 'rent',
          asset_unit_ids: [],
          tenant_name_snapshot: '租户甲',
          rent_period: '2026-10',
          scheduled_rent: 1000,
          owner_received_amount: 0,
          counted_record_ids: [],
          received_on: null,
          fee_rate: 0.1,
          fee_amount: 0,
          deferred_amount: 1000,
          deferral_reason: null,
          carried_from_statement_id: null,
          processed: false,
        },
      ],
    });
    vi.mocked(managementFeeService.confirm).mockResolvedValue({
      statement_id: 'st',
      version: 3,
      idempotent: false,
    });
    vi.mocked(managementFeeService.upload).mockResolvedValue({
      statement_id: 'st',
      version: 3,
      idempotent: false,
      document_id: 'doc',
      fee_amount: 100,
    });
    vi.mocked(managementFeeService.defer).mockResolvedValue({
      statement_id: 'st',
      version: 3,
      idempotent: false,
    });
    render(
      <QueryClientProvider client={client}>
        <MemoryRouter initialEntries={['/fees/st']}>
          <Routes>
            <Route path="/fees/:statement_id" element={<Page />} />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>
    );
    await screen.findByText('FEE-1');
    if (action === 'confirm') await user.click(screen.getByRole('button', { name: '确认对账单' }));
    if (action === 'upload') {
      await user.upload(
        screen.getByLabelText('盖章文件'),
        new File(['pdf'], 'stamp.pdf', { type: 'application/pdf' })
      );
      await user.click(screen.getByRole('button', { name: '替换盖章件' }));
    }
    if (action === 'defer') {
      await user.selectOptions(screen.getByLabelText('租金账期'), 'rent');
      await user.type(screen.getByLabelText('顺延原因'), '待核对');
      await user.click(screen.getByRole('button', { name: '标记顺延' }));
    }
    await waitFor(() =>
      expect(invalidate).toHaveBeenCalledWith({ queryKey: ['management-fee-matrix'] })
    );
  }
);

it('disables confirmation while collecting even if a stamp exists', async () => {
  vi.mocked(managementFeeService.get).mockResolvedValue({
    ...statement,
    status: 'collecting',
    stamped_document_id: 'doc',
  });
  show();
  expect(await screen.findByRole('button', { name: '确认对账单' })).toBeDisabled();
});

it.each([
  { reason: '此前顺延', processed: true, deadline: '2099-11-30' },
  { reason: null, processed: true, deadline: '2099-11-30' },
  { reason: null, processed: false, deadline: '2000-11-30' },
])('prevents repeat or automatic deferral: %j', async ({ reason, processed, deadline }) => {
  const user = (await import('@testing-library/user-event')).default.setup();
  vi.mocked(managementFeeService.get).mockResolvedValue({
    ...statement,
    deadline,
    lines: [
      {
        id: null,
        line_kind: 'current',
        upstream_contract_id: 'up',
        terminal_contract_id: 'term',
        rent_ledger_entry_id: 'rent',
        asset_unit_ids: [],
        tenant_name_snapshot: '租户甲',
        rent_period: '2026-10',
        scheduled_rent: 1000,
        owner_received_amount: 0,
        counted_record_ids: [],
        received_on: null,
        fee_rate: 0.1,
        fee_amount: 0,
        deferred_amount: 1000,
        deferral_reason: reason,
        carried_from_statement_id: null,
        processed,
      },
    ],
  });
  show();
  await user.selectOptions(await screen.findByLabelText('租金账期'), 'rent');
  await user.type(screen.getByLabelText('顺延原因'), '新原因');
  expect(screen.getByRole('button', { name: '标记顺延' })).toBeDisabled();
});

it.each([
  [0, '零元整'],
  [0.05, '零元伍分'],
  [100001000, '壹亿零壹仟元整'],
  [100000001, '壹亿零壹元整'],
  [100010000, '壹亿零壹万元整'],
  [1.01, '壹元零壹分'],
])('formats capital amount %s', (value, expected) => {
  expect(capitalMoney(Number(value))).toBe(expected);
});
