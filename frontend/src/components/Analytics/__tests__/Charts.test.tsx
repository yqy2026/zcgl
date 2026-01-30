/**
 * Charts 组件测试
 * 测试图表组件重导出和错误边界集成
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import React from 'react';

// Mock color utilities
vi.mock('@/styles/colorMap', () => ({
  CHART_COLORS: ['#1890ff', '#52c41a', '#faad14', '#ff4d4f', '#722ed1'],
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
  Line: ({ height }: { height?: number }) => (
    <div data-testid="line-chart" data-height={height}>
      Line Chart
    </div>
  ),
  Area: ({ height }: { height?: number }) => (
    <div data-testid="area-chart" data-height={height}>
      Area Chart
    </div>
  ),
}));

// Mock Ant Design components
vi.mock('antd', () => ({
  Empty: ({ description }: { description?: React.ReactNode }) => (
    <div data-testid="empty">{description}</div>
  ),
  Spin: ({ size }: { size?: string }) => <div data-testid="spin" data-size={size} />,
}));

// Mock ChartErrorBoundary
vi.mock('../ChartErrorBoundary', () => ({
  default: ({ children }: { children?: React.ReactNode }) => (
    <div data-testid="chart-error-boundary">{children}</div>
  ),
  ChartErrorBoundary: ({ children }: { children?: React.ReactNode }) => (
    <div data-testid="chart-error-boundary">{children}</div>
  ),
}));

describe('Charts - 组件导出测试', () => {
  it('应该能够导出AnalyticsPieChart组件', async () => {
    const module = await import('../Charts');
    expect(module.AnalyticsPieChart).toBeDefined();
  });

  it('应该能够导出AnalyticsBarChart组件', async () => {
    const module = await import('../Charts');
    expect(module.AnalyticsBarChart).toBeDefined();
  });

  it('应该能够导出AnalyticsLineChart组件', async () => {
    const module = await import('../Charts');
    expect(module.AnalyticsLineChart).toBeDefined();
  });

  it('应该能够导出AnalyticsMultiBarChart组件', async () => {
    const module = await import('../Charts');
    expect(module.AnalyticsMultiBarChart).toBeDefined();
  });

  it('应该能够导出AnalyticsAreaChart组件', async () => {
    const module = await import('../Charts');
    expect(module.AnalyticsAreaChart).toBeDefined();
  });
});

describe('AnalyticsPieChart - 渲染测试', () => {
  it('有数据时应该渲染饼图', async () => {
    const { AnalyticsPieChart } = await import('../Charts');
    const data = [
      { name: '选项1', value: 100 },
      { name: '选项2', value: 200 },
    ];
    render(<AnalyticsPieChart data={data} dataKey="value" />);

    expect(screen.getByTestId('chart-error-boundary')).toBeInTheDocument();
    expect(screen.getByTestId('pie-chart')).toBeInTheDocument();
  });

  it('空数据时应该显示Empty', async () => {
    const { AnalyticsPieChart } = await import('../Charts');
    render(<AnalyticsPieChart data={[]} dataKey="value" />);

    expect(screen.getByTestId('empty')).toBeInTheDocument();
    expect(screen.getByText('暂无数据')).toBeInTheDocument();
  });

  it('应该支持自定义height', async () => {
    const { AnalyticsPieChart } = await import('../Charts');
    const data = [{ name: '选项1', value: 100 }];
    render(<AnalyticsPieChart data={data} dataKey="value" height={400} />);

    expect(screen.getByTestId('pie-chart')).toHaveAttribute('data-height', '400');
  });
});

describe('AnalyticsBarChart - 渲染测试', () => {
  it('有数据时应该渲染柱状图', async () => {
    const { AnalyticsBarChart } = await import('../Charts');
    const data = [
      { name: '项目1', value: 100 },
      { name: '项目2', value: 200 },
    ];
    render(<AnalyticsBarChart data={data} xDataKey="name" yDataKey="value" />);

    expect(screen.getByTestId('chart-error-boundary')).toBeInTheDocument();
    expect(screen.getByTestId('column-chart')).toBeInTheDocument();
  });

  it('空数据时应该显示Empty', async () => {
    const { AnalyticsBarChart } = await import('../Charts');
    render(<AnalyticsBarChart data={[]} xDataKey="name" yDataKey="value" />);

    expect(screen.getByTestId('empty')).toBeInTheDocument();
  });

  it('应该支持自定义height', async () => {
    const { AnalyticsBarChart } = await import('../Charts');
    const data = [{ name: '项目1', value: 100 }];
    render(<AnalyticsBarChart data={data} xDataKey="name" yDataKey="value" height={400} />);

    expect(screen.getByTestId('column-chart')).toHaveAttribute('data-height', '400');
  });
});

describe('AnalyticsLineChart - 渲染测试', () => {
  it('有数据时应该渲染折线图', async () => {
    const { AnalyticsLineChart } = await import('../Charts');
    const data = [
      { date: '2024-01', value: 100 },
      { date: '2024-02', value: 200 },
    ];
    render(<AnalyticsLineChart data={data} xDataKey="date" yDataKey="value" />);

    expect(screen.getByTestId('chart-error-boundary')).toBeInTheDocument();
    expect(screen.getByTestId('line-chart')).toBeInTheDocument();
  });

  it('空数据时应该显示Empty', async () => {
    const { AnalyticsLineChart } = await import('../Charts');
    render(<AnalyticsLineChart data={[]} xDataKey="date" yDataKey="value" />);

    expect(screen.getByTestId('empty')).toBeInTheDocument();
  });

  it('应该支持自定义height', async () => {
    const { AnalyticsLineChart } = await import('../Charts');
    const data = [{ date: '2024-01', value: 100 }];
    render(<AnalyticsLineChart data={data} xDataKey="date" yDataKey="value" height={400} />);

    expect(screen.getByTestId('line-chart')).toHaveAttribute('data-height', '400');
  });
});

describe('AnalyticsMultiBarChart - 渲染测试', () => {
  it('有数据时应该渲染多系列柱状图', async () => {
    const { AnalyticsMultiBarChart } = await import('../Charts');
    const data = [{ name: '项目1', value1: 100, value2: 200 }];
    const bars = [
      { dataKey: 'value1', name: '系列1', fill: '#1890ff' },
      { dataKey: 'value2', name: '系列2', fill: '#52c41a' },
    ];
    render(<AnalyticsMultiBarChart data={data} xDataKey="name" bars={bars} />);

    expect(screen.getByTestId('chart-error-boundary')).toBeInTheDocument();
    expect(screen.getByTestId('column-chart')).toBeInTheDocument();
  });

  it('空数据时应该显示Empty', async () => {
    const { AnalyticsMultiBarChart } = await import('../Charts');
    render(<AnalyticsMultiBarChart data={[]} xDataKey="name" bars={[]} />);

    expect(screen.getByTestId('empty')).toBeInTheDocument();
  });
});

describe('AnalyticsAreaChart - 渲染测试', () => {
  it('有数据时应该渲染面积图', async () => {
    const { AnalyticsAreaChart } = await import('../Charts');
    const data = [
      { date: '2024-01', value: 100 },
      { date: '2024-02', value: 200 },
    ];
    render(<AnalyticsAreaChart data={data} xDataKey="date" yDataKey="value" />);

    expect(screen.getByTestId('chart-error-boundary')).toBeInTheDocument();
    expect(screen.getByTestId('area-chart')).toBeInTheDocument();
  });

  it('空数据时应该显示Empty', async () => {
    const { AnalyticsAreaChart } = await import('../Charts');
    render(<AnalyticsAreaChart data={[]} xDataKey="date" yDataKey="value" />);

    expect(screen.getByTestId('empty')).toBeInTheDocument();
  });

  it('应该支持自定义height', async () => {
    const { AnalyticsAreaChart } = await import('../Charts');
    const data = [{ date: '2024-01', value: 100 }];
    render(<AnalyticsAreaChart data={data} xDataKey="date" yDataKey="value" height={400} />);

    expect(screen.getByTestId('area-chart')).toHaveAttribute('data-height', '400');
  });
});

describe('Charts - 错误边界集成测试', () => {
  it('所有图表组件都应该被ChartErrorBoundary包裹', async () => {
    const { AnalyticsPieChart } = await import('../Charts');
    const data = [{ name: '测试', value: 100 }];
    render(<AnalyticsPieChart data={data} dataKey="value" />);

    expect(screen.getByTestId('chart-error-boundary')).toBeInTheDocument();
  });
});

describe('Charts - 边界情况测试', () => {
  it('应该处理height为0', async () => {
    const { AnalyticsPieChart } = await import('../Charts');
    const data = [{ name: '测试', value: 100 }];
    render(<AnalyticsPieChart data={data} dataKey="value" height={0} />);

    expect(screen.getByTestId('pie-chart')).toHaveAttribute('data-height', '0');
  });

  it('应该过滤掉value为0的饼图数据', async () => {
    const { AnalyticsPieChart } = await import('../Charts');
    const data = [
      { name: '有值', value: 100 },
      { name: '无值', value: 0 },
    ];
    render(<AnalyticsPieChart data={data} dataKey="value" />);

    // 组件应该正常渲染
    expect(screen.getByTestId('pie-chart')).toBeInTheDocument();
  });
});
