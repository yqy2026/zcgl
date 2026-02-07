/**
 * DataTrendCard 组件测试
 * 测试数据趋势卡片组件
 *
 * 修复说明：
 * - 移除 antd Card, Statistic 组件 mock
 * - 移除 @ant-design/icons mock
 * - 保留 CSS modules mock（非 antd 相关）
 * - 使用 className 和文本内容进行断言
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import React from 'react';
import { screen } from '@/test/utils/test-helpers';
import DataTrendCard from '../DataTrendCard';

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
    const { container } = renderWithProviders(
      <DataTrendCard title="总面积" value={1234.5} precision={1} suffix="㎡" />
    );

    expect(screen.getByText('总面积')).toBeInTheDocument();
    const stat = container.querySelector('.ant-statistic');
    expect(stat).toBeInTheDocument();
  });

  it('正向趋势应显示正号', () => {
    renderWithProviders(
      <DataTrendCard
        title="出租率"
        value={90}
        trend={{ value: 3.5, period: '较上月', isPositive: true }}
      />
    );

    expect(screen.getByText('+3.5%')).toBeInTheDocument();
    expect(screen.getByText('较上月')).toBeInTheDocument();
  });

  it('负向趋势应显示负号', () => {
    renderWithProviders(
      <DataTrendCard
        title="出租率"
        value={80}
        trend={{ value: -2.4, period: '较上月', isPositive: false }}
      />
    );

    expect(screen.getByText('-2.4%')).toBeInTheDocument();
  });

  it('趋势为0时应显示0%', () => {
    renderWithProviders(
      <DataTrendCard
        title="出租率"
        value={80}
        trend={{ value: 0, period: '较上月', isPositive: false }}
      />
    );

    expect(screen.getByText('0.0%')).toBeInTheDocument();
  });

  it('应该根据loading状态显示loading', () => {
    const { container } = renderWithProviders(
      <DataTrendCard title="总资产" value={100} color="success" size="large" loading={true} />
    );

    const card = container.querySelector('.ant-card');
    expect(card).toBeInTheDocument();
    expect(card?.classList.contains('ant-card-loading')).toBe(true);
  });
});
