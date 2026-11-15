import { expect, it, vi } from 'vitest';
import { apiClient } from '@/api/client';
import { archiveDocumentService } from '@/services/archiveDocumentService';
import { AxiosError, AxiosHeaders } from 'axios';
import { ApiErrorHandler } from '@/utils/responseExtractor';
import { AssetOperationsError } from '@/services/assetOperationsService';

vi.mock('@/api/client', () => ({
  apiClient: { get: vi.fn(), post: vi.fn(), getAxiosInstance: vi.fn() },
}));

it('keeps supplement targets separate from certificate targets', async () => {
  vi.mocked(apiClient.post).mockResolvedValue({ success: true, data: { id: 'new' } });
  vi.mocked(apiClient.get).mockResolvedValue({ success: true, data: { items: [] } });
  await archiveDocumentService.upload(
    'supp',
    new File(['scan'], '协议.pdf'),
    'contract_supplement'
  );
  const body = vi.mocked(apiClient.post).mock.calls.at(-1)![1] as FormData;
  expect(body.get('target_type')).toBe('contract_supplement');
  expect(body.get('document_type')).toBe('supplement');
  await archiveDocumentService.list('supp', 'contract_supplement');
  expect(apiClient.get).toHaveBeenLastCalledWith(
    '/api/v1/archive/documents',
    expect.objectContaining({
      params: expect.objectContaining({
        target_type: 'contract_supplement',
        document_type: 'supplement',
      }),
    })
  );
});

it('uploads one file with its certificate target and disables mutation retries', async () => {
  vi.mocked(apiClient.post).mockResolvedValue({ success: true, data: { id: 'new' } });
  const file = new File(['scan'], '证照.pdf', { type: 'application/pdf' });
  await archiveDocumentService.upload('cert', file);
  const [url, body, config] = vi.mocked(apiClient.post).mock.calls.at(-1)!;
  expect(url).toBe('/api/v1/archive/documents');
  expect(body).toBeInstanceOf(FormData);
  expect((body as FormData).get('target_id')).toBe('cert');
  expect((body as FormData).get('file')).toBe(file);
  expect(config).toEqual({ retry: false });
});

it('replaces a document by its archive ID without changing its target', async () => {
  vi.mocked(apiClient.post).mockResolvedValue({ success: true, data: { id: 'next' } });
  await archiveDocumentService.replace('doc/a', new File(['new'], '新.pdf'));
  expect(apiClient.post).toHaveBeenLastCalledWith(
    '/api/v1/archive/documents/doc%2Fa/replacement',
    expect.any(FormData),
    { retry: false }
  );
});

it('loads all versions without exposing a storage path', async () => {
  vi.mocked(apiClient.get).mockResolvedValue({ success: true, data: { items: [] } });
  expect(await archiveDocumentService.list('cert/a')).toEqual([]);
  expect(apiClient.get).toHaveBeenCalledWith(
    '/api/v1/archive/documents',
    expect.objectContaining({
      params: expect.objectContaining({ target_id: 'cert/a', include_history: true }),
    })
  );
});

it('preserves a scope error from a real enhanced Blob response', async () => {
  const blob = new Blob(['error'], { type: 'application/json' });
  Object.defineProperty(blob, 'text', {
    value: async () => JSON.stringify({ error: { code: 'PARTY_SCOPE_MISSING' } }),
  });
  const original = new AxiosError('Forbidden', 'ERR_BAD_REQUEST', undefined, undefined, {
    status: 403,
    statusText: 'Forbidden',
    headers: {},
    config: { headers: new AxiosHeaders() },
    data: blob,
  });
  vi.mocked(apiClient.getAxiosInstance).mockReturnValue({
    get: vi.fn().mockRejectedValue(ApiErrorHandler.handleError(original)),
  } as unknown as ReturnType<typeof apiClient.getAxiosInstance>);
  await expect(archiveDocumentService.download('doc/a')).rejects.toMatchObject({
    code: 'PARTY_SCOPE_MISSING',
  });
});

it('normalizes enhanced list errors into the recoverable service error', async () => {
  const original = new AxiosError('Forbidden', 'ERR_BAD_REQUEST', undefined, undefined, {
    status: 403,
    statusText: 'Forbidden',
    headers: {},
    config: { headers: new AxiosHeaders() },
    data: { error: { code: 'PARTY_SCOPE_MISSING' } },
  });
  vi.mocked(apiClient.get).mockRejectedValueOnce(ApiErrorHandler.handleError(original));
  await expect(archiveDocumentService.list('cert')).rejects.toBeInstanceOf(AssetOperationsError);
});

it('routes handover files to their event without changing the certificate pair', async () => {
  vi.mocked(apiClient.post).mockResolvedValue({ success: true, data: { id: 'new' } });
  vi.mocked(apiClient.get).mockResolvedValue({ success: true, data: { items: [] } });
  await archiveDocumentService.upload(
    'event',
    new File(['scan'], '交接.pdf'),
    'contract_lifecycle_event'
  );
  const body = vi.mocked(apiClient.post).mock.calls.at(-1)![1] as FormData;
  expect(body.get('target_type')).toBe('contract_lifecycle_event');
  expect(body.get('document_type')).toBe('handover');
  await archiveDocumentService.list('event', 'contract_lifecycle_event');
  expect(apiClient.get).toHaveBeenLastCalledWith('/api/v1/archive/documents', {
    params: {
      target_type: 'contract_lifecycle_event',
      target_id: 'event',
      document_type: 'handover',
      include_history: true,
    },
    cache: false,
  });
});

it('routes contract scans to their matching archive target pair', async () => {
  vi.mocked(apiClient.post).mockResolvedValue({ success: true, data: { id: 'new' } });
  vi.mocked(apiClient.get).mockResolvedValue({ success: true, data: { items: [] } });
  await archiveDocumentService.upload('c1', new File(['scan'], '扫描.pdf'), 'upstream_contract');
  const body = vi.mocked(apiClient.post).mock.calls.at(-1)![1] as FormData;
  expect(body.get('target_type')).toBe('upstream_contract');
  expect(body.get('document_type')).toBe('upstream_contract');
  await archiveDocumentService.list('c2', 'terminal_contract');
  expect(apiClient.get).toHaveBeenLastCalledWith(
    '/api/v1/archive/documents',
    expect.objectContaining({
      params: expect.objectContaining({
        target_type: 'terminal_contract',
        document_type: 'terminal_contract',
      }),
    })
  );
});

it('reads fee stamps through the statement archive pair without an upload route', async () => {
  vi.mocked(apiClient.get).mockResolvedValue({ success: true, data: { items: [] } });
  await archiveDocumentService.list('st1', 'management_fee_statement');
  expect(apiClient.get).toHaveBeenLastCalledWith('/api/v1/archive/documents', {
    params: {
      target_type: 'management_fee_statement',
      target_id: 'st1',
      document_type: 'management_fee_statement',
      include_history: true,
    },
    cache: false,
  });
});
