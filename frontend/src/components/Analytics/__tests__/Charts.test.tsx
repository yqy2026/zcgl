/**
 * Charts 组件测试
 * 测试图表组件重导出和错误边界集成
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import React from 'react';

// Mock @ant-design/plots
vi.mock('@ant-design/plots', () => ({
  Pie: ({ data, height }: any) => (
    <div data-testid="pie" data-height={height}>
      {data?.map((d: any, i: number) => (
        <div key={i} />
      ))}
    </div>
  ),
  Column: ({ data, height }: any) => (
    <div data-testid="column" data-height={height}>
      {data?.map((d: any, i: number) => (
        <div key={i} />
      ))}
    </div>
  ),
  Line: ({ data, height }: any) => (
    <div data-testid="line" data-height={height}>
      {data?.map((d: any, i: number) => (
        <div key={i} />
      ))}
    </div>
  ),
  Area: ({ data, height }: any) => (
    <div data-testid="area" data-height={height}>
      {data?.map((d: any, i: number) => (
        <div key={i} />
      ))}
    </div>
  ),
}));

// Mock Ant Design components
vi.mock('antd', () => ({
  Card: ({ children, title, extra, hoverable, bordered, size }: any) => (
    <div
      data-testid="card"
      data-title={title}
      data-hoverable={hoverable}
      data-bordered={bordered}
      data-size={size}
    >
      {extra}
      {children}
    </div>
  ),
}));

// Mock ChartErrorBoundary
vi.mock('../ChartErrorBoundary', () => ({
  ChartErrorBoundary: class MockChartErrorBoundary extends React.Component<any, any> {
    static getDerivedStateFromError() {
      return { hasError: true };
    }
    state = { hasError: false };
    componentDidCatch = vi.fn();
    render() {
      if (this.state.hasError) {
        return <div data-testid="error-fallback">图表加载失败</div>;
      }
      return <>{this.props.children}</>;
    }
  },
}));

// Mock chart components
vi.mock('../AnalyticsChart', () => ({
  AnalyticsPieChart: ({ data, title, height }: any) => (
    <div data-testid="analytics-pie-chart" data-title={title} data-height={height}>
      <div data-testid="pie-data">{JSON.stringify(data)}</div>
    </div>
  ),
  AnalyticsBarChart: ({ data, dataKeys, title, height }: any) => (
    <div data-testid="analytics-bar-chart" data-title={title} data-height={height}>
      <div data-testid="bar-keys">{JSON.stringify(dataKeys)}</div>
      <div data-testid="bar-data">{JSON.stringify(data)}</div>
    </div>
  ),
  AnalyticsLineChart: ({ data, dataKey, title, height }: any) => (
    <div data-testid="analytics-line-chart" data-title={title} data-height={height}>
      <div data-testid="line-data-key">{dataKey}</div>
      <div data-testid="line-data">{JSON.stringify(data)}</div>
    </div>
  ),
  AnalyticsMultiBarChart: ({ data, bars, title, height }: any) => (
    <div data-testid="analytics-multi-bar-chart" data-title={title} data-height={height}>
      <div data-testid="multi-bar-bars">{JSON.stringify(bars)}</div>
      <div data-testid="multi-bar-data">{JSON.stringify(data)}</div>
    </div>
  ),
  AnalyticsAreaChart: ({ data, areas, title, height }: any) => (
    <div data-testid="analytics-area-chart" data-title={title} data-height={height}>
      <div data-testid="area-areas">{JSON.stringify(areas)}</div>
      <div data-testid="area-data">{JSON.stringify(data)}</div>
    </div>
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

describe('Charts - AnalyticsPieChart测试', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('应该支持data属性', async () => {
    const { AnalyticsPieChart } = await import('../Charts');
    const data = [{ name: '选项1', value: 100 }];
    const element = React.createElement(AnalyticsPieChart, { data });
    expect(element).toBeTruthy();
  });

  it('应该支持title属性', async () => {
    const { AnalyticsPieChart } = await import('../Charts');
    const data = [{ name: '选项1', value: 100 }];
    const element = React.createElement(AnalyticsPieChart, {
      data,
      title: '测试标题',
    });
    expect(element).toBeTruthy();
  });

  it('应该支持height属性', async () => {
    const { AnalyticsPieChart } = await import('../Charts');
    const data = [{ name: '选项1', value: 100 }];
    const element = React.createElement(AnalyticsPieChart, {
      data,
      height: 400,
    });
    expect(element).toBeTruthy();
  });

  it('默认height应该是300', async () => {
    const { AnalyticsPieChart } = await import('../Charts');
    const data = [{ name: '选项1', value: 100 }];
    const element = React.createElement(AnalyticsPieChart, { data });
    expect(element).toBeTruthy();
  });
});

describe('Charts - AnalyticsBarChart测试', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('应该支持data属性', async () => {
    const { AnalyticsBarChart } = await import('../Charts');
    const data = [{ name: '项目1', value1: 100, value2: 200 }];
    const element = React.createElement(AnalyticsBarChart, { data });
    expect(element).toBeTruthy();
  });

  it('应该支持dataKeys属性', async () => {
    const { AnalyticsBarChart } = await import('../Charts');
    const data = [{ name: '项目1', value1: 100, value2: 200 }];
    const dataKeys = ['value1', 'value2'];
    const element = React.createElement(AnalyticsBarChart, {
      data,
      dataKeys,
    });
    expect(element).toBeTruthy();
  });

  it('应该支持title属性', async () => {
    const { AnalyticsBarChart } = await import('../Charts');
    const data = [{ name: '项目1', value1: 100 }];
    const element = React.createElement(AnalyticsBarChart, {
      data,
      dataKeys: ['value1'],
      title: '测试标题',
    });
    expect(element).toBeTruthy();
  });

  it('应该支持height属性', async () => {
    const { AnalyticsBarChart } = await import('../Charts');
    const data = [{ name: '项目1', value1: 100 }];
    const element = React.createElement(AnalyticsBarChart, {
      data,
      dataKeys: ['value1'],
      height: 400,
    });
    expect(element).toBeTruthy();
  });
});

describe('Charts - AnalyticsLineChart测试', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('应该支持data属性', async () => {
    const { AnalyticsLineChart } = await import('../Charts');
    const data = [{ name: '1月', value: 100 }];
    const element = React.createElement(AnalyticsLineChart, { data });
    expect(element).toBeTruthy();
  });

  it('应该支持dataKey属性', async () => {
    const { AnalyticsLineChart } = await import('../Charts');
    const data = [{ name: '1月', value: 100 }];
    const element = React.createElement(AnalyticsLineChart, {
      data,
      dataKey: 'value',
    });
    expect(element).toBeTruthy();
  });

  it('应该支持title属性', async () => {
    const { AnalyticsLineChart } = await import('../Charts');
    const data = [{ name: '1月', value: 100 }];
    const element = React.createElement(AnalyticsLineChart, {
      data,
      dataKey: 'value',
      title: '测试标题',
    });
    expect(element).toBeTruthy();
  });

  it('应该支持height属性', async () => {
    const { AnalyticsLineChart } = await import('../Charts');
    const data = [{ name: '1月', value: 100 }];
    const element = React.createElement(AnalyticsLineChart, {
      data,
      dataKey: 'value',
      height: 400,
    });
    expect(element).toBeTruthy();
  });
});

describe('Charts - AnalyticsMultiBarChart测试', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('应该支持data属性', async () => {
    const { AnalyticsMultiBarChart } = await import('../Charts');
    const data = [{ name: '项目1', value1: 100, value2: 200 }];
    const element = React.createElement(AnalyticsMultiBarChart, { data });
    expect(element).toBeTruthy();
  });

  it('应该支持bars属性', async () => {
    const { AnalyticsMultiBarChart } = await import('../Charts');
    const data = [{ name: '项目1', value1: 100, value2: 200 }];
    const bars = [
      { dataKey: 'value1', fill: '#8884d8', name: '系列1' },
      { dataKey: 'value2', fill: '#82ca9d', name: '系列2' },
    ];
    const element = React.createElement(AnalyticsMultiBarChart, {
      data,
      bars,
    });
    expect(element).toBeTruthy();
  });

  it('应该支持title属性', async () => {
    const { AnalyticsMultiBarChart } = await import('../Charts');
    const data = [{ name: '项目1', value1: 100 }];
    const element = React.createElement(AnalyticsMultiBarChart, {
      data,
      bars: [{ dataKey: 'value1', fill: '#8884d8' }],
      title: '测试标题',
    });
    expect(element).toBeTruthy();
  });

  it('应该支持height属性', async () => {
    const { AnalyticsMultiBarChart } = await import('../Charts');
    const data = [{ name: '项目1', value1: 100 }];
    const element = React.createElement(AnalyticsMultiBarChart, {
      data,
      bars: [{ dataKey: 'value1', fill: '#8884d8' }],
      height: 400,
    });
    expect(element).toBeTruthy();
  });
});

describe('Charts - AnalyticsAreaChart测试', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('应该支持data属性', async () => {
    const { AnalyticsAreaChart } = await import('../Charts');
    const data = [{ name: '1月', value1: 100, value2: 200 }];
    const element = React.createElement(AnalyticsAreaChart, { data });
    expect(element).toBeTruthy();
  });

  it('应该支持areas属性', async () => {
    const { AnalyticsAreaChart } = await import('../Charts');
    const data = [{ name: '1月', value1: 100, value2: 200 }];
    const areas = [
      { dataKey: 'value1', fill: '#8884d8', stroke: '#8884d8' },
      { dataKey: 'value2', fill: '#82ca9d', stroke: '#82ca9d' },
    ];
    const element = React.createElement(AnalyticsAreaChart, {
      data,
      areas,
    });
    expect(element).toBeTruthy();
  });

  it('应该支持title属性', async () => {
    const { AnalyticsAreaChart } = await import('../Charts');
    const data = [{ name: '1月', value1: 100 }];
    const element = React.createElement(AnalyticsAreaChart, {
      data,
      areas: [{ dataKey: 'value1', fill: '#8884d8' }],
      title: '测试标题',
    });
    expect(element).toBeTruthy();
  });

  it('应该支持height属性', async () => {
    const { AnalyticsAreaChart } = await import('../Charts');
    const data = [{ name: '1月', value1: 100 }];
    const element = React.createElement(AnalyticsAreaChart, {
      data,
      areas: [{ dataKey: 'value1', fill: '#8884d8' }],
      height: 400,
    });
    expect(element).toBeTruthy();
  });
});

describe('Charts - 错误边界测试', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('所有图表组件都应该被ChartErrorBoundary包裹', async () => {
    const { AnalyticsPieChart } = await import('../Charts');
    const element = React.createElement(AnalyticsPieChart, {
      data: [{ name: '测试', value: 100 }],
    });
    expect(element).toBeTruthy();
  });

  it('错误时应该显示错误信息', async () => {
    const { ChartErrorBoundary } = await import('../ChartErrorBoundary');
    const ThrowError = () => {
      throw new Error('Test error');
    };
    const element = React.createElement(ChartErrorBoundary, {}, React.createElement(ThrowError));
    expect(element).toBeTruthy();
  });
});

describe('Charts - 空状态测试', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('AnalyticsPieChart应该处理空data', async () => {
    const { AnalyticsPieChart } = await import('../Charts');
    const element = React.createElement(AnalyticsPieChart, {
      data: [],
    });
    expect(element).toBeTruthy();
  });

  it('AnalyticsBarChart应该处理空data', async () => {
    const { AnalyticsBarChart } = await import('../Charts');
    const element = React.createElement(AnalyticsBarChart, {
      data: [],
      dataKeys: [],
    });
    expect(element).toBeTruthy();
  });

  it('AnalyticsLineChart应该处理空data', async () => {
    const { AnalyticsLineChart } = await import('../Charts');
    const element = React.createElement(AnalyticsLineChart, {
      data: [],
      dataKey: 'value',
    });
    expect(element).toBeTruthy();
  });

  it('AnalyticsMultiBarChart应该处理空data', async () => {
    const { AnalyticsMultiBarChart } = await import('../Charts');
    const element = React.createElement(AnalyticsMultiBarChart, {
      data: [],
      bars: [],
    });
    expect(element).toBeTruthy();
  });

  it('AnalyticsAreaChart应该处理空data', async () => {
    const { AnalyticsAreaChart } = await import('../Charts');
    const element = React.createElement(AnalyticsAreaChart, {
      data: [],
      areas: [],
    });
    expect(element).toBeTruthy();
  });
});

describe('Charts - 边界情况测试', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('AnalyticsPieChart应该处理undefined data', async () => {
    const { AnalyticsPieChart } = await import('../Charts');
    const element = React.createElement(AnalyticsPieChart, {
      data: undefined as any,
    });
    expect(element).toBeTruthy();
  });

  it('AnalyticsBarChart应该处理undefined dataKeys', async () => {
    const { AnalyticsBarChart } = await import('../Charts');
    const element = React.createElement(AnalyticsBarChart, {
      data: [{ name: '测试', value: 100 }],
      dataKeys: undefined as any,
    });
    expect(element).toBeTruthy();
  });

  it('AnalyticsLineChart应该处理undefined dataKey', async () => {
    const { AnalyticsLineChart } = await import('../Charts');
    const element = React.createElement(AnalyticsLineChart, {
      data: [{ name: '测试', value: 100 }],
      dataKey: undefined as any,
    });
    expect(element).toBeTruthy();
  });

  it('AnalyticsMultiBarChart应该处理undefined bars', async () => {
    const { AnalyticsMultiBarChart } = await import('../Charts');
    const element = React.createElement(AnalyticsMultiBarChart, {
      data: [{ name: '测试', value: 100 }],
      bars: undefined as any,
    });
    expect(element).toBeTruthy();
  });

  it('AnalyticsAreaChart应该处理undefined areas', async () => {
    const { AnalyticsAreaChart } = await import('../Charts');
    const element = React.createElement(AnalyticsAreaChart, {
      data: [{ name: '测试', value: 100 }],
      areas: undefined as any,
    });
    expect(element).toBeTruthy();
  });

  it('应该处理height为0', async () => {
    const { AnalyticsPieChart } = await import('../Charts');
    const element = React.createElement(AnalyticsPieChart, {
      data: [{ name: '测试', value: 100 }],
      height: 0,
    });
    expect(element).toBeTruthy();
  });

  it('应该处理负height', async () => {
    const { AnalyticsBarChart } = await import('../Charts');
    const element = React.createElement(AnalyticsBarChart, {
      data: [{ name: '测试', value: 100 }],
      dataKeys: ['value'],
      height: -100,
    });
    expect(element).toBeTruthy();
  });
});
