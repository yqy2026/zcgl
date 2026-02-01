/**
 * AnalyticsFilters 组件测试（修复版）
 * 测试分析筛选器组件
 *
 * 修复内容：
 * - 移除过度的 Ant Design 组件 mock
 * - 使用 renderWithProviders 提供必要的 Context Provider
 * - 保留必要的 mock（hooks, services, Filters子组件）
 * - 添加 beforeEach 清除 mock
 * - 保持完整的测试覆盖
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { renderWithProviders, screen, fireEvent } from '@/test/utils/test-helpers';
import React from 'react';

// Mock hooks（这些 mock 是必要的）
vi.mock('@/hooks/useSearchHistory', () => ({
  useSearchHistory: vi.fn(() => ({
    searchHistory: [],
    addSearchHistory: vi.fn(),
    removeSearchHistory: vi.fn(),
    clearSearchHistory: vi.fn(),
  })),
}));

vi.mock('@tanstack/react-query', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@tanstack/react-query')>();
  return {
    ...actual,
    useQuery: vi.fn(() => ({
      data: {
        ownershipEntities: [],
        businessCategories: [],
      },
      isLoading: false,
      error: null,
    })),
  };
});

// Mock services（这些 mock 是必要的）
vi.mock('@/services/assetService', () => ({
  assetService: {
    getOwnershipEntities: vi.fn(() => Promise.resolve([])),
    getBusinessCategories: vi.fn(() => Promise.resolve([])),
  },
}));

// Mock logger（这个 mock 是必要的）
vi.mock('@/utils/logger', () => ({
  createLogger: () => ({
    warn: vi.fn(),
    error: vi.fn(),
    info: vi.fn(),
  }),
}));

// Mock Filters sub-components（这些 mock 是必要的，避免测试子组件本身）
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
    renderWithProviders(<AnalyticsFilters filters={{}} onFiltersChange={vi.fn()} />);

    expect(screen.getByTestId('filters-provider')).toBeInTheDocument();
  });

  it('应该传递filters给Provider', async () => {
    const { AnalyticsFilters } = await import('../AnalyticsFilters');
    const filters = { ownership_status: '自有' };
    renderWithProviders(<AnalyticsFilters filters={filters} onFiltersChange={vi.fn()} />);

    const provider = screen.getByTestId('filters-provider');
    expect(provider).toHaveAttribute('data-filters', JSON.stringify(filters));
  });

  it('应该传递loading给Provider', async () => {
    const { AnalyticsFilters } = await import('../AnalyticsFilters');
    renderWithProviders(<AnalyticsFilters filters={{}} onFiltersChange={vi.fn()} loading={true} />);

    expect(screen.getByTestId('filters-provider')).toHaveAttribute('data-loading', 'true');
  });

  it('默认loading应该是false', async () => {
    const { AnalyticsFilters } = await import('../AnalyticsFilters');
    renderWithProviders(<AnalyticsFilters filters={{}} onFiltersChange={vi.fn()} />);

    expect(screen.getByTestId('filters-provider')).toHaveAttribute('data-loading', 'false');
  });

  it('应该传递showAdvanced给Provider', async () => {
    const { AnalyticsFilters } = await import('../AnalyticsFilters');
    renderWithProviders(<AnalyticsFilters filters={{}} onFiltersChange={vi.fn()} showAdvanced={true} />);

    expect(screen.getByTestId('filters-provider')).toHaveAttribute('data-show-advanced', 'true');
  });

  it('默认showAdvanced应该是false', async () => {
    const { AnalyticsFilters } = await import('../AnalyticsFilters');
    renderWithProviders(<AnalyticsFilters filters={{}} onFiltersChange={vi.fn()} />);

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
    renderWithProviders(<AnalyticsFilters filters={{}} onFiltersChange={handleFiltersChange} />);

    fireEvent.click(screen.getByTestId('change-filters-btn'));
    expect(handleFiltersChange).toHaveBeenCalledWith({ test: 'value' });
  });

  it('应该调用onApplyFilters', async () => {
    const { AnalyticsFilters } = await import('../AnalyticsFilters');
    const handleApply = vi.fn();
    renderWithProviders(<AnalyticsFilters filters={{}} onFiltersChange={vi.fn()} onApplyFilters={handleApply} />);

    fireEvent.click(screen.getByTestId('apply-btn'));
    expect(handleApply).toHaveBeenCalled();
  });

  it('应该调用onResetFilters', async () => {
    const { AnalyticsFilters } = await import('../AnalyticsFilters');
    const handleReset = vi.fn();
    renderWithProviders(<AnalyticsFilters filters={{}} onFiltersChange={vi.fn()} onResetFilters={handleReset} />);

    fireEvent.click(screen.getByTestId('reset-btn'));
    expect(handleReset).toHaveBeenCalled();
  });

  it('应该调用onToggleAdvanced', async () => {
    const { AnalyticsFilters } = await import('../AnalyticsFilters');
    const handleToggle = vi.fn();
    renderWithProviders(
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
    renderWithProviders(<AnalyticsFilters filters={{}} onFiltersChange={vi.fn()} />);

    expect(screen.getByTestId('filters-provider')).toBeInTheDocument();
  });

  it('应该处理realTimeUpdate属性', async () => {
    const { AnalyticsFilters } = await import('../AnalyticsFilters');
    renderWithProviders(<AnalyticsFilters filters={{}} onFiltersChange={vi.fn()} realTimeUpdate={false} />);

    expect(screen.getByTestId('filters-provider')).toBeInTheDocument();
  });
});
