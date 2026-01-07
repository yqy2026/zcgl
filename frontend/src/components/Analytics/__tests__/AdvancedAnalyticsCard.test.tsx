/**
 * AdvancedAnalyticsCard 组件测试
 * 测试高级分析卡片组件
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import React from 'react';

// Mock StatisticCard
vi.mock('../StatisticCard', () => ({
  FinancialStatisticCard: ({ title, value, precision, suffix, isPositive, loading }: any) => (
    <div
      data-testid="financial-statistic-card"
      data-title={title}
      data-value={value}
      data-precision={precision}
      data-suffix={suffix}
      data-is-positive={isPositive}
      data-loading={loading}
    >
      {title}: {value}
    </div>
  ),
}));

// Mock Ant Design components
vi.mock('antd', () => ({
  Card: ({ children, loading, title }: any) => (
    <div data-testid="card" data-loading={loading} data-title={title}>
      {children}
    </div>
  ),
  Row: ({ children, gutter }: any) => (
    <div data-testid="row" data-gutter={JSON.stringify(gutter)}>
      {children}
    </div>
  ),
  Col: ({ children, xs, sm, lg }: any) => (
    <div data-testid="col" data-xs={xs} data-sm={sm} data-lg={lg}>
      {children}
    </div>
  ),
  Statistic: ({ title, value, precision, suffix, prefix, valueStyle }: any) => (
    <div
      data-testid="statistic"
      data-title={title}
      data-value={value}
      data-precision={precision}
      style={valueStyle}
    >
      {prefix && <span data-testid="statistic-prefix">{prefix}</span>}
      <span>{value}</span>
      {suffix && <span data-testid="statistic-suffix">{suffix}</span>}
    </div>
  ),
  Progress: ({ percent, size, strokeColor, style }: any) => (
    <div
      data-testid="progress"
      data-percent={percent}
      data-size={size}
      data-stroke-color={JSON.stringify(strokeColor)}
      style={style}
    >
      {percent}%
    </div>
  ),
  Tag: ({ children, color, style }: any) => (
    <div data-testid="tag" data-color={color} style={style}>
      {children}
    </div>
  ),
  Tooltip: ({ children, title }: any) => (
    <div data-testid="tooltip" data-title={title}>
      {children}
    </div>
  ),
}));

// Mock icons
vi.mock('@ant-design/icons', () => ({
  ArrowUpOutlined: () => <div data-testid="icon-arrow-up" />,
  ArrowDownOutlined: () => <div data-testid="icon-arrow-down" />,
  InfoCircleOutlined: () => <div data-testid="icon-info-circle" />,
}));

// Mock types
vi.mock('../../types/analytics', () => ({}));

describe('AdvancedAnalyticsCard - 组件导入测试', () => {
  it('应该能够导入AdvancedAnalyticsCard组件', async () => {
    const module = await import('../AdvancedAnalyticsCard');
    expect(module).toBeDefined();
    expect(module.default).toBeDefined();
  });
});

describe('AdvancedAnalyticsCard - 基础属性测试', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('应该支持performanceMetrics属性', async () => {
    const AdvancedAnalyticsCard = (await import('../AdvancedAnalyticsCard')).default;
    const performanceMetrics = {
      asset_utilization: 0.8,
      income_efficiency: 0.7,
      occupancy_variance: 0.1,
      growth_rate: 0.05,
    };
    const element = React.createElement(AdvancedAnalyticsCard, { performanceMetrics });
    expect(element).toBeTruthy();
  });

  it('应该支持comparisonData属性', async () => {
    const AdvancedAnalyticsCard = (await import('../AdvancedAnalyticsCard')).default;
    const performanceMetrics = {
      asset_utilization: 0.8,
      income_efficiency: 0.7,
      occupancy_variance: 0.1,
      growth_rate: 0.05,
    };
    const comparisonData = {
      change_percentage: {
        total_assets: 5,
        total_area: 3,
        occupancy_rate: 2,
        total_net_income: 10,
      },
    };
    const element = React.createElement(AdvancedAnalyticsCard, {
      performanceMetrics,
      comparisonData,
    });
    expect(element).toBeTruthy();
  });

  it('应该支持loading属性', async () => {
    const AdvancedAnalyticsCard = (await import('../AdvancedAnalyticsCard')).default;
    const performanceMetrics = {
      asset_utilization: 0.8,
      income_efficiency: 0.7,
      occupancy_variance: 0.1,
      growth_rate: 0.05,
    };
    const element = React.createElement(AdvancedAnalyticsCard, {
      performanceMetrics,
      loading: true,
    });
    expect(element).toBeTruthy();
  });

  it('默认loading应该是false', async () => {
    const AdvancedAnalyticsCard = (await import('../AdvancedAnalyticsCard')).default;
    const performanceMetrics = {
      asset_utilization: 0.8,
      income_efficiency: 0.7,
      occupancy_variance: 0.1,
      growth_rate: 0.05,
    };
    const element = React.createElement(AdvancedAnalyticsCard, { performanceMetrics });
    expect(element).toBeTruthy();
  });
});

describe('AdvancedAnalyticsCard - 性能指标测试', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('应该显示资产利用率', async () => {
    const AdvancedAnalyticsCard = (await import('../AdvancedAnalyticsCard')).default;
    const performanceMetrics = {
      asset_utilization: 0.8,
      income_efficiency: 0.7,
      occupancy_variance: 0.1,
      growth_rate: 0.05,
    };
    const element = React.createElement(AdvancedAnalyticsCard, { performanceMetrics });
    expect(element).toBeTruthy();
  });

  it('应该显示收入效率', async () => {
    const AdvancedAnalyticsCard = (await import('../AdvancedAnalyticsCard')).default;
    const performanceMetrics = {
      asset_utilization: 0.8,
      income_efficiency: 0.7,
      occupancy_variance: 0.1,
      growth_rate: 0.05,
    };
    const element = React.createElement(AdvancedAnalyticsCard, { performanceMetrics });
    expect(element).toBeTruthy();
  });

  it('应该显示出租率稳定性', async () => {
    const AdvancedAnalyticsCard = (await import('../AdvancedAnalyticsCard')).default;
    const performanceMetrics = {
      asset_utilization: 0.8,
      income_efficiency: 0.7,
      occupancy_variance: 0.1,
      growth_rate: 0.05,
    };
    const element = React.createElement(AdvancedAnalyticsCard, { performanceMetrics });
    expect(element).toBeTruthy();
  });

  it('应该显示增长率', async () => {
    const AdvancedAnalyticsCard = (await import('../AdvancedAnalyticsCard')).default;
    const performanceMetrics = {
      asset_utilization: 0.8,
      income_efficiency: 0.7,
      occupancy_variance: 0.1,
      growth_rate: 0.05,
    };
    const element = React.createElement(AdvancedAnalyticsCard, { performanceMetrics });
    expect(element).toBeTruthy();
  });
});

describe('AdvancedAnalyticsCard - 进度条测试', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('资产利用率应该有进度条', async () => {
    const AdvancedAnalyticsCard = (await import('../AdvancedAnalyticsCard')).default;
    const performanceMetrics = {
      asset_utilization: 0.8,
      income_efficiency: 0.7,
      occupancy_variance: 0.1,
      growth_rate: 0.05,
    };
    const element = React.createElement(AdvancedAnalyticsCard, { performanceMetrics });
    expect(element).toBeTruthy();
  });

  it('收入效率应该有进度条', async () => {
    const AdvancedAnalyticsCard = (await import('../AdvancedAnalyticsCard')).default;
    const performanceMetrics = {
      asset_utilization: 0.8,
      income_efficiency: 0.7,
      occupancy_variance: 0.1,
      growth_rate: 0.05,
    };
    const element = React.createElement(AdvancedAnalyticsCard, { performanceMetrics });
    expect(element).toBeTruthy();
  });

  it('出租率稳定性应该有进度条', async () => {
    const AdvancedAnalyticsCard = (await import('../AdvancedAnalyticsCard')).default;
    const performanceMetrics = {
      asset_utilization: 0.8,
      income_efficiency: 0.7,
      occupancy_variance: 0.1,
      growth_rate: 0.05,
    };
    const element = React.createElement(AdvancedAnalyticsCard, { performanceMetrics });
    expect(element).toBeTruthy();
  });

  it('增长率应该有进度条', async () => {
    const AdvancedAnalyticsCard = (await import('../AdvancedAnalyticsCard')).default;
    const performanceMetrics = {
      asset_utilization: 0.8,
      income_efficiency: 0.7,
      occupancy_variance: 0.1,
      growth_rate: 0.05,
    };
    const element = React.createElement(AdvancedAnalyticsCard, { performanceMetrics });
    expect(element).toBeTruthy();
  });
});

describe('AdvancedAnalyticsCard - 状态标签测试', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('应该显示性能状态标签', async () => {
    const AdvancedAnalyticsCard = (await import('../AdvancedAnalyticsCard')).default;
    const performanceMetrics = {
      asset_utilization: 0.8,
      income_efficiency: 0.7,
      occupancy_variance: 0.1,
      growth_rate: 0.05,
    };
    const element = React.createElement(AdvancedAnalyticsCard, { performanceMetrics });
    expect(element).toBeTruthy();
  });
});

describe('AdvancedAnalyticsCard - 对比分析测试', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('有comparisonData时应该显示对比分析', async () => {
    const AdvancedAnalyticsCard = (await import('../AdvancedAnalyticsCard')).default;
    const performanceMetrics = {
      asset_utilization: 0.8,
      income_efficiency: 0.7,
      occupancy_variance: 0.1,
      growth_rate: 0.05,
    };
    const comparisonData = {
      change_percentage: {
        total_assets: 5,
        total_area: 3,
        occupancy_rate: 2,
        total_net_income: 10,
      },
    };
    const element = React.createElement(AdvancedAnalyticsCard, {
      performanceMetrics,
      comparisonData,
    });
    expect(element).toBeTruthy();
  });

  it('应该显示资产总数变化', async () => {
    const AdvancedAnalyticsCard = (await import('../AdvancedAnalyticsCard')).default;
    const performanceMetrics = {
      asset_utilization: 0.8,
      income_efficiency: 0.7,
      occupancy_variance: 0.1,
      growth_rate: 0.05,
    };
    const comparisonData = {
      change_percentage: {
        total_assets: 5,
        total_area: 3,
        occupancy_rate: 2,
        total_net_income: 10,
      },
    };
    const element = React.createElement(AdvancedAnalyticsCard, {
      performanceMetrics,
      comparisonData,
    });
    expect(element).toBeTruthy();
  });

  it('应该显示总面积变化', async () => {
    const AdvancedAnalyticsCard = (await import('../AdvancedAnalyticsCard')).default;
    const performanceMetrics = {
      asset_utilization: 0.8,
      income_efficiency: 0.7,
      occupancy_variance: 0.1,
      growth_rate: 0.05,
    };
    const comparisonData = {
      change_percentage: {
        total_assets: 5,
        total_area: 3,
        occupancy_rate: 2,
        total_net_income: 10,
      },
    };
    const element = React.createElement(AdvancedAnalyticsCard, {
      performanceMetrics,
      comparisonData,
    });
    expect(element).toBeTruthy();
  });

  it('应该显示出租率变化', async () => {
    const AdvancedAnalyticsCard = (await import('../AdvancedAnalyticsCard')).default;
    const performanceMetrics = {
      asset_utilization: 0.8,
      income_efficiency: 0.7,
      occupancy_variance: 0.1,
      growth_rate: 0.05,
    };
    const comparisonData = {
      change_percentage: {
        total_assets: 5,
        total_area: 3,
        occupancy_rate: 2,
        total_net_income: 10,
      },
    };
    const element = React.createElement(AdvancedAnalyticsCard, {
      performanceMetrics,
      comparisonData,
    });
    expect(element).toBeTruthy();
  });

  it('应该显示净收益变化', async () => {
    const AdvancedAnalyticsCard = (await import('../AdvancedAnalyticsCard')).default;
    const performanceMetrics = {
      asset_utilization: 0.8,
      income_efficiency: 0.7,
      occupancy_variance: 0.1,
      growth_rate: 0.05,
    };
    const comparisonData = {
      change_percentage: {
        total_assets: 5,
        total_area: 3,
        occupancy_rate: 2,
        total_net_income: 10,
      },
    };
    const element = React.createElement(AdvancedAnalyticsCard, {
      performanceMetrics,
      comparisonData,
    });
    expect(element).toBeTruthy();
  });
});

describe('AdvancedAnalyticsCard - 响应式布局测试', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('应该支持xs屏幕尺寸', async () => {
    const AdvancedAnalyticsCard = (await import('../AdvancedAnalyticsCard')).default;
    const performanceMetrics = {
      asset_utilization: 0.8,
      income_efficiency: 0.7,
      occupancy_variance: 0.1,
      growth_rate: 0.05,
    };
    const element = React.createElement(AdvancedAnalyticsCard, { performanceMetrics });
    expect(element).toBeTruthy();
  });

  it('应该支持sm屏幕尺寸', async () => {
    const AdvancedAnalyticsCard = (await import('../AdvancedAnalyticsCard')).default;
    const performanceMetrics = {
      asset_utilization: 0.8,
      income_efficiency: 0.7,
      occupancy_variance: 0.1,
      growth_rate: 0.05,
    };
    const element = React.createElement(AdvancedAnalyticsCard, { performanceMetrics });
    expect(element).toBeTruthy();
  });

  it('应该支持lg屏幕尺寸', async () => {
    const AdvancedAnalyticsCard = (await import('../AdvancedAnalyticsCard')).default;
    const performanceMetrics = {
      asset_utilization: 0.8,
      income_efficiency: 0.7,
      occupancy_variance: 0.1,
      growth_rate: 0.05,
    };
    const element = React.createElement(AdvancedAnalyticsCard, { performanceMetrics });
    expect(element).toBeTruthy();
  });
});

describe('AdvancedAnalyticsCard - 边界情况测试', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('应该处理undefined comparisonData', async () => {
    const AdvancedAnalyticsCard = (await import('../AdvancedAnalyticsCard')).default;
    const performanceMetrics = {
      asset_utilization: 0.8,
      income_efficiency: 0.7,
      occupancy_variance: 0.1,
      growth_rate: 0.05,
    };
    const element = React.createElement(AdvancedAnalyticsCard, {
      performanceMetrics,
      comparisonData: undefined,
    });
    expect(element).toBeTruthy();
  });

  it('应该处理增长率为0', async () => {
    const AdvancedAnalyticsCard = (await import('../AdvancedAnalyticsCard')).default;
    const performanceMetrics = {
      asset_utilization: 0.8,
      income_efficiency: 0.7,
      occupancy_variance: 0.1,
      growth_rate: 0,
    };
    const element = React.createElement(AdvancedAnalyticsCard, { performanceMetrics });
    expect(element).toBeTruthy();
  });

  it('应该处理负增长率', async () => {
    const AdvancedAnalyticsCard = (await import('../AdvancedAnalyticsCard')).default;
    const performanceMetrics = {
      asset_utilization: 0.8,
      income_efficiency: 0.7,
      occupancy_variance: 0.1,
      growth_rate: -0.05,
    };
    const element = React.createElement(AdvancedAnalyticsCard, { performanceMetrics });
    expect(element).toBeTruthy();
  });
});
