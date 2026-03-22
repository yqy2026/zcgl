/**
 * AssetListPage 页面测试
 */

import React from 'react';
import { renderWithProviders, screen, fireEvent, waitFor } from '@/test/utils/test-helpers';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { useQuery } from '@tanstack/react-query';
import AssetListPage from '../AssetListPage';

// Mock services
vi.mock('@/services/assetService', () => ({
  assetService: {
    deleteAsset: vi.fn(),
    restoreAsset: vi.fn(),
    hardDeleteAsset: vi.fn(),
    exportAssets: vi.fn(),
    exportSelectedAssets: vi.fn(),
  },
}));

vi.mock('@tanstack/react-query', () => ({
  useQuery: vi.fn(),
}));

// Mock components
vi.mock('@/components/Asset/AssetList', () => ({
  default: ({
    data: _data,
    onEdit,
    onDelete,
    onRestore,
    onHardDelete,
    onView,
  }: {
    data: unknown;
    onEdit: (asset: { id: string }) => void;
    onDelete: (id: string) => void;
    onRestore: (id: string) => void;
    onHardDelete: (id: string) => void;
    onView: (asset: { id: string }) => void;
  }) => (
    <div data-testid="asset-list">
      Asset List Component
      <button onClick={() => onEdit({ id: 'asset_1' })}>Edit</button>
      <button onClick={() => onDelete('asset_1')}>Delete</button>
      <button onClick={() => onRestore('asset_1')}>Restore</button>
      <button onClick={() => onHardDelete('asset_1')}>HardDelete</button>
      <button onClick={() => onView({ id: 'asset_1' })}>View</button>
    </div>
  ),
}));

vi.mock('@/components/Asset/AssetSearch', () => ({
  default: ({
    onSearch,
    onReset,
  }: {
    onSearch: (params: unknown) => void;
    onReset: () => void;
  }) => (
    <div data-testid="asset-search">
      <button onClick={() => onSearch({ keyword: 'test' })}>Search</button>
      <button onClick={onReset}>Reset</button>
    </div>
  ),
}));

vi.mock('@/components/Asset/AssetAreaSummary', () => ({
  default: () => <div data-testid="asset-area-summary">Area Summary</div>,
}));

vi.mock('@/components/Common/StateContainer', () => ({
  PageContainer: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="page-container">{children}</div>
  ),
  ContentSection: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  LoadingContainer: ({ text }: { text: string }) => <div data-testid="loading">{text}</div>,
}));

vi.mock('@/utils/logger', () => ({
  createLogger: () => ({
    info: vi.fn(),
    error: vi.fn(),
    warn: vi.fn(),
  }),
}));

vi.mock('@/utils/messageManager', () => ({
  MessageManager: {
    success: vi.fn(),
    error: vi.fn(),
    warning: vi.fn(),
  },
}));

const mockUseView = vi.fn(() => ({
  currentView: {
    key: 'owner:party-1',
    perspective: 'owner',
    partyId: 'party-1',
    partyName: '主体A',
    label: '产权方 · 主体A',
  },
  selectionRequired: false,
  isViewReady: true,
}));

vi.mock('@/contexts/ViewContext', () => ({
  useView: () => mockUseView(),
}));

const mockBuildQueryScopeKey = vi.fn(() => 'user:user-1|perspective:owner');
const mockUseRoutePerspective = vi.fn(() => ({
  perspective: 'owner',
  isPerspectiveRoute: true,
}));

vi.mock('@/utils/queryScope', () => ({
  buildQueryScopeKey: (value: unknown) => mockBuildQueryScopeKey(value),
}));

vi.mock('@/routes/perspective', () => ({
  useRoutePerspective: () => mockUseRoutePerspective(),
}));
import { assetService } from '@/services/assetService';
import { MessageManager } from '@/utils/messageManager';

const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

const renderPage = (route = '/owner/assets') => renderWithProviders(<AssetListPage />, { route });

let mockData: Array<{ id: string; asset_name: string }> = [];
let mockIsAssetsInitialLoading = false;
let mockIsAssetsFetching = false;
let mockError: Error | null = null;
let mockPagination = { current: 1, pageSize: 20, total: 0 };
let mockAnalyticsData: { data: Record<string, unknown> } = { data: {} };
let mockAnalyticsLoading = false;

const mockRefetchAssets = vi.fn().mockResolvedValue({ data: undefined });
const mockRefetchAnalytics = vi.fn().mockResolvedValue({ data: undefined });
const mockFallbackRefetch = vi.fn().mockResolvedValue({ data: undefined });

const buildAssetsQueryResult = () =>
  ({
    data: {
      items: mockData,
      total: mockPagination.total,
      pages:
        mockPagination.pageSize > 0 ? Math.ceil(mockPagination.total / mockPagination.pageSize) : 0,
    },
    error: mockError,
    isLoading: mockIsAssetsInitialLoading,
    isFetching: mockIsAssetsFetching,
    refetch: mockRefetchAssets,
  }) as unknown as ReturnType<typeof useQuery>;

const buildAnalyticsQueryResult = () =>
  ({
    data: mockAnalyticsData,
    isLoading: mockAnalyticsLoading,
    refetch: mockRefetchAnalytics,
  }) as unknown as ReturnType<typeof useQuery>;

const buildFallbackQueryResult = () =>
  ({
    data: undefined,
    error: null,
    isLoading: false,
    isFetching: false,
    refetch: mockFallbackRefetch,
  }) as unknown as ReturnType<typeof useQuery>;

describe('AssetListPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseView.mockReturnValue({
      currentView: {
        key: 'owner:party-1',
        perspective: 'owner',
        partyId: 'party-1',
        partyName: '主体A',
        label: '产权方 · 主体A',
      },
      selectionRequired: false,
      isViewReady: true,
    });
    mockUseRoutePerspective.mockReturnValue({
      perspective: 'owner',
      isPerspectiveRoute: true,
    });
    mockData = [
      { id: 'asset_1', asset_name: '资产A' },
      { id: 'asset_2', asset_name: '资产B' },
    ];
    mockIsAssetsInitialLoading = false;
    mockIsAssetsFetching = false;
    mockError = null;
    mockPagination = { current: 1, pageSize: 20, total: 2 };
    mockAnalyticsData = { data: {} };
    mockAnalyticsLoading = false;

    vi.mocked(useQuery).mockImplementation(options => {
      const [scope] = options.queryKey as [string, ...unknown[]];
      if (scope === 'assets-list') {
        return buildAssetsQueryResult();
      }
      if (scope === 'analytics') {
        return buildAnalyticsQueryResult();
      }
      return buildFallbackQueryResult();
    });
  });

  describe('渲染', () => {
    it('渲染页面标题', () => {
      renderPage();

      expect(screen.getByText('资产列表')).toBeInTheDocument();
      expect(mockBuildQueryScopeKey).toHaveBeenCalledWith('owner');
    });

    it('渲染操作按钮', () => {
      renderPage();

      expect(screen.getByText('新增资产')).toBeInTheDocument();
      expect(screen.getByText('导入资产')).toBeInTheDocument();
      expect(screen.getByText('导出全部')).toBeInTheDocument();
    });

    it('渲染搜索组件', () => {
      renderPage();

      expect(screen.getByTestId('asset-search')).toBeInTheDocument();
    });

    it('渲染面积汇总组件', () => {
      renderPage();

      expect(screen.getByTestId('asset-area-summary')).toBeInTheDocument();
    });

    it('渲染资产列表组件', () => {
      renderPage();

      expect(screen.getByTestId('asset-list')).toBeInTheDocument();
    });

    it('显示当前视角标签', () => {
      renderPage();

      expect(screen.getByText('当前视角')).toBeInTheDocument();
      expect(screen.getByText('业主视角')).toBeInTheDocument();
    });

    it('资产列表与统计查询应把当前视角纳入 queryKey', () => {
      renderPage();

      expect(useQuery).toHaveBeenCalledWith(
        expect.objectContaining({
          queryKey: ['assets-list', 'user:user-1|perspective:owner', 1, 20, {}],
        })
      );
      expect(useQuery).toHaveBeenCalledWith(
        expect.objectContaining({
          queryKey: ['analytics', 'user:user-1|perspective:owner', {}],
        })
      );
    });

    it('legacy 路径不显示视角标签，但仍启用资产列表和统计查询', () => {
      mockUseView.mockReturnValue({
        currentView: null,
        selectionRequired: true,
        isViewReady: false,
      });
      mockUseRoutePerspective.mockReturnValue({
        perspective: null,
        isPerspectiveRoute: false,
      });

      renderPage('/assets/list');

      expect(screen.queryByText('当前视角')).not.toBeInTheDocument();
      expect(useQuery).toHaveBeenCalledWith(
        expect.objectContaining({
          queryKey: ['assets-list', 'user:user-1|perspective:owner', 1, 20, {}],
        })
      );
      expect(useQuery).toHaveBeenCalledWith(
        expect.objectContaining({
          queryKey: ['analytics', 'user:user-1|perspective:owner', {}],
        })
      );
    });
  });

  describe('加载状态', () => {
    it('加载中显示加载状态', () => {
      mockIsAssetsInitialLoading = true;
      mockData = [];
      mockPagination = { current: 1, pageSize: 20, total: 0 };

      renderPage();

      expect(screen.getByTestId('loading')).toBeInTheDocument();
      expect(screen.getByText('加载资产数据中...')).toBeInTheDocument();
    });
  });

  describe('错误处理', () => {
    it('显示错误信息', async () => {
      mockError = new Error('服务器错误');
      mockData = [];
      mockIsAssetsInitialLoading = false;
      mockPagination = { current: 1, pageSize: 20, total: 0 };

      renderPage();

      await waitFor(() => {
        expect(screen.getByText('数据加载失败')).toBeInTheDocument();
      });
      expect(screen.getByText('重新加载')).toBeInTheDocument();

      fireEvent.click(screen.getByText('重新加载'));
      await waitFor(() => {
        expect(mockRefetchAssets).toHaveBeenCalled();
      });
    });
  });

  describe('导航功能', () => {
    it('点击新增资产导航到创建页', () => {
      renderPage();

      fireEvent.click(screen.getByText('新增资产'));

      expect(mockNavigate).toHaveBeenCalledWith('/assets/new');
    });

    it('点击导入资产导航到导入页', () => {
      renderPage();

      fireEvent.click(screen.getByText('导入资产'));

      expect(mockNavigate).toHaveBeenCalledWith('/assets/import');
    });

    it('点击编辑导航到编辑页', () => {
      renderPage();

      fireEvent.click(screen.getByText('Edit'));

      expect(mockNavigate).toHaveBeenCalledWith('/assets/asset_1/edit');
    });

    it('点击查看导航到详情页', () => {
      renderPage();

      fireEvent.click(screen.getByText('View'));

      expect(mockNavigate).toHaveBeenCalledWith('/assets/asset_1');
    });
  });

  describe('删除功能', () => {
    it('删除成功显示成功消息', async () => {
      vi.mocked(assetService.deleteAsset).mockResolvedValue(undefined);

      renderPage();

      fireEvent.click(screen.getByText('Delete'));

      await waitFor(() => {
        expect(assetService.deleteAsset).toHaveBeenCalledWith('asset_1');
        expect(MessageManager.success).toHaveBeenCalledWith('删除成功，已移入回收站');
        expect(mockRefetchAssets).toHaveBeenCalledTimes(1);
        expect(mockRefetchAnalytics).toHaveBeenCalledTimes(1);
      });
    });

    it('删除失败显示错误消息', async () => {
      vi.mocked(assetService.deleteAsset).mockRejectedValue(new Error('删除失败'));

      renderPage();

      fireEvent.click(screen.getByText('Delete'));

      await waitFor(() => {
        expect(MessageManager.error).toHaveBeenCalledWith('删除失败');
      });
    });

    it('恢复成功后应同时刷新资产列表和统计摘要', async () => {
      vi.mocked(assetService.restoreAsset).mockResolvedValue(undefined);

      renderPage();

      fireEvent.click(screen.getByText('Restore'));

      await waitFor(() => {
        expect(assetService.restoreAsset).toHaveBeenCalledWith('asset_1');
        expect(MessageManager.success).toHaveBeenCalledWith('恢复成功');
        expect(mockRefetchAssets).toHaveBeenCalledTimes(1);
        expect(mockRefetchAnalytics).toHaveBeenCalledTimes(1);
      });
    });

    it('彻底删除成功后应同时刷新资产列表和统计摘要', async () => {
      vi.mocked(assetService.hardDeleteAsset).mockResolvedValue(undefined);

      renderPage();

      fireEvent.click(screen.getByText('HardDelete'));

      await waitFor(() => {
        expect(assetService.hardDeleteAsset).toHaveBeenCalledWith('asset_1');
        expect(MessageManager.success).toHaveBeenCalledWith('彻底删除成功');
        expect(mockRefetchAssets).toHaveBeenCalledTimes(1);
        expect(mockRefetchAnalytics).toHaveBeenCalledTimes(1);
      });
    });
  });

  describe('搜索功能', () => {
    it('点击搜索触发带关键字的查询键更新', async () => {
      renderPage();

      fireEvent.click(screen.getByText('Search'));

      await waitFor(() => {
        const calls = vi.mocked(useQuery).mock.calls;
        const hasKeywordQuery = calls.some(([queryOptions]) => {
          const queryKey = queryOptions.queryKey;
          if (!Array.isArray(queryKey) || queryKey[0] !== 'assets-list') {
            return false;
          }
          if (queryKey[1] !== 'user:user-1|perspective:owner') {
            return false;
          }
          const filters = queryKey[4];
          if (filters == null || typeof filters !== 'object') {
            return false;
          }
          return (filters as { keyword?: string }).keyword === 'test';
        });
        expect(hasKeywordQuery).toBe(true);
      });
    });

    it('点击重置触发空筛选查询键', async () => {
      renderPage();

      fireEvent.click(screen.getByText('Search'));

      fireEvent.click(screen.getByText('Reset'));

      await waitFor(() => {
        const calls = vi.mocked(useQuery).mock.calls;
        const hasEmptyFiltersQuery = calls.some(([queryOptions]) => {
          const queryKey = queryOptions.queryKey;
          if (!Array.isArray(queryKey) || queryKey[0] !== 'assets-list') {
            return false;
          }
          if (queryKey[1] !== 'user:user-1|perspective:owner') {
            return false;
          }
          const filters = queryKey[4];
          if (filters == null || typeof filters !== 'object') {
            return false;
          }
          return Object.keys(filters).length === 0;
        });
        expect(hasEmptyFiltersQuery).toBe(true);
      });
    });
  });

  describe('导出功能', () => {
    it('点击导出全部触发导出', async () => {
      const mockBlob = new Blob(['test'], { type: 'application/xlsx' });
      vi.mocked(assetService.exportAssets).mockResolvedValue(mockBlob);

      // Mock URL.createObjectURL
      global.URL.createObjectURL = vi.fn(() => 'blob:test');
      global.URL.revokeObjectURL = vi.fn();

      renderPage();

      fireEvent.click(screen.getByText('导出全部'));

      await waitFor(() => {
        expect(assetService.exportAssets).toHaveBeenCalledWith({}, { format: 'xlsx' });
        expect(MessageManager.success).toHaveBeenCalledWith('资产数据导出成功');
      });
    });
  });
});
