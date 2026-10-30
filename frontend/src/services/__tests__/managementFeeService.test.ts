import { beforeEach, expect, it, vi } from 'vitest';
import { apiClient } from '@/api/client';
import { managementFeeService } from '@/services/managementFeeService';
import { AxiosError } from 'axios';

vi.mock('@/api/client', () => ({ apiClient: { get: vi.fn(), post: vi.fn() } }));
beforeEach(() => vi.clearAllMocks());

it('loads the yearly fee matrix and converts confirmed totals', async () => {
  vi.mocked(apiClient.get).mockResolvedValue({
    success: true,
    data: {
      ledger_type: 'management_fee',
      year: 2026,
      current_month: 10,
      rows: [
        {
          owner_party_id: '001',
          total_confirmed_amount: '12.34',
          months: [{ month: 10, fee_amount: '12.34' }],
        },
      ],
      total_confirmed_amount: '12.34',
    },
  });
  const result = await managementFeeService.matrix(2026);
  expect(apiClient.get).toHaveBeenCalledWith('/api/v1/rent-ledgers', {
    cache: false,
    params: { ledger_type: 'management_fee', year: 2026 },
  });
  expect(result.total_confirmed_amount).toBe(12.34);
  expect(result.rows[0]?.total_confirmed_amount).toBe(12.34);
  expect(result.rows[0]?.owner_party_id).toBe('001');
});

it('converts nested fee amounts while preserving identifiers', async () => {
  vi.mocked(apiClient.get).mockResolvedValue({
    success: true,
    data: {
      id: 'statement',
      base_amount: '4000.00',
      fee_amount: '400.00',
      lines: [
        {
          scheduled_rent: '10000.00',
          owner_received_amount: '4000.00',
          deferred_amount: '6000.00',
          fee_rate: '0.1',
          fee_amount: '400.00',
        },
      ],
    },
  });
  const result = await managementFeeService.get('statement');
  expect(result.base_amount).toBe(4000);
  expect(result.lines[0]).toEqual({
    scheduled_rent: 10000,
    owner_received_amount: 4000,
    deferred_amount: 6000,
    fee_rate: 0.1,
    fee_amount: 400,
  });
  expect(result.id).toBe('statement');
});

it('serializes owner receipts and sends a stable command key', async () => {
  vi.mocked(apiClient.post).mockResolvedValue({
    success: true,
    data: { id: 'record', version: 2 },
  });
  await managementFeeService.record(
    'st/1',
    { rent_ledger_entry_id: 'rent', amount: 40, occurred_on: '2026-10-29', expected_version: 1 },
    'key'
  );
  expect(apiClient.post).toHaveBeenCalledWith(
    '/api/v1/management-fee-statements/st%2F1/owner-receipts',
    expect.objectContaining({ amount: '40' }),
    expect.objectContaining({ retry: false, headers: { 'Idempotency-Key': 'key' } })
  );
});

it('uploads multipart without overriding its boundary header', async () => {
  vi.mocked(apiClient.post).mockResolvedValue({ success: true, data: { fee_amount: '12.00' } });
  const file = new File(['pdf'], 'stamp.pdf', { type: 'application/pdf' });
  const result = await managementFeeService.upload('st', file, 2);
  const call = vi.mocked(apiClient.post).mock.calls[0];
  expect(call?.[1]).toBeInstanceOf(FormData);
  const form = call?.[1] as FormData;
  expect(form.get('file')).toBe(file);
  expect(form.get('expected_version')).toBe('2');
  expect(call?.[2]).toEqual({ retry: false });
  expect(result.fee_amount).toBe(12);
});

it('preserves business errors rather than returning an empty statement', async () => {
  vi.mocked(apiClient.get).mockResolvedValue({
    success: false,
    error: '无权限',
    rawResponse: { data: { error: { code: 'PARTY_SCOPE_MISSING' } } },
  });
  await expect(managementFeeService.list('2026-10')).rejects.toMatchObject({
    code: 'PARTY_SCOPE_MISSING',
  });
});

it('reads the requested month without caching and converts list amounts', async () => {
  vi.mocked(apiClient.get).mockResolvedValue({
    success: true,
    data: {
      items: [{ id: '001', base_amount: '0.00', fee_amount: '12.34', lines: [] }],
      total: 1,
    },
  });
  const result = await managementFeeService.list('2026-10');
  expect(apiClient.get).toHaveBeenCalledWith('/api/v1/management-fee-statements', {
    cache: false,
    params: { period: '2026-10' },
  });
  expect(result.items[0]).toEqual({ id: '001', base_amount: 0, fee_amount: 12.34, lines: [] });
});

it('sends deferral, confirmation and correction with their versions and stable keys', async () => {
  vi.mocked(apiClient.post).mockResolvedValue({
    success: true,
    data: {
      statement_id: 'st',
      version: 4,
      idempotent: true,
      successor_statement_id: 'next',
    },
  });
  const deferred = { rent_ledger_entry_id: 'rent', reason: '待核实', expected_version: 3 };
  await managementFeeService.defer('st/1', deferred, 'defer-key');
  await managementFeeService.confirm('st/1', { expected_version: 3 }, 'confirm-key');
  const correction = await managementFeeService.supersede(
    'st/1',
    { expected_version: 3, reason: '更正金额' },
    'correct-key'
  );
  expect(apiClient.post).toHaveBeenNthCalledWith(
    1,
    '/api/v1/management-fee-statements/st%2F1/deferrals',
    deferred,
    { retry: false, headers: { 'Idempotency-Key': 'defer-key' } }
  );
  expect(apiClient.post).toHaveBeenNthCalledWith(
    2,
    '/api/v1/management-fee-statements/st%2F1/confirmation',
    { expected_version: 3 },
    { retry: false, headers: { 'Idempotency-Key': 'confirm-key' } }
  );
  expect(apiClient.post).toHaveBeenNthCalledWith(
    3,
    '/api/v1/management-fee-statements/st%2F1/successor',
    { expected_version: 3, reason: '更正金额' },
    { retry: false, headers: { 'Idempotency-Key': 'correct-key' } }
  );
  expect(correction).toMatchObject({
    successor_statement_id: 'next',
    idempotent: true,
    version: 4,
  });
});

it('rejects a successful envelope without data', async () => {
  vi.mocked(apiClient.get).mockResolvedValue({ success: true, data: null });
  await expect(managementFeeService.get('st')).rejects.toMatchObject({
    code: 'INVALID_RESPONSE_DATA',
  });
});

it('preserves thrown HTTP business errors', async () => {
  const error = new AxiosError('Conflict');
  error.response = {
    data: { error: { code: 'VERSION_CONFLICT', message: '请刷新' } },
    status: 409,
    statusText: 'Conflict',
    headers: {},
    config: { headers: {} },
  } as typeof error.response;
  vi.mocked(apiClient.post).mockRejectedValue(error);
  await expect(
    managementFeeService.confirm('st', { expected_version: 1 }, 'key')
  ).rejects.toMatchObject({ code: 'VERSION_CONFLICT', message: '请刷新' });
});
