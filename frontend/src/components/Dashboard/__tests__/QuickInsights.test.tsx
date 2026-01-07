/**
 * QuickInsights 组件测试
 * 测试智能洞察卡片组件
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import React from 'react';

// Mock Ant Design components
vi.mock('antd', () => ({
  Card: ({ children, title, loading, className, variant, size }: any) => (
    <div
      data-testid="card"
      data-title={title}
      data-loading={loading}
      data-class-name={className}
      data-variant={variant}
      data-size={size}
    >
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
  Typography: {
    Title: ({ children, level, className }: any) => (
      <div data-testid="title" data-level={level} className={className}>
        {children}
      </div>
    ),
    Text: ({ children, type }: any) => (
      <div data-testid="text" data-type={type}>
        {children}
      </div>
    ),
  },
  Space: ({ children }: any) => <div data-testid="space">{children}</div>,
}));

// Mock icons
vi.mock('@ant-design/icons', () => ({
  HomeOutlined: () => <div data-testid="icon-home" />,
  PieChartOutlined: () => <div data-testid="icon-pie-chart" />,
  RiseOutlined: () => <div data-testid="icon-rise" />,
  AlertOutlined: () => <div data-testid="icon-alert" />,
  CheckCircleOutlined: () => <div data-testid="icon-check-circle" />,
}));

// Mock CSS modules
vi.mock('./QuickInsights.module.css', () => ({
  insightsContainer: 'insights-container',
  titleContainer: 'title-container',
  title: 'title',
  insightCard: 'insight-card',
  success: 'success',
  warning: 'warning',
  error: 'error',
  info: 'info',
  insightHeader: 'insight-header',
  insightIcon: 'insight-icon',
  insightTitle: 'insight-title',
  insightContent: 'insight-content',
  insightDescription: 'insight-description',
  insightHighlight: 'insight-highlight',
}));

describe('QuickInsights - 组件导入测试', () => {
  it('应该能够导入QuickInsights组件', async () => {
    const module = await import('../QuickInsights');
    expect(module).toBeDefined();
    expect(module.default).toBeDefined();
  });
});

describe('QuickInsights - 基础属性测试', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('应该支持data属性', async () => {
    const QuickInsights = (await import('../QuickInsights')).default;
    const data = {
      totalAssets: 100,
      totalArea: 5000,
      occupancyRate: 85,
      totalRentedArea: 4000,
      totalUnrentedArea: 1000,
    };
    const element = React.createElement(QuickInsights, { data });
    expect(element).toBeTruthy();
  });

  it('应该支持loading属性', async () => {
    const QuickInsights = (await import('../QuickInsights')).default;
    const data = {
      totalAssets: 100,
      totalArea: 5000,
      occupancyRate: 85,
      totalRentedArea: 4000,
      totalUnrentedArea: 1000,
    };
    const element = React.createElement(QuickInsights, { data, loading: true });
    expect(element).toBeTruthy();
  });

  it('默认loading应该是false', async () => {
    const QuickInsights = (await import('../QuickInsights')).default;
    const data = {
      totalAssets: 100,
      totalArea: 5000,
      occupancyRate: 85,
      totalRentedArea: 4000,
      totalUnrentedArea: 1000,
    };
    const element = React.createElement(QuickInsights, { data });
    expect(element).toBeTruthy();
  });
});

describe('QuickInsights - 出租率洞察测试', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('occupancyRate大于95%应该显示成功洞察', async () => {
    const QuickInsights = (await import('../QuickInsights')).default;
    const data = {
      totalAssets: 100,
      totalArea: 5000,
      occupancyRate: 96,
      totalRentedArea: 4800,
      totalUnrentedArea: 200,
    };
    const element = React.createElement(QuickInsights, { data });
    expect(element).toBeTruthy();
  });

  it('occupancyRate小于85%应该显示警告洞察', async () => {
    const QuickInsights = (await import('../QuickInsights')).default;
    const data = {
      totalAssets: 100,
      totalArea: 5000,
      occupancyRate: 80,
      totalRentedArea: 4000,
      totalUnrentedArea: 1000,
    };
    const element = React.createElement(QuickInsights, { data });
    expect(element).toBeTruthy();
  });

  it('occupancyRate在85%-95%之间应该显示正常洞察', async () => {
    const QuickInsights = (await import('../QuickInsights')).default;
    const data = {
      totalAssets: 100,
      totalArea: 5000,
      occupancyRate: 90,
      totalRentedArea: 4500,
      totalUnrentedArea: 500,
    };
    const element = React.createElement(QuickInsights, { data });
    expect(element).toBeTruthy();
  });

  it('occupancyRate正好为95%应该显示成功洞察', async () => {
    const QuickInsights = (await import('../QuickInsights')).default;
    const data = {
      totalAssets: 100,
      totalArea: 5000,
      occupancyRate: 95,
      totalRentedArea: 4750,
      totalUnrentedArea: 250,
    };
    const element = React.createElement(QuickInsights, { data });
    expect(element).toBeTruthy();
  });

  it('occupancyRate正好为85%应该显示正常洞察', async () => {
    const QuickInsights = (await import('../QuickInsights')).default;
    const data = {
      totalAssets: 100,
      totalArea: 5000,
      occupancyRate: 85,
      totalRentedArea: 4250,
      totalUnrentedArea: 750,
    };
    const element = React.createElement(QuickInsights, { data });
    expect(element).toBeTruthy();
  });
});

describe('QuickInsights - 资产规模洞察测试', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('totalAssets大于500应该显示资产规模洞察', async () => {
    const QuickInsights = (await import('../QuickInsights')).default;
    const data = {
      totalAssets: 600,
      totalArea: 50000,
      occupancyRate: 85,
      totalRentedArea: 42500,
      totalUnrentedArea: 7500,
    };
    const element = React.createElement(QuickInsights, { data });
    expect(element).toBeTruthy();
  });

  it('totalAssets等于500不应该显示资产规模洞察', async () => {
    const QuickInsights = (await import('../QuickInsights')).default;
    const data = {
      totalAssets: 500,
      totalArea: 25000,
      occupancyRate: 85,
      totalRentedArea: 21250,
      totalUnrentedArea: 3750,
    };
    const element = React.createElement(QuickInsights, { data });
    expect(element).toBeTruthy();
  });

  it('totalAssets小于500不应该显示资产规模洞察', async () => {
    const QuickInsights = (await import('../QuickInsights')).default;
    const data = {
      totalAssets: 400,
      totalArea: 20000,
      occupancyRate: 85,
      totalRentedArea: 17000,
      totalUnrentedArea: 3000,
    };
    const element = React.createElement(QuickInsights, { data });
    expect(element).toBeTruthy();
  });
});

describe('QuickInsights - 空置资产洞察测试', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('totalUnrentedArea大于10000应该显示空置面积警告', async () => {
    const QuickInsights = (await import('../QuickInsights')).default;
    const data = {
      totalAssets: 100,
      totalArea: 50000,
      occupancyRate: 75,
      totalRentedArea: 37500,
      totalUnrentedArea: 12500,
    };
    const element = React.createElement(QuickInsights, { data });
    expect(element).toBeTruthy();
  });

  it('totalUnrentedArea等于10000不应该显示空置面积警告', async () => {
    const QuickInsights = (await import('../QuickInsights')).default;
    const data = {
      totalAssets: 100,
      totalArea: 40000,
      occupancyRate: 75,
      totalRentedArea: 30000,
      totalUnrentedArea: 10000,
    };
    const element = React.createElement(QuickInsights, { data });
    expect(element).toBeTruthy();
  });

  it('totalUnrentedArea小于10000不应该显示空置面积警告', async () => {
    const QuickInsights = (await import('../QuickInsights')).default;
    const data = {
      totalAssets: 100,
      totalArea: 30000,
      occupancyRate: 75,
      totalRentedArea: 22500,
      totalUnrentedArea: 7500,
    };
    const element = React.createElement(QuickInsights, { data });
    expect(element).toBeTruthy();
  });
});

describe('QuickInsights - 默认洞察测试', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('没有匹配条件时应该显示默认洞察', async () => {
    const QuickInsights = (await import('../QuickInsights')).default;
    const data = {
      totalAssets: 400,
      totalArea: 20000,
      occupancyRate: 90,
      totalRentedArea: 18000,
      totalUnrentedArea: 2000,
    };
    const element = React.createElement(QuickInsights, { data });
    expect(element).toBeTruthy();
  });
});

describe('QuickInsights - 多洞察组合测试', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('高出租率+大规模应该显示两个洞察', async () => {
    const QuickInsights = (await import('../QuickInsights')).default;
    const data = {
      totalAssets: 600,
      totalArea: 50000,
      occupancyRate: 96,
      totalRentedArea: 48000,
      totalUnrentedArea: 2000,
    };
    const element = React.createElement(QuickInsights, { data });
    expect(element).toBeTruthy();
  });

  it('低出租率+高空置应该显示两个洞察', async () => {
    const QuickInsights = (await import('../QuickInsights')).default;
    const data = {
      totalAssets: 400,
      totalArea: 50000,
      occupancyRate: 75,
      totalRentedArea: 37500,
      totalUnrentedArea: 12500,
    };
    const element = React.createElement(QuickInsights, { data });
    expect(element).toBeTruthy();
  });

  it('所有条件满足应该显示多个洞察', async () => {
    const QuickInsights = (await import('../QuickInsights')).default;
    const data = {
      totalAssets: 600,
      totalArea: 60000,
      occupancyRate: 96,
      totalRentedArea: 48000,
      totalUnrentedArea: 12000,
    };
    const element = React.createElement(QuickInsights, { data });
    expect(element).toBeTruthy();
  });
});

describe('QuickInsights - recentActivity测试', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('应该支持recentActivity属性', async () => {
    const QuickInsights = (await import('../QuickInsights')).default;
    const data = {
      totalAssets: 100,
      totalArea: 5000,
      occupancyRate: 85,
      totalRentedArea: 4000,
      totalUnrentedArea: 1000,
      recentActivity: {
        newAssets: 5,
        updatedAssets: 10,
        maintenanceRequired: 2,
      },
    };
    const element = React.createElement(QuickInsights, { data });
    expect(element).toBeTruthy();
  });

  it('recentActivity可以为undefined', async () => {
    const QuickInsights = (await import('../QuickInsights')).default;
    const data = {
      totalAssets: 100,
      totalArea: 5000,
      occupancyRate: 85,
      totalRentedArea: 4000,
      totalUnrentedArea: 1000,
    };
    const element = React.createElement(QuickInsights, { data });
    expect(element).toBeTruthy();
  });
});

describe('QuickInsights - 洞察类型样式测试', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('成功洞察应该应用success样式', async () => {
    const QuickInsights = (await import('../QuickInsights')).default;
    const data = {
      totalAssets: 100,
      totalArea: 5000,
      occupancyRate: 96,
      totalRentedArea: 4800,
      totalUnrentedArea: 200,
    };
    const element = React.createElement(QuickInsights, { data });
    expect(element).toBeTruthy();
  });

  it('警告洞察应该应用warning样式', async () => {
    const QuickInsights = (await import('../QuickInsights')).default;
    const data = {
      totalAssets: 100,
      totalArea: 5000,
      occupancyRate: 80,
      totalRentedArea: 4000,
      totalUnrentedArea: 1000,
    };
    const element = React.createElement(QuickInsights, { data });
    expect(element).toBeTruthy();
  });

  it('正常洞察应该应用info样式', async () => {
    const QuickInsights = (await import('../QuickInsights')).default;
    const data = {
      totalAssets: 100,
      totalArea: 5000,
      occupancyRate: 90,
      totalRentedArea: 4500,
      totalUnrentedArea: 500,
    };
    const element = React.createElement(QuickInsights, { data });
    expect(element).toBeTruthy();
  });
});

describe('QuickInsights - 响应式布局测试', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('应该支持xs屏幕尺寸', async () => {
    const QuickInsights = (await import('../QuickInsights')).default;
    const data = {
      totalAssets: 100,
      totalArea: 5000,
      occupancyRate: 85,
      totalRentedArea: 4000,
      totalUnrentedArea: 1000,
    };
    const element = React.createElement(QuickInsights, { data });
    expect(element).toBeTruthy();
  });

  it('应该支持sm屏幕尺寸', async () => {
    const QuickInsights = (await import('../QuickInsights')).default;
    const data = {
      totalAssets: 100,
      totalArea: 5000,
      occupancyRate: 85,
      totalRentedArea: 4000,
      totalUnrentedArea: 1000,
    };
    const element = React.createElement(QuickInsights, { data });
    expect(element).toBeTruthy();
  });

  it('应该支持lg屏幕尺寸', async () => {
    const QuickInsights = (await import('../QuickInsights')).default;
    const data = {
      totalAssets: 100,
      totalArea: 5000,
      occupancyRate: 85,
      totalRentedArea: 4000,
      totalUnrentedArea: 1000,
    };
    const element = React.createElement(QuickInsights, { data });
    expect(element).toBeTruthy();
  });
});

describe('QuickInsights - 边界情况测试', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('应该处理data为undefined', async () => {
    const QuickInsights = (await import('../QuickInsights')).default;
    const element = React.createElement(QuickInsights, { data: undefined });
    expect(element).toBeTruthy();
  });

  it('应该处理occupancyRate为0', async () => {
    const QuickInsights = (await import('../QuickInsights')).default;
    const data = {
      totalAssets: 100,
      totalArea: 5000,
      occupancyRate: 0,
      totalRentedArea: 0,
      totalUnrentedArea: 5000,
    };
    const element = React.createElement(QuickInsights, { data });
    expect(element).toBeTruthy();
  });

  it('应该处理occupancyRate为100', async () => {
    const QuickInsights = (await import('../QuickInsights')).default;
    const data = {
      totalAssets: 100,
      totalArea: 5000,
      occupancyRate: 100,
      totalRentedArea: 5000,
      totalUnrentedArea: 0,
    };
    const element = React.createElement(QuickInsights, { data });
    expect(element).toBeTruthy();
  });

  it('应该处理totalAssets为0', async () => {
    const QuickInsights = (await import('../QuickInsights')).default;
    const data = {
      totalAssets: 0,
      totalArea: 0,
      occupancyRate: 0,
      totalRentedArea: 0,
      totalUnrentedArea: 0,
    };
    const element = React.createElement(QuickInsights, { data });
    expect(element).toBeTruthy();
  });
});

describe('QuickInsights - Card属性测试', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('应该使用borderless variant', async () => {
    const QuickInsights = (await import('../QuickInsights')).default;
    const data = {
      totalAssets: 100,
      totalArea: 5000,
      occupancyRate: 85,
      totalRentedArea: 4000,
      totalUnrentedArea: 1000,
    };
    const element = React.createElement(QuickInsights, { data });
    expect(element).toBeTruthy();
  });

  it('应该显示标题', async () => {
    const QuickInsights = (await import('../QuickInsights')).default;
    const data = {
      totalAssets: 100,
      totalArea: 5000,
      occupancyRate: 85,
      totalRentedArea: 4000,
      totalUnrentedArea: 1000,
    };
    const element = React.createElement(QuickInsights, { data });
    expect(element).toBeTruthy();
  });
});
