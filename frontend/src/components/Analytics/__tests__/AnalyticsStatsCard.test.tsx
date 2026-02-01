/**
 * AnalyticsStatsCard 组件测试（修复版）
 * 测试分析统计卡片组件
 *
 * 修复内容：
 * - 移除过度的 Ant Design 组件 mock
 * - 使用 renderWithProviders 提供必要的 Context Provider
 * - 保留必要的 mock（color utilities）
 * - 添加 beforeEach 清除 mock
 * - 保持完整的测试覆盖
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { renderWithProviders, screen } from '@/test/utils/test-helpers';
import React from 'react';

// Mock color utilities（这个 mock 是必要的，因为涉及样式计算）
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

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('应该渲染Row布局', async () => {
    const { AnalyticsStatsGrid } = await import('../AnalyticsStatsCard');
    const { container } = renderWithProviders(<AnalyticsStatsGrid data={mockData} />);

    const row = container.querySelector('.ant-row');
    expect(row).toBeInTheDocument();
  });

  it('应该渲染4个基础统计卡片', async () => {
    const { AnalyticsStatsGrid } = await import('../AnalyticsStatsCard');
    const { container } = renderWithProviders(<AnalyticsStatsGrid data={mockData} />);

    const cols = container.querySelectorAll('.ant-col');
    expect(cols.length).toBeGreaterThanOrEqual(4);
  });

  it('应该显示资产总数', async () => {
    const { AnalyticsStatsGrid } = await import('../AnalyticsStatsCard');
    renderWithProviders(<AnalyticsStatsGrid data={mockData} />);

    expect(screen.getByText('资产总数')).toBeInTheDocument();
  });

  it('应该显示总面积', async () => {
    const { AnalyticsStatsGrid } = await import('../AnalyticsStatsCard');
    renderWithProviders(<AnalyticsStatsGrid data={mockData} />);

    expect(screen.getByText('总面积')).toBeInTheDocument();
  });

  it('应该显示可租面积', async () => {
    const { AnalyticsStatsGrid } = await import('../AnalyticsStatsCard');
    renderWithProviders(<AnalyticsStatsGrid data={mockData} />);

    expect(screen.getByText('可租面积')).toBeInTheDocument();
  });

  it('应该显示整体出租率', async () => {
    const { AnalyticsStatsGrid } = await import('../AnalyticsStatsCard');
    renderWithProviders(<AnalyticsStatsGrid data={mockData} />);

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

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('loading为true时应该显示loading状态', async () => {
    const { AnalyticsStatsGrid } = await import('../AnalyticsStatsCard');
    const { container } = renderWithProviders(<AnalyticsStatsGrid data={mockData} loading={true} />);

    const skeletons = container.querySelectorAll('.ant-skeleton');
    expect(skeletons.length).toBeGreaterThan(0);
  });

  it('默认loading应该是false', async () => {
    const { AnalyticsStatsGrid } = await import('../AnalyticsStatsCard');
    renderWithProviders(<AnalyticsStatsGrid data={mockData} />);

    expect(screen.getByText('100')).toBeInTheDocument();
  });
});

describe('AnalyticsStatsGrid - 财务指标测试', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('应该显示年收入卡片（如果有数据）', async () => {
    const { AnalyticsStatsGrid } = await import('../AnalyticsStatsCard');
    const dataWithIncome = {
      total_assets: 100,
      total_area: 5000,
      total_rentable_area: 4000,
      occupancy_rate: 85,
      total_annual_income: 100000,
    };
    renderWithProviders(<AnalyticsStatsGrid data={dataWithIncome} />);

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
    renderWithProviders(<AnalyticsStatsGrid data={dataWithNetIncome} />);

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
    renderWithProviders(<AnalyticsStatsGrid data={dataWithRent} />);

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

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('应该渲染Row布局', async () => {
    const { FinancialStatsGrid } = await import('../AnalyticsStatsCard');
    const { container } = renderWithProviders(<FinancialStatsGrid data={mockFinancialData} />);

    const row = container.querySelector('.ant-row');
    expect(row).toBeInTheDocument();
  });

  it('应该显示年收入', async () => {
    const { FinancialStatsGrid } = await import('../AnalyticsStatsCard');
    renderWithProviders(<FinancialStatsGrid data={mockFinancialData} />);

    expect(screen.getByText('年收入')).toBeInTheDocument();
  });

  it('应该显示年支出', async () => {
    const { FinancialStatsGrid } = await import('../AnalyticsStatsCard');
    renderWithProviders(<FinancialStatsGrid data={mockFinancialData} />);

    expect(screen.getByText('年支出')).toBeInTheDocument();
  });

  it('应该显示净收益', async () => {
    const { FinancialStatsGrid } = await import('../AnalyticsStatsCard');
    renderWithProviders(<FinancialStatsGrid data={mockFinancialData} />);

    expect(screen.getByText('净收益')).toBeInTheDocument();
  });

  it('应该显示月租金', async () => {
    const { FinancialStatsGrid } = await import('../AnalyticsStatsCard');
    renderWithProviders(<FinancialStatsGrid data={mockFinancialData} />);

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

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('loading为true时应该显示loading状态', async () => {
    const { FinancialStatsGrid } = await import('../AnalyticsStatsCard');
    const { container } = renderWithProviders(<FinancialStatsGrid data={mockFinancialData} loading={true} />);

    const skeletons = container.querySelectorAll('.ant-skeleton');
    expect(skeletons.length).toBeGreaterThan(0);
  });
});

describe('AnalyticsStatsGrid - 边界情况测试', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('应该处理occupancy_rate为0', async () => {
    const { AnalyticsStatsGrid } = await import('../AnalyticsStatsCard');
    const data = {
      total_assets: 0,
      total_area: 0,
      total_rentable_area: 0,
      occupancy_rate: 0,
    };
    renderWithProviders(<AnalyticsStatsGrid data={data} />);

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
    renderWithProviders(<AnalyticsStatsGrid data={data} />);

    expect(screen.getByText('净收益')).toBeInTheDocument();
  });
});
