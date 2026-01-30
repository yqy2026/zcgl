/**
 * AnalyticsCard 组件测试
 * 测试分析卡片组件
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import React from 'react';

// Mock Ant Design components
vi.mock('antd', () => ({
  Card: ({
    children,
    title,
    size,
    className,
    loading,
  }: {
    children?: React.ReactNode;
    title?: React.ReactNode;
    size?: string;
    className?: string;
    loading?: boolean;
  }) => (
    <div
      data-testid="card"
      data-size={size}
      data-loading={loading}
      className={className}
    >
      {title && <div data-testid="card-title">{title}</div>}
      {children}
    </div>
  ),
  Empty: ({ description }: { description?: React.ReactNode }) => (
    <div data-testid="empty">{description}</div>
  ),
}));

describe('AnalyticsCard - 组件导入测试', () => {
  it('应该能够导入AnalyticsCard组件', async () => {
    const module = await import('../AnalyticsCard');
    expect(module).toBeDefined();
    expect(module.AnalyticsCard).toBeDefined();
  });

  it('应该能够导入ChartCard组件', async () => {
    const module = await import('../AnalyticsCard');
    expect(module.ChartCard).toBeDefined();
  });
});

describe('AnalyticsCard - 渲染测试', () => {
  it('应该渲染title', async () => {
    const { AnalyticsCard } = await import('../AnalyticsCard');
    render(
      <AnalyticsCard title="测试标题">
        <div>内容</div>
      </AnalyticsCard>
    );

    expect(screen.getByTestId('card-title')).toHaveTextContent('测试标题');
  });

  it('应该渲染children内容', async () => {
    const { AnalyticsCard } = await import('../AnalyticsCard');
    render(
      <AnalyticsCard title="测试">
        <div data-testid="child-content">子内容</div>
      </AnalyticsCard>
    );

    expect(screen.getByTestId('child-content')).toBeInTheDocument();
  });

  it('hasData为false时应该显示Empty', async () => {
    const { AnalyticsCard } = await import('../AnalyticsCard');
    render(
      <AnalyticsCard title="测试" hasData={false}>
        <div>内容</div>
      </AnalyticsCard>
    );

    expect(screen.getByTestId('empty')).toBeInTheDocument();
    expect(screen.getByText('暂无数据')).toBeInTheDocument();
  });

  it('hasData为true时应该渲染children', async () => {
    const { AnalyticsCard } = await import('../AnalyticsCard');
    render(
      <AnalyticsCard title="测试" hasData={true}>
        <div data-testid="content">有数据的内容</div>
      </AnalyticsCard>
    );

    expect(screen.getByTestId('content')).toBeInTheDocument();
    expect(screen.queryByTestId('empty')).not.toBeInTheDocument();
  });

  it('默认hasData应该是true', async () => {
    const { AnalyticsCard } = await import('../AnalyticsCard');
    render(
      <AnalyticsCard title="测试">
        <div data-testid="content">内容</div>
      </AnalyticsCard>
    );

    expect(screen.getByTestId('content')).toBeInTheDocument();
  });
});

describe('AnalyticsCard - loading属性测试', () => {
  it('loading为true时Card应该有loading属性', async () => {
    const { AnalyticsCard } = await import('../AnalyticsCard');
    render(
      <AnalyticsCard title="测试" loading={true}>
        <div>内容</div>
      </AnalyticsCard>
    );

    expect(screen.getByTestId('card')).toHaveAttribute('data-loading', 'true');
  });

  it('默认loading应该是false', async () => {
    const { AnalyticsCard } = await import('../AnalyticsCard');
    render(
      <AnalyticsCard title="测试">
        <div>内容</div>
      </AnalyticsCard>
    );

    expect(screen.getByTestId('card')).toHaveAttribute('data-loading', 'false');
  });
});

describe('AnalyticsCard - size属性测试', () => {
  it('默认size应该是small', async () => {
    const { AnalyticsCard } = await import('../AnalyticsCard');
    render(
      <AnalyticsCard title="测试">
        <div>内容</div>
      </AnalyticsCard>
    );

    expect(screen.getByTestId('card')).toHaveAttribute('data-size', 'small');
  });

  it('应该支持自定义size', async () => {
    const { AnalyticsCard } = await import('../AnalyticsCard');
    render(
      <AnalyticsCard title="测试" size="default">
        <div>内容</div>
      </AnalyticsCard>
    );

    expect(screen.getByTestId('card')).toHaveAttribute('data-size', 'default');
  });
});

describe('AnalyticsCard - className属性测试', () => {
  it('应该支持自定义className', async () => {
    const { AnalyticsCard } = await import('../AnalyticsCard');
    render(
      <AnalyticsCard title="测试" className="custom-class">
        <div>内容</div>
      </AnalyticsCard>
    );

    expect(screen.getByTestId('card')).toHaveClass('custom-class');
  });
});

describe('ChartCard - 测试', () => {
  it('ChartCard应该与AnalyticsCard功能相同', async () => {
    const { ChartCard } = await import('../AnalyticsCard');
    render(
      <ChartCard title="图表标题">
        <div data-testid="chart-content">图表内容</div>
      </ChartCard>
    );

    expect(screen.getByTestId('card-title')).toHaveTextContent('图表标题');
    expect(screen.getByTestId('chart-content')).toBeInTheDocument();
  });
});
