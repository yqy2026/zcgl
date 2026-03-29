import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ApiErrorType } from '@/types/apiResponse';
import { PartyService } from '../partyService';

vi.mock('@/api/client', () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
  },
}));

vi.mock('@/utils/responseExtractor', () => ({
  ApiErrorHandler: {
    handleError: vi.fn(error => ({
      message: error instanceof Error ? error.message : String(error),
    })),
  },
}));

import { apiClient } from '@/api/client';
import { ApiErrorHandler } from '@/utils/responseExtractor';

describe('PartyService', () => {
  let service: PartyService;

  beforeEach(() => {
    service = new PartyService();
    vi.clearAllMocks();
  });

  it('normalizes list response when backend returns raw array', async () => {
    const mockItems = [{ id: 'party-1', name: '甲方' }] as Array<Record<string, unknown>>;
    vi.mocked(apiClient.get).mockResolvedValue({
      success: true,
      data: mockItems,
    });

    const result = await service.getParties({ skip: 10, limit: 50 });

    expect(result.items).toEqual(mockItems);
    expect(result.skip).toBe(10);
    expect(result.limit).toBe(50);
    expect(result.isTruncated).toBe(false);
  });

  it('normalizes list response when backend returns paged envelope', async () => {
    vi.mocked(apiClient.get).mockResolvedValue({
      success: true,
      data: {
        items: [{ id: 'party-1', name: '甲方' }],
        total: 101,
        skip: 0,
        limit: 20,
      },
    });

    const result = await service.getParties({ limit: 20 });

    expect(result.items).toHaveLength(1);
    expect(result.total).toBe(101);
    expect(result.isTruncated).toBe(true);
  });

  it('searches parties with default limit=20', async () => {
    vi.mocked(apiClient.get).mockResolvedValue({
      success: true,
      data: [],
    });

    await service.searchParties('  acme  ');

    expect(apiClient.get).toHaveBeenCalledWith(
      '/parties',
      expect.objectContaining({
        params: expect.objectContaining({
          search: 'acme',
          limit: 20,
        }),
      })
    );
  });

  it('fetches party by id', async () => {
    vi.mocked(apiClient.get).mockResolvedValue({
      success: true,
      data: { id: 'party-1', name: '甲方' },
    });

    const result = await service.getPartyById('party-1');

    expect(result.id).toBe('party-1');
    expect(apiClient.get).toHaveBeenCalledWith(
      '/parties/party-1',
      expect.objectContaining({ cache: true })
    );
  });

  it('creates and updates party', async () => {
    vi.mocked(apiClient.post).mockResolvedValue({
      success: true,
      data: { id: 'party-1', party_type: 'organization', name: '甲方', code: 'A-01' },
    });
    vi.mocked(apiClient.put).mockResolvedValue({
      success: true,
      data: { id: 'party-1', party_type: 'organization', name: '甲方-更新', code: 'A-01' },
    });

    const created = await service.createParty({
      party_type: 'organization',
      name: '甲方',
      code: 'A-01',
    });
    const updated = await service.updateParty('party-1', { name: '甲方-更新' });

    expect(created.id).toBe('party-1');
    expect(updated.name).toBe('甲方-更新');
  });

  it('submits, approves, and rejects party review', async () => {
    vi.mocked(apiClient.post)
      .mockResolvedValueOnce({
        success: true,
        data: { id: 'party-1', review_status: 'pending' },
      })
      .mockResolvedValueOnce({
        success: true,
        data: { id: 'party-1', review_status: 'approved' },
      })
      .mockResolvedValueOnce({
        success: true,
        data: { id: 'party-1', review_status: 'draft', review_reason: '资料不完整' },
      });

    const submitted = await service.submitReview('party-1');
    const approved = await service.approveReview('party-1');
    const rejected = await service.rejectReview('party-1', { reason: '资料不完整' });

    expect(submitted.review_status).toBe('pending');
    expect(approved.review_status).toBe('approved');
    expect(rejected.review_status).toBe('draft');
    expect(apiClient.post).toHaveBeenNthCalledWith(
      1,
      '/parties/party-1/submit-review',
      undefined,
      expect.objectContaining({ smartExtract: true })
    );
    expect(apiClient.post).toHaveBeenNthCalledWith(
      2,
      '/parties/party-1/approve-review',
      undefined,
      expect.objectContaining({ smartExtract: true })
    );
    expect(apiClient.post).toHaveBeenNthCalledWith(
      3,
      '/parties/party-1/reject-review',
      { reason: '资料不完整' },
      expect.objectContaining({ smartExtract: true })
    );
  });

  it('fetches party hierarchy', async () => {
    vi.mocked(apiClient.get).mockResolvedValue({
      success: true,
      data: ['party-1', 'party-2'],
    });

    const result = await service.getPartyHierarchy('party-1', true);

    expect(result).toEqual(['party-1', 'party-2']);
    expect(apiClient.get).toHaveBeenCalledWith(
      '/parties/party-1/hierarchy',
      expect.objectContaining({
        params: { include_self: true },
      })
    );
  });

  it('imports parties in batch', async () => {
    vi.mocked(apiClient.post).mockResolvedValue({
      success: true,
      data: {
        created_count: 1,
        error_count: 0,
        items: [{ index: 0, status: 'created', party_id: 'party-1', message: null }],
      },
    });

    const result = await service.importParties({
      items: [
        {
          party_type: 'organization',
          name: '导入主体',
          code: 'IMP-001',
        },
      ],
    });

    expect(result.created_count).toBe(1);
    expect(apiClient.post).toHaveBeenCalledWith(
      '/parties/import',
      {
        items: [
          {
            party_type: 'organization',
            name: '导入主体',
            code: 'IMP-001',
          },
        ],
      },
      expect.objectContaining({ smartExtract: true })
    );
  });

  it('preserves structured error metadata for forbidden detection consumers', async () => {
    vi.mocked(apiClient.get).mockRejectedValue(new Error('request failed'));
    vi.mocked(ApiErrorHandler.handleError).mockReturnValue({
      type: ApiErrorType.AUTH_ERROR,
      code: 'HTTP_403',
      message: '权限不足，无法访问',
      statusCode: 403,
      timestamp: '2026-02-28T00:00:00Z',
    });

    await expect(service.searchParties('acme')).rejects.toMatchObject({
      message: '权限不足，无法访问',
      code: 'HTTP_403',
      statusCode: 403,
    });
  });
});
