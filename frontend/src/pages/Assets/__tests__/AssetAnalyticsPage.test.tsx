import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen } from '@testing-library/react';
import { renderWithProviders } from '@/test/test-utils';

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

const mockUseAssetAnalytics = vi.fn(() => ({
  analyticsData: {
    area_summary: {
      total_assets: 1,
      total_area: 100,
      total_rentable_area: 80,
      occupancy_rate: 50,
    },
    financial_summary: {
      total_annual_income: 1000,
      total_annual_expense: 100,
      total_net_income: 900,
      total_monthly_rent: 80,
    },
    property_nature_distribution: [],
    ownership_status_distribution: [],
    usage_status_distribution: [],
    business_category_distribution: [],
    occupancy_trend: [],
  },
  loading: false,
  error: null,
  refetch: vi.fn(),
  filters: {},
  dimension: 'area',
  hasData: true,
  handleFilterChange: vi.fn(),
  handleFilterReset: vi.fn(),
  handleDimensionChange: vi.fn(),
  handleExport: vi.fn(),
}));

vi.mock('@/contexts/ViewContext', () => ({
  useView: () => mockUseView(),
}));

vi.mock('@/hooks/useAssetAnalytics', () => ({
  useAssetAnalytics: () => mockUseAssetAnalytics(),
}));

vi.mock('@/hooks/useFullscreen', () => ({
  useFullscreen: () => ({
    isFullscreen: false,
    toggleFullscreen: vi.fn(),
  }),
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
  default: () => <div data-testid="analytics-filters" />,
}));

vi.mock('@/components/Analytics/AssetDistributionGrid', () => ({
  default: () => <div data-testid="asset-distribution-grid" />,
}));

vi.mock('@/components/Analytics/AssetDistributionDetails', () => ({
  default: () => <div data-testid="asset-distribution-details" />,
}));

import AssetAnalyticsPage from '../AssetAnalyticsPage';

describe('AssetAnalyticsPage', () => {
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
    mockUseAssetAnalytics.mockReturnValue({
      analyticsData: {
        area_summary: {
          total_assets: 1,
          total_area: 100,
          total_rentable_area: 80,
          occupancy_rate: 50,
        },
        financial_summary: {
          total_annual_income: 1000,
          total_annual_expense: 100,
          total_net_income: 900,
          total_monthly_rent: 80,
        },
        property_nature_distribution: [],
        ownership_status_distribution: [],
        usage_status_distribution: [],
        business_category_distribution: [],
        occupancy_trend: [],
      },
      loading: false,
      error: null,
      refetch: vi.fn(),
      filters: {},
      dimension: 'area',
      hasData: true,
      handleFilterChange: vi.fn(),
      handleFilterReset: vi.fn(),
      handleDimensionChange: vi.fn(),
      handleExport: vi.fn(),
    });
  });

  it('视角未就绪时不应误显示暂无数据', () => {
    mockUseView.mockReturnValue({
      currentView: null,
      selectionRequired: true,
      isViewReady: false,
    });
    mockUseAssetAnalytics.mockReturnValue({
      analyticsData: null,
      loading: false,
      error: null,
      refetch: vi.fn(),
      filters: {},
      dimension: 'area',
      hasData: false,
      handleFilterChange: vi.fn(),
      handleFilterReset: vi.fn(),
      handleDimensionChange: vi.fn(),
      handleExport: vi.fn(),
    });

    renderWithProviders(<AssetAnalyticsPage />, { route: '/assets/analytics' });

    expect(screen.getByText('加载分析数据中...')).toBeInTheDocument();
    expect(screen.queryByText('暂无数据')).not.toBeInTheDocument();
  });
});
