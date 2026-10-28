import { act, cleanup, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, expect, it, vi } from 'vitest';
import ContractRentPanel from '../ContractRentPanel';
import { assetLedgerService } from '@/services/assetLedgerService';
import type { CorrectionPreview } from '@/services/assetLedgerService';

vi.mock('@/services/assetLedgerService', async original => ({
  ...(await original<typeof import('@/services/assetLedgerService')>()),
  assetLedgerService: { previewCorrection: vi.fn(), commitCorrection: vi.fn() },
}));
vi.mock('@/components/System/CapabilityGuard', () => ({
  default: ({ children }: { children: React.ReactNode }) => children,
}));
afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

it('discards a slow preview when the proposal changed before it returned', async () => {
  let finish!: (result: CorrectionPreview) => void;
  vi.mocked(assetLedgerService.previewCorrection).mockReturnValue(
    new Promise(resolve => {
      finish = resolve;
    })
  );
  render(
    <QueryClientProvider client={new QueryClient()}>
      <MemoryRouter>
        <ContractRentPanel
          kind="terminal"
          contractId="contract"
          startDate="2026-01-01"
          endDate="2026-12-31"
          schedules={[]}
          summary={null}
        />
      </MemoryRouter>
    </QueryClientProvider>
  );
  const user = userEvent.setup();
  await user.click(screen.getByRole('button', { name: '更正租金阶段' }));
  await user.type(screen.getByLabelText('更正原因'), 'proposal A');
  await user.click(screen.getByRole('button', { name: '预览更正影响' }));
  await user.type(screen.getByLabelText('更正原因'), ' changed to B');
  await act(async () =>
    finish({
      contract_id: 'contract',
      contract_version: 1,
      preview_token: 'old-token',
      expires_at: '2026-12-31T00:00:00Z',
      rent_schedules: [],
      impact: {
        created_count: 0,
        updated_count: 0,
        voided_count: 0,
        restored_count: 0,
        mismatched_entry_ids: [],
        warnings: [],
      },
    })
  );
  await screen.findByRole('button', { name: '预览更正影响' });
  expect(screen.queryByRole('button', { name: '确认更正租金阶段' })).toBeNull();
  expect(assetLedgerService.commitCorrection).not.toHaveBeenCalled();
  vi.mocked(assetLedgerService.previewCorrection).mockResolvedValue({
    contract_id: 'contract',
    contract_version: 1,
    preview_token: 'new-token',
    expires_at: '2026-12-31T00:00:00Z',
    rent_schedules: [],
    impact: {
      created_count: 0,
      updated_count: 0,
      voided_count: 0,
      restored_count: 0,
      mismatched_entry_ids: [],
      warnings: [],
    },
  });
  await user.click(screen.getByRole('button', { name: '预览更正影响' }));
  await user.click(await screen.findByRole('button', { name: '确认更正租金阶段' }));
  expect(assetLedgerService.commitCorrection).toHaveBeenCalledWith(
    'terminal',
    'contract',
    { preview_token: 'new-token', expected_version: 1 },
    expect.any(String)
  );
});
