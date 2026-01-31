/**
 * DataTrendCard 组件测试
 * 测试数据趋势卡片组件
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import React from 'react';
import { render, screen } from '@testing-library/react';
import DataTrendCard from '../DataTrendCard';

interface CardMockProps {
  children?: React.ReactNode;
  className?: string;
  loading?: boolean;
  variant?: string;
}

interface StatisticMockProps {
  value?: number;
  precision?: number;
  suffix?: string;
  valueStyle?: React.CSSProperties;
}

// Mock Ant Design components
vi.mock('antd', () => ({
  Card: ({ children, className, loading, variant }: CardMockProps) => (
    <div
      data-testid="card"
      data-class-name={className}
      data-loading={loading}
      data-variant={variant}
    >
      {children}
    </div>
  ),
  Statistic: ({ value, precision, suffix, valueStyle }: StatisticMockProps) => (
    <div
      data-testid="statistic"
      data-value={value}
      data-precision={precision}
      data-suffix={suffix}
      data-value-style={JSON.stringify(valueStyle)}
    />
  ),
}));

// Mock icons
vi.mock('@ant-design/icons', () => ({
  ArrowUpOutlined: () => <div data-testid="icon-trend-up" />,
  ArrowDownOutlined: () => <div data-testid="icon-trend-down" />,
  MinusOutlined: () => <div data-testid="icon-trend-neutral" />,
}));

// Mock CSS modules
vi.mock('../DataTrendCard.module.css', () => ({
  default: {
    trendCard: 'trend-card',
    trendUp: 'trend-up',
    trendDown: 'trend-down',
    trendNeutral: 'trend-neutral',
    cardHeader: 'card-header',
    cardTitle: 'card-title',
    cardIcon: 'card-icon',
    cardContent: 'card-content',
    trendIcon: 'trend-icon',
    trendText: 'trend-text',
    trendPeriod: 'trend-period',
    primary: 'primary',
    success: 'success',
    warning: 'warning',
    error: 'error',
    default: 'default',
    small: 'small',
    large: 'large',
  },
}));

describe('DataTrendCard - 组件导入测试', () => {
  it('应该能够导入DataTrendCard组件', () => {
    expect(DataTrendCard).toBeDefined();
  });
});

describe('DataTrendCard - 渲染与趋势测试', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('应该渲染标题与统计值', () => {
    render(
      <DataTrendCard title="总面积" value={1234.5} precision={1} suffix="㎡" />
    );

    expect(screen.getByText('总面积')).toBeInTheDocument();
    const stat = screen.getByTestId('statistic');
    expect(stat).toHaveAttribute('data-value', '1234.5');
    expect(stat).toHaveAttribute('data-precision', '1');
    expect(stat).toHaveAttribute('data-suffix', '㎡');
  });

  it('正向趋势应显示上升图标与正号', () => {
    render(
      <DataTrendCard
        title="出租率"
        value={90}
        trend={{ value: 3.5, period: '较上月', isPositive: true }}
      />
    );

    expect(screen.getByTestId('icon-trend-up')).toBeInTheDocument();
    expect(screen.getByText('+3.5%')).toBeInTheDocument();
    expect(screen.getByText('较上月')).toBeInTheDocument();
  });

  it('负向趋势应显示下降图标与负号', () => {
    render(
      <DataTrendCard
        title="出租率"
        value={80}
        trend={{ value: -2.4, period: '较上月', isPositive: false }}
      />
    );

    expect(screen.getByTestId('icon-trend-down')).toBeInTheDocument();
    expect(screen.getByText('-2.4%')).toBeInTheDocument();
  });

  it('趋势为0时应显示中性图标', () => {
    render(
      <DataTrendCard
        title="出租率"
        value={80}
        trend={{ value: 0, period: '较上月', isPositive: false }}
      />
    );

    expect(screen.getByTestId('icon-trend-neutral')).toBeInTheDocument();
    expect(screen.getByText('0.0%')).toBeInTheDocument();
  });

  it('应根据颜色和尺寸应用类名', () => {
    render(
      <DataTrendCard
        title="总资产"
        value={100}
        color="success"
        size="large"
        loading={true}
      />
    );

    const card = screen.getByTestId('card');
    const className = card.getAttribute('data-class-name') ?? '';
    expect(className).toContain('trend-card');
    expect(className).toContain('success');
    expect(className).toContain('large');
    expect(card).toHaveAttribute('data-loading', 'true');
    expect(card).toHaveAttribute('data-variant', 'borderless');
  });
});
