import { beforeEach, describe, expect, it, vi } from 'vitest';

import { analyticsService } from '@/services/analyticsService';
import { createTestQueryClient, renderHookWithProviders, waitFor } from '@/test/test-utils';

import { useAnalytics } from '../useAnalytics';

const mockUseRoutePerspective = vi.hoisted(() =>
  vi.fn(() => ({
    perspective: 'owner',
    isPerspectiveRoute: true,
  }))
);

vi.mock('@/routes/perspective', () => ({
  useRoutePerspective: () => mockUseRoutePerspective(),
}));

vi.mock('@/utils/queryScope', () => ({
  buildQueryScopeKey: () => 'user:user-1|perspective:owner',
}));

vi.mock('@/services/analyticsService', () => ({
  analyticsService: {
    getComprehensiveAnalytics: vi.fn(() => Promise.resolve({ area_summary: { total_assets: 1 } })),
  },
}));

describe('useAnalytics', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseRoutePerspective.mockReturnValue({
      perspective: 'owner',
      isPerspectiveRoute: true,
    });
  });

  it('应把综合分析 queryKey 绑定到当前视角作用域', async () => {
    const queryClient = createTestQueryClient();

    renderHookWithProviders(() => useAnalytics({ keyword: '园区' }), { queryClient });

    await waitFor(() => {
      expect(analyticsService.getComprehensiveAnalytics).toHaveBeenCalledWith({ keyword: '园区' });
    });

    const queryKeys = queryClient
      .getQueryCache()
      .getAll()
      .map(query => query.queryKey);

    expect(queryKeys).toContainEqual([
      'analytics',
      'user:user-1|perspective:owner',
      'comprehensive',
      { keyword: '园区' },
    ]);
  });

  it('不再依赖视角就绪门闸才发起综合分析请求', async () => {
    const queryClient = createTestQueryClient();

    renderHookWithProviders(() => useAnalytics({ keyword: '园区' }), { queryClient });

    await waitFor(() => {
      expect(analyticsService.getComprehensiveAnalytics).toHaveBeenCalledWith({ keyword: '园区' });
    });
  });

  it('在共享路由缺少视角时不应请求综合分析接口', async () => {
    mockUseRoutePerspective.mockReturnValue({
      perspective: null,
      isPerspectiveRoute: false,
    });
    const queryClient = createTestQueryClient();

    renderHookWithProviders(() => useAnalytics({ keyword: '园区' }), { queryClient });

    await waitFor(() => {
      expect(queryClient.getQueryCache().getAll()).toHaveLength(1);
    });

    expect(analyticsService.getComprehensiveAnalytics).not.toHaveBeenCalled();
  });
});
