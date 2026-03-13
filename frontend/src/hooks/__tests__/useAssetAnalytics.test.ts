import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, act, waitFor } from '@/test/utils/test-helpers';
import { useAssetAnalytics } from '../useAssetAnalytics';
import { analyticsService } from '@/services/analyticsService';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import React from 'react';

// Mock dependencies
vi.mock('@/services/analyticsService', () => ({
  analyticsService: {
    getComprehensiveAnalytics: vi.fn(),
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
  });

  it('should initialize with default state', () => {
    const { result } = renderHook(() => useAssetAnalytics(), {
      wrapper: createWrapper(),
    });

    expect(result.current.filters).toEqual({});
    expect(result.current.dimension).toBe('area');
    expect(result.current.loading).toBe(true); // Initially loading
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
});
