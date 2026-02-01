/**
 * AnalyticsCard 组件测试（修复版）
 * 测试分析卡片组件
 *
 * 修复内容：
 * - 移除过度的 Ant Design 组件 mock
 * - 使用 renderWithProviders 提供必要的 Context Provider
 * - 添加 beforeEach 清除 mock
 * - 保持完整的测试覆盖
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { renderWithProviders, screen } from '@/test/utils/test-helpers';
import React from 'react';

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
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('应该渲染title', async () => {
    const { AnalyticsCard } = await import('../AnalyticsCard');
    renderWithProviders(
      <AnalyticsCard title="测试标题">
        <div>内容</div>
      </AnalyticsCard>
    );

    expect(screen.getByText('测试标题')).toBeInTheDocument();
  });

  it('应该渲染children内容', async () => {
    const { AnalyticsCard } = await import('../AnalyticsCard');
    renderWithProviders(
      <AnalyticsCard title="测试">
        <div data-testid="child-content">子内容</div>
      </AnalyticsCard>
    );

    expect(screen.getByTestId('child-content')).toBeInTheDocument();
  });

  it('hasData为false时应该显示Empty', async () => {
    const { AnalyticsCard } = await import('../AnalyticsCard');
    renderWithProviders(
      <AnalyticsCard title="测试" hasData={false}>
        <div>内容</div>
      </AnalyticsCard>
    );

    const emptyText = screen.getAllByText('暂无数据');
    expect(emptyText.length).toBeGreaterThan(0);
  });

  it('hasData为true时应该渲染children', async () => {
    const { AnalyticsCard } = await import('../AnalyticsCard');
    renderWithProviders(
      <AnalyticsCard title="测试" hasData={true}>
        <div data-testid="content">有数据的内容</div>
      </AnalyticsCard>
    );

    expect(screen.getByTestId('content')).toBeInTheDocument();
  });

  it('默认hasData应该是true', async () => {
    const { AnalyticsCard } = await import('../AnalyticsCard');
    renderWithProviders(
      <AnalyticsCard title="测试">
        <div data-testid="content">内容</div>
      </AnalyticsCard>
    );

    expect(screen.getByTestId('content')).toBeInTheDocument();
  });
});

describe('AnalyticsCard - loading属性测试', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('loading为true时应该显示loading状态', async () => {
    const { AnalyticsCard } = await import('../AnalyticsCard');
    const { container } = renderWithProviders(
      <AnalyticsCard title="测试" loading={true}>
        <div>内容</div>
      </AnalyticsCard>
    );

    const skeleton = container.querySelector('.ant-skeleton');
    expect(skeleton).toBeInTheDocument();
  });

  it('默认loading应该是false', async () => {
    const { AnalyticsCard } = await import('../AnalyticsCard');
    renderWithProviders(
      <AnalyticsCard title="测试">
        <div>内容</div>
      </AnalyticsCard>
    );

    expect(screen.getByText('内容')).toBeInTheDocument();
  });
});

describe('AnalyticsCard - size属性测试', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('默认size应该是small', async () => {
    const { AnalyticsCard } = await import('../AnalyticsCard');
    const { container } = renderWithProviders(
      <AnalyticsCard title="测试">
        <div>内容</div>
      </AnalyticsCard>
    );

    const card = container.querySelector('.ant-card');
    expect(card?.className).toContain('ant-card-small');
  });

  it('应该支持自定义size', async () => {
    const { AnalyticsCard } = await import('../AnalyticsCard');
    const { container } = renderWithProviders(
      <AnalyticsCard title="测试" size="default">
        <div>内容</div>
      </AnalyticsCard>
    );

    const card = container.querySelector('.ant-card');
    expect(card?.className).not.toContain('ant-card-small');
  });
});

describe('AnalyticsCard - className属性测试', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('应该支持自定义className', async () => {
    const { AnalyticsCard } = await import('../AnalyticsCard');
    const { container } = renderWithProviders(
      <AnalyticsCard title="测试" className="custom-class">
        <div>内容</div>
      </AnalyticsCard>
    );

    const card = container.querySelector('.custom-class');
    expect(card).toBeInTheDocument();
  });
});

describe('ChartCard - 测试', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('ChartCard应该与AnalyticsCard功能相同', async () => {
    const { ChartCard } = await import('../AnalyticsCard');
    renderWithProviders(
      <ChartCard title="图表标题">
        <div data-testid="chart-content">图表内容</div>
      </ChartCard>
    );

    expect(screen.getByText('图表标题')).toBeInTheDocument();
    expect(screen.getByTestId('chart-content')).toBeInTheDocument();
  });
});
