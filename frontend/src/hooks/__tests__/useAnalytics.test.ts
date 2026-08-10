import { beforeEach, describe, expect, it, vi } from 'vitest';

import { analyticsService } from '@/services/analyticsService';
import { createTestQueryClient, renderHookWithProviders, waitFor } from '@/test/test-utils';

import { useAnalytics } from '../useAnalytics';

vi.mock('@/utils/queryScope', () => ({
  buildQueryScopeKey: () => 'user:user-1|scope:owner,manager',
}));

vi.mock('@/stores/dataScopeStore', () => ({
  useDataScopeStore: (
    selector: (state: {
      initialized: boolean;
      isDualBinding: boolean;
      getEffectiveViewMode: () => 'owner' | 'manager' | null;
    }) => unknown
  ) =>
    selector({
      initialized: scopeState.initialized,
      isDualBinding: scopeState.isDualBinding,
      getEffectiveViewMode: () => scopeState.currentViewMode,
    }),
}));

vi.mock('@/services/analyticsService', () => ({
  analyticsService: {
    getComprehensiveAnalytics: vi.fn(() => Promise.resolve({ area_summary: { total_assets: 1 } })),
  },
}));

const scopeState = {
  initialized: true,
  isDualBinding: false,
  currentViewMode: 'owner' as 'owner' | 'manager' | null,
};

describe('useAnalytics', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    scopeState.initialized = true;
    scopeState.isDualBinding = false;
    scopeState.currentViewMode = 'owner';
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

  it('双视角未选择视图时不发起综合分析请求并暴露选择引导', async () => {
    scopeState.isDualBinding = true;
    scopeState.currentViewMode = null;
    const queryClient = createTestQueryClient();

    const { result } = renderHookWithProviders(() => useAnalytics(), { queryClient });

    await new Promise(resolve => setTimeout(resolve, 50));

    expect(result.current.needsViewModeSelection).toBe(true);
    expect(analyticsService.getComprehensiveAnalytics).not.toHaveBeenCalled();
  });
});
