import { beforeEach, describe, expect, it, vi } from 'vitest';
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
});
