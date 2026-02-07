/**
 * AnalyticsDashboard 组件测试（修复版）
 * 测试分析仪表板组件
 *
 * 修复内容：
 * - 移除过度的 Ant Design 组件 mock
 * - 使用 renderWithProviders 提供必要的 Context Provider
 * - 保留必要的 mock（hooks, utils, 子组件）
 * - 添加 beforeEach 清除 mock
 * - 保持完整的测试覆盖
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { renderWithProviders, screen, fireEvent } from '@/test/utils/test-helpers';
import React from 'react';
import { useAnalytics } from '@/hooks/useAnalytics';

// Mock hooks（这些 mock 是必要的）
vi.mock('@/hooks/useAnalytics', () => ({
  useAnalytics: vi.fn(() => ({
    data: {
      data: {
        area_summary: {
          total_assets: 100,
          total_area: 5000,
          total_rentable_area: 4000,
          occupancy_rate: 85,
        },
        financial_summary: {
          estimated_annual_income: 100000,
          total_monthly_rent: 10000,
          total_deposit: 50000,
        },
        property_nature_distribution: [{ name: '商业', count: 50, percentage: 50 }],
        ownership_status_distribution: [{ status: '已确权', count: 80, percentage: 80 }],
        usage_status_distribution: [{ status: '出租', count: 70, percentage: 70 }],
        occupancy_distribution: [{ range: '80-100%', count: 30, percentage: 30 }],
        business_category_distribution: [{ category: '零售', occupancy_rate: 90, count: 20 }],
        occupancy_trend: [
          {
            date: '2024-01',
            occupancy_rate: 85,
            total_rented_area: 3400,
            total_rentable_area: 4000,
          },
        ],
      },
    },
    isLoading: false,
    error: null,
    refetch: vi.fn(),
  })),
}));

// Mock utils（这些 mock 是必要的）
vi.mock('@/utils/messageManager', () => ({
  MessageManager: {
    loading: vi.fn(),
    success: vi.fn(),
    error: vi.fn(),
  },
}));

vi.mock('@/utils/logger', () => ({
  createLogger: () => ({
    error: vi.fn(),
    warn: vi.fn(),
    info: vi.fn(),
  }),
}));

vi.mock('@/api/config', async importOriginal => {
  const actual = await importOriginal<typeof import('@/api/config')>();
  return {
    ...actual,
    createApiUrl: (path: string) => `/api${path}`,
  };
});

// Mock sub-components（这些 mock 是必要的，避免测试子组件本身）
vi.mock('@/components/Analytics/AnalyticsFilters', () => ({
  AnalyticsFilters: ({
    onApplyFilters,
    onResetFilters,
    loading,
  }: {
    filters: Record<string, unknown>;
    onFiltersChange: (f: Record<string, unknown>) => void;
    onApplyFilters?: () => void;
    onResetFilters?: () => void;
    loading?: boolean;
    showAdvanced?: boolean;
    onToggleAdvanced?: () => void;
  }) => (
    <div data-testid="analytics-filters" data-loading={loading}>
      <button data-testid="apply-filters" onClick={onApplyFilters}>
        Apply
      </button>
      <button data-testid="reset-filters" onClick={onResetFilters}>
        Reset
      </button>
    </div>
  ),
}));

vi.mock('@/components/Analytics/StatisticCard', () => ({
  StatisticCard: ({
    title,
    value,
    suffix,
    loading,
  }: {
    title: string;
    value: number;
    suffix?: string;
    loading?: boolean;
  }) => (
    <div data-testid="statistic-card" data-title={title} data-loading={loading}>
      {value}
      {suffix}
    </div>
  ),
  FinancialStatisticCard: ({
    title,
    value,
    suffix,
    loading,
  }: {
    title: string;
    value: number;
    suffix?: string;
    loading?: boolean;
    isPositive?: boolean;
  }) => (
    <div data-testid="financial-statistic-card" data-title={title} data-loading={loading}>
      {value}
      {suffix}
    </div>
  ),
}));

vi.mock('@/components/Analytics/AnalyticsCard', () => ({
  ChartCard: ({
    title,
    children,
    loading,
  }: {
    title: string;
    hasData?: boolean;
    loading?: boolean;
    children?: React.ReactNode;
  }) => (
    <div data-testid="chart-card" data-title={title} data-loading={loading}>
      {children}
    </div>
  ),
}));

vi.mock('@/components/Analytics/Charts', () => ({
  AnalyticsPieChart: ({ data }: { data: unknown[]; dataKey: string; labelKey: string }) => (
    <div data-testid="pie-chart">{JSON.stringify(data)}</div>
  ),
  AnalyticsBarChart: ({
    data,
  }: {
    data: unknown[];
    xDataKey: string;
    yDataKey: string;
    barName?: string;
    isPercentage?: boolean;
  }) => <div data-testid="bar-chart">{JSON.stringify(data)}</div>,
  AnalyticsLineChart: ({
    data,
  }: {
    data: unknown[];
    xDataKey: string;
    yDataKey: string;
    lineName?: string;
    isPercentage?: boolean;
  }) => <div data-testid="line-chart">{JSON.stringify(data)}</div>,
}));

vi.mock('@/components/PerformanceMonitor', () => ({
  default: () => <div data-testid="performance-monitor" />,
}));

const resetAnalyticsHookMock = (): void => {
  vi.mocked(useAnalytics).mockReturnValue({
    data: {
      data: {
        area_summary: {
          total_assets: 100,
          total_area: 5000,
          total_rentable_area: 4000,
          occupancy_rate: 85,
        },
        financial_summary: {
          estimated_annual_income: 100000,
          total_monthly_rent: 10000,
          total_deposit: 50000,
        },
        property_nature_distribution: [{ name: '商业', count: 50, percentage: 50 }],
        ownership_status_distribution: [{ status: '已确权', count: 80, percentage: 80 }],
        usage_status_distribution: [{ status: '出租', count: 70, percentage: 70 }],
        occupancy_distribution: [{ range: '80-100%', count: 30, percentage: 30 }],
        business_category_distribution: [{ category: '零售', occupancy_rate: 90, count: 20 }],
        occupancy_trend: [
          {
            date: '2024-01',
            occupancy_rate: 85,
            total_rented_area: 3400,
            total_rentable_area: 4000,
          },
        ],
      },
    },
    isLoading: false,
    error: null,
    refetch: vi.fn(),
  } as unknown as ReturnType<typeof useAnalytics>);
};

describe('AnalyticsDashboard - 组件导入测试', () => {
  it('应该能够导入AnalyticsDashboard组件', async () => {
    const module = await import('../AnalyticsDashboard');
    expect(module).toBeDefined();
    expect(module.AnalyticsDashboard).toBeDefined();
  });

  it('应该导出默认导出', async () => {
    const module = await import('../AnalyticsDashboard');
    expect(module.default).toBeDefined();
  });
});

describe('AnalyticsDashboard - 渲染测试', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    resetAnalyticsHookMock();
  });

  it('应该渲染标题', async () => {
    const { AnalyticsDashboard } = await import('../AnalyticsDashboard');
    renderWithProviders(<AnalyticsDashboard />);

    expect(screen.getByText('资产分析')).toBeInTheDocument();
  });

  it('应该渲染AnalyticsFilters组件', async () => {
    const { AnalyticsDashboard } = await import('../AnalyticsDashboard');
    renderWithProviders(<AnalyticsDashboard />);

    expect(screen.getByTestId('analytics-filters')).toBeInTheDocument();
  });

  it('应该渲染刷新按钮', async () => {
    const { AnalyticsDashboard } = await import('../AnalyticsDashboard');
    renderWithProviders(<AnalyticsDashboard />);

    expect(screen.getByText('刷新')).toBeInTheDocument();
  });

  it('应该渲染导出按钮', async () => {
    const { AnalyticsDashboard } = await import('../AnalyticsDashboard');
    renderWithProviders(<AnalyticsDashboard />);

    expect(screen.getByText('导出')).toBeInTheDocument();
  });

  it('应该渲染全屏按钮', async () => {
    const { AnalyticsDashboard } = await import('../AnalyticsDashboard');
    renderWithProviders(<AnalyticsDashboard />);

    expect(screen.getByText('全屏')).toBeInTheDocument();
  });

  it('应该渲染自动刷新按钮', async () => {
    const { AnalyticsDashboard } = await import('../AnalyticsDashboard');
    renderWithProviders(<AnalyticsDashboard />);

    expect(screen.getByText('自动刷新')).toBeInTheDocument();
  });
});

describe('AnalyticsDashboard - 统计卡片测试', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    resetAnalyticsHookMock();
  });

  it('应该渲染关键指标卡片', async () => {
    const { AnalyticsDashboard } = await import('../AnalyticsDashboard');
    renderWithProviders(<AnalyticsDashboard />);

    const statisticCards = screen.getAllByTestId('statistic-card');
    expect(statisticCards.length).toBeGreaterThan(0);
  });

  it('应该渲染财务指标卡片', async () => {
    const { AnalyticsDashboard } = await import('../AnalyticsDashboard');
    renderWithProviders(<AnalyticsDashboard />);

    const financialCards = screen.getAllByTestId('financial-statistic-card');
    expect(financialCards.length).toBeGreaterThan(0);
  });
});

describe('AnalyticsDashboard - 图表测试', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    resetAnalyticsHookMock();
  });

  it('应该渲染图表卡片', async () => {
    const { AnalyticsDashboard } = await import('../AnalyticsDashboard');
    renderWithProviders(<AnalyticsDashboard />);

    const chartCards = screen.getAllByTestId('chart-card');
    expect(chartCards.length).toBeGreaterThan(0);
  });

  it('应该渲染饼图', async () => {
    const { AnalyticsDashboard } = await import('../AnalyticsDashboard');
    renderWithProviders(<AnalyticsDashboard />);

    const pieCharts = screen.getAllByTestId('pie-chart');
    expect(pieCharts.length).toBeGreaterThan(0);
  });

  it('应该渲染柱状图', async () => {
    const { AnalyticsDashboard } = await import('../AnalyticsDashboard');
    renderWithProviders(<AnalyticsDashboard />);

    const barCharts = screen.getAllByTestId('bar-chart');
    expect(barCharts.length).toBeGreaterThan(0);
  });

  it('应该渲染折线图', async () => {
    const { AnalyticsDashboard } = await import('../AnalyticsDashboard');
    renderWithProviders(<AnalyticsDashboard />);

    const lineCharts = screen.getAllByTestId('line-chart');
    expect(lineCharts.length).toBeGreaterThan(0);
  });
});

describe('AnalyticsDashboard - 交互测试', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    resetAnalyticsHookMock();
  });

  it('点击刷新按钮应该调用refetch', async () => {
    const { useAnalytics } = await import('@/hooks/useAnalytics');
    const mockRefetch = vi.fn();
    vi.mocked(useAnalytics).mockReturnValue({
      data: {
        data: {
          area_summary: {
            total_assets: 100,
            total_area: 5000,
            total_rentable_area: 4000,
            occupancy_rate: 85,
          },
          financial_summary: {
            estimated_annual_income: 100000,
            total_monthly_rent: 10000,
            total_deposit: 50000,
          },
          property_nature_distribution: [],
          ownership_status_distribution: [],
          usage_status_distribution: [],
          occupancy_distribution: [],
          business_category_distribution: [],
          occupancy_trend: [],
        },
      },
      isLoading: false,
      error: null,
      refetch: mockRefetch,
    } as ReturnType<typeof useAnalytics>);

    const { AnalyticsDashboard } = await import('../AnalyticsDashboard');
    renderWithProviders(<AnalyticsDashboard />);

    const refreshButton = screen.getByText('刷新');
    fireEvent.click(refreshButton);

    expect(mockRefetch).toHaveBeenCalled();
  });

  it('点击应用筛选按钮应该调用refetch', async () => {
    const { useAnalytics } = await import('@/hooks/useAnalytics');
    const mockRefetch = vi.fn();
    vi.mocked(useAnalytics).mockReturnValue({
      data: {
        data: {
          area_summary: {
            total_assets: 100,
            total_area: 5000,
            total_rentable_area: 4000,
            occupancy_rate: 85,
          },
          financial_summary: {
            estimated_annual_income: 100000,
            total_monthly_rent: 10000,
            total_deposit: 50000,
          },
          property_nature_distribution: [],
          ownership_status_distribution: [],
          usage_status_distribution: [],
          occupancy_distribution: [],
          business_category_distribution: [],
          occupancy_trend: [],
        },
      },
      isLoading: false,
      error: null,
      refetch: mockRefetch,
    } as ReturnType<typeof useAnalytics>);

    const { AnalyticsDashboard } = await import('../AnalyticsDashboard');
    renderWithProviders(<AnalyticsDashboard />);

    const applyButton = screen.getByTestId('apply-filters');
    fireEvent.click(applyButton);

    expect(mockRefetch).toHaveBeenCalled();
  });
});

describe('AnalyticsDashboard - 导出功能测试', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    resetAnalyticsHookMock();
  });

  it('应该有Excel导出选项', async () => {
    const { AnalyticsDashboard } = await import('../AnalyticsDashboard');
    renderWithProviders(<AnalyticsDashboard />);

    const exportButton = screen.getByRole('button', { name: /导出/ });
    fireEvent.mouseEnter(exportButton);
    fireEvent.mouseOver(exportButton);
    expect(await screen.findByText('导出为 Excel')).toBeInTheDocument();
  });

  it('应该有PDF导出选项', async () => {
    const { AnalyticsDashboard } = await import('../AnalyticsDashboard');
    renderWithProviders(<AnalyticsDashboard />);

    const exportButton = screen.getByRole('button', { name: /导出/ });
    fireEvent.mouseEnter(exportButton);
    fireEvent.mouseOver(exportButton);
    expect(await screen.findByText('导出为 PDF')).toBeInTheDocument();
  });

  it('应该有CSV导出选项', async () => {
    const { AnalyticsDashboard } = await import('../AnalyticsDashboard');
    renderWithProviders(<AnalyticsDashboard />);

    const exportButton = screen.getByRole('button', { name: /导出/ });
    fireEvent.mouseEnter(exportButton);
    fireEvent.mouseOver(exportButton);
    expect(await screen.findByText('导出为 CSV')).toBeInTheDocument();
  });
});

describe('AnalyticsDashboard - 空状态测试', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    resetAnalyticsHookMock();
  });

  it('无数据时应该显示暂无数据', async () => {
    const { useAnalytics } = await import('@/hooks/useAnalytics');
    vi.mocked(useAnalytics).mockReturnValue({
      data: {
        data: {
          area_summary: {
            total_assets: 0,
            total_area: 0,
            total_rentable_area: 0,
            occupancy_rate: 0,
          },
          financial_summary: {
            estimated_annual_income: 0,
            total_monthly_rent: 0,
            total_deposit: 0,
          },
          property_nature_distribution: [],
          ownership_status_distribution: [],
          usage_status_distribution: [],
          occupancy_distribution: [],
          business_category_distribution: [],
          occupancy_trend: [],
        },
      },
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    } as ReturnType<typeof useAnalytics>);

    const { AnalyticsDashboard } = await import('../AnalyticsDashboard');
    renderWithProviders(<AnalyticsDashboard />);

    expect(screen.getByText('暂无数据')).toBeInTheDocument();
  });
});

describe('AnalyticsDashboard - 错误状态测试', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    resetAnalyticsHookMock();
  });

  it('错误时应该显示错误信息', async () => {
    const { useAnalytics } = await import('@/hooks/useAnalytics');
    vi.mocked(useAnalytics).mockReturnValue({
      data: undefined,
      isLoading: false,
      error: { message: '网络错误' },
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof useAnalytics>);

    const { AnalyticsDashboard } = await import('../AnalyticsDashboard');
    renderWithProviders(<AnalyticsDashboard />);

    expect(screen.getByText('数据加载失败')).toBeInTheDocument();
  });

  it('错误时应该显示重试按钮', async () => {
    const { useAnalytics } = await import('@/hooks/useAnalytics');
    vi.mocked(useAnalytics).mockReturnValue({
      data: undefined,
      isLoading: false,
      error: { message: '网络错误' },
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof useAnalytics>);

    const { AnalyticsDashboard } = await import('../AnalyticsDashboard');
    renderWithProviders(<AnalyticsDashboard />);

    expect(screen.getByRole('button', { name: /重\s*试/ })).toBeInTheDocument();
  });
});

describe('AnalyticsDashboard - 属性测试', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    resetAnalyticsHookMock();
  });

  it('应该支持initialFilters属性', async () => {
    const { AnalyticsDashboard } = await import('../AnalyticsDashboard');
    const initialFilters = { ownership_status: '自有' };
    renderWithProviders(<AnalyticsDashboard initialFilters={initialFilters} />);

    expect(screen.getByTestId('analytics-filters')).toBeInTheDocument();
  });

  it('应该支持className属性', async () => {
    const { AnalyticsDashboard } = await import('../AnalyticsDashboard');
    const { container } = renderWithProviders(<AnalyticsDashboard className="custom-class" />);

    expect(container.firstChild).toHaveClass('custom-class');
  });
});
