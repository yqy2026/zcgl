/**
 * QuickInsights 组件测试
 * 测试智能洞察卡片组件
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import React from 'react';
import { screen } from '@/test/utils/test-helpers';
import QuickInsights from '../QuickInsights';

interface CardMockProps {
  children?: React.ReactNode;
  title?: React.ReactNode;
  loading?: boolean;
  className?: string;
  variant?: string;
  size?: string;
}

interface RowMockProps {
  children?: React.ReactNode;
  gutter?: unknown;
}

interface ColMockProps {
  children?: React.ReactNode;
  xs?: unknown;
  sm?: unknown;
  lg?: unknown;
}

interface TitleMockProps {
  children?: React.ReactNode;
  level?: number;
  className?: string;
}

interface TextMockProps {
  children?: React.ReactNode;
  type?: string;
}

// Mock Ant Design components
vi.mock('antd', () => ({
  Card: ({ children, title, loading, className, variant, size }: CardMockProps) => (
    <div
      data-testid="card"
      data-loading={loading}
      data-class-name={className}
      data-variant={variant}
      data-size={size}
    >
      {title && <div data-testid="card-title">{title}</div>}
      {children}
    </div>
  ),
  Row: ({ children, gutter }: RowMockProps) => (
    <div data-testid="row" data-gutter={JSON.stringify(gutter)}>
      {children}
    </div>
  ),
  Col: ({ children, xs, sm, lg }: ColMockProps) => (
    <div data-testid="col" data-xs={xs} data-sm={sm} data-lg={lg}>
      {children}
    </div>
  ),
  Typography: {
    Title: ({ children, level, className }: TitleMockProps) => (
      <div data-testid="title" data-level={level} className={className}>
        {children}
      </div>
    ),
    Text: ({ children, type }: TextMockProps) => (
      <div data-testid="text" data-type={type}>
        {children}
      </div>
    ),
  },
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
vi.mock('../QuickInsights.module.css', () => ({
  default: {
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
  },
}));

describe('QuickInsights - 组件导入测试', () => {
  it('应该能够导入QuickInsights组件', () => {
    expect(QuickInsights).toBeDefined();
  });
});

describe('QuickInsights - 渲染与洞察测试', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('应该显示标题与副标题', () => {
    renderWithProviders(
      <QuickInsights
        data={{
          totalAssets: 100,
          totalArea: 5000,
          occupancyRate: 90,
          totalRentedArea: 4500,
          totalUnrentedArea: 500,
        }}
      />
    );

    expect(screen.getByText('智能洞察')).toBeInTheDocument();
    expect(screen.getByText('基于当前数据的智能分析')).toBeInTheDocument();
  });

  it('高出租率应显示成功洞察', () => {
    renderWithProviders(
      <QuickInsights
        data={{
          totalAssets: 100,
          totalArea: 5000,
          occupancyRate: 96,
          totalRentedArea: 4800,
          totalUnrentedArea: 200,
        }}
      />
    );

    expect(screen.getByText('出租率表现优异')).toBeInTheDocument();
    expect(screen.getByText('96.0%')).toBeInTheDocument();
  });

  it('低出租率应显示警告洞察', () => {
    renderWithProviders(
      <QuickInsights
        data={{
          totalAssets: 100,
          totalArea: 5000,
          occupancyRate: 80,
          totalRentedArea: 4000,
          totalUnrentedArea: 12500,
        }}
      />
    );

    expect(screen.getByText('出租率有待提升')).toBeInTheDocument();
    expect(screen.getByText('12500㎡ 空置面积')).toBeInTheDocument();
  });

  it('正常出租率应显示信息洞察', () => {
    renderWithProviders(
      <QuickInsights
        data={{
          totalAssets: 100,
          totalArea: 5000,
          occupancyRate: 90,
          totalRentedArea: 4500,
          totalUnrentedArea: 500,
        }}
      />
    );

    expect(screen.getByText('出租率正常')).toBeInTheDocument();
  });

  it('资产规模大于阈值应显示规模洞察', () => {
    renderWithProviders(
      <QuickInsights
        data={{
          totalAssets: 600,
          totalArea: 50000,
          occupancyRate: 90,
          totalRentedArea: 45000,
          totalUnrentedArea: 5000,
        }}
      />
    );

    expect(screen.getByText('资产规模可观')).toBeInTheDocument();
    expect(screen.getByText('管理 600 个资产')).toBeInTheDocument();
  });

  it('空置面积过大应显示空置洞察', () => {
    renderWithProviders(
      <QuickInsights
        data={{
          totalAssets: 200,
          totalArea: 60000,
          occupancyRate: 90,
          totalRentedArea: 48000,
          totalUnrentedArea: 12000,
        }}
      />
    );

    expect(screen.getByText('空置面积较大')).toBeInTheDocument();
    expect(screen.getByText('12000㎡ 空置')).toBeInTheDocument();
  });

  it('loading为true时应透传给Card', () => {
    renderWithProviders(
      <QuickInsights
        loading={true}
        data={{
          totalAssets: 100,
          totalArea: 5000,
          occupancyRate: 90,
          totalRentedArea: 4500,
          totalUnrentedArea: 500,
        }}
      />
    );

    const cards = screen.getAllByTestId('card');
    expect(cards[0]).toHaveAttribute('data-loading', 'true');
  });
});
