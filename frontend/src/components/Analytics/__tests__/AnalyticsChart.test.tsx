/**
 * AnalyticsChart 组件测试（修复版）
 * 测试分析图表组件
 *
 * 修复内容：
 * - 移除过度的 Ant Design 组件 mock
 * - 使用 renderWithProviders 提供必要的 Context Provider
 * - 保留必要的 mock（@ant-design/plots, color utilities）
 * - 添加 beforeEach 清除 mock
 * - 保持完整的测试覆盖
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { renderWithProviders, screen } from '@/test/utils/test-helpers';
import React from 'react';

// Mock color utilities（这个 mock 是必要的）
vi.mock('@/styles/colorMap', () => ({
  CHART_COLORS: ['#1890ff', '#52c41a', '#faad14', '#ff4d4f', '#722ed1'],
  CHART_LABEL_COLORS: {
    light: '#fff',
    medium: '#666',
  },
}));

// Mock @ant-design/plots（这个 mock 是必要的，因为图表库依赖复杂）
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
  Line: ({ height }: { height?: number }) => (
    <div data-testid="line-chart" data-height={height}>
      Line Chart
    </div>
  ),
}));

describe('AnalyticsChart - 组件导出测试', () => {
  it('应该能够导出AnalyticsPieChart组件', async () => {
    const { AnalyticsPieChart } = await import('../AnalyticsChart');
    expect(AnalyticsPieChart).toBeDefined();
  });

  it('应该能够导出AnalyticsBarChart组件', async () => {
    const { AnalyticsBarChart } = await import('../AnalyticsChart');
    expect(AnalyticsBarChart).toBeDefined();
  });

  it('应该能够导出AnalyticsLineChart组件', async () => {
    const { AnalyticsLineChart } = await import('../AnalyticsChart');
    expect(AnalyticsLineChart).toBeDefined();
  });

  it('应该能够导出chartDataUtils工具函数', async () => {
    const { chartDataUtils } = await import('../AnalyticsChart');
    expect(chartDataUtils).toBeDefined();
  });
});

describe('AnalyticsPieChart - 渲染测试', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('有数据时应该渲染饼图', async () => {
    const { AnalyticsPieChart } = await import('../AnalyticsChart');
    const data = [
      { type: '选项1', value: 100 },
      { type: '选项2', value: 200 },
    ];
    renderWithProviders(<AnalyticsPieChart title="测试饼图" data={data} />);

    expect(screen.getByText('测试饼图')).toBeInTheDocument();
    expect(screen.getByTestId('pie-chart')).toBeInTheDocument();
  });

  it('空数据时应该显示Empty', async () => {
    const { AnalyticsPieChart } = await import('../AnalyticsChart');
    renderWithProviders(<AnalyticsPieChart title="空饼图" data={[]} />);

    const emptyText = screen.getAllByText('暂无数据');
    expect(emptyText.length).toBeGreaterThan(0);
  });

  it('应该支持自定义height', async () => {
    const { AnalyticsPieChart } = await import('../AnalyticsChart');
    const data = [{ type: '选项1', value: 100 }];
    renderWithProviders(<AnalyticsPieChart title="测试" data={data} height={400} />);

    expect(screen.getByTestId('pie-chart')).toHaveAttribute('data-height', '400');
  });

  it('默认height应该是300', async () => {
    const { AnalyticsPieChart } = await import('../AnalyticsChart');
    const data = [{ type: '选项1', value: 100 }];
    renderWithProviders(<AnalyticsPieChart title="测试" data={data} />);

    expect(screen.getByTestId('pie-chart')).toHaveAttribute('data-height', '300');
  });
});

describe('AnalyticsBarChart - 渲染测试', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('有数据时应该渲染柱状图', async () => {
    const { AnalyticsBarChart } = await import('../AnalyticsChart');
    const data = [
      { name: '项目1', value: 100 },
      { name: '项目2', value: 200 },
    ];
    renderWithProviders(<AnalyticsBarChart title="测试柱状图" data={data} xAxisKey="name" barKey="value" />);

    expect(screen.getByText('测试柱状图')).toBeInTheDocument();
    expect(screen.getByTestId('column-chart')).toBeInTheDocument();
  });

  it('空数据时应该显示Empty', async () => {
    const { AnalyticsBarChart } = await import('../AnalyticsChart');
    renderWithProviders(<AnalyticsBarChart title="空柱状图" data={[]} xAxisKey="name" barKey="value" />);

    const emptyText = screen.getAllByText('暂无数据');
    expect(emptyText.length).toBeGreaterThan(0);
  });

  it('应该支持自定义height', async () => {
    const { AnalyticsBarChart } = await import('../AnalyticsChart');
    const data = [{ name: '项目1', value: 100 }];
    renderWithProviders(<AnalyticsBarChart title="测试" data={data} xAxisKey="name" barKey="value" height={400} />);

    expect(screen.getByTestId('column-chart')).toHaveAttribute('data-height', '400');
  });
});

describe('AnalyticsLineChart - 渲染测试', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('有数据时应该渲染折线图', async () => {
    const { AnalyticsLineChart } = await import('../AnalyticsChart');
    const data = [
      { date: '2024-01', value: 100 },
      { date: '2024-02', value: 200 },
    ];
    const lines = [{ key: 'value', name: '趋势', color: '#1890ff' }];
    renderWithProviders(<AnalyticsLineChart title="测试折线图" data={data} xAxisKey="date" lines={lines} />);

    expect(screen.getByText('测试折线图')).toBeInTheDocument();
    expect(screen.getByTestId('line-chart')).toBeInTheDocument();
  });

  it('空数据时应该显示Empty', async () => {
    const { AnalyticsLineChart } = await import('../AnalyticsChart');
    const lines = [{ key: 'value', name: '趋势', color: '#1890ff' }];
    renderWithProviders(<AnalyticsLineChart title="空折线图" data={[]} xAxisKey="date" lines={lines} />);

    const emptyText = screen.getAllByText('暂无数据');
    expect(emptyText.length).toBeGreaterThan(0);
  });

  it('应该支持自定义height', async () => {
    const { AnalyticsLineChart } = await import('../AnalyticsChart');
    const data = [{ date: '2024-01', value: 100 }];
    const lines = [{ key: 'value', name: '趋势', color: '#1890ff' }];
    renderWithProviders(<AnalyticsLineChart title="测试" data={data} xAxisKey="date" lines={lines} height={400} />);

    expect(screen.getByTestId('line-chart')).toHaveAttribute('data-height', '400');
  });
});

describe('chartDataUtils - 数据转换工具测试', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('toPieData应该正确转换数据格式', async () => {
    const { chartDataUtils } = await import('../AnalyticsChart');
    const input = [
      { name: '选项1', count: 100, percentage: 10 },
      { name: '选项2', count: 200, percentage: 20 },
    ];
    const result = chartDataUtils.toPieData(input);

    expect(result).toEqual([
      { type: '选项1', value: 100, count: 100, percentage: 10 },
      { type: '选项2', value: 200, count: 200, percentage: 20 },
    ]);
  });

  it('toBusinessCategoryData应该正确转换数据格式', async () => {
    const { chartDataUtils } = await import('../AnalyticsChart');
    const input = [
      { category: '类别1', count: 100, occupancy_rate: 80 },
      { category: '类别2', count: 200, occupancy_rate: 90 },
    ];
    const result = chartDataUtils.toBusinessCategoryData(input);

    expect(result).toEqual([
      { name: '类别1', value: 100, count: 100, occupancy_rate: 80 },
      { name: '类别2', value: 200, count: 200, occupancy_rate: 90 },
    ]);
  });

  it('toOccupancyData应该正确转换数据格式', async () => {
    const { chartDataUtils } = await import('../AnalyticsChart');
    const input = [
      { range: '0-20%', count: 10, percentage: 10 },
      { range: '20-40%', count: 20, percentage: 20 },
    ];
    const result = chartDataUtils.toOccupancyData(input);

    expect(result).toEqual([
      { name: '0-20%', value: 10, count: 10, percentage: 10 },
      { name: '20-40%', value: 20, count: 20, percentage: 20 },
    ]);
  });

  it('toTrendData应该正确转换数据格式', async () => {
    const { chartDataUtils } = await import('../AnalyticsChart');
    const input = [
      {
        date: '2024-01-01',
        occupancy_rate: 85,
        total_rented_area: 1000,
        total_rentable_area: 1200,
      },
    ];
    const result = chartDataUtils.toTrendData(input);

    expect(result).toEqual([
      {
        date: '2024-01-01',
        occupancy_rate: 85,
        total_rented_area: 1000,
        total_rentable_area: 1200,
      },
    ]);
  });

  it('toAreaData应该正确转换数据格式', async () => {
    const { chartDataUtils } = await import('../AnalyticsChart');
    const input = [{ name: '商业', total_area: 1000, area_percentage: 10, average_area: 100 }];
    const result = chartDataUtils.toAreaData(input);

    expect(result).toEqual([
      { type: '商业', value: 1000, total_area: 1000, percentage: 10, average_area: 100 },
    ]);
  });

  it('toAreaBarData应该正确转换数据格式', async () => {
    const { chartDataUtils } = await import('../AnalyticsChart');
    const input = [{ name: '办公', total_area: 500, count: 10, average_area: 50 }];
    const result = chartDataUtils.toAreaBarData(input);

    expect(result[0]).toHaveProperty('name', '办公');
    expect(result[0]).toHaveProperty('value', 500);
    expect(result[0]).toHaveProperty('count', 10);
  });

  it('toBusinessCategoryAreaData应该正确转换数据格式', async () => {
    const { chartDataUtils } = await import('../AnalyticsChart');
    const input = [
      { category: '零售', total_area: 800, area_percentage: 40, occupancy_rate: 75 },
    ];
    const result = chartDataUtils.toBusinessCategoryAreaData(input);

    expect(result[0]).toHaveProperty('name', '零售');
    expect(result[0]).toHaveProperty('value', 800);
    expect(result[0]).toHaveProperty('occupancy_rate', 75);
  });
});

describe('AnalyticsChart - 边界情况测试', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('应该处理value为0的选项', async () => {
    const { AnalyticsPieChart } = await import('../AnalyticsChart');
    const data = [{ type: '选项1', value: 0 }];
    renderWithProviders(<AnalyticsPieChart title="测试" data={data} />);

    // 应该正常渲染
    expect(screen.getByText('测试')).toBeInTheDocument();
  });

  it('应该处理负数value', async () => {
    const { AnalyticsBarChart } = await import('../AnalyticsChart');
    const data = [{ name: '选项1', value: -100 }];
    renderWithProviders(<AnalyticsBarChart title="测试" data={data} xAxisKey="name" barKey="value" />);

    // 应该正常渲染
    expect(screen.getByText('测试')).toBeInTheDocument();
  });
});
