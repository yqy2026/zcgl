/**
 * AreaStatisticsChart 组件测试
 * 测试面积统计图表组件
 *
 * 修复说明：
 * - 移除 antd 所有组件 mock
 * - 移除 @ant-design/icons mock
 * - 保留 @tanstack/react-query mock (业务逻辑)
 * - 保留 @ant-design/plots mock (图表库)
 * - 保留服务层 mock (assetService)
 * - 使用 className 和文本内容进行断言
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import React from 'react';

// Mock @tanstack/react-query
const mockUseQuery = vi.fn();
vi.mock('@tanstack/react-query', () => ({
  useQuery: (options: unknown) => mockUseQuery(options),
}));

// Mock @ant-design/plots
vi.mock('@ant-design/plots', () => ({
  Column: ({ height }: { height?: number }) => (
    <div data-testid="column-chart" data-height={height}>
      Column Chart
    </div>
  ),
  DualAxes: ({ height }: { height?: number }) => (
    <div data-testid="dual-axes-chart" data-height={height}>
      DualAxes Chart
    </div>
  ),
}));

// Mock asset service
vi.mock('@/services/assetService', () => ({
  assetService: {
    getAreaStatistics: vi.fn(),
  },
}));

// Sample mock data
const mockAreaData = {
  total_statistics: {
    total_land_area: 100000,
    total_property_area: 80000,
    total_rentable_area: 60000,
    total_rented_area: 45000,
    total_vacant_area: 15000,
    total_non_commercial_area: 20000,
  },
  by_property_nature: [
    {
      property_nature: '经营类',
      land_area: 60000,
      property_area: 50000,
      rentable_area: 40000,
      rented_area: 35000,
    },
    {
      property_nature: '非经营类',
      land_area: 40000,
      property_area: 30000,
      rentable_area: 20000,
      rented_area: 10000,
    },
  ],
  by_ownership_entity: [
    { ownership_entity: '权属方A', total_area: 30000, occupancy_rate: 85.0 },
    { ownership_entity: '权属方B', total_area: 25000, occupancy_rate: 75.0 },
    { ownership_entity: '权属方C', total_area: 20000, occupancy_rate: 90.0 },
  ],
  by_usage_status: [
    { usage_status: '出租', asset_count: 80, total_area: 45000, average_area: 562.5 },
    { usage_status: '闲置', asset_count: 30, total_area: 15000, average_area: 500.0 },
    { usage_status: '自用', asset_count: 40, total_area: 20000, average_area: 500.0 },
  ],
  area_ranges: [
    { range: '0-100㎡', count: 20, total_area: 1500, percentage: 13.3 },
    { range: '100-500㎡', count: 50, total_area: 15000, percentage: 33.3 },
    { range: '500-1000㎡', count: 40, total_area: 30000, percentage: 26.7 },
    { range: '1000㎡以上', count: 40, total_area: 33500, percentage: 26.7 },
  ],
  top_assets_by_area: [
    { asset_name: '资产A', property_area: 5000, rentable_area: 4500, occupancy_rate: 90.0 },
    { asset_name: '资产B', property_area: 4000, rentable_area: 3500, occupancy_rate: 85.0 },
    { asset_name: '资产C', property_area: 3500, rentable_area: 3000, occupancy_rate: 80.0 },
  ],
};

describe('AreaStatisticsChart', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Default mock: loading complete with data
    mockUseQuery.mockReturnValue({
      data: mockAreaData,
      isLoading: false,
      error: null,
    });
  });

  describe('Component Import', () => {
    it('should be able to import AreaStatisticsChart component', async () => {
      const module = await import('../AreaStatisticsChart');
      expect(module).toBeDefined();
      expect(module.default).toBeDefined();
    });
  });

  describe('Basic Rendering', () => {
    it('should render without crashing', async () => {
      const AreaStatisticsChart = (await import('../AreaStatisticsChart')).default;
      render(<AreaStatisticsChart />);
      expect(screen.getAllByTestId('column-chart').length).toBeGreaterThanOrEqual(1);
    });

    it('should render with filters prop', async () => {
      const AreaStatisticsChart = (await import('../AreaStatisticsChart')).default;
      const filters = { ownership_status: '自有' };
      render(<AreaStatisticsChart filters={filters} />);
      expect(screen.getAllByTestId('column-chart').length).toBeGreaterThanOrEqual(1);
    });

    it('should render with custom height prop', async () => {
      const AreaStatisticsChart = (await import('../AreaStatisticsChart')).default;
      render(<AreaStatisticsChart height={500} />);
      const columnCharts = screen.getAllByTestId('column-chart');
      expect(columnCharts[0]).toHaveAttribute('data-height', '500');
    });
  });

  describe('Statistics Display', () => {
    it('should display total land area statistic', async () => {
      const AreaStatisticsChart = (await import('../AreaStatisticsChart')).default;
      render(<AreaStatisticsChart />);
      expect(screen.getByText('总土地面积')).toBeInTheDocument();
    });

    it('should display total property area statistic', async () => {
      const AreaStatisticsChart = (await import('../AreaStatisticsChart')).default;
      render(<AreaStatisticsChart />);
      expect(screen.getByText('总房产面积')).toBeInTheDocument();
    });

    it('should display rentable area statistic', async () => {
      const AreaStatisticsChart = (await import('../AreaStatisticsChart')).default;
      render(<AreaStatisticsChart />);
      expect(screen.getByText('可租面积')).toBeInTheDocument();
    });

    it('should display rented area statistic', async () => {
      const AreaStatisticsChart = (await import('../AreaStatisticsChart')).default;
      render(<AreaStatisticsChart />);
      expect(screen.getByText('已租面积')).toBeInTheDocument();
    });

    it('should display vacant area statistic', async () => {
      const AreaStatisticsChart = (await import('../AreaStatisticsChart')).default;
      render(<AreaStatisticsChart />);
      expect(screen.getByText('空置面积')).toBeInTheDocument();
    });

    it('should display non-commercial area statistic', async () => {
      const AreaStatisticsChart = (await import('../AreaStatisticsChart')).default;
      render(<AreaStatisticsChart />);
      expect(screen.getByText('非经营面积')).toBeInTheDocument();
    });
  });

  describe('Chart Components', () => {
    it('should render property nature column chart', async () => {
      const AreaStatisticsChart = (await import('../AreaStatisticsChart')).default;
      render(<AreaStatisticsChart />);
      const columnCharts = screen.getAllByTestId('column-chart');
      expect(columnCharts.length).toBeGreaterThanOrEqual(1);
    });

    it('should render area range column chart', async () => {
      const AreaStatisticsChart = (await import('../AreaStatisticsChart')).default;
      render(<AreaStatisticsChart />);
      const columnCharts = screen.getAllByTestId('column-chart');
      expect(columnCharts.length).toBeGreaterThanOrEqual(2);
    });

    it('should render ownership entity dual axes chart', async () => {
      const AreaStatisticsChart = (await import('../AreaStatisticsChart')).default;
      render(<AreaStatisticsChart />);
      expect(screen.getByTestId('dual-axes-chart')).toBeInTheDocument();
    });
  });

  describe('Card Titles', () => {
    it('should display property nature area distribution card title', async () => {
      const AreaStatisticsChart = (await import('../AreaStatisticsChart')).default;
      render(<AreaStatisticsChart />);
      expect(screen.getByText('物业性质面积分布')).toBeInTheDocument();
    });

    it('should display area range distribution card title', async () => {
      const AreaStatisticsChart = (await import('../AreaStatisticsChart')).default;
      render(<AreaStatisticsChart />);
      expect(screen.getByText('面积区间分布')).toBeInTheDocument();
    });

    it('should display ownership entity comparison card title', async () => {
      const AreaStatisticsChart = (await import('../AreaStatisticsChart')).default;
      render(<AreaStatisticsChart />);
      expect(screen.getByText('权属方面积与出租率对比')).toBeInTheDocument();
    });

    it('should display usage status area statistics card title', async () => {
      const AreaStatisticsChart = (await import('../AreaStatisticsChart')).default;
      render(<AreaStatisticsChart />);
      expect(screen.getByText('使用状态面积统计')).toBeInTheDocument();
    });

    it('should display top assets by area card title', async () => {
      const AreaStatisticsChart = (await import('../AreaStatisticsChart')).default;
      render(<AreaStatisticsChart />);
      expect(screen.getByText(/面积最大资产/)).toBeInTheDocument();
    });
  });

  describe('Loading State', () => {
    it('should show spin component when loading', async () => {
      mockUseQuery.mockReturnValue({
        data: undefined,
        isLoading: true,
        error: null,
      });
      const AreaStatisticsChart = (await import('../AreaStatisticsChart')).default;
      const { container } = render(<AreaStatisticsChart />);
      const spinElements = container.querySelectorAll('.ant-spin');
      expect(spinElements.length).toBeGreaterThan(0);
    });
  });

  describe('Error State', () => {
    it('should display Alert when there is an error', async () => {
      mockUseQuery.mockReturnValue({
        data: undefined,
        isLoading: false,
        error: new Error('Failed to load'),
      });
      const AreaStatisticsChart = (await import('../AreaStatisticsChart')).default;
      const { container } = render(<AreaStatisticsChart />);
      const alertElements = container.querySelectorAll('.ant-alert-error');
      expect(alertElements.length).toBeGreaterThan(0);
    });

    it('should display error message in Alert', async () => {
      mockUseQuery.mockReturnValue({
        data: undefined,
        isLoading: false,
        error: new Error('Failed to load'),
      });
      const AreaStatisticsChart = (await import('../AreaStatisticsChart')).default;
      render(<AreaStatisticsChart />);
      expect(screen.getByText(/数据加载失败/)).toBeInTheDocument();
    });
  });

  describe('Data Query', () => {
    it('should call useQuery with correct query key', async () => {
      const AreaStatisticsChart = (await import('../AreaStatisticsChart')).default;
      render(<AreaStatisticsChart />);
      expect(mockUseQuery).toHaveBeenCalled();
      const callArgs = mockUseQuery.mock.calls[0][0];
      expect(callArgs.queryKey).toContain('area-statistics');
    });

    it('should include filters in query key', async () => {
      const AreaStatisticsChart = (await import('../AreaStatisticsChart')).default;
      const filters = { ownership_status: '自有' };
      render(<AreaStatisticsChart filters={filters} />);
      const callArgs = mockUseQuery.mock.calls[0][0];
      expect(callArgs.queryKey).toContain(filters);
    });
  });

  describe('Edge Cases', () => {
    it('should handle undefined filters', async () => {
      const AreaStatisticsChart = (await import('../AreaStatisticsChart')).default;
      render(<AreaStatisticsChart filters={undefined} />);
      expect(screen.getAllByTestId('column-chart').length).toBeGreaterThanOrEqual(1);
    });

    it('should handle empty filters', async () => {
      const AreaStatisticsChart = (await import('../AreaStatisticsChart')).default;
      render(<AreaStatisticsChart filters={{}} />);
      expect(screen.getAllByTestId('column-chart').length).toBeGreaterThanOrEqual(1);
    });

    it('should handle empty data', async () => {
      mockUseQuery.mockReturnValue({
        data: undefined,
        isLoading: false,
        error: null,
      });
      const AreaStatisticsChart = (await import('../AreaStatisticsChart')).default;
      render(<AreaStatisticsChart />);
      expect(screen.getAllByTestId('column-chart').length).toBeGreaterThanOrEqual(1);
    });

    it('should handle height of 0', async () => {
      const AreaStatisticsChart = (await import('../AreaStatisticsChart')).default;
      render(<AreaStatisticsChart height={0} />);
      const columnCharts = screen.getAllByTestId('column-chart');
      expect(columnCharts[0]).toHaveAttribute('data-height', '0');
    });
  });
});
