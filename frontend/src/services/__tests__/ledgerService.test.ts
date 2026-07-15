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

  it('lists payment flows for one allocation target', async () => {
    vi.mocked(apiClient.get).mockResolvedValue({
      success: true,
      data: [
        {
          flow_id: 'flow-1',
          flow_type: 'terminal_rent_receipt',
          occurred_on: '2026-05-10',
          amount: '1000.00',
          registered_by: 'operator',
          status: 'active',
          corrected_from_flow_id: null,
          status_changed_by: null,
          status_changed_at: null,
          status_change_reason: null,
          allocations: [],
          voucher_attachments: [],
        },
      ],
    });

    const result = await service.listPaymentFlows({
      target_type: 'contract_ledger_entry',
      target_id: 'entry-1',
    });

    expect(apiClient.get).toHaveBeenCalledWith('/ledger/payment-flows', {
      params: {
        target_type: 'contract_ledger_entry',
        target_id: 'entry-1',
      },
      cache: false,
      retry: { maxAttempts: 2, delay: 500, backoffMultiplier: 2 },
      smartExtract: true,
    });
    expect(result[0].flow_id).toBe('flow-1');
  });

  it('voids an active payment flow with an explicit reason', async () => {
    vi.mocked(apiClient.post).mockResolvedValue({
      success: true,
      data: {
        flow_id: 'flow-1',
        flow_type: 'terminal_rent_receipt',
        occurred_on: '2026-05-10',
        amount: '1000.00',
        registered_by: 'operator',
        status: 'voided',
        status_change_reason: '重复登记',
      },
    });

    const result = await service.voidPaymentFlow('flow-1', { reason: '重复登记' });

    expect(apiClient.post).toHaveBeenCalledWith(
      '/ledger/payment-flows/flow-1/void',
      { reason: '重复登记' },
      { retry: false, smartExtract: true }
    );
    expect(result.status).toBe('voided');
  });

  it('corrects a payment flow with one atomic replacement payload', async () => {
    vi.mocked(apiClient.post).mockResolvedValue({
      success: true,
      data: {
        flow_id: 'flow-2',
        flow_type: 'terminal_rent_receipt',
        occurred_on: '2026-05-11',
        amount: '900.00',
        registered_by: 'operator',
        status: 'active',
        corrected_from_flow_id: 'flow-1',
      },
    });
    const payload = {
      reason: '金额录入错误',
      replacement: {
        flow_type: 'terminal_rent_receipt' as const,
        occurred_on: '2026-05-11',
        amount: '900.00',
        counterparty_id: 'tenant-1',
      },
      allocations: [
        {
          target_type: 'contract_ledger_entry' as const,
          target_id: 'entry-1',
          year_month: '2026-05',
          amount: '900.00',
        },
      ],
    };

    const result = await service.correctPaymentFlow('flow-1', payload);

    expect(apiClient.post).toHaveBeenCalledWith('/ledger/payment-flows/flow-1/correct', payload, {
      retry: false,
      smartExtract: true,
    });
    expect(result.corrected_from_flow_id).toBe('flow-1');
  });

  it('downloads a voucher only through the audited payment-flow endpoint', async () => {
    const blob = new Blob(['voucher']);
    vi.mocked(apiClient.get).mockResolvedValue({ success: true, data: blob });

    const result = await service.downloadPaymentFlowVoucher('flow-1', 'attachment-1');

    expect(apiClient.get).toHaveBeenCalledWith(
      '/ledger/payment-flows/flow-1/vouchers/attachment-1/download',
      {
        cache: false,
        retry: false,
        responseType: 'blob',
        smartExtract: false,
      }
    );
    expect(result).toBe(blob);
  });

  it('uploads a voucher as the payment-flow file field', async () => {
    const file = new File(['voucher'], 'receipt.pdf', { type: 'application/pdf' });
    vi.mocked(apiClient.post).mockResolvedValue({
      success: true,
      data: {
        id: 'attachment-1',
        file_name: 'receipt.pdf',
        file_type: 'application/pdf',
        file_size: 7,
      },
    });

    const result = await service.uploadPaymentFlowVoucher('flow-1', file);

    const [url, body, options] = vi.mocked(apiClient.post).mock.calls[0];
    expect(url).toBe('/ledger/payment-flows/flow-1/vouchers');
    expect(body).toBeInstanceOf(FormData);
    expect((body as FormData).get('file')).toBe(file);
    expect(options).toEqual({
      headers: { 'Content-Type': 'multipart/form-data' },
      retry: false,
      smartExtract: true,
    });
    expect(result.file_name).toBe('receipt.pdf');
  });

  it('lists voucher download audit evidence for one payment flow', async () => {
    vi.mocked(apiClient.get).mockResolvedValue({
      success: true,
      data: [
        {
          log_id: 'audit-1',
          user_id: 'user-1',
          flow_id: 'flow-1',
          attachment_id: 'attachment-1',
          file_name: 'receipt.pdf',
          downloaded_at: '2026-05-12T10:00:00Z',
        },
      ],
    });

    const result = await service.listPaymentFlowVoucherDownloadAudits('flow-1');

    expect(apiClient.get).toHaveBeenCalledWith(
      '/ledger/payment-flows/flow-1/voucher-download-audits',
      {
        cache: false,
        retry: { maxAttempts: 2, delay: 500, backoffMultiplier: 2 },
        smartExtract: true,
      }
    );
    expect(result[0].log_id).toBe('audit-1');
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

    const result = await service.listServiceFees({ contract_group_id: 'group-1' });

    expect(apiClient.get).toHaveBeenCalledWith('/ledger/service-fees', {
      params: { contract_group_id: 'group-1' },
      cache: false,
      retry: { maxAttempts: 2, delay: 500, backoffMultiplier: 2 },
      smartExtract: true,
    });
    expect(result[0].source_ledger_ids).toEqual(['rent-ledger-1']);
  });

  it('lists service-fee ledgers by project', async () => {
    vi.mocked(apiClient.get).mockResolvedValue({ success: true, data: [] });

    await service.listServiceFees({ project_id: 'project-1' });

    expect(apiClient.get).toHaveBeenCalledWith('/ledger/service-fees', {
      params: { project_id: 'project-1' },
      cache: false,
      retry: { maxAttempts: 2, delay: 500, backoffMultiplier: 2 },
      smartExtract: true,
    });
  });

  it('reconciles a service-fee ledger source with an explicit reason', async () => {
    vi.mocked(apiClient.post).mockResolvedValue({
      success: true,
      data: {
        service_fee_entry_id: 'service-fee-1',
        contract_group_id: 'group-1',
        agency_contract_id: 'contract-direct-1',
        agency_agreement_contract_id: 'contract-entrust-1',
        source_ledger_ids: ['rent-ledger-current'],
        year_month: '2026-05',
        amount_due: '50.00',
        paid_amount: '20.00',
        payment_status: 'partial',
        currency_code: 'CNY',
        service_fee_ratio: '0.1000',
        calculation_base_amount: '500.00',
      },
    });

    const result = await service.reconcileServiceFeeSource('service-fee-1', {
      reason: '确认采用当前租金台账来源',
    });

    expect(apiClient.post).toHaveBeenCalledWith(
      '/ledger/service-fees/service-fee-1/reconcile',
      { reason: '确认采用当前租金台账来源' },
      { retry: false, smartExtract: true }
    );
    expect(result.source_ledger_ids).toEqual(['rent-ledger-current']);
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
