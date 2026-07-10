import { beforeEach, describe, expect, it, vi } from 'vitest';
import { LedgerService } from '../ledgerService';

vi.mock('@/api/client', () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
  },
}));

vi.mock('@/utils/responseExtractor', () => ({
  ApiErrorHandler: {
    handleError: vi.fn(error => ({
      message: error instanceof Error ? error.message : 'Unknown error',
      code: 'UNKNOWN',
    })),
  },
}));

import { apiClient } from '@/api/client';

describe('LedgerService', () => {
  let service: LedgerService;

  beforeEach(() => {
    service = new LedgerService();
    vi.clearAllMocks();
  });

  it('fetches global ledger entries with compact filters', async () => {
    vi.mocked(apiClient.get).mockResolvedValue({
      success: true,
      data: {
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
            payment_status: 'partial',
            paid_amount: '2000.00',
          },
        ],
        total: 1,
        offset: 0,
        limit: 20,
      },
    });

    const result = await service.getLedgerEntries({
      year_month_start: '2026-05',
      year_month_end: '2026-05',
      payment_status: 'partial',
      contract_id: '',
      offset: 0,
      limit: 20,
    });

    expect(apiClient.get).toHaveBeenCalledWith('/ledger/entries', {
      params: {
        year_month_start: '2026-05',
        year_month_end: '2026-05',
        payment_status: 'partial',
        offset: 0,
        limit: 20,
      },
      cache: false,
      retry: { maxAttempts: 2, delay: 500, backoffMultiplier: 2 },
      smartExtract: true,
    });
    expect(result.items[0].payment_status).toBe('partial');
  });

  it('throws when the ledger API returns failure', async () => {
    vi.mocked(apiClient.get).mockResolvedValue({
      success: false,
      error: 'bad ledger',
    });

    await expect(
      service.getLedgerEntries({
        year_month_start: '2026-05',
      })
    ).rejects.toThrow('获取经营台账失败: bad ledger');
  });

  it('exports global ledger entries as a blob', async () => {
    const blob = new Blob(['ledger']);
    vi.mocked(apiClient.get).mockResolvedValue({
      success: true,
      data: blob,
    });

    const result = await service.exportLedgerEntries(
      {
        year_month_start: '2026-05',
        payment_status: 'paid',
      },
      'csv'
    );

    expect(apiClient.get).toHaveBeenCalledWith('/ledger/entries/export', {
      params: {
        year_month_start: '2026-05',
        payment_status: 'paid',
        export_format: 'csv',
      },
      cache: false,
      retry: false,
      responseType: 'blob',
      smartExtract: false,
    });
    expect(result).toBe(blob);
  });

  it('recalculates contract ledger and returns skipped paid entries', async () => {
    vi.mocked(apiClient.post).mockResolvedValue({
      success: true,
      data: {
        created: 1,
        updated: 0,
        voided: 0,
        skipped_entries: [
          {
            entry_id: 'ledger-paid',
            year_month: '2026-05',
            payment_status: 'paid',
            reason: 'paid_or_partial_entry_requires_manual_resolution',
          },
        ],
      },
    });

    const result = await service.recalculateContractLedger('contract-1');

    expect(apiClient.post).toHaveBeenCalledWith(
      '/contracts/contract-1/ledger/recalculate',
      {},
      {
        retry: false,
        smartExtract: true,
      }
    );
    expect(result.skipped_entries).toHaveLength(1);
    expect(result.skipped_entries[0].entry_id).toBe('ledger-paid');
  });

  it('creates a payment flow and saves allocations', async () => {
    vi.mocked(apiClient.post)
      .mockResolvedValueOnce({
        success: true,
        data: {
          flow_id: 'flow-1',
          flow_type: 'terminal_rent_receipt',
          occurred_on: '2026-05-10',
          amount: '1000.00',
          registered_by: 'operator',
          status: 'active',
        },
      })
      .mockResolvedValueOnce({
        success: true,
        data: [
          {
            allocation_id: 'allocation-1',
            flow_id: 'flow-1',
            target_type: 'contract_ledger_entry',
            target_id: 'entry-1',
            year_month: '2026-05',
            amount: '1000.00',
          },
        ],
      });

    const flow = await service.createPaymentFlow({
      flow_type: 'terminal_rent_receipt',
      occurred_on: '2026-05-10',
      amount: '1000.00',
      registered_by: 'operator',
    });
    const allocations = await service.savePaymentFlowAllocations(flow.flow_id, [
      {
        target_type: 'contract_ledger_entry',
        target_id: 'entry-1',
        year_month: '2026-05',
        amount: '1000.00',
      },
    ]);

    expect(apiClient.post).toHaveBeenNthCalledWith(
      1,
      '/ledger/payment-flows',
      {
        flow_type: 'terminal_rent_receipt',
        occurred_on: '2026-05-10',
        amount: '1000.00',
        registered_by: 'operator',
      },
      {
        retry: false,
        smartExtract: true,
      }
    );
    expect(apiClient.post).toHaveBeenNthCalledWith(
      2,
      '/ledger/payment-flows/flow-1/allocations',
      {
        allocations: [
          {
            target_type: 'contract_ledger_entry',
            target_id: 'entry-1',
            year_month: '2026-05',
            amount: '1000.00',
          },
        ],
      },
      {
        retry: false,
        smartExtract: true,
      }
    );
    expect(allocations[0].allocation_id).toBe('allocation-1');
  });

  it('lists service-fee ledgers by contract group', async () => {
    vi.mocked(apiClient.get).mockResolvedValue({
      success: true,
      data: [
        {
          service_fee_entry_id: 'service-fee-1',
          contract_group_id: 'group-1',
          agency_contract_id: 'contract-direct-1',
          agency_agreement_contract_id: 'contract-entrust-1',
          source_ledger_ids: ['rent-ledger-1'],
          year_month: '2026-05',
          amount_due: '50.00',
          paid_amount: '20.00',
          payment_status: 'partial',
          currency_code: 'CNY',
          service_fee_ratio: '0.1000',
          calculation_base_amount: '500.00',
        },
      ],
    });

    const result = await service.listServiceFees('group-1');

    expect(apiClient.get).toHaveBeenCalledWith('/ledger/service-fees', {
      params: { contract_group_id: 'group-1' },
      cache: false,
      retry: { maxAttempts: 2, delay: 500, backoffMultiplier: 2 },
      smartExtract: true,
    });
    expect(result[0].source_ledger_ids).toEqual(['rent-ledger-1']);
  });

  it('generates service fees and updates follow-up state', async () => {
    vi.mocked(apiClient.post).mockResolvedValue({
      success: true,
      data: { created: 1, updated: 0, voided: 0, source_mismatches: 0 },
    });
    vi.mocked(apiClient.patch).mockResolvedValue({
      success: true,
      data: {
        entry_id: 'entry-1',
        contract_id: 'contract-1',
        year_month: '2026-05',
        due_date: '2026-05-31',
        amount_due: '1000.00',
        ledger_views: ['terminal_collection'],
        currency_code: 'CNY',
        is_tax_included: true,
        payment_status: 'unpaid',
        paid_amount: '0',
        follow_up_status: 'contacted',
      },
    });

    const generateResult = await service.generateServiceFees({ contract_group_id: 'group-1' });
    const entry = await service.updateLedgerEntryFollowUp('entry-1', {
      follow_up_status: 'contacted',
      next_follow_up_date: '2026-05-20',
      follow_up_note: '已联系',
    });

    expect(apiClient.post).toHaveBeenCalledWith(
      '/ledger/service-fees/generate',
      { contract_group_id: 'group-1' },
      {
        retry: false,
        smartExtract: true,
      }
    );
    expect(apiClient.patch).toHaveBeenCalledWith(
      '/ledger/entries/entry-1/follow-up',
      {
        follow_up_status: 'contacted',
        next_follow_up_date: '2026-05-20',
        follow_up_note: '已联系',
      },
      {
        retry: false,
        smartExtract: true,
      }
    );
    expect(generateResult.created).toBe(1);
    expect(entry.follow_up_status).toBe('contacted');
  });
});
