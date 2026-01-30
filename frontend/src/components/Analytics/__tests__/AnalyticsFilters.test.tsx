/**
 * AnalyticsFilters 组件测试
 * 测试分析筛选器组件
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import React from 'react';

// Mock hooks
vi.mock('@/hooks/useSearchHistory', () => ({
  useSearchHistory: vi.fn(() => ({
    searchHistory: [],
    addSearchHistory: vi.fn(),
    removeSearchHistory: vi.fn(),
    clearSearchHistory: vi.fn(),
  })),
}));

vi.mock('@tanstack/react-query', () => ({
  useQuery: vi.fn(() => ({
    data: {
      ownershipEntities: [],
      businessCategories: [],
    },
    isLoading: false,
    error: null,
  })),
}));

// Mock services
vi.mock('@/services/assetService', () => ({
  assetService: {
    getOwnershipEntities: vi.fn(() => Promise.resolve([])),
    getBusinessCategories: vi.fn(() => Promise.resolve([])),
  },
}));

// Mock logger
vi.mock('@/utils/logger', () => ({
  createLogger: () => ({
    warn: vi.fn(),
    error: vi.fn(),
    info: vi.fn(),
  }),
}));

// Mock Filters sub-components
vi.mock('../Filters', () => ({
  AnalyticsFiltersProvider: ({
    children,
    filters,
    onFiltersChange,
    onApplyFilters,
    onResetFilters,
    loading,
    showAdvanced,
    onToggleAdvanced,
  }: {
    children: React.ReactNode;
    filters: Record<string, unknown>;
    onFiltersChange: (f: Record<string, unknown>) => void;
    onApplyFilters?: () => void;
    onResetFilters?: () => void;
    loading?: boolean;
    showAdvanced?: boolean;
    onToggleAdvanced?: () => void;
    onPresetSelect?: (key: string) => void;
    realTimeUpdate?: boolean;
  }) => (
    <div
      data-testid="filters-provider"
      data-filters={JSON.stringify(filters)}
      data-loading={loading}
      data-show-advanced={showAdvanced}
    >
      {children}
      <button data-testid="apply-btn" onClick={onApplyFilters}>
        Apply
      </button>
      <button data-testid="reset-btn" onClick={onResetFilters}>
        Reset
      </button>
      <button data-testid="toggle-advanced-btn" onClick={onToggleAdvanced}>
        Toggle Advanced
      </button>
      <button
        data-testid="change-filters-btn"
        onClick={() => onFiltersChange({ test: 'value' })}
      >
        Change Filters
      </button>
    </div>
  ),
  useAnalyticsFiltersContext: () => ({
    filters: {},
    activeFiltersCount: 0,
    setSaveName: vi.fn(),
    showHistory: false,
    setShowHistory: vi.fn(),
    handleReset: vi.fn(),
    handleApply: vi.fn(),
    loading: false,
    showAdvanced: false,
    onToggleAdvanced: vi.fn(),
  }),
  BasicFiltersSection: () => <div data-testid="basic-filters">Basic Filters</div>,
  FiltersSection: () => <div data-testid="filters-section">Filters Section</div>,
  SearchPresetsSection: () => <div data-testid="search-presets">Search Presets</div>,
  FilterHistorySection: () => <div data-testid="filter-history">Filter History</div>,
  FilterActionsSection: () => <div data-testid="filter-actions">Filter Actions</div>,
  FILTER_PRESETS: [
    { key: 'all', label: '全部资产', filters: {} },
    { key: 'rented', label: '出租资产', filters: { usage_status: '出租' } },
  ],
}));

// Mock Ant Design components
vi.mock('antd', () => ({
  Card: ({
    children,
    title,
    extra,
    size,
  }: {
    children?: React.ReactNode;
    title?: React.ReactNode;
    extra?: React.ReactNode;
    size?: string;
  }) => (
    <div data-testid="card" data-size={size}>
      <div data-testid="card-title">{title}</div>
      <div data-testid="card-extra">{extra}</div>
      {children}
    </div>
  ),
  Space: ({ children }: { children?: React.ReactNode }) => (
    <div data-testid="space">{children}</div>
  ),
  Tag: ({ children, color }: { children?: React.ReactNode; color?: string }) => (
    <span data-testid="tag" data-color={color}>
      {children}
    </span>
  ),
  Button: ({
    children,
    icon,
    onClick,
    disabled,
    loading,
    type,
    size,
  }: {
    children?: React.ReactNode;
    icon?: React.ReactNode;
    onClick?: () => void;
    disabled?: boolean;
    loading?: boolean;
    type?: string;
    size?: string;
  }) => (
    <button
      data-testid="button"
      data-type={type}
      data-loading={loading}
      data-size={size}
      disabled={disabled}
      onClick={onClick}
    >
      {icon}
      {children}
    </button>
  ),
  Tooltip: ({ children, title }: { children?: React.ReactNode; title?: React.ReactNode }) => (
    <div data-testid="tooltip" data-title={title}>
      {children}
    </div>
  ),
}));

// Mock icons
vi.mock('@ant-design/icons', () => ({
  FilterOutlined: () => <span data-testid="icon-filter" />,
  ClearOutlined: () => <span data-testid="icon-clear" />,
  SaveOutlined: () => <span data-testid="icon-save" />,
  HistoryOutlined: () => <span data-testid="icon-history" />,
  ReloadOutlined: () => <span data-testid="icon-reload" />,
  DownOutlined: () => <span data-testid="icon-down" />,
  UpOutlined: () => <span data-testid="icon-up" />,
}));

describe('AnalyticsFilters - 组件导入测试', () => {
  it('应该能够导入AnalyticsFilters组件', async () => {
    const module = await import('../AnalyticsFilters');
    expect(module).toBeDefined();
    expect(module.AnalyticsFilters).toBeDefined();
  });
});

describe('AnalyticsFilters - 渲染测试', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('应该渲染AnalyticsFiltersProvider', async () => {
    const { AnalyticsFilters } = await import('../AnalyticsFilters');
    render(<AnalyticsFilters filters={{}} onFiltersChange={vi.fn()} />);

    expect(screen.getByTestId('filters-provider')).toBeInTheDocument();
  });

  it('应该传递filters给Provider', async () => {
    const { AnalyticsFilters } = await import('../AnalyticsFilters');
    const filters = { ownership_status: '自有' };
    render(<AnalyticsFilters filters={filters} onFiltersChange={vi.fn()} />);

    const provider = screen.getByTestId('filters-provider');
    expect(provider).toHaveAttribute('data-filters', JSON.stringify(filters));
  });

  it('应该传递loading给Provider', async () => {
    const { AnalyticsFilters } = await import('../AnalyticsFilters');
    render(<AnalyticsFilters filters={{}} onFiltersChange={vi.fn()} loading={true} />);

    expect(screen.getByTestId('filters-provider')).toHaveAttribute('data-loading', 'true');
  });

  it('默认loading应该是false', async () => {
    const { AnalyticsFilters } = await import('../AnalyticsFilters');
    render(<AnalyticsFilters filters={{}} onFiltersChange={vi.fn()} />);

    expect(screen.getByTestId('filters-provider')).toHaveAttribute('data-loading', 'false');
  });

  it('应该传递showAdvanced给Provider', async () => {
    const { AnalyticsFilters } = await import('../AnalyticsFilters');
    render(<AnalyticsFilters filters={{}} onFiltersChange={vi.fn()} showAdvanced={true} />);

    expect(screen.getByTestId('filters-provider')).toHaveAttribute('data-show-advanced', 'true');
  });

  it('默认showAdvanced应该是false', async () => {
    const { AnalyticsFilters } = await import('../AnalyticsFilters');
    render(<AnalyticsFilters filters={{}} onFiltersChange={vi.fn()} />);

    expect(screen.getByTestId('filters-provider')).toHaveAttribute('data-show-advanced', 'false');
  });
});

describe('AnalyticsFilters - 回调函数测试', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('应该调用onFiltersChange', async () => {
    const { AnalyticsFilters } = await import('../AnalyticsFilters');
    const handleFiltersChange = vi.fn();
    render(<AnalyticsFilters filters={{}} onFiltersChange={handleFiltersChange} />);

    fireEvent.click(screen.getByTestId('change-filters-btn'));
    expect(handleFiltersChange).toHaveBeenCalledWith({ test: 'value' });
  });

  it('应该调用onApplyFilters', async () => {
    const { AnalyticsFilters } = await import('../AnalyticsFilters');
    const handleApply = vi.fn();
    render(<AnalyticsFilters filters={{}} onFiltersChange={vi.fn()} onApplyFilters={handleApply} />);

    fireEvent.click(screen.getByTestId('apply-btn'));
    expect(handleApply).toHaveBeenCalled();
  });

  it('应该调用onResetFilters', async () => {
    const { AnalyticsFilters } = await import('../AnalyticsFilters');
    const handleReset = vi.fn();
    render(<AnalyticsFilters filters={{}} onFiltersChange={vi.fn()} onResetFilters={handleReset} />);

    fireEvent.click(screen.getByTestId('reset-btn'));
    expect(handleReset).toHaveBeenCalled();
  });

  it('应该调用onToggleAdvanced', async () => {
    const { AnalyticsFilters } = await import('../AnalyticsFilters');
    const handleToggle = vi.fn();
    render(
      <AnalyticsFilters filters={{}} onFiltersChange={vi.fn()} onToggleAdvanced={handleToggle} />
    );

    fireEvent.click(screen.getByTestId('toggle-advanced-btn'));
    expect(handleToggle).toHaveBeenCalled();
  });
});

describe('AnalyticsFilters - 边界情况测试', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('应该处理空filters', async () => {
    const { AnalyticsFilters } = await import('../AnalyticsFilters');
    render(<AnalyticsFilters filters={{}} onFiltersChange={vi.fn()} />);

    expect(screen.getByTestId('filters-provider')).toBeInTheDocument();
  });

  it('应该处理realTimeUpdate属性', async () => {
    const { AnalyticsFilters } = await import('../AnalyticsFilters');
    render(<AnalyticsFilters filters={{}} onFiltersChange={vi.fn()} realTimeUpdate={false} />);

    expect(screen.getByTestId('filters-provider')).toBeInTheDocument();
  });
});
