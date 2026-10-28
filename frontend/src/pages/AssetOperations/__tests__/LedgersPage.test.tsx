import { beforeEach, expect, it, vi } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import { afterEach } from 'vitest';
import LedgersPage, { RentEntryPanel } from '../LedgersPage';
import type { RentEntry } from '@/services/assetLedgerService';
import userEvent from '@testing-library/user-event';
import { waitFor } from '@testing-library/react';
import { assetLedgerService } from '@/services/assetLedgerService';
import { AssetOperationsError } from '@/services/assetOperationsService';

vi.mock('@/services/assetLedgerService', async original => ({
  ...(await original<typeof import('@/services/assetLedgerService')>()),
  assetLedgerService: { getMatrix: vi.fn(), getEntry: vi.fn(), record: vi.fn(), reverse: vi.fn() },
}));
vi.mock('@/components/System/CapabilityGuard', () => ({
  default: ({ children }: { children: React.ReactNode }) => children,
}));
beforeEach(() => vi.clearAllMocks());
afterEach(cleanup);
function show(): void {
  render(
    <QueryClientProvider
      client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}
    >
      <MemoryRouter>
        <LedgersPage />
      </MemoryRouter>
    </QueryClientProvider>
  );
}
it('renders scope denial without calling it an empty ledger', async () => {
  vi.mocked(assetLedgerService.getMatrix).mockRejectedValue(
    new AssetOperationsError('无有效范围', 'PARTY_SCOPE_MISSING')
  );
  show();
  expect(await screen.findByText('暂无台账访问权限')).toBeVisible();
  expect(screen.queryByText('本年暂无租金义务')).toBeNull();
});
it('renders a genuine empty ledger with a contract entry link', async () => {
  vi.mocked(assetLedgerService.getMatrix).mockResolvedValue({
    ledger_type: 'terminal_rent',
    year: 2026,
    current_month: 10,
    rows: [],
    total_due_amount: 0,
    total_paid_amount: 0,
    total_remaining_amount: 0,
  });
  show();
  expect(await screen.findByText('本年暂无租金义务')).toBeVisible();
  expect(screen.getByRole('link', { name: '核对合同租金阶段' })).toBeVisible();
});

it('defaults a partial receipt to the remaining amount and requires a reversal reason', async () => {
  const entry: RentEntry = {
    id: 'entry-1',
    entry_type: 'terminal_receivable',
    contract_kind: 'terminal',
    contract_id: 'contract-1',
    period: '2026-10',
    period_start: '2026-10-01',
    period_end: '2026-10-31',
    due_date: '2026-10-25',
    due_amount: 100,
    currency: 'CNY',
    origin: 'generated',
    basis_note: null,
    locked_source: {},
    voided_at: null,
    version: 2,
    effective_paid_amount: 40,
    remaining_amount: 60,
    status: 'partial',
    warnings: [],
    records: [
      {
        id: 'record-1',
        ledger_entry_id: 'entry-1',
        record_type: 'receipt',
        amount: 40,
        occurred_on: '2026-10-20',
        reason: null,
        reverses_record_id: null,
        document_id: null,
        created_by: 'actor-1',
        created_at: '2026-10-20T00:00:00Z',
      },
    ],
  };
  const saved = vi.fn();
  vi.mocked(assetLedgerService.record).mockResolvedValue({
    id: 'record-2',
    ledger_entry_id: 'entry-1',
    version: 3,
    idempotent: false,
  });
  const user = userEvent.setup();
  render(
    <QueryClientProvider client={new QueryClient()}>
      <RentEntryPanel entry={entry} onChanged={saved} />
    </QueryClientProvider>
  );
  expect(screen.getByLabelText('登记金额')).toHaveValue(60);
  expect(screen.getByRole('button', { name: '撤销该笔登记' })).toBeDisabled();
  await user.click(screen.getByRole('button', { name: '登记到账' }));
  await waitFor(() => expect(saved).toHaveBeenCalledTimes(1));
  expect(assetLedgerService.record).toHaveBeenCalledWith(
    'entry-1',
    expect.objectContaining({ amount: '60', expected_version: 2, record_type: 'receipt' }),
    expect.any(String)
  );
  await user.type(screen.getByLabelText('撤销或作废原因'), '登记金额录错');
  expect(screen.getByRole('button', { name: '撤销该笔登记' })).toBeEnabled();
});
