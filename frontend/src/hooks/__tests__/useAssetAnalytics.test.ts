import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, act, waitFor } from '@/test/utils/test-helpers';
import { useAssetAnalytics } from '../useAssetAnalytics';
import { analyticsService } from '@/services/analyticsService';
import { exportAnalyticsData } from '@/services/analyticsExportService';
import { MessageManager } from '@/utils/messageManager';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import React from 'react';

const formatStdoutWrites = (calls: unknown[][]) => calls.map(call => String(call[0] ?? '')).join(' ');

vi.mock('@/utils/queryScope', () => ({
  buildQueryScopeKey: () => 'user:user-1|scope:owner,manager',
}));

vi.mock('@/stores/dataScopeStore', () => ({
  useDataScopeStore: (selector: (state: { initialized: boolean }) => boolean) =>
    selector({ initialized: true }),
}));

// Mock dependencies
vi.mock('@/services/analyticsService', () => ({
  analyticsService: {
    getComprehensiveAnalytics: vi.fn(),
    downloadAnalyticsReport: vi.fn(),
  },
}));

vi.mock('@/services/analyticsExportService', () => ({
  exportAnalyticsData: vi.fn(),
}));

vi.mock('@/utils/messageManager', () => ({
  MessageManager: {
    loading: vi.fn(),
    success: vi.fn(),
    error: vi.fn(),
    destroy: vi.fn(),
  },
}));

vi.mock('@/utils/logger', () => ({
  createLogger: () => ({
    debug: vi.fn(),
    error: vi.fn(),
    warn: vi.fn(),
    info: vi.fn(),
  }),
}));

// Setup QueryClient for testing
const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });
  const Wrapper = ({ children }: { children: React.ReactNode }) =>
    React.createElement(QueryClientProvider, { client: queryClient }, children);
  Wrapper.displayName = 'QueryClientWrapper';
  return Wrapper;
};

describe('useAssetAnalytics', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(analyticsService.getComprehensiveAnalytics).mockResolvedValue({
      success: true,
      data: {
        area_summary: {
          total_assets: 0,
          total_area: 0,
          total_rentable_area: 0,
          total_rented_area: 0,
          total_unrented_area: 0,
          assets_with_area_data: 0,
          occupancy_rate: 0,
          total_non_commercial_area: 0,
        },
        financial_summary: {
          estimated_annual_income: 0,
          total_annual_income: 0,
          total_annual_expense: 0,
          total_net_income: 0,
          total_monthly_rent: 0,
          total_deposit: 0,
          assets_with_income_data: 0,
          assets_with_rent_data: 0,
          profit_margin: 0,
        },
        property_nature_distribution: [],
        ownership_status_distribution: [],
        usage_status_distribution: [],
        business_category_distribution: [],
        occupancy_trend: [],
        occupancy_distribution: [],
      },
    });
  });

  it('should initialize with default state', () => {
    const stdoutWriteSpy = vi.spyOn(process.stdout, 'write').mockImplementation(() => true);

    try {
      const { result } = renderHook(() => useAssetAnalytics(), {
        wrapper: createWrapper(),
      });

      expect(result.current.filters).toEqual({});
      expect(result.current.dimension).toBe('area');
      expect(result.current.loading).toBe(true);
      expect(formatStdoutWrites(stdoutWriteSpy.mock.calls)).not.toContain('[DEBUG] [useAssetAnalytics]');
    } finally {
      stdoutWriteSpy.mockRestore();
    }
  });

  it('should fetch data on mount', async () => {
    const mockData = {
      success: true,
      data: {
        area_summary: { total_assets: 10, total_area: 1000 },
        financial_summary: {},
      },
    };
    vi.mocked(analyticsService.getComprehensiveAnalytics).mockResolvedValue(mockData);

    const { result } = renderHook(() => useAssetAnalytics(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.loading).toBe(false));

      expect(analyticsService.getComprehensiveAnalytics).toHaveBeenCalledWith({});
      expect(result.current.analyticsData).toEqual(mockData.data);
      expect(result.current.hasData).toBe(true);
  });

  it('should scope analytics cache keys to the current view', async () => {
    const queryClient = new QueryClient({
      defaultOptions: {
        queries: {
          retry: false,
        },
      },
    });
    const Wrapper = ({ children }: { children: React.ReactNode }) =>
      React.createElement(QueryClientProvider, { client: queryClient }, children);
    Wrapper.displayName = 'ScopedQueryClientWrapper';

    renderHook(() => useAssetAnalytics(), {
      wrapper: Wrapper,
    });

    await waitFor(() => {
      expect(analyticsService.getComprehensiveAnalytics).toHaveBeenCalledWith({});
    });

    const queryKeys = queryClient
      .getQueryCache()
      .getAll()
      .map(query => query.queryKey);

    expect(
      queryKeys.some(
        queryKey =>
            Array.isArray(queryKey) &&
            queryKey[0] === 'analytics' &&
            queryKey[1] === 'user:user-1|scope:owner,manager' &&
            queryKey[2] === 'comprehensive'
        )
      ).toBe(true);
  });

  it('should update filters and refetch', async () => {
    const { result } = renderHook(() => useAssetAnalytics(), {
      wrapper: createWrapper(),
    });

    act(() => {
      result.current.handleFilterChange({ keyword: 'test' });
    });

    expect(result.current.filters).toEqual({ keyword: 'test' });

    await waitFor(() => {
      expect(analyticsService.getComprehensiveAnalytics).toHaveBeenCalledWith({ keyword: 'test' });
    });
  });

  it('should change dimension', () => {
    const { result } = renderHook(() => useAssetAnalytics(), {
      wrapper: createWrapper(),
    });

    act(() => {
      result.current.handleDimensionChange('count');
    });

    expect(result.current.dimension).toBe('count');
  });

  it('should pass ANA-001 fields through analyticsData', async () => {
    const mockData = {
      success: true,
      data: {
        area_summary: { total_assets: 5, total_area: 2000 },
        financial_summary: { total_annual_income: 100000 },
        total_income: 80000,
        self_operated_rent_income: 50000,
        agency_service_income: 30000,
        customer_entity_count: 8,
        customer_contract_count: 12,
        metrics_version: 'req-ana-001-v1',
        property_nature_distribution: [],
        ownership_status_distribution: [],
        usage_status_distribution: [],
        business_category_distribution: [],
        occupancy_trend: [],
        occupancy_distribution: [],
      },
    };
    vi.mocked(analyticsService.getComprehensiveAnalytics).mockResolvedValue(mockData);

    const { result } = renderHook(() => useAssetAnalytics(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.loading).toBe(false));

    expect(result.current.analyticsData?.total_income).toBe(80000);
    expect(result.current.analyticsData?.self_operated_rent_income).toBe(50000);
    expect(result.current.analyticsData?.agency_service_income).toBe(30000);
    expect(result.current.analyticsData?.customer_entity_count).toBe(8);
    expect(result.current.analyticsData?.customer_contract_count).toBe(12);
    expect(result.current.analyticsData?.metrics_version).toBe('req-ana-001-v1');
  });

  it('should delegate export to analyticsService backend flow', async () => {
    const mockData = {
      success: true,
      data: {
        area_summary: { total_assets: 5, total_area: 2000 },
        financial_summary: { total_annual_income: 100000 },
        total_income: 80000,
        self_operated_rent_income: 50000,
        agency_service_income: 30000,
        customer_entity_count: 8,
        customer_contract_count: 12,
        metrics_version: 'req-ana-001-v1',
        property_nature_distribution: [],
        ownership_status_distribution: [],
        usage_status_distribution: [],
        business_category_distribution: [],
        occupancy_trend: [],
        occupancy_distribution: [],
      },
    };
    vi.mocked(analyticsService.getComprehensiveAnalytics).mockResolvedValue(mockData);
    vi.mocked(analyticsService.downloadAnalyticsReport).mockResolvedValue(undefined);

    const { result } = renderHook(() => useAssetAnalytics(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.loading).toBe(false));

    await act(async () => {
      await result.current.handleExport();
    });

    expect(analyticsService.downloadAnalyticsReport).toHaveBeenCalledWith('excel', {});
    expect(exportAnalyticsData).not.toHaveBeenCalled();
    expect(MessageManager.success).toHaveBeenCalledWith('数据导出成功！');
  });
});
