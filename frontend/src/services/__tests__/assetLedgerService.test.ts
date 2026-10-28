import { beforeEach, expect, it, vi } from 'vitest';
import { apiClient } from '@/api/client';
import { AxiosError, AxiosHeaders } from 'axios';
import { assetLedgerService, isLedgerForbidden } from '../assetLedgerService';

vi.mock('@/api/client', () => ({ apiClient: { get: vi.fn(), post: vi.fn() } }));
beforeEach(() => vi.clearAllMocks());

it.each(['get', 'post'] as const)('normalizes a rejected HTTP 403 from %s', async method => {
  const rejection = new AxiosError(
    'Request failed with status code 403',
    'ERR_BAD_REQUEST',
    undefined,
    undefined,
    {
      status: 403,
      statusText: 'Forbidden',
      headers: {},
      config: { headers: new AxiosHeaders() },
      data: { success: false, error: { code: 'PARTY_SCOPE_MISSING', message: '无有效范围' } },
    }
  );
  vi.mocked(apiClient[method]).mockRejectedValueOnce(rejection);
  const request =
    method === 'get'
      ? assetLedgerService.getMatrix('terminal_rent', 2026)
      : assetLedgerService.record(
          'entry-1',
          { record_type: 'receipt', amount: 1, occurred_on: '2026-10-28', expected_version: 1 },
          'key'
        );
  const error: unknown = await request.catch(value => value);
  expect(error).toMatchObject({ code: 'PARTY_SCOPE_MISSING' });
  expect(isLedgerForbidden(error)).toBe(true);
});

it('converts ledger Decimal amounts through the shared recursive converter', async () => {
  vi.mocked(apiClient.get).mockResolvedValue({
    success: true,
    data: {
      id: 'entry-1',
      due_amount: '100.00',
      effective_paid_amount: '40.00',
      remaining_amount: '60.00',
      records: [{ amount: '40.00' }],
    },
  });
  const entry = await assetLedgerService.getEntry('entry-1');
  expect(entry.due_amount).toBe(100);
  expect(entry.effective_paid_amount).toBe(40);
  expect(entry.remaining_amount).toBe(60);
  expect(entry.records[0]?.amount).toBe(40);
});

it('serializes payment amount and preserves the explicit idempotency header', async () => {
  vi.mocked(apiClient.post).mockResolvedValue({
    success: true,
    data: { id: 'record-1', amount: '25.00', version: 2 },
  });
  await assetLedgerService.record(
    'entry-1',
    { record_type: 'receipt', amount: 25, occurred_on: '2026-10-27', expected_version: 1 },
    'request-1'
  );
  expect(apiClient.post).toHaveBeenCalledWith(
    '/api/v1/rent-ledger-entries/entry-1/records',
    expect.objectContaining({ amount: '25' }),
    expect.objectContaining({ headers: { 'Idempotency-Key': 'request-1' }, retry: false })
  );
});

it('keeps a scope denial distinct from an empty matrix', async () => {
  vi.mocked(apiClient.get).mockResolvedValue({
    success: false,
    error: '无有效范围',
    rawResponse: { data: { error: { code: 'PARTY_SCOPE_MISSING' } } },
  });
  await expect(assetLedgerService.getMatrix('terminal_rent', 2026)).rejects.toMatchObject({
    code: 'PARTY_SCOPE_MISSING',
  });
});
