/**
 * OccupancyRateChart 组件测试
 * 测试出租率图表组件
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
  Line: ({ height }: { height?: number }) => (
    <div data-testid="line-chart" data-height={height}>
      Line Chart
    </div>
  ),
  Column: ({ height }: { height?: number }) => (
    <div data-testid="column-chart" data-height={height}>
      Column Chart
    </div>
  ),
  Pie: ({ height }: { height?: number }) => (
    <div data-testid="pie-chart" data-height={height}>
      Pie Chart
    </div>
  ),
}));

// Mock Ant Design components
vi.mock('antd', () => ({
  Card: ({
    children,
    title,
  }: {
    children?: React.ReactNode;
    title?: React.ReactNode;
  }) => (
    <div data-testid="card">
      {title && <div data-testid="card-title">{title}</div>}
      {children}
    </div>
  ),
  Row: ({ children }: { children?: React.ReactNode }) => (
    <div data-testid="row">{children}</div>
  ),
  Col: ({ children }: { children?: React.ReactNode }) => (
    <div data-testid="col">{children}</div>
  ),
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
  Spin: ({
    children,
    spinning,
  }: {
    children?: React.ReactNode;
    spinning?: boolean;
  }) => (
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
}));

// Mock icons
vi.mock('@ant-design/icons', () => ({
  PercentageOutlined: () => <span data-testid="icon-percentage" />,
  RiseOutlined: () => <span data-testid="icon-rise" />,
  FallOutlined: () => <span data-testid="icon-fall" />,
  MinusOutlined: () => <span data-testid="icon-minus" />,
}));

// Mock asset service
vi.mock('@/services/assetService', () => ({
  assetService: {
    getOccupancyRateStats: vi.fn(),
  },
}));

// Sample mock data
const mockOccupancyData = {
  overall_rate: 85.5,
  trend: 'up' as const,
  trend_percentage: 2.5,
  by_property_nature: [
    { property_nature: '经营类', rate: 90.0, total_area: 10000, rented_area: 9000 },
    { property_nature: '非经营类', rate: 75.0, total_area: 5000, rented_area: 3750 },
  ],
  by_ownership_entity: [
    { ownership_entity: '权属方A', rate: 88.0, asset_count: 10 },
    { ownership_entity: '权属方B', rate: 82.0, asset_count: 8 },
  ],
  monthly_trend: [
    { month: '2024-01', rate: 80.0, total_area: 15000, rented_area: 12000 },
    { month: '2024-02', rate: 85.0, total_area: 15000, rented_area: 12750 },
  ],
  top_performers: [
    { property_name: '资产A', rate: 98.0, area: 1000 },
    { property_name: '资产B', rate: 95.0, area: 800 },
  ],
  low_performers: [
    { property_name: '资产X', rate: 20.0, area: 500 },
    { property_name: '资产Y', rate: 30.0, area: 600 },
  ],
};

describe('OccupancyRateChart', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Default mock: loading complete with data
    mockUseQuery.mockReturnValue({
      data: mockOccupancyData,
      isLoading: false,
      error: null,
    });
  });

  describe('Component Import', () => {
    it('should be able to import OccupancyRateChart component', async () => {
      const module = await import('../OccupancyRateChart');
      expect(module).toBeDefined();
      expect(module.default).toBeDefined();
    });
  });

  describe('Basic Rendering', () => {
    it('should render without crashing', async () => {
      const OccupancyRateChart = (await import('../OccupancyRateChart')).default;
      render(<OccupancyRateChart />);
      expect(screen.getAllByTestId('card').length).toBeGreaterThan(0);
    });

    it('should render with filters prop', async () => {
      const OccupancyRateChart = (await import('../OccupancyRateChart')).default;
      const filters = { ownership_status: '自有' };
      render(<OccupancyRateChart filters={filters} />);
      expect(screen.getAllByTestId('card').length).toBeGreaterThan(0);
    });

    it('should render with custom height prop', async () => {
      const OccupancyRateChart = (await import('../OccupancyRateChart')).default;
      render(<OccupancyRateChart height={500} />);
      const lineChart = screen.getByTestId('line-chart');
      expect(lineChart).toHaveAttribute('data-height', '500');
    });
  });

  describe('Statistics Display', () => {
    it('should display overall occupancy rate statistic', async () => {
      const OccupancyRateChart = (await import('../OccupancyRateChart')).default;
      render(<OccupancyRateChart />);
      const statisticTitles = screen.getAllByTestId('statistic-title');
      const titles = statisticTitles.map(el => el.textContent);
      expect(titles).toContain('总体出租率');
    });

    it('should display trend change statistic', async () => {
      const OccupancyRateChart = (await import('../OccupancyRateChart')).default;
      render(<OccupancyRateChart />);
      const statisticTitles = screen.getAllByTestId('statistic-title');
      const titles = statisticTitles.map(el => el.textContent);
      expect(titles).toContain('趋势变化');
    });

    it('should display commercial property occupancy rate', async () => {
      const OccupancyRateChart = (await import('../OccupancyRateChart')).default;
      render(<OccupancyRateChart />);
      const statisticTitles = screen.getAllByTestId('statistic-title');
      const titles = statisticTitles.map(el => el.textContent);
      expect(titles).toContain('经营类物业出租率');
    });

    it('should display ownership entity count', async () => {
      const OccupancyRateChart = (await import('../OccupancyRateChart')).default;
      render(<OccupancyRateChart />);
      const statisticTitles = screen.getAllByTestId('statistic-title');
      const titles = statisticTitles.map(el => el.textContent);
      expect(titles).toContain('权属方数量');
    });
  });

  describe('Chart Components', () => {
    it('should render trend line chart', async () => {
      const OccupancyRateChart = (await import('../OccupancyRateChart')).default;
      render(<OccupancyRateChart />);
      expect(screen.getByTestId('line-chart')).toBeInTheDocument();
    });

    it('should render property nature pie chart', async () => {
      const OccupancyRateChart = (await import('../OccupancyRateChart')).default;
      render(<OccupancyRateChart />);
      expect(screen.getByTestId('pie-chart')).toBeInTheDocument();
    });

    it('should render ownership entity column chart', async () => {
      const OccupancyRateChart = (await import('../OccupancyRateChart')).default;
      render(<OccupancyRateChart />);
      expect(screen.getByTestId('column-chart')).toBeInTheDocument();
    });
  });

  describe('Card Titles', () => {
    it('should display trend analysis card title', async () => {
      const OccupancyRateChart = (await import('../OccupancyRateChart')).default;
      render(<OccupancyRateChart />);
      const cardTitles = screen.getAllByTestId('card-title');
      const titles = cardTitles.map(el => el.textContent);
      expect(titles).toContain('出租率趋势分析');
    });

    it('should display property nature distribution card title', async () => {
      const OccupancyRateChart = (await import('../OccupancyRateChart')).default;
      render(<OccupancyRateChart />);
      const cardTitles = screen.getAllByTestId('card-title');
      const titles = cardTitles.map(el => el.textContent);
      expect(titles).toContain('物业性质出租率分布');
    });

    it('should display ownership entity comparison card title', async () => {
      const OccupancyRateChart = (await import('../OccupancyRateChart')).default;
      render(<OccupancyRateChart />);
      const cardTitles = screen.getAllByTestId('card-title');
      const titles = cardTitles.map(el => el.textContent);
      expect(titles).toContain('权属方出租率对比');
    });

    it('should display top performers card title', async () => {
      const OccupancyRateChart = (await import('../OccupancyRateChart')).default;
      render(<OccupancyRateChart />);
      const cardTitles = screen.getAllByTestId('card-title');
      const titles = cardTitles.map(el => el.textContent);
      expect(titles).toContain('出租率最高资产');
    });

    it('should display low performers card title', async () => {
      const OccupancyRateChart = (await import('../OccupancyRateChart')).default;
      render(<OccupancyRateChart />);
      const cardTitles = screen.getAllByTestId('card-title');
      const titles = cardTitles.map(el => el.textContent);
      expect(titles).toContain('出租率最低资产');
    });
  });

  describe('Loading State', () => {
    it('should show spin component when loading', async () => {
      mockUseQuery.mockReturnValue({
        data: undefined,
        isLoading: true,
        error: null,
      });
      const OccupancyRateChart = (await import('../OccupancyRateChart')).default;
      render(<OccupancyRateChart />);
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
      const OccupancyRateChart = (await import('../OccupancyRateChart')).default;
      render(<OccupancyRateChart />);
      expect(screen.getByTestId('alert')).toBeInTheDocument();
      expect(screen.getByTestId('alert')).toHaveAttribute('data-type', 'error');
    });

    it('should display error message in Alert', async () => {
      mockUseQuery.mockReturnValue({
        data: undefined,
        isLoading: false,
        error: new Error('Failed to load'),
      });
      const OccupancyRateChart = (await import('../OccupancyRateChart')).default;
      render(<OccupancyRateChart />);
      expect(screen.getByTestId('alert-message')).toHaveTextContent('数据加载失败');
    });
  });

  describe('Data Query', () => {
    it('should call useQuery with correct query key', async () => {
      const OccupancyRateChart = (await import('../OccupancyRateChart')).default;
      render(<OccupancyRateChart />);
      expect(mockUseQuery).toHaveBeenCalled();
      const callArgs = mockUseQuery.mock.calls[0][0];
      expect(callArgs.queryKey).toContain('occupancy-rate-stats');
    });

    it('should include filters in query key', async () => {
      const OccupancyRateChart = (await import('../OccupancyRateChart')).default;
      const filters = { ownership_status: '自有' };
      render(<OccupancyRateChart filters={filters} />);
      const callArgs = mockUseQuery.mock.calls[0][0];
      expect(callArgs.queryKey).toContain(filters);
    });
  });

  describe('Edge Cases', () => {
    it('should handle undefined filters', async () => {
      const OccupancyRateChart = (await import('../OccupancyRateChart')).default;
      render(<OccupancyRateChart filters={undefined} />);
      expect(screen.getAllByTestId('card').length).toBeGreaterThan(0);
    });

    it('should handle empty filters', async () => {
      const OccupancyRateChart = (await import('../OccupancyRateChart')).default;
      render(<OccupancyRateChart filters={{}} />);
      expect(screen.getAllByTestId('card').length).toBeGreaterThan(0);
    });

    it('should handle empty data', async () => {
      mockUseQuery.mockReturnValue({
        data: undefined,
        isLoading: false,
        error: null,
      });
      const OccupancyRateChart = (await import('../OccupancyRateChart')).default;
      render(<OccupancyRateChart />);
      expect(screen.getAllByTestId('card').length).toBeGreaterThan(0);
    });
  });
});
