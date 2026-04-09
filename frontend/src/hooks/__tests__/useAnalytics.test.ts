import { beforeEach, describe, expect, it, vi } from 'vitest';

import { analyticsService } from '@/services/analyticsService';
import { createTestQueryClient, renderHookWithProviders, waitFor } from '@/test/test-utils';

import { useAnalytics } from '../useAnalytics';

vi.mock('@/utils/queryScope', () => ({
  buildQueryScopeKey: () => 'user:user-1|scope:owner,manager',
}));

vi.mock('@/stores/dataScopeStore', () => ({
  useDataScopeStore: (
    selector: (state: { initialized: boolean; getEffectiveViewMode: () => 'owner' }) => unknown
  ) =>
    selector({
      initialized: true,
      getEffectiveViewMode: () => 'owner',
    }),
}));

vi.mock('@/services/analyticsService', () => ({
  analyticsService: {
    getComprehensiveAnalytics: vi.fn(() => Promise.resolve({ area_summary: { total_assets: 1 } })),
  },
}));

describe('useAnalytics', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('应把综合分析 queryKey 绑定到当前数据范围作用域', async () => {
    const queryClient = createTestQueryClient();

    renderHookWithProviders(() => useAnalytics({ keyword: '园区' }), { queryClient });

    await waitFor(() => {
      expect(analyticsService.getComprehensiveAnalytics).toHaveBeenCalledWith(
        { keyword: '园区' },
        'owner'
      );
    });

    const queryKeys = queryClient
      .getQueryCache()
      .getAll()
      .map(query => query.queryKey);

    expect(queryKeys).toContainEqual([
      'analytics',
      'user:user-1|scope:owner,manager',
      'owner',
      'comprehensive',
      { keyword: '园区' },
    ]);
  });

  it('不再依赖视角就绪门闸才发起综合分析请求', async () => {
    const queryClient = createTestQueryClient();

    renderHookWithProviders(() => useAnalytics({ keyword: '园区' }), { queryClient });

    await waitFor(() => {
      expect(analyticsService.getComprehensiveAnalytics).toHaveBeenCalledWith(
        { keyword: '园区' },
        'owner'
      );
    });
  });
});
