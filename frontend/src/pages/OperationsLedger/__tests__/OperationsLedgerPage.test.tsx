import { beforeEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, renderWithProviders, screen, waitFor, within } from '@/test/utils/test-helpers';
import OperationsLedgerPage from '../OperationsLedgerPage';

vi.mock('@/services/ledgerService', () => ({
  ledgerService: {
    getLedgerEntries: vi.fn(),
    exportLedgerEntries: vi.fn(),
    createPaymentFlow: vi.fn(),
    savePaymentFlowAllocations: vi.fn(),
    generateServiceFees: vi.fn(),
    updateLedgerEntryFollowUp: vi.fn(),
    triggerLedgerDownload: vi.fn(),
  },
}));

vi.mock('antd', async () => {
  const actual = await vi.importActual<typeof import('antd')>('antd');

  const MockRangePicker = ({
    value,
    onChange,
    picker,
  }: {
    value?: unknown;
    picker?: string;
    onChange?: (value: null) => void;
  }) => (
    <div>
      <span data-testid={`${picker === 'month' ? 'month' : 'date'}-range-picker-value`}>
        {Array.isArray(value) ? 'set' : 'empty'}
      </span>
      <button
        type="button"
        aria-label={picker === 'month' ? '清空账期' : '清空流水日期'}
        onClick={() => onChange?.(null)}
      >
        {picker === 'month' ? '清空账期' : '清空流水日期'}
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

const selectFirstLedgerRow = () => {
  const rowSelectionRadios = screen.getAllByRole('radio').filter(radio => {
    const label = radio.closest('label');
    return label?.classList.contains('ant-radio-wrapper') === true;
  });
  expect(rowSelectionRadios).toHaveLength(1);
  fireEvent.click(rowSelectionRadios[0]);
};

describe('OperationsLedgerPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(ledgerService.getLedgerEntries).mockResolvedValue({
      items: [
        {
          entry_id: 'ledger-1',
          contract_id: 'contract-1',
          year_month: '2026-05',
          due_date: '2020-05-15',
          amount_due: '12000.00',
          ledger_views: ['terminal_collection'],
          flow_occurred_on_dates: ['2026-05-10'],
          currency_code: 'CNY',
          is_tax_included: true,
          tax_rate: '0.06',
          payment_status: 'partial',
          paid_amount: '2000.00',
          follow_up_status: 'pending_follow_up',
          next_follow_up_date: '2026-05-20',
          follow_up_note: '待电话确认',
          attributed_project_id: 'project-1',
          attributed_operator_party_id: 'operator-party-1',
          attributed_asset_ids: ['asset-1'],
          notes: '逾期未收',
        },
      ],
      total: 1,
      offset: 0,
      limit: 20,
    });
    vi.mocked(ledgerService.exportLedgerEntries).mockResolvedValue(new Blob(['ledger']));
    vi.mocked(ledgerService.createPaymentFlow).mockResolvedValue({
      flow_id: 'flow-1',
      flow_type: 'terminal_rent_receipt',
      occurred_on: '2026-05-10',
      amount: '10000.00',
      registered_by: 'operator',
      status: 'active',
    });
    vi.mocked(ledgerService.savePaymentFlowAllocations).mockResolvedValue([
      {
        allocation_id: 'allocation-1',
        flow_id: 'flow-1',
        target_type: 'contract_ledger_entry',
        target_id: 'ledger-1',
        year_month: '2026-05',
        amount: '10000.00',
      },
    ]);
    vi.mocked(ledgerService.generateServiceFees).mockResolvedValue({
      created: 1,
      updated: 0,
      voided: 0,
      source_mismatches: 0,
    });
    vi.mocked(ledgerService.updateLedgerEntryFollowUp).mockResolvedValue({
      entry_id: 'ledger-1',
      contract_id: 'contract-1',
      year_month: '2026-05',
      due_date: '2026-05-15',
      amount_due: '12000.00',
      ledger_views: ['terminal_collection'],
      currency_code: 'CNY',
      is_tax_included: true,
      payment_status: 'partial',
      paid_amount: '2000.00',
      follow_up_status: 'pending_follow_up',
    });
  });

  it('renders terminal collection entries with operations-ledger filters', async () => {
    renderWithProviders(<OperationsLedgerPage />);

    expect(await screen.findByText('经营台账')).toBeInTheDocument();
    expect(screen.getByText('按经营视图查询收缴、收入、成本和服务费结算。')).toBeInTheDocument();

    await waitFor(() => {
      expect(ledgerService.getLedgerEntries).toHaveBeenCalledWith(
        expect.objectContaining({
          ledger_view: 'terminal_collection',
          offset: 0,
          limit: 20,
          year_month_start: expect.stringMatching(/^\d{4}-\d{2}$/),
          year_month_end: expect.stringMatching(/^\d{4}-\d{2}$/),
        })
      );
    });

    expect(await screen.findByText('contract-1')).toBeInTheDocument();
    expect(screen.getByText('逾期')).toBeInTheDocument();
    expect(screen.getByText('待跟进')).toBeInTheDocument();
  });

  it('does not query or export when required ledger filters are cleared', async () => {
    renderWithProviders(<OperationsLedgerPage />);

    await waitFor(() => {
      expect(ledgerService.getLedgerEntries).toHaveBeenCalledTimes(1);
    });

    fireEvent.click(screen.getByRole('button', { name: '清空账期' }));

    expect(
      await screen.findByText('请至少选择账期、项目、合同、资产、主体或流水日期后查询经营台账。')
    ).toBeInTheDocument();
    expect(ledgerService.getLedgerEntries).toHaveBeenCalledTimes(1);
    expect(screen.getByRole('button', { name: /刷\s*新/ })).toBeDisabled();
    expect(screen.getByRole('button', { name: /导\s*出/ })).toBeDisabled();
  });

  it('shows an export error when global ledger export fails', async () => {
    vi.mocked(ledgerService.exportLedgerEntries).mockRejectedValue(new Error('导出接口失败'));

    renderWithProviders(<OperationsLedgerPage />);

    await waitFor(() => {
      expect(ledgerService.getLedgerEntries).toHaveBeenCalledTimes(1);
    });

    fireEvent.click(screen.getByRole('button', { name: /导\s*出/ }));

    expect(await screen.findByText('导出接口失败')).toBeInTheDocument();
    expect(ledgerService.triggerLedgerDownload).not.toHaveBeenCalled();
  });

  it('registers terminal receipt flows and allocations for selected entries', async () => {
    renderWithProviders(<OperationsLedgerPage />);

    expect(await screen.findByText('contract-1')).toBeInTheDocument();

    selectFirstLedgerRow();
    fireEvent.click(screen.getByRole('button', { name: /登记收款/ }));
    fireEvent.change(screen.getByLabelText('经办人'), { target: { value: 'operator' } });
    fireEvent.click(within(screen.getByRole('dialog')).getByRole('button', { name: /登\s*记/ }));

    await waitFor(() => {
      expect(ledgerService.createPaymentFlow).toHaveBeenCalledWith(
        expect.objectContaining({
          flow_type: 'terminal_rent_receipt',
          amount: 10000,
          registered_by: 'operator',
          counterparty_id: 'operator-party-1',
        })
      );
    });
    expect(ledgerService.savePaymentFlowAllocations).toHaveBeenCalledWith('flow-1', [
      {
        target_type: 'contract_ledger_entry',
        target_id: 'ledger-1',
        year_month: '2026-05',
        amount: 10000,
      },
    ]);
  });

  it('updates terminal follow-up state for selected entries', async () => {
    renderWithProviders(<OperationsLedgerPage />);

    expect(await screen.findByText('contract-1')).toBeInTheDocument();

    selectFirstLedgerRow();
    fireEvent.click(screen.getByRole('button', { name: /维护跟进/ }));
    fireEvent.click(within(screen.getByRole('dialog')).getByRole('button', { name: /保\s*存/ }));

    await waitFor(() => {
      expect(ledgerService.updateLedgerEntryFollowUp).toHaveBeenCalledWith('ledger-1', {
        follow_up_status: 'pending_follow_up',
        next_follow_up_date: '2026-05-20',
        follow_up_note: '待电话确认',
      });
    });
  });

  it('generates service fees from the service-fee settlement view', async () => {
    renderWithProviders(<OperationsLedgerPage />);

    fireEvent.click(screen.getByText('服务费结算'));
    fireEvent.change(screen.getByLabelText('合同组 ID'), {
      target: { value: 'group-1' },
    });
    fireEvent.click(screen.getByRole('button', { name: /生成服务费/ }));

    await waitFor(() => {
      expect(ledgerService.generateServiceFees).toHaveBeenCalledWith({
        contract_group_id: 'group-1',
      });
    });
  });
});
