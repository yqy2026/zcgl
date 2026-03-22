import { beforeEach, describe, expect, it, vi } from 'vitest';

import { analyticsService } from '@/services/analyticsService';
import { createTestQueryClient, renderHookWithProviders, waitFor } from '@/test/test-utils';

import { useAnalytics } from '../useAnalytics';

const mockUseView = vi.fn(() => ({
  currentView: {
    key: 'owner:party-1',
    perspective: 'owner',
    partyId: 'party-1',
    partyName: '主体A',
    label: '产权方 · 主体A',
  },
  selectionRequired: false,
  isViewReady: true,
}));

vi.mock('@/contexts/ViewContext', () => ({
  useView: () => mockUseView(),
}));

vi.mock('@/routes/perspective', () => ({
  useRoutePerspective: () => ({
    perspective: 'owner',
    isPerspectiveRoute: true,
  }),
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
    mockUseView.mockReturnValue({
      currentView: {
        key: 'owner:party-1',
        perspective: 'owner',
        partyId: 'party-1',
        partyName: '主体A',
        label: '产权方 · 主体A',
      },
      selectionRequired: false,
      isViewReady: true,
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
    expect(mockUseView).not.toHaveBeenCalled();
  });

  it('不再依赖视角就绪门闸才发起综合分析请求', async () => {
    const queryClient = createTestQueryClient();

    mockUseView.mockReturnValue({
      currentView: null,
      selectionRequired: true,
      isViewReady: false,
    });

    renderHookWithProviders(() => useAnalytics({ keyword: '园区' }), { queryClient });

    await waitFor(() => {
      expect(analyticsService.getComprehensiveAnalytics).toHaveBeenCalledWith({ keyword: '园区' });
    });

    expect(mockUseView).not.toHaveBeenCalled();
  });
});
