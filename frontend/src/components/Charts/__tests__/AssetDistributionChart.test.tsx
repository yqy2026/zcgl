/**
 * AssetDistributionChart 组件测试
 * 测试资产分布图表组件
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
  Pie: ({ height }: { height?: number }) => (
    <div data-testid="pie-chart" data-height={height}>
      Pie Chart
    </div>
  ),
  Column: ({ height }: { height?: number }) => (
    <div data-testid="column-chart" data-height={height}>
      Column Chart
    </div>
  ),
}));

// Mock Ant Design components
vi.mock('antd', () => ({
  Card: ({ children, title }: { children?: React.ReactNode; title?: React.ReactNode }) => (
    <div data-testid="card">
      {title && <div data-testid="card-title">{title}</div>}
      {children}
    </div>
  ),
  Row: ({ children }: { children?: React.ReactNode }) => <div data-testid="row">{children}</div>,
  Col: ({ children }: { children?: React.ReactNode }) => <div data-testid="col">{children}</div>,
  Statistic: ({
    title,
    value,
    suffix,
  }: {
    title?: React.ReactNode;
    value?: number;
    suffix?: React.ReactNode;
  }) => (
    <div data-testid="statistic">
      <span data-testid="statistic-title">{title}</span>
      <span data-testid="statistic-value">{value}</span>
      {suffix && <span data-testid="statistic-suffix">{suffix}</span>}
    </div>
  ),
  Spin: ({ children, spinning }: { children?: React.ReactNode; spinning?: boolean }) => (
    <div data-testid="spin" data-spinning={spinning}>
      {children}
    </div>
  ),
  Alert: ({
    message,
    description,
    type,
  }: {
    message?: React.ReactNode;
    description?: React.ReactNode;
    type?: string;
  }) => (
    <div data-testid="alert" data-type={type}>
      <span data-testid="alert-message">{message}</span>
      <span data-testid="alert-description">{description}</span>
    </div>
  ),
  Typography: {
    Title: ({ children }: { children?: React.ReactNode }) => (
      <div data-testid="typography-title">{children}</div>
    ),
    Text: ({ children }: { children?: React.ReactNode }) => (
      <span data-testid="typography-text">{children}</span>
    ),
  },
  Space: ({ children }: { children?: React.ReactNode }) => (
    <div data-testid="space">{children}</div>
  ),
  Tag: ({ children, color }: { children?: React.ReactNode; color?: string }) => (
    <span data-testid="tag" data-color={color}>
      {children}
    </span>
  ),
}));

// Mock icons
vi.mock('@ant-design/icons', () => ({
  PieChartOutlined: () => <span data-testid="icon-pie-chart" />,
  HomeOutlined: () => <span data-testid="icon-home" />,
  EnvironmentOutlined: () => <span data-testid="icon-environment" />,
  UserOutlined: () => <span data-testid="icon-user" />,
}));

// Mock asset service
vi.mock('@/services/assetService', () => ({
  assetService: {
    getAssetDistributionStats: vi.fn(),
  },
}));

// Sample mock data
const mockDistributionData = {
  total_assets: 150,
  by_property_nature: [
    { property_nature: '经营类', count: 80, percentage: 53.3, total_area: 50000 },
    { property_nature: '非经营类', count: 70, percentage: 46.7, total_area: 30000 },
  ],
  by_ownership_status: [
    { ownership_status: '已确权', count: 100, percentage: 66.7 },
    { ownership_status: '未确权', count: 50, percentage: 33.3 },
  ],
  by_usage_status: [
    { usage_status: '出租', count: 80, percentage: 53.3 },
    { usage_status: '闲置', count: 30, percentage: 20.0 },
    { usage_status: '自用', count: 40, percentage: 26.7 },
  ],
  by_ownership_entity: [
    { ownership_entity: '权属方A', count: 50, percentage: 33.3, total_area: 25000 },
    { ownership_entity: '权属方B', count: 40, percentage: 26.7, total_area: 20000 },
    { ownership_entity: '权属方C', count: 30, percentage: 20.0, total_area: 15000 },
  ],
  by_region: [
    { region: '区域A', count: 60, percentage: 40.0 },
    { region: '区域B', count: 90, percentage: 60.0 },
  ],
  summary: {
    total_area: 80000,
    commercial_area: 50000,
    non_commercial_area: 30000,
    rented_area: 40000,
    vacant_area: 10000,
  },
};

describe('AssetDistributionChart', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Default mock: loading complete with data
    mockUseQuery.mockReturnValue({
      data: mockDistributionData,
      isLoading: false,
      error: null,
    });
  });

  describe('Component Import', () => {
    it('should be able to import AssetDistributionChart component', async () => {
      const module = await import('../AssetDistributionChart');
      expect(module).toBeDefined();
      expect(module.default).toBeDefined();
    });
  });

  describe('Basic Rendering', () => {
    it('should render without crashing', async () => {
      const AssetDistributionChart = (await import('../AssetDistributionChart')).default;
      render(<AssetDistributionChart />);
      expect(screen.getAllByTestId('card').length).toBeGreaterThan(0);
    });

    it('should render with filters prop', async () => {
      const AssetDistributionChart = (await import('../AssetDistributionChart')).default;
      const filters = { ownership_status: '自有' };
      render(<AssetDistributionChart filters={filters} />);
      expect(screen.getAllByTestId('card').length).toBeGreaterThan(0);
    });

    it('should render with custom height prop', async () => {
      const AssetDistributionChart = (await import('../AssetDistributionChart')).default;
      render(<AssetDistributionChart height={400} />);
      const pieCharts = screen.getAllByTestId('pie-chart');
      expect(pieCharts[0]).toHaveAttribute('data-height', '400');
    });
  });

  describe('Statistics Display', () => {
    it('should display total assets statistic', async () => {
      const AssetDistributionChart = (await import('../AssetDistributionChart')).default;
      render(<AssetDistributionChart />);
      const statisticTitles = screen.getAllByTestId('statistic-title');
      const titles = statisticTitles.map(el => el.textContent);
      expect(titles).toContain('资产总数');
    });

    it('should display total area statistic', async () => {
      const AssetDistributionChart = (await import('../AssetDistributionChart')).default;
      render(<AssetDistributionChart />);
      const statisticTitles = screen.getAllByTestId('statistic-title');
      const titles = statisticTitles.map(el => el.textContent);
      expect(titles).toContain('总面积');
    });

    it('should display ownership entity count statistic', async () => {
      const AssetDistributionChart = (await import('../AssetDistributionChart')).default;
      render(<AssetDistributionChart />);
      const statisticTitles = screen.getAllByTestId('statistic-title');
      const titles = statisticTitles.map(el => el.textContent);
      expect(titles).toContain('权属方数量');
    });

    it('should display commercial area statistic', async () => {
      const AssetDistributionChart = (await import('../AssetDistributionChart')).default;
      render(<AssetDistributionChart />);
      const statisticTitles = screen.getAllByTestId('statistic-title');
      const titles = statisticTitles.map(el => el.textContent);
      expect(titles).toContain('经营类面积');
    });
  });

  describe('Chart Components', () => {
    it('should render property nature pie chart', async () => {
      const AssetDistributionChart = (await import('../AssetDistributionChart')).default;
      render(<AssetDistributionChart />);
      const pieCharts = screen.getAllByTestId('pie-chart');
      expect(pieCharts.length).toBeGreaterThanOrEqual(1);
    });

    it('should render ownership status pie chart', async () => {
      const AssetDistributionChart = (await import('../AssetDistributionChart')).default;
      render(<AssetDistributionChart />);
      const pieCharts = screen.getAllByTestId('pie-chart');
      expect(pieCharts.length).toBeGreaterThanOrEqual(2);
    });

    it('should render usage status pie chart', async () => {
      const AssetDistributionChart = (await import('../AssetDistributionChart')).default;
      render(<AssetDistributionChart />);
      const pieCharts = screen.getAllByTestId('pie-chart');
      expect(pieCharts.length).toBeGreaterThanOrEqual(3);
    });

    it('should render ownership entity column chart', async () => {
      const AssetDistributionChart = (await import('../AssetDistributionChart')).default;
      render(<AssetDistributionChart />);
      expect(screen.getByTestId('column-chart')).toBeInTheDocument();
    });
  });

  describe('Card Titles', () => {
    it('should display property nature distribution card title', async () => {
      const AssetDistributionChart = (await import('../AssetDistributionChart')).default;
      render(<AssetDistributionChart />);
      const cardTitles = screen.getAllByTestId('card-title');
      const titles = cardTitles.map(el => el.textContent);
      expect(titles).toContain('物业性质分布');
    });

    it('should display ownership status distribution card title', async () => {
      const AssetDistributionChart = (await import('../AssetDistributionChart')).default;
      render(<AssetDistributionChart />);
      const cardTitles = screen.getAllByTestId('card-title');
      const titles = cardTitles.map(el => el.textContent);
      expect(titles).toContain('确权状态分布');
    });

    it('should display usage status distribution card title', async () => {
      const AssetDistributionChart = (await import('../AssetDistributionChart')).default;
      render(<AssetDistributionChart />);
      const cardTitles = screen.getAllByTestId('card-title');
      const titles = cardTitles.map(el => el.textContent);
      expect(titles).toContain('使用状态分布');
    });

    it('should display ownership entity distribution card title', async () => {
      const AssetDistributionChart = (await import('../AssetDistributionChart')).default;
      render(<AssetDistributionChart />);
      const cardTitles = screen.getAllByTestId('card-title');
      const titles = cardTitles.map(el => el.textContent);
      expect(titles.some(t => t?.includes('权属方'))).toBe(true);
    });

    it('should display property nature details card title', async () => {
      const AssetDistributionChart = (await import('../AssetDistributionChart')).default;
      render(<AssetDistributionChart />);
      const cardTitles = screen.getAllByTestId('card-title');
      const titles = cardTitles.map(el => el.textContent);
      expect(titles).toContain('物业性质详情');
    });

    it('should display usage status details card title', async () => {
      const AssetDistributionChart = (await import('../AssetDistributionChart')).default;
      render(<AssetDistributionChart />);
      const cardTitles = screen.getAllByTestId('card-title');
      const titles = cardTitles.map(el => el.textContent);
      expect(titles).toContain('使用状态详情');
    });
  });

  describe('Loading State', () => {
    it('should show spin component when loading', async () => {
      mockUseQuery.mockReturnValue({
        data: undefined,
        isLoading: true,
        error: null,
      });
      const AssetDistributionChart = (await import('../AssetDistributionChart')).default;
      render(<AssetDistributionChart />);
      const spinElements = screen.getAllByTestId('spin');
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
      const AssetDistributionChart = (await import('../AssetDistributionChart')).default;
      render(<AssetDistributionChart />);
      expect(screen.getByTestId('alert')).toBeInTheDocument();
      expect(screen.getByTestId('alert')).toHaveAttribute('data-type', 'error');
    });

    it('should display error message in Alert', async () => {
      mockUseQuery.mockReturnValue({
        data: undefined,
        isLoading: false,
        error: new Error('Failed to load'),
      });
      const AssetDistributionChart = (await import('../AssetDistributionChart')).default;
      render(<AssetDistributionChart />);
      expect(screen.getByTestId('alert-message')).toHaveTextContent('数据加载失败');
    });
  });

  describe('Data Query', () => {
    it('should call useQuery with correct query key', async () => {
      const AssetDistributionChart = (await import('../AssetDistributionChart')).default;
      render(<AssetDistributionChart />);
      expect(mockUseQuery).toHaveBeenCalled();
      const callArgs = mockUseQuery.mock.calls[0][0];
      expect(callArgs.queryKey).toContain('asset-distribution-stats');
    });

    it('should include filters in query key', async () => {
      const AssetDistributionChart = (await import('../AssetDistributionChart')).default;
      const filters = { ownership_status: '自有' };
      render(<AssetDistributionChart filters={filters} />);
      const callArgs = mockUseQuery.mock.calls[0][0];
      expect(callArgs.queryKey).toContain(filters);
    });
  });

  describe('Edge Cases', () => {
    it('should handle undefined filters', async () => {
      const AssetDistributionChart = (await import('../AssetDistributionChart')).default;
      render(<AssetDistributionChart filters={undefined} />);
      expect(screen.getAllByTestId('card').length).toBeGreaterThan(0);
    });

    it('should handle empty filters', async () => {
      const AssetDistributionChart = (await import('../AssetDistributionChart')).default;
      render(<AssetDistributionChart filters={{}} />);
      expect(screen.getAllByTestId('card').length).toBeGreaterThan(0);
    });

    it('should handle empty data', async () => {
      mockUseQuery.mockReturnValue({
        data: undefined,
        isLoading: false,
        error: null,
      });
      const AssetDistributionChart = (await import('../AssetDistributionChart')).default;
      render(<AssetDistributionChart />);
      expect(screen.getAllByTestId('card').length).toBeGreaterThan(0);
    });

    it('should handle height of 0', async () => {
      const AssetDistributionChart = (await import('../AssetDistributionChart')).default;
      render(<AssetDistributionChart height={0} />);
      const pieCharts = screen.getAllByTestId('pie-chart');
      expect(pieCharts[0]).toHaveAttribute('data-height', '0');
    });
  });
});
