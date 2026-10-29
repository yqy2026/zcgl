import { afterEach, expect, it, vi } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import ContractDepositPanel from '../ContractDepositPanel';
import { assetDepositService } from '@/services/assetDepositService';
import type { DepositDetail } from '@/services/assetDepositService';
import { AssetOperationsError } from '@/services/assetOperationsService';

vi.mock('@/services/assetDepositService', () => ({
  assetDepositService: { list: vi.fn(), detail: vi.fn(), record: vi.fn(), reverse: vi.fn() },
}));
vi.mock('@/components/System/CapabilityGuard', () => ({
  default: ({ children }: { children: React.ReactNode }) => children,
}));
const detail: DepositDetail = {
  id: 'deposit',
  contract_kind: 'terminal',
  contract_id: 'contract',
  collector: 'operator',
  agreed_amount: 100,
  held_amount: 100,
  carried_in_amount: 0,
  carried_out_amount: 0,
  direction: 'refundable',
  outstanding_amount: 100,
  status: 'refundable_unreturned',
  version: 2,
  ended: true,
  read_only: false,
  offset_candidates: [],
  records: [],
};
function show(type?: string): void {
  render(
    <QueryClientProvider
      client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}
    >
      <ContractDepositPanel kind="terminal" contractId="contract" contractType={type} />
    </QueryClientProvider>
  );
}
afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});
it('keeps a forbidden response separate from an empty deposit', async () => {
  vi.mocked(assetDepositService.list).mockRejectedValue(
    new AssetOperationsError('无范围', 'PARTY_SCOPE_MISSING')
  );
  show();
  expect(await screen.findByRole('alert')).toHaveTextContent('没有权限查看押金');
  expect(screen.queryByText('尚无押金条目，请先核对合同。')).toBeNull();
});
it('requires a reason for forfeiture and uses the deposit version', async () => {
  vi.mocked(assetDepositService.list).mockResolvedValue({
    items: [detail],
    total: 1,
    page: 1,
    page_size: 50,
  });
  vi.mocked(assetDepositService.detail).mockResolvedValue(detail);
  vi.mocked(assetDepositService.record).mockResolvedValue(undefined);
  show();
  const user = userEvent.setup();
  await user.selectOptions(await screen.findByLabelText('押金处理'), 'forfeit');
  expect(screen.getByRole('button', { name: '登记押金处理' })).toBeDisabled();
  await user.type(screen.getByLabelText('处理原因（必填）'), '合同约定赔偿');
  await user.click(screen.getByRole('button', { name: '登记押金处理' }));
  expect(assetDepositService.record).toHaveBeenCalledWith(
    'deposit',
    expect.objectContaining({
      record_type: 'forfeit',
      expected_version: 2,
      reason: '合同约定赔偿',
    }),
    expect.any(String)
  );
});
it('does not fetch deposits for a management agreement', () => {
  show('management_agreement');
  expect(assetDepositService.list).not.toHaveBeenCalled();
  expect(screen.queryByText('押金明细')).toBeNull();
});
it('requires selecting an unpaid rent period for an offset', async () => {
  vi.mocked(assetDepositService.list).mockResolvedValue({
    items: [detail],
    total: 1,
    page: 1,
    page_size: 50,
  });
  vi.mocked(assetDepositService.detail).mockResolvedValue(detail);
  vi.mocked(assetDepositService.record).mockResolvedValue(undefined);
  vi.mocked(assetDepositService.detail).mockResolvedValue({
    ...detail,
    offset_candidates: [
      {
        id: 'rent',
        contract_id: 'ancestor',
        period_start: '2026-01-01',
        period_end: '2026-01-31',
        due_date: '2026-01-01',
        remaining_amount: 100,
      },
    ],
  });
  show();
  const user = userEvent.setup();
  await user.selectOptions(await screen.findByLabelText('押金处理'), 'deduct');
  expect(screen.getByRole('button', { name: '登记押金处理' })).toBeDisabled();
  await user.selectOptions(screen.getByLabelText('抵扣租金账期'), 'rent');
  await user.click(screen.getByRole('button', { name: '登记押金处理' }));
  expect(assetDepositService.record).toHaveBeenCalledWith(
    'deposit',
    expect.objectContaining({ record_type: 'deduct', offset_ledger_entry_id: 'rent' }),
    expect.any(String)
  );
});
