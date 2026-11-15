import { beforeEach, expect, it, vi } from 'vitest';
import { render, screen, cleanup } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';
import ContractSupplementsPanel from '../ContractSupplementsPanel';
import { contractSupplementService } from '@/services/contractSupplementService';
const permission = vi.hoisted(() => ({ archive: true }));
vi.mock('@/components/System/CapabilityGuard', () => ({
  default: ({ children }: { children: ReactNode }) => (permission.archive ? children : null),
}));
vi.mock('@/services/contractSupplementService', () => ({
  contractSupplementService: { list: vi.fn(), register: vi.fn(), withdraw: vi.fn() },
}));
function show() {
  render(
    <QueryClientProvider
      client={
        new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: 1 } } })
      }
    >
      <ContractSupplementsPanel kind="upstream" contractId="parent" />
    </QueryClientProvider>
  );
}
beforeEach(() => {
  cleanup();
  vi.clearAllMocks();
  permission.archive = true;
  vi.mocked(contractSupplementService.list).mockResolvedValue([]);
});
it('keeps registration unavailable to readers', async () => {
  permission.archive = false;
  show();
  await screen.findByText('尚未登记补充协议。');
  expect(screen.queryByRole('button', { name: '登记补充协议' })).toBeNull();
});
it('registers one business entry without claiming a scan was uploaded', async () => {
  vi.mocked(contractSupplementService.register).mockResolvedValue({
    id: 'new',
    contract_kind: 'upstream',
    contract_id: 'parent',
    agreement_number: 'S1',
    title: '租期补充',
    signed_on: null,
    version: 1,
    withdrawn_at: null,
  });
  show();
  await userEvent.type(screen.getByLabelText('协议编号'), 'S1');
  await userEvent.type(screen.getByLabelText('协议名称'), '租期补充');
  await userEvent.click(screen.getByRole('button', { name: '登记补充协议' }));
  await screen.findByText('已登记补充协议，请在档案中维护扫描件。');
  expect(contractSupplementService.register).toHaveBeenCalledWith({
    contract_kind: 'upstream',
    contract_id: 'parent',
    agreement_number: 'S1',
    title: '租期补充',
    signed_on: null,
  });
});
it('requires a reason before withdrawal and submits the version', async () => {
  vi.mocked(contractSupplementService.list).mockResolvedValue([
    {
      id: 's',
      contract_kind: 'upstream',
      contract_id: 'parent',
      agreement_number: 'S1',
      title: '租期补充',
      signed_on: null,
      version: 2,
      withdrawn_at: null,
    },
  ]);
  vi.mocked(contractSupplementService.withdraw).mockResolvedValue({ id: 's' } as never);
  show();
  await userEvent.click(await screen.findByRole('button', { name: '撤回登记' }));
  await userEvent.type(screen.getByLabelText('撤回原因'), '误登记');
  await userEvent.click(screen.getByRole('button', { name: '确认撤回登记' }));
  expect(contractSupplementService.withdraw).toHaveBeenCalledWith('s', 2, '误登记');
});
it('does not replay a failed registration under global mutation retries', async () => {
  const { AssetOperationsError } = await import('@/services/assetOperationsService');
  vi.mocked(contractSupplementService.register).mockRejectedValue(
    new AssetOperationsError('重复', 'SUPPLEMENT_NUMBER_EXISTS')
  );
  show();
  await userEvent.type(screen.getByLabelText('协议编号'), 'S1');
  await userEvent.type(screen.getByLabelText('协议名称'), '协议');
  await userEvent.click(screen.getByRole('button', { name: '登记补充协议' }));
  await screen.findByText('此合同已有相同协议编号，请核对登记清单。');
  expect(contractSupplementService.register).toHaveBeenCalledTimes(1);
});
