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
  OperationalGroupsGrid: () => <div data-testid="operational-groups-grid" />,
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

vi.mock('@/components/Analytics/ViewModeSegment', () => ({
  default: () => <div data-testid="view-mode-segment" />,
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
        operational_metric_groups: {
          terminal_collection: {
            label: '终端租户收缴',
            amount_due: 10000,
            paid_amount: 8500,
            outstanding_amount: 1500,
            collection_rate: 85,
          },
          operator_income: {
            label: '运营方收入',
            amount_due: 12000,
            paid_amount: 10000,
            outstanding_amount: 2000,
            collection_rate: 83.33,
          },
          operator_cost: {
            label: '运营方成本',
            amount_due: 6000,
            paid_amount: 4000,
            outstanding_amount: 2000,
            payment_rate: 66.67,
          },
          operating_result: {
            label: '经营结果',
            accrual_net_amount: 6000,
            cash_net_amount: 6000,
          },
        },
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
    expect(screen.getByTestId('view-mode-segment')).toBeInTheDocument();

    expect(screen.getByText('经营分析')).toBeInTheDocument();
    expect(screen.getByText('项目与模式分区')).toBeInTheDocument();
    expect(screen.getAllByText('承租转租').length).toBeGreaterThan(0);
    expect(screen.getAllByText('代理运营').length).toBeGreaterThan(0);
    expect(screen.getByText('湖滨产业园')).toBeInTheDocument();
  });

  it('渲染经营口径分区（operational_metric_groups 四分组）', () => {
    renderWithProviders(<AssetAnalyticsPage />, { route: '/analytics' });

    expect(screen.getByText('经营口径分区')).toBeInTheDocument();
    expect(screen.getByTestId('operational-groups-grid')).toBeInTheDocument();
  });
});
