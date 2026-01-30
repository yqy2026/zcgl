/**
 * AnalyticsStatsCard 组件测试
 * 测试分析统计卡片组件
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import React from 'react';

// Mock color utilities
vi.mock('@/styles/colorMap', () => ({
  getTrendColor: (trend: number, trendType?: string) =>
    trend > 0 ? (trendType === 'down' ? '#ff4d4f' : '#52c41a') : '#ff4d4f',
  getOccupancyRateColor: (rate: number) =>
    rate >= 80 ? '#52c41a' : rate >= 60 ? '#faad14' : '#ff4d4f',
  COLORS: {
    primary: '#1890ff',
    success: '#52c41a',
    warning: '#faad14',
    error: '#ff4d4f',
    textTertiary: '#8c8c8c',
  },
}));

// Mock Ant Design components
vi.mock('antd', () => ({
  Card: ({
    children,
    loading,
    size,
  }: {
    children?: React.ReactNode;
    loading?: boolean;
    size?: string;
  }) => (
    <div data-testid="card" data-loading={loading} data-size={size}>
      {children}
    </div>
  ),
  Row: ({ children, gutter }: { children?: React.ReactNode; gutter?: unknown }) => (
    <div data-testid="row" data-gutter={JSON.stringify(gutter)}>
      {children}
    </div>
  ),
  Col: ({
    children,
    xs,
    sm,
    lg,
  }: {
    children?: React.ReactNode;
    xs?: number;
    sm?: number;
    lg?: number;
  }) => (
    <div data-testid="col" data-xs={xs} data-sm={sm} data-lg={lg}>
      {children}
    </div>
  ),
  Statistic: ({
    title,
    value,
    precision,
    suffix,
    valueStyle,
  }: {
    title?: React.ReactNode;
    value?: number;
    precision?: number;
    suffix?: React.ReactNode;
    valueStyle?: React.CSSProperties;
  }) => (
    <div data-testid="statistic" style={valueStyle}>
      <div data-testid="statistic-title">{title}</div>
      <div data-testid="statistic-value" data-precision={precision}>
        {value}
        {suffix && <span data-testid="statistic-suffix">{suffix}</span>}
      </div>
    </div>
  ),
}));

// Mock icons
vi.mock('@ant-design/icons', () => ({
  ArrowUpOutlined: () => <span data-testid="icon-arrow-up" />,
  ArrowDownOutlined: () => <span data-testid="icon-arrow-down" />,
  ApartmentOutlined: () => <span data-testid="icon-apartment" />,
  ThunderboltOutlined: () => <span data-testid="icon-thunderbolt" />,
  PieChartOutlined: () => <span data-testid="icon-pie-chart" />,
  MoneyCollectOutlined: () => <span data-testid="icon-money-collect" />,
  TransactionOutlined: () => <span data-testid="icon-transaction" />,
  AreaChartOutlined: () => <span data-testid="icon-area-chart" />,
}));

describe('AnalyticsStatsCard - 组件导入测试', () => {
  it('应该能够导出AnalyticsStatsGrid组件', async () => {
    const module = await import('../AnalyticsStatsCard');
    expect(module).toBeDefined();
    expect(module.AnalyticsStatsGrid).toBeDefined();
  });

  it('应该能够导出FinancialStatsGrid组件', async () => {
    const module = await import('../AnalyticsStatsCard');
    expect(module.FinancialStatsGrid).toBeDefined();
  });
});

describe('AnalyticsStatsGrid - 渲染测试', () => {
  const mockData = {
    total_assets: 100,
    total_area: 5000,
    total_rentable_area: 4000,
    occupancy_rate: 85,
  };

  it('应该渲染Row布局', async () => {
    const { AnalyticsStatsGrid } = await import('../AnalyticsStatsCard');
    render(<AnalyticsStatsGrid data={mockData} />);

    expect(screen.getByTestId('row')).toBeInTheDocument();
  });

  it('应该渲染4个基础统计卡片', async () => {
    const { AnalyticsStatsGrid } = await import('../AnalyticsStatsCard');
    render(<AnalyticsStatsGrid data={mockData} />);

    const cols = screen.getAllByTestId('col');
    expect(cols.length).toBeGreaterThanOrEqual(4);
  });

  it('应该显示资产总数', async () => {
    const { AnalyticsStatsGrid } = await import('../AnalyticsStatsCard');
    render(<AnalyticsStatsGrid data={mockData} />);

    expect(screen.getByText('资产总数')).toBeInTheDocument();
  });

  it('应该显示总面积', async () => {
    const { AnalyticsStatsGrid } = await import('../AnalyticsStatsCard');
    render(<AnalyticsStatsGrid data={mockData} />);

    expect(screen.getByText('总面积')).toBeInTheDocument();
  });

  it('应该显示可租面积', async () => {
    const { AnalyticsStatsGrid } = await import('../AnalyticsStatsCard');
    render(<AnalyticsStatsGrid data={mockData} />);

    expect(screen.getByText('可租面积')).toBeInTheDocument();
  });

  it('应该显示整体出租率', async () => {
    const { AnalyticsStatsGrid } = await import('../AnalyticsStatsCard');
    render(<AnalyticsStatsGrid data={mockData} />);

    expect(screen.getByText('整体出租率')).toBeInTheDocument();
  });
});

describe('AnalyticsStatsGrid - loading状态测试', () => {
  const mockData = {
    total_assets: 100,
    total_area: 5000,
    total_rentable_area: 4000,
    occupancy_rate: 85,
  };

  it('loading为true时Card应该有loading属性', async () => {
    const { AnalyticsStatsGrid } = await import('../AnalyticsStatsCard');
    render(<AnalyticsStatsGrid data={mockData} loading={true} />);

    const cards = screen.getAllByTestId('card');
    expect(cards[0]).toHaveAttribute('data-loading', 'true');
  });

  it('默认loading应该是false', async () => {
    const { AnalyticsStatsGrid } = await import('../AnalyticsStatsCard');
    render(<AnalyticsStatsGrid data={mockData} />);

    const cards = screen.getAllByTestId('card');
    expect(cards[0]).toHaveAttribute('data-loading', 'false');
  });
});

describe('AnalyticsStatsGrid - 财务指标测试', () => {
  it('应该显示年收入卡片（如果有数据）', async () => {
    const { AnalyticsStatsGrid } = await import('../AnalyticsStatsCard');
    const dataWithIncome = {
      total_assets: 100,
      total_area: 5000,
      total_rentable_area: 4000,
      occupancy_rate: 85,
      total_annual_income: 100000,
    };
    render(<AnalyticsStatsGrid data={dataWithIncome} />);

    expect(screen.getByText('年收入')).toBeInTheDocument();
  });

  it('应该显示净收益卡片（如果有数据）', async () => {
    const { AnalyticsStatsGrid } = await import('../AnalyticsStatsCard');
    const dataWithNetIncome = {
      total_assets: 100,
      total_area: 5000,
      total_rentable_area: 4000,
      occupancy_rate: 85,
      total_net_income: 50000,
    };
    render(<AnalyticsStatsGrid data={dataWithNetIncome} />);

    expect(screen.getByText('净收益')).toBeInTheDocument();
  });

  it('应该显示月租金卡片（如果有数据）', async () => {
    const { AnalyticsStatsGrid } = await import('../AnalyticsStatsCard');
    const dataWithRent = {
      total_assets: 100,
      total_area: 5000,
      total_rentable_area: 4000,
      occupancy_rate: 85,
      total_monthly_rent: 10000,
    };
    render(<AnalyticsStatsGrid data={dataWithRent} />);

    expect(screen.getByText('月租金')).toBeInTheDocument();
  });
});

describe('FinancialStatsGrid - 渲染测试', () => {
  const mockFinancialData = {
    total_annual_income: 100000,
    total_annual_expense: 50000,
    total_net_income: 50000,
    total_monthly_rent: 10000,
  };

  it('应该渲染Row布局', async () => {
    const { FinancialStatsGrid } = await import('../AnalyticsStatsCard');
    render(<FinancialStatsGrid data={mockFinancialData} />);

    expect(screen.getByTestId('row')).toBeInTheDocument();
  });

  it('应该显示年收入', async () => {
    const { FinancialStatsGrid } = await import('../AnalyticsStatsCard');
    render(<FinancialStatsGrid data={mockFinancialData} />);

    expect(screen.getByText('年收入')).toBeInTheDocument();
  });

  it('应该显示年支出', async () => {
    const { FinancialStatsGrid } = await import('../AnalyticsStatsCard');
    render(<FinancialStatsGrid data={mockFinancialData} />);

    expect(screen.getByText('年支出')).toBeInTheDocument();
  });

  it('应该显示净收益', async () => {
    const { FinancialStatsGrid } = await import('../AnalyticsStatsCard');
    render(<FinancialStatsGrid data={mockFinancialData} />);

    expect(screen.getByText('净收益')).toBeInTheDocument();
  });

  it('应该显示月租金', async () => {
    const { FinancialStatsGrid } = await import('../AnalyticsStatsCard');
    render(<FinancialStatsGrid data={mockFinancialData} />);

    expect(screen.getByText('月租金')).toBeInTheDocument();
  });
});

describe('FinancialStatsGrid - loading状态测试', () => {
  const mockFinancialData = {
    total_annual_income: 100000,
    total_annual_expense: 50000,
    total_net_income: 50000,
    total_monthly_rent: 10000,
  };

  it('loading为true时Card应该有loading属性', async () => {
    const { FinancialStatsGrid } = await import('../AnalyticsStatsCard');
    render(<FinancialStatsGrid data={mockFinancialData} loading={true} />);

    const cards = screen.getAllByTestId('card');
    expect(cards[0]).toHaveAttribute('data-loading', 'true');
  });
});

describe('AnalyticsStatsGrid - 边界情况测试', () => {
  it('应该处理occupancy_rate为0', async () => {
    const { AnalyticsStatsGrid } = await import('../AnalyticsStatsCard');
    const data = {
      total_assets: 0,
      total_area: 0,
      total_rentable_area: 0,
      occupancy_rate: 0,
    };
    render(<AnalyticsStatsGrid data={data} />);

    expect(screen.getByText('整体出租率')).toBeInTheDocument();
  });

  it('应该处理负净收益', async () => {
    const { AnalyticsStatsGrid } = await import('../AnalyticsStatsCard');
    const data = {
      total_assets: 100,
      total_area: 5000,
      total_rentable_area: 4000,
      occupancy_rate: 85,
      total_net_income: -10000,
    };
    render(<AnalyticsStatsGrid data={data} />);

    expect(screen.getByText('净收益')).toBeInTheDocument();
  });
});
