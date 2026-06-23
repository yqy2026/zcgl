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
    ).rejects.toThrow('获取财务台账失败: bad ledger');
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

  it('registers received ledger amounts through the contract ledger endpoint', async () => {
    vi.mocked(apiClient.patch).mockResolvedValue({
      success: true,
      data: [
        {
          entry_id: 'ledger-1',
          contract_id: 'contract-1',
          year_month: '2026-05',
          due_date: '2026-05-15',
          amount_due: '12000.00',
          currency_code: 'CNY',
          is_tax_included: true,
          payment_status: 'paid',
          paid_amount: '12000.00',
        },
      ],
    });

    const result = await service.updateContractLedgerStatus('contract-1', {
      entry_ids: ['ledger-1'],
      paid_amount: '12000.00',
      notes: '实收登记',
    });

    expect(apiClient.patch).toHaveBeenCalledWith(
      '/contracts/contract-1/ledger/batch-update-status',
      {
        entry_ids: ['ledger-1'],
        paid_amount: '12000.00',
        notes: '实收登记',
      },
      {
        retry: false,
      }
    );
    expect(result[0].payment_status).toBe('paid');
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
});
