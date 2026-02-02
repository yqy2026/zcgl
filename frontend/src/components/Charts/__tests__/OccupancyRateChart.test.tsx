/**
 * OccupancyRateChart 组件测试
 *
 * 修复说明：
 * - 移除 antd 所有组件 mock
 * - 保留 @tanstack/react-query mock
 * - 保留 @ant-design/plots mock
 * - 使用文本内容和 className 进行断言
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import React from 'react';

const mockUseQuery = vi.fn();
vi.mock('@tanstack/react-query', () => ({
  useQuery: (options: unknown) => mockUseQuery(options),
}));

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

const mockData = {
  occupancy_trend: [
    { date: '2024-01', occupancy_rate: 85.5 },
    { date: '2024-02', occupancy_rate: 87.2 },
  ],
  by_property_nature: [
    { property_nature: '经营类', occupancy_rate: 90.0 },
    { property_nature: '非经营类', occupancy_rate: 80.0 },
  ],
};

describe('OccupancyRateChart', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseQuery.mockReturnValue({
      data: mockData,
      isLoading: false,
      error: null,
    });
  });

  it('should render without crashing', async () => {
    const OccupancyRateChart = (await import('../OccupancyRateChart')).default;
    render(<OccupancyRateChart />);
    expect(screen.getAllByTestId('line-chart').length).toBeGreaterThanOrEqual(1);
  });

  it('should render with custom height', async () => {
    const OccupancyRateChart = (await import('../OccupancyRateChart')).default;
    render(<OccupancyRateChart height={400} />);
    const charts = screen.getAllByTestId('line-chart');
    expect(charts[0]).toHaveAttribute('data-height', '400');
  });

  it('should display title', async () => {
    const OccupancyRateChart = (await import('../OccupancyRateChart')).default;
    render(<OccupancyRateChart />);
    expect(screen.getByText('出租率统计')).toBeInTheDocument();
  });
});
