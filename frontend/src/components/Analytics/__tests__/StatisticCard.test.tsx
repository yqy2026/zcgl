/**
 * StatisticCard 组件测试
 * 测试统计卡片组件
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import React from 'react';

// Mock Ant Design components
vi.mock('antd', () => ({
  Card: ({
    children,
    loading,
  }: {
    children?: React.ReactNode;
    loading?: boolean;
  }) => (
    <div data-testid="card" data-loading={loading}>
      {children}
    </div>
  ),
  Statistic: ({
    title,
    value,
    precision,
    suffix,
    prefix,
    valueStyle,
  }: {
    title?: React.ReactNode;
    value?: number;
    precision?: number;
    suffix?: React.ReactNode;
    prefix?: React.ReactNode;
    valueStyle?: React.CSSProperties;
  }) => (
    <div data-testid="statistic" style={valueStyle}>
      <div data-testid="statistic-title">{title}</div>
      <div data-testid="statistic-value" data-precision={precision}>
        {prefix && <span data-testid="statistic-prefix">{prefix}</span>}
        <span>{value}</span>
        {suffix && <span data-testid="statistic-suffix">{suffix}</span>}
      </div>
    </div>
  ),
}));

describe('StatisticCard - 组件导入测试', () => {
  it('应该能够导入StatisticCard组件', async () => {
    const module = await import('../StatisticCard');
    expect(module).toBeDefined();
    expect(module.StatisticCard).toBeDefined();
  });

  it('应该能够导入FinancialStatisticCard组件', async () => {
    const module = await import('../StatisticCard');
    expect(module.FinancialStatisticCard).toBeDefined();
  });
});

describe('StatisticCard - 渲染测试', () => {
  it('应该渲染title', async () => {
    const { StatisticCard } = await import('../StatisticCard');
    render(<StatisticCard title="测试标题" value={100} />);

    expect(screen.getByTestId('statistic-title')).toHaveTextContent('测试标题');
  });

  it('应该渲染value', async () => {
    const { StatisticCard } = await import('../StatisticCard');
    render(<StatisticCard title="测试" value={12345} />);

    expect(screen.getByText('12345')).toBeInTheDocument();
  });

  it('应该渲染suffix', async () => {
    const { StatisticCard } = await import('../StatisticCard');
    render(<StatisticCard title="测试" value={100} suffix="%" />);

    expect(screen.getByTestId('statistic-suffix')).toHaveTextContent('%');
  });

  it('应该渲染prefix', async () => {
    const { StatisticCard } = await import('../StatisticCard');
    render(<StatisticCard title="测试" value={100} prefix="$" />);

    expect(screen.getByTestId('statistic-prefix')).toHaveTextContent('$');
  });
});

describe('StatisticCard - loading属性测试', () => {
  it('loading为true时Card应该有loading属性', async () => {
    const { StatisticCard } = await import('../StatisticCard');
    render(<StatisticCard title="测试" value={100} loading={true} />);

    expect(screen.getByTestId('card')).toHaveAttribute('data-loading', 'true');
  });

  it('默认loading应该是false', async () => {
    const { StatisticCard } = await import('../StatisticCard');
    render(<StatisticCard title="测试" value={100} />);

    expect(screen.getByTestId('card')).toHaveAttribute('data-loading', 'false');
  });
});

describe('StatisticCard - precision属性测试', () => {
  it('应该传递precision属性', async () => {
    const { StatisticCard } = await import('../StatisticCard');
    render(<StatisticCard title="测试" value={100} precision={2} />);

    expect(screen.getByTestId('statistic-value')).toHaveAttribute('data-precision', '2');
  });

  it('默认precision应该是0', async () => {
    const { StatisticCard } = await import('../StatisticCard');
    render(<StatisticCard title="测试" value={100} />);

    expect(screen.getByTestId('statistic-value')).toHaveAttribute('data-precision', '0');
  });
});

describe('FinancialStatisticCard - 渲染测试', () => {
  it('应该渲染title和value', async () => {
    const { FinancialStatisticCard } = await import('../StatisticCard');
    render(<FinancialStatisticCard title="财务标题" value={5000} />);

    expect(screen.getByTestId('statistic-title')).toHaveTextContent('财务标题');
    expect(screen.getByText('5000')).toBeInTheDocument();
  });

  it('正值且isPositive为true时应该使用绿色', async () => {
    const { FinancialStatisticCard } = await import('../StatisticCard');
    render(<FinancialStatisticCard title="测试" value={100} isPositive={true} />);

    const statistic = screen.getByTestId('statistic');
    expect(statistic).toHaveStyle({ color: '#3f8600' });
  });

  it('正值且isPositive为false时应该使用红色', async () => {
    const { FinancialStatisticCard } = await import('../StatisticCard');
    render(<FinancialStatisticCard title="测试" value={100} isPositive={false} />);

    const statistic = screen.getByTestId('statistic');
    expect(statistic).toHaveStyle({ color: '#cf1322' });
  });

  it('负值时应该使用红色', async () => {
    const { FinancialStatisticCard } = await import('../StatisticCard');
    render(<FinancialStatisticCard title="测试" value={-100} isPositive={true} />);

    const statistic = screen.getByTestId('statistic');
    expect(statistic).toHaveStyle({ color: '#cf1322' });
  });

  it('默认isPositive应该是true', async () => {
    const { FinancialStatisticCard } = await import('../StatisticCard');
    render(<FinancialStatisticCard title="测试" value={100} />);

    const statistic = screen.getByTestId('statistic');
    expect(statistic).toHaveStyle({ color: '#3f8600' });
  });
});

describe('StatisticCard - 边界情况测试', () => {
  it('应该处理value为0', async () => {
    const { StatisticCard } = await import('../StatisticCard');
    render(<StatisticCard title="测试" value={0} />);

    expect(screen.getByText('0')).toBeInTheDocument();
  });

  it('应该处理负数value', async () => {
    const { StatisticCard } = await import('../StatisticCard');
    render(<StatisticCard title="测试" value={-100} />);

    expect(screen.getByText('-100')).toBeInTheDocument();
  });
});

describe('FinancialStatisticCard - 边界情况测试', () => {
  it('应该处理value为0', async () => {
    const { FinancialStatisticCard } = await import('../StatisticCard');
    render(<FinancialStatisticCard title="测试" value={0} />);

    expect(screen.getByText('0')).toBeInTheDocument();
  });

  it('应该支持suffix属性', async () => {
    const { FinancialStatisticCard } = await import('../StatisticCard');
    render(<FinancialStatisticCard title="测试" value={100} suffix="元" />);

    expect(screen.getByTestId('statistic-suffix')).toHaveTextContent('元');
  });

  it('应该支持loading属性', async () => {
    const { FinancialStatisticCard } = await import('../StatisticCard');
    render(<FinancialStatisticCard title="测试" value={100} loading={true} />);

    expect(screen.getByTestId('card')).toHaveAttribute('data-loading', 'true');
  });
});
