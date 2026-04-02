import { beforeEach, describe, expect, it, vi } from 'vitest';
import { SearchService } from '../searchService';

vi.mock('@/api/client', () => ({
  apiClient: {
    get: vi.fn(),
  },
}));

import { apiClient } from '@/api/client';

describe('SearchService', () => {
  let service: SearchService;

  beforeEach(() => {
    vi.clearAllMocks();
    service = new SearchService();
  });

  it('fetches global search results by query string', async () => {
    vi.mocked(apiClient.get).mockResolvedValue({
      success: true,
      data: {
        query: '测试',
        total: 1,
        items: [
          {
            object_type: 'asset',
            object_id: 'asset-1',
            title: '测试资产',
            subtitle: 'AST-001',
            summary: '资产结果',
            keywords: ['asset_name'],
            route_path: '/manager/assets/asset-1',
            score: 90,
            business_rank: 50,
            group_label: '资产',
          },
        ],
        groups: [{ object_type: 'asset', label: '资产', count: 1 }],
      },
    });

    const result = await service.searchGlobal('测试');

    expect(apiClient.get).toHaveBeenCalledWith('/search', {
      params: { q: '测试' },
      cache: false,
      retry: { maxAttempts: 2, delay: 500, backoffMultiplier: 2 },
      smartExtract: true,
    });
    expect(result.total).toBe(1);
    expect(result.items[0].object_type).toBe('asset');
  });
});
