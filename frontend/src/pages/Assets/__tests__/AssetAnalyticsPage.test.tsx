import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen } from '@testing-library/react';
import { renderWithProviders } from '@/test/test-utils';

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
    project_breakdown: [],
    mode_breakdown: [],
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
        project_breakdown: [
          {
            project_id: 'project-1',
            project_name: '湖滨产业园',
            contract_relation_count: 2,
            contract_count: 3,
            lease_relation_count: 1,
            agency_relation_count: 1,
            total_income: 720,
            self_operated_rent_income: 600,
            agency_service_income: 120,
            actual_receipts: 450,
            customer_entity_count: 2,
            customer_contract_count: 2,
          },
        ],
        mode_breakdown: [
          {
            relation_kind: 'lease_sublease',
            label: '承租转租',
            contract_relation_count: 1,
            contract_count: 2,
            total_income: 600,
            self_operated_rent_income: 600,
            agency_service_income: 0,
            actual_receipts: 450,
            customer_entity_count: 1,
            customer_contract_count: 1,
          },
          {
            relation_kind: 'agency_operation',
            label: '代理运营',
            contract_relation_count: 1,
            contract_count: 1,
            total_income: 120,
            self_operated_rent_income: 0,
            agency_service_income: 120,
            actual_receipts: 0,
            customer_entity_count: 1,
            customer_contract_count: 1,
          },
        ],
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

  it('loading 时不应误显示暂无数据', () => {
    mockUseAssetAnalytics.mockReturnValue({
      analyticsData: null,
      loading: true,
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

  it('展示全局经营分析的项目和经营模式分区', () => {
    renderWithProviders(<AssetAnalyticsPage />, { route: '/analytics' });

    expect(screen.getByText('经营分析')).toBeInTheDocument();
    expect(screen.getByText('项目与模式分区')).toBeInTheDocument();
    expect(screen.getAllByText('承租转租').length).toBeGreaterThan(0);
    expect(screen.getAllByText('代理运营').length).toBeGreaterThan(0);
    expect(screen.getByText('湖滨产业园')).toBeInTheDocument();
  });
});
