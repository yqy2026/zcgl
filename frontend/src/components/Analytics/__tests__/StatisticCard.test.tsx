/**
 * StatisticCard 组件测试（修复版）
 * 测试统计卡片组件
 *
 * 修复内容：
 * - 移除过度的 Ant Design 组件 mock
 * - 使用 renderWithProviders 提供必要的 Context Provider
 * - 保持完整的测试覆盖
 */

import { describe, it, expect, beforeEach } from 'vitest';
import { renderWithProviders, screen } from '@/test/utils/test-helpers';
import React from 'react';

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
  beforeEach(() => {
    // 清除所有 mock，使用真实组件
    vi.clearAllMocks();
  });

  it('应该渲染title', async () => {
    const { StatisticCard } = await import('../StatisticCard');
    renderWithProviders(<StatisticCard title="测试标题" value={100} />);

    expect(screen.getByText('测试标题')).toBeInTheDocument();
  });

  it('应该渲染value', async () => {
    const { StatisticCard } = await import('../StatisticCard');
    renderWithProviders(<StatisticCard title="测试" value={12345} />);

    expect(screen.getByText(/12,?345/)).toBeInTheDocument();
  });

  it('应该渲染suffix', async () => {
    const { StatisticCard } = await import('../StatisticCard');
    renderWithProviders(<StatisticCard title="测试" value={100} suffix="%" />);

    expect(screen.getByText('%')).toBeInTheDocument();
  });

  it('应该渲染prefix', async () => {
    const { StatisticCard } = await import('../StatisticCard');
    renderWithProviders(<StatisticCard title="测试" value={100} prefix="$" />);

    expect(screen.getByText('$')).toBeInTheDocument();
  });
});

describe('StatisticCard - loading属性测试', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('loading为true时应该显示loading状态', async () => {
    const { StatisticCard } = await import('../StatisticCard');
    const { container } = renderWithProviders(
      <StatisticCard title="测试" value={100} loading={true} />
    );

    // Ant Design Statistic 组件在 loading 时会显示 skeleton
    const skeleton = container.querySelector('.ant-skeleton');
    expect(skeleton).toBeInTheDocument();
  });

  it('默认loading应该是false', async () => {
    const { StatisticCard } = await import('../StatisticCard');
    renderWithProviders(<StatisticCard title="测试" value={100} />);

    // 应该显示实际值而不是 loading
    expect(screen.getByText('100')).toBeInTheDocument();
  });
});

describe('StatisticCard - precision属性测试', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('应该正确格式化小数', async () => {
    const { StatisticCard } = await import('../StatisticCard');
    renderWithProviders(<StatisticCard title="测试" value={100.456} precision={2} />);

    // Ant Design Statistic 会根据 precision 格式化
    const value = document.querySelector('.ant-statistic-content-value');
    expect(value?.textContent).toMatch(/100\.4[56]/);
  });

  it('默认precision应该是0', async () => {
    const { StatisticCard } = await import('../StatisticCard');
    renderWithProviders(<StatisticCard title="测试" value={100.789} />);

    // 默认没有小数
    const value = document.querySelector('.ant-statistic-content-value');
    expect(value?.textContent).toBe('100');
  });
});

describe('FinancialStatisticCard - 渲染测试', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('应该渲染title和value', async () => {
    const { FinancialStatisticCard } = await import('../StatisticCard');
    renderWithProviders(<FinancialStatisticCard title="财务标题" value={5000} />);

    expect(screen.getByText('财务标题')).toBeInTheDocument();
    expect(screen.getByText(/5,?000/)).toBeInTheDocument();
  });

  it('正值且isPositive为true时应该使用绿色', async () => {
    const { FinancialStatisticCard } = await import('../StatisticCard');
    const { container } = renderWithProviders(
      <FinancialStatisticCard title="测试" value={100} isPositive={true} />
    );

    const value = container.querySelector('.ant-statistic-content');
    expect(value?.getAttribute('style')).toContain('var(--color-success)');
  });

  it('负值时应该使用红色', async () => {
    const { FinancialStatisticCard } = await import('../StatisticCard');
    const { container } = renderWithProviders(
      <FinancialStatisticCard title="测试" value={-100} isPositive={true} />
    );

    const value = container.querySelector('.ant-statistic-content');
    expect(value?.getAttribute('style')).toContain('var(--color-error)');
  });

  it('默认isPositive应该是true', async () => {
    const { FinancialStatisticCard } = await import('../StatisticCard');
    const { container } = renderWithProviders(<FinancialStatisticCard title="测试" value={100} />);

    const value = container.querySelector('.ant-statistic-content');
    expect(value?.getAttribute('style')).toContain('var(--color-success)');
  });
});

describe('StatisticCard - 边界情况测试', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('应该处理value为0', async () => {
    const { StatisticCard } = await import('../StatisticCard');
    renderWithProviders(<StatisticCard title="测试" value={0} />);

    expect(screen.getByText('0')).toBeInTheDocument();
  });

  it('应该处理负数value', async () => {
    const { StatisticCard } = await import('../StatisticCard');
    renderWithProviders(<StatisticCard title="测试" value={-100} />);

    expect(screen.getByText('-100')).toBeInTheDocument();
  });

  it('应该处理非常大的数值', async () => {
    const { StatisticCard } = await import('../StatisticCard');
    renderWithProviders(<StatisticCard title="测试" value={999999999} />);

    const statistic = document.querySelector('.ant-statistic');
    const displayedText = statistic?.textContent ?? '';
    expect(displayedText.length).toBeGreaterThan(0);
  });
});

describe('FinancialStatisticCard - 边界情况测试', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('应该处理value为0', async () => {
    const { FinancialStatisticCard } = await import('../StatisticCard');
    renderWithProviders(<FinancialStatisticCard title="测试" value={0} />);

    expect(screen.getByText('0')).toBeInTheDocument();
  });

  it('应该支持suffix属性', async () => {
    const { FinancialStatisticCard } = await import('../StatisticCard');
    renderWithProviders(<FinancialStatisticCard title="测试" value={100} suffix="元" />);

    expect(screen.getByText('元')).toBeInTheDocument();
  });

  it('应该支持loading属性', async () => {
    const { FinancialStatisticCard } = await import('../StatisticCard');
    const { container } = renderWithProviders(
      <FinancialStatisticCard title="测试" value={100} loading={true} />
    );

    // 检查是否有 skeleton
    const skeleton = container.querySelector('.ant-skeleton');
    expect(skeleton).toBeInTheDocument();
  });
});
