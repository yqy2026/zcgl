import React from 'react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { fireEvent, renderWithProviders, screen, waitFor } from '@/test/utils/test-helpers';
import AssetAnalyticsPage from '../AssetAnalyticsPage';
import { analyticsService } from '@/services/analyticsService';
import { MessageManager } from '@/utils/messageManager';

vi.mock('@/utils/queryScope', () => ({
  buildQueryScopeKey: () => 'user:user-1|scope:owner,manager',
}));

vi.mock('@/stores/dataScopeStore', () => ({
  useDataScopeStore: (selector: (state: { initialized: boolean }) => unknown) =>
    selector({ initialized: true }),
}));

vi.mock('@/hooks/useFullscreen', () => ({
  useFullscreen: () => ({
    isFullscreen: false,
    toggleFullscreen: vi.fn(),
  }),
}));

vi.mock('@/utils/logger', () => ({
  createLogger: () => ({
    debug: vi.fn(),
    error: vi.fn(),
    warn: vi.fn(),
    info: vi.fn(),
  }),
}));

vi.mock('@/utils/messageManager', () => ({
  MessageManager: {
    loading: vi.fn(),
    success: vi.fn(),
    error: vi.fn(),
    destroy: vi.fn(),
  },
}));

vi.mock('@/components/Analytics/AnalyticsStatsCard', () => ({
  AnalyticsStatsGrid: () => <div data-testid="analytics-stats-grid" />,
  FinancialStatsGrid: () => <div data-testid="financial-stats-grid" />,
  RevenueStatsGrid: () => <div data-testid="revenue-stats-grid" />,
}));

vi.mock('@/components/Analytics/AnalyticsChart', () => ({
  AnalyticsLineChart: () => <div data-testid="analytics-line-chart" />,
  chartDataUtils: {
    toTrendData: vi.fn(() => []),
  },
}));

vi.mock('@/components/Analytics/AnalyticsFilters', () => ({
  default: ({
    onFiltersChange,
  }: {
    filters: Record<string, unknown>;
    onFiltersChange: (filters: Record<string, unknown>) => void;
    onResetFilters: () => void;
    loading: boolean;
  }) => (
    <div data-testid="analytics-filters">
      <button
        data-testid="set-export-filters"
        onClick={() =>
          onFiltersChange({
            start_date: '2026-03-01',
            end_date: '2026-03-31',
            include_deleted: true,
          })
        }
      >
        Set Export Filters
      </button>
    </div>
  ),
}));

vi.mock('@/components/Analytics/AssetDistributionGrid', () => ({
  default: () => <div data-testid="asset-distribution-grid" />,
}));

vi.mock('@/components/Analytics/AssetDistributionDetails', () => ({
  default: () => <div data-testid="asset-distribution-details" />,
}));

const analyticsResponse = {
  success: true,
  data: {
    area_summary: {
      total_assets: 5,
      total_area: 2000,
      total_rentable_area: 1500,
      total_rented_area: 1000,
      total_unrented_area: 500,
      assets_with_area_data: 5,
      occupancy_rate: 66.67,
      total_non_commercial_area: 0,
    },
    financial_summary: {
      estimated_annual_income: 100000,
      total_annual_income: 95000,
      total_annual_expense: 5000,
      total_net_income: 90000,
      total_monthly_rent: 8000,
      total_deposit: 12000,
      assets_with_income_data: 5,
      assets_with_rent_data: 5,
      profit_margin: 90,
    },
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

describe('AssetAnalyticsPage export flow', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.spyOn(analyticsService, 'getComprehensiveAnalytics').mockResolvedValue(analyticsResponse);
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('passes the same export filters from the asset analytics page to analyticsService', async () => {
    const blob = new Blob(['xlsx']);
    vi.spyOn(analyticsService, 'downloadAnalyticsReport').mockResolvedValue(blob);

    const anchor = document.createElement('a');
    anchor.click = vi.fn();
    anchor.remove = vi.fn();

    const originalCreateElement = document.createElement.bind(document);
    vi.spyOn(document, 'createElement').mockImplementation((tagName: string) => {
      if (tagName === 'a') {
        return anchor;
      }
      return originalCreateElement(tagName);
    });

    global.URL.createObjectURL = vi.fn(() => 'blob:asset-analytics');
    global.URL.revokeObjectURL = vi.fn();

    renderWithProviders(<AssetAnalyticsPage />, { route: '/assets/analytics' });

    await waitFor(() => {
      expect(screen.getByText('资产分析')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId('set-export-filters'));
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /导出/ })).toBeInTheDocument();
    });
    fireEvent.click(screen.getByRole('button', { name: /导出/ }));

    await waitFor(() => {
      expect(analyticsService.downloadAnalyticsReport).toHaveBeenCalledWith('excel', {
        start_date: '2026-03-01',
        end_date: '2026-03-31',
        include_deleted: true,
      });
      expect(MessageManager.success).toHaveBeenCalledWith('数据导出成功！');
    });
  });

  it('shows an error toast and avoids blob download when export fails', async () => {
    vi.spyOn(analyticsService, 'downloadAnalyticsReport').mockRejectedValue(
      new Error('501 Not Implemented')
    );
    global.URL.createObjectURL = vi.fn(() => 'blob:asset-analytics');
    global.URL.revokeObjectURL = vi.fn();

    renderWithProviders(<AssetAnalyticsPage />, { route: '/assets/analytics' });

    await waitFor(() => {
      expect(screen.getByText('资产分析')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole('button', { name: /导出/ }));

    await waitFor(() => {
      expect(MessageManager.error).toHaveBeenCalledWith('导出失败，请重试');
    });
    expect(global.URL.createObjectURL).not.toHaveBeenCalled();
    expect(global.URL.revokeObjectURL).not.toHaveBeenCalled();
  });
});
