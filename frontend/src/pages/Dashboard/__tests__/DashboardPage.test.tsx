/**
 * DashboardPage 页面测试
 */

import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import DashboardPage from '../DashboardPage';

// Mock useAnalytics hook
vi.mock('../../../hooks/useAnalytics', () => ({
  useAnalytics: vi.fn(),
}));

// Mock CSS modules
vi.mock('../DashboardPage.module.css', () => ({
  default: {
    dashboardContainer: 'dashboardContainer',
    dashboardHeader: 'dashboardHeader',
    dashboardTitle: 'dashboardTitle',
    dashboardSubtitle: 'dashboardSubtitle',
    dashboardActions: 'dashboardActions',
    actionButton: 'actionButton',
    keyMetricsSection: 'keyMetricsSection',
    insightsSection: 'insightsSection',
    detailedStatsSection: 'detailedStatsSection',
    statsCard: 'statsCard',
    statsCardHeader: 'statsCardHeader',
    statsCardTitle: 'statsCardTitle',
    statsCardBody: 'statsCardBody',
    statItem: 'statItem',
    statValue: 'statValue',
    statLabel: 'statLabel',
    errorContainer: 'errorContainer',
    errorTitle: 'errorTitle',
    errorDescription: 'errorDescription',
    fullscreen: 'fullscreen',
    headerContent: 'headerContent',
  },
}));

// Mock DataTrendCard component
vi.mock('../../../components/Dashboard/DataTrendCard', () => ({
  default: ({ title, value, suffix, loading }: { title: string; value: number; suffix: string; loading: boolean }) => (
    <div data-testid={`trend-card-${title}`}>
      {loading ? 'Loading...' : `${title}: ${value}${suffix}`}
    </div>
  ),
}));

// Mock QuickInsights component
vi.mock('../../../components/Dashboard/QuickInsights', () => ({
  default: ({ data: _data, loading }: { data: unknown; loading: boolean }) => (
    <div data-testid="quick-insights">
      {loading ? 'Loading insights...' : 'Quick Insights'}
    </div>
  ),
}));

import { useAnalytics } from '../../../hooks/useAnalytics';

// 创建测试用 QueryClient
const createTestQueryClient = () =>
  new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        gcTime: 0,
      },
    },
  });

// 渲染辅助函数
const renderWithProviders = () => {
  const queryClient = createTestQueryClient();

  return render(
    <QueryClientProvider client={queryClient}>
      <DashboardPage />
    </QueryClientProvider>
  );
};

describe('DashboardPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();

    // 默认 mock 返回值
    vi.mocked(useAnalytics).mockReturnValue({
      data: {
        success: true,
        data: {
          area_summary: {
            total_assets: 100,
            total_area: 50000,
            total_rentable_area: 40000,
            total_rented_area: 35000,
            total_unrented_area: 5000,
            total_non_commercial_area: 10000,
            assets_with_area_data: 95,
            occupancy_rate: 87.5,
          },
          occupancy_trend: [],
        },
      },
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof useAnalytics>);
  });

  describe('渲染', () => {
    it('渲染页面标题', () => {
      renderWithProviders();

      expect(screen.getByText('资产管理看板')).toBeInTheDocument();
      expect(screen.getByText('实时监控资产运营状况，提供数据驱动的决策支持')).toBeInTheDocument();
    });

    it('渲染操作按钮', () => {
      renderWithProviders();

      expect(screen.getByText('刷新')).toBeInTheDocument();
      expect(screen.getByText('导出')).toBeInTheDocument();
      expect(screen.getByText('全屏')).toBeInTheDocument();
    });

    it('渲染关键指标卡片', () => {
      renderWithProviders();

      expect(screen.getByTestId('trend-card-资产总数')).toBeInTheDocument();
      expect(screen.getByTestId('trend-card-管理总面积')).toBeInTheDocument();
      expect(screen.getByTestId('trend-card-可租面积')).toBeInTheDocument();
      expect(screen.getByTestId('trend-card-整体出租率')).toBeInTheDocument();
    });

    it('渲染智能洞察区域', () => {
      renderWithProviders();

      expect(screen.getByTestId('quick-insights')).toBeInTheDocument();
    });

    it('渲染详细统计区域', () => {
      renderWithProviders();

      expect(screen.getByText('面积分布统计')).toBeInTheDocument();
      expect(screen.getByText('运营状况概览')).toBeInTheDocument();
    });
  });

  describe('加载状态', () => {
    it('加载中时显示加载状态', () => {
      vi.mocked(useAnalytics).mockReturnValue({
        data: null,
        isLoading: true,
        error: null,
        refetch: vi.fn(),
      } as unknown as ReturnType<typeof useAnalytics>);

      renderWithProviders();

      expect(screen.getByTestId('quick-insights')).toHaveTextContent('Loading insights...');
    });
  });

  describe('错误处理', () => {
    it('显示错误信息', () => {
      vi.mocked(useAnalytics).mockReturnValue({
        data: null,
        isLoading: false,
        error: new Error('网络错误'),
        refetch: vi.fn(),
      } as unknown as ReturnType<typeof useAnalytics>);

      renderWithProviders();

      expect(screen.getByText('数据加载失败')).toBeInTheDocument();
      expect(screen.getByText('网络错误')).toBeInTheDocument();
      expect(screen.getByText('重试')).toBeInTheDocument();
    });

    it('点击重试按钮调用 refetch', () => {
      const refetch = vi.fn();
      vi.mocked(useAnalytics).mockReturnValue({
        data: null,
        isLoading: false,
        error: new Error('网络错误'),
        refetch,
      } as unknown as ReturnType<typeof useAnalytics>);

      renderWithProviders();

      fireEvent.click(screen.getByText('重试'));

      expect(refetch).toHaveBeenCalled();
    });
  });

  describe('操作功能', () => {
    it('点击刷新按钮调用 refetch', () => {
      const refetch = vi.fn();
      vi.mocked(useAnalytics).mockReturnValue({
        data: {
          success: true,
          data: {
            area_summary: {
              total_assets: 100,
              total_area: 50000,
              occupancy_rate: 87.5,
            },
          },
        },
        isLoading: false,
        error: null,
        refetch,
      } as unknown as ReturnType<typeof useAnalytics>);

      renderWithProviders();

      fireEvent.click(screen.getByText('刷新'));

      expect(refetch).toHaveBeenCalled();
    });

    it('点击全屏按钮切换全屏状态', () => {
      // Mock requestFullscreen
      document.documentElement.requestFullscreen = vi.fn().mockResolvedValue(undefined);

      renderWithProviders();

      const fullscreenButton = screen.getByText('全屏');
      fireEvent.click(fullscreenButton);

      expect(document.documentElement.requestFullscreen).toHaveBeenCalled();
    });
  });

  describe('数据显示', () => {
    it('正确显示资产统计数据', () => {
      renderWithProviders();

      expect(screen.getByText('资产总数: 100个')).toBeInTheDocument();
      expect(screen.getByText('管理总面积: 50000㎡')).toBeInTheDocument();
      expect(screen.getByText('可租面积: 40000㎡')).toBeInTheDocument();
      expect(screen.getByText('整体出租率: 87.5%')).toBeInTheDocument();
    });

    it('正确显示面积分布数据', () => {
      renderWithProviders();

      expect(screen.getByText('已租面积 (㎡)')).toBeInTheDocument();
      expect(screen.getByText('空置面积 (㎡)')).toBeInTheDocument();
      expect(screen.getByText('非商业面积 (㎡)')).toBeInTheDocument();
    });
  });

  describe('空数据处理', () => {
    it('数据为空时显示默认值', () => {
      vi.mocked(useAnalytics).mockReturnValue({
        data: {
          success: true,
          data: {
            area_summary: null,
          },
        },
        isLoading: false,
        error: null,
        refetch: vi.fn(),
      } as unknown as ReturnType<typeof useAnalytics>);

      renderWithProviders();

      expect(screen.getByText('资产总数: 0个')).toBeInTheDocument();
      expect(screen.getByText('管理总面积: 0㎡')).toBeInTheDocument();
    });
  });
});
