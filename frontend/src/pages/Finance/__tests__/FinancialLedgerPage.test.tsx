import { beforeEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, renderWithProviders, screen, waitFor } from '@/test/utils/test-helpers';
import FinancialLedgerPage from '../FinancialLedgerPage';

vi.mock('@/services/ledgerService', () => ({
  ledgerService: {
    getLedgerEntries: vi.fn(),
    exportLedgerEntries: vi.fn(),
    triggerLedgerDownload: vi.fn(),
  },
}));

vi.mock('antd', async () => {
  const actual = await vi.importActual<typeof import('antd')>('antd');

  const MockRangePicker = ({
    value,
    onChange,
  }: {
    value?: unknown;
    onChange?: (value: null) => void;
  }) => (
    <div>
      <span data-testid="mock-range-picker-value">{Array.isArray(value) ? 'set' : 'empty'}</span>
      <button type="button" onClick={() => onChange?.(null)}>
        清空账期
      </button>
    </div>
  );

  return {
    ...actual,
    DatePicker: {
      ...actual.DatePicker,
      RangePicker: MockRangePicker,
    },
  };
});

vi.mock('@/utils/queryScope', () => ({
  buildQueryScopeKey: vi.fn(() => 'user:user-1|scope:owner,manager'),
}));

import { ledgerService } from '@/services/ledgerService';

describe('FinancialLedgerPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(ledgerService.getLedgerEntries).mockResolvedValue({
      items: [
        {
          entry_id: 'ledger-1',
          contract_id: 'contract-1',
          year_month: '2026-05',
          due_date: '2026-05-15',
          amount_due: '12000.00',
          currency_code: 'CNY',
          is_tax_included: true,
          tax_rate: '0.06',
          payment_status: 'overdue',
          paid_amount: '2000.00',
          notes: '逾期未收',
        },
      ],
      total: 1,
      offset: 0,
      limit: 20,
    });
    vi.mocked(ledgerService.exportLedgerEntries).mockResolvedValue(new Blob(['ledger']));
  });

  it('renders global financial ledger entries with business labels', async () => {
    renderWithProviders(<FinancialLedgerPage />);

    expect(await screen.findByText('财务台账')).toBeInTheDocument();
    expect(screen.getByText('跨项目查询合同应收、应付、实收、实付和逾期记录。')).toBeInTheDocument();

    await waitFor(() => {
      expect(ledgerService.getLedgerEntries).toHaveBeenCalledWith(
        expect.objectContaining({
          offset: 0,
          limit: 20,
          year_month_start: expect.stringMatching(/^\d{4}-\d{2}$/),
          year_month_end: expect.stringMatching(/^\d{4}-\d{2}$/),
        })
      );
    });

    expect(await screen.findByText('contract-1')).toBeInTheDocument();
    expect(screen.getByText('逾期')).toBeInTheDocument();
    expect(screen.getByText('逾期未收')).toBeInTheDocument();
  });

  it('does not query or export when required ledger filters are cleared', async () => {
    renderWithProviders(<FinancialLedgerPage />);

    await waitFor(() => {
      expect(ledgerService.getLedgerEntries).toHaveBeenCalledTimes(1);
    });

    const clearPeriodButton = screen.getByText('清空账期').closest('button');
    expect(clearPeriodButton).not.toBeNull();
    fireEvent.click(clearPeriodButton!);

    expect(await screen.findByText('请至少选择账期、合同、资产或主体后查询财务台账。')).toBeInTheDocument();
    expect(ledgerService.getLedgerEntries).toHaveBeenCalledTimes(1);
    expect(screen.getByRole('button', { name: /刷\s*新/ })).toBeDisabled();
    expect(screen.getByRole('button', { name: /导\s*出/ })).toBeDisabled();
  });

  it('shows an export error when global ledger export fails', async () => {
    vi.mocked(ledgerService.exportLedgerEntries).mockRejectedValue(new Error('导出接口失败'));

    renderWithProviders(<FinancialLedgerPage />);

    await waitFor(() => {
      expect(ledgerService.getLedgerEntries).toHaveBeenCalledTimes(1);
    });

    fireEvent.click(screen.getByRole('button', { name: /导\s*出/ }));

    expect(await screen.findByText('导出接口失败')).toBeInTheDocument();
    expect(ledgerService.triggerLedgerDownload).not.toHaveBeenCalled();
  });
});
